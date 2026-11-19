# Player knight SKM_PlayerKnight: low-poly stylized armour + bean head with a sprout, skinned to the UE mannequin.
# Needs the scene from Export/Reference/SKM_Manny_Simple.fbx (armature 'root' = UE root bone, mesh
# 'SKM_Manny_Simple.001' used as the weight source and for proportions). Character faces -Y, left = +X, metres.
#
# Pieces are lofts / ellipsoids / rings built straight into one bmesh. Vertex colour RGB = albedo (sRGB-encoded),
# A = metallic (steel/gold 1, leather/skin/cloth 0) -> material M_Stylized_Character.
# Skinning per piece: rigid {bone: weight} for hard plates (no stretching), or 'xfer' = weights copied from the
# mannequin body (torso, waist, gauntlets, under-padding) so they bend with the joints.
import bpy, bmesh, math
from mathutils import Vector, Matrix

ARM = 'root'
SRC = 'SKM_Manny_Simple.001'
NAME = 'SKM_PlayerKnight'

STEEL_D = (0.30, 0.32, 0.35); STEEL_L = (0.80, 0.82, 0.85)
GOLD = (0.78, 0.52, 0.18); GOLD_D = (0.45, 0.27, 0.07)
LEATHER = (0.16, 0.075, 0.03); LEATHER_D = (0.07, 0.03, 0.012)
SKIN = (0.80, 0.47, 0.32); SKIN_D = (0.62, 0.30, 0.19)
DARK = (0.035, 0.022, 0.02)
CLOTH = (0.05, 0.05, 0.06)
LEAF = (0.10, 0.36, 0.03); LEAF_L = (0.30, 0.62, 0.08)


def lin2srgb(c):
    return c * 12.92 if c <= 0.0031308 else 1.055 * max(c, 0.0) ** (1 / 2.4) - 0.055


def mix(a, b, t):
    t = max(0.0, min(1.0, t)); return tuple(x + (y - x) * t for x, y in zip(a, b))


# ---- colour functions: f(position, normal) -> (rgb, metallic)
# metallic < 1: fully metallic steel mirrors the environment and goes dark on sideways faces (stylized = soft metal)
def steel(p, n):
    return mix(STEEL_D, STEEL_L, 0.45 + 0.55 * n.z), 0.55


def gold(p, n):
    return mix(GOLD_D, GOLD, 0.5 + 0.5 * n.z), 0.75


def leather(p, n):
    return mix(LEATHER_D, LEATHER, 0.5 + 0.5 * n.z), 0.0


def skin(p, n):
    return mix(SKIN_D, SKIN, 0.55 + 0.45 * n.z), 0.0


def flat(c, m=0.0):
    return lambda p, n: (c, m)


def cloth(p, n):
    return CLOTH, 0.2


def leaf(p, n):
    return mix(LEAF, LEAF_L, 0.5 + 0.5 * n.z), 0.0


