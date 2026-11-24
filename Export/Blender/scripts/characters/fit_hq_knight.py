# Fit the user's Tripo knight (Export/HighQualityKnight/SKM_HQKnight.fbx: own rig, T-pose, 0.97 m tall, UE5 mannequin bone
# names) onto the UE mannequin skeleton (Export/Reference/SKM_Manny_Simple.fbx, A-pose) -> Export/SKM_HQKnight_Manny.fbx,
# imported onto SK_Mannequin by Tools/import_hq_knight_manny.py (all player anims, physics asset, stick/potion work).
# Headless:  blender -b --factory-startup --python <this file> [-- --no-export]
#   saves Export/Blender/HQKnight_Fit.blend, previews Export/Blender/compare/hq_knight_*.png
# Method: knight scaled uniformly to Manny's pelvis height, then every Tripo bone gets an affine map
#   (translate its joint onto Manny's joint, rotate its joint->child segment onto Manny's, stretch along that segment to
#   Manny's length; leaf bones: parent's rotation, no stretch; twist bones = parent's map). Vertices are deformed by the
#   weighted blend of those maps with the Tripo weights, then bound to Manny's armature with the same vertex groups
#   (bone names match 1:1).
import bpy, math, os, sys
from mathutils import Vector, Matrix, Quaternion

ROOT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject"
REF = os.path.join(ROOT, r"Export\Reference\SKM_Manny_Simple.fbx")
SRC = os.path.join(ROOT, r"Export\HighQualityKnight\SKM_HQKnight.fbx")
OUT_BLEND = os.path.join(ROOT, r"Export\Blender\HQKnight_Fit.blend")
OUT_FBX = os.path.join(ROOT, r"Export\SKM_HQKnight_Manny.fbx")
CMP = os.path.join(ROOT, r"Export\Blender\compare")
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
V = Vector
log = lambda *a: print('HQFIT', *a)

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

# ---- mannequin (target) armature + its mesh for the comparison render
bpy.ops.import_scene.fbx(filepath=REF, ignore_leaf_bones=False, automatic_bone_orientation=False)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
arm.name = 'root'
if arm.animation_data:
    arm.animation_data.action = None
manny_mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
manny_mesh.name = 'Manny_Compare'
existing = set(bpy.data.objects)

# ---- Tripo knight (source)
bpy.ops.import_scene.fbx(filepath=SRC, ignore_leaf_bones=False, automatic_bone_orientation=False)
new = [o for o in bpy.data.objects if o not in existing]
tarm = next(o for o in new if o.type == 'ARMATURE')
tmesh = next(o for o in new if o.type == 'MESH')
tarm.data.pose_position = 'REST'
bpy.context.view_layer.update()
# textures sit next to the FBX (the .fbm folder was flattened when copying)
for img in bpy.data.images:
    if img.filepath and not os.path.exists(bpy.path.abspath(img.filepath)):
        cand = os.path.join(os.path.dirname(SRC), os.path.basename(img.filepath.replace('\\', '/')))
        if os.path.exists(cand):
            img.filepath = cand; img.reload()
log('images', [(i.name, os.path.exists(bpy.path.abspath(i.filepath))) for i in bpy.data.images if i.filepath])

mh = {b.name: arm.matrix_world @ b.head_local for b in arm.data.bones}
th_raw = {b.name: tarm.matrix_world @ b.head_local for b in tarm.data.bones}
S = mh['pelvis'].z / th_raw['pelvis'].z
th = {n: p * S for n, p in th_raw.items()}
log(f'scale {S:.4f}  knight height {0.9714 * S:.3f} m  manny pelvis {mh["pelvis"].z:.3f}')
missing = [n for n in th if n not in mh]
log('tripo bones missing on manny:', missing)

# ---- segment child for each bone (joint -> next joint)
CHILD = {'pelvis': 'spine_01', 'spine_01': 'spine_02', 'spine_02': 'spine_03', 'spine_03': 'spine_04',
         'spine_04': 'spine_05', 'spine_05': 'neck_01', 'neck_01': 'neck_02', 'neck_02': 'head'}
for s in ('l', 'r'):
    CHILD.update({f'clavicle_{s}': f'upperarm_{s}', f'upperarm_{s}': f'lowerarm_{s}', f'lowerarm_{s}': f'hand_{s}',
                  f'hand_{s}': f'middle_metacarpal_{s}', f'thigh_{s}': f'calf_{s}', f'calf_{s}': f'foot_{s}',
                  f'foot_{s}': f'ball_{s}', f'thumb_01_{s}': f'thumb_02_{s}', f'thumb_02_{s}': f'thumb_03_{s}'})
    for f in ('index', 'middle', 'ring', 'pinky'):
        CHILD.update({f'{f}_metacarpal_{s}': f'{f}_01_{s}', f'{f}_01_{s}': f'{f}_02_{s}', f'{f}_02_{s}': f'{f}_03_{s}'})


