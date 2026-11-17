# Stylized flower clumps (one material slot M_Stylized_Foliage, two-sided, vertex colours):
#   SM_Flower_Daisy, SM_Flower_Tulip, SM_Flower_Lavender, SM_Flower_Marigold, SM_Flower_BabysBreath,
#   SM_Flower_LilyOfTheValley, SM_Flower_Fireweed
# Built from chunky parts: tapered tube stems, rounded leaves / petals (Builder.blade), lumpy blobs. Pivot = ground.
import bpy, math, random
from mathutils import Vector, Matrix, noise

exec(open(r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Blender\scripts\props\props_common.py",
          encoding='utf-8').read())

STEM_A = (0.035, 0.11, 0.015); STEM_B = (0.08, 0.22, 0.03)
LEAF_A = (0.025, 0.09, 0.012); LEAF_B = (0.11, 0.29, 0.035)
UP = Vector((0, 0, 1))


def leaf_profile(t):
    return max(0.3, math.sin(math.pi * (0.08 + 0.84 * t)) ** 0.6)


def petal_profile(t):
    return max(0.45, math.sin(math.pi * (0.1 + 0.75 * t)) ** 0.5)


def grad(a, b):
    return lambda t, s, p: mix(a, b, c01(t))


def basis(f):
    u = f.orthogonal().normalized(); v = f.cross(u).normalized()
    return u, v


class Plant:
    def __init__(self, seed):
        self.B = Builder(); self.rng = random.Random(seed)

    def stem(self, pts, r0, r1, sides=6, col=(STEM_A, STEM_B)):
        n = len(pts)
        radii = [r0 + (r1 - r0) * k / (n - 1) for k in range(n)]
        self.B.tube(pts, radii, sides=sides, color=lambda t, p: mix(col[0], col[1], t))

    def curve(self, base, top, sway):
        """Gently bent stem polyline (4 points)."""
        mid = base.lerp(top, 0.5) + sway
        return [base, base.lerp(mid, 0.6), mid.lerp(top, 0.5), top]

    def leaf(self, base, direction, length, width, bend=0.5, col=(LEAF_A, LEAF_B), cup=0.3, rows=4):
        d = direction.normalized()
        up = (UP - d * UP.dot(d)) if abs(d.dot(UP)) < 0.98 else Vector((1, 0, 0))
        side = d.cross(up)
        up = (up.normalized() + side.normalized() * self.rng.uniform(-0.3, 0.3)).normalized()
        self.B.blade(base, d, up, length, width, bend=bend, rows=rows, color=grad(*col), cup=cup, profile=leaf_profile)

    def petals(self, centre, facing, count, length, width, tilt, col, bend=0.0, cup=0.3, phase=0.0, rows=3,
               offset=0.0):
        u, v = basis(facing)
        for k in range(count):
            a = phase + 2 * math.pi * k / count
            radial = u * math.cos(a) + v * math.sin(a)
            d = (radial * math.cos(tilt) + facing * math.sin(tilt)).normalized()
            self.B.blade(centre + radial * offset, d, facing, length, width, bend=bend, rows=rows, color=grad(*col),
                         cup=cup, profile=petal_profile)

    def blob(self, c, r, scl=(1, 1, 1), col=((1, 1, 1), (1, 1, 1)), subdiv=2, lump=0.15):
        self.B.blob(c, r, scl=scl, subdiv=subdiv, lump=lump, seed=self.rng.random() * 10,
                    color=lambda q, p: mix(col[0], col[1], c01(q.z * 0.5 + 0.5)))

    def finish(self, name, x):
        ob = self.B.finish(name, [material('M_Stylized_Foliage', True)], collection='Flowers', location=(x, 8, 0))
        return ob


def scatter(rng, n, radius):
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n + rng.uniform(-0.4, 0.4); r = radius * math.sqrt(rng.uniform(0.15, 1.0))
        out.append(Vector((math.cos(a) * r, math.sin(a) * r, 0)))
    return out


