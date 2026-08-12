#!/usr/bin/env python3
"""build_font_subset.py — the self-hosted Source Serif 4 faces, reproducibly.

Rule 2.3's type pairing makes Source Serif 4 the voice face, and CLAUDE.md
makes "the site works offline and forever" a claim the module is partly for.
A Google-hosted webfont link would satisfy the first and break the second, so
the faces are self-hosted — and this script is how they were made, so nobody
has to guess at a binary in docs/assets/ later.

Source: the OFL distribution of Source Serif 4 in google/fonts, which ships a
VARIABLE font (wght 200-900, opsz 8-60). Both weights are instanced from that
one file rather than mixing a local static Regular with a downloaded Semibold:
two faces cut from different releases can disagree on metrics, and the
disagreement shows up as headings that sit a hair off the body text.

    https://github.com/google/fonts/raw/main/ofl/sourceserif4/SourceSerif4%5Bopsz%2Cwght%5D.ttf

Version 4.004. Licence SIL OFL 1.1, shipped alongside as SourceSerif4-OFL.txt
— the OFL requires the licence to travel with the font.

Requires fonttools with brotli installed — woff2 compression is brotli, and
without it fontTools fails on the flavor rather than falling back.

Usage:
    python src/build_font_subset.py <path-to-SourceSerif4-VF.ttf>
"""

from __future__ import annotations

import sys
from pathlib import Path

from fontTools import subset
from fontTools.varLib import instancer
from fontTools.ttLib import TTFont

# opsz is pinned rather than kept live. Optical sizing is a real refinement,
# but a wrong pin is worse than a neutral one and the axis default is the
# designer's neutral. The serif runs 13px (annotations) to 30px (h1), which
# sits comfortably either side of 20.
OPSZ = 20

# The weights the stylesheet actually declares. Nothing else is shipped, so
# there is no face here that no rule asks for.
WEIGHTS = {400: "Regular", 600: "Semibold"}

# Latin-1 plus the specific punctuation these pages genuinely use: en and em
# dash, curly quotes, the right arrow in the cross-links, the double dagger
# flagging derived Q4 values, the middle dot in the provenance strip, and the
# true minus. Subsetting to bare ASCII would drop glyphs already sitting on
# the frozen pages; taking whole blocks on spec costs kilobytes per unused
# glyph, and 575 glyphs is what the generous version cost.
UNICODES = (
    "U+0000-00FF,U+0131,U+0152-0153,U+2010-2015,U+2018-201A,U+201C-201E,"
    "U+2020-2022,U+2026,U+2030,U+2039-203A,U+2044,U+20AC,U+2122,U+2192,"
    "U+2212,U+FEFF,U+FFFD"
)

# Only the features the text actually renders through. "*" keeps every feature
# in the font, which retained a 51 KB GPOS of kerning for scripts these pages
# will never set and pushed each face to 107 KB. Kerning and the standard
# ligature/contextual set are the ones a reader would notice missing.
LAYOUT_FEATURES = ["kern", "liga", "clig", "calt", "ccmp", "locl", "mark", "mkmk"]


def build(src: Path, out_dir: Path) -> None:
    for weight, name in WEIGHTS.items():
        font = TTFont(src)
        # Pin both axes -> a static instance. Partial instancing would leave a
        # variable face, which is fine but larger and needs
        # font-variation-settings in the CSS for no benefit at two weights.
        instancer.instantiateVariableFont(
            font, {"wght": weight, "opsz": OPSZ}, inplace=True, updateFontNames=True
        )

        options = subset.Options()
        options.flavor = "woff2"
        options.layout_features = LAYOUT_FEATURES
        # Family, subfamily, unique id, full name, version, PostScript name and
        # the licence strings. Enough for a font manager and for anyone who
        # opens the binary wondering where it came from.
        options.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14]
        options.notdef_outline = True

        subsetter = subset.Subsetter(options=options)
        subsetter.populate(unicodes=subset.parse_unicodes(UNICODES))
        subsetter.subset(font)

        dest = out_dir / f"SourceSerif4-{name}-subset.woff2"
        font.flavorData = None
        font.save(dest)
        kb = dest.stat().st_size / 1024
        print(f"  {dest.name:<38} wght {weight}  opsz {OPSZ}  {kb:6.1f} KB")


def main() -> int:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1])
    if not src.exists():
        sys.exit(f"no variable font at {src}")
    out_dir = Path(__file__).resolve().parent.parent / "docs" / "assets"
    print(f"Instancing {src.name} -> {out_dir}")
    build(src, out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
