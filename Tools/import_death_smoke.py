# Death smoke: Export/Textures/Effects/T_DeathSmoke.png (8x8 flipbook of a Mantaflow smoke burst,
# Export/Blender/scripts/props/gen_death_smoke_sim.py; the older 4x4 noise puff gen_death_smoke.py needs GRID = 4)
# -> /Game/Effects/DeathSmoke/{T_DeathSmoke, M_DeathSmoke}. M_DeathSmoke (deleted + rebuilt each run):
#   lit translucent (volumetric non-directional), two-sided, used with instanced static meshes (ADeathSmoke's cards)
#   frame = PerInstanceCustomData 0 (0..GRID*GRID-1, two frames blended), opacity = PerInstanceCustomData 1
#   BaseColor = smoke rgb * Tint, Emissive = same * EmissiveBoost (keeps it white in dark places), soft depth fade
# Editor closed:
#   UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script="<abs/forward/slash>/Tools/import_death_smoke.py" -unattended -nosplash -stdout
import os
import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
DEST = "/Game/Effects/DeathSmoke"
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda m: unreal.log_warning("DEATHSMOKE " + m)
GRID = 8

task = unreal.AssetImportTask()
task.set_editor_property("filename", os.path.join(PROJ, "Export", "Textures", "Effects", "T_DeathSmoke.png"))
task.set_editor_property("destination_path", DEST); task.set_editor_property("automated", True)
task.set_editor_property("replace_existing", True); task.set_editor_property("save", False)
tools.import_asset_tasks([task])
tex = unreal.load_asset(f"{DEST}/T_DeathSmoke")
tex.set_editor_property("srgb", True)
eal.save_asset(f"{DEST}/T_DeathSmoke", only_if_is_dirty=False)

path = f"{DEST}/M_DeathSmoke"
if eal.does_asset_exist(path):
    eal.delete_asset(path)
m = tools.create_asset("M_DeathSmoke", DEST, unreal.Material, unreal.MaterialFactoryNew())
m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
m.set_editor_property("two_sided", True)
m.set_editor_property("used_with_instanced_static_meshes", True)
m.set_editor_property("translucency_lighting_mode", unreal.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
C = mel.connect_material_expressions


def op(cls, a, b, x, y, const=None, aout="", bout=""):
    e = E(cls, x, y)
    C(a, aout, e, "A")
    if const is None:
        C(b, bout, e, "B")
    else:
        e.set_editor_property("const_b", const)
    return e


def custom(i, x, y):
    e = E(unreal.MaterialExpressionPerInstanceCustomData, x, y); e.set_editor_property("data_index", i); return e


def sparam(name, v, x, y):
    e = E(unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", name); e.set_editor_property("default_value", v); return e


tc = E(unreal.MaterialExpressionTextureCoordinate, -2200, -200)
frame = custom(0, -2200, 200)
f0 = E(unreal.MaterialExpressionFloor, -2000, 150); C(frame, "", f0, "")
f1a = op(unreal.MaterialExpressionAdd, f0, None, -1850, 300, const=1.0)
f1 = op(unreal.MaterialExpressionMin, f1a, None, -1700, 300, const=float(GRID * GRID - 1))
blend = E(unreal.MaterialExpressionFrac, -2000, 450); C(frame, "", blend, "")


def cell_sample(fi, y):
    row = E(unreal.MaterialExpressionFloor, -1450, y + 60)
    q = op(unreal.MaterialExpressionMultiply, fi, None, -1600, y + 60, const=1.0 / GRID); C(q, "", row, "")
    r4 = op(unreal.MaterialExpressionMultiply, row, None, -1300, y + 120, const=float(GRID))
    col = op(unreal.MaterialExpressionSubtract, fi, r4, -1150, y)
    ap = E(unreal.MaterialExpressionAppendVector, -1000, y)
    C(col, "", ap, "A"); C(row, "", ap, "B")
    uv = op(unreal.MaterialExpressionAdd, tc, ap, -850, y)
    uv4 = op(unreal.MaterialExpressionMultiply, uv, None, -700, y, const=1.0 / GRID)
    s = E(unreal.MaterialExpressionTextureSampleParameter2D, -550, y)
    s.set_editor_property("parameter_name", "SmokeMap"); s.set_editor_property("texture", tex)
    C(uv4, "", s, "UVs")
    return s


s0 = cell_sample(f0, 0)
s1 = cell_sample(f1, 400)
lr = E(unreal.MaterialExpressionLinearInterpolate, -300, 200)
C(s0, "RGBA", lr, "A"); C(s1, "RGBA", lr, "B"); C(blend, "", lr, "Alpha")
rgb = E(unreal.MaterialExpressionComponentMask, -150, 100)
rgb.set_editor_property("r", True); rgb.set_editor_property("g", True); rgb.set_editor_property("b", True); C(lr, "", rgb, "")
al = E(unreal.MaterialExpressionComponentMask, -150, 300)
al.set_editor_property("a", True); C(lr, "", al, "")
tint = E(unreal.MaterialExpressionVectorParameter, -150, -100)
tint.set_editor_property("parameter_name", "Tint"); tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
bc = op(unreal.MaterialExpressionMultiply, rgb, tint, 50, 0)
mel.connect_material_property(bc, "", unreal.MaterialProperty.MP_BASE_COLOR)
boost = sparam("EmissiveBoost", 0.6, 50, 150)
em = op(unreal.MaterialExpressionMultiply, bc, boost, 250, 100)
mel.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
opac = custom(1, -150, 500)
# soft round edge on the card: the late flipbook frames grow past their cell (the cut would show as a square)
ctr = op(unreal.MaterialExpressionSubtract, tc, None, -450, 650, const=0.5)
ln = E(unreal.MaterialExpressionLength, -300, 650); C(ctr, "", ln, "")
rim = E(unreal.MaterialExpressionOneMinus, -200, 650); C(op(unreal.MaterialExpressionMultiply, ln, None, -250, 750, const=2.0), "", rim, "")
rimk = op(unreal.MaterialExpressionMultiply, rim, None, -100, 650, const=3.5)
vig = E(unreal.MaterialExpressionSaturate, 0, 650); C(rimk, "", vig, "")
alv = op(unreal.MaterialExpressionMultiply, al, vig, -50, 400)
a1 = op(unreal.MaterialExpressionMultiply, alv, opac, 50, 400)
oscale = sparam("OpacityScale", 1.0, 50, 550)
a2 = op(unreal.MaterialExpressionMultiply, a1, oscale, 250, 450)
df = E(unreal.MaterialExpressionDepthFade, 400, 450); df.set_editor_property("fade_distance_default", 40.0)
C(a2, "", df, "Opacity")
mel.connect_material_property(df, "", unreal.MaterialProperty.MP_OPACITY)
r = E(unreal.MaterialExpressionConstant, 250, 300); r.set_editor_property("r", 1.0)
mel.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
mel.recompile_material(m)
eal.save_asset(path, only_if_is_dirty=False)
log(f"OK tex={bool(tex)} nexpr={mel.get_num_material_expressions(m)}")
