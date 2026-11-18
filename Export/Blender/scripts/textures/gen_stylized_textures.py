# Stylized tileable ground/surface textures (2048 px, one tile ~ TILE_M metres):
#   Grass, Stone (pebbles), Rock, FallenLeaves, Snow, Sand, Soil, Water
# For each: T_Stylized_<Name>_BC (sRGB colour), _N (DirectX normal), _ARH (R ambient occlusion, G roughness, B height)
# into Export/Textures/Stylized/.
# Method: seamless noise from a 4D torus mapping baked with Cycles (same trick as gen_bark_texture.py),
# plus shapes (grass strokes, pebbles, leaves) stamped with numpy using wrap-around indexing -> everything tiles.
# Look: stylized = flat-ish colour areas, soft gradients, simple shapes, gentle normals.
import bpy, math, os, random
import numpy as np

OUT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Textures\Stylized"
RES = 2048
TILE_M = 2.0


# ------------------------------------------------------------------ baking seamless noise
def _torus(nt, sep, n_u, n_v, off):
    def m(op, a, val):
        n = nt.nodes.new('ShaderNodeMath'); n.operation = op
        nt.links.new(a, n.inputs[0]); n.inputs[1].default_value = val
        return n.outputs[0]

    def f(op, a):
        n = nt.nodes.new('ShaderNodeMath'); n.operation = op; nt.links.new(a, n.inputs[0]); return n.outputs[0]
    th = m('MULTIPLY', sep.outputs['X'], 2 * math.pi); ph = m('MULTIPLY', sep.outputs['Y'], 2 * math.pi)
    ru = n_u / (2 * math.pi); rv = n_v / (2 * math.pi)
    x = m('ADD', m('MULTIPLY', f('COSINE', th), ru), off[0]); y = m('ADD', m('MULTIPLY', f('SINE', th), ru), off[1])
    z = m('ADD', m('MULTIPLY', f('COSINE', ph), rv), off[2]); w = m('ADD', m('MULTIPLY', f('SINE', ph), rv), off[3])
    cv = nt.nodes.new('ShaderNodeCombineXYZ')
    nt.links.new(x, cv.inputs[0]); nt.links.new(y, cv.inputs[1]); nt.links.new(z, cv.inputs[2])
    return cv.outputs[0], w


def _channel(nt, sep, spec):
    """spec = (kind, n_u, n_v, seed, extra) -> socket. kind: noise | f1 | edge | cell"""
    kind, nu, nv, seed = spec[:4]; extra = spec[4] if len(spec) > 4 else {}
    off = (seed * 1.37, seed * 2.11, seed * 0.73, seed * 1.91)
    vec, w = _torus(nt, sep, nu, nv, off)
    if extra.get('warp'):
        wn = nt.nodes.new('ShaderNodeTexNoise'); wn.noise_dimensions = '4D'
        nt.links.new(vec, wn.inputs['Vector']); nt.links.new(w, wn.inputs['W']); wn.inputs['Scale'].default_value = 0.7
        vm = nt.nodes.new('ShaderNodeVectorMath'); vm.operation = 'MULTIPLY_ADD'
        nt.links.new(wn.outputs['Color'], vm.inputs[0]); vm.inputs[1].default_value = (extra['warp'],) * 3
        nt.links.new(vec, vm.inputs[2]); vec = vm.outputs[0]
    if kind == 'noise':
        n = nt.nodes.new('ShaderNodeTexNoise'); n.noise_dimensions = '4D'
        nt.links.new(vec, n.inputs['Vector']); nt.links.new(w, n.inputs['W'])
        n.inputs['Scale'].default_value = 1.0; n.inputs['Detail'].default_value = extra.get('detail', 4)
        n.inputs['Roughness'].default_value = extra.get('rough', 0.5)
        return n.outputs['Fac']
    v = nt.nodes.new('ShaderNodeTexVoronoi'); v.voronoi_dimensions = '4D'
    v.feature = {'f1': 'F1', 'edge': 'DISTANCE_TO_EDGE', 'cell': 'F1'}[kind]
    nt.links.new(vec, v.inputs['Vector']); nt.links.new(w, v.inputs['W']); v.inputs['Scale'].default_value = 1.0
    if 'randomness' in extra:
        v.inputs['Randomness'].default_value = extra['randomness']
    if kind == 'cell':
        sc = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(v.outputs['Color'], sc.inputs[0]); return sc.outputs[0]
    return v.outputs['Distance']


