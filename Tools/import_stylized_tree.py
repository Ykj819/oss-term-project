# Imports the stylized trees Export/SM_StylizedTree*.fbx (made in Export/Blender/StylizedTree.blend with
# Export/Blender/scripts/trees/gen_stylized_tree.py) into /Game/Environment/Trees.
# All trees share two vertex-colour materials, created only if missing (so tweaks made in the editor are kept).
# Colours are baked into the mesh's vertex colours. The FBX holds sRGB values, and UE hands the material exactly
# those sRGB values (FbxMesh.cpp decodes, the static mesh build re-encodes), so the material raises them to 2.2.
# Collision: UCX_<mesh>_00 = trunk only (the canopy does not block).
# Existing meshes are imported over (replace_existing), never deleted, so trees already placed in levels update.
# Run with the editor closed:
#   UnrealEditor-Cmd.exe <project>.uproject -run=pythonscript -script="<this file>" -unattended -nosplash -stdout
import os
import unreal

DEST = "/Game/Environment/Trees"
TREES = ["SM_StylizedTree", "SM_StylizedTree1", "SM_StylizedTree2", "SM_StylizedTree3"]
EXPORT_DIR = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()), "Export")

eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()


def get_or_make_material(name, two_sided, roughness):
    full = f"{DEST}/{name}"
    if eal.does_asset_exist(full):
        return unreal.load_asset(full)
    mat = tools.create_asset(name, DEST, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("two_sided", two_sided)
    mat.set_editor_property("used_with_instanced_static_meshes", True)  # foliage painting

    vc = mel.create_material_expression(mat, unreal.MaterialExpressionVertexColor, -700, 0)
    gamma = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -700, 200)
    gamma.set_editor_property("parameter_name", "VertexColorGamma")
    gamma.set_editor_property("default_value", 2.2)
    power = mel.create_material_expression(mat, unreal.MaterialExpressionPower, -450, 0)
    mel.connect_material_expressions(vc, "", power, "Base")
    mel.connect_material_expressions(gamma, "", power, "Exp")

    tint = mel.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -450, 200)
    tint.set_editor_property("parameter_name", "Tint")
    tint.set_editor_property("default_value", unreal.LinearColor(1.0, 1.0, 1.0, 1.0))
    mul = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -200, 0)
    mel.connect_material_expressions(power, "", mul, "A")
    mel.connect_material_expressions(tint, "", mul, "B")
    mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)

    rough = mel.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -200, 250)
    rough.set_editor_property("parameter_name", "Roughness")
    rough.set_editor_property("default_value", roughness)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)

    mel.recompile_material(mat)
    eal.save_asset(full, only_if_is_dirty=False)
    return mat


bark = get_or_make_material("M_StylizedTree_Bark", False, 0.9)
leaves = get_or_make_material("M_StylizedTree_Leaves", True, 0.7)


def safe(fn):
    try:
        return fn()
    except Exception as e:  # API names differ between engine versions; the check must not fail the import
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
    mats = mesh.get_editor_property("static_materials")
    for i, sm in enumerate(mats):
        slot = str(sm.get_editor_property("material_slot_name"))
        mesh.set_material(i, leaves if "Leaves" in slot else bark)
    eal.save_asset(path, only_if_is_dirty=False)

    convex = safe(lambda: len(mesh.get_editor_property("body_setup").get_editor_property("agg_geom").get_editor_property("convex_elems")))
    slots = [str(m.get_editor_property("material_slot_name")) + "=" +
             (m.get_editor_property("material_interface").get_name() if m.get_editor_property("material_interface") else "None")
             for m in mesh.get_editor_property("static_materials")]
    b = mesh.get_bounding_box()
    unreal.log_warning(f"TREE_IMPORT_OK {name} tris={safe(lambda: mesh.get_num_triangles(0))} convex={convex} slots={slots} "
                       f"size_cm=({b.max.x - b.min.x:.0f}, {b.max.y - b.min.y:.0f}, {b.max.z - b.min.z:.0f})")

# the importer also creates empty materials named after the Blender ones: remove them
for leftover in ("M_Tree_Bark", "M_Tree_Leaves"):
    p = f"{DEST}/{leftover}"
    if eal.does_asset_exist(p):
        eal.delete_asset(p)
