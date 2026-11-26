# auto-models

3D models of two real cars, built as the starting point for a game in which the cars transform:

| Key | Vehicle | Reference photos |
|---|---|---|
| `rav4` | 2023 Toyota RAV4 LE AWD, Magnetic Gray Metallic | `reference/rav4/` |
| `e90` | 2006 BMW 325xi (E90) sedan, Sparkling Graphite Metallic | `reference/e90/` |

Factory dimensions and the details taken from the photos are in [`reference/specs.md`](reference/specs.md).

## Layout

```
reference/   photos of both cars + spec sheet
generator/   v0 procedural builder (Node + three.js) that lofts each body from spec tables
  viewer/    three.js viewer page (loads the .glb files)
models/v0/   exported .glb from the v0 builder
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
