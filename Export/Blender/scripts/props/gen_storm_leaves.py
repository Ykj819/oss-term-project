# Tree boss phase-2 leaf storm leaves (2026-11-23), headless:  blender -b --factory-startup --python <this file>
#   T_StormLeaves.png (768 x 256 RGBA atlas, 3 cells: yellow ginkgo | red maple | brown leaf; alpha = leaf shape)
#   SM_StormLeaf.fbx  one slightly curled card, 100 x 100 cm in XY (centred), UV 0..1 = one atlas cell
# UE: material M_StormLeaf picks the cell from the instance's custom data 0 (0 / 1 / 2) -> ATreeBoss::StormLeaves.
# Saves Export/Blender/StormLeaves.blend.
import bpy, bmesh, math, os
import numpy as np

ROOT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject"
N = 256
rng = np.random.default_rng(3)


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def grid():
    c = (np.arange(N) + 0.5) / N * 2 - 1
    x, y = np.meshgrid(c, c)            # y up (image rows are bottom-up in Blender)
    return x, y


def noise(scale):
    g = rng.random((scale + 1, scale + 1))
    c = np.linspace(0, scale, N)
    i = np.clip(c.astype(int), 0, scale - 1); f = c - i
    a = g[i][:, i]; b = g[i][:, i + 1]; cc = g[i + 1][:, i]; d = g[i + 1][:, i + 1]
    f2 = f[None, :]; f1 = f[:, None]
    return (a * (1 - f2) + b * f2) * (1 - f1) + (cc * (1 - f2) + d * f2) * f1


def stem(x, y, top, width=0.035):
    return (np.abs(x) < width) & (y < top) & (y > -0.98)


def ginkgo():
    x, y = grid()
    sx, sy = 0.0, -0.55                                      # fan origin (top of the stem)
    dx, dy = x - sx, y - sy
    r = np.hypot(dx, dy); th = np.arctan2(dx, dy)            # 0 = straight up
    edge = 1.12 - 0.24 * np.exp(-(th / 0.11) ** 2) + 0.035 * np.sin(th * 23) - 0.25 * smooth(0.6, 1.0, np.abs(th))   # notch in the middle, wavy rim
    a = smooth(0.0, 0.03, edge - r) * smooth(0.0, 0.05, 1.0 - np.abs(th)) * (dy > -0.02)
    a = np.maximum(a, stem(x, y, sy + 0.05, 0.03).astype(float))
    veins = 0.5 + 0.5 * np.cos(th * 46)
    base = np.array([0.97, 0.80, 0.16]); dark = np.array([0.86, 0.58, 0.07])
    t = np.clip(0.25 * veins + 0.35 * (r / 1.1) + 0.25 * noise(6), 0, 1)
    rgb = base + (dark - base) * t[..., None]
    return rgb, a


def maple():
    x, y = grid()
    cx, cy = 0.0, -0.12
    dx, dy = x - cx, y - cy
    r = np.hypot(dx, dy); th = np.arctan2(dx, dy)
    lobes = np.abs(np.cos(th * 2.5)) ** 0.7                # 5 pointed lobes (top, 2 sides, 2 low)
    teeth = 0.05 * np.abs(np.sin(th * 22))
    edge = (0.42 + 0.5 * lobes - teeth) * (1 - 0.35 * smooth(2.2, 3.1, np.abs(th)))   # small gap at the stem
    a = smooth(0.0, 0.03, edge - r)
    a = np.maximum(a, stem(x, y, cy, 0.03).astype(float))
    # veins: lines from the centre toward each lobe tip
    vein = np.zeros_like(r)
    for k in range(5):
        ang = (k - 2) * (2 * math.pi / 5)
        d = np.abs(np.sin(th - ang)) * r
        vein = np.maximum(vein, smooth(0.025, 0.0, d) * (np.cos(th - ang) > 0))
    base = np.array([0.86, 0.10, 0.05]); dark = np.array([0.55, 0.03, 0.03]); tip = np.array([0.95, 0.35, 0.06])
    rgb = base + (tip - base) * (smooth(0.3, 0.9, r) * noise(5))[..., None]
    rgb = rgb + (dark - rgb) * (0.6 * vein + 0.2 * noise(9))[..., None]
    return rgb, a


def brown():
    x, y = grid()
    yy = (y + 0.05) / 0.85                                  # leaf from y=-0.9 (base) to 0.8 (tip)
    w = 0.48 * np.clip(1 - yy ** 2, 0, 1) ** 0.75 * (1 + 0.25 * yy)
    w = w * (1 - 0.06 * np.abs(np.sin(yy * 14)))            # slightly wavy, dried edge
    a = smooth(0.0, 0.025, w - np.abs(x + 0.06 * yy ** 2)) * (np.abs(yy) < 1)
    a = np.maximum(a, stem(x, y, -0.85, 0.03).astype(float))
    mid = smooth(0.03, 0.0, np.abs(x + 0.06 * yy ** 2))
    side = smooth(0.02, 0.0, np.abs(np.sin((y - np.abs(x) * 0.9) * 12)) * 0.08) * (np.abs(x) < w)
    base = np.array([0.50, 0.30, 0.12]); dark = np.array([0.28, 0.15, 0.05]); edgec = np.array([0.34, 0.19, 0.07])
    rgb = base + (edgec - base) * smooth(0.6, 1.0, np.abs(x) / np.maximum(w, 1e-3))[..., None]
    rgb = rgb + (dark - rgb) * np.clip(0.7 * mid + 0.4 * side + 0.25 * noise(8), 0, 1)[..., None]
    return rgb, a


def atlas():
    cells = [ginkgo(), maple(), brown()]
    img = np.zeros((N, N * 3, 4), np.float32)
    for i, (rgb, a) in enumerate(cells):
        # transparent area gets the leaf's mean colour (no dark fringe when mip-mapped)
        mean = rgb[a > 0.5].mean(axis=0)
        img[:, i * N:(i + 1) * N, :3] = np.where(a[..., None] > 0.01, rgb, mean)
        img[:, i * N:(i + 1) * N, 3] = a
    path = os.path.join(ROOT, r"Export\Textures\Enemies\T_StormLeaves.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im = bpy.data.images.new('T_StormLeaves', N * 3, N, alpha=True)
    im.pixels.foreach_set(img.ravel()); im.filepath_raw = path; im.file_format = 'PNG'; im.save()
    return path


def card():
    bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap')
    n = 4
    verts = [[bm.verts.new(((i / n - 0.5), (j / n - 0.5), 0.10 * (i / n - 0.5) ** 2 * 4 + 0.05 * (j / n - 0.5) ** 2 * 4))
              for i in range(n + 1)] for j in range(n + 1)]
    for j in range(n):
        for i in range(n):
            f = bm.faces.new((verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]))
            for l, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                l[uv].uv = (a / n, b / n)
    me = bpy.data.meshes.new('SM_StormLeaf'); bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new('SM_StormLeaf', me); bpy.context.scene.collection.objects.link(ob)
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    fbx = os.path.join(ROOT, 'Export', 'SM_StormLeaf.fbx')
    bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={'MESH'}, apply_scale_options='FBX_SCALE_UNITS',
                             mesh_smooth_type='FACE', use_mesh_modifiers=False, bake_anim=False, add_leaf_bones=False)
    return fbx


for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
print('LEAVES', atlas(), card())
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, r"Export\Blender\StormLeaves.blend"))
