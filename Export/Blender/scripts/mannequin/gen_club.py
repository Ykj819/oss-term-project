
# Club giant anims (AEnemyClub: mannequin played 1.5x in UE). Two-handed big club, built with fishman_helpers pose dicts.
# World meters, faces -Y, right = -X. Club contract (same as the player's stick, see C++ AEnemyClub):
#   axis = knuckle line pinky->index of hand_r, right-hand grip = lerp(hand_r, middle_01_r, 0.6),
#   bottom end CLUB_GRIP below the right grip, left hand grip CLUB_HANDS_GAP below the right grip.
import bpy, bmesh, math
from mathutils import Vector, Matrix
g = {}; exec(bpy.data.texts['fishman_helpers.py'].as_string(), g)
V = g['V']; P = g['P']; arm = g['arm']; H = g['H']; sc = bpy.context.scene
CLUB_LEN = 160.0; CLUB_GRIP = 30.0; CLUB_HANDS_GAP = 0.13   # cm, cm, m

def build_club():
    """preview mesh in hand_r space (cm), origin = right grip, +Z = club axis"""
    ob = bpy.data.objects.get('Club')
    if ob: bpy.data.objects.remove(ob)
    me = bpy.data.meshes.new('Club'); bm = bmesh.new()
    def cyl(z0, z1, r0, r1):
        bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=r0, radius2=r1, depth=z1 - z0, matrix=Matrix.Translation((0, 0, (z0 + z1) / 2)))
    cyl(-CLUB_GRIP, 25, 3.0, 3.2)                       # handle
    cyl(20, CLUB_LEN - CLUB_GRIP - 7, 4.5, 8.0)         # swelling head
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=8.0, matrix=Matrix.Translation((0, 0, CLUB_LEN - CLUB_GRIP - 7)))
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('Club', me); sc.collection.objects.link(ob)
    c = ob.constraints.new('CHILD_OF'); c.target = arm; c.subtarget = 'hand_r'
    c.inverse_matrix = Matrix.Identity(4)
    K, N, grip = H['hand_local']('r')
    Z = K.normalized(); X = (N - Z * N.dot(Z)).normalized(); Y = Z.cross(X)
    M = Matrix((X, Y, Z)).transposed().to_4x4(); M.translation = grip
    ob.matrix_basis = M
    return ob

def club(G, K, S, **body):
    """two-hand grip: right grip at G (world m), club axis K (toward the tip), S = side the palms face away from
    (right palm faces +S... i.e. backs: right hand back -> -S, left hand back -> +S)"""
    G = V(G); K = V(K).normalized(); S = V(S); S = (S - K * S.dot(K)).normalized()
    d = dict(hr=G, Kr=K, Nr=-S, hl=G - K * CLUB_HANDS_GAP, Kl=K, Nl=S)
    d.update(body)
    return d


def hz_side(K):
    """hand-back side for horizontal swings: Z x K (stays continuous while the club goes round)"""
    K = V(K).normalized(); s = V((0, 0, 1)).cross(K)
    return s if s.length > 1e-3 else V((1, 0, 0))

EL = V((0.6, 0.2, 1.0)); ER = V((-0.6, 0.2, 0.9))
READY = club((0.0, -0.36, 1.0), (-0.45, -0.2, 0.87), (0.2, -0.45, 0), spine=14.0, el=EL, er=ER)

# ---------- overhead slam: long wind-up, smash into the ground ~1.7m ahead, stuck there (punish window) ----------
# impact f70 (hit window ~f62-f74 of 150)
SLAM_RAISE = club((-0.04, 0.02, 1.88), (0.0, 0.55, 0.45), (1, 0, 0), spine=-6.0, neck=-18.0, pel=V((0, 0.05, -0.08)),
                  el=V((0.7, -0.2, 1.9)), er=V((-0.7, -0.2, 1.9)))
SLAM_COCK = club((-0.03, 0.10, 1.90), (0.0, 0.80, 0.15), (1, 0, 0), spine=-12.0, neck=-20.0, pel=V((0, 0.08, -0.06)),
                 el=V((0.7, -0.2, 1.9)), er=V((-0.7, -0.2, 1.9)))
SLAM_DOWN = club((-0.02, -0.45, 1.35), (0.0, -0.75, 0.66), (1, 0, 0), spine=20.0, neck=-10.0, pel=V((0, -0.02, -0.18)),
                 el=V((0.7, 0.2, 1.3)), er=V((-0.7, 0.2, 1.3)))
SLAM_HIT = club((-0.02, -0.58, 0.62), (0.0, -0.92, -0.39), (1, 0, 0), spine=42.0, neck=-28.0, pel=V((0, 0.06, -0.32)),
                el=V((0.7, 0.3, 0.9)), er=V((-0.7, 0.3, 0.9)))
SLAM_STUCK = dict(SLAM_HIT, spine=38.0, pel=V((0, 0.05, -0.30)))
SLAM = [(1, READY), (40, SLAM_RAISE), (58, SLAM_COCK), (66, SLAM_DOWN), (70, SLAM_HIT), (76, dict(SLAM_HIT, spine=45.0, pel=V((0, 0.07, -0.34)))),
        (112, SLAM_STUCK), (150, READY)]


def snap_club(action, frames, spacing=2.6, axis='X', weapon='Club'):
    """side-by-side stick figures + club for frames of action (objects Prev_*), laid out along X"""
    arm.animation_data.action = bpy.data.actions[action]
    try: arm.animation_data.action_slot = bpy.data.actions[action].slots[0]
    except Exception: pass
    bpy.data.objects[weapon].hide_viewport = False    # a hidden object's Child Of isn't evaluated
    sg = {}; exec(bpy.data.texts['skel_preview.py'].as_string(), sg)
    for o in [o for o in bpy.data.objects if o.name.startswith('Prev_')]: bpy.data.objects.remove(o)
    names = []
    for i, f in enumerate(frames):
        arm.hide_viewport = False; sc.frame_set(f); bpy.context.view_layer.update()
        ob = sg['build_skel'](); cl = bpy.data.objects[weapon]
        for src, tag in ((ob, 'b'), (cl, 'c')):
            o = bpy.data.objects.new(f'Prev_{f}_{tag}', src.data.copy()); sc.collection.objects.link(o)
            off = V((-i * spacing, 0, 0)) if axis == 'X' else V((0, i * spacing, 0))
            o.matrix_world = Matrix.Translation(off) @ src.matrix_world
            names.append(o.name)
    bpy.data.objects['SkelPreview'].hide_viewport = True
    bpy.data.objects[weapon].hide_viewport = True
    arm.hide_viewport = False
    return names


# ---------- horizontal sweep, right -> left (club ~0.92m high = ~1.4m in game) ----------
# hit window ~f52-f68 of 130; chains into MM_Club_Sweep_Back from ~f88 (its first frame = SWEEP_HOLD)
def hz(G, K, **body):
    return club(G, K, hz_side(K), **body)
SW_PEL = V((0, 0.04, -0.15))
SWEEP_WIND = hz((-0.36, 0.10, 1.32), (-0.30, 0.80, 0.50), spine=8.0, spine_twist=-36.0, pel=SW_PEL, neck=-12.0,
                el=V((0.2, -0.5, 1.0)), er=V((-0.7, 0.4, 0.8)))
SWEEP_COCK = hz((-0.40, 0.16, 1.30), (-0.20, 0.90, 0.40), spine=6.0, spine_twist=-42.0, pel=SW_PEL, neck=-12.0,
                el=V((0.2, -0.5, 1.0)), er=V((-0.7, 0.4, 0.8)))
SWEEP_SIDE = hz((-0.38, -0.22, 1.05), (-0.95, -0.15, 0.10), spine=14.0, spine_twist=-20.0, pel=SW_PEL, neck=-14.0,
                el=V((0.4, -0.3, 0.9)), er=V((-0.6, 0.5, 0.8)))
SWEEP_MID = hz((-0.04, -0.44, 0.94), (0.05, -1.0, 0.0), spine=18.0, spine_twist=6.0, pel=SW_PEL, neck=-16.0,
               el=V((0.6, 0.0, 0.8)), er=V((-0.5, 0.3, 0.8)))
