# Stylized stone VERTICAL ROUND SHAFT (well-like cylinder of stone courses), same stone look as gen_stone_tunnel.py:
#   SM_StoneShaft   tileable segment 4 m high: stack them every 400 cm along +Z (courses line up across the seam)
# Pivot = shaft centre at the bottom of the segment (z = 0), open top and bottom (no floor, no entrance).
# Inside diameter 5 m (radius 2.5 m), wall 0.45 m thick -> outside diameter 5.9 m.
# Colour = vertex colours (material slot M_Stylized_Prop). Collision: 24 UCX convex wall wedges.
# Run headless (saves Export/Blender/StoneShaft.blend, previews Export/Blender/compare/stone_shaft_*.png,
# exports Export/SM_StoneShaft.fbx):
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup
#       --python Export/Blender/scripts/props/gen_stone_shaft.py
import bpy, bmesh, math, random, os
from mathutils import Vector, Matrix, noise

exec(open(r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Blender\scripts\props\props_common.py",
          encoding='utf-8').read())

H = 4.0            # segment height (m), tiles along Z
R = 2.5            # inner radius
T = 0.45           # wall thickness
COURSES = 8        # stone courses per segment (0.5 m each)
GAP = 0.024
BEVEL = 0.035
MORTAR = (0.045, 0.040, 0.034)
STONE_WARM = (0.45, 0.38, 0.28); STONE_COOL = (0.32, 0.33, 0.34); STONE_LIGHT = (0.62, 0.56, 0.47)
MOSS = (0.07, 0.13, 0.03); DIRT = (0.06, 0.045, 0.03)
COLL = 'StoneShaft'


def C(th, r, z):
    return Vector((r * math.cos(th), r * math.sin(th), z))


FACES8 = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]


class Mesh:
    def __init__(self):
        self.bm = bmesh.new()
        self.col = self.bm.loops.layers.color.new('Col'); self.uv = self.bm.loops.layers.uv.new('UVMap')
        self.n_stones = 0

    def block(self, corners, colour, bevel=BEVEL, wobble=0.012, seed=0.0):
        tb = bmesh.new()
        vs = [tb.verts.new(c) for c in corners]
        for f in FACES8: tb.faces.new([vs[i] for i in f])
        bmesh.ops.recalc_face_normals(tb, faces=tb.faces)
        if bevel > 0:
            bmesh.ops.bevel(tb, geom=list(tb.edges) + list(tb.verts), offset=bevel, offset_type='OFFSET',
                            segments=2, profile=0.5, affect='EDGES', clamp_overlap=True)
        tb.normal_update()
        if wobble > 0:
            moves = [(v, v.normal * noise.noise(v.co * 3.1 + Vector((seed, seed * 0.7, 0))) * wobble) for v in tb.verts]
            for v, m in moves: v.co += m
            tb.normal_update()
        vmap = {v: self.bm.verts.new(v.co) for v in tb.verts}
        for f in tb.faces:
            try: nf = self.bm.faces.new([vmap[v] for v in f.verts])
            except ValueError: continue
            nf.smooth = True
            for l, ol in zip(nf.loops, f.loops):
                c = colour(ol.vert.co, ol.vert.normal, f.normal)
                l[self.col] = (lin2srgb(c[0]), lin2srgb(c[1]), lin2srgb(c[2]), 1.0)
                p = ol.vert.co; l[self.uv].uv = (math.atan2(p.y, p.x) * R, p.z)
        tb.free(); self.n_stones += 1

    def finish(self, name):
        old = bpy.data.objects.get(name)
        if old:
            m = old.data; bpy.data.objects.remove(old, do_unlink=True); bpy.data.meshes.remove(m)
        self.bm.normal_update()
        me = bpy.data.meshes.new(name); self.bm.to_mesh(me); self.bm.free()
        me.materials.append(material('M_Stylized_Prop', False))
        col = bpy.data.collections.get(COLL) or bpy.data.collections.new(COLL)
        if col.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(col)
        ob = bpy.data.objects.new(name, me); col.objects.link(ob)
        return ob


