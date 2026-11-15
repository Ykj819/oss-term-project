
# Fishman boss anims (mannequin, played 2x scaled in UE). Uses kneel_helpers.py / pose_helpers.py.
import bpy, math
from mathutils import Vector, Matrix
ns = {}; exec(bpy.data.texts['kneel_helpers.py'].as_string(), ns)
H = ns['ns']; P = ns['P']; arm = ns['arm']; W = ns['W']; sc = bpy.context.scene
arm.animation_data.action = None
base = H['get_base']()
H['reset_base'](base)
FROT_L = P['foot_l'].matrix.to_3x3().normalized(); FROT_R = P['foot_r'].matrix.to_3x3().normalized()
V = Vector

def smooth(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
def lerp(a, b, t):
    if isinstance(a, tuple): return tuple(lerp(x, y, t) for x, y in zip(a, b))
    return a + (b - a) * t

# a pose = dict of parameters; missing keys fall back to STANCE
STANCE = dict(
    pel=V((0, 0.03, -0.12)), spine=16.0, spine_side=0.0, spine_twist=0.0, neck=-12.0,
    al=V((0.20, -0.04, 0.094)), ar=V((-0.20, 0.0, 0.094)), pl=0.0, pr=-6.0,
    kl=V((0.5, -1.5, 0.5)), kr=V((-0.5, -1.5, 0.5)),
    hl=V((0.30, -0.10, 0.86)), Kl=V((0, -1, 0)), Nl=V((1, 0, 0)), el=V((0.6, 0.5, 1.1)), pol_l=0.0,
    hr=V((-0.30, -0.10, 0.86)), Kr=V((0, -1, 0)), Nr=V((-1, 0, 0)), er=V((-0.6, 0.2, 0.8)), pol_r=-90.0,
)

def apply(p):
    q = dict(STANCE); q.update(p)
    arm.hide_viewport = False   # a hidden armature is not evaluated
    H['reset_base'](base)
    ns['move_pelvis'](q['pel'].z, q['pel'].y)
    if abs(q['pel'].x) > 1e-5:
        pb = P['pelvis']; M = pb.matrix.copy(); M.translation = M.translation + ns['Wi'].to_3x3() @ V((q['pel'].x, 0, 0)); pb.matrix = M; bpy.context.view_layer.update()
    ns['solve_leg']('l', q['al'], ns['foot_rot']('l', FROT_L, q['pl']), q['kl'], -180)
    ns['solve_leg']('r', q['ar'], ns['foot_rot']('r', FROT_R, q['pr']), q['kr'], -180)
    for s_, fr, pit in (('l', FROT_L, q['pl']), ('r', FROT_R, q['pr'])):
        pb = P['foot_'+s_]; M = pb.matrix.copy(); R = ns['foot_rot'](s_, fr, pit).to_4x4(); R.translation = M.translation
        pb.matrix = R; bpy.context.view_layer.update()
    H['tilt_bone']('spine_01', q['spine'] * 0.5); H['tilt_bone']('spine_03', q['spine'] * 0.5)
    if q['spine_side']: H['tilt_bone']('spine_02', q['spine_side'], 'Y')
    if q['spine_twist']: H['tilt_bone']('spine_02', q['spine_twist'], 'Z')
    H['solve_arm']('l', q['hl'], q['Kl'], q['Nl'], pole=q['pol_l'], pole_pos=q['el'])
    H['solve_arm']('r', q['hr'], q['Kr'], q['Nr'], pole=q['pol_r'], pole_pos=q['er'])
    H['tilt_bone']('neck_01', q['neck'])

def blend(keys, f):
    """keys: [(frame, pose dict)], smoothstep between neighbours"""
    full = [(k, dict(STANCE, **p)) for k, p in keys]
    if f <= full[0][0]: return full[0][1]
    for (f0, a), (f1, b) in zip(full, full[1:]):
        if f <= f1:
            t = smooth((f - f0) / (f1 - f0))
            return {n: lerp(a[n], b[n], t) for n in a}
    return full[-1][1]

def make(name, keys, step=2):
    arm.animation_data.action = None
    arm.location = (0, 0, 0)
    last = keys[-1][0]
    frames = list(range(keys[0][0], last + 1, step))
    if frames[-1] != last: frames.append(last)
    poses = []
    for f in frames:
        apply(blend(keys, f)); poses.append((f, {pb.name: pb.matrix_basis.copy() for pb in P}))
    act = bpy.data.actions.get(name)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    arm.animation_data.action = act
    for f, mats in poses:
        for pb in P: pb.matrix_basis = mats[pb.name]
        ns['key_all'](f)
    arm.keyframe_insert('location', frame=frames[0]); arm.keyframe_insert('location', frame=last)
    sc.frame_start = frames[0]; sc.frame_end = last
    return act
