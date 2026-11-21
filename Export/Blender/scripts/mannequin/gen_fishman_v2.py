
# Fishman boss anims v2 (2026-11-22): Fish_Slam / Fish_Jump_Slam / Fish_Stomp_R / Fish_Stomp_L remade on gen_club.py v4.7.
# v1 (gen_fishman.py + fishman_helpers.make: Blender IK arms, keys every 2 frames) had straight elbows (1-2 deg), elbow
# flips up to 150 deg/frame and upper-arm twist up to +-179 deg (user: "shoulders and arms twist").
# Same key poses and lengths as v1 (the C++ hit-window fractions stay valid). New:
#  - pass-through keys ('_pass': True, cubic Hermite / Catmull-Rom tangent, no stop) make the hands swing up in an arc in
#    FRONT of the body: v1 moved them in a straight line hip -> overhead, through the shoulder, so the arm folded up and
#    the elbow flipped (slam f20-24, jump take-off f35-40, jump landing f66-72);
#  - analytic arm IK (solve_arm3), hand never further than REACH of the arm; the elbow base direction is continuous
#    (75% previous frame + 25% authored el / er point);
#  - elbow swing about the shoulder->wrist line chosen over the WHOLE anim (Viterbi + Gaussian smoothing),
#    cost = elbow into the body + distance from the authored pole (an upper-arm twist term was tried: every twist
#    reference is near-singular for arms overhead, so it only pushed the elbows backward);
#  - hands: no twist relative to the forearm (the fishman mesh has no twist-bone weights, so any hand twist wraps the
#    wrist skin); the wrist bend comes from the authored orientation, softly limited to WRIST_MAX;
#  - hand orientations slerped between keys (v1 lerped the K / N vectors);
#  - clavicles follow the arms (raise when the hands go above the shoulder, protract when they reach forward), measured
#    in the chest frame;
#  - legs: solve_leg2 (knee over the toes); every frame keyed, quaternion signs fixed.
import bpy, math
from mathutils import Vector, Matrix, Quaternion
C = {}; exec(bpy.data.texts['gen_club.py'].as_string(), C)
V = Vector; arm = C['arm']; P = C['P']; H = C['H']; KN = C['KN']; BASE = C['BASE']; STANCE = C['STANCE']
sc = bpy.context.scene; W = arm.matrix_world; Wi = W.inverted(); W3 = W.to_3x3()
smooth = C['smooth']; lerp = C['lerp']
WRIST_MAX = 45.0                 # deg, wrist bend away from the BASE hand pose (tanh-limited)
CLAV_UP = 22.0; CLAV_FWD = 10.0  # deg, clavicle raise (hands straight up) / protraction (hands straight forward)
SW_STATES = list(range(-90, 91, 10)); SW_LAMBDA = 1.0; SW_COST = 0.5

# ================================================================ keys (same as v1 gen_fishman.py)
# ---------------- two-hand overhead slam (150 f)
UP = dict(pel=V((0, 0.06, -0.04)), spine=-14.0, neck=-18.0,
          hl=V((0.07, 0.02, 2.05)), Kl=V((-1, 0, 0)), Nl=V((0, 1, 0.3)), el=V((0.7, -0.3, 1.7)),
          hr=V((-0.07, 0.02, 2.05)), Kr=V((1, 0, 0)), Nr=V((0, 1, 0.3)), er=V((-0.7, -0.3, 1.7)))
DOWN = dict(pel=V((0, 0.16, -0.50)), spine=82.0, neck=-40.0, kl=V((0.6, -1.5, 0.5)), kr=V((-0.6, -1.5, 0.5)),
            hl=V((0.09, -0.66, 0.12)), Kl=V((-1, 0, 0)), Nl=V((0, -1, 0.6)), el=V((0.8, 0.2, 1.0)),
            hr=V((-0.09, -0.66, 0.12)), Kr=V((1, 0, 0)), Nr=V((0, -1, 0.6)), er=V((-0.8, 0.2, 1.0)))
def between(a, b, t, **over):
    """pass-through key: the body halfway between keys a and b (missing params = STANCE), then `over`"""
    fa = dict(STANCE, **a); fb = dict(STANCE, **b)
    d = {n: lerp(fa[n], fb[n], t) for n in fa}; d.update(over); d['_pass'] = True
    return d
# v2: hands swing forward and up (chest height in front) instead of straight up past the shoulder
SWING = between({}, UP, 0.5, hl=V((0.14, -0.55, 1.35)), hr=V((-0.14, -0.55, 1.35)), el=V((0.8, 0.0, 1.1)), er=V((-0.8, 0.0, 1.1)))
SLAM = [(1, {}), (24, SWING), (50, UP), (64, dict(UP, spine=-18.0)), (74, DOWN), (110, dict(DOWN, spine=78.0)), (150, {})]

