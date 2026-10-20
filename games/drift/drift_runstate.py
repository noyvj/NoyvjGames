"""The module variables that get REPLACED while the game runs (panel-open flags, notes, filters, the undo snapshots, the neighbouring region, the assist mode and similar).

Other modules read and write them as `runstate.x`, never as a copied name; game.py forwards reads and writes of them."""


# I1/I7: the optional neighbouring region (None until opened) and how much
# support the main region has sent it.
neighbor = None
neighbor_support_sent = 0.0


coda_visible = False

building_pop_count = 0  # transient, never saved: how many pops have run this page load

changelog_open = False


achievements_open = False

# Unlock toast + hub-dashboard link (TODO.md "roll achievements out
# everywhere" — required on top of the base per-game rollout, per
# ACHIEVEMENTS-SYSTEM-DESIGN.md's site-wide goal). Same pattern as
# SOL/Grid/Canopy's own retrofit: a snapshot of which ids were already
# earned as of the last seed point, so a fresh load or a loaded save
# doesn't flood the player with toasts for achievements it already
# satisfies.
_achievements_seen_ids = set()

info_page_open = False

ledger_open = False
ledger_sort = "round_desc"
ledger_filter = "all"

round_start_snapshot = None  # what Reset this round returns to
rewind_snapshot = None  # the state just before the last Advance Round
rewind_armed = False
round_tools_message = ""

collection_open = False
collection_note = ""

# Perfect Fit streak, Crisis Calendar and Surge Tests, Mayor's Council, Budget
# Autopilot, star ratings and the copy-able run summary. See the constants above
# the RegionState class for the rules.
calendar_note_text = ""

council_note_text = ""
summary_note_text = ""

skin_note = ""

template_note = ""

# I-12 / I-16: what the trend graph shows. Display choices only: never saved, back to the defaults on reload.
trend_range = "all"

load_note_text = ""

tier_note_text = ""

assist_mode = "off"
assisted_run = False

confirm_threshold = 0

save_baseline_round = 1
nudge_snooze_round = 0

glossary_open = None
glossary_pinned = False

report_open = False
report_note_text = ""

band_note_text = ""

cross_region_learning = False  # drift_model_region reads the saved browser flag into this when it is imported

skin_choice = None  # drift_collection loads the saved skin choice into this when it is imported

non_visual_mode = False

# Names that other modules must reach as runstate.<name> (game.py forwards reads and writes to them).
LIVE_NAMES = (
    "cross_region_learning",
    "neighbor",
    "neighbor_support_sent",
    "coda_visible",
    "building_pop_count",
    "changelog_open",
    "achievements_open",
    "_achievements_seen_ids",
    "info_page_open",
    "ledger_open",
    "ledger_sort",
    "ledger_filter",
    "round_start_snapshot",
    "rewind_snapshot",
    "rewind_armed",
    "round_tools_message",
    "collection_open",
    "collection_note",
    "calendar_note_text",
    "council_note_text",
    "summary_note_text",
    "skin_choice",
    "skin_note",
    "template_note",
    "trend_range",
    "load_note_text",
    "tier_note_text",
    "assist_mode",
    "assisted_run",
    "confirm_threshold",
    "save_baseline_round",
    "nudge_snooze_round",
    "_last_seen_saved_at",
    "glossary_open",
    "glossary_pinned",
    "report_open",
    "report_note_text",
    "band_note_text",
    "non_visual_mode",
)