class Kit:
    def __init__(self):
        self.bm = bmesh.new()
        self.col = self.bm.loops.layers.color.new('Col')
        self.pid = self.bm.verts.layers.int.new('piece')
        self.specs = []          # piece id -> weight spec
        self.cur = 0

    def piece(self, spec):
        self.specs.append(spec); self.cur = len(self.specs) - 1

    def faces(self, verts, faces, color):
        vs = [self.bm.verts.new(v) for v in verts]
        for v in vs:
            v[self.pid] = self.cur
        out = []
        for fi in faces:
            try:
                f = self.bm.faces.new([vs[i] for i in fi])
            except ValueError:
                continue
            f.smooth = True; out.append(f)
        # consistent outward normals (lofts along downward limbs came out inverted -> dark, wrong colour gradient)
        bmesh.ops.recalc_face_normals(self.bm, faces=out)
        self.bm.normal_update()
        for f in out:
            for l in f.loops:
                rgb, m = color(l.vert.co, l.vert.normal)
                l[self.col] = (lin2srgb(rgb[0]), lin2srgb(rgb[1]), lin2srgb(rgb[2]), m)
        return out

    # ---- loft along a polyline; rings: list of (point, rx, ry_front, ry_back) ; ellipse in plane _|_ direction,
    # 'front' axis = -Y projected (so ry_front bulges toward the character's front)
    def loft(self, rings, sides=10, color=steel, cap0=True, cap1=True, cyclic=False, front=Vector((0, -1, 0))):
        n = len(rings); verts = []
        for k, (p, rx, ryf, ryb) in enumerate(rings):
            a = rings[(k - 1) % n][0] if (cyclic or k > 0) else p
            b = rings[(k + 1) % n][0] if (cyclic or k < n - 1) else p
            d = (b - a).normalized() if (b - a).length > 1e-6 else Vector((0, 0, 1))
            fy = (front - d * front.dot(d))
            if fy.length < 1e-4:
                fy = Vector((0, 0, 1)) - d * d.z
            fy.normalize(); fx = fy.cross(d).normalized()
            for s in range(sides):
                ang = 2 * math.pi * s / sides
                c, sn = math.cos(ang), math.sin(ang)
                ry = ryf if sn > 0 else ryb
                verts.append(p + fx * (c * rx) + fy * (sn * ry))
        faces = []
        segs = n if cyclic else n - 1
        for k in range(segs):
            k2 = (k + 1) % n
            for s in range(sides):
                s2 = (s + 1) % sides
                faces.append((k * sides + s, k2 * sides + s, k2 * sides + s2, k * sides + s2))
        if not cyclic:
            if cap0:
                verts.append(rings[0][0].copy()); c0 = len(verts) - 1
                faces += [(c0, s2, s) for s, s2 in ((s, (s + 1) % sides) for s in range(sides))]
            if cap1:
                verts.append(rings[-1][0].copy()); c1 = len(verts) - 1
                o = (n - 1) * sides
                faces += [(c1, o + s, o + (s + 1) % sides) for s in range(sides)]
        return self.faces(verts, faces, color)

    def tube(self, a, b, r0, r1, sides=10, color=steel, mid=None, caps=True):
        rings = [(a, r0, r0, r0)]
        if mid:
            for f, r in mid:
                rings.append((a.lerp(b, f), r, r, r))
        rings.append((b, r1, r1, r1))
        return self.loft(rings, sides, color, caps, caps)

    def ring(self, centre, axis, rx, ry=None, width=0.018, sides=12, color=gold, flare=0.004):
        ry = ry or rx; ax = axis.normalized()
        return self.loft([(centre - ax * width / 2, rx, ry, ry), (centre, rx + flare, ry + flare, ry + flare),
                          (centre + ax * width / 2, rx, ry, ry)], sides, color, False, False)

    def ellipsoid(self, c, r, rot=Matrix.Identity(3), segs=12, rings=8, color=steel, zmin=-1.0, shape=None):
        """r = (rx, ry, rz). zmin: cut below this normalised height (-1 = full). shape(local)->local tweak."""
        verts = []; faces = []
        lat = [(-math.pi / 2 + math.pi * i / rings) for i in range(rings + 1)]
        lat = [l for l in lat if math.sin(l) >= zmin - 1e-6]
        if zmin > -1 and math.sin(lat[0]) > zmin + 1e-6:
            lat.insert(0, math.asin(zmin))
        top = len(lat) - 1
        for i, la in enumerate(lat):
            ring_n = 1 if i == top or (i == 0 and zmin <= -1) else segs
            for s in range(ring_n):
                lo = 2 * math.pi * s / segs
                v = Vector((math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)))
                if shape:
                    v = shape(v)
                verts.append(c + rot @ Vector((v.x * r[0], v.y * r[1], v.z * r[2])))
        idx = []; k = 0
        for i, la in enumerate(lat):
            ring_n = 1 if i == top or (i == 0 and zmin <= -1) else segs
            idx.append(list(range(k, k + ring_n))); k += ring_n
        for i in range(len(idx) - 1):
            A, Bv = idx[i], idx[i + 1]
            for s in range(segs):
                s2 = (s + 1) % segs
                if len(A) == 1:
                    faces.append((A[0], Bv[s2], Bv[s]))
                elif len(Bv) == 1:
                    faces.append((A[s], A[s2], Bv[0]))
                else:
                    faces.append((A[s], A[s2], Bv[s2], Bv[s]))
        return self.faces(verts, faces, color)


