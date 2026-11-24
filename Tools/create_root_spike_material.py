# /Game/Characters/Tree/Materials/M_RootSpike: the tree boss's own bark (T_Tree_BC / T_Tree_N, baked by the Tree_Rig.blend
# pipeline) for ARootSpike's engine cones. The texture is the boss's UV atlas, so the cone's 0..1 UVs are squeezed into a
# bark-only window of it (vertical grain, bottom-left of the atlas): UV' = BarkOffset + UV * BarkSize. Param Tint.
# Editor closed:
#   UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script="<abs/forward/slash>/Tools/create_root_spike_material.py" -unattended -nosplash -stdout
import unreal

PATH, NAME = "/Game/Characters/Tree/Materials", "M_RootSpike"
BARK_OFFSET, BARK_SIZE = (0.04, 0.66), (0.17, 0.20)     # atlas window (u, v from the image's top-left)
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary
bc = unreal.load_asset("/Game/Characters/Tree/Textures/T_Tree_BC")
nm = unreal.load_asset("/Game/Characters/Tree/Textures/T_Tree_N")
if eal.does_asset_exist(f"{PATH}/{NAME}"):
    eal.delete_asset(f"{PATH}/{NAME}")
m = unreal.AssetToolsHelpers.get_asset_tools().create_asset(NAME, PATH, unreal.Material, unreal.MaterialFactoryNew())
E = lambda cls, x, y: mel.create_material_expression(m, cls, x, y)
tc = E(unreal.MaterialExpressionTextureCoordinate, -1200, 0)
size = E(unreal.MaterialExpressionConstant2Vector, -1200, 150)
size.set_editor_property("r", BARK_SIZE[0]); size.set_editor_property("g", BARK_SIZE[1])
off = E(unreal.MaterialExpressionConstant2Vector, -1200, 300)
off.set_editor_property("r", BARK_OFFSET[0]); off.set_editor_property("g", BARK_OFFSET[1])
mul = E(unreal.MaterialExpressionMultiply, -1000, 50)
mel.connect_material_expressions(tc, "", mul, "A"); mel.connect_material_expressions(size, "", mul, "B")
uv = E(unreal.MaterialExpressionAdd, -850, 50)
mel.connect_material_expressions(mul, "", uv, "A"); mel.connect_material_expressions(off, "", uv, "B")
t = E(unreal.MaterialExpressionTextureSampleParameter2D, -650, 0)
t.set_editor_property("parameter_name", "BarkMap"); t.set_editor_property("texture", bc)
mel.connect_material_expressions(uv, "", t, "UVs")
tint = E(unreal.MaterialExpressionVectorParameter, -650, 250)
tint.set_editor_property("parameter_name", "Tint"); tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
b = E(unreal.MaterialExpressionMultiply, -400, 0)
mel.connect_material_expressions(t, "RGB", b, "A"); mel.connect_material_expressions(tint, "", b, "B")
mel.connect_material_property(b, "", unreal.MaterialProperty.MP_BASE_COLOR)
# Glow (default 0): the warning disc pulses its bark orange before the spikes come up (ARootSpike sets it)
glow = E(unreal.MaterialExpressionScalarParameter, -650, 650)
glow.set_editor_property("parameter_name", "Glow"); glow.set_editor_property("default_value", 0.0)
gcol = E(unreal.MaterialExpressionConstant3Vector, -650, 750); gcol.set_editor_property("constant", unreal.LinearColor(1.0, 0.35, 0.05, 1))
gm = E(unreal.MaterialExpressionMultiply, -450, 650)
mel.connect_material_expressions(t, "RGB", gm, "A"); mel.connect_material_expressions(gcol, "", gm, "B")
em = E(unreal.MaterialExpressionMultiply, -300, 650)
mel.connect_material_expressions(gm, "", em, "A"); mel.connect_material_expressions(glow, "", em, "B")
mel.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
n = E(unreal.MaterialExpressionTextureSampleParameter2D, -650, 450)
n.set_editor_property("parameter_name", "NormalMap"); n.set_editor_property("texture", nm)
n.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
mel.connect_material_expressions(uv, "", n, "UVs")
mel.connect_material_property(n, "RGB", unreal.MaterialProperty.MP_NORMAL)
r = E(unreal.MaterialExpressionConstant, -400, 300); r.set_editor_property("r", 0.85)
mel.connect_material_property(r, "", unreal.MaterialProperty.MP_ROUGHNESS)
mel.recompile_material(m)
eal.save_asset(f"{PATH}/{NAME}", only_if_is_dirty=False)
unreal.log_warning(f"SPIKEMAT OK bc={bool(bc)} n={bool(nm)} nexpr={mel.get_num_material_expressions(m)}")
