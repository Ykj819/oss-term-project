# Import the vertical round stone shaft (Export/SM_StoneShaft.fbx, made by Export/Blender/scripts/props/gen_stone_shaft.py)
# with its UCX_ collision into /Game/Environment/Props, material M_Stylized_Prop (vertex colours).
# Same method as import_stone_tunnel.py (default Interchange pipeline keeps the UCX collision; delete + fresh import).
# Editor closed:
#   UnrealEditor-Cmd.exe <project>.uproject -run=pythonscript -script="<abs/forward/slash/path>/Tools/import_stone_shaft.py" -unattended -nosplash -stdout
import os
import unreal

PROPS = [("SM_StoneShaft", "/Game/Environment/Props")]

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
prop_mat = unreal.load_asset("/Game/Environment/Materials/M_Stylized_Prop")

for name, dest in PROPS:
    if eal.does_asset_exist(f"{dest}/{name}"):
        eal.delete_asset(f"{dest}/{name}")
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", os.path.join(PROJ, "Export", name + ".fbx"))
    task.set_editor_property("destination_path", dest); task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True); task.set_editor_property("save", False)
    tools.import_asset_tasks([task])
    path = f"{dest}/{name}"
    mesh = unreal.load_asset(path)
    if not mesh:
        unreal.log_warning(f"SHAFT FAILED {name}"); continue
    for i in range(len(mesh.get_editor_property("static_materials"))):
        mesh.set_material(i, prop_mat)
    ns = mesh.get_editor_property("nanite_settings"); ns.set_editor_property("enabled", True)
    mesh.set_editor_property("nanite_settings", ns)
    eal.save_asset(path, only_if_is_dirty=False)
    leftover = f"{dest}/M_Stylized_Prop"
    if eal.does_asset_exist(leftover):
        eal.delete_asset(leftover)
    ag = mesh.get_editor_property("body_setup").get_editor_property("agg_geom")
    b = mesh.get_bounding_box()
    unreal.log_warning(f"SHAFT OK {name} convex={len(ag.get_editor_property('convex_elems'))} "
                       f"size_cm=({b.max.x - b.min.x:.0f},{b.max.y - b.min.y:.0f},{b.max.z - b.min.z:.0f}) "
                       f"min=({b.min.x:.0f},{b.min.y:.0f},{b.min.z:.0f})")
