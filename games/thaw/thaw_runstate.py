"""The module variables that get REPLACED while the game runs (modes, panel-open flags, counters, the undo snapshot).

Other modules read and write them as `runstate.x`, never as a copied name."""


long_game = False
hold_the_line = False
temp_unit = "c"

worst_case_region_revealed = False
# G30: the "Region D is fully automated" first-reveal note shows until the
# player closes the panel once, then never again.
worst_case_intro_seen = False

log_filter = "all"
log_query = ""

preset_used_ever = False

custom_preset = None  # {category: units 1..PLANNER_MAX_UNITS} for the categories in the mix, or None


confirm_threshold = 0

hard_mode = False
forecast_miss_total = 0.0  # the sum of how far each scored forecast was from the real figure

info_page_open = False

carbon_bank = 0

crates_delivered = 0
crates_opened = 0
_crate_just_opened = None  # one render's worth of "lid pops open", set by open_crate()

framing = "regional"

forecast_guess = None      # the locked-in guess for the coming round, or None
forecast_total = 0         # forecasts ever scored
forecast_hits = 0          # of those, how many landed within FORECAST_TOLERANCE
forecast_last = None       # (guess, actual, hit) from the most recent scoring, transient


achievements_open = False


# Unlock toast (TODO.md "roll achievements out everywhere" — required on
# top of the base per-game rollout). Same pattern as every other game's
# reference retrofit: a snapshot of which ids were already earned as of
# the last seed point, so a fresh load or a loaded save doesn't flood the
# player with toasts for achievements it already satisfies.
_achievements_seen_ids = set()

skins_unlocked = set()
current_skin = "default"

archive_open = False

changelog_open = False

community_compare_open = False


climate_scientist_open = False

convoys_sent = 0
convoy_tax_lost = 0.0

balance_bonuses = 0
just_balanced = False

run_over = False
run_result = None  # {"survived": int, "saved": float, "reason": "tipped" | "limit"}
just_escalated = 0  # the escalation level announced by the latest Advance Round, else 0

_compare_option_count = -1

board_sort = "region"
board_descending = False

undo_used = False
_undo_snapshot = None

replay_follow = True  # true while the slider sits at the latest round, so it follows new rounds

_roll_token = 0

pace_best = None  # thaw_pace sets the stored best pace here when it is imported (load_best_pace())


# Names that other modules must reach as runstate.<name> (game.py forwards reads and writes to them).
LIVE_NAMES = (
    "long_game",
    "hold_the_line",
    "temp_unit",
    "worst_case_region_revealed",
    "worst_case_intro_seen",
    "log_filter",
    "log_query",
    "preset_used_ever",
    "custom_preset",
    "confirm_threshold",
    "hard_mode",
    "forecast_miss_total",
    "info_page_open",
    "carbon_bank",
    "crates_delivered",
    "crates_opened",
    "_crate_just_opened",
    "framing",
    "forecast_guess",
    "forecast_total",
    "forecast_hits",
    "forecast_last",
    "achievements_open",
    "_achievements_seen_ids",
    "skins_unlocked",
    "current_skin",
    "archive_open",
    "changelog_open",
    "community_compare_open",
    "climate_scientist_open",
    "convoys_sent",
    "convoy_tax_lost",
    "balance_bonuses",
    "just_balanced",
    "run_over",
    "run_result",
    "just_escalated",
    "_compare_option_count",
    "board_sort",
    "board_descending",
    "undo_used",
    "_undo_snapshot",
    "replay_follow",
    "pace_best",
    "_roll_token",
)
