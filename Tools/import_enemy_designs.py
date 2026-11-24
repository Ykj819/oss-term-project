# Enemy redesign import (2026-11-23). Sources:
#   Export/SKM_PlushBear.fbx, SKM_PlushBunny.fbx   <- Export/Blender/scripts/characters/gen_plush_enemies.py
#   Export/SM_ClubBat.fbx, SM_EnemyShield.fbx, SM_FogTree.fbx, Export/Textures/Enemies/T_{BatWood,FogNoise}.png
#                                                   <- Export/Blender/scripts/props/gen_enemy_props.py
#   Export/MM_Shield_{Hold,Brace,Push}.fbx          <- Export/Blender/scripts/mannequin/build_shield_anims.py
# -> /Game/Characters/Enemies/{Meshes,Materials,Textures} and /Game/Characters/Mannequins/Anims/Shield
# Materials (deleted + rebuilt every run):
#   M_PlushEnemy       BaseColor = VC^2.2 * "Paint Tint" * (1 + Sheen * fresnel)  (EnemyCharacter's bTintBody sets Paint Tint)
#   M_ClubBat          T_BatWood * VC^2.2 * Color
#   M_EnemyShieldIron  VC^2.2 * Color, Metallic = VC.a, Emissive = VC^2.2 * Flash (block flash from C++)
#   M_FogTree          T_RealBark_BC/N (the realistic tree bark) * VC^2.2 * Color
#   M_EnemyFog         lit translucent two-sided fog: Color.rgb, opacity = Color.a * world-space T_FogNoise (two drifting
#                      samples) * soft edges (1 - fresnel) * depth fade (no hard line where it meets the ground / trunk)
#                      * camera depth fade (no wall in the face when the camera is inside)
# Headless (editor closed):
#   UnrealEditor-Cmd.exe <uproject> -ExecutePythonScript="<abs/forward/slash>/Tools/import_enemy_designs.py" -unattended -nullrhi -nosplash -stdout
import os
import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
BASE = "/Game/Characters/Enemies"
MESHD, MATD, TEXD = BASE + "/Meshes", BASE + "/Materials", BASE + "/Textures"
ANIMD = "/Game/Characters/Mannequins/Anims/Shield"
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda m: unreal.log_warning("ENEMYDES " + m)
skeleton = unreal.load_asset("/Game/Characters/Mannequins/Meshes/SK_Mannequin")
manny = unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple")
MP = unreal.MaterialProperty


def E(m, cls, x, y):
    return mel.create_material_expression(m, cls, x, y)


def C(a, out, b, inp):
    mel.connect_material_expressions(a, out, b, inp)


def op(m, cls, a, b, x, y, const=None, aout="", bout=""):
    e = E(m, cls, x, y)
    C(a, aout, e, "A")
    if const is None:
        C(b, bout, e, "B")
    else:
        e.set_editor_property("const_b", const)
    return e


def sparam(m, name, v, x, y):
    e = E(m, unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", name); e.set_editor_property("default_value", v); return e


def vparam(m, name, v, x, y):
    e = E(m, unreal.MaterialExpressionVectorParameter, x, y)
    e.set_editor_property("parameter_name", name); e.set_editor_property("default_value", unreal.LinearColor(*v)); return e


def tparam(m, name, tex, st, x, y):
    e = E(m, unreal.MaterialExpressionTextureSampleParameter2D, x, y)
    e.set_editor_property("parameter_name", name); e.set_editor_property("texture", tex)
    e.set_editor_property("sampler_type", st); return e


def vc_linear(m, x, y):
    """VertexColor.rgb ^ 2.2 (FBX sRGB values arrive unchanged) -> (vertex colour node, linear rgb)"""
    vc = E(m, unreal.MaterialExpressionVertexColor, x, y)
    pw = E(m, unreal.MaterialExpressionPower, x + 220, y)
    C(vc, "", pw, "Base"); pw.set_editor_property("const_exponent", 2.2)
    return vc, pw


def new_material(name, **props):
    path = f"{MATD}/{name}"
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    m = tools.create_asset(name, MATD, unreal.Material, unreal.MaterialFactoryNew())
    for k, v in props.items():
        m.set_editor_property(k, v)
    return m


def finish(m):
    mel.recompile_material(m)
    eal.save_asset(m.get_path_name().split(".")[0], only_if_is_dirty=False)
    log(f"material {m.get_name()} nexpr={mel.get_num_material_expressions(m)}")
    return m


def import_texture(name, srgb, comp):
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", os.path.join(PROJ, "Export", "Textures", "Enemies", name + ".png"))
    task.set_editor_property("destination_path", TEXD); task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True); task.set_editor_property("save", False)
    tools.import_asset_tasks([task])
    t = unreal.load_asset(f"{TEXD}/{name}")
    t.set_editor_property("srgb", srgb); t.set_editor_property("compression_settings", comp)
    eal.save_asset(f"{TEXD}/{name}", only_if_is_dirty=False)
    return t


