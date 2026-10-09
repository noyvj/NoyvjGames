"""Continuum -- K-12: a generated map with biomes.

An optional start (chosen before the first season of a fresh settlement, off by default)
gives the settlement a **map**: a small grid of ground, `WIDTH` by `HEIGHT` cells, drawn from
a number (the **seed**) that is shown and can be re-rolled until the first season has passed.
The same seed always gives the same map on every device. Each cell is plains, or one of four
biomes: **river**, **coast** (open water along one edge), **mountains** or **desert**.

What a biome does. The more cells of it, the stronger its level (1 to 3); each biome has one
boon and one price, both through the one research seam (the effects dict), so they work exactly
like a discovery:

* River: food gathered +4% and canals +6% per level; the land recovers 3% slower (flooding).
* Coast: surplus kept as trade +5% and relay throughput +5% per level; food stores hold 3 less
  (damp air).
* Mountains: materials gathered +5% per level; food gathered 3% less (little farmland).
* Desert: food stores hold 6 more (dry air); food gathered 5% less and land recovery 4%
  slower per level.

Small on purpose: the map is a flavour with a trade-off, not a lever that decides a run, and
every number is shown in the Geography panel with where it comes from.

What it does NOT do (the item asked for more, see CLAUDE.md): there are no disasters in
Continuum's deterministic simulation, so none "hit" differently; building costs are
fixed constants shared by the Build panel, the Hamlet view and the advisors, so the map
changes yields rather than prices; and districts are not blocked from any ground (a canal
without a river just gets no river bonus). Consulting cases carry a fixed inherited map.

Where it plugs in. The seed lives in `campaign.ui["geography"] = {"seed": n}` (plain JSON,
written only when a map is chosen, validated on every read by `clean_seed`). A consulting
case's map comes from `CASE_SEEDS` and needs nothing saved. Pure functions only: no DOM, no
storage, no clock; the generator uses its own small linear congruential generator so a
seed means the same map in every browser.
"""

import html

KEY = "geography"
WIDTH = 7
HEIGHT = 5
SEED_MAX = 2 ** 31 - 1

PLAINS = "plains"
RIVER = "river"
COAST = "coast"
MOUNTAINS = "mountains"
DESERT = "desert"
BIOMES = (RIVER, COAST, MOUNTAINS, DESERT)
LABEL = {PLAINS: "Plains", RIVER: "River", COAST: "Coast", MOUNTAINS: "Mountains", DESERT: "Desert"}
# One letter per cell on the map, so the map never relies on colour alone.
LETTER = {PLAINS: "", RIVER: "~", COAST: "≈", MOUNTAINS: "▲", DESERT: "·"}

# Boon and price per level, as {effects key: change}. Multipliers are bases-of-1.0 deltas, bonuses additive.
EFFECTS = {
    RIVER: {"food_yield_mult": 0.04, "canal_yield_bonus": 0.06, "regen_mult": -0.03},
    COAST: {"surplus_conversion_bonus": 0.05, "relay_bonus": 0.05, "food_storage_bonus": -3.0},
    MOUNTAINS: {"materials_yield_mult": 0.05, "food_yield_mult": -0.03},
    DESERT: {"food_storage_bonus": 6.0, "food_yield_mult": -0.05, "regen_mult": -0.04},
}
BLURB = {
    RIVER: "Fertile floodplain and a place for canals, but the floods wear the soil.",
    COAST: "Open water: easier trade and longer reach, with damp air that spoils stored food.",
    MOUNTAINS: "Stone and ore close at hand, and very little land to farm.",
    DESERT: "Dry air keeps the stores sound, and the thin ground gives and recovers less.",
}

# The inherited maps of the two consulting cases (seeds chosen so each has the geography its case is named for).
CASE_SEEDS = {"smokestack": 3, "sprawl": 65}


# --- validation -------------------------------------------------------------
def clean_seed(raw):
    """A seed from whatever a save handed back: an int in 1..SEED_MAX, or None."""
    if isinstance(raw, bool) or not isinstance(raw, int):
        return None
    return raw if 1 <= raw <= SEED_MAX else None


