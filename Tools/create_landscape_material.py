# Landscape layered material from the stylized surface textures (/Game/Environment/Textures/Stylized):
#   M_Stylized_Landscape   -> /Game/Environment/Materials
#   Paint layers (height blend, the ARH height channel decides which layer pokes through at the edges):
#     Grass, Soil, Stone, Rock, Sand, Snow, FallenLeaves
#   World-aligned UVs (TileSize in metres), shared wrap samplers (21 textures > 16 sampler limit),
#   large-scale brightness variation (MacroStrength / MacroScale) to hide tiling.
#   Per-layer parameters: <Layer>_Tint, <Layer>_TileScale.  Global: TileSize, NormalStrength, RoughnessScale.
# Run with the editor closed:
#   UnrealEditor-Cmd.exe <project>.uproject -run=pythonscript -script="<this file>" -unattended -nosplash -stdout
import unreal

MATS = "/Game/Environment/Materials"
TEXD = "/Game/Environment/Textures/Stylized"
PATH = f"{MATS}/M_Stylized_Landscape"
LAYERS = ["Grass", "Soil", "Stone", "Rock", "Sand", "Snow", "FallenLeaves"]
# default per-layer texture scale multiplier (1 = TileSize metres per repeat)
TILE_SCALE = {"Grass": 1.0, "Soil": 1.0, "Stone": 0.8, "Rock": 1.6, "Sand": 1.2, "Snow": 1.5, "FallenLeaves": 1.0}

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda msg: unreal.log_warning("LANDMAT " + msg)
SHARED = unreal.SamplerSourceMode.SSM_WRAP_WORLD_GROUP_SETTINGS

if eal.does_asset_exist(PATH):
    mat = unreal.load_asset(PATH); mel.delete_all_material_expressions(mat)
else:
    mat = tools.create_asset("M_Stylized_Landscape", MATS, unreal.Material, unreal.MaterialFactoryNew())


def E(cls, x, y):
    return mel.create_material_expression(mat, cls, x, y)


def C(a, ao, b, bi):
    if not mel.connect_material_expressions(a, ao, b, bi):
        log(f"(warn) connect failed -> {bi}")


