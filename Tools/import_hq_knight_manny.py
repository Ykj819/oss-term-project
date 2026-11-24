# Import the Tripo knight fitted onto the mannequin (Export/SKM_HQKnight_Manny.fbx, made by
# Export/Blender/scripts/characters/fit_hq_knight.py) -> /Game/Characters/HighQualityKnight/SKM_HQKnight_Manny on the
# existing skeleton SK_Mannequin (all player anims work), physics asset = Manny's, material M_HQKnight (rebuilt here from
# the textures that Tools/import_hq_knight.py imported). Not put on the player BP: AModelSwapVolume swaps it in at runtime.
# Headless:  UnrealEditor-Cmd.exe <uproject> -ExecutePythonScript="<this file>" -unattended -nullrhi -nosplash -stdout
import os
import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
DEST = "/Game/Characters/HighQualityKnight"
NAME = "SKM_HQKnight_Manny"
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda m: unreal.log_warning("HQMANNY " + m)

skeleton = unreal.load_asset("/Game/Characters/Mannequins/Meshes/SK_Mannequin")
manny = unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple")

if eal.does_asset_exist(f"{DEST}/{NAME}"):
    eal.delete_asset(f"{DEST}/{NAME}")   # re-import keeps stored settings: start clean
ui = unreal.FbxImportUI()
ui.set_editor_property("import_mesh", True)
ui.set_editor_property("import_as_skeletal", True)
ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
ui.set_editor_property("skeleton", skeleton)
ui.set_editor_property("import_materials", False)
ui.set_editor_property("import_textures", False)
ui.set_editor_property("import_animations", False)
ui.set_editor_property("create_physics_asset", False)
task = unreal.AssetImportTask()
task.set_editor_property("filename", os.path.join(PROJ, "Export", NAME + ".fbx"))
task.set_editor_property("destination_path", DEST)
task.set_editor_property("automated", True); task.set_editor_property("replace_existing", True)
task.set_editor_property("save", False); task.set_editor_property("options", ui)
tools.import_asset_tasks([task])
mesh = unreal.load_asset(f"{DEST}/{NAME}")
if not mesh:
    log("FAILED import")
    raise SystemExit

# ---- material (textures from Tools/import_hq_knight.py)
tex = {n: unreal.load_asset(f"{DEST}/{n}") for n in ("T_HQKnight_BC", "T_HQKnight_N", "T_HQKnight_M", "T_HQKnight_R")}
MAT = f"{DEST}/M_HQKnight"
if eal.does_asset_exist(MAT):
    mat = unreal.load_asset(MAT); mel.delete_all_material_expressions(mat)
else:
    mat = tools.create_asset("M_HQKnight", DEST, unreal.Material, unreal.MaterialFactoryNew())
mat.set_editor_property("used_with_skeletal_mesh", True)
E = lambda cls, x, y: mel.create_material_expression(mat, cls, x, y)


def tparam(n, t, st, x, y):
    e = E(unreal.MaterialExpressionTextureSampleParameter2D, x, y)
    e.set_editor_property("parameter_name", n); e.set_editor_property("texture", t)
    e.set_editor_property("sampler_type", st); return e


ST = unreal.MaterialSamplerType
bc = tparam("BaseColorMap", tex["T_HQKnight_BC"], ST.SAMPLERTYPE_COLOR, -500, 0)
nm = tparam("NormalMap", tex["T_HQKnight_N"], ST.SAMPLERTYPE_NORMAL, -500, 250)
mt = tparam("MetallicMap", tex["T_HQKnight_M"], ST.SAMPLERTYPE_LINEAR_GRAYSCALE, -500, 500)
rg = tparam("RoughnessMap", tex["T_HQKnight_R"], ST.SAMPLERTYPE_LINEAR_GRAYSCALE, -500, 750)
mel.connect_material_property(bc, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
mel.connect_material_property(nm, "RGB", unreal.MaterialProperty.MP_NORMAL)
mel.connect_material_property(mt, "R", unreal.MaterialProperty.MP_METALLIC)
mel.connect_material_property(rg, "R", unreal.MaterialProperty.MP_ROUGHNESS)
mel.recompile_material(mat); eal.save_asset(MAT, only_if_is_dirty=False)

mats = []
for m in mesh.get_editor_property("materials"):   # elements are copies: edit and set the whole list back
    m.set_editor_property("material_interface", mat)
    mats.append(m)
mesh.set_editor_property("materials", mats)
pa = manny.get_editor_property("physics_asset")
if pa:
    mesh.set_editor_property("physics_asset", pa)
eal.save_asset(f"{DEST}/{NAME}", only_if_is_dirty=False)
b = mesh.get_bounds()
sk = mesh.get_editor_property("skeleton")
log(f"mesh OK skeleton={sk.get_name() if sk else None} slots={len(mats)} physics={pa.get_name() if pa else None} "
    f"extent=({b.box_extent.x:.0f},{b.box_extent.y:.0f},{b.box_extent.z:.0f}) origin_z={b.origin.z:.0f}")

if "executepythonscript" in unreal.SystemLibrary.get_command_line().lower():
    unreal.SystemLibrary.quit_editor()