SWEEP_LEFT = hz((0.32, -0.26, 0.98), (0.95, -0.20, -0.02), spine=18.0, spine_twist=30.0, pel=SW_PEL, neck=-16.0,
                el=V((0.6, 0.4, 0.8)), er=V((-0.2, -0.5, 0.9)))
SWEEP_FOLLOW = hz((0.34, 0.04, 1.04), (0.60, 0.75, -0.10), spine=18.0, spine_twist=42.0, pel=SW_PEL, neck=-14.0,
                  el=V((0.7, 0.4, 0.8)), er=V((-0.2, -0.5, 0.9)))
SWEEP_HOLD = dict(SWEEP_FOLLOW, spine_twist=40.0, spine=17.0)
SWEEP = [(1, READY), (34, SWEEP_WIND), (48, SWEEP_COCK), (55, SWEEP_SIDE), (60, SWEEP_MID), (65, SWEEP_LEFT), (74, SWEEP_FOLLOW),
         (88, SWEEP_HOLD), (130, READY)]

# ---------- backhand sweep, left -> right (2nd hit of the combo) ----------
# hit window ~f27-f43 of 110
BACK_WIND = hz((0.38, 0.12, 1.32), (0.30, 0.80, 0.50), spine=8.0, spine_twist=46.0, pel=SW_PEL, neck=-12.0,
               el=V((0.7, 0.4, 0.8)), er=V((-0.2, -0.5, 1.0)))
BACK_SIDE = hz((0.36, -0.22, 1.05), (0.95, -0.15, 0.10), spine=14.0, spine_twist=22.0, pel=SW_PEL, neck=-14.0,
               el=V((0.6, 0.5, 0.8)), er=V((-0.4, -0.3, 0.9)))
BACK_MID = hz((0.04, -0.44, 0.94), (-0.05, -1.0, 0.0), spine=18.0, spine_twist=-4.0, pel=SW_PEL, neck=-16.0,
              el=V((0.5, 0.3, 0.8)), er=V((-0.6, 0.0, 0.8)))
BACK_RIGHT = hz((-0.32, -0.26, 0.98), (-0.95, -0.20, -0.02), spine=18.0, spine_twist=-30.0, pel=SW_PEL, neck=-16.0,
                el=V((0.2, -0.5, 0.9)), er=V((-0.6, 0.4, 0.8)))
BACK_FOLLOW = hz((-0.34, 0.04, 1.04), (-0.60, 0.75, -0.10), spine=18.0, spine_twist=-42.0, pel=SW_PEL, neck=-14.0,
                 el=V((0.2, -0.5, 0.9)), er=V((-0.7, 0.4, 0.8)))
SWEEP_BACK = [(1, SWEEP_HOLD), (18, BACK_WIND), (30, BACK_SIDE), (35, BACK_MID), (40, BACK_RIGHT), (50, BACK_FOLLOW),
              (64, dict(BACK_FOLLOW, spine_twist=-40.0)), (110, READY)]

# ---------- idle hold (loop; played on the UpperBody slot while walking / standing) ----------
IDLE = [(1, READY), (60, dict(READY, pel=V((0, 0.03, -0.135)), spine=16.0, hr=READY['hr'] + V((0, 0, -0.015)), hl=READY['hl'] + V((0, 0, -0.015)))), (120, READY)]

def build_all():
    out = [g['make']('MM_Club_Idle', IDLE), g['make']('MM_Club_Slam', SLAM), g['make']('MM_Club_Sweep', SWEEP), g['make']('MM_Club_Sweep_Back', SWEEP_BACK)]
    return out


def action_fcurves(act):
    try:
        return list(act.fcurves)
    except AttributeError:
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags: out += list(bag.fcurves)
        return out

def fix_quat_signs(act):
    """keep each bone's quaternion keys in one hemisphere so in-between frames don't spin the long way"""
    groups = {}
    for fc in action_fcurves(act):
        if fc.data_path.endswith('rotation_quaternion'): groups.setdefault(fc.data_path, {})[fc.array_index] = fc
    flips = 0
    for path, comps in groups.items():
        if len(comps) != 4: continue
        n = len(comps[0].keyframe_points)
        prev = None
        for i in range(n):
            q = [comps[c].keyframe_points[i].co[1] for c in range(4)]
            if prev and sum(a * b for a, b in zip(q, prev)) < 0:
                q = [-x for x in q]; flips += 1
                for c in range(4):
                    kp = comps[c].keyframe_points[i]; kp.co[1] = q[c]; kp.handle_left[1] = q[c]; kp.handle_right[1] = q[c]
            prev = q
        for c in range(4): comps[c].update()
    return flips

def make_club(name, keys):
    act = g['make'](name, keys, step=1)
    print(name, 'quat flips fixed:', fix_quat_signs(act))
    return act

def build_all():
    return [make_club('MM_Club_Idle', IDLE), make_club('MM_Club_Slam', SLAM), make_club('MM_Club_Sweep', SWEEP), make_club('MM_Club_Sweep_Back', SWEEP_BACK)]


# =====================================================================================================================
# v2 (2026-11-15): fixes for "broken arms"
#  1. club orientation is slerped as one rotation (cG + cQ) instead of lerping K / N vectors (which could pass through 0)
#  2. reach limit: the club is pulled toward the shoulders so the hand never needs more than REACH of the arm length
#  3. club roll per key is chosen to minimise wrist twist (a round club looks the same rolled); the remaining
#     forearm twist is shared with lowerarm_twist_01/02 so the skin doesn't candy-wrap at the wrist
# =====================================================================================================================
from mathutils import Quaternion
KN = g['ns']; BASE = g['base']; STANCE = g['STANCE']; lerp = g['lerp']; smooth = g['smooth']
ARM_LEN = {s: (arm.data.bones['lowerarm_' + s].head_local - arm.data.bones['upperarm_' + s].head_local).length +
              (arm.data.bones['hand_' + s].head_local - arm.data.bones['lowerarm_' + s].head_local).length for s in 'lr'}
REACH = 0.96
REST_REL = {s: arm.data.bones['lowerarm_' + s].matrix_local.to_3x3().inverted() @ arm.data.bones['hand_' + s].matrix_local.to_3x3() for s in 'lr'}
def _twist_bones(s):
    hand = arm.data.bones['hand_' + s].head_local
    b = sorted(['lowerarm_twist_01_' + s, 'lowerarm_twist_02_' + s], key=lambda n: (arm.data.bones[n].head_local - hand).length)
    return [(b[0], 0.6), (b[1], 0.3)]          # nearer the wrist takes more
TWIST_BONES = {s: _twist_bones(s) for s in 'lr'}
ARM_CHAIN = [n + '_' + s for s in 'lr' for n in ('upperarm', 'lowerarm', 'hand')]

def club_q(K, S):
    Z = V(K).normalized(); X = V(S); X = (X - Z * X.dot(Z)).normalized(); Y = Z.cross(X)
    return Matrix((X, Y, Z)).transposed().to_quaternion()

def club(G, K, S, **body):
    d = dict(cG=V(G), cK=V(K).normalized(), cS=V(S)); d.update(body)
    return d

def hands_of(G, Q):
    K = Q @ V((0, 0, 1)); S = Q @ V((1, 0, 0))
    return dict(hr=G, hl=G - K * CLUB_HANDS_GAP, Kr=K, Kl=K, Nr=-S, Nl=S)

def apply_body(q):
    """fishman_helpers.apply without the arms / neck"""
    arm.hide_viewport = False
    H['reset_base'](BASE)
    KN['move_pelvis'](q['pel'].z, q['pel'].y)
    if abs(q['pel'].x) > 1e-5:
        pb = P['pelvis']; M = pb.matrix.copy(); M.translation = M.translation + KN['Wi'].to_3x3() @ V((q['pel'].x, 0, 0)); pb.matrix = M; bpy.context.view_layer.update()
    KN['solve_leg']('l', q['al'], KN['foot_rot']('l', g['FROT_L'], q['pl']), q['kl'], -180)
    KN['solve_leg']('r', q['ar'], KN['foot_rot']('r', g['FROT_R'], q['pr']), q['kr'], -180)
    for s_, fr, pit in (('l', g['FROT_L'], q['pl']), ('r', g['FROT_R'], q['pr'])):
        pb = P['foot_' + s_]; M = pb.matrix.copy(); R = KN['foot_rot'](s_, fr, pit).to_4x4(); R.translation = M.translation
        pb.matrix = R; bpy.context.view_layer.update()
    H['tilt_bone']('spine_01', q['spine'] * 0.5); H['tilt_bone']('spine_03', q['spine'] * 0.5)
    if q['spine_side']: H['tilt_bone']('spine_02', q['spine_side'], 'Y')
    if q['spine_twist']: H['tilt_bone']('spine_02', q['spine_twist'], 'Z')

