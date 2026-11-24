# Death smoke flipbook v2 (2026-11-23): a REAL smoke simulation (Mantaflow) instead of the noise puff of
# gen_death_smoke.py. A sphere emits smoke for 3 frames with a strong outward (normal) velocity -> the burst rolls
# out in vortices, rises a little and dissolves. 64 frames rendered in Cycles (front, transparent film, white smoke lit
# from above) and packed 8 x 8 (frame 0 top-left, row by row) into Export/Textures/Effects/T_DeathSmoke.png
# (RGB = lit smoke, A = coverage). Headless:  blender -b --factory-startup --python <this file>
# UE: Tools/import_death_smoke.py (GRID = 8) -> M_DeathSmoke. Saves Export/Blender/DeathSmokeSim.blend.
import bpy, os, math, shutil, sys
import numpy as np

ROOT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject"
OUT = os.path.join(ROOT, r"Export\Textures\Effects\T_DeathSmoke.png")
CACHE = os.path.join(ROOT, r"Export\Blender\cache_death_smoke")
CELL, GRID = 256, 8
FRAMES = GRID * GRID
START = 3                       # first rendered sim frame (frame 1 = the emitter's first step)

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 1, START + FRAMES

# ---- domain (5.6 m cube, open borders; big enough that the burst thins out before it reaches the sides)
bpy.ops.mesh.primitive_cube_add(size=5.6, location=(0, 0, 0.7))
dom = bpy.context.active_object; dom.name = 'SmokeDomain'
m = dom.modifiers.new('Fluid', 'FLUID'); m.fluid_type = 'DOMAIN'
d = m.domain_settings
d.domain_type = 'GAS'
d.resolution_max = 168
d.use_collision_border_front = d.use_collision_border_back = False
d.use_collision_border_right = d.use_collision_border_left = False
d.use_collision_border_top = d.use_collision_border_bottom = False
d.alpha = 0.25                  # gentle rise
d.beta = 0.0
d.vorticity = 0.7              # curly billows
d.use_dissolve_smoke = True; d.dissolve_speed = 20; d.use_dissolve_smoke_log = True
d.cache_directory = CACHE
d.cache_type = 'ALL'
d.cache_frame_start = 1; d.cache_frame_end = START + FRAMES
# smaller cache files (was ~6.5 GB): Blosc compression + half floats (each set on its own: the depth enum is dynamic)
for prop, val in (('openvdb_cache_compress_type', 'BLOSC'), ('openvdb_data_depth', '16')):
    try:
        setattr(d, prop, val)
    except Exception as e:
        print('SMOKE cache option not set:', prop, e)
d.use_adaptive_domain = False
try:
    d.use_noise = True; d.noise_scale = 2; d.noise_strength = 1.2
except Exception:
    pass

# ---- emitter: sphere that puffs for 3 frames, smoke shot outward along its normals
bpy.ops.mesh.primitive_ico_sphere_add(radius=0.35, subdivisions=3, location=(0, 0, 0))
src = bpy.context.active_object; src.name = 'SmokeBurst'
f = src.modifiers.new('Fluid', 'FLUID'); f.fluid_type = 'FLOW'
fs = f.flow_settings
fs.flow_type = 'SMOKE'; fs.flow_behavior = 'INFLOW'; fs.flow_source = 'MESH'
fs.surface_distance = 0.25
fs.use_initial_velocity = True; fs.velocity_normal = 3.0; fs.velocity_factor = 1.6   # the growing sphere's own motion pushes the smoke out
fs.density = 1.0; fs.temperature = 0.6
fs.smoke_color = (1, 1, 1)
# the sphere balloons out over 8 frames while emitting (outward burst), then stops emitting
src.scale = (0.3, 0.3, 0.3); src.keyframe_insert('scale', frame=1)
src.scale = (2.4, 2.4, 2.1); src.keyframe_insert('scale', frame=8)
for fc in src.animation_data.action.fcurves if hasattr(src.animation_data.action, 'fcurves') else []:
    for kp in fc.keyframe_points:
        kp.interpolation = 'QUAD'; kp.easing = 'EASE_OUT'