# ---------------------------------------------------------------- materials
def plush_material():
    m = new_material("M_PlushEnemy", used_with_skeletal_mesh=True)
    vc, lin = vc_linear(m, -1200, 0)
    tint = vparam(m, "Paint Tint", (1, 1, 1, 1), -900, 200)
    base = op(m, unreal.MaterialExpressionMultiply, lin, tint, -700, 0)
    fr = E(m, unreal.MaterialExpressionFresnel, -900, 400); fr.set_editor_property("exponent", 3.0)
    sheen = sparam(m, "Sheen", 0.35, -900, 550)
    fs = op(m, unreal.MaterialExpressionMultiply, fr, sheen, -700, 400)
    one = op(m, unreal.MaterialExpressionAdd, fs, None, -550, 400, const=1.0)
    bc = op(m, unreal.MaterialExpressionMultiply, base, one, -400, 0)
    mel.connect_material_property(bc, "", MP.MP_BASE_COLOR)
    rl = E(m, unreal.MaterialExpressionLinearInterpolate, -400, 250)
    rl.set_editor_property("const_a", 0.92); rl.set_editor_property("const_b", 0.22)
    C(vc, "A", rl, "Alpha")
    mel.connect_material_property(rl, "", MP.MP_ROUGHNESS)
    spec = E(m, unreal.MaterialExpressionConstant, -400, 450); spec.set_editor_property("r", 0.3)
    mel.connect_material_property(spec, "", MP.MP_SPECULAR)
    return finish(m)


def bat_material(wood):
    m = new_material("M_ClubBat")
    vc, lin = vc_linear(m, -1200, 0)
    t = tparam(m, "WoodMap", wood, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, -1200, 250)
    a = op(m, unreal.MaterialExpressionMultiply, t, lin, -800, 100, aout="RGB")
    col = vparam(m, "Color", (1, 1, 1, 1), -800, 300)
    bc = op(m, unreal.MaterialExpressionMultiply, a, col, -550, 100)
    mel.connect_material_property(bc, "", MP.MP_BASE_COLOR)
    r = E(m, unreal.MaterialExpressionConstant, -550, 350); r.set_editor_property("r", 0.55)
    mel.connect_material_property(r, "", MP.MP_ROUGHNESS)
    return finish(m)


def shield_material():
    m = new_material("M_EnemyShieldIron")
    vc, lin = vc_linear(m, -1200, 0)
    col = vparam(m, "Color", (1, 1, 1, 1), -900, 200)
    bc = op(m, unreal.MaterialExpressionMultiply, lin, col, -650, 0)
    mel.connect_material_property(bc, "", MP.MP_BASE_COLOR)
    met = op(m, unreal.MaterialExpressionMultiply, vc, None, -650, 300, const=0.9, aout="A")
    mel.connect_material_property(met, "", MP.MP_METALLIC)
    rl = E(m, unreal.MaterialExpressionLinearInterpolate, -650, 450)
    rl.set_editor_property("const_a", 0.8); rl.set_editor_property("const_b", 0.4)
    C(vc, "A", rl, "Alpha")
    mel.connect_material_property(rl, "", MP.MP_ROUGHNESS)
    flash = sparam(m, "Flash", 0.0, -900, 650)
    em = op(m, unreal.MaterialExpressionMultiply, bc, flash, -400, 650)
    mel.connect_material_property(em, "", MP.MP_EMISSIVE_COLOR)
    return finish(m)


def fog_tree_material():
    bcx = unreal.load_asset("/Game/Environment/Trees/Textures/T_RealBark_BC")
    nx = unreal.load_asset("/Game/Environment/Trees/Textures/T_RealBark_N")
    m = new_material("M_FogTree")
    vc, lin = vc_linear(m, -1200, 0)
    t = tparam(m, "BarkMap", bcx, unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, -1200, 250)
    a = op(m, unreal.MaterialExpressionMultiply, t, lin, -800, 100, aout="RGB")
    col = vparam(m, "Color", (1, 1, 1, 1), -800, 300)
    bc = op(m, unreal.MaterialExpressionMultiply, a, col, -550, 100)
    mel.connect_material_property(bc, "", MP.MP_BASE_COLOR)
    n = tparam(m, "NormalMap", nx, unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, -800, 500)
    mel.connect_material_property(n, "RGB", MP.MP_NORMAL)
    r = E(m, unreal.MaterialExpressionConstant, -550, 400); r.set_editor_property("r", 0.9)
    mel.connect_material_property(r, "", MP.MP_ROUGHNESS)
    return finish(m)


