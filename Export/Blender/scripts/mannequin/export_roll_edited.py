# Exports the user's hand-edited roll from Export/Blender/Roll.blend to Export/MM_Roll_Fwd.fbx (no regeneration).
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b Export/Blender/Roll.blend
#       --python Export/Blender/scripts/mannequin/export_roll_edited.py
# Previous FBX kept as Export/MM_Roll_Fwd_v2_backup.fbx (once). Then prints the CLAUDE.md checks (file is not saved).
import bpy, os, shutil

ROOT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject"
FBX = os.path.join(ROOT, r"Export\MM_Roll_Fwd.fbx")
sc = bpy.context.scene
arm = bpy.data.objects['root']
act = arm.animation_data.action
f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
print('EXP action', act.name, 'range', f0, f1, 'scene range', sc.frame_start, sc.frame_end, 'fps', sc.render.fps,
      'actions', [a.name for a in bpy.data.actions])

bak = FBX.replace('.fbx', '_v2_backup.fbx')
if os.path.exists(FBX) and not os.path.exists(bak):
    shutil.copy2(FBX, bak)
# export the scene range (1-54): stray keys outside it (e.g. a key at frame 0) would add frames to the anim
print('EXP exporting frames', sc.frame_start, sc.frame_end)
for o in bpy.context.view_layer.objects: o.select_set(False)
arm.hide_viewport = False; arm.hide_set(False); arm.select_set(True); bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.fbx(filepath=FBX, use_selection=True, object_types={'ARMATURE'}, apply_scale_options='FBX_SCALE_UNITS',
                         add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                         bake_anim_use_all_bones=True, bake_anim_force_startend_keying=True, bake_anim_step=1.0,
                         bake_anim_simplify_factor=0.0, use_armature_deform_only=False)
print('EXP fbx', os.path.getsize(FBX), 'backup', bak)

# checks (after export; executing gen_club may clear the armature action, the file is not saved)
try:
    R = {}; exec(bpy.data.texts['gen_roll.py'].as_string(), R)
    arm.animation_data.action = act
    try: arm.animation_data.action_slot = act.slots[0]
    except Exception: pass
    print('EXP check:'); R['C']['check']((act.name,))
    arm.animation_data.action = act
    try: arm.animation_data.action_slot = act.slots[0]
    except Exception: pass
    print('EXP leg twist max', R['leg_twist_max']())
    print('EXP ground (f, hand z, ball z, body clearance)', R['ground_contacts']())
except Exception as e:
    import traceback; traceback.print_exc(); print('EXP check failed', e)
