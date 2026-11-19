# Import the stylized clouds (Export/Blender/scripts/props/gen_clouds.py) -> /Game/Environment/Sky
# Material M_Stylized_Cloud (/Game/Environment/Materials): lit vertex-colour material, VertexColor^2.2 * Tint,
# Roughness 1. No collision. Run with the editor closed, or in the open editor via Tools -> Execute Python Script.
import os
import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
DEST = "/Game/Environment/Sky"
MAT = "/Game/Environment/Materials/M_Stylized_Cloud"
NAMES = ["SM_Cloud_Small", "SM_Cloud_Medium", "SM_Cloud_Long", "SM_Cloud_Cumulus", "SM_Cloud_HorizonBand"]
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda m: unreal.log_warning("CLOUD " + m)

if eal.does_asset_exist(MAT):
    mat = unreal.load_asset(MAT)
else:
    mat = tools.create_asset("M_Stylized_Cloud", MAT.rsplit("/", 1)[0], unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("used_with_instanced_static_meshes", True)
    mat.set_editor_property("used_with_nanite", True)
    vc =mel.create_material_expression(mat, unreal.MaterialExpressionVertexColor, -700, 0)
    g = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -700, 200)
    g.set_editor_property("parameter_name", "VertexColorGamma"); g.set_editor_property("default_value", 2.2)
    pw = mel.create_material_expression(mat, unreal.MaterialExpressionPower, -450, 0)
    mel.connect_material_expressions(vc, "", pw, "Base"); mel.connect_material_expressions(g, "", pw, "Exp")
    tint = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -450, 200)
    tint.set_editor_property("parameter_name", "Tint"); tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    mul = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -200, 0)
    mel.connect_material_expressions(pw, "", mul, "A"); mel.connect_material_expressions(tint, "", mul, "B")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    r = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -200, 250)
    r.set_editor_property("parameter_name", "Roughness"); r.set_editor_property("default_value", 1.0)
    mel.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(mat); eal.save_asset(MAT, only_if_is_dirty=False)

for name in NAMES:
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", os.path.join(PROJ, "Export", name + ".fbx"))
    task.set_editor_property("destination_path", DEST); task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True); task.set_editor_property("save", False)
    tools.import_asset_tasks([task])
    path = f"{DEST}/{name}"
    mesh = unreal.load_asset(path)
    if not mesh:
        log(f"FAILED {name}"); continue
    for i in range(len(mesh.get_editor_property("static_materials"))):
        mesh.set_material(i, mat)
    bs = mesh.get_editor_property("body_setup")
    bs.set_editor_property("agg_geom", unreal.KAggregateGeom())
    bi = bs.get_editor_property("default_instance")
    bi.set_editor_property("collision_profile_name", "NoCollision")
    bi.set_editor_property("collision_enabled", unreal.CollisionEnabled.NO_COLLISION)
    bs.set_editor_property("default_instance", bi)
    eal.save_asset(path, only_if_is_dirty=False)
    b = mesh.get_bounding_box()
    log(f"OK {name} size_m=({(b.max.x - b.min.x) / 100:.0f},{(b.max.y - b.min.y) / 100:.0f},{(b.max.z - b.min.z) / 100:.0f})")
leftover = f"{DEST}/M_Stylized_Cloud"
if eal.does_asset_exist(leftover):
    eal.delete_asset(leftover)
