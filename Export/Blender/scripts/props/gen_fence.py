# Stylized wooden fence segment SM_StylizedFence: two chunky posts 2 m apart + two thick planks on the front.
# Pivot = bottom centre of the left post, segment runs along +X, so segments chain every 200 cm (posts coincide).
# Soft look: boxes merged with voxel remesh + Smooth (rounded edges, soft valleys where planks meet posts),
# decimated to ~2k tris. Colour = vertex colours (darker posts, lighter planks, dirt at the bottom, sunlit tops,
# faint stretched grain). Collision: one UCX box. Material slot M_Stylized_Prop.
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise

exec(open(r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Blender\scripts\props\props_common.py",
          encoding='utf-8').read())

NAME = 'SM_StylizedFence'
LENGTH = 2.0
POST_W = 0.19; POST_H = 1.08
PLANK_H = 0.19; PLANK_T = 0.065
PLANK_Z = (0.36, 0.78)
POST_DARK = (0.06, 0.032, 0.016); POST_MID = (0.12, 0.068, 0.036); POST_LIGHT = (0.26, 0.16, 0.085)
PLANK_DARK = (0.09, 0.05, 0.025); PLANK_MID = (0.24, 0.14, 0.07); PLANK_LIGHT = (0.40, 0.26, 0.13)
DIRT = (0.05, 0.035, 0.02)


def add_box(bm, centre, size, rot=Matrix.Identity(3)):
    r = bmesh.ops.create_cube(bm, size=1.0)
    for v in r['verts']:
        v.co = centre + rot @ Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))


def build(seed=5, do_export=True, tris=2200):
    rng = random.Random(seed)
    bm = bmesh.new()
    for px in (0.0, LENGTH):
        lean = Matrix.Rotation(rng.uniform(-0.03, 0.03), 3, 'X') @ Matrix.Rotation(rng.uniform(-0.03, 0.03), 3, 'Y') \
            @ Matrix.Rotation(rng.uniform(-0.12, 0.12), 3, 'Z')
        h = POST_H * rng.uniform(0.95, 1.03)
        add_box(bm, Vector((px, 0, h / 2 - 0.05)), (POST_W, POST_W, h), lean)
    for z in PLANK_Z:
        tilt = Matrix.Rotation(rng.uniform(-0.035, 0.035), 3, 'Y')          # slightly crooked planks
        add_box(bm, Vector((LENGTH / 2, -(POST_W / 2 + PLANK_T / 2 - 0.01), z + rng.uniform(-0.02, 0.02))),
                (LENGTH + 0.22, PLANK_T, PLANK_H), tilt)
    me = bpy.data.meshes.new('_fence_tmp'); bm.to_mesh(me); bm.free()
    tmp = bpy.data.objects.new('_fence_tmp', me); bpy.context.scene.collection.objects.link(tmp)
    rm = tmp.modifiers.new('r', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = 0.012
    sm = tmp.modifiers.new('s', 'SMOOTH'); sm.factor = 0.8; sm.iterations = 6
    dc = tmp.modifiers.new('d', 'DECIMATE'); dc.ratio = 1.0
    dg = bpy.context.evaluated_depsgraph_get(); ev = tmp.evaluated_get(dg)
    n_tri = len(ev.to_mesh().polygons) * 2; ev.to_mesh_clear()
    dc.ratio = min(1.0, tris / max(n_tri, 1))
    dg = bpy.context.evaluated_depsgraph_get(); ev = tmp.evaluated_get(dg)
    bm = bmesh.new(); bm.from_mesh(ev.to_mesh()); ev.to_mesh_clear()
    bpy.data.objects.remove(tmp, do_unlink=True); bpy.data.meshes.remove(me)
    bm.normal_update()
    # gentle hand-made wobble
    for v in bm.verts:
        v.co += v.normal * noise.noise(v.co * 2.5 + Vector((seed, 0, 0))) * 0.008
    bm.normal_update()

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
            # grain: noise stretched along the plank length (x) or the post height (z)
            g = noise.noise(Vector((p.x * 1.2, p.z * 14, p.y * 14)) if is_plank else Vector((p.x * 14, p.y * 14, p.z * 1.2)))
            up = c01(n.z * 0.5 + 0.5)
            c = mix(dark, mid, c01(0.55 + 0.35 * g + 0.25 * (up - 0.5)))
            c = mix(c, light, c01((up - 0.55) * 1.6) * 0.8)                   # sunlit tops
            edge = c01((1.0 - n.dot(fn)) * 6.0)
            c = mix(c, light, edge * 0.2)                                      # worn edges
            c = mix(c, DIRT, c01((0.22 - p.z) / 0.22) * 0.75)                  # dirt / damp at the base
            c = scale(c, 0.9 + 0.2 * noise.noise(p * 1.3 + Vector((3, 7, seed))))
            l[B.col] = (lin2srgb(c[0]), lin2srgb(c[1]), lin2srgb(c[2]), 1.0)
            l[B.uv].uv = (p.x + p.y, p.z)
    ob = B.finish(NAME, [material('M_Stylized_Prop', False)], collection='Fence')

    # collision: one box around the whole segment
    old = bpy.data.objects.get('UCX_' + NAME + '_00')
    if old:
        m = old.data; bpy.data.objects.remove(old, do_unlink=True); bpy.data.meshes.remove(m)
    cb = bmesh.new(); add_box(cb, Vector((LENGTH / 2, -0.035, POST_H / 2)), (LENGTH + 0.2, 0.22, POST_H)); cm = bpy.data.meshes.new('UCX_' + NAME + '_00')
    cb.to_mesh(cm); cb.free()
    ucx = bpy.data.objects.new('UCX_' + NAME + '_00', cm); ob.users_collection[0].objects.link(ucx)
    ucx.display_type = 'WIRE'
    n = export(ob, [ucx]) if do_export else sum(len(p.vertices) - 2 for p in ob.data.polygons)
    return ob.name, n
