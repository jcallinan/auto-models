"""2023 Toyota RAV4 LE AWD — profile tables, panel map and detail parts."""
import math
from carlib import *

SPEC = dict(
    key='rav4', name='RAV4_2023_LE', paint=0x5b5e62,
    L=4.595, W=1.855, H=1.702,
    axles=[0.94, 0.94 + 2.690], trackF=1.610, trackR=1.641, groundClear=0.213,
    wheelR=0.362, archR=0.425, archShape=1.0, roofRound=0.06,
    fn=dict(
        zBot=[[0, 0.50], [0.05, 0.42], [0.25, 0.36], [0.55, 0.31], [1.4, 0.25], [3.2, 0.25], [4.05, 0.33], [4.40, 0.40], [4.595, 0.50]],
        zTop=[[0, 0.84], [0.025, 0.93], [0.07, 0.985], [0.25, 1.02], [0.90, 1.075], [1.52, 1.115], [1.62, 1.15],
              [2.30, 1.655], [2.55, 1.690], [3.00, 1.700], [3.60, 1.690], [4.05, 1.665], [4.18, 1.630],
              [4.36, 1.24], [4.48, 1.10], [4.555, 0.98], [4.585, 0.80], [4.595, 0.62]],
        zBelt=[[0, 0.82], [0.10, 0.95], [0.4, 0.99], [1.0, 1.05], [1.6, 1.10], [2.5, 1.125], [3.50, 1.15], [3.78, 1.26], [4.2, 1.28], [4.45, 1.12], [4.595, 0.62]],
        hw=[[0, 0.64], [0.03, 0.78], [0.10, 0.87], [0.30, 0.91], [0.8, 0.926], [3.7, 0.9275], [4.2, 0.912], [4.45, 0.878], [4.56, 0.80], [4.595, 0.68]],
        hwTop=[[0, 0.58], [0.1, 0.74], [0.9, 0.81], [1.55, 0.80], [2.3, 0.70], [3.0, 0.695], [4.0, 0.685], [4.2, 0.68], [4.40, 0.74], [4.595, 0.60]],
        crown=[[0, 0.02], [0.8, 0.05], [1.55, 0.05], [1.65, 0.03], [2.3, 0.04], [4.2, 0.04], [4.595, 0.06]],
        inset=[[0, 0.015], [1.4, 0.03], [1.75, 0.075], [4.05, 0.075], [4.35, 0.03], [4.595, 0.015]],
    ),
    wheel=dict(R=0.362, width=0.225, rimR=0.216, rotorR=0.150, tread_depth=0.014, tread_count=36, tread_rows=3, tread_pattern='at', cap_mat='rim'),
)
AXF, AXR = SPEC['axles']
F = {k: mono(v) for k, v in SPEC['fn'].items()}

def a_line(z):  return 1.72 + (z - 1.14) * (0.70 / 0.52)      # front edge of front-door glass
def d_line(z):  return 4.06 - (z - 1.22) * 0.30                 # rear edge of quarter glass
def rd_edge(z):                                                  # rear-door trailing edge, wraps the rear arch
    if z < 0.851: return AXR - math.sqrt(max(0.0, 0.49 ** 2 - (z - 0.362) ** 2))
    return 3.72

