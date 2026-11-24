# Stylized BONFIRE (rest point, ABonfire) in the soft stylized prop style:
#   SM_Bonfire       ring of rounded stones + ash bed + teepee of logs (charred towards the fire) + 2 logs across the base.
#                    Vertex colours, slot M_Stylized_Prop, one UCX convex collision (octagonal prism).
#   SM_BonfireFlame  stylized flame tongues (lathed teardrops, centre + ring + yellow core). Slot M_BonfireFlame
#                    (UE: unlit additive, emissive = vertex colour, flicker + sway in the material).
#                    Vertex colour RGB = flame colour, A = sway weight (0 at the base, 1 at the tips).
# Pivot = centre of the fire on the floor (z = 0). Ring outside diameter ~1.45 m, logs ~0.7 m high, flame ~1.2 m.
# Run headless (saves Export/Blender/Bonfire.blend, previews Export/Blender/compare/bonfire_*.png,
# exports Export/SM_Bonfire.fbx + Export/SM_BonfireFlame.fbx):
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup
#       --python Export/Blender/scripts/props/gen_bonfire.py
import bpy, bmesh, math, random, os
from mathutils import Vector, Matrix, noise

exec(open(r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Blender\scripts\props\props_common.py",
          encoding='utf-8').read())

COLL = 'Bonfire'
STONE_WARM = (0.42, 0.36, 0.28); STONE_COOL = (0.30, 0.31, 0.33); STONE_LIGHT = (0.58, 0.53, 0.45)
SOOT = (0.025, 0.022, 0.02); MOSS = (0.07, 0.12, 0.03)
BARK = (0.13, 0.075, 0.04); BARK_DARK = (0.06, 0.035, 0.02); CHAR = (0.018, 0.015, 0.013)
WOOD = (0.55, 0.38, 0.2); WOOD_RING = (0.33, 0.2, 0.09)
ASH = (0.11, 0.105, 0.1); ASH_DARK = (0.03, 0.028, 0.026); EMBER = (0.55, 0.12, 0.02)


class Mesh:
    def __init__(self):
        self.bm = bmesh.new()
        self.col = self.bm.loops.layers.color.new('Col'); self.uv = self.bm.loops.layers.uv.new('UVMap')
        self.parts = 0

    def add(self, tb, colour, alpha=None, uvs=None):
        """copy a temp bmesh in; colour(p, n, face_normal) -> linear rgb; alpha(p) -> 0..1 (stored as is);
        uvs: {temp vert: (u, v)} with u in [0, 1) around a cylinder (faces across the seam get u + 1)"""
        tb.normal_update()
        vmap = {v: self.bm.verts.new(v.co) for v in tb.verts}
        for f in tb.faces:
            try: nf = self.bm.faces.new([vmap[v] for v in f.verts])
            except ValueError: continue
            nf.smooth = f.smooth
            if uvs:
                us = [uvs[v][0] for v in f.verts if uvs[v][0] is not None]
                wrap = us and max(us) - min(us) > 0.5
            for l, ol in zip(nf.loops, f.loops):
                c = colour(ol.vert.co, ol.vert.normal, f.normal)
                a = alpha(ol.vert.co) if alpha else 1.0
                l[self.col] = (lin2srgb(c[0]), lin2srgb(c[1]), lin2srgb(c[2]), a)
                p = ol.vert.co
                if uvs:
                    u, v = uvs[ol.vert]
                    if u is None:                                   # pole: middle of the face's u range
                        u = (min(us) + max(us)) / 2 if not wrap else (min(us) + 1 + max(us)) / 2
                    elif wrap and u < 0.5:
                        u += 1.0
                    l[self.uv].uv = (u, v)
                else:
                    l[self.uv].uv = (p.x + p.z * 0.5, p.y + p.z * 0.5)
        tb.free(); self.parts += 1

    def finish(self, name, mat):
        old = bpy.data.objects.get(name)
        if old:
            m = old.data; bpy.data.objects.remove(old, do_unlink=True); bpy.data.meshes.remove(m)
        self.bm.normal_update()
        me = bpy.data.meshes.new(name); self.bm.to_mesh(me); self.bm.free()
        me.materials.append(mat)
        col = bpy.data.collections.get(COLL) or bpy.data.collections.new(COLL)
        if col.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(col)
        ob = bpy.data.objects.new(name, me); col.objects.link(ob)
        return ob


