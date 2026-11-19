# Player knight v2 (~50k tris): same design as v1 (gen_player_knight.py: bean head with sprout, silver plate armour,
# gold trims, brown belt + pouch) with smooth high-resolution shapes and detail: layered lames, rolled gold rims,
# rivets, chest emblem, belt loops / buckle / straps, segmented gauntlet fingers with knuckle caps, knee and elbow
# wings, segmented sabatons. Colours are still written as vertex colours (RGB albedo, A metallic) and then BAKED to
# textures by bake_player_knight.py. Skinning: same rigid / copied-weight system as v1 (make_object from v1).
import bpy, bmesh, math
from mathutils import Vector, Matrix

V1 = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Blender\scripts\characters\gen_player_knight.py"
exec(open(V1, encoding='utf-8').read())          # Kit, colour functions, make_object, constants

# softer fake lighting in the albedo (real AO is baked on top)
def steel(p, n):
    return mix((0.46, 0.48, 0.52), (0.80, 0.82, 0.85), 0.5 + 0.5 * n.z), 0.55


def steel_hi(p, n):
    return mix((0.62, 0.64, 0.67), (0.92, 0.93, 0.95), 0.5 + 0.5 * n.z), 0.55


def gold(p, n):
    return mix((0.55, 0.34, 0.10), (0.85, 0.60, 0.22), 0.5 + 0.5 * n.z), 0.75


def leather(p, n):
    return mix((0.10, 0.045, 0.018), (0.20, 0.10, 0.045), 0.5 + 0.5 * n.z), 0.0


def skin(p, n):
    return mix((0.70, 0.38, 0.25), (0.84, 0.52, 0.36), 0.55 + 0.45 * n.z), 0.0


def dark_steel(p, n):
    return mix((0.13, 0.135, 0.15), (0.26, 0.27, 0.29), 0.5 + 0.5 * n.z), 0.5


def catmull(p0, p1, p2, p3, t):
    t2, t3 = t * t, t * t * t
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)


