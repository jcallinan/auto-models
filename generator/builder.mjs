// Parametric car builder: lofts a body from side/plan profile tables (metres),
// paints regions by rule, and adds wheels/mirrors/lights/trim.
// Internal coords: x = length from front bumper (m), y = lateral (+ = car's left), z = up.
// Output (three/glTF): X = lateral (+left), Y = up, Z = forward (front of car at +Z).
import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

// ---------- interpolation ----------
export function mono(pts) {
  const n = pts.length, xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  const d = [], m = new Array(n);
  for (let i = 0; i < n - 1; i++) d.push((ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]));
  m[0] = d[0]; m[n - 1] = d[n - 2];
  for (let i = 1; i < n - 1; i++) m[i] = d[i - 1] * d[i] <= 0 ? 0 : (d[i - 1] + d[i]) / 2;
  for (let i = 0; i < n - 1; i++) {
    if (d[i] === 0) { m[i] = 0; m[i + 1] = 0; continue; }
    const a = m[i] / d[i], b = m[i + 1] / d[i], s = a * a + b * b;
    if (s > 9) { const t = 3 / Math.sqrt(s); m[i] = t * a * d[i]; m[i + 1] = t * b * d[i]; }
  }
  return x => {
    if (x <= xs[0]) return ys[0];
    if (x >= xs[n - 1]) return ys[n - 1];
    let i = 0; while (x > xs[i + 1]) i++;
    const h = xs[i + 1] - xs[i], t = (x - xs[i]) / h, t2 = t * t, t3 = t2 * t;
    return (2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h * m[i] + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h * m[i + 1];
  };
}
const lerp = (a, b, t) => a + (b - a) * t;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

// ---------- materials ----------
export function makeMaterials(paintHex, extra = {}) {
  const M = (o) => new THREE.MeshPhysicalMaterial(o);
  return {
    paint: M({ name: 'Paint', color: paintHex, metalness: 0.55, roughness: 0.32, clearcoat: 1, clearcoatRoughness: 0.06 }),
    glass: M({ name: 'Glass_Tinted', color: 0x0c1015, metalness: 0.85, roughness: 0.05 }),
    black: M({ name: 'Trim_GlossBlack', color: 0x0a0a0b, metalness: 0.3, roughness: 0.22, clearcoat: 0.6 }),
    plastic: M({ name: 'Trim_TexturedBlack', color: 0x1b1b1c, metalness: 0.0, roughness: 0.85 }),
    light: M({ name: 'Headlight_Lens', color: 0xc8d1da, metalness: 0.0, roughness: 0.1, emissive: 0x1a1d22, clearcoat: 1 }),
    tail: M({ name: 'Taillight_Lens', color: 0xa8121a, metalness: 0.25, roughness: 0.18, emissive: 0x3a0004 }),
    amber: M({ name: 'Amber_Lens', color: 0xe07a10, metalness: 0.3, roughness: 0.2 }),
    chrome: M({ name: 'Chrome', color: 0xd4d8db, metalness: 1.0, roughness: 0.12 }),
    rim: M({ name: 'Wheel_MatteBlack', color: 0x151516, metalness: 0.45, roughness: 0.55 }),
    tire: M({ name: 'Tire_Rubber', color: 0x161616, metalness: 0.0, roughness: 0.95 }),
    brake: M({ name: 'Brake_Rotor', color: 0x6f6f70, metalness: 0.85, roughness: 0.45 }),
    caliper: M({ name: 'Brake_Caliper', color: 0x2a2a2a, metalness: 0.5, roughness: 0.5 }),
    under: M({ name: 'Underbody', color: 0x0d0d0d, metalness: 0.0, roughness: 1.0 }),
    plate: M({ name: 'License_Plate', color: 0xe9eef3, metalness: 0.1, roughness: 0.5 }),
    ...extra,
  };
}

// ---------- body ----------
const SEG = { BOTTOM: 0, CORNER: 1, SIDE: 2, SHOULDER: 3, GREEN: 4, TOP: 5 };
const NSEG = [6, 5, 28, 6, 16, 18]; // samples per segment (right half)