# ---------------------------------------------------------------- stones
def stone(M, rng, centre, size, yaw):
    tb = bmesh.new()
    bmesh.ops.create_icosphere(tb, subdivisions=2, radius=1.0)
    s = rng.uniform(0, 100)
    for v in tb.verts:
        d = v.co.copy()
        d *= 1.0 + 0.16 * noise.noise(d * 1.3 + Vector((s, 0, 0))) + 0.06 * noise.noise(d * 3.0 + Vector((0, s, 0)))
        d.z = d.z * 0.62 if d.z > 0 else d.z * 0.35          # flat-ish, sits in the ground
        v.co = Matrix.Rotation(yaw, 3, 'Z') @ Vector((d.x * size[0], d.y * size[1], d.z * size[2])) + centre
    for f in tb.faces: f.smooth = True
    base = scale(mix(STONE_COOL, STONE_WARM, rng.random()), rng.uniform(0.85, 1.15))

    def colour(p, n, fn_):
        c = scale(base, 0.9 + 0.18 * noise.noise(p * 9.0 + Vector((s, 0, 0))))
        c = mix(c, STONE_LIGHT, c01(n.z) * 0.25)                                     # sunlit tops lighter
        inward = -(Vector((p.x, p.y, 0)).normalized()).dot(Vector((n.x, n.y, 0)))     # faces looking at the fire
        c = mix(c, SOOT, c01(inward * 1.6 - 0.2) * 0.85)
        c = mix(c, MOSS, c01(noise.noise(p * 6.0 + Vector((3, s, 1))) * 2.0 - 0.4) * c01(-inward) * 0.6)
        if p.z < 0.03: c = scale(c, 0.7)
        return c
    M.add(tb, colour)


def stone_ring(M, rng, n=11, R=0.6):
    a0 = rng.uniform(0, 1)
    for i in range(n):
        a = a0 + 2 * math.pi * i / n + rng.uniform(-0.06, 0.06)
        r = R + rng.uniform(-0.03, 0.03)
        sz = (rng.uniform(0.15, 0.19), rng.uniform(0.11, 0.14), rng.uniform(0.13, 0.19))
        stone(M, rng, Vector((r * math.cos(a), r * math.sin(a), 0.02)), sz, a + rng.uniform(-0.2, 0.2))


# ---------------------------------------------------------------- ash bed
def ash_bed(M, rng, R=0.52):
    tb = bmesh.new()
    rings, segs = 6, 24
    cen = tb.verts.new((0, 0, 0.055))
    grid = []
    for j in range(1, rings + 1):
        rr = R * j / rings
        row = []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            p = Vector((rr * math.cos(a), rr * math.sin(a), 0))
            p.z = 0.055 * (1 - (j / rings) ** 2) + 0.012 * noise.noise(p * 6.0) - 0.01 * (j == rings)
            row.append(tb.verts.new(p))
        grid.append(row)
    for i in range(segs):
        tb.faces.new((cen, grid[0][i], grid[0][(i + 1) % segs]))
    for j in range(rings - 1):
        for i in range(segs):
            i2 = (i + 1) % segs
            tb.faces.new((grid[j][i], grid[j + 1][i], grid[j + 1][i2], grid[j][i2]))
    for f in tb.faces: f.smooth = True

    def colour(p, n, fn_):
        r = math.hypot(p.x, p.y) / R
        c = mix(ASH_DARK, ASH, c01(noise.noise(p * 7.0) * 1.5 + 0.5))
        c = mix(c, ASH_DARK, c01(1.0 - r * 1.6) * 0.8)                                # charcoal in the middle
        e = c01(noise.noise(p * 11.0 + Vector((5, 1, 0))) * 3.0 - 0.6) * c01(1.0 - r * 1.3)
        return mix(c, EMBER, e)                                                      # glowing ember spots
    M.add(tb, colour)