class Kit2(Kit):
    def loft2(self, rings, sides=28, color=steel, cap0=True, cap1=True, sub=3, ridge=0.0, cyclic=False,
              front=Vector((0, -1, 0))):
        """rings: (point, rx, ry_front, ry_back); sub = rings inserted between control rings (Catmull-Rom)."""
        n = len(rings)
        if sub and n >= 2 and not cyclic:
            pts = [r[0] for r in rings]; vals = [Vector(r[1:]) for r in rings]
            ext_p = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
            ext_v = [vals[0]] + vals + [vals[-1]]
            out = []
            for i in range(n - 1):
                for k in range(sub + 1):
                    t = k / (sub + 1)
                    p = catmull(ext_p[i], ext_p[i + 1], ext_p[i + 2], ext_p[i + 3], t)
                    v = catmull(ext_v[i], ext_v[i + 1], ext_v[i + 2], ext_v[i + 3], t)
                    out.append((p, max(v.x, 1e-4), max(v.y, 1e-4), max(v.z, 1e-4)))
            out.append(rings[-1]); rings = out
        if ridge:
            return self._loft_ridge(rings, sides, color, cap0, cap1, ridge, front)
        return self.loft(rings, sides, color, cap0, cap1, cyclic=cyclic, front=front)

    def _loft_ridge(self, rings, sides, color, cap0, cap1, ridge, front):
        n = len(rings); verts = []
        for k, (p, rx, ryf, ryb) in enumerate(rings):
            a = rings[max(k - 1, 0)][0]; b = rings[min(k + 1, n - 1)][0]
            d = (b - a).normalized()
            fy = front - d * front.dot(d); fy.normalize(); fx = fy.cross(d).normalized()
            for s in range(sides):
                ang = 2 * math.pi * s / sides; c, sn = math.cos(ang), math.sin(ang)
                ry = ryf if sn > 0 else ryb
                bump = 1 + ridge * max(0.0, sn) ** 14            # sharp-ish ridge down the front centre
                verts.append(p + fx * (c * rx) + fy * (sn * ry * bump))
        faces = []
        for k in range(n - 1):
            for s in range(sides):
                s2 = (s + 1) % sides
                faces.append((k * sides + s, (k + 1) * sides + s, (k + 1) * sides + s2, k * sides + s2))
        if cap0:
            verts.append(rings[0][0].copy()); c0 = len(verts) - 1
            faces += [(c0, (s + 1) % sides, s) for s in range(sides)]
        if cap1:
            verts.append(rings[-1][0].copy()); c1 = len(verts) - 1; o = (n - 1) * sides
            faces += [(c1, o + s, o + (s + 1) % sides) for s in range(sides)]
        return self.faces(verts, faces, color)

    def rim(self, pts, r=0.006, sides=8, color=gold, closed=True):
        """rolled edge: thin tube through pts."""
        if closed:
            return self.loft([(p, r, r, r) for p in pts], sides, color, cyclic=True, front=Vector((0, 0, 1)))
        return self.loft([(p, r, r, r) for p in pts], sides, color, True, True, front=Vector((0, 0, 1)))

    def rivet(self, p, nrm, r=0.0075, color=steel_hi):
        z = nrm.normalized(); x = z.orthogonal().normalized(); y = z.cross(x)
        rot = Matrix((x, y, z)).transposed()
        return self.ellipsoid(p, (r, r, r * 0.7), rot, segs=10, rings=6, color=color, zmin=0.0)

    def dome(self, c, r, rot, zc, segs=40, rings=16, color=steel, rim_r=0.007, rim_color=gold, rivets=0,
             rivet_from=0.0):
        """cut ellipsoid shell + rolled rim along the cut + rivets just above the rim."""
        self.ellipsoid(c, r, rot, segs=segs, rings=rings, color=color, zmin=zc)
        rr = math.sqrt(max(1 - zc * zc, 0.0))
        loop = [c + rot @ Vector((r[0] * rr * math.cos(a), r[1] * rr * math.sin(a), r[2] * zc))
                for a in (2 * math.pi * i / segs for i in range(segs))]
        self.rim(loop, rim_r, 8, rim_color)
        if rivets:
            z2 = zc + 0.18; rr2 = math.sqrt(max(1 - z2 * z2, 0.0))
            for i in range(rivets):
                a = rivet_from + 2 * math.pi * i / rivets
                lp = Vector((r[0] * rr2 * math.cos(a), r[1] * rr2 * math.sin(a), r[2] * z2))
                nl = Vector((lp.x / r[0] ** 2, lp.y / r[1] ** 2, lp.z / r[2] ** 2)).normalized()
                self.rivet(c + rot @ lp, rot @ nl)

    def rbox(self, c, size, rot=Matrix.Identity(3), color=leather, segs=24, rings=12, p=0.35):
        """rounded box (super-ellipsoid)."""
        def sq(v):
            return Vector(tuple(math.copysign(abs(x) ** p, x) for x in v))
        return self.ellipsoid(c, size, rot, segs=segs, rings=rings, color=color, shape=sq)

    def band(self, centre, axis, rx, ry, width=0.02, sides=32, color=gold, flare=0.004, rolled=True):
        """gold band: short ring + rolled rims on both edges."""
        self.ring(centre, axis, rx, ry, width=width, sides=sides, color=color, flare=flare)
        if rolled:
            ax = axis.normalized()
            fy = Vector((0, -1, 0)) - ax * ax.y * -1 if abs(ax.y) < 0.9 else Vector((0, 0, 1))
            fy = (Vector((0, -1, 0)) - ax * Vector((0, -1, 0)).dot(ax))
            if fy.length < 1e-3:
                fy = Vector((0, 0, 1)) - ax * ax.z
            fy.normalize(); fx = fy.cross(ax).normalized()
            for off in (-width / 2, width / 2):
                loop = [centre + ax * off + fx * (math.cos(a) * (rx + 0.002)) + fy * (math.sin(a) * (ry + 0.002))
                        for a in (2 * math.pi * i / sides for i in range(sides))]
                self.rim(loop, 0.0035, 6, color)


