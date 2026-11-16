# Imports the procedural bark texture set (Export/Textures/RealBark, made by
# Export/Blender/scripts/textures/gen_bark_texture.py) into /Game/Environment/Trees/Textures and rebuilds
# M_RealisticTree_Bark around it:
#   BaseColor = T_RealBark_BC * VertexColor^2.2 (moss / young-bark multiplier baked on the mesh) * Tint
#   Normal    = T_RealBark_N (DirectX)            AO = ARH.R        Roughness = ARH.G * RoughnessScale
# Tiling: the mesh UVs are already in tile units (one tile = 0.7 m of bark), parameter TextureScale multiplies them.
# Run with the editor closed, BEFORE Tools/import_realistic_tree.py (which then keeps this material):
#   UnrealEditor-Cmd.exe <project>.uproject -run=pythonscript -script="<this file>" -unattended -nosplash -stdout
import os
import unreal

TEX_DIR = "/Game/Environment/Trees/Textures"
MAT = "/Game/Environment/Trees/M_RealisticTree_Bark"
SRC = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()), "Export", "Textures", "RealBark")

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()

# ---- textures
SETTINGS = {
    "T_RealBark_BC": dict(srgb=True, comp=unreal.TextureCompressionSettings.TC_DEFAULT),
    "T_RealBark_N": dict(srgb=False, comp=unreal.TextureCompressionSettings.TC_NORMALMAP),
    "T_RealBark_ARH": dict(srgb=False, comp=unreal.TextureCompressionSettings.TC_MASKS),
}
tex = {}
for name, s in SETTINGS.items():
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", os.path.join(SRC, name + ".png"))
    task.set_editor_property("destination_path", TEX_DIR)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False)
    tools.import_asset_tasks([task])
    t = unreal.load_asset(f"{TEX_DIR}/{name}")
    t.set_editor_property("srgb", s["srgb"])
    t.set_editor_property("compression_settings", s["comp"])
    if name.endswith("_N"):
        t.set_editor_property("flip_green_channel", False)  # already DirectX
    eal.save_asset(f"{TEX_DIR}/{name}", only_if_is_dirty=False)
    tex[name] = t

# ---- material (rebuilt in place so the meshes keep pointing at it)
if eal.does_asset_exist(MAT):
    mat = unreal.load_asset(MAT)
    mel.delete_all_material_expressions(mat)
else:
    mat = tools.create_asset("M_RealisticTree_Bark", "/Game/Environment/Trees", unreal.Material, unreal.MaterialFactoryNew())
mat.set_editor_property("two_sided", False)
mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
mat.set_editor_property("used_with_instanced_static_meshes", True)


def expr(cls, x, y):
    return mel.create_material_expression(mat, cls, x, y)


def scalar(name, value, x, y):
    e = expr(unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", name); e.set_editor_property("default_value", value)
    return e


uv = expr(unreal.MaterialExpressionTextureCoordinate, -1500, 0)
tscale = scalar("TextureScale", 1.0, -1500, 120)
uvm = expr(unreal.MaterialExpressionMultiply, -1300, 0)
mel.connect_material_expressions(uv, "", uvm, "A"); mel.connect_material_expressions(tscale, "", uvm, "B")


def sample(name, sampler, x, y):
    e = expr(unreal.MaterialExpressionTextureSample, x, y)
    e.set_editor_property("texture", tex[name]); e.set_editor_property("sampler_type", sampler)
    mel.connect_material_expressions(uvm, "", e, "UVs")
    return e


bc = sample("T_RealBark_BC", unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, -1050, -250)
nrm = sample("T_RealBark_N", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, -1050, 100)
arh = sample("T_RealBark_ARH", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, -1050, 400)

vc = expr(unreal.MaterialExpressionVertexColor, -1050, -500)
gamma = scalar("VertexColorGamma", 2.2, -1050, -620)
vpow = expr(unreal.MaterialExpressionPower, -800, -500)
mel.connect_material_expressions(vc, "", vpow, "Base"); mel.connect_material_expressions(gamma, "", vpow, "Exp")

tint = expr(unreal.MaterialExpressionVectorParameter, -800, -350)
tint.set_editor_property("parameter_name", "Tint"); tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
m1 = expr(unreal.MaterialExpressionMultiply, -550, -300)
mel.connect_material_expressions(bc, "RGB", m1, "A"); mel.connect_material_expressions(vpow, "", m1, "B")
m2 = expr(unreal.MaterialExpressionMultiply, -350, -300)
mel.connect_material_expressions(m1, "", m2, "A"); mel.connect_material_expressions(tint, "", m2, "B")
mel.connect_material_property(m2, "", unreal.MaterialProperty.MP_BASE_COLOR)

mel.connect_material_property(nrm, "RGB", unreal.MaterialProperty.MP_NORMAL)
mel.connect_material_property(arh, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
rs = scalar("RoughnessScale", 1.0, -800, 550)
rm = expr(unreal.MaterialExpressionMultiply, -550, 450)
mel.connect_material_expressions(arh, "G", rm, "A"); mel.connect_material_expressions(rs, "", rm, "B")
mel.connect_material_property(rm, "", unreal.MaterialProperty.MP_ROUGHNESS)

mel.recompile_material(mat)
eal.save_asset(MAT, only_if_is_dirty=False)
unreal.log_warning(f"REAL_BARK_OK textures={list(tex)} material={MAT} expressions={mel.get_num_material_expressions(mat)}")