def classify(x, y, z, n, seg, s, side):
    hwt = float(F['hwTop'](x))
    sill = 0.365
    # ---- glass
    if seg == SEG_TOP and 1.66 < x < 2.25 and y < hwt - 0.075: return 'Windshield', 'glass'
    if seg == SEG_TOP and 4.21 < x < 4.42 and y < hwt - 0.095: return 'Liftgate_Glass', 'glass'
    if seg == SEG_GREEN and 1.60 < x < 4.20 and 0.07 < s < 0.86 and a_line(z) < x < d_line(z):
        if 2.975 < x < 3.065 or 3.64 < x < 3.71: pass
        elif x < 3.02: return f'Door_F{side}_Glass', 'glass'
        elif x < 3.675: return f'Door_R{side}_Glass', 'glass'
        else: return f'Quarter_{side}_Glass', 'glass'
    # ---- lamps
    if x < 0.34 and y > 0.40 and 0.855 + 0.07 * (x / 0.34) < z < 0.948: return f'Headlight_{side}', 'lens'
    if x > 4.40 and 0.985 < z < 1.105 and y > 0.32:
        return (f'Taillight_{side}', 'tail') if y > 0.62 else (f'Liftgate_Taillight_{side}', 'tail')
    # ---- grille opening
    if x < 0.14 and 0.50 < z < 0.79 and y < 0.40 + (0.79 - z) * 0.45: return 'Grille', 'plastic'
    if seg in (SEG_BOTTOM, SEG_CORNER): return 'Underbody', 'under'
    # ---- top surfaces
    if seg == SEG_TOP:
        hood_front = 0.13 + 0.06 * (y / 0.8) ** 2
        if x < hood_front: return 'Bumper_Front', 'paint'
        if x < 1.56: return 'Hood', 'paint'
        if x < 1.66: return 'Cowl', 'plastic'
        if x < 4.21: return 'Roof', 'paint'
        return 'Liftgate', 'paint'
    # ---- rear
    if x > 4.24 and z > 0.58 and y < 0.62: return 'Liftgate', 'paint'
    if x > 4.0 and z < 0.60: return 'Bumper_Rear', ('plastic' if z < 0.48 else 'paint')
    # ---- front fascia
    if seg == SEG_CAP and x < 0.2: return 'Bumper_Front', ('plastic' if z < 0.47 else 'paint')
    if x < 0.52 + (0.93 - z) * 0.2 and z < 0.97:
        return 'Bumper_Front', ('plastic' if z < 0.47 or (x < 0.30 and y > 0.62 and z < 0.66) else 'paint')
    # ---- side cladding
    for ax, tag in ((AXF, 'F'), (AXR, 'R')):
        d = math.hypot(x - ax, z - SPEC['wheelR'])
        if d < SPEC['archR'] + 0.07 and z > 0.27 and seg in (SEG_SIDE,): return f'Flare_{tag}{side}', 'plastic'
    if seg == SEG_SIDE and z < sill and 1.2 < x < 3.4: return f'Rocker_{side}', 'plastic'
    # ---- greenhouse frame
    if seg == SEG_GREEN:
        if x < a_line(z) - 0.02: return f'APillar_{side}', 'paint'
        if x < 3.02: return f'Door_F{side}', 'black'
        if x < 3.675: return f'Door_R{side}', 'black'
        if x < d_line(z) + 0.01: return f'Quarter_{side}', 'black'
        return f'Quarter_{side}', 'paint'
    # ---- side sheet metal
    if x < 1.64: return f'Fender_{side}', 'paint'
    if x < 3.02: return f'Door_F{side}', 'paint'
    if x < rd_edge(z): return f'Door_R{side}', 'paint'
    return f'Quarter_{side}', 'paint'

# hinge / pivot points (internal coords). y is filled per side.
PIVOTS = {
    'Door_F': (1.66, 0.90, 0.80), 'Door_R': (3.04, 0.90, 0.80),
    'Hood': (1.55, 0.0, 1.11), 'Liftgate': (4.19, 0.0, 1.635),
}


def spokes(r, a):
    """Split 10-spoke mesh wheel: 10 spokes to a mid ring, 20 spokes to the rim."""
    rm = 0.125
    if abs(r - rm) < 0.008: return True
    n, off, hw = (10, 0.0, 0.012) if r < rm else (20, math.pi / 20, 0.0072)
    per = 2 * math.pi / n; da = (a - off) % per; da = min(da, per - da)
    return da * r < hw

def groups_of(name):
    for g in ('Door_FL', 'Door_FR', 'Door_RL', 'Door_RR'):
        if name.startswith(g): return g
    if name == 'Hood': return 'Hood'
    if name.startswith('Liftgate'): return 'Liftgate'
    return None

