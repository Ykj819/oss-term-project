
# Kneel helpers (one knee down, for the bonfire rest). Uses pose_helpers.py.
import bpy, math
from mathutils import Vector, Matrix
ns = {}; exec(bpy.data.texts['pose_helpers.py'].as_string(), ns)
sc = bpy.context.scene; arm = ns['arm']; P = ns['P']
W = arm.matrix_world; Wi = W.inverted()

def move_pelvis(dz, dy=0.0):
    pb = P['pelvis']; M = pb.matrix.copy()
    M.translation = M.translation + Wi.to_3x3() @ Vector((0, dy, dz))
    pb.matrix = M; bpy.context.view_layer.update()

def solve_leg(s, ankle_w, foot_rot_w, pole_w, pole_angle=0):
    """ankle (foot_s head) to ankle_w (world m), foot world rotation foot_rot_w (3x3, armature axes), knee toward pole_w"""
    pb = P['foot_'+s]
    R = foot_rot_w
    head = Wi @ Vector(ankle_w)
    tail = head + R.col[1] * arm.data.bones['foot_'+s].length
    e = bpy.data.objects.new('IKT', None); sc.collection.objects.link(e)
    e.matrix_world = W @ Matrix.Translation(tail) @ R.to_4x4()
    pl = bpy.data.objects.new('POLE', None); sc.collection.objects.link(pl)
    pl.location = Vector(pole_w)
    c = pb.constraints.new('IK'); c.target=e; c.pole_target=pl; c.chain_count=3; c.use_rotation=True; c.pole_angle=math.radians(pole_angle)
    bpy.context.view_layer.update()
    chain = [n+'_'+s for n in ('thigh','calf','foot')]
    mats = {n: P[n].matrix.copy() for n in chain}
    pb.constraints.remove(c)
    for n in chain:
        P[n].matrix = mats[n]; bpy.context.view_layer.update()
    err = (W @ pb.head - Vector(ankle_w)).length
    bpy.data.objects.remove(e); bpy.data.objects.remove(pl)
    return err, W @ P['calf_'+s].head

def foot_rot(s, base_rot, pitch_deg=0.0):
    """base foot rotation (armature 3x3) pitched about X (positive = toes down)"""
    return Matrix.Rotation(math.radians(pitch_deg), 3, 'X') @ base_rot

def key_all(f):
    for pb in P:
        pb.keyframe_insert('location', frame=f); pb.keyframe_insert('rotation_quaternion', frame=f); pb.keyframe_insert('scale', frame=f)
