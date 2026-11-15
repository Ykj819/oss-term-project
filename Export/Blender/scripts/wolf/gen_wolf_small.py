
# Small-wolf animations (AEnemyWolf): Wolf_Run (in-place gallop loop) and Wolf_Jump_Bite (in place: the leap itself is done in code).
# Built for the full-size rig (UE scales the mesh to 0.35). 60fps, faces -Y, left = +X. Meters.
import bpy, math
from mathutils import Vector
A = {}; exec(bpy.data.texts['gen_wolf_attacks.py'].as_string(), A)
G = A['G']; H = A['H']; C0 = A['C0']; UNIT = A['UNIT']; smooth = A['smooth']
lerp_val = A['lerp_val']; L = A['L']; root_matrix = A['root_matrix']


def build_manual(name, f0, f1, root_fn, feet_fn, body_fn):
    """Same as gen_wolf_anims.build, but bakes by reading each bone's visual pose per frame
    (bpy.ops.nla.bake lost the IK knee / elbow bend in Blender 5.2)."""
    arm = H['arm']; P = H['P']; sc = bpy.context.scene; LEGS = H['LEGS']; WS = H['WS']
    H['setup_ik']()
    arm.animation_data_create()
    old = bpy.data.actions.get(name)
    if old: bpy.data.actions.remove(old)
    tmp = bpy.data.actions.new(name + '_src')
    arm.animation_data.action = tmp
    for pb in P: pb.rotation_mode = 'QUATERNION'
    for f in range(f0, f1 + 1):
        loc, yaw = root_fn(f); W = root_matrix(loc, yaw)
        arm.location = loc * WS; arm.rotation_euler = (0, 0, math.radians(yaw))
        arm.keyframe_insert('location', frame=f); arm.keyframe_insert('rotation_euler', frame=f)
        G['fk'](body_fn(f))
        for bn in G['FK_BONES']:
            P[bn].keyframe_insert('location', frame=f); P[bn].keyframe_insert('rotation_quaternion', frame=f)
        for leg in LEGS:
            c, lift = feet_fn(leg, f, W)
            H['place_leg'](leg, c, W, lift)
            for sfx in ('_upper', '_contact'):
                bpy.data.objects['IK_' + leg + sfx].keyframe_insert('location', frame=f)
    # read the evaluated (constrained) pose of every bone
    frames = {}
    for f in range(f0, f1 + 1):
        sc.frame_set(f)
        frames[f] = ({pb.name: arm.convert_space(pose_bone=pb, matrix=pb.matrix, from_space='POSE', to_space='LOCAL') for pb in P},
                     arm.location.copy(), arm.rotation_euler.copy())
    H['remove_ik']()
    for o in [o for o in bpy.data.objects if o.name.startswith('IK_')]:
        if o.animation_data: o.animation_data_clear()
    act = bpy.data.actions.new(name); act.use_fake_user = True
    arm.animation_data.action = act
    for f, (mats, aloc, arot) in frames.items():
        arm.location = aloc; arm.rotation_euler = arot
        arm.keyframe_insert('location', frame=f); arm.keyframe_insert('rotation_euler', frame=f)
        for pb in P:
            l, r, _ = mats[pb.name].decompose()
            pb.location = l; pb.rotation_quaternion = r
            pb.keyframe_insert('location', frame=f); pb.keyframe_insert('rotation_quaternion', frame=f)
    bpy.data.actions.remove(tmp)
    for a in list(bpy.data.actions):
        if a.name.startswith('IK_') and a.users == 0: bpy.data.actions.remove(a)
    sc.frame_start, sc.frame_end = f0, f1
    return act

# ---------- run: transverse gallop, in place ----------
# full-scale speed RUN_STRIDE / (RUN_N/60) = 6.0 / 0.7 = 8.57 m/s  (UE: RunAnimSpeedAtFullScale = 857)
RUN_N = 42; RUN_STRIDE = 6.0
RUN_ST = 0.32                                   # stance fraction
RUN_PH = {'HL': 0.0, 'HR': 0.09, 'FL': 0.42, 'FR': 0.52}
RUN_REACH = {'HL': (-0.25, 0.0), 'HR': (-0.25, 0.0), 'FL': (-0.45, 0.0), 'FR': (-0.45, 0.0)}   # stance center shift (y), front reach forward
RUN_LIFT = {'F': 0.75, 'H': 0.65}
def run():
    travel = RUN_STRIDE * RUN_ST                # foot slides this far back during stance
    a = travel / 2
    def root_fn(f): return Vector(), 0.0
    def feet_fn(lg, f, W):
        p = ((f - 1) / RUN_N + RUN_PH[lg]) % 1.0
        cy = RUN_REACH[lg][0]
        if p < RUN_ST:
            y = cy - a + 2 * a * (p / RUN_ST); lift = 0.0
        else:
            u = (p - RUN_ST) / (1 - RUN_ST)
            y = cy + a - 2 * a * smooth(u)
            lift = RUN_LIFT[lg[0]] * math.sin(math.pi * u) ** 0.8
        return W @ (C0[lg] + Vector((0, y, 0)) * UNIT), lift
    def body_fn(f):
        t = (f - 1) / RUN_N
        w = 2 * math.pi
        # spine: gathered (flexed) while the hind legs reach under, extended while the front legs reach
        flex = math.cos(w * (t - 0.30))
        bob = 0.10 * math.cos(w * (t - 0.72))      # highest in the suspension after the front feet push off
        return {'pelvis': {'loc': Vector((0, 0, -0.12 + bob)), 'pitch': 3 * flex},
                'spine_01': {'pitch': -5 * flex}, 'spine_02': {'pitch': -5 * flex}, 'spine_03': {'pitch': 4 * flex},
                'neck_01': {'pitch': 24 + 4 * math.cos(w * (t - 0.5))}, 'neck_02': {'pitch': 6},
                'head': {'pitch': -14 - 3 * math.cos(w * (t - 0.5))},
                'jaw': {'pitch': 8}, 'ear_l': {'pitch': -30}, 'ear_r': {'pitch': -30},
                'tail_01': {'pitch': 14 + 5 * flex}, 'tail_02': {'pitch': 4}, 'tail_03': {'pitch': -4 * flex},
                'tail_05': {'yaw': 6 * math.sin(w * t)}}
    return build_manual('Wolf_Run', 1, RUN_N + 1, root_fn, feet_fn, body_fn)