def details(B):
    M = B.M
    B.grille_insert(cell=0.022)
    B.organise(PIVOTS, groups_of)
    B.tub()
    G = B.groups
    for side, sl in ((1, 'L'), (-1, 'R')):
        # mirror: base on the door, housing + glass fold around the base
        loc, n = B.side_hit(1.80, 1.15, side)
        base = rounded_box(f'Mirror_{sl}', (0.09, 0.11, 0.05), M['black'], 0.012)
        base.location = loc + Vector((side * 0.035, 0.01, 0.0))
        hous = superellipsoid(f'Mirror_{sl}_Housing', 0.125, 0.065, 0.078, M['paint'], n=2.6)
        hous.location = loc + Vector((side * 0.155, 0.035, 0.045))
        mg = superellipsoid(f'Mirror_{sl}_Glass', 0.108, 0.004, 0.062, M['mirror'], n=3.2)
        mg.location = hous.location + Vector((0, 0.063, 0))
        sig = rounded_box(f'Mirror_{sl}_Signal', (0.07, 0.006, 0.008), M['amber'], 0.003)
        sig.location = hous.location + Vector((side * 0.02, -0.062, -0.02))
        parent_keep(mg, hous); parent_keep(sig, hous); parent_keep(hous, base); parent_keep(base, G[f'Door_F{sl}'])
        # door handles
        for d, hx in (('F', 2.74), ('R', 3.50)):
            loc, n = B.side_hit(hx, 1.06, side)
            h = rounded_box(f'Door_{d}{sl}_Handle', (0.03, 0.17, 0.028), M['paint'], 0.011)
            h.location = loc + n * 0.012
            cup = superellipsoid(f'Door_{d}{sl}_HandleCup', 0.004, 0.10, 0.03, M['black'], n=2.2)
            cup.location = loc + n * 0.001
            parent_keep(h, G[f'Door_{d}{sl}']); parent_keep(cup, G[f'Door_{d}{sl}'])
        # LED projector cups inside the headlight + amber corner
        for i, yy in enumerate((0.55, 0.69)):
            loc, n = B.front_hit(side * yy, 0.905)
            if loc:
                cup = lathe(f'Headlight_{sl}_Projector{i}', [(0.0, 0.0), (0.024, 0.0), (0.03, -0.02), (0.03, -0.04)], 32, M['reflector'])
                cup.rotation_euler = (0, 0, math.pi / 2); cup.location = loc - n * 0.012
                parent_keep(cup, B.parts[f'Headlight_{sl}'])
        loc, n = B.side_hit(0.20, 0.905, side)
        if loc:
            am = rounded_box(f'Headlight_{sl}_Amber', (0.006, 0.09, 0.022), M['amber'], 0.004); am.location = loc - n * 0.004
            parent_keep(am, B.parts[f'Headlight_{sl}'])
        # exhaust tips (one each side)
        tip = lathe(f'Exhaust_{sl}', [(0.031, -0.07), (0.036, -0.07), (0.037, 0.05), (0.032, 0.05)], 32, M['chrome'])
        tip.rotation_euler = (0, 0, math.pi / 2); tip.location = B.bl(B.L - 0.20, side * 0.43, 0.36)
        B.attach(tip, B.body)
    # roof spoiler, antenna, wipers
    loc, n = B.top_hit(4.10, 0)
    sp = rounded_box('Roof_Spoiler', (1.28, 0.26, 0.045), M['paint'], 0.018); sp.location = loc + Vector((0, 0.03, 0.005)); sp.rotation_euler = (math.radians(-7), 0, 0)
    parent_keep(sp, G['Liftgate'])
    hbl = rounded_box('Liftgate_BrakeLight', (0.50, 0.012, 0.016), M['tail'], 0.004); hbl.location = loc + Vector((0, 0.205, -0.012)); parent_keep(hbl, sp)
    loc, n = B.top_hit(3.92, 0)
    fin = superellipsoid('Antenna_Fin', 0.024, 0.085, 0.045, M['paint'], n=2.2); fin.location = loc + Vector((0, 0, 0.012)); B.attach(fin, B.body)
    for i, (y0, ang) in enumerate(((0.08, 6), (-0.62, 4))):
        loc, n = B.top_hit(1.70, y0 + 0.28)
        wp = rounded_box(f'Wiper_{i}', (0.58, 0.016, 0.012), M['black'], 0.004); wp.location = loc + n * 0.02 + Vector((0, 0, 0))
        wp.rotation_euler = (0, math.radians(-12), math.radians(ang)); B.attach(wp, B.body)
    loc, n = B.top_hit(4.30, 0.12)
    rw = rounded_box('Liftgate_Wiper', (0.36, 0.014, 0.012), M['black'], 0.004); rw.location = loc + n * 0.02; rw.rotation_euler = (math.radians(-60), 0, math.radians(18)); parent_keep(rw, G['Liftgate'])
    # rear plate (blank) + plain emblem placeholders (no logo artwork)
    loc, n = B.front_hit(0, 0.90, rear=True)
    pl = rounded_box('Liftgate_Plate', (0.305, 0.006, 0.152), M['plate'], 0.002); pl.location = loc + n * 0.005
    pl.rotation_euler = (math.asin(max(-1, min(1, n.z))), 0, 0); parent_keep(pl, G['Liftgate'])
    for nm, (yy, zz, rear) in (('Emblem_Front', (0, 0.82, False)), ('Liftgate_Emblem', (0, 1.045, True))):
        loc, n = B.front_hit(yy, zz, rear=rear)
        em = superellipsoid(nm, 0.06, 0.008, 0.042, M['chrome'], n=2); em.location = loc + n * 0.006
        if rear: parent_keep(em, G['Liftgate'])
        else: B.attach(em, B.groups['Grille'])
    B.wheels(spokes)
