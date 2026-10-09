#!/usr/bin/env python3
"""Generate the social share cards and the Open Graph / Twitter meta (TODO Y-7).

Run from anywhere:  python3 scripts/generate-share-cards.py   (add --check to verify, writes nothing)

What it writes (all committed; re-run when a game is added, renamed or re-themed):
  share/hub.png            1200x630 card for the hub and its public pages
  share/<slug>.png         1200x630 card per hub-linked game
  share/meta/hub.html      the head snippet used by the hub (also injected into index.html)
  share/meta/<slug>.html   a ready-to-paste head snippet per game (title, description, canonical,
                           Open Graph, Twitter). Game pages are NOT edited here: the main session wires
                           these in later.
  <public page>.html       an idempotent block between
                           `<!-- share-meta:start -->` and `<!-- share-meta:end -->` is added to (or
                           refreshed in) the hub and the public hub pages listed in sitedata.PUBLIC_PAGES.

Every picture is drawn in code from the hub's own title-card thumbnail colours (style.css
`.title-card-thumb--*`) and the per-game favicon glyphs (icons/favicon-*.svg, redrawn here because there
is no SVG renderer on the box). No AI imagery, no photographs. Needs Pillow (`python3 -c 'import PIL'`);
without it the script stops with a clear message instead of writing broken files. Fonts: the first
system bold font found (Helvetica/Arial/DejaVu), else Pillow's built-in font; so card text can differ
slightly between machines. Dimensions never do.
"""

import math
import random
import re
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sitedata  # noqa: E402

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:  # pragma: no cover - environment dependent
    sys.exit("Pillow is required: pip install pillow (needed to draw the 1200x630 PNG cards).")

W, H = 1200, 630
SS = 2  # supersample factor for smooth shapes
SHARE = sitedata.ROOT / "share"

# slug -> (background stops top-left to bottom-right, motif, accent, tile fill, glyph kind)
# Colours are copied from style.css `.title-card-thumb--*` and icons/favicon-*.svg.
THEMES = {
    "sol": (["#3a5a9c", "#101830"], "stars", "#dfe8ff", "#2c4a7c", ("letter", "S", "#ffffff")),
    "canopy": (["#123a22", "#1f5c33"], "forest", "#c8ffb4", "#1f5c33", ("leaf",)),
    "grid": (["#0d3a4a", "#072430"], "gridlines", "#9fe8ff", "#0d5866", ("bolt",)),
    "tide": (["#0a3a49", "#12586b"], "waves", "#bee6f0", "#12586b", ("waves",)),
    "aftermath": (["#3a1f18", "#24120e"], "embers", "#ffb366", "#b8632e", ("letter", "A", "#ffffff")),
    "herd": (["#6b5a2a", "#a67d3a", "#c99a4a"], "hills:#4a6b2a", "#ffdc96", "#8f6a2a", ("letter", "H", "#ffffff")),
    "thaw": (["#04141c", "#0a2430"], "aurora", "#cfeeff", "#2d7d76", ("snow",)),
    "loop": (["#0c2e22", "#071d16"], "ring", "#bfffe0", "#1f7a52", ("infinity",)),
    "drift": (["#2a1c3a", "#6e3a4a", "#b5623a"], "hills:#241a2c", "#f3c9a0", "#7a3a3a", ("letter", "D", "#ffffff")),
    "champ-de-mots": (["#a9c9e0", "#e8c896", "#edb98a"], "hills:#4d7a2e", "#fff3c4", "#4a6b2a", ("letter", "F", "#ffffff")),
    "continuum": (["#241a3a", "#4a3a5c", "#7a5230", "#c9922f"], "skyline", "#8cdcdc", "#4a3a5c|#c9922f", ("letter", "C", "#ffffff")),
    "signal": (["#14211c", "#0d1512"], "pulse", "#ffb347", "#14211c", ("signal",)),
    "lexis": (["#1b2747", "#0e1426"], "marks", "#9ad0ff", "#16203a", ("lexis",)),
    "heist-committee": (["#3a2a52", "#1d1530"], "skyline", "#ffc15e", "#2a1f3d", ("hat",)),
    "lighthouse": (["#143a52", "#0a1f30"], "waves", "#ffcf6b", "#143a52", ("lighthouse",)),
    "pocket-bazaar": (["#3a2f4a", "#2a2233"], "hills:#1a1420", "#e8a33d", "#2a2233", ("stall",)),
    "dead-reckoning": (["#17405e", "#07131f"], "gridlines", "#7fd1ff", "#10283d", ("compass",)),
    "logic-gates": (["#14233a", "#0a1220"], "gridlines", "#5fd4e6", "#0a1220", ("gate",)),
    "trade-empire": (["#1a1f3a", "#0d0f1e"], "network", "#e0c34c", "#171b30", ("letter", "$", "#e0c34c")),
}
FALLBACK_THEME = (["#1a1f3a", "#0d0f1e"], "stars", "#8fb0e8", "#2c4a7c", ("letter", "?", "#ffffff"))

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]
REGULAR_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def font(size, bold=True):
    for path in FONT_CANDIDATES if bold else REGULAR_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