# ---------------------------------------------------------------------------------------------------------------
def daisy():
    P = Plant(21); rng = P.rng
    WHITE_A = (0.62, 0.62, 0.58); WHITE_B = (0.85, 0.85, 0.82); YEL_A = (0.45, 0.20, 0.005); YEL_B = (0.75, 0.42, 0.01)
    for k in range(8):  # basal rosette
        a = 2 * math.pi * k / 8 + rng.uniform(-0.2, 0.2)
        P.leaf(Vector((0, 0, 0.005)), Vector((math.cos(a), math.sin(a), 0.35)), rng.uniform(0.08, 0.11), 0.035, bend=-0.6)
    for base in scatter(rng, 5, 0.08):
        h = rng.uniform(0.24, 0.38)
        top = base + Vector((rng.uniform(-.05, .05), rng.uniform(-.05, .05), h))
        P.stem(P.curve(base, top, Vector((rng.uniform(-.03, .03), rng.uniform(-.03, .03), 0))), 0.004, 0.003)
        face = (UP * 1.0 + (top - base).normalized() * 0.4 + Vector((rng.uniform(-.4, .4), rng.uniform(-.4, .4), 0))).normalized()
        P.petals(top, face, 14, 0.034, 0.011, -0.05, (WHITE_A, WHITE_B), bend=-0.35, cup=0.2, phase=rng.random(), offset=0.008)
        P.blob(top + face * 0.004, 0.012, scl=(1, 1, 0.55), col=(YEL_A, YEL_B), subdiv=2)
    return P.finish('SM_Flower_Daisy', -9)


def tulip():
    P = Plant(22); rng = P.rng
    COLS = [((0.42, 0.015, 0.01), (0.78, 0.07, 0.03)), ((0.55, 0.30, 0.01), (0.88, 0.62, 0.05)),
            ((0.50, 0.08, 0.16), (0.85, 0.30, 0.45))]
    for i, base in enumerate(scatter(rng, 3, 0.07)):
        h = rng.uniform(0.32, 0.45)
        top = base + Vector((rng.uniform(-.03, .03), rng.uniform(-.03, .03), h))
        P.stem(P.curve(base, top, Vector((rng.uniform(-.02, .02), rng.uniform(-.02, .02), 0))), 0.0065, 0.005, sides=7)
        for k in range(2):  # broad leaves
            a = rng.uniform(0, 2 * math.pi)
            P.leaf(base + Vector((0, 0, 0.01)), Vector((math.cos(a) * 0.35, math.sin(a) * 0.35, 1)), rng.uniform(0.18, 0.24),
                   0.055, bend=-0.5, cup=0.5, rows=5)
        face = UP
        col = COLS[i % len(COLS)]
        # cup: 3 outer + 3 inner petals, standing up and curling inward
        P.petals(top - UP * 0.01, face, 3, 0.065, 0.042, 1.25, col, bend=-0.25, cup=0.7, phase=0.0, rows=4, offset=0.006)
        P.petals(top - UP * 0.01, face, 3, 0.06, 0.04, 1.3, col, bend=-0.3, cup=0.7, phase=math.pi / 3, rows=4, offset=0.004)
        P.blob(top + UP * 0.005, 0.012, scl=(1, 1, 1.2), col=((0.05, 0.12, 0.02), (0.25, 0.25, 0.05)), subdiv=1)
    return P.finish('SM_Flower_Tulip', -6)


def lavender():
    P = Plant(23); rng = P.rng
    LAV_A = (0.10, 0.04, 0.28); LAV_B = (0.36, 0.20, 0.68); SAGE_A = (0.05, 0.09, 0.05); SAGE_B = (0.20, 0.28, 0.17)
    for k in range(14):  # narrow grey-green leaves
        a = rng.uniform(0, 2 * math.pi)
        P.leaf(Vector((0, 0, 0.01)), Vector((math.cos(a) * 0.5, math.sin(a) * 0.5, 1)), rng.uniform(0.12, 0.18), 0.018,
               bend=-0.5, col=(SAGE_A, SAGE_B), cup=0.2)
    for k in range(13):
        a = 2 * math.pi * k / 13 + rng.uniform(-0.2, 0.2); lean = rng.uniform(0.15, 0.45)
        d = Vector((math.cos(a) * lean, math.sin(a) * lean, 1)).normalized()
        L = rng.uniform(0.40, 0.56)
        base = Vector((math.cos(a) * 0.02, math.sin(a) * 0.02, 0)); top = base + d * L
        P.stem(P.curve(base, top, Vector((0, 0, 0))), 0.003, 0.0025, sides=5, col=(SAGE_A, SAGE_B))
        # spike: whorls of chunky buds over the last 12 cm, smaller toward the tip
        n_wh = 9
        for w in range(n_wh):
            t = w / (n_wh - 1)
            c = top - d * (0.12 * (1 - t))
            u, v = basis(d)
            rr = 0.0075 * (1.0 - 0.45 * t)
            for b in range(5):
                ang = 2 * math.pi * b / 5 + w * 0.6
                P.blob(c + (u * math.cos(ang) + v * math.sin(ang)) * rr * 0.9, rr, col=(mix(LAV_A, LAV_B, t * 0.5), LAV_B),
                       subdiv=1, lump=0.1)
    return P.finish('SM_Flower_Lavender', -3)


