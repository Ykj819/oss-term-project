# Stylized wooden sword for the player (replaces the engine-cylinder "stick"; same grips, so the stick animations work):
#   SM_WoodSword: 95 cm, +Z along the sword (blade up), origin = centre of the length (like the old cylinder), blade
#   width along X (the edge), thickness along Y. Bottom end = pommel; the right hand grips 30 cm from the bottom, the
#   left 13 cm below (StickGripFromEnd + the authored slash anims) -> handle 5.5..37.5 cm, guard 37.5..41, blade 41..95.
#   Soft cage meshes + subdivision (Palworld-like), vertex colours RGB = albedo (sRGB): light grained blade with a burnt
#   centre groove, dark wood guard + pommel, spiral leather wrap on the handle.
# Headless:  blender -b --factory-startup --python <this file> [-- --no-export]
#   saves Export/Blender/WoodSword.blend, previews Export/Blender/compare/wood_sword_*.png, exports Export/SM_WoodSword.fbx
# UE import: Tools/import_wood_sword.py
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix

ROOT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject"
CMP = os.path.join(ROOT, r"Export\Blender\compare")
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
V = Vector
LENGTH = 0.95
HANDLE = (0.055, 0.375)
GUARD = (0.375, 0.41)
BLADE = (0.395, LENGTH)   # base sunk into the guard (subdivision rounds the bottom cap off)
log = lambda *a: print('SWORD', *a)

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)