def rgb(color, alpha=255):
    color = color.lstrip("#")
    return (int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16), alpha)


def lerp_color(stops, t):
    """Piecewise-linear colour along evenly spaced stops, t in [0, 1]."""
    if len(stops) == 1:
        return rgb(stops[0])
    t = min(max(t, 0.0), 1.0) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    a, b, f = rgb(stops[i]), rgb(stops[i + 1]), t - i
    return tuple(int(a[k] + (b[k] - a[k]) * f) for k in range(4))


def diagonal_gradient(width, height, stops):
    """A top-left to bottom-right linear gradient. Built from a thin strip, so it is cheap."""
    length = width + height
    strip = Image.new("RGBA", (length, 1))
    strip.putdata([lerp_color(stops, i / (length - 1)) for i in range(length)])
    image = Image.new("RGBA", (width, height))
    # Each row is the strip shifted by y: pasting row by row is far faster than per pixel.
    for y in range(height):
        image.paste(strip.crop((y, 0, y + width, 1)), (0, y))
    return image


# ---------------------------------------------------------------- motifs

def motif(layer, name, accent, rng, size):
    """Draw decoration on an RGBA layer of `size` (already supersampled)."""
    w, h = size
    draw = ImageDraw.Draw(layer)
    s = w / W
    kind, _, arg = name.partition(":")
    if kind == "stars":
        for _ in range(70):
            x, y, r = rng.random() * w, rng.random() * h, (0.8 + rng.random() * 1.8) * s
            draw.ellipse((x - r, y - r, x + r, y + r), fill=rgb("#ffffff", int(120 + rng.random() * 120)))
        r = 44 * s
        draw.ellipse((w * 0.62 - r, h * 0.2 - r, w * 0.62 + r, h * 0.2 + r), fill=rgb(accent, 70))
    elif kind == "forest":
        for k in range(3):
            pts = [(0, h)]
            x, y = 0, h * (0.74 - 0.07 * k)
            while x < w:
                pts.append((x, y - rng.random() * 90 * s))
                x += 38 * s
            pts += [(w, h)]
            draw.polygon(pts, fill=rgb("#0d2416", 150 + 35 * k))
        for _ in range(5):
            x, y, r = rng.random() * w, rng.random() * h * 0.5, 50 * s
            draw.ellipse((x - r, y - r, x + r, y + r), fill=rgb(accent, 30))
    elif kind == "gridlines":
        step = 48 * s
        k = 0
        while k * step < w:
            draw.line((k * step, 0, k * step, h), fill=rgb("#78dcff", 38), width=max(1, int(s)))
            k += 1
        k = 0
        while k * step < h:
            draw.line((0, k * step, w, k * step), fill=rgb("#78dcff", 38), width=max(1, int(s)))
            k += 1
        for _ in range(14):
            x, y, r = round(rng.random() * w / step) * step, round(rng.random() * h / step) * step, 4 * s
            draw.ellipse((x - r, y - r, x + r, y + r), fill=rgb(accent, 220))
    elif kind == "waves":
        for k in range(5):
            base = h * (0.62 + 0.09 * k)
            pts = [(x, base + math.sin(x / (110 * s) + k * 1.3) * 16 * s) for x in range(0, int(w) + 8, 8)]
            draw.polygon(pts + [(w, h), (0, h)], fill=rgb(accent if k == 0 else "#0a4a5c", 70 + 25 * k))
    elif kind == "embers":
        for _ in range(26):
            x, y, r = rng.random() * w, h * (0.35 + 0.65 * rng.random()), (1.5 + rng.random() * 3) * s
            draw.ellipse((x - r, y - r, x + r, y + r), fill=rgb(accent if rng.random() < 0.6 else "#ff8c42", 230))
        for k in range(3):
            x, y, r = w * (0.2 + 0.3 * k), h * 0.12, 120 * s
            draw.ellipse((x - r, y - r * 0.6, x + r, y + r * 0.6), fill=rgb("#5a4038", 70))
    elif kind == "hills":
        color = arg or "#2f4a1c"
        for k in range(2):
            base = h * (0.8 + 0.06 * k)
            pts = [(x, base + math.sin(x / (170 * s) + k * 2) * 22 * s) for x in range(0, int(w) + 8, 8)]
            draw.polygon(pts + [(w, h), (0, h)], fill=rgb(color, 255 - 60 * k))
        r = 52 * s
        draw.ellipse((w * 0.58 - r, h * 0.2 - r, w * 0.58 + r, h * 0.2 + r), fill=rgb(accent, 120))
    elif kind == "aurora":
        glow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse((w * 0.05, -h * 0.2, w * 0.55, h * 0.4), fill=rgb("#50dcb4", 110))
        gd.ellipse((w * 0.45, -h * 0.3, w * 0.95, h * 0.3), fill=rgb("#78a0ff", 100))
        layer.alpha_composite(glow.filter(ImageFilter.GaussianBlur(40 * s)))
        draw.polygon([(x, h * 0.86 + math.sin(x / (200 * s)) * 18 * s) for x in range(0, int(w) + 8, 8)] + [(w, h), (0, h)],
                     fill=rgb("#cfeeff", 200))
    elif kind == "ring":
        cx, cy = w * 0.5, h * 0.5
        for radius, alpha in ((250, 60), (190, 45)):
            r = radius * s
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=rgb("#5adca0", alpha), width=max(2, int(3 * s)))
        for _ in range(8):
            x, y, r = rng.random() * w, rng.random() * h, 3 * s
            draw.ellipse((x - r, y - r, x + r, y + r), fill=rgb(accent, 220))
    elif kind == "skyline":
        pts = [(0, h)]
        x = 0.0
        while x < w:
            top = h * (0.84 - 0.34 * (x / w) ** 1.6) - rng.random() * 40 * s
            pts += [(x, top), (x + 46 * s, top)]
            x += 46 * s
        pts.append((w, h))
        draw.polygon(pts, fill=rgb("#1a1220", 235))
        r = 36 * s
        draw.ellipse((w * 0.9 - r, h * 0.16 - r, w * 0.9 + r, h * 0.16 + r), outline=rgb(accent, 150), width=max(2, int(4 * s)))
    elif kind == "pulse":
        cx, cy = w * 0.5, h * 0.55
        for k, radius in enumerate((130, 230, 330, 430)):
            r = radius * s
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=rgb(accent, 80 - 15 * k), width=max(2, int(5 * s)))
    elif kind == "marks":
        for row, y in enumerate((0.2, 0.34, 0.78, 0.9)):
            x = rng.random() * 60 * s
            while x < w:
                length = (20 + rng.random() * 60) * s
                draw.rounded_rectangle((x, h * y, x + length, h * y + 8 * s), radius=4 * s,
                                       fill=rgb(accent, 70 if row % 2 else 110))
                x += length + (22 + rng.random() * 30) * s
    elif kind == "network":
        nodes = [(w * rng.uniform(0.05, 0.95), h * rng.uniform(0.08, 0.92)) for _ in range(9)]
        for i, a in enumerate(nodes):
            b = nodes[(i * 3 + 1) % len(nodes)]
            draw.line((*a, *b), fill=rgb("#8ca0ff", 70), width=max(1, int(2 * s)))
        for i, (x, y) in enumerate(nodes):
            r = (6 if i else 9) * s
            draw.ellipse((x - r, y - r, x + r, y + r), fill=rgb("#3a5a9c" if i else accent, 235))


