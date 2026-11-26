"""
carlib — builds a panelised, game-ready car in Blender (bpy) from profile tables.

Pipeline
  1. loft a watertight body surface from side / plan profile tables (metres)
  2. classify every face into (panel, material) with the car's rule function
  3. smooth the stair-stepped seams between panels/materials onto clean curves
  4. split along panel seams and pull each side back to leave a real panel gap
  5. give every panel thickness (solidify) + rolled edges (bevel), mark sharp edges
  6. set each panel's origin on its real hinge / pivot and parent into a hierarchy

Internal coordinates: x = metres back from the front bumper, y = lateral (+ = car's left), z = up.
Blender coordinates:  X = y, Y = x - L/2 (front of car toward -Y), Z = z.
Exported FBX/glTF then load in Unity with the car facing +Z, Y up, 1 unit = 1 m.
"""
import math
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

# --------------------------------------------------------------------------- utils
def mono(pts):
    """Monotone cubic (Fritsch–Carlson) interpolant, returned as a vectorised function."""
    xs = np.array([p[0] for p in pts], float); ys = np.array([p[1] for p in pts], float)
    n = len(xs); d = np.diff(ys) / np.diff(xs); m = np.zeros(n)
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        m[i] = 0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2
    for i in range(n - 1):
        if d[i] == 0: m[i] = m[i + 1] = 0; continue
        a, b = m[i] / d[i], m[i + 1] / d[i]; s = a * a + b * b
        if s > 9: t = 3 / math.sqrt(s); m[i] = t * a * d[i]; m[i + 1] = t * b * d[i]
    def f(x):
        x = np.asarray(x, float); xc = np.clip(x, xs[0], xs[-1])
        i = np.clip(np.searchsorted(xs, xc) - 1, 0, n - 2)
        h = xs[i + 1] - xs[i]; t = (xc - xs[i]) / h; t2 = t * t; t3 = t2 * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h * m[i + 1])
    return f

def to_bl(x, y, z, L):
    return Vector((y, x - L / 2, z))

def from_bl(v, L):
    return (v.y + L / 2, v.x, v.z)

SEG_BOTTOM, SEG_CORNER, SEG_SIDE, SEG_SHOULDER, SEG_GREEN, SEG_TOP, SEG_CAP = 0, 1, 2, 3, 4, 5, -1

# --------------------------------------------------------------------------- materials
def principled(name, color, metallic=0.0, rough=0.5, coat=0.0, transmission=0.0, alpha=1.0, emission=None, ior=1.45):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Metallic'].default_value = metallic
    b.inputs['Roughness'].default_value = rough
    if 'Coat Weight' in b.inputs: b.inputs['Coat Weight'].default_value = coat
    if 'Transmission Weight' in b.inputs: b.inputs['Transmission Weight'].default_value = transmission
    b.inputs['IOR'].default_value = ior
    if alpha < 1:
        b.inputs['Alpha'].default_value = alpha
    if emission:
        b.inputs['Emission Color'].default_value = (*emission[0], 1)
        b.inputs['Emission Strength'].default_value = emission[1]
    m.diffuse_color = (*color, alpha)
    return m

