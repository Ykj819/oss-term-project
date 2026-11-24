# Re-import the tree boss mesh (Export/SK_Tree.fbx from Export/Blender/Tree_Rig.blend: smoothed/decimated body, detailed
# eyes, user-made mouth + teeth, twig fingers, baked bark/leaf textures) over /Game/Characters/Tree/SK_Tree on the
# EXISTING skeleton SK_Tree_Skeleton (all Tree_* anims and ABP_Tree keep working) and keeps the existing physics asset.
# Textures Export/Textures/Tree/T_Tree_BC.png / T_Tree_N.png (Blender = OpenGL normal map -> flip green).
# Materials in /Game/Characters/Tree/Materials, matched to the FBX slot names:
#   M_Tree (BC + normal), M_TreeEye (emissive, param EyeGlow), M_TreePupil.
# Backup of the old assets: Saved/Backup_Tree_v1/ (old FBX: Export/SK_Tree_v1_backup.fbx).
# Headless:  UnrealEditor-Cmd.exe <uproject> -ExecutePythonScript="<abs path>" -unattended -nullrhi -nosplash -stdout
import os, shutil
import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
DEST = "/Game/Characters/Tree"
MATS = DEST + "/Materials"
TEXD = DEST + "/Textures"
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda m: unreal.log_warning("TREE " + m)

# ---- backup
bak = os.path.join(PROJ, "Saved", "Backup_Tree_v1")
if not os.path.exists(bak):
    os.makedirs(bak)
    for f in ("SK_Tree.uasset", "SK_Tree_Physics.uasset", "SK_Tree_Skeleton.uasset"):
        p = os.path.join(PROJ, "Content", "Characters", "Tree", f)
        if os.path.exists(p):
            shutil.copy2(p, bak)

old_mesh = unreal.load_asset(DEST + "/SK_Tree")
skeleton = unreal.load_asset(DEST + "/SK_Tree_Skeleton")
physics = old_mesh.get_editor_property("physics_asset") if old_mesh else unreal.load_asset(DEST + "/SK_Tree_Physics")
log(f"before: skeleton={skeleton.get_name() if skeleton else None} physics={physics.get_name() if physics else None}")

# ---- mesh
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
task = unreal.AssetImportTask()
task.set_editor_property("filename", os.path.join(PROJ, "Export", "SK_Tree.fbx"))
task.set_editor_property("destination_path", DEST)
task.set_editor_property("automated", True); task.set_editor_property("replace_existing", True)
task.set_editor_property("save", False); task.set_editor_property("options", ui)
tools.import_asset_tasks([task])
mesh = unreal.load_asset(DEST + "/SK_Tree")
if not mesh:
    log("FAILED import")
    raise SystemExit

# ---- textures
tex = {}
for name, srgb, comp, flip in (("T_Tree_BC", True, unreal.TextureCompressionSettings.TC_DEFAULT, False),
                               ("T_Tree_N", False, unreal.TextureCompressionSettings.TC_NORMALMAP, True)):
    t_task = unreal.AssetImportTask()
    t_task.set_editor_property("filename", os.path.join(PROJ, "Export", "Textures", "Tree", name + ".png"))
    t_task.set_editor_property("destination_path", TEXD); t_task.set_editor_property("automated", True)
    t_task.set_editor_property("replace_existing", True); t_task.set_editor_property("save", False)
    tools.import_asset_tasks([t_task])
    t = unreal.load_asset(f"{TEXD}/{name}")
    t.set_editor_property("srgb", srgb); t.set_editor_property("compression_settings", comp)
    t.set_editor_property("flip_green_channel", flip)
    eal.save_asset(f"{TEXD}/{name}", only_if_is_dirty=False)
    tex[name] = t

made = {}