fs.use_inflow = True; fs.keyframe_insert('use_inflow', frame=8)
fs.use_inflow = False; fs.keyframe_insert('use_inflow', frame=9)
src.hide_render = True
# lumpy emission: cloud noise texture modulates the emitted density (cauliflower billows instead of a smooth ball)
tx = bpy.data.textures.new('SmokeLumps', 'CLOUDS'); tx.noise_scale = 0.28; tx.noise_depth = 3; tx.contrast = 1.6
fs.use_texture = True; fs.noise_texture = tx; fs.texture_map_type = 'AUTO'; fs.texture_size = 1.0
# swirling air around the burst
bpy.ops.object.effector_add(type='TURBULENCE', location=(0, 0, 0.3))
turb = bpy.context.active_object; turb.field.strength = 7.0; turb.field.size = 0.45; turb.field.flow = 0.6

if os.path.isdir(CACHE):
    shutil.rmtree(CACHE, ignore_errors=True)
bpy.context.view_layer.objects.active = dom
for o in bpy.context.view_layer.objects:
    o.select_set(o == dom)
with bpy.context.temp_override(object=dom, active_object=dom, selected_objects=[dom]):
    bpy.ops.fluid.bake_all()
print('SMOKE baked')

# ---- render setup
sc.render.engine = 'CYCLES'
sc.cycles.samples = 96
try:
    sc.cycles.use_denoising = True
except Exception:
    pass
sc.cycles.volume_bounces = 2
sc.cycles.volume_step_rate = 1.0
sc.render.film_transparent = True
sc.render.resolution_x = sc.render.resolution_y = CELL
sc.view_settings.view_transform = 'Standard'
mat = bpy.data.materials.new('M_SmokeSim'); mat.use_nodes = True
nt = mat.node_tree; nt.nodes.clear()
out = nt.nodes.new('ShaderNodeOutputMaterial'); vol = nt.nodes.new('ShaderNodeVolumePrincipled')
vol.inputs['Color'].default_value = (1, 1, 1, 1)
vol.inputs['Density'].default_value = 20.0
try:
    vol.inputs['Density Attribute'].default_value = 'density'      # the smoke grid (default, set to be sure)
except Exception:
    pass
nt.links.new(vol.outputs['Volume'], out.inputs['Volume'])
dom.data.materials.clear(); dom.data.materials.append(mat)
bpy.ops.object.light_add(type='SUN', rotation=(math.radians(35), math.radians(-30), 0))
bpy.context.active_object.data.energy = 5.0
world = bpy.data.worlds.new('W'); sc.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.57, 0.6, 1)
bpy.ops.object.camera_add(location=(0, -12, 0.55), rotation=(math.radians(90), 0, 0))
cam = bpy.context.active_object; cam.data.type = 'ORTHO'; cam.data.ortho_scale = 5.0; sc.camera = cam

atlas = np.zeros((CELL * GRID, CELL * GRID, 4), np.float32)
tmp = os.path.join(ROOT, r"Export\Blender\compare\_smoke_frame.png")
os.makedirs(os.path.dirname(tmp), exist_ok=True); os.makedirs(os.path.dirname(OUT), exist_ok=True)
for k in range(FRAMES):
    sc.frame_set(START + k)
    sc.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(tmp)
    px = np.empty(CELL * CELL * 4, np.float32); img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    px = px.reshape(CELL, CELL, 4)[::-1]
    r, c = divmod(k, GRID)
    atlas[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL] = px
    if k % 8 == 0:
        edge = max(px[0, :, 3].max(), px[-1, :, 3].max(), px[:, 0, 3].max(), px[:, -1, 3].max())
        print('SMOKE frame', k, 'alpha mean', round(float(px[..., 3].mean()), 3), 'edge alpha', round(float(edge), 3))
a = atlas[..., 3:4]
atlas[..., :3] = np.where(a > 0.02, atlas[..., :3], 1.0)
im = bpy.data.images.new('T_DeathSmoke', CELL * GRID, CELL * GRID, alpha=True)
im.pixels.foreach_set(atlas[::-1].ravel())
im.filepath_raw = OUT; im.file_format = 'PNG'; im.save()
os.remove(tmp)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, r"Export\Blender\DeathSmokeSim.blend"))
# the bake is only needed to render the flipbook above (re-baked on every run): free the disk space
# (pass "-- --keep-cache" to keep it, e.g. to scrub the sim in DeathSmokeSim.blend)
if '--keep-cache' not in sys.argv:
    shutil.rmtree(CACHE, ignore_errors=True)
    print('SMOKE cache removed', CACHE)
print('SMOKE done', OUT)
