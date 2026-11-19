# One-sided fog wall material M_FogWall (+ instance MI_FogWall) -> /Game/Environment/Materials
# Put it on a Plane / Cube face: Two Sided is OFF, so the fog is only visible from the front side of the face
# (from behind, the face is culled and you see straight through).
# Look: translucent, default lit (no emissive -> unaffected by the project's physical auto exposure), two soft noise
# layers panning upward/sideways, soft edges, DepthFade so it doesn't cut hard lines into the ground.
# Params: Color, Opacity, Speed, Tiling, EdgeSoftness, DepthFadeDistance.
# Run with the editor closed, or in the open editor via Tools -> Execute Python Script.
import unreal

MATS = "/Game/Environment/Materials"
PATH = f"{MATS}/M_FogWall"
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda m: unreal.log_warning("FOGWALL " + m)
noise_tex = unreal.load_asset("/Game/Environment/Textures/Stylized/T_Stylized_Soil_ARH")   # B = soft noise

if eal.does_asset_exist(PATH):
    mat = unreal.load_asset(PATH); mel.delete_all_material_expressions(mat)
else:
    mat = tools.create_asset("M_FogWall", MATS, unreal.Material, unreal.MaterialFactoryNew())
mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
mat.set_editor_property("two_sided", False)
mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)


def E(cls, x, y):
    return mel.create_material_expression(mat, cls, x, y)


def C(a, ao, b, bi):
    if not mel.connect_material_expressions(a, ao, b, bi):
        log(f"(warn) connect failed -> {bi}")


def scalar(name, v, x, y):
    e = E(unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", name); e.set_editor_property("default_value", v); return e


tc = E(unreal.MaterialExpressionTextureCoordinate, -1800, 0)
tiling = scalar("Tiling", 1.0, -1800, 120)
uv = E(unreal.MaterialExpressionMultiply, -1600, 0); C(tc, "", uv, "A"); C(tiling, "", uv, "B")
speed = scalar("Speed", 1.0, -1800, 250)
time = E(unreal.MaterialExpressionTime, -1800, 350)
ts = E(unreal.MaterialExpressionMultiply, -1600, 300); C(time, "", ts, "A"); C(speed, "", ts, "B")

samples = []
for i, (sx, sy, k) in enumerate(((0.03, -0.06, 1.0), (-0.025, -0.035, 0.6))):
    uvk = E(unreal.MaterialExpressionMultiply, -1400, i * 300); C(uv, "", uvk, "A"); uvk.set_editor_property("const_b", k)
    p = E(unreal.MaterialExpressionPanner, -1200, i * 300); C(uvk, "", p, "Coordinate"); C(ts, "", p, "Time")
    p.set_editor_property("speed_x", sx); p.set_editor_property("speed_y", sy)
    s = E(unreal.MaterialExpressionTextureSample, -1000, i * 300); s.set_editor_property("texture", noise_tex)
    s.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS); C(p, "", s, "UVs")
    samples.append(s)
nmul = E(unreal.MaterialExpressionMultiply, -750, 100); C(samples[0], "B", nmul, "A"); C(samples[1], "B", nmul, "B")
# remap noise product (~0..1) to a soft 0.35..1 density
nr = E(unreal.MaterialExpressionMultiply, -600, 100); C(nmul, "", nr, "A"); nr.set_editor_property("const_b", 1.3)
na = E(unreal.MaterialExpressionAdd, -480, 100); C(nr, "", na, "A"); na.set_editor_property("const_b", 0.35)

# soft edges: 1 - max(|u-0.5|, |v-0.5|) * 2, sharpened by EdgeSoftness
cen = E(unreal.MaterialExpressionSubtract, -1400, 700); C(tc, "", cen, "A"); cen.set_editor_property("const_b", 0.5)
ab = E(unreal.MaterialExpressionAbs, -1250, 700); C(cen, "", ab, "")
mu = E(unreal.MaterialExpressionComponentMask, -1100, 650); mu.set_editor_property("r", True); C(ab, "", mu, "")
mv = E(unreal.MaterialExpressionComponentMask, -1100, 750); mv.set_editor_property("g", True); C(ab, "", mv, "")
mx = E(unreal.MaterialExpressionMax, -950, 700); C(mu, "", mx, "A"); C(mv, "", mx, "B")
m2 = E(unreal.MaterialExpressionMultiply, -820, 700); C(mx, "", m2, "A"); m2.set_editor_property("const_b", 2.0)
inv = E(unreal.MaterialExpressionOneMinus, -700, 700); C(m2, "", inv, "")
es = scalar("EdgeSoftness", 4.0, -700, 800)
em = E(unreal.MaterialExpressionMultiply, -560, 700); C(inv, "", em, "A"); C(es, "", em, "B")
esat = E(unreal.MaterialExpressionSaturate, -440, 700); C(em, "", esat, "")

op = scalar("Opacity", 0.7, -480, 300)
o1 = E(unreal.MaterialExpressionMultiply, -330, 150); C(na, "", o1, "A"); C(op, "", o1, "B")
o2 = E(unreal.MaterialExpressionMultiply, -200, 300); C(o1, "", o2, "A"); C(esat, "", o2, "B")
df = E(unreal.MaterialExpressionDepthFade, -60, 300); C(o2, "", df, "Opacity")
dfd = scalar("DepthFadeDistance", 100.0, -200, 450); C(dfd, "", df, "FadeDistance")
osat = E(unreal.MaterialExpressionSaturate, 80, 300); C(df, "", osat, "")
mel.connect_material_property(osat, "", unreal.MaterialProperty.MP_OPACITY)

col = E(unreal.MaterialExpressionVectorParameter, -330, -150)
col.set_editor_property("parameter_name", "Color"); col.set_editor_property("default_value", unreal.LinearColor(0.85, 0.88, 0.92, 1))
mel.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
r = scalar("Roughness", 1.0, -330, -30)
mel.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)

mel.recompile_material(mat); eal.save_asset(PATH, only_if_is_dirty=False)

mi_path = f"{MATS}/MI_FogWall"
mi = unreal.load_asset(mi_path) if eal.does_asset_exist(mi_path) else tools.create_asset(
    "MI_FogWall", MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
mel.set_material_instance_parent(mi, mat); eal.save_asset(mi_path, only_if_is_dirty=False)
log(f"DONE {PATH} + {mi_path} expressions={mel.get_num_material_expressions(mat)}")
