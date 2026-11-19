# Print which anim blueprint / blend space the player uses and the blend space samples.
# Headless: UnrealEditor-Cmd.exe <uproject> -ExecutePythonScript="<this file>" -unattended -nullrhi -nosplash -stdout
import unreal
log = lambda m: unreal.log_warning("LOCO " + str(m))
bp = unreal.load_asset("/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter")
cdo = unreal.get_default_object(bp.generated_class())
mesh = cdo.get_editor_property("mesh")
log(f"anim class = {mesh.get_editor_property('anim_class')}  mode={mesh.get_editor_property('animation_mode')}")
log(f"parent class = {bp.get_editor_property('parent_class')}")
for path in ("/Game/Characters/Mannequins/Anims/Unarmed/BS_Idle_Walk_Run",):
    bs = unreal.load_asset(path)
    log(f"{path} class={bs.get_class().get_name()}")
    try:
        for s in bs.get_editor_property("sample_data"):
            log(f"  sample {s.get_editor_property('animation').get_path_name()} @ {s.get_editor_property('sample_value')}"
                f" rate={s.get_editor_property('rate_scale')}")
    except Exception as e:
        log(f"  sample_data error {e}")
    try:
        for p in bs.get_editor_property("blend_parameters"):
            log(f"  axis {p.get_editor_property('display_name')} {p.get_editor_property('min')}..{p.get_editor_property('max')}")
    except Exception as e:
        log(f"  axis error {e}")
reg = unreal.AssetRegistryHelpers.get_asset_registry()
opts = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True)
for pkg in ("/Game/Characters/Mannequins/Anims/Unarmed/BS_Idle_Walk_Run", "/Game/Characters/Mannequins/Anims/Unarmed/Walk/MF_Unarmed_Walk_Fwd",
            "/Game/Characters/Mannequins/Anims/Unarmed/Jog/MF_Unarmed_Jog_Fwd"):
    refs = reg.get_referencers(pkg, opts) or []
    log(f"referencers of {pkg}: {[str(r) for r in refs]}")
if "executepythonscript" in unreal.SystemLibrary.get_command_line().lower():
    unreal.SystemLibrary.quit_editor()
