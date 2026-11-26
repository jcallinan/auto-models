import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
import { writeFileSync, mkdirSync } from 'node:fs';
import { build, SPECS } from './cars.mjs';

globalThis.FileReader = class {
  readAsArrayBuffer(b) { b.arrayBuffer().then(r => { this.result = r; this.onloadend?.(); this.onload?.(); }); }
  readAsDataURL(b) { b.arrayBuffer().then(r => { this.result = 'data:application/octet-stream;base64,' + Buffer.from(r).toString('base64'); this.onloadend?.(); this.onload?.(); }); }
};

mkdirSync('../models/v0', { recursive: true });
const files = { rav4: 'Toyota_RAV4_2023_LE.glb', e90: 'BMW_325xi_2006_E90.glb' };
for (const key of Object.keys(SPECS)) {
  const car = build(key);
  let tris = 0; car.traverse(o => { if (o.isMesh) tris += (o.geometry.index ? o.geometry.index.count : o.geometry.attributes.position.count) / 3; });
  const buf = await new GLTFExporter().parseAsync(car, { binary: true });
  writeFileSync('../models/v0/' + files[key], Buffer.from(buf));
  console.log(key, files[key], (buf.byteLength / 1e6).toFixed(2) + ' MB', Math.round(tris) + ' tris');
}
