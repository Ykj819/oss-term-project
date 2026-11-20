# Bake the Arena collection (made by gen_arena.py) into one mesh SM_Arena with vertex colours and export
# Export/SM_Arena.fbx. Colours = each part material's noise/ramp evaluated per face corner (same as the Blender shader).
# UE: Tools/import_arena.py (M_Stylized_Prop: VertexColor^2.2 * Tint).
import bpy, math, os
from mathutils import Vector, noise

PROJ = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject"
col = bpy.data.collections['Arena']
for o in list(bpy.data.objects):
    if o.name.startswith('SM_Arena_Export'):
        bpy.data.objects.remove(o, do_unlink=True)
exp_mat = bpy.data.materials.get('M_Stylized_Prop') or bpy.data.materials.new('M_Stylized_Prop')

dg = bpy.context.evaluated_depsgraph_get()
parts = []
for o in col.objects:
    if o.type != 'MESH':
        continue
    m = o.material_slots[0].material
    ramp = next(n for n in m.node_tree.nodes if n.type == 'VALTORGB')
    c2 = Vector(ramp.color_ramp.elements[0].color[:3])
    c1 = Vector(ramp.color_ramp.elements[1].color[:3])
    sc = next(n for n in m.node_tree.nodes if n.type == 'TEX_NOISE').inputs['Scale'].default_value
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    me.transform(o.matrix_world)
    me.materials.clear()
    me.materials.append(exp_mat)
    co = [v.co.copy() for v in me.vertices]
    vcols = []
    for v in co:
        f = (0.5 + 0.5 * noise.noise(v * sc) - 0.35) / 0.3
        f = min(1.0, max(0.0, f))
        c = c2.lerp(c1, f)
        vcols.append((c.x, c.y, c.z, 1.0))
    attr = me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    flat = []
    uvs = []
    for lp in me.loops:
        flat.extend(vcols[lp.vertex_index])
        p = co[lp.vertex_index]
        uvs.extend(((p.x + p.y) * 0.1, p.z * 0.1))
    attr.data.foreach_set('color', flat)          # linear in, stored sRGB-encoded (exported as SRGB)
    uv = me.uv_layers.new(name='UVMap')
    uv.data.foreach_set('uv', uvs)
    ob = bpy.data.objects.new('SM_Arena_Export_' + o.name, me)
    bpy.context.scene.collection.objects.link(ob)
    parts.append(ob)

bpy.ops.object.select_all(action='DESELECT')
for ob in parts:
    ob.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
arena = bpy.context.view_layer.objects.active
arena.name = 'SM_Arena_Export'
arena.data.name = 'SM_Arena'
col.hide_viewport = False
tris = sum(len(p.vertices) - 2 for p in arena.data.polygons)

fbx = os.path.join(PROJ, 'Export', 'SM_Arena.fbx')
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, object_types={'MESH'}, colors_type='SRGB',
                         apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE', use_mesh_modifiers=True,
                         bake_anim=False)
arena.hide_set(True)
arena.hide_render = True
print('ARENA_BAKE tris', tris, 'fbx', os.path.getsize(fbx))
