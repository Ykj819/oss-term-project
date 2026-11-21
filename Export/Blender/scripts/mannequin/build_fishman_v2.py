# Headless build of the fishman boss anims v2:
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b Export/Blender/Club.blend
#       --python Export/Blender/scripts/mannequin/build_fishman_v2.py -- [--no-export] [--no-preview] [--only Fish_Slam,...]
# Loads gen_fishman_v2.py as a text, keeps the v1 actions as Fish_*_v1, builds the v2 actions, prints the CLAUDE.md checks,
# adds a display-only fishman mesh (FishMan_View, rebound to `root`), renders before/after previews to
# Export/Blender/compare/fishman_<anim>.png, exports Export/Fish_*.fbx (previous files kept as Fish_*_before_v2.fbx)
# and saves Export/Blender/Fishman_v2.blend (Club.blend itself is not overwritten).
import bpy, os, sys, shutil
import numpy as np
from mathutils import Vector, Matrix

ROOT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject"
SRC = os.path.join(ROOT, r"Export\Blender\scripts\mannequin\gen_fishman_v2.py")
MODEL = os.path.join(ROOT, r"Export\Blender\FishMan_Model.blend")
OUT_BLEND = os.path.join(ROOT, r"Export\Blender\Fishman_v2.blend")
CMP = os.path.join(ROOT, r"Export\Blender\compare")
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
only = args[args.index('--only') + 1].split(',') if '--only' in args else None

txt = bpy.data.texts.get('gen_fishman_v2.py') or bpy.data.texts.new('gen_fishman_v2.py')
txt.clear(); txt.write(open(SRC, encoding='utf-8').read())
for n in ('gen_fishman.py', 'fishman_helpers.py'):
    pass   # v1 texts stay in the file (gen_club.py still execs fishman_helpers for STANCE / foot rotations)
for name in ('Fish_Slam', 'Fish_Jump_Slam', 'Fish_Stomp_R', 'Fish_Stomp_L'):
    a = bpy.data.actions.get(name)
    if a and not bpy.data.actions.get(name + '_v1'):
        a.name = name + '_v1'; a.use_fake_user = True
R = {}; exec(txt.as_string(), R)
anims = [(n, k) for n, k in R['ANIMS'] if only is None or n in only]
for n, k in anims: R['make'](n, k)
names = tuple(n for n, _ in anims)
print('FISH check v2:'); R['C']['check'](names); R['check_more'](names)
print('FISH check v1:'); R['C']['check'](tuple(n + '_v1' for n in names)); R['check_more'](tuple(n + '_v1' for n in names))

sc = bpy.context.scene; arm = R['arm']

# ---------------------------------------------------------------- display mesh (same method as add_knight_to_roll.py)
def add_view_mesh():
    for o in [o for o in bpy.data.objects if o.get('fish_view')]:
        bpy.data.objects.remove(o)
    col = bpy.data.collections.get('FishMan_View') or bpy.data.collections.new('FishMan_View')
    if col.name not in sc.collection.children: sc.collection.children.link(col)
    with bpy.data.libraries.load(MODEL) as (src, dst):
        dst.objects = ['SK_FishMan', 'root', 'SKM_Manny_Simple']
    mesh_o, karm, kempty = dst.objects
    for o in dst.objects:
        col.objects.link(o); o['fish_view'] = True
    mesh_o.name = 'FishMan_View'
    arm.animation_data.action = None
    for pb in arm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    def depth(b):
        d = 0
        while b.parent: b = b.parent; d += 1
        return d
    for pb in karm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
    for pb in sorted(karm.pose.bones, key=lambda p: depth(p.bone)):
        if pb.name not in arm.data.bones: continue
        pb.matrix = karm.matrix_world.inverted() @ arm.matrix_world @ arm.data.bones[pb.name].matrix_local
        bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects: o.select_set(False)
    bpy.context.view_layer.objects.active = mesh_o; mesh_o.select_set(True)
    mod = next(m for m in mesh_o.modifiers if m.type == 'ARMATURE')
    bpy.ops.object.modifier_apply(modifier=mod.name)
    mw = mesh_o.matrix_world.copy(); mesh_o.parent = None; mesh_o.matrix_world = mw
    m = mesh_o.modifiers.new('Armature', 'ARMATURE'); m.object = arm; m.use_vertex_groups = True
    bpy.data.objects.remove(karm); bpy.data.objects.remove(kempty)
    mesh_o.hide_select = True; arm.show_in_front = True
    bpy.context.view_layer.update()
    print('FISH view mesh', len(mesh_o.data.vertices), 'verts')
    return mesh_o

