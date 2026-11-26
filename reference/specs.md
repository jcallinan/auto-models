# Vehicle specs

## 2023 Toyota RAV4 LE AWD

| Item | Value | Source |
|---|---|---|
| Length | 180.9 in / 4595 mm | KBB, auto123 |
| Width (w/o mirrors) | 73.0 in / 1855 mm | KBB, cars.com |
| Height | 67.0 in / 1702 mm | cars.com |
| Wheelbase | 105.9 in / 2690 mm | KBB |
| Track F / R | 63.4 / 64.6 in | auto123 |
| Ground clearance | 8.4 in | KBB |
| Engine | 2.5 L I4, 203 hp | KBB |

**From the photos (`reference/rav4/`):**
- Magnetic Gray Metallic paint, with body-colour mirror caps and door handles.
- Aftermarket gloss-black mesh / split multi-spoke wheels on all-terrain tyres. The size is not confirmed; it is modelled as 225/65R17, which is about 28.5 in in diameter.
- Black wheel-arch flares and black rocker cladding. The lower front fascia and rear bumper are textured black.
- Dual exhaust tips, one on each side, plus a roof spoiler, a shark-fin antenna and the "LE AWD" badging.
- Front plate: none. The rear plate sits on the liftgate.

## 2006 BMW 325xi (E90)

| Item | Value | Source |
|---|---|---|
| Length | 4520 mm / 178.0 in | BMW workshop data, auto-data.net |
| Width | 1817 mm / 71.5 in | same |
| Height | 1421 mm / 55.9 in | same |
| Wheelbase | 2760 mm / 108.7 in | same |
| Track F / R | 1500 / 1513 mm | same |
| Engine | N52B25, 2.5 L I6, 215 hp, xDrive AWD | ultimatespecs |

**From the photos (`reference/e90/`):**
- Sparkling Graphite Metallic paint.
- Aftermarket gloss-black double-slat kidney grilles and black mirror caps.
- Matte-black 5-double-spoke 17 in wheels with roundel centre caps, on winter tyres (Ice Edge). The tyres are modelled as 225/45R17.
- Sunroof. Halogen headlights with amber corners. Clear side repeaters on the front fenders.
- Twin exhaust tips on the left side only. The rear plate sits on the trunk lid between the L-shaped tail lamps.
- Visible wear: hazed headlights and scuffs on the front and rear bumpers. This is optional "as-is" detail.

## Roadmap: transforming game asset

A car that transforms needs the following:

1. **Panelised geometry.** Each panel is a separate, closed mesh with real thickness: hood, trunk or liftgate, 4 doors with their glass, 4 fenders or quarters, roof, front and rear bumpers, grille, lights, mirrors, 4 wheels.
2. **Pivots at real hinge lines.** Doors pivot on the A/B-pillar hinges, the hood on the cowl, the trunk on the deck, and the wheels on their hubs.
3. **An internal robot skeleton** whose segments each panel attaches to, so the car shape and the robot shape are two poses of the same rig.
4. **LODs**, plus a PBR material set (paint, glass, rubber, chrome, plastic, lens).
