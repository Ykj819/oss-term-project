# Plush enemies on the UE mannequin skeleton (2026-11-23):
#   SKM_PlushBear  (EnemyCharacter / EnemyRanged / EnemyShield, ~1500 tris, light brown, black eyes + round ears)
#   SKM_PlushBunny (EnemyClub, ~2000 tris, white, black eyes + long ears)
# Headless:  blender -b --factory-startup --python <this file> [-- --no-export]
#   (imports Export/Reference/SKM_Manny_Simple.fbx WITH leaf bones for the exact reference pose - PlayerKnight.blend's rig
#    lacks head / ball_*, Club.blend's rest pose is an anim pose; saves Export/Blender/PlushEnemies.blend)
# Body = metaballs along the bones (smooth joints, no seams), converted + decimated, bone-heat weights on the main
# deform bones only (no fingers: mitten hands). Eyes are separate black spheres, rigid on the head.
# Vertex colour RGB = albedo (sRGB), A = gloss (eyes 1) -> UE material M_PlushEnemy (param "Paint Tint" multiplies it).
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix, Quaternion

ROOT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject"
OUT_BLEND = os.path.join(ROOT, r"Export\Blender\PlushEnemies.blend")
CMP = os.path.join(ROOT, r"Export\Blender\compare")
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
V = Vector
REF = os.path.join(ROOT, r"Export\Reference\SKM_Manny_Simple.fbx")
if 'root' not in bpy.data.objects:
    # exact mannequin reference pose WITH the leaf bones (head, ball_*): import the reference FBX into an empty scene
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=REF, ignore_leaf_bones=False, automatic_bone_orientation=False)
    for o in [o for o in bpy.data.objects if o.type == 'MESH']:
        bpy.data.objects.remove(o, do_unlink=True)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
arm.name = 'root'
if arm.animation_data:
    arm.animation_data.action = None
DEFORM = ['pelvis', 'spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05', 'neck_01', 'neck_02', 'HEAD',
          'clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l', 'thigh_l', 'calf_l', 'foot_l', 'ball_l',
          'clavicle_r', 'upperarm_r', 'lowerarm_r', 'hand_r', 'thigh_r', 'calf_r', 'foot_r', 'ball_r']
HEAD = next(b.name for b in arm.data.bones if b.parent and b.parent.name == 'neck_02' and 'head' in b.name.lower())
DEFORM[DEFORM.index('HEAD')] = HEAD


def bw(n, tail=False):
    b = arm.data.bones[n]
    return arm.matrix_world @ (b.tail_local if tail else b.head_local)


def lin2srgb(c):
    return tuple(((1.055 * x ** (1 / 2.4) - 0.055) if x > 0.0031308 else 12.92 * x) for x in c)


# ---------------------------------------------------------------- metaball helpers
_K = [None]


def radius_factor():
    """visible radius / element radius for a lone ball (default stiffness, threshold)"""
    if _K[0]:
        return _K[0]
    mb = bpy.data.metaballs.new('MBCal'); mb.resolution = 0.01
    e = mb.elements.new(); e.radius = 1.0
    ob = bpy.data.objects.new('MBCal', mb); bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    _K[0] = max(v.co.x for v in me.vertices)
    bpy.data.objects.remove(ob); bpy.data.metaballs.remove(mb); bpy.data.meshes.remove(me)
    return _K[0]


