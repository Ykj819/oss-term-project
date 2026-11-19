# Reimport the player's roll (Export/MM_Roll_Fwd.fbx, built by Export/Blender/scripts/mannequin/build_roll.py) over
# /Game/Characters/Mannequins/Anims/Unarmed/Roll/MM_Roll_Fwd on SK_Mannequin. The old .uasset is copied to
# Saved/Backup_Roll_v1 once. Prints length and pelvis height samples (scale check: standing pelvis ~70-90 cm).
# Headless: UnrealEditor-Cmd.exe <uproject> -ExecutePythonScript="<this file>" -unattended -nullrhi -nosplash -stdout
import os, shutil
import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
log = lambda m: unreal.log_warning("ROLLIMP " + str(m))
DEST_DIR = "/Game/Characters/Mannequins/Anims/Unarmed/Roll"; NAME = "MM_Roll_Fwd"
REL = os.path.join("Content", "Characters", "Mannequins", "Anims", "Unarmed", "Roll", NAME + ".uasset")
bak_dir = os.path.join(PROJ, "Saved", "Backup_Roll_v1"); os.makedirs(bak_dir, exist_ok=True)
bak = os.path.join(bak_dir, NAME + ".uasset")
if os.path.exists(os.path.join(PROJ, REL)) and not os.path.exists(bak):
    shutil.copy2(os.path.join(PROJ, REL), bak)

ui = unreal.FbxImportUI()
ui.set_editor_property("import_mesh", False); ui.set_editor_property("import_animations", True)
ui.set_editor_property("import_as_skeletal", True)
ui.set_editor_property("skeleton", unreal.load_asset("/Game/Characters/Mannequins/Meshes/SK_Mannequin"))
ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
ui.set_editor_property("import_materials", False); ui.set_editor_property("import_textures", False)
task = unreal.AssetImportTask()
task.set_editor_property("filename", os.path.join(PROJ, "Export", NAME + ".fbx"))
task.set_editor_property("destination_path", DEST_DIR); task.set_editor_property("destination_name", NAME)
task.set_editor_property("automated", True); task.set_editor_property("replace_existing", True)
task.set_editor_property("save", False); task.set_editor_property("options", ui)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
anim = unreal.load_asset(f"{DEST_DIR}/{NAME}")
if not anim:
    log("FAILED import")
else:
    anim.set_editor_property("enable_root_motion", False)
    AL = unreal.AnimationLibrary
    n = AL.get_num_frames(anim)
    samples = []
    for fr in (0, n // 3, n // 2, (2 * n) // 3, n - 1):
        t = AL.get_bone_pose_for_frame(anim, "pelvis", fr, False).translation
        r = AL.get_bone_pose_for_frame(anim, "root", fr, False).translation
        samples.append((fr, round(t.z, 1), round(r.y, 1)))
    unreal.EditorAssetLibrary.save_asset(f"{DEST_DIR}/{NAME}", only_if_is_dirty=False)
    log(f"OK skeleton={anim.get_editor_property('skeleton').get_name()} frames={n} length={anim.get_play_length():.3f}s "
        f"(frame, pelvis local z cm, root y cm)={samples} backup={bak}")

if "executepythonscript" in unreal.SystemLibrary.get_command_line().lower():
    unreal.SystemLibrary.quit_editor()