def chosen_seed(ui):
    """The seed the player chose (None for open land)."""
    raw = ui.get(KEY) if isinstance(ui, dict) else None
    return clean_seed(raw.get("seed")) if isinstance(raw, dict) else None


def set_seed(ui, seed):
    seed = clean_seed(seed)
    if seed is None:
        ui.pop(KEY, None)
        return None
    ui[KEY] = {"seed": seed}
    return seed


def active_seed(ui, case_id=None):
    """The seed in force: a consulting case's inherited map, else the player's choice, else None."""
    if isinstance(case_id, str) and case_id in CASE_SEEDS:
        return CASE_SEEDS[case_id]
    return chosen_seed(ui)


# --- the generator ------------------------------------------------------------
class _Lcg:
    def __init__(self, seed):
        self.state = seed % 2147483648 or 1

    def next(self, bound):
        self.state = (self.state * 1103515245 + 12345) % 2147483648
        return (self.state >> 8) % bound


def generate(seed):
    """The map for `seed` as a list of HEIGHT rows of WIDTH biome names (an empty list for a bad seed)."""
    seed = clean_seed(seed)
    if seed is None:
        return []
    rng = _Lcg(seed)
    grid = [[PLAINS] * WIDTH for _ in range(HEIGHT)]
    # Coast: open water along one edge, ragged by one cell, 60% of the time.
    sea_edge = None
    if rng.next(10) < 6:
        sea_edge = rng.next(4)
        for i in range(WIDTH if sea_edge in (0, 1) else HEIGHT):
            depth = 1 + rng.next(2)
            for d in range(depth):
                if sea_edge == 0:
                    grid[d][i] = COAST
                elif sea_edge == 1:
                    grid[HEIGHT - 1 - d][i] = COAST
                elif sea_edge == 2:
                    grid[i][d] = COAST
                else:
                    grid[i][WIDTH - 1 - d] = COAST
    # River: a walk across the map, away from the sea when there is one, 70% of the time.
    if rng.next(10) < 7:
        if sea_edge in (0, 1):
            x, y, dy = rng.next(WIDTH), (HEIGHT - 1 if sea_edge == 0 else 0), (-1 if sea_edge == 0 else 1)
            for _ in range(HEIGHT):
                if grid[y][x] == PLAINS:
                    grid[y][x] = RIVER
                step = rng.next(3) - 1
                x = max(0, min(WIDTH - 1, x + step))
                y += dy
                if not 0 <= y < HEIGHT:
                    break
        else:
            y, x = rng.next(HEIGHT), 0
            for _ in range(WIDTH):
                if grid[y][x] == PLAINS:
                    grid[y][x] = RIVER
                step = rng.next(3) - 1
                y = max(0, min(HEIGHT - 1, y + step))
                x += 1
                if x >= WIDTH:
                    break
    # Mountains and desert: grown clusters on plains.
    for biome, chance, size_low, size_high in ((MOUNTAINS, 8, 3, 6), (DESERT, 5, 3, 5)):
        if rng.next(10) >= chance:
            continue
        cx, cy = rng.next(WIDTH), rng.next(HEIGHT)
        want = size_low + rng.next(size_high - size_low + 1)
        placed, tries = 0, 0
        while placed < want and tries < 60:
            tries += 1
            if grid[cy][cx] == PLAINS:
                grid[cy][cx] = biome
                placed += 1
            cx = max(0, min(WIDTH - 1, cx + rng.next(3) - 1))
            cy = max(0, min(HEIGHT - 1, cy + rng.next(3) - 1))
    return grid


def counts(grid):
    out = {b: 0 for b in BIOMES}
    for row in grid or []:
        for cell in row:
            if cell in out:
                out[cell] += 1
    return out


def level_of(cells):
    """1 to 3 by how many cells a biome covers (0 for none)."""
    if cells <= 0:
        return 0
    if cells <= 3:
        return 1
    if cells <= 7:
        return 2
    return 3


