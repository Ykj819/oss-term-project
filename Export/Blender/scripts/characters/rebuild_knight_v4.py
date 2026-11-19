# Headless rebuild of the player knight v4:  regenerate -> bake (4K) -> under-side check renders -> save -> FBX.
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b Export/Blender/PlayerKnight.blend
#       --python Export/Blender/scripts/characters/rebuild_knight_v4.py -- [--no-bake] [--no-export]
# Check renders use backface culling (= what UE shows with a one-sided material): Export/Blender/compare/under_*.png
import bpy, os, sys, math, time
from mathutils import Vector

D = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Blender\scripts\characters"
CMP = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Blender\compare"
FBX = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\SKM_PlayerKnight.fbx"
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []


def load(name):
    g = {'__name__': name}
    exec(open(os.path.join(D, name + '.py'), encoding='utf-8').read(), g)
    return g


def under_renders():
    sc = bpy.context.scene
    cmp = load('compare_ref'); cam, sun = cmp['setup_render'](sc)
    cam.data.type = 'PERSP'; cam.data.lens = 35
    sc.render.resolution_x = 900; sc.render.resolution_y = 900
    ob = bpy.data.objects['SKM_PlayerKnight']
    for m in ob.data.materials:
        m.use_backface_culling = True
    tgt = Vector((0, 0, 1.15))
    outs = []
    for name, pos, aim in (('front_low', Vector((0.9, -1.9, 0.15)), tgt), ('back_low', Vector((-0.9, 1.9, 0.15)), tgt),
                           ('shoulder_low', Vector((0.9, -0.55, 0.95)), Vector((0.25, 0.0, 1.5))),
                           ('skirt_low', Vector((0.35, -0.9, 0.45)), Vector((0, 0, 1.0)))):
        cam.location = pos
        cam.rotation_euler = (aim - pos).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(CMP, f'under_{name}.png')
        bpy.ops.render.render(write_still=True); outs.append(sc.render.filepath)
    for m in ob.data.materials:
        m.use_backface_culling = False
    for n in ('_cmp_cam', '_cmp_sun'):
        o = bpy.data.objects.get(n)
        if o:
            bpy.data.objects.remove(o, do_unlink=True)
    return outs


t = time.time()
arm = bpy.data.objects['root']
for pb in arm.pose.bones:
    pb.rotation_euler = (0, 0, 0); pb.rotation_quaternion = (1, 0, 0, 0); pb.location = (0, 0, 0)
v4 = load('gen_player_knight_v4')
print('KNIGHT build', v4['run'](), round(time.time() - t, 1))
if '--no-bake' not in args:
    bk = load('bake_player_knight'); bk['RES'] = 4096
    print('KNIGHT bake', bk['run'](), round(time.time() - t, 1))
print('KNIGHT under', under_renders())
print('KNIGHT compare', load('compare_ref')['run']())
bpy.ops.wm.save_mainfile()
if '--no-export' not in args:
    ob = bpy.data.objects['SKM_PlayerKnight']
    bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True); ob.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(filepath=FBX, use_selection=True, object_types={'ARMATURE', 'MESH'},
                             apply_scale_options='FBX_SCALE_UNITS', add_leaf_bones=False, bake_anim=False,
                             mesh_smooth_type='FACE', colors_type='SRGB', use_armature_deform_only=False)
    print('KNIGHT fbx', os.path.getsize(FBX))
print('KNIGHT done', round(time.time() - t, 1))
