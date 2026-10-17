"""Fixed numbers and content tables for the core rules: grid sizes, difficulty, plot states, seasons, the Forest Lab numbers, maturity, stakeholder and specialist constants, tree species, neighbour synergy. No browser calls."""

import canopy_runstate as runstate


# B13 (planning/TODO.md "Per-game: Canopy"): a larger-grid option as a
# difficulty/length variant, selectable via reset_session() below. GRID_ROWS/
# GRID_COLS are deliberately mutable module globals rather than true
# constants -- a size change rebuilds `plots` at the new dimensions.
# "normal" (6x6 = 36) stays the default at import time so every existing
# test/tutorial reference to "36 plots" is unaffected unless a player (or a
# loaded save) explicitly picks "large" (9x8 = 72, double the plot count for
# a longer session). GRID_COLS stays under 26 for both presets so
# plot_coordinate_label()'s A..Z column-letter scheme never needs to wrap.
GRID_SIZE_PRESETS = {
    "small": (4, 4),
    "normal": (6, 6),
    "large": (9, 8),
}

runstate.GRID_ROWS, runstate.GRID_COLS = GRID_SIZE_PRESETS[runstate.current_grid_size]
TICK_INTERVAL_MS = 1000

# Standing value accrued per tick at ticks_intact == 0 is BASE_ACCRUAL *
# (1 + GROWTH_PER_TICK); the multiplier itself grows every subsequent tick,
# so patience is rewarded increasingly rather than at a flat rate.
BASE_ACCRUAL = 1.0
GROWTH_PER_TICK = 0.05

# Soil degradation: each clear on a given plot permanently lowers that
# plot's future productivity. Never fully to zero — a plot always keeps
# some minimum ability to regrow, matching the site's "no dead-end states"
# philosophy.
DEGRADE_PER_CLEAR = 0.1
MIN_PRODUCTIVITY_MULTIPLIER = 0.2

# B7: "forest ranger" harder difficulty -- each clear degrades soil twice as
# steeply. A session-wide setting (changing it resets the session, exactly
# like a grid-size change, since soil quality is derived from clear_count
# and would otherwise silently rewrite every plot's history).
DIFFICULTY_NORMAL = "normal"
DIFFICULTY_RANGER = "ranger"
DIFFICULTY_WILDFIRE = "wildfire"  # GB-1: normal soil damage plus a summer and autumn fire season
DIFFICULTY_RIVAL = "rival"  # GB-12: normal soil damage plus Halloran Timber Co. bidding on edge plots
DEGRADE_PER_CLEAR_BY_DIFFICULTY = {
    DIFFICULTY_NORMAL: DEGRADE_PER_CLEAR,
    DIFFICULTY_RANGER: DEGRADE_PER_CLEAR * 2,
    DIFFICULTY_WILDFIRE: DEGRADE_PER_CLEAR,
    DIFFICULTY_RIVAL: DEGRADE_PER_CLEAR,
}
runstate.current_difficulty = DIFFICULTY_NORMAL


# How many ticks a replanted plot spends in REPLANTING before it
# automatically becomes RECOVERED. A never-cleared plot pays no such
# delay — this is the "slower timeline" the plan calls for.
RECOVERY_TICKS = 10

PRESERVED = "preserved"
BARE = "bare"
REPLANTING = "replanting"
RECOVERED = "recovered"

STATE_LABEL = {
    PRESERVED: "Preserved",
    BARE: "Bare",
    REPLANTING: "Replanting",
    RECOVERED: "Recovered",
}

# Icons ride alongside color so plot state doesn't rely on color alone —
# a small accessibility/legibility pass, not just decoration. B9
# (colorblind-safety, planning/ACHIEVEMENTS... no, planning/TODO.md's
# per-game Canopy section) closed the one gap here: BARE previously had no
# icon at all, meaning it depended on hue alone to read as distinct from a
# young REPLANTING/PRESERVED tile -- see style.css's `.plot-tile.plot-*`
# pattern overlays (also new this pass) for the second, independent
# redundant-coding channel per the Okabe-Ito-audit method (see
# games/continuum/CLAUDE.md's colorblind-safety-audit note for the
# worked example this follows).
STATE_ICON = {
    PRESERVED: "\U0001F332",  # evergreen tree
    BARE: "\U0001FAB5",  # wood log -- was previously blank (hue-only)
    REPLANTING: "\U0001F331",  # seedling
    RECOVERED: "\U0001F333",  # deciduous tree
}

# Which of the two actions are valid from each state. Preserve isn't a
# click action — a PRESERVED/RECOVERED plot accrues passive value simply
# by being left alone (see the plan's "preserve = do nothing" framing).
VALID_ACTIONS = {
    PRESERVED: {"clear"},
    RECOVERED: {"clear"},
    BARE: {"replant"},
    REPLANTING: set(),
}