def bake(specs):
    """Bake up to 3 channel specs per pass; returns list of (RES, RES) float arrays."""
    sc = bpy.context.scene
    prev = sc.render.engine
    try:
        sc.render.engine = 'CYCLES'
    except TypeError:
        pass
    sc.cycles.samples = 1
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -200))
    ob = bpy.context.active_object; ob.name = '_TexBakePlane'
    mat = bpy.data.materials.new('_TexBake'); mat.use_nodes = True; ob.data.materials.append(mat)
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        if o:
            o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    out = []
    for i in range(0, len(specs), 3):
        group = specs[i:i + 3]
        nt = mat.node_tree; nt.nodes.clear()
        tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(tc.outputs['UV'], sep.inputs[0])
        cc = nt.nodes.new('ShaderNodeCombineColor')
        for k, spec in enumerate(group):
            nt.links.new(_channel(nt, sep, spec), cc.inputs[k])
        em = nt.nodes.new('ShaderNodeEmission'); nt.links.new(cc.outputs[0], em.inputs['Color'])
        o_ = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(em.outputs[0], o_.inputs['Surface'])
        img = bpy.data.images.new('_tex_bake', RES, RES, alpha=False, float_buffer=True)
        img.colorspace_settings.name = 'Non-Color'
        tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = img; nt.nodes.active = tn
        bpy.ops.object.bake(type='EMIT')
        a = np.empty(RES * RES * 4, np.float32); img.pixels.foreach_get(a); bpy.data.images.remove(img)
        a = a.reshape(RES, RES, 4)
        for k in range(len(group)):
            out.append(a[:, :, k].copy())
    bpy.data.objects.remove(ob, do_unlink=True); bpy.data.materials.remove(mat)
    try:
        sc.render.engine = prev
    except TypeError:
        pass
    return out


# ------------------------------------------------------------------ numpy helpers
def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def blur(x, r):
    for axis in (0, 1):
        acc = np.zeros_like(x)
        for k in range(-r, r + 1):
            acc += np.roll(x, k, axis=axis)
        x = acc / (2 * r + 1)
    return x


def lerp3(a, b, t):
    a = np.asarray(a, np.float32); b = np.asarray(b, np.float32)
    return a * (1 - t[..., None]) + b * t[..., None]