# ---------------------------------------------------------------- favicon glyphs (64x64 design space)

def bezier(p0, p1, p2, p3, steps=24):
    out = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        out.append((u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
                    u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]))
    return out


def arc_points(cx, cy, r, a0, a1, steps=24):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / steps)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / steps))) for i in range(steps + 1)]


def stroke(draw, points, width, fill):
    """A polyline with round caps and joins."""
    draw.line(points, fill=fill, width=int(round(width)), joint="curve")
    for x, y in (points[0], points[-1]):
        r = width / 2
        draw.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def draw_glyph(draw, glyph, scale, tile_color):
    """Draw a favicon glyph given in 64x64 design units onto `draw` scaled by `scale`."""
    S = lambda pts: [(x * scale, y * scale) for x, y in pts]
    white = rgb("#ffffff")
    kind = glyph[0]
    if kind == "letter":
        _, char, color = glyph
        face = font(int(36 * scale) if char != "$" else int(34 * scale))
        draw.text((32 * scale, 34 * scale), char, font=face, fill=rgb(color), anchor="mm")
    elif kind == "leaf":
        pts = bezier((32, 14), (45, 21), (45, 41), (32, 51)) + bezier((32, 51), (19, 41), (19, 21), (32, 14))
        draw.polygon(S(pts), fill=white)
        stroke(draw, S([(32, 20), (32, 47)]), 2.2 * scale, rgb(tile_color))
    elif kind == "bolt":
        draw.polygon(S([(35, 10), (17, 36), (27, 36), (23, 54), (48, 26), (36, 26)]), fill=white)
    elif kind == "waves":
        for dy, alpha in ((0, 255), (14, 158)):
            pts = []
            for p in ((11, 27), (17, 19), (23, 19), (29, 27)), ((29, 27), (35, 35), (41, 35), (47, 27)), ((47, 27), (53, 19), (59, 19), (65, 27)):
                pts += bezier(*[(x, y + dy) for x, y in p])
            stroke(draw, S(pts), 5 * scale, rgb("#ffffff", alpha))
    elif kind == "snow":
        for a, b in (((32, 12), (32, 52)), ((14, 22), (50, 42)), ((14, 42), (50, 22))):
            stroke(draw, S([a, b]), 4.5 * scale, white)
    elif kind == "infinity":
        pts = [(32 + 17 * math.cos(t) / (1 + math.sin(t) ** 2), 32 + 17 * math.sin(t) * math.cos(t) / (1 + math.sin(t) ** 2) * 1.6)
               for t in [i * math.pi * 2 / 80 for i in range(81)]]
        stroke(draw, S(pts), 5 * scale, white)
    elif kind == "signal":
        amber = rgb("#ffb347")
        stroke(draw, S(arc_points(36.33, 32, 20, 156.4, 203.6)), 5 * scale, amber)
        stroke(draw, S(arc_points(27.67, 32, 20, -23.6, 23.6)), 5 * scale, amber)
        stroke(draw, S(arc_points(33.66, 32, 10, 130.9, 229.1)), 5 * scale, amber)
        stroke(draw, S(arc_points(30.34, 32, 10, -49.1, 49.1)), 5 * scale, amber)
        r = 4.5 * scale
        draw.ellipse((32 * scale - r, 32 * scale - r, 32 * scale + r, 32 * scale + r), fill=amber)
    elif kind == "hat":
        gold, plum, blue = rgb("#ffc15e"), rgb("#7a2e4e"), rgb("#8fd3ff")
        draw.polygon(S(bezier((19, 41), (17, 24), (27, 17), (32, 17)) + bezier((32, 17), (37, 17), (47, 24), (45, 41))), fill=gold)
        draw.ellipse((9 * scale, 35 * scale, 55 * scale, 49 * scale), fill=gold)
        draw.polygon(S([(19.4, 36), (44.6, 36), (44.9, 40.5), (19.1, 40.5)]), fill=plum)
        for cx, r in ((32, 2.2), (24, 1.6), (40, 1.6)):
            draw.ellipse(((cx - r) * scale, (50.5 - r) * scale, (cx + r) * scale, (50.5 + r) * scale), fill=blue)
    elif kind == "lighthouse":
        draw.polygon(S([(0, 26), (30, 26), (30, 30), (0, 36)]), fill=rgb("#ffcf6b", 140))
        draw.polygon(S([(25, 50), (28, 24), (36, 24), (39, 50)]), fill=rgb("#f4f1e8"))
        draw.polygon(S([(26.4, 40), (27.2, 33), (36.8, 33), (37.6, 40)]), fill=rgb("#c8483a"))
        draw.rectangle((27 * scale, 17 * scale, 37 * scale, 24 * scale), fill=rgb("#ffcf6b"))
        draw.polygon(S([(26, 17), (38, 17), (32, 10)]), fill=rgb("#e8eef2"))
        draw.rectangle((23 * scale, 49 * scale, 41 * scale, 52 * scale), fill=rgb("#f4f1e8"))
        stroke(draw, S(bezier((10, 56), (14, 52), (20, 52), (24, 56)) + bezier((24, 56), (28, 60), (34, 60), (38, 56)) + bezier((38, 56), (42, 52), (48, 52), (52, 56))), 2.2 * scale, rgb("#7fd1ff"))
    elif kind == "stall":
        draw.rounded_rectangle((8 * scale, 12 * scale, 56 * scale, 36 * scale), radius=10 * scale, fill=rgb("#e8a33d"))
        draw.rectangle((8 * scale, 24 * scale, 56 * scale, 36 * scale), fill=rgb("#e8a33d"))
        for k in range(4):
            x0 = (8 + 12 * k) * scale
            draw.rectangle((x0, 24 * scale, x0 + 12 * scale, 30 * scale), fill=rgb("#c7442e"))
            draw.ellipse((x0, 24 * scale, x0 + 12 * scale, 33 * scale), fill=rgb("#c7442e"))
        draw.rounded_rectangle((12 * scale, 38 * scale, 52 * scale, 52 * scale), radius=3 * scale, fill=rgb("#7bc96f"), outline=rgb("#1a1420"), width=max(1, int(2 * scale)))
        for cx, col in ((24, "#ff9f6b"), (40, "#f2c14e")):
            draw.ellipse(((cx - 4) * scale, 41 * scale, (cx + 4) * scale, 49 * scale), fill=rgb(col))
    elif kind == "compass":
        cyan, ice, orange = rgb("#7fd1ff"), rgb("#e7eff9"), rgb("#ffb25e")
        draw.ellipse((10 * scale, 10 * scale, 54 * scale, 54 * scale), outline=cyan, width=max(1, int(2.5 * scale)))
        draw.polygon(S([(32, 8), (36, 32), (32, 56), (28, 32)]), fill=ice)
        draw.polygon(S([(10, 32), (32, 28.5), (54, 32), (32, 35.5)]), outline=cyan, width=max(1, int(2 * scale)))
        stroke(draw, S(bezier((16, 46), (24, 43), (36, 36), (40, 22)) + [(47, 18)]), 3.5 * scale, orange)
        for k in range(4):
            t0, t1 = k / 4.5, (k + 0.55) / 4.5
            a = (18 + 27 * t0, 49 - 25 * t0)
            b = (18 + 27 * t1, 49 - 25 * t1)
            stroke(draw, S([a, b]), 2.5 * scale, cyan)
    elif kind == "gate":
        cyan, gold = rgb("#5fd4e6"), rgb("#f2b84b")
        stroke(draw, S([(12, 20), (26, 20)]), 3 * scale, cyan)
        stroke(draw, S([(12, 44), (26, 44)]), 3 * scale, cyan)
        body = [(26, 12), (36, 12)] + arc_points(36, 32, 20, -90, 90) + [(26, 52)]
        draw.polygon(S(body), fill=rgb("#14233a"))
        stroke(draw, S(body + [(26, 12)]), 3 * scale, cyan)
        stroke(draw, S([(42, 32), (54, 32)]), 3 * scale, gold)
        draw.ellipse((51 * scale, 28 * scale, 59 * scale, 36 * scale), fill=gold)
    elif kind == "lexis":
        blue = rgb("#9ad0ff")
        for a, b in (((16, 22), (26, 22)), ((34, 22), (36, 22)), ((42, 22), (48, 22)),
                     ((16, 42), (18, 42)), ((26, 42), (38, 42)), ((46, 42), (48, 42))):
            stroke(draw, S([a, b]), 5 * scale, blue)
        r = 3 * scale
        draw.ellipse((32 * scale - r, 32 * scale - r, 32 * scale + r, 32 * scale + r), fill=rgb("#ffd27a"))