def stone_colour(rng, light=1.0):
    base = scale(mix(STONE_COOL, STONE_WARM, rng.random()), rng.uniform(0.82, 1.15) * light)
    s = rng.uniform(0, 100)

    def fn(p, n, fn_):
        g = noise.noise(p * 2.2 + Vector((s, 0, 0)))
        c = scale(base, 0.9 + 0.18 * g)
        c = mix(c, STONE_LIGHT, c01((1.0 - n.dot(fn_)) * 5.0) * 0.28)             # worn edges
        th = math.atan2(p.y, p.x)
        # moss patches + vertical damp streaks (streaks depend on the angle only -> continuous across stacked segments)
        mz = noise.noise(p * 0.9 + Vector((7, s * 0.01, 3)))
        c = mix(c, MOSS, c01(mz * 2.2 - 0.25) * 0.7)
        streak = c01(noise.noise(Vector((math.cos(th) * 6.0, math.sin(th) * 6.0, 0.3))) * 2.5 - 0.2)
        c = mix(c, DIRT, streak * 0.45)
        if math.hypot(p.x, p.y) < R + 0.08: c = scale(c, 0.85)                    # shaded inside face
        return c
    return fn


def mortar_colour(p, n, fn_):
    return scale(MORTAR, 0.85 + 0.3 * noise.noise(p * 1.7))


def wall_stone(M, rng):
    """courses of curved stones (0.7-1.15 m long on the inner circle), joints staggered course to course"""
    h = H / COURSES
    for j in range(COURSES):
        z0 = j * h + GAP / 2; z1 = (j + 1) * h - GAP / 2
        cuts = []; a = (j % 2) * 0.22 + rng.uniform(0, 0.08)
        while True:
            cuts.append(a)
            a += rng.uniform(0.7, 1.15) / R
            if a >= cuts[0] + 2 * math.pi - 0.5 / R: break
        n = len(cuts)
        for i in range(n):
            a0 = cuts[i] + (GAP / 2) / R
            a1 = (cuts[i + 1] if i + 1 < n else cuts[0] + 2 * math.pi) - (GAP / 2) / R
            r0 = R - rng.uniform(0.0, 0.03); r1 = R + T + rng.uniform(-0.03, 0.03)
            M.curved_block(a0, a1, r0, r1, z0, z1, stone_colour(rng), rng.uniform(0, 50))


def curved_block(self, a0, a1, r0, r1, z0, z1, colour, seed):
    """bevelled box in (angle, r, z) space, bent onto the cylinder afterwards (keeps the bevel even)"""
    rm = (r0 + r1) / 2
    w = (a1 - a0) * rm                                        # arc length at mid radius
    segs = max(1, int(math.ceil((a1 - a0) / 0.12)))
    tb = bmesh.new()
    bmesh.ops.create_cube(tb, size=1.0)
    for v in tb.verts:
        v.co = Vector(((v.co.x + 0.5) * w, (v.co.y + 0.5) * (r1 - r0), (v.co.z + 0.5) * (z1 - z0)))
    bmesh.ops.bevel(tb, geom=list(tb.edges) + list(tb.verts), offset=BEVEL, offset_type='OFFSET',
                    segments=2, profile=0.5, affect='EDGES', clamp_overlap=True)
    # cut along the length so it can bend
    for k in range(1, segs):
        x = w * k / segs
        bmesh.ops.bisect_plane(tb, geom=list(tb.verts) + list(tb.edges) + list(tb.faces), dist=1e-5,
                               plane_co=(x, 0, 0), plane_no=(1, 0, 0))
    for v in tb.verts:
        x, y, z = v.co
        th = a0 + x / rm; r = r0 + y
        v.co = Vector((r * math.cos(th), r * math.sin(th), z0 + z))
    tb.normal_update()
    moves = [(v, v.normal * noise.noise(v.co * 3.1 + Vector((seed, seed * 0.7, 0))) * 0.012) for v in tb.verts]
    for v, m in moves: v.co += m
    bmesh.ops.recalc_face_normals(tb, faces=tb.faces)
    tb.normal_update()
    vmap = {v: self.bm.verts.new(v.co) for v in tb.verts}
    for f in tb.faces:
        try: nf = self.bm.faces.new([vmap[v] for v in f.verts])
        except ValueError: continue
        nf.smooth = True
        for l, ol in zip(nf.loops, f.loops):
            c = colour(ol.vert.co, ol.vert.normal, f.normal)
            l[self.col] = (lin2srgb(c[0]), lin2srgb(c[1]), lin2srgb(c[2]), 1.0)
            p = ol.vert.co; l[self.uv].uv = (math.atan2(p.y, p.x) * R, p.z)
    tb.free(); self.n_stones += 1


