"""Make a lighter web-viewer copy of a built .blend (decimated, glb)."""
import sys, bpy
src, dst, ratio = sys.argv[1], sys.argv[2], float(sys.argv[3])
bpy.ops.wm.open_mainfile(filepath=src)
for o in bpy.data.objects:
    if o.type != 'MESH': continue
    n = len(o.data.polygons)
    if n < 3000: continue
    m = o.modifiers.new('Dec', 'DECIMATE'); m.ratio = max(ratio, 3000 / n) if n > 6000 else 0.6
bpy.ops.export_scene.gltf(filepath=dst, export_format='GLB', export_apply=True)