def levels(grid):
    return {biome: level_of(n) for biome, n in counts(grid).items()}


# --- effects -------------------------------------------------------------------
def effect_deltas(grid):
    """The combined {effects key: change} the map's biomes make."""
    total = {}
    for biome, level in levels(grid).items():
        for key, per_level in EFFECTS[biome].items():
            total[key] = round(total.get(key, 0.0) + per_level * level, 4)
    return {key: value for key, value in total.items() if value}


def apply_effects(effects, seed):
    """`effects` with the map's changes added (the same object when there is no map)."""
    grid = generate(seed)
    if not grid:
        return effects
    deltas = effect_deltas(grid)
    if not deltas:
        return effects
    out = dict(effects)
    for key, delta in deltas.items():
        value = out.get(key, 1.0 if key.endswith("_mult") else 0.0) + delta
        if key.endswith("_mult"):
            value = max(0.1, value)
        elif key == "food_storage_bonus":
            value = max(-20.0, value)
        out[key] = value
    return out


def describe(grid):
    """Plain lines, one per biome that is present: its share, level, boon and price."""
    lines = []
    n = counts(grid)
    for biome in BIOMES:
        if not n[biome]:
            continue
        level = level_of(n[biome])
        parts = []
        for key, per_level in EFFECTS[biome].items():
            total = per_level * level
            label = EFFECT_TEXT[key]
            if key == "food_storage_bonus":
                parts.append(f"{label} {total:+.0f}")
            else:
                parts.append(f"{label} {total * 100:+.0f}%")
        lines.append(f"{LABEL[biome]} ({n[biome]} of {WIDTH * HEIGHT} cells, level {level}): " + "; ".join(parts) + ". " + BLURB[biome])
    return lines


EFFECT_TEXT = {
    "food_yield_mult": "food gathered",
    "canal_yield_bonus": "canal yield",
    "regen_mult": "land recovery",
    "surplus_conversion_bonus": "surplus kept as trade",
    "relay_bonus": "relay throughput",
    "food_storage_bonus": "food storage",
    "materials_yield_mult": "materials gathered",
}


def summary_text(grid):
    if not grid:
        return "open land"
    n = counts(grid)
    present = [f"{LABEL[b].lower()} {n[b]}" for b in BIOMES if n[b]]
    return ", ".join(present) if present else "all plains"


# --- the 2D map -------------------------------------------------------------------
CELL = 26


def map_svg(grid):
    """The map as an SVG: every cell labelled by a symbol and its biome in the title, so colour is not the only cue."""
    if not grid:
        return ""
    width, height = WIDTH * CELL + 8, HEIGHT * CELL + 8
    parts = [
        f'<svg viewBox="0 0 {width} {height}" class="views-svg geo-svg" role="img" '
        f'aria-label="Map of the settlement\'s ground: {html.escape(summary_text(grid))}">'
    ]
    for y, row in enumerate(grid):
        for x, biome in enumerate(row):
            px, py = 4 + x * CELL, 4 + y * CELL
            parts.append(
                f'<rect x="{px}" y="{py}" width="{CELL - 2}" height="{CELL - 2}" rx="3" class="geo-cell geo-{biome}">'
                f'<title>{LABEL[biome]}</title></rect>'
            )
            mark = LETTER[biome]
            if mark:
                parts.append(f'<text x="{px + (CELL - 2) / 2}" y="{py + CELL / 2 + 3}" text-anchor="middle" class="geo-mark">{mark}</text>')
    parts.append("</svg>")
    return "".join(parts)


def terrain_cells(grid):
    """The non-plains cells for the 3D scene: [{"x": -1..1, "z": -1..1, "biome": name}] in map-centred units."""
    out = []
    for y, row in enumerate(grid or []):
        for x, biome in enumerate(row):
            if biome == PLAINS:
                continue
            out.append({
                "x": round((x - (WIDTH - 1) / 2) / ((WIDTH - 1) / 2), 3),
                "z": round((y - (HEIGHT - 1) / 2) / ((HEIGHT - 1) / 2), 3),
                "biome": biome,
            })
    return out