# States in which a plot accrues standing value each tick.
ACCRUING_STATES = {PRESERVED, RECOVERED}


# B17 (planning/TODO.md "Per-game: Canopy"): a genuine in-game seasonal
# cycle -- distinct from B30's purely decorative real-calendar backdrop
# tint (settings.js's `data-season`, which never touches game math). This
# one is driven by `forest_tick`, a persisted counter (unlike the
# ephemeral `_session_ticks`), so a season boundary survives a save/load
# exactly like any other real game fact instead of resetting on reload.
# Each season applies a modest permanent multiplier to a plot's per-tick
# ECONOMIC growth only -- biodiversity accrual is deliberately untouched,
# so Pass 3's already-tuned wildlife-icon pacing doesn't shift underneath
# a season change.
SEASON_CYCLE_TICKS = 40
SEASONS = ["spring", "summer", "autumn", "winter"]
SEASON_GROWTH_MULTIPLIER = {"spring": 1.10, "summer": 1.00, "autumn": 0.95, "winter": 0.85}
SEASON_ICON = {"spring": "\U0001F331", "summer": "☀️", "autumn": "\U0001F342", "winter": "❄️"}
SEASON_LABEL = {"spring": "Spring", "summer": "Summer", "autumn": "Autumn", "winter": "Winter"}