def stamp(canvas_h, canvas_c, cx, cy, mask, height, color, mode='over'):
    """Stamp a (h, w) mask at (cx, cy) with wrap-around. color: (h, w, 3) or rgb. height: (h, w) added/maxed."""
    h, w = mask.shape
    ys = (np.arange(h) + int(cy) - h // 2) % RES; xs = (np.arange(w) + int(cx) - w // 2) % RES
    iy, ix = np.ix_(ys, xs)
    m = mask[..., None]
    col = color if np.ndim(color) == 3 else np.broadcast_to(np.asarray(color, np.float32), (h, w, 3))
    canvas_c[iy, ix] = canvas_c[iy, ix] * (1 - m) + col * m
    if mode == 'over':
        canvas_h[iy, ix] = canvas_h[iy, ix] * (1 - mask) + height * mask
    else:
        canvas_h[iy, ix] = np.maximum(canvas_h[iy, ix], height * mask)


def shape_grid(size, angle):
    """Local coordinates (u along angle, v across) in [-1, 1] for a square stamp of `size` pixels."""
    r = np.linspace(-1, 1, size, dtype=np.float32)
    X, Y = np.meshgrid(r, r)
    ca, sa = math.cos(angle), math.sin(angle)
    return X * ca + Y * sa, -X * sa + Y * ca


def normal_ao(h, depth_m, ao_r=8, ao_k=2.0):
    px = TILE_M / RES
    dhdu = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * depth_m / (2 * px)
    dhdv = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * depth_m / (2 * px)
    n = np.stack([-dhdu, -dhdv, np.ones_like(h)], axis=2); n /= np.linalg.norm(n, axis=2, keepdims=True)
    gl = n * 0.5 + 0.5; dx = gl.copy(); dx[:, :, 1] = 1 - dx[:, :, 1]
    ao = 1 - np.clip((blur(h, ao_r) - h) * ao_k, 0, 0.6)
    return dx, gl, ao


def save_png(name, rgb, srgb):
    os.makedirs(OUT, exist_ok=True)
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, RES, RES, alpha=False, float_buffer=False)
    img.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
    if srgb:
        rgb = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.power(np.clip(rgb, 0, None), 1 / 2.4) - 0.055)
    rgba = np.concatenate([np.clip(rgb, 0, 1), np.ones((RES, RES, 1), np.float32)], axis=2).astype(np.float32)
    img.pixels.foreach_set(rgba.ravel()); img.filepath_raw = os.path.join(OUT, name + '.png'); img.file_format = 'PNG'
    img.save(); bpy.data.images.remove(img)


def write_set(name, col, h, rough, depth_m, ao_r=8, ao_k=2.0):
    h = (h - h.min()) / max(h.max() - h.min(), 1e-6)
    dx, gl, ao = normal_ao(h, depth_m, ao_r, ao_k)
    save_png(f'T_Stylized_{name}_BC', (col * (0.55 + 0.45 * ao[..., None])).astype(np.float32), True)
    save_png(f'T_Stylized_{name}_N', dx.astype(np.float32), False)
    save_png(f'T_Stylized_{name}_ARH', np.stack([ao, rough, h], axis=2).astype(np.float32), False)
    return float(col.mean())


# ------------------------------------------------------------------ the eight textures
def tex_grass(rng):
    big, mid, fine = bake([('noise', 3, 3, 1, {'detail': 3}), ('noise', 9, 9, 2, {'detail': 3}),
                           ('noise', 40, 40, 3, {'detail': 2})])
    DARK = (0.022, 0.07, 0.012); MID = (0.06, 0.17, 0.022); LIGHT = (0.15, 0.31, 0.04); YEL = (0.25, 0.33, 0.06)
    t = np.clip(0.5 + (big - 0.5) * 1.8 + (mid - 0.5) * 0.8, 0, 1)
    col = lerp3(DARK, MID, smooth(0.2, 0.55, t)); col = lerp3(col, LIGHT, smooth(0.55, 0.9, t) * 0.7)
    h = 0.3 * mid + 0.1 * fine
    # stylized blade strokes: short tapered strokes, dark root -> light tip
    for k in range(5200):
        size = rng.randint(28, 52); ang = rng.uniform(-0.6, 0.6) - math.pi / 2
        U, V = shape_grid(size, ang)
        L = (U + 1) / 2                                   # 0 root .. 1 tip
        wdt = 0.28 * (1 - 0.75 * L)
        mask = (np.abs(V) < wdt) & (U > -1) & (U < 1)
        mask = mask.astype(np.float32) * smooth(0.0, 0.15, (wdt - np.abs(V)))
        base = np.asarray(lerp3(MID, LIGHT, np.array(rng.random())), np.float32)
        tip = np.asarray(lerp3(LIGHT, YEL, np.array(rng.random() * 0.6)), np.float32)
        colr = (base[None, None, :] * (1 - L[..., None]) + tip[None, None, :] * L[..., None]) * (0.8 + 0.4 * rng.random())
        stamp(h, col, rng.uniform(0, RES), rng.uniform(0, RES), mask, (0.4 + 0.6 * L) * 0.9, colr, mode='max')
    rough = np.full_like(h, 0.85)
    return write_set('Grass', col, h, rough, 0.012)