def hand_head_target(s, grip_w, Kw, Nw):
    """where hand_s's head must go (armature space) for its grip point to be at grip_w"""
    K, N, grip = H['hand_local'](s)
    R = H['frame'](V(Kw), V(Nw)) @ H['frame'](K, N).transposed()
    return arm.matrix_world.inverted() @ V(grip_w) - R @ grip

def reach_fix(G, Q):
    W3 = arm.matrix_world.to_3x3()
    for _ in range(6):
        h = hands_of(G, Q); worst = None
        for s in 'lr':
            d = hand_head_target(s, h['h' + s], h['K' + s], h['N' + s]) - P['upperarm_' + s].head
            over = d.length - REACH * ARM_LEN[s]
            if over > 0.05 and (worst is None or over > worst[0]): worst = (over, -d.normalized() * over)
        if not worst: break
        G = G + W3 @ worst[1]
    return G

def solve_arms(h, q):
    for n in ARM_CHAIN: P[n].matrix_basis = BASE[n]
    bpy.context.view_layer.update()
    H['solve_arm']('l', h['hl'], h['Kl'], h['Nl'], pole=q['pol_l'], pole_pos=q['el'])
    H['solve_arm']('r', h['hr'], h['Kr'], h['Nr'], pole=q['pol_r'], pole_pos=q['er'])

def wrist_twist(s):
    rel = P['lowerarm_' + s].matrix.to_3x3().inverted() @ P['hand_' + s].matrix.to_3x3()
    q = (REST_REL[s].inverted() @ rel).to_quaternion()
    return math.degrees(q.to_swing_twist('Y')[1])

def spread_twist(s):
    tw = wrist_twist(s)
    axis = (P['lowerarm_' + s].matrix.to_3x3() @ V((0, 1, 0))).normalized()
    for name, frac in TWIST_BONES[s]:
        pb = P[name]; M = pb.matrix.copy(); piv = M.translation.copy()
        pb.matrix = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(tw * frac), 4, axis) @ Matrix.Translation(-piv) @ M
    bpy.context.view_layer.update()

def apply_club(q):
    apply_body(q)
    G = reach_fix(q['cG'], q['cQ'])
    solve_arms(hands_of(G, q['cQ']), q)
    spread_twist('l'); spread_twist('r')
    H['tilt_bone']('neck_01', q['neck'])

def prepare(keys):
    """pick each key's club roll: least wrist twist, without spinning far from the previous key"""
    prevQ = None
    for f, p in keys:
        if 'cQ' not in p:
            q = dict(STANCE); q.update(p)
            apply_body(q)
            Q0 = club_q(p['cK'], p['cS'])
            best = None
            for roll in range(-180, 180, 15):
                Q = Q0 @ Quaternion((0, 0, 1), math.radians(roll))
                G = reach_fix(q['cG'], Q)
                solve_arms(hands_of(G, Q), q)
                cost = abs(wrist_twist('l')) + abs(wrist_twist('r'))
                if prevQ is not None: cost += 0.25 * math.degrees(prevQ.rotation_difference(Q).angle)
                if best is None or cost < best[0]: best = (cost, Q, roll)
            p['cQ'] = best[1]
        prevQ = p['cQ']

def blend_club(keys, f):
    full = [(k, dict(STANCE, **p)) for k, p in keys]
    if f <= full[0][0]: return full[0][1]
    for (f0, a), (f1, b) in zip(full, full[1:]):
        if f <= f1:
            t = smooth((f - f0) / (f1 - f0))
            out = {n: lerp(a[n], b[n], t) for n in a if n not in ('cQ', 'cK', 'cS') and not isinstance(a[n], Quaternion)}
            qa, qb = a['cQ'], b['cQ']
            if qa.dot(qb) < 0: qb = -qb
            out['cQ'] = qa.slerp(qb, t)
            return out
    return full[-1][1]

def make_club(name, keys):
    prepare(keys)
    arm.animation_data.action = None; arm.location = (0, 0, 0)
    f0, f1 = keys[0][0], keys[-1][0]
    poses = []
    for f in range(f0, f1 + 1):
        apply_club(blend_club(keys, f)); poses.append((f, {pb.name: pb.matrix_basis.copy() for pb in P}))
    act = bpy.data.actions.get(name)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    arm.animation_data.action = act
    for f, mats in poses:
        for pb in P: pb.matrix_basis = mats[pb.name]
        KN['key_all'](f)
    arm.keyframe_insert('location', frame=f0); arm.keyframe_insert('location', frame=f1)
    sc.frame_start = f0; sc.frame_end = f1
    print(name, 'quat flips fixed:', fix_quat_signs(act))
    return act

# ---------- keys (same moves as v1 + in-between keys where the club turns a long way) ----------
READY = club((0.0, -0.36, 1.0), (-0.45, -0.2, 0.87), (0.2, -0.45, 0), spine=14.0, el=EL, er=ER)
def rekey(d, **extra):
    """v1 pose dict -> v2 (hand fields -> club fields)"""
    out = {k: v for k, v in d.items() if k not in ('hr', 'hl', 'Kr', 'Kl', 'Nr', 'Nl')}
    out.update(cG=V(d['hr']), cK=V(d['Kr']).normalized(), cS=V(d['Nl'])); out.update(extra)
    return out
SLAM2 = [(1, READY), (40, rekey(SLAM_RAISE)), (58, rekey(SLAM_COCK)), (66, rekey(SLAM_DOWN)), (70, rekey(SLAM_HIT)),
         (76, rekey(SLAM_HIT, spine=45.0, pel=V((0, 0.07, -0.34)))), (112, rekey(SLAM_STUCK)),
         (132, club((-0.04, -0.45, 0.86), (-0.20, -0.75, 0.62), (1, 0, 0), spine=26.0, pel=V((0, 0.03, -0.22)), el=EL, er=ER)),
         (150, READY)]
S_HOLD = rekey(SWEEP_HOLD)
SWEEP2 = [(1, READY), (34, rekey(SWEEP_WIND)), (48, rekey(SWEEP_COCK)), (55, rekey(SWEEP_SIDE)), (60, rekey(SWEEP_MID)),
          (65, rekey(SWEEP_LEFT)), (74, rekey(SWEEP_FOLLOW)), (88, S_HOLD),
          (108, club((0.14, -0.30, 1.10), (0.25, -0.15, 0.95), (1, 0, 0), spine=16.0, spine_twist=14.0, pel=SW_PEL, el=EL, er=ER)),
          (130, READY)]
SWEEP_BACK2 = [(1, S_HOLD), (18, rekey(BACK_WIND)), (30, rekey(BACK_SIDE)), (35, rekey(BACK_MID)), (40, rekey(BACK_RIGHT)),
               (50, rekey(BACK_FOLLOW)), (64, rekey(BACK_FOLLOW, spine_twist=-40.0)),
               (86, club((-0.15, -0.38, 1.00), (-0.60, -0.30, 0.75), (1, 0, 0), spine=16.0, spine_twist=-14.0, pel=SW_PEL, el=EL, er=ER)),
               (110, READY)]
IDLE2 = [(1, READY), (60, dict(READY, pel=V((0, 0.03, -0.135)), spine=16.0, cG=READY['cG'] + V((0, 0, -0.015)))), (120, READY)]

def build_all():
    return [make_club('MM_Club_Idle', IDLE2), make_club('MM_Club_Slam', SLAM2), make_club('MM_Club_Sweep', SWEEP2), make_club('MM_Club_Sweep_Back', SWEEP_BACK2)]


