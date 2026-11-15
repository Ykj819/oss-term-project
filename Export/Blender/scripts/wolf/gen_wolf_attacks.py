
# Wolf attacks / moves. Builds on gen_wolf_anims.py (same IK feet + FK body + bake). Meters, faces -Y, left = +X.
# Player reference: 1.8m tall -> claws sweep ~1.2m high, bite ~1.35m high, all hits land ~3.5m in front of the wolf's start position.
import bpy, math
from mathutils import Vector, Matrix
G = {}; exec(bpy.data.texts['gen_wolf_anims.py'].as_string(), G)
H = G['H']; arm = G['arm']; ad = G['ad']; P = G['P']; LEGS = G['LEGS']; C0 = G['C0']; sc = G['sc']
smooth = G['smooth']; root_matrix = G['root_matrix']; UNIT = H['UNIT']; WS = H['WS']; fk = G['fk']; FK_BONES = G['FK_BONES']

def L(W, v):            # root-local meters -> world meters
    return W @ (Vector(v) * UNIT)
def rest_world(W, leg): return W @ C0[leg]
def lerp_path(keys, f):
    """keys: [(frame, Vector)] -> smooth interpolation"""
    if f <= keys[0][0]: return Vector(keys[0][1])
    for (f0, a), (f1, b) in zip(keys, keys[1:]):
        if f0 <= f <= f1: return Vector(a).lerp(Vector(b), smooth((f - f0) / (f1 - f0)))
    return Vector(keys[-1][1])
def lerp_val(keys, f):
    if f <= keys[0][0]: return keys[0][1]
    for (f0, a), (f1, b) in zip(keys, keys[1:]):
        if f0 <= f <= f1: return a + (b - a) * smooth((f - f0) / (f1 - f0))
    return keys[-1][1]
def step(a, b, f, s, e, h):
    """planted at a before s, at b after e, arc of height h between (world meters)"""
    if f <= s: return a, 0.0
    if f >= e: return b, 0.0
    u = (f - s) / (e - s)
    return a.lerp(b, smooth(u)), h * math.sin(math.pi * u)

def build2(name, f0, f1, root_fn, feet_fn, body_fn, head_fn=None):
    """feet_fn(leg, f, W) -> (contact_m, lift_m) or (contact_m, lift_m, upper_m); head_fn(f, W) -> (snout target m, influence)"""
    H['setup_ik']()
    tgt = bpy.data.objects.get('IK_HEAD') or bpy.data.objects.new('IK_HEAD', None)
    if tgt.name not in sc.collection.objects: sc.collection.objects.link(tgt)
    for c in list(P['head'].constraints): P['head'].constraints.remove(c)
    hc = P['head'].constraints.new('IK'); hc.target = tgt; hc.chain_count = 3; hc.influence = 0.0
    arm.animation_data_create()
    old = bpy.data.actions.get(name)
    if old: bpy.data.actions.remove(old)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    arm.animation_data.action = act
    for pb in P: pb.rotation_mode = 'QUATERNION'
    for f in range(f0, f1 + 1):
        loc, yaw = root_fn(f); W = root_matrix(loc, yaw)
        arm.location = loc * WS; arm.rotation_euler = (0, 0, math.radians(yaw))
        arm.keyframe_insert('location', frame=f); arm.keyframe_insert('rotation_euler', frame=f)
        fk(body_fn(f))
        for bn in FK_BONES:
            P[bn].keyframe_insert('location', frame=f); P[bn].keyframe_insert('rotation_quaternion', frame=f)
        for leg in LEGS:
            r = feet_fn(leg, f, W)
            H['place_leg'](leg, r[0], W, r[1])
            if len(r) > 2 and r[2] is not None:
                bpy.data.objects['IK_' + leg + '_upper'].location = Vector(r[2]) * WS
            for s in ('_upper', '_contact'):
                bpy.data.objects['IK_' + leg + s].keyframe_insert('location', frame=f)
        if head_fn:
            t, inf = head_fn(f, W)
            tgt.location = t * WS; tgt.keyframe_insert('location', frame=f)
            hc.influence = inf; hc.keyframe_insert('influence', frame=f)
    sc.frame_start, sc.frame_end = f0, f1
    for o in bpy.context.view_layer.objects: o.select_set(False)
    arm.select_set(True); bpy.context.view_layer.objects.active = arm
    with bpy.context.temp_override(active_object=arm, object=arm, selected_objects=[arm]):
        bpy.ops.object.mode_set(mode='POSE'); bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.nla.bake(frame_start=f0, frame_end=f1, only_selected=False, visual_keying=True, clear_constraints=False, use_current_action=True, bake_types={'POSE'})
        bpy.ops.object.mode_set(mode='OBJECT')
    for c in list(P['head'].constraints): P['head'].constraints.remove(c)
    # constraint influence keys live in the action too: drop them
    for fc in [fc for fc in G['action_fcurves'](act) if 'constraints' in fc.data_path]:
        G['remove_fcurve'](act, fc)
    for o in [o for o in bpy.data.objects if o.name.startswith('IK_')]:
        if o.animation_data: o.animation_data_clear()
    if tgt.animation_data: tgt.animation_data_clear()
    H['remove_ik']()
    bpy.data.objects.remove(tgt)
    for a in list(bpy.data.actions):
        if a.name.startswith('IK_') and a.users == 0: bpy.data.actions.remove(a)
    return act

