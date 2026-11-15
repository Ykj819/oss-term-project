
import bpy, bmesh
from mathutils import Vector, Matrix
def build_skel():
    arm=bpy.data.objects['root']; W=arm.matrix_world
    me = bpy.data.meshes.get('SkelPreview') or bpy.data.meshes.new('SkelPreview')
    ob = bpy.data.objects.get('SkelPreview')
    if not ob:
        ob = bpy.data.objects.new('SkelPreview', me); bpy.context.scene.collection.objects.link(ob)
    for m in list(ob.modifiers): ob.modifiers.remove(m)
    skip=('twist','ik_','interaction','center_of_mass','weapon','metacarpal','_02','_03')
    pts={pb.name: W@pb.head for pb in arm.pose.bones}
    bm=bmesh.new()
    for pb in arm.pose.bones:
        if not pb.parent or any(k in pb.name for k in skip if k not in ('_02','_03')): continue
        if pb.name.startswith(('index','middle','ring','pinky','thumb')): continue
        a=pts[pb.parent.name]; b=pts[pb.name]; d=b-a; L=d.length
        if L<1e-4: continue
        r = 0.035 if pb.name.startswith(('thigh','calf','spine','neck','pelvis','upperarm','lowerarm','foot','ball','head')) else 0.02
        q=d.normalized().to_track_quat('Z','Y').to_matrix().to_4x4()
        M=Matrix.Translation((a+b)/2) @ q
        bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=r, radius2=r*0.8, depth=L, matrix=M)
    head=pts['head']+Vector((0,0,0.1))
    bmesh.ops.create_uvsphere(bm,u_segments=12,v_segments=8,radius=0.1,matrix=Matrix.Translation(head))
    for n in ('hand_l','hand_r'):
        bmesh.ops.create_uvsphere(bm,u_segments=8,v_segments=6,radius=0.045,matrix=Matrix.Translation((pts[n]+pts['middle_01'+n[-2:]])/2))
    bm.to_mesh(me); bm.free(); ob.hide_viewport=False
    arm.hide_viewport=True
    return ob
