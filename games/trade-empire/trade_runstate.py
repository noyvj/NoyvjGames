"""The live state of the running game: the module variables that get REPLACED (rebound) while it runs.

THE RULE: a variable that some function reassigns (`total_profit += ...`, `guild_state = "offered"`) lives only here, and every
other module reads and writes it as `runstate.<name>` (each module starts with `import trade_runstate as runstate`). Never
`from trade_runstate import total_profit`: that copies the value once and goes stale at the next change. Lists, dicts and sets
that are only changed in place can stay in the module that owns them.

LIVE_NAMES at the bottom lists every such variable. game.py forwards `game.<name>` reads and writes to this module for exactly
those names (tests use game.total_profit, game.run_seed and so on). Add a new rebound variable here AND to LIVE_NAMES."""


seasonal_demand_enabled = False
season_ticks = 0

cross_system_units = 0

route_hazards_enabled = False
route_insurance_enabled = False
disruptions_suffered = 0
insurance_payouts = 0
premiums_paid = 0

run_seed = ""  # made on first need (current_run_seed)
run_seed_pinned = False  # True once the player typed one (or a save carried one)
run_seed_message = ""
hazard_rolls = 0  # how many hazard rolls the run has made (the stream position)
guild_offers = 0  # how many guild offers the run has made

# Milestone 12 — fleet-level automation: off by default, so Milestone 6's
# per-route autopilot behavior (and every test written against it) is
# preserved exactly when the mode isn't switched on. When it is, an idle
# automated ship stops blindly reloading its local produce and instead
# checks whether the fleet's most under-served colony is fed by a
# *different* producer — if so, it repositions there empty to help,
# rather than staying tethered to its original A<->B shuttle forever.
fleet_priority_enabled = False

research_points = 0.0
unlocked_research = set()

total_profit = 0
sale_log = []  # most recent sale message, for the status line

# New tracked state for achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md §4):
# each of these tracks something that genuinely *happened*, which isn't
# recoverable from state that only reflects the current moment (e.g.
# total_profit can go back down after an automation purchase, so it can't
# tell you the highest it's ever been).
total_sales_count = 0
max_profit_ever = 0
goods_sold_ever = set()
ever_repositioned = False

captain_earned = set()  # ship ids that reached veteran status this charter

captains_met = set()  # captains ever posted, across every charter

endgame_reached = False
ticks_since_endgame = 0

guild_state = "none"

guild_completed = 0
guild_failed = 0

legacy_level = 0
legacy_achievements = []  # ids earned by earlier corporations, carried over
_fresh_state = None  # get_state() of a brand-new game, captured before setup()

founding_seed = 0  # 0 = the standard first charter

charters_completed = 0
charter_points_earned = 0
charter_perks = set()
hard_charter_active = False  # this charter was begun as a harder charter
hard_charter_next = False  # the player's pending choice for the next renewal
# O-3 -- lifetime ledger. Totals persist across renewals (found_new_corporation
# carries them over the reset); ledger_routes_seen is the current charter's
# set of distinct routes, so a route counts once per charter.
ledger_units_moved = 0
ledger_routes_established = 0
ledger_hard_completed = 0
ledger_routes_seen = set()
# J-14 -- units delivered in the CURRENT charter (the ledger above is
# lifetime), and the career log: one entry per completed charter, newest last.
ledger_charter_units = 0
charter_career = []


_galaxy_hover_wired = False

changelog_open = False


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

_notice_hide_proxy_gen = 0

summary_open = False

charter_open = False

captains_open = False

blackout_enabled = False
blackout_clean = False  # on since before the first sale of this charter and never switched off
blackout_done = False  # this charter reached the endgame on an unbroken Blackout

weather_enabled = False
weather_n = 0  # events generated so far in this charter (the hash input)
weather_event = None  # {"good", "kind", "style", "wait", "left", "dur"} or None
_weather_ticker_text = None

