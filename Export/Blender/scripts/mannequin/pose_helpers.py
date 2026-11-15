
# Pose helpers for the mannequin imported from Export/MM_Stick_Slash_A.fbx (armature "root", faces -Y, right = -X).
# Base pose = frame 1 of action "root|Scene" (slash A ready stance). Arms are posed with temporary IK.
import bpy, math
from mathutils import Vector, Matrix
sc = bpy.context.scene
arm = bpy.data.objects['root']; P = arm.pose.bones

def get_base():
    prev = arm.animation_data.action
    arm.animation_data.action = bpy.data.actions['root|Scene']
    sc.frame_set(1)
    b = {pb.name: pb.matrix_basis.copy() for pb in P}
    arm.animation_data.action = prev
    return b

def reset_base(base):
    for pb in P: pb.matrix_basis = base[pb.name]
    bpy.context.view_layer.update()

def frame(K, N):
    K = K.normalized(); N = (N - K*N.dot(K)).normalized()
    return Matrix((K, N, K.cross(N))).transposed()

def hand_local(s):
    """knuckle axis (pinky->index), back-of-hand normal and grip point (C++ stick grip) in hand bone space"""
    h = P['hand_'+s].matrix; inv = h.inverted()
    L = lambda n: inv @ P[n+'_'+s].head
    K = (L('index_01') - L('pinky_01')).normalized()
    F = L('middle_01').normalized()
    th = L('thumb_01'); th = th - F*th.dot(F); th = th - K*th.dot(K)
    return K, -th.normalized(), L('middle_01')*0.6

def solve_arm(s, grip_w, Kw, Nw, pole=-90, pole_pos=None):
    """put hand s's grip point at grip_w (world m), knuckle axis along Kw, back of hand toward Nw"""
    inv_w = arm.matrix_world.inverted()
    K, N, grip = hand_local(s)
    R = frame(Vector(Kw), Vector(Nw)) @ frame(K, N).transposed()
    head = (inv_w @ Vector(grip_w)) - R @ grip
    tail = head + R.col[1] * arm.data.bones['hand_'+s].length
    e = bpy.data.objects.new('IKT', None); sc.collection.objects.link(e)
    e.matrix_world = arm.matrix_world @ Matrix.Translation(tail) @ R.to_4x4()
    pl = bpy.data.objects.new('POLE', None); sc.collection.objects.link(pl)
    sx = -1 if s=='r' else 1
    pl.location = pole_pos or (arm.matrix_world @ Vector((sx*60, 20, 80)))
    c = P['hand_'+s].constraints.new('IK'); c.target=e; c.pole_target=pl; c.chain_count=3; c.use_rotation=True; c.pole_angle=math.radians(pole)
    bpy.context.view_layer.update()
    chain = [n+'_'+s for n in ('upperarm','lowerarm','hand')]
    mats = {n: P[n].matrix.copy() for n in chain}
    P['hand_'+s].constraints.remove(c)
    for n in chain:
        P[n].matrix = mats[n]; bpy.context.view_layer.update()
    err = (P['hand_'+s].head - head).length
    bpy.data.objects.remove(e); bpy.data.objects.remove(pl)
    return err, arm.matrix_world @ P['lowerarm_'+s].head

def tilt_bone(name, deg, axis='X'):
    pb = P[name]; M = pb.matrix.copy(); piv = M.translation.copy()
    pb.matrix = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-piv) @ M
    bpy.context.view_layer.update()
