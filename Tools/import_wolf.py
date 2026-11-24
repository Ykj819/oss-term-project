# Re-import the wolf boss mesh (Export/SK_Wolf.fbx from Export/Blender/Wolf_Rig.blend: smoothed/decimated body, eyes,
# mouth + teeth, claws, baked fur textures) over /Game/Characters/Wolf/SK_Wolf on the EXISTING skeleton
# SK_Wolf_Skeleton (all Wolf_* anims and ABP_Wolf keep working) and keeps the existing physics asset.
# Textures Export/Textures/Wolf/T_Wolf_BC.png / T_Wolf_N.png (Blender = OpenGL normal map -> flip green).
# Materials in /Game/Characters/Wolf/Materials, matched to the FBX slot names:
#   M_Wolf (BC + normal), M_WolfEye (emissive, param EyeGlow), M_WolfMouth, M_WolfTeeth, M_WolfNose, M_WolfClaw.
# Backup of the old assets: Saved/Backup_Wolf_v1/.
# Headless:  UnrealEditor-Cmd.exe <uproject> -ExecutePythonScript="<abs path>" -unattended -nullrhi -nosplash -stdout
import os, shutil
import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
DEST = "/Game/Characters/Wolf"
MATS = DEST + "/Materials"
TEXD = DEST + "/Textures"
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda m: unreal.log_warning("WOLF " + m)

# ---- backup
bak = os.path.join(PROJ, "Saved", "Backup_Wolf_v1")
if not os.path.exists(bak):
    os.makedirs(bak)
    for f in ("SK_Wolf.uasset", "SK_Wolf_Physics.uasset", "SK_Wolf_Skeleton.uasset"):
        p = os.path.join(PROJ, "Content", "Characters", "Wolf", f)
        if os.path.exists(p):
            shutil.copy2(p, bak)

old_mesh = unreal.load_asset(DEST + "/SK_Wolf")
skeleton = unreal.load_asset(DEST + "/SK_Wolf_Skeleton")
physics = (old_mesh.get_editor_property("physics_asset") if old_mesh else None) or unreal.load_asset(DEST + "/SK_Wolf_Physics")
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
sk.set_editor_property("vertex_color_import_option", unreal.VertexColorImportOption.REPLACE)
task = unreal.AssetImportTask()
task.set_editor_property("filename", os.path.join(PROJ, "Export", "SK_Wolf.fbx"))
task.set_editor_property("destination_path", DEST)
task.set_editor_property("automated", True); task.set_editor_property("replace_existing", True)
task.set_editor_property("save", False); task.set_editor_property("options", ui)
tools.import_asset_tasks([task])
mesh = unreal.load_asset(DEST + "/SK_Wolf")
if not mesh:
    log("FAILED import")
    raise SystemExit

# ---- textures
tex = {}
for name, srgb, comp, flip in (("T_Wolf_BC", True, unreal.TextureCompressionSettings.TC_DEFAULT, False),
                               ("T_Wolf_N", False, unreal.TextureCompressionSettings.TC_NORMALMAP, True)):
    t_task = unreal.AssetImportTask()
    t_task.set_editor_property("filename", os.path.join(PROJ, "Export", "Textures", "Wolf", name + ".png"))
    t_task.set_editor_property("destination_path", TEXD); t_task.set_editor_property("automated", True)
    t_task.set_editor_property("replace_existing", True); t_task.set_editor_property("save", False)
    tools.import_asset_tasks([t_task])
    t = unreal.load_asset(f"{TEXD}/{name}")
    t.set_editor_property("srgb", srgb); t.set_editor_property("compression_settings", comp)
    t.set_editor_property("flip_green_channel", flip)
    eal.save_asset(f"{TEXD}/{name}", only_if_is_dirty=False)
    tex[name] = t


