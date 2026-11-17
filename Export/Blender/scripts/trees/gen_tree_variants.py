# Bare and autumn versions of the four stylized trees (StylizedTree.blend).
#   SM_StylizedBareTree[,1,2,3]   : the tree's trunk + extra branches/twigs growing into where the crown was
#   SM_StylizedAutumnTree[,1,2,3] : same tree, crown recoloured  (none = yellow, 1 = red, 2 = brown, 3 = yellow/red mix)
# Same look rules as the stylized trees: chunky tapered tubes, soft gradients baked to vertex colours (sRGB-encoded).
# Usage: g = {}; exec(open(path).read(), g); g['build_all']()
import bpy, bmesh, math, random, os
from mathutils import Vector, noise

ROOT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject"
SRC = {  # source tree -> (trunk curve, crown mesh, collision, crown clump objects or VARIANTS key)
    '': ('Tree_Trunk', 'Leaves_Merged', 'UCX_SM_StylizedTree_00'),
    '1': ('SM_StylizedTree1_Trunk', 'SM_StylizedTree1_Leaves', 'UCX_SM_StylizedTree1_00'),
    '2': ('SM_StylizedTree2_Trunk', 'SM_StylizedTree2_Leaves', 'UCX_SM_StylizedTree2_00'),
    '3': ('SM_StylizedTree3_Trunk', 'SM_StylizedTree3_Leaves', 'UCX_SM_StylizedTree3_00'),
}
AUTUMN = {  # linear colour ramps: dark (inside/bottom) -> mid -> bright (top)
    '': [(0.10, 0.045, 0.004), (0.46, 0.25, 0.01), (0.88, 0.62, 0.05)],     # yellow
    '1': [(0.07, 0.006, 0.004), (0.36, 0.025, 0.012), (0.78, 0.11, 0.03)],  # red
    '2': [(0.045, 0.02, 0.008), (0.19, 0.085, 0.028), (0.43, 0.22, 0.075)], # brown
    '3': None,                                                               # yellow / red mix
}

c01 = lambda x: max(0.0, min(1.0, x))
to_srgb = lambda c: c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def ramp3(stops, t):
    t = c01(t)
    if t < 0.55:
        a, b, f = stops[0], stops[1], t / 0.55
    else:
        a, b, f = stops[1], stops[2], (t - 0.55) / 0.45
    return tuple(x + (y - x) * f for x, y in zip(a, b))


def clumps_of(key):
    """Crown clumps (centre, radius) of a source tree."""
    if key == '':
        out = []
        for o in bpy.data.objects:
            if o.name.startswith('Leaves_') and o.name != 'Leaves_Merged' and o.type == 'MESH':
                r = max(v.co.length for v in o.data.vertices)
                out.append((o.location.copy(), r * 0.9))
        return out
    g = {}
    exec(open(os.path.join(ROOT, r"Export\Blender\scripts\trees\gen_stylized_tree.py"), encoding='utf-8').read(), g)
    v = g['VARIANTS']['SM_StylizedTree' + key]
    return [(Vector((x, y, z)), r) for (x, y, z, r, sq) in v['clumps']]


def skeleton_points(cu):
    """Sample the existing trunk/branch curves: (position, radius)."""
    pts = []
    for sp in cu.splines:
        bp = sp.bezier_points
        for i in range(len(bp) - 1):
            for k in range(6):
                t = k / 6
                p = bp[i].co.lerp(bp[i + 1].co, t); r = bp[i].radius * (1 - t) + bp[i + 1].radius * t
                pts.append((p, r))
    return pts


def add_spline(cu, pts):
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for b, (p, r) in zip(sp.bezier_points, pts):
        b.co = p; b.radius = r; b.handle_left_type = b.handle_right_type = 'AUTO'


def bare_curve(key, rng):
    src = bpy.data.objects[SRC[key][0]].data
    cu = src.copy(); cu.name = 'BareCurve' + key
    skel = [(p, r) for (p, r) in skeleton_points(src) if r > 0.06 and p.z > 1.2]
    for (c, cr) in clumps_of(key):
        for n in range(2):
            # target inside the clump, a bit up and out
            tgt = c + Vector((rng.uniform(-.6, .6), rng.uniform(-.6, .6), rng.uniform(-.1, .6))) * cr
            cand = [s for s in skel if s[0].z < tgt.z - 0.3] or skel
            base, br = min(cand, key=lambda s: (s[0] - tgt).length)
            # chunky stylized limbs: thick, short taper, rounded (capped) ends — no thin spiky twigs
            r0 = max(0.07, min(0.15, br * 0.8))
            mid = base.lerp(tgt, 0.5) + Vector((0, 0, 0.1 * (tgt - base).length))
            add_spline(cu, [(base, r0), (mid, r0 * 0.75), (tgt, r0 * 0.5)])
            # one stubby side branch
            st = mid.lerp(tgt, rng.uniform(0.2, 0.6))
            d = (tgt - base).normalized()
            side = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.3, 1))).normalized()
            tip = st + (d * 0.4 + side * 0.6).normalized() * rng.uniform(0.3, 0.5) * cr
            add_spline(cu, [(st, r0 * 0.55), (st.lerp(tip, 0.5), r0 * 0.45), (tip, r0 * 0.35)])
    cu.bevel_resolution = 1; cu.resolution_u = 3
    return cu


