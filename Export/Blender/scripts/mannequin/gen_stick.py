
# Player stick slashes v2 (2026-11-15): heavier MM_Stick_Slash_A (overhead diagonal down, right-high -> left-low) and
# MM_Stick_Slash_B (rising backhand, left-low -> right-high, ends in A's wind-up so the combo flows A->B->A).
# Uses gen_club.py v4.x (analytic arm IK + whole-anim roll / grip / elbow optimisation). Stick contract = club contract
# (right grip 30cm from the bottom end, left hand 13cm below). 60 frames each; C++ plays them at the unarmed attack's
# duration / StickAttackSpeedMultiplier. Root motion = armature object location (forward = -Y), feet stay planted in world.
import bpy, math
from mathutils import Vector, Matrix, Quaternion
C = {}; exec(bpy.data.texts['gen_club.py'].as_string(), C)
V = Vector; arm = C['arm']; P = C['P']; sc = bpy.context.scene; club = C['club']; STANCE = C['STANCE']
smooth = C['smooth']

def build_stick_preview():
    import bmesh
    ob = bpy.data.objects.get('StickPrev')
    if ob: bpy.data.objects.remove(ob)
    me = bpy.data.meshes.new('StickPrev'); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=2.0, radius2=2.0, depth=65.0, matrix=Matrix.Translation((0, 0, 65.0 / 2 - 30.0)))
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('StickPrev', me); sc.collection.objects.link(ob)
    c = ob.constraints.new('CHILD_OF'); c.target = arm; c.subtarget = 'hand_r'; c.inverse_matrix = Matrix.Identity(4)
    K, N, grip = C['H']['hand_local']('r')
    Z = K.normalized(); X = (N - Z * N.dot(Z)).normalized(); Y = Z.cross(X)
    M = Matrix((X, Y, Z)).transposed().to_4x4(); M.translation = grip
    ob.matrix_basis = M
    return ob

def ramp(keys, f):
    """[(frame, value)] smoothstep"""
    if f <= keys[0][0]: return keys[0][1]
    for (f0, a), (f1, b) in zip(keys, keys[1:]):
        if f <= f1: return a + (b - a) * smooth((f - f0) / (f1 - f0))
    return keys[-1][1]