function stationParams(spec, x) {
  const f = spec.fn;
  const zTop = f.zTop(x), crown = f.crown(x), rr = spec.roofRound ?? 0.06;
  let zb = f.zBot(x);
  for (const ax of spec.axles) {
    const dx = x - ax;
    if (Math.abs(dx) < spec.archR) zb = Math.max(zb, spec.wheelR + Math.sqrt(spec.archR ** 2 - dx * dx) * spec.archShape);
  }
  zb = Math.min(zb, zTop - 0.05);
  let zBelt = Math.min(f.zBelt(x), zTop - crown - rr + 0.005);
  zBelt = Math.max(zBelt, zb + 0.06);
  const hw = f.hw(x);
  const hwTop = Math.min(f.hwTop(x), hw - 0.02);
  return { x, zb, zBelt, zTop, crown, rr, hw, hwTop, inset: f.inset ? f.inset(x) : (spec.shoulderInset ?? 0.06) };
}

function ringHalf(p) {
  const pts = [];
  const add = (y, z, seg, s) => pts.push({ y, z, seg, s });
  const rb = clamp((p.zBelt - p.zb) * 0.25, 0.01, 0.07);
  const yb = p.hw * 0.965;
  // bottom
  for (let i = 0; i < NSEG[0]; i++) { const t = i / NSEG[0]; add((yb - rb) * t, p.zb, SEG.BOTTOM, t); }
  // corner arc
  for (let i = 0; i < NSEG[1]; i++) {
    const t = i / NSEG[1], a = -Math.PI / 2 + t * Math.PI / 2;
    add(yb - rb + rb * Math.cos(a), p.zb + rb + rb * Math.sin(a), SEG.CORNER, t);
  }
  // side: from (yb, zb+rb) to (hw, zBelt-0.03) with tumble-under
  const zS0 = p.zb + rb, zS1 = Math.max(zS0 + 0.01, p.zBelt - 0.035);
  for (let i = 0; i < NSEG[2]; i++) {
    const t = i / NSEG[2];
    const y = p.hw * (1 - 0.035 * (1 - t) ** 2 - 0.006 * t * t);
    add(y, lerp(zS0, zS1, t), SEG.SIDE, t);
  }
  // shoulder: quadratic bezier to greenhouse base
  const yG = p.hw - p.inset, zG = p.zBelt + 0.01;
  const P0 = [p.hw * 0.994, zS1], C = [p.hw * 0.99, p.zBelt + 0.005], P2 = [yG, zG];
  for (let i = 0; i < NSEG[3]; i++) {
    const t = i / NSEG[3], u = 1 - t;
    add(u * u * P0[0] + 2 * u * t * C[0] + t * t * P2[0], u * u * P0[1] + 2 * u * t * C[1] + t * t * P2[1], SEG.SHOULDER, t);
  }
  // greenhouse side
  const zE = Math.max(zG, p.zTop - p.crown - p.rr);
  for (let i = 0; i < NSEG[4]; i++) {
    const t = i / NSEG[4];
    const y = lerp(yG, p.hwTop, t) + 0.025 * Math.sin(Math.PI * t) * (zE - zG > 0.05 ? 1 : 0);
    add(y, lerp(zG, zE, t), SEG.GREEN, t);
  }
  // top: superellipse from edge to centre
  const n = 2.6;
  for (let i = 0; i <= NSEG[5]; i++) {
    const t = i / NSEG[5], th = t * Math.PI / 2;
    const c = Math.cos(th), s = Math.sin(th);
    add(p.hwTop * Math.pow(c, 2 / n), zE + (p.zTop - zE) * Math.pow(s, 2 / n), SEG.TOP, t);
  }
  return pts;
}

function stationXs(L, n) {
  const xs = [];
  for (let i = 0; i < n; i++) { const u = i / (n - 1); xs.push(L * (0.5 - 0.5 * Math.cos(Math.PI * u)) * 0.35 + L * u * 0.65); }
  return xs;
}

const toV = (x, y, z, L) => new THREE.Vector3(y, z, L / 2 - x); // internal -> three