# ---------------- jump in place, land with an area shockwave (140 f)
def arms(hl, hr, Kl=V((0, -1, 0)), Kr=V((0, -1, 0)), Nl=V((1, 0, 0)), Nr=V((-1, 0, 0)), el=V((0.8, 0.5, 1.0)), er=None):
    er = er or V((-el.x, el.y, el.z))
    return dict(hl=hl, hr=hr, Kl=Kl, Kr=Kr, Nl=Nl, Nr=Nr, el=el, er=er)
CROUCH = dict(pel=V((0, 0.08, -0.40)), spine=38.0, neck=-30.0, **arms(V((0.32, 0.30, 0.62)), V((-0.32, 0.30, 0.62)), el=V((0.6, 0.2, 1.4))))
TAKEOFF = dict(pel=V((0, 0.0, 0.12)), spine=4.0, neck=-14.0, al=V((0.20, -0.02, 0.17)), ar=V((-0.20, 0.02, 0.17)), pl=35.0, pr=29.0,
               **arms(V((0.30, -0.25, 1.75)), V((-0.30, -0.25, 1.75)), Kl=V((0, 0, 1)), Kr=V((0, 0, 1)), el=V((0.9, 0.3, 1.6))))
PEAK = dict(pel=V((0, 0.0, 0.50)), spine=10.0, neck=-16.0, al=V((0.22, 0.04, 0.50)), ar=V((-0.22, 0.06, 0.52)), pl=25.0, pr=19.0,
            kl=V((0.5, -1.5, 1.2)), kr=V((-0.5, -1.5, 1.2)),
            **arms(V((0.28, -0.20, 2.25)), V((-0.28, -0.20, 2.25)), Kl=V((0, 0, 1)), Kr=V((0, 0, 1)), Nl=V((0, 1, 0)), Nr=V((0, 1, 0)), el=V((0.9, 0.0, 2.0))))
FALL = dict(PEAK, pel=V((0, 0.02, 0.18)), al=V((0.24, -0.02, 0.16)), ar=V((-0.24, 0.0, 0.16)), pl=12.0, pr=6.0, kl=V((0.5, -1.5, 0.5)), kr=V((-0.5, -1.5, 0.5)))
LAND = dict(pel=V((0, 0.10, -0.46)), spine=48.0, neck=-34.0, al=V((0.26, -0.06, 0.094)), ar=V((-0.26, -0.02, 0.094)), kl=V((0.8, -1.5, 0.5)), kr=V((-0.8, -1.5, 0.5)),
            **arms(V((0.42, -0.42, 0.14)), V((-0.42, -0.42, 0.14)), Kl=V((0, -1, 0)), Kr=V((0, -1, 0)), Nl=V((0.3, -0.2, 1)), Nr=V((-0.3, -0.2, 1)), el=V((1.0, 0.3, 1.2))))
# v2: arms swing forward on the way up (take-off) and forward-out on the way down (landing)
SWING_UP = between(CROUCH, TAKEOFF, 0.5, hl=V((0.30, -0.52, 1.05)), hr=V((-0.30, -0.52, 1.05)), el=V((0.9, 0.3, 1.2)), er=V((-0.9, 0.3, 1.2)))
SWING_DOWN = between(FALL, LAND, 0.5, hl=V((0.55, -0.45, 1.20)), hr=V((-0.55, -0.45, 1.20)), el=V((1.0, 0.3, 1.4)), er=V((-1.0, 0.3, 1.4)))
JUMP = [(1, {}), (32, CROUCH), (37, SWING_UP), (42, TAKEOFF), (56, PEAK), (66, FALL), (69, SWING_DOWN), (72, LAND),
        (106, dict(LAND, spine=44.0)), (140, {})]