def favicon_tile(slug, size):
    """The game's favicon redrawn at `size` px (rounded square plus glyph), RGBA."""
    theme = THEMES.get(slug, FALLBACK_THEME)
    big = size * 4
    scale = big / 64
    tile = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    fill = theme[3]
    if "|" in fill:
        a, b = fill.split("|")
        base = diagonal_gradient(big, big, [a, b]).transpose(Image.FLIP_TOP_BOTTOM)
    else:
        base = Image.new("RGBA", (big, big), rgb(fill))
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, big - 1, big - 1), radius=14 * scale, fill=255)
    tile.paste(base, (0, 0), mask)
    glyph = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw_glyph(ImageDraw.Draw(glyph), theme[4], scale, fill.split("|")[0])
    tile.alpha_composite(glyph)
    return tile.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------- cards

def fit_text(draw, text, max_width, start, minimum=48):
    size = start
    while size > minimum and draw.textlength(text, font=font(size)) > max_width:
        size -= 4
    return font(size)


def paste_shadowed(canvas, tile, xy, blur=22, alpha=150):
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sd = Image.new("RGBA", tile.size, (0, 0, 0, alpha))
    sd.putalpha(tile.getchannel("A").point(lambda v: min(v, alpha)))
    shadow.paste(sd, (xy[0], xy[1] + 10))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(blur)))
    canvas.alpha_composite(tile, xy)


