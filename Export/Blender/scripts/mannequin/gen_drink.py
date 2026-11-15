
# Generates action MM_Drink_Potion (60fps, 96 frames): right hand from the hip to the mouth and back, left arm relaxed.
import bpy
from mathutils import Vector
ns = {}; exec(bpy.data.texts['pose_helpers.py'].as_string(), ns)
sc = bpy.context.scene; arm = ns['arm']; P = ns['P']
base = ns['get_base']()
act = bpy.data.actions.get('MM_Drink_Potion')
if act: bpy.data.actions.remove(act)
act = bpy.data.actions.new('MM_Drink_Potion'); act.use_fake_user = True
arm.animation_data.action = act
arm.location = (0,0,0)
# (grip point world m, knuckle axis, back-of-hand direction)
HIP   = ((-0.21, -0.06, 0.93), (0,0,1), (-1,0,0))
CHEST = ((-0.12, -0.26, 1.25), (0.2,0.2,1), (-0.6,-0.8,0))
MOUTH = ((-0.025, -0.165, 1.555), (0.25,0.45,0.85), (-0.8,-0.6,0))
LEFT  = ((0.23, -0.03, 0.88), (0,-1,0), (1,0,0))
LEFT_POLE = Vector((0.25, 0.6, 1.2))
# (frame, right hand pose, head tilt back in degrees)
KEYS = [(1, HIP, 0), (18, CHEST, 0), (30, MOUTH, -8), (60, MOUTH, -18), (70, MOUTH, -10), (84, CHEST, 0), (96, HIP, 0)]
for f, pose, tilt in KEYS:
    ns['reset_base'](base)
    er, elr = ns['solve_arm']('r', *pose)
    el, ell = ns['solve_arm']('l', *LEFT, pole=0, pole_pos=LEFT_POLE)
    if tilt: ns['tilt_bone']('head', tilt)
    for pb in P:
        pb.keyframe_insert('location', frame=f); pb.keyframe_insert('rotation_quaternion', frame=f); pb.keyframe_insert('scale', frame=f)
    print(f, 'err %.3f %.3f' % (er, el), 'elbow r', tuple(round(v,2) for v in elr), 'l', tuple(round(v,2) for v in ell))
arm.keyframe_insert('location', frame=1); arm.keyframe_insert('location', frame=96)
sc.frame_start, sc.frame_end = 1, 96
