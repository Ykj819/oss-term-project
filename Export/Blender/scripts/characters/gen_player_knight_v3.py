# Player knight v3: v2 reworked to match the front/side/back turnaround concept (2026-11-20).
# Changes vs v2 (gen_player_knight_v2.py, whose Kit2 / colours / make_object are reused):
#   - darker, more metallic steel (polished mid-grey instead of near-white), richer gold
#   - taller flared gorget with a gold rolled top (head sits in the collar)
#   - bigger pauldrons with 4 gold-edged lames
#   - breastplate: gold plackart arc across the belly, larger emblem; back: gold scapula arcs + leather strap/buckle
#   - fauld skirt: front inverted-U arch (dark crotch visible), long side tassets, rounded culet over the buttocks,
#     gold bottom edge + steel lame lines
#   - knee cops and elbow cops with gold rings, gold top edge on the cuisses, pointed sabatons, gold cuff rims
#   - bigger belt pouch
# Run inside PlayerKnight.blend: exec this file, then run(); then bake_player_knight.run().
import bpy, bmesh, math
from mathutils import Vector, Matrix

V2 = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Blender\scripts\characters\gen_player_knight_v2.py"
exec(open(V2, encoding='utf-8').read())          # Kit2, colour functions, make_object (via v1), constants


# ---- v3 palette. Kit2 methods bind v2's colour functions as default args, so swap their code in place.
def _steel(p, n):
    return mix((0.36, 0.38, 0.42), (0.80, 0.82, 0.86), 0.42 + 0.58 * n.z), 0.8


def _steel_hi(p, n):
    return mix((0.55, 0.57, 0.61), (0.92, 0.93, 0.95), 0.5 + 0.5 * n.z), 0.8


def _gold(p, n):
    return mix((0.50, 0.30, 0.07), (0.88, 0.62, 0.20), 0.45 + 0.55 * n.z), 0.9


def _dark_steel(p, n):
    return mix((0.11, 0.105, 0.105), (0.24, 0.23, 0.22), 0.5 + 0.5 * n.z), 0.45


steel.__code__ = _steel.__code__
steel_hi.__code__ = _steel_hi.__code__
gold.__code__ = _gold.__code__
dark_steel.__code__ = _dark_steel.__code__


def pad(p, n):          # dark quilted padding at the joints / crotch
    return mix((0.06, 0.055, 0.05), (0.13, 0.12, 0.11), 0.5 + 0.5 * n.z), 0.0


