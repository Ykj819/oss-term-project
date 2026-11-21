# Stylized stone barrel-vault passage (semicircular arch on low walls), two meshes:
#   SM_StoneTunnel           tileable segment, 4 m long: chain them every 400 cm along +X (stones interlock across the seam)
#   SM_StoneTunnel_Entrance  the same segment + a protruding arch ring with keystone and pillars at the front (x = 0)
# Pivot = floor centre at the start of the segment (x = 0), passage runs along +X, floor top at z ~ 0.03 m.
# Inside: 5 m wide (vault radius 2.5 m), walls 1.2 m, apex 3.7 m. Stones / wall blocks / floor slabs are separate bevelled
# blocks with a dark mortar body behind the gaps. Colour = vertex colours (material slot M_Stylized_Prop, like the fence).
# Collision: UCX convex pieces (floor, walls, vault wedges; ring + pillars on the entrance).
# Run headless (saves Export/Blender/StoneTunnel.blend, previews in Export/Blender/compare/stone_tunnel_*.png,
# exports Export/SM_StoneTunnel*.fbx):
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup
#       --python Export/Blender/scripts/props/gen_stone_tunnel.py
import bpy, bmesh, math, random, os
from mathutils import Vector, Matrix, noise

exec(open(r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Blender\scripts\props\props_common.py",
          encoding='utf-8').read())

L = 4.0            # segment length (m)
R = 2.5            # inner vault radius = half the inner width
T = 0.45           # wall / vault thickness
WALL_H = 1.2       # springing height
COURSES = 13       # voussoir courses over the half circle
WALL_COURSES = 3
FLOOR_ROWS = 4
GAP = 0.024        # joint width
BEVEL = 0.035
MORTAR = (0.045, 0.040, 0.034)
STONE_WARM = (0.45, 0.38, 0.28); STONE_COOL = (0.32, 0.33, 0.34); STONE_LIGHT = (0.62, 0.56, 0.47)
FLOOR_STONE = (0.26, 0.25, 0.22)
MOSS = (0.07, 0.13, 0.03); DIRT = (0.06, 0.045, 0.03)


def P(x, r, th):
    """vault point: x along the passage, radius r, angle th (0 = +Y side, pi = -Y side)"""
    return Vector((x, r * math.cos(th), WALL_H + r * math.sin(th)))


def periodic_cuts(rng, offset, lo, hi):
    """joint positions along x on a loop of length L (so segments tile)"""
    cuts = []; x = offset % L
    while True:
        cuts.append(x)
        x += rng.uniform(lo, hi)
        if x >= offset % L + L - lo * 0.6: break
    return sorted(c % L for c in cuts)


def x_stones(cuts):
    """stones along x on the loop; each stone = list of pieces (x0, x1, seam0, seam1, xoff). A stone crossing the seam is
    split into [a, L] and [0, b - L] (seam faces: no gap, no bevel). xoff puts a piece back into the stone's unsplit frame
    so both halves get the same noise / colour; the caller draws the stone's random sizes ONCE for all its pieces."""
    out = []
    n = len(cuts)
    for i in range(n):
        a = cuts[i]; b = cuts[(i + 1) % n] + (L if i == n - 1 else 0.0)
        if b <= L + 1e-6:
            out.append([(a, b, False, False, 0.0)])
        else:
            out.append([p for p in ((a, L, False, True, 0.0), (0.0, b - L, True, False, L)) if p[1] - p[0] > 0.02])
    return out


# ---------------------------------------------------------------- one bevelled block from 8 corners
# corner index = a*4 + b*2 + c   (a: x end, b: along the course, c: inner -> outer)
FACES8 = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]


