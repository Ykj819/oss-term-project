# Set "Used with Nanite" on the environment materials that sit on Nanite meshes and re-save them
# (UE warns "material is missing the Nanite usage flag" and may render it wrong outside the editor otherwise).
# Run with the editor closed, or in the open editor via Tools -> Execute Python Script.
import unreal

PATHS = ["/Game/Environment/Materials/M_Stylized_Cloud", "/Game/Environment/Materials/M_Stylized_Prop",
         "/Game/Environment/Materials/M_Stylized_Foliage", "/Game/Environment/Materials/M_Stylized_Surface",
         "/Game/Environment/Trees/M_StylizedTree_Bark", "/Game/Environment/Trees/M_StylizedTree_Leaves",
         "/Game/Environment/Trees/M_RealisticTree_Bark", "/Game/Environment/Trees/M_RealisticTree_Leaves"]
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary

for p in PATHS:
    m = unreal.load_asset(p)
    if not m:
        unreal.log_warning(f"NANITEFLAG missing {p}"); continue
    before = m.get_editor_property("used_with_nanite")
    if not before:
        m.set_editor_property("used_with_nanite", True)
        mel.recompile_material(m)
    eal.save_asset(p, only_if_is_dirty=False)
    unreal.log_warning(f"NANITEFLAG {p.rsplit('/', 1)[1]} {before} -> {m.get_editor_property('used_with_nanite')}")
