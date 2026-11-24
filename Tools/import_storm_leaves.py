# Tree boss phase-2 leaf storm: Export/SM_StormLeaf.fbx + Export/Textures/Enemies/T_StormLeaves.png
# (Export/Blender/scripts/props/gen_storm_leaves.py) -> /Game/Characters/Tree/Storm, material M_StormLeaf:
#   masked, two-sided, ISM; UV.x = (UV.x + PerInstanceCustomData[0]) / 3  -> 0 ginkgo (yellow), 1 maple (red), 2 brown
# Used by ATreeBoss::StormLeaves (NumCustomDataFloats = 1). Editor closed:
#   UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script="<abs/forward/slash>/Tools/import_storm_leaves.py" -unattended -nosplash -stdout
import os
import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
DEST = "/Game/Characters/Tree/Storm"
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda m: unreal.log_warning("STORMLEAF " + m)


def task_for(path):
    t = unreal.AssetImportTask()
    t.set_editor_property("filename", path); t.set_editor_property("destination_path", DEST)
    t.set_editor_property("automated", True); t.set_editor_property("replace_existing", True); t.set_editor_property("save", False)
    return t


tools.import_asset_tasks([task_for(os.path.join(PROJ, "Export", "Textures", "Enemies", "T_StormLeaves.png"))])
tex = unreal.load_asset(f"{DEST}/T_StormLeaves")
tex.set_editor_property("srgb", True)
eal.save_asset(f"{DEST}/T_StormLeaves", only_if_is_dirty=False)

mpath = f"{DEST}/M_StormLeaf"
if eal.does_asset_exist(mpath):
    eal.delete_asset(mpath)
m = tools.create_asset("M_StormLeaf", DEST, unreal.Material, unreal.MaterialFactoryNew())
m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
m.set_editor_property("two_sided", True)
m.set_editor_property("used_with_instanced_static_meshes", True)
E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
tc = E(unreal.MaterialExpressionTextureCoordinate, -1200, 0)
cd = E(unreal.MaterialExpressionPerInstanceCustomData, -1200, 150)
cd.set_editor_property("data_index", 0)
ap = E(unreal.MaterialExpressionAppendVector, -1000, 150)
mel.connect_material_expressions(cd, "", ap, "A")
zero = E(unreal.MaterialExpressionConstant, -1200, 300); zero.set_editor_property("r", 0.0)
mel.connect_material_expressions(zero, "", ap, "B")
add = E(unreal.MaterialExpressionAdd, -850, 50)
mel.connect_material_expressions(tc, "", add, "A"); mel.connect_material_expressions(ap, "", add, "B")
sc = E(unreal.MaterialExpressionConstant2Vector, -850, 200)
sc.set_editor_property("r", 1.0 / 3.0); sc.set_editor_property("g", 1.0)
uv = E(unreal.MaterialExpressionMultiply, -700, 50)
mel.connect_material_expressions(add, "", uv, "A"); mel.connect_material_expressions(sc, "", uv, "B")
t = E(unreal.MaterialExpressionTextureSampleParameter2D, -500, 0)
t.set_editor_property("parameter_name", "LeafAtlas"); t.set_editor_property("texture", tex)
mel.connect_material_expressions(uv, "", t, "UVs")
mel.connect_material_property(t, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
mel.connect_material_property(t, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
r = E(unreal.MaterialExpressionConstant, -300, 250); r.set_editor_property("r", 0.75)
mel.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
mel.recompile_material(m)
eal.save_asset(mpath, only_if_is_dirty=False)

meshp = f"{DEST}/SM_StormLeaf"
if eal.does_asset_exist(meshp):
    eal.delete_asset(meshp)
tools.import_asset_tasks([task_for(os.path.join(PROJ, "Export", "SM_StormLeaf.fbx"))])
mesh = unreal.load_asset(meshp)
for i in range(len(mesh.get_editor_property("static_materials"))):
    mesh.set_material(i, m)
bs = mesh.get_editor_property("body_setup")
if bs:
    bs.set_editor_property("agg_geom", unreal.KAggregateGeom())
eal.save_asset(meshp, only_if_is_dirty=False)
for p in eal.list_assets(DEST, recursive=False):           # material Interchange may have made next to the mesh
    a = unreal.load_asset(p)
    if isinstance(a, unreal.Material) and a.get_name() != "M_StormLeaf":
        eal.delete_asset(p.split(".")[0]); log(f"deleted leftover {p}")
b = mesh.get_bounding_box()
log(f"OK tex={bool(tex)} mesh bounds {b.min} {b.max}")
