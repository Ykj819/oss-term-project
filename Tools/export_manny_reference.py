# Export SKM_Manny_Simple (mesh + skeleton in its reference pose) to Export/Reference/SKM_Manny_Simple.fbx so new
# characters can be modelled and skinned in Blender on the exact UE mannequin reference pose.
import os
import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
out_dir = os.path.join(PROJ, "Export", "Reference")
os.makedirs(out_dir, exist_ok=True)
mesh = unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple")
task = unreal.AssetExportTask()
task.set_editor_property("object", mesh)
task.set_editor_property("filename", os.path.join(out_dir, "SKM_Manny_Simple.fbx"))
task.set_editor_property("automated", True)
task.set_editor_property("prompt", False)
task.set_editor_property("replace_identical", True)
opts = unreal.FbxExportOption()
opts.set_editor_property("collision", False)
opts.set_editor_property("level_of_detail", False)
# material baking (MeshMergeUtilities) crashes in the commandlet -> off
for prop, val in (("bake_material_inputs", unreal.FbxMaterialBakeMode.DISABLED),
                  ("export_morph_targets", False), ("export_preview_mesh", False)):
    try:
        opts.set_editor_property(prop, val)
    except Exception as e:
        unreal.log_warning(f"MANNYEXP (warn) {prop}: {e}")
task.set_editor_property("options", opts)
ok = unreal.Exporter.run_asset_export_task(task)
skel = mesh.get_editor_property("skeleton")
unreal.log_warning(f"MANNYEXP ok={ok} skeleton={skel.get_path_name() if skel else None} "
                   f"file={os.path.exists(os.path.join(out_dir, 'SKM_Manny_Simple.fbx'))}")
# the -run=pythonscript commandlet crashes in this export; run headless with -ExecutePythonScript and quit here
if "executepythonscript" in unreal.SystemLibrary.get_command_line().lower():
    unreal.SystemLibrary.quit_editor()