def tex_stone(rng):
    # pebble ground: round/oval stones stamped one by one (overlapping), dark soil between them
    big, fine = bake([('noise', 3, 3, 4, {'detail': 3}), ('noise', 30, 30, 5, {'detail': 4})])
    SOIL_A = (0.035, 0.02, 0.01); SOIL_B = (0.075, 0.042, 0.02)
    col = lerp3(SOIL_A, SOIL_B, big); h = 0.05 * fine
    # v2: warmer / cooler, more saturated pebbles (v1 was a flat grey mix that read as blurry on the landscape)
    PAL = [(0.34, 0.26, 0.17), (0.25, 0.26, 0.28), (0.40, 0.32, 0.21), (0.21, 0.22, 0.25), (0.36, 0.21, 0.11),
           (0.29, 0.28, 0.26)]
    for k in range(1100):
        size = rng.randint(60, 150); ang = rng.uniform(0, math.pi)
        U, V = shape_grid(size, ang)
        el = rng.uniform(1.0, 1.7)
        d = np.sqrt(U ** 2 + (V * el) ** 2)
        mask = smooth(0.0, 0.08, 0.92 - d)
        dome = np.sqrt(np.clip(1 - d * d, 0, 1))
        c = np.asarray(PAL[rng.randrange(len(PAL))], np.float32) * (0.8 + 0.4 * rng.random())
        light = 0.6 + 0.55 * dome + 0.2 * (-U * 0.5 + V * 0.5)         # soft top light, stylized (strong)
        stamp(h, col, rng.uniform(0, RES), rng.uniform(0, RES), mask, 0.3 + 0.7 * dome, c[None, None, :] * light[..., None],
              mode='max')
    col = col * (0.92 + 0.16 * fine[..., None])
    rough = np.full_like(h, 0.8)
    return write_set('Stone', col, h, rough, 0.03, ao_r=10, ao_k=2.5)


def tex_rock(rng):
    f1, cell, edge, big, fine, crack = bake([('f1', 5, 5, 6, {'warp': 0.5}), ('cell', 5, 5, 6, {'warp': 0.5}),
                                             ('edge', 5, 5, 6, {'warp': 0.5}), ('noise', 2, 2, 7, {'detail': 3}),
                                             ('noise', 25, 25, 8, {'detail': 4}), ('edge', 14, 14, 9, {'warp': 0.4})])
    # stylized faceted rock: each cell is a tilted flat plane (stepped look), dark cracks between cells
    gx = np.roll(cell, -1, 1) - cell
    plane = cell * 0.6 + (f1 - f1.mean()) * 0.6
    e = edge / np.percentile(edge, 98); c2 = crack / np.percentile(crack, 98)
    h = plane * smooth(0.0, 0.08, e) + 0.06 * fine - 0.12 * (1 - smooth(0.0, 0.05, c2))
    # v2: wider value range and warm/cool facets (v1 was nearly colourless grey and read as blurry)
    DARK = (0.03, 0.035, 0.05); MID = (0.15, 0.15, 0.17); LIGHT = (0.42, 0.40, 0.36)
    WARM = (0.40, 0.27, 0.15); COOL = (0.17, 0.21, 0.30)
    t = np.clip(0.25 + cell * 0.75 + (fine - 0.5) * 0.3, 0, 1)
    col = lerp3(DARK, MID, smooth(0.0, 0.45, t)); col = lerp3(col, LIGHT, smooth(0.5, 1.0, t))
    col = lerp3(col, WARM, smooth(0.45, 0.8, big) * 0.5)
    col = lerp3(col, COOL, smooth(0.55, 0.2, big) * 0.35)
    col = col * (0.4 + 0.6 * smooth(0.0, 0.08, e))[..., None] * (0.5 + 0.5 * smooth(0.0, 0.05, c2))[..., None]
    rough = np.full_like(h, 0.82)
    return write_set('Rock', col, h, rough, 0.05, ao_r=10, ao_k=2.0)


