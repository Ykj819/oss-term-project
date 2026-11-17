# Stylized grass patch SM_StylizedGrass: 2 m x 2 m, pivot at the centre of the patch on the ground.
# Chunky clumps of wide blades with rounded tips (no thin spiky blades), leaning outward from each clump.
# Colour: dark green at the root -> light yellow-green at the tip, slight per-clump hue variation.
# Normals are bent toward +Z so the patch shades softly like a lawn instead of showing every blade.
import bpy, math, random
from mathutils import Vector, noise

exec(open(r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Blender\scripts\props\props_common.py",
          encoding='utf-8').read())

SIZE = 2.0
ROOT_C = (0.018, 0.065, 0.012); MID_C = (0.07, 0.20, 0.025); TIP_C = (0.26, 0.46, 0.06); DRY_C = (0.36, 0.40, 0.10)


def build(seed=7, clumps=190, do_export=True):
    rng = random.Random(seed)
    B = Builder(); mat = material('M_Stylized_Foliage', True)
    half = SIZE / 2
    nblades = 0
    for c in range(clumps):
        cx, cy = rng.uniform(-half + 0.05, half - 0.05), rng.uniform(-half + 0.05, half - 0.05)
        centre = Vector((cx, cy, 0))
        tint = rng.random()
        dry = c01((noise.noise(Vector((cx * 0.9, cy * 0.9, 3.3))) - 0.25) * 3)
        for b in range(rng.randint(9, 16)):
            a = rng.uniform(0, 2 * math.pi); rr = rng.uniform(0, 0.06)
            base = centre + Vector((math.cos(a) * rr, math.sin(a) * rr, -0.01))
            if abs(base.x) > half or abs(base.y) > half:
                continue
            out = Vector((math.cos(a), math.sin(a), 0))
            lean = rng.uniform(0.15, 0.55)
            d = (Vector((0, 0, 1)) + out * lean).normalized()
            twist = rng.uniform(-0.6, 0.6)
            up = (out * math.cos(twist) + out.cross(Vector((0, 0, 1))) * math.sin(twist))
            length = rng.uniform(0.2, 0.36) * (0.85 + 0.3 * tint)
            width = rng.uniform(0.05, 0.075)

            def col(t, s, p, tint=tint, dry=dry):
                c = mix(ROOT_C, MID_C, c01(t * 2.2))
                c = mix(c, TIP_C, c01((t - 0.4) / 0.6))
                c = mix(c, DRY_C, dry * c01(t - 0.3) * 0.6)
                return scale(c, 0.85 + 0.3 * tint)
            B.blade(base, d, -up, length, width, bend=rng.uniform(0.4, 0.9), rows=3, mat=0, color=col,
                    cup=0.25, profile=lambda t: 1.0 - 0.45 * t)
            nblades += 1
    ob = B.finish('SM_StylizedGrass', [mat], collection='Grass')
    # soft lawn shading: bend every normal toward +Z
    me = ob.data
    normals = []
    for v in me.vertices:
        n = (v.normal * 0.3 + Vector((0, 0, 1))).normalized()
        normals.append(n)
    me.normals_split_custom_set_from_vertices(normals)
    tris = export(ob) if do_export else sum(len(p.vertices) - 2 for p in me.polygons)
    return ob.name, nblades, tris
