
# Dive roll v2 (MM_Roll_Fwd, 2026-11-20): gather -> push off -> airborne dive -> hands plant -> chin tucked shoulder roll ->
# tucked ball over the back -> feet plant -> rise to the ready stance. 54 frames @ 60 fps (0.88 s). C++ plays the whole anim
# as the roll and pushes the capsule with RollSpeed = 500 cm/s for 85% of it (strength 1 -> 0.2 over the last 30%).
# Built on gen_club.py v4.7: analytic arm IK (solve_arm3) with continuous elbow directions, analytic leg IK (solve_leg2,
# knee over the toes), every frame keyed, quaternion signs fixed. New here:
#  - the whole body pitches about X (pelvis rotation; arm space axes = world axes);
#  - limb targets are body-local between keys (authored in world at each key, converted with that key's body transform);
#  - ground contacts (push-off feet, planted hands, landing feet) are fixed in the WORLD: in this in-place anim they slide
#    backward at the capsule's speed, so in game they stay put;
#  - the pelvis is lifted out of the ground / pulled onto it (rolling phase) by a clearance test on spine / head / shoulders;
#  - free hands keep the forearm-relative rotation of the BASE pose (no skin twist), planted hands lie palm down.
import bpy, math
from mathutils import Vector, Matrix, Quaternion
C = {}; exec(bpy.data.texts['gen_club.py'].as_string(), C)
V = Vector; arm = C['arm']; P = C['P']; sc = bpy.context.scene; H = C['H']; KN = C['KN']; BASE = C['BASE']
G = C['g']; FROT = {'l': G['FROT_L'], 'r': G['FROT_R']}; STANCE = C['STANCE']
NAME = 'MM_Roll_Fwd'; FPS = 60; F0, F1 = 1, 54
arm.animation_data.action = None; arm.location = (0, 0, 0); bpy.context.view_layer.update()   # in-place anim: root at origin
ROLL_SPEED = 5.0; MOVE_FRAC = 0.85
WRIST_MAX = 75.0
FINGERS = [n for n in (f'{a}_{i:02d}_{s}' for s in 'lr' for a in ('index', 'middle', 'ring', 'pinky', 'thumb') for i in (1, 2, 3))
           if n in P]
_Bn = arm.data.bones
BALL_OFF = {s: _Bn['foot_' + s].matrix_local.to_3x3().inverted() @ (_Bn['ball_' + s].head_local - _Bn['foot_' + s].head_local)
            for s in 'lr'}                                   # foot head -> ball, foot bone space (arm units)


def Rx(deg, n=3):
    return Matrix.Rotation(math.radians(deg), n, 'X')