export function buildBody(spec, mats) {
  const L = spec.L;
  const xs = stationXs(L, spec.stations ?? 280);
  const rings = xs.map(x => { const p = stationParams(spec, x); return { p, half: ringHalf(p) }; });
  const N = rings[0].half.length;
  const M = 2 * N - 2; // closed ring
  const ringIdx = k => (k < N ? k : 2 * N - 2 - k); // map full-ring index -> half index
  const ringSign = k => (k < N ? 1 : -1);

  const pos = [];
  rings.forEach(({ p, half }) => {
    for (let k = 0; k < M; k++) {
      const h = half[ringIdx(k)];
      const v = toV(p.x, h.y * ringSign(k), h.z, L);
      pos.push(v.x, v.y, v.z);
    }
  });
  const buckets = {};
  const push = (key, ...ids) => (buckets[key] ??= []).push(...ids);
  for (let i = 0; i < rings.length - 1; i++) {
    for (let k = 0; k < M; k++) {
      const k2 = (k + 1) % M;
      const a = i * M + k, b = i * M + k2, c = (i + 1) * M + k, d = (i + 1) * M + k2;
      const hk = rings[i].half[ringIdx(k)], hk2 = rings[i].half[ringIdx(k2)];
      const h1 = rings[i + 1].half[ringIdx(k)];
      const x = (rings[i].p.x + rings[i + 1].p.x) / 2;
      const y = Math.abs((hk.y + hk2.y + h1.y) / 3);
      const z = (hk.z + hk2.z + h1.z + rings[i + 1].half[ringIdx(k2)].z) / 4;
      const seg = ringIdx(k) < ringIdx(k2) ? hk.seg : hk2.seg;
      const s = ringIdx(k) < ringIdx(k2) ? hk.s : hk2.s;
      const key = spec.paint(x, y, z, seg, s, rings[i].p, spec) || 'paint';
      // winding: outward
      push(key, a, c, b, b, c, d);
    }
  }
  const geom = new THREE.BufferGeometry();
  geom.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  const index = []; const matList = [];
  Object.entries(buckets).forEach(([key, ids]) => {
    geom.addGroup(index.length, ids.length, matList.length);
    matList.push(mats[key]); for (const v of ids) index.push(v);
  });
  geom.setIndex(index);
  geom.computeVertexNormals();
  const body = new THREE.Mesh(geom, matList);
  body.name = 'Body';

  // end caps (concentric rings to centroid so caps can carry grille/plate regions)
  const caps = new THREE.Group(); caps.name = 'Body_EndCaps';
  for (const end of [0, rings.length - 1]) {
    const { p, half } = rings[end];
    const zc = (p.zb + p.zTop) / 2, levels = 10;
    const cpos = []; const cb = {};
    for (let l = 0; l <= levels; l++) {
      const t = l / levels; // 0 = outer ring, 1 = centre
      for (let k = 0; k < M; k++) {
        const h = half[ringIdx(k)];
        const y = h.y * ringSign(k) * (1 - t), z = lerp(h.z, zc, t);
        const bulge = (end === 0 ? -1 : 1) * 0.012 * Math.sin(Math.PI / 2 * t);
        const v = toV(p.x + bulge, y, z, L); cpos.push(v.x, v.y, v.z);
      }
    }
    for (let l = 0; l < levels; l++) for (let k = 0; k < M; k++) {
      const k2 = (k + 1) % M;
      const a = l * M + k, b = l * M + k2, c = (l + 1) * M + k, d = (l + 1) * M + k2;
      const h = half[ringIdx(k)], t = (l + 0.5) / levels;
      const y = Math.abs(h.y) * (1 - t), z = lerp(h.z, zc, t);
      const key = spec.paint(p.x, y, z, -1, t, p, spec) || 'paint';
      (cb[key] ??= []).push(...(end === 0 ? [a, b, c, b, d, c] : [a, c, b, b, c, d]));
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(cpos, 3));
    const idx = [], ml = [];
    Object.entries(cb).forEach(([key, ids]) => { g.addGroup(idx.length, ids.length, ml.length); ml.push(mats[key]); for (const v of ids) idx.push(v); });
    g.setIndex(idx); g.computeVertexNormals();
    const m = new THREE.Mesh(g, ml); m.name = end === 0 ? 'Body_FrontFascia' : 'Body_RearFascia';
    caps.add(m);
  }
  return { body, caps, rings };
}

