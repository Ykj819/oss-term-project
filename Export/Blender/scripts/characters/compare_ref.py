# Side-by-side comparison of SKM_PlayerKnight with the turnaround concept image.
# Renders orthographic front / side (character's right, -X) / back views at the reference image's pixel scale and
# writes  [ref front | model front | ref side | model side | ref back | model back]  to OUT_PNG.
# Reference measurements (1024x572 webp): feet at y~545, head top y~62 => 1.90 m = 483 px.
import bpy, os, math
import numpy as np
from mathutils import Vector

REF = r"C:\Users\ykj08\Desktop\이미지\a7e3d496-43fd-4515-8724-72fc8be8b796.webp"
OUT_DIR = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Blender\compare"
OUT_PNG = os.path.join(OUT_DIR, "compare.png")
PX_PER_M = 483 / 1.90
CROP_Y0, CROP_H, CROP_W = 30, 530, 320
FEET_Y = 546
VIEWS = (('front', 220, Vector((0, -10, 0))), ('side', 528, Vector((-10, 0, 0))), ('back', 848, Vector((0, 10, 0))))
UPS = 2          # render/upscale factor


def load_ref():
    img = bpy.data.images.load(REF, check_existing=True)
    w, h = img.size
    a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]       # top row first
    return a


def crop(a, cx):
    x0 = cx - CROP_W // 2
    c = a[CROP_Y0:CROP_Y0 + CROP_H, x0:x0 + CROP_W]
    return np.repeat(np.repeat(c, UPS, 0), UPS, 1)


def setup_render(sc):
    for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try:
            sc.render.engine = eng; break
        except TypeError:
            pass
    sc.render.resolution_x = CROP_W * UPS; sc.render.resolution_y = CROP_H * UPS
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    sc.view_settings.view_transform = 'AgX' if 'AgX' in [i.identifier for i in
        bpy.types.ColorManagedViewSettings.bl_rna.properties['view_transform'].enum_items] else 'Standard'
    # studio HDRI shipped with Blender
    w = bpy.data.worlds.get('_cmp_world') or bpy.data.worlds.new('_cmp_world')
    w.use_nodes = True; nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputWorld'); bg = nt.nodes.new('ShaderNodeBackground')
    env = nt.nodes.new('ShaderNodeTexEnvironment')
    d = bpy.utils.system_resource('DATAFILES', path='studiolights/world')
    hdr = os.path.join(d, 'forest.exr') if os.path.exists(os.path.join(d, 'forest.exr')) else \
        os.path.join(d, sorted(os.listdir(d))[0])
    env.image = bpy.data.images.load(hdr, check_existing=True)
    nt.links.new(env.outputs[0], bg.inputs[0]); nt.links.new(bg.outputs[0], out.inputs[0])
    bg.inputs[1].default_value = 1.0
    sc.world = w
    sun = bpy.data.objects.get('_cmp_sun')
    if not sun:
        sun = bpy.data.objects.new('_cmp_sun', bpy.data.lights.new('_cmp_sun', 'SUN'))
        sc.collection.objects.link(sun)
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(-25))
    cam = bpy.data.objects.get('_cmp_cam')
    if not cam:
        cam = bpy.data.objects.new('_cmp_cam', bpy.data.cameras.new('_cmp_cam'))
        sc.collection.objects.link(cam)
    cam.data.type = 'ORTHO'
    cam.data.ortho_scale = CROP_H / PX_PER_M
    sc.camera = cam
    return cam, sun


def run(views=None):
    os.makedirs(OUT_DIR, exist_ok=True)
    sc = bpy.context.scene
    keep = (sc.render.engine, sc.world, sc.camera, sc.render.resolution_x, sc.render.resolution_y,
            sc.render.film_transparent, sc.view_settings.view_transform)
    cam, sun = setup_render(sc)
    hidden = [o for o in sc.objects if o.type == 'MESH' and o.name != 'SKM_PlayerKnight' and not o.hide_render]
    for o in hidden:
        o.hide_render = True
    ref = load_ref()
    zc = (FEET_Y - CROP_Y0 - CROP_H / 2) / PX_PER_M
    tiles = []
    for name, cx, pos in VIEWS:
        if views and name not in views:
            continue
        cam.location = Vector((pos.x, pos.y, zc))
        d = -pos.normalized()
        cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        path = os.path.join(OUT_DIR, f"model_{name}.png")
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(path, check_existing=False)
        m = np.array(im.pixels[:], dtype=np.float32).reshape(CROP_H * UPS, CROP_W * UPS, 4)[::-1]
        bpy.data.images.remove(im)
        bgc = np.array([0.55, 0.55, 0.58], np.float32)
        m = m[..., :3] * m[..., 3:4] + bgc * (1 - m[..., 3:4])
        r = crop(ref, cx)[..., :3]
        tiles += [r, m]
    for o in hidden:
        o.hide_render = False
    (sc.render.engine, sc.world, sc.camera, sc.render.resolution_x, sc.render.resolution_y,
     sc.render.film_transparent, sc.view_settings.view_transform) = keep
    allim = np.concatenate(tiles, axis=1)
    # horizontal guide lines every 0.1 m (feet = 0) to read heights
    for k in range(0, 20):
        y = int((FEET_Y - CROP_Y0) * UPS - k * 0.1 * PX_PER_M * UPS)
        if 0 <= y < allim.shape[0]:
            allim[y, :, :] = allim[y, :, :] * 0.6 + (np.array([1, 0.2, 0.2]) if k % 5 == 0 else np.array([0.2, 0.6, 1])) * 0.4
    h, w = allim.shape[:2]
    out = bpy.data.images.new('_cmp_out', w, h, alpha=False)
    rgba = np.concatenate([np.clip(allim, 0, 1), np.ones((h, w, 1), np.float32)], axis=2)[::-1]
    out.pixels.foreach_set(rgba.ravel()); out.filepath_raw = OUT_PNG; out.file_format = 'PNG'; out.save()
    bpy.data.images.remove(out)
    return OUT_PNG
