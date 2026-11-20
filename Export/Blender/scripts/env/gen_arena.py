# Stylized colosseum-style arena with 4 gates (N/E/S/W). Re-runnable: deletes collection "Arena" first.
# Run in Blender: exec(open(<this file>, encoding='utf-8').read(), {'__name__': '__main__'})
import bpy, bmesh, math, random, bisect
from mathutils import Vector, Matrix

random.seed(7)
A, B = 46.0, 38.0        # outer wall outer face semi-axes (m)
SEG = 256                # ring segments
NB = 56                  # outer bays (divisible by 4 -> gates on the axes)
GATE_HW = 2.2            # tunnel half width
WALL_T = 2.5


def ell(d, t):
    return Vector(((A - d) * math.cos(t), (B - d) * math.sin(t), 0.0))


def frame(d, t):
    """local x = tangent, local y = inward, z = up, origin on the offset ellipse"""
    a, b = A - d, B - d
    P = Vector((a * math.cos(t), b * math.sin(t), 0))
    T = Vector((-a * math.sin(t), b * math.cos(t), 0)).normalized()
    N = Vector((b * math.cos(t), a * math.sin(t), 0)).normalized()
    M = Matrix.Identity(4)
    for i in range(3):
        M[i][0], M[i][1], M[i][2], M[i][3] = T[i], -N[i], (0, 0, 1)[i], P[i]
    return M


def prism(bm, outline, y0, y1, M):
    f = [bm.verts.new(M @ Vector((x, y0, z))) for x, z in outline]
    k = [bm.verts.new(M @ Vector((x, y1, z))) for x, z in outline]
    bm.faces.new(f)
    bm.faces.new(k[::-1])
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((f[i], f[j], k[j], k[i]))


def box(bm, x0, x1, y0, y1, z0, z1, M=Matrix.Identity(4)):
    prism(bm, [(x0, z0), (x1, z0), (x1, z1), (x0, z1)], y0, y1, M)


def arch_outline(w, h, ow, spring, n=12):
    r = ow / 2
    pts = [(-w / 2, 0), (-r, 0)]
    for i in range(n + 1):
        a = math.pi * (1 - i / n)
        pts.append((r * math.cos(a), spring + r * math.sin(a)))
    return pts + [(r, 0), (w / 2, 0), (w / 2, h), (-w / 2, h)]


def ring(bm, d_in, d_out, z0, z1, keep=None, seg=SEG):
    prof = [(d_in, z0), (d_out, z0), (d_out, z1), (d_in, z1)]
    V = [[bm.verts.new(ell(d, 2 * math.pi * i / seg) + Vector((0, 0, z))) for d, z in prof] for i in range(seg)]
    K = [True] * seg
    if keep:
        for i in range(seg):
            m = ell((d_in + d_out) / 2, 2 * math.pi * (i + .5) / seg)
            K[i] = keep(m.x, m.y)
    for i in range(seg):
        if not K[i]:
            continue
        j = (i + 1) % seg
        for e in range(4):
            e2 = (e + 1) % 4
            bm.faces.new((V[i][e], V[i][e2], V[j][e2], V[j][e]))
        if not K[i - 1]:
            bm.faces.new(V[i])
        if not K[j]:
            bm.faces.new(V[j][::-1])


def gate_keep(hw):
    return lambda x, y: abs(x) > hw and abs(y) > hw


# arc-length table on the outer ellipse
NS = 8192
TS = [2 * math.pi * i / NS for i in range(NS + 1)]
CUM = [0.0]
for i in range(NS):
    CUM.append(CUM[-1] + (ell(0, TS[i + 1]) - ell(0, TS[i])).length)
L = CUM[-1]


def t_at(s):
    s %= L
    i = min(bisect.bisect_right(CUM, s) - 1, NS - 1)
    return TS[i] + (TS[i + 1] - TS[i]) * (s - CUM[i]) / (CUM[i + 1] - CUM[i])


# ---------------------------------------------------------------- materials
def mat(name, c1, c2, scale=0.35, rough=0.9):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type not in ('BSDF_PRINCIPLED', 'OUTPUT_MATERIAL'):
            nt.nodes.remove(n)
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Roughness'].default_value = rough
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = scale
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[1].position = 0.65
    ramp.color_ramp.elements[0].color = (*c2, 1)
    ramp.color_ramp.elements[1].color = (*c1, 1)
    nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    m.diffuse_color = (*c1, 1)
    return m


MATS = {
    'Stone': mat('M_Arena_Stone', (0.105, 0.092, 0.080), (0.070, 0.062, 0.055)),
    'Trim': mat('M_Arena_Trim', (0.150, 0.132, 0.112), (0.110, 0.096, 0.082)),
    'Inner': mat('M_Arena_Inner', (0.060, 0.052, 0.045), (0.042, 0.036, 0.031)),
    'Seats': mat('M_Arena_Seats', (0.120, 0.106, 0.092), (0.085, 0.075, 0.065), scale=0.6),
    'Sand': mat('M_Arena_Sand', (0.150, 0.125, 0.095), (0.110, 0.090, 0.068), scale=0.15),
    'Ground': mat('M_Arena_Ground', (0.065, 0.058, 0.050), (0.050, 0.044, 0.038)),
    'Dark': mat('M_Arena_Dark', (0.035, 0.028, 0.022), (0.03, 0.024, 0.02)),
}

