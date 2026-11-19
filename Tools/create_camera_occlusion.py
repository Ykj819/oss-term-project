# Camera occlusion fade for environment materials.
#   MPC_CameraOcclusion (/Game/Environment/Materials): CameraPos, PlayerPos (written every frame by the player
#   character, Oss_TermProjectCharacter.cpp UpdateCameraOcclusion), RadiusCamera, RadiusPlayer, PlayerGap, Strength.
#   Each listed material becomes Masked; pixels inside the capsule camera -> player (radius lerps from RadiusCamera at
#   the camera to RadiusPlayer at the player, the last PlayerGap part next to the player is kept) dither out
#   (DitherTemporalAA). Shadows are unaffected (ShadowReplace -> opacity 1 in the shadow pass).
#   Existing opacity masks are multiplied in. Materials that already have the fade (node desc TAG) are skipped.
# Run with the editor closed, or in the open editor via Tools -> Execute Python Script.
import unreal

MATS = "/Game/Environment/Materials"
MPC_PATH = f"{MATS}/MPC_CameraOcclusion"
TAG = "CameraOcclusionFade"
TARGETS = ["/Game/Environment/Trees/M_StylizedTree_Bark", "/Game/Environment/Trees/M_StylizedTree_Leaves",
           "/Game/Environment/Materials/M_Stylized_Prop",
           "/Game/Environment/Trees/M_RealisticTree_Bark", "/Game/Environment/Trees/M_RealisticTree_Leaves"]

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda m: unreal.log_warning("CAMOCC " + m)

# ---- parameter collection (created once: re-creating would change the parameter ids the materials reference)
if eal.does_asset_exist(MPC_PATH):
    mpc = unreal.load_asset(MPC_PATH)
else:
    mpc = tools.create_asset("MPC_CameraOcclusion", MATS, unreal.MaterialParameterCollection,
                             unreal.MaterialParameterCollectionFactoryNew())
    sc = []
    for n, v in (("RadiusCamera", 150.0), ("RadiusPlayer", 90.0), ("PlayerGap", 0.85), ("Strength", 0.92)):
        p = unreal.CollectionScalarParameter(); p.set_editor_property("parameter_name", n)
        p.set_editor_property("default_value", v); sc.append(p)
    vc = []
    for n in ("CameraPos", "PlayerPos"):   # far away by default -> no fade outside play
        p = unreal.CollectionVectorParameter(); p.set_editor_property("parameter_name", n)
        p.set_editor_property("default_value", unreal.LinearColor(0, 0, -1.0e7, 0)); vc.append(p)
    mpc.set_editor_property("scalar_parameters", sc)
    mpc.set_editor_property("vector_parameters", vc)
    eal.save_asset(MPC_PATH, only_if_is_dirty=False)
log(f"MPC {MPC_PATH} scalars={[str(p.get_editor_property('parameter_name')) for p in mpc.get_editor_property('scalar_parameters')]}")

dither_fn = unreal.load_asset("/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA")