# ---------- v2.1: elbow continuity. The pole target follows the previous frame's pole direction (75%) and eases toward the
# authored pole (25%), so a fast hand can't flip the elbow to the other side between two frames ----------
def coherent_pole(s, q, h, prev):
    authored = V(q['e' + s])
    if prev is None: return authored
    Wm = arm.matrix_world
    sh = Wm @ P['upperarm_' + s].head
    hd = Wm @ hand_head_target(s, h['h' + s], h['K' + s], h['N' + s])
    ax = (hd - sh).normalized(); mid = (sh + hd) * 0.5
    def perp(v):
        v = v - ax * v.dot(ax)
        return v.normalized() if v.length > 1e-5 else None
    da = perp(authored - mid); dp = perp(V(prev) - mid)
    if dp is None: return authored
    d = dp * 0.75 + (da * 0.25 if da is not None else V())
    if d.length < 1e-3: d = dp
    return mid + d.normalized() * 0.6

def apply_club(q, prev=None):
    apply_body(q)
    G = reach_fix(q['cG'], q['cQ'])
    h = hands_of(G, q['cQ'])
    for n in ARM_CHAIN: P[n].matrix_basis = BASE[n]
    bpy.context.view_layer.update()
    poles = {s: coherent_pole(s, q, h, prev[s] if prev else None) for s in 'lr'}
    H['solve_arm']('l', h['hl'], h['Kl'], h['Nl'], pole=q['pol_l'], pole_pos=poles['l'])
    H['solve_arm']('r', h['hr'], h['Kr'], h['Nr'], pole=q['pol_r'], pole_pos=poles['r'])
    spread_twist('l'); spread_twist('r')
    H['tilt_bone']('neck_01', q['neck'])
    return poles      # the pole targets used (pole space, so the right arm's -90 pole angle stays consistent)

def make_club(name, keys):
    prepare(keys)
    arm.animation_data.action = None; arm.location = (0, 0, 0)
    f0, f1 = keys[0][0], keys[-1][0]
    poses = []; prev = None
    for f in range(f0, f1 + 1):
        prev = apply_club(blend_club(keys, f), prev); poses.append((f, {pb.name: pb.matrix_basis.copy() for pb in P}))
    act = bpy.data.actions.get(name)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    arm.animation_data.action = act
    for f, mats in poses:
        for pb in P: pb.matrix_basis = mats[pb.name]
        KN['key_all'](f)
    arm.keyframe_insert('location', frame=f0); arm.keyframe_insert('location', frame=f1)
    sc.frame_start = f0; sc.frame_end = f1
    print(name, 'quat flips fixed:', fix_quat_signs(act))
    return act

def check(names=('MM_Club_Idle', 'MM_Club_Sweep', 'MM_Club_Sweep_Back', 'MM_Club_Slam')):
    """per arm: smallest elbow bend, biggest elbow-direction jump per frame, biggest wrist twist and twist jump"""
    def ang(a, b): return math.degrees(a.angle(b)) if a.length > 1e-6 and b.length > 1e-6 else 0
    for name in names:
        act = bpy.data.actions[name]; arm.animation_data.action = act
        try: arm.animation_data.action_slot = act.slots[0]
        except Exception: pass
        f0, f1 = map(int, act.frame_range)
        for s in 'lr':
            prev = None; minbend = (999, 0); jump = (0, 0); tw = (0, 0); twj = (0, 0); wsw = (0, 0)
            for f in range(f0, f1 + 1):
                sc.frame_set(f)
                ua, la, ha = P['upperarm_' + s].head, P['lowerarm_' + s].head, P['hand_' + s].head
                bend = 180 - ang(ua - la, ha - la)
                if bend < minbend[0]: minbend = (bend, f)
                ax = (ha - ua).normalized(); e = la - ua; e = e - ax * e.dot(ax)
                w = _wrap(skin_twist(s))
                if abs(w) > abs(tw[0]): tw = (w, f)
                ws_ = wrist_swing(s)
                if ws_ > wsw[0]: wsw = (ws_, f)
                if prev:
                    j = ang(e, prev[0]); d = abs(w - prev[1])
                    if j > jump[0]: jump = (j, f)
                    if d > twj[0]: twj = (d, f)
                prev = (e, w)
            print(f'{name} {s}: elbow min bend {minbend[0]:.0f}@f{minbend[1]} | elbow jump {jump[0]:.0f}@f{jump[1]} | skin twist {tw[0]:.0f}@f{tw[1]} | twist jump {twj[0]:.0f}@f{twj[1]} | wrist bend {wsw[0]:.0f}@f{wsw[1]}')


# ---------- v3: analytic two-bone arm IK (no Blender IK solver -> no jumping between solutions) ----------
# upperarm / lowerarm are turned so the elbow hinge keeps the rest pose's bend plane; the elbow points along a pole
# direction that follows the previous frame (75%) and eases toward the authored el / er point (25%); the hand gets
# its rotation directly (grip contract), its twist then shared with the twist bones.
_B = arm.data.bones
REST_ARM = {}
for _s in 'lr':
    S0 = _B['upperarm_' + _s].head_local; E0 = _B['lowerarm_' + _s].head_local; W0 = _B['hand_' + _s].head_local
    REST_ARM[_s] = dict(a=(E0 - S0).length, b=(W0 - E0).length, u=(E0 - S0).normalized(), l=(W0 - E0).normalized(),
                        n0=(E0 - S0).cross(W0 - E0).normalized(),
                        Ru=_B['upperarm_' + _s].matrix_local.to_3x3(), Rl=_B['lowerarm_' + _s].matrix_local.to_3x3())

def frame2(y, n):
    y = y.normalized(); n = (n - y * n.dot(y)).normalized()
    return Matrix((y, n, y.cross(n))).transposed()

def elbow_dir(s, q, S, T, prev_dir):
    """pole direction (armature space, perpendicular to shoulder->wrist)"""
    ax = (T - S).normalized()
    def perp(v):
        v = v - ax * v.dot(ax)
        return v.normalized() if v.length > 1e-6 else None
    mid_w = arm.matrix_world @ ((S + T) * 0.5)
    da = perp(V(q['e' + s]) - mid_w)          # world and armature axes are parallel (the armature is only scaled)
    dp = perp(V(prev_dir)) if prev_dir is not None else None
    if dp is None: return da if da is not None else perp(V((0, 0, -1)))
    d = dp * 0.75 + (da * 0.25 if da is not None else V())
    return perp(d) or dp

def solve_arm2(s, q, grip_w, Kw, Nw, prev_dir):
    r = REST_ARM[s]
    S = P['upperarm_' + s].head.copy()
    T = hand_head_target(s, grip_w, Kw, Nw)
    dv = T - S; ax = dv.normalized()
    d = min(dv.length, (r['a'] + r['b']) * 0.999); T = S + ax * d
    pd = elbow_dir(s, q, S, T, prev_dir)
    x = (r['a'] ** 2 - r['b'] ** 2 + d * d) / (2 * d); y = math.sqrt(max(r['a'] ** 2 - x * x, 0.0))
    E = S + ax * x + pd * y
    n = (E - S).cross(T - E)
    if n.length < 1e-6: n = ax.cross(pd)
    M = (frame2(E - S, n) @ frame2(r['u'], r['n0']).transposed() @ r['Ru']).to_4x4(); M.translation = S
    P['upperarm_' + s].matrix = M; bpy.context.view_layer.update()
    M = (frame2(T - E, n) @ frame2(r['l'], r['n0']).transposed() @ r['Rl']).to_4x4(); M.translation = E
    P['lowerarm_' + s].matrix = M; bpy.context.view_layer.update()
    K, N, grip = H['hand_local'](s)
    M = (H['frame'](V(Kw), V(Nw)) @ H['frame'](K, N).transposed()).to_4x4(); M.translation = T
    P['hand_' + s].matrix = M; bpy.context.view_layer.update()
    return pd

def solve_arms(h, q, prev=None):
    for n in ARM_CHAIN: P[n].matrix_basis = BASE[n]
    bpy.context.view_layer.update()
    return {s: solve_arm2(s, q, h['h' + s], h['K' + s], h['N' + s], prev[s] if prev else None) for s in 'lr'}