# ---------- claw swipe (root step forward 0.6m) ----------
def claw(side):                     # 'R' = right paw (swipes right -> left), 'L' = mirror
    m = -1 if side == 'R' else 1    # x sign of the attacking side
    leg = 'F' + side; other_front = 'FL' if side == 'R' else 'FR'
    END = 66
    def root_fn(f): return Vector((0, -0.6 * smooth((f - 6) / 20), 0)), 0.0
    W0 = root_matrix(Vector(), 0); W1 = root_matrix(Vector((0, -0.6, 0)), 0)
    # paw path in root-local meters (claws sweep across ~1.2m high, ~2.9m in front -> ~3.5m from the start)
    path = [(1, None), (16, (m * 1.0, -1.15, 2.5)), (20, (m * 0.55, -2.2, 1.7)), (23, (m * 0.1, -2.9, 1.25)),
            (27, (-m * 0.55, -2.6, 1.05)), (33, (-m * 0.35, -2.0, 0.7)), (46, None)]
    def feet_fn(lg, f, W):
        if lg == leg:
            if f <= 2 or f >= 46:
                # on the ground: start / end rest spots, stepping up from / down to them
                return (rest_world(W0, lg) if f <= 2 else rest_world(W1, lg)), 0.0
            if f < 16:   # lift to the wind-up
                u = smooth((f - 2) / 14); a = rest_world(W0, lg); b = L(W, path[1][1])
                c = a.lerp(b, u)
            elif f <= 33:
                c = L(W, lerp_path([(k, v) for k, v in path[1:-1]], f))
            else:        # put it back down
                u = smooth((f - 33) / 13); a = L(W, path[-2][1]); b = rest_world(W1, lg)
                c = a.lerp(b, u) + Vector((0, 0, 0.25 * math.sin(math.pi * u)))
            upper = c + W.to_3x3() @ (Vector((0, 0.18, 0.19)) * UNIT)    # wrist behind / above the paw: claws lead
            return c, 0.0, upper
        if lg == other_front:
            return step(rest_world(W0, lg), rest_world(W1, lg), f, 38, 54, 0.3)
        s = 12 if lg[1] == side else 18
        return step(rest_world(W0, lg), rest_world(W1, lg), f, s, s + 14, 0.3)
    def body_fn(f):
        sw = lerp_val([(1, 0), (16, -1), (23, 0.2), (30, 1), (50, 0)], f)          # -1 wound up, +1 follow-through
        low = lerp_val([(1, 0), (16, 0.4), (24, 1), (40, 0.6), (64, 0)], f)
        return {'pelvis': {'loc': Vector((-m * 0.12 * low, 0, -0.25 * low))},
                'spine_02': {'yaw': m * 8 * sw}, 'spine_03': {'yaw': m * 10 * sw, 'pitch': 8 * low},
                'neck_01': {'yaw': -m * 12 * sw, 'pitch': 6 * low}, 'head': {'yaw': -m * 6 * sw},
                'jaw': {'pitch': 12 * low}, 'ear_l': {'pitch': -25 * low}, 'ear_r': {'pitch': -25 * low},
                'tail_01': {'yaw': -m * 10 * sw, 'pitch': 8 * low}, 'tail_03': {'yaw': -m * 12 * sw}}
    return build2('Wolf_Claw_' + ('Right' if side == 'R' else 'Left'), 1, END, root_fn, feet_fn, body_fn)

