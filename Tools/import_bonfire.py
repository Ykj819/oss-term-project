# Import the bonfire (Export/SM_Bonfire.fbx + SM_BonfireFlame.fbx + Export/Textures/Bonfire/T_FlameNoise.png, made by
# Export/Blender/scripts/props/gen_bonfire.py) into /Game/Environment/Props and (re)build the flame material
# /Game/Environment/Materials/M_BonfireFlame:
#   SM_Bonfire       stones/logs/ash, vertex colours -> M_Stylized_Prop, UCX collision, Nanite on (like the other props)
#   SM_BonfireFlame  flame tongues (cylindrical UVs: U around, V up) -> M_BonfireFlame, Nanite OFF (translucent)
# M_BonfireFlame (unlit, additive, two-sided):
#   noise   = 2 * T_FlameNoise(UV panned up, slow) * T_FlameNoise(UV x(2,1.6) panned up, fast)
#   mask    = saturate(noise * 1.6 - vertexA * Erode + 0.35)      (vertex A = 0 base .. 1 tip -> tips break into licks)
#   emissive= vertexRGB^2.2 * Glow * flicker * (1 - fresnel) * mask * (0.5 + noise)
#   WPO     = sideways sine sway * vertexA * Sway
#   params: Glow (12), Erode (0.9), Sway (5 cm), FlickerSpeed (1.7), NoiseMap
# The material is DELETED and recreated on every run (rebuilding an existing graph with delete_all_material_expressions
# crashes headless runs). Used by ABonfire (Bonfire.cpp, sets "Glow").
# Editor closed:
#   UnrealEditor-Cmd.exe <project>.uproject -run=pythonscript -script="<abs/forward/slash/path>/Tools/import_bonfire.py" -unattended -nosplash -stdout
import os
import unreal

DEST = "/Game/Environment/Props"
MATD = "/Game/Environment/Materials"
TEXD = "/Game/Environment/Textures"
PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda m: unreal.log_warning("BONFIRE " + m)


def E(m, cls, x, y):
    return mel.create_material_expression(m, cls, x, y)


def C(a, out, b, inp):
    mel.connect_material_expressions(a, out, b, inp)


def mul(m, a, b, x, y, const=None):
    e = E(m, unreal.MaterialExpressionMultiply, x, y)
    C(a, "", e, "A")
    if const is None: C(b, "", e, "B")
    else: e.set_editor_property("const_b", const)
    return e


def add(m, a, b, x, y, const=None):
    e = E(m, unreal.MaterialExpressionAdd, x, y)
    C(a, "", e, "A")
    if const is None: C(b, "", e, "B")
    else: e.set_editor_property("const_b", const)
    return e


def sparam(m, name, v, x, y):
    e = E(m, unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", name); e.set_editor_property("default_value", v); return e


def import_texture():
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", os.path.join(PROJ, "Export", "Textures", "Bonfire", "T_FlameNoise.png"))
    task.set_editor_property("destination_path", TEXD); task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True); task.set_editor_property("save", False)
    tools.import_asset_tasks([task])
    t = unreal.load_asset(f"{TEXD}/T_FlameNoise")
    t.set_editor_property("srgb", False)
    t.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_GRAYSCALE)
    eal.save_asset(f"{TEXD}/T_FlameNoise", only_if_is_dirty=False)
    return t


