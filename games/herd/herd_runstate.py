"""The live state of the running game: the module variables that get REPLACED (rebound) while it runs.

THE RULE: a variable that some function reassigns (`farm = new_sandbox_farm()`, `generation += 1`) lives only here, and
every other module reads and writes it as `runstate.<name>` (each module starts with `import herd_runstate as runstate`).
Never `from herd_runstate import farm`: that copies the name once and goes stale the moment the farm is replaced. Lists,
dicts and sets that are only changed in place can stay in the module that owns them.

LIVE_NAMES at the bottom lists every such variable. game.py forwards `game.<name>` reads and writes to this module for
exactly those names (tests use game.farm and so on), and the practice sandbox swaps them through vars(runstate). Add a
new rebound variable here AND to LIVE_NAMES. A few start as None because their first value needs code from a later
module; game.py sets them at start-up (see the start-up steps in game.py).
"""

from herd_rules import RULE_SPECS


ranch_rules = {name: spec["default"] for name, spec in RULE_SPECS.items()}


farm = None  # set when game.py starts up (its first value needs code from a later module)


record_coupling_ratio = None  # set when game.py starts up (its first value needs code from a later module)


info_page_open = False


report_card_open = False


achievements_open = False


# Unlock toast (TODO.md "roll achievements out everywhere" — required on
# top of the base per-game rollout). Same pattern as Grid/Canopy's
# reference retrofit: a snapshot of which ids were already earned as of
# the last seed point, so a fresh load or a loaded save doesn't flood the
# player with toasts for achievements it already satisfies.
_achievements_seen_ids = set()


cow_quip_count = 0
cow_bubble_token = 0


changelog_open = False


breeds_collected = []
combos_found = []


# F-17: lever history log with a filter.
lever_history_filter = "all"


# ===========================================================================
# Round-4 batch (planning/TODO.md "GF + F. Herd"): F-19 bulk buying, F-20 round-delta
# chips, GF-18 undo last round, F-21 season calendar, F-22 poultry vs cattle card,
# F-23 breeding rings, GF-13 named cows and hall of fame, F-28 pace note.
# ===========================================================================

# ---- F-19 bulk-buy stepper -------------------------------------------------------------
bulk_mode = 1


# ---- F-20 round-delta chips ------------------------------------------------------------
last_deltas = {}
delta_pinned = set()
delta_faded = False
delta_token = 0


# ---- GF-13 named cows and the hall of fame ----------------------------------------------
hall_of_fame = []  # [name, rounds served, generation], longest first


session_rounds = 0


explain_kind = None  # which breakdown is showing; session only, never saved


plan_steps = []  # [round offset (0 = now), lever key, count]
plan_horizon = 5


ledger_filter = "all"


pinned_stats = None  # set when game.py starts up (its first value needs code from a later module)


# ---- GF-25 feed-additive mixer -------------------------------------------------------------
mixer_message = ""


family_endings = []  # branch ids whose ending has been read, in the order found; survives a handover


generation = 1
legacy_points = 0
legacy_perks = {}


last_round_income = None  # GF-14: the income of the round before, for the "best round" burst


pending_recovery = None  # {"data": dict | None, "problems": [(key, reason)]}, never saved


settings_code_status_text = ""


barns_unlocked = []  # unlocked skin ids other than the default; survives a handover
barn_skin = None  # set when game.py starts up (its first value needs code from a later module)
barn_status_text = ""


golden_cow_status_text = ""


loadouts_unlocked = []  # unlocked loadout ids other than standard; survives a handover
loadout_choice = "standard"  # applied to an untouched farm now and to every later generation
loadout_status_text = ""
_loadout_options_key = ""


sandbox_active = False
_sandbox_real = None


# Every variable above that gets reassigned. game.py forwards game.<name> to this module for exactly these names.
LIVE_NAMES = (
    "ranch_rules",
    "farm",
    "record_coupling_ratio",
    "info_page_open",
    "report_card_open",
    "achievements_open",
    "_achievements_seen_ids",
    "cow_quip_count",
    "cow_bubble_token",
    "changelog_open",
    "breeds_collected",
    "combos_found",
    "lever_history_filter",
    "bulk_mode",
    "last_deltas",
    "delta_pinned",
    "delta_faded",
    "delta_token",
    "hall_of_fame",
    "session_rounds",
    "explain_kind",
    "plan_steps",
    "plan_horizon",
    "ledger_filter",
    "pinned_stats",
    "mixer_message",
    "family_endings",
    "generation",
    "legacy_points",
    "legacy_perks",
    "last_round_income",
    "pending_recovery",
    "settings_code_status_text",
    "barns_unlocked",
    "barn_skin",
    "barn_status_text",
    "golden_cow_status_text",
    "loadouts_unlocked",
    "loadout_choice",
    "loadout_status_text",
    "_loadout_options_key",
    "sandbox_active",
    "_sandbox_real",
)
