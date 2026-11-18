# Import single stylized props (FBX in Export/, made by Export/Blender/scripts/props/*) with their UCX_ collision,
# material M_Stylized_Prop. Edit PROPS below: (fbx name, destination folder).
# Run with the editor closed, or in the open editor via Tools -> Execute Python Script:
#   UnrealEditor-Cmd.exe <project>.uproject -run=pythonscript -script="<this file>" -unattended -nosplash -stdout
import os
import unreal

PROPS = [("SM_StylizedFence", "/Game/Environment/Props")]

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
prop_mat = unreal.load_asset("/Game/Environment/Materials/M_Stylized_Prop")

for name, dest in PROPS:
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", os.path.join(PROJ, "Export", name + ".fbx"))
    task.set_editor_property("destination_path", dest); task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True); task.set_editor_property("save", False)
    tools.import_asset_tasks([task])
    path = f"{dest}/{name}"
    mesh = unreal.load_asset(path)
    if not mesh:
        unreal.log_warning(f"PROP FAILED {name}"); continue
    for i in range(len(mesh.get_editor_property("static_materials"))):
        mesh.set_material(i, prop_mat)
    eal.save_asset(path, only_if_is_dirty=False)
    leftover = f"{dest}/M_Stylized_Prop"
    if eal.does_asset_exist(leftover):
        eal.delete_asset(leftover)
    bs = mesh.get_editor_property("body_setup")
    b = mesh.get_bounding_box()
    unreal.log_warning(f"PROP OK {name} boxes={len(bs.get_editor_property('agg_geom').get_editor_property('box_elems'))} "
                       f"convex={len(bs.get_editor_property('agg_geom').get_editor_property('convex_elems'))} "
                       f"size_cm=({b.max.x - b.min.x:.0f},{b.max.y - b.min.y:.0f},{b.max.z - b.min.z:.0f})")
