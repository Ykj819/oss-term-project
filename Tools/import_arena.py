# Import Export/SM_Arena.fbx (Export/Blender/Arena.blend, scripts/env/gen_arena.py + bake_arena.py)
# -> /Game/Environment/Arena/SM_Arena, material M_Stylized_Prop (vertex colours), complex-as-simple collision.
#   UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script="Tools/import_arena.py" -unattended -nosplash -stdout
import os
import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
FBX = os.path.join(PROJ, "Export", "SM_Arena.fbx")
DEST = "/Game/Environment/Arena"
MAT = "/Game/Environment/Materials/M_Stylized_Prop"
eal = unreal.EditorAssetLibrary
log = lambda m: unreal.log_warning("ARENA " + m)

before = set(eal.list_assets(DEST, recursive=True)) if eal.does_directory_exist(DEST) else set()
task = unreal.AssetImportTask()
task.set_editor_property("filename", FBX)
task.set_editor_property("destination_path", DEST)
task.set_editor_property("destination_name", "SM_Arena")
task.set_editor_property("automated", True)
task.set_editor_property("replace_existing", True)
task.set_editor_property("save", True)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

mat = unreal.load_asset(MAT)
mesh = None
for p in eal.list_assets(DEST, recursive=True):
    a = unreal.load_asset(p)
    log(f"asset {p} {a.get_class().get_name() if a else None}")
    if isinstance(a, unreal.StaticMesh):
        mesh = a
if not mesh:
    log("FAILED no static mesh")
else:
    for i in range(len(mesh.get_editor_property("static_materials"))):
        mesh.set_material(i, mat)
    bs = mesh.get_editor_property("body_setup")
    bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    eal.save_asset(mesh.get_path_name().split(".")[0], only_if_is_dirty=False)
    for p in eal.list_assets(DEST, recursive=True):
        a = unreal.load_asset(p)
        if isinstance(a, (unreal.Material, unreal.Texture)):
            eal.delete_asset(p.split(".")[0])
            log(f"deleted leftover {p}")
    b = mesh.get_bounding_box()
    log(f"MESH_OK {mesh.get_path_name()} size_cm=({b.max.x - b.min.x:.0f},{b.max.y - b.min.y:.0f},{b.max.z - b.min.z:.0f}) "
        f"nanite={mesh.get_editor_property('nanite_settings').get_editor_property('enabled')}")