def build():
    arm = bpy.data.objects[ARM]; Mw = arm.matrix_world
    H = lambda b: Mw @ arm.data.bones[b].head_local
    T = lambda b: Mw @ arm.data.bones[b].tail_local
    K = Kit()

    # ---------------- head (bean), face, sprout : rigid neck_02
    K.piece({'neck_02': 1.0})
    hc = Vector((0, -0.005, 1.735)); hr = (0.122, 0.112, 0.165)

    def bean(v):   # narrower at the bottom, slightly flat face
        k = 1.0 - 0.13 * max(0.0, -v.z)
        y = v.y * (0.92 if v.y < 0 else 1.0)
        return Vector((v.x * k, y * k, v.z))
    K.ellipsoid(hc, hr, segs=16, rings=10, color=skin, shape=bean)

    def face_y(x, z):   # front surface of the bean at (x, z)
        vz = (z - hc.z) / hr[2]; k = 1.0 - 0.13 * max(0.0, -vz)
        q = 1 - (x / (hr[0] * k)) ** 2 - vz ** 2
        return hc.y - hr[1] * 0.92 * k * math.sqrt(max(q, 0.0))
    for s in (-1, 1):
        ex = 0.043 * s; ez = 1.728
        K.ellipsoid(Vector((ex, face_y(ex, ez) + 0.002, ez)), (0.011, 0.006, 0.016), segs=8, rings=4,
                    color=flat(DARK))
        # angry brows: inner end low
        p0 = Vector((0.018 * s, 0, 1.757)); p1 = Vector((0.072 * s, 0, 1.776))
        pts = [p0.lerp(p1, f) for f in (0.0, 0.5, 1.0)]
        for p in pts:
            p.y = face_y(p.x, p.z) - 0.002
        K.loft([(p, 0.007, 0.004, 0.004) for p in pts], 4, flat(DARK), True, True)
    mpts = [Vector((x, 0, 1.672 + 0.004 * math.sin(i * 2.2))) for i, x in enumerate((-0.026, -0.009, 0.009, 0.026))]
    for p in mpts:
        p.y = face_y(p.x, p.z) - 0.002
    K.loft([(p, 0.0055, 0.003, 0.003) for p in mpts], 4, flat(DARK), True, True)
    top = Vector((0, hc.y, hc.z + hr[2] - 0.006))
    K.loft([(top, 0.009, 0.009, 0.009), (top + Vector((0.002, 0, 0.03)), 0.008, 0.008, 0.008),
            (top + Vector((0.006, 0.004, 0.055)), 0.006, 0.006, 0.006)], 6, leaf, False, True)
    for s in (-1, 1):
        rot = Matrix.Rotation(math.radians(30 * s), 3, 'Y') @ Matrix.Rotation(math.radians(-15), 3, 'X')
        K.ellipsoid(top + Vector((0.028 * s + 0.006, 0.004, 0.058)), (0.03, 0.016, 0.006), rot, segs=8, rings=4,
                    color=leaf)

    # ---------------- gorget : spine_05 / neck_01
    K.piece({'spine_05': 0.5, 'neck_01': 0.5})
    K.loft([(Vector((0, 0.0, 1.46)), 0.14, 0.125, 0.12), (Vector((0, -0.005, 1.515)), 0.118, 0.11, 0.105),
            (Vector((0, -0.008, 1.575)), 0.112, 0.105, 0.1)], 14, steel, False, False)
    K.ring(Vector((0, -0.008, 1.575)), Vector((0, 0, 1)), 0.113, 0.104, width=0.016, sides=14)

    # ---------------- cuirass, chest trims, belt, faulds, padding : copied weights
    K.piece('xfer')
    cu = [(0.97, 0.168, 0.125, 0.115, -0.02), (1.06, 0.158, 0.125, 0.11, -0.025), (1.18, 0.168, 0.15, 0.115, -0.03),
          (1.30, 0.188, 0.165, 0.125, -0.025), (1.40, 0.192, 0.158, 0.13, -0.015), (1.47, 0.16, 0.13, 0.12, -0.005),
          (1.505, 0.11, 0.09, 0.09, 0.0)]
    K.loft([(Vector((0, cy, z)), rx, ryf, ryb) for z, rx, ryf, ryb, cy in cu], 16, steel, True, True)

    def chest_y(x, z):
        for (z0, rx0, f0, b0, c0), (z1, rx1, f1, b1, c1) in zip(cu, cu[1:]):
            if z0 <= z <= z1:
                t = (z - z0) / (z1 - z0)
                rx = rx0 + (rx1 - rx0) * t; ry = f0 + (f1 - f0) * t; cy = c0 + (c1 - c0) * t
                return cy - ry * math.sqrt(max(1 - (x / rx) ** 2, 0.0))
        return -0.1
    for s in (-1, 1):   # gold V lines from the collar to the sternum
        pts = [Vector((0.115 * s, 0, 1.455)), Vector((0.06 * s, 0, 1.39)), Vector((0.0, 0, 1.33))]
        for p in pts:
            p.y = chest_y(p.x, p.z) - 0.004
        K.loft([(p, 0.008, 0.004, 0.004) for p in pts], 4, gold, True, True)
    # belt + buckle + pouch
    K.loft([(Vector((0, -0.02, 0.975)), 0.176, 0.132, 0.12), (Vector((0, -0.02, 1.0)), 0.178, 0.134, 0.122),
            (Vector((0, -0.02, 1.025)), 0.174, 0.13, 0.118)], 16, leather, False, False)
    K.ellipsoid(Vector((0, -0.02 - 0.136, 1.0)), (0.032, 0.008, 0.026), segs=8, rings=4, color=gold)
    K.ellipsoid(Vector((-0.172, -0.07, 0.93)), (0.035, 0.03, 0.045), segs=8, rings=6, color=leather)
    K.ellipsoid(Vector((-0.172, -0.085, 0.955)), (0.038, 0.022, 0.022), segs=8, rings=4, color=flat(LEATHER_D))
    # faulds: flared skirt with a front arch, gold bottom edge
    sides = 16; top_r = []; bot_r = []
    for i in range(sides):
        a = 2 * math.pi * i / sides
        c, s_ = math.cos(a), math.sin(a)
        frontness = max(0.0, -s_)
        top_r.append(Vector((0.172 * c, -0.02 + (0.128 if s_ < 0 else 0.118) * s_, 0.975)))
        zb = 0.845 + 0.085 * frontness ** 3
        bot_r.append(Vector((0.198 * c, -0.02 + (0.15 if s_ < 0 else 0.14) * s_, zb)))
    verts = top_r + bot_r
    faces = [(i, (i + 1) % sides, sides + (i + 1) % sides, sides + i) for i in range(sides)]
    K.faces(verts, faces, steel)
    K.loft([(p + (p - Vector((0, -0.02, p.z))).normalized() * 0.006, 0.008, 0.008, 0.008) for p in bot_r],
           4, gold, cyclic=True, front=Vector((0, 0, 1)))
    # dark padding under the armour (fills the joints)
    K.ellipsoid(Vector((0, -0.02, 0.89)), (0.165, 0.12, 0.09), segs=12, rings=6, color=cloth)
    for side, s in (('l', 1), ('r', -1)):
        # follow the bones through the joint (a straight shoulder->hand tube ran 10 cm in front of the elbow)
        K.loft([(H(f'upperarm_{side}'), 0.042, 0.042, 0.042), (H(f'lowerarm_{side}'), 0.04, 0.04, 0.04),
                (H(f'hand_{side}'), 0.036, 0.036, 0.036)], 8, cloth, True, True)
        K.loft([(H(f'thigh_{side}') + Vector((0, -0.02, -0.03)), 0.058, 0.058, 0.058),
                (H(f'calf_{side}'), 0.05, 0.05, 0.05), (H(f'foot_{side}') + Vector((0, 0, 0.03)), 0.04, 0.04, 0.04)],
               8, cloth, True, True)
    # gauntlets: palm + fingers, copied weights so the fingers curl
    for side, s in (('l', 1), ('r', -1)):
        h0 = H(f'hand_{side}'); m0 = H(f'middle_01_{side}')
        dirv = (m0 - h0); L = dirv.length; dirv.normalize()
        across = (H(f'index_01_{side}') - H(f'pinky_01_{side}')).normalized()
        nrm = dirv.cross(across).normalized()
        rot = Matrix((across, dirv, nrm)).transposed()
        K.ellipsoid(h0 + dirv * (L * 0.55), (0.042, L * 0.62, 0.022), rot, segs=10, rings=6, color=flat((0.22, 0.23, 0.25), 0.5))
        for f in ('index', 'middle', 'ring', 'pinky'):
            a = H(f'{f}_01_{side}'); b = H(f'{f}_02_{side}'); tip = T(f'{f}_02_{side}')
            tip = b + (tip - b).normalized() * max((tip - b).length, 0.03)
            K.loft([(a, 0.0105, 0.0105, 0.0105), (b, 0.0095, 0.0095, 0.0095), (tip, 0.0085, 0.0085, 0.0085)], 5,
                   flat((0.20, 0.21, 0.23), 0.5), True, True)
        a = H(f'thumb_01_{side}'); b = H(f'thumb_02_{side}'); tip = T(f'thumb_02_{side}')
        tip = b + (tip - b).normalized() * max((tip - b).length, 0.03)
        K.loft([(a, 0.012, 0.012, 0.012), (b, 0.0105, 0.0105, 0.0105), (tip, 0.009, 0.009, 0.009)], 5,
               flat((0.20, 0.21, 0.23), 0.5), True, True)
        # forearm vambrace + wrist cuff (copied weights: follows the twist bones)
        la = H(f'lowerarm_{side}'); ha = h0
        d = (ha - la).normalized()
        K.loft([(la + d * 0.03, 0.056, 0.058, 0.056), (la.lerp(ha, 0.5), 0.058, 0.06, 0.058),
                (ha - d * 0.035, 0.055, 0.055, 0.055), (ha - d * 0.005, 0.064, 0.064, 0.064)], 10, steel, True, False)
        K.ring(ha - d * 0.035, d, 0.06, width=0.018, sides=10)

    # ---------------- limbs: rigid plates
    for side, s in (('l', 1), ('r', -1)):
        ua = H(f'upperarm_{side}'); la = H(f'lowerarm_{side}'); d = (la - ua).normalized()
        cl = H(f'clavicle_{side}')
        # pauldron: two layered domes with gold lips
        K.piece({f'clavicle_{side}': 0.35, f'upperarm_{side}': 0.65})
        out = Vector((s, 0, 0))
        for k, (off, r, tilt, zc) in enumerate(((Vector((0.0, 0.0, 0.04)), (0.145, 0.15, 0.11), 22, -0.25),
                                               (Vector((0.06, 0.0, -0.045)), (0.12, 0.135, 0.08), 40, -0.2))):
            c = ua + Vector((off.x * s, off.y, off.z))
            rot = Matrix.Rotation(math.radians(-tilt * s), 3, 'Y')
            K.ellipsoid(c, r, rot, segs=12, rings=7, color=steel, zmin=zc)
            rim = c + rot @ Vector((0, 0, r[2] * zc))
            rr = math.sqrt(1 - zc * zc)
            K.ring(rim, rot @ Vector((0, 0, 1)), r[0] * rr + 0.004, r[1] * rr + 0.004, width=0.016, sides=12)
        # rerebrace
        K.piece({f'upperarm_{side}': 1.0})
        K.tube(ua + d * 0.07, la - d * 0.025, 0.064, 0.057, 10, steel)
        K.ring(ua + (la - ua) * 0.45, d, 0.066, width=0.018, sides=10)
        K.ring(ua + (la - ua) * 0.8, d, 0.061, width=0.018, sides=10)
        # couter (elbow cop)
        K.piece({f'upperarm_{side}': 0.4, f'lowerarm_{side}': 0.6})
        K.ellipsoid(la + Vector((0, 0.012, 0)), (0.06, 0.062, 0.06), segs=10, rings=6, color=steel)

        th = H(f'thigh_{side}'); ca = H(f'calf_{side}'); ft = H(f'foot_{side}')
        dl = (ca - th).normalized(); off = Vector((0, -0.012, 0))
        K.piece({f'thigh_{side}': 1.0})
        K.loft([(th + off + dl * 0.03, 0.088, 0.09, 0.08), (th.lerp(ca, 0.5) + off, 0.082, 0.085, 0.075),
                (ca + off - dl * 0.07, 0.066, 0.07, 0.062)], 10, steel, True, True)
        K.piece({f'thigh_{side}': 0.3, f'calf_{side}': 0.7})
        K.ellipsoid(ca + Vector((0, -0.045, 0.005)), (0.062, 0.042, 0.068), segs=10, rings=6, color=steel)
        K.ring(ca + Vector((0, -0.01, 0.065)), dl, 0.064, 0.066, width=0.016, sides=10)
        K.ring(ca + Vector((0, -0.01, -0.06)), dl, 0.06, 0.062, width=0.016, sides=10)
        dc = (ft - ca).normalized()
        K.piece({f'calf_{side}': 1.0})
        K.loft([(ca + dc * 0.06, 0.06, 0.066, 0.06), (ca.lerp(ft, 0.35), 0.064, 0.07, 0.066),
                (ca.lerp(ft, 0.75), 0.052, 0.056, 0.05), (ft + Vector((0, 0, 0.01)), 0.05, 0.054, 0.05)], 10, steel,
               True, False)
        # sabaton (foot points -Y), tall at the ankle so it overlaps the greave
        K.piece({f'foot_{side}': 1.0})
        x = ft.x
        prof = [(0.07, 0.048, 0.07), (0.02, 0.06, 0.12), (-0.05, 0.06, 0.085), (-0.13, 0.054, 0.058),
                (-0.195, 0.042, 0.04), (-0.226, 0.024, 0.024)]
        rings = [(Vector((x + 0.004 * s, y, h / 2 + 0.003)), w, h / 2, h / 2) for y, w, h in prof]
        K.loft(rings, 10, steel, True, True, front=Vector((0, 0, 1)))
        K.ring(ft + Vector((0, 0.0, 0.03)), Vector((0, 0, 1)), 0.056, 0.06, width=0.02, sides=10)
    return K


