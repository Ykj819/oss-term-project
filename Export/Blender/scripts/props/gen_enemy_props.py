# Enemy props (2026-11-23), headless:  blender -b --factory-startup --python <this file>
#   SM_ClubBat     : wooden baseball bat for EnemyClub. +Z along the bat, origin = right-hand grip (30 cm from the knob end,
#                    160 cm long, like the old engine-shape club), one smooth lathe; UV u around / v along -> T_BatWood
#   SM_EnemyShield : iron tower shield for EnemyShield, real size (10 x 80 x 110 cm, front = +X), origin = plate centre,
#                    curved plate + raised rim + boss + rivets, two vertical back grips at y = +-17 cm, z = -6 cm, 4.5 cm
#                    behind the back surface. Vertex colour RGB = albedo (sRGB), A = metallic.
#   SM_FogTree     : the fog tree's trunk / roots / bare branches (same layout as the old engine shapes in EnemyFogTree.cpp)
#                    as one metaball surface (smooth joints), decimated to <= 1000 tris, cylindrical bark UVs (0.7 m tile =
#                    the realistic bark texture), origin = ground under the trunk.
#   T_BatWood.png, T_FogNoise.png -> Export/Textures/Enemies
# Saves Export/Blender/EnemyProps.blend.
import bpy, bmesh, math, os, random
import numpy as np
from mathutils import Vector, Matrix

ROOT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject"
TEX = os.path.join(ROOT, r"Export\Textures\Enemies")
V = Vector


def link(name, bm, smooth=True):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob


def set_colours(ob, fn):
    me = ob.data
    col = me.color_attributes.get('Col') or me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    for poly in me.polygons:
        rgb, a = fn(poly)
        for li in poly.loop_indices:
            col.data[li].color_srgb = (*rgb, a)
    me.color_attributes.active_color = col


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def export(ob):
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=os.path.join(ROOT, 'Export', ob.name + '.fbx'), use_selection=True,
                             object_types={'MESH'}, apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE',
                             colors_type='SRGB', use_mesh_modifiers=True, bake_anim=False, add_leaf_bones=False)


# ---------------------------------------------------------------- tileable noise
def value_noise(w, h, cells_x, cells_y, rng):
    g = rng.random((cells_y, cells_x))
    ys = np.arange(h) / h * cells_y; xs = np.arange(w) / w * cells_x
    y0 = np.floor(ys).astype(int); x0 = np.floor(xs).astype(int)
    fy = ys - y0; fx = xs - x0
    fy = fy * fy * (3 - 2 * fy); fx = fx * fx * (3 - 2 * fx)
    y1 = (y0 + 1) % cells_y; x1 = (x0 + 1) % cells_x
    a = g[y0][:, x0]; b = g[y0][:, x1]; c = g[y1][:, x0]; d = g[y1][:, x1]
    top = a + (b - a) * fx[None, :]; bot = c + (d - c) * fx[None, :]
    return top + (bot - top) * fy[:, None]


def fbm(w, h, cx, cy, octaves, rng):
    out = np.zeros((h, w)); amp = 1.0; tot = 0.0
    for o in range(octaves):
        out += amp * value_noise(w, h, cx * 2 ** o, cy * 2 ** o, rng); tot += amp; amp *= 0.5
    return out / tot


def save_png(name, rgb):
    os.makedirs(TEX, exist_ok=True)
    h, w = rgb.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=True)
    px = np.ones((h, w, 4), np.float32); px[..., :3] = rgb
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = os.path.join(TEX, name + '.png'); img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)


def textures():
    rng = np.random.default_rng(7)
    # fog: soft isotropic fBm, wide value range
    n = fbm(256, 256, 4, 4, 5, rng)
    n = np.clip((n - n.min()) / (n.max() - n.min()), 0, 1)
    save_png('T_FogNoise', np.repeat(n[..., None], 3, axis=2))
    # bat wood: grain lines run along v (bat length), wobbling; warm light ash wood (values are sRGB)
    W, H = 256, 1024
    warp = fbm(W, H, 2, 6, 3, rng)
    u = np.arange(W)[None, :] / W
    rings = np.sin((u * 9 + warp * 2.2) * 2 * math.pi)
    fine = fbm(W, H, 32, 4, 2, rng)
    t = np.clip(0.55 + 0.25 * rings + 0.35 * (fine - 0.5), 0, 1)
    light = np.array([0.86, 0.66, 0.43]); dark = np.array([0.55, 0.34, 0.17])
    save_png('T_BatWood', dark + (light - dark) * t[..., None])