def tag_label(tag):
    return tag.replace("-", " ").title()


def draw_footer(draw, y=566):
    draw.text((72, y), sitedata.BASE_URL.replace("https://", "").rstrip("/"), font=font(26, bold=False), fill=rgb("#ffffff", 210))


def game_card(game):
    slug = game["slug"]
    stops, motif_name, accent, _tile, _glyph = THEMES.get(slug, FALLBACK_THEME)
    rng = random.Random(slug)
    base = diagonal_gradient(W * SS, H * SS, stops)
    art = Image.new("RGBA", base.size, (0, 0, 0, 0))
    motif(art, motif_name, accent, rng, base.size)
    base.alpha_composite(art)
    canvas = base.resize((W, H), Image.LANCZOS)

    # Scrim so white text stays readable on the bright themes (champ-de-mots, herd).
    row = Image.new("RGBA", (W, 1))
    row.putdata([(8, 10, 22, int(205 * max(0.0, 1 - x / (W * 0.82)) + 40)) for x in range(W)])
    canvas.alpha_composite(row.resize((W, H)))

    draw = ImageDraw.Draw(canvas)
    draw.text((72, 64), "NOYVJGAMES", font=font(28), fill=rgb(accent))
    title_font = fit_text(draw, game["name"], 700, 118)
    draw.text((72, 112), game["name"], font=title_font, fill=rgb("#ffffff"))
    y = 112 + title_font.size + 26
    for line in textwrap.wrap(textwrap.shorten(game["blurb"], width=150, placeholder="..."), width=40)[:4]:
        draw.text((72, y), line, font=font(34, bold=False), fill=rgb("#ffffff", 235))
        y += 48
    x = 72
    for tag in game["tags"][:3]:
        label = tag_label(tag)
        pill_w = int(draw.textlength(label, font=font(24))) + 36
        draw.rounded_rectangle((x, 500, x + pill_w, 548), radius=24, outline=rgb("#ffffff", 190), width=2)
        draw.text((x + 18, 524), label, font=font(24), fill=rgb("#ffffff"), anchor="lm")
        x += pill_w + 14
    draw_footer(draw)
    paste_shadowed(canvas, favicon_tile(slug, 300), (820, 165))
    return canvas.convert("RGB")


