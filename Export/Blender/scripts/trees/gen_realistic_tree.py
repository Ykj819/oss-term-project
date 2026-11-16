# Realistic tree generator (StylizedTree.blend), silhouette taken from SM_StylizedTree1 (tall, slim, stacked crown).
#  1. Branching: space colonization -> attractor points fill the Tree1 crown ellipsoids, branches grow toward them.
#  2. Radii: pipe model r^2.5 = sum(child r^2.5).
#  3. Wood: swept tubes (parallel-transport frames), bark ridges as real geometry on thick parts, lobed root flare.
#  4. Leaves: real leaf meshes (12 tris, bent + folded), clustered on twig ends, facing up/out.
#  5. Colour: baked to vertex colours (sRGB-encoded) — bark crevices dark, ridges light, moss at the base;
#     leaves vary per leaf, darker deep inside the crown, yellower on the sunny outside.
# Usage: g = {}; exec(open(path).read(), g); g['build']()
import bpy, bmesh, math, random, os
from mathutils import Vector, Matrix, noise, kdtree

ROOT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject"
NAME = 'SM_RealisticTree1'

# Tree1 crown: (x, y, z, r, z_squash)
CROWN = [(0, 0, 6.3, 1.1, 1.15), (0.3, 0.2, 5.2, 1.25, 1.0), (-0.4, -0.2, 4.4, 1.2, 0.95),
         (0.5, -0.3, 3.8, 1.0, 0.9), (-0.25, 0.45, 3.5, 0.95, 0.9), (0, 0, 7.2, 0.75, 1.1)]
CROWN_SCALE = 1.08

P = dict(seed=5, attractors=14000, step=0.07, influence=0.9, kill=0.16, tropism=0.45,
         tip_r=0.0035, pipe=2.2, trunk_top=2.7, leader_top=6.2, max_kids=4, leaves_per_segment=6, leaf_twig_r=0.012, leaf_len=0.12, trunk_r=0.22)


def crown_depth(p):
    """0 on/outside the crown surface, ->1 at a clump centre."""
    best = 0.0
    for (x, y, z, r, sq) in CROWN:
        r *= CROWN_SCALE
        d = Vector(((p.x - x) / r, (p.y - y) / r, (p.z - z) / (r * sq))).length
        best = max(best, 1.0 - d)
    return best


def sample_attractors(rng, n):
    pts = []
    lo = Vector((-2, -2, 2.4)); hi = Vector((2, 2, 8.4))
    while len(pts) < n:
        p = Vector((rng.uniform(lo.x, hi.x), rng.uniform(lo.y, hi.y), rng.uniform(lo.z, hi.z)))
        if crown_depth(p) > 0.0:
            pts.append(p)
    return pts


def grow(rng):
    pos = []; parent = []
    # straight-ish trunk up to the crown, slight wobble like Tree1
    z = 0.0
    while z < P['leader_top']:
        pos.append(Vector((0.04 * math.sin(z * 1.3), 0.03 * math.sin(z * 0.9 + 1), z))); parent.append(len(pos) - 2)
        z += P['step']
    parent[0] = -1
    att = sample_attractors(rng, P['attractors'])
    alive = list(range(len(att)))
    up = Vector((0, 0, 1))
    nkids = [0] * len(pos)
    for i in range(1, len(pos)):
        nkids[i - 1] = 1
    for it in range(400):
        if not alive:
            break
        kd = kdtree.KDTree(len(pos))
        for i, p in enumerate(pos):
            kd.insert(p, i)
        kd.balance()
        # only nodes with few children may sprout (otherwise one node grows a whorl/fan of twigs)
        grow_ids = [i for i in range(len(pos)) if nkids[i] < P['max_kids']]
        kg = kdtree.KDTree(max(len(grow_ids), 1))
        for i in grow_ids:
            kg.insert(pos[i], i)
        kg.balance()
        pull = {}
        still = []
        for a in alive:
            co, idx, dist = kd.find(att[a])
            if dist < P['kill']:
                continue
            still.append(a)
            if not grow_ids:
                continue
            co, gi, gdist = kg.find(att[a])
            if gdist < P['influence']:
                pull.setdefault(gi, Vector()).__iadd__((att[a] - pos[gi]).normalized())
        alive = still
        if not pull:
            break
        for idx, v in pull.items():
            d = (v.normalized() + up * P['tropism']).normalized()
            np_ = pos[idx] + d * P['step']
            pos.append(np_); parent.append(idx); nkids.append(0); nkids[idx] += 1
    return pos, parent


