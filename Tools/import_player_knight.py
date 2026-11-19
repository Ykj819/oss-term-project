# Import the player knight (Export/SKM_PlayerKnight.fbx, made by Export/Blender/scripts/characters/gen_player_knight.py)
#   -> /Game/Characters/PlayerKnight/SKM_PlayerKnight on the existing skeleton SK_Mannequin (all mannequin anims work),
#   physics asset = the mannequin's (ragdoll on death), material M_Stylized_Character:
#   BaseColor = VertexColor.rgb^2.2 * Tint, Metallic = VertexColor.a * MetallicScale,
#   Roughness = lerp(RoughnessCloth, RoughnessMetal, VertexColor.a).
# SET_PLAYER = True also puts the mesh on BP_ThirdPersonCharacter (backup of the .uasset is made first).
# Headless:  UnrealEditor-Cmd.exe <uproject> -ExecutePythonScript="<this file>" -unattended -nullrhi -nosplash -stdout
import os, shutil
import unreal

SET_PLAYER = True
PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
DEST = "/Game/Characters/PlayerKnight"
MAT = "/Game/Characters/PlayerKnight/M_Stylized_Character"
BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda m: unreal.log_warning("KNIGHT " + m)

skeleton = unreal.load_asset("/Game/Characters/Mannequins/Meshes/SK_Mannequin")
manny = unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple")

ui = unreal.FbxImportUI()
ui.set_editor_property("import_mesh", True)
ui.set_editor_property("import_as_skeletal", True)
ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
ui.set_editor_property("skeleton", skeleton)
ui.set_editor_property("import_materials", False)
ui.set_editor_property("import_textures", False)
ui.set_editor_property("import_animations", False)
ui.set_editor_property("create_physics_asset", False)
sk = ui.get_editor_property("skeletal_mesh_import_data")
sk.set_editor_property("import_morph_targets", False)
sk.set_editor_property("vertex_color_import_option", unreal.VertexColorImportOption.REPLACE)
task = unreal.AssetImportTask()
task.set_editor_property("filename", os.path.join(PROJ, "Export", "SKM_PlayerKnight.fbx"))
task.set_editor_property("destination_path", DEST)
task.set_editor_property("automated", True); task.set_editor_property("replace_existing", True)
task.set_editor_property("save", False); task.set_editor_property("options", ui)
tools.import_asset_tasks([task])
mesh = unreal.load_asset(f"{DEST}/SKM_PlayerKnight")
if not mesh:
    log("FAILED import")
    raise SystemExit

