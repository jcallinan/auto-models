"""
Build a panelised, Unity-ready car.
  python3 build.py rav4|e90 [--stations N]
Outputs to ../models/v1/<Name>.{blend,fbx,glb}
"""
import sys, os, time, math, importlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from mathutils import Vector, Matrix
from carlib import *

class Builder:
    def __init__(self, car, stations):
        self.car = car; self.S = car.SPEC; self.L = self.S['L']
        clean_scene()
        self.M = make_materials(self.S['key'], self.S['paint'])
        t = time.time()
        self.parts, self.prof, self.bvh = panelise(self.S, self.M, car.classify, stations=stations)
        self.parts = self.parts
        print(f'panelise {time.time() - t:.1f}s  {len(self.parts)} panels')
        self.root = empty(self.S['name'], (0, 0, 0), size=0.5)
        self.body = empty('Body', (0, 0, 0), self.root)
        self.groups = {}

    # ---- geometry queries -------------------------------------------------
    def bl(self, x, y, z): return to_bl(x, y, z, self.L)
    def side_hit(self, x, z, side=1):
        """Point on the (pre-gap) body surface seen from the side, internal (x,z)."""
        o = self.bl(x, side * 3.0, z); d = Vector((-side, 0, 0))
        loc, nrm, _, _ = self.bvh.ray_cast(o, d)
        return loc, nrm
    def front_hit(self, y, z, rear=False):
        o = self.bl(-1.0 if not rear else self.L + 1.0, y, z); d = Vector((0, 1 if not rear else -1, 0))
        return self.bvh.ray_cast(o, d)[:2]
    def top_hit(self, x, y):
        return self.bvh.ray_cast(self.bl(x, y, 3.0), Vector((0, 0, -1)))[:2]

    def group(self, name, pivot=None, parent=None):
        if name not in self.groups:
            self.groups[name] = empty(name + '_Pivot', pivot if pivot is not None else (0, 0, 0), parent or self.root, 0.15)
        return self.groups[name]

    def attach(self, ob, grp):
        parent_keep(ob, self.group(grp) if isinstance(grp, str) else grp)

    # ---- finishing panels -------------------------------------------------
    def finish_panels(self):
        M = self.M
        for k, o in list(self.parts.items()):
            if k.endswith('_Glass') or k == 'Windshield':
                thicken(o, 0.0045, 0, push=-0.007)
            elif k.startswith(('Headlight', 'Taillight', 'Liftgate_Taillight', 'Trunk_Taillight')):
                thicken(o, 0.003, 0.0006, push=-0.0015)
                inner = offset_copy(o, k + '_Reflector', -0.028, M['reflector'] if k.startswith('Headlight') else M['tail_in'])
                thicken(inner, 0.002, 0)
                self.lamp_inners = getattr(self, 'lamp_inners', {}); self.lamp_inners[k] = inner
            elif k == 'Underbody':
                thicken(o, 0.003, 0)
            elif k == 'Grille':
                continue
            else:
                thicken(o, 0.0028, 0.0012)

    def tub(self):
        """Dark inner shell just inside the panels, so gaps and glass never show daylight."""
        V, F, _, _ = build_surface(self.S, 110, 6)
        P = self.prof.params(V[:, 0])
        zc = (P['zb'] + P['zTop']) / 2
        d = 0.035
        out = []
        for (x, y, z), c in zip(V, zc):
            v = Vector((0, y, z - c)); l = v.length
            s = max(0.0, l - d) / l if l > 1e-6 else 1.0
            xi = min(max(x, d), self.L - d)
            out.append(to_bl(xi, y * s, c + (z - c) * s, self.L))
        bm = bmesh.new(); vs = [bm.verts.new(v) for v in out]
        for f in F: bm.faces.new([vs[i] for i in f])
        bm.normal_update()
        ob = obj_from_bm('Chassis_Tub', bm, [self.M['inner']]); mark_sharp(ob, 40)
        self.attach(ob, self.body); return ob

    def grille_insert(self, cell=0.026, bar=0.0045, depth=0.03, hexes=True):
        g = self.parts.pop('Grille')
        bvh = BVHTree.FromObject(g, bpy.context.evaluated_depsgraph_get())
        back = offset_copy(g, 'Grille_Backing', -depth, self.M['under'])
        thicken(back, 0.002, 0)
        bpy.data.objects.remove(g)
        lo, hi = bbox(back)
        bm = bmesh.new()
        dx, dz = cell * math.sqrt(3), cell * 1.5
        j = 0; z = lo.z
        while z < hi.z + cell:
            x = lo.x + (dx / 2 if j % 2 else 0)
            while x < hi.x + cell:
                hit = bvh.ray_cast(Vector((x, -10, z)), Vector((0, 1, 0)))
                if hit[0] is not None:
                    base = hit[0] - hit[1] * (depth * 0.45)
                    ring_o, ring_i = [], []
                    for k in range(6):
                        a = math.pi / 6 + k * math.pi / 3
                        po = Vector((math.cos(a), 0, math.sin(a))) * cell; pi = po * (1 - bar / cell * 2.2)
                        ring_o.append(bm.verts.new(base + po)); ring_i.append(bm.verts.new(base + pi))
                    for k in range(6):
                        k2 = (k + 1) % 6
                        bm.faces.new((ring_o[k], ring_o[k2], ring_i[k2], ring_i[k]))
                x += dx
            z += dz; j += 1
        bm.normal_update()
        for f in bm.faces:
            if f.normal.y > 0: f.normal_flip()
        ob = obj_from_bm('Grille_Mesh', bm, [self.M['black']]); thicken(ob, depth * 0.8, 0, offset=-1)
        for o in (back, ob): self.attach(o, self.group('Grille', None, self.body))

    # ---- wheels -----------------------------------------------------------
    def wheels(self, spoke_fn):
        S = self.S; w = dict(S['wheel']); w['spoke_fn'] = spoke_fn
        for i, ax in enumerate(S['axles']):
            track = S['trackF'] if i == 0 else S['trackR']
            for side, sl in ((1, 'L'), (-1, 'R')):
                tag = f'{"F" if i == 0 else "R"}{sl}'
                hub = self.bl(ax, side * track / 2, w['R'])
                knuckle = empty(f'Suspension_{tag}', hub, self.root, 0.2)
                root, cal = build_wheel(f'Wheel_{tag}', w, self.M)
                root.location = hub
                if side < 0: root.rotation_euler = (0, 0, math.pi)
                cal.location = hub + Vector((-side * 0.01, cal.location.y if side > 0 else cal.location.y, cal.location.z))
                cal.location = hub + Vector((side * -0.005, -0.03 if i == 0 else 0.03, w['rotorR'] - 0.035))
                parent_keep(root, knuckle); parent_keep(cal, knuckle)

    # ---- hierarchy & pivots ------------------------------------------------
    def organise(self, pivots, groups_of):
        """pivots: {group_name: (x, y, z, side_aware)}; groups_of(panel_name) -> group name or None (body)."""
        for name, ob in list(self.parts.items()):
            g = groups_of(name)
            if g is None:
                set_origin(ob, centroid(ob)); self.attach(ob, self.body)
            else:
                parent = self.groups.get(g) or self.group(g, self._pivot(g, pivots), self.root)
                set_origin(ob, centroid(ob)); self.attach(ob, parent)
        for k, ob in getattr(self, 'lamp_inners', {}).items():
            set_origin(ob, centroid(ob)); self.attach(ob, self.parts[k])

    def _pivot(self, g, pivots):
        for key, (x, y, z) in pivots.items():
            if g.startswith(key):
                side = -1 if g.endswith('R') and key.startswith('Door') else 1
                return self.bl(x, y * side, z)
        return (0, 0, 0)

    # ---- export ------------------------------------------------------------
    def export(self, outdir):
        os.makedirs(outdir, exist_ok=True)
        name = self.S['name']
        for o in bpy.data.objects:
            if o.type == 'MESH':
                o.data.name = o.name
        bpy.context.view_layer.update()
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(outdir, name + '.blend'))
        bpy.ops.export_scene.fbx(filepath=os.path.join(outdir, name + '.fbx'), apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS',
                                 bake_space_transform=True, axis_forward='-Z', axis_up='Y', object_types={'EMPTY', 'MESH'},
                                 mesh_smooth_type='FACE', use_mesh_modifiers=True, add_leaf_bones=False)
        bpy.ops.export_scene.gltf(filepath=os.path.join(outdir, name + '.glb'), export_format='GLB', export_apply=True)
        tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in bpy.data.objects if o.type == 'MESH')
        meshes = sum(1 for o in bpy.data.objects if o.type == 'MESH')
        print(f'exported {name}: {meshes} meshes, {tris:,} tris')

if __name__ == '__main__':
    key = sys.argv[1]
    st = int(sys.argv[sys.argv.index('--stations') + 1]) if '--stations' in sys.argv else 380
    car = importlib.import_module(key)
    B = Builder(car, st)
    B.finish_panels()
    car.details(B)
    B.export(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'models', 'v1'))
