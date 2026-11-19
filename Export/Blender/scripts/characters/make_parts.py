# Split the baked SKM_PlayerKnight (v4) into separate assembly parts and save them, spread out ("exploded"), as
# Export/Blender/PlayerKnight_Parts.blend -- an assembly exercise for the user. Static meshes only (no rig).
# Part labels come from gen_player_knight_v4.Kit4 (same vertex order as the mesh made by make_object, as long as
# the mesh was not decimated). Each part's origin is its bounding-box centre; the correct position is stored in the
# custom property "정답_위치" (answer location). A light wireframe guide of the whole knight marks the target.
# Run inside PlayerKnight.blend (after gen v4 run() + bake): exec this file, then run().
import bpy, os
import numpy as np
from mathutils import Vector

V4 = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Blender\scripts\characters\gen_player_knight_v4.py"
OUT = r"C:\Users\ykj08\Documents\Unreal Projects\Oss_TermProject\Export\Blender\PlayerKnight_Parts.blend"
SRC = 'SKM_PlayerKnight'

KO = {'Head': '머리', 'Collar': '목가리개', 'Breastplate': '흉갑', 'Belt': '벨트_파우치', 'Skirt': '허리치마',
      'Underlayer': '내피', 'Pauldron': '견갑', 'UpperArm': '위팔갑', 'Elbow': '팔꿈치갑', 'Vambrace': '팔뚝갑',
      'Gauntlet': '건틀릿', 'Thigh': '허벅지갑', 'Knee': '무릎갑', 'Shin': '정강이갑', 'Foot': '발갑'}
SIDE = {'L': '왼쪽', 'R': '오른쪽'}
# exploded offsets (x is mirrored for the right side; character's left = +X)
OFFS = {'Head': (0, 0, 0.42), 'Collar': (0, 0, 0.24), 'Breastplate': (0, 0, 0), 'Belt': (0, -0.55, 0.05),
        'Skirt': (0, -0.45, -0.15), 'Underlayer': (0, 0.55, -0.05),
        'Pauldron': (0.35, 0, 0.28), 'UpperArm': (0.55, 0, 0.12), 'Elbow': (0.75, 0, 0.0), 'Vambrace': (0.95, 0, -0.1),
        'Gauntlet': (1.15, 0, -0.22), 'Thigh': (0.35, 0, -0.05), 'Knee': (0.55, -0.12, -0.08),
        'Shin': (0.7, 0, -0.12), 'Foot': (0.85, -0.12, -0.02)}


def part_labels():
    g = {'__name__': 'knight_v4_parts'}
    exec(open(V4, encoding='utf-8').read(), g)
    K = g['build']()
    labels = np.array(K.part_of, dtype=np.int32); names = list(K.part_names)
    K.bm.free()
    return labels, names


def make_mesh(name, co, loop_vi, loop_start, uv, smooth, mat):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(co)); me.vertices.foreach_set('co', co.ravel())
    me.loops.add(len(loop_vi)); me.loops.foreach_set('vertex_index', loop_vi)
    me.polygons.add(len(loop_start)); me.polygons.foreach_set('loop_start', loop_start)
    me.polygons.foreach_set('use_smooth', smooth)
    uvl = me.uv_layers.new(name='UVMap'); uvl.data.foreach_set('uv', uv.ravel())
    me.update(calc_edges=True); me.validate()
    me.materials.append(mat)
    return me


def run():
    labels, names = part_labels()
    src = bpy.data.objects[SRC]; me = src.data
    nv = len(me.vertices)
    assert nv == len(labels), f"vertex count {nv} != labels {len(labels)} (mesh changed / decimated?)"
    bpy.ops.wm.save_mainfile()                                     # keep PlayerKnight.blend as it is
    Mw = np.array(src.matrix_world)
    co = np.empty(nv * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    co = co @ Mw[:3, :3].T + Mw[:3, 3]                                 # world metres
    nl = len(me.loops); npoly = len(me.polygons)
    lvi = np.empty(nl, np.int32); me.loops.foreach_get('vertex_index', lvi)
    lst = np.empty(npoly, np.int32); me.polygons.foreach_get('loop_start', lst)
    ltot = np.empty(npoly, np.int32); me.polygons.foreach_get('loop_total', ltot)
    sm = np.empty(npoly, bool); me.polygons.foreach_get('use_smooth', sm)
    uv = np.empty(nl * 2, np.float32); me.uv_layers.active.data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
    mat = me.materials[0]
    poly_part = labels[lvi[lst]]

    # fresh scene content: remove everything else
    for o in list(bpy.data.objects):
        if o != src:
            bpy.data.objects.remove(o, do_unlink=True)
    col_parts = bpy.data.collections.new('부품'); bpy.context.scene.collection.children.link(col_parts)
    col_guide = bpy.data.collections.new('가이드'); bpy.context.scene.collection.children.link(col_guide)
    made = []
    for pi, pname in enumerate(names):
        sel = np.nonzero(poly_part == pi)[0]
        if not len(sel):
            continue
        starts = lst[sel]; tots = ltot[sel]
        loop_idx = np.concatenate([np.arange(s, s + t) for s, t in zip(starts, tots)])
        vids = lvi[loop_idx]
        uniq, inv = np.unique(vids, return_inverse=True)
        pco = co[uniq]
        centre = (pco.min(0) + pco.max(0)) / 2
        new_start = np.concatenate([[0], np.cumsum(tots)[:-1]]).astype(np.int32)
        base, side = (pname.rsplit('_', 1) + [''])[:2] if pname[-2:] in ('_L', '_R') else (pname, '')
        ko = KO.get(base, base) + (f'_{SIDE[side]}' if side else '')
        m = make_mesh(ko, (pco - centre).astype(np.float32), inv.astype(np.int32), new_start, uv[loop_idx],
                      sm[sel], mat)
        ob = bpy.data.objects.new(ko, m); col_parts.objects.link(ob)
        answer = Vector(centre.tolist())
        off = Vector(OFFS.get(base, (0, 0, 0)))
        if side == 'R':
            off.x = -off.x
        ob.location = answer + off
        ob['정답_위치'] = tuple(round(x, 4) for x in answer)
        made.append((ko, len(sel)))
    # wireframe guide of the assembled knight (decimated so the wires stay readable)
    gme = make_mesh('가이드_완성본', co.astype(np.float32), lvi, lst, uv, sm, mat)
    guide = bpy.data.objects.new('가이드_완성본', gme); col_guide.objects.link(guide)
    dm = guide.modifiers.new('dec', 'DECIMATE'); dm.ratio = 0.04
    guide.display_type = 'WIRE'; guide.hide_select = True; guide.hide_render = True
    # remove the source mesh / armature data, keep only the parts
    bpy.data.objects.remove(src, do_unlink=True)
    for a in list(bpy.data.armatures):
        if a.users == 0:
            bpy.data.armatures.remove(a)
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.spaces.active.shading.type = 'MATERIAL'
    bpy.ops.wm.save_as_mainfile(filepath=OUT)
    return OUT, made