class Mesh:
    def __init__(self):
        self.bm = bmesh.new()
        self.col = self.bm.loops.layers.color.new('Col'); self.uv = self.bm.loops.layers.uv.new('UVMap')
        self.n_stones = 0

    def block(self, corners, colour, seam=(False, False), bevel=BEVEL, wobble=0.012, seed=0.0, xoff=0.0):
        """colour(position, vertex normal, face normal) -> linear rgb. seam: corner faces a=0 / a=1 lie on the tile seam
        (kept flat; seam verts only move across the passage so both halves of a split stone meet exactly)."""
        sh = Vector((xoff, 0, 0))
        tb = bmesh.new()
        vs = [tb.verts.new(c) for c in corners]
        for f in FACES8: tb.faces.new([vs[i] for i in f])
        bmesh.ops.recalc_face_normals(tb, faces=tb.faces)
        on_seam = set()
        if seam[0]: on_seam |= {vs[i] for i in range(4)}
        if seam[1]: on_seam |= {vs[i] for i in range(4, 8)}
        if bevel > 0:
            edges = [e for e in tb.edges if not (e.verts[0] in on_seam and e.verts[1] in on_seam)]
            bmesh.ops.bevel(tb, geom=edges + list({v for e in edges for v in e.verts}), offset=bevel, offset_type='OFFSET',
                            segments=2, profile=0.5, affect='EDGES', clamp_overlap=True)
        tb.normal_update()
        seam_x = [c.x for i, c in enumerate(corners) if (seam[0] and i < 4) or (seam[1] and i >= 4)]
        moves = []
        for v in tb.verts:
            d = v.normal.copy()
            if any(abs(v.co.x - sx) < 1e-5 for sx in seam_x):
                d.x = 0.0                                               # stay on the seam plane
                d = d.normalized() if d.length > 1e-6 else d
            moves.append((v, d * noise.noise((v.co + sh) * 3.1 + Vector((seed, seed * 0.7, 0))) * wobble))
        for v, m in moves: v.co += m
        tb.normal_update()
        vmap = {v: self.bm.verts.new(v.co) for v in tb.verts}
        for f in tb.faces:
            try: nf = self.bm.faces.new([vmap[v] for v in f.verts])
            except ValueError: continue
            nf.smooth = True
            for l, ol in zip(nf.loops, f.loops):
                c = colour(ol.vert.co + sh, ol.vert.normal, f.normal)
                l[self.col] = (lin2srgb(c[0]), lin2srgb(c[1]), lin2srgb(c[2]), 1.0)
                p = ol.vert.co; l[self.uv].uv = (p.x + p.y, p.z)
        tb.free(); self.n_stones += 1

    def finish(self, name):
        old = bpy.data.objects.get(name)
        if old:
            m = old.data; bpy.data.objects.remove(old, do_unlink=True); bpy.data.meshes.remove(m)
        self.bm.normal_update()
        me = bpy.data.meshes.new(name); self.bm.to_mesh(me); self.bm.free()
        me.materials.append(material('M_Stylized_Prop', False))
        col = bpy.data.collections.get('StoneTunnel') or bpy.data.collections.new('StoneTunnel')
        if col.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(col)
        ob = bpy.data.objects.new(name, me); col.objects.link(ob)
        return ob


# ---------------------------------------------------------------- colours
def stone_colour(rng, base_mix=None, light=1.0, floor=False):
    t = rng.random() if base_mix is None else base_mix
    base = FLOOR_STONE if floor else mix(STONE_COOL, STONE_WARM, t)
    base = scale(base, rng.uniform(0.82, 1.15) * light)
    s = rng.uniform(0, 100)

    def fn(p, n, fn_):
        g = noise.noise(Vector((p.x, p.y, p.z)) * 2.2 + Vector((s, 0, 0)))
        c = scale(base, 0.9 + 0.18 * g)
        edge = c01((1.0 - n.dot(fn_)) * 5.0)
        c = mix(c, STONE_LIGHT if not floor else scale(STONE_LIGHT, 0.6), edge * 0.28)          # worn, catching edges
        # moss: on upward-facing outer surfaces and creeping up from the floor along the walls
        up = c01((n.z - 0.45) * 2.0)
        mz = noise.noise(Vector((p.x, p.y, p.z)) * 0.9 + Vector((7, s * 0.01, 3)))
        moss = max(up * c01(0.5 + mz), c01((0.45 - p.z) / 0.45) * c01(0.3 + mz) * (0.0 if floor else 1.0))
        c = mix(c, MOSS, moss * 0.75)
        c = mix(c, DIRT, c01((0.25 - p.z) / 0.35) * (0.35 if floor else 0.5))                 # damp base
        inner = (Vector((0, p.y, p.z - WALL_H)).length < R + 0.08) and p.z > WALL_H
        if inner: c = scale(c, 0.85)                                                            # shaded ceiling
        return c
    return fn


