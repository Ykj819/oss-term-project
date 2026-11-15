
# Wolf animations: procedural feet (IK empties) + FK body, baked to bone keys. 60fps, faces -Y, left = +X.
import bpy, math
from mathutils import Vector, Matrix, Quaternion
H = {}; exec(bpy.data.texts['wolf_helpers.py'].as_string(), H)
sc = bpy.context.scene; arm = H['arm']; ad = arm.data; P = H['P']; LEGS = H['LEGS']
C0 = {leg: H['contact_rest'](leg) for leg in LEGS}

def smooth(x): x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)
UNIT = H['UNIT']
def root_matrix(loc, yaw_deg): return Matrix.Translation(loc) @ Matrix.Rotation(math.radians(yaw_deg), 4, 'Z') @ Matrix.Scale(1.0 / UNIT, 4)

def local_axis(bone, world_axis):
    return (ad.bones[bone].matrix_local.to_3x3().inverted() @ Vector(world_axis)).normalized()

def fk(pose):
    """pose: {bone: {'pitch': deg, 'yaw': deg, 'loc': armature-space Vector}} -> sets basis (rest for others), keys them"""
    for pb in P:
        if pb.name in pose or pb.name in FK_BONES:
            d = pose.get(pb.name, {})
            q = Quaternion()
            if d.get('yaw'):   q = Quaternion(local_axis(pb.name, (0, 0, 1)), math.radians(d['yaw'])) @ q
            if d.get('pitch'): q = Quaternion((0, 0, 1), math.radians(d['pitch'])) @ q     # local Z = lateral axis
            pb.rotation_quaternion = q
            pb.location = ad.bones[pb.name].matrix_local.to_3x3().inverted() @ (d['loc'] * UNIT) if 'loc' in d else Vector()   # loc given in meters
FK_BONES = ['pelvis', 'spine_01', 'spine_02', 'spine_03', 'neck_01', 'neck_02', 'head', 'jaw', 'ear_l', 'ear_r',
            'tail_01', 'tail_02', 'tail_03', 'tail_04', 'tail_05']

def build(name, f0, f1, root_fn, feet_fn, body_fn):
    """root_fn(f)->(loc, yaw); feet_fn(leg, f, W)->(contact_world, lift); body_fn(f)->fk pose dict"""
    H['setup_ik']()
    arm.animation_data_create()
    old = bpy.data.actions.get(name)
    if old: bpy.data.actions.remove(old)
    act = bpy.data.actions.new(name); act.use_fake_user = True
    arm.animation_data.action = act
    for pb in P: pb.rotation_mode = 'QUATERNION'
    for f in range(f0, f1 + 1):
        loc, yaw = root_fn(f); W = root_matrix(loc, yaw)
        arm.location = loc * H['WS']; arm.rotation_euler = (0, 0, math.radians(yaw))   # loc in meters
        arm.keyframe_insert('location', frame=f); arm.keyframe_insert('rotation_euler', frame=f)
        fk(body_fn(f))
        for bn in FK_BONES:
            P[bn].keyframe_insert('location', frame=f); P[bn].keyframe_insert('rotation_quaternion', frame=f)
        for leg in LEGS:
            c, lift = feet_fn(leg, f, W)
            H['place_leg'](leg, c, W, lift)
            for s in ('_upper', '_contact'):
                e = bpy.data.objects['IK_' + leg + s]; e.keyframe_insert('location', frame=f)
    # bake the constrained legs into bone keys (into this action)
    sc.frame_start, sc.frame_end = f0, f1
    for o in bpy.context.view_layer.objects: o.select_set(False)
    arm.select_set(True); bpy.context.view_layer.objects.active = arm
    with bpy.context.temp_override(active_object=arm, object=arm, selected_objects=[arm]):
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.nla.bake(frame_start=f0, frame_end=f1, only_selected=False, visual_keying=True, clear_constraints=False,
                         use_current_action=True, bake_types={'POSE'})
        bpy.ops.object.mode_set(mode='OBJECT')
    # empties' keys are throwaway
    for leg in LEGS:
        for s in ('_upper', '_contact'):
            e = bpy.data.objects['IK_' + leg + s]
            if e.animation_data: e.animation_data_clear()
    # constraints off again so the baked keys play as-is (setup_ik re-adds them for the next build)
    H['remove_ik']()
    return act

