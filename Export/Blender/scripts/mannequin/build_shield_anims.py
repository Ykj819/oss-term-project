# Shield enemy upper-body poses (2026-11-23), made with the gen_club v4.7 / gen_fishman_v2 arm pipeline
# (analytic two-bone IK solve_arm3, continuous elbow directions, Viterbi elbow swing, wrist bend limit, leg IK):
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b Export/Blender/Club.blend
#       --python Export/Blender/scripts/mannequin/build_shield_anims.py
#   MM_Shield_Hold  (80 f loop)  both hands on the shield's vertical back grips, chest height
#   MM_Shield_Brace (30 f)       shield pulled in to the chest (rush wind-up)
#   MM_Shield_Push  (20 f)       shield shoved forward, chest leaning in (rush)
# Played on the ABP's UpperBody slot by AEnemyShield; the shield mesh sits on the actor at the grip positions printed
# here (SHIELD lines -> AEnemyShield::ShieldForward / ShieldHeight). Saves Export/Blender/ShieldAnims.blend.
import bpy, os, math
from mathutils import Vector

ROOT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject"
SRC = os.path.join(ROOT, r"Export\Blender\scripts\mannequin\gen_fishman_v2.py")
txt = bpy.data.texts.get('gen_fishman_v2.py') or bpy.data.texts.new('gen_fishman_v2.py')
txt.clear(); txt.write(open(SRC, encoding='utf-8').read())
R = {}; exec(txt.as_string(), R)
C = R['C']; P = R['P']; arm = R['arm']; sc = bpy.context.scene; W = arm.matrix_world
V = Vector

GRIP_X, GRIP_LOCAL_X, GRIP_LOCAL_Z = 0.17, -0.036, -0.06     # grips in SM_EnemyShield space (m): +-y, x, z
CAPSULE_HALF = 0.96                                          # mannequin mesh sits 96 cm below the capsule centre


def grip(y, z, spine, neck):
    # vertical grips: knuckle line up, back of the hand outward (hammer grip), elbows out and down
    return dict(hl=V((GRIP_X, y, z)), hr=V((-GRIP_X, y, z)), Kl=V((0, 0, 1)), Kr=V((0, 0, 1)),
                Nl=V((1, 0.15, 0)), Nr=V((-1, 0.15, 0)), el=V((0.65, 0.15, 0.85)), er=V((-0.65, 0.15, 0.85)),
                spine=spine, neck=neck)


HOLD = grip(-0.34, 1.10, 6.0, -6.0)
HOLD_B = dict(HOLD, hl=HOLD['hl'] + V((0, 0, -0.012)), hr=HOLD['hr'] + V((0, 0, -0.012)), spine=7.0)
BRACE = grip(-0.27, 1.14, -2.0, 0.0)
PUSH = grip(-0.43, 1.06, 16.0, -14.0)
ANIMS = [('MM_Shield_Hold', [(1, HOLD), (40, HOLD_B), (80, HOLD)]),
         ('MM_Shield_Brace', [(1, BRACE), (30, BRACE)]),
         ('MM_Shield_Push', [(1, PUSH), (20, PUSH)])]

for name, keys in ANIMS:
    R['make'](name, keys)
names = tuple(n for n, _ in ANIMS)
print('SHIELD check:'); C['check'](names); R['check_more'](names)

# where the grips really ended up (reach limit / wrist limit move them a little) -> shield placement on the actor
for name in names:
    R['set_action'](name); sc.frame_set(1); bpy.context.view_layer.update()
    g = []
    for s in 'lr':
        K, N, gl = C['H']['hand_local'](s)
        g.append(W @ (P['hand_' + s].matrix @ gl))
    mid = (g[0] + g[1]) * 0.5
    fwd_cm = (-mid.y - GRIP_LOCAL_X) * 100; up_cm = (mid.z - GRIP_LOCAL_Z - CAPSULE_HALF) * 100
    print(f'SHIELD {name} grips l={tuple(round(c, 3) for c in g[0])} r={tuple(round(c, 3) for c in g[1])} '
          f'gap={round((g[0] - g[1]).length, 3)} -> shield X={round(fwd_cm, 1)} Z={round(up_cm, 1)} cm')

for name in names:
    act = R['set_action'](name)
    sc.frame_start, sc.frame_end = map(int, act.frame_range); sc.render.fps = 60
    for o in bpy.context.view_layer.objects: o.select_set(False)
    arm.hide_viewport = False; arm.hide_set(False); arm.select_set(True); bpy.context.view_layer.objects.active = arm
    fbx = os.path.join(ROOT, 'Export', name + '.fbx')
    bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={'ARMATURE'}, apply_scale_options='FBX_SCALE_UNITS',
                             add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                             bake_anim_use_all_bones=True, bake_anim_force_startend_keying=True, bake_anim_step=1.0,
                             bake_anim_simplify_factor=0.0, use_armature_deform_only=False)
    print('SHIELD fbx', fbx, os.path.getsize(fbx))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, r"Export\Blender\ShieldAnims.blend"))