def mortar_colour(p, n, fn_):
    return scale(MORTAR, 0.85 + 0.3 * noise.noise(p * 1.7))


# ---------------------------------------------------------------- parts
def vault(M, rng):
    dth = math.pi / COURSES
    for k in range(COURSES):
        th0 = k * dth; th1 = (k + 1) * dth
        for stone in x_stones(periodic_cuts(rng, (k % 2) * 0.45 + rng.uniform(0, 0.1), 0.65, 1.05)):
            a0 = th0 + (GAP / 2) / R; a1 = th1 - (GAP / 2) / R
            r0 = R - rng.uniform(0.0, 0.03); r1 = R + T + rng.uniform(-0.03, 0.03)
            col = stone_colour(rng); sd = rng.uniform(0, 50)
            for x0, x1, s0, s1, xo in stone:
                g0 = 0.0 if s0 else GAP / 2; g1 = 0.0 if s1 else GAP / 2
                cs = [P(xx, r, th) for xx in (x0 + g0, x1 - g1) for th in (a0, a1) for r in (r0, r1)]
                M.block(cs, col, seam=(s0, s1), seed=sd, xoff=xo)


def walls(M, rng):
    h = WALL_H / WALL_COURSES
    for side in (1, -1):
        for j in range(WALL_COURSES):
            z0 = -0.1 if j == 0 else j * h; z1 = (j + 1) * h
            for stone in x_stones(periodic_cuts(rng, ((j + (side > 0)) % 2) * 0.5 + rng.uniform(0, 0.1), 0.7, 1.2)):
                r0 = R - rng.uniform(0.0, 0.03); r1 = R + T + rng.uniform(-0.03, 0.03)
                col = stone_colour(rng, light=0.95); sd = rng.uniform(0, 50)
                for x0, x1, s0, s1, xo in stone:
                    g0 = 0.0 if s0 else GAP / 2; g1 = 0.0 if s1 else GAP / 2
                    cs = [Vector((xx, side * r, z)) for xx in (x0 + g0, x1 - g1)
                          for z in (z0 + (0 if j == 0 else GAP / 2), z1 - GAP / 2) for r in (r0, r1)]
                    M.block(cs, col, seam=(s0, s1), seed=sd, xoff=xo)


def floor(M, rng):
    w = 2 * R / FLOOR_ROWS
    for i in range(FLOOR_ROWS):
        y0 = -R + i * w; y1 = y0 + w
        for stone in x_stones(periodic_cuts(rng, (i % 2) * 0.4 + rng.uniform(0, 0.2), 0.75, 1.25)):
            ztop = 0.03 + rng.uniform(-0.008, 0.008)
            col = stone_colour(rng, floor=True); sd = rng.uniform(0, 50)
            for x0, x1, s0, s1, xo in stone:
                g0 = 0.0 if s0 else GAP / 2; g1 = 0.0 if s1 else GAP / 2
                cs = [Vector((xx, y, z)) for xx in (x0 + g0, x1 - g1) for y in (y0 + GAP / 2, y1 - GAP / 2)
                      for z in (-0.08, ztop)]
                M.block(cs, col, seam=(s0, s1), bevel=0.025, wobble=0.006, seed=sd, xoff=xo)


