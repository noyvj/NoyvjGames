"""Fixed numbers and content tables (costs, thresholds, tiers, titles, stances, storage keys): no browser calls, no state."""


STARTING_FUNDS = 300.0

CATEGORIES = ["output", "preserve", "monitor"]

CATEGORY_LABEL = {
    "output": "Output",
    "preserve": "Permafrost Preservation",
    "monitor": "Monitoring & Response",
}

CATEGORY_ICON = {
    "output": "\U0001F3ED",  # factory
    "preserve": "\U0001F332",  # evergreen tree
    "monitor": "\U0001F4E1",  # satellite antenna
}

TEMPERATURE_METER_MAX = 30.0

INVEST_COST = {
    "output": 20,
    "preserve": 25,
    "monitor": 20,
}

OUTPUT_INCOME_PER_UNIT = 6

# Global temperature rises this much every round, no matter what the
# player does — it's a background trajectory, not something the player
# directly drives. This is the thing that makes Thaw different from
# Herd/Grid: the player isn't the primary cause of the central meter.
BASE_TEMP_RISE_PER_ROUND = 1.0

# Permafrost melt + methane feedback: once temperature crosses this
# threshold, melt releases methane that ADDS to next round's rise —
# warming causes melt causes more warming. This is the entire lesson of
# the game: a slow, linear problem tipping into a runaway one.
MELT_THRESHOLD = 10.0
FEEDBACK_RATE_PER_DEGREE_OVER = 0.15

# G9: the optional "long game" mode. Chosen once, before any round is
# played, it stretches the whole trajectory: the background rise, the melt
# feedback and the restoration pull-back all run at LONG_GAME_WARMING_SCALE
# of their normal speed, while Output income runs at LONG_GAME_INCOME_SCALE,
# so reaching the same milestones takes roughly two and a half times as many
# rounds. Income is cut by less than warming, so a longer game is also a
# slightly gentler one per degree of warming. Off by default; the flag lives
# in the module (`long_game`, below) because it applies to every region.
LONG_GAME_WARMING_SCALE = 0.4
LONG_GAME_INCOME_SCALE = 0.6

# G3/G10: a second, further warming milestone past the initial melt
# threshold. Crossing +10.0 is "the tipping point" (Pass 1's flash);
# crossing this second, higher milestone while accelerating hard is what
# G3's "critical" visual state calls out, and it's also the milestone G10
# watches to announce the first time intervention has measurably delayed
# reaching it relative to the undampened counterfactual.
SECOND_WARMING_MILESTONE = 15.0
CRITICAL_ACCELERATION_FACTOR = 2.0

# Intervention: preserve/monitor investment dampens the FEEDBACK
# contribution only — never the background BASE_TEMP_RISE_PER_ROUND,
# which stays outside player control by design. "A real lever that
# measurably slows the loop, even if it can't fully stop the background
# trajectory" — the plan's hope-angle requirement, made literal.
DAMPENING_PER_PRESERVE_UNIT = 0.08
DAMPENING_PER_MONITOR_UNIT = 0.04
MAX_FEEDBACK_DAMPENING = 0.85

# G21: the region rescue — a costly, one-time-per-region emergency lever
# available only while that region is in the critical tier. It is a
# temporary dampening boost layered ON TOP of investment dampening (and
# allowed to push past MAX_FEEDBACK_DAMPENING, up to RESCUE_MAX_DAMPENING)
# for a fixed number of rounds, buying a stricken region breathing room
# but never a permanent fix: once it lapses, only real preserve/monitor
# investment keeps the feedback loop in check.
# G15: permafrost restoration. Once a melting region has held the feedback
# loop under RESTORATION_MAX_ACCELERATION on investment alone (a temporary
# rescue boost doesn't count) for RESTORATION_STREAK_ROUNDS rounds in a row,
# every Preservation unit starts pulling melt-driven warming back each
# round, up to RESTORATION_MAX_PER_ROUND. It removes real accumulated
# temperature but never outruns the fixed background rise, so it slows the
# climb rather than reversing it -- "some melt", per the design note.
RESTORATION_MAX_ACCELERATION = 1.3
RESTORATION_STREAK_ROUNDS = 3
RESTORATION_PER_PRESERVE_UNIT = 0.05
RESTORATION_MAX_PER_ROUND = 0.5