# ---------------------------------------------------------------- logs
def log(M, rng, a, b, r, char_end=1.0):
    """cylinder from a to b (8 sides, slightly irregular), charred towards the fire end (b if char_end=1)"""
    a = Vector(a); b = Vector(b); ax = b - a; L = ax.length
    tb = bmesh.new()
    bmesh.ops.create_cone(tb, cap_ends=True, cap_tris=False, segments=8, radius1=r, radius2=r * 0.92, depth=L)
    ksplit = 4
    for k in range(1, ksplit):
        z = -L / 2 + L * k / ksplit
        bmesh.ops.bisect_plane(tb, geom=list(tb.verts) + list(tb.edges) + list(tb.faces), dist=1e-5,
                               plane_co=(0, 0, z), plane_no=(0, 0, 1))
    s = rng.uniform(0, 100)
    for v in tb.verts:
        rad = Vector((v.co.x, v.co.y, 0))
        if rad.length > 1e-4:
            v.co += rad.normalized() * r * 0.12 * noise.noise(Vector((v.co.x * 9, v.co.y * 9, v.co.z * 3 + s)))
    rot = Vector((0, 0, 1)).rotation_difference(ax.normalized()).to_matrix()
    roll = Matrix.Rotation(rng.uniform(0, 6.28), 3, 'Z')
    for v in tb.verts:
        v.co = rot @ (roll @ v.co) + (a + b) / 2
    for f in tb.faces:
        f.smooth = len(f.verts) == 4
    axn = ax.normalized()

    def colour(p, n, fn_):
        t = (p - a).dot(axn) / L                                     # 0 at a, 1 at b
        tf = t if char_end > 0.5 else 1 - t
        if abs(fn_.dot(axn)) > 0.9:                                  # cut end: light wood rings, dark rim
            q = p - (a + axn * (p - a).dot(axn))
            rr = q.length / r
            c = mix(WOOD, WOOD_RING, 0.5 + 0.5 * math.sin(rr * 18.0))
            c = mix(c, BARK_DARK, c01((rr - 0.78) * 6))
            return mix(c, CHAR, c01(tf * 2.2 - 1.1))
        g = noise.noise(Vector((p.x * 14, p.y * 14, p.z * 4)) + Vector((s, 0, 0)))
        c = mix(BARK, BARK_DARK, c01(g * 1.4 + 0.5))
        c = mix(c, CHAR, c01(tf * 2.0 - 0.9))                        # charred near the fire
        return mix(c, EMBER, c01(tf * 3.0 - 2.55) * c01(g * 2 + 0.6) * 0.8)   # glowing tips
    M.add(tb, colour)


def logs(M, rng):
    n = 6
    top = Vector((0, 0, 0.66))
    for i in range(n):
        a = 2 * math.pi * i / n + rng.uniform(-0.15, 0.15) + 0.3
        foot = Vector((0.4 * math.cos(a), 0.4 * math.sin(a), 0.02))
        d = (top - foot).normalized()
        tip = top + d * rng.uniform(0.04, 0.12) + Vector((rng.uniform(-0.03, 0.03), rng.uniform(-0.03, 0.03), 0))
        log(M, rng, foot, tip, rng.uniform(0.05, 0.065))
    # two logs lying across the base
    for a, off in ((0.35, 0.05), (0.35 + math.pi / 2 + 0.25, -0.04)):
        d = Vector((math.cos(a), math.sin(a), 0)); side = Vector((-d.y, d.x, 0)) * off
        log(M, rng, -d * 0.5 + side + Vector((0, 0, 0.07)), d * 0.5 + side + Vector((0, 0, 0.09)), 0.07, char_end=1.0)