def apply_club(q, prev=None):
    apply_body(q)
    G = reach_fix(q['cG'], q['cQ'])
    dirs = solve_arms(hands_of(G, q['cQ']), q, prev)
    spread_twist('l'); spread_twist('r')
    H['tilt_bone']('neck_01', q['neck'])
    return dirs


# ---------- v3.1: left-hand grip angle around the handle (constant for every club anim), searched for least wrist twist ----------
LEFT_ROLL = -30.0     # left-hand grip angle around the handle; -30 = least wrist twist over all keys (search_left_roll, 2026-11-15)
def hands_of(G, Q):
    K = Q @ V((0, 0, 1)); Sr = Q @ V((1, 0, 0))
    Sl = Quaternion(K, math.radians(LEFT_ROLL)) @ (-Sr)
    return dict(hr=G, hl=G - K * CLUB_HANDS_GAP, Kr=K, Kl=K, Nr=-Sr, Nl=-Sl)

def all_keys():
    return [IDLE2, SLAM2, SWEEP2, SWEEP_BACK2]

def search_left_roll(step=30, roll_step=30):
    global LEFT_ROLL
    dicts = []
    for keys in all_keys():
        for f, p in keys:
            if all(p is not d for d in dicts): dicts.append(p)
    results = []
    for lr in range(-180, 180, step):
        LEFT_ROLL = float(lr); total = 0.0; worst = 0.0
        for p in dicts:
            q = dict(STANCE); q.update(p); apply_body(q)
            Q0 = club_q(p['cK'], p['cS']); best = None
            for roll in range(-180, 180, roll_step):
                Q = Q0 @ Quaternion((0, 0, 1), math.radians(roll))
                solve_arms(hands_of(reach_fix(q['cG'], Q), Q), q)
                c = max(abs(wrist_twist('l')), abs(wrist_twist('r')))
                best = c if best is None else min(best, c)
            total += best; worst = max(worst, best)
        results.append((total / len(dicts), worst, lr))
    results.sort()
    LEFT_ROLL = float(results[0][2])
    return results[:5]


# ---------- v3.2: per-frame club roll (a round club looks the same rolled): keeps the wrists near neutral between keys too ----------
def apply_club(q, prev=None):
    """prev = (elbow dirs, roll offset) of the previous frame"""
    apply_body(q)
    prev_dirs, prev_off = prev if prev else (None, 0.0)
    best = None
    for off in range(-90, 91, 10):
        Q = q['cQ'] @ Quaternion((0, 0, 1), math.radians(off))
        G = reach_fix(q['cG'], Q)
        solve_arms(hands_of(G, Q), q, prev_dirs)
        cost = max(abs(wrist_twist('l')), abs(wrist_twist('r'))) + 0.6 * abs(off - prev_off)
        if best is None or cost < best[0]: best = (cost, off, G, Q)
    _, off, G, Q = best
    dirs = solve_arms(hands_of(G, Q), q, prev_dirs)
    spread_twist('l'); spread_twist('r')
    H['tilt_bone']('neck_01', q['neck'])
    return dirs, float(off)


# ---------- v3.3: right wrist <- club roll, left wrist <- small slide of the left grip around the handle (each searched on its own) ----------
def hands_of(G, Q, left_extra=0.0):
    K = Q @ V((0, 0, 1)); Sr = Q @ V((1, 0, 0))
    Sl = Quaternion(K, math.radians(LEFT_ROLL + left_extra)) @ (-Sr)
    return dict(hr=G, hl=G - K * CLUB_HANDS_GAP, Kr=K, Kl=K, Nr=-Sr, Nl=-Sl)

def apply_club(q, prev=None):
    """prev = (elbow dirs, right roll offset, left grip offset) of the previous frame"""
    apply_body(q)
    prev_dirs, pr, pl = prev if prev else (None, 0.0, 0.0)
    for n in ARM_CHAIN: P[n].matrix_basis = BASE[n]
    bpy.context.view_layer.update()
    pd = prev_dirs or {'l': None, 'r': None}
    best = None
    for off in range(-90, 91, 10):
        Q = q['cQ'] @ Quaternion((0, 0, 1), math.radians(off))
        h = hands_of(reach_fix(q['cG'], Q), Q, pl)
        solve_arm2('r', q, h['hr'], h['Kr'], h['Nr'], pd['r'])
        c = abs(wrist_twist('r')) + 0.6 * abs(off - pr)
        if best is None or c < best[0]: best = (c, off, Q)
    _, off_r, Q = best
    best = None
    for le in range(-60, 61, 10):
        h = hands_of(reach_fix(q['cG'], Q), Q, le)
        solve_arm2('l', q, h['hl'], h['Kl'], h['Nl'], pd['l'])
        c = abs(wrist_twist('l')) + 0.6 * abs(le - pl)
        if best is None or c < best[0]: best = (c, le)
    off_l = best[1]
    h = hands_of(reach_fix(q['cG'], Q), Q, off_l)
    dirs = {s: solve_arm2(s, q, h['h' + s], h['K' + s], h['N' + s], pd[s]) for s in 'lr'}
    spread_twist('l'); spread_twist('r')
    H['tilt_bone']('neck_01', q['neck'])
    return dirs, float(off_r), float(off_l)


# ---------- v3.4: the elbow may also swing about the shoulder->wrist line (shoulder rotation) to unwind the wrist ----------
_solve_arm2_v3 = solve_arm2
def solve_arm2(s, q, grip_w, Kw, Nw, prev_dir, swing=0.0):
    if not swing: return _solve_arm2_v3(s, q, grip_w, Kw, Nw, prev_dir)
    r = REST_ARM[s]
    S = P['upperarm_' + s].head.copy(); T = hand_head_target(s, grip_w, Kw, Nw)
    ax = (T - S).normalized()
    base_dir = elbow_dir(s, q, S, S + ax * min((T - S).length, (r['a'] + r['b']) * 0.999), prev_dir)
    turned = Quaternion(ax, math.radians(swing)) @ base_dir
    return _solve_arm2_v3(s, dict(q, **{'e' + s: arm.matrix_world @ (S + turned * 50.0)}), grip_w, Kw, Nw, None)

def apply_club(q, prev=None):
    """prev = (elbow dirs, right roll offset, (left swing, left grip offset), right swing) of the previous frame"""
    apply_body(q)
    if prev: prev_dirs, pr, (psl, pl), psr = prev
    else: prev_dirs, pr, psl, pl, psr = None, 0.0, 0.0, 0.0, 0.0
    for n in ARM_CHAIN: P[n].matrix_basis = BASE[n]
    bpy.context.view_layer.update()
    pd = prev_dirs or {'l': None, 'r': None}
    # right wrist: club roll (+ a little elbow swing)
    best = None
    for off in range(-90, 91, 10):
        Q = q['cQ'] @ Quaternion((0, 0, 1), math.radians(off))
        h = hands_of(reach_fix(q['cG'], Q), Q, pl)
        for sw in (-30, -15, 0, 15, 30):
            solve_arm2('r', q, h['hr'], h['Kr'], h['Nr'], pd['r'], sw)
            c = abs(wrist_twist('r')) + 0.6 * abs(off - pr) + 0.8 * abs(sw - psr) + 0.2 * abs(sw)
            if best is None or c < best[0]: best = (c, off, Q, sw)
    _, off_r, Q, sw_r = best
    # left wrist: grip slide around the handle + elbow swing
    best = None
    for le in range(-60, 61, 15):
        h = hands_of(reach_fix(q['cG'], Q), Q, le)
        for sw in range(-60, 61, 15):
            solve_arm2('l', q, h['hl'], h['Kl'], h['Nl'], pd['l'], sw)
            c = abs(wrist_twist('l')) + 0.6 * abs(le - pl) + 0.8 * abs(sw - psl) + 0.2 * abs(sw)
            if best is None or c < best[0]: best = (c, le, sw)
    _, off_l, sw_l = best
    h = hands_of(reach_fix(q['cG'], Q), Q, off_l)
    dirs = {'l': solve_arm2('l', q, h['hl'], h['Kl'], h['Nl'], pd['l'], sw_l),
            'r': solve_arm2('r', q, h['hr'], h['Kr'], h['Nr'], pd['r'], sw_r)}
    # the swing is not fed back as the next frame's pole (it would compound): store the unswung direction
    for s, sw in (('l', sw_l), ('r', sw_r)):
        if sw:
            S = P['upperarm_' + s].head; T = P['hand_' + s].head; ax = (T - S).normalized()
            dirs[s] = Quaternion(ax, math.radians(-sw)) @ dirs[s]
    spread_twist('l'); spread_twist('r')
    H['tilt_bone']('neck_01', q['neck'])
    return dirs, float(off_r), (float(sw_l), float(off_l)), float(sw_r)