def flame_material(tex):
    path = f"{MATD}/M_BonfireFlame"
    if eal.does_asset_exist(path):
        eal.delete_asset(path)
    m = tools.create_asset("M_BonfireFlame", MATD, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
    m.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    m.set_editor_property("two_sided", True)

    vc = E(m, unreal.MaterialExpressionVertexColor, -1800, 0)
    t = E(m, unreal.MaterialExpressionTime, -1800, 300)

    # ---- scrolling noise
    def noise_sample(tile, speed, y, name):
        tc = E(m, unreal.MaterialExpressionTextureCoordinate, -1800, y)
        tc.set_editor_property("u_tiling", tile[0]); tc.set_editor_property("v_tiling", tile[1])
        pn = E(m, unreal.MaterialExpressionPanner, -1600, y)
        pn.set_editor_property("speed_x", speed[0]); pn.set_editor_property("speed_y", speed[1])
        C(tc, "", pn, "Coordinate")
        s = E(m, unreal.MaterialExpressionTextureSampleParameter2D, -1400, y)
        s.set_editor_property("parameter_name", name); s.set_editor_property("texture", tex)
        s.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
        C(pn, "", s, "UVs")
        return s
    # V goes up the flame -> negative speed_y moves the pattern upward
    n1 = noise_sample((1.0, 1.0), (0.03, -0.45), 600, "NoiseMap")
    n2 = noise_sample((2.0, 1.6), (-0.05, -0.85), 900, "NoiseMap")
    nm = E(m, unreal.MaterialExpressionMultiply, -1150, 700)
    C(n1, "R", nm, "A"); C(n2, "R", nm, "B")
    noise = mul(m, nm, None, -1000, 700, const=2.0)

    # ---- erosion towards the tips
    # vertex alpha: take the VertexColor node's "A" output (a ComponentMask on its default output only sees RGB and fails
    # to compile -> UE silently draws the grid default material)
    va = E(m, unreal.MaterialExpressionMultiply, -1400, 1200)
    C(vc, "A", va, "A"); va.set_editor_property("const_b", 1.0)
    erode = sparam(m, "Erode", 0.9, -1400, 1300)
    ae = mul(m, va, erode, -1150, 1200)
    n16 = mul(m, noise, None, -850, 800, const=1.6)
    sub = E(m, unreal.MaterialExpressionSubtract, -700, 850)
    C(n16, "", sub, "A"); C(ae, "", sub, "B")
    a35 = add(m, sub, None, -550, 850, const=0.35)
    mask = E(m, unreal.MaterialExpressionSaturate, -420, 850)
    C(a35, "", mask, "")
    bright = add(m, noise, None, -700, 650, const=0.5)
    detail = mul(m, mask, bright, -280, 700)

    # ---- colour, glow, flicker, soft edges
    pw = E(m, unreal.MaterialExpressionPower, -1550, 0)
    pw.set_editor_property("const_exponent", 2.2)
    C(vc, "", pw, "Base")
    glow = sparam(m, "Glow", 12.0, -1550, 150)
    fs = sparam(m, "FlickerSpeed", 1.7, -1800, 400)
    tm = mul(m, t, fs, -1550, 320)
    sn = E(m, unreal.MaterialExpressionSine, -1400, 320); C(tm, "", sn, "")
    fl = mul(m, sn, None, -1250, 320, const=0.15)
    fa = add(m, fl, None, -1100, 320, const=0.85)
    fr = E(m, unreal.MaterialExpressionFresnel, -1100, 450); fr.set_editor_property("exponent", 1.5)
    om = E(m, unreal.MaterialExpressionOneMinus, -950, 450); C(fr, "", om, "")
    e1 = mul(m, pw, glow, -1250, 50)
    e2 = mul(m, e1, fa, -950, 100)
    e3 = mul(m, e2, om, -700, 150)
    e4 = mul(m, e3, detail, -150, 200)
    mel.connect_material_property(e4, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    # ---- sway (cm): A * Sway * (sin(t*1.1 + z*0.02), sin(t*0.9 + z*0.025 + 0.3), 0)
    wp = E(m, unreal.MaterialExpressionWorldPosition, -1800, 1500)
    mz = E(m, unreal.MaterialExpressionComponentMask, -1600, 1500)
    mz.set_editor_property("r", False); mz.set_editor_property("g", False); mz.set_editor_property("b", True)
    C(wp, "", mz, "")
    parts = []
    for i, (spd, k, ph) in enumerate(((1.1, 0.02, 0.0), (0.9, 0.025, 0.3))):
        y = 1450 + i * 200
        a = mul(m, t, None, -1400, y, const=spd)
        b = mul(m, mz, None, -1400, y + 80, const=k)
        s = add(m, a, b, -1250, y)
        s2 = add(m, s, None, -1100, y, const=ph)
        sn2 = E(m, unreal.MaterialExpressionSine, -950, y); C(s2, "", sn2, "")
        parts.append(sn2)
    ap = E(m, unreal.MaterialExpressionAppendVector, -800, 1500)
    C(parts[0], "", ap, "A"); C(parts[1], "", ap, "B")
    zero = E(m, unreal.MaterialExpressionConstant, -800, 1650); zero.set_editor_property("r", 0.0)
    ap0 = E(m, unreal.MaterialExpressionAppendVector, -650, 1550)
    C(ap, "", ap0, "A"); C(zero, "", ap0, "B")
    sw = sparam(m, "Sway", 5.0, -800, 1750)
    w1 = mul(m, sw, va, -550, 1700)
    w2 = mul(m, ap0, w1, -400, 1600)
    mel.connect_material_property(w2, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)

    mel.recompile_material(m)
    eal.save_asset(path, only_if_is_dirty=False)
    return m


def import_mesh(name, mat, nanite):
    if eal.does_asset_exist(f"{DEST}/{name}"):
        eal.delete_asset(f"{DEST}/{name}")
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", os.path.join(PROJ, "Export", name + ".fbx"))
    task.set_editor_property("destination_path", DEST); task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True); task.set_editor_property("save", False)
    tools.import_asset_tasks([task])
    path = f"{DEST}/{name}"
    mesh = unreal.load_asset(path)
    if not mesh:
        log(f"FAILED {name}"); return None
    for i in range(len(mesh.get_editor_property("static_materials"))):
        mesh.set_material(i, mat)
    ns = mesh.get_editor_property("nanite_settings"); ns.set_editor_property("enabled", nanite)
    mesh.set_editor_property("nanite_settings", ns)
    eal.save_asset(path, only_if_is_dirty=False)
    for leftover in ("M_Stylized_Prop", "M_BonfireFlame"):          # materials Interchange made next to the mesh
        if eal.does_asset_exist(f"{DEST}/{leftover}"):
            eal.delete_asset(f"{DEST}/{leftover}")
    ag = mesh.get_editor_property("body_setup").get_editor_property("agg_geom")
    b = mesh.get_bounding_box()
    # (EditorStaticMeshLibrary.has_vertex_colors reads False in the commandlet even for working vertex-colour props)
    log(f"OK {name} convex={len(ag.get_editor_property('convex_elems'))} "
        f"size_cm=({b.max.x - b.min.x:.0f},{b.max.y - b.min.y:.0f},{b.max.z - b.min.z:.0f}) min_z={b.min.z:.0f}")
    return mesh


# flame mesh first out of the way, so the material can be deleted and rebuilt
if eal.does_asset_exist(f"{DEST}/SM_BonfireFlame"):
    eal.delete_asset(f"{DEST}/SM_BonfireFlame")
prop_mat = unreal.load_asset(f"{MATD}/M_Stylized_Prop")
flame_mat = flame_material(import_texture())
import_mesh("SM_Bonfire", prop_mat, True)
flame = import_mesh("SM_BonfireFlame", flame_mat, False)
if flame:
    flame.get_editor_property("body_setup").set_editor_property("agg_geom", unreal.KAggregateGeom())   # no collision
    eal.save_asset(f"{DEST}/SM_BonfireFlame", only_if_is_dirty=False)