def build():
    arm = bpy.data.objects[ARM]; Mw = arm.matrix_world
    H = lambda b: Mw @ arm.data.bones[b].head_local
    T = lambda b: Mw @ arm.data.bones[b].tail_local
    K = Kit2()
    UP = Vector((0, 0, 1))

    # ================= head, face, sprout (rigid neck_02)
    K.piece({'neck_02': 1.0})
    hc = Vector((0, -0.005, 1.735)); hr = (0.122, 0.112, 0.165)

    def bean(v):
        k = 1.0 - 0.13 * max(0.0, -v.z)
        return Vector((v.x * k, v.y * (0.92 if v.y < 0 else 1.0) * k, v.z))

    def skin_c(p, n):   # soft cheek blush
        c, m = skin(p, n)
        blush = max(0.0, 1 - ((abs(p.x) - 0.075) ** 2 + (p.z - 1.695) ** 2) / 0.0012) * (1 if p.y < hc.y else 0)
        return mix(c, (0.85, 0.36, 0.28), blush * 0.45), m
    K.ellipsoid(hc, hr, segs=56, rings=36, color=skin_c, shape=bean)

    def face_y(x, z):
        vz = (z - hc.z) / hr[2]; k = 1.0 - 0.13 * max(0.0, -vz)
        q = 1 - (x / (hr[0] * k)) ** 2 - vz ** 2
        return hc.y - hr[1] * 0.92 * k * math.sqrt(max(q, 0.0))
    for s in (-1, 1):
        ex, ez = 0.043 * s, 1.728
        K.ellipsoid(Vector((ex, face_y(ex, ez) + 0.002, ez)), (0.011, 0.006, 0.016), segs=16, rings=8,
                    color=flat(DARK))
        K.ellipsoid(Vector((ex + 0.003 * s, face_y(ex, ez + 0.006) - 0.0035, ez + 0.006)), (0.003, 0.0015, 0.004),
                    segs=8, rings=4, color=flat((0.9, 0.9, 0.9)))          # eye highlight
        p0 = Vector((0.017 * s, 0, 1.756)); p1 = Vector((0.074 * s, 0, 1.777))
        pts = [p0.lerp(p1, f) + Vector((0, 0, 0.003 * math.sin(f * math.pi))) for f in (0, 0.25, 0.5, 0.75, 1.0)]
        for p in pts:
            p.y = face_y(p.x, p.z) - 0.002
        rings = [(p, 0.0075 * (0.75 + 0.25 * math.sin(i / 4 * math.pi)), 0.004, 0.004) for i, p in enumerate(pts)]
        K.loft(rings, 8, flat(DARK), True, True)
    mpts = [Vector((x, 0, 1.671 + 0.0045 * math.sin(i * 1.15))) for i, x in
            enumerate((-0.028, -0.019, -0.009, 0.0, 0.009, 0.019, 0.028))]
    for p in mpts:
        p.y = face_y(p.x, p.z) - 0.0018
    K.loft([(p, 0.0052, 0.003, 0.003) for p in mpts], 8, flat(DARK), True, True)
    top = Vector((0, hc.y, hc.z + hr[2] - 0.006))
    K.loft2([(top, 0.0095, 0.0095, 0.0095), (top + Vector((0.002, 0, 0.03)), 0.008, 0.008, 0.008),
             (top + Vector((0.006, 0.004, 0.058)), 0.0055, 0.0055, 0.0055)], 10, leaf, False, True, sub=3)
    for s in (-1, 1):   # leaves: blade with a midrib
        base = top + Vector((0.006, 0.004, 0.056))
        d = Vector((s * 0.9, 0.0, 0.45)).normalized()
        side = Vector((0, 1, 0)); nrm = d.cross(side).normalized()
        verts = []; faces = []
        NL, NW = 10, 5
        for i in range(NL + 1):
            t = i / NL
            w = 0.022 * math.sin(math.pi * min(1, t * 1.05)) ** 0.8
            curl = 0.012 * t * t
            for j in range(NW + 1):
                u = -1 + 2 * j / NW
                verts.append(base + d * (0.058 * t) + side * (u * w) + nrm * (curl - 0.004 * abs(u) + 0.0))
        for i in range(NL):
            for j in range(NW):
                a = i * (NW + 1) + j
                faces.append((a, a + 1, a + NW + 2, a + NW + 1))
        K.faces(verts, faces, leaf)
        # back side (two-sided look with a one-sided material)
        K.faces([v - nrm * 0.0015 for v in verts], [tuple(reversed(f)) for f in faces], leaf)

    # ================= gorget: three lames with rolled gold top + rivets
    K.piece({'spine_05': 0.5, 'neck_01': 0.5})
    for k, (z0, z1, r0, r1) in enumerate(((1.455, 1.50, 0.145, 0.128), (1.49, 1.535, 0.128, 0.118),
                                          (1.525, 1.578, 0.118, 0.113))):
        K.loft2([(Vector((0, -0.005, z0)), r0, r0 * 0.9, r0 * 0.86), (Vector((0, -0.006, z1)), r1, r1 * 0.93, r1 * 0.88)],
                40, steel, False, False, sub=2)
        K.rim([Vector((r1 * math.cos(a), -0.006 + (r1 * (0.93 if math.sin(a) < 0 else 0.88)) * math.sin(a), z1))
               for a in (2 * math.pi * i / 40 for i in range(40))], 0.0045 if k < 2 else 0.007, 8,
              gold if k == 2 else steel_hi)
    for a in (-0.6, 0.6, math.pi / 2 + 1.2, math.pi / 2 - 1.2 + math.pi):
        pass
    for i in range(6):
        a = -math.pi / 2 + (i - 2.5) * 0.42
        K.rivet(Vector((0.124 * math.cos(a), -0.006 + 0.112 * math.sin(a), 1.548)), Vector((math.cos(a), math.sin(a), 0.2)))

    # ================= torso (copied weights)
    K.piece('xfer')
    cu = [(0.965, 0.168, 0.125, 0.115, -0.02), (1.06, 0.158, 0.125, 0.11, -0.025),
          (1.18, 0.168, 0.15, 0.115, -0.03), (1.30, 0.188, 0.165, 0.125, -0.025),
          (1.40, 0.192, 0.158, 0.13, -0.015), (1.47, 0.16, 0.13, 0.12, -0.005), (1.505, 0.11, 0.09, 0.09, 0.0)]
    K.loft2([(Vector((0, cy, z)), rx, ryf, ryb) for z, rx, ryf, ryb, cy in cu], 64, steel, True, True, sub=4,
            ridge=0.05)

    def chest_pt(x, z, out=0.0):
        for (z0, rx0, f0, b0, c0), (z1, rx1, f1, b1, c1) in zip(cu, cu[1:]):
            if z0 <= z <= z1:
                t = (z - z0) / (z1 - z0)
                rx = rx0 + (rx1 - rx0) * t; ry = f0 + (f1 - f0) * t; cy = c0 + (c1 - c0) * t
                q = math.sqrt(max(1 - (x / rx) ** 2, 0.0))
                bump = 1 + 0.05 * q ** 14
                return Vector((x, cy - ry * q * bump - out, z))
        return Vector((x, -0.1, z))
    for s in (-1, 1):   # gold V lines collar -> sternum, and armpit curves
        ctrl = [(0.118, 1.455), (0.085, 1.415), (0.045, 1.37), (0.0, 1.33)]
        pts = []
        for i in range(len(ctrl) - 1):
            for f in (0, 0.25, 0.5, 0.75):
                x = ctrl[i][0] + (ctrl[i + 1][0] - ctrl[i][0]) * f; z = ctrl[i][1] + (ctrl[i + 1][1] - ctrl[i][1]) * f
                pts.append(chest_pt(x * s, z, 0.004))
        pts.append(chest_pt(0.0, 1.33, 0.004))
        K.loft([(p, 0.0075, 0.0045, 0.0045) for p in pts], 8, gold, True, True)
        arc = [chest_pt(s * (0.17 - 0.035 * math.sin(f * math.pi)), 1.43 - 0.17 * f, 0.004) for f in
               (i / 10 for i in range(11))]
        K.loft([(p, 0.006, 0.0038, 0.0038) for p in arc], 8, gold, True, True)
    # emblem (stylised fleur): light silver centre lobe + two curls + base bar
    ec = chest_pt(0.0, 1.385, 0.003)
    K.ellipsoid(ec + Vector((0, 0, 0.012)), (0.009, 0.004, 0.022), segs=16, rings=8, color=steel_hi)
    for s in (-1, 1):
        curl = [chest_pt(s * (0.004 + 0.016 * math.sin(f * 2.4)), 1.385 + 0.02 * math.cos(f * 2.4) - 0.006, 0.003)
                for f in (i / 7 for i in range(8))]
        K.loft([(p, 0.0042, 0.0028, 0.0028) for p in curl], 8, steel_hi, True, True)
    K.loft([(chest_pt(x, 1.372, 0.0035), 0.0042, 0.003, 0.003) for x in (-0.017, -0.006, 0.006, 0.017)], 8,
           steel_hi, True, True)
    # belt: band, loops, buckle frame + prong, strap end, pouch with flap + button, hanging straps
    def belt_pt(a, z, extra=0.0):
        return Vector(((0.178 + extra) * math.cos(a), -0.02 + ((0.134 if math.sin(a) < 0 else 0.122) + extra) * math.sin(a), z))
    K.loft2([(Vector((0, -0.02, 0.975)), 0.176, 0.132, 0.12), (Vector((0, -0.02, 1.0)), 0.179, 0.135, 0.123),
             (Vector((0, -0.02, 1.025)), 0.175, 0.131, 0.119)], 56, leather, False, False, sub=2)
    for z in (0.976, 1.024):
        K.rim([belt_pt(2 * math.pi * i / 56, z, -0.001) for i in range(56)], 0.0035, 6, flat(LEATHER_D))
    for a in (-math.pi / 2 + 0.75, -math.pi / 2 - 0.75, math.pi / 2 + 0.6, math.pi / 2 - 0.6):
        p = belt_pt(a, 1.0, 0.004); nrm = (p - Vector((0, -0.02, 1.0))).normalized()
        K.rbox(p, (0.011, 0.005, 0.031), Matrix.Rotation(math.atan2(nrm.x, -nrm.y), 3, 'Z'), color=leather, segs=12, rings=8)
    bc = belt_pt(-math.pi / 2, 1.0, 0.006)
    frame = [bc + Vector((0.026 * math.copysign(abs(math.cos(a)) ** 0.5, math.cos(a)), 0,
                          0.022 * math.copysign(abs(math.sin(a)) ** 0.5, math.sin(a)))) for a in
             (2 * math.pi * i / 24 for i in range(24))]
    K.rim(frame, 0.0042, 8, gold)
    K.loft([(bc + Vector((-0.024, -0.002, 0)), 0.003, 0.003, 0.003), (bc + Vector((0.006, -0.004, 0)), 0.003, 0.003, 0.003)],
           6, gold, True, True)
    strap = [belt_pt(-math.pi / 2 + 0.06 * i, 1.0, 0.004) for i in range(5)]
    K.loft([(p, 0.004, 0.018, 0.018) for p in strap], 4, leather, True, True, front=Vector((0, 0, 1)))
    pc = Vector((-0.178, -0.075, 0.928)); prot = Matrix.Rotation(math.radians(-25), 3, 'Z')
    K.rbox(pc, (0.036, 0.028, 0.044), prot, color=leather)
    K.rbox(pc + prot @ Vector((0, -0.012, 0.024)), (0.038, 0.02, 0.022), prot @ Matrix.Rotation(0.25, 3, 'X'),
           color=flat(LEATHER_D))
    K.ellipsoid(pc + prot @ Vector((0, -0.032, 0.008)), (0.006, 0.004, 0.006), prot, segs=10, rings=6, color=gold)
    # faulds: two overlapping lames, front arch, rolled gold bottom edge
    for k, (zt, zb, rt, rb, arch) in enumerate(((0.975, 0.905, 1.0, 1.06, 0.06), (0.915, 0.84, 1.06, 1.13, 0.09))):
        S = 56; top_r = []; bot_r = []
        for i in range(S):
            a = 2 * math.pi * i / S; c, s_ = math.cos(a), math.sin(a)
            fr = max(0.0, -s_)
            top_r.append(Vector((0.172 * rt * c, -0.02 + (0.128 if s_ < 0 else 0.118) * rt * s_, zt + arch * fr ** 3 * 0.6 * k)))
            bot_r.append(Vector((0.172 * rb * c, -0.02 + (0.128 if s_ < 0 else 0.118) * rb * s_, zb + arch * fr ** 3)))
        mid_r = [a.lerp(b, 0.5) + (a.lerp(b, 0.5) - Vector((0, -0.02, a.z))).normalized() * 0.004 for a, b in zip(top_r, bot_r)]
        rows = [top_r, mid_r, bot_r]
        verts = [v for r in rows for v in r]
        faces = [(r * S + i, r * S + (i + 1) % S, (r + 1) * S + (i + 1) % S, (r + 1) * S + i) for r in range(2) for i in range(S)]
        K.faces(verts, faces, steel)
        K.rim([p + (p - Vector((0, -0.02, p.z))).normalized() * 0.004 for p in bot_r], 0.0065, 8, gold)
    # padding / mail under the armour
    K.ellipsoid(Vector((0, -0.02, 0.89)), (0.165, 0.12, 0.09), segs=32, rings=16, color=cloth)
    for side, s in (('l', 1), ('r', -1)):
        K.loft2([(H(f'upperarm_{side}'), 0.042, 0.042, 0.042), (H(f'lowerarm_{side}'), 0.04, 0.04, 0.04),
                 (H(f'hand_{side}'), 0.036, 0.036, 0.036)], 16, cloth, True, True, sub=3)
        K.loft2([(H(f'thigh_{side}') + Vector((0, -0.02, -0.03)), 0.058, 0.058, 0.058), (H(f'calf_{side}'), 0.05, 0.05, 0.05),
                 (H(f'foot_{side}') + Vector((0, 0, 0.03)), 0.04, 0.04, 0.04)], 16, cloth, True, True, sub=3)
    # gauntlets + vambraces (copied weights: fingers curl, forearm twists)
    for side, s in (('l', 1), ('r', -1)):
        h0 = H(f'hand_{side}'); m0 = H(f'middle_01_{side}')
        dirv = m0 - h0; L = dirv.length; dirv.normalize()
        across = (H(f'index_01_{side}') - H(f'pinky_01_{side}')).normalized()
        nrm = dirv.cross(across).normalized()
        if nrm.dot(Vector((s, 0, 0.3))) < 0:   # back of the hand faces outward/up
            nrm = -nrm
        rot = Matrix((across, dirv, nrm)).transposed()
        K.rbox(h0 + dirv * (L * 0.55), (0.043, L * 0.6, 0.021), rot, color=flat((0.10, 0.06, 0.035)), p=0.6)
        K.ellipsoid(h0 + dirv * (L * 0.55) + nrm * 0.012, (0.04, L * 0.55, 0.014), rot, segs=24, rings=10,
                    color=dark_steel, zmin=0.0)                                       # back-of-hand plate
        for f in ('index', 'middle', 'ring', 'pinky', 'thumb'):
            a = H(f'{f}_01_{side}'); b = H(f'{f}_02_{side}'); tip = T(f'{f}_02_{side}')
            tip = b + (tip - b).normalized() * max((tip - b).length, 0.03)
            r = 0.0115 if f == 'thumb' else 0.0105
            K.loft2([(a, r, r, r), (a.lerp(b, 0.5), r * 0.97, r * 0.97, r * 0.97), (b, r * 0.93, r * 0.93, r * 0.93),
                     (tip, r * 0.8, r * 0.8, r * 0.8)], 10, dark_steel, True, True, sub=1)
            for q, rr in ((a, r * 1.25), (b, r * 1.15)):        # knuckle caps
                K.ellipsoid(q + nrm * r * 0.45, (rr, rr, rr * 0.7), rot, segs=12, rings=6, color=steel, zmin=0.0)
        la = H(f'lowerarm_{side}'); d = (h0 - la).normalized()
        K.loft2([(la + d * 0.03, 0.056, 0.058, 0.056), (la.lerp(h0, 0.5), 0.059, 0.061, 0.059),
                 (h0 - d * 0.04, 0.054, 0.055, 0.054), (h0 - d * 0.012, 0.06, 0.06, 0.06), (h0 + d * 0.008, 0.07, 0.07, 0.07)],
                36, steel, True, False, sub=3, ridge=0.08)
        K.band(h0 - d * 0.042, d, 0.057, 0.058, width=0.016, sides=36)
        K.rim([h0 + d * 0.008 + Vector(v) for v in []], 0.004) if False else None

    # ================= limbs: rigid plates
    for side, s in (('l', 1), ('r', -1)):
        ua = H(f'upperarm_{side}'); la = H(f'lowerarm_{side}'); d = (la - ua).normalized()
        K.piece({f'clavicle_{side}': 0.35, f'upperarm_{side}': 0.65})
        for k, (off, r, tilt, zc, riv) in enumerate(((Vector((0.0, 0.0, 0.04)), (0.145, 0.15, 0.11), 22, -0.25, 3),
                                                    (Vector((0.06, 0.0, -0.045)), (0.12, 0.135, 0.08), 40, -0.2, 0),
                                                    (Vector((0.085, 0.0, -0.09)), (0.1, 0.118, 0.06), 52, -0.15, 0))):
            c = ua + Vector((off.x * s, off.y, off.z))
            rot = Matrix.Rotation(math.radians(-tilt * s), 3, 'Y')
            K.dome(c, r, rot, zc, segs=48, rings=18, rim_r=0.0075 if k == 0 else 0.006, rivets=riv,
                   rivet_from=math.pi / 2 if s > 0 else math.pi / 2)
        # rounded raised flange on the neck side of the pauldron (blunt, not spiky)
        fc = ua + Vector((-0.045 * s, 0.0, 0.135))
        frot = Matrix.Rotation(math.radians(15 * s), 3, 'Y')
        K.ellipsoid(fc, (0.012, 0.11, 0.05), frot, segs=32, rings=12, color=steel, zmin=-0.3)
        K.rim([fc + frot @ Vector((0, 0.11 * math.cos(a), 0.05 * max(math.sin(a), -0.3) + 0.002)) for a in
               (math.pi * i / 20 for i in range(21))], 0.006, 8, gold, closed=False)
        # rerebrace: two overlapping lames with gold bands
        K.piece({f'upperarm_{side}': 1.0})
        for f0, f1, r0, r1 in ((0.22, 0.6, 0.066, 0.063), (0.55, 0.92, 0.062, 0.058)):
            K.loft2([(ua.lerp(la, f0), r0, r0, r0), (ua.lerp(la, (f0 + f1) / 2), r0 * 1.01, r0 * 1.01, r0 * 1.01),
                     (ua.lerp(la, f1), r1, r1, r1)], 36, steel, True, False, sub=2)
            K.band(ua.lerp(la, f1 - 0.03), d, r1 + 0.002, r1 + 0.002, width=0.016, sides=36)
        # couter + side wing
        K.piece({f'upperarm_{side}': 0.4, f'lowerarm_{side}': 0.6})
        K.ellipsoid(la + Vector((0, 0.012, 0)), (0.06, 0.063, 0.06), segs=32, rings=16, color=steel)
        wing_rot = Matrix.Rotation(math.radians(90), 3, 'Y') if s > 0 else Matrix.Rotation(math.radians(-90), 3, 'Y')
        wc = la + Vector((0.058 * s, 0.01, 0.0))
        K.dome(wc, (0.05, 0.055, 0.016), wing_rot, -0.1, segs=36, rings=10, rim_r=0.005)

        th = H(f'thigh_{side}'); ca = H(f'calf_{side}'); ft = H(f'foot_{side}')
        dl = (ca - th).normalized(); off = Vector((0, -0.012, 0))
        K.piece({f'thigh_{side}': 1.0})
        K.loft2([(th + off + dl * 0.03, 0.088, 0.09, 0.08), (th.lerp(ca, 0.5) + off, 0.083, 0.087, 0.076),
                 (ca + off - dl * 0.07, 0.066, 0.07, 0.062)], 40, steel, True, True, sub=4, ridge=0.06)
        K.piece({f'thigh_{side}': 0.3, f'calf_{side}': 0.7})
        K.ellipsoid(ca + Vector((0, -0.045, 0.005)), (0.062, 0.043, 0.068), segs=36, rings=16, color=steel)
        K.dome(ca + Vector((0.05 * s, -0.025, 0.0)), (0.045, 0.05, 0.015),
               Matrix.Rotation(math.radians(90 * s), 3, 'Y') @ Matrix.Rotation(math.radians(20 * s), 3, 'X'), -0.1,
               segs=32, rings=10, rim_r=0.0045)
        K.band(ca + Vector((0, -0.01, 0.068)), dl, 0.065, 0.067, width=0.016, sides=36)
        K.band(ca + Vector((0, -0.01, -0.062)), dl, 0.061, 0.063, width=0.016, sides=36)
        dc = (ft - ca).normalized()
        K.piece({f'calf_{side}': 1.0})
        K.loft2([(ca + dc * 0.06, 0.06, 0.066, 0.06), (ca.lerp(ft, 0.35), 0.064, 0.071, 0.066),
                 (ca.lerp(ft, 0.75), 0.052, 0.056, 0.05), (ft + Vector((0, 0, 0.01)), 0.05, 0.054, 0.05)], 40, steel,
                True, False, sub=4, ridge=0.1)
        K.piece({f'foot_{side}': 1.0})
        x = ft.x + 0.004 * s
        K.band(ft + Vector((0, 0.0, 0.03)), UP, 0.056, 0.06, width=0.02, sides=36)
        # sabaton: heel/ankle shell + three overlapping lames + toe cap
        prof = [(0.07, 0.048, 0.07), (0.02, 0.06, 0.12), (-0.05, 0.06, 0.085)]
        K.loft2([(Vector((x, y, h / 2 + 0.003)), w, h / 2, h / 2) for y, w, h in prof], 32, steel, True, False, sub=3,
                front=UP)
        for i, (y0, y1, w0, h0_, w1, h1) in enumerate(((-0.04, -0.095, 0.062, 0.088, 0.058, 0.07),
                                                      (-0.085, -0.14, 0.058, 0.07, 0.053, 0.056),
                                                      (-0.13, -0.18, 0.053, 0.056, 0.046, 0.044))):
            K.loft2([(Vector((x, y0, h0_ / 2 + 0.003)), w0, h0_ / 2, h0_ / 2),
                     (Vector((x, y1, h1 / 2 + 0.003)), w1, h1 / 2, h1 / 2)], 32, steel, False, False, sub=1, front=UP)
            K.rim([Vector((x + (w1 + 0.001) * math.cos(a), y1, h1 / 2 + 0.003 + (h1 / 2 + 0.001) * math.sin(a)))
                   for a in (2 * math.pi * j / 32 for j in range(32)) if math.sin(a) > -0.6], 0.0035, 6,
                  steel_hi, closed=False)
        K.loft2([(Vector((x, -0.175, 0.024)), 0.047, 0.022, 0.022), (Vector((x, -0.205, 0.02)), 0.038, 0.018, 0.018),
                 (Vector((x, -0.228, 0.016)), 0.02, 0.012, 0.012)], 32, steel, False, True, sub=2, front=UP)
    return K


def run(target_tris=50000):
    K = build()
    ob = make_object(K)
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    if tris > target_tris:   # collapse-decimate to the budget (keeps weights, colours, silhouettes of dense lofts)
        dm = ob.modifiers.new('dec', 'DECIMATE'); dm.ratio = target_tris / tris; dm.use_collapse_triangulate = True
        bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_move_to_index(modifier='dec', index=0)
        bpy.ops.object.modifier_apply(modifier='dec')
        bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    unweighted = sum(1 for v in ob.data.vertices if not v.groups)
    return ob.name, tris, unweighted
