# Creates /Game/Effects/M_WeatherParticle: unlit, translucent, two-sided, usable on instanced static meshes.
# Vector parameter "Color": RGB -> Emissive Color (can go above 1), A -> Opacity. Used by UBossWeatherComponent (snow / rain).
# Run with the editor closed:
#   UnrealEditor-Cmd.exe <project>.uproject -run=pythonscript -script="<this file>" -unattended -nosplash -stdout
import unreal

PATH = "/Game/Effects"
NAME = "M_WeatherParticle"
FULL = f"{PATH}/{NAME}"

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary

if eal.does_asset_exist(FULL):
    eal.delete_asset(FULL)

tools = unreal.AssetToolsHelpers.get_asset_tools()
mat = tools.create_asset(NAME, PATH, unreal.Material, unreal.MaterialFactoryNew())

mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
mat.set_editor_property("two_sided", True)
mat.set_editor_property("used_with_instanced_static_meshes", True)

color = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -400, 0)
color.set_editor_property("parameter_name", "Color")
color.set_editor_property("default_value", unreal.LinearColor(1.0, 1.0, 1.0, 1.0))

mel.connect_material_property(color, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
mel.connect_material_property(color, "A", unreal.MaterialProperty.MP_OPACITY)

mel.recompile_material(mat)
eal.save_asset(FULL, only_if_is_dirty=False)
unreal.log_warning(f"WEATHER_MATERIAL_OK {FULL} ism={mat.get_editor_property('used_with_instanced_static_meshes')}")