class Blob:
    def __init__(self, name, res=0.018):
        self.mb = bpy.data.metaballs.new(name + '_MB'); self.mb.resolution = res; self.mb.render_resolution = res
        self.ob = bpy.data.objects.new(name + '_MB', self.mb); bpy.context.scene.collection.objects.link(self.ob)
        self.k = radius_factor()

    def ball(self, c, r, stiff=2.0):
        e = self.mb.elements.new(); e.type = 'BALL'; e.co = c; e.radius = r / self.k; e.stiffness = stiff

    def ellipsoid(self, c, radii, up=None, stiff=2.0):
        """radii along local x, y, z; up = direction the local Z axis points to"""
        e = self.mb.elements.new(); e.type = 'ELLIPSOID'; e.co = c; e.stiffness = stiff
        r = max(radii); e.radius = r / self.k
        e.size_x, e.size_y, e.size_z = (radii[0] / r, radii[1] / r, radii[2] / r)
        if up is not None:
            e.rotation = V((0, 0, 1)).rotation_difference(V(up).normalized())

    def tube(self, a, b, r0, r1, step=0.45, stiff=2.0):
        """chain of balls from a to b, radius r0 -> r1 (tapered capsule)"""
        a, b = V(a), V(b); L = (b - a).length
        n = max(2, int(L / (min(r0, r1) * step)) + 1)
        for i in range(n):
            t = i / (n - 1)
            self.ball(a.lerp(b, t), r0 + (r1 - r0) * t, stiff)

    def to_mesh(self, name):
        bpy.context.view_layer.update()
        me = bpy.data.meshes.new_from_object(self.ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        me.name = name
        bpy.data.objects.remove(self.ob); bpy.data.metaballs.remove(self.mb)
        return me


# ---------------------------------------------------------------- body plans (world metres, faces -Y, left = +X)
def limbs(B, s, arm_r, hand_r, thigh_r, calf_r, foot):
    sx = 1 if s == 'l' else -1
    sh = bw('upperarm_' + s); el = bw('lowerarm_' + s); wr = bw('hand_' + s); mid = bw('middle_01_' + s)
    B.tube(sh + V((-sx * 0.03, 0, 0.0)), el, arm_r, arm_r * 0.9)
    B.tube(el, wr, arm_r * 0.9, arm_r * 0.82)
    B.ball(wr.lerp(mid, 0.45), hand_r)                       # mitten
    hip = bw('thigh_' + s); kn = bw('calf_' + s); an = bw('foot_' + s); toe = bw('ball_' + s)
    B.tube(hip + V((0, 0, 0.04)), kn, thigh_r, thigh_r * 0.88)
    B.tube(kn, an + V((0, 0, 0.02)), thigh_r * 0.88, calf_r)
    c = an.lerp(toe, 0.45); c.z = foot[2] * 0.95
    B.ellipsoid(c, foot)


def bear_plan():
    B = Blob('PlushBear')
    hd = bw(HEAD)
    B.ellipsoid(V((0, -0.005, 1.13)), (0.235, 0.20, 0.33))           # tummy / chest
    B.ellipsoid(V((0, 0.01, 0.93)), (0.22, 0.19, 0.16))              # round bottom
    B.ball(bw('neck_01') + V((0, -0.01, 0.03)), 0.13)                # neck (head sits on the shoulders)
    H = hd + V((0, -0.04, 0.06))
    B.ellipsoid(H, (0.20, 0.185, 0.18))                               # head
    ears = []
    for sx in (1, -1):
        c = H + V((sx * 0.145, 0.015, 0.15))
        B.ellipsoid(c, (0.068, 0.034, 0.066), up=V((sx * 0.5, 0, 1)))
        ears.append(c)
    for s in 'lr':
        limbs(B, s, 0.085, 0.085, 0.097, 0.088, (0.085, 0.13, 0.065))
    eyes = [H + V((sx * 0.075, -0.163, 0.03)) for sx in (1, -1)]
    return B, H, ears, eyes, 0.027


def bunny_plan():
    B = Blob('PlushBunny')
    hd = bw(HEAD)
    B.ellipsoid(V((0, 0.0, 1.13)), (0.215, 0.19, 0.32))
    B.ellipsoid(V((0, 0.01, 0.93)), (0.205, 0.18, 0.155))
    B.ball(bw('neck_01') + V((0, -0.01, 0.03)), 0.12)
    H = hd + V((0, -0.035, 0.06))
    B.ellipsoid(H, (0.185, 0.175, 0.175))
    B.ellipsoid(H + V((0, -0.06, -0.06)), (0.12, 0.10, 0.08))      # soft cheeks (no features)
    ears = []
    for sx in (1, -1):
        up = V((sx * 0.22, 0.12, 1.0)).normalized()
        c = H + V((sx * 0.07, 0.02, 0.13)) + up * 0.19
        B.ellipsoid(c, (0.058, 0.028, 0.20), up=up)
        ears.append(c)
    for s in 'lr':
        limbs(B, s, 0.075, 0.078, 0.09, 0.08, (0.08, 0.16, 0.06))
    eyes = [H + V((sx * 0.07, -0.157, 0.025)) for sx in (1, -1)]
    return B, H, ears, eyes, 0.025

# ---------------------------------------------------------------- mesh building
def decimate(ob, target_tris):
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    m = ob.modifiers.new('dec', 'DECIMATE'); m.ratio = min(1.0, target_tris / tris)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier='dec')


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def make_eyes(name, centers, r):
    bm = bmesh.new()
    for c in centers:
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=7, radius=r, matrix=Matrix.Translation(c))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob


def colour(ob, fn):
    me = ob.data
    if not me.color_attributes.get('Col'):
        me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    col = me.color_attributes['Col']
    for poly in me.polygons:
        for li in poly.loop_indices:
            p = me.vertices[me.loops[li].vertex_index].co
            rgb, a = fn(p)
            col.data[li].color_srgb = (*rgb, a)          # rgb given as sRGB
    me.color_attributes.active_color = col