# ---------- strafe walk (in place) ----------
STRAFE_N = 48                     # frames per cycle (0.8s)
STRAFE_STRIDE = 0.6               # m per cycle -> 75 cm/s
STRAFE_PHASE = {'HL': 0.0, 'FL': 0.25, 'HR': 0.5, 'FR': 0.75}
def strafe(direction):            # +1 left, -1 right
    a = STRAFE_STRIDE / 2; st = 0.65; h = 0.3
    def root_fn(f): return Vector((0, 0, 0)), 0.0
    def feet_fn(leg, f, W):
        # going left: the leading (left) legs go first
        ph = STRAFE_PHASE[leg] if direction > 0 else STRAFE_PHASE[{'HL':'HR','FL':'FR','HR':'HL','FR':'FL'}[leg]]
        p = ((f - 1) / STRAFE_N + ph) % 1.0
        if p < st: x = a - 2 * a * (p / st); lift = 0.0
        else:
            u = (p - st) / (1 - st); x = -a + 2 * a * smooth(u); lift = h * math.sin(math.pi * u)
        side = 0.05 if leg.endswith('L') else -0.05
        return W @ (C0[leg] + Vector((direction * x + side, 0, 0)) * UNIT), lift
    def body_fn(f):
        t = (f - 1) / STRAFE_N * 2 * math.pi
        return {'pelvis': {'loc': Vector((direction * 0.04 * math.sin(t), 0, -0.04 + 0.03 * math.cos(2 * t)))},
                'spine_02': {'yaw': 2 * math.sin(t)},
                'neck_01': {'yaw': -direction * 6, 'pitch': 3},
                'head': {'yaw': -direction * 4},
                'tail_01': {'yaw': 6 * math.sin(t + 1), 'pitch': 4}, 'tail_03': {'yaw': 8 * math.sin(t)}, 'tail_05': {'yaw': 8 * math.sin(t - 1)}}
    name = 'Wolf_Walk_Left' if direction > 0 else 'Wolf_Walk_Right'
    return build(name, 1, STRAFE_N + 1, root_fn, feet_fn, body_fn)

# ---------- turn 45 (root motion yaw) ----------
TURN_LEN = 50
def turn(direction):              # +1 left (counter-clockwise), -1 right
    def yaw_at(f): return direction * 45 * smooth((f - 1 - 4) / (TURN_LEN - 14))
    W0 = root_matrix(Vector(), 0); W1 = root_matrix(Vector(), direction * 45)
    order = ['FL', 'HR', 'FR', 'HL'] if direction > 0 else ['FR', 'HL', 'FL', 'HR']
    windows = {leg: (2 + i * 9, 2 + i * 9 + 16) for i, leg in enumerate(order)}
    def root_fn(f): return Vector(), yaw_at(f)
    def feet_fn(leg, f, W):
        s, e = windows[leg]; u = (f - s) / (e - s)
        a = W0 @ C0[leg]; b = W1 @ C0[leg]
        if u <= 0: return a, 0.0
        if u >= 1: return b, 0.0
        return a.lerp(b, smooth(u)), 0.45 * math.sin(math.pi * u)
    def body_fn(f):
        k = math.sin(math.pi * min(max((f - 1) / (TURN_LEN - 6), 0), 1))
        return {'neck_01': {'yaw': direction * 14 * k}, 'head': {'yaw': direction * 8 * k},
                'spine_03': {'yaw': direction * 5 * k}, 'spine_01': {'yaw': -direction * 3 * k},
                'pelvis': {'loc': Vector((0, 0, -0.06 * k))},
                'tail_02': {'yaw': -direction * 10 * k}, 'tail_04': {'yaw': -direction * 8 * k}}
    name = 'Wolf_Turn_Left_45' if direction > 0 else 'Wolf_Turn_Right_45'
    return build(name, 1, TURN_LEN + 1, root_fn, feet_fn, body_fn)