def srgb(h):
    c = [((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255]
    return tuple((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)

def make_materials(prefix, paint_hex, extra=None):
    M = {
        'paint':   principled(f'{prefix}_Paint', srgb(paint_hex), 0.55, 0.30, coat=1.0),
        'glass':   principled(f'{prefix}_Glass_Tint', srgb(0x0b0f14), 0.0, 0.03, transmission=0.0, alpha=0.88),
        'black':   principled(f'{prefix}_Trim_GlossBlack', srgb(0x0a0a0b), 0.1, 0.18, coat=0.6),
        'plastic': principled(f'{prefix}_Trim_Textured', srgb(0x1c1c1d), 0.0, 0.82),
        'lens':    principled(f'{prefix}_Lens_Clear', srgb(0xf2f6fa), 0.0, 0.02, transmission=1.0, alpha=0.25),
        'reflector': principled(f'{prefix}_Lamp_Reflector', srgb(0xd8dde2), 1.0, 0.12),
        'tail':    principled(f'{prefix}_Lens_Red', srgb(0xb0121a), 0.0, 0.08, transmission=0.6, alpha=0.85, emission=(srgb(0x8a0008), 0.4)),
        'tail_in': principled(f'{prefix}_Lamp_RedInner', srgb(0x5a0306), 0.3, 0.3),
        'amber':   principled(f'{prefix}_Lens_Amber', srgb(0xe07010), 0.0, 0.1, transmission=0.5, alpha=0.9),
        'chrome':  principled(f'{prefix}_Chrome', srgb(0xdde1e4), 1.0, 0.08),
        'rim':     principled(f'{prefix}_Wheel_Black', srgb(0x121213), 0.5, 0.45),
        'tire':    principled(f'{prefix}_Tire_Rubber', srgb(0x151515), 0.0, 0.92),
        'brake':   principled(f'{prefix}_Brake_Rotor', srgb(0x707070), 0.9, 0.4),
        'caliper': principled(f'{prefix}_Brake_Caliper', srgb(0x2b2b2b), 0.5, 0.5),
        'under':   principled(f'{prefix}_Underbody', srgb(0x0e0e0e), 0.0, 0.95),
        'inner':   principled(f'{prefix}_Chassis_Inner', srgb(0x1a1c1f), 0.6, 0.55),
        'plate':   principled(f'{prefix}_Plate_Blank', srgb(0xeef2f6), 0.1, 0.45),
        'mirror':  principled(f'{prefix}_Mirror_Glass', srgb(0xcfd6dc), 1.0, 0.02),
        'rubber':  principled(f'{prefix}_Seal_Rubber', srgb(0x0c0c0c), 0.0, 0.7),
    }
    if extra: M.update(extra)
    return M

# --------------------------------------------------------------------------- profile -> rings
class Profile:
    def __init__(self, spec):
        self.s = spec
        f = spec['fn']
        self.F = {k: mono(v) for k, v in f.items()}

    def params(self, x):
        s, F = self.s, self.F
        x = np.asarray(x, float)
        zTop = F['zTop'](x); crown = F['crown'](x); rr = s.get('roofRound', 0.06)
        zb = F['zBot'](x)
        for ax in s['axles']:
            dx = x - ax
            inside = np.abs(dx) < s['archR']
            arch = s['wheelR'] + np.sqrt(np.clip(s['archR'] ** 2 - dx * dx, 0, None)) * s.get('archShape', 1.0)
            zb = np.where(inside, np.maximum(zb, arch), zb)
        zb = np.minimum(zb, zTop - 0.05)
        zBelt = np.minimum(F['zBelt'](x), zTop - crown - rr + 0.005)
        zBelt = np.maximum(zBelt, zb + 0.06)
        hw = F['hw'](x)
        hwTop = np.minimum(F['hwTop'](x), hw - 0.02)
        inset = F['inset'](x) if 'inset' in F else np.full_like(x, 0.06)
        return dict(x=x, zb=zb, zBelt=zBelt, zTop=zTop, crown=crown, rr=rr, hw=hw, hwTop=hwTop, inset=inset)

NSEG = (12, 10, 46, 10, 30, 34)

def ring_half(p, i):
    """Half cross-section at station i: arrays y, z, seg, s from bottom centre to top centre."""
    g = lambda k: float(p[k][i]) if np.ndim(p[k]) else float(p[k])
    zb, zBelt, zTop, crown, rr, hw, hwTop, inset = (g(k) for k in ('zb', 'zBelt', 'zTop', 'crown', 'rr', 'hw', 'hwTop', 'inset'))
    Y, Z, S, T = [], [], [], []
    def add(y, z, seg, t): Y.append(y); Z.append(z); S.append(seg); T.append(t)
    rb = min(max((zBelt - zb) * 0.25, 0.01), 0.07); yb = hw * 0.965
    for k in range(NSEG[0]):
        t = k / NSEG[0]; add((yb - rb) * t, zb, SEG_BOTTOM, t)
    for k in range(NSEG[1]):
        t = k / NSEG[1]; a = -math.pi / 2 + t * math.pi / 2
        add(yb - rb + rb * math.cos(a), zb + rb + rb * math.sin(a), SEG_CORNER, t)
    zS0, zS1 = zb + rb, max(zb + rb + 0.01, zBelt - 0.035)
    for k in range(NSEG[2]):
        t = k / NSEG[2]
        add(hw * (1 - 0.035 * (1 - t) ** 2 - 0.006 * t * t), zS0 + (zS1 - zS0) * t, SEG_SIDE, t)
    yG, zG = hw - inset, zBelt + 0.01
    P0, C, P2 = (hw * 0.994, zS1), (hw * 0.99, zBelt + 0.005), (yG, zG)
    for k in range(NSEG[3]):
        t = k / NSEG[3]; u = 1 - t
        add(u * u * P0[0] + 2 * u * t * C[0] + t * t * P2[0], u * u * P0[1] + 2 * u * t * C[1] + t * t * P2[1], SEG_SHOULDER, t)
    zE = max(zG, zTop - crown - rr)
    for k in range(NSEG[4]):
        t = k / NSEG[4]
        bow = 0.025 * math.sin(math.pi * t) if zE - zG > 0.05 else 0.0
        add(yG + (hwTop - yG) * t + bow, zG + (zE - zG) * t, SEG_GREEN, t)
    n = 2.6
    for k in range(NSEG[5] + 1):
        t = k / NSEG[5]; th = t * math.pi / 2
        c, s_ = math.cos(th), math.sin(th)
        add(hwTop * (abs(c) ** (2 / n)), zE + (zTop - zE) * (abs(s_) ** (2 / n)), SEG_TOP, t)
    return np.array(Y), np.array(Z), np.array(S), np.array(T)

def station_xs(L, n):
    u = np.linspace(0, 1, n)
    return L * (0.5 - 0.5 * np.cos(np.pi * u)) * 0.4 + L * u * 0.6

# --------------------------------------------------------------------------- body surface
def build_surface(spec, stations=380, cap_levels=16):
    """Returns verts (N,3 internal), faces (list of index tuples), face meta (seg, s, station-x)."""
    L = spec['L']; prof = Profile(spec)
    xs = station_xs(L, stations)
    P = prof.params(xs)
    rings = [ring_half(P, i) for i in range(len(xs))]
    NH = len(rings[0][0]); M = 2 * NH - 2
    ridx = lambda k: k if k < NH else 2 * NH - 2 - k
    rsgn = lambda k: 1.0 if k < NH else -1.0
    verts = []
    for i, (Y, Z, S, T) in enumerate(rings):
        for k in range(M):
            h = ridx(k); verts.append((xs[i], Y[h] * rsgn(k), Z[h]))
    faces, meta = [], []
    for i in range(len(xs) - 1):
        for k in range(M):
            k2 = (k + 1) % M
            a, b, c, d = i * M + k, i * M + k2, (i + 1) * M + k, (i + 1) * M + k2
            h, h2 = ridx(k), ridx(k2)
            lo = h if h < h2 else h2
            Y, Z, S, T = rings[i]
            faces.append((a, c, d, b)); meta.append((int(S[lo]), float(T[lo])))
    # caps: concentric rings to a centre point
    for end in (0, len(xs) - 1):
        Y, Z, S, T = rings[end]; x0 = xs[end]
        zc = (P['zb'][end] + P['zTop'][end]) / 2
        base = end * M
        prev = [base + k for k in range(M)]
        for l in range(1, cap_levels + 1):
            t = l / cap_levels
            if l < cap_levels:
                bul = (-1 if end == 0 else 1) * 0.014 * math.sin(math.pi / 2 * t)
                cur = []
                for k in range(M):
                    h = ridx(k)
                    verts.append((x0 + bul, Y[h] * rsgn(k) * (1 - t), Z[h] + (zc - Z[h]) * t)); cur.append(len(verts) - 1)
                for k in range(M):
                    k2 = (k + 1) % M
                    q = (prev[k], prev[k2], cur[k2], cur[k]) if end == 0 else (prev[k], cur[k], cur[k2], prev[k2])
                    faces.append(q); meta.append((SEG_CAP, t))
                prev = cur
            else:
                verts.append((x0 + (-1 if end == 0 else 1) * 0.014, 0.0, zc)); c = len(verts) - 1
                for k in range(M):
                    k2 = (k + 1) % M
                    q = (prev[k], prev[k2], c) if end == 0 else (prev[k], c, prev[k2])
                    faces.append(q); meta.append((SEG_CAP, 1.0))
    return np.array(verts), faces, meta, prof

def mesh_from(name, verts_bl, faces, mats=None, mat_idx=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts_bl], [], faces)
    if mats:
        for m in mats: me.materials.append(m)
        if mat_idx is not None:
            me.polygons.foreach_set('material_index', mat_idx)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob

# --------------------------------------------------------------------------- panel split
def panelise(spec, M, classify, gap=0.0045, stations=380):
    """Build the body, classify faces, smooth seams, split into panel objects (dict name->object)."""
    L = spec['L']
    V, F, META, prof = build_surface(spec, stations)
    Vbl = [to_bl(*v, L) for v in V]
    bm = bmesh.new()
    bv = [bm.verts.new(v) for v in Vbl]
    for f in F:
        bm.faces.new([bv[i] for i in f])
    bm.faces.ensure_lookup_table(); bm.verts.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # a side face on the left (+X) must point +X
    test = max(bm.faces, key=lambda f: f.calc_center_median().x)
    if test.normal.x < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    bvh0 = BVHTree.FromBMesh(bm)

    # ---- classify
    names, mats = [], list(M.keys())
    pan_layer = bm.faces.layers.int.new('panel')
    key_of = {}
    for f, (seg, s) in zip(bm.faces, META):
        c = f.calc_center_median(); n = f.normal
        x, y, z = from_bl(c, L)
        panel, mat = classify(x, abs(y), z, (n.y, abs(n.x), n.z), seg, s, 'L' if y >= 0 else 'R')
        if panel not in names: names.append(panel)
        f[pan_layer] = names.index(panel)
        f.material_index = mats.index(mat)

    # ---- seam smoothing (panel seams and material seams)
    def fkey(f): return (f[pan_layer], f.material_index)
    seam_edges = [e for e in bm.edges if len(e.link_faces) == 2 and fkey(e.link_faces[0]) != fkey(e.link_faces[1])]
    adj = {}
    for e in seam_edges:
        a, b = e.verts
        adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    movable = []
    for v, nb in adj.items():
        keys = {fkey(f) for f in v.link_faces}
        if len(nb) == 2 and len(keys) == 2:
            movable.append((v, nb))
    for it in range(40):
        newpos = {}
        for v, (a, b) in movable:
            p = v.co * 0.5 + (a.co + b.co) * 0.25
            loc, nrm, _, _ = bvh0.find_nearest(p)
            newpos[v] = loc if loc is not None else p
        for v, p in newpos.items(): v.co = p
    # light relaxation of the ring of verts next to the seams so faces don't fold
    seam_set = set(adj.keys())
    ring1 = {n for v in seam_set for e in v.link_edges for n in e.verts if n not in seam_set}
    for it in range(4):
        newpos = {}
        for v in ring1:
            nb = [e.other_vert(v).co for e in v.link_edges]
            p = v.co * 0.5 + sum(nb, Vector()) / len(nb) * 0.5
            loc, _, _, _ = bvh0.find_nearest(p)
            newpos[v] = loc if loc is not None else p
        for v, p in newpos.items(): v.co = p

    # ---- split along panel seams, then pull each side back by gap/2
    pan_edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.link_faces[0][pan_layer] != e.link_faces[1][pan_layer]]
    bmesh.ops.split_edges(bm, edges=pan_edges)
    bm.verts.ensure_lookup_table(); bm.normal_update()
    moves = {}
    for v in bm.verts:
        if not v.is_boundary: continue
        nrm = v.normal
        inward = Vector()
        for f in v.link_faces:
            d = f.calc_center_median() - v.co
            inward += d - nrm * d.dot(nrm)
        if inward.length < 1e-9: continue
        moves[v] = v.co + inward.normalized() * (gap / 2)
    for v, p in moves.items(): v.co = p

    # ---- separate into objects
    bm.faces.ensure_lookup_table()
    groups = {}
    for f in bm.faces: groups.setdefault(f[pan_layer], []).append(f)
    out = {}
    for pid, fs in groups.items():
        vmap = {}; verts = []; faces = []; midx = []
        for f in fs:
            idx = []
            for v in f.verts:
                if v not in vmap: vmap[v] = len(verts); verts.append(v.co.copy())
                idx.append(vmap[v])
            faces.append(idx); midx.append(f.material_index)
        used = sorted(set(midx)); remap = {m: i for i, m in enumerate(used)}
        ob = mesh_from(names[pid], verts, faces, [M[mats[m]] for m in used], [remap[m] for m in midx])
        out[names[pid]] = ob
    bm.free()
    return out, prof, bvh0

# --------------------------------------------------------------------------- finishing
def apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    old = ob.data; ob.modifiers.clear(); ob.data = me
    bpy.data.meshes.remove(old)

def mark_sharp(ob, angle_deg=38):
    me = ob.data; bm = bmesh.new(); bm.from_mesh(me)
    lim = math.radians(angle_deg)
    for f in bm.faces: f.smooth = True
    for e in bm.edges:
        e.smooth = not (len(e.link_faces) != 2 or e.calc_face_angle(0) > lim)
    bm.to_mesh(me); bm.free()

def thicken(ob, t=0.0025, bevel=0.0011, offset=-1.0, push=0.0):
    if push:
        for v in ob.data.vertices: pass
        bm = bmesh.new(); bm.from_mesh(ob.data); bm.normal_update()
        for v in bm.verts: v.co += v.normal * push
        bm.to_mesh(ob.data); bm.free()
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges[:])
    bm.to_mesh(ob.data); bm.free()
    s = ob.modifiers.new('Solidify', 'SOLIDIFY'); s.thickness = t; s.offset = offset; s.use_rim = True
    s.use_even_offset = False; s.use_quality_normals = True; s.thickness_clamp = 0.5
    if bevel:
        b = ob.modifiers.new('Bevel', 'BEVEL'); b.width = bevel; b.segments = 2; b.limit_method = 'ANGLE'; b.angle_limit = math.radians(60)
    apply_mods(ob); mark_sharp(ob)