# G13: the optional starting policy stance for Region A -- a real-world-
# inspired framing chosen once, before the first round is played, that
# subtly weights the region's starting position. Each stance trades a
# little starting funds against a little permanent baseline dampening;
# none is a clearly best pick. `dampening` counts toward the region's
# feedback dampening exactly like investment does (so it is subject to
# MAX_FEEDBACK_DAMPENING), but never counts as an investment: it doesn't
# earn the "first intervention" achievement or the pre-emptive-investment
# praise. Region B/C already model strategies through their presets, and
# Region D is the deliberately-unmanaged baseline, so only A gets a stance.
POLICY_STANCES = {
    "growth": {
        "label": "Growth-led (stated policies)",
        "blurb": "Bank on the economy first: +100 starting funds, no head start on dampening.",
        "funds": 100.0,
        "dampening": 0.0,
    },
    "balanced": {
        "label": "Balanced (transition pathway)",
        "blurb": "A middle path: +40 starting funds and a 3% permafrost-protection head start.",
        "funds": 40.0,
        "dampening": 0.03,
    },
    "mitigation": {
        "label": "Mitigation-led (Paris-aligned)",
        "blurb": "Protect the peat from day one: a 6% permafrost-protection head start, no extra funds.",
        "funds": 0.0,
        "dampening": 0.06,
    },
}

RESCUE_COST = 200.0
RESCUE_DURATION_ROUNDS = 5
RESCUE_DAMPENING_BONUS = 0.5
RESCUE_MAX_DAMPENING = 0.95

# GG-13: the "Ice Age" streak medal. Consecutive rounds Region A goes without
# a tipping event (melt starting, or the critical tier) earn a frostier medal
# at each tier: (rounds needed, name, icon), ascending.
ICE_AGE_TIERS = (
    (5, "Frost", "\u2744\uFE0F"),
    (10, "Glacier", "\U0001F9CA"),
    (15, "Ice Age", "\U0001F3D4\uFE0F"),
)

# G-24: how many recent rounds of acceleration readings each region keeps for
# the sparkline next to the acceleration readout.
ACCEL_HISTORY_MAX = 30


# GG-2: "Hold the Line", the run-based mode. Keep at least HOLD_LINE_MIN_UNTIPPED of the three
# managed regions out of the critical tier for as many rounds as you can. A region counts as
# tipped while it is critical (its methane feedback is at least as large as the background rise).
# The background gets harsher in steps: every HOLD_LINE_ESCALATION_EVERY rounds a new escalation
# event adds HOLD_LINE_ESCALATION_STEP degrees to every round's background rise AND erodes the
# ceiling on how much dampening investment can hold (by HOLD_LINE_CAP_EROSION, never below
# HOLD_LINE_MIN_CAP), so even a fully invested region eventually cannot hold. The events are
# stylised game events, not forecasts, and are fixed by the round number (no luck). Score is rounds
# survived. HOLD_LINE_MAX_ROUNDS ends a run that is still standing, as a completed run.
HOLD_LINE_MIN_UNTIPPED = 2
HOLD_LINE_ESCALATION_EVERY = 5
HOLD_LINE_ESCALATION_STEP = 0.2
HOLD_LINE_CAP_EROSION = 0.02
HOLD_LINE_MIN_CAP = 0.3
HOLD_LINE_MAX_ROUNDS = 100
HOLD_LINE_EVENTS = (
    "Heat dome",
    "Boreal wildfire season",
    "Marine heatwave",
    "Early snowmelt",
    "Dry summer",
    "Soot on the ice",
)

# GG-24: run titles by average degrees saved across Regions A-C at the end of a run,
# (minimum saved, title), ascending. The escalating counterfactual makes saved figures large, so
# the bands are set from the three stewards' fixed plans (about 14, 150 and 260).
RUN_TITLES = (
    (0.0, "Ice Cube"),
    (10.0, "Snowflake Counter"),
    (40.0, "Frost Warden"),
    (90.0, "Permafrost Keeper"),
    (150.0, "Glacier Steward"),
    (220.0, "Tundra Guardian"),
    (300.0, "Cryosphere Guardian"),
)

# G-13: display units for temperature. Every figure in this game is a rise above the starting
# level, so a Fahrenheit reading multiplies by 1.8 (no 32 offset) and Kelvin equals Celsius.
TEMP_UNITS = ("c", "f", "k")
TEMP_UNIT_STORAGE_KEY = "thaw_temp_unit_v1"

CASCADE_CHANCE = 0.25
CASCADE_BUMP = 0.5

FORECAST_TOLERANCE = 0.2
FORECAST_MIN = -100.0
FORECAST_MAX = 1000.0

FIELD_NOTES_KEY = "thaw_field_notes_v1"
FIELD_NOTES_MAX = 30
FIELD_NOTES_CURVE_POINTS = 60

PLANNER_ROUNDS = 10
PLANNER_MAX_UNITS = 99
PLANNER_W = 320
PLANNER_H = 110
PLAN_ORDER = ("preserve", "monitor", "output")  # what gets bought first when funds run short