# ---- v2: baked textures (Export/Textures/PlayerKnight) + textured material M_PlayerKnight
TEX_SRC = os.path.join(PROJ, "Export", "Textures", "PlayerKnight")
textured = os.path.exists(os.path.join(TEX_SRC, "T_PlayerKnight_BC.png"))
if textured:
    tex = {}
    for name, srgb, comp in (("T_PlayerKnight_BC", True, unreal.TextureCompressionSettings.TC_DEFAULT),
                             ("T_PlayerKnight_ORM", False, unreal.TextureCompressionSettings.TC_MASKS)):
        t_task = unreal.AssetImportTask()
        t_task.set_editor_property("filename", os.path.join(TEX_SRC, name + ".png"))
        t_task.set_editor_property("destination_path", DEST); t_task.set_editor_property("automated", True)
        t_task.set_editor_property("replace_existing", True); t_task.set_editor_property("save", False)
        tools.import_asset_tasks([t_task])
        t = unreal.load_asset(f"{DEST}/{name}")
        t.set_editor_property("srgb", srgb); t.set_editor_property("compression_settings", comp)
        eal.save_asset(f"{DEST}/{name}", only_if_is_dirty=False)
        tex[name] = t
    MAT = f"{DEST}/M_PlayerKnight"
    if eal.does_asset_exist(MAT):
        mat = unreal.load_asset(MAT); mel.delete_all_material_expressions(mat)
    else:
        mat = tools.create_asset("M_PlayerKnight", DEST, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("used_with_skeletal_mesh", True)
    E = lambda cls, x, y: mel.create_material_expression(mat, cls, x, y)

    def scalar(n, v, x, y):
        e = E(unreal.MaterialExpressionScalarParameter, x, y)
        e.set_editor_property("parameter_name", n); e.set_editor_property("default_value", v); return e

    def tparam(n, t, st, x, y):
        e = E(unreal.MaterialExpressionTextureSampleParameter2D, x, y)
        e.set_editor_property("parameter_name", n); e.set_editor_property("texture", t)
        e.set_editor_property("sampler_type", st); return e
    bc = tparam("BaseColorMap", tex["T_PlayerKnight_BC"], unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, -800, 0)
    orm = tparam("ORMMap", tex["T_PlayerKnight_ORM"], unreal.MaterialSamplerType.SAMPLERTYPE_MASKS, -800, 350)
    tint = E(unreal.MaterialExpressionVectorParameter, -500, -150)
    tint.set_editor_property("parameter_name", "Tint"); tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    bm = E(unreal.MaterialExpressionMultiply, -250, 0)
    mel.connect_material_expressions(bc, "RGB", bm, "A"); mel.connect_material_expressions(tint, "", bm, "B")
    mel.connect_material_property(bm, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(orm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    rs = scalar("RoughnessScale", 1.0, -500, 450)
    rmul = E(unreal.MaterialExpressionMultiply, -250, 400)
    mel.connect_material_expressions(orm, "G", rmul, "A"); mel.connect_material_expressions(rs, "", rmul, "B")
    mel.connect_material_property(rmul, "", unreal.MaterialProperty.MP_ROUGHNESS)
    ms = scalar("MetallicScale", 1.0, -500, 600)
    mmul = E(unreal.MaterialExpressionMultiply, -250, 550)
    mel.connect_material_expressions(orm, "B", mmul, "A"); mel.connect_material_expressions(ms, "", mmul, "B")
    mel.connect_material_property(mmul, "", unreal.MaterialProperty.MP_METALLIC)
    mel.recompile_material(mat); eal.save_asset(MAT, only_if_is_dirty=False)

# ---- v1 vertex-colour material
if textured:
    pass
elif eal.does_asset_exist(MAT):
    mat = unreal.load_asset(MAT)
else:
    mat = tools.create_asset("M_Stylized_Character", DEST, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("used_with_skeletal_mesh", True)
    E = lambda cls, x, y: mel.create_material_expression(mat, cls, x, y)

    def scalar(n, v, x, y):
        e = E(unreal.MaterialExpressionScalarParameter, x, y)
        e.set_editor_property("parameter_name", n); e.set_editor_property("default_value", v); return e
    vc = E(unreal.MaterialExpressionVertexColor, -900, 0)
    g = scalar("VertexColorGamma", 2.2, -900, 200)
    pw = E(unreal.MaterialExpressionPower, -650, 0)
    mel.connect_material_expressions(vc, "", pw, "Base"); mel.connect_material_expressions(g, "", pw, "Exp")
    tint = E(unreal.MaterialExpressionVectorParameter, -650, 200)
    tint.set_editor_property("parameter_name", "Tint"); tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    bm = E(unreal.MaterialExpressionMultiply, -400, 0)
    mel.connect_material_expressions(pw, "", bm, "A"); mel.connect_material_expressions(tint, "", bm, "B")
    mel.connect_material_property(bm, "", unreal.MaterialProperty.MP_BASE_COLOR)
    ms = scalar("MetallicScale", 1.0, -650, 350)
    mm = E(unreal.MaterialExpressionMultiply, -400, 300)
    mel.connect_material_expressions(vc, "A", mm, "A"); mel.connect_material_expressions(ms, "", mm, "B")
    mel.connect_material_property(mm, "", unreal.MaterialProperty.MP_METALLIC)
    rc = scalar("RoughnessCloth", 0.75, -650, 500); rm = scalar("RoughnessMetal", 0.32, -650, 600)
    rl = E(unreal.MaterialExpressionLinearInterpolate, -400, 500)
    mel.connect_material_expressions(rc, "", rl, "A"); mel.connect_material_expressions(rm, "", rl, "B")
    mel.connect_material_expressions(vc, "A", rl, "Alpha")
    mel.connect_material_property(rl, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(mat); eal.save_asset(MAT, only_if_is_dirty=False)

mats = []
for m in mesh.get_editor_property("materials"):   # elements are copies: edit and set the whole list back
    m.set_editor_property("material_interface", mat)
    mats.append(m)
mesh.set_editor_property("materials", mats)
pa = manny.get_editor_property("physics_asset")
if pa:
    mesh.set_editor_property("physics_asset", pa)
eal.save_asset(f"{DEST}/SKM_PlayerKnight", only_if_is_dirty=False)
log(f"mesh OK skeleton={mesh.get_editor_property('skeleton').get_name()} slots={len(mats)} physics={pa.get_name() if pa else None}")

# ---- put it on the player blueprint
if SET_PLAYER:
    src = os.path.join(PROJ, "Content", "ThirdPerson", "Blueprints", "BP_ThirdPersonCharacter.uasset")
    bak = os.path.join(PROJ, "Saved", "Backup_BP_ThirdPersonCharacter_before_knight.uasset")
    if not os.path.exists(bak):
        shutil.copy2(src, bak)
    bp = unreal.load_asset(BP)
    cdo = unreal.get_default_object(bp.generated_class())
    comp = cdo.get_editor_property("mesh")
    before = comp.get_editor_property("skeletal_mesh_asset")
    comp.set_editor_property("skeletal_mesh_asset", mesh)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    eal.save_asset(BP, only_if_is_dirty=False)
    cdo = unreal.get_default_object(unreal.load_asset(BP).generated_class())
    after = cdo.get_editor_property("mesh").get_editor_property("skeletal_mesh_asset")
    log(f"player BP mesh {before.get_name() if before else None} -> {after.get_name() if after else None} (backup {bak})")

if "executepythonscript" in unreal.SystemLibrary.get_command_line().lower():
    unreal.SystemLibrary.quit_editor()