def align(a, b, a2=None, b2=None):
    """rotation taking direction a to b; if a2/b2 are given, also turns the plane (a, a2) onto (b, b2)"""
    q = a.normalized().rotation_difference(b.normalized())
    if a2 is not None:
        bn = b.normalized()
        x = (q @ a2); x = (x - bn * x.dot(bn)).normalized()
        y = (b2 - bn * b2.dot(bn)).normalized()
        ang = math.atan2(x.cross(y).dot(bn), x.dot(y))
        q = Quaternion(bn, ang) @ q
    return q


def affine(head_src, head_dst, rot, axis=None, ratio=1.0):
    """x -> head_dst + rot @ stretch(x - head_src) with the stretch along axis (source space)"""
    St = Matrix.Identity(3)
    if axis is not None and abs(ratio - 1.0) > 1e-4:
        u = axis.normalized()
        St = Matrix.Identity(3) + (ratio - 1.0) * Matrix(((u.x * u.x, u.x * u.y, u.x * u.z),
                                                          (u.y * u.x, u.y * u.y, u.y * u.z),
                                                          (u.z * u.x, u.z * u.y, u.z * u.z)))
    L = rot.to_matrix() @ St
    M = L.to_4x4()
    M.translation = head_dst - L @ head_src
    return M


TORSO = {'pelvis', 'spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05', 'neck_01', 'neck_02', 'head'}
maps, rots, ratios = {}, {}, {}
order = []
def walk(b):
    order.append(b.name)
    for c in b.children:
        walk(c)
for b in tarm.data.bones:
    if b.parent is None:
        walk(b)

for n in order:
    b = tarm.data.bones[n]
    par = b.parent.name if b.parent else None
    if par is None or n == 'root':
        maps[n] = affine(th[n], mh.get(n, th[n]), Quaternion()); rots[n] = Quaternion(); continue
    if 'twist' in n:
        maps[n] = maps[par]; rots[n] = rots[par]; continue
    if n in TORSO:   # Tripo's spine joints are bunched (stretch ratios 0.4..3.2): keep the knight's own torso shape
        maps[n] = Matrix.Identity(4); rots[n] = Quaternion(); continue
    c = CHILD.get(n)
    if c and c in th and c in mh and n in mh:
        a = th[c] - th[n]; m = mh[c] - mh[n]
        if n.startswith('hand_'):
            s = n[-1]
            q = align(a, m, th[f'index_01_{s}'] - th[f'pinky_01_{s}'], mh[f'index_01_{s}'] - mh[f'pinky_01_{s}'])
        else:
            q = align(a, m)
        r = m.length / max(a.length, 1e-6)
        ratios[n] = r
        if n.startswith('hand_'):
            r = 1.0   # metacarpal heads sit at different depths in the two rigs: don't squash the palm
        maps[n] = affine(th[n], mh[n], q, a, r); rots[n] = q
    else:   # leaf: parent's rotation, joint moved onto Manny's
        q = rots[par]
        maps[n] = affine(th[n], mh.get(n, th[n]), q); rots[n] = q
log('length ratios', {k: round(v, 2) for k, v in ratios.items() if not any(f in k for f in ('index', 'middle', 'ring', 'pinky', 'thumb'))})
fr = [v for k, v in ratios.items() if any(f in k for f in ('index', 'middle', 'ring', 'pinky', 'thumb'))]
log(f'finger ratios min {min(fr):.2f} max {max(fr):.2f}')
for s in ('l', 'r'):
    d = rots[f'hand_{s}'].rotation_difference(rots[f'lowerarm_{s}'])
    log(f'hand_{s} vs lowerarm_{s} rotation difference {math.degrees(d.angle):.1f} deg')