# ---------------- stomp with one foot (120 f); side +1 = right foot, -1 = left foot
def stomp(side):
    x = -side   # right is -X
    s_, o_ = ('r', 'l') if side > 0 else ('l', 'r')
    def legs(stomp_ankle, pitch, knee):
        return {'a' + s_: stomp_ankle, 'p' + s_: pitch, 'k' + s_: knee}
    def hands(h_same, h_other, el_same, el_other):
        d = {}
        d['h' + s_] = h_same; d['h' + o_] = h_other
        d['e' + s_] = el_same; d['e' + o_] = el_other
        d['K' + s_] = V((0, -1, 0)); d['K' + o_] = V((0, -1, 0))
        d['N' + s_] = V((x, 0, 0)); d['N' + o_] = V((-x, 0, 0))
        return d
    base_pitch = -6.0 if s_ == 'r' else 0.0
    LIFT = dict(pel=V((-x * 0.08, 0.04, -0.06)), spine=4.0, neck=-14.0,
                **legs(V((x * 0.18, -0.20, 0.62)), base_pitch - 35.0, V((x * 0.4, -1.5, 1.3))),
                **hands(V((x * 0.48, -0.25, 1.10)), V((-x * 0.50, -0.02, 1.05)), V((x * 0.9, 0.5, 1.2)), V((-x * 0.9, 0.5, 1.2))))
    TOP = dict(LIFT, spine=0.0, **legs(V((x * 0.18, -0.24, 0.68)), base_pitch - 40.0, V((x * 0.4, -1.5, 1.4))))
    STOMP = dict(pel=V((x * 0.02, 0.06, -0.30)), spine=30.0, neck=-28.0,
                 **legs(V((x * 0.21, -0.50, 0.094)), base_pitch, V((x * 0.5, -1.5, 0.6))),
                 **hands(V((x * 0.36, -0.40, 0.62)), V((-x * 0.40, -0.25, 0.66)), V((x * 0.9, 0.4, 1.1)), V((-x * 0.9, 0.4, 1.1))))
    BACK = dict(pel=V((-x * 0.04, 0.03, -0.12)), spine=16.0, **legs(V((x * 0.20, -0.22, 0.20)), base_pitch, V((x * 0.5, -1.5, 0.6))))
    return [(1, {}), (34, LIFT), (46, TOP), (54, STOMP), (90, dict(STOMP, spine=26.0)), (106, BACK), (120, {})]
STOMP_R = stomp(1); STOMP_L = stomp(-1)

ANIMS = [('Fish_Slam', SLAM), ('Fish_Jump_Slam', JUMP), ('Fish_Stomp_R', STOMP_R), ('Fish_Stomp_L', STOMP_L)]

# ================================================================ interpolation (hand orientations slerped)
def hand_q(K, N):
    return H['frame'](V(K), V(N)).to_quaternion()

def full(keys):
    out = []
    for f, p in keys:
        d = dict(STANCE); d.update(p); d.setdefault('_pass', False)
        d['Ql'] = hand_q(d['Kl'], d['Nl']); d['Qr'] = hand_q(d['Kr'], d['Nr'])
        out.append((f, d))
    return out

def blend(fk, f):
    """cubic Hermite per segment: tangent 0 at normal keys (ease in / out, holds stay put), Catmull-Rom tangent at
    '_pass' keys (the motion flows through them); hand rotations slerped with the matching ease"""
    if f <= fk[0][0]: return dict(fk[0][1])
    n = len(fk)
    def tan(i, name):
        fi, d = fk[i]
        if not d['_pass'] or i == 0 or i == n - 1: return None
        (fp, a), (fn, b) = fk[i - 1], fk[i + 1]
        return (b[name] - a[name]) * (1.0 / (fn - fp))
    for i in range(n - 1):
        (f0, a), (f1, b) = fk[i], fk[i + 1]
        if f <= f1:
            h = f1 - f0; t = (f - f0) / h; t2 = t * t; t3 = t2 * t
            out = {'_pass': False}
            for name, va in a.items():
                if isinstance(va, Quaternion) or isinstance(va, bool) or name == '_pass': continue
                vb = b[name]; ma = tan(i, name); mb = tan(i + 1, name)
                v = va * (2 * t3 - 3 * t2 + 1) + vb * (-2 * t3 + 3 * t2)
                if ma is not None: v = v + ma * (h * (t3 - 2 * t2 + t))
                if mb is not None: v = v + mb * (h * (t3 - t2))
                out[name] = v
            pa, pb = a['_pass'], b['_pass']
            e = t if (pa and pb) else (t * (2 - t) if pa else (t * t if pb else smooth(t)))
            for name in ('Ql', 'Qr'):
                qa, qb = a[name], b[name]
                if qa.dot(qb) < 0: qb = -qb
                out[name] = qa.slerp(qb, e)
            return out
    return dict(fk[-1][1])

# ================================================================ clavicles, arms, hands
H['reset_base'](BASE)
SP5_0 = P['spine_05'].matrix.to_3x3().normalized()
def _rel(a, b): return P[a].matrix.to_3x3().inverted() @ P[b].matrix.to_3x3()
SH_REL = {s: _rel('clavicle_' + s, 'upperarm_' + s) for s in 'lr'}
SH_AX = {s: (P['upperarm_' + s].matrix.to_3x3().inverted() @ (P['lowerarm_' + s].head - P['upperarm_' + s].head)).normalized()
         for s in 'lr'}