def make_stick(name, keys, root_keys, foot_keys):
    """keys: pose keys (root-local); root_keys: [(f, forward m)]; foot_keys: {'l'|'r': [(f, (x, y_world, lift))]} feet in WORLD y"""
    C['prepare'](keys)
    arm.animation_data.action = None; arm.location = (0, 0, 0)
    f0, f1 = keys[0][0], keys[-1][0]
    frames = list(range(f0, f1 + 1))
    def feet_local(q, f):
        root = ramp(root_keys, f)
        for s in 'lr':
            ks = foot_keys[s]
            x = ramp([(k, v[0]) for k, v in ks], f); y = ramp([(k, v[1]) for k, v in ks], f); lift = ramp([(k, v[2]) for k, v in ks], f)
            base = STANCE['a' + s]
            q['a' + s] = V((x, y + root, base.z + lift))          # world y -> root-local (root moves toward -Y)
        return q
    qs = [feet_local(C['blend_club'](keys, f), f) for f in frames]
    # same pipeline as gen_club make_club (v4.5), on these poses
    bd = C['base_dirs'](qs)
    R_STATES, L_STATES, LAMBDA = C['R_STATES'], C['L_STATES'], C['LAMBDA']
    rc = []
    for q, b in zip(qs, bd):
        C['apply_body'](q); row = []
        for off, sw in R_STATES:
            Q = q['cQ'] @ Quaternion((0, 0, 1), math.radians(off)); h = C['hands_of'](C['reach_fix'](q['cG'], Q), Q, 0.0)
            C['solve_arm3']('r', q, h['hr'], h['Kr'], h['Nr'], b['r'], sw)
            row.append(C['wrist_cost']('r') + 0.15 * abs(sw))
        rc.append(row)
    rpath = C['smooth_path'](C['viterbi'](rc, R_STATES, LAMBDA))
    lc = []
    for q, b, (off, _) in zip(qs, bd, rpath):
        C['apply_body'](q); row = []
        Q = q['cQ'] @ Quaternion((0, 0, 1), math.radians(off))
        for le, sw in L_STATES:
            h = C['hands_of'](C['reach_fix'](q['cG'], Q, le), Q, le)
            C['solve_arm3']('l', q, h['hl'], h['Kl'], h['Nl'], b['l'], sw)
            row.append(C['wrist_cost']('l') + 0.15 * abs(sw))
        lc.append(row)
    lpath = C['smooth_path'](C['viterbi'](lc, L_STATES, LAMBDA))
    poses = []
    for f, q, b, (off, swr), (le, swl) in zip(frames, qs, bd, rpath, lpath):
        C['apply_body'](q)
        Q = q['cQ'] @ Quaternion((0, 0, 1), math.radians(off))
        h = C['hands_of'](C['reach_fix'](q['cG'], Q, le), Q, le)
        C['solve_arm3']('r', q, h['hr'], h['Kr'], h['Nr'], b['r'], swr)
        C['solve_arm3']('l', q, h['hl'], h['Kl'], h['Nl'], b['l'], swl)
        C['spread_twist']('l'); C['spread_twist']('r')
        C['H']['tilt_bone']('neck_01', q['neck'])
        poses.append((f, {pb.name: pb.matrix_basis.copy() for pb in P}))
    act = bpy.data.actions.get(name)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    arm.animation_data.action = act
    for f, mats in poses:
        for pb in P: pb.matrix_basis = mats[pb.name]
        C['KN']['key_all'](f)
        arm.location = (0, -ramp(root_keys, f), 0); arm.keyframe_insert('location', frame=f)
    arm.location = (0, 0, 0)
    sc.frame_start = f0; sc.frame_end = f1
    print(name, 'quat flips fixed:', C['fix_quat_signs'](act))
    return act

EL0 = V((0.6, 0.5, 1.1)); ER0 = V((-0.6, 0.2, 0.8))
READY_S = club((-0.24, -0.24, 1.08), (-0.10, -0.75, 0.65), (1, 0, 0), el=EL0, er=ER0)

# ---------------- Slash A: overhead diagonal, right-high -> left-low (contact ~f27-f36), chain point f39 (0.65) ----------------
A_RAISE = club((-0.30, 0.02, 1.62), (-0.15, 0.55, 0.82), (1, 0, 0), spine=4.0, spine_twist=-30.0, neck=-14.0,
               pel=V((0, 0.06, -0.08)), el=V((0.5, -0.3, 1.3)), er=V((-0.7, 0.3, 1.4)))
A_COCK = club((-0.32, 0.08, 1.66), (-0.10, 0.75, 0.65), (1, 0, 0), spine=0.0, spine_twist=-38.0, neck=-14.0,
              pel=V((0, 0.08, -0.06)), el=V((0.5, -0.3, 1.3)), er=V((-0.7, 0.3, 1.4)))
A_DOWN = club((-0.18, -0.40, 1.40), (-0.25, -0.75, 0.60), (1, 0, 0), spine=22.0, spine_twist=-10.0, neck=-16.0,
              pel=V((0, 0.0, -0.16)), el=V((0.6, 0.0, 1.0)), er=V((-0.7, 0.2, 1.0)))
A_HIT = club((0.02, -0.50, 1.05), (0.35, -0.90, -0.10), (1, 0, 0), spine=30.0, spine_twist=10.0, neck=-18.0,
             pel=V((0, -0.04, -0.22)), el=V((0.6, 0.2, 0.9)), er=V((-0.5, 0.2, 0.9)))
A_THRU = club((0.22, -0.32, 0.80), (0.75, -0.20, -0.60), (1, 0, 0), spine=36.0, spine_twist=30.0, neck=-20.0,
              pel=V((0, -0.06, -0.28)), el=V((0.7, 0.3, 0.8)), er=V((-0.3, -0.3, 0.8)))