def set_origin(ob, point_bl):
    """Move object origin to point (Blender world coords) without moving geometry."""
    off = Vector(point_bl) - ob.location
    ob.data.transform(Matrix.Translation(-off))
    ob.location = Vector(point_bl)
    bpy.context.view_layer.update()

def centroid(ob):
    bpy.context.view_layer.update()
    vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
    return sum(vs, Vector()) / max(1, len(vs))

def bbox(ob):
    bpy.context.view_layer.update()
    vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
    return Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs))), Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))

def empty(name, loc=(0, 0, 0), parent=None, size=0.1):
    e = bpy.data.objects.new(name, None); e.empty_display_size = size; e.empty_display_type = 'PLAIN_AXES'
    bpy.context.scene.collection.objects.link(e); e.location = loc
    if parent: parent_keep(e, parent)
    return e

def parent_keep(ch, par):
    bpy.context.view_layer.update()
    mw = ch.matrix_world.copy(); ch.parent = par; ch.matrix_parent_inverse = Matrix.Identity(4)
    bpy.context.view_layer.update()
    ch.matrix_world = mw

def offset_copy(ob, name, dist, mat=None, thickness=None):
    """Duplicate a panel's mesh pushed along its normals (e.g. lamp reflector behind a lens)."""
    me = ob.data.copy(); bm = bmesh.new(); bm.from_mesh(me); bm.normal_update()
    for v in bm.verts: v.co += v.normal * dist
    bm.to_mesh(me); bm.free()
    if mat is not None:
        me.materials.clear(); me.materials.append(mat)
        for p in me.polygons: p.material_index = 0
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    o.matrix_world = ob.matrix_world.copy()
    if thickness: thicken(o, thickness, 0)
    return o

