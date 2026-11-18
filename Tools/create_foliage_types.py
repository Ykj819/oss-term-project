# Foliage Type assets (<Mesh>_FoliageType, next to each mesh, same naming as the user's tree foliage types) for
# flowers, grass (tufts + 2 m patch), stones and rocks, with paint settings tuned per kind.
# Existing assets are updated in place (settings re-applied).
# Run with the editor closed, or in the open editor via Tools -> Execute Python Script:
#   UnrealEditor-Cmd.exe <project>.uproject -run=pythonscript -script="<this file>" -unattended -nosplash -stdout
import unreal

eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
log = lambda m: unreal.log_warning("FTYPE " + m)
FI = unreal.FloatInterval
II = unreal.Int32Interval

# kind: density (/1000x1000 uu = per 10 m x 10 m), radius cm, scale, align, max align angle, random pitch,
#       z offset cm, ground slope deg, collision, cast shadow, cull distance cm (0,0 = never)
KINDS = {
    "tuft":   dict(density=300.0, radius=0.0, scale=(0.8, 1.3), align=True, align_max=25.0, pitch=0.0,
                   z=(-3.0, 0.0), slope=(0.0, 40.0), collide=False, shadow=False, cull=(0, 5000)),
    "patch":  dict(density=25.0, radius=150.0, scale=(0.9, 1.1), align=True, align_max=20.0, pitch=0.0,
                   z=(-3.0, 0.0), slope=(0.0, 35.0), collide=False, shadow=False, cull=(0, 6000)),
    "flower": dict(density=8.0, radius=25.0, scale=(0.8, 1.25), align=True, align_max=15.0, pitch=0.0,
                   z=(-2.0, 0.0), slope=(0.0, 35.0), collide=False, shadow=True, cull=(0, 6000)),
    "stone":  dict(density=4.0, radius=40.0, scale=(0.6, 1.4), align=True, align_max=30.0, pitch=10.0,
                   z=(-5.0, -1.0), slope=(0.0, 45.0), collide=False, shadow=True, cull=(0, 8000)),
    "rock":   dict(density=0.3, radius=400.0, scale=(0.7, 1.4), align=True, align_max=15.0, pitch=8.0,
                   z=(-30.0, -10.0), slope=(0.0, 60.0), collide=True, shadow=True, cull=(0, 0)),
}

MESHES = (
    [("/Game/Environment/Foliage", f"SM_GrassTuft{i}", "tuft") for i in (1, 2, 3)] +
    [("/Game/Environment/Foliage", "SM_StylizedGrass", "patch")] +
    [("/Game/Environment/Foliage/Flowers", f"SM_Flower_{n}", "flower") for n in
     ["Daisy", "Tulip", "Lavender", "Marigold", "BabysBreath", "LilyOfTheValley", "Fireweed"]] +
    [("/Game/Environment/Rocks", f"SM_StylizedStone{i}", "stone") for i in (1, 2, 3)] +
    [("/Game/Environment/Rocks", f"SM_StylizedRock{i}", "rock") for i in (1, 2, 3)]
)


def setp(obj, prop, val):
    try:
        obj.set_editor_property(prop, val)
    except Exception as e:
        log(f"  (warn) {prop}: {e}")


for folder, mesh_name, kind in MESHES:
    mesh = unreal.load_asset(f"{folder}/{mesh_name}")
    if not mesh:
        log(f"MISSING mesh {mesh_name}"); continue
    name = f"{mesh_name}_FoliageType"; path = f"{folder}/{name}"
    if eal.does_asset_exist(path):
        ft = unreal.load_asset(path)
    else:
        ft = tools.create_asset(name, folder, unreal.FoliageType_InstancedStaticMesh,
                                unreal.FoliageType_InstancedStaticMeshFactory())
    if not ft:
        log(f"FAILED create {name}"); continue
    k = KINDS[kind]
    setp(ft, "mesh", mesh)
    setp(ft, "density", k["density"]); setp(ft, "radius", k["radius"])
    setp(ft, "scaling", unreal.FoliageScaling.UNIFORM)
    setp(ft, "scale_x", FI(k["scale"][0], k["scale"][1]))
    setp(ft, "align_to_normal", k["align"]); setp(ft, "align_max_angle", k["align_max"])
    setp(ft, "random_yaw", True); setp(ft, "random_pitch_angle", k["pitch"])
    setp(ft, "z_offset", FI(*k["z"])); setp(ft, "ground_slope_angle", FI(*k["slope"]))
    setp(ft, "cast_shadow", k["shadow"]); setp(ft, "cast_dynamic_shadow", k["shadow"])
    setp(ft, "cull_distance", II(*k["cull"]))
    bi = ft.get_editor_property("body_instance")
    bi.set_editor_property("collision_profile_name", "BlockAll" if k["collide"] else "NoCollision")
    bi.set_editor_property("collision_enabled",
                           unreal.CollisionEnabled.QUERY_AND_PHYSICS if k["collide"] else unreal.CollisionEnabled.NO_COLLISION)
    setp(ft, "body_instance", bi)
    eal.save_asset(path, only_if_is_dirty=False)
    got = ft.get_editor_property("mesh")
    log(f"OK {name} kind={kind} mesh={got.get_name() if got else None} density={ft.get_editor_property('density')} "
        f"profile={ft.get_editor_property('body_instance').get_editor_property('collision_profile_name')}")