# ---------- charge: long dash forward (root motion) ----------
# distance ~= TOP*(RAMP_END-18)/2/60 + TOP*(HOLD_END-RAMP_END)/60 + TOP*(STOP-HOLD_END)/2/60
CH_TOP = 7.0; CH_RAMP_END = 32; CH_HOLD_END = 76; CH_STOP = 100; CH_END = 120
def charge():
    fps = 60.0
    def speed(f):                 # m/s
        if f < 18: return 0.0
        if f < CH_RAMP_END: return CH_TOP * smooth((f - 18) / (CH_RAMP_END - 18))
        if f < CH_HOLD_END: return CH_TOP
        if f < CH_STOP: return CH_TOP * (1 - smooth((f - CH_HOLD_END) / (CH_STOP - CH_HOLD_END)))
        return 0.0
    ys = {1: 0.0}
    for f in range(2, CH_END + 2): ys[f] = ys[f - 1] - speed(f) / fps     # forward = -Y
    def root_fn(f): return Vector((0, ys[f], 0)), 0.0
    def W_at(f): return root_matrix(Vector((0, ys[min(max(f, 1), CH_END)], 0)), 0)
    # bound gait: hind pair, then front pair
    CYC = 24; OFF = {'HL': 0.0, 'HR': 0.06, 'FL': 0.5, 'FR': 0.56}; ST = 0.3
    plants = {}
    for leg in LEGS:
        pl = [(-1e9, None, W_at(1) @ C0[leg])]
        c = 18
        while c <= CH_HOLD_END + 6:
            s = c + OFF[leg] * CYC; e = s + ST * CYC
            pos = W_at(int((s + e) / 2)) @ C0[leg] + Vector((0, -0.35 * speed(int(s)) / CH_TOP, 0))
            if (pos - pl[-1][2]).length < 0.4:
                pl[-1] = (pl[-1][0], e, pl[-1][2])          # barely moved: keep standing
            else:
                pl[-1] = (pl[-1][0], max(pl[-1][1] or s - 12, (pl[-1][0] if pl[-1][0] > 0 else 0)), pl[-1][2]) if pl[-1][1] is None else pl[-1]
                pl.append((s, e, pos))
            c += CYC
        final = W_at(CH_END) @ C0[leg]
        last_end = pl[-1][1]
        pl.append((min(last_end + 14, CH_END - 8), 1e9, final))
        # fix first plant's end (lift time) = next start - swing
        if len(pl) > 1 and pl[0][1] is None: pl[0] = (pl[0][0], pl[1][0] - 12, pl[0][2])
        plants[leg] = pl
    def feet_fn(leg, f, W):
        pl = plants[leg]
        for i, (s, e, pos) in enumerate(pl):
            if s <= f <= e: return pos, 0.0
            if i + 1 < len(pl) and e < f < pl[i + 1][0]:
                n = pl[i + 1]; u = (f - e) / (n[0] - e)
                d = (n[2] - pos).length
                return pos.lerp(n[2], smooth(u)), min(0.25 + d * 0.15, 0.8) * math.sin(math.pi * u)
        return pl[-1][2], 0.0
    def body_fn(f):
        crouch = smooth((f - 1) / 17) if f < 18 else (1.0 if f < CH_STOP - 8 else 1 - smooth((f - CH_STOP + 8) / 24))
        run = speed(f) / CH_TOP
        ph = ((f - 18) / CYC) % 1.0 if 18 <= f <= CH_STOP else 0.0
        flex = math.cos(2 * math.pi * (ph - 0.4)) * run          # + extended, - gathered
        return {'pelvis': {'loc': Vector((0, 0.12 * crouch * (1 - run), -0.35 * crouch + 0.15 * run * max(0.0, math.sin(2 * math.pi * (ph - 0.3)))))},
                'spine_01': {'pitch': -6 * flex}, 'spine_02': {'pitch': -5 * flex}, 'spine_03': {'pitch': 4 * flex},
                'neck_01': {'pitch': 14 * crouch}, 'neck_02': {'pitch': 4 * crouch}, 'head': {'pitch': -10 * crouch},
                'jaw': {'pitch': 14 * crouch}, 'ear_l': {'pitch': -35 * crouch}, 'ear_r': {'pitch': -35 * crouch},
                'tail_01': {'pitch': 18 * run + 6 * flex}, 'tail_02': {'pitch': 6 * run}, 'tail_03': {'pitch': 4 * run - 5 * flex}}
    return build('Wolf_Charge', 1, CH_END, root_fn, feet_fn, body_fn)

def build_all():
    strafe(+1); strafe(-1); turn(+1); turn(-1); charge()


def action_fcurves(act):
    try:
        return list(act.fcurves)
    except AttributeError:
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags: out += list(bag.fcurves)
        return out
def remove_fcurve(act, fc):
    try:
        act.fcurves.remove(fc); return
    except AttributeError:
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    if fc in list(bag.fcurves): bag.fcurves.remove(fc); return