A_FOLLOW = club((0.26, -0.18, 0.74), (0.60, 0.35, -0.70), (1, 0, 0), spine=36.0, spine_twist=36.0, neck=-20.0,
                pel=V((0, -0.05, -0.28)), el=V((0.7, 0.4, 0.8)), er=V((-0.3, -0.4, 0.8)))
A_SETTLE = club((0.02, -0.36, 0.98), (0.30, -0.80, 0.25), (1, 0, 0), spine=24.0, spine_twist=8.0, neck=-14.0,
                pel=V((0, -0.02, -0.20)), el=EL0, er=ER0)
SLASH_A = [(1, READY_S), (14, A_RAISE), (22, A_COCK), (27, A_DOWN), (30, A_HIT), (34, A_THRU), (40, A_FOLLOW), (60, A_SETTLE)]
A_ROOT = [(1, 0.0), (23, 0.0), (34, 0.7), (60, 0.7)]
# feet world (x, y, lift): left steps in on the swing, right drags after
A_FEET = {'l': [(1, (0.20, -0.04, 0.0)), (23, (0.20, -0.04, 0.0)), (28, (0.21, -0.45, 0.09)), (32, (0.22, -0.89, 0.0)), (60, (0.22, -0.89, 0.0))],
          'r': [(1, (-0.20, 0.0, 0.0)), (30, (-0.20, 0.0, 0.0)), (35, (-0.20, -0.28, 0.04)), (40, (-0.20, -0.55, 0.0)), (60, (-0.20, -0.55, 0.0))]}

# ---------------- Slash B: rising backhand, left-low -> right-high (contact ~f24-f33), chain point f39 (0.65) = A's wind-up ----------------
B_GATHER = club((0.30, -0.05, 0.78), (0.45, 0.75, -0.45), (1, 0, 0), spine=30.0, spine_twist=40.0, neck=-18.0,
                pel=V((0, 0.0, -0.26)), el=V((0.7, 0.4, 0.8)), er=V((-0.3, -0.4, 0.8)))
B_PEAK = club((0.32, 0.02, 0.80), (0.30, 0.85, -0.40), (1, 0, 0), spine=30.0, spine_twist=44.0, neck=-18.0,
              pel=V((0, 0.02, -0.27)), el=V((0.7, 0.4, 0.8)), er=V((-0.3, -0.4, 0.8)))
B_RISE = club((0.10, -0.48, 0.95), (-0.30, -0.90, 0.30), (1, 0, 0), spine=20.0, spine_twist=10.0, neck=-16.0,
              pel=V((0, -0.03, -0.20)), el=V((0.6, 0.1, 0.9)), er=V((-0.6, 0.1, 0.9)))
B_HIT = club((-0.18, -0.42, 1.30), (-0.75, -0.35, 0.55), (1, 0, 0), spine=12.0, spine_twist=-15.0, neck=-14.0,
             pel=V((0, -0.02, -0.14)), el=V((0.6, -0.1, 1.1)), er=V((-0.7, 0.2, 1.1)))
B_THRU = club((-0.30, -0.12, 1.62), (-0.35, 0.35, 0.87), (1, 0, 0), spine=6.0, spine_twist=-30.0, neck=-14.0,
              pel=V((0, 0.03, -0.09)), el=V((0.5, -0.3, 1.3)), er=V((-0.7, 0.3, 1.4)))
B_FOLLOW = A_RAISE              # same key object = same club roll; A's wind-up: B -> A chains here (A starts at its f14)
B_SETTLE = READY_S
B_SIDE = club((0.28, -0.30, 0.82), (0.85, -0.30, -0.40), (1, 0, 0), spine=26.0, spine_twist=28.0, neck=-17.0,
              pel=V((0, -0.01, -0.24)), el=V((0.7, 0.3, 0.8)), er=V((-0.4, -0.2, 0.85)))
