import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from carlib import *
import importlib
car = importlib.import_module(sys.argv[1] if len(sys.argv) > 1 else 'rav4')
clean_scene()
M = make_materials(car.SPEC['key'], car.SPEC['paint'])
t = time.time()
parts, prof, bvh = panelise(car.SPEC, M, car.classify, stations=int(os.environ.get('ST', 380)))
print('panelise', round(time.time() - t, 1), 's', len(parts), 'panels')
for k, o in sorted(parts.items()): print(f'  {k:28s} {len(o.data.polygons):6d}')
t = time.time()
for k, o in parts.items():
    if 'Glass' in k: thicken(o, 0.004, 0, push=-0.006)
    elif k.startswith(('Headlight', 'Taillight', 'Liftgate_Tail')): thicken(o, 0.003, 0.0006, push=-0.002)
    else: thicken(o, 0.0025, 0.0011)
print('thicken', round(time.time() - t, 1))
bpy.ops.export_scene.gltf(filepath=f'/tmp/{car.SPEC["key"]}_test.glb', export_format='GLB', export_apply=True)
print('ok')
