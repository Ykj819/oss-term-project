# Shared helpers for the stylized props (Export/Blender/StylizedProps.blend): rocks, stones, grass, flowers.
# Geometry is built straight into one bmesh with per-loop vertex colours (sRGB-encoded, see CLAUDE.md) and
# material slots whose NAMES drive the Unreal import (Tools/import_stylized_batch.py):
#   M_Stylized_Prop     -> one-sided vertex-colour material (rocks, stones)
#   M_Stylized_Foliage  -> two-sided vertex-colour material (grass, flowers, leaves)
import bpy, bmesh, math, os
from mathutils import Vector, Matrix, noise

ROOT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject"


def c01(x):
    return max(0.0, min(1.0, x))


def lin2srgb(c):
    return c * 12.92 if c <= 0.0031308 else 1.055 * max(c, 0.0) ** (1 / 2.4) - 0.055


def mix(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def scale(c, k):
    return tuple(x * k for x in c)


def material(name, two_sided):
    """Material showing the 'Col' attribute (so the Blender preview = the Unreal look)."""
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    ca = nt.nodes.new('ShaderNodeVertexColor'); ca.layer_name = 'Col'
    nt.links.new(ca.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.75 if two_sided else 0.85
    m.use_backface_culling = not two_sided
    return m


class Builder:
    def __init__(self):
        self.bm = bmesh.new()
        self.col = self.bm.loops.layers.color.new('Col')
        self.uv = self.bm.loops.layers.uv.new('UVMap')

    # ---- primitive: arbitrary faces; colour = tuple or fn(index, position) -> linear rgb
    def faces(self, verts, faces, mat=0, color=(1, 1, 1), smooth=True):
        vs = [self.bm.verts.new(v) for v in verts]
        out = []
        for fi in faces:
            try:
                f = self.bm.faces.new([vs[i] for i in fi])
            except ValueError:
                continue
            f.material_index = mat; f.smooth = smooth
            for l, i in zip(f.loops, fi):
                c = color(i, verts[i]) if callable(color) else color
                l[self.col] = (lin2srgb(c[0]), lin2srgb(c[1]), lin2srgb(c[2]), 1.0)
                l[self.uv].uv = (verts[i][0] + verts[i][1], verts[i][2])
            out.append(f)
        return out

    def tube(self, pts, radii, sides=6, mat=0, color=None, cap_end=True):
        """Swept tube along pts (parallel transport). color(t 0..1 along, position) -> rgb."""
        n = len(pts); verts = []; ts = []
        prev_n = None; prev_t = None
        for k in range(n):
            a = pts[max(k - 1, 0)]; b = pts[min(k + 1, n - 1)]
            tan = (b - a).normalized()
            if prev_n is None:
                prev_n = tan.orthogonal().normalized()
            else:
                ax = prev_t.cross(tan)
                if ax.length > 1e-6:
                    prev_n = (Matrix.Rotation(prev_t.angle(tan), 3, ax.normalized()) @ prev_n).normalized()
            prev_t = tan; bn = tan.cross(prev_n)
            for s in range(sides):
                ang = 2 * math.pi * s / sides
                verts.append(pts[k] + (prev_n * math.cos(ang) + bn * math.sin(ang)) * radii[k])
                ts.append(k / (n - 1))
        faces = []
        for k in range(n - 1):
            for s in range(sides):
                s2 = (s + 1) % sides
                faces.append((k * sides + s, k * sides + s2, (k + 1) * sides + s2, (k + 1) * sides + s))
        if cap_end:  # rounded-ish end: a centre vertex pushed out a little
            verts.append(pts[-1] + prev_t * radii[-1] * 0.8); ts.append(1.0)
            c = len(verts) - 1
            for s in range(sides):
                faces.append(((n - 1) * sides + s, (n - 1) * sides + (s + 1) % sides, c))
        col = (lambda i, p: color(ts[i], p)) if color else (0.1, 0.3, 0.05)
        return self.faces(verts, faces, mat, col)

    def blob(self, centre, radius, scl=(1, 1, 1), subdiv=2, mat=0, color=(1, 1, 1), lump=0.0, seed=0.0):
        """Lumpy ellipsoid. color(normalised local position, world position) -> rgb."""
        t = bmesh.new(); bmesh.ops.create_icosphere(t, subdivisions=subdiv, radius=1.0)
        verts = []; locs = []
        for v in t.verts:
            d = v.co.copy()
            if lump:
                d *= 1 + lump * noise.noise(d * 1.7 + Vector((seed, seed * 1.3, seed * 0.7)))
            loc = Vector((d.x * scl[0], d.y * scl[1], d.z * scl[2]))
            verts.append(centre + loc * radius); locs.append(v.co.copy())
        faces = [[v.index for v in f.verts] for f in t.faces]; t.free()
        col = (lambda i, p: color(locs[i], p)) if callable(color) else color
        return self.faces(verts, faces, mat, col)

    def blade(self, base, direction, up, length, width, bend=0.3, rows=4, mat=0, color=None, cup=0.0, tip_round=0.35,
              profile=None):
        """Leaf / petal / grass blade: a lens-shaped strip, bent along its length and cupped across.
        direction: growth direction; up: blade normal side. color(t along 0..1, s across -1..1, position)."""
        d = direction.normalized(); side = d.cross(up).normalized(); nrm = side.cross(d).normalized()
        verts = []; meta = []
        prof = profile or (lambda t: math.sin(math.pi * min(1.0, t * (1 + tip_round) / (1 + tip_round * t))) ** 0.7)
        for r in range(rows + 1):
            t = r / rows
            if r < rows:
                w = width * 0.5 * prof(t)
            elif profile:   # custom profile: blunt, rounded end
                w = width * 0.5 * prof(1.0) * 0.55
            else:
                w = width * 0.5 * tip_round * 0.25
            ang = bend * t * t
            centre = base + (d * math.cos(ang) + nrm * math.sin(ang)) * length * t
            for s in (-1, 0, 1):
                off = side * s * w + nrm * cup * abs(s) * w   # edges lifted toward the normal = cupped
                if r == rows and profile and s == 0:
                    off += d * w * 0.9                        # round the blunt end
                verts.append(centre + off); meta.append((t, s))
        faces = []
        for r in range(rows):
            a = r * 3; b = (r + 1) * 3
            faces += [(a, a + 1, b + 1, b), (a + 1, a + 2, b + 2, b + 1)]
        col = (lambda i, p: color(meta[i][0], meta[i][1], p)) if color else (0.1, 0.3, 0.05)
        return self.faces(verts, faces, mat, col)

    def finish(self, name, mats, collection='Props', location=(0, 0, 0)):
        old = bpy.data.objects.get(name)
        if old:
            m = old.data; bpy.data.objects.remove(old, do_unlink=True); bpy.data.meshes.remove(m)
        self.bm.normal_update()
        me = bpy.data.meshes.new(name); self.bm.to_mesh(me); self.bm.free()
        for m in mats:
            me.materials.append(m)
        col = bpy.data.collections.get(collection)
        if not col:
            col = bpy.data.collections.new(collection); bpy.context.scene.collection.children.link(col)
        ob = bpy.data.objects.new(name, me); col.objects.link(ob); ob.location = location
        return ob


def export(ob, extra=()):
    """FBX next to the other exports. extra: UCX_ collision objects (exported with the mesh)."""
    loc = ob.location.copy(); ob.location = (0, 0, 0)
    # objects removed earlier in the same script stay in view_layer.objects as None until an update
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        if o:
            o.select_set(False)
    ob.select_set(True)
    for e in extra:
        e.location = (0, 0, 0); e.hide_set(False); e.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=os.path.join(ROOT, 'Export', ob.name + '.fbx'), use_selection=True,
                             object_types={'MESH'}, apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE',
                             colors_type='SRGB', use_mesh_modifiers=True, bake_anim=False, add_leaf_bones=False)
    ob.location = loc
    for e in extra:
        e.location = loc; e.hide_set(True); e.hide_render = True
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)