def new_mat(name):
    path = f"{MATS}/{name}"
    if eal.does_asset_exist(path):
        # keep an existing graph (delete_all_material_expressions crashes the headless editor: !IsRooted)
        made[name] = unreal.load_asset(path)
        return None
    m = tools.create_asset(name, MATS, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("used_with_skeletal_mesh", True)
    return m


def E(m, cls, x, y):
    return mel.create_material_expression(m, cls, x, y)


def vparam(m, n, rgb, x, y):
    e = E(m, unreal.MaterialExpressionVectorParameter, x, y)
    e.set_editor_property("parameter_name", n); e.set_editor_property("default_value", unreal.LinearColor(*rgb, 1)); return e


def sparam(m, n, v, x, y):
    e = E(m, unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", n); e.set_editor_property("default_value", v); return e


def build_body(m):
    bc = E(m, unreal.MaterialExpressionTextureSampleParameter2D, -700, 0)
    bc.set_editor_property("parameter_name", "BaseColorMap"); bc.set_editor_property("texture", tex["T_Tree_BC"])
    nm = E(m, unreal.MaterialExpressionTextureSampleParameter2D, -700, 350)
    nm.set_editor_property("parameter_name", "NormalMap"); nm.set_editor_property("texture", tex["T_Tree_N"])
    nm.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    tint = vparam(m, "Tint", (1, 1, 1), -450, -150)
    mul = E(m, unreal.MaterialExpressionMultiply, -250, 0)
    mel.connect_material_expressions(bc, "RGB", mul, "A"); mel.connect_material_expressions(tint, "", mul, "B")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(nm, "RGB", unreal.MaterialProperty.MP_NORMAL)
    mel.connect_material_property(sparam(m, "Roughness", 0.85, -450, 250), "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(sparam(m, "Specular", 0.3, -450, 450), "", unreal.MaterialProperty.MP_SPECULAR)


def build_eye(m):
    # glowing amber eye. Physical auto exposure: emissive 1 looks dark -> EyeGlow scales it (like M_WolfEye).
    col = vparam(m, "Color", (1.0, 0.7, 0.15), -500, 0)
    glow = sparam(m, "EyeGlow", 8.0, -500, 200)
    em = E(m, unreal.MaterialExpressionMultiply, -250, 100)
    mel.connect_material_expressions(col, "", em, "A"); mel.connect_material_expressions(glow, "", em, "B")
    mel.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.connect_material_property(sparam(m, "Roughness", 0.85, -500, 350), "", unreal.MaterialProperty.MP_ROUGHNESS)


def build_pupil(m):
    mel.connect_material_property(vparam(m, "Color", (0.01, 0.008, 0.005), -400, 0), "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(sparam(m, "Roughness", 0.3, -400, 200), "", unreal.MaterialProperty.MP_ROUGHNESS)


for name, build in (("M_Tree", build_body), ("M_TreeEye", build_eye), ("M_TreePupil", build_pupil)):
    m = new_mat(name)
    if m:
        build(m)
        mel.recompile_material(m); eal.save_asset(f"{MATS}/{name}", only_if_is_dirty=False)
        made[name] = m

# ---- assign by slot name (elements are copies: edit and set the whole list back)
slots = []
names = []
for s in mesh.get_editor_property("materials"):
    sn = str(s.get_editor_property("material_slot_name"))
    key = next((k for k in sorted(made, key=len, reverse=True)
                if sn == k or sn.startswith(k + "_") or sn.startswith(k + ".")), None)
    if key:
        s.set_editor_property("material_interface", made[key])
    names.append(f"{sn}->{key}")
    slots.append(s)
mesh.set_editor_property("materials", slots)
if physics:
    mesh.set_editor_property("physics_asset", physics)
eal.save_asset(DEST + "/SK_Tree", only_if_is_dirty=False)
b = mesh.get_bounds()
log(f"OK skeleton={mesh.get_editor_property('skeleton').get_name()} physics="
    f"{mesh.get_editor_property('physics_asset').get_name() if mesh.get_editor_property('physics_asset') else None} "
    f"slots={names} bounds_extent=({b.box_extent.x:.0f},{b.box_extent.y:.0f},{b.box_extent.z:.0f})")

if "executepythonscript" in unreal.SystemLibrary.get_command_line().lower():
    unreal.SystemLibrary.quit_editor()
