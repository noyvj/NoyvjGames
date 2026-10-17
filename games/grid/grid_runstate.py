"""The live state of the running game: the module variables that get REPLACED (rebound) while it runs.

THE RULE: a variable that some function reassigns (`state = GridState()`, `career = validate_career(saved)`) lives only here, and
every other module reads and writes it as `runstate.<name>` (each module starts with `import grid_runstate as runstate`).
Never `from grid_runstate import state`: that copies the name once and goes stale the moment the grid is replaced. Lists,
dicts and sets that are only changed in place can stay in the module that owns them.

LIVE_NAMES at the bottom lists every such variable. game.py forwards `game.<name>` reads and writes to this module for
exactly those names (tests use game.state and so on), and the practice sandbox swaps them through vars(runstate). Add a
new rebound variable here AND to LIVE_NAMES. A few start as None because their first value needs code from a later
module; game.py sets them at start-up (see the start-up steps in game.py).
"""

from grid_rules import PREF_DEFAULTS


state = None  # set when game.py starts up (its first value needs code from a later module)


career = None  # set when game.py starts up (its first value needs code from a later module)
# GC-26: records the most recent Finish run broke (empty = none); shown as a
# "New record!" line in the Career panel until the next round is advanced.
last_finish_records = []


prefs = dict(PREF_DEFAULTS)


info_page_open = False


achievements_open = False
summary_panel_open = False


# Unlock toast + hub-dashboard link (TODO.md "roll achievements out
# everywhere" — required on top of the base per-game rollout, per
# ACHIEVEMENTS-SYSTEM-DESIGN.md's site-wide goal). Same pattern as SOL's
# reference retrofit: a snapshot of which ids were already earned as of
# the last seed point, so a fresh load or a loaded save doesn't flood the
# player with toasts for achievements it already satisfies.
_achievements_seen_ids = set()


changelog_open = False


# TODO-C17 -- weather-event log panel, same hidden-until-opened .section
# idiom as the changelog panel just above.
weather_log_open = False


fleet_sort_key = "count"
fleet_sort_reverse = True


confirm_reset_message = ""


slot_attached = None  # index of the slot the live run autosaves into, or None
slot_message = ""


rank_theme_message = ""


career_open = False


career_data_message = ""


_career_view = None


run_setup_message = ""


# C8 -- transient (never saved) "currently showing" flag for the one-time
# 50%-renewable-capacity callout, same reasoning as C20's callouts below:
# state.renewable_50_reached is the persisted "has this ever happened"
# gate, this is just whether it's visible in this session right now.
renewable_milestone_visible = False


# C20 -- transient (never saved) "currently showing" flags for the
# first-use callouts below. state.seen_retire_callout/seen_maintain_callout
# are the persisted "have we ever shown this" gate; these two control
# whether it's visible *right now* in this session, so a loaded save that
# already has the persisted flag set doesn't re-flash the callout on load.
retire_callout_visible = False
maintain_callout_visible = False


shadow_scenario = None   # None = off; otherwise a key of SCENARIOS
shadow_actions = []      # [{"round": int, "kind": "build"|"retire", "type": plant type}]


real_grid_choice = None   # None = off; otherwise a key of REAL_GRIDS


auto_advance_message = ""


_round_animation_token = 0


difficulty_note = ""


sandbox_active = False
_sandbox_real = None


# Every variable above that gets reassigned. game.py forwards game.<name> to this module for exactly these names.
LIVE_NAMES = (
    "state",
    "career",
    "last_finish_records",
    "prefs",
    "info_page_open",
    "achievements_open",
    "summary_panel_open",
    "_achievements_seen_ids",
    "changelog_open",
    "weather_log_open",
    "fleet_sort_key",
    "fleet_sort_reverse",
    "confirm_reset_message",
    "slot_attached",
    "slot_message",
    "rank_theme_message",
    "career_open",
    "career_data_message",
    "_career_view",
    "run_setup_message",
    "renewable_milestone_visible",
    "retire_callout_visible",
    "maintain_callout_visible",
    "shadow_scenario",
    "shadow_actions",
    "real_grid_choice",
    "auto_advance_message",
    "_round_animation_token",
    "difficulty_note",
    "sandbox_active",
    "_sandbox_real",
)