def radii(pos, parent):
    n = len(pos); kids = [[] for _ in range(n)]
    for i, pa in enumerate(parent):
        if pa >= 0:
            kids[pa].append(i)
    r = [0.0] * n
    order = sorted(range(n), key=lambda i: -i)  # children always have larger indices
    for i in order:
        if not kids[i]:
            r[i] = P['tip_r']
        else:
            r[i] = sum(r[k] ** P['pipe'] for k in kids[i]) ** (1 / P['pipe'])
    return r, kids


def chains(pos, parent, r, kids):
    """Split the node tree into smooth tubes: each continues along its thickest child."""
    out = []
    stack = [(0, None)]
    while stack:
        start, from_ = stack.pop()
        ch = [from_] if from_ is not None else []
        i = start
        while True:
            ch.append(i)
            if not kids[i]:
                break
            ks = sorted(kids[i], key=lambda k: -r[k])
            for k in ks[1:]:
                stack.append((k, i))
            i = ks[0]
        out.append(ch)
    return out


def catmull(pts, t):
    i = min(int(t), len(pts) - 2); f = t - i
    p0 = pts[max(i - 1, 0)]; p1 = pts[i]; p2 = pts[i + 1]; p3 = pts[min(i + 2, len(pts) - 1)]
    return 0.5 * ((2 * p1) + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f * f + (-p0 + 3 * p1 - 3 * p2 + p3) * f ** 3)


def build_wood(bm, colors, pos, r, chs):
    lay = colors
    for ch in chs:
        pts = [pos[i] for i in ch]; rs = [r[i] for i in ch]
        if len(pts) < 2:
            continue
        # child tube starts at the parent: use the child's own radius there
        if len(rs) > 1:
            rs[0] = rs[1]
        rmax = max(rs)
        nseg = max(4, min(72, int(2 * math.pi * rmax / 0.01)))
        is_trunk = ch[0] == 0

        # ring spacing follows the local radius: fine only where the bark ridges are modelled
        def rad_at(t):
            i0 = int(t); f = t - i0
            return rs[min(i0, len(rs) - 1)] * (1 - f) + rs[min(i0 + 1, len(rs) - 1)] * f
        ts = [0.0]; tend = len(pts) - 1
        while ts[-1] < tend:
            t = ts[-1]; i0 = min(int(t), len(pts) - 2)
            seg = max((pts[i0 + 1] - pts[i0]).length, 1e-4)
            rr_ = rad_at(t)
            sp = 0.015 if rr_ > 0.07 else (0.04 if rr_ > 0.025 else 0.06)
            ts.append(min(tend, t + sp / seg))
        rings = []; centres = []; prev_n = None; prev_t = None
        for t in ts:
            c = catmull(pts, t)
            c2 = catmull(pts, min(t + 0.05, len(pts) - 1.0001)); c1 = catmull(pts, max(t - 0.05, 0))
            tan = (c2 - c1).normalized()
            if prev_n is None:
                prev_n = tan.orthogonal().normalized()
            else:  # parallel transport
                ax = prev_t.cross(tan)
                if ax.length > 1e-6:
                    prev_n = (Matrix.Rotation(prev_t.angle(tan), 3, ax.normalized()) @ prev_n).normalized()
            prev_t = tan
            bnorm = tan.cross(prev_n)
            i0 = int(t); f = t - i0
            rad = rs[min(i0, len(rs) - 1)] * (1 - f) + rs[min(i0 + 1, len(rs) - 1)] * f
            ring = []
            for s in range(nseg):
                a = 2 * math.pi * s / nseg
                nrm = prev_n * math.cos(a) + bnorm * math.sin(a)
                rr = rad; crev = 0.5
                if is_trunk and c.z < 0.7:  # lobed root flare
                    h = 1 - c.z / 0.7
                    rr *= 1 + 0.9 * h * h * (0.55 + 0.45 * math.cos(5 * a + 0.7))
                p = c + nrm * rr
                if rad > 0.025:  # large bark undulation only; the furrows come from the bark texture
                    q = Vector((p.x * 22, p.y * 22, p.z * 3.2))
                    ridge = 1 - abs(noise.noise(q))
                    crev = ridge
                    p += nrm * (ridge - 0.6) * min(0.006, rad * 0.04)
                v = bm.verts.new(p)
                ring.append((v, crev, nrm))
            rings.append(ring)
            centres.append(c)
        # bark UVs: k whole tiles around (seamless), same texel size along the branch (isotropic)
        k_around = max(1, round(2 * math.pi * rmax / BARK_TILE_M))
        tile_len = 2 * math.pi * rmax / k_around
        vcoord = [0.0]
        for a_, b_ in zip(centres[:-1], centres[1:]):
            vcoord.append(vcoord[-1] + (b_ - a_).length / tile_len)
        voff = (ch[0] * 0.618034) % 1.0   # deterministic offset so branches don't all start the same
        for k in range(len(rings) - 1):
            A = rings[k]; B = rings[k + 1]
            for s in range(nseg):
                s2 = (s + 1) % nseg
                f = bm.faces.new((A[s][0], A[s2][0], B[s2][0], B[s][0]))
                f.material_index = 0; f.smooth = True
                for l, (ss, kk) in zip(f.loops, ((s, k), (s + 1, k), (s + 1, k + 1), (s, k + 1))):
                    l[UV_LAYER[0]].uv = (ss / nseg * k_around, vcoord[kk] + voff)
        # colour stored per vertex via a lookup
        for ring in rings:
            for (v, crev, nrm) in ring:
                BARK_INFO[v] = (crev, nrm)