def marigold():
    P = Plant(24); rng = P.rng
    OR_A = (0.55, 0.07, 0.003); OR_B = (0.95, 0.34, 0.01); YL_A = (0.70, 0.30, 0.004); YL_B = (0.95, 0.60, 0.02)
    for i, base in enumerate(scatter(rng, 4, 0.07)):
        h = rng.uniform(0.22, 0.32)
        top = base + Vector((rng.uniform(-.04, .04), rng.uniform(-.04, .04), h))
        P.stem(P.curve(base, top, Vector((rng.uniform(-.02, .02), rng.uniform(-.02, .02), 0))), 0.005, 0.004)
        for k in range(5):  # small lobed leaves up the stem
            t = 0.15 + 0.15 * k
            p = base.lerp(top, t); a = rng.uniform(0, 2 * math.pi)
            P.leaf(p, Vector((math.cos(a), math.sin(a), 0.5)), 0.06, 0.022, bend=-0.4)
        col = (OR_A, OR_B) if i % 2 == 0 else (YL_A, YL_B)
        face = (UP + Vector((rng.uniform(-.3, .3), rng.uniform(-.3, .3), 0))).normalized()
        # pom-pom: rings of ruffled petals, more upright toward the centre
        for ring, (cnt, ln, wd, tilt) in enumerate([(12, 0.026, 0.02, 0.15), (10, 0.022, 0.018, 0.6),
                                                     (8, 0.018, 0.016, 1.0), (6, 0.014, 0.014, 1.3)]):
            P.petals(top + face * (0.004 * ring), face, cnt, ln, wd, tilt, col, bend=0.3, cup=0.5,
                     phase=ring * 0.4 + rng.random(), offset=0.002)
        P.blob(top + face * 0.012, 0.009, col=col, subdiv=1)
    return P.finish('SM_Flower_Marigold', 0)


def babys_breath():
    P = Plant(25); rng = P.rng
    WH_A = (0.62, 0.66, 0.62); WH_B = (0.88, 0.90, 0.88)
    tips = []

    def branch(p, d, length, r, depth):
        end = p + d * length
        P.stem([p, p.lerp(end, 0.5), end], r, r * 0.75, sides=4)
        if depth == 0:
            tips.append(end); return
        for k in range(3 if depth > 1 else rng.randint(2, 4)):
            a = rng.uniform(0, 2 * math.pi)
            nd = (d * 0.6 + Vector((math.cos(a), math.sin(a), 0.35)) * 0.6).normalized()
            branch(end, nd, length * rng.uniform(0.5, 0.7), r * 0.7, depth - 1)
    for k in range(4):
        a = 2 * math.pi * k / 4 + rng.uniform(-0.3, 0.3)
        d = Vector((math.cos(a) * 0.25, math.sin(a) * 0.25, 1)).normalized()
        branch(Vector((math.cos(a) * 0.02, math.sin(a) * 0.02, 0)), d, 0.22, 0.004, 3)
    for t in tips:  # puffs of tiny flowers, as soft little clusters
        for b in range(3):
            o = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.3, 1))) * 0.009
            P.blob(t + o, rng.uniform(0.007, 0.011), col=(WH_A, WH_B), subdiv=1, lump=0.25)
    for k in range(6):
        a = rng.uniform(0, 2 * math.pi)
        P.leaf(Vector((0, 0, 0.01)), Vector((math.cos(a), math.sin(a), 0.6)), 0.07, 0.014, bend=-0.4)
    return P.finish('SM_Flower_BabysBreath', 3)


