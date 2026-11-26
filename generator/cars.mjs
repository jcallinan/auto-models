// Vehicle specs. All dimensions in metres; x measured back from the front bumper.
import { mono, buildCar, surfaceY, faceX, place, ellipsoid, box, THREE, SEG } from './builder.mjs';

const inPoly = (x, z, poly) => {
  let c = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [xi, zi] = poly[i], [xj, zj] = poly[j];
    if ((zi > z) !== (zj > z) && x < (xj - xi) * (z - zi) / (zj - zi) + xi) c = !c;
  }
  return c;
};

// =====================================================================
// 2023 Toyota RAV4 LE AWD — Magnetic Gray Metallic, aftermarket black mesh
// wheels on all-terrain tyres.  Spec: L 180.9in, W 73.0in, H 67.0in,
// WB 105.9in, track 63.4/64.6in (Toyota), clearance 8.4in.
// =====================================================================
const rav4 = {
  name: 'Toyota_RAV4_2023_LE_AWD',
  paintHex: 0x4c4f53,
  L: 4.595, W: 1.855, H: 1.702,
  axles: [0.94, 0.94 + 2.690],
  trackF: 1.610, trackR: 1.641,
  groundClear: 0.213,
  wheelR: 0.362, archR: 0.425, archShape: 1.0,
  shoulderInset: 0.075, roofRound: 0.06,
  tire: { R: 0.362, width: 0.225, rimR: 0.216, rotorR: 0.150, style: 'mesh-y10', capMat: 'rim',
          tread: { count: 34, rows: 3, depth: 0.012 } },
  fn: {
    zBot: mono([[0, 0.50], [0.05, 0.42], [0.25, 0.36], [0.55, 0.31], [1.4, 0.25], [3.2, 0.25], [4.05, 0.33], [4.40, 0.40], [4.595, 0.50]]),
    zTop: mono([[0, 0.80], [0.03, 0.88], [0.10, 0.96], [0.30, 1.01], [0.90, 1.07], [1.52, 1.115], [1.62, 1.15],
                [2.30, 1.655], [2.55, 1.690], [3.00, 1.700], [3.60, 1.690], [4.05, 1.665], [4.18, 1.630],
                [4.36, 1.24], [4.48, 1.10], [4.555, 0.98], [4.585, 0.80], [4.595, 0.62]]),
    zBelt: mono([[0, 0.78], [0.12, 0.93], [0.4, 0.99], [1.0, 1.05], [1.6, 1.10], [2.5, 1.125], [3.55, 1.16], [3.85, 1.22], [4.2, 1.22], [4.45, 1.10], [4.595, 0.62]]),
    hw: mono([[0, 0.60], [0.04, 0.75], [0.15, 0.855], [0.35, 0.905], [0.8, 0.926], [3.7, 0.9275], [4.2, 0.912], [4.45, 0.878], [4.56, 0.80], [4.595, 0.68]]),
    hwTop: mono([[0, 0.52], [0.2, 0.74], [0.9, 0.81], [1.55, 0.80], [2.3, 0.70], [3.0, 0.695], [4.0, 0.685], [4.2, 0.68], [4.40, 0.74], [4.595, 0.60]]),
    crown: mono([[0, 0.02], [0.8, 0.05], [1.55, 0.05], [1.65, 0.03], [2.3, 0.04], [4.2, 0.04], [4.595, 0.06]]),
    inset: mono([[0, 0.015], [1.4, 0.03], [1.75, 0.075], [4.05, 0.075], [4.35, 0.03], [4.595, 0.015]]),
  },
  paint(x, y, z, seg, s, p, spec) {
    const L = spec.L;
    // ---- front fascia (end cap, seg -1) and nose
    if (x < 0.14 && z > 0.50 && z < 0.79 && y < 0.40 + (0.79 - z) * 0.45) return 'black';      // big trapezoid grille
    if (x < 0.10 && z >= 0.80 && z < 0.865 && y < 0.36) return 'black';                       // upper grille slot
    if (x < 0.32 && y > 0.40 && z > 0.855 + 0.07 * (x / 0.32) && z < 0.948) return 'light'; // headlights
    if (x < 0.40 && z < 0.47) return 'plastic';                                                // lower bumper
    if (x < 0.30 && y > 0.62 && z < 0.66 && z > 0.47) return 'plastic';                        // fog bezels
    // ---- rear
    if (x > 4.42 && z > 0.985 && z < 1.105 && y > 0.32) return 'tail';
    if (x > 4.30 && z < 0.50) return 'plastic';                                                // rear lower bumper
    // ---- underside & cladding
    if (seg === SEG.BOTTOM || seg === SEG.CORNER) return 'plastic';
    if (seg === SEG.SIDE && z < spec.fn.zBot(Math.min(Math.max(x, 1.4), 3.2)) + 0.115 && x > 1.2 && x < 3.4) return 'plastic'; // rocker cladding
    for (const ax of spec.axles) {
      const d = Math.hypot(x - ax, z - spec.wheelR);
      if (d < spec.archR + 0.07 && z > 0.28 && (seg === SEG.SIDE || seg === SEG.CORNER)) return 'plastic';   // arch flares
    }
    // ---- glass
    if (seg === SEG.TOP && x > 1.65 && x < 2.26 && y < p.hwTop - 0.07) return 'glass';          // windshield
    if (seg === SEG.TOP && x > 4.20 && x < 4.43 && y < p.hwTop - 0.09) return 'glass';          // rear glass
    if (seg === SEG.GREEN) {
      if (x < 1.60 || x > 4.20) return 'paint';
      const aLine = 1.72 + (z - 1.14) * (0.70 / 0.52);   // front edge of front door glass (behind A-pillar)
      const inBand = s > 0.07 && s < 0.86;
      if (!inBand) return x > 1.68 && x < 4.05 ? 'black' : 'paint';
      if (x < aLine) return 'paint';
      if (x > 2.98 && x < 3.07) return 'black';           // B-pillar
      if (x > 3.64 && x < 3.71) return 'black';           // rear-door/quarter divider
      const dLine = 4.06 - (z - 1.22) * 0.30;             // D-pillar
      if (x > dLine) return 'paint';
      return 'glass';
    }
    return 'paint';
  },
  details(car, m, spec) {
    // mirrors (body colour caps on black base)
    for (const sd of [1, -1]) {
      const yS = surfaceY(spec, 1.80, 1.13);
      const cap = ellipsoid(0.13, 0.085, 0.07, m.paint, `Mirror_${sd > 0 ? 'L' : 'R'}`);
      place(cap, spec, 1.86, sd * (yS + 0.115), 1.18); car.add(cap);
      const base = box(0.10, 0.05, 0.09, m.black, 'Mirror_Base'); place(base, spec, 1.80, sd * (yS + 0.03), 1.15); car.add(base);
      // door handles
      for (const hx of [2.72, 3.48]) {
        const y = surfaceY(spec, hx, 1.06);
        const h = box(0.03, 0.025, 0.17, m.paint, 'Door_Handle', 0.01);
        place(h, spec, hx, sd * (y + 0.008), 1.06); car.add(h);
      }
      // fuel door outline is just paint — skip
      // exhaust tips (one each side)
      const tip = new THREE.CylinderGeometry(0.035, 0.035, 0.12, 24, 1, true); tip.rotateX(Math.PI / 2);
      const t = Object.assign(new THREE.Mesh(tip, m.chrome), { name: 'Exhaust_Tip' });
      place(t, spec, faceX(spec, 0.42, 1) - 0.02, sd * 0.42, 0.35); car.add(t);
    }
    // roof spoiler over the rear glass
    const sp = box(1.30, 0.05, 0.22, m.paint, 'Roof_Spoiler', 0.02); place(sp, spec, 4.13, 0, 1.655); sp.rotation.x = 0.12; car.add(sp);
    const sp2 = box(1.10, 0.02, 0.10, m.black, 'Spoiler_Lip'); place(sp2, spec, 4.25, 0, 1.625); car.add(sp2);
    // shark fin antenna
    const fin = ellipsoid(0.02, 0.035, 0.08, m.paint, 'Shark_Fin'); place(fin, spec, 3.95, 0, 1.70); car.add(fin);
    // emblems (plain placeholders, no logo artwork)
    const ef = ellipsoid(0.010, 0.045, 0.065, m.chrome, 'Emblem_Front'); ef.rotation.y = 0;
    place(ef, spec, faceX(spec, 0.78, 0) - 0.01, 0, 0.78); ef.scale.set(1, 1, 1); car.add(ef);
    const er = ellipsoid(0.010, 0.04, 0.06, m.chrome, 'Emblem_Rear'); place(er, spec, faceX(spec, 1.04, 1) + 0.005, 0, 1.04); car.add(er);
    // rear plate (blank)
    const pz = 0.90, px = faceX(spec, pz, 1);
    const pl = box(0.305, 0.152, 0.006, m.plate, 'License_Plate_Rear'); place(pl, spec, px + 0.006, 0, pz); pl.rotation.x = -0.12; car.add(pl);
    // third brake light + rear wiper
    const hbl = box(0.45, 0.02, 0.01, m.tail, 'High_Brake_Light'); place(hbl, spec, 4.21, 0, 1.635); car.add(hbl);
    const wip = box(0.012, 0.012, 0.32, m.black, 'Rear_Wiper'); place(wip, spec, 4.37, 0.08, 1.20); wip.rotation.set(-1.15, 0, 0); wip.rotation.order = 'YXZ'; wip.rotation.y = Math.PI / 2 - 0.5; car.add(wip);
  },
};

