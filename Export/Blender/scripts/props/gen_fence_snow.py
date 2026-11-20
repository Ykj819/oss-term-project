# Snowy version of the stylized fence: SM_StylizedFence_Snow. Same layout/pivot/collision as gen_fence.py
# (segments chain every 200 cm), plus lumpy snow caps on the post tops and along the plank tops, merged by the
# same voxel remesh so the snow flows softly over the wood. Snow = vertex colour (white, bluish on shaded sides).
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise

exec(open(r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Blender\scripts\props\gen_fence.py",
          encoding='utf-8').read())

NAME_SNOW = 'SM_StylizedFence_Snow'
SNOW_LIT = (0.80, 0.86, 0.93)
SNOW_SHADE = (0.50, 0.60, 0.75)


def build_snow(seed=5, do_export=True, tris=3500):
    rng = random.Random(seed)
    bm = bmesh.new()
    snow = []          # (centre, half size) boxes, used to tell snow vertices apart after the remesh
    tops = []
    for px in (0.0, LENGTH):
        lean = Matrix.Rotation(rng.uniform(-0.03, 0.03), 3, 'X') @ Matrix.Rotation(rng.uniform(-0.03, 0.03), 3, 'Y') \
            @ Matrix.Rotation(rng.uniform(-0.12, 0.12), 3, 'Z')
        h = POST_H * rng.uniform(0.95, 1.03)
        add_box(bm, Vector((px, 0, h / 2 - 0.05)), (POST_W, POST_W, h), lean)
        top = Vector((px, 0, h - 0.05))
        tops.append(top)
        # snow cap: a wider slab + a smaller dome on top
        for c, s in ((top + Vector((0, 0, 0.035)), (POST_W + 0.05, POST_W + 0.05, 0.07)),
                     (top + Vector((rng.uniform(-.02, .02), rng.uniform(-.02, .02), 0.085)), (POST_W - 0.03, POST_W - 0.03, 0.06))):
            add_box(bm, c, s)
            snow.append((c, Vector(s) / 2))
    for z in PLANK_Z:
        tilt = Matrix.Rotation(rng.uniform(-0.035, 0.035), 3, 'Y')
        zc = z + rng.uniform(-0.02, 0.02)
        yc = -(POST_W / 2 + PLANK_T / 2 - 0.01)
        add_box(bm, Vector((LENGTH / 2, yc, zc)), (LENGTH + 0.22, PLANK_T, PLANK_H), tilt)
        # lumpy snow strip along the plank top: pieces of varying height, a few gaps
        n = 9
        for i in range(n):
            if rng.random() < 0.15:
                continue
            x = -0.08 + (LENGTH + 0.16) * (i + 0.5) / n
            hgt = rng.uniform(0.035, 0.07)
            zt = zc + PLANK_H / 2 + (tilt @ Vector((x - LENGTH / 2, 0, 0))).z
            c = Vector((x, yc, zt + hgt / 2 - 0.01))
            s = ((LENGTH + 0.16) / n + 0.04, PLANK_T + 0.035, hgt)
            add_box(bm, c, s)
            snow.append((c, Vector(s) / 2))

    me = bpy.data.meshes.new('_fence_tmp'); bm.to_mesh(me); bm.free()
    tmp = bpy.data.objects.new('_fence_tmp', me); bpy.context.scene.collection.objects.link(tmp)
    rm = tmp.modifiers.new('r', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.012
    sm = tmp.modifiers.new('s', 'SMOOTH'); sm.factor = 0.8; sm.iterations = 8
    dc = tmp.modifiers.new('d', 'DECIMATE'); dc.ratio = 1.0
    dg = bpy.context.evaluated_depsgraph_get(); ev = tmp.evaluated_get(dg)
    n_tri = len(ev.to_mesh().polygons) * 2; ev.to_mesh_clear()
    dc.ratio = min(1.0, tris / max(n_tri, 1))
    dg = bpy.context.evaluated_depsgraph_get(); ev = tmp.evaluated_get(dg)
    bm = bmesh.new(); bm.from_mesh(ev.to_mesh()); ev.to_mesh_clear()
    bpy.data.objects.remove(tmp, do_unlink=True); bpy.data.meshes.remove(me)
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * noise.noise(v.co * 2.5 + Vector((seed, 0, 0))) * 0.008
    bm.normal_update()

    def snow_amount(p, n):
        best = 0.0
        for c, hs in snow:
            d = max(abs(p.x - c.x) - hs.x, abs(p.y - c.y) - hs.y, abs(p.z - c.z) - hs.z)
            best = max(best, c01(1.0 - (d + 0.004) / 0.018))
        return best * c01(n.z * 2.0 + 1.2)        # no snow on faces pointing down

    B = Builder(); B.bm.free(); B.bm = bm
    B.col = bm.loops.layers.color.new('Col'); B.uv = bm.loops.layers.uv.new('UVMap')
    plank_y = -(POST_W / 2) + 0.004
    for f in bm.faces:
        f.smooth = True; f.material_index = 0
        fn = f.normal
        for l in f.loops:
            p = l.vert.co; n = l.vert.normal
            is_plank = p.y < plank_y and 0.2 < p.z < 0.95
            dark, mid, light = (PLANK_DARK, PLANK_MID, PLANK_LIGHT) if is_plank else (POST_DARK, POST_MID, POST_LIGHT)
            g = noise.noise(Vector((p.x * 1.2, p.z * 14, p.y * 14)) if is_plank else Vector((p.x * 14, p.y * 14, p.z * 1.2)))
            up = c01(n.z * 0.5 + 0.5)
            c = mix(dark, mid, c01(0.55 + 0.35 * g + 0.25 * (up - 0.5)))
            c = mix(c, light, c01((up - 0.55) * 1.6) * 0.5)
            edge = c01((1.0 - n.dot(fn)) * 6.0)
            c = mix(c, light, edge * 0.2)
            c = mix(c, (0.06, 0.05, 0.05), c01((0.22 - p.z) / 0.22) * 0.6)    # wet dark base
            c = scale(c, 0.9 + 0.2 * noise.noise(p * 1.3 + Vector((3, 7, seed))))
            s = snow_amount(p, n)
            if s > 0:
                sc = mix(SNOW_SHADE, SNOW_LIT, c01(n.z * 0.8 + 0.3))
                sc = scale(sc, 0.95 + 0.08 * noise.noise(p * 9.0))
                c = mix(c, sc, s)
            l[B.col] = (lin2srgb(c[0]), lin2srgb(c[1]), lin2srgb(c[2]), 1.0)
            l[B.uv].uv = (p.x + p.y, p.z)
    ob = B.finish(NAME_SNOW, [material('M_Stylized_Prop', False)], collection='Fence')
    ob.location.y = 1.5                       # show next to the plain fence in the .blend

    old = bpy.data.objects.get('UCX_' + NAME_SNOW + '_00')
    if old:
        m = old.data; bpy.data.objects.remove(old, do_unlink=True); bpy.data.meshes.remove(m)
    cb = bmesh.new(); add_box(cb, Vector((LENGTH / 2, -0.035, POST_H / 2)), (LENGTH + 0.2, 0.22, POST_H))
    cm = bpy.data.meshes.new('UCX_' + NAME_SNOW + '_00'); cb.to_mesh(cm); cb.free()
    ucx = bpy.data.objects.new('UCX_' + NAME_SNOW + '_00', cm); ob.users_collection[0].objects.link(ucx)
    ucx.display_type = 'WIRE'
    n = export(ob, [ucx]) if do_export else sum(len(p.vertices) - 2 for p in ob.data.polygons)
    return ob.name, n
