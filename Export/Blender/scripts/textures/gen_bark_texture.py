# Tileable realistic bark texture set (furrowed grey-brown bark, poplar/oak-like), for SM_RealisticTree1.
# Method: shader noise is evaluated on a 4D torus (u, v -> cos/sin pairs), which makes every pattern seamless,
# baked (Cycles EMIT) into float images, then combined with numpy:
#   T_RealBark_BC   base colour (sRGB)
#   T_RealBark_N    normal map, DirectX convention (UE)       T_RealBark_N_GL  OpenGL version (Blender preview)
#   T_RealBark_ARH  R = ambient occlusion, G = roughness, B = height (linear)
# One tile = TILE_M x TILE_M metres of bark (the tree UVs use the same size).
# Usage: g = {}; exec(open(path).read(), g); g['make']()
import bpy, math, os
import numpy as np

OUT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Textures\RealBark"
RES = 2048
TILE_M = 0.7
# cross-break cells per tile across (u) and along (v)
PLATES_U, PLATES_V = 10, 2.5
# furrow noise: features per tile across / along (very anisotropic -> long vertical furrows) and contour count
FURROW_U, FURROW_V, FURROW_CONTOURS = 13, 1.6, 0.0


def _torus(nt, sep, n_u, n_v, off=(0.0, 0.0, 0.0, 0.0)):
    """Vector + W on a 4D torus: n_u features around u, n_v along v (with Scale 1)."""
    def m(op, a, b=None, val=None):
        n = nt.nodes.new('ShaderNodeMath'); n.operation = op
        nt.links.new(a, n.inputs[0])
        if b is not None:
            nt.links.new(b, n.inputs[1])
        elif val is not None:
            n.inputs[1].default_value = val
        return n.outputs[0]
    th = m('MULTIPLY', sep.outputs['X'], val=2 * math.pi)
    ph = m('MULTIPLY', sep.outputs['Y'], val=2 * math.pi)
    ru = n_u / (2 * math.pi); rv = n_v / (2 * math.pi)
    x = m('ADD', m('MULTIPLY', m('COSINE', th), val=ru), val=off[0])
    y = m('ADD', m('MULTIPLY', m('SINE', th), val=ru), val=off[1])
    z = m('ADD', m('MULTIPLY', m('COSINE', ph), val=rv), val=off[2])
    w = m('ADD', m('MULTIPLY', m('SINE', ph), val=rv), val=off[3])
    cv = nt.nodes.new('ShaderNodeCombineXYZ')
    nt.links.new(x, cv.inputs[0]); nt.links.new(y, cv.inputs[1]); nt.links.new(z, cv.inputs[2])
    return cv.outputs[0], w


def _noise4(nt, vec, w, scale=1.0, detail=6.0, rough=0.55):
    n = nt.nodes.new('ShaderNodeTexNoise'); n.noise_dimensions = '4D'
    nt.links.new(vec, n.inputs['Vector']); nt.links.new(w, n.inputs['W'])
    n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail
    n.inputs['Roughness'].default_value = rough
    return n


def _voronoi4(nt, vec, w, feature):
    v = nt.nodes.new('ShaderNodeTexVoronoi'); v.voronoi_dimensions = '4D'; v.feature = feature
    nt.links.new(vec, v.inputs['Vector']); nt.links.new(w, v.inputs['W'])
    v.inputs['Scale'].default_value = 1.0
    return v


