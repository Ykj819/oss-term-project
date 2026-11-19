# Player knight v4: rebuilt from measurements of the user's turnaround concept (front/side/back, 2026-11-20),
# compared with compare_ref.py (same pixel scale: 1.90 m = 483 px). High poly (no decimation by default).
# Proportions moved toward the concept within the fixed UE mannequin skeleton:
#   high collar (1.60-1.72) with the narrow capsule head sunk into it, face just above the collar rim;
#   pauldrons = ridged shell (crest peak ~1.72) + 5 gold-edged lames down the upper arm;
#   short torso: belt at 1.16, fauld skirt 1.14 -> 0.88 with a narrow front arch and a wide back arch showing a steel
#   crotch cup / two steel seat lobes; big lens-shaped knee cops with full gold borders; dark leather behind the knees.
# Reuses Kit2 (gen_player_knight_v2.py) and make_object / weights (gen_player_knight.py).
import bpy, bmesh, math
from mathutils import Vector, Matrix

V2 = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Blender\scripts\characters\gen_player_knight_v2.py"
exec(open(V2, encoding='utf-8').read())


# ---- palette (Kit2 default args point at v2's functions -> replace their code in place)
def _steel(p, n):
    return mix((0.36, 0.38, 0.41), (0.62, 0.64, 0.67), 0.5 + 0.5 * n.z), 1.0


def _steel_hi(p, n):
    return mix((0.55, 0.57, 0.60), (0.78, 0.79, 0.81), 0.5 + 0.5 * n.z), 1.0


def _gold(p, n):
    return mix((0.62, 0.40, 0.12), (0.86, 0.62, 0.24), 0.5 + 0.5 * n.z), 1.0


def _dark_steel(p, n):
    return mix((0.34, 0.35, 0.37), (0.48, 0.49, 0.51), 0.5 + 0.5 * n.z), 1.0


def _leather(p, n):
    return mix((0.13, 0.065, 0.03), (0.22, 0.12, 0.06), 0.5 + 0.5 * n.z), 0.0


steel.__code__ = _steel.__code__
steel_hi.__code__ = _steel_hi.__code__
gold.__code__ = _gold.__code__
dark_steel.__code__ = _dark_steel.__code__
leather.__code__ = _leather.__code__


def pad(p, n):          # dark leather / quilt visible at the joints
    return mix((0.07, 0.055, 0.045), (0.15, 0.12, 0.10), 0.5 + 0.5 * n.z), 0.0


def glove(p, n):
    return mix((0.06, 0.04, 0.03), (0.13, 0.085, 0.06), 0.5 + 0.5 * n.z), 0.0


def etch(p, n):         # pale etched emblem on the breastplate
    return (0.88, 0.89, 0.9), 0.3


def skin4(p, n):
    return mix((0.70, 0.36, 0.24), (0.88, 0.53, 0.38), 0.45 + 0.55 * n.z), 0.0


def leaf4(p, n):
    return mix((0.10, 0.33, 0.03), (0.30, 0.62, 0.10), 0.5 + 0.5 * n.z), 0.0


def ploop(c, ax, rx, ry=None, n=48, a0=0.0, a1=2 * math.pi, closed=True):
    """points of an ellipse around axis ax (ry toward the character's front / up)."""
    ax = ax.normalized(); ry = ry or rx
    fy = Vector((0, -1, 0)) - ax * ax.dot(Vector((0, -1, 0)))
    if fy.length < 1e-3:
        fy = Vector((0, 0, 1)) - ax * ax.z
    fy.normalize(); fx = fy.cross(ax).normalized()
    cnt = n if closed else n + 1
    return [c + fx * (rx * math.cos(a0 + (a1 - a0) * i / n)) + fy * (ry * math.sin(a0 + (a1 - a0) * i / n))
            for i in range(cnt)]


