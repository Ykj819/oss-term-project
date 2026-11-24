# Boss fog gate material: /Game/Effects/FogGate/M_FogGate (deleted + rebuilt each run), used by AFogGate (FogGate.h).
# Lit translucent (volumetric non-directional), two-sided, on the engine plane (UV 0..1). Two panned samples of
# /Game/Characters/Enemies/Textures/T_FogNoise make drifting milky fog; soft UV edges; depth fade.
# Params: Color, EmissiveBoost (keeps it glowing in the dark), OpacityScale, Fade (AFogGate fades it out when the boss
# dies), Seed (per layer offset), Speed.
# Editor closed:
#   UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script="<abs/forward/slash>/Tools/create_fog_gate_material.py" -unattended -nosplash -stdout
import unreal

DEST = "/Game/Effects/FogGate"
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda m: unreal.log_warning("FOGGATE " + m)

tex = unreal.load_asset("/Game/Characters/Enemies/Textures/T_FogNoise")
path = f"{DEST}/M_FogGate"
if eal.does_asset_exist(path):
    eal.delete_asset(path)
m = tools.create_asset("M_FogGate", DEST, unreal.Material, unreal.MaterialFactoryNew())
m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
m.set_editor_property("two_sided", True)
m.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
C = mel.connect_material_expressions


def op(cls, a, b, x, y, const=None):
    e = E(cls, x, y)
    C(a, "", e, "A")
    if const is None:
        C(b, "", e, "B")
    else:
        e.set_editor_property("const_b", const)
    return e


def sparam(name, v, x, y):
    e = E(unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", name); e.set_editor_property("default_value", v); return e


tc = E(unreal.MaterialExpressionTextureCoordinate, -1800, 0)
seed = sparam("Seed", 0.0, -1800, 150)
speed = sparam("Speed", 1.0, -1800, 300)
time = E(unreal.MaterialExpressionTime, -1800, 420)
t = op(unreal.MaterialExpressionMultiply, time, speed, -1600, 400)


def noise(tile, sx, sy, y):
    uv = op(unreal.MaterialExpressionMultiply, tc, None, -1450, y, const=tile)
    uvs = op(unreal.MaterialExpressionAdd, uv, seed, -1300, y)
    p = E(unreal.MaterialExpressionPanner, -1150, y)
    p.set_editor_property("speed_x", sx); p.set_editor_property("speed_y", sy)
    C(uvs, "", p, "Coordinate"); C(t, "", p, "Time")
    s = E(unreal.MaterialExpressionTextureSample, -950, y)
    s.set_editor_property("texture", tex)
    C(p, "", s, "UVs")
    return s


n1 = noise(1.3, 0.03, 0.06, 0)
n2 = noise(2.7, -0.05, 0.09, 300)
nsum = E(unreal.MaterialExpressionAdd, -700, 150)
C(n1, "R", nsum, "A"); C(n2, "R", nsum, "B")
nsh = op(unreal.MaterialExpressionMultiply, nsum, None, -550, 150, const=0.75)
nmin = op(unreal.MaterialExpressionAdd, nsh, None, -400, 150, const=0.15)

# soft edges: min(u, 1-u, v, 1-v) * 5, saturated
mask_u = E(unreal.MaterialExpressionComponentMask, -1450, 650); mask_u.set_editor_property("r", True); C(tc, "", mask_u, "")
mask_v = E(unreal.MaterialExpressionComponentMask, -1450, 800); mask_v.set_editor_property("g", True); C(tc, "", mask_v, "")


def edge(v, y):
    inv = E(unreal.MaterialExpressionOneMinus, -1300, y + 60); C(v, "", inv, "")
    mn = op(unreal.MaterialExpressionMin, v, inv, -1150, y)
    k = op(unreal.MaterialExpressionMultiply, mn, None, -1000, y, const=5.0)
    s = E(unreal.MaterialExpressionSaturate, -850, y); C(k, "", s, "")
    return s


eu = edge(mask_u, 650)
ev = edge(mask_v, 800)
emask = op(unreal.MaterialExpressionMultiply, eu, ev, -700, 720)

a1 = op(unreal.MaterialExpressionMultiply, nmin, emask, -250, 300)
oscale = sparam("OpacityScale", 0.85, -250, 450)
fade = sparam("Fade", 1.0, -250, 550)
a2 = op(unreal.MaterialExpressionMultiply, a1, oscale, -50, 350)
a3 = op(unreal.MaterialExpressionMultiply, a2, fade, 100, 400)
a4 = E(unreal.MaterialExpressionSaturate, 250, 400); C(a3, "", a4, "")
df = E(unreal.MaterialExpressionDepthFade, 400, 400); df.set_editor_property("fade_distance_default", 60.0)
C(a4, "", df, "Opacity")
mel.connect_material_property(df, "", unreal.MaterialProperty.MP_OPACITY)

col = E(unreal.MaterialExpressionVectorParameter, -250, -250)
col.set_editor_property("parameter_name", "Color"); col.set_editor_property("default_value", unreal.LinearColor(0.85, 0.88, 0.95, 1))
shade = op(unreal.MaterialExpressionMultiply, col, nmin, -50, -150)
mel.connect_material_property(shade, "", unreal.MaterialProperty.MP_BASE_COLOR)
boost = sparam("EmissiveBoost", 0.5, -50, -20)
em = op(unreal.MaterialExpressionMultiply, shade, boost, 150, -100)
mel.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
r = E(unreal.MaterialExpressionConstant, 150, 50); r.set_editor_property("r", 1.0)
mel.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
mel.recompile_material(m)
eal.save_asset(path, only_if_is_dirty=False)
log(f"OK tex={bool(tex)} nexpr={mel.get_num_material_expressions(m)}")