def fog_material(noise):
    m = new_material("M_EnemyFog", blend_mode=unreal.BlendMode.BLEND_TRANSLUCENT, two_sided=True,
                     translucency_lighting_mode=unreal.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
    col = vparam(m, "Color", (0.92, 0.93, 0.95, 0.35), -400, -200)
    mel.connect_material_property(col, "RGB", MP.MP_BASE_COLOR)
    r = E(m, unreal.MaterialExpressionConstant, -400, -50); r.set_editor_property("r", 1.0)
    mel.connect_material_property(r, "", MP.MP_ROUGHNESS)
    wp = E(m, unreal.MaterialExpressionWorldPosition, -2000, 200)
    t = E(m, unreal.MaterialExpressionTime, -2000, 450)
    scale = sparam(m, "NoiseScale", 420.0, -2000, 600)

    def sample(mask_g, mask_b, div, speed, y, name):
        mk = E(m, unreal.MaterialExpressionComponentMask, -1750, y)
        mk.set_editor_property("r", True); mk.set_editor_property("g", mask_g); mk.set_editor_property("b", mask_b)
        C(wp, "", mk, "")
        d = op(m, unreal.MaterialExpressionDivide, mk, scale, -1550, y)
        d2 = op(m, unreal.MaterialExpressionMultiply, d, None, -1400, y, const=div)
        sp = E(m, unreal.MaterialExpressionConstant2Vector, -1550, y + 120)
        sp.set_editor_property("r", speed[0]); sp.set_editor_property("g", speed[1])
        ts = op(m, unreal.MaterialExpressionMultiply, t, sp, -1400, y + 120)
        uv = op(m, unreal.MaterialExpressionAdd, d2, ts, -1250, y)
        s = tparam(m, name, noise, unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE, -1100, y)
        C(uv, "", s, "UVs")
        return s
    n1 = sample(True, False, 1.0, (0.018, 0.009), 150, "NoiseMap")
    n2 = sample(False, True, 1.7, (-0.012, 0.024), 450, "NoiseMap2")
    nn = op(m, unreal.MaterialExpressionMultiply, n1, n2, -850, 300, aout="R", bout="R")
    contrast = sparam(m, "NoiseContrast", 2.6, -850, 450)
    nc = op(m, unreal.MaterialExpressionMultiply, nn, contrast, -700, 300)
    sat = E(m, unreal.MaterialExpressionSaturate, -560, 300); C(nc, "", sat, "")
    nl = E(m, unreal.MaterialExpressionLinearInterpolate, -420, 300)
    nl.set_editor_property("const_a", 0.25); nl.set_editor_property("const_b", 1.0); C(sat, "", nl, "Alpha")
    fr = E(m, unreal.MaterialExpressionFresnel, -700, 600); fr.set_editor_property("exponent", 1.2)
    edge = E(m, unreal.MaterialExpressionOneMinus, -560, 600); C(fr, "", edge, "")
    edge2 = op(m, unreal.MaterialExpressionMultiply, edge, edge, -420, 600)
    a1 = op(m, unreal.MaterialExpressionMultiply, nl, edge2, -280, 400)
    a2 = op(m, unreal.MaterialExpressionMultiply, a1, col, -150, 400, bout="A")
    df = E(m, unreal.MaterialExpressionDepthFade, 0, 400)
    df.set_editor_property("fade_distance_default", 160.0)
    C(a2, "", df, "Opacity")
    pd = E(m, unreal.MaterialExpressionPixelDepth, -420, 800)        # camera fade: saturate((depth - 30) / 250)
    pds = op(m, unreal.MaterialExpressionSubtract, pd, None, -280, 800, const=30.0)
    pdd = op(m, unreal.MaterialExpressionDivide, pds, None, -150, 800, const=250.0)
    cdf = E(m, unreal.MaterialExpressionSaturate, 0, 650); C(pdd, "", cdf, "")
    op_out = op(m, unreal.MaterialExpressionMultiply, df, cdf, 200, 450)
    mel.connect_material_property(op_out, "", MP.MP_OPACITY)
    return finish(m)


# ---------------------------------------------------------------- meshes
def clean_leftovers(folder, keep):
    for p in eal.list_assets(folder, recursive=False):
        a = unreal.load_asset(p)
        if isinstance(a, unreal.Material) and a.get_name() not in keep:
            eal.delete_asset(p.split(".")[0]); log(f"deleted leftover {p}")


def import_skeletal(name, mat):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", True); ui.set_editor_property("import_as_skeletal", True)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    ui.set_editor_property("skeleton", skeleton)
    ui.set_editor_property("import_materials", False); ui.set_editor_property("import_textures", False)
    ui.set_editor_property("import_animations", False); ui.set_editor_property("create_physics_asset", False)
    sk = ui.get_editor_property("skeletal_mesh_import_data")
    sk.set_editor_property("import_morph_targets", False)
    sk.set_editor_property("vertex_color_import_option", unreal.VertexColorImportOption.REPLACE)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", os.path.join(PROJ, "Export", name + ".fbx"))
    task.set_editor_property("destination_path", MESHD)
    task.set_editor_property("automated", True); task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False); task.set_editor_property("options", ui)
    tools.import_asset_tasks([task])
    mesh = unreal.load_asset(f"{MESHD}/{name}")
    if not mesh:
        log(f"FAILED {name}"); return
    mats = []
    for s in mesh.get_editor_property("materials"):       # copies: edit and set the whole list back
        s.set_editor_property("material_interface", mat); mats.append(s)
    mesh.set_editor_property("materials", mats)
    pa = manny.get_editor_property("physics_asset")
    if pa:
        mesh.set_editor_property("physics_asset", pa)
    eal.save_asset(f"{MESHD}/{name}", only_if_is_dirty=False)
    log(f"OK {name} skeleton={mesh.get_editor_property('skeleton').get_name()} slots={len(mats)} "
        f"root children={mesh.get_bone_children('root')} physics={pa.get_name() if pa else None}")