# --------------------------------------------------------------------------- primitive builders
def obj_from_bm(name, bm, mat_list):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mat_list: me.materials.append(m)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob

def lathe(name, profile, segs, mat, axis='X'):
    """Revolve (radius, axial) profile points around the X axis (lateral) — for tyres, barrels, rotors."""
    bm = bmesh.new(); rings = []
    for k in range(segs):
        a = 2 * math.pi * k / segs; ca, sa = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((ax, r * ca, r * sa)) for r, ax in profile])
    for k in range(segs):
        r0, r1 = rings[k], rings[(k + 1) % segs]
        for j in range(len(profile) - 1):
            bm.faces.new((r0[j], r1[j], r1[j + 1], r0[j + 1]))
    bm.normal_update()
    ob = obj_from_bm(name, bm, [mat]); mark_sharp(ob, 50); return ob

def box_bm(bm, center, size, rot=Matrix.Identity(3)):
    r = bmesh.ops.create_cube(bm, size=1.0)
    for v in r['verts']:
        v.co = rot @ Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])) + Vector(center)
    return r['verts']

def rounded_box(name, size, mat, bevel=0.004, segs=3):
    bm = bmesh.new(); box_bm(bm, (0, 0, 0), size)
    bmesh.ops.bevel(bm, geom=bm.edges[:] + bm.verts[:], offset=bevel, segments=segs, affect='EDGES', profile=0.5)
    ob = obj_from_bm(name, bm, [mat]); mark_sharp(ob, 50); return ob