def mortar(M):
    """dark body behind every joint (closed pieces, flat ends on the seam)"""
    ri, ro = R + 0.03, R + T - 0.06
    n = 36
    for k in range(n):                                       # vault ring in wedges
        a, b = math.pi * k / n, math.pi * (k + 1) / n
        cs = [P(x, r, th) for x in (0.0, L) for th in (a, b) for r in (ri, ro)]
        M.block(cs, mortar_colour, seam=(True, True), bevel=0.0, wobble=0.0)
    for side in (1, -1):                                     # walls
        cs = [Vector((x, side * r, z)) for x in (0.0, L) for z in (-0.1, WALL_H) for r in (ri, ro)]
        M.block(cs, mortar_colour, seam=(True, True), bevel=0.0, wobble=0.0)
    cs = [Vector((x, y, z)) for x in (0.0, L) for y in (-R - 0.02, R + 0.02) for z in (-0.12, 0.0)]   # floor bed
    M.block(cs, mortar_colour, seam=(True, True), bevel=0.0, wobble=0.0)


RING_X = (-0.35, 0.12); RING_IN = R - 0.08; RING_OUT = R + T + 0.28; RING_N = 15


def entrance_ring(M, rng):
    dth = math.pi / RING_N
    for k in range(RING_N):
        key = k == RING_N // 2
        a0 = k * dth + (GAP / 2) / R; a1 = (k + 1) * dth - (GAP / 2) / R
        r0 = RING_IN - (0.04 if key else rng.uniform(0, 0.02)); r1 = RING_OUT + (0.14 if key else rng.uniform(-0.03, 0.03))
        xa = RING_X[0] - (0.05 if key else 0.0)
        cs = [P(x, r, th) for x in (xa, RING_X[1]) for th in (a0, a1) for r in (r0, r1)]
        M.block(cs, stone_colour(rng, base_mix=0.65, light=1.12), bevel=0.045, wobble=0.01, seed=rng.uniform(0, 50))
    # pillars: plinth, 3 stacked blocks, impost cap
    for side in (1, -1):
        parts = [(-0.1, 0.25, 0.06), (0.25 + GAP, 0.55, 0.0), (0.55 + GAP, 0.85, 0.0), (0.85 + GAP, WALL_H - 0.14, 0.0),
                 (WALL_H - 0.14 + GAP, WALL_H - GAP / 2, 0.07)]
        for z0, z1, grow in parts:
            cs = [Vector((x, side * r, z)) for x in (RING_X[0] - grow, RING_X[1] + grow * 0.5) for z in (z0, z1)
                  for r in (RING_IN - grow, RING_OUT + grow)]
            M.block(cs, stone_colour(rng, base_mix=0.65, light=1.08), bevel=0.04, wobble=0.008, seed=rng.uniform(0, 50))


# ---------------------------------------------------------------- collision
def ucx_objects(name, entrance):
    for o in [o for o in bpy.data.objects if o.name.startswith('UCX_' + name + '_')]:
        m = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(m)
    hulls = []
    hulls.append([Vector((x, y, z)) for x in (0, L) for y in (-R - T, R + T) for z in (-0.12, 0.03)])        # floor
    for side in (1, -1):
        hulls.append([Vector((x, side * r, z)) for x in (0, L) for r in (R, R + T) for z in (0.0, WALL_H)])  # walls
    n = 8
    for k in range(n):
        a, b = math.pi * k / n, math.pi * (k + 1) / n
        hulls.append([P(x, r, th) for x in (0, L) for th in (a, b) for r in (R, R + T)])                    # vault
    if entrance:
        for k in range(n):
            a, b = math.pi * k / n, math.pi * (k + 1) / n
            hulls.append([P(x, r, th) for x in RING_X for th in (a, b) for r in (RING_IN, RING_OUT)])
        for side in (1, -1):
            hulls.append([Vector((x, side * r, z)) for x in (RING_X[0] - 0.06, RING_X[1]) for r in (RING_IN, RING_OUT)
                          for z in (-0.1, WALL_H)])
    out = []
    for i, pts in enumerate(hulls):
        bm = bmesh.new()
        for p in pts: bm.verts.new(p)
        bmesh.ops.convex_hull(bm, input=bm.verts)
        nm = f'UCX_{name}_{i:02d}'; me = bpy.data.meshes.new(nm); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(nm, me); bpy.data.collections['StoneTunnel'].objects.link(o)
        o.display_type = 'WIRE'; out.append(o)
    return out