def import_static(name, mat):
    path = f"{MESHD}/{name}"
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", os.path.join(PROJ, "Export", name + ".fbx"))
    task.set_editor_property("destination_path", MESHD); task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True); task.set_editor_property("save", False)
    tools.import_asset_tasks([task])
    mesh = unreal.load_asset(path)
    if not mesh:
        log(f"FAILED {name}"); return
    for i in range(len(mesh.get_editor_property("static_materials"))):
        mesh.set_material(i, mat)
    ns = mesh.get_editor_property("nanite_settings"); ns.set_editor_property("enabled", False)
    mesh.set_editor_property("nanite_settings", ns)
    bs = mesh.get_editor_property("body_setup")
    if bs:
        bs.set_editor_property("agg_geom", unreal.KAggregateGeom())
    eal.save_asset(path, only_if_is_dirty=False)
    b = mesh.get_bounding_box()
    log(f"OK {name} tris={unreal.EditorStaticMeshLibrary.get_number_verts(mesh, 0)}v "
        f"bounds min={b.min} max={b.max}")


def import_anim(name):
    ui = unreal.FbxImportUI()
    ui.set_editor_property("import_mesh", False); ui.set_editor_property("import_animations", True)
    ui.set_editor_property("import_as_skeletal", True); ui.set_editor_property("skeleton", skeleton)
    ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
    ui.set_editor_property("import_materials", False); ui.set_editor_property("import_textures", False)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", os.path.join(PROJ, "Export", name + ".fbx"))
    task.set_editor_property("destination_path", ANIMD); task.set_editor_property("destination_name", name)
    task.set_editor_property("automated", True); task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", False); task.set_editor_property("options", ui)
    tools.import_asset_tasks([task])
    anim = unreal.load_asset(f"{ANIMD}/{name}")
    if not anim:
        log(f"FAILED {name}"); return
    anim.set_editor_property("enable_root_motion", False)
    eal.save_asset(f"{ANIMD}/{name}", only_if_is_dirty=False)
    log(f"OK {name} frames={unreal.AnimationLibrary.get_num_frames(anim)} length={anim.get_play_length():.2f}s")


wood = import_texture("T_BatWood", True, unreal.TextureCompressionSettings.TC_DEFAULT)
noise = import_texture("T_FogNoise", False, unreal.TextureCompressionSettings.TC_GRAYSCALE)
plush = plush_material()
bat_m = bat_material(wood)
shield_m = shield_material()
tree_m = fog_tree_material()
fog_m = fog_material(noise)
for n in ("SKM_PlushBear", "SKM_PlushBunny"):
    import_skeletal(n, plush)
import_static("SM_ClubBat", bat_m)
import_static("SM_EnemyShield", shield_m)
import_static("SM_FogTree", tree_m)
clean_leftovers(MESHD, ())
for n in ("MM_Shield_Hold", "MM_Shield_Brace", "MM_Shield_Push"):
    import_anim(n)
log("done")
if "executepythonscript" in unreal.SystemLibrary.get_command_line().lower():
    unreal.SystemLibrary.quit_editor()
