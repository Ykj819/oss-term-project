# Scatter the stylized clouds (/Game/Environment/Sky) over a map, based on the landscape bounds.
#   - sky clouds above the landscape (Small/Medium/Long/Cumulus mix), random yaw/scale, 60-130 m above the top
#   - HorizonBand ring far outside the landscape, concave side facing the centre
#   - Cast Shadow off, not spatially loaded (World Partition would stream far clouds out), folder "Clouds",
#     tag "AutoCloud". Re-running removes the previous AutoCloud actors first.
# Editor closed: commandlet (edits MAP). Editor open: Tools -> Execute Python Script (uses the open level).
import math, random
import unreal

MAP = "/Game/ThirdPerson/Lvl_ThirdPerson"
SKY = "/Game/Environment/Sky"
SEED = 7
TAG = "AutoCloud"
log = lambda m: unreal.log_warning("PLACECLOUD " + m)

world = unreal.EditorLevelLibrary.get_editor_world()
# headless run (editor closed):
#   UnrealEditor-Cmd.exe <uproject> -ExecutePythonScript="<this file>" -unattended -nullrhi -nosplash -stdout
# (a -run=pythonscript commandlet cannot spawn actors). Opens MAP, saves, quits.
_cmd = unreal.SystemLibrary.get_command_line().lower()
is_cmdlet = "executepythonscript" in _cmd or "-run=pythonscript" in _cmd
if is_cmdlet and (world is None or world.get_path_name().split(".")[0] != MAP):
    world = unreal.EditorLoadingAndSavingUtils.load_map(MAP) or unreal.EditorLevelLibrary.get_editor_world()
log(f"world={world.get_name() if world else None} commandlet={is_cmdlet}")

# remove previous auto clouds
for a in unreal.GameplayStatics.get_all_actors_with_tag(world, TAG):
    a.destroy_actor()

# landscape bounds from World Partition actor descriptors (works with unloaded cells), else loaded actors
lo = None; hi = None
try:
    for d in unreal.WorldPartitionBlueprintLibrary.get_actor_descs():
        if "Landscape" in str(d.get_editor_property("native_class")):
            b = d.get_editor_property("bounds")
            mn, mx = b.min, b.max
            if mx.x - mn.x <= 0:
                continue
            lo = mn if lo is None else unreal.Vector(min(lo.x, mn.x), min(lo.y, mn.y), min(lo.z, mn.z))
            hi = mx if hi is None else unreal.Vector(max(hi.x, mx.x), max(hi.y, mx.y), max(hi.z, mx.z))
except Exception as e:
    log(f"(warn) actor descs: {e}")
if lo is None:
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.LandscapeProxy):
        o, e = a.get_actor_bounds(False)
        mn = o - e; mx = o + e
        lo = mn if lo is None else unreal.Vector(min(lo.x, mn.x), min(lo.y, mn.y), min(lo.z, mn.z))
        hi = mx if hi is None else unreal.Vector(max(hi.x, mx.x), max(hi.y, mx.y), max(hi.z, mx.z))
if lo is None:
    lo = unreal.Vector(-50000, -50000, 0); hi = unreal.Vector(50000, 50000, 0)
    log("(warn) no landscape found, using a 1 km area at the origin")
cx, cy = (lo.x + hi.x) / 2, (lo.y + hi.y) / 2
ex, ey = (hi.x - lo.x) / 2, (hi.y - lo.y) / 2
top = hi.z
log(f"landscape centre=({cx:.0f},{cy:.0f}) half=({ex:.0f},{ey:.0f}) top={top:.0f}")

meshes = {n: unreal.load_asset(f"{SKY}/SM_Cloud_{n}") for n in ["Small", "Medium", "Long", "Cumulus", "HorizonBand"]}
rng = random.Random(SEED)


def spawn(name, loc, yaw, scale):
    a = unreal.EditorLevelLibrary.spawn_actor_from_object(meshes[name], loc, unreal.Rotator(0, 0, yaw))
    if a is None:
        raise RuntimeError("spawn failed (a -run=pythonscript commandlet cannot spawn; use -ExecutePythonScript)")
    a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    smc = a.get_editor_property("static_mesh_component")
    smc.set_editor_property("cast_shadow", False)
    for p, v in (("is_spatially_loaded", False),):
        try:
            a.set_editor_property(p, v)
        except Exception as e:
            log(f"(warn) {p}: {e}")
    a.set_folder_path("Clouds")
    a.set_actor_label(f"Cloud_{name}_{len(placed):02d}")
    a.tags = [TAG]
    placed.append(a)


placed = []
# sky clouds: area 1.4x the landscape, about one cloud per 120 m x 120 m, at least 10, at most 45
ax, ay = ex * 1.4, ey * 1.4
count = int(max(10, min(45, (4 * ax * ay) / (12000.0 ** 2))))
kinds = ["Small"] * 35 + ["Medium"] * 30 + ["Long"] * 20 + ["Cumulus"] * 15
pts = []
for i in range(count):
    for _ in range(30):   # keep clouds apart (poisson-ish)
        x = cx + rng.uniform(-ax, ax); y = cy + rng.uniform(-ay, ay)
        if all((x - px) ** 2 + (y - py) ** 2 > (min(ax, ay) * 0.22) ** 2 for px, py in pts):
            break
    pts.append((x, y))
    k = rng.choice(kinds)
    z = top + rng.uniform(6000, 13000) + (2000 if k == "Cumulus" else 0)
    spawn(k, unreal.Vector(x, y, z), rng.uniform(0, 360), rng.uniform(0.8, 1.6))

# horizon ring
R = max(ex, ey) * 1.25 + 25000
nb = 8
for i in range(nb):
    a = 2 * math.pi * i / nb + rng.uniform(-0.12, 0.12)
    loc = unreal.Vector(cx + R * math.cos(a), cy + R * math.sin(a), top + rng.uniform(1500, 4000))
    spawn("HorizonBand", loc, math.degrees(a) - 90 + rng.uniform(-8, 8), rng.uniform(1.4, 2.0))

log(f"placed {len(placed)} clouds ({count} sky + {nb} horizon), ring radius {R / 100:.0f} m")

if is_cmdlet:
    ok = unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    log(f"saved dirty packages: {ok}")
    if "executepythonscript" in _cmd:
        unreal.SystemLibrary.quit_editor()