# ---------------------------------------------------------------- before / after previews (top row v1, bottom row v2)
KEYF = {'Fish_Slam': [1, 30, 50, 64, 70, 74, 90, 130], 'Fish_Jump_Slam': [1, 32, 42, 56, 66, 72, 90, 120],
        'Fish_Stomp_R': [1, 20, 34, 46, 54, 80, 106, 115], 'Fish_Stomp_L': [1, 20, 34, 46, 54, 80, 106, 115]}
TW, TH = 260, 330

def render_strip(name):
    cam = bpy.data.objects.get('FV_cam') or bpy.data.objects.new('FV_cam', bpy.data.cameras.new('FV_cam'))
    if cam.name not in sc.collection.objects: sc.collection.objects.link(cam)
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 3.0; cam.data.sensor_fit = 'VERTICAL'
    d = Vector((-0.55, -1.0, 0.25)).normalized()
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam; sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'MATERIAL'
    sc.render.resolution_x = TW; sc.render.resolution_y = TH; sc.render.resolution_percentage = 100
    sc.render.film_transparent = False; arm.hide_render = True
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name != 'FishMan_View': o.hide_render = True     # Club / stick / skeleton previews
    tiles = []
    for act_name in (name + '_v1', name):
        R['set_action'](act_name); row = []
        for f in KEYF[name]:
            sc.frame_set(f); bpy.context.view_layer.update()
            c = arm.matrix_world @ arm.pose.bones['pelvis'].head
            cam.location = Vector((c.x, c.y, c.z + 0.15)) + d * 6.0
            p = os.path.join(CMP, '_tile.png'); sc.render.filepath = p; bpy.ops.render.render(write_still=True)
            img = bpy.data.images.load(p); a = np.empty(TW * TH * 4, np.float32); img.pixels.foreach_get(a)
            row.append(a.reshape(TH, TW, 4)); bpy.data.images.remove(img)
        tiles.append(np.concatenate(row, axis=1))
    full = np.concatenate([tiles[1], tiles[0]], axis=0)        # image rows are bottom-up: v2 below, v1 on top
    out = bpy.data.images.new('FV_out', full.shape[1], full.shape[0], alpha=True)
    out.pixels.foreach_set(full.ravel()); out.filepath_raw = os.path.join(CMP, f'fishman_{name}.png'); out.file_format = 'PNG'
    out.save(); bpy.data.images.remove(out)
    os.remove(os.path.join(CMP, '_tile.png'))
    arm.hide_render = False
    return os.path.join(CMP, f'fishman_{name}.png')

if '--no-preview' not in args:
    os.makedirs(CMP, exist_ok=True)
    add_view_mesh()
    for n in names: print('FISH preview', render_strip(n))

# ---------------------------------------------------------------- export + save
if '--no-export' not in args:
    for n in names:
        fbx = os.path.join(ROOT, 'Export', n + '.fbx'); bak = fbx.replace('.fbx', '_before_v2.fbx')
        if os.path.exists(fbx) and not os.path.exists(bak): shutil.copy2(fbx, bak)
        act = R['set_action'](n)
        sc.frame_start, sc.frame_end = map(int, act.frame_range); sc.render.fps = 60
        for o in bpy.context.view_layer.objects: o.select_set(False)
        arm.hide_viewport = False; arm.hide_set(False); arm.select_set(True); bpy.context.view_layer.objects.active = arm
        bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={'ARMATURE'}, apply_scale_options='FBX_SCALE_UNITS',
                                 add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                                 bake_anim_use_all_bones=True, bake_anim_force_startend_keying=True, bake_anim_step=1.0,
                                 bake_anim_simplify_factor=0.0, use_armature_deform_only=False)
        print('FISH fbx', fbx, os.path.getsize(fbx))
R['set_action'](names[0]); sc.frame_start, sc.frame_end = map(int, bpy.data.actions[names[0]].frame_range); sc.frame_set(1)
arm.hide_viewport = False; arm.hide_set(False)
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print('FISH saved', OUT_BLEND)
