# Stylized static clouds (Palworld-like puffy masses), same soft-merge pipeline as the tree crowns:
# puffs (squashed spheres, flattened bottoms) -> voxel remesh -> Smooth -> Decimate. Pivot = centre of the cloud base.
# Colour (vertex colours): bluish grey underside -> light grey sides -> white tops, light noise.
# Material slot M_Stylized_Cloud (lit, so the sun/sky tint them; unlit would look grey under the auto exposure).
#   SM_Cloud_Small      ~12 m   few puffs
#   SM_Cloud_Medium     ~25 m
#   SM_Cloud_Long       ~45 m   stretched row
#   SM_Cloud_Cumulus    ~30 m wide, ~30 m tall towering
#   SM_Cloud_HorizonBand ~160 m low wide band for the far horizon (curved slightly toward the viewer)
import bpy, bmesh, math, random
from mathutils import Vector, noise

exec(open(r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Blender\scripts\props\props_common.py",
          encoding='utf-8').read())

BOTTOM = (0.40, 0.48, 0.64); MID = (0.72, 0.77, 0.86); TOP = (0.93, 0.94, 0.95)

# name: (seed, length m, depth m, height m, puffs, puff radius range (fraction of height), tris, arc)
VARIANTS = {
    'SM_Cloud_Small':       (3, 12, 7, 5, 6, (0.45, 0.8), 2000, 0.0),
    'SM_Cloud_Medium':      (7, 25, 13, 9, 11, (0.4, 0.75), 3000, 0.0),
    'SM_Cloud_Long':        (11, 45, 11, 7, 16, (0.4, 0.8), 3500, 0.0),
    'SM_Cloud_Cumulus':     (19, 20, 18, 28, 24, (0.25, 0.45), 5000, 0.0),
    'SM_Cloud_HorizonBand': (23, 160, 18, 12, 38, (0.45, 0.9), 6000, 0.08),
}


def build(name, do_export=True):
    seed, L, D, H, n, rr, tris, arc = VARIANTS[name]
    rng = random.Random(seed)
    base = 0.0
    bm = bmesh.new()
    puffs = []
    for i in range(n):
        u = (i + rng.uniform(0.2, 0.8)) / n - 0.5            # spread along the length
        x = u * L * 0.85
        y = rng.gauss(0, D * 0.18)
        # taller in the middle (dome profile), towering for the cumulus
        prof = math.cos(u * math.pi) ** (0.6 if name != 'SM_Cloud_Cumulus' else 0.35)
        r = H * rng.uniform(*rr) * (0.6 + 0.5 * prof)
        z = base + r * 0.35 + (H - r) * prof * rng.uniform(0.3, 0.9) * (1.0 if name == 'SM_Cloud_Cumulus' else 0.5)
        puffs.append((Vector((x, y, z)), r))
    # a few cap puffs on top of the biggest ones
    for c, r in sorted(puffs, key=lambda p: -p[0].z - p[1])[:max(2, n // 4)]:
        puffs.append((c + Vector((rng.uniform(-0.3, 0.3) * r, rng.uniform(-0.3, 0.3) * r, r * 0.55)), r * 0.6))
    for c, r in puffs:
        t = bmesh.new(); bmesh.ops.create_icosphere(t, subdivisions=3, radius=1.0)
        for v in t.verts:
            p = c + Vector((v.co.x * r * 1.15, v.co.y * r, v.co.z * r * 0.9))
            if p.z < base:                                      # flat underside
                p.z = base - (base - p.z) * 0.12
            v.co = p
        me_t = bpy.data.meshes.new('_t'); t.to_mesh(me_t); t.free()
        bm.from_mesh(me_t); bpy.data.meshes.remove(me_t)
    if arc:   # bend the long band toward -Y at its ends (faces the player from far away)
        for v in bm.verts:
            v.co.y += arc * (v.co.x ** 2) / L
    me = bpy.data.meshes.new('_cloud_tmp'); bm.to_mesh(me); bm.free()
    tmp = bpy.data.objects.new('_cloud_tmp', me); bpy.context.scene.collection.objects.link(tmp)
    rm = tmp.modifiers.new('r', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = max(H, D) / 45
    sm = tmp.modifiers.new('s', 'SMOOTH'); sm.factor = 0.8; sm.iterations = 10
    dc = tmp.modifiers.new('d', 'DECIMATE'); dc.ratio = 1.0
    dg = bpy.context.evaluated_depsgraph_get(); ev = tmp.evaluated_get(dg)
    n_tri = len(ev.to_mesh().polygons) * 2; ev.to_mesh_clear()
    dc.ratio = min(1.0, tris / max(n_tri, 1))
    dg = bpy.context.evaluated_depsgraph_get(); ev = tmp.evaluated_get(dg)
    bm = bmesh.new(); bm.from_mesh(ev.to_mesh()); ev.to_mesh_clear()
    bpy.data.objects.remove(tmp, do_unlink=True); bpy.data.meshes.remove(me)
    bm.normal_update()

    B = Builder(); B.bm.free(); B.bm = bm
    B.col = bm.loops.layers.color.new('Col'); B.uv = bm.loops.layers.uv.new('UVMap')
    zmin = min(v.co.z for v in bm.verts); zmax = max(v.co.z for v in bm.verts)
    off = Vector((seed * 1.7, seed * 0.3, 0))
    for f in bm.faces:
        f.smooth = True; f.material_index = 0
        for l in f.loops:
            p = l.vert.co; nrm = l.vert.normal
            h = c01((p.z - zmin) / max(zmax - zmin, 1e-3))
            up = c01(nrm.z * 0.5 + 0.5)
            t = c01(0.6 * up + 0.4 * h + 0.12 * noise.noise(p * (3.0 / H) + off))
            c = mix(BOTTOM, MID, c01(t / 0.5))
            c = mix(c, TOP, c01((t - 0.5) / 0.4))
            l[B.col] = (lin2srgb(c[0]), lin2srgb(c[1]), lin2srgb(c[2]), 1.0)
            l[B.uv].uv = (p.x / L, p.z / H)
    ob = B.finish(name, [material('M_Stylized_Cloud', False)], collection='Clouds')
    n_out = export(ob) if do_export else sum(len(p.vertices) - 2 for p in ob.data.polygons)
    dims = tuple(round(d, 1) for d in ob.dimensions)
    return name, n_out, dims


def build_all(do_export=True):
    return [build(n, do_export) for n in VARIANTS]
