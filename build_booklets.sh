#!/usr/bin/env bash
# Convert road-trip booklet Markdown files into PDFs with embedded images
# and clickable links. Pipeline: pandoc (md -> standalone HTML) + headless
# Chrome (HTML -> PDF). Emoji render in full colour via Chrome.
set -euo pipefail

ROOT="/Users/jan/Projects/RoadtripPlanning"
CSS="$ROOT/booklet_style.css"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# All booklet markdown files (both folders).
FILES=(
  "$ROOT/Belchite to Valladolid/Belchite_to_Valladolid_Route.md"
  "$ROOT/Belchite to Valladolid/Belchite_to_Valladolid_Backroads.md"
  "$ROOT/Belchite_Roadtrip/Route_Booklet_NEW_Uitgeest_to_Belchite.md"
  "$ROOT/Belchite_Roadtrip/Route_Booklet_Uitgeest_to_Belchite.md"
)

# Allow building a single file: ./build_booklets.sh "<path.md>"
if [[ $# -ge 1 ]]; then
  FILES=("$@")
fi

# Max width (px) for embedded map images. The source PNGs are ~7200px /
# 25-50 MB each (intentional high-res masters); at this width they print
# crisply on A4 while keeping the PDF small. Originals are never modified.
MAXW=2000

for md in "${FILES[@]}"; do
  dir="$(dirname "$md")"
  base="$(basename "$md" .md)"
  html="$dir/$base.html"
  pdf="$dir/$base.pdf"

  echo "==> $base"

  # Stage downscaled copies of any referenced images into a temp resource dir
  # mirroring images/, so pandoc resolves images/foo.png to the smaller copy.
  tmp="$(mktemp -d)"
  if [[ -d "$dir/images" ]]; then
    mkdir -p "$tmp/images"
    for img in "$dir"/images/*.png; do
      [[ -e "$img" ]] || continue
      cp "$img" "$tmp/images/"
      sips --resampleWidth "$MAXW" "$tmp/images/$(basename "$img")" >/dev/null 2>&1 || true
    done
  fi

  # 1) Markdown -> self-contained HTML, resolving images from the temp dir;
  #    --embed-resources inlines the (downscaled) PNGs into the HTML.
  pandoc "$md" \
    --from gfm \
    --standalone \
    --embed-resources \
    --metadata pagetitle="$base" \
    --css "$CSS" \
    --resource-path "$tmp" \
    --output "$html"

  # 2) HTML -> PDF via headless Chrome (preserves clickable links + emoji).
  "$CHROME" \
    --headless \
    --disable-gpu \
    --no-pdf-header-footer \
    --print-to-pdf="$pdf" \
    "file://$html" 2>/dev/null

  rm -f "$html"
  rm -rf "$tmp"
  echo "    wrote $pdf"
done

echo "Done."