def smooth(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- capsule travel (C++ DoRoll root motion source)
def _strength(u):
    return 1.0 if u < 0.7 else max(0.2, 1.0 - 0.8 * (u - 0.7) / 0.3)


def cap_disp(f):
    """metres the capsule has moved forward at frame f"""
    T = (F1 - F0) / FPS; Fd = MOVE_FRAC * T; te = (f - F0) / FPS; n = 300; d = 0.0
    for i in range(n):
        t = te * (i + 0.5) / n
        if t < Fd:
            d += ROLL_SPEED * _strength(t / Fd) * te / n
    return d


# ---------------------------------------------------------------- interpolation (cubic Hermite, Catmull-Rom tangents, eased ends)
def interp(keys, f):
    if f <= keys[0][0]: return keys[0][1]
    if f >= keys[-1][0]: return keys[-1][1]
    n = len(keys)

    def tan(j):
        if j == 0 or j == n - 1: return keys[j][1] * 0.0
        return (keys[j + 1][1] - keys[j - 1][1]) * (1.0 / (keys[j + 1][0] - keys[j - 1][0]))
    for i in range(n - 1):
        fa, a = keys[i]; fb, b = keys[i + 1]
        if fa <= f <= fb:
            h = fb - fa; t = (f - fa) / h; t2 = t * t; t3 = t2 * t
            return a * (2 * t3 - 3 * t2 + 1) + tan(i) * (h * (t3 - 2 * t2 + t)) + b * (-2 * t3 + 3 * t2) + tan(i + 1) * (h * (t3 - t2))
    return keys[-1][1]


def ramp(pts, f):
    """[(frame, value)] smoothstep"""
    if f <= pts[0][0]: return pts[0][1]
    for (a, va), (b, vb) in zip(pts, pts[1:]):
        if f <= b: return va + (vb - va) * smooth((f - a) / (b - a))
    return pts[-1][1]


# ---------------------------------------------------------------- reference stance
def measure():
    arm.animation_data.action = None; arm.location = (0, 0, 0); bpy.context.view_layer.update()
    C['apply_body'](dict(STANCE))
    pw = arm.matrix_world @ P['pelvis'].head
    return pw.y, pw.z


# ---------------------------------------------------------------- keys
def build_keys(Y0, Z0):
    w = lambda *v: ('w', V(v)); b = lambda *v: ('b', V(v))
    K = [
        dict(f=1, th=12.0, pel=(0.0, Z0 - 0.14), sp=12.0, nk=-5.0, cw=0.0,
             hl=w(0.27, 0.22, 0.78), hr=w(-0.27, 0.18, 0.80), al=w(0.13, -0.33, 0.094), ar=w(-0.13, -0.02, 0.12),
             pl=-12.0, pr=13.0, el=V((0.4, 1.0, -0.3)), er=V((-0.4, 1.0, -0.3))),
        dict(f=7, th=48.0, pel=(-0.14, Z0 + 0.02), sp=-6.0, nk=-22.0, cw=0.0,
             hl=w(0.24, -0.62, 1.22), hr=w(-0.24, -0.60, 1.20), al=w(0.13, 0.12, 0.26), ar=w(-0.13, 0.40, 0.22),
             pl=0.0, pr=10.0, el=V((1.0, 0.2, -0.3)), er=V((-1.0, 0.2, -0.3))),
        dict(f=13, th=88.0, pel=(-0.30, 0.80), sp=0.0, nk=-28.0, cw=0.0,
             hl=w(0.22, -0.98, 0.42), hr=w(-0.22, -0.96, 0.40), al=b(0.11, 0.12, -0.80), ar=b(-0.11, 0.16, -0.78),
             pl=35.0, pr=35.0, el=V((1.0, 0.1, 0.2)), er=V((-1.0, 0.1, 0.2))),
        dict(f=18, th=122.0, pel=(-0.42, 0.66), sp=18.0, nk=30.0, cw=0.0,
             hl=w(0.21, -0.86, 0.03), hr=w(-0.21, -0.86, 0.03), al=b(0.12, -0.05, -0.68), ar=b(-0.12, -0.02, -0.66),
             pl=45.0, pr=45.0, el=V((1.0, 0.4, 0.2)), er=V((-1.0, 0.4, 0.2))),
        dict(f=23, th=188.0, pel=(-0.46, 0.50), sp=45.0, nk=55.0, cw=1.0,
             hl=w(0.22, -0.55, 0.12), hr=w(-0.22, -0.55, 0.12), al=b(0.12, -0.25, -0.30), ar=b(-0.12, -0.24, -0.31),
             pl=30.0, pr=30.0, el=V((1.0, 0.3, 0.0)), er=V((-1.0, 0.3, 0.0))),
        dict(f=29, th=255.0, pel=(-0.32, 0.36), sp=50.0, nk=50.0, cw=1.0,
             hl=b(0.16, -0.36, -0.06), hr=b(-0.16, -0.36, -0.06), al=b(0.12, -0.20, -0.16), ar=b(-0.12, -0.20, -0.17),
             pl=30.0, pr=30.0, el=V((1.0, 0.2, 0.0)), er=V((-1.0, 0.2, 0.0))),
        dict(f=35, th=320.0, pel=(-0.18, 0.42), sp=38.0, nk=28.0, cw=0.0,
             hl=w(0.27, -0.82, 0.62), hr=w(-0.27, -0.80, 0.62), al=w(0.13, -0.50, 0.094), ar=w(-0.13, -0.47, 0.094),
             pl=40.0, pr=40.0, el=V((1.0, 0.4, -0.2)), er=V((-1.0, 0.4, -0.2))),
        dict(f=43, th=372.0, pel=(-0.08, Z0 - 0.30), sp=26.0, nk=2.0, cw=0.0,
             hl=w(0.27, -0.48, 0.88), hr=w(-0.27, -0.46, 0.88), al=w(0.13, -0.07, 0.094), ar=w(-0.13, -0.04, 0.094),
             pl=-12.0, pr=-12.0, el=V((0.8, 0.6, -0.2)), er=V((-0.8, 0.6, -0.2))),
        dict(f=54, th=360.0, pel=(Y0, Z0), sp=float(STANCE['spine']), nk=float(STANCE['neck']), cw=0.0,
             hl=w(0.27, -0.10, 0.86), hr=w(-0.27, -0.08, 0.86), al=w(0.13, 0.0, 0.094), ar=w(-0.13, 0.02, 0.094),
             pl=0.0, pr=0.0, el=V((0.7, 0.7, 0.0)), er=V((-0.7, 0.7, 0.0))),
    ]
    # world contacts: (on_start, on_full, off_start, off_end, anchor at on_full (root-local m), pitch keys [(f, world deg)])
    D = cap_disp
    end_l = (35, 37, 99, 99, V((0.13, -0.50, 0.094)), [(35, 0.0)])
    end_r = (35, 37, 99, 99, V((-0.13, -0.47, 0.094)), [(35, 0.0)])
    PL = {'al': [(1, 1, 6, 9, V((0.13, -0.33, 0.094)), [(1, 0.0), (7, 45.0)]), end_l],
          'ar': [(1, 1, 8, 11, V((-0.13, -0.02, 0.094)), [(1, 25.0), (9, 60.0)]), end_r],
          'hl': [(16, 18, 20, 26, V((0.21, -0.92, 0.03)), None)],
          'hr': [(16, 18, 20, 26, V((-0.21, -0.92, 0.03)), None)]}
    # landing anchors chosen so the feet end under the body when the capsule stops: shift them by the remaining travel
    for k in ('al', 'ar'):
        on0, on1, o0, o1, anc, pk = PL[k][1]
        target_end_y = {'al': 0.0, 'ar': 0.02}[k]
        anc.y = target_end_y - (D(F1) - D(on1))
    return K, PL


def to_local(key):
    """convert the key's world limb targets to body-local (relative to the pelvis, unrotated by th)"""
    Rinv = Rx(key['th']).inverted(); pel = V((0.0, key['pel'][0], key['pel'][1]))
    out = {}
    for k in ('hl', 'hr', 'al', 'ar'):
        mode, v = key[k]
        out[k] = V(v) if mode == 'b' else Rinv @ (V(v) - pel)
    return out


# ---------------------------------------------------------------- posing
W = arm.matrix_world; Wi = W.inverted(); W3 = W.to_3x3()


def pose_body(th, pel_w, sp):
    H['reset_base'](BASE)
    pb = P['pelvis']; M = Rx(th, 4) @ pb.matrix.copy(); M.translation = Wi @ pel_w
    pb.matrix = M; bpy.context.view_layer.update()
    for n in ('spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05'):
        H['tilt_bone'](n, sp / 5.0)


def plant_state(PL, k, f):
    """(weight, world target or None, world pitch) of the contact list for limb k at frame f"""
    for on0, on1, o0, o1, anc, pk in PL.get(k, []):
        if on0 <= f <= o1:
            w = 1.0 if on0 == on1 else smooth((f - on0) / (on1 - on0))
            if f > o0: w = min(w, 1.0 - smooth((f - o0) / (o1 - o0)))
            pos = anc + V((0, cap_disp(f) - cap_disp(on1), 0))
            pitch = ramp(pk, f) if pk else 0.0
            return w, pos, pitch
    return 0.0, None, 0.0


def solve_leg_h(s, ankle_w, foot_rot, hint, hw):
    """gen_club solve_leg2 (analytic, knee over the toes) + a knee hint: in the tuck the toes point along the hip->ankle
    line, so 'over the toes' is undefined there; the knee then also leans toward `hint` (arm-space dir) with weight hw"""
    r = C['REST_LEG'][s]; frame2 = C['frame2']
    S = P['thigh_' + s].head.copy()
    T = Wi @ V(ankle_w)
    dv = T - S; ax = dv.normalized(); d = min(dv.length, (r['a'] + r['b']) * 0.995); T = S + ax * d
    proj = lambda v: v - ax * v.dot(ax)
    toe = proj(foot_rot @ r['toe_local']); hh = proj(V(hint))
    pd = toe * (1.0 - hw) + (hh.normalized() if hh.length > 1e-6 else hh) * hw
    if pd.length < 1e-6: pd = toe if toe.length > 1e-6 else ax.orthogonal()
    pd.normalize()
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


def foot_target(s, pos_w, R):
    """planted foot: anchor = ankle position of the FLAT foot -> keep the ball fixed while the heel lifts"""
    R0 = FROT[s]
    ball = Wi @ pos_w + R0 @ BALL_OFF[s]
    return W @ (ball - R @ BALL_OFF[s])


def clearance():
    pts = []
    hd = (P['head'].head - P['neck_02'].head).normalized()
    pts.append((W @ (P['head'].head + hd * 8.0), 0.11))
    for n, r in (('neck_01', 0.07), ('spine_05', 0.13), ('spine_04', 0.13), ('spine_03', 0.13), ('spine_02', 0.13),
                 ('pelvis', 0.12), ('clavicle_l', 0.07), ('clavicle_r', 0.07), ('upperarm_l', 0.07), ('upperarm_r', 0.07),
                 ('thigh_l', 0.09), ('thigh_r', 0.09)):
        pts.append((W @ P[n].head, r))
    return min(p.z - r for p, r in pts)


def pose_frame(st, pel_w, prev_dirs):
    th = st['th']; Rb = Rx(th)
    pose_body(th, pel_w, st['sp'])
    # legs
    for s in 'lr':
        k = 'a' + s
        Tb = pel_w + Rb @ st[k]; Rb_foot = Rb @ Rx(st['p' + s]) @ FROT[s]
        w, pos, pw = st['plant'][k]
        if w > 0:
            Rw = Rx(pw) @ FROT[s]
            Rf = Rb_foot.to_quaternion().slerp(Rw.to_quaternion(), w).to_matrix()
            T = Tb.lerp(foot_target(s, pos, Rw), w)
        else:
            Rf = Rb_foot; T = Tb
        T.z = max(T.z, 0.085)
        solve_leg_h(s, T, Rf, Rb @ V((0, -1.0, 0.35)), min(max(st['kh'], 0.0), 1.0))
    # arms
    dirs = {}
    for s in 'lr':
        k = 'h' + s; sx = 1.0 if s == 'l' else -1.0
        Tb = pel_w + Rb @ st[k]
        w, pos, _ = st['plant'][k]
        G_ = Tb.lerp(pos, w) if w > 0 else Tb
        G_.z = max(G_.z, 0.025)
        Kw = V((-sx, 0, 0)); Nw = V((0, 0, 1))           # palm down, thumb side toward the centre
        S = P['upperarm_' + s].head
        T = C['hand_head_target'](s, G_, Kw, Nw)
        over = (T - S).length - C['REACH'] * C['ARM_LEN'][s]
        if over > 0:
            G_ = G_ - W3 @ ((T - S).normalized() * over)
        authored = Rb @ st['e' + s]
        base = authored if prev_dirs is None else (V(prev_dirs[s]) * 0.75 + authored.normalized() * 0.25)
        dirs[s] = C['solve_arm3'](s, {}, G_, Kw, Nw, base, 0.0)
        # free hand: forearm-relative BASE rotation (no skin twist); planted: palm down
        Rp = P['hand_' + s].matrix.to_3x3().to_quaternion()
        Rr = (P['lowerarm_' + s].matrix.to_3x3() @ C['BASE_REL'][s]).to_quaternion()
        tr = P['hand_' + s].matrix.translation.copy()
        we = w
        for _ in range(16):          # wrist bend <= WRIST_MAX: a planted palm may lift onto its heel instead
            M = Rr.slerp(Rp, we).to_matrix().to_4x4(); M.translation = tr
            P['hand_' + s].matrix = M; bpy.context.view_layer.update()
            if we <= 0.0 or C['wrist_swing'](s) <= WRIST_MAX: break
            we = max(0.0, we - 0.08)
        C['spread_twist'](s)
    # fingers: half relaxed, flat when planted
    hp = max(st['plant']['hl'][0], st['plant']['hr'][0])
    for n in FINGERS:
        side = n[-1]; w = st['plant']['h' + side][0]
        q = BASE[n].to_quaternion().slerp(Quaternion(), 0.4 + 0.6 * w)
        M = q.to_matrix().to_4x4(); M.translation = BASE[n].translation; P[n].matrix_basis = M
    bpy.context.view_layer.update()
    H['tilt_bone']('neck_01', st['nk'] * 0.6); H['tilt_bone']('neck_02', st['nk'] * 0.4)
    return dirs


def make_roll():
    Y0, Z0 = measure()
    keys, PL = build_keys(Y0, Z0)
    loc = [to_local(k) for k in keys]
    sk = lambda name: [(k['f'], float(k[name])) for k in keys]
    vk = lambda name: [(k['f'], V(k[name])) for k in keys]
    lk = lambda name: [(k['f'], l[name]) for k, l in zip(keys, loc)]
    KH = {1: 0.0, 7: 0.0, 13: 0.2, 18: 0.6, 23: 1.0, 29: 1.0, 35: 0.8, 43: 0.2, 54: 0.0}    # knee hint weight
    tracks = dict(th=sk('th'), sp=sk('sp'), nk=sk('nk'), cw=sk('cw'), pl=sk('pl'), pr=sk('pr'),
                  kh=[(k['f'], KH[k['f']]) for k in keys],
                  py=[(k['f'], float(k['pel'][0])) for k in keys], pz=[(k['f'], float(k['pel'][1])) for k in keys],
                  hl=lk('hl'), hr=lk('hr'), al=lk('al'), ar=lk('ar'), el=vk('el'), er=vk('er'))
    arm.animation_data.action = None; arm.location = (0, 0, 0)
    poses = []; prev = None; log = []
    for f in range(F0, F1 + 1):
        st = {n: interp(tr, f) for n, tr in tracks.items()}
        st['plant'] = {k: plant_state(PL, k, f) for k in ('al', 'ar', 'hl', 'hr')}
        cw = min(max(st['cw'], 0.0), 1.0)
        pel = V((0.0, st['py'], st['pz']))
        for it in range(4):
            pose_frame(st, pel, prev)
            c = clearance()
            if c < -0.002: pel.z -= c
            elif cw > 0 and c > 0.002: pel.z -= c * cw
            else: break
        prev = pose_frame(st, pel, prev)
        log.append((f, round(st['th'], 1), round(pel.y, 3), round(pel.z, 3), round(clearance(), 3)))
        poses.append((f, {pb.name: pb.matrix_basis.copy() for pb in P}))
    act = bpy.data.actions.get(NAME)
    if act: bpy.data.actions.remove(act)
    act = bpy.data.actions.new(NAME); act.use_fake_user = True
    arm.animation_data.action = act
    for f, mats in poses:
        for pb in P: pb.matrix_basis = mats[pb.name]
        KN['key_all'](f)
    arm.location = (0, 0, 0); arm.keyframe_insert('location', frame=F0); arm.keyframe_insert('location', frame=F1)
    sc.frame_start = F0; sc.frame_end = F1; sc.render.fps = FPS
    print(NAME, 'quat flips fixed:', C['fix_quat_signs'](act))
    return act, log


def leg_twist_max(name=NAME):
    act = bpy.data.actions[name]; arm.animation_data.action = act
    try: arm.animation_data.action_slot = act.slots[0]
    except Exception: pass
    worst = {'l': (0, 0), 'r': (0, 0)}
    for f in range(F0, F1 + 1):
        sc.frame_set(f)
        for s in 'lr':
            t = abs(C['leg_twist'](s))
            if t > worst[s][0]: worst[s] = (round(t, 1), f)
    return worst


def ground_contacts(name=NAME):
    """per frame: lowest hand / foot / body point (to verify nothing goes under the floor)"""
    act = bpy.data.actions[name]; arm.animation_data.action = act
    out = []
    for f in range(F0, F1 + 1, 3):
        sc.frame_set(f)
        hz = min((W @ P['hand_' + s].head).z for s in 'lr'); fz = min((W @ P['ball_' + s].head).z for s in 'lr')
        out.append((f, round(hz, 3), round(fz, 3), round(clearance(), 3)))
    return out