class Kit4(Kit2):
    """Kit2 + a part label per vertex (K.part_of[i] indexes K.part_names), used by make_parts.py to split the
    model into separate assembly pieces. Geometry and vertex order are identical to Kit2."""
    def __init__(self):
        super().__init__(); self.part_names = ['Misc']; self.part_of = []; self.cur_part = 0

    def part(self, name):
        if name not in self.part_names:
            self.part_names.append(name)
        self.cur_part = self.part_names.index(name)

    def faces(self, verts, faces, color):
        n0 = len(self.bm.verts)
        out = super().faces(verts, faces, color)
        self.part_of.extend([self.cur_part] * (len(self.bm.verts) - n0))
        return out

    def thicken_open(self, depth=0.0015):
        """Single-sided open shells (pauldrons, lames, skirt, cops...) are see-through from behind in UE (backface
        culling). Give every open island (one with boundary edges) an inner copy with flipped normals, `depth` behind
        it. New verts are appended at the end, so part labels / piece ids stay aligned."""
        bm = self.bm
        bm.verts.index_update(); bm.faces.index_update()
        bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
        seen = set(); open_faces = []
        for f0 in bm.faces:
            if f0.index in seen:
                continue
            stack = [f0]; seen.add(f0.index); isl = []; is_open = False
            while stack:
                f = stack.pop(); isl.append(f)
                for e in f.edges:
                    lf = e.link_faces
                    if len(lf) < 2:
                        is_open = True
                    for g in lf:
                        if g.index not in seen:
                            seen.add(g.index); stack.append(g)
            if is_open:
                open_faces += isl
        n0 = len(bm.verts)
        old_verts = list({v for f in open_faces for v in f.verts})
        part_by_vert = {v.index: self.part_of[v.index] for v in old_verts}
        res = bmesh.ops.duplicate(bm, geom=open_faces)
        old_set = set(old_verts)
        # vert_map holds old->new (and possibly new->old) pairs: keep only old->new
        pairs = [(a, b) for a, b in res['vert_map'].items() if isinstance(a, bmesh.types.BMVert) and a in old_set
                 and b not in old_set]
        new_faces = [g for g in res['geom'] if isinstance(g, bmesh.types.BMFace)]
        bmesh.ops.reverse_faces(bm, faces=new_faces)
        for v_old, v_new in pairs:
            v_new.co = v_old.co - v_old.normal * depth
        bm.verts.index_update(); bm.verts.ensure_lookup_table()
        # duplicated verts are appended in creation order; label them from their source vertex
        src_of = {v_new.index: part_by_vert[v_old.index] for v_old, v_new in pairs}
        assert len(src_of) == len(bm.verts) - n0, (len(src_of), len(bm.verts) - n0)
        self.part_of.extend(src_of[i] for i in range(n0, len(bm.verts)))
        bm.normal_update()
        return len(open_faces)


