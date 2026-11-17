# Stylized stones (SM_StylizedStone1..3, 0.25-0.5 m) and rocks (SM_StylizedRock1..3, 1.3-3.2 m).
# Shape: a squashed sphere cut by random planes (flat facets, convex) -> bevelled edges (soft, chunky stylized look)
#        -> slight lumps. The unbevelled convex shape is exported as the UCX_ collision.
# Colour: cool grey, darker at the bottom/sides, lighter facets facing up, worn lighter edges, moss on top of rocks.
import bpy, bmesh, math, random
from mathutils import Vector, noise

exec(open(r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Blender\scripts\props\props_common.py",
          encoding='utf-8').read())

SPECS = [
    # name, size (x, y, z) metres, cuts, bevel (fraction of size), moss, seed
    ('SM_StylizedStone1', (0.42, 0.34, 0.22), 7, 0.10, 0.0, 1),
    ('SM_StylizedStone2', (0.30, 0.26, 0.24), 6, 0.12, 0.0, 2),
    ('SM_StylizedStone3', (0.55, 0.30, 0.16), 8, 0.09, 0.0, 3),
    ('SM_StylizedRock1', (1.6, 1.3, 1.1), 10, 0.06, 0.6, 11),
    ('SM_StylizedRock2', (3.2, 2.2, 1.5), 12, 0.05, 0.8, 12),
    ('SM_StylizedRock3', (1.4, 1.2, 2.6), 11, 0.06, 0.4, 13),   # tall standing rock
]
GREY_DARK = (0.035, 0.038, 0.045); GREY_MID = (0.13, 0.135, 0.14); GREY_LIGHT = (0.21, 0.21, 0.20)
WARM = (0.20, 0.17, 0.13); MOSS = (0.10, 0.20, 0.03); MOSS_LIGHT = (0.20, 0.36, 0.05)


def convex_rock(size, cuts, rng):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=0.5)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    for k in range(cuts):
        # plane normal: random, more often sideways/up; offset: how deep the cut goes
        n = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.3, 1))).normalized()
        ext = 0.5 * Vector((abs(n.x) * size[0], abs(n.y) * size[1], abs(n.z) * size[2])).length
        d = ext * rng.uniform(0.62, 0.85)
        geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=n * d, plane_no=n, clear_outer=True)
        bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    # flat bottom slightly below ground so it sits embedded
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, -size[2] * 0.32), plane_no=(0, 0, -1), clear_outer=True)
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    bmesh.ops.convex_hull(bm, input=bm.verts)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(2), verts=bm.verts, edges=bm.edges)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(2), verts=bm.verts, edges=bm.edges)
    # move so the bottom sits 8% of the height below z = 0
    zmin = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= zmin + size[2] * 0.08
    return bm


def build(spec):
    name, size, cuts, bev, moss, seed = spec
    rng = random.Random(seed)
    hull = convex_rock(size, cuts, rng)
    # collision copy (convex, few faces)
    cm = bpy.data.meshes.new('UCX_' + name + '_00'); hull.to_mesh(cm)
    # soft edges without bevel artefacts: voxel remesh of the faceted hull, smooth (rounds the edges, keeps the
    # facets), then decimate to the budget
    hm = bpy.data.meshes.new('_rock_tmp'); hull.to_mesh(hm); hull.free()
    tmp = bpy.data.objects.new('_rock_tmp', hm); bpy.context.scene.collection.objects.link(tmp)
    rm = tmp.modifiers.new('r', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = min(size) * 0.035
    sm = tmp.modifiers.new('s', 'SMOOTH'); sm.factor = 0.8; sm.iterations = int(4 + bev * 60)
    dc = tmp.modifiers.new('d', 'DECIMATE'); dc.ratio = 1.0
    dg = bpy.context.evaluated_depsgraph_get(); ev = tmp.evaluated_get(dg); n_tri = len(ev.to_mesh().polygons) * 2
    ev.to_mesh_clear()
    dc.ratio = min(1.0, 3500 / max(n_tri, 1))
    dg = bpy.context.evaluated_depsgraph_get(); ev = tmp.evaluated_get(dg)
    bm = bmesh.new(); bm.from_mesh(ev.to_mesh()); ev.to_mesh_clear()
    bpy.data.objects.remove(tmp, do_unlink=True); bpy.data.meshes.remove(hm)
    bm.normal_update()
    off = Vector((seed * 3.1, seed * 1.7, seed * 0.9))
    for v in bm.verts:
        v.co += v.normal * noise.noise(v.co * (3.0 / max(size)) + off) * min(size) * 0.025
    bm.normal_update()

    B = Builder(); B.bm.free(); B.bm = bm
    B.col = bm.loops.layers.color.new('Col'); B.uv = bm.loops.layers.uv.new('UVMap')
    zmax = max(v.co.z for v in bm.verts); zmin = min(v.co.z for v in bm.verts)
    for f in bm.faces:
        f.smooth = True; f.material_index = 0
        fn = f.normal
        for l in f.loops:
            p = l.vert.co; n = l.vert.normal
            h = c01((p.z - zmin) / max(zmax - zmin, 1e-3))
            up = c01(n.z * 0.5 + 0.5)
            # convex edges (vertex normal deviates from the face normal) -> worn, lighter
            edge = c01((1.0 - n.dot(fn)) * 6.0)
            nz = noise.noise(p * (6.0 / max(size)) + off)
            c = mix(GREY_DARK, GREY_MID, c01(0.25 + 0.75 * h))
            c = mix(c, GREY_LIGHT, c01(up * 0.65 - 0.25 + 0.15 * nz))
            c = mix(c, WARM, c01(0.5 + 1.2 * noise.noise(p * (1.5 / max(size)) + off * 2)) * 0.25)
            c = mix(c, GREY_LIGHT, edge * 0.22)
            if moss:
                m = c01((n.z - 0.35) * 3.0) * c01(0.55 + 1.4 * noise.noise(p * (2.2 / max(size)) - off)) * moss
                c = mix(c, mix(MOSS, MOSS_LIGHT, c01(h)), m)
            l[B.col] = (lin2srgb(c[0]), lin2srgb(c[1]), lin2srgb(c[2]), 1.0)
            l[B.uv].uv = (p.x + p.y, p.z)
    ob = B.finish(name, [material('M_Stylized_Prop', False)], collection='Rocks')
    ucx = bpy.data.objects.get('UCX_' + name + '_00')
    if ucx:
        bpy.data.objects.remove(ucx, do_unlink=True)
    ucx = bpy.data.objects.new('UCX_' + name + '_00', cm); ob.users_collection[0].objects.link(ucx)
    ucx.display_type = 'WIRE'
    return ob, ucx


def build_all(do_export=True):
    out = []
    for i, spec in enumerate(SPECS):
        ob, ucx = build(spec)
        tris = export(ob, [ucx]) if do_export else sum(len(p.vertices) - 2 for p in ob.data.polygons)
        ob.location = ((i % 3) * 4.5 - 4.5, (i // 3) * 5.0 - 2.5, 0)
        ucx.location = ob.location
        out.append((ob.name, tris, tuple(round(d, 2) for d in ob.dimensions)))
    return out