def make_object(K):
    arm = bpy.data.objects[ARM]
    old = bpy.data.objects.get(NAME)
    if old:
        m = old.data; bpy.data.objects.remove(old, do_unlink=True); bpy.data.meshes.remove(m)
    me = bpy.data.meshes.new(NAME)
    pid_layer = K.bm.verts.layers.int.get('piece')
    pids = [v[pid_layer] for v in K.bm.verts]
    K.bm.to_mesh(me); K.bm.free()
    mat = bpy.data.materials.get('M_Stylized_Character') or bpy.data.materials.new('M_Stylized_Character')
    mat.use_nodes = True; nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    if not any(n.type == 'VERTEX_COLOR' for n in nt.nodes):
        vc = nt.nodes.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'
        nt.links.new(vc.outputs['Color'], bsdf.inputs['Base Color'])
        nt.links.new(vc.outputs['Alpha'], bsdf.inputs['Metallic'])
        bsdf.inputs['Roughness'].default_value = 0.45
    me.materials.append(mat)
    ob = bpy.data.objects.new(NAME, me)
    bpy.context.scene.collection.objects.link(ob)
    # world metres -> armature space (the armature carries the 0.01 scale), parent without inverse
    inv = arm.matrix_world.inverted()
    me.transform(inv)
    ob.parent = arm; ob.matrix_parent_inverse = Matrix.Identity(4); ob.matrix_basis = Matrix.Identity(4)
    mod = ob.modifiers.new('Armature', 'ARMATURE'); mod.object = arm

    # ---- weights
    src = bpy.data.objects[SRC]
    xfer = ob.vertex_groups.new(name='XFER')
    xidx = [i for i, p in enumerate(pids) if K.specs[p] == 'xfer']
    xfer.add(xidx, 1.0, 'REPLACE')
    for g in src.vertex_groups:
        if g.name not in ob.vertex_groups:
            ob.vertex_groups.new(name=g.name)
    for spec in K.specs:       # bones used by rigid pieces may have no group on the mannequin mesh
        if spec != 'xfer':
            for bone in spec:
                if bone not in ob.vertex_groups:
                    ob.vertex_groups.new(name=bone)
    dt = ob.modifiers.new('xfer', 'DATA_TRANSFER'); dt.object = src
    dt.use_vert_data = True; dt.data_types_verts = {'VGROUP_WEIGHTS'}; dt.vert_mapping = 'POLYINTERP_NEAREST'
    dt.layers_vgroup_select_src = 'ALL'; dt.layers_vgroup_select_dst = 'NAME'; dt.vertex_group = 'XFER'
    bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_move_to_index(modifier='xfer', index=0)
    bpy.ops.object.modifier_apply(modifier='xfer')
    ob.vertex_groups.remove(ob.vertex_groups['XFER'])
    # rigid pieces
    by_piece = {}
    for i, p in enumerate(pids):
        if K.specs[p] != 'xfer':
            by_piece.setdefault(p, []).append(i)
    for p, idx in by_piece.items():
        for g in ob.vertex_groups:
            g.remove(idx)
        for bone, w in K.specs[p].items():
            ob.vertex_groups[bone].add(idx, w, 'REPLACE')
    bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL', limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL', lock_active=False)
    return ob


def run():
    K = build()
    ob = make_object(K)
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    unweighted = sum(1 for v in ob.data.vertices if not v.groups)
    return ob.name, tris, unweighted
