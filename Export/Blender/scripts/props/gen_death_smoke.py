# Death smoke flipbook (2026-11-23), headless:  blender -b --factory-startup --python <this file>
# One white smoke puff that bursts out, billows and thins away, rendered in Cycles as a volume (4D noise evolving over
# time, radial falloff growing, density eroding) from the front, transparent film -> 16 frames of 256 px packed 4 x 4
# (frame 0 top-left, row by row) into Export/Textures/Effects/T_DeathSmoke.png (RGB = lit smoke, A = coverage).
# UE: Tools/import_death_smoke.py -> M_DeathSmoke (ADeathSmoke). Saves Export/Blender/DeathSmoke.blend.
import bpy, os, math
import numpy as np

ROOT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject"
OUT = os.path.join(ROOT, r"Export\Textures\Effects\T_DeathSmoke.png")
CELL, GRID = 256, 4
FRAMES = GRID * GRID

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.samples = 128
try:
    sc.cycles.use_denoising = True
except Exception:
    pass
sc.cycles.volume_bounces = 2
sc.render.film_transparent = True
sc.render.resolution_x = sc.render.resolution_y = CELL
sc.view_settings.view_transform = 'Standard'

# ---- volume domain: cube -1..1 with a procedural puff
bpy.ops.mesh.primitive_cube_add(size=2.0)
dom = bpy.context.active_object; dom.name = 'SmokeDomain'
mat = bpy.data.materials.new('M_SmokeVolume'); mat.use_nodes = True
nt = mat.node_tree; nt.nodes.clear()
out = nt.nodes.new('ShaderNodeOutputMaterial')
vol = nt.nodes.new('ShaderNodeVolumePrincipled')
vol.inputs['Color'].default_value = (1, 1, 1, 1)
tc = nt.nodes.new('ShaderNodeTexCoord')
noise = nt.nodes.new('ShaderNodeTexNoise'); noise.noise_dimensions = '4D'
noise.inputs['Scale'].default_value = 1.5; noise.inputs['Detail'].default_value = 2.5; noise.inputs['Roughness'].default_value = 0.45
nt.links.new(tc.outputs['Object'], noise.inputs['Vector'])
length = nt.nodes.new('ShaderNodeVectorMath'); length.operation = 'LENGTH'
nt.links.new(tc.outputs['Object'], length.inputs[0])
# falloff = 1 - |p| / R      (R animated)
div = nt.nodes.new('ShaderNodeMath'); div.operation = 'DIVIDE'
nt.links.new(length.outputs['Value'], div.inputs[0])
fall = nt.nodes.new('ShaderNodeMath'); fall.operation = 'SUBTRACT'; fall.inputs[0].default_value = 1.0
nt.links.new(div.outputs['Value'], fall.inputs[1])
# shape = falloff * 1.6 + (noise - 0.5) * 1.8 - erosion
f2 = nt.nodes.new('ShaderNodeMath'); f2.operation = 'MULTIPLY'; f2.inputs[1].default_value = 1.6
nt.links.new(fall.outputs['Value'], f2.inputs[0])
n2 = nt.nodes.new('ShaderNodeMath'); n2.operation = 'MULTIPLY_ADD'; n2.inputs[1].default_value = 1.8; n2.inputs[2].default_value = -0.9
nt.links.new(noise.outputs['Fac'], n2.inputs[0])
s1 = nt.nodes.new('ShaderNodeMath'); s1.operation = 'ADD'
nt.links.new(f2.outputs['Value'], s1.inputs[0]); nt.links.new(n2.outputs['Value'], s1.inputs[1])
ero = nt.nodes.new('ShaderNodeMath'); ero.operation = 'SUBTRACT'
nt.links.new(s1.outputs['Value'], ero.inputs[0])
clamp = nt.nodes.new('ShaderNodeMath'); clamp.operation = 'MAXIMUM'; clamp.inputs[1].default_value = 0.0
nt.links.new(ero.outputs['Value'], clamp.inputs[0])
dens = nt.nodes.new('ShaderNodeMath'); dens.operation = 'MULTIPLY'
nt.links.new(clamp.outputs['Value'], dens.inputs[0])
nt.links.new(dens.outputs['Value'], vol.inputs['Density'])
nt.links.new(vol.outputs['Volume'], out.inputs['Volume'])
dom.data.materials.append(mat)

# ---- light + camera (front, slightly from below the key light)
bpy.ops.object.light_add(type='SUN', rotation=(math.radians(40), math.radians(-25), 0))
bpy.context.active_object.data.energy = 5.0
world = bpy.data.worlds.new('W'); sc.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.55, 0.57, 0.6, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
bpy.ops.object.camera_add(location=(0, -6, 0), rotation=(math.radians(90), 0, 0))
cam = bpy.context.active_object; cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.05; sc.camera = cam

# ---- frames
atlas = np.zeros((CELL * GRID, CELL * GRID, 4), np.float32)          # top-down rows
tmp = os.path.join(ROOT, r"Export\Blender\compare\_smoke_frame.png")
os.makedirs(os.path.dirname(tmp), exist_ok=True); os.makedirs(os.path.dirname(OUT), exist_ok=True)
for k in range(FRAMES):
    t = k / (FRAMES - 1)
    div.inputs[1].default_value = 0.6 + 0.42 * (1 - (1 - t) ** 2)       # puff radius grows fast, then slows
    noise.inputs['W'].default_value = t * 1.4                           # billowing
    ero.inputs[1].default_value = 0.0 + 0.95 * t ** 1.8                # thins out from the edges inward
    dens.inputs[1].default_value = 14.0 * (1 - 0.6 * t)
    sc.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(tmp)
    px = np.empty(CELL * CELL * 4, np.float32); img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    px = px.reshape(CELL, CELL, 4)[::-1]                                  # bottom-up -> top-down
    r, c = divmod(k, GRID)
    atlas[r * CELL:(r + 1) * CELL, c * CELL:(c + 1) * CELL] = px
    print('SMOKE frame', k, 'alpha max', round(float(px[..., 3].max()), 3), 'mean', round(float(px[..., 3].mean()), 3))
# straight alpha: rgb of nearly transparent pixels -> white (no dark fringes)
a = atlas[..., 3:4]
atlas[..., :3] = np.where(a > 0.02, atlas[..., :3], 1.0)
im = bpy.data.images.new('T_DeathSmoke', CELL * GRID, CELL * GRID, alpha=True)
im.pixels.foreach_set(atlas[::-1].ravel())                               # back to bottom-up for Blender
im.filepath_raw = OUT; im.file_format = 'PNG'; im.save()
os.remove(tmp)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, r"Export\Blender\DeathSmoke.blend"))
print('SMOKE done', OUT)