// helpers to stick parts onto the surface
export function surfaceY(spec, x, z) {
  const p = stationParams(spec, x); const half = ringHalf(p);
  let best = 0;
  for (let i = 0; i < half.length - 1; i++) {
    const a = half[i], b = half[i + 1];
    if ((a.z - z) * (b.z - z) <= 0 && a.z !== b.z) {
      const t = (z - a.z) / (b.z - a.z); best = Math.max(best, lerp(a.y, b.y, t));
    }
  }
  return best;
}
// x of the front (end=0) or rear (end=1) face at height z, at centreline
export function faceX(spec, z, end) {
  const n = 600;
  for (let i = 0; i <= n; i++) {
    const u = i / n, x = end === 0 ? u * spec.L : spec.L * (1 - u);
    const p = stationParams(spec, x);
    if (z >= p.zb && z <= p.zTop) return x;
  }
  return end === 0 ? 0 : spec.L;
}

// ---------- wheels ----------
function holesBetweenSpokes(angles, halfW, rIn, rOut, minGap = 0.006) {
  const holes = [];
  const n = angles.length;
  for (let i = 0; i < n; i++) {
    const a1 = angles[i], a2 = i === n - 1 ? angles[0] + Math.PI * 2 : angles[i + 1];
    // find the smallest radius where the window opens
    let r0 = rIn;
    while (r0 < rOut && (a2 - a1) * r0 - 2 * halfW(r0) < minGap) r0 += 0.002;
    if (rOut - r0 < 0.015) continue;
    const pts = [];
    const steps = 14;
    for (let j = 0; j <= steps; j++) { const r = rOut; const t = j / steps; const aa = a1 + halfW(r) / r, bb = a2 - halfW(r) / r; const a = lerp(aa, bb, t); pts.push(new THREE.Vector2(r * Math.cos(a), r * Math.sin(a))); }
    for (let j = steps; j >= 0; j--) { const r = lerp(r0, rOut, j / steps); const a = a2 - halfW(r) / r; pts.push(new THREE.Vector2(r * Math.cos(a), r * Math.sin(a))); }
    // inner arc
    const ai = a1 + halfW(r0) / r0, bi = a2 - halfW(r0) / r0;
    for (let j = 1; j < 5; j++) { const a = lerp(bi, ai, j / 5); pts.push(new THREE.Vector2(r0 * Math.cos(a), r0 * Math.sin(a))); }
    for (let j = 0; j <= steps; j++) { const r = lerp(r0, rOut, j / steps); const a = a1 + halfW(r) / r; pts.push(new THREE.Vector2(r * Math.cos(a), r * Math.sin(a))); }
    holes.push(new THREE.Path(pts.reverse()));
  }
  return holes;
}