# ---------- jump bite (in place; UE moves the body). Timing = AEnemyWolf: wind-up 0.5s, air 0.5s, land recover 0.8s ----------
# f1 wind-up start, f31 take-off, f57 jaws snap, f61 landing, f109 end (1.8s). Snap fraction = 56/108 = 0.52
JB_END = 109
def keys3(keys, f):
    """keys: [(frame, dy, lift)] smooth piecewise -> (dy, lift)"""
    if f <= keys[0][0]: return keys[0][1], keys[0][2]
    for (f0, a0, b0), (f1, a1, b1) in zip(keys, keys[1:]):
        if f0 <= f <= f1:
            u = smooth((f - f0) / (f1 - f0)); return a0 + (a1 - a0) * u, b0 + (b1 - b0) * u
    return keys[-1][1], keys[-1][2]
JB_FRONT = [(1, 0, 0), (24, 0, 0), (29, 0.05, 0.08), (37, -0.9, 0.75), (50, -1.3, 0.6), (57, -0.8, 0.12), (60, -0.75, 0),
            (82, -0.75, 0), (90, -0.35, 0.3), (97, 0, 0)]
JB_HIND = [(1, 0, 0), (30, 0, 0), (34, 0.35, 0.08), (41, 1.0, 0.5), (51, 0.45, 0.75), (59, 0.05, 0.35), (64, 0.1, 0),
           (88, 0.1, 0), (94, 0.05, 0.2), (100, 0, 0)]
def jump_bite():
    def root_fn(f): return Vector(), 0.0
    def feet_fn(lg, f, W):
        d = 2 if lg.endswith('R') else 0              # right side a touch later
        dy, lift = keys3(JB_FRONT if lg[0] == 'F' else JB_HIND, f - d)
        side = 0.0
        return W @ (C0[lg] + Vector((side, dy, 0)) * UNIT), lift
    def body_fn(f):
        crouch = lerp_val([(1, 0), (26, 1), (32, -0.35), (42, -0.1), (56, 0), (64, 0.85), (80, 0.35), (105, 0)], f)
        back = lerp_val([(1, 0), (26, 0.25), (33, -0.15), (45, 0), (60, 0), (64, 0.15), (95, 0)], f)
        ext = lerp_val([(1, 0), (26, -0.4), (37, 1), (52, 0.5), (60, 0), (64, -0.5), (92, 0)], f)
        neck = lerp_val([(1, 0), (26, 14), (36, -6), (50, -10), (57, 8), (64, 22), (84, 10), (106, 0)], f)
        head = lerp_val([(1, 0), (26, -12), (36, -4), (52, -6), (58, 4), (64, -6), (106, 0)], f)
        jaw = lerp_val([(1, 0), (18, 10), (30, 14), (39, 42), (52, 44), (55, 30), (57, 0), (64, 3), (82, 5), (102, 0)], f)
        ears = lerp_val([(1, 0), (18, -42), (60, -45), (90, -12), (106, 0)], f)
        shake_env = lerp_val([(60, 0), (64, 1), (80, 1), (88, 0)], f) if 60 <= f <= 88 else 0.0
        shake = shake_env * math.sin((f - 60) / 60 * 2 * math.pi * 5)       # tearing at the grip: 5 shakes/s
        return {'pelvis': {'loc': Vector((0, 0.25 * back, -0.3 * crouch))},
                'spine_01': {'pitch': -6 * ext}, 'spine_02': {'pitch': -5 * ext}, 'spine_03': {'pitch': 5 * ext},
                'neck_01': {'pitch': neck, 'yaw': 8 * shake}, 'neck_02': {'pitch': 0.3 * neck},
                'head': {'pitch': head, 'yaw': 10 * shake},
                'jaw': {'pitch': jaw}, 'ear_l': {'pitch': ears}, 'ear_r': {'pitch': ears},
                'tail_01': {'pitch': lerp_val([(1, 0), (26, -8), (40, 18), (60, 10), (85, 0)], f), 'yaw': -6 * shake},
                'tail_03': {'pitch': lerp_val([(1, 0), (40, -8), (70, 0)], f)}}
    return build_manual('Wolf_Jump_Bite', 1, JB_END, root_fn, feet_fn, body_fn)
