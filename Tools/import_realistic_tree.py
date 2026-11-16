# Imports the realistic tree(s) Export/SM_RealisticTree*.fbx (made with Export/Blender/scripts/trees/gen_realistic_tree.py)
# into /Game/Environment/Trees and creates two vertex-colour materials (only if missing, so editor tweaks are kept):
#   M_RealisticTree_Bark   : default lit, BaseColor = VertexColor^2.2 * Tint
#   M_RealisticTree_Leaves : Two Sided Foliage (light shines through the leaves), two-sided,
#                            SubsurfaceColor = BaseColor * SubsurfaceTint
# Vertex colours: FBX holds sRGB values and UE passes them to the material unchanged -> ^2.2 (see CLAUDE.md).
# Leaves are real geometry (no masked alpha), so Nanite (on by default at import) handles the ~0.6M triangles well.
# Run with the editor closed:
#   UnrealEditor-Cmd.exe <project>.uproject -run=pythonscript -script="<this file>" -unattended -nosplash -stdout
import os
import unreal

DEST = "/Game/Environment/Trees"
TREES = ["SM_RealisticTree1"]
EXPORT_DIR = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()), "Export")

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()


def get_or_make_material(name, foliage, roughness):
    full = f"{DEST}/{name}"
    if eal.does_asset_exist(full):
        return unreal.load_asset(full)
    mat = tools.create_asset(name, DEST, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("used_with_instanced_static_meshes", True)  # foliage painting
    if foliage:
        mat.set_editor_property("two_sided", True)
        mat.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)

    vc = mel.create_material_expression(mat, unreal.MaterialExpressionVertexColor, -900, 0)
    gamma = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -900, 200)
    gamma.set_editor_property("parameter_name", "VertexColorGamma")
    gamma.set_editor_property("default_value", 2.2)
    power = mel.create_material_expression(mat, unreal.MaterialExpressionPower, -650, 0)
    mel.connect_material_expressions(vc, "", power, "Base")
    mel.connect_material_expressions(gamma, "", power, "Exp")

    tint = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -650, 200)
    tint.set_editor_property("parameter_name", "Tint")
    tint.set_editor_property("default_value", unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
    base = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -400, 0)
    mel.connect_material_expressions(power, "", base, "A")
    mel.connect_material_expressions(tint, "", base, "B")
    mel.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)

    rough = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -400, 250)
    rough.set_editor_property("parameter_name", "Roughness")
    rough.set_editor_property("default_value", roughness)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)

    if foliage:
        sst = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -400, 400)
        sst.set_editor_property("parameter_name", "SubsurfaceTint")
        sst.set_editor_property("default_value", unreal.LinearColor(0.9, 1.1, 0.5, 1.0))
        ss = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -150, 400)
        mel.connect_material_expressions(base, "", ss, "A")
        mel.connect_material_expressions(sst, "", ss, "B")
        mel.connect_material_property(ss, "", unreal.MaterialProperty.MP_SUBSURFACE_COLOR)

    mel.recompile_material(mat)
    eal.save_asset(full, only_if_is_dirty=False)
    return mat


bark = get_or_make_material("M_RealisticTree_Bark", False, 0.95)
leaves = get_or_make_material("M_RealisticTree_Leaves", True, 0.6)


def safe(fn):
    try:
        return fn()
    except Exception as e:
        return f"n/a({e.__class__.__name__})"


for name in TREES:
    fbx = os.path.join(EXPORT_DIR, name + ".fbx")
    if not os.path.exists(fbx):
        unreal.log_warning(f"TREE_IMPORT skip {name}: no {fbx}")
        continue
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", fbx)
    task.set_editor_property("destination_path", DEST)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)
    tools.import_asset_tasks([task])

    path = f"{DEST}/{name}"
    mesh = unreal.load_asset(path)
    if not mesh:
        unreal.log_warning(f"TREE_IMPORT FAILED {name}")
        continue
    for i, sm in enumerate(mesh.get_editor_property("static_materials")):
        slot = str(sm.get_editor_property("material_slot_name"))
        mesh.set_material(i, leaves if "Leaves" in slot else bark)
    eal.save_asset(path, only_if_is_dirty=False)

    convex = safe(lambda: len(mesh.get_editor_property("body_setup").get_editor_property("agg_geom").get_editor_property("convex_elems")))
    nanite = safe(lambda: mesh.get_editor_property("nanite_settings").get_editor_property("enabled"))
    slots = [str(m.get_editor_property("material_slot_name")) + "=" +
             (m.get_editor_property("material_interface").get_name() if m.get_editor_property("material_interface") else "None")
             for m in mesh.get_editor_property("static_materials")]
    b = mesh.get_bounding_box()
    unreal.log_warning(f"TREE_IMPORT_OK {name} nanite={nanite} convex={convex} slots={slots} "
                       f"size_cm=({b.max.x - b.min.x:.0f}, {b.max.y - b.min.y:.0f}, {b.max.z - b.min.z:.0f})")

# the importer also creates empty materials named after the Blender ones: remove them
for leftover in ("M_Real_Bark", "M_Real_Leaves"):
    p = f"{DEST}/{leftover}"
    if eal.does_asset_exist(p):
        eal.delete_asset(p)