def _bake(obj, mat, build):
    """build(nt, sep) -> (r, g, b) sockets; returns float array (RES, RES, 3)."""
    nt = mat.node_tree; nt.nodes.clear()
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['UV'], sep.inputs[0])
    r, g, b = build(nt, sep)
    cc = nt.nodes.new('ShaderNodeCombineColor')
    nt.links.new(r, cc.inputs[0]); nt.links.new(g, cc.inputs[1]); nt.links.new(b, cc.inputs[2])
    em = nt.nodes.new('ShaderNodeEmission'); nt.links.new(cc.outputs[0], em.inputs['Color'])
    out = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(em.outputs[0], out.inputs['Surface'])
    img = bpy.data.images.get('_bark_bake')
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new('_bark_bake', RES, RES, alpha=False, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = img
    nt.nodes.active = tn
    bpy.ops.object.bake(type='EMIT')
    a = np.empty(RES * RES * 4, dtype=np.float32); img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(RES, RES, 4)[:, :, :3].copy()


def _blur(x, r):
    """Box blur with wrap-around (keeps the tiling)."""
    for axis in (0, 1):
        acc = np.zeros_like(x)
        for k in range(-r, r + 1):
            acc += np.roll(x, k, axis=axis)
        x = acc / (2 * r + 1)
    return x


def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def _save(name, rgb, srgb):
    os.makedirs(OUT, exist_ok=True)
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, RES, RES, alpha=False, float_buffer=False)
    img.colorspace_settings.name = 'sRGB' if srgb else 'Non-Color'
    if srgb:  # store sRGB-encoded values (byte image pixels are written as-is)
        rgb = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * np.power(np.clip(rgb, 0, None), 1 / 2.4) - 0.055)
    rgba = np.concatenate([np.clip(rgb, 0, 1), np.ones((RES, RES, 1), np.float32)], axis=2)
    img.pixels.foreach_set(rgba.astype(np.float32).ravel())
    img.filepath_raw = os.path.join(OUT, name + '.png'); img.file_format = 'PNG'
    img.save()
    return img.filepath_raw


