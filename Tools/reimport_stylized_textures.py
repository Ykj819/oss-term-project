# Re-import only some stylized surface texture sets (Export/Textures/Stylized/T_Stylized_<Name>_{BC,N,ARH}.png)
# into /Game/Environment/Textures/Stylized, keeping the same settings as Tools/import_stylized_batch.py.
# Edit SETS below. Works in the commandlet (editor closed) or in the open editor via Tools -> Execute Python Script.
import os
import unreal

SETS = ["Soil", "Stone", "Rock"]
PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
SRC = os.path.join(PROJ, "Export", "Textures", "Stylized")
TEXD = "/Game/Environment/Textures/Stylized"
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()

for s in SETS:
    for suffix, srgb, comp in (("BC", True, unreal.TextureCompressionSettings.TC_DEFAULT),
                               ("N", False, unreal.TextureCompressionSettings.TC_NORMALMAP),
                               ("ARH", False, unreal.TextureCompressionSettings.TC_MASKS)):
        name = f"T_Stylized_{s}_{suffix}"
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", os.path.join(SRC, name + ".png"))
        task.set_editor_property("destination_path", TEXD); task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", True); task.set_editor_property("save", False)
        tools.import_asset_tasks([task])
        t = unreal.load_asset(f"{TEXD}/{name}")
        if not t:
            unreal.log_warning(f"RETEX FAILED {name}"); continue
        t.set_editor_property("srgb", srgb); t.set_editor_property("compression_settings", comp)
        if suffix == "N":
            t.set_editor_property("flip_green_channel", False)
        eal.save_asset(f"{TEXD}/{name}", only_if_is_dirty=False)
        unreal.log_warning(f"RETEX OK {name}")
