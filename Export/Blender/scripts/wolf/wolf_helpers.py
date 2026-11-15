
# Wolf rig helpers: leg IK (empties) for procedural animation, then bake.
import bpy, math
from mathutils import Vector, Matrix, Quaternion
sc = bpy.context.scene
arm = bpy.data.objects['root']; ad = arm.data; P = arm.pose.bones
# armature object is scaled 0.01 (bones in cm, like the UE mannequin) so the FBX is written in cm; UNIT converts meters -> armature units
WS = 1.0 / sc.unit_settings.scale_length      # scene units per meter (scene is in cm: scale_length 0.01)
UNIT = WS / arm.scale.x                        # armature units per meter
# leg: (ik bone (chain 2), tracker bone (damped track), contact bone whose head touches the ground, pole local offset from the joint)
LEGS = {
  'FL': ('lowerarm_l', 'hand_l', 'paw_l', Vector((0, 3.0, 0.6))),
  'FR': ('lowerarm_r', 'hand_r', 'paw_r', Vector((0, 3.0, 0.6))),
  'HL': ('calf_l', 'foot_l', 'toe_l', Vector((0, -3.0, 0.3))),
  'HR': ('calf_r', 'foot_r', 'toe_r', Vector((0, -3.0, 0.3))),
}
POLE_ANGLE = {'FL': -180, 'FR': 0, 'HL': 0, 'HR': -180}

def rest_head(b): return ad.bones[b].head_local.copy()

def contact_rest(leg): return rest_head(LEGS[leg][2])          # paw / toe head (armature space)
def upper_offset(leg):                                         # wrist / hock relative to the contact point
    ik, tr, ct, _ = LEGS[leg]; return rest_head(tr) - rest_head(ct)

def empty(name, parent=None):
    e = bpy.data.objects.get(name)
    if not e:
        e = bpy.data.objects.new(name, None); sc.collection.objects.link(e); e.empty_display_size = 0.2
    e.parent = parent
    return e

def setup_ik():
    for leg, (ik, tr, ct, pole) in LEGS.items():
        tU = empty('IK_' + leg + '_upper'); tC = empty('IK_' + leg + '_contact')
        pl = empty('IK_' + leg + '_pole', arm)
        pl.location = ad.bones[ik].head_local + pole * UNIT
        for c in list(P[ik].constraints) + list(P[tr].constraints): c.id_data.pose.bones[c.id_data.pose.bones.find(ik)]
        for pb in (P[ik], P[tr]):
            for c in list(pb.constraints): pb.constraints.remove(c)
        c = P[ik].constraints.new('IK'); c.target = tU; c.pole_target = pl; c.chain_count = 2; c.pole_angle = math.radians(POLE_ANGLE[leg])
        d = P[tr].constraints.new('DAMPED_TRACK'); d.target = tC; d.track_axis = 'TRACK_Y'

def remove_ik():
    for leg, (ik, tr, ct, pole) in LEGS.items():
        for pb in (P[ik], P[tr]):
            for c in list(pb.constraints): pb.constraints.remove(c)
        for s in ('_upper', '_contact', '_pole'):
            e = bpy.data.objects.get('IK_' + leg + s)
            if e: bpy.data.objects.remove(e)

def place_leg(leg, contact_world, root_matrix, lift=0.0):
    """contact point in world METERS; root_matrix maps armature units -> world meters. The wrist/hock target follows at the rest offset"""
    up = root_matrix.to_3x3() @ upper_offset(leg)
    C = Vector(contact_world) + Vector((0, 0, lift))
    bpy.data.objects['IK_' + leg + '_contact'].location = C * WS
    bpy.data.objects['IK_' + leg + '_upper'].location = (C + up) * WS