# ---------------------------------------------------------------- bat
def bat():
    prof = [(-0.300, 0.0), (-0.300, 0.026), (-0.293, 0.040), (-0.280, 0.043), (-0.268, 0.034), (-0.255, 0.027),
            (-0.10, 0.026), (0.10, 0.027), (0.25, 0.031), (0.40, 0.042), (0.55, 0.056), (0.70, 0.068),
            (0.85, 0.074), (1.15, 0.076), (1.23, 0.072), (1.27, 0.062), (1.293, 0.042), (1.30, 0.0)]
    segs = 16
    bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap')
    rings = []
    for z, r in prof:
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / segs), r * math.sin(2 * math.pi * i / segs), z))
                      for i in range(segs)] if r > 0 else None)
    pole = {0: bm.verts.new((0, 0, prof[0][0])), len(prof) - 1: bm.verts.new((0, 0, prof[-1][0]))}
    for k in range(len(prof) - 1):
        A, B = rings[k], rings[k + 1]
        v0, v1 = prof[k][0] / 0.55, prof[k + 1][0] / 0.55
        for i in range(segs):
            j = (i + 1) % segs
            if A is None:
                f = bm.faces.new((pole[k], B[j], B[i]))
                for l, uvv in zip(f.loops, (((i + 0.5) / segs, v0), ((i + 1) / segs, v1), (i / segs, v1))):
                    l[uv].uv = uvv
            elif B is None:
                f = bm.faces.new((A[i], A[j], pole[k + 1]))
                for l, uvv in zip(f.loops, ((i / segs, v0), ((i + 1) / segs, v0), ((i + 0.5) / segs, v1))):
                    l[uv].uv = uvv
            else:
                f = bm.faces.new((A[i], A[j], B[j], B[i]))
                for l, uvv in zip(f.loops, ((i / segs, v0), ((i + 1) / segs, v0), ((i + 1) / segs, v1), (i / segs, v1))):
                    l[uv].uv = uvv
    ob = link('SM_ClubBat', bm)
    # vertex colour: wood (white = texture as is); knob slightly darker / burnt
    set_colours(ob, lambda p: (((0.62, 0.55, 0.5) if p.center.z < -0.25 else (1.0, 1.0, 1.0)), 0.0))
    return ob


# ---------------------------------------------------------------- shield
SH_W, SH_H, SH_CURVE = 0.40, 0.55, 0.375          # half width / half height (m), plate x drop = CURVE * y^2
GRIP_Y, GRIP_Z, GRIP_BACK = 0.17, -0.06, 0.045


def outline(n=56, rc=0.13):
    """rounded-rectangle outline in (y, z), counter-clockwise seen from the front (+X)"""
    pts = []
    corners = [(SH_W - rc, SH_H - rc, 0), (-(SH_W - rc), SH_H - rc, 90), (-(SH_W - rc), -(SH_H - rc), 180), (SH_W - rc, -(SH_H - rc), 270)]
    per = n // 4
    for cy, cz, a0 in corners:
        for i in range(per):
            a = math.radians(a0 + 90 * i / (per - 1))
            pts.append((cy + rc * math.cos(a), cz + rc * math.sin(a)))
    return pts