def rot_about(name, axis, deg):
    pb = P[name]; M = pb.matrix.copy(); piv = M.translation.copy()
    pb.matrix = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(deg), 4, V(axis)) @ Matrix.Translation(-piv) @ M
    bpy.context.view_layer.update()

def raise_clavicles(q):
    Rc = P['spine_05'].matrix.to_3x3().normalized() @ SP5_0.inverted()     # chest rotation vs BASE (armature axes)
    for s in 'lr':
        sx = 1.0 if s == 'l' else -1.0
        d = V(q['h' + s]) - W @ P['upperarm_' + s].head
        if d.length < 1e-6: continue
        dc = Rc.inverted() @ d.normalized()                                  # world and armature axes are parallel
        elev = math.degrees(math.asin(max(-1.0, min(1.0, dc.z))))
        up = CLAV_UP * smooth(elev / 90.0)
        fwd = CLAV_FWD * smooth(max(0.0, -dc.y))
        rot_about('clavicle_' + s, Rc @ V((0, 1, 0)), -sx * up)
        rot_about('clavicle_' + s, Rc @ V((0, 0, 1)), -sx * fwd)

def arm_target(s, q):
    """grip point (world, pulled in to REACH), knuckle axis, back-of-hand normal"""
    Q = q['Q' + s]; Kw = Q @ V((1, 0, 0)); Nw = Q @ V((0, 1, 0))
    G = V(q['h' + s]); S = P['upperarm_' + s].head
    T = C['hand_head_target'](s, G, Kw, Nw)
    over = (T - S).length - C['REACH'] * C['ARM_LEN'][s]
    if over > 0: G = G - W3 @ ((T - S).normalized() * over)
    return G, Kw, Nw

UB0 = {s: P['upperarm_' + s].matrix.to_3x3().normalized() for s in 'lr'}       # BASE upper arms (armature space)
def shoulder_twist(s):
    """upper-arm twist about its own axis (deg). Zero-twist reference for an arm direction d: the BASE upper arm swung
    (shortest arc) out to the side, then shortest arc from the side to d, all in the chest frame. A direct swing from
    BASE (arms forward-down) is singular for arms overhead (~180 deg away); the side reference is singular only for an
    arm pointing straight across the chest."""
    sx = 1.0 if s == 'l' else -1.0
    Rc = P['spine_05'].matrix.to_3x3().normalized() @ SP5_0.inverted()
    U = P['upperarm_' + s].matrix.to_3x3().normalized()
    Ub = Rc @ UB0[s]; ab = (Ub @ SH_AX[s]).normalized(); d = (U @ SH_AX[s]).normalized()
    lat = Rc @ V((sx, 0, 0))
    Ref = (lat.rotation_difference(d) @ ab.rotation_difference(lat)).to_matrix() @ Ub
    q = (Ref.inverted() @ U).to_quaternion()
    p = V((q.x, q.y, q.z)).dot(SH_AX[s])
    return C['_wrap'](math.degrees(2.0 * math.atan2(p, q.w)))

def fix_hand(s):
    """keep the hand's bend from the authored pose, drop its twist about the forearm, limit the bend"""
    La = P['lowerarm_' + s].matrix.to_3x3(); BR = C['BASE_REL'][s]
    q = (BR.inverted() @ (La.inverted() @ P['hand_' + s].matrix.to_3x3())).to_quaternion()
    ax = (BR.transposed() @ C['BASE_AXIS'][s]).normalized()
    tw = Quaternion(ax, 2.0 * math.atan2(V((q.x, q.y, q.z)).dot(ax), q.w))
    sw = q @ tw.inverted()
    if sw.w < 0: sw = -sw
    a = sw.angle; lim = math.radians(WRIST_MAX)
    sw2 = Quaternion(sw.axis, lim * math.tanh(a / lim)) if a > 1e-6 else Quaternion()
    M = (La @ BR @ sw2.to_matrix()).to_4x4(); M.translation = P['hand_' + s].matrix.translation.copy()
    P['hand_' + s].matrix = M; bpy.context.view_layer.update()

def arm_cost(s, sw):
    sx = 1.0 if s == 'l' else -1.0
    E = P['lowerarm_' + s].head; S = P['upperarm_' + s].head
    inward = -(sx * (E.x - S.x))                     # cm the elbow sits inside the shoulder
    return SW_COST * abs(sw) + 2.0 * max(0.0, inward - 3.0)

