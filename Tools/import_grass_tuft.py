# Import the single low-poly grass tufts SM_GrassTuft1..3 (Export/Blender/scripts/props/gen_grass_tuft.py)
# -> /Game/Environment/Foliage, material M_Stylized_Foliage, no collision (walk through).
# Run with the editor closed:
#   UnrealEditor-Cmd.exe <project>.uproject -run=pythonscript -script="<this file>" -unattended -nosplash -stdout
import os
import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
DEST = "/Game/Environment/Foliage"
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda m: unreal.log_warning("TUFT " + m)
foliage = unreal.load_asset("/Game/Environment/Materials/M_Stylized_Foliage")

for name in ["SM_GrassTuft1", "SM_GrassTuft2", "SM_GrassTuft3"]:
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
        mesh.set_material(i, foliage)
    bs = mesh.get_editor_property("body_setup")
    bs.set_editor_property("agg_geom", unreal.KAggregateGeom())
    bi = bs.get_editor_property("default_instance")
    bi.set_editor_property("collision_profile_name", "NoCollision")
    bi.set_editor_property("collision_enabled", unreal.CollisionEnabled.NO_COLLISION)
    bs.set_editor_property("default_instance", bi)
    eal.save_asset(path, only_if_is_dirty=False)
    b = mesh.get_bounding_box()
    log(f"OK {name} convex={len(bs.get_editor_property('agg_geom').get_editor_property('convex_elems'))} "
        f"size_cm=({b.max.x - b.min.x:.0f},{b.max.y - b.min.y:.0f},{b.max.z - b.min.z:.0f})")
# leftover material created by the FBX import
for p in [f"{DEST}/M_Stylized_Foliage"]:
    if eal.does_asset_exist(p):
        eal.delete_asset(p)
