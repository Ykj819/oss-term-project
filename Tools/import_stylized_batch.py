# Batch import of the stylized environment set (made in Export/Blender/StylizedTree.blend and StylizedProps.blend):
#   Trees   : SM_StylizedBareTree[,1,2,3], SM_StylizedAutumnTree[,1,2,3]        -> /Game/Environment/Trees
#   Rocks   : SM_StylizedStone1..3, SM_StylizedRock1..3                          -> /Game/Environment/Rocks
#   Foliage : SM_StylizedGrass, SM_Flower_*  (no collision)                      -> /Game/Environment/Foliage
#   Textures: Export/Textures/Stylized/T_Stylized_<Name>_{BC,N,ARH}.png          -> /Game/Environment/Textures/Stylized
#   Materials (/Game/Environment/Materials):
#     M_Stylized_Prop, M_Stylized_Foliage : vertex-colour materials (like M_StylizedTree_*; VertexColor^2.2 * Tint)
#     M_Stylized_Surface + MI_Stylized_<Name> : tiling texture material + one instance per texture set
#     M_Stylized_Water : translucent, two panning normal maps
# Run with the editor closed, then run Tools/foliage_no_collision.py (removing the auto-generated collision of the
# grass/flowers does not work from here):
#   UnrealEditor-Cmd.exe <project>.uproject -run=pythonscript -script="<this file>" -unattended -nosplash -stdout
import os
import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
EXPORT = os.path.join(PROJ, "Export")
MATS = "/Game/Environment/Materials"
TEXD = "/Game/Environment/Textures/Stylized"

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda msg: unreal.log_warning("BATCH " + msg)


def safe(fn, default=None):
    try:
        return fn()
    except Exception as e:
        log(f"  (warn) {e.__class__.__name__}: {e}")
        return default


# ------------------------------------------------------------------ vertex-colour materials
def vc_material(path, two_sided, roughness):
    if eal.does_asset_exist(path):
        return unreal.load_asset(path)
    folder, name = path.rsplit("/", 1)
    mat = tools.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("two_sided", two_sided)
    mat.set_editor_property("used_with_instanced_static_meshes", True)
    vc = mel.create_material_expression(mat, unreal.MaterialExpressionVertexColor, -700, 0)
    gamma = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -700, 200)
    gamma.set_editor_property("parameter_name", "VertexColorGamma"); gamma.set_editor_property("default_value", 2.2)
    pw = mel.create_material_expression(mat, unreal.MaterialExpressionPower, -450, 0)
    mel.connect_material_expressions(vc, "", pw, "Base"); mel.connect_material_expressions(gamma, "", pw, "Exp")
    tint = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -450, 200)
    tint.set_editor_property("parameter_name", "Tint"); tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    mul = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -200, 0)
    mel.connect_material_expressions(pw, "", mul, "A"); mel.connect_material_expressions(tint, "", mul, "B")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    r = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -200, 250)
    r.set_editor_property("parameter_name", "Roughness"); r.set_editor_property("default_value", roughness)
    mel.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(mat); eal.save_asset(path, only_if_is_dirty=False)
    return mat


tree_bark = vc_material("/Game/Environment/Trees/M_StylizedTree_Bark", False, 0.9)
tree_leaves = vc_material("/Game/Environment/Trees/M_StylizedTree_Leaves", True, 0.7)
prop_mat = vc_material(f"{MATS}/M_Stylized_Prop", False, 0.85)
foliage_mat = vc_material(f"{MATS}/M_Stylized_Foliage", True, 0.7)
SLOT_MAP = [("Tree_Bark", tree_bark), ("Tree_Leaves", tree_leaves), ("Stylized_Prop", prop_mat), ("Stylized_Foliage", foliage_mat)]
LEFTOVER = ["M_Tree_Bark", "M_Tree_Leaves", "M_Stylized_Prop", "M_Stylized_Foliage"]