def lily_of_the_valley():
    P = Plant(26); rng = P.rng
    BELL_A = (0.62, 0.66, 0.60); BELL_B = (0.88, 0.90, 0.86)
    for i, base in enumerate(scatter(rng, 3, 0.06)):
        a0 = rng.uniform(0, 2 * math.pi)
        for k in range(2):  # two broad upright leaves
            a = a0 + k * math.pi + rng.uniform(-0.3, 0.3)
            P.leaf(base + Vector((0, 0, 0.005)), Vector((math.cos(a) * 0.3, math.sin(a) * 0.3, 1)), rng.uniform(0.17, 0.22),
                   0.065, bend=-0.35, cup=0.6, rows=5)
        # arching flower stem with hanging bells
        out = Vector((math.cos(a0 + math.pi / 2), math.sin(a0 + math.pi / 2), 0))
        pts = [base, base + Vector((0, 0, 0.09)), base + out * 0.04 + Vector((0, 0, 0.16)), base + out * 0.10 + Vector((0, 0, 0.18)),
               base + out * 0.15 + Vector((0, 0, 0.16))]
        P.stem(pts, 0.0028, 0.002, sides=5)
        for b in range(7):
            t = 0.35 + 0.65 * b / 6
            seg = t * (len(pts) - 1); k = min(int(seg), len(pts) - 2)
            p = pts[k].lerp(pts[k + 1], seg - k)
            hang = p + Vector((0, 0, -0.012)) + out.cross(UP) * (0.006 if b % 2 else -0.006)
            P.stem([p, hang], 0.0012, 0.001, sides=4)
            r = 0.0065 * (1.0 - 0.35 * b / 6)
            P.blob(hang - UP * r * 0.7, r, scl=(1, 1, 1.05), col=(BELL_A, BELL_B), subdiv=2, lump=0.05)
            # flared rim: little petal tips curling outward at the bottom
            P.petals(hang - UP * r * 1.5, -UP, 6, r * 0.7, r * 0.6, -0.9, (BELL_A, BELL_B), bend=-0.6, cup=0.1, rows=2,
                     offset=r * 0.6)
    return P.finish('SM_Flower_LilyOfTheValley', 6)


def fireweed():
    P = Plant(27); rng = P.rng
    PINK_A = (0.42, 0.04, 0.16); PINK_B = (0.82, 0.16, 0.42); BUD_A = (0.22, 0.03, 0.10); BUD_B = (0.45, 0.07, 0.22)
    STEMC = ((0.10, 0.06, 0.04), (0.20, 0.10, 0.10))   # reddish stems
    for i, base in enumerate(scatter(rng, 4, 0.08)):
        h = rng.uniform(0.80, 1.10)
        top = base + Vector((rng.uniform(-.06, .06), rng.uniform(-.06, .06), h))
        P.stem(P.curve(base, top, Vector((rng.uniform(-.03, .03), rng.uniform(-.03, .03), 0))), 0.009, 0.006, sides=6, col=STEMC)
        sd = (top - base).normalized()
        for k in range(12):  # narrow alternate leaves on the lower 2/3
            t = 0.08 + 0.05 * k
            p = base.lerp(top, t); a = k * 2.4 + rng.random() * 0.3
            P.leaf(p, Vector((math.cos(a), math.sin(a), 0.4)), 0.12 * (1.0 - 0.4 * t), 0.032, bend=-0.4)
        # raceme: open flowers below, buds toward the tip
        for k in range(16):
            t = k / 15
            c = top - sd * (0.32 * (1 - t))
            a = k * 2.4
            out = Vector((math.cos(a), math.sin(a), 0))
            pos = c + out * 0.024
            if t < 0.65:
                face = (out + UP * 0.6).normalized()
                P.petals(pos, face, 4, 0.028, 0.024, 0.1, (PINK_A, PINK_B), bend=0.2, cup=0.35, phase=rng.random(), rows=3,
                         offset=0.002)
                P.blob(pos + face * 0.003, 0.003, col=((0.8, 0.8, 0.8), (0.9, 0.9, 0.9)), subdiv=1)
            else:
                P.blob(pos, 0.009 * (1.2 - 0.6 * t), scl=(1, 1, 1.6), col=(BUD_A, BUD_B), subdiv=1, lump=0.05)
            P.stem([c, pos], 0.0015, 0.0012, sides=4, col=STEMC)
    return P.finish('SM_Flower_Fireweed', 9)


ALL = [daisy, tulip, lavender, marigold, babys_breath, lily_of_the_valley, fireweed]


def build_all(do_export=True):
    out = []
    for fn in ALL:
        ob = fn()
        tris = export(ob) if do_export else sum(len(p.vertices) - 2 for p in ob.data.polygons)
        out.append((ob.name, tris, tuple(round(d, 2) for d in ob.dimensions)))
    return out
