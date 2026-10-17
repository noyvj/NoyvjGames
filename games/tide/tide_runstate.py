"""The module variables that get REPLACED while the game runs (the settlement, panel-open flags, filters, library picks).

Other modules read and write them as `runstate.x`, never as a copied name."""

from tide_rules import LIBRARY_CURRENT, PLANNER_MIN_SEASONS


# D8: which rows were flooded as of the last render_coastline() call --
# purely a rendering concern (drives the one-shot flash below), never
# part of the save contract, so it's a plain module global rather than
# anything on SettlementState. Reset in setup() and load_state() so a
# fresh/loaded game doesn't spuriously flash every already-flooded row
# on its very first render.
_previous_flooded_rows = set()

info_page_open = False


# D-22 / D-23: which stretch of the session the trend graphs show, and whether series get
# distinct dash styles and point shapes. Both are view options kept in this browser only.
graph_range = "all"
graph_markers = False


achievements_open = False

# Tracks the earned-id set as of the last time it was checked, so a fresh
# unlock (one that wasn't in this set last time) can trigger a toast
# without re-toasting every already-earned achievement on every render.
# Reset (without toasting) right after setup()'s initial render and right
# after load_state() applies a save, so neither a fresh game nor a loaded
# one spams toasts for achievements that were already satisfied before
# this render cycle started.
_previously_earned_ids = set()

_toast_hide_proxy_gen = 0

changelog_open = False


# D7: an end-of-session summary screen -- player-triggered, same
# optional/never-forced pattern as the achievements/info-page panels.
session_summary_open = False


# D-17: which filter chip and search text the full history is showing. A
# view preference only: never saved, resets on reload.
ticker_filter = "all"
ticker_search = ""

# The live ticker has its OWN filter, separate from the full history's. It starts on All, is closed behind a
# "Filter this list" summary and is never saved, so a reload always shows every recent message. While a filter
# is on, a visible line under the ticker (and the summary itself) says how many messages are hidden.
live_ticker_filter = "all"
live_ticker_search = ""

ledger_open = False
ledger_sort_key = "season"
ledger_sort_descending = True

scrub_season = None
_scrub_stamp = None

library_open = False
library_a = LIBRARY_CURRENT
library_b = ""
library_overlay_id = ""
_library_status = ""
_library_proxies = []

daily_open = False

almanac_open = False

planner_open = False
planner_length = PLANNER_MIN_SEASONS

_FAVICON_ORIGINAL = None

afford_pin = ""  # id of the target highlighted in the affordability list ("" for none); kept per browser


# R-30: the community average of coastline_kept, handed in by the page once GET /stats/games/tide has
# answered (nothing is stored; a reload asks again). None until then, and whenever the figure is
# suppressed (fewer than three saves) or the backend does not list the field yet.
community_coastline = None

state = None  # tide_model_season creates the SettlementState here when it is imported

best_coastline_saved = None  # tide_panels sets the stored best here when it is imported (load_best_coastline_saved())

almanac = None  # tide_almanac creates the empty almanac here when it is imported; game.py fills it from localStorage before setup()


# Names that other modules must reach as runstate.<name> (game.py forwards reads and writes to them).
LIVE_NAMES = (
    "state",
    "_previous_flooded_rows",
    "info_page_open",
    "graph_range",
    "graph_markers",
    "best_coastline_saved",
    "achievements_open",
    "_previously_earned_ids",
    "_toast_hide_proxy_gen",
    "changelog_open",
    "session_summary_open",
    "ticker_filter",
    "ticker_search",
    "live_ticker_filter",
    "live_ticker_search",
    "ledger_open",
    "ledger_sort_key",
    "ledger_sort_descending",
    "scrub_season",
    "_scrub_stamp",
    "library_open",
    "library_a",
    "library_b",
    "library_overlay_id",
    "_library_status",
    "_library_proxies",
    "daily_open",
    "almanac",
    "almanac_open",
    "planner_open",
    "planner_length",
    "_FAVICON_ORIGINAL",
    "afford_pin",
    "community_coastline",
)