def add_fade(mat):
    def E(cls, x, y):
        return mel.create_material_expression(mat, cls, x, y)

    ok = [True]

    def C(a, ao, b, bi):
        if not mel.connect_material_expressions(a, ao, b, bi):
            log(f"  (warn) {mat.get_name()}: connect failed -> {bi}"); ok[0] = False

    def coll(name, x, y):
        e = E(unreal.MaterialExpressionCollectionParameter, x, y)
        e.set_editor_property("collection", mpc); e.set_editor_property("parameter_name", name); return e

    def rgb(src, x, y):
        m = E(unreal.MaterialExpressionComponentMask, x, y)
        for c in ("r", "g", "b"):
            m.set_editor_property(c, True)
        C(src, "", m, ""); return m

    X, Y = -3200, 1400
    cam = rgb(coll("CameraPos", X, Y), X + 200, Y)
    ply = rgb(coll("PlayerPos", X, Y + 150), X + 200, Y + 150)
    wp = E(unreal.MaterialExpressionWorldPosition, X, Y + 300)
    ab = E(unreal.MaterialExpressionSubtract, X + 400, Y + 100); C(ply, "", ab, "A"); C(cam, "", ab, "B")
    ap = E(unreal.MaterialExpressionSubtract, X + 400, Y + 250); C(wp, "", ap, "A"); C(cam, "", ap, "B")
    d1 = E(unreal.MaterialExpressionDotProduct, X + 600, Y + 200); C(ap, "", d1, "A"); C(ab, "", d1, "B")
    d2 = E(unreal.MaterialExpressionDotProduct, X + 600, Y + 50); C(ab, "", d2, "A"); C(ab, "", d2, "B")
    mx = E(unreal.MaterialExpressionMax, X + 750, Y + 50); C(d2, "", mx, "A"); mx.set_editor_property("const_b", 1.0)
    dv = E(unreal.MaterialExpressionDivide, X + 900, Y + 150); C(d1, "", dv, "A"); C(mx, "", dv, "B")
    t = E(unreal.MaterialExpressionSaturate, X + 1050, Y + 150); C(dv, "", t, "")
    abt = E(unreal.MaterialExpressionMultiply, X + 1200, Y + 100); C(ab, "", abt, "A"); C(t, "", abt, "B")
    cl = E(unreal.MaterialExpressionAdd, X + 1350, Y + 50); C(cam, "", cl, "A"); C(abt, "", cl, "B")
    dist = E(unreal.MaterialExpressionDistance, X + 1500, Y + 250); C(wp, "", dist, "A"); C(cl, "", dist, "B")
    rc = coll("RadiusCamera", X + 1200, Y + 400); rp = coll("RadiusPlayer", X + 1200, Y + 520)
    r = E(unreal.MaterialExpressionLinearInterpolate, X + 1400, Y + 450)
    C(rc, "", r, "A"); C(rp, "", r, "B"); C(t, "", r, "Alpha")
    sub = E(unreal.MaterialExpressionSubtract, X + 1650, Y + 300); C(r, "", sub, "A"); C(dist, "", sub, "B")
    half = E(unreal.MaterialExpressionMultiply, X + 1650, Y + 450); C(r, "", half, "A"); half.set_editor_property("const_b", 0.5)
    dv2 = E(unreal.MaterialExpressionDivide, X + 1800, Y + 350); C(sub, "", dv2, "A"); C(half, "", dv2, "B")
    inside = E(unreal.MaterialExpressionSaturate, X + 1950, Y + 350); C(dv2, "", inside, "")
    gap = coll("PlayerGap", X + 1650, Y + 600)
    gs = E(unreal.MaterialExpressionSubtract, X + 1800, Y + 600); C(gap, "", gs, "A"); C(t, "", gs, "B")
    gm = E(unreal.MaterialExpressionMultiply, X + 1950, Y + 600); C(gs, "", gm, "A"); gm.set_editor_property("const_b", 15.0)
    gsat = E(unreal.MaterialExpressionSaturate, X + 2100, Y + 600); C(gm, "", gsat, "")
    st = coll("Strength", X + 2100, Y + 750)
    f1 = E(unreal.MaterialExpressionMultiply, X + 2250, Y + 450); C(inside, "", f1, "A"); C(gsat, "", f1, "B")
    f2 = E(unreal.MaterialExpressionMultiply, X + 2400, Y + 500); C(f1, "", f2, "A"); C(st, "", f2, "B")
    alpha = E(unreal.MaterialExpressionOneMinus, X + 2550, Y + 500); C(f2, "", alpha, "")
    dith = E(unreal.MaterialExpressionMaterialFunctionCall, X + 2700, Y + 500)
    dith.set_editor_property("material_function", dither_fn)
    if not mel.connect_material_expressions(alpha, "", dith, "Alpha Threshold"):
        C(alpha, "", dith, "AlphaThreshold")
    sr = E(unreal.MaterialExpressionShadowReplace, X + 2950, Y + 500)
    C(dith, "", sr, "Default")
    one = E(unreal.MaterialExpressionConstant, X + 2800, Y + 650); one.set_editor_property("r", 1.0)
    C(one, "", sr, "Shadow")
    final = sr
    prev = mel.get_material_property_input_node(mat, unreal.MaterialProperty.MP_OPACITY_MASK)
    if prev:
        out = mel.get_material_property_input_node_output_name(mat, unreal.MaterialProperty.MP_OPACITY_MASK)
        mm = E(unreal.MaterialExpressionMultiply, X + 3150, Y + 450); C(prev, out, mm, "A"); C(sr, "", mm, "B")
        final = mm
    final.set_editor_property("desc", TAG)
    mel.connect_material_property(final, "", unreal.MaterialProperty.MP_OPACITY_MASK)
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    return ok[0], bool(prev)


for path in TARGETS:
    mat = unreal.load_asset(path)
    if not mat:
        log(f"skip (missing) {path}"); continue
    cur = mel.get_material_property_input_node(mat, unreal.MaterialProperty.MP_OPACITY_MASK)
    if cur and str(cur.get_editor_property("desc")) == TAG:
        log(f"skip (already has fade) {path}"); continue
    ok, had_mask = add_fade(mat)
    mel.recompile_material(mat)
    eal.save_asset(path, only_if_is_dirty=False)
    log(f"{'OK' if ok else 'WARN'} {path} blend={mat.get_editor_property('blend_mode')} kept_old_mask={had_mask}")