# ---------- bite (lunge 1.0m, head down to ~1.35m) ----------
def bite():
    END = 76
    def root_fn(f): return Vector((0, lerp_val([(1, 0), (14, 0.15), (28, -1.0)], f), 0)), 0.0
    W0 = root_matrix(Vector(), 0); W1 = root_matrix(Vector((0, -1.0, 0)), 0)
    def feet_fn(lg, f, W):
        s = {'FL': 18, 'FR': 21, 'HL': 26, 'HR': 30}[lg]
        return step(rest_world(W0, lg), rest_world(W1, lg), f, s, s + 14, 0.35)
    def head_fn(f, W):
        t = L(W, lerp_path([(14, (0, -2.05, 2.2)), (22, (0, -2.3, 1.7)), (27, (0, -2.45, 1.35)), (36, (0, -2.4, 1.45)), (50, (0, -2.4, 2.0))], f))
        return t, lerp_val([(10, 0.0), (20, 1.0), (36, 1.0), (54, 0.0)], f)
    def body_fn(f):
        coil = lerp_val([(1, 0), (14, 1), (22, 0)], f)
        lunge = lerp_val([(14, 0), (26, 1), (40, 0.8), (70, 0)], f)
        jaw = lerp_val([(1, 0), (12, 10), (22, 38), (26, 40), (29, 0), (40, 6), (60, 0)], f)
        return {'pelvis': {'loc': Vector((0, 0.15 * coil, -0.3 * coil - 0.3 * lunge))},
                'spine_01': {'pitch': -4 * coil}, 'spine_03': {'pitch': 12 * lunge - 4 * coil},
                'neck_01': {'pitch': -18 * coil}, 'head': {'pitch': 10 * coil},
                'jaw': {'pitch': jaw}, 'ear_l': {'pitch': -40 * max(coil, lunge)}, 'ear_r': {'pitch': -40 * max(coil, lunge)},
                'tail_01': {'pitch': 10 * lunge - 6 * coil}}
    return build2('Wolf_Bite', 1, END, root_fn, feet_fn, body_fn, head_fn)

# ---------- jump back (4m, root motion; height in the pelvis) ----------
def jump_back():
    END = 72; T0, T1 = 14, 36
    def ry(f): return 4.0 * smooth((f - T0) / (T1 - T0))
    def arc(f): return 0.9 * math.sin(math.pi * min(max((f - T0) / (T1 - T0), 0), 1))
    def root_fn(f): return Vector((0, ry(f), 0)), 0.0
    W0 = root_matrix(Vector(), 0); W1 = root_matrix(Vector((0, 4.0, 0)), 0)
    TUCK = {'FL': (0, 0.25), 'FR': (0, 0.25), 'HL': (0, -0.35), 'HR': (0, -0.35)}
    def feet_fn(lg, f, W):
        lead = 2 if lg[0] == 'F' else 0                 # front feet leave a bit later, land a bit later
        if f <= T0 + lead: return rest_world(W0, lg), 0.0
        if f >= T1 + lead: return rest_world(W1, lg), 0.0
        u = (f - T0 - lead) / (T1 - T0); tk = math.sin(math.pi * u)
        c = rest_world(W, lg) + Vector((0, TUCK[lg][1] * tk, 0))
        return c, max(arc(f) - 0.15, 0.0) * 0.9 + 0.15 * tk
    def body_fn(f):
        crouch = lerp_val([(1, 0), (12, 1), (16, 0.2), (T1, 0.2), (T1 + 6, 1.1), (60, 0)], f)
        return {'pelvis': {'loc': Vector((0, 0, arc(f) - 0.4 * crouch))},
                'spine_03': {'pitch': -6 * crouch}, 'neck_01': {'pitch': -10 * arc(f) / 0.9 + 6 * crouch},
                'ear_l': {'pitch': -35 * min(1, crouch + arc(f))}, 'ear_r': {'pitch': -35 * min(1, crouch + arc(f))},
                'tail_01': {'pitch': -15 * arc(f) / 0.9}, 'tail_03': {'pitch': -8 * arc(f) / 0.9}}
    return G['build']('Wolf_Jump_Back', 1, END, root_fn, feet_fn, body_fn)

# ---------- walk forward (in place, 48-frame loop, 2 m/s) ----------
def walk_forward():
    N = 48; STRIDE = 1.6; a = STRIDE / 2; st = 0.62; h = 0.35
    PH = {'HL': 0.0, 'FL': 0.25, 'HR': 0.5, 'FR': 0.75}
    def root_fn(f): return Vector(), 0.0
    def feet_fn(lg, f, W):
        p = ((f - 1) / N + PH[lg]) % 1.0
        if p < st: y = -a + 2 * a * (p / st); lift = 0.0
        else:
            u = (p - st) / (1 - st); y = a - 2 * a * smooth(u); lift = h * math.sin(math.pi * u)
        return W @ (C0[lg] + Vector((0, y, 0)) * UNIT), lift
    def body_fn(f):
        t = (f - 1) / N * 2 * math.pi
        return {'pelvis': {'loc': Vector((0.03 * math.sin(t), 0, -0.05 + 0.05 * math.cos(2 * t)))},
                'spine_02': {'yaw': 2.5 * math.sin(t)}, 'neck_01': {'pitch': 4 + 3 * math.cos(2 * t)},
                'tail_01': {'yaw': 7 * math.sin(t + 1), 'pitch': 5}, 'tail_03': {'yaw': 9 * math.sin(t)}, 'tail_05': {'yaw': 9 * math.sin(t - 1)}}
    return G['build']('Wolf_Walk_Fwd', 1, N + 1, root_fn, feet_fn, body_fn)
