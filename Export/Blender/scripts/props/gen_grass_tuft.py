# Single low-poly grass tufts SM_GrassTuft1..3 (one plant each, for the Foliage tool / Landscape Grass Type).
# Each blade = 7 vertices / 5 triangles: two bent segments and a blunt pentagon tip (no spiky points).
# Colour: dark green root -> yellow-green tip. Normals bent toward +Z so the tuft shades softly like a lawn.
# Pivot at the centre of the tuft on the ground. Material slot M_Stylized_Foliage (two-sided).
import bpy, math, random
from mathutils import Vector

exec(open(r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Blender\scripts\props\props_common.py",
          encoding='utf-8').read())

ROOT_C = (0.018, 0.065, 0.012); MID_C = (0.07, 0.20, 0.025); TIP_C = (0.26, 0.46, 0.06); DRY_C = (0.36, 0.40, 0.10)

# name: (seed, blades, length range m, width range m, lean range, spread radius m, dry amount)
VARIANTS = {
    'SM_GrassTuft1': (11, 7, (0.18, 0.28), (0.055, 0.075), (0.25, 0.6), 0.03, 0.0),   # short, round tuft
    'SM_GrassTuft2': (23, 9, (0.30, 0.45), (0.05, 0.07), (0.15, 0.45), 0.035, 0.1),   # tall tuft
    'SM_GrassTuft3': (37, 6, (0.14, 0.22), (0.07, 0.09), (0.55, 0.9), 0.04, 0.45),    # low, splayed, dry tips
}


def low_blade(B, base, d_out, length, width, lean, bend, color):
    """7 verts / 5 tris. d_out: horizontal outward direction."""
    up = Vector((0, 0, 1)); side = d_out.cross(up).normalized()
    pts = []; meta = []
    for r, (t, wk) in enumerate(((0.0, 0.9), (0.5, 1.0), (0.86, 0.85))):
        # centre along a bent curve (angle from vertical grows toward the tip)
        c = base + (up * math.cos(lean + bend * t * t * 0.5) + d_out * math.sin(lean + bend * t * t * 0.5)) * length * t
        for s in (-1, 1):
            pts.append(c + side * s * width * 0.5 * wk); meta.append((t, s))
    ang = lean + bend * 0.5                             # blunt round end: tip only a little past the last row
    tip = base + (up * math.cos(ang) + d_out * math.sin(ang)) * length * 0.95
    pts.append(tip); meta.append((1.0, 0))
    faces = [(0, 1, 3, 2), (2, 3, 5, 4), (4, 5, 6)]
    return B.faces(pts, faces, 0, lambda i, p: color(meta[i][0]))


def build(name, do_export=True):
    seed, nb, lr, wr, lean_r, spread, dry = VARIANTS[name]
    rng = random.Random(seed)
    B = Builder(); mat = material('M_Stylized_Foliage', True)
    a0 = rng.uniform(0, 2 * math.pi)
    for b in range(nb):
        a = a0 + 2 * math.pi * b / nb + rng.uniform(-0.35, 0.35)
        out = Vector((math.cos(a), math.sin(a), 0))
        base = out * rng.uniform(0, spread) + Vector((0, 0, -0.01))
        L = rng.uniform(*lr); tint = rng.uniform(0.85, 1.15)

        def col(t, tint=tint):
            c = mix(ROOT_C, MID_C, c01(t * 2.2))
            c = mix(c, TIP_C, c01((t - 0.4) / 0.6))
            c = mix(c, DRY_C, dry * c01(t - 0.3) * 1.2)
            return scale(c, tint)
        low_blade(B, base, out, L, rng.uniform(*wr), rng.uniform(*lean_r), rng.uniform(0.3, 0.7), col)
    ob = B.finish(name, [mat], collection='GrassTufts')
    me = ob.data
    me.normals_split_custom_set_from_vertices([(v.normal * 0.3 + Vector((0, 0, 1))).normalized() for v in me.vertices])
    tris = export(ob) if do_export else sum(len(p.vertices) - 2 for p in me.polygons)
    return ob.name, nb, tris


def build_all(do_export=True):
    return [build(n, do_export) for n in VARIANTS]
