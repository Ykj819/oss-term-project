# Import the player's wooden sword (Export/SM_WoodSword.fbx, made by Export/Blender/scripts/props/gen_wood_sword.py)
#   -> /Game/Characters/PlayerKnight/Weapon/SM_WoodSword (Nanite off, no collision) + material M_WoodSword
#   (BaseColor = VertexColor^2.2 * Tint, Roughness param; no camera-occlusion dither: it is held at the player).
# Used by AOss_TermProjectCharacter::WeaponMesh (StickMesh component).
# Headless:  UnrealEditor-Cmd.exe <uproject> -ExecutePythonScript="<this file>" -unattended -nullrhi -nosplash -stdout
import os
import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
DEST = "/Game/Characters/PlayerKnight/Weapon"
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda m: unreal.log_warning("WOODSWORD " + m)

# ---- material (deleted + recreated: rebuilding a graph in place can crash headless runs)
MAT = f"{DEST}/M_WoodSword"
if eal.does_asset_exist(f"{DEST}/SM_WoodSword"):
    eal.delete_asset(f"{DEST}/SM_WoodSword")
if eal.does_asset_exist(MAT):
    eal.delete_asset(MAT)
mat = tools.create_asset("M_WoodSword", DEST, unreal.Material, unreal.MaterialFactoryNew())
E = lambda cls, x, y: mel.create_material_expression(mat, cls, x, y)


def scalar(n, v, x, y):
    e = E(unreal.MaterialExpressionScalarParameter, x, y)
    e.set_editor_property("parameter_name", n); e.set_editor_property("default_value", v); return e


vc = E(unreal.MaterialExpressionVertexColor, -900, 0)
pw = E(unreal.MaterialExpressionPower, -650, 0); pw.set_editor_property("const_exponent", 2.2)
mel.connect_material_expressions(vc, "", pw, "Base")
tint = E(unreal.MaterialExpressionVectorParameter, -650, 200)
tint.set_editor_property("parameter_name", "Tint"); tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
bm = E(unreal.MaterialExpressionMultiply, -400, 0)
mel.connect_material_expressions(pw, "", bm, "A"); mel.connect_material_expressions(tint, "", bm, "B")
mel.connect_material_property(bm, "", unreal.MaterialProperty.MP_BASE_COLOR)
mel.connect_material_property(scalar("Roughness", 0.72, -400, 300), "", unreal.MaterialProperty.MP_ROUGHNESS)
mel.recompile_material(mat); eal.save_asset(MAT, only_if_is_dirty=False)

# ---- mesh
task = unreal.AssetImportTask()
task.set_editor_property("filename", os.path.join(PROJ, "Export", "SM_WoodSword.fbx"))
task.set_editor_property("destination_path", DEST); task.set_editor_property("automated", True)
task.set_editor_property("replace_existing", True); task.set_editor_property("save", False)
tools.import_asset_tasks([task])
path = f"{DEST}/SM_WoodSword"
mesh = unreal.load_asset(path)
if not mesh:
    log("FAILED import")
    raise SystemExit
for i in range(len(mesh.get_editor_property("static_materials"))):
    mesh.set_material(i, mat)
ns = mesh.get_editor_property("nanite_settings"); ns.set_editor_property("enabled", False)
mesh.set_editor_property("nanite_settings", ns)
mesh.get_editor_property("body_setup").set_editor_property("agg_geom", unreal.KAggregateGeom())   # no collision
eal.save_asset(path, only_if_is_dirty=False)
for a in eal.list_assets(DEST, recursive=False):                    # material Interchange may have made from the FBX
    n = a.split(".")[-1]
    if n not in ("SM_WoodSword", "M_WoodSword"):
        eal.delete_asset(a); log("removed leftover " + n)
b = mesh.get_bounding_box()
log(f"OK size_cm=({b.max.x - b.min.x:.1f},{b.max.y - b.min.y:.1f},{b.max.z - b.min.z:.1f}) z=({b.min.z:.1f}..{b.max.z:.1f})")

if "executepythonscript" in unreal.SystemLibrary.get_command_line().lower():
    unreal.SystemLibrary.quit_editor()