# ---------- v4: whole-animation optimisation of the free angles (Viterbi over frames), then smoothed ----------
# per frame free angles: right = (club roll offset, elbow swing), left = (grip slide, elbow swing)
# cost = |wrist twist| + LAMBDA * change between frames  -> unwinds early and smoothly instead of snapping late
LAMBDA = 1.0
R_STATES = [(o, w) for o in range(-90, 91, 10) for w in (-30, -15, 0, 15, 30)]
L_STATES = [(o, w) for o in range(-60, 61, 15) for w in range(-60, 61, 15)]

def viterbi(costs, states, lam):
    n = len(costs); S = len(states)
    acc = list(costs[0]); back = []
    for f in range(1, n):
        new = []; bk = []
        for j in range(S):
            best = None
            for i in range(S):
                c = acc[i] + lam * (abs(states[i][0] - states[j][0]) + abs(states[i][1] - states[j][1]))
                if best is None or c < best[0]: best = (c, i)
            new.append(best[0] + costs[f][j]); bk.append(best[1])
        acc = new; back.append(bk)
    j = min(range(S), key=lambda k: acc[k]); path = [j]
    for bk in reversed(back):
        j = bk[j]; path.append(j)
    path.reverse()
    return [states[k] for k in path]

def smooth_path(vals, sigma=2.5):
    n = len(vals); r = int(sigma * 3); out = []
    for i in range(n):
        ws = 0.0; acc = [0.0] * len(vals[0])
        for k in range(-r, r + 1):
            j = min(max(i + k, 0), n - 1); w = math.exp(-0.5 * (k / sigma) ** 2); ws += w
            for c in range(len(acc)): acc[c] += w * vals[j][c]
        out.append(tuple(a / ws for a in acc))
    return out

def make_club(name, keys):
    prepare(keys)
    arm.animation_data.action = None; arm.location = (0, 0, 0)
    f0, f1 = keys[0][0], keys[-1][0]
    frames = list(range(f0, f1 + 1)); qs = [blend_club(keys, f) for f in frames]
    # right arm table
    rc = []
    for q in qs:
        apply_body(q); row = []
        for off, sw in R_STATES:
            Q = q['cQ'] @ Quaternion((0, 0, 1), math.radians(off)); h = hands_of(reach_fix(q['cG'], Q), Q, 0.0)
            solve_arm2('r', q, h['hr'], h['Kr'], h['Nr'], None, sw)
            row.append(abs(wrist_twist('r')) + 0.15 * abs(sw))
        rc.append(row)
    rpath = smooth_path([tuple(map(float, s)) for s in viterbi(rc, R_STATES, LAMBDA)])
    # left arm table (with the chosen club roll)
    lc = []
    for q, (off, _) in zip(qs, rpath):
        apply_body(q); row = []
        Q = q['cQ'] @ Quaternion((0, 0, 1), math.radians(off))
        for le, sw in L_STATES:
            h = hands_of(reach_fix(q['cG'], Q), Q, le)
            solve_arm2('l', q, h['hl'], h['Kl'], h['Nl'], None, sw)
            row.append(abs(wrist_twist('l')) + 0.15 * abs(sw))
        lc.append(row)
    lpath = smooth_path([tuple(map(float, s)) for s in viterbi(lc, L_STATES, LAMBDA)])
    poses = []
    for f, q, (off, swr), (le, swl) in zip(frames, qs, rpath, lpath):
        apply_body(q)
        Q = q['cQ'] @ Quaternion((0, 0, 1), math.radians(off))
        h = hands_of(reach_fix(q['cG'], Q), Q, le)
        solve_arm2('r', q, h['hr'], h['Kr'], h['Nr'], None, swr)
        solve_arm2('l', q, h['hl'], h['Kl'], h['Nl'], None, swl)
        spread_twist('l'); spread_twist('r')
        H['tilt_bone']('neck_01', q['neck'])
        poses.append((f, {pb.name: pb.matrix_basis.copy() for pb in P}))
    act = bpy.data.actions.get(name)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    arm.animation_data.action = act
    for f, mats in poses:
        for pb in P: pb.matrix_basis = mats[pb.name]
        KN['key_all'](f)
    arm.keyframe_insert('location', frame=f0); arm.keyframe_insert('location', frame=f1)
    sc.frame_start = f0; sc.frame_end = f1
    print(name, 'quat flips fixed:', fix_quat_signs(act))
    return act


# ---------- v4.1: roll / grip angles searched over the full circle (circular distance), unwrapped before smoothing ----------
R_STATES = [(o, w) for o in range(-180, 180, 15) for w in (-30, -15, 0, 15, 30)]
L_STATES = [(o, w) for o in range(-180, 180, 20) for w in range(-60, 61, 20)]
def cdiff(a, b):
    d = (a - b) % 360.0
    return min(d, 360.0 - d)

def viterbi(costs, states, lam):
    n = len(costs); S = len(states)
    trans = [[lam * (cdiff(states[i][0], states[j][0]) + abs(states[i][1] - states[j][1])) for i in range(S)] for j in range(S)]
    acc = list(costs[0]); back = []
    for f in range(1, n):
        new = []; bk = []
        for j in range(S):
            tj = trans[j]
            i = min(range(S), key=lambda k: acc[k] + tj[k])
            new.append(acc[i] + tj[i] + costs[f][j]); bk.append(i)
        acc = new; back.append(bk)
    j = min(range(S), key=lambda k: acc[k]); path = [j]
    for bk in reversed(back):
        j = bk[j]; path.append(j)
    path.reverse()
    out = [list(map(float, states[k])) for k in path]
    for i in range(1, len(out)):           # unwrap the circular angle
        while out[i][0] - out[i - 1][0] > 180: out[i][0] -= 360
        while out[i][0] - out[i - 1][0] < -180: out[i][0] += 360
    return [tuple(v) for v in out]

def make_club(name, keys):
    prepare(keys)
    arm.animation_data.action = None; arm.location = (0, 0, 0)
    f0, f1 = keys[0][0], keys[-1][0]
    frames = list(range(f0, f1 + 1)); qs = [blend_club(keys, f) for f in frames]
    rc = []
    for q in qs:
        apply_body(q); row = []
        for off, sw in R_STATES:
            Q = q['cQ'] @ Quaternion((0, 0, 1), math.radians(off)); h = hands_of(reach_fix(q['cG'], Q), Q, 0.0)
            solve_arm2('r', q, h['hr'], h['Kr'], h['Nr'], None, sw)
            row.append(abs(wrist_twist('r')) + 0.15 * abs(sw))
        rc.append(row)
    rpath = smooth_path(viterbi(rc, R_STATES, LAMBDA))
    lc = []
    for q, (off, _) in zip(qs, rpath):
        apply_body(q); row = []
        Q = q['cQ'] @ Quaternion((0, 0, 1), math.radians(off))
        for le, sw in L_STATES:
            h = hands_of(reach_fix(q['cG'], Q), Q, le)
            solve_arm2('l', q, h['hl'], h['Kl'], h['Nl'], None, sw)
            row.append(abs(wrist_twist('l')) + 0.15 * abs(sw))
        lc.append(row)
    lpath = smooth_path(viterbi(lc, L_STATES, LAMBDA))
    poses = []
    for f, q, (off, swr), (le, swl) in zip(frames, qs, rpath, lpath):
        apply_body(q)
        Q = q['cQ'] @ Quaternion((0, 0, 1), math.radians(off))
        h = hands_of(reach_fix(q['cG'], Q), Q, le)
        solve_arm2('r', q, h['hr'], h['Kr'], h['Nr'], None, swr)
        solve_arm2('l', q, h['hl'], h['Kl'], h['Nl'], None, swl)
        spread_twist('l'); spread_twist('r')
        H['tilt_bone']('neck_01', q['neck'])
        poses.append((f, {pb.name: pb.matrix_basis.copy() for pb in P}))
    act = bpy.data.actions.get(name)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    arm.animation_data.action = act
    for f, mats in poses:
        for pb in P: pb.matrix_basis = mats[pb.name]
        KN['key_all'](f)
    arm.keyframe_insert('location', frame=f0); arm.keyframe_insert('location', frame=f1)
    sc.frame_start = f0; sc.frame_end = f1
    print(name, 'quat flips fixed:', fix_quat_signs(act))
    return act


