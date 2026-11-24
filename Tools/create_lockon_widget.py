# On-screen lock-on marker assets: /Game/UI/T_LockOnRing (white ring + dot + 4 ticks, Export/Textures/UI/T_LockOnRing.png,
# tinted pink by the widget) and /Game/UI/WBP_LockOn (Widget Blueprint, parent C++ ULockOnWidget; the C++ class builds
# the Image when the Designer is empty). Needs the C++ build with LockOnWidget first.
# Editor closed:
#   UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script="<abs/forward/slash>/Tools/create_lockon_widget.py" -unattended -nosplash -stdout
import os
import unreal

PROJ = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
DEST = "/Game/UI"
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda m: unreal.log_warning("LOCKONUI " + m)

task = unreal.AssetImportTask()
task.set_editor_property("filename", os.path.join(PROJ, "Export", "Textures", "UI", "T_LockOnRing.png"))
task.set_editor_property("destination_path", DEST); task.set_editor_property("automated", True)
task.set_editor_property("replace_existing", True); task.set_editor_property("save", False)
tools.import_asset_tasks([task])
tex = unreal.load_asset(f"{DEST}/T_LockOnRing")
tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON)
tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
eal.save_asset(f"{DEST}/T_LockOnRing", only_if_is_dirty=False)

path = f"{DEST}/WBP_LockOn"
if not eal.does_asset_exist(path):
    fac = unreal.WidgetBlueprintFactory()
    fac.set_editor_property("parent_class", unreal.LockOnWidget)
    bp = tools.create_asset("WBP_LockOn", DEST, unreal.WidgetBlueprint, fac)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    eal.save_asset(path, only_if_is_dirty=False)
bp = unreal.load_asset(path)
log(f"texture={bool(tex)} wbp={bool(bp)} class={bp.generated_class().get_name() if bp else None} is_lockon={unreal.get_default_object(bp.generated_class()).__class__.__name__ if bp else None}")