def current_season():
    return SEASONS[(runstate.forest_tick // SEASON_CYCLE_TICKS) % len(SEASONS)]


def current_season_multiplier():
    return season_multiplier_for(current_season())


# B-5 (2026-10-09): Forest Lab. Four sandbox dials (1.0 is the normal game). They are applied through these helpers, so
# the counterfactual and the projection use the same numbers as the real forest.
LAB_KEYS = ("soil", "maturity", "requests", "season")
LAB_MIN, LAB_MAX, LAB_STEP = 0.5, 2.0, 0.25
lab = {key: 1.0 for key in LAB_KEYS}


def lab_active():
    return any(abs(value - 1.0) > 1e-9 for value in lab.values())


def growth_per_tick():
    return GROWTH_PER_TICK * lab["maturity"]


def season_multiplier_for(season):
    """The season's growth multiplier with the Lab's season strength applied to its distance from 1.0."""
    base = SEASON_GROWTH_MULTIPLIER[season]
    return max(0.1, 1.0 + (base - 1.0) * lab["season"])


def ticks_until_next_season():
    return SEASON_CYCLE_TICKS - (runstate.forest_tick % SEASON_CYCLE_TICKS)


# Iteration-pass additions: a continuous color gradient per plot (not
# just one flat color per discrete state) so maturity/recovery progress
# is legible at a glance, plus a one-tick "just recovered" flash so the
# REPLANTING -> RECOVERED transition registers as a felt moment.
MATURITY_TICKS = 60

# Iteration Pass 2 — biodiversity sub-meter: a slower, flat (non-
# compounding) accrual separate from economic value, so a long-standing
# plot visibly "has life in it" beyond just being worth more. Represented
# via a wildlife icon once a plot crosses the threshold, not a number to
# read.
#
# Iteration Pass 3 (fun/teaching balance) — threshold lowered from the
# original 1.0 (a 50-tick wait for the first icon) to 0.2 (~10 ticks).
# The old pacing meant the first felt "something is alive here" payoff
# landed well after two stakeholder-tension cycles had already fired,
# leaving the early game's only real beat as a repeat of the same
# decision. Pulling this forward gives players a distinct payoff moment
# inside the first idle stretch instead of after it.
BIODIVERSITY_ACCRUAL_PER_TICK = 0.02
BIODIVERSITY_WILDLIFE_THRESHOLD = 0.2
# The wildlife icon itself is rendered purely via CSS (`.plot-has-wildlife
# ::after`'s content, style.css) once has_wildlife() adds that class — not
# read from a Python-side constant, so none is declared here.

# Iteration Pass 2 — stakeholder tension: periodically, the community
# asks to clear the single most-established standing plot for a stated
# real need. Deliberately not a trap: granting clears the plot (same
# payout as a normal Clear) and nudges community relations up; declining
# keeps the plot standing and nudges relations down a smaller amount —
# neither choice is free, neither is catastrophic, matching the site's
# no-dead-end-states philosophy. Reason cycles deterministically rather
# than by RNG, since nothing else in this game uses randomness.
#
# Iteration Pass 3 (fun/teaching balance) — interval tightened from 20
# ticks to 15. Grant/decline was already the game's clearest skill-bearing
# beat (it forces weighing relations against banking value before the
# community claims your best plot), so making it recur a bit sooner keeps
# the challenge curve paced against a session's growing plot count instead
# of leaving long unbroken waits between it.
STAKEHOLDER_EVENT_INTERVAL_TICKS = 15
STAKEHOLDER_REASONS = ["housing", "farming", "resources"]
STAKEHOLDER_REASON_TEXT = {
    "housing": "the community is asking to clear it for new housing — people need somewhere to live too",
    "farming": "a local family wants to farm it for food security this season",
    "resources": "the community needs timber from it for winter building repairs",
}
STAKEHOLDER_GRANT_RELATIONS_DELTA = 10
STAKEHOLDER_DECLINE_RELATIONS_DELTA = -5
STARTING_COMMUNITY_RELATIONS = 50

# B11 (planning/TODO.md "Per-game: Canopy"): diversify stakeholder requests
# to sometimes offer a positive trade-off instead of only "give up this
# plot or don't." An "incentive" request never asks the player to clear
# anything -- accepting keeps the named plot standing untouched and pays a
# funding bonus + relations boost; declining costs nothing (turning down a
# gift isn't the same as refusing the community's ask for the plot
# itself). Cycles in after every full pass through STAKEHOLDER_REASONS
# (see maybe_trigger_stakeholder_request()) so the original 3-reason
# "clear" cycle finishes before the first incentive ever appears --
# preserves test_stakeholder_reason_cycles_deterministically's exact
# first-3-requests expectation unchanged.
STAKEHOLDER_KIND_CLEAR = "clear"
STAKEHOLDER_KIND_INCENTIVE = "incentive"
STAKEHOLDER_REQUEST_CYCLE_LENGTH = len(STAKEHOLDER_REASONS) + 1  # 3 clear requests, then 1 incentive
STAKEHOLDER_INCENTIVE_REASONS = ["ecotourism", "conservation_grant", "carbon_credit"]
STAKEHOLDER_INCENTIVE_REASON_TEXT = {
    "ecotourism": "a nearby eco-tourism operator wants to feature it on their nature trail if it stays standing",
    "conservation_grant": "a conservation program is offering a small grant to keep it standing",
    "carbon_credit": "a carbon-credit buyer wants to certify it as protected forest",
}
STAKEHOLDER_INCENTIVE_ACCEPT_RELATIONS_DELTA = 10
STAKEHOLDER_INCENTIVE_INCOME_BONUS = 25.0
VETERAN_REQUESTS_SURVIVED = 3  # B22

# B25: an occasional "community grant" -- a fund offers money specifically
# for replanting a bare plot. Rides the incentive slot of the request cycle:
# every second incentive turn (the 8th, 16th, ... request), if any plot is
# bare, the incentive is a replant grant instead. Accepting replants the
# offered plot and pays the grant; declining costs nothing.
STAKEHOLDER_KIND_REPLANT_GRANT = "replant_grant"
REPLANT_GRANT_INCOME_BONUS = 15.0
REPLANT_GRANT_RELATIONS_DELTA = 5


# B21: a plot left standing SPECIALIST_MIN_TICKS_INTACT ticks can be given a
# one-time, permanent specialization. Economic: +25% standing-value accrual.
# Biodiversity: 2.5x biodiversity accrual. Not reversible, and lost with the
# plot if it is ever cleared (clear() resets it).
SPECIALIST_MIN_TICKS_INTACT = 90
SPECIALIZATION_ECONOMIC = "economic"
SPECIALIZATION_BIODIVERSITY = "biodiversity"
SPECIALIST_ECONOMIC_VALUE_MULTIPLIER = 1.25
SPECIALIST_BIODIVERSITY_MULTIPLIER = 2.5
SPECIALIZATION_LABEL = {SPECIALIZATION_ECONOMIC: "economic", SPECIALIZATION_BIODIVERSITY: "biodiversity"}


# B11 (planning/TODO.md "Per-game: Canopy"): a "reforestation partner" --
# an alternate way to replant a Bare plot. (Note: an EARLIER B11 --
# diversifying stakeholder requests with a positive "incentive" offer --
# is what the STAKEHOLDER_KIND_INCENTIVE comments above still reference;
# TODO.md was renumbered after that shipped, and this is the *current*
# B11.) Canopy has no separate resource currency for a partner to
# literally "co-fund", so the trade this offers is time for a permanent
# cut of value instead: the partner halves the recovery wait, in exchange
# for a fixed share of that one planting's future ECONOMIC value (never
# biodiversity). The deal is void the moment the plot is next cleared --
# a fresh partnership has to be struck on the next bare replant.
PARTNER_RECOVERY_TICKS = max(1, RECOVERY_TICKS // 2)
PARTNER_SHARE_RATIO = 0.35


# GB-6 (2026-10-09): tree species chosen when replanting. "standard" is the original seedling (no change to the rules).
# Pine recovers fast but tops out low, oak is slow but rich in value and wildlife, an orchard pays steadily but
# attracts no wildlife. A forest mixing species grows a little faster (see mixed_forest_multiplier).
SPECIES_STANDARD = "standard"
SPECIES_MANGROVE = "mangrove"  # GB-24: planted only in the Wetland Forest, only while a plot is flooded
SPECIES = {
    "standard": {"label": "Standard seedling", "mark": "", "recovery": 1.0, "value": 1.0, "bio": 1.0, "steady_after": None,
                 "note": "the usual seedling"},
    "pine": {"label": "Pioneer pine", "mark": "\u25b2", "recovery": 0.5, "value": 0.75, "bio": 1.0, "steady_after": None,
             "note": "recovers in half the time, lower ceiling (-25% value)"},
    "oak": {"label": "Hardwood oak", "mark": "\u25cf", "recovery": 2.0, "value": 1.35, "bio": 1.5, "steady_after": None,
            "note": "twice the wait, +35% value and +50% biodiversity"},
    "mangrove": {"label": "Mangrove", "mark": "\u2237", "recovery": 0.6, "value": 1.1, "bio": 1.4, "steady_after": None,
                 "note": "wetland only, planted while the plot is under water: recovers fast and floods cannot harm it"},
    "orchard": {"label": "Orchard", "mark": "\u25c6", "recovery": 1.0, "value": 1.0, "bio": 0.0, "steady_after": 30,
                "note": "steady income (stops compounding after 30 ticks), no wildlife"},
}
MIXED_FOREST_BONUS_PER_EXTRA_SPECIES = 0.05
species_planted = set()  # which species this forest has planted (for the Almanac); saved only when non-empty


def species_recovery_ticks(species, base):
    return max(1, int(round(base * SPECIES.get(species, SPECIES[SPECIES_STANDARD])["recovery"])))


def mixed_forest_multiplier(plot_list=None):
    """+5% growth for each distinct chosen species standing beyond the first (so +10% with all three)."""
    standing = {p.species for p in (runstate.plots if plot_list is None else plot_list) if p.state in ACCRUING_STATES and p.species}
    return 1.0 + MIXED_FOREST_BONUS_PER_EXTRA_SPECIES * max(0, len(standing) - 1)


# GB-5 (2026-10-09): neighbour synergy. A mature standing plot grows SYNERGY_PER_NEIGHBOUR faster for each of its (up to four)
# edge-sharing neighbours that is also mature, and a plot replanted next to a mature one recovers SYNERGY_REPLANT_FACTOR
# as long. Main forest only. Solid blocks pay, checkerboards do not, and a cleared "farm edge" beside a protected core
# replants quickly. The counterfactual "left standing" line does not model this bonus.
SYNERGY_PER_NEIGHBOUR = 0.04
SYNERGY_REPLANT_FACTOR = 0.8
UI_PREF_SYNERGY_MARKS_OFF = "canopy-synergy-marks-off"  # hides only the +link marks, never the bonus


def _is_mature_standing(plot):
    return plot.state in ACCRUING_STATES and plot.ticks_intact >= MATURITY_TICKS


def _edge_neighbours(index, cols=None):
    cols = runstate.GRID_COLS if cols is None else cols
    row, col = divmod(index, cols)
    out = []
    for nr, nc in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
        if nr >= 0 and 0 <= nc < cols:
            out.append(nr * cols + nc)
    return out


def mature_neighbour_count(plot):
    if plot.region != "main":
        return 0
    return sum(1 for i in _edge_neighbours(plot.index) if i < len(runstate.plots) and runstate.plots[i].region == "main" and _is_mature_standing(runstate.plots[i]))


def synergy_multiplier(plot):
    """1.0 for a plot that is not mature or has no mature neighbour."""
    if plot.region != "main" or not _is_mature_standing(plot):
        return 1.0
    return 1.0 + SYNERGY_PER_NEIGHBOUR * mature_neighbour_count(plot)


runstate.community_relations = STARTING_COMMUNITY_RELATIONS

runstate.community_relations_min_ever = STARTING_COMMUNITY_RELATIONS  # lowest community_relations has ever been

CARBON_SLUMP_MULTIPLIER = 0.9

carbon = {"credits": 0.0, "slump": 0, "sold": 0.0, "earned_from_sales": 0.0}

CLEAR_CUT_DIP = 0.30
CLEAR_CUT_HEAL_TICKS = 3 * SEASON_CYCLE_TICKS

# B-11 (2026-10-09): scenario seeds: pre-made starting forests picked at session start, each with its own
# best standing value. They only change which plots start bare, so they reuse the ordinary plot save format.
SCENARIO_NONE = "none"

expedition_meta = {"best": {}, "finished": 0, "last_seed": ""}  # per browser: best score per seed, runs finished