def viterbi1(costs, states, lam):
    n = len(costs); S = len(states)
    acc = list(costs[0]); back = []
    for f in range(1, n):
        new = []; bk = []
        for j in range(S):
            i = min(range(S), key=lambda k: acc[k] + lam * abs(states[k] - states[j]))
            new.append(acc[i] + lam * abs(states[i] - states[j]) + costs[f][j]); bk.append(i)
        acc = new; back.append(bk)
    j = min(range(S), key=lambda k: acc[k]); path = [j]
    for bk in reversed(back):
        j = bk[j]; path.append(j)
    path.reverse()
    return [float(states[k]) for k in path]

def body(q):
    C['apply_body'](q); raise_clavicles(q)

def pose(q, bd, sw):
    body(q)
    for s in 'lr':
        G, K, N = arm_target(s, q)
        C['solve_arm3'](s, q, G, K, N, bd[s], sw[s])
        fix_hand(s)
    H['tilt_bone']('neck_01', q['neck'])

DEBUG = {}
def make(name, keys):
    fk = full(keys); f0, f1 = fk[0][0], fk[-1][0]
    frames = list(range(f0, f1 + 1)); qs = [blend(fk, f) for f in frames]
    arm.animation_data.action = None; arm.location = (0, 0, 0); arm.hide_viewport = False
    bds = []; prev = None                            # pass 1: continuous elbow base directions
    for q in qs:
        body(q); cur = {}
        for s in 'lr':
            G, K, N = arm_target(s, q)
            S = P['upperarm_' + s].head.copy(); T = C['hand_head_target'](s, G, K, N)
            cur[s] = C['elbow_dir'](s, q, S, T, prev[s] if prev else None)
        bds.append(cur); prev = cur
    paths = {}                                       # pass 2: elbow swing over the whole anim
    for s in 'lr':
        costs = []
        for q, b in zip(qs, bds):
            body(q); G, K, N = arm_target(s, q); row = []
            for sw in SW_STATES:
                C['solve_arm3'](s, q, G, K, N, b[s], sw); row.append(arm_cost(s, sw))
            costs.append(row)
        paths[s] = [v[0] for v in C['smooth_path']([(v,) for v in viterbi1(costs, SW_STATES, SW_LAMBDA)])]
    DEBUG[name] = dict(frames=frames, bds=bds, paths=paths)
    poses = []
    for i, (f, q) in enumerate(zip(frames, qs)):
        pose(q, bds[i], {s: paths[s][i] for s in 'lr'})
        poses.append((f, {pb.name: pb.matrix_basis.copy() for pb in P}))
    act = bpy.data.actions.get(name)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    arm.animation_data.action = act
    for f, mats in poses:
        for pb in P: pb.matrix_basis = mats[pb.name]
        KN['key_all'](f)
    arm.location = (0, 0, 0); arm.keyframe_insert('location', frame=f0); arm.keyframe_insert('location', frame=f1)
    sc.frame_start = f0; sc.frame_end = f1
    print(name, 'quat flips fixed:', C['fix_quat_signs'](act), '| elbow swing range l',
          (round(min(paths['l'])), round(max(paths['l']))), 'r', (round(min(paths['r'])), round(max(paths['r']))))
    return act

def build_all():
    return [make(n, k) for n, k in ANIMS]

# ================================================================ checks
def set_action(name):
    act = bpy.data.actions[name]; arm.animation_data.action = act
    try: arm.animation_data.action_slot = act.slots[0]
    except Exception: pass
    return act

def check_more(names):
    """per arm: max |upper-arm twist| and its biggest per-frame jump; per leg: max |leg twist|"""
    for name in names:
        act = set_action(name); f0, f1 = map(int, act.frame_range)
        out = []
        for s in 'lr':
            mx = (0, 0); jmp = (0, 0); prev = None; lt = (0, 0)
            for f in range(f0, f1 + 1):
                sc.frame_set(f); t = shoulder_twist(s)
                if abs(t) > abs(mx[0]): mx = (round(t), f)
                if prev is not None and abs(C['_wrap'](t - prev)) > jmp[0]: jmp = (round(abs(C['_wrap'](t - prev))), f)
                prev = t
                l = abs(C['leg_twist'](s))
                if l > lt[0]: lt = (round(l, 1), f)
            out.append(f'{s}: shoulder twist {mx[0]}@f{mx[1]} jump {jmp[0]}@f{jmp[1]} | leg twist {lt[0]}@f{lt[1]}')
        print(name, ' || '.join(out))
