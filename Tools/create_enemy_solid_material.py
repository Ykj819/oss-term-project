# /Game/Characters/Enemies/Materials/M_EnemySolid: plain lit colour for enemies built from engine shapes
# (EnemyBall ball + spikes, EnemyLeech segments + mouth). Params: Color (vector, set per part by C++ MIDs), Roughness.
# Replaces the engine's BasicShapeMaterial on those parts (it showed the grey grid default material).
# Editor closed:
#   UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script="<abs/forward/slash>/Tools/create_enemy_solid_material.py" -unattended -nosplash -stdout
import unreal

PATH, NAME = "/Game/Characters/Enemies/Materials", "M_EnemySolid"
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
if eal.does_asset_exist(f"{PATH}/{NAME}"):
    eal.delete_asset(f"{PATH}/{NAME}")
m = unreal.AssetToolsHelpers.get_asset_tools().create_asset(NAME, PATH, unreal.Material, unreal.MaterialFactoryNew())
col = mel.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -500, 0)
col.set_editor_property("parameter_name", "Color"); col.set_editor_property("default_value", unreal.LinearColor(0.5, 0.5, 0.5, 1))
mel.connect_material_property(col, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
r = mel.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -500, 250)
r.set_editor_property("parameter_name", "Roughness"); r.set_editor_property("default_value", 0.55)
mel.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
mel.recompile_material(m)
eal.save_asset(f"{PATH}/{NAME}", only_if_is_dirty=False)
unreal.log_warning(f"SOLIDMAT OK nexpr={mel.get_num_material_expressions(m)}")