def hub_card(games):
    canvas = diagonal_gradient(W, H, ["#0b0d17", "#1a2140", "#0b0d17"])
    art = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    motif(art, "stars", "#8fb0e8", random.Random("hub"), art.size)
    canvas.alpha_composite(art.resize((W, H), Image.LANCZOS))
    draw = ImageDraw.Draw(canvas)
    draw.text((72, 78), "NoyvjGames", font=fit_text(draw, "NoyvjGames", 1000, 124), fill=rgb("#ffffff"))
    draw.text((72, 226), "Small AI-assisted game demos, built one milestone at a time.", font=font(34, bold=False), fill=rgb("#ffffff", 230))
    draw.text((72, 276), f"{len(games)} games in your browser. Nothing to install.", font=font(28, bold=False), fill=rgb("#8fb0e8"))
    cols = 7
    size, gap = 100, 16
    left = (W - (cols * size + (cols - 1) * gap)) // 2
    for i, game in enumerate(games):
        col, row = i % cols, i // cols
        paste_shadowed(canvas, favicon_tile(game["slug"], size), (left + col * (size + gap), 330 + row * (size + gap)), blur=8, alpha=120)
    draw_footer(draw, 586)
    return canvas.convert("RGB")


# ---------------------------------------------------------------- meta snippets