def superellipsoid(name, rx, ry, rz, mat, n=3.0, segs=40, rings=24, flat_x=None):
    bm = bmesh.new(); grid = []
    for i in range(rings + 1):
        th = -math.pi / 2 + math.pi * i / rings; row = []
        for j in range(segs):
            ph = 2 * math.pi * j / segs
            ct, st, cp, sp = math.cos(th), math.sin(th), math.cos(ph), math.sin(ph)
            f = lambda c: math.copysign(abs(c) ** (2 / n), c)
            x, y, z = rx * f(ct) * f(cp), ry * f(ct) * f(sp), rz * f(st)
            if flat_x is not None: x = max(x, flat_x)
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for i in range(rings):
        for j in range(segs):
            a, b, c, d = grid[i][j], grid[i][(j + 1) % segs], grid[i + 1][(j + 1) % segs], grid[i + 1][j]
            try: bm.faces.new((a, b, c, d))
            except ValueError: pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bm.normal_update()
    ob = obj_from_bm(name, bm, [mat]); mark_sharp(ob, 45); return ob

def cylinder(name, r, depth, mat, segs=32, axis='X', cap=True):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=cap, segments=segs, radius1=r, radius2=r, depth=depth)
    if axis == 'X': bmesh.ops.rotate(bm, verts=bm.verts[:], matrix=Matrix.Rotation(math.pi / 2, 3, 'Y'))
    elif axis == 'Y': bmesh.ops.rotate(bm, verts=bm.verts[:], matrix=Matrix.Rotation(math.pi / 2, 3, 'X'))
    ob = obj_from_bm(name, bm, [mat]); mark_sharp(ob, 40); return ob

