"""Herd's numbers and tables: costs, ratios, thresholds, seasons, policy cards and the ranch-rule and audit specs.
Pure data, no behaviour. Ask for this file to change a price, a rate or a threshold.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

STARTING_FUNDS = 300.0
HERD_GROWTH_COST = 20
HERD_INCOME_PER_UNIT = 5

# Coupling: methane emitted per herd unit per round, before any decoupling
# investment. This ratio is the entire lesson — it's what makes "grow the
# farm" and "keep emissions low" pull against each other by default.
BASE_COUPLING_RATIO = 1.0

# Decoupling measures reduce the coupling ratio without requiring herd
# shrinkage — same herd size, lower emissions. Floored so it can never
# hit zero (decoupling is never "free," just much better).
MIN_COUPLING_RATIO = 0.1

DECOUPLING_MEASURES = {
    "feed": {"cost": 15, "ratio_reduction": 0.04, "label": "Feed Additives", "icon": "\U0001F33E"},
    "caps": {"cost": 20, "ratio_reduction": 0.06, "label": "Herd Caps", "icon": "\U0001F404"},
    "capture": {"cost": 20, "ratio_reduction": 0.10, "label": "Capture Systems", "icon": "♻️"},
}

# Soft consequences: sustained methane deterministically eats into income
# via market/regulatory pressure and degraded yields — no hard fail-state,
# no randomness, just an unchecked-growth strategy quietly undercutting
# its own revenue over time.
PRESSURE_SCALE = 100.0
MAX_PRESSURE = 0.8

# Scoring: profitability minus a methane penalty. Rewards decoupling
# specifically — pure growth racks up methane (and the pressure drag that
# comes with it), pure restraint never earns much profit either. Tuned
# (see tests/test_scoring.py) so decoupled growth overtakes pure growth
# within about 10 rounds — a real payoff within a normal play session,
# not a decades-long theoretical one.
METHANE_PENALTY_WEIGHT = 2.0

# Iteration-pass additions: a prominent dial gauge for coupling ratio
# (the mechanic the whole lesson depends on) and an ambient haze overlay
# tracking methane pressure, so the tension is felt, not just read as
# numbers.
GAUGE_LOW_COLOR = "#4c9c6e"  # fully decoupled
GAUGE_HIGH_COLOR = "#e0674c"  # fully coupled (baseline)
MAX_HAZE_OPACITY = 0.4

# Iteration Pass 2 — alternative protein pivot (the fallback path,
# chosen over market dynamics per CLAUDE.md's own conditional: market
# dynamics is an income-side mechanic that can't naturally feed into the
# coupling-ratio gauge, which the design notes require stay the
# centerpiece; the pivot is structurally another decoupling lever, so
# it blends directly into the same gauge feed/caps/capture already use).
# Unlike those three, this changes *what* is produced, not how
# efficiently the same thing is produced.
PLANT_PIVOT_COST = 25
PLANT_PIVOT_FRACTION_PER_UNIT = 0.05
MAX_PLANT_BASED_FRACTION = 0.6
# Plant-based output still carries a small footprint (land use etc.) —
# not literally zero, just far below animal output.
PLANT_BASED_EMISSIONS_MULTIPLIER = 0.05
# Real-world margin difference — a genuine cost, not a strict downgrade,
# since the methane cut this buys also reduces pressure-driven income
# loss elsewhere.
PLANT_BASED_INCOME_MULTIPLIER = 0.85

# F6 (planning/TODO.md) — a rising growth-cost curve instead of a flat
# one. Cost still starts at exactly HERD_GROWTH_COST for the very first
# unit (herd_size == 0), so nothing about the existing flat-cost tests
# for a fresh farm changes; every unit after that gets marginally more
# expensive, reflecting real land/logistics constraints on scaling a herd.
HERD_GROWTH_COST_SLOPE = 2.0

# F15 — the real documented methane-intensity reduction figure cited in
# this game's own Info Page (see INFO_PAGE below and CLAUDE.md), surfaced
# as a live in-game comparison rather than only inside the optional panel.
REAL_WORLD_REDUCTION_FRACTION = 0.42

# F5/F11/F17 — one-time nudge thresholds for the shared milestone-toast
# (distinct from the achievement-unlock toast). Each fires once per
# session the first time its condition is met, mirroring Thaw's
# tipping-flash pattern (a one-tick flag consumed by the next render).
HALF_DECOUPLED_CALLOUT_THRESHOLD = 0.5
PRESSURE_CALLOUT_THRESHOLD = 0.25
METHANE_PENALTY_NUDGE_THRESHOLD = 30.0

# F11 — sustainable certification: holding the coupling ratio at or
# below this level for this many consecutive rounds earns a permanent
# income price premium (the counterfactual baseline never gets it).
CERTIFICATION_RATIO_THRESHOLD = 0.5
CERTIFICATION_ROUNDS_REQUIRED = 5
CERTIFICATION_PRICE_PREMIUM = 0.10

# Achievements — clean_operator's round/pressure bar.
CLEAN_OPERATOR_MIN_ROUND = 15
CLEAN_OPERATOR_MAX_PRESSURE = 0.1

# F29 -- real-world grounding (see planning/FOR-YOU.md): farms do sell captured
# biogas/RNG (and its RIN/LCFS credits). The first CAPTURE_SELF_USE_UNITS of
# capture cover on-farm use; each capture unit beyond that yields saleable gas.
CAPTURE_SELF_USE_UNITS = 2
BIOGAS_SALE_PER_UNIT = 0.05  # funds per herd unit per surplus capture unit

# F23 -- second herd type, unlocked by sustainable certification (this
# game's prestige). Poultry: cheap, low-emission per unit, own levers, own
# housing upkeep. Its emissions are shown as "methane-equivalent" (real
# poultry emissions are mostly manure N2O/ammonia, not enteric methane).
POULTRY_GROW_COST = 12
POULTRY_GROW_SLOPE = 1.0
POULTRY_INCOME_PER_UNIT = 2.5
POULTRY_UPKEEP_PER_UNIT = 0.4
POULTRY_BASE_RATIO = 0.3
MIN_POULTRY_RATIO = 0.05
POULTRY_MEASURES = {
    "litter": {"cost": 12, "ratio_reduction": 0.04, "label": "Litter Management", "icon": "\U0001F33E"},
    "biofilter": {"cost": 15, "ratio_reduction": 0.05, "label": "Ventilation Biofilters", "icon": "\U0001F4A8"},
}

# F1 -- satellite farm ("regional herd network"): a second, smaller, older
# farm the player can open once the main farm is established. It has its own
# coupling ratio (older barns, so it starts dirtier than the main farm), its
# own retrofit lever and a hard size limit. The network effect: the main
# farm's decoupling beyond SATELLITE_OFFSET_FLOOR spills over as shared
# know-how and equipment, cutting the satellite's emissions by
# SATELLITE_OFFSET_RATE per point of that surplus (capped at
# SATELLITE_MAX_OFFSET) -- so investing at home also cleans up the network.
SATELLITE_MIN_MAIN_HERD = 6
SATELLITE_OPEN_COST = 40
SATELLITE_MAX_SIZE = 10
SATELLITE_GROW_COST = 15
SATELLITE_GROW_SLOPE = 1.5
SATELLITE_INCOME_PER_UNIT = 4.0
SATELLITE_BASE_RATIO = 1.2
MIN_SATELLITE_RATIO = 0.15
SATELLITE_RETROFIT_COST = 14
SATELLITE_RETROFIT_REDUCTION = 0.08
SATELLITE_MAX_RETROFITS = 8
SATELLITE_OFFSET_FLOOR = 0.4
SATELLITE_OFFSET_RATE = 1.0
SATELLITE_MAX_OFFSET = 0.5

# F5 -- generational genetics: a slow-burn fourth lever. Each investment
# takes GENETICS_MATURE_ROUNDS rounds to breed through, then permanently
# lowers the ratio.
GENETICS_COST = 30
GENETICS_RATIO_REDUCTION = 0.05
GENETICS_MATURE_ROUNDS = 3

# F13 -- supply chain: downstream processing/distribution, an income lever
# independent of herd growth.
SUPPLY_CHAIN_COST = 30
SUPPLY_CHAIN_BONUS_PER_UNIT = 0.06
SUPPLY_CHAIN_MAX_UNITS = 5

# F15 -- herd welfare: a light second axis. Better feed, caps (less
# crowding) and breeding raise it; above the neutral point it lifts income.
WELFARE_START = 50.0
WELFARE_FEED = 5.0
WELFARE_CAPS = 3.0
WELFARE_GENETICS = 4.0
WELFARE_MAX = 100.0
WELFARE_INCOME_BONUS_MAX = 0.10

# F9/F3 -- opt-in "market & weather variation": deterministic per-round
# income swings (season) plus periodic plant-based demand surges.
SEASONS = [
    ("Drought", -0.10),
    ("Dry spell", -0.05),
    ("Normal season", 0.0),
    ("Good pasture", 0.05),
    ("Bumper season", 0.10),
]
DEMAND_SURGE_PLANT_INCOME_MULTIPLIER = 1.05

# F19 -- opt-in regional methane cap: growth that would push per-round
# methane past the cap is blocked, forcing decoupling.
REGIONAL_CAP = 20.0

# F27 -- policy advisor: every POLICY_EVENT_INTERVAL rounds, choose between
# a decoupling subsidy and a flat cash bonus.
POLICY_EVENT_INTERVAL = 8
POLICY_SUBSIDY_DISCOUNT = 0.30
POLICY_SUBSIDY_ROUNDS = 5
POLICY_CASH_BONUS = 40

# F-9 -- the policy advisor draws its two offers from a pool of six options, without repeats
# until the pool has been used, in a fixed order (no luck). Each option has a plain real-world tag
# (a kind of scheme that exists, with no figures) shown next to it and in the advisor history.
POLICY_ORDER = ["subsidy", "cash", "carbon_credit", "feed_hedge", "organic_trial", "welfare_grant"]
POLICY_OPTIONS = {
    "subsidy": {
        "label": "Decoupling subsidy", "tag": "Subsidy programme",
        "blurb": f"{POLICY_SUBSIDY_DISCOUNT * 100:.0f}% off every decoupling lever for {POLICY_SUBSIDY_ROUNDS} rounds",
        "real": "Real-world idea: public programmes that help pay for methane-reduction equipment on farms.",
    },
    "cash": {
        "label": "Cash bonus", "tag": "Direct payment", "blurb": f"{POLICY_CASH_BONUS} funds now",
        "real": "Real-world idea: direct payments to farmers.",
    },
    "carbon_credit": {
        "label": "Carbon-credit contract", "tag": "Carbon market",
        "blurb": "funds now, more the further you are below baseline emissions",
        "real": "Real-world idea: voluntary carbon-credit contracts that pay a farm for emission cuts that are checked.",
    },
    "feed_hedge": {
        "label": "Feed-price hedge", "tag": "Price hedge", "blurb": "Feed Additives half price for 6 rounds",
        "real": "Real-world idea: forward contracts that fix a feed price in advance.",
    },
    "organic_trial": {
        "label": "Organic label trial", "tag": "Eco-label", "blurb": "+8% herd income for 4 rounds",
        "real": "Real-world idea: eco-labels that let a farm sell at a small premium while it is certified.",
    },
    "welfare_grant": {
        "label": "Welfare grant", "tag": "Welfare payment",
        "blurb": "funds now, more the higher your herd welfare is above 50",
        "real": "Real-world idea: payments that reward higher animal-welfare standards.",
    },
}
POLICY_HEDGE_DISCOUNT = 0.5
POLICY_HEDGE_ROUNDS = 6
POLICY_LABEL_BONUS = 0.08
POLICY_LABEL_ROUNDS = 4
POLICY_CARBON_BASE = 20
POLICY_CARBON_PER_DECOUPLED = 80
POLICY_WELFARE_BASE = 10
POLICY_WELFARE_PER_POINT = 1.2
POLICY_HISTORY_MAX = 40

# GF-25 -- the optional feed-additive mixer: a short click-timing blend (the page's JS handles the bar)
# that pays a small bonus, at most MIXER_BONUS_FRACTION of the funds in hand (and never more than
# MIXER_BONUS_MAX), once per round. The auto-blend button pays MIXER_AUTO_QUALITY of that, so nobody
# has to play it. Needs one Feed Additives unit.
MIXER_BONUS_FRACTION = 0.05
MIXER_BONUS_MAX = 40.0
MIXER_AUTO_QUALITY = 0.5
MIXER_PERFECT_QUALITY = 0.9
MIXER_MIN_QUALITY = 0.2  # a timed blend always pays a little, so a miss is never wasted


# GF-15 -- perfect-round streak: a round is "perfect" when the methane it added
# fell below the previous round's AND funds ended the round higher than they ended
# the round before (so spending on decoupling still paid for itself). Streaks pay a
# small one-off bonus to the real farm (never the baseline) at these lengths.
PERFECT_STREAK_BONUSES = {3: 10, 5: 20, 10: 40}

# F-17 -- lever history: every purchase is logged (round, lever key, cost paid) and
# the log is capped so a very long game cannot grow the save without bound.
LEVER_LOG_MAX = 300
LEVER_LABELS = {
    "herd": "Grow Herd",
    "feed": "Feed Additives",
    "caps": "Herd Caps",
    "capture": "Capture Systems",
    "pivot": "Plant-Based Pivot",
    "genetics": "Breeding Program",
    "supply": "Processing & Distribution",
    "poultry": "Grow Flock",
    "litter": "Litter Management",
    "biofilter": "Ventilation Biofilters",
    "satellite_open": "Open Satellite Farm",
    "satellite_grow": "Grow Satellite Herd",
    "satellite_retrofit": "Retrofit Barns",
}

# F-19 -- bulk buying: Grow Herd and the three decoupling levers can be bought in steps
# of 1, 5 or as many as the funds (and the regional cap) allow, capped at BULK_MAX_UNITS
# so one click can never loop for long.
BULK_MODES = (1, 5, "max")
BULK_MAX_UNITS = 50

# GF-18 -- undo the last round: once per game, and it costs funds.
UNDO_PENALTY_FUNDS = 25

# F-20 -- round-delta chips: shown after Advance Round, fade after a few seconds unless pinned.
DELTA_KEYS = ("funds", "methane", "welfare", "pressure")
DELTA_FADE_MS = 6000

# F-28 -- a discreet pace note, and a save-and-rest nudge every this many rounds in one sitting.
SAVE_NUDGE_EVERY = 10

# GF-13 -- every herd unit has a name (fixed by its position in the herd and the generation,
# never random, so the names are the same after a reload). Longest-serving units of a
# retired generation go to the hall of fame.
COW_NAMES = [
    "Beyonmoo", "Sir Grazealot", "Moolan Rouge", "Udder Chaos", "Cowlin Farrell", "Hay Z",
    "Clover Kent", "Bovine Jovi", "Lady Gagraze", "Moo Thurman", "Dolly Pasture", "Count Chewcula",
    "Mootilda", "Grassy Elliott", "Marie Cowrie", "Buttercup Cumberbatch", "Hoofy Mercury",
    "Curd Vader", "Ruminate Rosie", "Daisy Ridley", "Cud Norris", "Flossie Nightingale",
    "Moomin", "Bessie Smith",
]
HALL_OF_FAME_SIZE = 5
HALL_PER_HANDOVER = 3


# F-1 -- Ranch Rules: four balance sliders for a custom run. Standard values are the ones the rest of
# the file is written around, so a farm on standard rules behaves exactly as it always has. Any other
# value makes the run "unranked": it stays off the opt-in leaderboard and out of the other-farms
# comparison (FY-32). Rules live outside `farm` (like the succession perks) so a handover keeps them.
RULE_SPECS = {
    "starting_funds": {"label": "Starting funds", "min": 150, "max": 600, "step": 50, "default": 300, "unit": ""},
    "season_swing": {"label": "Season swing", "min": 0, "max": 200, "step": 50, "default": 100, "unit": "%"},
    "pressure_strength": {"label": "Pressure penalty", "min": 50, "max": 200, "step": 25, "default": 100, "unit": "%"},
    "growth_slope": {"label": "Growth-cost slope", "min": 0, "max": 4, "step": 0.5, "default": 2.0, "unit": ""},
}
RULES_STORAGE_KEY = "herd-ranch-rules"


# GF-3 -- regulator audits. Every AUDIT_EVERY rounds, at the end of the round, an inspector checks two
# visible targets (coupling ratio low enough, welfare high enough). The targets are shown from round 1
# and rise with each audit (to 0.60 and 60). Passing earns a permanent perk for this farm; failing
# costs a fine and a short market-trust hit. Deterministic: no luck, and the baseline farm is untouched.
AUDIT_EVERY = 10
AUDIT_WARNING_ROUNDS = 3
AUDIT_LOG_MAX = 10
AUDIT_FINE_INCOME_ROUNDS = 1.0  # a fine is this many rounds of income (so a farm earning nothing owes nothing)
AUDIT_TRUST_ROUNDS = 3
AUDIT_TRUST_PENALTY = 0.05
AUDIT_GOODWILL_BONUS = 0.03
AUDIT_PERK_REPEAT_FUNDS = 40
AUDIT_PERKS = [
    {"id": "goodwill", "label": "Regulator's Goodwill", "blurb": "+3% farm income, for good."},
    {"id": "green_loan", "label": "Green Loan Terms", "blurb": "Feed Additives, Herd Caps and Capture Systems cost 1 less."},
    {"id": "friendly_inspector", "label": "Friendly Inspector", "blurb": "A failed audit costs half the fine and half the trust hit."},
]