def tex_fallen_leaves(rng):
    big, fine = bake([('noise', 3, 3, 10, {'detail': 3}), ('noise', 30, 30, 11, {'detail': 4})])
    SOIL_A = (0.04, 0.025, 0.015); SOIL_B = (0.09, 0.055, 0.03)
    col = lerp3(SOIL_A, SOIL_B, big); h = 0.05 * fine
    PAL = [(0.75, 0.42, 0.03), (0.70, 0.18, 0.02), (0.55, 0.06, 0.02), (0.36, 0.17, 0.05), (0.50, 0.32, 0.08),
           (0.82, 0.55, 0.06)]
    for k in range(1500):
        size = rng.randint(70, 150); ang = rng.uniform(0, 2 * math.pi)
        U, V = shape_grid(size, ang)
        L = (U + 1) / 2
        wdt = 0.55 * np.clip(np.sin(np.clip(L, 0, 1) * math.pi), 0, None) ** 0.8   # pointed leaf outline
        mask = smooth(0.0, 0.06, wdt - np.abs(V)) * (U > -0.95) * (U < 0.95)
        base = np.asarray(PAL[rng.randrange(len(PAL))], np.float32) * (0.75 + 0.5 * rng.random())
        vein = 1 - 0.3 * np.exp(-(V / 0.04) ** 2)                       # midrib
        edge_dark = 0.75 + 0.25 * smooth(0.0, 0.2, wdt - np.abs(V))
        colr = base[None, None, :] * (vein * edge_dark * (0.85 + 0.3 * L))[..., None]
        z = k / 1500.0
        stamp(h, col, rng.uniform(0, RES), rng.uniform(0, RES), mask.astype(np.float32),
              0.2 + 0.8 * z + 0.05 * np.abs(V), colr, mode='over')
    rough = np.full_like(h, 0.75)
    return write_set('FallenLeaves', col, h, rough, 0.015, ao_r=6, ao_k=3.0)


def tex_snow(rng):
    big, mid, fine = bake([('noise', 3, 3, 12, {'detail': 2}), ('noise', 8, 8, 13, {'detail': 3}),
                           ('noise', 60, 60, 14, {'detail': 2})])
    h = 0.45 * big + 0.45 * mid + 0.04 * fine
    LOW = (0.60, 0.68, 0.80); HIGH = (0.88, 0.90, 0.93)
    col = lerp3(LOW, HIGH, smooth(0.15, 0.6, (h - h.min()) / (h.max() - h.min())))
    sparkle = (fine > np.percentile(fine, 99.6)).astype(np.float32)
    col = col + sparkle[..., None] * 0.12
    rough = 0.7 - 0.3 * sparkle
    return write_set('Snow', col, h, rough, 0.06, ao_r=14, ao_k=1.5)


def tex_sand(rng):
    warp, big, fine = bake([('noise', 2, 3, 15, {'detail': 2}), ('noise', 3, 3, 16, {'detail': 3}),
                            ('noise', 90, 90, 17, {'detail': 2})])
    v = np.linspace(0, 1, RES, endpoint=False, dtype=np.float32)[:, None] * np.ones((1, RES), np.float32)
    phase = (v * 14 + (warp - 0.5) * 3.0) * 2 * math.pi                # 14 ripples per tile, wavy
    rip = 0.5 + 0.5 * np.sin(phase)
    rip = rip ** 1.6                                                    # sharper crests, wide troughs
    h = 0.6 * rip + 0.35 * big + 0.04 * fine
    DARK = (0.34, 0.24, 0.13); LIGHT = (0.70, 0.56, 0.36)
    col = lerp3(DARK, LIGHT, smooth(0.15, 0.85, 0.6 * rip + 0.4 * big))
    grains = (fine > np.percentile(fine, 97)).astype(np.float32)
    col = col * (1 - 0.25 * grains[..., None])
    rough = np.full_like(h, 0.92)
    return write_set('Sand', col, h, rough, 0.015, ao_r=8, ao_k=1.5)