# ------------------------------------------------------------------ meshes
MESHES = (
    [("/Game/Environment/Trees", n, True) for n in
     ["SM_StylizedBareTree", "SM_StylizedBareTree1", "SM_StylizedBareTree2", "SM_StylizedBareTree3",
      "SM_StylizedAutumnTree", "SM_StylizedAutumnTree1", "SM_StylizedAutumnTree2", "SM_StylizedAutumnTree3"]] +
    [("/Game/Environment/Rocks", n, True) for n in
     ["SM_StylizedStone1", "SM_StylizedStone2", "SM_StylizedStone3", "SM_StylizedRock1", "SM_StylizedRock2", "SM_StylizedRock3"]] +
    [("/Game/Environment/Foliage", "SM_StylizedGrass", False)] +
    [("/Game/Environment/Foliage/Flowers", n, False) for n in
     ["SM_Flower_Daisy", "SM_Flower_Tulip", "SM_Flower_Lavender", "SM_Flower_Marigold", "SM_Flower_BabysBreath",
      "SM_Flower_LilyOfTheValley", "SM_Flower_Fireweed"]]
)

ok_meshes = []
for folder, name, collide in MESHES:
    fbx = os.path.join(EXPORT, name + ".fbx")
    if not os.path.exists(fbx):
        log(f"MISSING {fbx}"); continue
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", fbx); task.set_editor_property("destination_path", folder)
    task.set_editor_property("automated", True); task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    tools.import_asset_tasks([task])
    path = f"{folder}/{name}"
    mesh = unreal.load_asset(path)
    if not mesh:
        log(f"FAILED {name}"); continue
    slots = []
    for i, sm in enumerate(mesh.get_editor_property("static_materials")):
        slot = str(sm.get_editor_property("material_slot_name"))
        mat = next((m for key, m in SLOT_MAP if key in slot), foliage_mat if not collide else prop_mat)
        mesh.set_material(i, mat); slots.append(f"{slot}={mat.get_name()}")
    if not collide:  # grass / flowers: walk through them
        safe(lambda: unreal.EditorStaticMeshLibrary.remove_collisions(mesh))
        safe(lambda: mesh.get_editor_property("body_setup").set_editor_property(
            "collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX))
    eal.save_asset(path, only_if_is_dirty=False)
    convex = safe(lambda: len(mesh.get_editor_property("body_setup").get_editor_property("agg_geom").get_editor_property("convex_elems")), -1)
    b = mesh.get_bounding_box()
    log(f"MESH_OK {name} convex={convex} slots={slots} size_cm=({b.max.x - b.min.x:.0f},{b.max.y - b.min.y:.0f},{b.max.z - b.min.z:.0f})")
    ok_meshes.append(name)
    for lo in LEFTOVER:
        p = f"{folder}/{lo}"
        if eal.does_asset_exist(p) and p != prop_mat.get_path_name().split(".")[0] and p != foliage_mat.get_path_name().split(".")[0]:
            eal.delete_asset(p)

# ------------------------------------------------------------------ textures
SETS = ["Grass", "Stone", "Rock", "FallenLeaves", "Snow", "Sand", "Soil", "Water"]
TEX_SRC = os.path.join(EXPORT, "Textures", "Stylized")
tex = {}
for s in SETS:
    for suffix, srgb, comp in (("BC", True, unreal.TextureCompressionSettings.TC_DEFAULT),
                               ("N", False, unreal.TextureCompressionSettings.TC_NORMALMAP),
                               ("ARH", False, unreal.TextureCompressionSettings.TC_MASKS)):
        name = f"T_Stylized_{s}_{suffix}"
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", os.path.join(TEX_SRC, name + ".png"))
        task.set_editor_property("destination_path", TEXD); task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", True); task.set_editor_property("save", False)
        tools.import_asset_tasks([task])
        t = unreal.load_asset(f"{TEXD}/{name}")
        if not t:
            log(f"TEX FAILED {name}"); continue
        t.set_editor_property("srgb", srgb); t.set_editor_property("compression_settings", comp)
        if suffix == "N":
            t.set_editor_property("flip_green_channel", False)
        eal.save_asset(f"{TEXD}/{name}", only_if_is_dirty=False)
        tex[name] = t
log(f"TEX_OK {len(tex)} textures")


# ------------------------------------------------------------------ surface master material + instances
def rebuild(path, create):
    if eal.does_asset_exist(path):
        m = unreal.load_asset(path); mel.delete_all_material_expressions(m); return m
    folder, name = path.rsplit("/", 1)
    return tools.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())


def E(mat, cls, x, y):
    return mel.create_material_expression(mat, cls, x, y)


def scalar(mat, name, v, x, y):
    e = E(mat, unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", name); e.set_editor_property("default_value", v); return e


def tex_param(mat, name, t, sampler, uv, x, y):
    e = E(mat, unreal.MaterialExpressionTextureSampleParameter2D, x, y)
    e.set_editor_property("parameter_name", name); e.set_editor_property("texture", t)
    e.set_editor_property("sampler_type", sampler); mel.connect_material_expressions(uv, "", e, "UVs"); return e


surf = rebuild(f"{MATS}/M_Stylized_Surface", True)
surf.set_editor_property("used_with_instanced_static_meshes", True)
tc = E(surf, unreal.MaterialExpressionTextureCoordinate, -1600, 0)
tiling = scalar(surf, "Tiling", 1.0, -1600, 120)
uv = E(surf, unreal.MaterialExpressionMultiply, -1400, 0)
mel.connect_material_expressions(tc, "", uv, "A"); mel.connect_material_expressions(tiling, "", uv, "B")
bc = tex_param(surf, "BaseColorMap", tex.get("T_Stylized_Grass_BC"), unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, uv, -1100, -300)
nm = tex_param(surf, "NormalMap", tex.get("T_Stylized_Grass_N"), unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, uv, -1100, 50)
arh = tex_param(surf, "ARHMap", tex.get("T_Stylized_Grass_ARH"), unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, uv, -1100, 400)
tint = E(surf, unreal.MaterialExpressionVectorParameter, -800, -450)
tint.set_editor_property("parameter_name", "Tint"); tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
bm = E(surf, unreal.MaterialExpressionMultiply, -550, -300)
mel.connect_material_expressions(bc, "RGB", bm, "A"); mel.connect_material_expressions(tint, "", bm, "B")
mel.connect_material_property(bm, "", unreal.MaterialProperty.MP_BASE_COLOR)
flat = E(surf, unreal.MaterialExpressionConstant3Vector, -800, 150)
flat.set_editor_property("constant", unreal.LinearColor(0, 0, 1, 1))
ns = scalar(surf, "NormalStrength", 1.0, -800, 250)
nl = E(surf, unreal.MaterialExpressionLinearInterpolate, -550, 100)
mel.connect_material_expressions(flat, "", nl, "A"); mel.connect_material_expressions(nm, "RGB", nl, "B")
mel.connect_material_expressions(ns, "", nl, "Alpha")
mel.connect_material_property(nl, "", unreal.MaterialProperty.MP_NORMAL)
mel.connect_material_property(arh, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
rs = scalar(surf, "RoughnessScale", 1.0, -800, 550)
rm = E(surf, unreal.MaterialExpressionMultiply, -550, 450)
mel.connect_material_expressions(arh, "G", rm, "A"); mel.connect_material_expressions(rs, "", rm, "B")
mel.connect_material_property(rm, "", unreal.MaterialProperty.MP_ROUGHNESS)
mel.recompile_material(surf); eal.save_asset(f"{MATS}/M_Stylized_Surface", only_if_is_dirty=False)

for s in SETS:
    if s == "Water":
        continue
    path = f"{MATS}/MI_Stylized_{s}"
    mi = unreal.load_asset(path) if eal.does_asset_exist(path) else tools.create_asset(
        f"MI_Stylized_{s}", MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mel.set_material_instance_parent(mi, surf)
    for p, suf in (("BaseColorMap", "BC"), ("NormalMap", "N"), ("ARHMap", "ARH")):
        t = tex.get(f"T_Stylized_{s}_{suf}")
        if t:
            mel.set_material_instance_texture_parameter_value(mi, p, t)
    eal.save_asset(path, only_if_is_dirty=False)
log("SURFACE_OK M_Stylized_Surface + " + ", ".join(f"MI_Stylized_{s}" for s in SETS if s != "Water"))

# ------------------------------------------------------------------ water
wat = rebuild(f"{MATS}/M_Stylized_Water", True)
wat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
safe(lambda: wat.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_SURFACE))
wat.set_editor_property("two_sided", False)
tcw = E(wat, unreal.MaterialExpressionTextureCoordinate, -1700, 0)
tw = scalar(wat, "Tiling", 1.0, -1700, 120)
uvw = E(wat, unreal.MaterialExpressionMultiply, -1500, 0)
mel.connect_material_expressions(tcw, "", uvw, "A"); mel.connect_material_expressions(tw, "", uvw, "B")


def panner(sx, sy, x, y):
    p = E(wat, unreal.MaterialExpressionPanner, x, y)
    p.set_editor_property("speed_x", sx); p.set_editor_property("speed_y", sy)
    mel.connect_material_expressions(uvw, "", p, "Coordinate"); return p


p1 = panner(0.015, 0.008, -1300, -100); p2 = panner(-0.01, 0.013, -1300, 200)
wbc = E(wat, unreal.MaterialExpressionTextureSample, -1050, -400)
wbc.set_editor_property("texture", tex.get("T_Stylized_Water_BC")); mel.connect_material_expressions(p1, "", wbc, "UVs")
n1 = E(wat, unreal.MaterialExpressionTextureSample, -1050, -50)
n1.set_editor_property("texture", tex.get("T_Stylized_Water_N"))
n1.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL); mel.connect_material_expressions(p1, "", n1, "UVs")
n2 = E(wat, unreal.MaterialExpressionTextureSample, -1050, 250)
n2.set_editor_property("texture", tex.get("T_Stylized_Water_N"))
n2.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL); mel.connect_material_expressions(p2, "", n2, "UVs")
nadd = E(wat, unreal.MaterialExpressionAdd, -800, 100)
mel.connect_material_expressions(n1, "RGB", nadd, "A"); mel.connect_material_expressions(n2, "RGB", nadd, "B")
nn = E(wat, unreal.MaterialExpressionNormalize, -600, 100); mel.connect_material_expressions(nadd, "", nn, "")
mel.connect_material_property(nn, "", unreal.MaterialProperty.MP_NORMAL)
wtint = E(wat, unreal.MaterialExpressionVectorParameter, -800, -550)
wtint.set_editor_property("parameter_name", "Tint"); wtint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
wb = E(wat, unreal.MaterialExpressionMultiply, -550, -400)
mel.connect_material_expressions(wbc, "RGB", wb, "A"); mel.connect_material_expressions(wtint, "", wb, "B")
mel.connect_material_property(wb, "", unreal.MaterialProperty.MP_BASE_COLOR)
mel.connect_material_property(scalar(wat, "Roughness", 0.06, -550, 350), "", unreal.MaterialProperty.MP_ROUGHNESS)
mel.connect_material_property(scalar(wat, "Opacity", 0.78, -550, 450), "", unreal.MaterialProperty.MP_OPACITY)
mel.connect_material_property(scalar(wat, "Specular", 0.6, -550, 550), "", unreal.MaterialProperty.MP_SPECULAR)
mel.recompile_material(wat); eal.save_asset(f"{MATS}/M_Stylized_Water", only_if_is_dirty=False)
log("WATER_OK M_Stylized_Water")
log(f"DONE meshes={len(ok_meshes)}/{len(MESHES)} textures={len(tex)}/24")
