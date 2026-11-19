# Male (Manny) forward walk / run for the player: the project only has the female template locomotion (MF_Unarmed_*).
# Epic's Manny MM_Walk_Fwd / MM_Run_Fwd ship in the engine plugin MoverExamples (not enabled in the project).
# This script (run once, headless, plugin enabled only for this run):
#   1. exports those two anims from the plugin to Export/Anims/Manny/*.fbx
#   2. backs up Content/.../Walk/MF_Unarmed_Walk_Fwd.uasset and Jog/MF_Unarmed_Jog_Fwd.uasset to Saved/Backup_FemaleLocomotion
#   3. imports the Manny FBX OVER those two assets (same names -> BS_Idle_Walk_Run / ABP_Unarmed pick them up unchanged)
#      on /Game/Characters/Mannequins/Meshes/SK_Mannequin
#   4. root-locks them (in place, like the template anims) and sets RateScale so the stride matches the blend-space speed
# Restore the female anims: copy the backups back (editor closed).
# Run:  UnrealEditor-Cmd.exe <uproject> -ExecutePythonScript="<this file>" -EnablePlugins=Mover,ChaosMover,CableComponent,MoverExamples
#       -unattended -RenderOffscreen -nosplash -stdout          (FBX export of skeletal data asserts under -nullrhi)
import os, shutil
import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
log = lambda m: unreal.log_warning("MANNY " + str(m))
SKEL = unreal.load_asset("/Game/Characters/Mannequins/Meshes/SK_Mannequin")
BS = "/Game/Characters/Mannequins/Anims/Unarmed/BS_Idle_Walk_Run"
JOBS = [("/MoverExamples/Characters/Mannequins/Animations/Manny/MM_Walk_Fwd", "/Game/Characters/Mannequins/Anims/Unarmed/Walk",
         "MF_Unarmed_Walk_Fwd", r"Content\Characters\Mannequins\Anims\Unarmed\Walk\MF_Unarmed_Walk_Fwd.uasset"),
        ("/MoverExamples/Characters/Mannequins/Animations/Manny/MM_Run_Fwd", "/Game/Characters/Mannequins/Anims/Unarmed/Jog",
         "MF_Unarmed_Jog_Fwd", r"Content\Characters\Mannequins\Anims\Unarmed\Jog\MF_Unarmed_Jog_Fwd.uasset")]
FBX_DIR = os.path.join(PROJ, "Export", "Anims", "Manny")
BAK_DIR = os.path.join(PROJ, "Saved", "Backup_FemaleLocomotion")
os.makedirs(FBX_DIR, exist_ok=True); os.makedirs(BAK_DIR, exist_ok=True)
AL = unreal.AnimationLibrary


def root_speed(anim):
    n = AL.get_num_frames(anim); length = anim.get_play_length()
    a = AL.get_bone_pose_for_frame(anim, "root", 0, False).translation
    b = AL.get_bone_pose_for_frame(anim, "root", n - 1, False).translation
    d = ((b.x - a.x) ** 2 + (b.y - a.y) ** 2) ** 0.5
    return d / length if length > 0 else 0.0, length


def bs_speeds():
    out = {}
    bs = unreal.load_asset(BS)
    try:
        for s in bs.get_editor_property("sample_data"):
            an = s.get_editor_property("animation")
            out[an.get_name()] = s.get_editor_property("sample_value")
    except Exception as e:
        log(f"cannot read blend space samples: {e}")
    return out


speeds = bs_speeds()
log(f"blend space samples: {[(k, (round(v.x), round(v.y))) for k, v in speeds.items() if 'Fwd' in k and 'Left' not in k and 'Right' not in k]}")
tools = unreal.AssetToolsHelpers.get_asset_tools()
for src_path, dest_dir, dest_name, rel in JOBS:
    src = unreal.load_asset(src_path)
    if not src:
        log(f"FAILED load {src_path} (plugin not mounted?)"); continue
    src_speed, src_len = root_speed(src)
    fbx = os.path.join(FBX_DIR, src.get_name() + ".fbx")
    t = unreal.AssetExportTask()
    t.set_editor_property("object", src); t.set_editor_property("filename", fbx)
    t.set_editor_property("automated", True); t.set_editor_property("prompt", False); t.set_editor_property("replace_identical", True)
    t.set_editor_property("options", unreal.FbxExportOption())
    ok = unreal.Exporter.run_asset_export_task(t)
    log(f"export {src.get_name()} ok={ok} size={os.path.getsize(fbx) if os.path.exists(fbx) else 0} root speed {src_speed:.0f} cm/s len {src_len:.2f}s")
    if not ok or not os.path.exists(fbx):
        continue
    bak = os.path.join(BAK_DIR, os.path.basename(rel))
    if not os.path.exists(bak):
        shutil.copy2(os.path.join(PROJ, rel), bak)
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", False); ui.set_editor_property("import_animations", True)
    ui.set_editor_property("import_as_skeletal", True); ui.set_editor_property("skeleton", SKEL)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
    ui.set_editor_property("import_materials", False); ui.set_editor_property("import_textures", False)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", fbx); task.set_editor_property("destination_path", dest_dir)
    task.set_editor_property("destination_name", dest_name)
    task.set_editor_property("automated", True); task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False); task.set_editor_property("options", ui)
    tools.import_asset_tasks([task])
    anim = unreal.load_asset(f"{dest_dir}/{dest_name}")
    if not anim:
        log(f"FAILED import {dest_name}"); continue
    new_speed, new_len = root_speed(anim)
    anim.set_editor_property("enable_root_motion", False)
    anim.set_editor_property("force_root_lock", True)
    target = speeds.get(dest_name)
    rate = 1.0
    if target is not None and new_speed > 1:
        tgt = max(abs(target.x), abs(target.y))
        rate = max(0.6, min(1.6, tgt / new_speed))
        anim.set_editor_property("rate_scale", rate)
    unreal.EditorAssetLibrary.save_asset(f"{dest_dir}/{dest_name}", only_if_is_dirty=False)
    log(f"{dest_name} <- {src.get_name()}: skeleton={anim.get_editor_property('skeleton').get_name()} len {new_len:.2f}s "
        f"root speed {new_speed:.0f} cm/s, blend-space speed {target}, rate_scale {rate:.2f} (backup {bak})")

if "executepythonscript" in unreal.SystemLibrary.get_command_line().lower():
    unreal.SystemLibrary.quit_editor()