# ---------- v4.2: continuous elbow base direction per frame (pass 1), searched swings are relative to it ----------
def solve_arm3(s, q, grip_w, Kw, Nw, base_dir, swing=0.0):
    """analytic IK with the elbow toward base_dir (armature space) turned by swing about shoulder->wrist; returns the unswung dir"""
    r = REST_ARM[s]
    S = P['upperarm_' + s].head.copy(); T = hand_head_target(s, grip_w, Kw, Nw)
    dv = T - S; ax = dv.normalized(); d = min(dv.length, (r['a'] + r['b']) * 0.999); T = S + ax * d
    pd = V(base_dir) - ax * V(base_dir).dot(ax)
    pd = pd.normalized() if pd.length > 1e-6 else ax.orthogonal().normalized()
    pdt = Quaternion(ax, math.radians(swing)) @ pd if swing else pd
    x = (r['a'] ** 2 - r['b'] ** 2 + d * d) / (2 * d); y = math.sqrt(max(r['a'] ** 2 - x * x, 0.0))
    E = S + ax * x + pdt * y
    n = (E - S).cross(T - E)
    if n.length < 1e-6: n = ax.cross(pdt)
    M = (frame2(E - S, n) @ frame2(r['u'], r['n0']).transposed() @ r['Ru']).to_4x4(); M.translation = S
    P['upperarm_' + s].matrix = M; bpy.context.view_layer.update()
    M = (frame2(T - E, n) @ frame2(r['l'], r['n0']).transposed() @ r['Rl']).to_4x4(); M.translation = E
    P['lowerarm_' + s].matrix = M; bpy.context.view_layer.update()
    K, N, grip = H['hand_local'](s)
    M = (H['frame'](V(Kw), V(Nw)) @ H['frame'](K, N).transposed()).to_4x4(); M.translation = T
    P['hand_' + s].matrix = M; bpy.context.view_layer.update()
    return pd

def base_dirs(qs):
    """pass 1: elbow directions that follow the previous frame (75%) and ease to the authored poles (25%)"""
    out = []; prev = None
    for q in qs:
        apply_body(q)
        h = hands_of(reach_fix(q['cG'], q['cQ']), q['cQ'], 0.0)
        cur = {}
        for s in 'lr':
            S = P['upperarm_' + s].head.copy(); T = hand_head_target(s, h['h' + s], h['K' + s], h['N' + s])
            cur[s] = elbow_dir(s, q, S, T, prev[s] if prev else None)
        out.append(cur); prev = cur
    return out

# ---------- v4.3: the cost also keeps the wrist from bending far (real wrists: ~70-80 deg) ----------
def wrist_swing(s):
    rel = P['lowerarm_' + s].matrix.to_3x3().inverted() @ P['hand_' + s].matrix.to_3x3()
    q = (REST_REL[s].inverted() @ rel).to_quaternion()
    return math.degrees(q.to_swing_twist('Y')[0].angle)
def wrist_cost(s):
    return abs(wrist_twist(s)) + 1.5 * max(0.0, wrist_swing(s) - 40.0)

def make_club(name, keys):
    prepare(keys)
    arm.animation_data.action = None; arm.location = (0, 0, 0)
    f0, f1 = keys[0][0], keys[-1][0]
    frames = list(range(f0, f1 + 1)); qs = [blend_club(keys, f) for f in frames]
    bd = base_dirs(qs)
    rc = []
    for q, b in zip(qs, bd):
        apply_body(q); row = []
        for off, sw in R_STATES:
            Q = q['cQ'] @ Quaternion((0, 0, 1), math.radians(off)); h = hands_of(reach_fix(q['cG'], Q), Q, 0.0)
            solve_arm3('r', q, h['hr'], h['Kr'], h['Nr'], b['r'], sw)
            row.append(wrist_cost('r') + 0.15 * abs(sw))
        rc.append(row)
    rpath = smooth_path(viterbi(rc, R_STATES, LAMBDA))
    lc = []
    for q, b, (off, _) in zip(qs, bd, rpath):
        apply_body(q); row = []
        Q = q['cQ'] @ Quaternion((0, 0, 1), math.radians(off))
        for le, sw in L_STATES:
            h = hands_of(reach_fix(q['cG'], Q), Q, le)
            solve_arm3('l', q, h['hl'], h['Kl'], h['Nl'], b['l'], sw)
            row.append(wrist_cost('l') + 0.15 * abs(sw))
        lc.append(row)
    lpath = smooth_path(viterbi(lc, L_STATES, LAMBDA))
    poses = []
    for f, q, b, (off, swr), (le, swl) in zip(frames, qs, bd, rpath, lpath):
        apply_body(q)
        Q = q['cQ'] @ Quaternion((0, 0, 1), math.radians(off))
        h = hands_of(reach_fix(q['cG'], Q), Q, le)
        solve_arm3('r', q, h['hr'], h['Kr'], h['Nr'], b['r'], swr)
        solve_arm3('l', q, h['hl'], h['Kl'], h['Nl'], b['l'], swl)
        spread_twist('l'); spread_twist('r')
        H['tilt_bone']('neck_01', q['neck'])
        poses.append((f, {pb.name: pb.matrix_basis.copy() for pb in P}))
    act = bpy.data.actions.get(name)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    arm.animation_data.action = act
    for f, mats in poses:
        for pb in P: pb.matrix_basis = mats[pb.name]
        KN['key_all'](f)
    arm.keyframe_insert('location', frame=f0); arm.keyframe_insert('location', frame=f1)
    sc.frame_start = f0; sc.frame_end = f1
    print(name, 'quat flips fixed:', fix_quat_signs(act))
    return act


# ---------- v4.4: anatomical wrist measures (the Blender rest pose of this rig is NOT neutral: right wrist bent 85 deg) ----------
def _anat_twist(S, E, W, I, Pk):
    fa = (W - E).normalized()
    ref = S - E; ref = ref - fa * ref.dot(fa)
    K = I - Pk; K = K - fa * K.dot(fa)
    if ref.length < 1e-6 or K.length < 1e-6: return 0.0
    return math.degrees(math.atan2(fa.dot(ref.cross(K)), ref.dot(K)))
_Bn = arm.data.bones
REST_TWIST = {s: _anat_twist(_Bn['upperarm_' + s].head_local, _Bn['lowerarm_' + s].head_local, _Bn['hand_' + s].head_local,
                             _Bn['index_01_' + s].head_local, _Bn['pinky_01_' + s].head_local) for s in 'lr'}

def wrist_twist(s):
    """pronation / supination: 0 = knuckle line (pinky->index) points toward the upper arm side of the elbow bend (handshake)"""
    return _anat_twist(P['upperarm_' + s].head, P['lowerarm_' + s].head, P['hand_' + s].head, P['index_01_' + s].head, P['pinky_01_' + s].head)

def wrist_swing(s):
    """wrist bend: angle between the forearm and the hand (wrist -> middle knuckle)"""
    E = P['lowerarm_' + s].head; W = P['hand_' + s].head; M = P['middle_01_' + s].head
    return math.degrees((W - E).angle(M - W))

def spread_twist(s):
    """forearm skin follows the pronation: twist bones turn by part of (twist - rest twist) about the forearm"""
    tw = wrist_twist(s) - REST_TWIST[s]
    tw = (tw + 180.0) % 360.0 - 180.0
    E = P['lowerarm_' + s].head; W = P['hand_' + s].head; axis = (W - E).normalized()
    for name, frac in TWIST_BONES[s]:
        pb = P[name]; M = pb.matrix.copy(); piv = M.translation.copy()
        pb.matrix = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(tw * frac), 4, axis) @ Matrix.Translation(-piv) @ M
    bpy.context.view_layer.update()

