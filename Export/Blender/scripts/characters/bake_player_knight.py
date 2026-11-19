# Bake SKM_PlayerKnight's vertex colours (RGB albedo, A metallic) + ambient occlusion to textures:
#   Export/Textures/PlayerKnight/T_PlayerKnight_BC.png   (sRGB albedo, AO multiplied in softly)
#   Export/Textures/PlayerKnight/T_PlayerKnight_ORM.png  (linear: R = AO, G = roughness, B = metallic)
# UVs: Smart UV Project (one atlas). Then the Blender material is switched to the baked textures (preview = UE look).
import bpy, os, math
import numpy as np

NAME = 'SKM_PlayerKnight'
RES = 2048
OUT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Textures\PlayerKnight"
ROUGH_CLOTH, ROUGH_METAL = 0.75, 0.32
AO_IN_BC = 0.55


def uv_unwrap(ob):
    me = ob.data
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    me.uv_layers.new(name='UVMap')
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.003, area_weight=0.0, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=0.003, rotate=True)
    bpy.ops.object.mode_set(mode='OBJECT')


def float_image(name):
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, RES, RES, alpha=False, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'
    return img


def bake(ob, mat, img, kind, emit_socket=None):
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img
    nt.nodes.active = tex; tex.select = True
    if kind == 'EMIT':
        attr = nt.nodes.new('ShaderNodeVertexColor'); attr.layer_name = 'Col'
        em = nt.nodes.new('ShaderNodeEmission')
        nt.links.new(attr.outputs[emit_socket], em.inputs['Color'])
        nt.links.new(em.outputs[0], out.inputs['Surface'])
    else:
        bsdf = nt.nodes.new('ShaderNodeBsdfDiffuse')
        nt.links.new(bsdf.outputs[0], out.inputs['Surface'])
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.bake(type=kind, margin=16, use_clear=True)
    return np.array(img.pixels[:], dtype=np.float32).reshape(RES, RES, 4)[..., :3]


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def save_png(name, rgb):
    img = bpy.data.images.get(name)
    if img:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, RES, RES, alpha=False, float_buffer=False)
    img.colorspace_settings.name = 'Non-Color'
    rgba = np.concatenate([np.clip(rgb, 0, 1), np.ones((RES, RES, 1), np.float32)], axis=2)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = os.path.join(OUT, name + '.png'); img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img)
    return os.path.join(OUT, name + '.png')


def run():
    os.makedirs(OUT, exist_ok=True)
    ob = bpy.data.objects[NAME]
    sc = bpy.context.scene
    try:
        sc.render.engine = 'CYCLES'
    except TypeError:
        pass
    sc.cycles.samples = 48
    sc.cycles.use_denoising = False
    if sc.world is None:
        sc.world = bpy.data.worlds.new('World')
    sc.world.light_settings.distance = 0.12           # AO reach (m)
    # hide everything else from the bake (other meshes would occlude the AO)
    hidden = []
    for o in sc.objects:
        if o.type == 'MESH' and o != ob and not o.hide_render:
            o.hide_render = True; hidden.append(o)
    uv_unwrap(ob)
    bake_mat = bpy.data.materials.get('_bake') or bpy.data.materials.new('_bake'); bake_mat.use_nodes = True
    keep = list(ob.data.materials)
    ob.data.materials.clear(); ob.data.materials.append(bake_mat)
    col = bake(ob, bake_mat, float_image('_bk_col'), 'EMIT', 'Color')      # linear albedo
    met = bake(ob, bake_mat, float_image('_bk_met'), 'EMIT', 'Alpha')[..., 0]
    ao = bake(ob, bake_mat, float_image('_bk_ao'), 'AO')[..., 0]
    ao = np.clip(ao, 0, 1)
    bc = col * (1 - AO_IN_BC + AO_IN_BC * ao)[..., None]
    rough = ROUGH_CLOTH + (ROUGH_METAL - ROUGH_CLOTH) * met
    # image rows: Blender pixels start at the bottom -> PNG saved by Blender handles it (same convention both ways)
    p_bc = save_png('T_PlayerKnight_BC', srgb(bc))
    p_orm = save_png('T_PlayerKnight_ORM', np.stack([ao, rough, met], axis=2))
    for o in hidden:
        o.hide_render = False
    # preview material with the baked textures
    ob.data.materials.clear()
    mat = bpy.data.materials.get('M_PlayerKnight') or bpy.data.materials.new('M_PlayerKnight')
    mat.use_nodes = True; nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial'); bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bsdf.outputs[0], out.inputs['Surface'])
    t1 = nt.nodes.new('ShaderNodeTexImage'); t1.image = bpy.data.images.load(p_bc, check_existing=False)
    t2 = nt.nodes.new('ShaderNodeTexImage'); t2.image = bpy.data.images.load(p_orm, check_existing=False)
    t2.image.colorspace_settings.name = 'Non-Color'
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(t1.outputs['Color'], bsdf.inputs['Base Color'])
    nt.links.new(t2.outputs['Color'], sep.inputs['Color'])
    nt.links.new(sep.outputs[1], bsdf.inputs['Roughness'])
    nt.links.new(sep.outputs[2], bsdf.inputs['Metallic'])
    ob.data.materials.append(mat)
    return p_bc, p_orm, float(ao.mean()), float(met.mean())
