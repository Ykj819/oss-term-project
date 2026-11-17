# Grass and flower meshes: no collision at all (the player walks through them).
# The importer auto-generates a convex hull; EditorStaticMeshLibrary.remove_collisions does nothing in a commandlet,
# so the body setup's geometry is cleared directly and its default collision profile set to NoCollision.
# Run with the editor closed:
#   UnrealEditor-Cmd.exe <project>.uproject -run=pythonscript -script="<this file>" -unattended -nosplash -stdout
import unreal

eal = unreal.EditorAssetLibrary
PATHS = ["/Game/Environment/Foliage/SM_StylizedGrass"] + [
    f"/Game/Environment/Foliage/Flowers/SM_Flower_{n}" for n in
    ["Daisy", "Tulip", "Lavender", "Marigold", "BabysBreath", "LilyOfTheValley", "Fireweed"]]

for p in PATHS:
    mesh = unreal.load_asset(p)
    if not mesh:
        unreal.log_warning(f"NOCOL missing {p}"); continue
    bs = mesh.get_editor_property("body_setup")
    notes = []
    try:
        bs.set_editor_property("agg_geom", unreal.KAggregateGeom()); notes.append("geom cleared")
    except Exception as e:
        notes.append(f"geom: {e}")
    try:
        bi = bs.get_editor_property("default_instance")
        bi.set_editor_property("collision_profile_name", "NoCollision")
        bi.set_editor_property("collision_enabled", unreal.CollisionEnabled.NO_COLLISION)
        bs.set_editor_property("default_instance", bi); notes.append("profile NoCollision")
    except Exception as e:
        notes.append(f"profile: {e}")
    try:
        bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
    except Exception as e:
        notes.append(f"trace: {e}")
    try:
        mesh.set_editor_property("customized_collision", True)
    except Exception:
        pass
    eal.save_asset(p, only_if_is_dirty=False)
    n = len(bs.get_editor_property("agg_geom").get_editor_property("convex_elems"))
    prof = bs.get_editor_property("default_instance").get_editor_property("collision_profile_name")
    unreal.log_warning(f"NOCOL {p.rsplit('/', 1)[1]} convex={n} profile={prof} {notes}")