# ---- deform the knight mesh
me = tmesh.data.copy()
me.name = 'SKM_HQKnight_Manny'
import re
base = lambda s: re.sub(r'\.\d{3}$', '', s)   # the FBX importer suffixes names that clash with Manny's ("pelvis.001")
gnames = {g.index: base(g.name) for g in tmesh.vertex_groups}
Mw = tmesh.matrix_world
inv_arm = arm.matrix_world.inverted()
unweighted = 0
moved = []
for v in me.vertices:
    p = (Mw @ v.co) * S
    acc = V((0, 0, 0)); wsum = 0.0
    for g in v.groups:
        n = gnames.get(g.group)
        if g.weight <= 0 or n not in maps:
            continue
        acc += g.weight * (maps[n] @ p); wsum += g.weight
    if wsum <= 1e-6:
        unweighted += 1; q = p
    else:
        q = acc / wsum
    moved.append((q - p).length)
    v.co = inv_arm @ q
log(f'verts {len(me.vertices)} unweighted {unweighted} max move {max(moved):.3f} m')

ob = bpy.data.objects.new('SKM_HQKnight_Manny', me)
bpy.context.scene.collection.objects.link(ob)
if len(ob.vertex_groups) == 0:   # Blender 3+ keeps the group names on the mesh data: the copy already has them
    for g in sorted(tmesh.vertex_groups, key=lambda g: g.index):
        ob.vertex_groups.new(name=base(g.name))
for g in ob.vertex_groups:
    g.name = base(g.name)
ob.parent = arm
ob.matrix_parent_inverse = Matrix.Identity(4); ob.matrix_basis = Matrix.Identity(4)
mod = ob.modifiers.new('Armature', 'ARMATURE'); mod.object = arm
bpy.context.view_layer.objects.active = ob
if me.has_custom_normals:
    bpy.ops.mesh.customdata_custom_splitnormals_clear()
for poly in me.polygons:
    poly.use_smooth = True
for m in me.materials:
    if m:
        m.name = 'M_HQKnight'
bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
bad = [g.name for g in ob.vertex_groups if g.name not in arm.data.bones]
log('vertex groups without a manny bone:', bad)

# Tripo source no longer needed
bpy.data.objects.remove(tmesh, do_unlink=True)
bpy.data.objects.remove(tarm, do_unlink=True)
bpy.context.view_layer.update()

# ---- previews (workbench, texture colour)
def preview():
    os.makedirs(CMP, exist_ok=True)
    sc = bpy.context.scene
    cam = bpy.data.objects.new('_cam', bpy.data.cameras.new('_cam')); sc.collection.objects.link(cam)
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.2; sc.camera = cam
    sc.render.engine = 'BLENDER_WORKBENCH'
    sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'TEXTURE'
    sc.render.resolution_x = 420; sc.render.resolution_y = 480
    arm.hide_render = True
    pose = {'upperarm_l': ('X', -60), 'lowerarm_l': ('Z', 70), 'upperarm_r': ('Z', 60), 'lowerarm_r': ('Z', 90),
            'hand_r': ('X', 40), 'thigh_l': ('Z', 60), 'calf_l': ('Z', -90), 'thigh_r': ('Z', -25),
            'spine_03': ('X', 20), 'neck_01': ('Z', 25)}
    outs = []
    for tag, obj, posed in (('manny', manny_mesh, False), ('knight', ob, False), ('knight_posed', ob, True),
                            ('manny_posed', manny_mesh, True)):
        for o in bpy.data.objects:
            if o.type == 'MESH':
                o.hide_render = o is not obj
        for pb in arm.pose.bones:
            pb.matrix_basis = Matrix.Identity(4)
        if posed:
            for n, (ax, d) in pose.items():
                pb = arm.pose.bones[n]; pb.rotation_mode = 'XYZ'
                setattr(pb.rotation_euler, 'xyz'['XYZ'.index(ax)], math.radians(d))
        bpy.context.view_layer.update()
        for view, d in (('front', V((0.0, -1, 0.05))), ('side', V((1, 0, 0.05)))):
            d = d.normalized(); cam.location = V((0, 0, 0.95)) + d * 6
            cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
            p = os.path.join(CMP, f'hq_knight_{tag}_{view}.png')
            sc.render.filepath = p; bpy.ops.render.render(write_still=True); outs.append(p)
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.data.objects.remove(cam)
    return outs


log('previews', preview())
manny_mesh.hide_set(True); manny_mesh.hide_render = True
bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)

if '--no-export' not in args:
    bpy.ops.object.select_all(action='DESELECT')
    arm.hide_set(False); arm.select_set(True); ob.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(filepath=OUT_FBX, use_selection=True, object_types={'ARMATURE', 'MESH'},
                             apply_scale_options='FBX_SCALE_UNITS', add_leaf_bones=False, bake_anim=False,
                             mesh_smooth_type='FACE', use_armature_deform_only=False, path_mode='STRIP')
    log('fbx', OUT_FBX, os.path.getsize(OUT_FBX))
