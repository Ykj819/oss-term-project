
# Generates MM_Kneel_Down / MM_Kneel_Idle / MM_Kneel_Up (60fps): bonfire rest, right knee on the ground, left foot forward, left forearm on the knee.
import bpy, math
from mathutils import Vector
ns = {}; exec(bpy.data.texts['kneel_helpers.py'].as_string(), ns)
H = ns['ns']; P = ns['P']; arm = ns['arm']; W = ns['W']; sc = bpy.context.scene
arm.animation_data.action = None  # an attached action would override the base pose
base = H['get_base']()
H['reset_base'](base)
FROT_L = P['foot_l'].matrix.to_3x3().normalized(); FROT_R = P['foot_r'].matrix.to_3x3().normalized()
ANK_L0 = Vector((0.159, -0.138, 0.094)); ANK_L1 = Vector((0.16, -0.40, 0.094))
ANK_R0 = Vector((-0.158, 0.173, 0.11));  ANK_R1 = Vector((-0.15, 0.42, 0.175))
# (grip world, knuckle axis, back of hand)
HANG_L = (Vector((0.23, -0.03, 0.88)), Vector((0, -1, 0)), Vector((1, 0, 0)))
HANG_R = (Vector((-0.23, -0.03, 0.88)), Vector((0, -1, 0)), Vector((-1, 0, 0)))
KNEE_L = (Vector((0.10, -0.47, 0.50)), Vector((-1, 0, 0)), Vector((0, -1, 0.2)))
THIGH_R = (Vector((-0.21, -0.08, 0.45)), Vector((0, -1, 0)), Vector((-1, 0, 0)))
LEFT_POLE0 = Vector((0.25, 0.6, 1.2)); LEFT_POLE1 = Vector((0.6, 0.3, 0.8))

def smooth(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
def lerp(a, b, t): return a + (b - a) * t

def pose(t, breath=0.0):
    """t: 0 = standing, 1 = kneeling. breath: extra chest lean (deg) for the idle"""
    H['reset_base'](base)
    tp = smooth((t - 0.1) / 0.9)          # pelvis goes down
    ts = smooth(t / 0.55)                 # left foot steps forward
    ns['move_pelvis'](lerp(0, -0.45, tp), lerp(0, 0.06, tp))
    ankl = lerp(ANK_L0, ANK_L1, ts) + Vector((0, 0, 0.07 * math.sin(math.pi * ts)))
    ns['solve_leg']('l', ankl, FROT_L, (0.16, -1.5, 0.6), -180)
    tr = smooth((t - 0.15) / 0.85)
    ns['solve_leg']('r', lerp(ANK_R0, ANK_R1, tr), ns['foot_rot']('r', FROT_R, 70 * tr), (-0.15, -1.5, 0.3), -180)
    H['tilt_bone']('spine_01', 25 * smooth(t / 0.8) + breath)
    ta = smooth((t - 0.2) / 0.8)
    gl = [lerp(a, b, ta) for a, b in zip(HANG_L, KNEE_L)]
    gr = [lerp(a, b, ta) for a, b in zip(HANG_R, THIGH_R)]
    H['solve_arm']('l', gl[0], gl[1], gl[2], pole=0, pole_pos=lerp(LEFT_POLE0, LEFT_POLE1, ta))
    H['solve_arm']('r', gr[0], gr[1], gr[2])
    H['tilt_bone']('neck_01', 10 * ta + breath * 0.5)

def make(name, keys):
    # pose with no action attached (an attached action would overwrite the pose on every update), then key the stored poses
    arm.animation_data.action = None
    arm.location = (0, 0, 0)
    poses = []
    for f, t, br in keys:
        pose(t, br); poses.append((f, {pb.name: pb.matrix_basis.copy() for pb in P}))
    act = bpy.data.actions.get(name)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    arm.animation_data.action = act
    for f, mats in poses:
        for pb in P:
            pb.matrix_basis = mats[pb.name]
        ns['key_all'](f)
    arm.keyframe_insert('location', frame=keys[0][0]); arm.keyframe_insert('location', frame=keys[-1][0])
    return act

DOWN_LEN = 50
make('MM_Kneel_Down', [(1 + i * 5, (i * 5) / DOWN_LEN, 0) for i in range(DOWN_LEN // 5 + 1)])
make('MM_Kneel_Up',   [(1 + i * 5, 1 - (i * 5) / DOWN_LEN, 0) for i in range(DOWN_LEN // 5 + 1)])
make('MM_Kneel_Idle', [(1, 1, 0), (61, 1, 2.0), (121, 1, 0)])
