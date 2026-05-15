# Indian Bedroom Prompt Guide

Use this guide to judge whether the generated result looks like a realistic Indian bedroom and not a generic or animated render.

## Target Look

- Real Indian bedroom, not a UK or Western catalog room
- Bed is the hero object, clearly visible and correctly placed
- Only one main wardrobe wall unless the room is very large
- Realistic Indian finishes: laminate, acrylic, PU, vitrified tile, marble-look tile, warm wood
- POP false ceiling, warm cove light, ceiling fan, practical TV unit or dresser
- Real-camera lighting, believable shadows, no fake CGI glow

## Output Scoring Out Of 100

- `25` points: Bedroom identity
  - Full bed with mattress, pillows, bedding visible
  - Room reads immediately as a bedroom
- `20` points: Indian style match
  - Looks like a modern Indian apartment or house bedroom
  - Uses Indian-friendly colors, furniture, ceiling, lighting, and storage style
- `20` points: Realism
  - Photoreal lighting, believable textures, proper furniture scale
  - No animated, plastic, or game-like render feel
- `15` points: Layout quality
  - Functional placement of bed, wardrobe, TV unit, mirror, side tables
  - No overstuffing and no empty showroom feeling
- `10` points: Geometry preservation
  - Windows, walls, camera view, ceiling lines, and proportions stay consistent
- `10` points: Finish quality
  - Clean detailing, balanced colors, no visible model artifacts

## Score For Current Result

Based on the screenshot you shared, the current generated result scores about `38/100`.

- `10/25` Bedroom identity: it reads more like a wardrobe wall than a complete bedroom
- `7/20` Indian style match: some wardrobe cues fit, but overall it does not feel like a strong Indian bedroom
- `6/20` Realism: lighting and materials look too smooth and CG-like
- `6/15` Layout quality: missing strong bed-first composition
- `5/10` Geometry preservation: shell is mostly preserved
- `4/10` Finish quality: acceptable, but still synthetic and incomplete

## Main Problems In Current Output

- Bed is missing, too small, or not treated as the main subject
- Wardrobe dominates the whole wall and makes the room feel like a closet display
- Lighting feels flat and staged instead of camera-real
- Room styling is too generic and not specifically Indian enough
- Materials look too perfect and smooth, which creates the animated look

## Best Improvement Strategy

- Make the prompt bed-first, not wardrobe-first
- Explicitly ask for a photoreal Indian apartment bedroom
- Ask for only one wardrobe wall
- Force practical Indian elements: POP ceiling, warm cove lights, fan, curtains, TV unit or dresser
- Add negative terms against cartoon, CGI, plastic render, floating furniture, and storage-only layout
- Keep output consistent by using one strong default prompt instead of random bedroom prompt selection

## Strong Prompt To Test

```text
Transform this EXACT room into: REALISTIC INDIAN BEDROOM, bed-first layout, not wardrobe-first. Place one complete king or queen bed with mattress, padded headboard, pillows and bedsheet as the main subject, grounded naturally on the floor and sized correctly for the room. Use one wardrobe wall only, not wardrobes on every wall. Add a compact TV unit or dresser only if space allows. Indian apartment details: POP false ceiling, warm cove lighting, ceiling fan, practical side tables, soft curtains, believable joinery, cream or pastel walls, matte laminate or acrylic wardrobe shutters, realistic Indian flooring such as vitrified tile, marble-look tile, or warm wood. Keep the room functional, middle-class to premium Indian home style, lived-in but neat, photoreal DSLR interior photo, natural daylight from existing windows mixed with warm 3000K ceiling lights, tactile materials, true scale, realistic shadows. Preserve exact wall, window, door, and ceiling geometry.
```

## Good Extra User Requirements

You can paste one of these into the app's additional requirements box:

```text
Indian master bedroom, walnut and beige palette, upholstered bed, soft curtains, warm cove lighting, fan, single wardrobe wall, realistic camera look
```

```text
Modern Indian bedroom, sage green and ivory wardrobe, queen bed, side tables, dresser mirror, TV panel, POP ceiling, marble-look tile floor, photoreal
```

```text
Premium Indian bedroom like a Bangalore or Hyderabad apartment interior, realistic daylight, warm LEDs, functional layout, not animated, not wardrobe-only
```