def build():
    arm = bpy.data.objects[ARM]; Mw = arm.matrix_world
    H = lambda b: Mw @ arm.data.bones[b].head_local
    T = lambda b: Mw @ arm.data.bones[b].tail_local
    K = Kit2()
    UP = Vector((0, 0, 1))

    # ================= head, face, sprout (rigid neck_02) -- unchanged from v2
    K.piece({'neck_02': 1.0})
    hc = Vector((0, -0.005, 1.735)); hr = (0.122, 0.112, 0.165)

    def bean(v):
        k = 1.0 - 0.13 * max(0.0, -v.z)
        return Vector((v.x * k, v.y * (0.92 if v.y < 0 else 1.0) * k, v.z))

    def skin_c(p, n):
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
                    segs=8, rings=4, color=flat((0.9, 0.9, 0.9)))
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
    for s in (-1, 1):
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
                verts.append(base + d * (0.058 * t) + side * (u * w) + nrm * (curl - 0.004 * abs(u)))
        for i in range(NL):
            for j in range(NW):
                a = i * (NW + 1) + j
                faces.append((a, a + 1, a + NW + 2, a + NW + 1))
        K.faces(verts, faces, leaf)
        K.faces([v - nrm * 0.0015 for v in verts], [tuple(reversed(f)) for f in faces], leaf)

    # ================= gorget: taller, flared collar with a gold rolled top (head sits in it)
    K.piece({'spine_05': 0.45, 'neck_01': 0.55})
    lames = ((1.455, 1.505, 0.148, 0.130), (1.495, 1.545, 0.130, 0.120), (1.535, 1.612, 0.120, 0.132))
    for k, (z0, z1, r0, r1) in enumerate(lames):
        K.loft2([(Vector((0, -0.005, z0)), r0, r0 * 0.9, r0 * 0.86), (Vector((0, -0.007, z1)), r1, r1 * 0.92, r1 * 0.88)],
                44, steel, False, False, sub=2)
        K.rim([Vector((r1 * math.cos(a), -0.007 + (r1 * (0.92 if math.sin(a) < 0 else 0.88)) * math.sin(a), z1))
               for a in (2 * math.pi * i / 44 for i in range(44))], 0.0045 if k < 2 else 0.0085, 8,
              gold if k == 2 else steel_hi)
    for i in range(6):
        a = -math.pi / 2 + (i - 2.5) * 0.42
        K.rivet(Vector((0.126 * math.cos(a), -0.006 + 0.113 * math.sin(a), 1.565)), Vector((math.cos(a), math.sin(a), 0.2)))

    # ================= torso (copied weights)
    K.piece('xfer')
    cu = [(0.965, 0.168, 0.125, 0.115, -0.02), (1.06, 0.158, 0.128, 0.11, -0.025),
          (1.18, 0.170, 0.155, 0.118, -0.03), (1.30, 0.192, 0.172, 0.128, -0.025),
          (1.40, 0.196, 0.162, 0.132, -0.015), (1.47, 0.162, 0.132, 0.122, -0.005), (1.505, 0.11, 0.09, 0.09, 0.0)]
    K.loft2([(Vector((0, cy, z)), rx, ryf, ryb) for z, rx, ryf, ryb, cy in cu], 64, steel, True, True, sub=4,
            ridge=0.05)

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
                return Vector((x, cy - ry * q * (1 + 0.05 * q ** 14) - out, z))
        return Vector((x, -0.1, z))

    def gold_line(pts2d, r=0.0065, back=False, color=None):
        pts = [body_pt(x, z, 0.004, back) for x, z in pts2d]
        K.loft([(p, r, r * 0.6, r * 0.6) for p in pts], 8, color or gold, True, True)

    def sample(ctrl, n=4):
        out = []
        for i in range(len(ctrl) - 1):
            for f in [j / n for j in range(n)]:
                out.append((ctrl[i][0] + (ctrl[i + 1][0] - ctrl[i][0]) * f, ctrl[i][1] + (ctrl[i + 1][1] - ctrl[i][1]) * f))
        out.append(ctrl[-1]); return out
    for s in (-1, 1):
        # collar V to the sternum
        gold_line(sample([(0.118 * s, 1.455), (0.085 * s, 1.415), (0.045 * s, 1.37), (0.0, 1.33)]), 0.0075)
        # armhole curve down the side of the breastplate
        gold_line([(s * (0.175 - 0.04 * math.sin(f * math.pi)), 1.44 - 0.2 * f) for f in (i / 12 for i in range(13))],
                  0.006)
        # back: scapula arcs + armhole curves
        gold_line([(s * (0.04 + 0.12 * math.sin(f * math.pi / 2)), 1.45 - 0.2 * f ** 1.4) for f in
                   (i / 12 for i in range(13))], 0.006, back=True)
    # plackart arc across the belly (U shape)
    gold_line([(x, 1.13 + 0.095 * (x / 0.15) ** 2) for x in (i / 10 * 0.3 - 0.15 for i in range(11))], 0.0065)
    gold_line([(x, 1.12 + 0.08 * (x / 0.15) ** 2) for x in (i / 10 * 0.3 - 0.15 for i in range(11))], 0.0065,
              back=True)
    # chest emblem (larger fleur)
    ec = body_pt(0.0, 1.39, 0.003)
    K.ellipsoid(ec + Vector((0, 0, 0.016)), (0.012, 0.005, 0.03), segs=16, rings=8, color=steel_hi)
    for s in (-1, 1):
        curl = [body_pt(s * (0.005 + 0.022 * math.sin(f * 2.4)), 1.39 + 0.027 * math.cos(f * 2.4) - 0.008, 0.003)
                for f in (i / 8 for i in range(9))]
        K.loft([(p, 0.005, 0.0032, 0.0032) for p in curl], 8, steel_hi, True, True)
    K.loft([(body_pt(x, 1.373, 0.0035), 0.005, 0.0034, 0.0034) for x in (-0.024, -0.008, 0.008, 0.024)], 8,
           steel_hi, True, True)
    # back strap + buckle between the shoulder blades
    bs = body_pt(0.0, 1.36, 0.004, back=True)
    K.rbox(bs, (0.016, 0.006, 0.055), color=leather, segs=12, rings=8, p=0.5)
    bb = body_pt(0.0, 1.385, 0.009, back=True)
    K.rim([bb + Vector((0.017 * math.copysign(abs(math.cos(a)) ** 0.5, math.cos(a)), 0,
                        0.014 * math.copysign(abs(math.sin(a)) ** 0.5, math.sin(a)))) for a in
           (2 * math.pi * i / 20 for i in range(20))], 0.0035, 8, gold)

    # belt: band, loops, buckle frame + prong, strap end, pouch with flap + button
    def belt_pt(a, z, extra=0.0):
        return Vector(((0.178 + extra) * math.cos(a), -0.02 + ((0.134 if math.sin(a) < 0 else 0.122) + extra) * math.sin(a), z))
    K.loft2([(Vector((0, -0.02, 0.972)), 0.177, 0.133, 0.121), (Vector((0, -0.02, 1.0)), 0.180, 0.136, 0.124),
             (Vector((0, -0.02, 1.028)), 0.176, 0.132, 0.120)], 56, leather, False, False, sub=2)
    for z in (0.973, 1.027):
        K.rim([belt_pt(2 * math.pi * i / 56, z, -0.001) for i in range(56)], 0.0035, 6, flat(LEATHER_D))
    for a in (-math.pi / 2 + 0.75, -math.pi / 2 - 0.75, math.pi / 2 + 0.6, math.pi / 2 - 0.6):
        p = belt_pt(a, 1.0, 0.004); nrm = (p - Vector((0, -0.02, 1.0))).normalized()
        K.rbox(p, (0.011, 0.005, 0.033), Matrix.Rotation(math.atan2(nrm.x, -nrm.y), 3, 'Z'), color=leather, segs=12, rings=8)
    bc = belt_pt(-math.pi / 2, 1.0, 0.006)
    K.rim([bc + Vector((0.028 * math.copysign(abs(math.cos(a)) ** 0.5, math.cos(a)), 0,
                        0.024 * math.copysign(abs(math.sin(a)) ** 0.5, math.sin(a)))) for a in
           (2 * math.pi * i / 24 for i in range(24))], 0.0045, 8, gold)
    K.loft([(bc + Vector((-0.026, -0.002, 0)), 0.003, 0.003, 0.003), (bc + Vector((0.006, -0.004, 0)), 0.003, 0.003, 0.003)],
           6, gold, True, True)
    strap = [belt_pt(-math.pi / 2 + 0.06 * i, 1.0, 0.004) for i in range(5)]
    K.loft([(p, 0.004, 0.019, 0.019) for p in strap], 4, leather, True, True, front=Vector((0, 0, 1)))
    pc = Vector((-0.19, -0.07, 0.94)); prot = Matrix.Rotation(math.radians(-28), 3, 'Z')
    K.rbox(pc, (0.045, 0.034, 0.052), prot, color=leather)
    K.rbox(pc + prot @ Vector((0, -0.014, 0.03)), (0.047, 0.024, 0.026), prot @ Matrix.Rotation(0.25, 3, 'X'),
           color=flat(LEATHER_D))
    K.ellipsoid(pc + prot @ Vector((0, -0.039, 0.01)), (0.007, 0.005, 0.007), prot, segs=10, rings=6, color=gold)

    # fauld skirt: two lames; bottom edge = front inverted-U arch, long side tassets, rounded culet at the back
    def skirt_ring(z_of_a, scale, culet, S=72, lift=0.0):
        pts = []
        for i in range(S):
            a = 2 * math.pi * i / S; c, s_ = math.cos(a), math.sin(a)
            ry = (0.128 if s_ < 0 else 0.118 * (1 + culet * s_ ** 2)) * scale
            pts.append(Vector((0.172 * scale * c, -0.02 + ry * s_, z_of_a(a) + lift)))
        return pts

    def z_bottom(a):
        s_ = math.sin(a); fr = max(0.0, -s_); bk = max(0.0, s_)
        return 0.775 + 0.135 * fr ** 4 + 0.085 * bk ** 6     # front arch high, sides long, culet arch at the back

    for k, (f0, f1, sc0, sc1, cul0, cul1) in enumerate(((0.0, 0.52, 1.0, 1.07, 0.05, 0.16),
                                                        (0.46, 1.0, 1.065, 1.14, 0.15, 0.28))):
        zt = lambda a, f=f0: 0.975 + (z_bottom(a) - 0.975) * f
        zb = lambda a, f=f1: 0.975 + (z_bottom(a) - 0.975) * f
        top_r = skirt_ring(zt, sc0, cul0); bot_r = skirt_ring(zb, sc1, cul1)
        S = len(top_r)
        mid_r = [a.lerp(b, 0.5) + (a.lerp(b, 0.5) - Vector((0, -0.02, a.lerp(b, 0.5).z))).normalized() * 0.005
                 for a, b in zip(top_r, bot_r)]
        rows = [top_r, mid_r, bot_r]
        verts = [v for r in rows for v in r]
        faces = [(r * S + i, r * S + (i + 1) % S, (r + 1) * S + (i + 1) % S, (r + 1) * S + i) for r in range(2) for i in range(S)]
        K.faces(verts, faces, steel)
        edge = [p + (p - Vector((0, -0.02, p.z))).normalized() * 0.004 for p in bot_r]
        K.rim(edge, 0.0075 if k == 1 else 0.0045, 8, gold if k == 1 else steel_hi)
    # dark padding under the armour (crotch shows through the front arch)
    K.ellipsoid(Vector((0, -0.02, 0.885)), (0.165, 0.125, 0.095), segs=32, rings=16, color=pad)
    for side, s in (('l', 1), ('r', -1)):
        K.loft2([(H(f'upperarm_{side}'), 0.044, 0.044, 0.044), (H(f'lowerarm_{side}'), 0.042, 0.042, 0.042),
                 (H(f'hand_{side}'), 0.036, 0.036, 0.036)], 16, pad, True, True, sub=3)
        K.loft2([(H(f'thigh_{side}') + Vector((0, -0.02, -0.03)), 0.06, 0.06, 0.06), (H(f'calf_{side}'), 0.054, 0.054, 0.054),
                 (H(f'foot_{side}') + Vector((0, 0, 0.03)), 0.04, 0.04, 0.04)], 16, pad, True, True, sub=3)
    # gauntlets + vambraces (copied weights: fingers curl, forearm twists)
    for side, s in (('l', 1), ('r', -1)):
        h0 = H(f'hand_{side}'); m0 = H(f'middle_01_{side}')
        dirv = m0 - h0; L = dirv.length; dirv.normalize()
        across = (H(f'index_01_{side}') - H(f'pinky_01_{side}')).normalized()
        nrm = dirv.cross(across).normalized()
        if nrm.dot(Vector((s, 0, 0.3))) < 0:
            nrm = -nrm
        rot = Matrix((across, dirv, nrm)).transposed()
        K.rbox(h0 + dirv * (L * 0.55), (0.045, L * 0.62, 0.023), rot, color=flat((0.10, 0.065, 0.04)), p=0.6)
        K.ellipsoid(h0 + dirv * (L * 0.55) + nrm * 0.013, (0.043, L * 0.57, 0.015), rot, segs=24, rings=10,
                    color=dark_steel, zmin=0.0)
        for f in ('index', 'middle', 'ring', 'pinky', 'thumb'):
            a = H(f'{f}_01_{side}'); b = H(f'{f}_02_{side}'); tip = T(f'{f}_02_{side}')
            tip = b + (tip - b).normalized() * max((tip - b).length, 0.03)
            r = 0.012 if f == 'thumb' else 0.011
            K.loft2([(a, r, r, r), (a.lerp(b, 0.5), r * 0.97, r * 0.97, r * 0.97), (b, r * 0.93, r * 0.93, r * 0.93),
                     (tip, r * 0.8, r * 0.8, r * 0.8)], 10, dark_steel, True, True, sub=1)
            for q, rr in ((a, r * 1.25), (b, r * 1.15)):
                K.ellipsoid(q + nrm * r * 0.45, (rr, rr, rr * 0.7), rot, segs=12, rings=6, color=dark_steel, zmin=0.0)
        la = H(f'lowerarm_{side}'); d = (h0 - la).normalized()
        K.loft2([(la + d * 0.03, 0.057, 0.059, 0.057), (la.lerp(h0, 0.5), 0.060, 0.062, 0.060),
                 (h0 - d * 0.04, 0.055, 0.056, 0.055), (h0 - d * 0.012, 0.062, 0.062, 0.062), (h0 + d * 0.01, 0.074, 0.074, 0.074)],
                36, steel, True, False, sub=3, ridge=0.08)
        K.band(h0 - d * 0.045, d, 0.058, 0.059, width=0.016, sides=36)
        K.band(la + d * 0.035, d, 0.059, 0.061, width=0.012, sides=36)
        K.rim([h0 + d * 0.01 + v for v in
               ((lambda fy, fx: [fx * (0.075 * math.cos(t)) + fy * (0.075 * math.sin(t)) for t in
                                 (2 * math.pi * i / 36 for i in range(36))])(
                   (Vector((0, -1, 0)) - d * Vector((0, -1, 0)).dot(d)).normalized(),
                   (Vector((0, -1, 0)) - d * Vector((0, -1, 0)).dot(d)).normalized().cross(d)))], 0.0045, 8, gold)

    # ================= limbs: rigid plates
    for side, s in (('l', 1), ('r', -1)):
        ua = H(f'upperarm_{side}'); la = H(f'lowerarm_{side}'); d = (la - ua).normalized()
        K.piece({f'clavicle_{side}': 0.35, f'upperarm_{side}': 0.65})
        for k, (off, r, tilt, zc, riv) in enumerate(((Vector((0.0, 0.0, 0.042)), (0.152, 0.158, 0.115), 22, -0.25, 3),
                                                    (Vector((0.062, 0.0, -0.045)), (0.126, 0.142, 0.084), 38, -0.2, 0),
                                                    (Vector((0.088, 0.0, -0.092)), (0.104, 0.122, 0.062), 50, -0.15, 0),
                                                    (Vector((0.106, 0.0, -0.135)), (0.086, 0.104, 0.048), 60, -0.12, 0))):
            c = ua + Vector((off.x * s, off.y, off.z))
            rot = Matrix.Rotation(math.radians(-tilt * s), 3, 'Y')
            K.dome(c, r, rot, zc, segs=48, rings=18, rim_r=0.008 if k == 0 else 0.0065, rivets=riv,
                   rivet_from=math.pi / 2)
        # raised, rounded flange on the neck side of the pauldron, gold edge
        fc = ua + Vector((-0.05 * s, 0.0, 0.15))
        frot = Matrix.Rotation(math.radians(15 * s), 3, 'Y')
        K.ellipsoid(fc, (0.013, 0.12, 0.055), frot, segs=32, rings=12, color=steel, zmin=-0.3)
        K.rim([fc + frot @ Vector((0, 0.12 * math.cos(a), 0.055 * max(math.sin(a), -0.3) + 0.002)) for a in
               (math.pi * i / 20 for i in range(21))], 0.0065, 8, gold, closed=False)
        # rerebrace: two overlapping lames with gold bands
        K.piece({f'upperarm_{side}': 1.0})
        for f0, f1, r0, r1 in ((0.25, 0.6, 0.067, 0.064), (0.55, 0.92, 0.063, 0.059)):
            K.loft2([(ua.lerp(la, f0), r0, r0, r0), (ua.lerp(la, (f0 + f1) / 2), r0 * 1.01, r0 * 1.01, r0 * 1.01),
                     (ua.lerp(la, f1), r1, r1, r1)], 36, steel, True, False, sub=2)
            K.band(ua.lerp(la, f1 - 0.03), d, r1 + 0.002, r1 + 0.002, width=0.016, sides=36)
        # couter: big cop with a gold ring + side wing
        K.piece({f'upperarm_{side}': 0.4, f'lowerarm_{side}': 0.6})
        cc = la + Vector((0, 0.014, 0)); cr = (0.066, 0.068, 0.066)
        K.ellipsoid(cc, cr, segs=36, rings=18, color=steel)
        yo = 0.034; k_ = math.sqrt(1 - (yo / cr[1]) ** 2)
        K.rim([cc + Vector((cr[0] * k_ * math.cos(t), yo, cr[2] * k_ * math.sin(t))) for t in
               (2 * math.pi * i / 36 for i in range(36))], 0.0055, 8, gold)
        wing_rot = Matrix.Rotation(math.radians(90 * s), 3, 'Y')
        K.dome(la + Vector((0.064 * s, 0.01, 0.0)), (0.055, 0.06, 0.017), wing_rot, -0.1, segs=36, rings=10, rim_r=0.0055)

        th = H(f'thigh_{side}'); ca = H(f'calf_{side}'); ft = H(f'foot_{side}')
        dl = (ca - th).normalized(); off = Vector((0, -0.012, 0))
        K.piece({f'thigh_{side}': 1.0})
        K.loft2([(th + off + dl * 0.03, 0.090, 0.092, 0.082), (th.lerp(ca, 0.5) + off, 0.084, 0.088, 0.077),
                 (ca + off - dl * 0.07, 0.066, 0.07, 0.062)], 40, steel, True, True, sub=4, ridge=0.06)
        K.band(th.lerp(ca, 0.3) + off, dl, 0.088, 0.091, width=0.014, sides=40)
        # poleyn: round cop with a gold ring facing forward, small side wing
        K.piece({f'thigh_{side}': 0.3, f'calf_{side}': 0.7})
        pc_ = ca + Vector((0, -0.048, 0.005)); pr = (0.068, 0.048, 0.074)
        K.ellipsoid(pc_, pr, segs=36, rings=18, color=steel)
        yo = 0.024; k_ = math.sqrt(1 - (yo / pr[1]) ** 2)
        K.rim([pc_ + Vector((pr[0] * k_ * math.cos(t), -yo, pr[2] * k_ * math.sin(t))) for t in
               (2 * math.pi * i / 36 for i in range(36))], 0.0065, 8, gold)
        K.ellipsoid(pc_ + Vector((0, -0.044, 0)), (0.026, 0.008, 0.028), segs=16, rings=8, color=steel_hi)
        K.dome(ca + Vector((0.052 * s, -0.025, 0.0)), (0.042, 0.048, 0.014),
               Matrix.Rotation(math.radians(90 * s), 3, 'Y') @ Matrix.Rotation(math.radians(20 * s), 3, 'X'), -0.1,
               segs=32, rings=10, rim_r=0.0045)
        K.band(ca + Vector((0, -0.01, 0.075)), dl, 0.066, 0.068, width=0.014, sides=36)
        K.band(ca + Vector((0, -0.01, -0.068)), dl, 0.062, 0.064, width=0.014, sides=36)
        dc = (ft - ca).normalized()
        K.piece({f'calf_{side}': 1.0})
        K.loft2([(ca + dc * 0.06, 0.06, 0.066, 0.06), (ca.lerp(ft, 0.35), 0.064, 0.071, 0.067),
                 (ca.lerp(ft, 0.75), 0.051, 0.055, 0.049), (ft + Vector((0, 0, 0.01)), 0.05, 0.054, 0.05)], 40, steel,
                True, False, sub=4, ridge=0.1)
        K.piece({f'foot_{side}': 1.0})
        x = ft.x + 0.004 * s
        K.band(ft + Vector((0, 0.0, 0.03)), UP, 0.057, 0.061, width=0.02, sides=36)
        # sabaton: heel/ankle shell + three lames + pointed toe cap with a gold edge
        prof = [(0.07, 0.048, 0.07), (0.02, 0.06, 0.12), (-0.05, 0.06, 0.085)]
        K.loft2([(Vector((x, y, h / 2 + 0.003)), w, h / 2, h / 2) for y, w, h in prof], 32, steel, True, False, sub=3,
                front=UP)
        for i, (y0, y1, w0, h0_, w1, h1) in enumerate(((-0.04, -0.095, 0.062, 0.088, 0.058, 0.07),
                                                      (-0.085, -0.14, 0.058, 0.07, 0.052, 0.055),
                                                      (-0.13, -0.18, 0.052, 0.055, 0.044, 0.042))):
            K.loft2([(Vector((x, y0, h0_ / 2 + 0.003)), w0, h0_ / 2, h0_ / 2),
                     (Vector((x, y1, h1 / 2 + 0.003)), w1, h1 / 2, h1 / 2)], 32, steel, False, False, sub=1, front=UP)
            K.rim([Vector((x + (w1 + 0.001) * math.cos(a), y1, h1 / 2 + 0.003 + (h1 / 2 + 0.001) * math.sin(a)))
                   for a in (2 * math.pi * j / 32 for j in range(32)) if math.sin(a) > -0.6], 0.0035, 6,
                  gold if i == 2 else steel_hi, closed=False)
        K.loft2([(Vector((x, -0.175, 0.023)), 0.045, 0.021, 0.021), (Vector((x, -0.205, 0.018)), 0.034, 0.017, 0.017),
                 (Vector((x, -0.228, 0.013)), 0.016, 0.01, 0.01)], 32, steel, False, True, sub=2, front=UP)
    return K


def run(target_tris=55000):
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
