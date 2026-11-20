# Puts the player knight mesh into Export/Blender/Roll.blend so the user can see it while editing MM_Roll_Fwd.
#   "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b Export/Blender/Roll_bones_only_backup.blend
#       --python Export/Blender/scripts/mannequin/add_knight_to_roll.py
# (run on the bones-only backup; the first run creates that backup from Roll.blend)
# The knight is skinned on the mannequin REFERENCE rest pose, the roll rig `root` has a different rest pose. So the
# knight's own armature is appended, posed into the roll rig's rest pose, the Armature modifier is applied (mesh now
# in the roll rest pose, vertex groups kept), and the mesh is re-pointed at `root`. The knight armature is deleted.
# The mesh is unselectable, so clicks in Pose Mode pick the bones. Display only: the FBX export (armature only) is unchanged.
import bpy, os, shutil
from mathutils import Vector, Matrix

ROOT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject"
KB = os.path.join(ROOT, r"Export\Blender\PlayerKnight.blend")
OUT = os.path.join(ROOT, r"Export\Blender\Roll.blend")
CMP = os.path.join(ROOT, r"Export\Blender\compare")
sc = bpy.context.scene
roll = bpy.data.objects['root']

bak = OUT.replace('.blend', '_bones_only_backup.blend')
if not os.path.exists(bak) and os.path.abspath(bpy.data.filepath) == os.path.abspath(OUT):
    shutil.copy2(OUT, bak)
for o in [o for o in bpy.data.objects if o.get('knight_view')]:
    bpy.data.objects.remove(o)
col = bpy.data.collections.get('Knight_View') or bpy.data.collections.new('Knight_View')
if col.name not in sc.collection.children: sc.collection.children.link(col)

with bpy.data.libraries.load(KB) as (src, dst):
    dst.objects = ['SKM_PlayerKnight', 'root', 'SKM_Manny_Simple']
mesh_o, karm, kempty = dst.objects
for o in dst.objects:
    col.objects.link(o); o['knight_view'] = True
mesh_o.name = 'PlayerKnight_View'; karm.name = 'KnightRig_tmp'; kempty.name = 'KnightRig_tmp_scale'
bpy.context.view_layer.update()

# 1. pose the knight armature into the roll rig's rest pose (parents first)
def depth(b):
    d = 0
    while b.parent: b = b.parent; d += 1
    return d
for pb in karm.pose.bones: pb.matrix_basis = Matrix.Identity(4)
for pb in sorted(karm.pose.bones, key=lambda p: depth(p.bone)):
    if pb.name not in roll.data.bones: continue
    pb.matrix = karm.matrix_world.inverted() @ roll.matrix_world @ roll.data.bones[pb.name].matrix_local
    bpy.context.view_layer.update()

# 2. apply the deformation, keep the vertex groups
for o in bpy.context.view_layer.objects: o.select_set(False)
bpy.context.view_layer.objects.active = mesh_o; mesh_o.select_set(True)
mod = next(m for m in mesh_o.modifiers if m.type == 'ARMATURE')
bpy.ops.object.modifier_apply(modifier=mod.name)

# 3. bind to the roll rig
mw = mesh_o.matrix_world.copy()
mesh_o.parent = None; mesh_o.matrix_world = mw
m = mesh_o.modifiers.new('Armature', 'ARMATURE'); m.object = roll; m.use_vertex_groups = True
bpy.data.objects.remove(karm); bpy.data.objects.remove(kempty)
bpy.context.view_layer.update()
mesh_o.hide_select = True
roll.show_in_front = True          # bones drawn over the mesh
print('KV vgroups', len(mesh_o.vertex_groups), 'mesh scale', tuple(round(x, 4) for x in mesh_o.matrix_world.to_scale()))

# side-view previews with the knight
cam = bpy.data.objects.new('KV_cam', bpy.data.cameras.new('KV_cam')); sc.collection.objects.link(cam)
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.6
cam.rotation_euler = Vector((-1, 0, 0)).to_track_quat('-Z', 'Y').to_euler()
sc.camera = cam; sc.render.engine = 'BLENDER_WORKBENCH'
sc.render.resolution_x = 300; sc.render.resolution_y = 340
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
roll.hide_render = True
os.makedirs(CMP, exist_ok=True)
outs = []
for f in (1, 7, 13, 18, 23, 29, 35, 43, 54):
    sc.frame_set(f); bpy.context.view_layer.update()
    c = roll.matrix_world @ roll.pose.bones['pelvis'].head
    cam.location = Vector((6.0, c.y, 0.9))
    sc.render.filepath = os.path.join(CMP, f'roll_knight_{f:02d}.png'); bpy.ops.render.render(write_still=True)
    outs.append(sc.render.filepath)
bpy.data.objects.remove(cam)
roll.hide_render = False

sc.frame_set(1)
for o in bpy.context.view_layer.objects: o.select_set(False)
bpy.context.view_layer.objects.active = roll; roll.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print('KV previews', len(outs))
print('KV saved', OUT)
