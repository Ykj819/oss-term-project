# Stylized tree generator (StylizedTree.blend). Same look as SM_StylizedTree:
#   trunk = bevelled bezier curve (+ branches, root flares), canopy = lumpy icospheres merged by voxel remesh + smooth
#   (soft valleys instead of hard intersections), decimated to a triangle budget, shader colours baked to vertex colours.
# Usage in Blender:  exec(open(r"<this file>").read(), g := {});  g['build'](VARIANTS['SM_StylizedTree1']) ...
# Exports Export/<name>.fbx (mesh + UCX_<name>_00 trunk collision). Import with Tools/import_stylized_tree.py.
import bpy, bmesh, math, random, os
from mathutils import Vector, noise

ROOT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject"
BARK = bpy.data.materials['M_Tree_Bark']
LEAF = bpy.data.materials['M_Tree_Leaves']


def _coll(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    for o in list(c.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    return c


def _trunk(name, col, v, rng):
    cu = bpy.data.curves.new(name + '_Trunk', 'CURVE'); cu.dimensions = '3D'
    cu.bevel_depth = 1.0; cu.bevel_resolution = 1; cu.resolution_u = 3; cu.use_fill_caps = True

    def spline(pts):
        sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
        for bp, p in zip(sp.bezier_points, pts):
            bp.co = Vector(p[:3]); bp.radius = p[3]; bp.handle_left_type = bp.handle_right_type = 'AUTO'

    spline(v['trunk'])
    for br in v['branches']:
        spline(br)
    r0 = v['trunk'][0][3]
    for k in range(v.get('roots', 4)):
        a = math.radians(k * 360 / v.get('roots', 4) + rng.uniform(-20, 20)); d = Vector((math.cos(a), math.sin(a), 0))
        spline([(0, 0, 0.7 * r0 / 0.55, 0.4 * r0), (*(d * r0 + Vector((0, 0, 0.1))), 0.3 * r0), (*(d * r0 * 1.9 + Vector((0, 0, -0.12))), 0.09 * r0)])
    o = bpy.data.objects.new(name + '_Trunk', cu); col.objects.link(o); cu.materials.append(BARK)
    return o


def _canopy(name, col, v, rng):
    tex = bpy.data.textures.get('T_LeafLumps') or bpy.data.textures.new('T_LeafLumps', 'CLOUDS')
    tex.noise_scale = 0.45; tex.noise_depth = 2
    bm = bmesh.new()
    for (x, y, z, r, sq) in v['clumps']:
        t = bmesh.new(); bmesh.ops.create_icosphere(t, subdivisions=4, radius=r)
        rot = Vector((rng.random(), rng.random(), rng.random()))
        from mathutils import Euler, Matrix
        M = Matrix.Translation((x, y, z)) @ Matrix.Diagonal((1, 1, sq, 1)) @ Euler(rot).to_matrix().to_4x4()
        t.transform(M)
        # lumps: displace along the normal with the same cloud texture (global coords)
        t.normal_update()
        for vert in t.verts:
            n = noise.fractal(vert.co * (1 / 0.45) + Vector(v.get('noise_offset', (0, 0, 0))), 0.5, 2.0, 2)
            vert.co += vert.normal * n * r * 0.35 * 0.5
        tm = bpy.data.meshes.new('_t'); t.to_mesh(tm); t.free(); bm.from_mesh(tm); bpy.data.meshes.remove(tm)
    me = bpy.data.meshes.new(name + '_Leaves'); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name + '_Leaves', me); col.objects.link(o); me.materials.append(LEAF)
    rm = o.modifiers.new('Remesh', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.08; rm.use_smooth_shade = True
    sm = o.modifiers.new('Soften', 'SMOOTH'); sm.factor = 0.8; sm.iterations = 12
    dc = o.modifiers.new('Decimate', 'DECIMATE'); dc.ratio = 1.0
    dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); m = ev.to_mesh()
    tris = sum(len(p.vertices) - 2 for p in m.polygons); ev.to_mesh_clear()
    dc.ratio = min(1.0, v.get('leaf_tris', 6000) / max(tris, 1))
    return o


def build(v, export=True):
    name = v['name']; rng = random.Random(v.get('seed', 1))
    col = _coll('Tree_' + name)
    trunk = _trunk(name, col, v, rng)
    leaves = _canopy(name, col, v, rng)
    dg = bpy.context.evaluated_depsgraph_get()

    bm = bmesh.new()
    for obj, mi in ((trunk, 0), (leaves, 1)):
        before = set(bm.faces)
        ev = obj.evaluated_get(dg); m = ev.to_mesh()
        t = bmesh.new(); t.from_mesh(m); t.transform(obj.matrix_world)
        tm = bpy.data.meshes.new('_t'); t.to_mesh(tm); t.free(); ev.to_mesh_clear()
        bm.from_mesh(tm); bpy.data.meshes.remove(tm)
        for f in bm.faces:
            if f not in before:
                f.material_index = mi; f.smooth = True
    bm.normal_update()

    node = lambda mat, t: next(n for n in mat.node_tree.nodes if n.type == t)
    leaf_ramp = node(LEAF, 'VALTORGB').color_ramp; bark_ramp = node(BARK, 'VALTORGB').color_ramp
    c01 = lambda x: max(0.0, min(1.0, x))
    to_srgb = lambda c: c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    lz = [vv.co.z for f in bm.faces if f.material_index == 1 for vv in f.verts]
    zlo, zhi = min(lz), max(lz)
    lay = bm.loops.layers.color.new('Col'); uv = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        for l in f.loops:
            p = l.vert.co
            if f.material_index == 0:
                c = bark_ramp.evaluate(c01(0.5 + 0.5 * noise.fractal(Vector((p.x * 18, p.y * 18, p.z * 2.4)), 0.5, 2.0, 4)))
            else:
                n = l.vert.normal
                a = c01((n.z + 0.6) / 1.6)
                b = c01((p.z - zlo) / max(zhi - zlo, 0.1))  # bottom of crown dark -> top bright
                c = leaf_ramp.evaluate(0.25 * (0.5 + 0.5 * noise.noise(p * 2.5)) + a + (b - a) * 0.55)
            l[lay] = (to_srgb(c[0]), to_srgb(c[1]), to_srgb(c[2]), 1.0)
            l[uv].uv = ((p.x + p.y) * 0.25, p.z * 0.25)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(BARK); me.materials.append(LEAF)
    sm = bpy.data.objects.new(name, me); col.objects.link(sm)

    # trunk collision: one convex cone from the ground to the first fork
    c = v['collision']  # (x, y, z_top, r_bottom, r_top)
    cb = bmesh.new(); bmesh.ops.create_cone(cb, cap_ends=True, segments=8, radius1=c[3], radius2=c[4], depth=c[2])
    bmesh.ops.translate(cb, verts=cb.verts, vec=(c[0], c[1], c[2] / 2))
    cm = bpy.data.meshes.new('UCX_' + name + '_00'); cb.to_mesh(cm); cb.free()
    ucx = bpy.data.objects.new('UCX_' + name + '_00', cm); col.objects.link(ucx); ucx.display_type = 'WIRE'

    if export:
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        sm.select_set(True); ucx.select_set(True); bpy.context.view_layer.objects.active = sm
        bpy.ops.export_scene.fbx(filepath=os.path.join(ROOT, 'Export', name + '.fbx'), use_selection=True,
                                 object_types={'MESH'}, apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE',
                                 colors_type='SRGB', use_mesh_modifiers=True, bake_anim=False, add_leaf_bones=False)
    for o in (trunk, leaves, ucx):
        o.hide_set(True); o.hide_render = True
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    return sm, tris


VARIANTS = {
    # 1: tall and slim, stacked canopy
    'SM_StylizedTree1': dict(
        name='SM_StylizedTree1', seed=11, leaf_tris=6000, noise_offset=(3, 1, 7),
        trunk=[(0, 0, -0.2, .42), (0.05, 0, 1.0, .30), (0, 0.05, 2.5, .25), (-0.05, 0, 4.0, .19), (0, 0, 5.6, .10)],
        branches=[[(0, 0.03, 3.0, .12), (0.35, 0.25, 3.5, .08), (0.55, 0.35, 3.9, .04)],
                  [(0, 0, 3.6, .11), (-0.4, -0.2, 4.0, .07), (-0.6, -0.3, 4.3, .04)]],
        clumps=[(0, 0, 6.3, 1.1, 1.15), (0.3, 0.2, 5.2, 1.25, 1.0), (-0.4, -0.2, 4.4, 1.2, 0.95),
                (0.5, -0.3, 3.8, 1.0, 0.9), (-0.25, 0.45, 3.5, 0.95, 0.9), (0, 0, 7.2, 0.75, 1.1)],
        collision=(0, 0, 3.2, 0.38, 0.22)),
    # 2: short thick trunk, wide flat umbrella canopy
    'SM_StylizedTree2': dict(
        name='SM_StylizedTree2', seed=22, leaf_tris=6500, roots=5, noise_offset=(-5, 2, 0),
        trunk=[(0, 0, -0.2, .70), (0, 0, 0.8, .50), (0.05, 0, 1.7, .42)],
        branches=[[(0, 0, 1.5, .34), (-1.2, 0.3, 2.7, .22), (-2.2, 0.4, 3.5, .10)],
                  [(0, 0, 1.5, .34), (1.1, -0.4, 2.8, .22), (2.3, -0.5, 3.4, .10)],
                  [(0, 0, 1.6, .30), (0.2, 0.9, 2.8, .19), (0.3, 1.8, 3.6, .09)],
                  [(0, 0, 1.6, .28), (-0.3, -0.9, 2.9, .18), (-0.6, -1.6, 3.6, .08)]],
        clumps=[(-2.2, 0.4, 4.0, 1.5, .65), (2.3, -0.5, 3.9, 1.5, .65), (0.3, 1.8, 4.1, 1.4, .65),
                (0, 0, 4.5, 1.7, .6), (-0.7, -1.5, 3.9, 1.35, .65), (1.2, 1.1, 4.3, 1.2, .65)],
        collision=(0, 0, 2.0, 0.62, 0.45)),
    # 3: young leaning tree, curved trunk, lopsided two-lobed canopy
    'SM_StylizedTree3': dict(
        name='SM_StylizedTree3', seed=33, leaf_tris=5000, roots=3, noise_offset=(8, -4, 2),
        trunk=[(0, 0, -0.2, .35), (0.2, 0, 1.0, .25), (0.6, 0.1, 2.2, .20), (1.2, 0.1, 3.2, .15), (1.5, 0, 3.9, .09)],
        branches=[[(0.5, 0.1, 2.0, .11), (-0.2, 0.3, 2.8, .07), (-0.6, 0.4, 3.3, .04)]],
        clumps=[(1.6, 0, 4.5, 1.3, .85), (2.3, 0.3, 4.0, 0.9, .85), (0.9, -0.4, 4.3, 1.0, .85),
                (-0.6, 0.4, 3.6, 0.95, .85), (-0.1, 0.65, 4.0, 0.7, .85)],
        collision=(0.25, 0.05, 2.0, 0.33, 0.24)),
}