def loft(name, rings, cap0=True, cap1=True):
    """rings: list of lists of 3D points (same count); quads between rings, n-gon caps"""
    bm = bmesh.new()
    vs = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    for a, b in zip(vs[:-1], vs[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    if cap0:
        bm.faces.new(list(reversed(vs[0])))
    if cap1:
        bm.faces.new(vs[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob


def smooth(ob, levels=2):
    m = ob.modifiers.new('sub', 'SUBSURF'); m.levels = levels; m.render_levels = levels
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier='sub')
    for p in ob.data.polygons:
        p.use_smooth = True


def colour(ob, fn):
    me = ob.data
    col = me.color_attributes.get('Col') or me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    for loop in me.loops:
        col.data[loop.index].color_srgb = (*fn(me.vertices[loop.vertex_index].co), 1.0)
    me.color_attributes.active_color = col


def lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


# ---------------------------------------------------------------- blade (lens cross-section with a raised centre ridge)
def blade():
    z0, z1 = BLADE
    tip_len = 0.13
    rings = []
    N = 34
    for k in range(N + 1):
        s = k / N
        z = z0 + (z1 - z0) * s
        w = 0.036 + 0.004 * math.sin(math.pi * min(s / 0.75, 1.0))     # slight leaf swell
        t = 0.0135 - 0.003 * s
        zt = z1 - tip_len
        if z > zt:                                                     # rounded point
            u = (z - zt) / tip_len
            f = math.sqrt(max(1 - u ** 1.6, 0.0))
            w *= max(f, 0.06); t *= max(f ** 0.5, 0.25)
        rings.append([V((x * w, y * t, z)) for x, y in
                      ((1, 0), (0.62, 0.78), (0, 1), (-0.62, 0.78), (-1, 0), (-0.62, -0.78), (0, -1), (0.62, -0.78))])
    ob = loft('Blade', rings)
    smooth(ob)

    def fn(p):
        light, dark = (0.88, 0.70, 0.47), (0.70, 0.50, 0.30)
        grain = 0.5 + 0.5 * math.sin(p.x * 260 + 3.0 * math.sin(p.z * 7.0) + 1.5 * math.sin(p.z * 23.0 + p.x * 40))
        c = lerp(dark, light, 0.35 + 0.65 * grain ** 0.6)
        if abs(p.x) < 0.0045 and p.z < z1 - tip_len * 0.6:             # burnt centre groove on both faces
            c = lerp(c, (0.42, 0.25, 0.13), 0.85)
        return c
    colour(ob, fn)
    return ob


# ---------------------------------------------------------------- handle (spiral leather wrap with relief)
def handle():
    z0, z1 = HANDLE
    n = 12
    rings = []
    N = 44
    for k in range(N + 1):
        z = z0 + (z1 - z0) * k / N
        ring = []
        for i in range(n):
            a = 2 * math.pi * i / n
            ph = (z / 0.032 + a / (2 * math.pi)) % 1.0                 # spiral: one turn per 3.2 cm
            r = 0.0175 * (1.0 + 0.09 * math.sin(math.pi * min(ph / 0.85, 1.0)))
            ring.append(V((r * math.cos(a) * 1.08, r * math.sin(a) * 0.92, z)))
        rings.append(ring)
    ob = loft('Handle', rings)
    smooth(ob)

    def fn(p):
        a = math.atan2(p.y / 0.92, p.x / 1.08)
        ph = (p.z / 0.032 + a / (2 * math.pi)) % 1.0
        return (0.30, 0.13, 0.08) if ph > 0.85 else lerp((0.48, 0.24, 0.14), (0.56, 0.30, 0.17), math.sin(math.pi * ph / 0.85))
    colour(ob, fn)
    return ob


# ---------------------------------------------------------------- cross guard (chunky bar with knobbed ends)
def guard():
    z0, z1 = GUARD
    zc, hz = (z0 + z1) / 2, (z1 - z0) / 2 + 0.004
    rings = []
    N = 16
    for k in range(N + 1):
        x = -0.095 + 0.19 * k / N
        e = abs(x) / 0.095
        s = 1.0 + 0.45 * max(0.0, (e - 0.7) / 0.3) ** 2                # knobs at the ends
        hy = 0.019 * s; hzz = hz * s
        rings.append([V((x, y * hy, zc + zz * hzz)) for y, zz in
                      ((1, 0), (0.75, 0.75), (0, 1), (-0.75, 0.75), (-1, 0), (-0.75, -0.75), (0, -1), (0.75, -0.75))])
    ob = loft('Guard', rings)
    smooth(ob)
    colour(ob, lambda p: lerp((0.36, 0.21, 0.11), (0.46, 0.29, 0.16), 0.5 + 0.5 * math.sin(p.x * 120 + p.z * 60)))
    return ob


# ---------------------------------------------------------------- pommel (squashed ball + collar)
def pommel():
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.029,
                              matrix=Matrix.Translation((0, 0, 0.033)) @ Matrix.Diagonal((1.0, 1.0, 0.9, 1.0)))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.021, radius2=0.021, depth=0.014,
                          matrix=Matrix.Translation((0, 0, 0.062)))
    me = bpy.data.meshes.new('Pommel'); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('Pommel', me); bpy.context.scene.collection.objects.link(ob)
    smooth(ob, 1)
    colour(ob, lambda p: (0.36, 0.21, 0.11) if p.z < 0.055 else (0.30, 0.17, 0.09))
    return ob


parts = [blade(), handle(), guard(), pommel()]
bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
sword = bpy.context.view_layer.objects.active
sword.name = 'SM_WoodSword'; sword.data.name = 'SM_WoodSword'
sword.data.transform(Matrix.Translation((0, 0, -LENGTH / 2)))        # origin = centre of the length
if not sword.data.uv_layers:
    sword.data.uv_layers.new(name='UVMap')
mat = bpy.data.materials.new('M_WoodSword'); mat.use_nodes = True
nt = mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
vc = nt.nodes.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'
nt.links.new(vc.outputs['Color'], bsdf.inputs['Base Color'])
sword.data.materials.append(mat)
tris = sum(len(p.vertices) - 2 for p in sword.data.polygons)
bb = [sword.matrix_world @ V(c) for c in sword.bound_box]
log(f'tris {tris}  size_cm x {100 * (max(b.x for b in bb) - min(b.x for b in bb)):.1f} '
    f'y {100 * (max(b.y for b in bb) - min(b.y for b in bb)):.1f} z {100 * (max(b.z for b in bb) - min(b.z for b in bb)):.1f}')


# ---------------------------------------------------------------- previews
def preview():
    os.makedirs(CMP, exist_ok=True)
    sc = bpy.context.scene
    cam = bpy.data.objects.new('_cam', bpy.data.cameras.new('_cam')); sc.collection.objects.link(cam)
    cam.data.type = 'ORTHO'; sc.camera = cam
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'VERTEX'
    outs = []
    for tag, d, scale, centre, res in (('front', V((0.0, -1, 0.0)), 1.05, V((0, 0, 0)), (300, 900)),
                                       ('side', V((1, 0, 0.0)), 1.05, V((0, 0, 0)), (300, 900)),
                                       ('hilt', V((0.6, -1, 0.35)), 0.42, V((0, 0, -0.18)), (500, 600)),
                                       ('tip', V((0.6, -1, 0.35)), 0.30, V((0, 0, 0.35)), (500, 500))):
        sc.render.resolution_x, sc.render.resolution_y = res
        cam.data.ortho_scale = scale
        d = d.normalized(); cam.location = centre + d * 3
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        p = os.path.join(CMP, f'wood_sword_{tag}.png')
        sc.render.filepath = p; bpy.ops.render.render(write_still=True); outs.append(p)
    bpy.data.objects.remove(cam)
    return outs


log('previews', preview())
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, r"Export\Blender\WoodSword.blend"))
if '--no-export' not in args:
    bpy.ops.object.select_all(action='DESELECT'); sword.select_set(True); bpy.context.view_layer.objects.active = sword
    out = os.path.join(ROOT, 'Export', 'SM_WoodSword.fbx')
    bpy.ops.export_scene.fbx(filepath=out, use_selection=True, object_types={'MESH'}, apply_scale_options='FBX_SCALE_UNITS',
                             mesh_smooth_type='FACE', colors_type='SRGB', bake_anim=False, add_leaf_bones=False)
    log('fbx', out, os.path.getsize(out))