# ---- materials
def new_mat(name):
    path = f"{MATS}/{name}"
    if eal.does_asset_exist(path):
        # existing material: keep its graph (delete_all_material_expressions crashed the headless editor on a
        # re-run: assertion !IsRooted in MaterialEditor) and only refresh the flags
        m = unreal.load_asset(path)
        m.set_editor_property("two_sided", True)
        mel.recompile_material(m); eal.save_asset(path, only_if_is_dirty=False)
        made[name] = m
        return None
    m = tools.create_asset(name, MATS, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("used_with_skeletal_mesh", True)
    # Two-sided: the rebuilt head has inward-facing faces around the snout/jaw seam; Blender shows back faces so they
    # look closed there, UE culls them and leaves see-through gaps.
    m.set_editor_property("two_sided", True)
    return m


def E(m, cls, x, y):
    return mel.create_material_expression(m, cls, x, y)


def vparam(m, n, rgb, x, y):
    e = E(m, unreal.MaterialExpressionVectorParameter, x, y)
    e.set_editor_property("parameter_name", n); e.set_editor_property("default_value", unreal.LinearColor(*rgb, 1)); return e


def sparam(m, n, v, x, y):
    e = E(m, unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", n); e.set_editor_property("default_value", v); return e


def finish(m, name):
    mel.recompile_material(m); eal.save_asset(f"{MATS}/{name}", only_if_is_dirty=False); return m


made = {}


def build_body(m):
    bc = E(m, unreal.MaterialExpressionTextureSampleParameter2D, -700, 0)
    bc.set_editor_property("parameter_name", "BaseColorMap"); bc.set_editor_property("texture", tex["T_Wolf_BC"])
    nm = E(m, unreal.MaterialExpressionTextureSampleParameter2D, -700, 350)
    nm.set_editor_property("parameter_name", "NormalMap"); nm.set_editor_property("texture", tex["T_Wolf_N"])
    nm.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    tint = vparam(m, "Tint", (1, 1, 1), -450, -150)
    mul = E(m, unreal.MaterialExpressionMultiply, -250, 0)
    mel.connect_material_expressions(bc, "RGB", mul, "A"); mel.connect_material_expressions(tint, "", mul, "B")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(nm, "RGB", unreal.MaterialProperty.MP_NORMAL)
    mel.connect_material_property(sparam(m, "Roughness", 0.8, -450, 250), "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(sparam(m, "Specular", 0.35, -450, 450), "", unreal.MaterialProperty.MP_SPECULAR)


def build_flat(rgb, rough):
    def f(m):
        mel.connect_material_property(vparam(m, "Color", rgb, -400, 0), "", unreal.MaterialProperty.MP_BASE_COLOR)
        mel.connect_material_property(sparam(m, "Roughness", rough, -400, 200), "", unreal.MaterialProperty.MP_ROUGHNESS)
    return f


def build_eye(m):
    # amber glow. With the project's physical auto exposure an emissive of 1 looks dark -> EyeGlow scales it.
    col = vparam(m, "Color", (1.0, 0.55, 0.05), -500, 0)
    glow = sparam(m, "EyeGlow", 8.0, -500, 200)      # default sun 10 lux -> white surface ~3; eyes a bit brighter
    em = E(m, unreal.MaterialExpressionMultiply, -250, 100)
    mel.connect_material_expressions(col, "", em, "A"); mel.connect_material_expressions(glow, "", em, "B")
    mel.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)


for name, build in (("M_Wolf", build_body), ("M_WolfMouth", build_flat((0.18, 0.02, 0.03), 0.45)),
                    ("M_WolfTeeth", build_flat((0.85, 0.82, 0.72), 0.35)), ("M_WolfNose", build_flat((0.02, 0.02, 0.02), 0.3)),
                    ("M_WolfClaw", build_flat((0.03, 0.028, 0.025), 0.35)), ("M_WolfEye", build_eye)):
    m = new_mat(name)
    if m:
        build(m)
        made[name] = finish(m, name)

# ---- assign by slot name (elements are copies: edit and set the whole list back)
slots = []
names = []
for s in mesh.get_editor_property("materials"):
    sn = str(s.get_editor_property("material_slot_name"))
    key = next((k for k in made if sn == k or sn.startswith(k + "_") or sn.startswith(k + ".")), None)
    if key is None and sn.startswith("M_WolfPlaceholder"):
        key = "M_Wolf"
    if key:
        s.set_editor_property("material_interface", made[key])
    names.append(f"{sn}->{key}")
    slots.append(s)
mesh.set_editor_property("materials", slots)
if physics:
    mesh.set_editor_property("physics_asset", physics)
eal.save_asset(DEST + "/SK_Wolf", only_if_is_dirty=False)
# bone check: an FBX exported without the (hidden) armature imports as a rigid mesh with ONE bone named after the mesh
# ("SK_Wolf_Skeleton is missing bones ... SK_Wolf") and no anim moves it.
log(f"bone check: root children={mesh.get_bone_children('root')} (expect ['pelvis'])")
b = mesh.get_bounds()
log(f"OK skeleton={mesh.get_editor_property('skeleton').get_name()} physics="
    f"{mesh.get_editor_property('physics_asset').get_name() if mesh.get_editor_property('physics_asset') else None} "
    f"slots={names} bounds_extent=({b.box_extent.x:.0f},{b.box_extent.y:.0f},{b.box_extent.z:.0f})")

if "executepythonscript" in unreal.SystemLibrary.get_command_line().lower():
    unreal.SystemLibrary.quit_editor()