expedition = None  # {"ship": ship id, "left": ticks} while one is away
expedition_log = ""  # the last result, shown in the Fleet Lab

lab_open = False

desk_open = False

hub_colony = None

meridian_enabled = False
meridian_ticks = 0  # the rival's clock; only runs while the mode is on
meridian_contest = None  # {"good", "left"} while it is contesting a good
meridian_shield = None  # {"good", "left"} a good it will not contest for a while
meridian_units = 0  # units it has moved in the current cycle
meridian_intel_bought = False

crisis_active = None  # the crisis id while one is being played (it runs inside the sandbox machinery)
crisis_ticks = 0
crisis_done = None  # {"medal", "ticks"} once solved this run

chain_open = False  # the Chain Builder window
chain_active = None  # the puzzle id while one is being played (it runs inside the sandbox machinery)
chain_plan = []  # per product: {"sites": [site id or None] * stages, "ships": [ships] * stages}
chain_tab = 0  # which product the map clicks fill
chain_hint_rung = 0  # suggestions revealed so far (0-3); the next press may place the par chain
chain_done = None  # {"medal", "units", "ships", "improved"} for the chain last locked in this run


_chain_rendered_sig = None
_chain_options_for = None

_chain_levels = None

_modes_screen = None
_modes_rendered_sig = None

sandbox_active = False
_sandbox_real = None

captain_assignments = {}  # trade_captains fills it (one 0 per captain perk) when it is imported

guild_cooldown = 0  # trade_guild sets the first-offer wait when it is imported


# Names that other modules must reach as runstate.<name> (game.py forwards reads and writes to them).
LIVE_NAMES = (
    "seasonal_demand_enabled",
    "season_ticks",
    "cross_system_units",
    "route_hazards_enabled",
    "route_insurance_enabled",
    "disruptions_suffered",
    "insurance_payouts",
    "premiums_paid",
    "run_seed",
    "run_seed_pinned",
    "run_seed_message",
    "hazard_rolls",
    "guild_offers",
    "fleet_priority_enabled",
    "research_points",
    "unlocked_research",
    "total_profit",
    "sale_log",
    "total_sales_count",
    "max_profit_ever",
    "goods_sold_ever",
    "ever_repositioned",
    "captain_earned",
    "captain_assignments",
    "captains_met",
    "endgame_reached",
    "ticks_since_endgame",
    "guild_state",
    "guild_cooldown",
    "guild_completed",
    "guild_failed",
    "legacy_level",
    "legacy_achievements",
    "_fresh_state",
    "founding_seed",
    "charters_completed",
    "charter_points_earned",
    "charter_perks",
    "hard_charter_active",
    "hard_charter_next",
    "ledger_units_moved",
    "ledger_routes_established",
    "ledger_hard_completed",
    "ledger_routes_seen",
    "ledger_charter_units",
    "charter_career",
    "_galaxy_hover_wired",
    "changelog_open",
    "achievements_open",
    "_previously_earned_ids",
    "_toast_hide_proxy_gen",
    "_notice_hide_proxy_gen",
    "summary_open",
    "charter_open",
    "captains_open",
    "blackout_enabled",
    "blackout_clean",
    "blackout_done",
    "weather_enabled",
    "weather_n",
    "weather_event",
    "_weather_ticker_text",
    "expedition",
    "expedition_log",
    "lab_open",
    "desk_open",
    "hub_colony",
    "meridian_enabled",
    "meridian_ticks",
    "meridian_contest",
    "meridian_shield",
    "meridian_units",
    "meridian_intel_bought",
    "crisis_active",
    "crisis_ticks",
    "crisis_done",
    "chain_open",
    "chain_active",
    "chain_plan",
    "chain_tab",
    "chain_hint_rung",
    "chain_done",
    "_chain_rendered_sig",
    "_chain_options_for",
    "_chain_levels",
    "_modes_screen",
    "_modes_rendered_sig",
    "sandbox_active",
    "_sandbox_real",
)