SLASH_B = [(1, A_FOLLOW), (12, B_GATHER), (20, B_PEAK), (23, B_SIDE), (26, B_RISE), (29, B_HIT), (33, B_THRU), (40, B_FOLLOW), (60, B_SETTLE)]
B_ROOT = [(1, 0.0), (21, 0.0), (32, 0.6), (60, 0.6)]
# starts in A's end stance (left forward); shuffles forward: left first, right drags
B_FEET = {'l': [(1, (0.22, -0.19, 0.0)), (21, (0.22, -0.19, 0.0)), (26, (0.22, -0.50, 0.08)), (30, (0.22, -0.79, 0.0)), (48, (0.22, -0.79, 0.0)), (58, (0.20, -0.64, 0.0)), (60, (0.20, -0.64, 0.0))],
          'r': [(1, (-0.20, 0.15, 0.0)), (28, (-0.20, 0.15, 0.0)), (33, (-0.20, -0.15, 0.04)), (38, (-0.20, -0.45, 0.0)), (48, (-0.20, -0.45, 0.0)), (58, (-0.20, -0.60, 0.0)), (60, (-0.20, -0.60, 0.0))]}


# ---------- v2.1: follow-through directions searched for least wrist strain; B = second stroke of an X
# (from A's low-left finish: lift over the left shoulder, cut left-high -> right-low) ----------
A_THRU['cK'] = V((0.50, -0.79, -0.36)).normalized()
A_FOLLOW['cK'] = V((0.93, -0.20, -0.31)).normalized()
B_LIFT = club((0.30, -0.10, 1.25), (0.35, 0.45, 0.82), (1, 0, 0), spine=14.0, spine_twist=30.0, neck=-14.0,
              pel=V((0, 0.0, -0.14)), el=V((0.7, 0.3, 1.0)), er=V((-0.2, -0.5, 1.0)))
B_WIND = club((0.34, 0.05, 1.45), (0.30, 0.75, 0.60), (1, 0, 0), spine=4.0, spine_twist=40.0, neck=-14.0,
              pel=V((0, 0.05, -0.08)), el=V((0.7, 0.4, 1.2)), er=V((-0.2, -0.5, 1.2)))
B_DOWN = club((0.18, -0.40, 1.38), (0.25, -0.75, 0.60), (1, 0, 0), spine=22.0, spine_twist=10.0, neck=-16.0,
              pel=V((0, 0.0, -0.16)), el=V((0.7, 0.2, 1.0)), er=V((-0.6, 0.0, 1.0)))
B_HIT = club((-0.02, -0.50, 1.05), (-0.35, -0.90, -0.10), (1, 0, 0), spine=30.0, spine_twist=-10.0, neck=-18.0,
             pel=V((0, -0.04, -0.22)), el=V((0.5, 0.2, 0.9)), er=V((-0.6, 0.2, 0.9)))
B_THRU = club((-0.22, -0.32, 0.80), (-0.56, -0.81, -0.17), (1, 0, 0), spine=36.0, spine_twist=-30.0, neck=-20.0,
              pel=V((0, -0.06, -0.28)), el=V((0.3, -0.3, 0.8)), er=V((-0.7, 0.3, 0.8)))
B_FOLLOW = club((-0.26, -0.15, 0.76), (-0.94, -0.13, -0.31), (1, 0, 0), spine=36.0, spine_twist=-36.0, neck=-20.0,
                pel=V((0, -0.05, -0.28)), el=V((0.3, -0.4, 0.8)), er=V((-0.7, 0.4, 0.8)))
SLASH_B = [(1, A_FOLLOW), (12, B_LIFT), (20, B_WIND), (25, B_DOWN), (28, B_HIT), (32, B_THRU), (40, B_FOLLOW), (60, READY_S)]
B_ROOT = [(1, 0.0), (22, 0.0), (32, 0.6), (60, 0.6)]


def build_slashes():
    return [make_stick('MM_Stick_Slash_A', SLASH_A, A_ROOT, A_FEET), make_stick('MM_Stick_Slash_B', SLASH_B, B_ROOT, B_FEET)]