# ---------------------------------------------------------------- flame
def flame_tongue(M, base, height, radius, lean, twist, col_bot, col_top, seed):
    rings, segs = 9, 10
    tb = bmesh.new()
    bottom = tb.verts.new(base + Vector((0, 0, -0.02)))
    u0 = (seed * 0.37) % 1.0                         # each tongue samples a different part of the noise texture
    uvs = {bottom: (None, 0.0)}
    rows = []
    for k in range(1, rings + 1):
        t = k / (rings + 1)
        prof = math.sin(math.pi * min(1.0, t ** 0.62)) * (1 - t) ** 0.25    # round base, long pointed top
        rr = radius * prof
        off = lean * t ** 2 + Vector((0.03 * math.sin(t * 7 + seed), 0.03 * math.cos(t * 6 + seed), 0)) * t
        row = []
        for i in range(segs):
            a = 2 * math.pi * i / segs + twist * t
            wob = 1 + 0.12 * math.sin(a * 3 + seed + t * 4)
            vt = tb.verts.new(base + off + Vector((rr * wob * math.cos(a), rr * wob * math.sin(a), height * t)))
            uvs[vt] = ((u0 + i / segs) % 1.0, t * height / 0.6)          # v in ~metres/0.6 -> same noise scale on all tongues
            row.append(vt)
        rows.append(row)
    tip = tb.verts.new(base + lean + Vector((0, 0, height)))
    uvs[tip] = (None, height / 0.6)
    for i in range(segs):
        i2 = (i + 1) % segs
        tb.faces.new((bottom, rows[0][i2], rows[0][i]))
        tb.faces.new((rows[-1][i], rows[-1][i2], tip))
    for k in range(rings - 1):
        for i in range(segs):
            i2 = (i + 1) % segs
            tb.faces.new((rows[k][i], rows[k][i2], rows[k + 1][i2], rows[k + 1][i]))
    for f in tb.faces: f.smooth = True
    z0 = base.z

    def colour(p, n, fn_):
        return mix(col_bot, col_top, c01((p.z - z0) / height) ** 0.8)

    def alpha(p):
        return c01((p.z - z0) / height) ** 1.2
    M.add(tb, colour, alpha, uvs)


def flame(M, rng):
    ORANGE = (1.0, 0.42, 0.06); RED = (0.75, 0.1, 0.02); YELLOW = (1.0, 0.8, 0.3); DEEP = (0.85, 0.22, 0.03)
    flame_tongue(M, Vector((0, 0, 0.1)), 1.15, 0.22, Vector((0.02, -0.03, 0)), 1.2, ORANGE, RED, 0.0)
    n = 5
    for i in range(n):
        a = 2 * math.pi * i / n + rng.uniform(-0.2, 0.2)
        d = Vector((math.cos(a), math.sin(a), 0))
        flame_tongue(M, Vector((0, 0, 0.1)) + d * 0.14, rng.uniform(0.55, 0.8), rng.uniform(0.11, 0.14),
                     d * rng.uniform(0.08, 0.14), rng.uniform(-1.5, 1.5), DEEP, RED, rng.uniform(0, 6))
    flame_tongue(M, Vector((0, 0, 0.1)), 0.62, 0.13, Vector((0, 0, 0)), 0.8, YELLOW, ORANGE, 2.0)


def flame_noise_texture(res=512, seed=3):
    """Tileable grey fBm, cells stretched along V (vertical licks) -> Export/Textures/Bonfire/T_FlameNoise.png.
    UE pans it upward along V on the flame tongues (M_BonfireFlame)."""
    import numpy as np
    rng = np.random.default_rng(seed)

    def value_noise(cx, cy):
        g = rng.random((cy, cx))
        x = np.arange(res) * cx / res; y = np.arange(res) * cy / res
        x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
        fx = x - x0; fy = y - y0
        fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
        x1 = (x0 + 1) % cx; y1 = (y0 + 1) % cy
        a = g[y0][:, x0]; b = g[y0][:, x1]; c = g[y1][:, x0]; d = g[y1][:, x1]
        top = a + (b - a) * fx[None, :]; bot = c + (d - c) * fx[None, :]
        return top + (bot - top) * fy[:, None]

    n = np.zeros((res, res)); amp = 1.0; tot = 0
    for o, (cx, cy) in enumerate(((6, 3), (12, 6), (24, 12), (48, 24), (96, 48))):
        n += value_noise(cx, cy) * amp; tot += amp; amp *= 0.55
    n /= tot
    n = (n - n.min()) / (n.max() - n.min())
    n = np.clip((n - 0.5) * 1.6 + 0.5, 0, 1)                      # more contrast
    out_dir = os.path.join(ROOT, r"Export\Textures\Bonfire"); os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "T_FlameNoise.png")
    img = bpy.data.images.get('T_FlameNoise') or bpy.data.images.new('T_FlameNoise', res, res, alpha=False)
    img.colorspace_settings.name = 'Non-Color'
    px = np.ones((res, res, 4), np.float32); px[..., 0] = px[..., 1] = px[..., 2] = n
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    print('BONFIRE texture', path)
    return img