def make():
    sc = bpy.context.scene
    prev_engine = sc.render.engine
    try:
        sc.render.engine = 'CYCLES'
    except TypeError as e:
        print(e)
    sc.cycles.samples = 1
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -100))
    ob = bpy.context.active_object; ob.name = '_BarkBakePlane'
    mat = bpy.data.materials.new('_BarkBake'); mat.use_nodes = True; ob.data.materials.append(mat)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob

    def bake1(nt, sep):
        # furrows: contour lines of a strongly vertical noise (they meander, split and merge like real bark);
        # fibres: fine vertical streaks; big colour noise
        # long, narrow voronoi cells (8x taller than wide) on a warped torus: cell edges = furrows,
        # cells = interlacing ridges with tapered ends
        vec, w = _torus(nt, sep, FURROW_U, FURROW_V)
        warp = _noise4(nt, vec, w, scale=0.8, detail=2)
        wv = nt.nodes.new('ShaderNodeVectorMath'); wv.operation = 'MULTIPLY_ADD'
        nt.links.new(warp.outputs['Color'], wv.inputs[0]); wv.inputs[1].default_value = (0.7, 0.7, 0.7)
        nt.links.new(vec, wv.inputs[2])
        furrow = _voronoi4(nt, wv.outputs[0], w, 'DISTANCE_TO_EDGE')
        fv, fw = _torus(nt, sep, 90, 6, off=(3.1, 1.7, 0.4, 2.2))
        fib = _noise4(nt, fv, fw, scale=1.0, detail=5, rough=0.6)
        bv, bw = _torus(nt, sep, 3, 2, off=(7.0, 2.0, 5.0, 1.0))
        big = _noise4(nt, bv, bw, scale=1.0, detail=4)
        return furrow.outputs['Distance'], fib.outputs['Fac'], big.outputs['Fac']

    def bake2(nt, sep):
        # fine surface grain, per-plate tint (voronoi cell colour, same warp/seed as bake1), lichen patches
        # second furrow set (other seed): min() of two contour sets makes ridges interlace into long diamonds
        vec, w = _torus(nt, sep, FURROW_U, FURROW_V, off=(5.3, 2.9, 7.1, 3.3))
        edge = _noise4(nt, vec, w, scale=1.0, detail=1.5, rough=0.5)
        gv, gw = _torus(nt, sep, 60, 60, off=(1.0, 9.0, 3.0, 4.0))
        grain = _noise4(nt, gv, gw, scale=1.0, detail=8, rough=0.65)
        lv, lw = _torus(nt, sep, 8, 8, off=(4.0, 4.0, 9.0, 2.0))
        lich = _noise4(nt, lv, lw, scale=1.0, detail=6, rough=0.6)
        return grain.outputs['Fac'], edge.outputs['Fac'], lich.outputs['Fac']

    a = _bake(ob, mat, bake1)
    b = _bake(ob, mat, bake2)
    bpy.data.objects.remove(ob, do_unlink=True); bpy.data.materials.remove(mat)
    try:
        sc.render.engine = prev_engine
    except TypeError:
        pass

    fur, fib, big = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    grain, fur2, lich = b[:, :, 0], b[:, :, 1], b[:, :, 2]

    # ---- height: furrows = contour lines of two vertical noises (min -> interlacing ridges / long diamonds),
    #      rounded ridge shoulders, corky rough ridge tops with vertical fibres, fine grain everywhere
    # fur = distance to the nearest cell edge (furrow centre); furrow width varies with a slow noise
    # furrow width from the distance distribution: ~35% of the surface is furrow, varying with a slow noise
    fn = fur / np.percentile(fur, 98)            # 0 at a furrow centre .. ~1 at a ridge centre
    wv = 0.75 + 0.5 * fur2                       # furrow width varies slowly
    ridge = _smooth(0.10 * wv, 0.55 * wv, fn * (1 + 0.15 * (grain - 0.5))) ** 0.8
    plate = ridge
    cellv = _blur(big, 2)                        # slow per-area tint
    cork = (grain - 0.5) * plate                  # rough, corky ridge tops
    h = 0.62 * plate + 0.18 * (fib - 0.5) * (0.2 + 0.8 * plate) + 0.32 * cork + 0.06 * (grain - 0.5) + 0.06 * (cellv - 0.5)
    h = (h - h.min()) / (h.max() - h.min())

    # ---- normal from height (wraps -> tileable). Rows go up in v (Blender buffer starts at the bottom).
    px_m = TILE_M / RES
    depth_m = 0.011                              # furrow depth in metres
    dhdu = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * depth_m / (2 * px_m)
    dhdv = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * depth_m / (2 * px_m)
    n = np.stack([-dhdu, -dhdv, np.ones_like(h)], axis=2)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    n_gl = n * 0.5 + 0.5
    n_dx = n_gl.copy(); n_dx[:, :, 1] = 1.0 - n_dx[:, :, 1]   # UE = DirectX: green flipped

    # ---- ambient occlusion: how far below its neighbourhood each pixel sits
    ao = 1.0 - np.clip((_blur(h, 6) - h) * 1.8, 0, 0.5)
    ao *= 1.0 - np.clip((_blur(h, 3) - h) * 2.0, 0, 0.3)

    # ---- colour (linear)
    DEEP = np.array([0.024, 0.016, 0.011]); MID = np.array([0.09, 0.068, 0.05]); TOP = np.array([0.15, 0.125, 0.10])
    WARM = np.array([0.15, 0.10, 0.065]); LICHEN = np.array([0.20, 0.23, 0.15])
    t1 = _smooth(0.05, 0.42, h)[..., None]; t2 = _smooth(0.45, 0.92, h)[..., None]
    col = DEEP * (1 - t1) + MID * t1
    col = col * (1 - t2) + TOP * t2
    warm = _smooth(0.45, 0.75, big)[..., None] * 0.45
    # warmer (browner) areas: hue shift that keeps the brightness (the old blend darkened them into smudges)
    hue = WARM / WARM.mean()
    col = col * ((1 - warm) + hue * warm)
    col *= (0.80 + 0.40 * cellv)[..., None] * (0.65 + 0.70 * grain)[..., None] * (0.85 + 0.3 * fib)[..., None]
    lm = (_smooth(0.58, 0.70, lich) * _smooth(0.55, 0.8, h))[..., None] * 0.65
    col = col * (1 - lm) + LICHEN * (0.8 + 0.4 * grain[..., None]) * lm

    rough = np.clip(0.80 + 0.15 * (1 - h) + 0.06 * (grain - 0.5) - 0.08 * lm[..., 0], 0, 1)
    arh = np.stack([ao, rough, h], axis=2)

    paths = [_save('T_RealBark_BC', col.astype(np.float32), True),
             _save('T_RealBark_N', n_dx.astype(np.float32), False),
             _save('T_RealBark_N_GL', n_gl.astype(np.float32), False),
             _save('T_RealBark_ARH', arh.astype(np.float32), False)]
    return paths, float(h.mean()), float(col.mean())
