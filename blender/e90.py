"""2006 BMW 325xi (E90) — profile tables, panel map and detail parts."""
import math
from carlib import *

SPEC = dict(
    key='e90', name='BMW_325xi_2006_E90', paint=0x40454c,
    L=4.520, W=1.817, H=1.421,
    axles=[0.765, 0.765 + 2.760], trackF=1.500, trackR=1.513, groundClear=0.140,
    wheelR=0.317, archR=0.360, archShape=1.0, roofRound=0.055,
    fn=dict(
        zBot=[[0, 0.36], [0.05, 0.27], [0.2, 0.21], [0.6, 0.195], [1.3, 0.185], [3.0, 0.185], [3.9, 0.22], [4.30, 0.28], [4.46, 0.34], [4.52, 0.40]],
        zTop=[[0, 0.60], [0.025, 0.665], [0.09, 0.722], [0.30, 0.765], [0.80, 0.825], [1.45, 0.905], [1.53, 0.925],
              [2.25, 1.385], [2.50, 1.416], [2.80, 1.421], [3.10, 1.398], [3.25, 1.36],
              [3.86, 1.045], [3.98, 1.030], [4.30, 1.022], [4.43, 1.005], [4.485, 0.94], [4.512, 0.80], [4.52, 0.62]],
        zBelt=[[0, 0.60], [0.15, 0.71], [0.6, 0.80], [1.5, 0.915], [1.6, 0.93], [2.6, 0.965], [3.4, 0.995], [3.75, 1.02], [4.52, 1.0]],
        hw=[[0, 0.62], [0.03, 0.75], [0.12, 0.84], [0.40, 0.893], [0.85, 0.9085], [3.6, 0.9085], [4.1, 0.896], [4.38, 0.862], [4.48, 0.80], [4.52, 0.70]],
        hwTop=[[0, 0.54], [0.15, 0.70], [0.8, 0.78], [1.5, 0.785], [2.25, 0.665], [2.8, 0.655], [3.25, 0.66], [3.9, 0.765], [4.3, 0.78], [4.52, 0.62]],
        crown=[[0, 0.02], [0.8, 0.045], [1.5, 0.05], [1.6, 0.03], [2.3, 0.04], [3.3, 0.04], [3.9, 0.03], [4.52, 0.04]],
        inset=[[0, 0.015], [1.35, 0.03], [1.62, 0.07], [3.70, 0.07], [3.95, 0.03], [4.52, 0.015]],
    ),
    wheel=dict(R=0.3175, width=0.225, rimR=0.216, rotorR=0.150, tread_depth=0.009, tread_count=44, tread_rows=4, tread_pattern='winter', cap_mat='chrome', dish=True),
)
AXF, AXR = SPEC['axles']
F = {k: mono(v) for k, v in SPEC['fn'].items()}

def a_line(z): return 1.64 + (z - 0.94) * 1.6
def c_line(z): return 3.44 - (z - 1.0) * 0.95 + 0.30 * max(0.0, z - 1.25)
def rd_edge(z):
    r = 0.43
    if z < SPEC['wheelR'] + r: return min(3.40, AXR - math.sqrt(max(0.0, r * r - (z - SPEC['wheelR']) ** 2)))
    return 3.40