def build(name, plan, target, body_rgb, ear_rgb, ear_inner):
    old = bpy.data.objects.get(name)
    if old:
        m = old.data; bpy.data.objects.remove(old, do_unlink=True); bpy.data.meshes.remove(m)
    B, H, ears, eye_c, eye_r = plan()
    me = B.to_mesh(name)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    eyes = make_eyes(name + '_Eyes', eye_c, eye_r)
    decimate(ob, target - tri_count(eyes))
    for p in ob.data.polygons:
        p.use_smooth = True

    # colours: body, ears slightly different on their front (inner) side; eyes black + glossy
    def body_col(p):
        for c in ears:
            if (p - c).length < ear_inner and p.y < c.y - 0.004:
                return ear_rgb, 0.0
        return body_rgb, 0.0
    colour(ob, body_col)
    colour(eyes, lambda p: ((0.012, 0.010, 0.010), 1.0))

    # weights: bone heat on the main bones only
    flags = {b.name: b.use_deform for b in arm.data.bones}
    for b in arm.data.bones:
        b.use_deform = b.name in DEFORM
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True); arm.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    for b in arm.data.bones:
        b.use_deform = flags[b.name]
    eyes.vertex_groups.new(name=HEAD).add(list(range(len(eyes.data.vertices))), 1.0, 'REPLACE')
    # join eyes into the body
    bpy.ops.object.select_all(action='DESELECT')
    eyes.select_set(True); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.join()
    # knight convention: mesh data in armature space, parent without inverse
    me = ob.data
    me.transform(arm.matrix_world.inverted() @ ob.matrix_world)
    ob.matrix_parent_inverse = Matrix.Identity(4); ob.matrix_basis = Matrix.Identity(4)
    if not any(m.type == 'ARMATURE' for m in ob.modifiers):
        mod = ob.modifiers.new('Armature', 'ARMATURE'); mod.object = arm
    bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
    if not me.uv_layers:
        me.uv_layers.new(name='UVMap')
    mat = bpy.data.materials.get('M_PlushEnemy') or bpy.data.materials.new('M_PlushEnemy')
    mat.use_nodes = True; nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    if not any(n.type == 'VERTEX_COLOR' for n in nt.nodes):
        vc = nt.nodes.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'
        nt.links.new(vc.outputs['Color'], bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = 0.9
    me.materials.clear(); me.materials.append(mat)
    unweighted = sum(1 for v in me.vertices if not v.groups)
    used = sorted({ob.vertex_groups[g.group].name for v in me.vertices for g in v.groups if g.weight > 0.05})
    print('PLUSH', name, 'tris', tri_count(ob), 'unweighted', unweighted, 'bones', used)
    return ob


# ---------------------------------------------------------------- previews: rest + a test pose, workbench vertex colours
def preview(obs):
    sc = bpy.context.scene
    cam = bpy.data.objects.get('_pl_cam') or bpy.data.objects.new('_pl_cam', bpy.data.cameras.new('_pl_cam'))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.3; sc.camera = cam
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'VERTEX'
    sc.render.resolution_x = 420; sc.render.resolution_y = 460; sc.render.film_transparent = False
    for o in bpy.data.objects:
        o.hide_render = o.type == 'MESH' and o not in obs
    arm.hide_render = True
    outs = []
    pose = {'upperarm_l': ('X', -50), 'upperarm_r': ('Z', 60), 'lowerarm_r': ('Z', 50), 'thigh_l': ('Z', 45),
            'calf_l': ('Z', -60), 'spine_03': ('X', 15), HEAD: ('Z', 25)}
    for posed in (False, True):
        for pb in arm.pose.bones:
            pb.matrix_basis = Matrix.Identity(4)
        if posed:
            for n, (ax, d) in pose.items():
                pb = arm.pose.bones[n]; pb.rotation_mode = 'XYZ'
                setattr(pb.rotation_euler, 'xyz'['XYZ'.index(ax)], math.radians(d))
        bpy.context.view_layer.update()
        for o in obs:
            for o2 in obs:
                o2.hide_render = o2 is not o
            for view, d in (('front', V((0.25, -1, 0.15))), ('side', V((1, -0.1, 0.1)))):
                d = d.normalized(); cam.location = V((0, 0, 1.0)) + d * 6
                cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
                p = os.path.join(CMP, f'plush_{o.name}_{view}{"_posed" if posed else ""}.png')
                sc.render.filepath = p; bpy.ops.render.render(write_still=True); outs.append(p)
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.data.objects.remove(cam)
    return outs


def run():
    for n in ('SKM_PlayerKnight', '_cmp_cam', '_cmp_sun'):
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)
    arm.hide_viewport = False; arm.hide_set(False)
    bear = build('SKM_PlushBear', bear_plan, 1500, (0.80, 0.60, 0.40), (0.62, 0.42, 0.26), 0.05)
    bunny = build('SKM_PlushBunny', bunny_plan, 2000, (0.96, 0.95, 0.93), (0.96, 0.78, 0.80), 0.17)
    os.makedirs(CMP, exist_ok=True)
    print('PLUSH previews', preview([bear, bunny]))
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    if '--no-export' not in args:
        for ob in (bear, bunny):
            bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); ob.select_set(True)
            bpy.context.view_layer.objects.active = arm
            fbx = os.path.join(ROOT, 'Export', ob.name + '.fbx')
            bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={'ARMATURE', 'MESH'},
                                     apply_scale_options='FBX_SCALE_UNITS', add_leaf_bones=False, bake_anim=False,
                                     mesh_smooth_type='FACE', colors_type='SRGB', use_armature_deform_only=False)
            print('PLUSH fbx', fbx, os.path.getsize(fbx))


run()