def eval_mesh(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg); m = ev.to_mesh()
    bm = bmesh.new(); bm.from_mesh(m); bm.transform(obj.matrix_world); ev.to_mesh_clear()
    return bm


def bark_colour(p):
    bark = bpy.data.materials['M_Tree_Bark']
    rmp = next(n for n in bark.node_tree.nodes if n.type == 'VALTORGB').color_ramp
    return rmp.evaluate(c01(0.5 + 0.5 * noise.fractal(Vector((p.x * 18, p.y * 18, p.z * 2.4)), 0.5, 2.0, 4)))[:3]


def make_mesh(name, parts, leaf_palette=None, mixed=False):
    """parts: list of (bmesh, material_index). Bakes colours, returns the object."""
    bm = bmesh.new()
    for (src, mi) in parts:
        tm = bpy.data.meshes.new('_t'); src.to_mesh(tm); src.free()
        before = set(bm.faces); bm.from_mesh(tm); bpy.data.meshes.remove(tm)
        for f in bm.faces:
            if f not in before:
                f.material_index = mi; f.smooth = True
    bm.normal_update()
    lz = [v.co.z for f in bm.faces if f.material_index == 1 for v in f.verts] or [0, 1]
    zlo, zhi = min(lz), max(lz)
    lay = bm.loops.layers.color.new('Col'); uv = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        for l in f.loops:
            p = l.vert.co
            if f.material_index == 0:
                c = bark_colour(p)
            else:
                n = l.vert.normal
                a = c01((n.z + 0.6) / 1.6); b = c01((p.z - zlo) / max(zhi - zlo, 0.1))
                t = 0.25 * (0.5 + 0.5 * noise.noise(p * 2.5)) + a + (b - a) * 0.55
                if mixed:
                    m = c01(0.5 + 1.6 * noise.noise(p * 0.55 + Vector((3.1, 7.2, 1.3))))
                    cy = ramp3(AUTUMN[''], t); cr = ramp3(AUTUMN['1'], t)
                    c = tuple(x + (y - x) * m for x, y in zip(cy, cr))
                else:
                    c = ramp3(leaf_palette, t)
            l[lay] = (to_srgb(c[0]), to_srgb(c[1]), to_srgb(c[2]), 1.0)
            l[uv].uv = ((p.x + p.y) * 0.25, p.z * 0.25)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(bpy.data.materials['M_Tree_Bark']); me.materials.append(bpy.data.materials['M_Tree_Leaves'])
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    ob = bpy.data.objects.new(name, me)
    col = bpy.data.collections.get('TreeVariants')
    if not col:
        col = bpy.data.collections.new('TreeVariants'); bpy.context.scene.collection.children.link(col)
    col.objects.link(ob)
    return ob


def export(ob, ucx_src):
    col = ob.users_collection[0]
    uname = 'UCX_' + ob.name + '_00'
    old = bpy.data.objects.get(uname)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    src = bpy.data.objects[ucx_src]
    u = bpy.data.objects.new(uname, src.data.copy()); col.objects.link(u); u.display_type = 'WIRE'
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.hide_set(False); ob.select_set(True); u.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=os.path.join(ROOT, 'Export', ob.name + '.fbx'), use_selection=True,
                             object_types={'MESH'}, apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE',
                             colors_type='SRGB', use_mesh_modifiers=True, bake_anim=False, add_leaf_bones=False)
    u.hide_set(True); u.hide_render = True


def build_all():
    out = []
    for key in ('', '1', '2', '3'):
        rng = random.Random(100 + len(key) + (int(key) if key else 0))
        trunk_name, leaves_name, ucx = SRC[key]
        # bare tree
        cu = bare_curve(key, rng)
        tmp = bpy.data.objects.new('_bare_tmp', cu); bpy.context.scene.collection.objects.link(tmp)
        ob = make_mesh('SM_StylizedBareTree' + key, [(eval_mesh(tmp), 0)])
        bpy.data.objects.remove(tmp, do_unlink=True); bpy.data.curves.remove(cu)
        export(ob, ucx); out.append((ob.name, sum(len(p.vertices) - 2 for p in ob.data.polygons)))
        # autumn tree
        trunk = bpy.data.objects[trunk_name]; leaves = bpy.data.objects[leaves_name]
        hidden = (trunk.hide_get(), leaves.hide_get())
        trunk.hide_set(False); leaves.hide_set(False)
        ob = make_mesh('SM_StylizedAutumnTree' + key, [(eval_mesh(trunk), 0), (eval_mesh(leaves), 1)],
                       leaf_palette=AUTUMN[key], mixed=AUTUMN[key] is None)
        trunk.hide_set(hidden[0]); leaves.hide_set(hidden[1])
        export(ob, ucx); out.append((ob.name, sum(len(p.vertices) - 2 for p in ob.data.polygons)))
    return out
