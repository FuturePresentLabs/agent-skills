# FPL Agent Skills

A monorepo of small, chainable “Unix philosophy” skills for AI agents.

Focus:
- Deterministic, scriptable pipelines
- Quote/manufacturing-friendly defaults
- Minimal dependencies (prefer pure Python / shell; avoid heavyweight CAD stacks)

## Skills

### `create-dxf`
Create RFQ-ready **2D DXF** (and optional SVG preview) from a strict JSON spec.

- Best for: plates, brackets, gussets, hole patterns, slots
- Defaults: manufacturing-oriented layers (outer profile vs inner cuts)

**Path:** `skills/create-dxf`

### `find-stl`
Search + fetch ready-to-print models (Printables-first) and write a local `manifest.json`
with license/attribution + file checksums.

**Path:** `skills/find-stl`

### `trace-to-svg`
Deterministic raster → vector tracing using `mkbitmap` + `potrace`.

- Best for: turning simple silhouettes / masks into clean SVG paths

**Path:** `skills/trace-to-svg`

### `image-to-relief-stl`
Convert an input image into a watertight, 3D-printable **bas-relief STL** via a raster heightfield pipeline.

- Modes:
  - **palette**: map specific colors (e.g. `#rrggbb`) to heights
  - **grayscale**: map luminance to a height range
- Optional: generate a potrace SVG preview (best-effort)

**Path:** `skills/image-to-relief-stl`

### `package-tracking`
Look up package tracking information for FedEx, UPS, USPS, and Ward trucking/logistics.

- Extract tracking numbers from emails/text
- Identify carrier from tracking number format
- Generate direct tracking URLs
- Delivery time estimates

**Path:** `skills/package-tracking`

---

## Install / Use

Skills are designed to be used directly (local scripts) or installed via **ClawHub**.

### Local
Each skill is a self-contained folder with:
- `SKILL.md` (interface + usage)
- `scripts/` (executables)
- `references/` (schemas, prompts, examples)

### ClawHub
If you have `clawhub` installed:

```bash
# Example: publish a skill folder (maintainers)
clawhub publish ./skills/<skill-name> --version 0.1.0
```

(Registry tip: ClawHub currently expects the `www` host: `https://www.clawhub.ai/api`.)

---

## Quick Examples

### `find-stl`
```bash
python3 skills/find-stl/scripts/find_stl.py search --query "phone stand" --limit 5
python3 skills/find-stl/scripts/find_stl.py fetch --print-id 123456 --out-dir /tmp/printables_model
```

### `create-dxf`
```bash
python3 skills/create-dxf/scripts/create_dxf.py \
  --spec skills/create-dxf/references/example_plate.json \
  --out-dir /tmp/dxf_out
```

### `trace-to-svg`
```bash
bash skills/trace-to-svg/scripts/trace_to_svg.sh input.png /tmp/out.svg
```

### `image-to-relief-stl`
```bash
bash skills/image-to-relief-stl/scripts/image_to_relief.sh input.png --out /tmp/relief.stl \
  --mode grayscale --min-height 0.0 --max-height 3.0 --base 1.2 --pixel 0.5
```

### `package-tracking`
```bash
# Look up a tracking number (auto-detects carrier)
python3 skills/package-tracking/scripts/track_package.py --number 9434650206217168190787

# Extract tracking numbers from email text
python3 skills/package-tracking/scripts/track_package.py --extract --number "<email text>"
```

---

## Contributing

- Keep skills small and composable.
- Prefer strict, validated inputs and predictable outputs.
- Avoid adding heavy dependencies unless absolutely necessary.

## License

See individual skills / repository license (if present).
