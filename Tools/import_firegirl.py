# FireGirl (sitting butler girl on a stool, static pose) from Export/Blender/firegirl_maybe.blend:
# the posed character + stool were frozen to meshes, UV-packed into ONE atlas and their procedural colours baked
# (Cycles diffuse colour) to Export/Textures/FireGirl/T_FireGirl_BC.png.
# Export/SM_FireGirl.fbx + Export/SM_FireGirl_Stool.fbx (same pivot: floor under the stool centre, real size ~1.7 m tall
# standing) -> /Game/Characters/FireGirl/{SM_FireGirl, SM_FireGirl_Stool, T_FireGirl_BC, M_FireGirl}.
# M_FireGirl (deleted + rebuilt each run): lit, two-sided (thin blindfold / lashes), Nanite, BaseColor = texture * Tint,
# params Roughness / Tint. Meshes: Nanite on, no collision for the character, simple box-ish collision kept for the stool.
# Editor closed:
#   UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script="<abs/forward/slash>/Tools/import_firegirl.py" -unattended -nosplash -stdout
import os
import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
DEST = "/Game/Characters/FireGirl"
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda m: unreal.log_warning("FIREGIRL " + m)

# clean the folder (fresh import, no stale Interchange settings / leftover materials)
for a in eal.list_assets(DEST, recursive=True, include_folder=False) if eal.does_directory_exist(DEST) else []:
    eal.delete_asset(a.split(".")[0])


def import_file(path, dest):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", path)
    task.set_editor_property("destination_path", dest); task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True); task.set_editor_property("save", False)
    tools.import_asset_tasks([task])


for name in ("SM_FireGirl", "SM_FireGirl_Stool"):
    import_file(os.path.join(PROJ, "Export", name + ".fbx"), DEST)

# drop whatever the FBX import created besides the meshes (Blender material / texture copies)
for a in eal.list_assets(DEST, recursive=True, include_folder=False):
    p = a.split(".")[0]
    if not p.split("/")[-1].startswith("SM_FireGirl"):
        eal.delete_asset(p)

import_file(os.path.join(PROJ, "Export", "Textures", "FireGirl", "T_FireGirl_BC.png"), DEST)
tex = unreal.load_asset(f"{DEST}/T_FireGirl_BC")
tex.set_editor_property("srgb", True)
eal.save_asset(f"{DEST}/T_FireGirl_BC", only_if_is_dirty=False)

m = tools.create_asset("M_FireGirl", DEST, unreal.Material, unreal.MaterialFactoryNew())
m.set_editor_property("two_sided", True)
m.set_editor_property("used_with_nanite", True)
E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
s = E(unreal.MaterialExpressionTextureSampleParameter2D, -600, 0)
s.set_editor_property("parameter_name", "BaseColorMap"); s.set_editor_property("texture", tex)
tint = E(unreal.MaterialExpressionVectorParameter, -600, -250)
tint.set_editor_property("parameter_name", "Tint"); tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
mul = E(unreal.MaterialExpressionMultiply, -300, 0)
mel.connect_material_expressions(s, "RGB", mul, "A"); mel.connect_material_expressions(tint, "", mul, "B")
mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
rough = E(unreal.MaterialExpressionScalarParameter, -300, 200)
rough.set_editor_property("parameter_name", "Roughness"); rough.set_editor_property("default_value", 0.6)
mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
mel.recompile_material(m)
eal.save_asset(f"{DEST}/M_FireGirl", only_if_is_dirty=False)

for name in ("SM_FireGirl", "SM_FireGirl_Stool"):
    path = f"{DEST}/{name}"
    mesh = unreal.load_asset(path)
    if not mesh:
        log(f"FAILED {name}"); continue
    for i in range(len(mesh.get_editor_property("static_materials"))):
        mesh.set_material(i, m)
    ns = mesh.get_editor_property("nanite_settings"); ns.set_editor_property("enabled", True)
    mesh.set_editor_property("nanite_settings", ns)
    if name == "SM_FireGirl":
        mesh.get_editor_property("body_setup").set_editor_property("agg_geom", unreal.KAggregateGeom())
    eal.save_asset(path, only_if_is_dirty=False)
    b = mesh.get_bounding_box()
    try:
        tris = unreal.EditorStaticMeshLibrary.get_number_verts(mesh, 0)
    except Exception:
        tris = -1
    log(f"OK {name} verts={tris} size_cm=({b.max.x - b.min.x:.0f},{b.max.y - b.min.y:.0f},"
        f"{b.max.z - b.min.z:.0f}) min_z={b.min.z:.0f}")
log("DONE " + ", ".join(a.split("/")[-1] for a in eal.list_assets(DEST, recursive=True, include_folder=False)))