def shield():
    bm = bmesh.new()
    O = outline()
    front = lambda y, z, lift=0.0: 0.05 + lift - SH_CURVE * y * y
    # front: concentric rings (scale, lift): edge bevel, raised rim, plate, towards the centre
    rings_def = [(1.0, -0.012), (0.985, 0.012), (0.935, 0.012), (0.92, 0.0), (0.6, 0.0), (0.3, 0.0)]
    rings = [[bm.verts.new((front(y * s, z * s, lift), y * s, z * s)) for y, z in O] for s, lift in rings_def]
    back_ring = [bm.verts.new((front(y, z) - 0.03 - 0.012, y, z)) for y, z in O]
    back_in = [bm.verts.new((front(y * 0.6, z * 0.6) - 0.03, y * 0.6, z * 0.6)) for y, z in O]
    n = len(O)
    rim_faces, plate_faces = [], []
    for k in range(len(rings) - 1):
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((rings[k][i], rings[k][j], rings[k + 1][j], rings[k + 1][i]))
            (rim_faces if k < 3 else plate_faces).append(f)
    centre = bm.verts.new((front(0, 0), 0, 0))
    for i in range(n):
        plate_faces.append(bm.faces.new((rings[-1][i], rings[-1][(i + 1) % n], centre)))
    # side + back
    for i in range(n):
        j = (i + 1) % n
        rim_faces.append(bm.faces.new((back_ring[i], back_ring[j], rings[0][j], rings[0][i])))
        plate_faces.append(bm.faces.new((back_in[i], back_in[j], back_ring[j], back_ring[i])))
    cb = bm.verts.new((front(0, 0) - 0.03, 0, 0))
    for i in range(n):
        plate_faces.append(bm.faces.new((back_in[(i + 1) % n], back_in[i], cb)))
    tag = {}
    for f in rim_faces: tag[f] = 'rim'
    for f in plate_faces: tag[f] = 'plate'

    def add(geom_fn, kind):
        before = set(bm.faces)
        geom_fn()
        for f in set(bm.faces) - before:
            tag[f] = kind
    # boss (flattened half dome) + rivets along the rim + two horizontal bands of rivets
    add(lambda: bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=0.11,
                                          matrix=Matrix.Translation((front(0, 0) - 0.01, 0, 0)) @ Matrix.Diagonal((0.55, 1, 1, 1))), 'boss')
    for y, z in outline(28, 0.13):
        y *= 0.96; z *= 0.96
        add(lambda y=y, z=z: bmesh.ops.create_uvsphere(bm, u_segments=6, v_segments=4, radius=0.012,
                                                       matrix=Matrix.Translation((front(y, z, 0.012), y, z))), 'rivet')
    # back grips: vertical bars on two standoffs each
    for sy in (1, -1):
        y = sy * GRIP_Y; xb = front(y, 0) - 0.03
        add(lambda y=y, xb=xb: bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.016, radius2=0.016, depth=0.17,
                                                     matrix=Matrix.Translation((xb - GRIP_BACK, y, GRIP_Z))), 'grip')
        for dz in (-0.09, 0.09):
            add(lambda y=y, xb=xb, dz=dz: bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Translation((xb - GRIP_BACK * 0.5, y, GRIP_Z + dz))
                                                                 @ Matrix.Diagonal((GRIP_BACK + 0.01, 0.03, 0.025, 1))), 'iron')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    kinds = [tag.get(f, 'plate') for f in bm.faces]
    ob = link('SM_EnemyShield', bm, smooth=False)
    pal = {'plate': ((0.30, 0.31, 0.33), 1.0), 'rim': ((0.50, 0.51, 0.53), 1.0), 'boss': ((0.58, 0.58, 0.60), 1.0),
           'rivet': ((0.66, 0.66, 0.68), 1.0), 'iron': ((0.40, 0.40, 0.42), 1.0), 'grip': ((0.26, 0.15, 0.08), 0.0)}
    set_colours(ob, lambda p: pal[kinds[p.index]])
    # smooth the curved plate / boss, keep the rim edges crisp
    for p in ob.data.polygons:
        p.use_smooth = kinds[p.index] in ('plate', 'boss', 'grip', 'rivet')
    ob.data.uv_layers.new(name='UVMap')
    return ob


# ---------------------------------------------------------------- fog tree
def dir_from(yaw, tilt):
    y, t = math.radians(yaw), math.radians(tilt)
    return V((math.cos(y) * math.sin(t), math.sin(y) * math.sin(t), math.cos(t)))