def tex_soil(rng):
    lump, big, fine = bake([('noise', 14, 14, 18, {'detail': 3, 'rough': 0.6}), ('noise', 3, 3, 19, {'detail': 3}),
                            ('noise', 45, 45, 20, {'detail': 4})])
    clods = smooth(0.3, 0.75, lump)                      # soft lumps, no crack network
    h = 0.35 * clods + 0.45 * big + 0.15 * fine
    # v2: richer, warmer brown with a wider dark->light range (v1 was flat and read as blurry)
    DARK = (0.035, 0.018, 0.008); MID = (0.12, 0.062, 0.026); LIGHT = (0.26, 0.15, 0.07)
    col = lerp3(DARK, MID, smooth(0.0, 0.5, clods)); col = lerp3(col, LIGHT, smooth(0.45, 0.95, 0.5 * clods + 0.5 * big) * 0.85)
    for k in range(700):  # small pebbles
        size = rng.randint(10, 26); ang = rng.uniform(0, math.pi)
        U, V = shape_grid(size, ang)
        d = np.sqrt(U ** 2 + (V * rng.uniform(1.0, 1.6)) ** 2)
        mask = smooth(0.0, 0.25, 0.9 - d)
        c = np.asarray((0.30, 0.24, 0.17), np.float32) * (0.7 + 0.5 * rng.random())
        colr = c[None, None, :] * (0.8 + 0.4 * (1 - d))[..., None]
        stamp(h, col, rng.uniform(0, RES), rng.uniform(0, RES), mask, 0.9 + 0.1 * (1 - d), colr, mode='max')
    rough = np.full_like(h, 0.95)
    return write_set('Soil', col, h, rough, 0.02, ao_r=8, ao_k=2.2)


def tex_water(rng):
    caustic, caustic2, big = bake([('edge', 6, 6, 21, {'warp': 0.6}), ('edge', 9, 9, 22, {'warp': 0.7}),
                                   ('noise', 3, 3, 23, {'detail': 3})])
    c1 = 1 - smooth(0.0, 0.06, caustic / np.percentile(caustic, 98))
    c2 = 1 - smooth(0.0, 0.05, caustic2 / np.percentile(caustic2, 98))
    lines = np.clip(c1 * 0.8 + c2 * 0.5, 0, 1)
    DEEP = (0.01, 0.08, 0.14); SHALLOW = (0.03, 0.24, 0.32); LINE = (0.35, 0.72, 0.80)
    col = lerp3(DEEP, SHALLOW, smooth(0.2, 0.8, big)); col = lerp3(col, LINE, lines * 0.55)
    h = 0.6 * big + 0.15 * (1 - smooth(0.0, 0.3, caustic / np.percentile(caustic, 98)))
    rough = np.full_like(h, 0.05)
    return write_set('Water', col, h, rough, 0.02, ao_r=6, ao_k=0.5)


ALL = [('Grass', tex_grass), ('Stone', tex_stone), ('Rock', tex_rock), ('FallenLeaves', tex_fallen_leaves),
       ('Snow', tex_snow), ('Sand', tex_sand), ('Soil', tex_soil), ('Water', tex_water)]


def make(names=None):
    res = []
    for i, (n, fn) in enumerate(ALL):
        if names and n not in names:
            continue
        res.append((n, round(fn(random.Random(100 + i)), 3)))
    return res