def build():
    arm = bpy.data.objects[ARM]; Mw = arm.matrix_world
    H = lambda b: Mw @ arm.data.bones[b].head_local
    T = lambda b: Mw @ arm.data.bones[b].tail_local
    K = Kit4()
    UP = Vector((0, 0, 1))

    # ================================================================ head (rigid neck_02)
    K.piece({'neck_02': 1.0}); K.part('Head')
    HC = Vector((0, -0.004, 1.755)); HRX, HRY, HTOP, HBOT, PW = 0.101, 0.096, 0.148, 0.15, 2.6

    def capsule(v):          # super-ellipse in height: straight sides, round top
        z = v.z; rr = math.sqrt(max(1 - z * z, 1e-9)); rr2 = (1 - abs(z) ** PW) ** (1 / PW)
        k = rr2 / rr if rr > 1e-4 else 1.0
        return Vector((v.x * k, v.y * k * (0.95 if v.y < 0 else 1.0), z * (HTOP if z > 0 else HBOT)))
    K.ellipsoid(HC, (HRX, HRY, 1.0), segs=96, rings=64, color=skin4, shape=capsule)

    def face_y(x, z):
        vz = (z - HC.z) / (HTOP if z > HC.z else HBOT)
        rr2 = (1 - abs(vz) ** PW) ** (1 / PW)
        q = 1 - (x / (HRX * rr2)) ** 2
        return HC.y - HRY * 0.95 * rr2 * math.sqrt(max(q, 0.0))

    def on_face(x, z, out=0.0):
        return Vector((x, face_y(x, z) - out, z))
    for s in (-1, 1):
        ex, ez = 0.035 * s, 1.739
        K.ellipsoid(on_face(ex, ez, -0.002), (0.0085, 0.005, 0.0115), segs=20, rings=10, color=flat(DARK))
        K.ellipsoid(on_face(ex + 0.002 * s, ez + 0.004, 0.003), (0.0024, 0.0012, 0.003), segs=10, rings=6,
                    color=flat((0.9, 0.9, 0.9)))
        # angry brows: thick, inner end low
        pts = [on_face(s * (0.013 + 0.043 * f), 1.756 + 0.019 * f - 0.004 * math.sin(f * math.pi), 0.002)
               for f in (i / 8 for i in range(9))]
        K.loft([(p, 0.0068 * (0.8 + 0.35 * math.sin(i / 8 * math.pi)), 0.0035, 0.0035) for i, p in enumerate(pts)],
               10, flat(DARK), True, True)
    # small wavy grumpy mouth
    mp = [on_face(x, 1.717 + 0.004 * math.sin((x + 0.02) * 140) + 0.003 * (1 - (x / 0.022) ** 2), 0.0015)
          for x in (-0.022 + 0.044 * i / 12 for i in range(13))]
    K.loft([(p, 0.0042, 0.0026, 0.0026) for p in mp], 10, flat(DARK), True, True)
    # sprout
    top = Vector((0, HC.y + 0.004, HC.z + HTOP - 0.004))
    stem = [top, top + Vector((0.001, 0, 0.015)), top + Vector((0.003, 0.002, 0.03)), top + Vector((0.004, 0.003, 0.04))]
    K.loft2([(p, 0.0055 - 0.0015 * i / 3, 0.0055 - 0.0015 * i / 3, 0.0055 - 0.0015 * i / 3) for i, p in enumerate(stem)],
            12, leaf4, False, True, sub=3)
    for s in (-1, 1):
        base = stem[-1] + Vector((0, 0, -0.002))
        d = Vector((s * 0.85, 0.0, 0.55)).normalized()
        side = Vector((0, 1, 0)); nrm = d.cross(side).normalized()
        if nrm.z < 0:
            nrm = -nrm
        verts = []; faces = []
        NL, NW = 14, 8
        for i in range(NL + 1):
            t = i / NL
            w = 0.0105 * math.sin(math.pi * min(1.0, t * 1.02)) ** 0.7
            for j in range(NW + 1):
                u = -1 + 2 * j / NW
                verts.append(base + d * (0.036 * t) + side * (u * w) + nrm * (0.008 * t * t - 0.0025 * u * u))
        for i in range(NL):
            for j in range(NW):
                a = i * (NW + 1) + j
                faces.append((a, a + 1, a + NW + 2, a + NW + 1))
        K.faces(verts, faces, leaf4)
        K.faces([v - nrm * 0.0012 for v in verts], [tuple(reversed(f)) for f in faces], leaf4)

    # ================================================================ collar (gorget), high, head sunk in it
    K.piece({'spine_05': 0.4, 'neck_01': 0.6}); K.part('Collar')
    K.loft2([(Vector((0, -0.004, 1.585)), 0.142, 0.135, 0.13), (Vector((0, -0.004, 1.63)), 0.126, 0.12, 0.116),
             (Vector((0, -0.004, 1.67)), 0.118, 0.112, 0.109), (Vector((0, -0.004, 1.70)), 0.12, 0.114, 0.111)],
            96, steel, False, False, sub=4)
    K.rim([Vector((0.122 * math.cos(a), -0.004 + (0.116 if math.sin(a) < 0 else 0.113) * math.sin(a), 1.701))
           for a in (2 * math.pi * i / 96 for i in range(96))], 0.0075, 12, steel_hi)
    K.rim([Vector((0.124 * math.cos(a), -0.004 + (0.118 if math.sin(a) < 0 else 0.114) * math.sin(a), 1.645))
           for a in (2 * math.pi * i / 96 for i in range(96))], 0.004, 10, steel_hi)
    # dark inside of the collar
    K.loft2([(Vector((0, -0.004, 1.697)), 0.112, 0.106, 0.103), (Vector((0, -0.004, 1.65)), 0.108, 0.102, 0.099)],
            96, pad, False, False, sub=1)

    # ================================================================ torso (copied weights)
    K.piece('xfer'); K.part('Breastplate')
    cu = [(1.10, 0.160, 0.126, 0.116, -0.025), (1.18, 0.160, 0.138, 0.118, -0.03), (1.28, 0.174, 0.162, 0.124, -0.03),
          (1.38, 0.196, 0.186, 0.136, -0.022), (1.47, 0.196, 0.174, 0.136, -0.012), (1.55, 0.178, 0.145, 0.128, -0.005),
          (1.61, 0.150, 0.132, 0.124, -0.004), (1.655, 0.134, 0.127, 0.121, -0.004)]
    K.loft2([(Vector((0, cy, z)), rx, ryf, ryb) for z, rx, ryf, ryb, cy in cu], 128, steel, True, False, sub=6,
            ridge=0.045)

    def body_pt(x, z, out=0.0, back=False):
        for (z0, rx0, f0, b0, c0), (z1, rx1, f1, b1, c1) in zip(cu, cu[1:]):
            if z0 <= z <= z1:
                t = (z - z0) / (z1 - z0)
                rx = rx0 + (rx1 - rx0) * t; cy = c0 + (c1 - c0) * t
                q = math.sqrt(max(1 - (x / rx) ** 2, 0.0))
                if back:
                    ry = b0 + (b1 - b0) * t
                    return Vector((x, cy + ry * q + out, z))
                ry = f0 + (f1 - f0) * t
                return Vector((x, cy - ry * q * (1 + 0.045 * q ** 14) - out, z))
        return Vector((x, -0.1, z))

    def surf_line(pts2d, r, back=False, color=None, flat_=0.6):
        pts = [body_pt(x, z, r * 0.4, back) for x, z in pts2d]
        K.loft([(p, r, r * flat_, r * flat_) for p in pts], 10, color or gold, True, True)

    def smooth_pts(ctrl, n=40):
        ext = [ctrl[0]] + ctrl + [ctrl[-1]]
        out = []
        for i in range(len(ctrl) - 1):
            for k in range(n // (len(ctrl) - 1)):
                t = k / (n // (len(ctrl) - 1))
                p = catmull(*(Vector(e) for e in ext[i:i + 4]), t)
                out.append((p.x, p.y))
        out.append(ctrl[-1]); return out
    for s in (-1, 1):
        # gold edge of the breastplate armholes, front and back
        arm_hole = smooth_pts([(s * 0.135, 1.62), (s * 0.172, 1.55), (s * 0.19, 1.45), (s * 0.18, 1.33), (s * 0.168, 1.20)])
        surf_line(arm_hole, 0.0055)
        surf_line(arm_hole, 0.0055, back=True)
    # breastplate top edge (gold) where it meets the collar
    K.rim([Vector((0.138 * math.cos(a), -0.004 + (0.131 if math.sin(a) < 0 else 0.125) * math.sin(a), 1.6))
           for a in (2 * math.pi * i / 96 for i in range(96))], 0.0055, 10, gold)
    # faint plackart lames above the belt
    for z in (1.275, 1.325):
        surf_line([(x, z - 0.012 * (1 - (x / 0.16) ** 2)) for x in (i / 30 * 0.32 - 0.16 for i in range(31))], 0.0028,
                  color=steel_hi)
    # etched emblem (pale fleur) on the upper chest
    ex = lambda x, z: body_pt(x, z, 0.0015)
    K.loft([(ex(0.0, z), 0.0065 * math.sin(math.pi * (z - 1.47) / 0.13) + 0.002, 0.0018, 0.0018)
            for z in (1.47 + 0.13 * i / 16 for i in range(17))], 10, etch, True, True)
    for s in (-1, 1):
        for (r0, z0, sc) in ((0.0, 1.535, 1.0), (0.0, 1.49, 0.75)):
            curl = [ex(s * (0.006 + 0.03 * sc * math.sin(f * 2.6)), z0 + 0.03 * sc * math.cos(f * 2.6) - 0.012 * sc)
                    for f in (i / 14 for i in range(15))]
            K.loft([(p, 0.0042 * sc + 0.001, 0.0016, 0.0016) for p in curl], 8, etch, True, True)
        tip = [ex(s * (0.005 + 0.022 * f), 1.57 + 0.025 * math.sin(f * math.pi * 0.8)) for f in (i / 10 for i in range(11))]
        K.loft([(p, 0.0035, 0.0015, 0.0015) for p in tip], 8, etch, True, True)
    K.loft([(ex(x, 1.468), 0.004, 0.0016, 0.0016) for x in (-0.03, -0.015, 0.0, 0.015, 0.03)], 8, etch, True, True)
    # back: centre seam, strap + square buckle between the shoulder blades
    surf_line([(0.0, z) for z in (1.20 + 0.26 * i / 20 for i in range(21))], 0.0025, back=True, color=steel_hi)
    strap = [body_pt(0.0, z, 0.003, back=True) for z in (1.47 + 0.15 * i / 10 for i in range(11))]
    K.loft([(p, 0.016, 0.003, 0.003) for p in strap], 4, leather, True, True, front=Vector((0, 0, 1)))
    bb = body_pt(0.0, 1.54, 0.008, back=True)
    K.rim([bb + Vector((0.021 * math.copysign(abs(math.cos(a)) ** 0.35, math.cos(a)), 0,
                        0.018 * math.copysign(abs(math.sin(a)) ** 0.35, math.sin(a)))) for a in
           (2 * math.pi * i / 32 for i in range(32))], 0.0035, 8, steel_hi)

    # ---- belt at 1.16
    K.part('Belt')
    BZ, BCY = 1.20, -0.028

    def belt_pt(a, z, extra=0.0):
        return Vector(((0.176 + extra) * math.cos(a), BCY + ((0.140 if math.sin(a) < 0 else 0.126) + extra) * math.sin(a), z))
    K.loft2([(Vector((0, BCY, BZ - 0.025)), 0.174, 0.138, 0.124), (Vector((0, BCY, BZ)), 0.178, 0.142, 0.128),
             (Vector((0, BCY, BZ + 0.025)), 0.174, 0.138, 0.124)], 96, leather, False, False, sub=2)
    for z in (BZ - 0.024, BZ + 0.024):
        K.rim([belt_pt(2 * math.pi * i / 96, z, -0.001) for i in range(96)], 0.0035, 8, flat((0.08, 0.035, 0.015)))
    for a in (-math.pi / 2 - 0.8, math.pi / 2 + 0.55, math.pi / 2 - 0.55):
        p = belt_pt(a, BZ, 0.004); nrm = (p - Vector((0, BCY, BZ))).normalized()
        K.rbox(p, (0.011, 0.005, 0.034), Matrix.Rotation(math.atan2(nrm.x, -nrm.y), 3, 'Z'), color=leather, segs=16, rings=10)
    ab = -math.pi / 2 + 0.33           # buckle on the character's left of centre
    bc = belt_pt(ab, BZ, 0.006); brot = Matrix.Rotation(math.atan2(bc.x, -(bc.y - BCY)), 3, 'Z')
    K.rim([bc + brot @ Vector((0.022 * math.copysign(abs(math.cos(a)) ** 0.4, math.cos(a)), 0,
                               0.026 * math.copysign(abs(math.sin(a)) ** 0.4, math.sin(a)))) for a in
           (2 * math.pi * i / 32 for i in range(32))], 0.0045, 10, gold)
    K.loft([(bc + brot @ Vector((-0.02, -0.002, 0)), 0.0028, 0.0028, 0.0028),
            (bc + brot @ Vector((0.008, -0.004, 0)), 0.0028, 0.0028, 0.0028)], 8, gold, True, True)
    tail = [belt_pt(ab + 0.045 * i, BZ, 0.004) for i in range(4)]
    K.loft([(p, 0.004, 0.02, 0.02) for p in tail], 4, leather, True, True, front=Vector((0, 0, 1)))
    # pouch on the right hip
    pc = Vector((-0.172, -0.112, 1.105)); prot = Matrix.Rotation(math.radians(-30), 3, 'Z')
    K.rbox(pc, (0.056, 0.038, 0.07), prot, color=leather, segs=32, rings=16)
    K.rbox(pc + prot @ Vector((0, -0.018, 0.042)), (0.059, 0.025, 0.036), prot @ Matrix.Rotation(0.22, 3, 'X'),
           color=leather, segs=32, rings=16)
    K.ellipsoid(pc + prot @ Vector((0, -0.043, 0.012)), (0.009, 0.006, 0.009), prot, segs=12, rings=8, color=gold)
    for sx in (-0.032, 0.032):
        K.rbox(pc + prot @ Vector((sx, -0.012, 0.092)), (0.009, 0.006, 0.03), prot, color=leather, segs=12, rings=8)

    # ---- fauld skirt: 3 lames, narrow front arch, wide back arch
    K.part('Skirt')
    ZT = BZ - 0.022

    def z_bot(a):            # rounded (semi-elliptic) arches: front +-0.075 m wide, back +-0.15 m
        s_ = math.sin(a); x = 0.2 * math.cos(a)
        if s_ < 0:
            t = 1 - (x / 0.075) ** 2
            return 0.915 + (1.12 - 0.915) * math.sqrt(t) if t > 0 else 0.915
        # back: no arch -- the skirt hangs a little lower over the seat so the buttocks are covered (user request)
        t = max(0.0, 1 - (x / 0.2) ** 2)
        return 0.915 - 0.035 * t * s_

    S = 192

    def skirt_ring(frac, extra):
        pts = []
        for i in range(S):
            a = 2 * math.pi * i / S; c, s_ = math.cos(a), math.sin(a)
            z = ZT + (z_bot(a) - ZT) * frac
            g = frac
            rx = 0.172 + 0.03 * g + extra
            ry = (0.136 + 0.026 * g if s_ < 0 else 0.122 + 0.045 * g) + extra
            pts.append(Vector((rx * c, BCY + ry * s_, z)))
        return pts
    for k, (f0, f1) in enumerate(((0.0, 0.42), (0.36, 0.72), (0.66, 1.0))):
        e = 0.003 * k
        rows = [skirt_ring(f0, e), skirt_ring((f0 + f1) / 2, e + 0.003), skirt_ring(f1, e + 0.004)]
        verts = [v for r in rows for v in r]
        faces = [(r * S + i, r * S + (i + 1) % S, (r + 1) * S + (i + 1) % S, (r + 1) * S + i) for r in range(2) for i in range(S)]
        K.faces(verts, faces, steel)
        edge = [p + (p - Vector((0, BCY, p.z))).normalized() * 0.003 for p in rows[-1]]
        K.rim(edge, 0.0075 if k == 2 else 0.003, 10, gold if k == 2 else steel_hi)
    # under the skirt: steel hip shell, crotch cup, seat lobes, dark filler
    K.part('Underlayer')
    K.loft2([(Vector((0, -0.022, 1.16)), 0.162, 0.122, 0.118), (Vector((0, -0.02, 1.05)), 0.168, 0.12, 0.124),
             (Vector((0, -0.018, 0.95)), 0.168, 0.11, 0.118)], 64, pad, False, True, sub=3)
    K.ellipsoid(Vector((0, -0.085, 1.0)), (0.068, 0.05, 0.115), segs=48, rings=24, color=dark_steel)
    for s in (-1, 1):
        # seat plates, now kept inside the closed back skirt (only seen from below)
        K.ellipsoid(Vector((0.065 * s, 0.035, 0.955)), (0.08, 0.06, 0.085), segs=48, rings=24, color=steel)
    for side, s in (('l', 1), ('r', -1)):
        K.loft2([(H(f'upperarm_{side}'), 0.046, 0.046, 0.046), (H(f'lowerarm_{side}'), 0.044, 0.044, 0.044),
                 (H(f'hand_{side}'), 0.036, 0.036, 0.036)], 24, pad, True, True, sub=4)
        K.loft2([(H(f'thigh_{side}') + Vector((0, -0.02, -0.03)), 0.062, 0.062, 0.062), (H(f'calf_{side}'), 0.058, 0.058, 0.058),
                 (H(f'foot_{side}') + Vector((0, 0, 0.03)), 0.04, 0.04, 0.04)], 24, pad, True, True, sub=4)

    # ---- vambraces + gauntlets (copied weights)
    for side, s in (('l', 1), ('r', -1)):
        K.part(f'Gauntlet_{side.upper()}')
        h0 = H(f'hand_{side}'); m0 = H(f'middle_01_{side}')
        dirv = m0 - h0; L = dirv.length; dirv.normalize()
        across = (H(f'index_01_{side}') - H(f'pinky_01_{side}')).normalized()
        nrm = dirv.cross(across).normalized()
        if nrm.dot(Vector((s, 0, 0.3))) < 0:
            nrm = -nrm
        rot = Matrix((across, dirv, nrm)).transposed()
        K.rbox(h0 + dirv * (L * 0.55), (0.044, L * 0.62, 0.022), rot, color=glove, p=0.6, segs=32, rings=16)
        K.ellipsoid(h0 + dirv * (L * 0.5) + nrm * 0.012, (0.043, L * 0.6, 0.016), rot, segs=40, rings=16,
                    color=steel, zmin=0.0)
        for kk in range(2):     # two lames across the back of the hand
            K.rim([h0 + dirv * (L * (0.25 + 0.3 * kk)) + rot @ Vector((0.043 * math.cos(t), 0, 0.017 * math.sin(t) + 0.013))
                   for t in (math.pi * i / 20 for i in range(21))], 0.0026, 8, steel_hi, closed=False)
        for f in ('index', 'middle', 'ring', 'pinky', 'thumb'):
            a = H(f'{f}_01_{side}'); b = H(f'{f}_02_{side}'); tip = T(f'{f}_02_{side}')
            tip = b + (tip - b).normalized() * max((tip - b).length, 0.03)
            r = 0.0115 if f == 'thumb' else 0.0105
            K.loft2([(a, r, r, r), (a.lerp(b, 0.5), r * 0.97, r * 0.97, r * 0.97), (b, r * 0.93, r * 0.93, r * 0.93),
                     (tip, r * 0.78, r * 0.78, r * 0.78)], 16, glove, True, True, sub=2)
            for q0, q1, rr in ((a, a.lerp(b, 0.85), r * 1.2), (b, b.lerp(tip, 0.8), r * 1.1)):   # steel finger plates
                dd = (q1 - q0)
                K.ellipsoid(q0.lerp(q1, 0.5) + nrm * r * 0.4, (rr, dd.length * 0.6, rr * 0.75),
                            Matrix((across, dd.normalized(), nrm)).transposed(), segs=20, rings=10, color=steel, zmin=0.0)
        K.part(f'Vambrace_{side.upper()}')
        la = H(f'lowerarm_{side}'); d = (h0 - la).normalized()
        K.loft2([(la + d * 0.03, 0.057, 0.06, 0.057), (la.lerp(h0, 0.45), 0.061, 0.064, 0.061),
                 (h0 - d * 0.045, 0.054, 0.056, 0.054), (h0 - d * 0.015, 0.064, 0.064, 0.064), (h0 + d * 0.012, 0.078, 0.078, 0.078)],
                64, steel, True, False, sub=4, ridge=0.07)
        K.band(h0 - d * 0.05, d, 0.057, 0.059, width=0.014, sides=64)
        K.rim(ploop(h0 + d * 0.012, d, 0.079, 0.079, 64), 0.0045, 10, gold)
        K.rim(ploop(la + d * 0.04, d, 0.06, 0.063, 64), 0.0035, 10, gold)

    # ================================================================ arms: rigid plates
    for side, s in (('l', 1), ('r', -1)):
        ua = H(f'upperarm_{side}'); la = H(f'lowerarm_{side}'); d = (la - ua).normalized()
        # pauldron shell with a crest (front view: peak ~1.72 at x ~0.2; side view: round)
        K.piece({f'clavicle_{side}': 0.35, f'upperarm_{side}': 0.65}); K.part(f'Pauldron_{side.upper()}')
        pc_ = Vector((0.228 * s, 0.012, 1.548)); pr = (0.10, 0.104, 0.145)       # ~15% smaller than first v4
        XL = -0.3

        def crest(v, s=s):      # top sheared toward the neck (high inner peak); outer lower edge droops over the arm
            xl = v.x * s
            z = v.z - 0.4 * max(0.0, xl) ** 2 * (1 - max(0.0, v.z))
            z -= 1.0 * max(0.0, xl) ** 1.5 * max(0.0, v.z)        # outer top slopes down toward the arm
            return Vector((v.x - s * 0.3 * max(0.0, v.z) ** 1.6 + s * 0.08 * max(0.0, xl) * max(0.0, -v.z), v.y, z))
        prot = Matrix.Identity(3)
        zc = -0.45
        K.ellipsoid(pc_, pr, prot, segs=96, rings=48, color=steel, zmin=zc, shape=crest)
        rr = math.sqrt(1 - zc * zc)
        rim_l = []
        for a in (2 * math.pi * i / 96 for i in range(96)):
            v = crest(Vector((rr * math.cos(a), rr * math.sin(a), zc)))
            rim_l.append(pc_ + prot @ Vector((v.x * pr[0], v.y * pr[1], v.z * pr[2])))
        K.rim(rim_l, 0.0085, 12, gold)
        # lames down the upper arm (gold lower edges)
        K.piece({f'upperarm_{side}': 1.0}); K.part(f'UpperArm_{side.upper()}')
        for k_, (t, r) in enumerate(((0.14, 0.082), (0.30, 0.077), (0.46, 0.073))):
            c0 = ua.lerp(la, t)
            K.loft2([(c0 - d * 0.04, r * 0.96, r * 0.96, r * 0.96), (c0, r, r, r), (c0 + d * 0.045, r * 1.03, r * 1.03, r * 1.03)],
                    72, steel, False, False, sub=2)
            K.rim(ploop(c0 + d * 0.045, d, r * 1.03 + 0.002, None, 72), 0.005, 10, gold)
        K.loft2([(ua.lerp(la, 0.55), 0.07, 0.07, 0.07), (ua.lerp(la, 0.75), 0.068, 0.068, 0.068),
                 (ua.lerp(la, 0.93), 0.064, 0.064, 0.064)], 64, steel, False, False, sub=3)
        # couter: big cop + gold ring + fan wing
        K.piece({f'upperarm_{side}': 0.45, f'lowerarm_{side}': 0.55}); K.part(f'Elbow_{side.upper()}')
        cc = la + Vector((0, 0.016, 0)); cr = (0.068, 0.07, 0.068)
        K.ellipsoid(cc, cr, segs=64, rings=32, color=steel)
        yo = 0.036; kk = math.sqrt(1 - (yo / cr[1]) ** 2)
        K.rim([cc + Vector((cr[0] * kk * math.cos(t), yo, cr[2] * kk * math.sin(t))) for t in
               (2 * math.pi * i / 64 for i in range(64))], 0.006, 10, gold)
        wing_rot = Matrix.Rotation(math.radians(90 * s), 3, 'Y')
        K.dome(la + Vector((0.066 * s, 0.012, 0.0)), (0.058, 0.066, 0.018), wing_rot, -0.1, segs=64, rings=16, rim_r=0.006)

    # ================================================================ legs
    for side, s in (('l', 1), ('r', -1)):
        th = H(f'thigh_{side}'); ca = H(f'calf_{side}'); ft = H(f'foot_{side}')
        dl = (ca - th).normalized(); off = Vector((0, -0.012, 0))
        K.piece({f'thigh_{side}': 1.0}); K.part(f'Thigh_{side.upper()}')
        K.loft2([(th + off + dl * 0.02, 0.092, 0.094, 0.084), (th.lerp(ca, 0.45) + off, 0.085, 0.089, 0.078),
                 (ca + off - dl * 0.115, 0.063, 0.064, 0.06)], 72, steel, True, True, sub=6, ridge=0.05)
        K.rim(ploop(ca + off - dl * 0.12, dl, 0.065, 0.066, 72), 0.003, 8, steel_hi)
        # knee: lens-shaped cop with full gold border, side wing
        K.piece({f'thigh_{side}': 0.3, f'calf_{side}': 0.7}); K.part(f'Knee_{side.upper()}')
        krot = Matrix.Rotation(math.radians(90), 3, 'X')       # local z -> -Y (forward), local y -> up
        kc = ca + Vector((0, -0.06, 0.02)); kr = (0.086, 0.106, 0.052); zc = 0.04

        def lens(v):
            return Vector((v.x * (1 - 0.35 * abs(v.y) ** 1.5), v.y, v.z))
        K.ellipsoid(kc, kr, krot, segs=72, rings=36, color=steel, zmin=zc, shape=lens)
        rr = math.sqrt(1 - zc * zc)
        K.rim([kc + krot @ Vector((kr[0] * rr * math.cos(a) * (1 - 0.35 * abs(math.sin(a) * rr) ** 1.5),
                                   kr[1] * rr * math.sin(a), kr[2] * zc)) for a in (2 * math.pi * i / 72 for i in range(72))],
              0.0075, 12, gold)
        K.ellipsoid(kc + Vector((0, -0.05, 0)), (0.024, 0.008, 0.03), segs=24, rings=12, color=steel_hi)
        K.dome(ca + Vector((0.058 * s, -0.018, 0.0)), (0.04, 0.05, 0.013),
               Matrix.Rotation(math.radians(90 * s), 3, 'Y') @ Matrix.Rotation(math.radians(15 * s), 3, 'X'), -0.1,
               segs=48, rings=12, rim_r=0.0045)
        dc = (ft - ca).normalized()
        K.piece({f'calf_{side}': 1.0}); K.part(f'Shin_{side.upper()}')
        K.loft2([(ca + dc * 0.105, 0.061, 0.064, 0.062), (ca.lerp(ft, 0.33), 0.066, 0.072, 0.07),
                 (ca.lerp(ft, 0.72), 0.052, 0.056, 0.051), (ft + Vector((0, 0, 0.058)), 0.049, 0.053, 0.049)], 72, steel,
                True, False, sub=6, ridge=0.08)
        K.rim(ploop(ca + dc * 0.105, dc, 0.062, 0.065, 72), 0.003, 8, steel_hi)
        K.rivet(ca.lerp(ft, 0.85) + Vector((0, 0.05, 0)), Vector((0, 1, 0)), r=0.006, color=gold)
        K.piece({f'foot_{side}': 1.0}); K.part(f'Foot_{side.upper()}')
        x = ft.x + 0.004 * s
        K.band(ft + Vector((0, 0.0, 0.058)), UP, 0.051, 0.055, width=0.018, sides=64)
        prof = [(0.07, 0.048, 0.07), (0.02, 0.06, 0.125), (-0.05, 0.06, 0.09)]
        K.loft2([(Vector((x, y, h / 2 + 0.003)), w, h / 2, h / 2) for y, w, h in prof], 64, steel, True, False, sub=4,
                front=UP)
        for i, (y0, y1, w0, h0_, w1, h1) in enumerate(((-0.04, -0.09, 0.062, 0.09, 0.058, 0.074),
                                                      (-0.08, -0.13, 0.058, 0.074, 0.053, 0.06),
                                                      (-0.12, -0.168, 0.053, 0.06, 0.046, 0.047))):
            K.loft2([(Vector((x, y0, h0_ / 2 + 0.003)), w0, h0_ / 2, h0_ / 2),
                     (Vector((x, y1, h1 / 2 + 0.003)), w1, h1 / 2, h1 / 2)], 64, steel, False, False, sub=2, front=UP)
            K.rim([Vector((x + (w1 + 0.001) * math.cos(a), y1, h1 / 2 + 0.003 + (h1 / 2 + 0.001) * math.sin(a)))
                   for a in (2 * math.pi * j / 64 for j in range(64)) if math.sin(a) > -0.6], 0.0035, 8,
                  gold if i == 0 else steel_hi, closed=False)
        K.loft2([(Vector((x, -0.163, 0.025)), 0.047, 0.022, 0.022), (Vector((x, -0.2, 0.019)), 0.036, 0.017, 0.017),
                 (Vector((x, -0.232, 0.012)), 0.014, 0.009, 0.009)], 64, steel, False, True, sub=3, front=UP)
    K.open_faces = K.thicken_open()
    return K


def run(target_tris=400000):
    K = build()
    ob = make_object(K)
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    if tris > target_tris:
        dm = ob.modifiers.new('dec', 'DECIMATE'); dm.ratio = target_tris / tris; dm.use_collapse_triangulate = True
        bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_move_to_index(modifier='dec', index=0)
        bpy.ops.object.modifier_apply(modifier='dec')
        bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    unweighted = sum(1 for v in ob.data.vertices if not v.groups)
    return ob.name, tris, unweighted