def build(name, entrance, seed=11):
    rng = random.Random(seed)                 # same seed -> the entrance segment's stones match the plain segment
    M = Mesh()
    vault(M, rng); walls(M, rng); floor(M, rng); mortar(M)
    if entrance: entrance_ring(M, random.Random(seed + 100))
    ob = M.finish(name)
    ucx = ucx_objects(name, entrance)
    tris = export(ob, ucx)
    print(f'TUNNEL {name}: {M.n_stones} blocks, {tris} tris, {len(ucx)} UCX')
    return ob


# ---------------------------------------------------------------- previews
def previews(seg, ent):
    CMP = os.path.join(ROOT, r"Export\Blender\compare"); os.makedirs(CMP, exist_ok=True)
    sc = bpy.context.scene; tmp = []
    for x in (L, 2 * L):                                      # entrance + 2 chained segments
        o = bpy.data.objects.new('PREV_seg', seg.data); sc.collection.objects.link(o); o.location = (x, 0, 0); tmp.append(o)
    ent.location = (0, 0, 0); seg.hide_render = True
    gm = bpy.data.meshes.new('PREV_ground'); gm.from_pydata([(-6, -8, -0.005), (16, -8, -0.005), (16, 8, -0.005), (-6, 8, -0.005)], [], [(0, 1, 2, 3)])
    g = bpy.data.objects.new('PREV_ground', gm); sc.collection.objects.link(g); tmp.append(g)
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.25, radius2=0.25, depth=1.8,
                                            matrix=Matrix.Translation((1.5, 0.6, 0.93)))
    hm = bpy.data.meshes.new('PREV_human'); bm.to_mesh(hm); bm.free()
    h = bpy.data.objects.new('PREV_human', hm); sc.collection.objects.link(h); tmp.append(h)   # 1.8 m person for scale
    for o in bpy.data.objects:
        if o.name.startswith('UCX_'): o.hide_render = True
    cam = bpy.data.objects.new('PREV_cam', bpy.data.cameras.new('PREV_cam')); sc.collection.objects.link(cam); tmp.append(cam)
    sc.camera = cam; sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading; sh.light = 'STUDIO'
    sh.color_type = 'VERTEX'                                  # show the 'Col' vertex colours
    for me in (seg.data, ent.data):
        me.color_attributes.active_color = me.color_attributes['Col']
    sh.show_cavity = True; sh.show_shadows = True
    sc.render.resolution_x = 1100; sc.render.resolution_y = 700
    outs = []
    for tag, loc, look_at, lens in (('outside', (-7.5, -6.5, 3.2), (3.5, 0, 1.6), 30),
                                    ('inside', (10.5, 0.9, 1.6), (0.0, -0.3, 1.9), 22)):
        cam.location = loc; cam.data.lens = lens
        cam.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        p = os.path.join(CMP, f'stone_tunnel_{tag}.png'); sc.render.filepath = p
        bpy.ops.render.render(write_still=True); outs.append(p)
    for o in tmp:
        d = o.data; bpy.data.objects.remove(o, do_unlink=True)
        if d and d.users == 0:
            (bpy.data.meshes if isinstance(d, bpy.types.Mesh) else bpy.data.cameras).remove(d)
    seg.hide_render = False; ent.location = (0, -8, 0)      # side by side in the saved file
    for o in bpy.data.objects:
        if o.name.startswith('UCX_SM_StoneTunnel_Entrance_'): o.location = (0, -8, 0)
    return outs


if __name__ == '__main__':
    for o in list(bpy.data.objects):
        if o.name in ('Cube',): bpy.data.objects.remove(o, do_unlink=True)
    seg = build('SM_StoneTunnel', False)
    ent = build('SM_StoneTunnel_Entrance', True)
    for p in previews(seg, ent): print('TUNNEL preview', p)
    out = os.path.join(ROOT, r"Export\Blender\StoneTunnel.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print('TUNNEL saved', out)