def fog_tree():
    limbs = []                                           # (start, end, r0, r1) metres, radius

    def limb(start, d, length, thick, tip):
        d = d.normalized(); end = start + d * length
        r = thick * 0.5
        limbs.append((start.copy(), end.copy(), r, (0.025 if tip else r * 0.85)))
        return end
    cm = 0.01
    top = limb(V((0, 0, -10 * cm)), V((0, 0, 1)), 170 * cm, 62 * cm, False)
    top = limb(top - V((0, 0, 8 * cm)), dir_from(20, 9), 120 * cm, 46 * cm, False)
    limb(top - V((0, 0, 6 * cm)), dir_from(200, 14), 70 * cm, 32 * cm, True)
    for i in range(5):
        limb(V((0, 0, 30 * cm)), dir_from(i * 72 + 15, 112), 85 * cm, 24 * cm, True)
    rnd = random.Random(1337)
    for z, yaw, tilt, length, thick in ((165, 35, 58, 150, 20), (205, 150, 48, 170, 18), (240, 265, 60, 130, 15),
                                        (270, 95, 35, 120, 14), (225, 330, 70, 110, 13)):
        mid = limb(V((0, 0, z * cm)), dir_from(yaw, tilt), length * 0.6 * cm, thick * cm, False)
        end = limb(mid, dir_from(yaw + rnd.uniform(-25, 25), tilt - rnd.uniform(5, 20)), length * 0.4 * cm, thick * 0.7 * cm, True)
        for t in range(2):
            side = -1 if t == 0 else 1
            frm = mid if t == 0 else mid.lerp(end, 0.5)
            limb(frm, dir_from(yaw + side * rnd.uniform(35, 60), tilt - rnd.uniform(10, 30)),
                 length * rnd.uniform(0.3, 0.45) * cm, thick * 0.45 * cm, True)
    # the trunk's base flares into the ground
    limbs.append((V((0, 0, 0.0)), V((0, 0, 0.35)), 0.40, 0.31))

    # metaball surface
    mb = bpy.data.metaballs.new('FogTreeMB'); mb.resolution = 0.022
    k_ob = bpy.data.objects.new('FogTreeMB', mb); bpy.context.scene.collection.objects.link(k_ob)
    for a, b, r0, r1 in limbs:
        L = (b - a).length; n = max(2, int(L / (min(r0, r1) * 0.5)) + 1)
        for i in range(n):
            t = i / (n - 1); e = mb.elements.new(); e.co = a.lerp(b, t)
            e.radius = (r0 + (r1 - r0) * t) * 1.32; e.stiffness = 2.6
    bpy.context.view_layer.update()
    me = bpy.data.meshes.new_from_object(k_ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    bpy.data.objects.remove(k_ob); bpy.data.metaballs.remove(mb)
    old = bpy.data.objects.get('SM_FogTree')
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    me.name = 'SM_FogTree'
    ob = bpy.data.objects.new('SM_FogTree', me); bpy.context.scene.collection.objects.link(ob)
    # cut what is below the ground
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, -0.02), plane_no=(0, 0, 1),
                           clear_inner=True)
    bm.to_mesh(me); bm.free()
    m = ob.modifiers.new('dec', 'DECIMATE'); m.ratio = 940 / max(1, tris(ob))
    bpy.context.view_layer.objects.active = ob; bpy.ops.object.modifier_apply(modifier='dec')
    for p in me.polygons:
        p.use_smooth = True

    # cylindrical bark UVs around the nearest limb (0.7 m texture tile, whole tiles around each limb)
    TILE = 0.7
    frames = []
    for idx, (a, b, r0, r1) in enumerate(limbs):
        d = (b - a).normalized(); e1 = d.orthogonal().normalized(); e2 = d.cross(e1)
        k = max(1, round(2 * math.pi * max(r0, r1) / TILE))
        frames.append((a, b, d, e1, e2, k, max(r0, r1) * 2 * math.pi / k, (idx * 0.618) % 1.0))

    def nearest(p):
        best = None
        for f in frames:
            a, b, d = f[0], f[1], f[2]
            t = max(0.0, min((b - a).length, (p - a).dot(d)))
            dist = (p - (a + d * t)).length
            r = limbs[frames.index(f)][2]
            s = dist - r
            if best is None or s < best[0]:
                best = (s, f)
        return best[1]
    uv = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        f = nearest(poly.center)
        a, b, d, e1, e2, k, tile_len, off = f
        us, vs = [], []
        for li in poly.loop_indices:
            p = me.vertices[me.loops[li].vertex_index].co - a
            ang = math.atan2(p.dot(e2), p.dot(e1)) / (2 * math.pi)
            us.append(ang * k); vs.append(p.dot(d) / tile_len + off)
        base = us[0]
        for i in range(len(us)):
            while us[i] - base > k * 0.5: us[i] -= k
            while us[i] - base < -k * 0.5: us[i] += k
        for li, u, v in zip(poly.loop_indices, us, vs):
            uv.data[li].uv = (u, v)
    # vertex colour: darker at the roots (ground contact / damp), white elsewhere (texture shows as is)
    set_colours(ob, lambda p: (tuple(0.55 + 0.45 * min(1.0, max(0.0, p.center.z / 0.6)) for _ in range(3)), 0.0))
    return ob


def run():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    textures()
    obs = [bat(), shield(), fog_tree()]
    for i, ob in enumerate(obs):
        ob.location.x = i * 3.0
    for ob in obs:
        loc = ob.location.copy(); ob.location = (0, 0, 0)
        export(ob)
        ob.location = loc
        print('PROPS', ob.name, 'tris', tris(ob), 'bbox', [tuple(round(c, 3) for c in v) for v in (Vector(ob.bound_box[0]), Vector(ob.bound_box[6]))])
    # preview
    sc = bpy.context.scene
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 9.5
    d = V((0.35, -1, 0.3)).normalized(); cam.location = V((3.0, 0, 1.6)) + d * 20
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'VERTEX'
    sc.render.resolution_x = 900; sc.render.resolution_y = 520
    sc.render.filepath = os.path.join(ROOT, r"Export\Blender\compare\enemy_props.png"); bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, r"Export\Blender\EnemyProps.blend"))
    print('PROPS done')


run()