BARK_INFO = {}
UV_LAYER = [None]
BARK_TILE_M = 0.7   # must match gen_bark_texture.TILE_M


def leaf_template(L):
    rows = [(0.0, 0.0), (0.2, 0.42), (0.45, 0.5), (0.72, 0.36), (1.0, 0.0)]
    verts = []; idx = []
    W = L * 0.48
    for t, w in rows:
        z = -0.18 * L * t * t  # droop
        if w == 0:
            idx.append([len(verts)]); verts.append(Vector((0, t * L, z)))
        else:
            fold = 0.25 * w * W  # V fold along the midrib
            row = []
            for side in (-1, 0, 1):
                row.append(len(verts))
                verts.append(Vector((side * w * W / 2 * 2, t * L, z + (fold if side else 0))))
            idx.append(row)
    faces = []
    for a, b in zip(idx[:-1], idx[1:]):
        if len(a) == 1:
            faces += [(a[0], b[1], b[0]), (a[0], b[2], b[1])]
        elif len(b) == 1:
            faces += [(a[0], a[1], b[0]), (a[1], a[2], b[0])]
        else:
            faces += [(a[0], a[1], b[1], b[0]), (a[1], a[2], b[2], b[1])]
    return verts, faces


def build_leaves(bm, rng, pos, parent, r, kids):
    verts, faces = leaf_template(P['leaf_len'])
    tips = [i for i in range(len(pos)) if not kids[i]]
    leaf_faces = []
    up = Vector((0, 0, 1))
    # every thin twig segment carries a few leaves (only thin ones: leaves on a thick limb made a "wreath";
    # all leaves of a twig at one point made a radial fan)
    thin = [i for i in range(len(pos)) if parent[i] >= 0 and r[i] < P['leaf_twig_r'] and r[parent[i]] < P['leaf_twig_r'] * 1.5]
    for t in thin:
        chain = [t]
        count = P['leaves_per_segment'] + (2 if not kids[t] else 0)
        for n in range(count):
            i = t
            pa = parent[i] if parent[i] >= 0 else i
            along = rng.random()
            base = pos[pa].lerp(pos[i], along) if pa != i else pos[i]
            twig = (pos[i] - pos[pa]).normalized() if pa != i else up
            out = Vector((base.x, base.y, 0)).normalized() if base.xy.length > 1e-3 else twig
            side = twig.cross(Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))).normalized()
            dirv = (twig * 0.6 + side * 0.9 + out * 0.4 + Vector((0, 0, -0.15))).normalized()
            # leaf blade faces mostly up
            nrm = (up * 1.2 + side * 0.4 + Vector((rng.uniform(-.3, .3), rng.uniform(-.3, .3), 0)))
            nrm = (nrm - dirv * nrm.dot(dirv)).normalized()
            xax = dirv.cross(nrm)
            M = Matrix((xax, dirv, nrm)).transposed()
            s = rng.uniform(0.75, 1.25)
            base = base + side * r[i] * 1.2
            vs = [bm.verts.new(base + M @ (v * s)) for v in verts]
            # per-leaf colour factors
            depth = crown_depth(base)
            hue = rng.random()
            for fi in faces:
                f = bm.faces.new([vs[k] for k in fi]); f.material_index = 1; f.smooth = False
                leaf_faces.append((f, depth, hue, base.z))
    return leaf_faces