# ---------------------------------------------------------------- collision / build
def ucx(name):
    for o in [o for o in bpy.data.objects if o.name.startswith('UCX_' + name + '_')]:
        m = o.data; bpy.data.objects.remove(o, do_unlink=True); bpy.data.meshes.remove(m)
    bm = bmesh.new()
    for z in (0.0, 0.45):
        for i in range(8):
            a = 2 * math.pi * (i + 0.5) / 8
            bm.verts.new((0.74 * math.cos(a), 0.74 * math.sin(a), z))
    bmesh.ops.convex_hull(bm, input=bm.verts)
    nm = f'UCX_{name}_00'; me = bpy.data.meshes.new(nm); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(nm, me); bpy.data.collections[COLL].objects.link(o); o.display_type = 'WIRE'
    return [o]


def flame_material():
    m = bpy.data.materials.get('M_BonfireFlame')
    if m: return m
    m = bpy.data.materials.new('M_BonfireFlame'); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    ca = nt.nodes.new('ShaderNodeVertexColor'); ca.layer_name = 'Col'
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = 4.0
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(ca.outputs['Color'], em.inputs['Color']); nt.links.new(em.outputs[0], out.inputs[0])
    return m


def build(seed=7):
    rng = random.Random(seed)
    M = Mesh()
    stone_ring(M, rng); ash_bed(M, rng); logs(M, rng)
    body = M.finish('SM_Bonfire', material('M_Stylized_Prop', False))
    col = ucx('SM_Bonfire')
    tris = export(body, col)
    print(f'BONFIRE SM_Bonfire: {M.parts} parts, {tris} tris')
    F = Mesh(); flame(F, rng)
    fl = F.finish('SM_BonfireFlame', flame_material())
    tris = export(fl)
    print(f'BONFIRE SM_BonfireFlame: {F.parts} tongues, {tris} tris')
    return body, fl


def previews(body, fl):
    CMP = os.path.join(ROOT, r"Export\Blender\compare"); os.makedirs(CMP, exist_ok=True)
    sc = bpy.context.scene; tmp = []
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.25, radius2=0.25, depth=1.8,
                                            matrix=Matrix.Translation((1.4, 0.6, 0.9)))
    hm = bpy.data.meshes.new('PREV_human'); bm.to_mesh(hm); bm.free()
    hu = bpy.data.objects.new('PREV_human', hm); sc.collection.objects.link(hu); tmp.append(hu)
    gm = bpy.data.meshes.new('PREV_ground'); gm.from_pydata([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], [], [(0, 1, 2, 3)])
    g = bpy.data.objects.new('PREV_ground', gm); sc.collection.objects.link(g); tmp.append(g)
    for ob in bpy.data.objects:
        if ob.name.startswith('UCX_'): ob.hide_render = True
    cam = bpy.data.objects.new('PREV_cam', bpy.data.cameras.new('PREV_cam')); sc.collection.objects.link(cam); tmp.append(cam)
    sc.camera = cam; sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading; sh.light = 'STUDIO'; sh.color_type = 'VERTEX'
    sh.show_cavity = True; sh.show_shadows = False
    for o in (body, fl):
        o.data.color_attributes.active_color = o.data.color_attributes['Col']
    sc.render.resolution_x = 900; sc.render.resolution_y = 900
    outs = []
    for tag, loc, look_at, lens, show_flame in (('side', (2.6, -3.0, 1.6), (0, 0, 0.45), 40, True),
                                               ('top', (0.4, -0.8, 3.2), (0, 0, 0.2), 32, False),
                                               ('logs', (1.6, -1.7, 1.0), (0, 0, 0.35), 45, False)):
        fl.hide_render = not show_flame
        cam.location = loc; cam.data.lens = lens
        cam.rotation_euler = (Vector(look_at) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        p = os.path.join(CMP, f'bonfire_{tag}.png'); sc.render.filepath = p
        bpy.ops.render.render(write_still=True); outs.append(p)
    fl.hide_render = False
    for o in tmp:
        d = o.data; bpy.data.objects.remove(o, do_unlink=True)
        if d and d.users == 0:
            (bpy.data.meshes if isinstance(d, bpy.types.Mesh) else bpy.data.cameras).remove(d)
    return outs


if __name__ == '__main__':
    for o in list(bpy.data.objects):
        if o.name in ('Cube',): bpy.data.objects.remove(o, do_unlink=True)
    flame_noise_texture()
    body, fl = build()
    for p in previews(body, fl): print('BONFIRE preview', p)
    out = os.path.join(ROOT, r"Export\Blender\Bonfire.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print('BONFIRE saved', out)
