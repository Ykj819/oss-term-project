# Import the user's Tripo knight (Desktop/이미지/high_quality_knight, copied to Export/HighQualityKnight)
#   -> /Game/Characters/HighQualityKnight/SKM_HQKnight with its OWN new skeleton (nothing existing is touched,
#   not put on the player). Textures T_HQKnight_{BC,N,M,R} + material M_HQKnight.
# Headless:  UnrealEditor-Cmd.exe <uproject> -ExecutePythonScript="<this file>" -unattended -nullrhi -nosplash -stdout
import os
import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
SRC = os.path.join(PROJ, "Export", "HighQualityKnight")
DEST = "/Game/Characters/HighQualityKnight"
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda m: unreal.log_warning("HQKNIGHT " + m)

ui = unreal.FbxImportUI()
ui.set_editor_property("import_mesh", True)
ui.set_editor_property("import_as_skeletal", True)
ui.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
ui.set_editor_property("import_materials", False)
ui.set_editor_property("import_textures", False)
ui.set_editor_property("import_animations", False)
ui.set_editor_property("create_physics_asset", True)
task = unreal.AssetImportTask()
task.set_editor_property("filename", os.path.join(SRC, "SKM_HQKnight.fbx"))
task.set_editor_property("destination_path", DEST)
task.set_editor_property("automated", True); task.set_editor_property("replace_existing", True)
task.set_editor_property("save", False); task.set_editor_property("options", ui)
tools.import_asset_tasks([task])
mesh = unreal.load_asset(f"{DEST}/SKM_HQKnight")
if not mesh:
    log("FAILED import")
    raise SystemExit

tex = {}
for src, name, srgb, comp in (
        ("player_knignt_basecolor.jpg", "T_HQKnight_BC", True, unreal.TextureCompressionSettings.TC_DEFAULT),
        ("player_knignt_normal.jpg", "T_HQKnight_N", False, unreal.TextureCompressionSettings.TC_NORMALMAP),
        ("player_knignt_metallic.jpg", "T_HQKnight_M", False, unreal.TextureCompressionSettings.TC_GRAYSCALE),
        ("player_knignt_roughness.jpg", "T_HQKnight_R", False, unreal.TextureCompressionSettings.TC_GRAYSCALE)):
    t_task = unreal.AssetImportTask()
    t_task.set_editor_property("filename", os.path.join(SRC, src))
    t_task.set_editor_property("destination_name", name)
    t_task.set_editor_property("destination_path", DEST); t_task.set_editor_property("automated", True)
    t_task.set_editor_property("replace_existing", True); t_task.set_editor_property("save", False)
    tools.import_asset_tasks([t_task])
    t = unreal.load_asset(f"{DEST}/{name}")
    t.set_editor_property("srgb", srgb); t.set_editor_property("compression_settings", comp)
    if name == "T_HQKnight_N":
        t.set_editor_property("flip_green_channel", True)   # Tripo (glTF) normal maps are OpenGL style
    eal.save_asset(f"{DEST}/{name}", only_if_is_dirty=False)
    tex[name] = t

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


bc = tparam("BaseColorMap", tex["T_HQKnight_BC"], unreal.MaterialSamplerType.SAMPLERTYPE_COLOR, -500, 0)
nm = tparam("NormalMap", tex["T_HQKnight_N"], unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL, -500, 250)
# non-sRGB grayscale textures need LINEAR_GRAYSCALE (plain GRAYSCALE = compile error -> grey default material)
mt = tparam("MetallicMap", tex["T_HQKnight_M"], unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE, -500, 500)
rg = tparam("RoughnessMap", tex["T_HQKnight_R"], unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE, -500, 750)
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
eal.save_asset(f"{DEST}/SKM_HQKnight", only_if_is_dirty=False)
eal.save_directory(DEST, only_if_is_dirty=False)   # also the new skeleton (not saved by the import task)
log("files: " + ", ".join(eal.list_assets(DEST, recursive=False)))
b =mesh.get_bounds()
sk = mesh.get_editor_property("skeleton")
log(f"mesh OK skeleton={sk.get_path_name() if sk else None} slots={len(mats)} "
    f"extent={b.box_extent} physics={mesh.get_editor_property('physics_asset')}")

if "executepythonscript" in unreal.SystemLibrary.get_command_line().lower():
    unreal.SystemLibrary.quit_editor()
