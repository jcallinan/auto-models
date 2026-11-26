"""Embed the web LOD .glb files (gzip+base64) into viewer/index.html."""
import base64, gzip, os, sys
sys.path.insert(0, 'blender')
H = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(H, '..')
stats = {}
try:
    import bpy
    for k, n in (('rav4', 'RAV4_2023_LE'), ('e90', 'BMW_325xi_2006_E90')):
        bpy.ops.wm.open_mainfile(filepath=f'{R}/models/v1/{n}.blend')
        ms = [o for o in bpy.data.objects if o.type == 'MESH']
        stats[k] = (len(ms), sum(sum(len(p.vertices) - 2 for p in o.data.polygons) for o in ms))
except Exception as e:
    print('stats skipped', e)
blobs = ''
for k, n in (('rav4', 'RAV4_2023_LE'), ('e90', 'BMW_325xi_2006_E90')):
    b = base64.b64encode(gzip.compress(open(f'{R}/models/v1/web/{n}.glb', 'rb').read(), 9)).decode()
    m, t = stats.get(k, (0, 0))
    blobs += f'<script type="application/octet-stream" id="glb-{k}" data-meshes="{m}" data-tris="{t}">{b}</script>\n'
s = open(f'{H}/index.template.html').read().replace('<!--MODELS-->', blobs)
open(f'{H}/index.html', 'w').write(s)
print('viewer', round(os.path.getsize(f'{H}/index.html') / 2**20, 2), 'MiB')