def scalar(name, v, x, y, group="Global"):
    e = E(unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", name); e.set_editor_property("default_value", v)
    e.set_editor_property("group", group); return e


def sample(t, stype, uv, x, y):
    e = E(unreal.MaterialExpressionTextureSample, x, y)
    e.set_editor_property("texture", t); e.set_editor_property("sampler_type", stype)
    e.set_editor_property("sampler_source", SHARED); C(uv, "", e, "UVs"); return e


# ---- world-aligned base UV: WorldPosition.xy / (TileSize * 100)
wp = E(unreal.MaterialExpressionWorldPosition, -3400, 0)
wxy = E(unreal.MaterialExpressionComponentMask, -3200, 0)
wxy.set_editor_property("r", True); wxy.set_editor_property("g", True); C(wp, "", wxy, "")
tile = scalar("TileSize", 2.0, -3400, 150)
tcm = E(unreal.MaterialExpressionMultiply, -3200, 150); C(tile, "", tcm, "A"); tcm.set_editor_property("const_b", 100.0)
base_uv = E(unreal.MaterialExpressionDivide, -3000, 0); C(wxy, "", base_uv, "A"); C(tcm, "", base_uv, "B")

# ---- three blend nodes (base colour / normal / ARH) with the same height-blended layers
def blend_node(x, y):
    b = E(unreal.MaterialExpressionLandscapeLayerBlend, x, y)
    ins = []
    for i, n in enumerate(LAYERS):
        li = unreal.LayerBlendInput()
        li.set_editor_property("layer_name", n)
        li.set_editor_property("blend_type", unreal.LandscapeLayerBlendType.LB_HEIGHT_BLEND)
        li.set_editor_property("preview_weight", 1.0 if i == 0 else 0.0)
        ins.append(li)
    b.set_editor_property("layers", ins); return b


bl_bc = blend_node(-600, -400)
bl_n = blend_node(-600, 400)
bl_arh = blend_node(-600, 1200)

flat = E(unreal.MaterialExpressionConstant3Vector, -1500, -900)
flat.set_editor_property("constant", unreal.LinearColor(0, 0, 1, 1))
nstr = scalar("NormalStrength", 1.0, -1500, -800)

y = -2400
for n in LAYERS:
    ts = scalar(f"{n}_TileScale", TILE_SCALE[n], -2800, y + 100, n)
    uv = E(unreal.MaterialExpressionDivide, -2550, y + 100); C(base_uv, "", uv, "A"); C(ts, "", uv, "B")
    bc = sample(unreal.load_asset(f"{TEXD}/T_Stylized_{n}_BC"), unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, uv, -2250, y)
    nm = sample(unreal.load_asset(f"{TEXD}/T_Stylized_{n}_N"), unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, uv, -2250, y + 250)
    ar = sample(unreal.load_asset(f"{TEXD}/T_Stylized_{n}_ARH"), unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, uv, -2250, y + 500)
    tint = E(unreal.MaterialExpressionVectorParameter, -1950, y - 100)
    tint.set_editor_property("parameter_name", f"{n}_Tint"); tint.set_editor_property("group", n)
    tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    tb = E(unreal.MaterialExpressionMultiply, -1700, y); C(bc, "RGB", tb, "A"); C(tint, "", tb, "B")
    C(tb, "", bl_bc, f"Layer {n}")
    nl = E(unreal.MaterialExpressionLinearInterpolate, -1700, y + 250)
    C(flat, "", nl, "A"); C(nm, "RGB", nl, "B"); C(nstr, "", nl, "Alpha")
    C(nl, "", bl_n, f"Layer {n}")
    C(ar, "", bl_arh, f"Layer {n}")
    for b in (bl_bc, bl_n, bl_arh):
        C(ar, "B", b, f"Height {n}")
    y += 800

# ---- macro variation: soft large-scale noise (soil height channel) multiplies base colour
mscale = scalar("MacroScale", 9.37, -1500, -1500, "Macro")
muv = E(unreal.MaterialExpressionDivide, -1300, -1500); C(base_uv, "", muv, "A"); C(mscale, "", muv, "B")
mtex = sample(unreal.load_asset(f"{TEXD}/T_Stylized_Soil_ARH"), unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, muv, -1100, -1500)
mrem = E(unreal.MaterialExpressionMultiply, -850, -1500); C(mtex, "B", mrem, "A"); mrem.set_editor_property("const_b", 0.8)
madd = E(unreal.MaterialExpressionAdd, -700, -1500); C(mrem, "", madd, "A"); madd.set_editor_property("const_b", 0.6)
mstr = scalar("MacroStrength", 0.5, -850, -1350, "Macro")
mlerp = E(unreal.MaterialExpressionLinearInterpolate, -500, -1400)
mlerp.set_editor_property("const_a", 1.0); C(madd, "", mlerp, "B"); C(mstr, "", mlerp, "Alpha")
fbc = E(unreal.MaterialExpressionMultiply, -250, -400); C(bl_bc, "", fbc, "A"); C(mlerp, "", fbc, "B")
mel.connect_material_property(fbc, "", unreal.MaterialProperty.MP_BASE_COLOR)

mel.connect_material_property(bl_n, "", unreal.MaterialProperty.MP_NORMAL)
ao = E(unreal.MaterialExpressionComponentMask, -250, 1100); ao.set_editor_property("r", True); C(bl_arh, "", ao, "")
mel.connect_material_property(ao, "", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
rg = E(unreal.MaterialExpressionComponentMask, -400, 1300); rg.set_editor_property("g", True); C(bl_arh, "", rg, "")
rs = scalar("RoughnessScale", 1.0, -400, 1450)
rm = E(unreal.MaterialExpressionMultiply, -250, 1300); C(rg, "", rm, "A"); C(rs, "", rm, "B")
mel.connect_material_property(rm, "", unreal.MaterialProperty.MP_ROUGHNESS)

mel.recompile_material(mat)
eal.save_asset(PATH, only_if_is_dirty=False)

for b, nm_ in ((bl_bc, "BC"), (bl_n, "N"), (bl_arh, "ARH")):
    ins = mel.get_inputs_for_material_expression(mat, b)
    log(f"{nm_} blend inputs connected {sum(1 for i in ins if i)}/{len(ins)}")
log(f"DONE {PATH} expressions={mel.get_num_material_expressions(mat)} "
    f"samplers={len(mel.get_used_textures(mat))} textures used")