def reach_fix(G, Q, left_extra=0.0):
    W3 = arm.matrix_world.to_3x3()
    for _ in range(6):
        h = hands_of(G, Q, left_extra); worst = None
        for s in 'lr':
            d = hand_head_target(s, h['h' + s], h['K' + s], h['N' + s]) - P['upperarm_' + s].head
            over = d.length - REACH * ARM_LEN[s]
            if over > 0.05 and (worst is None or over > worst[0]): worst = (over, -d.normalized() * over)
        if not worst: break
        G = G + W3 @ worst[1]
    return G


# ---------- v4.5: skin twist measured about the real forearm axis (this rig's bone Y is 90 deg off the bone direction),
# relative to the stick-ready BASE pose (looks right in game); cost = skin twist + anatomical limits ----------
def _forearm_local_axis(s):
    E = P['lowerarm_' + s].head; W = P['hand_' + s].head
    return (P['lowerarm_' + s].matrix.to_3x3().inverted() @ (W - E)).normalized()
def _rel(s): return P['lowerarm_' + s].matrix.to_3x3().inverted() @ P['hand_' + s].matrix.to_3x3()
H['reset_base'](BASE)
BASE_REL = {s: _rel(s) for s in 'lr'}
BASE_AXIS = {s: _forearm_local_axis(s) for s in 'lr'}

def skin_twist(s):
    q = (BASE_REL[s].inverted() @ _rel(s)).to_quaternion()
    # rotation of the hand relative to the forearm, twist part about the forearm axis (expressed in BASE hand space)
    ax = (BASE_REL[s].transposed() @ BASE_AXIS[s]).normalized()
    v = V((q.x, q.y, q.z)); p = v.dot(ax)
    return math.degrees(2.0 * math.atan2(p, q.w))
def _wrap(a): return (a + 180.0) % 360.0 - 180.0

def wrist_cost(s):
    return abs(_wrap(skin_twist(s))) + 1.0 * max(0.0, abs(wrist_twist(s)) - 90.0) + 1.5 * max(0.0, wrist_swing(s) - 40.0)

def spread_twist(s):
    tw = _wrap(skin_twist(s))
    E = P['lowerarm_' + s].head; W = P['hand_' + s].head; axis = (W - E).normalized()
    for name, frac in TWIST_BONES[s]:
        pb = P[name]; pb.matrix_basis = BASE[name]
    bpy.context.view_layer.update()
    for name, frac in TWIST_BONES[s]:
        pb = P[name]; M = pb.matrix.copy(); piv = M.translation.copy()
        pb.matrix = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(tw * frac), 4, axis) @ Matrix.Translation(-piv) @ M
    bpy.context.view_layer.update()


# ---------- v4.6: the club axis follows a great circle between keys (independent of the keys' roll); roll eases
# between the keys on top of parallel transport (the Viterbi pass then picks the final roll) ----------
def _signed_roll(Qfrom, Qto):
    """angle about Qto's local Z that turns Qfrom into Qto (both with the same Z axis)"""
    d = Qto.inverted() @ Qfrom
    return -2.0 * math.atan2(d.z, d.w)
def blend_club(keys, f):
    full = [(k, dict(STANCE, **p)) for k, p in keys]
    if f <= full[0][0]: return full[0][1]
    for (f0, a), (f1, b) in zip(full, full[1:]):
        if f <= f1:
            t = smooth((f - f0) / (f1 - f0))
            out = {n: lerp(a[n], b[n], t) for n in a if n not in ('cQ', 'cK', 'cS') and not isinstance(a[n], Quaternion)}
            Qa, Qb = a['cQ'], b['cQ']
            Ka = Qa @ V((0, 0, 1)); Kb = Qb @ V((0, 0, 1))
            Kt = Ka.slerp(Kb, t) if Ka.angle(Kb) < math.radians(179) else (Ka if t < 0.5 else Kb)
            Qend = Ka.rotation_difference(Kb) @ Qa                  # a's roll carried to b's axis
            delta = _signed_roll(Qend, Qb)
            if delta > math.pi: delta -= 2 * math.pi
            if delta < -math.pi: delta += 2 * math.pi
            out['cQ'] = Ka.rotation_difference(Kt) @ Qa @ Quaternion((0, 0, 1), delta * t)
            return out
    return full[-1][1]


# ---------- v4.7: analytic leg IK - the knee always points the way the toes point (Blender IK with a fixed
# knee pole twisted the leg when a foot was behind the body or the leg nearly straight) ----------
REST_LEG = {}
for _s in 'lr':
    S0 = _B['thigh_' + _s].head_local; E0 = _B['calf_' + _s].head_local; A0 = _B['foot_' + _s].head_local; T0 = _B['ball_' + _s].head_local
    REST_LEG[_s] = dict(a=(E0 - S0).length, b=(A0 - E0).length, u=(E0 - S0).normalized(), l=(A0 - E0).normalized(),
                        n0=(E0 - S0).cross(A0 - E0).normalized(),
                        Ru=_B['thigh_' + _s].matrix_local.to_3x3(), Rl=_B['calf_' + _s].matrix_local.to_3x3(),
                        toe_local=(_B['foot_' + _s].matrix_local.to_3x3().inverted() @ (T0 - A0)).normalized())

def solve_leg2(s, ankle_w, foot_rot):
    r = REST_LEG[s]
    S = P['thigh_' + s].head.copy()
    T = arm.matrix_world.inverted() @ V(ankle_w)
    dv = T - S; ax = dv.normalized(); d = min(dv.length, (r['a'] + r['b']) * 0.995); T = S + ax * d
    toe = foot_rot @ r['toe_local']
    pd = toe - ax * toe.dot(ax)
    pd = pd.normalized() if pd.length > 1e-6 else ax.orthogonal().normalized()
    x = (r['a'] ** 2 - r['b'] ** 2 + d * d) / (2 * d); y = math.sqrt(max(r['a'] ** 2 - x * x, 0.0))
    E = S + ax * x + pd * y
    n = (E - S).cross(T - E)
    if n.length < 1e-6: n = ax.cross(pd)
    M = (frame2(E - S, n) @ frame2(r['u'], r['n0']).transposed() @ r['Ru']).to_4x4(); M.translation = S
    P['thigh_' + s].matrix = M; bpy.context.view_layer.update()
    M = (frame2(T - E, n) @ frame2(r['l'], r['n0']).transposed() @ r['Rl']).to_4x4(); M.translation = E
    P['calf_' + s].matrix = M; bpy.context.view_layer.update()
    M = foot_rot.to_4x4(); M.translation = T
    P['foot_' + s].matrix = M; bpy.context.view_layer.update()

def apply_body(q):
    arm.hide_viewport = False
    H['reset_base'](BASE)
    KN['move_pelvis'](q['pel'].z, q['pel'].y)
    if abs(q['pel'].x) > 1e-5:
        pb = P['pelvis']; M = pb.matrix.copy(); M.translation = M.translation + KN['Wi'].to_3x3() @ V((q['pel'].x, 0, 0)); pb.matrix = M; bpy.context.view_layer.update()
    solve_leg2('l', q['al'], KN['foot_rot']('l', g['FROT_L'], q['pl']))
    solve_leg2('r', q['ar'], KN['foot_rot']('r', g['FROT_R'], q['pr']))
    H['tilt_bone']('spine_01', q['spine'] * 0.5); H['tilt_bone']('spine_03', q['spine'] * 0.5)
    if q['spine_side']: H['tilt_bone']('spine_02', q['spine_side'], 'Y')
    if q['spine_twist']: H['tilt_bone']('spine_02', q['spine_twist'], 'Z')

def leg_twist(s):
    """knee direction vs toe direction about the hip->ankle line (0 = knee over the toes)"""
    Hh = P['thigh_' + s].head; K = P['calf_' + s].head; A = P['foot_' + s].head; Bl = P['ball_' + s].head
    ax = (A - Hh).normalized()
    kd = K - (Hh + A) * 0.5; kd = kd - ax * kd.dot(ax)
    fd = Bl - A; fd = fd - ax * fd.dot(ax)
    return math.degrees(math.atan2(ax.dot(kd.cross(fd)), kd.dot(fd)))
