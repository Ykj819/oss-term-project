# Headless build of the dive roll:
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b Export/Blender/Club.blend
#       --python Export/Blender/scripts/mannequin/build_roll.py -- [--no-export]
# Loads gen_roll.py into the .blend as a text, builds MM_Roll_Fwd, prints the CLAUDE.md checks, renders previews to
# Export/Blender/compare/roll_*.png, exports Export/MM_Roll_Fwd.fbx (old one kept as MM_Roll_Fwd_v1_backup.fbx) and saves
# the result as Export/Blender/Roll.blend (Club.blend itself is not overwritten).
import bpy, os, sys, math, shutil
from mathutils import Vector, Matrix

ROOT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject"
SRC = os.path.join(ROOT, r"Export\Blender\scripts\mannequin\gen_roll.py")
OUT_BLEND = os.path.join(ROOT, r"Export\Blender\Roll.blend")
FBX = os.path.join(ROOT, r"Export\MM_Roll_Fwd.fbx")
CMP = os.path.join(ROOT, r"Export\Blender\compare")
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []

txt = bpy.data.texts.get('gen_roll.py') or bpy.data.texts.new('gen_roll.py')
txt.clear(); txt.write(open(SRC, encoding='utf-8').read())
R = {}; exec(txt.as_string(), R)
act, log = R['make_roll']()
for row in log[::3]:
    print('ROLL frame/th/pel_y/pel_z/clear', row)
print('ROLL check:'); R['C']['check']((R['NAME'],))
print('ROLL leg twist max', R['leg_twist_max']())
print('ROLL ground (f, hand z, ball z, body clearance)', R['ground_contacts']())

# ---------------------------------------------------------------- previews
sc = bpy.context.scene; arm = R['arm']
sg = {}; exec(bpy.data.texts['skel_preview.py'].as_string(), sg)


def strip(frames, spacing, world, fname):
    for o in [o for o in bpy.data.objects if o.name.startswith('RPrev_')]:
        bpy.data.objects.remove(o)
    arm.animation_data.action = act
    try: arm.animation_data.action_slot = act.slots[0]
    except Exception: pass
    ys = []
    for i, f in enumerate(frames):
        arm.hide_viewport = False; sc.frame_set(f); bpy.context.view_layer.update()
        ob = sg['build_skel']()
        y = (-R['cap_disp'](f)) if world else i * spacing
        o = bpy.data.objects.new(f'RPrev_{f}', ob.data.copy()); sc.collection.objects.link(o)
        o.matrix_world = Matrix.Translation((0, y, 0)) @ ob.matrix_world
        ys.append(y)
    bpy.data.objects['SkelPreview'].hide_render = True; arm.hide_viewport = False
    me = bpy.data.meshes.new('RPrev_ground'); y0, y1 = min(ys) - 1.2, max(ys) + 1.2
    me.from_pydata([(-0.6, y0, 0), (0.6, y0, 0), (0.6, y1, 0), (-0.6, y1, 0)], [], [(0, 1, 2, 3)])
    g = bpy.data.objects.new('RPrev_ground', me); sc.collection.objects.link(g)
    cam = bpy.data.objects.get('RPrev_cam') or bpy.data.objects.new('RPrev_cam', bpy.data.cameras.new('RPrev_cam'))
    if cam.name not in sc.collection.objects: sc.collection.objects.link(cam)
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = (y1 - y0)
    cam.location = Vector((6.0, (y0 + y1) / 2, 0.9))
    cam.rotation_euler = Vector((-1, 0, 0)).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.render.resolution_x = int(220 * (y1 - y0)); sc.render.resolution_y = int(220 * 2.4)
    cam.data.sensor_fit = 'HORIZONTAL'
    sc.render.film_transparent = False
    sc.render.filepath = os.path.join(CMP, fname); bpy.ops.render.render(write_still=True)
    return sc.render.filepath


os.makedirs(CMP, exist_ok=True)
FR = [1, 5, 9, 13, 16, 19, 22, 25, 28, 31, 35, 39, 43, 48, 54]
print('ROLL preview', strip(FR, 1.25, False, 'roll_strip.png'))
print('ROLL preview', strip([1, 7, 13, 18, 23, 29, 35, 43, 54], 0, True, 'roll_world.png'))
for o in [o for o in bpy.data.objects if o.name.startswith('RPrev_') or o.name == 'SkelPreview']:
    bpy.data.objects.remove(o)
arm.hide_viewport = False

# ---------------------------------------------------------------- export + save
if '--no-export' not in args:
    bak = FBX.replace('.fbx', '_v1_backup.fbx')
    if os.path.exists(FBX) and not os.path.exists(bak):
        shutil.copy2(FBX, bak)
    arm.animation_data.action = act
    try: arm.animation_data.action_slot = act.slots[0]
    except Exception: pass
    sc.frame_start, sc.frame_end = R['F0'], R['F1']
    for o in bpy.context.view_layer.objects: o.select_set(False)
    arm.hide_viewport = False; arm.hide_set(False); arm.select_set(True); bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(filepath=FBX, use_selection=True, object_types={'ARMATURE'}, apply_scale_options='FBX_SCALE_UNITS',
                             add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                             bake_anim_use_all_bones=True, bake_anim_force_startend_keying=True, bake_anim_step=1.0,
                             bake_anim_simplify_factor=0.0, use_armature_deform_only=False)
    print('ROLL fbx', os.path.getsize(FBX))
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print('ROLL saved', OUT_BLEND)