Mesh.curved_block = curved_block


def mortar(M):
    ri, ro = R + 0.03, R + T - 0.06
    n = 48
    for k in range(n):
        a, b = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        cs = [C(th, r, z) for z in (0.0, H) for th in (a, b) for r in (ri, ro)]
        M.block(cs, mortar_colour, bevel=0.0, wobble=0.0)


def ucx_objects(name):
    for o in [o for o in bpy.data.objects if o.name.startswith('UCX_' + name + '_')]:
        m = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(m)
    n = 24; half = math.pi / n
    ri = R / math.cos(half)                     # chord touches the inner radius mid-wedge (no bump into the shaft)
    out = []
    for i in range(n):
        a, b = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
        pts = [C(th, r, z) for z in (0.0, H) for th in (a, b) for r in (ri, R + T)]
        bm = bmesh.new()
        for p in pts: bm.verts.new(p)
        bmesh.ops.convex_hull(bm, input=bm.verts)
        nm = f'UCX_{name}_{i:02d}'; me = bpy.data.meshes.new(nm); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(nm, me); bpy.data.collections[COLL].objects.link(o)
        o.display_type = 'WIRE'; out.append(o)
    return out


def build(name, seed=21):
    rng = random.Random(seed)
    M = Mesh()
    wall_stone(M, rng); mortar(M)
    ob = M.finish(name)
    ucx = ucx_objects(name)
    tris = export(ob, ucx)
    print(f'SHAFT {name}: {M.n_stones} blocks, {tris} tris, {len(ucx)} UCX')
    return ob


def previews(seg):
    CMP = os.path.join(ROOT, r"Export\Blender\compare"); os.makedirs(CMP, exist_ok=True)
    sc = bpy.context.scene; tmp = []
    o = bpy.data.objects.new('PREV_seg', seg.data); sc.collection.objects.link(o); o.location = (0, 0, H); tmp.append(o)
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.25, radius2=0.25, depth=1.8,
                                            matrix=Matrix.Translation((0.8, 0.4, 0.9)))
    hm = bpy.data.meshes.new('PREV_human'); bm.to_mesh(hm); bm.free()
    hu = bpy.data.objects.new('PREV_human', hm); sc.collection.objects.link(hu); tmp.append(hu)
    gm = bpy.data.meshes.new('PREV_ground'); gm.from_pydata([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], [], [(0, 1, 2, 3)])
    g = bpy.data.objects.new('PREV_ground', gm); sc.collection.objects.link(g); tmp.append(g)
    for ob in bpy.data.objects:
        if ob.name.startswith('UCX_'): ob.hide_render = True
    cam = bpy.data.objects.new('PREV_cam', bpy.data.cameras.new('PREV_cam')); sc.collection.objects.link(cam); tmp.append(cam)
    sc.camera = cam; sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'VERTEX'
    seg.data.color_attributes.active_color = seg.data.color_attributes['Col']
    sh.show_cavity = True; sh.show_shadows = True
    sc.render.resolution_x = 900; sc.render.resolution_y = 900
    outs = []
    for tag, loc, look_at, lens in (('outside', (-9.0, -10.0, 9.0), (0, 0, 3.6), 32),
                                    ('top', (1.2, -1.5, 15.0), (0, 0, 0), 24),
                                    ('inside', (-1.6, 0.9, 1.0), (1.5, -0.6, 6.0), 16)):
        cam.location = loc; cam.data.lens = lens
        cam.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        p = os.path.join(CMP, f'stone_shaft_{tag}.png'); sc.render.filepath = p
        bpy.ops.render.render(write_still=True); outs.append(p)
    for o in tmp:
        d = o.data; bpy.data.objects.remove(o, do_unlink=True)
        if d and d.users == 0:
            (bpy.data.meshes if isinstance(d, bpy.types.Mesh) else bpy.data.cameras).remove(d)
    return outs


if __name__ == '__main__':
    for o in list(bpy.data.objects):
        if o.name in ('Cube',): bpy.data.objects.remove(o, do_unlink=True)
    seg = build('SM_StoneShaft')
    for p in previews(seg): print('SHAFT preview', p)
    out = os.path.join(ROOT, r"Export\Blender\StoneShaft.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print('SHAFT saved', out)
