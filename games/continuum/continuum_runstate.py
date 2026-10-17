"""The live state of the running game: the module variables that get REPLACED (rebound) while it runs.

THE RULE: a variable that some function reassigns (`campaign`, `sim_speed`, `views_tab`, the panel open flags ...) lives only here, and every
other module reads and writes it as `runstate.<name>` (each module starts with `import continuum_runstate as runstate`). Never
`from continuum_runstate import state`: that copies the object once and goes stale when the sandbox swaps the settlement. Lists, dicts and
sets that are only changed in place can stay in the module that owns them.

LIVE_NAMES at the bottom lists every such variable. game.py forwards `game.<name>` reads and writes to this module for exactly those
names (tests use game.state, game.sandbox_active and so on), and the practice sandbox swaps them through vars(runstate). Add a new
rebound variable here AND to LIVE_NAMES."""

import time

import challengerun
import research
import save
import sim


campaign = save.Campaign(sim.CityState(), research.build_tree())
# Module-level aliases for the two live engine objects. The save system
# always restores *into* these objects rather than replacing them, so these
# names stay valid across a load.
state = campaign.state
tree = campaign.tree
chronicle = campaign.log

# Milestone 5 — collapsed by default, per the design doc's Core system 6.
# Not one of CITY_FIELDS/tree state, so it rides in campaign.ui instead
# (get_state()/load_state() below), exactly what that save field is for.
info_page_open = False

# Milestone 17 (K14) — the research tree search/filter query. Transient UI
# state, not saved: unlike info_page_open (which rides campaign.ui because
# a toggle's open/closed state is worth restoring on load), a text query
# has no reason to survive a reload, so it's a plain module-level string,
# always "" on a fresh module load. achievements_open (below) is the same
# category — also never saved.
research_search_query = ""

challenge_panel_open = False
_challenge_editor = challengerun.default_config()   # the editor's current dial values (not saved)
_challenge_code_message = ""
_challenge_start_message = ""

timelapse_open = False
_tl_index = 0
_tl_playing = False
_tl_proxy = None

advisors_open = False

_advisors_signature_seen = None

summary_panel_open = False

_archive_confirm_clear = False

_export_status = ""

found_status = ""

founders_log_open = False
_last_tick = time.time()

# The name lives in campaign.ui (naming.py); the input in the Founder's Log
# window is only written to on open, on a suggestion and after a save, never on
# an ordinary render, so it never overwrites what the player is typing.
_name_roll = int(time.time() * 1000) % 100003

minutes_open = False

# A report built on demand from the saved record (postmortem.py); opened from
# a button inside the Civilization Summary and closed from its own button.
# Session-only display state, never saved.
postmortem_open = False

views_panel_open = False
views_tab = "dashboard"

# Nothing here is saved: the ghost lives in memory only, so a reload or a load of another save forgets it,
# and get_state() is unchanged. Python decides what to send and how to draw the comparison.
_peer_ghost = None
_peer_metric = "score"


achievements_open = False

# A snapshot of which achievement ids were already earned as of the last
# seed point, so an action handler's post-render check can tell "newly
# earned by that action" apart from "already earned before this page/save
# load" and only toast for the former. Seeded (never diffed against empty)
# by setup() and load_state() — never by render() itself, since render() is
# also what setup()/load_state() call before seeding — so a save that
# already has several achievements earned never floods the player with a
# toast per achievement the instant it loads.
_achievements_seen_ids = set()

changelog_open = False

# Session-only, like every report_sent flag in champ-de-mots — never rides
# get_state()/load_state(). _info_page_report_era tracks which era the
# "already sent" state applies to, so switching eras (or revisiting an
# earlier one via Look Back) reopens the report rather than permanently
# disabling the button after the first-ever report of a session.
info_page_report_sent = False
_info_page_report_era = None

hamlet_on = False
hamlet_town_open = False
_hamlet_built_key = None   # tuple of station ids the chips were built for

_hamlet_town_key = None    # signature of the town panel's dynamic lists

sim_speed = 0
season_progress = 0.0  # real seconds banked toward the next season, at 1x

_rewind_snapshot = None
dynasty_open = False
doctrines_open = False
citizens_open = False
neighbours_open = False
_dynasty_view = None

_dynasty_status = ""

neighbours_status = ""

# The rules live in orders.py. This is the DOM half: a panel of if/then rows chosen from menus,
# and the one call after each season that lets the council carry them out.
orders_open = False
orders_status = ""

_orders_signature = None

# The rules live in heritage.py. This is the DOM half: a panel listing the sites the settlement has left
# behind, each kept (a culture bonus) or cleared (materials and land now, a culture cost for good).
heritage_open = False
heritage_status = ""
heritage_confirm = None

# The rules live in beyond.py. This is the DOM half: the panel, the ladder kept in localStorage, and the
# one call after each season that scores a Beyond era.
beyond_open = False
beyond_status = ""
_beyond_signature = None

# The rules live in geography.py. This is the DOM half: an opt-in map chosen before the first season (or
# inherited from a consulting case), shown as a grid, with each biome's boon and price in words.
geography_open = False
geography_status = ""

# shared/sandbox-mode.js calls sandbox_enter() / sandbox_leave() / sandbox_is_active() through Pyodide and
# draws the "Sandbox: nothing here is saved" banner. The rules (every discovery known, resources never
# binding, no collapse) are in sandbox.py. The real settlement is never edited: the module-level
# `campaign`, `state`, `tree` and `chronicle` are simply pointed at a separate sandbox campaign, then back.
sandbox_active = False
_sandbox_real = None


# Names that other modules must reach as runstate.<name> (game.py forwards reads and writes to them).
LIVE_NAMES = (
    "campaign",
    "state",
    "tree",
    "chronicle",
    "info_page_open",
    "research_search_query",
    "challenge_panel_open",
    "_challenge_editor",
    "_challenge_code_message",
    "_challenge_start_message",
    "timelapse_open",
    "_tl_index",
    "_tl_playing",
    "_tl_proxy",
    "advisors_open",
    "_advisors_signature_seen",
    "summary_panel_open",
    "_archive_confirm_clear",
    "_export_status",
    "found_status",
    "founders_log_open",
    "_last_tick",
    "_name_roll",
    "minutes_open",
    "postmortem_open",
    "views_panel_open",
    "views_tab",
    "_peer_ghost",
    "_peer_metric",
    "achievements_open",
    "_achievements_seen_ids",
    "changelog_open",
    "info_page_report_sent",
    "_info_page_report_era",
    "hamlet_on",
    "hamlet_town_open",
    "_hamlet_built_key",
    "_hamlet_town_key",
    "sim_speed",
    "season_progress",
    "_rewind_snapshot",
    "dynasty_open",
    "doctrines_open",
    "citizens_open",
    "neighbours_open",
    "_dynasty_view",
    "_dynasty_status",
    "neighbours_status",
    "orders_open",
    "orders_status",
    "_orders_signature",
    "heritage_open",
    "heritage_status",
    "heritage_confirm",
    "beyond_open",
    "beyond_status",
    "_beyond_signature",
    "geography_open",
    "geography_status",
    "sandbox_active",
    "_sandbox_real",
)