export function buildWheel(w, mats, name) {
  // w: { R, width, rimR, style, tread }
  const g = new THREE.Group(); g.name = name;
  const W = w.width, R = w.R, Rr = w.rimR;
  // tire (lathe around Y, then rotate so axis -> X)
  const prof = [
    [Rr + 0.004, -W * 0.44], [Rr + 0.03, -W * 0.5], [R - 0.05, -W * 0.52], [R - 0.016, -W * 0.48], [R - 0.003, -W * 0.40],
    [R, -W * 0.30], [R, W * 0.30], [R - 0.003, W * 0.40], [R - 0.016, W * 0.48], [R - 0.05, W * 0.52], [Rr + 0.03, W * 0.5], [Rr + 0.004, W * 0.44],
  ].map(([r, y]) => new THREE.Vector2(r, y));
  const tireG = new THREE.LatheGeometry(prof, 72);
  tireG.rotateZ(Math.PI / 2);
  const tire = new THREE.Mesh(tireG, mats.tire); tire.name = 'Tire'; g.add(tire);
  // tread blocks
  if (w.tread) {
    const blocks = [];
    const nb = w.tread.count, rows = w.tread.rows;
    for (let i = 0; i < nb; i++) {
      for (let r = 0; r < rows; r++) {
        const bw = (W * 0.62) / rows - 0.008;
        const bx = new THREE.BoxGeometry(bw, w.tread.depth, (2 * Math.PI * R / nb) * 0.62);
        const off = ((r + 0.5) / rows - 0.5) * W * 0.62 + ((i % 2) ? 0.006 : -0.006);
        bx.translate(off, R + w.tread.depth / 2 - 0.002, 0);
        bx.rotateX((i + (r % 2) * 0.5) / nb * Math.PI * 2);
        blocks.push(bx);
      }
      // shoulder lugs
      for (const sgn of [-1, 1]) {
        const sb = new THREE.BoxGeometry(W * 0.12, w.tread.depth * 0.9, (2 * Math.PI * R / nb) * 0.5);
        sb.translate(sgn * W * 0.40, R - 0.004, 0);
        sb.rotateX((i + 0.25) / nb * Math.PI * 2);
        blocks.push(sb);
      }
    }
    const tb = new THREE.Mesh(mergeGeometries(blocks), mats.tire); tb.name = 'Tread'; g.add(tb);
  }
  // rim barrel
  const barrel = new THREE.CylinderGeometry(Rr, Rr, W * 0.85, 48, 1, true); barrel.rotateZ(Math.PI / 2);
  const bm = new THREE.Mesh(barrel, mats.rim); bm.name = 'Rim_Barrel'; g.add(bm);
  // inner dark disc so you can't see through the wheel
  const back = new THREE.CircleGeometry(Rr, 40); back.rotateY(Math.PI / 2); back.translate(-W * 0.25, 0, 0);
  const bk = new THREE.Mesh(back, mats.under); bk.name = 'Rim_Back'; g.add(bk);
  // brake rotor + caliper
  const rot = new THREE.CylinderGeometry(w.rotorR, w.rotorR, 0.028, 40); rot.rotateZ(Math.PI / 2); rot.translate(-0.02, 0, 0);
  g.add(Object.assign(new THREE.Mesh(rot, mats.brake), { name: 'Brake_Rotor' }));
  const cal = new THREE.BoxGeometry(0.06, 0.09, 0.16); cal.translate(-0.005, w.rotorR - 0.03, -0.04);
  g.add(Object.assign(new THREE.Mesh(cal, mats.caliper), { name: 'Brake_Caliper' }));
  // rim face
  const lipR = Rr + 0.012, faceR = Rr - 0.012, hubR = 0.075;
  const shape = new THREE.Shape(); shape.absarc(0, 0, lipR, 0, Math.PI * 2, false);
  let holes = [];
  if (w.style === 'bmw-double5') {
    const angs = []; for (let i = 0; i < 5; i++) { const c = i * 2 * Math.PI / 5 + Math.PI / 2; angs.push(c - 0.11, c + 0.11); }
    holes = holesBetweenSpokes(angs, r => 0.0085 + 0.003 * (r / faceR), hubR, faceR, 0.004);
  } else if (w.style === 'mesh-y10') {
    const a10 = [], a20 = [];
    for (let i = 0; i < 10; i++) a10.push(i * Math.PI / 5 + Math.PI / 2);
    for (let i = 0; i < 20; i++) a20.push(i * Math.PI / 10 + Math.PI / 2 + Math.PI / 20);
    const rm = faceR * 0.56;
    holes = [
      ...holesBetweenSpokes(a10, r => 0.010 + 0.002 * (r / faceR), hubR, rm - 0.006),
      ...holesBetweenSpokes(a20, r => 0.0065, rm + 0.006, faceR),
    ];
  }
  shape.holes.push(...holes);
  const face = new THREE.ExtrudeGeometry(shape, { depth: 0.022, bevelEnabled: true, bevelThickness: 0.004, bevelSize: 0.003, bevelSegments: 1, curveSegments: 40 });
  face.rotateY(Math.PI / 2); face.translate(W * 0.30, 0, 0);
  g.add(Object.assign(new THREE.Mesh(face, mats.rim), { name: 'Rim_Face' }));
  // hub, centre cap, lug nuts
  const hub = new THREE.CylinderGeometry(hubR, hubR * 1.05, 0.04, 40); hub.rotateZ(Math.PI / 2); hub.translate(W * 0.31, 0, 0);
  g.add(Object.assign(new THREE.Mesh(hub, mats.rim), { name: 'Hub' }));
  const capG = new THREE.CylinderGeometry(0.032, 0.034, 0.012, 32); capG.rotateZ(Math.PI / 2); capG.translate(W * 0.34, 0, 0);
  g.add(Object.assign(new THREE.Mesh(capG, w.capMat ? mats[w.capMat] : mats.chrome), { name: 'Center_Cap' }));
  const nuts = [];
  for (let i = 0; i < 5; i++) {
    const a = i * 2 * Math.PI / 5 + Math.PI / 2 + Math.PI / 5;
    const n = new THREE.CylinderGeometry(0.0095, 0.0095, 0.02, 6); n.rotateZ(Math.PI / 2);
    n.translate(W * 0.335, 0.052 * Math.sin(a), 0.052 * Math.cos(a)); nuts.push(n);
  }
  g.add(Object.assign(new THREE.Mesh(mergeGeometries(nuts), mats.chrome), { name: 'Lug_Nuts' }));
  return g;
}