def classify(x, y, z, n, seg, s, side):
    hwt = float(F['hwTop'](x))
    # ---- glass
    if seg == SEG_TOP and 1.57 < x < 2.20 and y < hwt - 0.06: return 'Windshield', 'glass'
    if seg == SEG_TOP and 3.31 < x < 3.82 and y < hwt - 0.07: return 'Rear_Glass', 'glass'
    if seg == SEG_TOP and 2.42 < x < 3.02 and y < 0.37: return 'Sunroof', 'glass'
    if seg == SEG_GREEN and 1.55 < x < 3.80 and 0.08 < s < 0.86 and a_line(z) < x < c_line(z):
        if 2.60 < x < 2.69 or 3.16 < x < 3.19: pass
        elif x < 2.645: return f'Door_F{side}_Glass', 'glass'
        else: return f'Door_R{side}_Glass', 'glass'
    # ---- lamps
    if x < 0.24 and y > 0.37 and 0.615 + 0.08 * (x / 0.24) < z < 0.725 + 0.02 * (x / 0.24): return f'Headlight_{side}', 'lens'
    if x > 4.25 and 0.84 < z < 0.955 and y > 0.47: return f'Taillight_{side}', 'tail'
    if x > 4.40 and 0.885 < z < 0.955 and 0.30 < y <= 0.47: return f'Trunk_Taillight_{side}', 'tail'
    if seg in (SEG_BOTTOM, SEG_CORNER): return 'Underbody', 'under'
    # ---- top surfaces
    if seg == SEG_TOP:
        if x < 0.10 + 0.05 * (y / 0.8) ** 2: return 'Bumper_Front', 'paint'
        if x < 1.50: return 'Hood', 'paint'
        if x < 1.57: return 'Cowl', 'plastic'
        if x < 3.82: return 'Roof', ('black' if x < 3.31 and y > hwt - 0.06 and x > 3.2 else 'paint')
        if x < 3.87: return 'Roof', 'paint'
        return 'Trunk', 'paint'
    # ---- rear face
    if x > 4.28 and z > 0.80 and y < 0.47: return 'Trunk', 'paint'
    if x > 3.95 and z < 0.81: return 'Bumper_Rear', ('plastic' if z < 0.29 else 'paint')
    # ---- front fascia
    if seg == SEG_CAP or (x < 0.42 + (0.70 - z) * 0.35 and z < 0.72):
        if x < 0.16 and 0.55 < z < 0.69 and y < 0.25: return 'Kidney_Surround', 'black'
        if x < 0.20 and y < 0.58 and 0.24 < z < 0.42: return 'Bumper_Front', 'plastic'
        if x < 0.10 and 0.60 < y < 0.72 and 0.28 < z < 0.35: return f'Foglight_{side}', 'lens'
        return 'Bumper_Front', 'paint'
    # ---- greenhouse frame
    if seg == SEG_GREEN:
        if x < a_line(z) - 0.02: return f'APillar_{side}', 'paint'
        if x < 2.645: return f'Door_F{side}', 'black'
        if x < c_line(z) + 0.01: return f'Door_R{side}', 'black'
        return f'Quarter_{side}', 'paint'
    # ---- side sheet metal
    if x < 1.55: return f'Fender_{side}', 'paint'
    if z < 0.245 and 1.5 < x < 3.3: return f'Rocker_{side}', 'paint'
    if x < 2.645: return f'Door_F{side}', 'paint'
    if x < rd_edge(z): return f'Door_R{side}', 'paint'
    return f'Quarter_{side}', 'paint'

PIVOTS = {
    'Door_F': (1.57, 0.88, 0.62), 'Door_R': (2.665, 0.88, 0.62),
    'Hood': (1.48, 0.0, 0.92), 'Trunk': (3.86, 0.0, 1.04),
}

def spokes(r, a):
    """5 double spokes: each pair diverges from the hub toward the rim."""
    per = 2 * math.pi / 5
    da = ((a - math.pi / 2) % per); da = min(da, per - da)
    t = (r - 0.07) / (0.212 - 0.07)
    sep = 0.012 + 0.020 * t            # half distance between the twin spokes (m, at radius r)
    hw = 0.0105 + 0.002 * t
    d = da * r
    return abs(d - sep) < hw

def groups_of(name):
    for g in ('Door_FL', 'Door_FR', 'Door_RL', 'Door_RR'):
        if name.startswith(g): return g
    if name == 'Hood': return 'Hood'
    if name.startswith('Trunk'): return 'Trunk'
    return None

def kidney(B, side):
    M = B.M; sl = 'L' if side > 0 else 'R'
    loc, n = B.front_hit(side * 0.125, 0.62)
    bm = bmesh.new()
    w, h = 0.205, 0.13
    def outline(sc):
        pts = []
        for k in range(48):
            t = 2 * math.pi * k / 48
            c, s_ = math.cos(t), math.sin(t)
            px = math.copysign(abs(c) ** 0.55, c) * w / 2 * sc
            pz = math.copysign(abs(s_) ** 0.7, s_) * h / 2 * sc + (0.008 * (px / (w / 2)) * -side)
            pts.append((px, pz))
        return pts
    o, i = outline(1.0), outline(0.86)
    vo = [bm.verts.new((p[0], 0, p[1])) for p in o]; vi = [bm.verts.new((p[0], 0, p[1])) for p in i]
    for k in range(48):
        k2 = (k + 1) % 48; bm.faces.new((vo[k], vo[k2], vi[k2], vi[k]))
    bm.normal_update()
    frame = obj_from_bm(f'Kidney_{sl}', bm, [M['black']]); thicken(frame, 0.028, 0.004, offset=1)
    back = superellipsoid(f'Kidney_{sl}_Backing', w * 0.44, 0.004, h * 0.44, M['under'], n=3.5); back.location = (0, 0.012, 0)
    sl_bm = bmesh.new()
    for j in range(9):
        for dd in (-0.0035, 0.0035):
            box_bm(sl_bm, ((j - 4) * 0.019 + dd, -0.004, 0), (0.0042, 0.022, h * 0.80))
    bmesh.ops.bevel(sl_bm, geom=sl_bm.edges[:], offset=0.0012, segments=1, affect='EDGES')
    slats = obj_from_bm(f'Kidney_{sl}_Slats', sl_bm, [M['black']]); mark_sharp(slats)
    root = empty(f'Kidney_{sl}_Pivot', (0, 0, 0))
    for o_ in (frame, back, slats): parent_keep(o_, root)
    root.location = loc - n * 0.004
    root.rotation_euler = (math.atan2(-n.z, -n.y) * -1 * 0.0 - math.radians(18), 0, side * math.radians(-8))
    parent_keep(root, B.parts['Kidney_Surround'])