// =====================================================================
// 2006 BMW 325xi (E90) — Sparkling Graphite Metallic, gloss-black double-slat
// kidneys, black mirror caps, matte black 5-double-spoke 17s on winter tyres.
// Spec: L 4520, W 1817, H 1421, WB 2760, track 1500/1513 mm (BMW).
// =====================================================================
const e90 = {
  name: 'BMW_325xi_2006_E90',
  paintHex: 0x3b4048,
  L: 4.520, W: 1.817, H: 1.421,
  axles: [0.765, 0.765 + 2.760],
  trackF: 1.500, trackR: 1.513,
  groundClear: 0.140,
  wheelR: 0.317, archR: 0.360, archShape: 1.0,
  shoulderInset: 0.07, roofRound: 0.055,
  tire: { R: 0.317, width: 0.225, rimR: 0.216, rotorR: 0.150, style: 'bmw-double5', capMat: 'chrome',
          tread: { count: 46, rows: 4, depth: 0.007 } },
  fn: {
    zBot: mono([[0, 0.36], [0.05, 0.27], [0.2, 0.21], [0.6, 0.195], [1.3, 0.185], [3.0, 0.185], [3.9, 0.22], [4.30, 0.28], [4.46, 0.34], [4.52, 0.40]]),
    zTop: mono([[0, 0.58], [0.03, 0.655], [0.10, 0.715], [0.30, 0.76], [0.80, 0.82], [1.45, 0.905], [1.53, 0.925],
                [2.25, 1.385], [2.50, 1.416], [2.80, 1.421], [3.10, 1.398], [3.25, 1.36],
                [3.86, 1.045], [3.98, 1.030], [4.30, 1.022], [4.43, 1.005], [4.485, 0.94], [4.512, 0.80], [4.52, 0.62]]),
    zBelt: mono([[0, 0.58], [0.15, 0.70], [0.6, 0.80], [1.5, 0.915], [1.6, 0.93], [2.6, 0.965], [3.4, 0.995], [3.75, 1.02], [4.52, 1.0]]),
    hw: mono([[0, 0.60], [0.04, 0.73], [0.15, 0.835], [0.40, 0.893], [0.85, 0.9085], [3.6, 0.9085], [4.1, 0.896], [4.38, 0.862], [4.48, 0.80], [4.52, 0.70]]),
    hwTop: mono([[0, 0.50], [0.2, 0.70], [0.8, 0.78], [1.5, 0.785], [2.25, 0.665], [2.8, 0.655], [3.25, 0.66], [3.9, 0.765], [4.3, 0.78], [4.52, 0.62]]),
    crown: mono([[0, 0.02], [0.8, 0.045], [1.5, 0.05], [1.6, 0.03], [2.3, 0.04], [3.3, 0.04], [3.9, 0.03], [4.52, 0.04]]),
    inset: mono([[0, 0.015], [1.4, 0.03], [1.68, 0.07], [3.75, 0.07], [4.0, 0.03], [4.52, 0.015]]),
  },
  paint(x, y, z, seg, s, p, spec) {
    // front
    if (x < 0.24 && y > 0.37 && z > 0.615 + 0.08 * (x / 0.24) && z < 0.725 + 0.02 * (x / 0.24)) return 'light';   // headlights
    if (x < 0.20 && y < 0.56 && z > 0.24 && z < 0.42) return 'plastic';                          // lower intake
    if (x < 0.10 && y > 0.60 && y < 0.72 && z > 0.28 && z < 0.35) return 'light';                // fog lights
    if (x > 0.95 && x < 1.06 && z > 0.655 && z < 0.69 && seg === SEG.SIDE) return 'light';       // side repeater
    // rear: L-shaped tail lamps
    if (x > 4.25 && z > 0.84 && z < 0.955 && y > 0.47) return 'tail';
    if (x > 4.40 && z > 0.885 && z < 0.955 && y > 0.30) return 'tail';
    if (x > 4.40 && z < 0.30 && y < 0.70) return 'plastic';                                       // rear diffuser strip
    if (seg === SEG.BOTTOM || seg === SEG.CORNER) return 'plastic';
    // glass
    if (seg === SEG.TOP && x > 1.57 && x < 2.20 && y < p.hwTop - 0.06) return 'glass';
    if (seg === SEG.TOP && x > 3.31 && x < 3.82 && y < p.hwTop - 0.07) return 'glass';
    if (seg === SEG.GREEN) {
      if (x < 1.55 || x > 3.80) return 'paint';
      const aLine = 1.64 + (z - 0.94) * 1.6;
      const inBand = s > 0.08 && s < 0.86;
      const cLine = 3.44 - (z - 1.0) * 0.95 + 0.10 * Math.max(0, z - 1.25) * 3;   // Hofmeister kink
      if (!inBand) return (x > aLine - 0.05 && x < cLine + 0.04) ? 'black' : 'paint';
      if (x < aLine) return 'paint';
      if (x > 2.60 && x < 2.69) return 'black';    // B-pillar
      if (x > 3.16 && x < 3.19) return 'black';    // rear-door fixed glass divider
      if (x > cLine) return 'paint';
      return 'glass';
    }
    return 'paint';
  },
  details(car, m, spec) {
    for (const sd of [1, -1]) {
      const yS = surfaceY(spec, 1.68, 0.95);
      const cap = ellipsoid(0.12, 0.08, 0.065, m.black, `Mirror_${sd > 0 ? 'L' : 'R'}`);   // black caps on this car
      place(cap, spec, 1.72, sd * (yS + 0.105), 0.99); car.add(cap);
      const base = box(0.09, 0.045, 0.08, m.black, 'Mirror_Base'); place(base, spec, 1.66, sd * (yS + 0.03), 0.96); car.add(base);
      for (const hx of [2.42, 3.22]) {
        const y = surfaceY(spec, hx, 0.87);
        const h = box(0.028, 0.024, 0.16, m.paint, 'Door_Handle', 0.01);
        place(h, spec, hx, sd * (y + 0.008), 0.87); car.add(h);
      }
    }
    // twin exhaust tips, driver (left) side
    for (const ty of [0.36, 0.45]) {
      const tip = new THREE.CylinderGeometry(0.033, 0.033, 0.14, 24, 1, true); tip.rotateX(Math.PI / 2);
      const t = Object.assign(new THREE.Mesh(tip, m.chrome), { name: 'Exhaust_Tip' });
      place(t, spec, faceX(spec, 0.30, 1) - 0.03, ty, 0.255); car.add(t);
    }
    // kidney grilles (gloss black, double slats)
    const kz = 0.615;
    const kx = faceX(spec, kz, 0);
    for (const sd of [1, -1]) {
      const k = new THREE.Group(); k.name = `Kidney_${sd > 0 ? 'L' : 'R'}`;
      const sh = new THREE.Shape();
      const w = 0.21, h = 0.135;
      // kidney outline: rounded, inner edge slightly taller
      sh.moveTo(-w / 2 + 0.03, -h / 2 + 0.01);
      sh.quadraticCurveTo(-w / 2, -h / 2, -w / 2, -h / 2 + 0.04);
      sh.lineTo(-w / 2 + 0.005, h / 2 - 0.035);
      sh.quadraticCurveTo(-w / 2 + 0.01, h / 2, -w / 2 + 0.05, h / 2);
      sh.lineTo(w / 2 - 0.035, h / 2 + 0.008);
      sh.quadraticCurveTo(w / 2, h / 2 + 0.01, w / 2, h / 2 - 0.03);
      sh.lineTo(w / 2 - 0.005, -h / 2 + 0.03);
      sh.quadraticCurveTo(w / 2 - 0.01, -h / 2 - 0.005, w / 2 - 0.045, -h / 2 - 0.004);
      sh.closePath();
      const inner = new THREE.Path(sh.getPoints(24).map(pt => pt.clone().multiplyScalar(0.86)));
      const frame = new THREE.Shape(sh.getPoints(24)); frame.holes.push(inner);
      const fg = new THREE.ExtrudeGeometry(frame, { depth: 0.03, bevelEnabled: true, bevelSize: 0.004, bevelThickness: 0.004, bevelSegments: 2 });
      k.add(Object.assign(new THREE.Mesh(fg, m.black), { name: 'Kidney_Frame' }));
      const back = new THREE.ShapeGeometry(new THREE.Shape(inner.getPoints()));
      const bm = Object.assign(new THREE.Mesh(back, m.under), { name: 'Kidney_Backing' }); bm.position.z = 0.002; k.add(bm);
      for (let i = 0; i < 9; i++) {
        const sx = (i - 4) * 0.019;
        for (const dd of [-0.0035, 0.0035]) {
          const sl = new THREE.BoxGeometry(0.0045, h * 0.86, 0.022); sl.translate(sx + dd, 0, 0.012);
          k.add(Object.assign(new THREE.Mesh(sl, m.black), { name: 'Kidney_Slat' }));
        }
      }
      // shape is in local XY facing +Z; car front is +Z in output space
      place(k, spec, kx - 0.005, sd * 0.125, kz);
      k.rotation.x = -0.32;            // follows the raked nose
      k.rotation.y = sd * 0.10;
      if (sd < 0) k.scale.x = -1;
      car.add(k);
    }
    // emblem placeholders (plain discs) on hood + trunk
    const ef = new THREE.CylinderGeometry(0.041, 0.041, 0.008, 40); ef.rotateX(0.0);
    const e1 = Object.assign(new THREE.Mesh(ef, m.chrome), { name: 'Emblem_Hood' });
    place(e1, spec, 0.12, 0, spec.fn.zTop(0.12) + 0.004); e1.rotation.x = -0.35; car.add(e1);
    const e2 = Object.assign(new THREE.Mesh(ef.clone(), m.chrome), { name: 'Emblem_Trunk' });
    const tx = faceX(spec, 0.975, 1);
    place(e2, spec, tx + 0.004, 0.17, 0.975); e2.rotation.x = Math.PI / 2; car.add(e2);
    // rear plate (blank) on trunk lid between lamps
    const pz = 0.82, px = faceX(spec, pz, 1);
    const pl = box(0.305, 0.152, 0.006, m.plate, 'License_Plate_Rear'); place(pl, spec, px + 0.006, 0, pz); pl.rotation.x = -0.06; car.add(pl);
    // shark fin + 3rd brake light
    const fin = ellipsoid(0.018, 0.03, 0.075, m.black, 'Shark_Fin'); place(fin, spec, 3.12, 0, 1.40); car.add(fin);
    const hbl = box(0.30, 0.015, 0.01, m.tail, 'High_Brake_Light'); place(hbl, spec, 3.30, 0, 1.345); car.add(hbl);
  },
};

export const SPECS = { rav4, e90 };
export function build(key) { return buildCar(SPECS[key]); }