BM = {k: bmesh.new() for k in ('OuterWall', 'Trim', 'Inner', 'Seats', 'Sand', 'Ground', 'Attic', 'Gates', 'Dark')}
MAT_OF = {'OuterWall': 'Stone', 'Trim': 'Trim', 'Inner': 'Inner', 'Seats': 'Seats', 'Sand': 'Sand',
          'Ground': 'Ground', 'Attic': 'Stone', 'Gates': 'Stone', 'Dark': 'Dark'}

# ---------------------------------------------------------------- outer arcade (3 tiers)
TIERS = [  # z0, z1, opening width, spring height
    (0.0, 8.0, 3.0, 4.6),
    (8.6, 15.0, 2.8, 3.4),
    (15.6, 22.0, 2.8, 3.4),
]
W = L / NB * 1.01
for k in range(NB):
    M = frame(0, t_at(k * L / NB))
    gate = k % (NB // 4) == 0
    for ti, (z0, z1, ow, sp) in enumerate(TIERS):
        if ti == 0 and gate:
            ow, sp = 4.0, 4.4
        Mz = M @ Matrix.Translation((0, 0, z0))
        prism(BM['OuterWall'], arch_outline(W, z1 - z0, ow, sp), 0, WALL_T, Mz)
        box(BM['OuterWall'], -W / 2 - 0.3, -W / 2 + 0.3, -0.35, 0, 0, z1 - z0, Mz)   # pilaster
        box(BM['Trim'], -W / 2 - 0.4, -W / 2 + 0.4, -0.45, 0, z1 - z0 - 0.5, z1 - z0, Mz)  # capital

# cornices double as corridor floors / roof
ring(BM['Trim'], 0.0, -0.5, 0.0, 0.6, keep=gate_keep(2.2), seg=512)   # plinth
ring(BM['Trim'], 5.6, -0.4, 8.0, 8.6)
ring(BM['Trim'], 5.6, -0.4, 15.0, 15.6)
ring(BM['Trim'], 6.2, -0.5, 22.0, 22.8)

# ---------------------------------------------------------------- inner structure
ring(BM['Inner'], 22.0, 5.6, 0.0, 4.5, keep=gate_keep(GATE_HW))      # substructure + podium wall
ring(BM['Inner'], 6.2, 5.6, 4.5, 22.0)                               # corridor inner wall
ring(BM['Trim'], 22.0, 21.6, 4.5, 5.5)                               # podium parapet (lintel over tunnels)
ring(BM['Trim'], 22.15, 21.6, 4.2, 4.5)                              # podium cornice

for sx, sy in ((0, 1), (0, -1), (1, 0), (-1, 0)):     # tunnel side walls
    for side in (-1, 1):
        if sx == 0:
            y0, y1 = (B - 22 - 0.5) * sy, (B - WALL_T) * sy
            x0, x1 = sorted((side * (GATE_HW - 0.35), side * (GATE_HW + 0.15)))
            box(BM['Inner'], x0, x1, min(y0, y1), max(y0, y1), 0, 4.5)
        else:
            x0, x1 = (A - 22 - 0.5) * sx, (A - WALL_T) * sx
            y0, y1 = sorted((side * (GATE_HW - 0.35), side * (GATE_HW + 0.15)))
            box(BM['Inner'], min(x0, x1), max(x0, x1), y0, y1, 0, 4.5)

# ---------------------------------------------------------------- cavea (3 tiers of seats, 2 walkways)
STEPS = [5, 5, 4]
WALK, JUMP = 1.2, 1.2
d, z = 21.6, 4.5
RUN = (21.6 - 6.2 - WALK * (len(STEPS) - 1)) / sum(STEPS)
RISE = (21.2 - 4.5 - JUMP * (len(STEPS) - 1)) / sum(STEPS)
for m, n in enumerate(STEPS):
    if m > 0:
        ring(BM['Seats'], d, d - WALK, 4.5, z)
        d -= WALK
        wz = z
        z += JUMP
        for i in range(16):                              # vomitoria (dark doorways in the walkway wall)
            t = 2 * math.pi * (i + 0.5) / 16
            Mv = frame(d, t)
            box(BM['Dark'], -0.7, 0.7, -0.02, 0.05, wz, wz + 1.7, Mv)
    for s in range(n):
        z += RISE
        ring(BM['Seats'], d, d - RUN, 4.5, z)
        d -= RUN

# ---------------------------------------------------------------- floor / ground
HOLE_R, HOLE_D = 3.0, 8.0     # round pit in the middle of the arena floor
sb = BM['Sand']
vo = [sb.verts.new(ell(22.0, 2 * math.pi * i / SEG) + Vector((0, 0, 0.03))) for i in range(SEG)]
vi = [sb.verts.new(Vector((HOLE_R * math.cos(2 * math.pi * i / SEG), HOLE_R * math.sin(2 * math.pi * i / SEG), 0.03)))
      for i in range(SEG)]
for i in range(SEG):
    j = (i + 1) % SEG
    sb.faces.new((vi[i], vi[j], vo[j], vo[i]))
# (no shaft under the hole: the hole is open to whatever is below the arena)
# rim stones around the pit
for i in range(24):
    a0, a1 = 2 * math.pi * i / 24, 2 * math.pi * (i + 0.85) / 24
    pts = [(HOLE_R * math.cos(a0), HOLE_R * math.sin(a0)), ((HOLE_R + 0.6) * math.cos(a0), (HOLE_R + 0.6) * math.sin(a0)),
           ((HOLE_R + 0.6) * math.cos(a1), (HOLE_R + 0.6) * math.sin(a1)), (HOLE_R * math.cos(a1), HOLE_R * math.sin(a1))]
    lo = [BM['Trim'].verts.new((x, y, 0.0)) for x, y in pts]
    hi = [BM['Trim'].verts.new((x, y, 0.3)) for x, y in pts]
    BM['Trim'].faces.new(lo[::-1]); BM['Trim'].faces.new(hi)
    for k in range(4):
        m = (k + 1) % 4
        BM['Trim'].faces.new((lo[k], lo[m], hi[m], hi[k]))
ring(BM['Ground'], 21.9, -3.0, -0.3, 0.0)

# ---------------------------------------------------------------- attic: tall on one side, broken elsewhere
TALL = (math.radians(35), math.radians(175))
for k in range(NB):
    t = t_at(k * L / NB)
    M = frame(0, t) @ Matrix.Translation((0, 0, 22.8))
    ang = t % (2 * math.pi)
    if TALL[0] <= ang <= TALL[1]:
        e = min(ang - TALL[0], TALL[1] - ang) / (2 * math.pi / NB)
        h = [1.6, 2.7, 3.5][int(e)] if e < 3 else 4.2
        if e < 3:   # jagged broken edge: two halves of different height
            box(BM['Attic'], -W / 2, 0, 0, 1.0, 0, h * random.uniform(0.6, 0.9), M)
            box(BM['Attic'], 0, W / 2, 0, 1.0, 0, h, M)
        else:
            box(BM['Attic'], -W / 2, W / 2, 0, 1.0, 0, h, M)
            box(BM['Attic'], -W / 2 - 0.25, -W / 2 + 0.25, -0.25, 0, 0, h, M)
            if k % 2 == 0:
                box(BM['Dark'], -0.5, 0.5, -0.04, 0.02, 1.8, 2.8, M)
            box(BM['Trim'], -W / 2, W / 2, -0.35, 1.0, h, h + 0.4, M)
    else:
        h = random.uniform(0.4, 1.3)
        box(BM['Attic'], -W / 2, W / 2, 0, 0.8, 0, h, M)

# ---------------------------------------------------------------- gate porticoes
for k in range(0, NB, NB // 4):
    M = frame(0, t_at(k * L / NB))
    g = BM['Gates']
    prism(g, arch_outline(10.6, 10.5, 4.6, 5.2), -9.0, -7.4, M)                     # front arch (open)
    for x0 in (4.0, -5.3):                                                           # side walls (closed)
        box(g, x0, x0 + 1.3, -7.4, 0.0, 0.0, 10.5, M)
    for px in (-5.0, -3.4, 3.4, 5.0):                                               # pilasters
        box(g, px - 0.4, px + 0.4, -9.4, -9.0, 0, 10.5, M)
    box(BM['Trim'], -5.8, 5.8, -9.6, 0.0, 10.5, 11.3, M)                            # roof slab / cornice
    box(g, -5.6, 5.6, -9.4, -8.9, 11.3, 12.4, M)                                     # parapet
    box(g, -5.6, -5.1, -8.9, 0.0, 11.3, 12.4, M)
    box(g, 5.1, 5.6, -8.9, 0.0, 11.3, 12.4, M)
    box(BM['Trim'], -3.0, 3.0, -10.6, -7.4, 0.0, 0.25, M)                            # threshold
    box(BM['Trim'], -2.9, 2.9, -9.45, -8.9, 9.5, 10.5, M)                            # inscription band

# ---------------------------------------------------------------- build objects
old = bpy.data.collections.get('Arena')
if old:
    for o in list(old.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(old)
col = bpy.data.collections.new('Arena')
bpy.context.scene.collection.children.link(col)
tris = 0
for name, bm in BM.items():
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new('SM_Arena_' + name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(MATS[MAT_OF[name]])
    ob = bpy.data.objects.new('SM_Arena_' + name, me)
    col.objects.link(ob)
    if name not in ('Sand', 'Ground', 'Dark'):
        bv = ob.modifiers.new('Bevel', 'BEVEL')
        bv.width = 0.07
        bv.segments = 2
        bv.limit_method = 'ANGLE'
        bv.angle_limit = math.radians(35)
    tris += sum(len(p.vertices) - 2 for p in me.polygons)
print('ARENA built, base tris', tris, 'perimeter', round(L, 1))