# --------------------------------------------------------------------------- wheels
def rim_face(name, R_out, R_hub, spoke_fn, depth_fn, mat, thick=0.022, nr=30, na=400):
    """Polar-grid rim face. spoke_fn(r, a) -> True where metal; depth_fn(r) -> axial offset (dish)."""
    bm = bmesh.new(); grid = []
    for i in range(nr + 1):
        r = R_hub + (R_out - R_hub) * i / nr; row = []
        for j in range(na):
            a = 2 * math.pi * j / na
            row.append(bm.verts.new((depth_fn(r), r * math.cos(a), r * math.sin(a))))
        grid.append(row)
    for i in range(nr):
        rc = R_hub + (R_out - R_hub) * (i + 0.5) / nr
        for j in range(na):
            ac = 2 * math.pi * (j + 0.5) / na
            if i < 2 or i >= nr - 2 or spoke_fn(rc, ac):
                bm.faces.new((grid[i][j], grid[i][(j + 1) % na], grid[i + 1][(j + 1) % na], grid[i + 1][j]))
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    # smooth the stair-stepped spoke edges
    for it in range(12):
        bm.verts.ensure_lookup_table()
        bnd = [v for v in bm.verts if v.is_boundary]
        new = {}
        for v in bnd:
            nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
            if len(nb) == 2:
                p = v.co * 0.5 + (nb[0].co + nb[1].co) * 0.25
                rr = math.hypot(p.y, p.z)
                if R_hub + 0.004 < rr < R_out - 0.004:
                    p.x = depth_fn(rr); new[v] = p
        for v, p in new.items(): v.co = p
    bm.normal_update()
    ob = obj_from_bm(name, bm, [mat])
    # face normals should point outward (+X)
    if ob.data.polygons[0].normal.x < 0:
        bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.reverse_faces(bm, faces=bm.faces[:]); bm.to_mesh(ob.data); bm.free()
    thicken(ob, thick, 0.003, offset=-1)
    return ob