def details(B):
    M = B.M
    B.organise(PIVOTS, groups_of)
    B.tub()
    G = B.groups
    for side, sl in ((1, 'L'), (-1, 'R')):
        kidney(B, side)
        loc, n = B.side_hit(1.66, 0.96, side)
        base = rounded_box(f'Mirror_{sl}', (0.085, 0.10, 0.045), M['black'], 0.011); base.location = loc + Vector((side * 0.03, 0.01, 0))
        hous = superellipsoid(f'Mirror_{sl}_Housing', 0.118, 0.06, 0.07, M['black'], n=2.4); hous.location = loc + Vector((side * 0.145, 0.03, 0.04))
        mg = superellipsoid(f'Mirror_{sl}_Glass', 0.1, 0.004, 0.056, M['mirror'], n=3.2); mg.location = hous.location + Vector((0, 0.058, 0))
        parent_keep(mg, hous); parent_keep(hous, base); parent_keep(base, G[f'Door_F{sl}'])
        for d, hx in (('F', 2.40), ('R', 3.20)):
            loc, n = B.side_hit(hx, 0.875, side)
            h = rounded_box(f'Door_{d}{sl}_Handle', (0.03, 0.16, 0.026), M['paint'], 0.010); h.location = loc + n * 0.012
            parent_keep(h, G[f'Door_{d}{sl}'])
        loc, n = B.side_hit(1.02, 0.672, side)
        rep = superellipsoid(f'Fender_{sl}_Repeater', 0.005, 0.05, 0.012, M['lens'], n=2.2); rep.location = loc + n * 0.002
        parent_keep(rep, B.parts[f'Fender_{sl}'])
        for i, yy in enumerate((0.47, 0.64)):
            loc, n = B.front_hit(side * yy, 0.668)
            if loc:
                cup = lathe(f'Headlight_{sl}_Bowl{i}', [(0.0, 0.0), (0.03, 0.0), (0.045, -0.03), (0.045, -0.05)], 36, M['reflector'])
                cup.rotation_euler = (0, 0, math.pi / 2); cup.location = loc - n * 0.012; parent_keep(cup, B.parts[f'Headlight_{sl}'])
        loc, n = B.side_hit(0.16, 0.66, side)
        if loc:
            am = rounded_box(f'Headlight_{sl}_Amber', (0.006, 0.07, 0.03), M['amber'], 0.004); am.location = loc - n * 0.005
            parent_keep(am, B.parts[f'Headlight_{sl}'])
    for ty in (0.37, 0.455):          # twin tips, car's left
        tip = lathe('Exhaust_Tip', [(0.030, -0.08), (0.035, -0.08), (0.036, 0.06), (0.031, 0.06)], 32, M['chrome'])
        tip.rotation_euler = (0, 0, math.pi / 2); tip.location = B.bl(B.L - 0.07, ty, 0.255); B.attach(tip, B.body)
    loc, n = B.top_hit(3.15, 0)
    fin = superellipsoid('Antenna_Fin', 0.02, 0.075, 0.04, M['black'], n=2.2); fin.location = loc + Vector((0, 0, 0.01)); B.attach(fin, B.body)
    loc, n = B.top_hit(3.33, 0)
    hbl = rounded_box('Roof_BrakeLight', (0.30, 0.02, 0.012), M['tail'], 0.004); hbl.location = loc - n * 0.012; B.attach(hbl, B.body)
    for i, (y0, ang) in enumerate(((0.10, 8), (-0.55, 5))):
        loc, n = B.top_hit(1.62, y0 + 0.25)
        wp = rounded_box(f'Wiper_{i}', (0.55, 0.016, 0.012), M['black'], 0.004); wp.location = loc + n * 0.02
        wp.rotation_euler = (0, math.radians(-10), math.radians(ang)); B.attach(wp, B.body)
    loc, n = B.front_hit(0, 0.84, rear=True)
    pl = rounded_box('Trunk_Plate', (0.305, 0.006, 0.152), M['plate'], 0.002); pl.location = loc + n * 0.005; parent_keep(pl, G['Trunk'])
    loc, n = B.top_hit(0.11, 0)
    em = cylinder('Emblem_Hood', 0.041, 0.008, M['chrome'], 48, axis='Z'); em.location = loc + n * 0.003; em.rotation_euler = (math.radians(-22), 0, 0); parent_keep(em, G['Hood'])
    loc, n = B.front_hit(0.18, 0.985, rear=True)
    em = cylinder('Trunk_Emblem', 0.039, 0.008, M['chrome'], 48, axis='Y'); em.location = loc + n * 0.004; parent_keep(em, G['Trunk'])
    B.wheels(spokes)
