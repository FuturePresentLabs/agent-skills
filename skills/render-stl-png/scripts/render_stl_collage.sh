#!/usr/bin/env bash
set -euo pipefail

# render_stl_collage.sh
#
# Render an STL from 6 angles (top, bottom, front, back, left, right)
# and create a collage using Python/Pillow (no ffmpeg needed)

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <in.stl> <out.png> [options...]" >&2
  echo "Renders 6 views (top/bottom/front/back/left/right) and creates a collage" >&2
  echo "Options: --color #hex --bg #hex --size N" >&2
  exit 2
fi

IN_STL="$1"
OUT_PNG="$2"
shift 2

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_BASE="${XDG_CACHE_HOME:-$HOME/.cache}/agent-skills"
VENV="$VENV_BASE/render-stl-png-venv"

# Setup venv if needed
mkdir -p "$VENV_BASE"
if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --upgrade pip >/dev/null
  "$VENV/bin/pip" install pillow >/dev/null
fi

# Create temp directory for individual renders
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# Parse options
COLOR="#4cc9f0"
BG="#0b0f14"
SIZE=600

while [[ $# -gt 0 ]]; do
  case "$1" in
    --color) COLOR="$2"; shift 2;;
    --bg) BG="$2"; shift 2;;
    --size) SIZE="$2"; shift 2;;
    *) shift;;
  esac
done

echo "Rendering 6 views..."

# Render 6 views
"$VENV/bin/python" "$SCRIPT_DIR/render_stl_png.py" --stl "$IN_STL" --out "$TMPDIR/front.png" --size $SIZE --color "$COLOR" --bg "$BG" --azim-deg 0 --elev-deg 25
"$VENV/bin/python" "$SCRIPT_DIR/render_stl_png.py" --stl "$IN_STL" --out "$TMPDIR/top.png" --size $SIZE --color "$COLOR" --bg "$BG" --azim-deg 0 --elev-deg 90
"$VENV/bin/python" "$SCRIPT_DIR/render_stl_png.py" --stl "$IN_STL" --out "$TMPDIR/back.png" --size $SIZE --color "$COLOR" --bg "$BG" --azim-deg 180 --elev-deg 25
"$VENV/bin/python" "$SCRIPT_DIR/render_stl_png.py" --stl "$IN_STL" --out "$TMPDIR/left.png" --size $SIZE --color "$COLOR" --bg "$BG" --azim-deg -90 --elev-deg 25
"$VENV/bin/python" "$SCRIPT_DIR/render_stl_png.py" --stl "$IN_STL" --out "$TMPDIR/bottom.png" --size $SIZE --color "$COLOR" --bg "$BG" --azim-deg 0 --elev-deg -90
"$VENV/bin/python" "$SCRIPT_DIR/render_stl_png.py" --stl "$IN_STL" --out "$TMPDIR/right.png" --size $SIZE --color "$COLOR" --bg "$BG" --azim-deg 90 --elev-deg 25

echo "Creating collage..."

# Use Python/Pillow to create collage
"$VENV/bin/python" - << PY
from PIL import Image, ImageDraw, ImageFont
import sys

size = $SIZE
bg_color = "$BG"

# Load all 6 images
views = {
    'front': Image.open("$TMPDIR/front.png"),
    'top': Image.open("$TMPDIR/top.png"),
    'back': Image.open("$TMPDIR/back.png"),
    'left': Image.open("$TMPDIR/left.png"),
    'bottom': Image.open("$TMPDIR/bottom.png"),
    'right': Image.open("$TMPDIR/right.png"),
}

# Create collage: 2 rows x 3 cols
# Row 1: Front | Top | Back
# Row 2: Left | Bottom | Right
collage_width = size * 3
collage_height = size * 2
collage = Image.new('RGB', (collage_width, collage_height), bg_color)

# Paste images
collage.paste(views['front'], (0, 0))
collage.paste(views['top'], (size, 0))
collage.paste(views['back'], (size * 2, 0))
collage.paste(views['left'], (0, size))
collage.paste(views['bottom'], (size, size))
collage.paste(views['right'], (size * 2, size))

# Add labels
draw = ImageDraw.Draw(collage)
try:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
except:
    font = ImageFont.load_default()

labels = [
    (size//2, 10, "FRONT"),
    (size + size//2, 10, "TOP"),
    (size*2 + size//2, 10, "BACK"),
    (size//2, size + 10, "LEFT"),
    (size + size//2, size + 10, "BOTTOM"),
    (size*2 + size//2, size + 10, "RIGHT"),
]

for x, y, label in labels:
    # Draw text with outline for visibility
    draw.text((x-1, y), label, font=font, fill="black", anchor="mt")
    draw.text((x+1, y), label, font=font, fill="black", anchor="mt")
    draw.text((x, y-1), label, font=font, fill="black", anchor="mt")
    draw.text((x, y+1), label, font=font, fill="black", anchor="mt")
    draw.text((x, y), label, font=font, fill="white", anchor="mt")

# Add border lines
line_color = "#333333"
for i in range(1, 3):
    draw.line([(i * size, 0), (i * size, collage_height)], fill=line_color, width=2)
draw.line([(0, size), (collage_width, size)], fill=line_color, width=2)

collage.save("$OUT_PNG")
print(f"Collage saved to: $OUT_PNG")
PY

echo "Done!"