def tread_blocks(name, R, W, count, rows, depth, mat, pattern='at'):
    bm = bmesh.new()
    for i in range(count):
        for r in range(rows):
            a = 2 * math.pi * (i + (0.5 if r % 2 else 0)) / count
            bw = W * 0.78 / rows - 0.009
            bl = 2 * math.pi * R / count * (0.60 if pattern == 'at' else 0.45)
            off = ((r + 0.5) / rows - 0.5) * W * 0.78
            if pattern == 'at': off += 0.006 if i % 2 else -0.006
            rot = Matrix.Rotation(a, 3, 'X')
            if pattern == 'winter':
                rot = rot @ Matrix.Rotation((0.35 if off > 0 else -0.35), 3, 'Z')
            vs = box_bm(bm, (0, 0, 0), (bw, bl, depth), Matrix.Identity(3))
            for v in vs:
                v.co = Matrix.Rotation(a, 3, 'X') @ ((Matrix.Rotation((0.35 if off > 0 else -0.35), 3, 'Z') if pattern == 'winter' else Matrix.Identity(3)) @ v.co + Vector((off, 0, R + depth / 2 - 0.002)))
        if pattern == 'at':
            for sg in (-1, 1):
                a = 2 * math.pi * (i + 0.25) / count
                vs = box_bm(bm, (0, 0, 0), (W * 0.13, 2 * math.pi * R / count * 0.5, depth * 0.9))
                for v in vs: v.co = Matrix.Rotation(a, 3, 'X') @ (v.co + Vector((sg * W * 0.45, 0, R - 0.006)))
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.0015, segments=1, affect='EDGES')
    ob = obj_from_bm(name, bm, [mat]); mark_sharp(ob, 40); return ob