// ---------- small parts ----------
export function ellipsoid(rx, ry, rz, mat, name) {
  const g = new THREE.SphereGeometry(1, 32, 20); g.scale(rx, ry, rz);
  return Object.assign(new THREE.Mesh(g, mat), { name });
}
export function box(sx, sy, sz, mat, name, round = 0) {
  const g = round ? roundedBox(sx, sy, sz, round) : new THREE.BoxGeometry(sx, sy, sz);
  return Object.assign(new THREE.Mesh(g, mat), { name });
}
function roundedBox(sx, sy, sz, r) {
  const s = new THREE.Shape(); const w = sx / 2 - r, h = sy / 2 - r;
  s.moveTo(-w, -sy / 2); s.lineTo(w, -sy / 2); s.quadraticCurveTo(sx / 2, -sy / 2, sx / 2, -h);
  s.lineTo(sx / 2, h); s.quadraticCurveTo(sx / 2, sy / 2, w, sy / 2); s.lineTo(-w, sy / 2);
  s.quadraticCurveTo(-sx / 2, sy / 2, -sx / 2, h); s.lineTo(-sx / 2, -h); s.quadraticCurveTo(-sx / 2, -sy / 2, -w, -sy / 2);
  const g = new THREE.ExtrudeGeometry(s, { depth: sz, bevelEnabled: false, curveSegments: 6 }); g.translate(0, 0, -sz / 2); return g;
}
// place an object using internal coords
export function place(obj, spec, x, y, z) { obj.position.copy(toV(x, y, z, spec.L)); return obj; }

// ---------- assemble ----------
export function buildCar(spec) {
  const mats = makeMaterials(spec.paintHex);
  const car = new THREE.Group(); car.name = spec.name;
  const { body, caps } = buildBody(spec, mats);
  car.add(body); car.add(caps);

  // underbody filler (blocks see-through under arches)
  const ub = box(spec.trackF - spec.tire.width - 0.10, 0.20, spec.axles[1] - spec.axles[0] + 0.5, mats.under, 'Underbody');
  place(ub, spec, (spec.axles[0] + spec.axles[1]) / 2, 0, spec.groundClear + 0.13); car.add(ub);
  for (const [i, ax] of spec.axles.entries()) {
    const track = i === 0 ? spec.trackF : spec.trackR;
    for (const side of [1, -1]) {
      const wh = buildWheel(spec.tire, mats, `Wheel_${i === 0 ? 'F' : 'R'}${side > 0 ? 'L' : 'R'}`);
      if (side < 0) wh.rotation.y = Math.PI;
      place(wh, spec, ax, side * track / 2, spec.tire.R); car.add(wh);
      // wheel-well liner
      const liner = new THREE.CylinderGeometry(spec.archR + 0.01, spec.archR + 0.01, spec.tire.width + 0.05, 32, 1, true, 0, Math.PI);
      liner.rotateZ(Math.PI / 2);
      const lm = new THREE.Mesh(liner, mats.under); lm.material = mats.under; lm.name = 'Wheelwell_Liner';
      lm.material.side = THREE.DoubleSide;
      place(lm, spec, ax, side * (track / 2 - 0.02), spec.tire.R); lm.rotation.x = -Math.PI / 2; car.add(lm);
    }
  }
  spec.details(car, mats, spec);
  car.updateMatrixWorld(true);
  return car;
}
export { THREE, toV, stationParams, SEG };
