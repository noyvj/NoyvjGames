"""Coastline helpers: which coastline is in force, its tiles, rows, heritage sites and flood state."""

import tide_runstate as runstate
from tide_rules import COASTLINES, COASTLINE_COLS, COASTLINE_ROWS, DEFAULT_COASTLINE, FLOODED, LAND


def clean_coastline(coastline_id):
    return coastline_id if isinstance(coastline_id, str) and coastline_id in COASTLINES else DEFAULT_COASTLINE


def _coast_id(coast_id=None):
    """The coastline in force: the one given, else the running settlement's."""
    if coast_id is None:
        coast_id = getattr(runstate.state, "coastline", DEFAULT_COASTLINE)
    return clean_coastline(coast_id)


def coast_info(coast_id=None):
    return COASTLINES[_coast_id(coast_id)]


def heritage_sites(coast_id=None):
    return coast_info(coast_id)["heritage"]


def coast_meter_max(coast_id=None):
    """The sea level at which even the highest row is flooded (the sea-level meter's full scale)."""
    return max(coast_info(coast_id)["thresholds"])


def coast_storm_interval(coast_id=None):
    return coast_info(coast_id)["storm_interval"]


def row_flood_threshold(row, coast_id=None):
    return coast_info(coast_id)["thresholds"][row]


def tile_row_state(row, sea_level, coast_id=None):
    return FLOODED if sea_level >= row_flood_threshold(row, coast_id) else LAND


def coastline_grid(sea_level, coast_id=None):
    """COASTLINE_ROWS x COASTLINE_COLS grid of "land"/"flooded" strings —
    pure state, no DOM — so the flood thresholds are testable without a
    browser."""
    return [
        [tile_row_state(row, sea_level, coast_id) for _ in range(COASTLINE_COLS)]
        for row in range(COASTLINE_ROWS)
    ]


def flooded_row_count(sea_level, coast_id=None):
    """How many of the COASTLINE_ROWS rows are flooded at a given sea
    level -- every row shares one state across all COASTLINE_COLS
    columns, so counting rows (not tiles) is the meaningful unit for
    "how much coastline is gone" (D4/D11/achievements all read this)."""
    return sum(1 for row in range(COASTLINE_ROWS) if tile_row_state(row, sea_level, coast_id) == FLOODED)


def _is_seawall_row(row_index, tier_index):
    """The bottom `tier_index` rows carry the seawall visual — thicker
    coverage as tiers unlock, since higher tiers mean more reinforced
    ground closest to the water."""
    return row_index >= COASTLINE_ROWS - tier_index