START, END = "<!-- share-meta:start (generated by scripts/generate-share-cards.py) -->", "<!-- share-meta:end -->"


def meta_block(title, description, url, image, alt):
    e = sitedata.esc
    return "\n".join([
        START,
        f'<meta name="description" content="{e(description)}">',
        f'<link rel="canonical" href="{e(url)}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:site_name" content="{sitedata.SITE_NAME}">',
        f'<meta property="og:title" content="{e(title)}">',
        f'<meta property="og:description" content="{e(description)}">',
        f'<meta property="og:url" content="{e(url)}">',
        f'<meta property="og:image" content="{e(image)}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:image:alt" content="{e(alt)}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{e(title)}">',
        f'<meta name="twitter:description" content="{e(description)}">',
        f'<meta name="twitter:image" content="{e(image)}">',
        f'<meta name="twitter:image:alt" content="{e(alt)}">',
        END,
    ]) + "\n"


def inject(text, block):
    """Insert or refresh the share-meta block right after </title> (it must come BEFORE the shared
    includes: shared/tests/test_site_includes.py needs the <head> to end with the lite-mode.css link)."""
    pattern = re.compile(re.escape(START.split(" (")[0]) + r".*?" + re.escape(END) + r"\n?", re.S)
    text = pattern.sub("", text, count=1)
    return re.sub(r"(</title>\n)", lambda m: m.group(1) + block, text, count=1)


def build_outputs(games):
    """{relative path: text} for every snippet and page block (the PNGs are written separately)."""
    out = {}
    hub_desc = sitedata.hub_description(games)
    hub_image = sitedata.BASE_URL + "share/hub.png"
    hub_alt = "NoyvjGames: the hub with a tile for each of its games"
    out["share/meta/hub.html"] = meta_block("NoyvjGames", hub_desc, sitedata.BASE_URL, hub_image, hub_alt)
    for game in games:
        title = f"{game['name']} - NoyvjGames"
        out[f"share/meta/{game['slug']}.html"] = (
            f"<title>{sitedata.esc(title)}</title>\n"
            + meta_block(title, game["blurb"], sitedata.game_url(game["slug"]), sitedata.share_image_url(game["slug"]),
                         f"{game['name']} on NoyvjGames")
        )
    for filename, title, description, _in_sitemap in sitedata.PUBLIC_PAGES:
        if filename in ("terms.html",):
            continue  # terms.html is not part of this batch's file ownership
        path = sitedata.ROOT / filename
        if not path.exists():
            continue
        block = meta_block(title if filename != "index.html" else "NoyvjGames: small AI-assisted game demos",
                           description or hub_desc, sitedata.page_url(filename), hub_image, hub_alt)
        out[filename] = inject(path.read_text(encoding="utf-8"), block)
    return out


def main(argv):
    check = "--check" in argv
    games = sitedata.load_games()
    if not games:
        sys.exit("No games found in index.html / game-manifest.json.")
    outputs = build_outputs(games)
    stale = []
    for rel, text in outputs.items():
        path = sitedata.ROOT / rel
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            stale.append(rel)
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
    if not check:
        SHARE.mkdir(exist_ok=True)
        hub_card(games).save(SHARE / "hub.png", optimize=True)
        for game in games:
            game_card(game).save(SHARE / f"{game['slug']}.png", optimize=True)
    if check:
        print("Out of date: " + ", ".join(stale) if stale else "Up to date (text files; PNGs are only checked by the tests)")
    else:
        print("Wrote: " + (", ".join(stale) or "no text files changed") + f"; {len(games) + 1} cards")
    return 1 if check and stale else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