def lin2srgb(c):
    return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def mix(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def build(export=True):
    rng = random.Random(P['seed'])
    BARK_INFO.clear()
    pos, parent = grow(rng)
    r, kids = radii(pos, parent)
    # trunk base thickness for a ~8 m tree
    # branches keep their pipe-model radii (thin twigs stay thin); only the pre-grown leader gets a real trunk taper
    n_leader = int(P['leader_top'] / P['step']) + 1
    for i in range(min(n_leader, len(pos))):
        zf = max(0.0, 1.0 - pos[i].z / (P['leader_top'] + 2.0))
        r[i] = max(r[i], P['trunk_r'] * zf ** 1.3)
    chs = chains(pos, parent, r, kids)
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap'); UV_LAYER[0] = uv
    build_wood(bm, None, pos, r, chs)
    leaf_faces = build_leaves(bm, rng, pos, parent, r, kids)

    # bark vertex colour = a MULTIPLIER for the bark texture (white = texture as is):
    # moss tint near the ground on one side, slightly paler young bark on thin branches
    col = bm.loops.layers.color.new('Col')
    MOSS = (0.45, 0.70, 0.25); YOUNG = (1.08, 1.0, 0.92)
    for f in bm.faces:
        if f.material_index != 0:
            continue
        for l in f.loops:
            crev, nrm = BARK_INFO.get(l.vert, (0.5, Vector((0, 0, 1))))
            p = l.vert.co
            c = (1.0, 1.0, 1.0)
            moss = max(0.0, min(1.0, (1.2 - p.z) / 1.2)) * max(0.0, -nrm.y * 0.8 + 0.3) * (0.5 + 0.5 * noise.noise(p * 4))
            c = mix(c, MOSS, min(1.0, moss * 0.9))
            if p.z > 3.0:
                c = mix(c, YOUNG, 0.5)
            l[col] = tuple(lin2srgb(min(1.0, x)) for x in c) + (1.0,)
    DARK = (0.02, 0.05, 0.012); MID = (0.05, 0.13, 0.02); SUN = (0.12, 0.24, 0.035); YEL = (0.17, 0.24, 0.04)
    for (f, depth, hue, z) in leaf_faces:
        base = mix(MID, SUN, max(0.0, min(1.0, (z - 3.0) / 4.5)) * 0.7)
        base = mix(base, YEL, max(0.0, hue - 0.8) * 3)            # a few yellowish leaves
        base = mix(base, DARK, min(1.0, depth * 1.2))              # self-shadowed inside the crown
        base = tuple(x * (0.8 + 0.4 * hue) for x in base)
        for l in f.loops:
            l[col] = tuple(lin2srgb(x) for x in base) + (1.0,)
            l[uv].uv = (0.5, 0.5)

    old = bpy.data.objects.get(NAME)
    if old:
        m = old.data; bpy.data.objects.remove(old, do_unlink=True); bpy.data.meshes.remove(m)
    me = bpy.data.meshes.new(NAME); bm.to_mesh(me); bm.free()
    for mn in ('M_Real_Bark', 'M_Real_Leaves'):
        me.materials.append(preview_material(mn))
    c = bpy.data.collections.get('Tree_' + NAME)
    if not c:
        c = bpy.data.collections.new('Tree_' + NAME); bpy.context.scene.collection.children.link(c)
    ob = bpy.data.objects.new(NAME, me); c.objects.link(ob)

    ucx = bpy.data.objects.get('UCX_' + NAME + '_00')
    if ucx:
        bpy.data.objects.remove(ucx, do_unlink=True)
    cb = bmesh.new(); bmesh.ops.create_cone(cb, cap_ends=True, segments=10, radius1=0.32, radius2=0.16, depth=3.0)
    bmesh.ops.translate(cb, verts=cb.verts, vec=(0, 0, 1.5))
    cm = bpy.data.meshes.new('UCX_' + NAME + '_00'); cb.to_mesh(cm); cb.free()
    ucx = bpy.data.objects.new('UCX_' + NAME + '_00', cm); c.objects.link(ucx); ucx.display_type = 'WIRE'; ucx.hide_render = True

    if export:
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        ob.select_set(True); ucx.select_set(True); bpy.context.view_layer.objects.active = ob
        bpy.ops.export_scene.fbx(filepath=os.path.join(ROOT, 'Export', NAME + '.fbx'), use_selection=True,
                                 object_types={'MESH'}, apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE',
                                 colors_type='SRGB', use_mesh_modifiers=False, bake_anim=False, add_leaf_bones=False)
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    nleaf = len(leaf_faces) // 8
    return ob, tris, len(pos), nleaf


def preview_material(name):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    ca = nt.nodes.new('ShaderNodeVertexColor'); ca.layer_name = 'Col'
    nt.links.new(ca.outputs['Color'], b.inputs['Base Color'])
    if 'Leaves' in name:
        b.inputs['Roughness'].default_value = 0.55
        out = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL')
        tr = nt.nodes.new('ShaderNodeBsdfTranslucent'); nt.links.new(ca.outputs['Color'], tr.inputs['Color'])
        mx = nt.nodes.new('ShaderNodeMixShader'); mx.inputs['Fac'].default_value = 0.3
        nt.links.new(b.outputs['BSDF'], mx.inputs[1]); nt.links.new(tr.outputs['BSDF'], mx.inputs[2])
        nt.links.new(mx.outputs['Shader'], out.inputs['Surface'])
    else:
        b.inputs['Roughness'].default_value = 0.95
    return m