def build_wheel(prefix, w, M):
    """Returns (wheel_root_empty, knuckle_parts). Wheel axis = X, centred at origin."""
    R, W, Rr = w['R'], w['width'], w['rimR']
    root = empty(f'{prefix}', (0, 0, 0), size=0.25)
    td = w['tread_depth']
    prof = [(Rr + 0.006, -W * 0.44), (Rr + 0.035, -W * 0.50), (R - 0.06, -W * 0.53), (R - 0.02, -W * 0.50), (R - td - 0.002, -W * 0.42),
            (R - td, -W * 0.30), (R - td, W * 0.30), (R - td - 0.002, W * 0.42), (R - 0.02, W * 0.50), (R - 0.06, W * 0.53), (R - 0.035 + 0.0, W * 0.50), (Rr + 0.006, W * 0.44)]
    t = lathe(f'{prefix}_Tire', prof, 96, M['tire']); parent_keep(t, root)
    tb = tread_blocks(f'{prefix}_Tread', R - td, W, w['tread_count'], w['tread_rows'], td + 0.002, M['tire'], w['tread_pattern']); parent_keep(tb, root)
    barrel = lathe(f'{prefix}_RimBarrel', [(Rr + 0.012, W * 0.40), (Rr + 0.004, W * 0.36), (Rr, W * 0.30), (Rr - 0.01, W * 0.0), (Rr, -W * 0.30), (Rr + 0.01, -W * 0.40)], 96, M['rim']); parent_keep(barrel, root)
    face_x = W * 0.33
    face = rim_face(f'{prefix}_RimFace', Rr - 0.004, 0.072, w['spoke_fn'], lambda r: face_x - 0.035 * ((r - 0.072) / (Rr - 0.076)) ** 1.6 * (1 if w.get('dish', True) else 0.3), M['rim'])
    parent_keep(face, root)
    hub = lathe(f'{prefix}_Hub', [(0.0, face_x + 0.006), (0.04, face_x + 0.006), (0.074, face_x - 0.002), (0.074, face_x - 0.03)], 48, M['rim']); parent_keep(hub, root)
    cap = cylinder(f'{prefix}_CenterCap', 0.031, 0.008, M[w.get('cap_mat', 'chrome')], 40); cap.location = (face_x + 0.009, 0, 0); parent_keep(cap, root)
    nuts = bmesh.new()
    for i in range(5):
        a = 2 * math.pi * i / 5 + math.pi / 10
        r = bmesh.ops.create_cone(nuts, cap_ends=True, segments=6, radius1=0.0105, radius2=0.0095, depth=0.022)
        for v in r['verts']:
            v.co = Matrix.Rotation(math.pi / 2, 3, 'Y') @ v.co + Vector((face_x + 0.004, 0.056 * math.cos(a), 0.056 * math.sin(a)))
    no = obj_from_bm(f'{prefix}_LugNuts', nuts, [M['chrome']]); mark_sharp(no, 30); parent_keep(no, root)
    valve = cylinder(f'{prefix}_Valve', 0.004, 0.03, M['rubber'], 10); valve.location = (face_x - 0.01, 0, Rr + 0.006); parent_keep(valve, root)
    rotor = lathe(f'{prefix}_Rotor', [(0.05, -0.02), (w['rotorR'], -0.02), (w['rotorR'], 0.008), (0.09, 0.008), (0.085, 0.04), (0.05, 0.04)], 64, M['brake'])
    parent_keep(rotor, root)
    # caliper sits on the knuckle (does not spin)
    cal = rounded_box(f'{prefix}_Caliper', (0.06, 0.16, 0.085), M['caliper'], 0.012)
    cal.location = (0.0, 0.03, w['rotorR'] - 0.032); cal.rotation_euler = (math.radians(-20), 0, 0)
    return root, cal

# --------------------------------------------------------------------------- export helpers
def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.objects):
        for it in list(c): c.remove(it)
