# auto-models

3D models of two real cars, built as the starting point for a game in which the cars transform:

| Key | Vehicle | Reference photos |
|---|---|---|
| `rav4` | 2023 Toyota RAV4 LE AWD, Magnetic Gray Metallic | `reference/rav4/` |
| `e90` | 2006 BMW 325xi (E90) sedan, Sparkling Graphite Metallic | `reference/e90/` |

Factory dimensions and the details taken from the photos are in [`reference/specs.md`](reference/specs.md).

## Layout

```
reference/     photos of both cars + spec sheet
blender/       v1 builder (Blender Python, bpy): panelised, rigged, Unity-ready
  carlib.py    loft -> classify -> seam smoothing -> panel split with gaps -> thickness/bevel -> pivots
  rav4.py      RAV4 profile tables, panel map, detail parts
  e90.py       325xi profile tables, panel map, detail parts
  build.py     python3 build.py rav4|e90  ->  models/v1/<Name>.{blend,fbx,glb}
  weblod.py    decimated copy for the web viewer
models/v1/     current models (.fbx for Unity, .blend source, .glb)
models/v0/     first single-shell prototype (superseded)
viewer/        three.js rig viewer (pack.py embeds models/v1/web/*.glb)
tools/         headless render check (shoot.py)
generator/     v0 Node builder (superseded)
```

## v1 (current)

Each car is a hierarchy of separate panels with real panel gaps, ~2.8 mm thickness and rolled edges:

```
<Car>
  Body/            fixed panels: roof, fenders, quarters, A-pillars, bumpers, rockers, flares, underbody, lamps, glass, grille, Chassis_Tub
  Door_FL_Pivot/   pivot on the front hinge line; door skin, glass, handle, mirror
  Door_FR_Pivot/ Door_RL_Pivot/ Door_RR_Pivot/
  Hood_Pivot/      pivot at the cowl hinge
  Liftgate_Pivot/ (RAV4)  Trunk_Pivot/ (325xi)   pivot at the top hinge
  Suspension_FL/   steer pivot at the hub centre; brake caliper
    Wheel_FL/      spin pivot (local X); tyre, tread, rim, rotor, lug nuts
  Suspension_FR/ Suspension_RL/ Suspension_RR/
```

`Chassis_Tub` is a dark inner shell: when panels move during a transform, you see machinery-coloured structure instead of empty space.

Budget: RAV4 ~900k triangles / 119 meshes, 325xi ~840k / 111 meshes. This is a hero LOD0 meant for close-ups. Make in-game LODs with Unity's LOD Group or `weblod.py`.

### Unity import
Drop `models/v1/*.fbx` into `Assets/`. The FBX is exported with -Z forward and Y up, with transforms baked, so the car faces +Z at 1 unit = 1 m with no rotation fix. Rotate the `*_Pivot` objects' local axes to animate the doors, hood and trunk; spin `Wheel_*` around local X; steer `Suspension_F*` around local Y.

### Rebuild
```
pip install bpy          # Blender as a Python module (5.x)
cd blender
python3 build.py rav4
python3 build.py e90
```

## Conventions (apply to every model version)

- Units: metres. Ground at Y = 0.
- Axes (glTF): +Y up, the front of the car faces +Z, and the car's left side is +X.
- Pivots: each wheel's pivot sits at its hub centre, so a wheel can spin and steer around its own origin.

## v0 status

v0 has accurate overall dimensions, but it is a single lofted body with painted-on regions. It is a proportion and layout reference, **not** the game asset. A model that can transform needs every panel as its own mesh with its own pivot (see the roadmap in `reference/specs.md`).

### Regenerate v0

```
cd generator
npm install
node export.mjs        # writes ../models/v0/*.glb
```
