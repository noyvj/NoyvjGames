"""Thaw — Permafrost Feedback Loop Game.

Runs in-browser via Pyodide. Milestone 1: the background trajectory and
core loop — global temperature rises on a fixed schedule each round,
independent of the player, while the player allocates regional resources
across output/preserve/monitor. The permafrost melt + methane feedback
loop (the entire point of this game) lands in Milestone 2.
"""

import json

import info_page
from js import document, setTimeout
from pyodide.ffi import create_proxy

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


class RegionState:
    def __init__(self):
        self.round_number = 1
        self.funds = STARTING_FUNDS
        self.capacity = {c: 0 for c in CATEGORIES}
        self.temperature = 0.0
        self.melt_started_round = None
        # One-tick flag: true only for the single render right after the
        # feedback loop crosses its tipping threshold — the visual cue
        # for that moment, consumed (and cleared) by the next render.
        self.just_started_melting = False
        # A parallel, fully undampened trajectory — same background rise,
        # same feedback mechanics, but zero intervention ever. The gap
        # between this and the real temperature is the hope-angle payoff.
        self.counterfactual_temperature = 0.0
        # Iteration Pass 2 — per-round temperature log, feeding this
        # region's mini-graph in the multi-region comparison.
        self.temperature_history = []
        # Iteration Pass 3 — one-tick flag: true only for the single
        # render right after preserve/monitor is invested, so the
        # dampening readout can flash instead of silently ticking up.
        # See feedback_dampening_fraction() below for why this matters:
        # pre-melt, that number has zero effect on anything else visible,
        # so without a cue of its own the lever reads as doing nothing.
        self.just_invested_intervention = False
        # G4: an optional, player-typed label for what strategy this
        # region is meant to represent ("aggressive growth", "heavy
        # preservation", ...) — purely descriptive, never read by any
        # game logic, so an empty string is always a safe default.
        self.strategy_label = ""
        # G10: the feedback-dampening fraction in effect at the exact
        # moment melt started (None until then) — lets early_investor
        # check "was meaningful dampening already in place *before* melt
        # began" rather than "is it in place right now," which could be
        # invested well after melt started and still read as true.
        self.dampening_at_melt_start = None
        # G10: one-time callout — true only for the single render right
        # after this region's real temperature first lags behind its own
        # undampened counterfactual crossing SECOND_WARMING_MILESTONE,
        # i.e. the first concrete proof intervention delayed reaching a
        # further warming milestone. `milestone_delay_announced` prevents
        # re-firing once already shown, the same one-shot-flag shape as
        # SOL/Grid's own achievement-adjacent "first time" trackers.
        self.just_delayed_milestone = False
        self.milestone_delay_announced = False

    def invest(self, category):
        cost = INVEST_COST[category]
        if self.funds < cost:
            return False
        self.funds -= cost
        self.capacity[category] += 1
        if category in ("preserve", "monitor"):
            self.just_invested_intervention = True
        return True

    def is_melting(self):
        return self.temperature >= MELT_THRESHOLD

    def feedback_dampening_fraction(self):
        total = (
            self.capacity["preserve"] * DAMPENING_PER_PRESERVE_UNIT
            + self.capacity["monitor"] * DAMPENING_PER_MONITOR_UNIT
        )
        return min(MAX_FEEDBACK_DAMPENING, total)

    def intervention_feedback_message(self):
        """Iteration Pass 3 fix: an immediate, legible efficacy readout
        for the intervention lever, true from the very first preserve/
        monitor investment — unlike trajectory_message()/
        acceleration_message(), it doesn't need melt to have started yet
        to say something real. Flow principle #2 (immediate feedback):
        without this, a player who invests early gets no visible sign
        their action did anything until a feedback loop they may never
        trigger this session finally kicks in.

        G18: phrasing now varies by dampening magnitude rather than one
        fixed sentence regardless of how much protection is actually in
        place — a player at 8% and a player at 80% were reading
        identical text before this, which undersold how much stronger a
        heavily-invested lever really is."""
        dampening = self.feedback_dampening_fraction()
        if dampening <= 0.0:
            return "No preservation or monitoring investment yet — a future melt would hit at full force."
        pct = dampening * 100
        if dampening < 0.3:
            tier = "a modest start"
        elif dampening < 0.6:
            tier = "a meaningful buffer"
        else:
            tier = "a strong shield"
        return (
            f"Preservation & monitoring investment is already dampening the feedback loop by "
            f"{pct:.0f}% — {tier}, in place now, whether or not melt has started yet."
        )

    def feedback_bonus(self):
        """Extra warming this round from methane released by permafrost
        melt — zero until the melt threshold is crossed, then grows with
        how far past it the temperature has climbed. Intervention
        investment dampens this, never the background rise itself."""
        excess = max(0.0, self.temperature - MELT_THRESHOLD)
        raw_bonus = excess * FEEDBACK_RATE_PER_DEGREE_OVER
        return raw_bonus * (1 - self.feedback_dampening_fraction())

    def current_rise_rate(self):
        return BASE_TEMP_RISE_PER_ROUND + self.feedback_bonus()

    def advance_round(self):
        self.funds += self.capacity["output"] * OUTPUT_INCOME_PER_UNIT
        current_round = self.round_number
        self.temperature += self.current_rise_rate()
        if self.melt_started_round is None and self.is_melting():
            self.melt_started_round = current_round
            self.just_started_melting = True
            # G10 (early_investor): snapshot dampening at the exact
            # moment melt begins, so the achievement can ask "was
            # meaningful protection already in place *before* melt
            # started" rather than just "is it in place right now."
            self.dampening_at_melt_start = self.feedback_dampening_fraction()

        counterfactual_excess = max(0.0, self.counterfactual_temperature - MELT_THRESHOLD)
        counterfactual_rate = BASE_TEMP_RISE_PER_ROUND + (
            counterfactual_excess * FEEDBACK_RATE_PER_DEGREE_OVER
        )
        self.counterfactual_temperature += counterfactual_rate

        self.round_number += 1
        self.temperature_history.append(self.temperature)

        # G10: the first time the undampened counterfactual has reached
        # SECOND_WARMING_MILESTONE while this (dampened) region hasn't —
        # concrete, one-time proof that intervention delayed reaching a
        # further warming milestone, not just slowed the rate in the
        # abstract. Only meaningful once some dampening has actually been
        # invested; a region with zero dampening never differs from its
        # own counterfactual, so the condition naturally never fires for
        # it (see feedback_bonus()/counterfactual math above — identical
        # for both when feedback_dampening_fraction() is 0).
        if (
            not self.milestone_delay_announced
            and self.counterfactual_temperature >= SECOND_WARMING_MILESTONE
            and self.temperature < SECOND_WARMING_MILESTONE
        ):
            self.milestone_delay_announced = True
            self.just_delayed_milestone = True

    def temperature_saved(self):
        """The hope-angle payoff, as a direct number: how much lower
        temperature is right now than the fully-undampened counterfactual
        trajectory would have reached by this round."""
        return self.counterfactual_temperature - self.temperature

    def trajectory_message(self):
        saved = self.temperature_saved()
        if saved <= 0.01:
            return "No meaningful difference from intervention yet."
        return (
            f"Early intervention has kept warming {saved:.1f}° lower than an "
            f"unmitigated trajectory would have reached by now."
        )

    def acceleration_factor(self):
        """How many times faster than the background baseline warming is
        rising right now — 1.0x when stable, growing once melt kicks in."""
        return self.current_rise_rate() / BASE_TEMP_RISE_PER_ROUND

    def acceleration_message(self):
        if not self.is_melting():
            return "Warming is rising at a steady, linear rate."
        return (
            f"Warming has accelerated to {self.acceleration_factor():.1f}x the background "
            f"rate since permafrost began melting in round {self.melt_started_round}."
        )


region = RegionState()

# Iteration Pass 2 — multi-region comparison: two more player-managed
# regions run alongside the original ("Region A", left entirely as-is
# above — same object, same element IDs, same behavior, so every Pass 1
# test keeps passing unchanged). Each can be given a different strategy,
# so the feedback-loop consequences of intervention vs. neglect are
# visible side-by-side within one session rather than only across
# separate playthroughs.
region_b = RegionState()
region_c = RegionState()
SECONDARY_REGIONS = {"b": region_b, "c": region_c}

REGION_FLAVOR = {
    "b": "Coastal tundra — closer to the sea, slightly more exposed to storm-driven erosion.",
    "c": "Boreal interior — deeper permafrost, slower to feel changes at first.",
}

# G13: a fourth, optional region that always neglects intervention —
# every round it auto-invests every affordable unit of funds straight
# into Output and never touches Preservation/Monitoring, so its feedback
# dampening stays permanently at 0%. Its temperature trajectory ends up
# numerically identical to the primary region's own
# counterfactual_temperature (both use the undampened feedback formula),
# which makes it a concrete, playable stand-in for "what if nobody
# intervened" rather than only an abstract number on Region A's card.
# Hidden behind a reveal toggle (worst_case_region_revealed) so it never
# clutters the default screen — the toggle itself doubles as the
# "worst_case_witnessed" achievement's tracked state, since revealing it
# is the one genuinely new player action involved.
region_d = RegionState()
worst_case_region_revealed = False


def _auto_play_worst_case_region():
    """Called once per Advance Round: spends every affordable unit of
    Region D's funds on Output only, then advances it — pure neglect,
    replayed automatically every round regardless of whether the panel
    revealing it is currently open."""
    while region_d.invest("output"):
        pass
    region_d.advance_round()


# G11: one-click preset strategies for Region B/C, so a player can set up
# a comparison strategy without manually clicking each category several
# times. Each preset spends as much of the region's *current* funds as
# it can afford in one go, repeatedly picking whichever weighted
# category is currently furthest behind its target share — a simple,
# deterministic way to approximate the named ratio without needing
# fractional investments (which don't exist in this game).
PRESET_WEIGHTS = {
    "growth": {"output": 1.0},
    "preservation": {"preserve": 0.6, "monitor": 0.4},
    "balanced": {"output": 1 / 3, "preserve": 1 / 3, "monitor": 1 / 3},
}

preset_used_ever = False


def apply_preset(r, preset_name):
    """Applies one named preset's weighting to region `r`, spending as
    much as it can afford right now. Returns True if at least one
    investment was actually made (used by the caller to decide whether
    to flip preset_used_ever, and by tests to check a no-op call did
    nothing)."""
    global preset_used_ever
    weights = PRESET_WEIGHTS.get(preset_name)
    if not weights:
        return False
    categories = list(weights.keys())
    spent = dict.fromkeys(categories, 0.0)
    invested_any = False
    while True:
        affordable = [c for c in categories if r.funds >= INVEST_COST[c]]
        if not affordable:
            break
        target = min(affordable, key=lambda c: spent[c] / weights[c])
        if not r.invest(target):
            break
        spent[target] += INVEST_COST[target]
        invested_any = True
    if invested_any:
        preset_used_ever = True
    return invested_any


def best_region_identifier():
    """G2/G15: which of the three player-managed regions (never Region D
    — it's a deliberate worst-case baseline, not a competitor for
    "best") currently has the lowest temperature. Ties resolve to
    whichever region is listed first (Region A), which is an acceptable,
    documented tie-break rather than a meaningful ranking."""
    candidates = [("A", region), ("B", region_b), ("C", region_c)]
    best_label, _ = min(candidates, key=lambda pair: pair[1].temperature)
    return best_label


def best_region_message():
    """G2: an explicit end-of-session (or any-time) "which region did
    best" line, comparing current temperature across the three
    player-managed regions."""
    label = best_region_identifier()
    best = {"A": region, "B": region_b, "C": region_c}[label]
    return (
        f"Region {label} currently has the lowest temperature (+{best.temperature:.1f}°) "
        f"among your three managed regions."
    )


MINI_GRAPH_WIDTH = 120
MINI_GRAPH_HEIGHT = 40


def mini_temp_graph_svg(history):
    """A compact single-line temperature trend for one region's card —
    deliberately tiny and unlabeled beyond its axis-free shape, since the
    point is the divergence *between* regions' graphs, not reading any
    one of them precisely.

    G14: also draws a faint dashed reference line at MELT_THRESHOLD when
    that value falls within the graph's current visible range, so the
    moment a region's curve crosses the melt threshold is legible on the
    mini-graph itself, not just inferable from the melt-status text next
    to it."""
    if len(history) < 2:
        return ""
    n = len(history)
    lo, hi = min(history), max(history)
    if hi - lo < 1e-9:
        ys = [MINI_GRAPH_HEIGHT / 2 for _ in history]
    else:
        ys = [MINI_GRAPH_HEIGHT - ((v - lo) / (hi - lo)) * MINI_GRAPH_HEIGHT for v in history]
    xs = [i * (MINI_GRAPH_WIDTH / (n - 1)) for i in range(n)]
    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))

    threshold_line = ""
    if hi - lo >= 1e-9 and lo <= MELT_THRESHOLD <= hi:
        threshold_y = MINI_GRAPH_HEIGHT - ((MELT_THRESHOLD - lo) / (hi - lo)) * MINI_GRAPH_HEIGHT
        threshold_line = (
            f'<line x1="0" y1="{threshold_y:.1f}" x2="{MINI_GRAPH_WIDTH}" y2="{threshold_y:.1f}" '
            f'class="mini-temp-threshold-line" />'
        )

    return (
        f'<svg viewBox="0 0 {MINI_GRAPH_WIDTH} {MINI_GRAPH_HEIGHT}" class="mini-temp-graph-svg">'
        f"{threshold_line}"
        f'<polyline points="{points}" class="mini-temp-line" />'
        f"</svg>"
    )


def _melt_status_label(r):
    """G3: a third, distinct "critical" state on top of the existing
    binary melting/stable read — once warming has accelerated past
    CRITICAL_ACCELERATION_FACTOR times the background rate, "Melting" no
    longer distinguishes a region that just crossed the threshold from
    one whose feedback loop is now compounding fast."""
    if not r.is_melting():
        return "stable"
    if r.acceleration_factor() >= CRITICAL_ACCELERATION_FACTOR:
        return "critical"
    return "melting"


def render_secondary_region(prefix, r):
    """Renders one of the two added regions into its `{prefix}-*`
    elements. Deliberately separate from the primary region's inline
    render code below (rather than a shared helper for all three) so
    the original Pass 1 behavior for "Region A" — including its
    whole-page tipping-flash — stays byte-for-byte unchanged.

    G1/G6: also renders the same dampening/acceleration/temperature-saved
    readouts Region A already had — every one of these is already a
    generic RegionState method, so no new game logic was needed, only
    new elements to write them into."""
    document.getElementById(f"{prefix}-temperature-display").innerText = f"+{r.temperature:.1f}°"
    document.getElementById(f"{prefix}-funds-display").innerText = f"Funds: {r.funds:.0f}"
    document.getElementById(f"{prefix}-graph").innerHTML = mini_temp_graph_svg(r.temperature_history)
    document.getElementById(f"{prefix}-dampening-display").innerText = (
        f"Dampening: {r.feedback_dampening_fraction() * 100:.0f}%"
    )
    document.getElementById(f"{prefix}-acceleration-display").innerText = r.acceleration_message()
    document.getElementById(f"{prefix}-trajectory-display").innerText = r.trajectory_message()

    status = _melt_status_label(r)
    melt_status_el = document.getElementById(f"{prefix}-melt-status-display")
    melt_status_el.innerText = status.capitalize()
    suffix = {"stable": "", "melting": " melt-status--active", "critical": " melt-status--critical"}[status]
    melt_status_el.className = "region-melt-status" + suffix

    card_el = document.getElementById(f"{prefix}-region-card")
    if r.just_started_melting:
        card_el.className = "region-card tipping-flash"
        r.just_started_melting = False
    else:
        card_el.className = "region-card"

    for category in CATEGORIES:
        document.getElementById(f"{prefix}-{category}-count").innerText = str(r.capacity[category])
        invest_button = document.getElementById(f"{prefix}-{category}-invest-button")
        invest_button.innerText = f"{CATEGORY_ICON[category]} ({INVEST_COST[category]})"
        invest_button.disabled = r.funds < INVEST_COST[category]


def render_worst_case_region():
    """G13: renders Region D's read-only stats into its own elements —
    no invest buttons, since it never receives player input, only the
    same graph/status readouts every other region gets. Always keeps
    its DOM up to date regardless of worst_case_region_revealed, so the
    numbers are correct the instant a player opens the panel rather than
    only starting from whenever they first reveal it."""
    r = region_d
    document.getElementById("d-temperature-display").innerText = f"+{r.temperature:.1f}°"
    document.getElementById("d-funds-display").innerText = f"Funds: {r.funds:.0f}"
    document.getElementById("d-graph").innerHTML = mini_temp_graph_svg(r.temperature_history)

    status = _melt_status_label(r)
    melt_status_el = document.getElementById("d-melt-status-display")
    melt_status_el.innerText = status.capitalize()
    suffix = {"stable": "", "melting": " melt-status--active", "critical": " melt-status--critical"}[status]
    melt_status_el.className = "region-melt-status" + suffix

    card_el = document.getElementById("d-region-card")
    if r.just_started_melting:
        card_el.className = "region-card tipping-flash"
        r.just_started_melting = False
    else:
        card_el.className = "region-card"


# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
INFO_PAGE = {
    "framing": (
        "Arctic permafrost holds thousands of years of stored carbon and "
        "methane, and as it thaws that store starts releasing — a "
        "feedback loop where warming causes more warming. But real "
        "climate scientists describe it as a dimmer switch, not an "
        "on/off switch: every bit of avoided warming keeps more "
        "permafrost frozen. That framing is the backbone of Thaw's whole "
        "design."
    ),
    "mechanic_tie_in": (
        "Thaw's tipping-point moment is grounded in real observed "
        "evidence of accelerating Arctic methane emissions, not a purely "
        "speculative mechanic."
    ),
    "sources": [
        {
            "label": "MIT Climate Portal — Is methane release from the Arctic unstoppable?",
            "url": "https://climate.mit.edu/ask-mit/methane-release-arctic-unstoppable",
            "note": "The clearest source for Thaw's hope angle — frames the feedback loop as a dimmer switch, not an on/off switch.",
        },
        {
            "label": "Nature Climate Change — Seasonal increase of methane emissions linked to warming in Siberian tundra",
            "url": "https://www.nature.com/articles/s41558-022-01512-4",
            "note": "Real observational evidence (not just modeling) of the feedback loop already measurably happening.",
        },
        {
            "label": "WWF Arctic — Thawing permafrost",
            "url": "https://www.arcticwwf.org/the-circle/stories/thawing-permafrost/",
            "note": "An accessible explainer connecting permafrost thaw to real Arctic communities' lived experience.",
        },
        {
            "label": "PMC/NCBI — 21st-century modeled permafrost carbon emissions accelerated by abrupt thaw beneath lakes",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6093858/",
            "note": "A more technical source on abrupt (not just gradual) thaw mechanisms, tying to Thaw's tipping-point moment.",
        },
    ],
}
info_page_open = False


# Rendering/toggle logic lives in shared/info_page.py now (see that
# module's docstring) -- this used to be a ~25+4 line implementation
# byte-identical across all 8 climate games. info_page_open stays local
# here since it's part of this game's save contract.
def render_info_page():
    info_page.render(INFO_PAGE, info_page_open)


def on_toggle_info_page(event=None):
    global info_page_open
    info_page_open = info_page.toggle(info_page_open)
    render_info_page()


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — following SOL's reference
# integration, as also built out for Canopy/Grid/Continuum. Every
# achievement's earned status is a pure function of state that already
# exists elsewhere in this module, recomputed fresh every call — never a
# separately hand-maintained "earned" flag. A handful of achievements
# genuinely needed new tracked state (dampening_at_melt_start on
# RegionState, and the module-level preset_used_ever/
# worst_case_region_revealed flags above) because "was this true at some
# specific past moment" or "has the player ever done X" can't be derived
# from state that only remembers the present.
# ===========================================================================
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract as SOL's/Grid's `_read_achievements_json()`:
    the boot script fetches achievements.json and hands it to Python as a
    window global before this file runs; the pytest harness's fake `js`
    module has no such attribute, so this falls through to reading the
    file straight off disk, keeping the module importable outside a real
    browser."""
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "ACHIEVEMENTS_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 -- only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to "no achievements catalog" rather than crashing this module's
# whole import — achievements are additive, not core to Thaw's gameplay.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

EARLY_INVESTOR_MIN_DAMPENING = 0.25
SLOW_BURN_ROUNDS_AFTER_MELT = 15
SLOW_BURN_MAX_ACCELERATION = 1.5
WELL_FUNDED_TARGET = 500
LONG_HAUL_ROUND_TARGET = 25
BEAT_BOTH_REGIONS_MIN_ROUND = 15


def _all_categories_invested():
    return all(region.capacity[c] >= 1 for c in CATEGORIES)


def _invested_count():
    return sum(1 for c in CATEGORIES if region.capacity[c] >= 1)


def _both_secondary_regions_invested():
    return sum(region_b.capacity.values()) >= 1 and sum(region_c.capacity.values()) >= 1


# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is ever cached or hand-flagged.
ACHIEVEMENT_CHECKS = {
    "first_output": lambda: region.capacity["output"] >= 1,
    "first_intervention": lambda: region.capacity["preserve"] >= 1 or region.capacity["monitor"] >= 1,
    "triple_threat": _all_categories_invested,
    "quarter_dampening": lambda: region.feedback_dampening_fraction() >= 0.25,
    "half_dampening": lambda: region.feedback_dampening_fraction() >= 0.5,
    "max_dampening": lambda: region.feedback_dampening_fraction() >= MAX_FEEDBACK_DAMPENING - 1e-9,
    "tipping_point_witnessed": lambda: region.melt_started_round is not None,
    "early_investor": lambda: (
        region.dampening_at_melt_start is not None
        and region.dampening_at_melt_start >= EARLY_INVESTOR_MIN_DAMPENING
    ),
    "degree_saved_5": lambda: region.temperature_saved() >= 5,
    "degree_saved_10": lambda: region.temperature_saved() >= 10,
    "degree_saved_20": lambda: region.temperature_saved() >= 20,
    "slow_burn": lambda: (
        region.melt_started_round is not None
        and (region.round_number - region.melt_started_round) >= SLOW_BURN_ROUNDS_AFTER_MELT
        and region.acceleration_factor() < SLOW_BURN_MAX_ACCELERATION
    ),
    "well_funded": lambda: region.funds >= WELL_FUNDED_TARGET,
    "long_haul": lambda: region.round_number >= LONG_HAUL_ROUND_TARGET,
    "beat_both_regions": lambda: (
        region.round_number >= BEAT_BOTH_REGIONS_MIN_ROUND
        and region.temperature < region_b.temperature
        and region.temperature < region_c.temperature
    ),
    "comparison_engaged": _both_secondary_regions_invested,
    "preset_strategist": lambda: preset_used_ever,
    "worst_case_witnessed": lambda: worst_case_region_revealed,
}

# Progress readouts, only for achievements with a genuine numeric scale-up
# — a one-shot milestone (e.g. "witness the tipping point") gets no
# progress row at all, the honest shape for it per the design doc.
ACHIEVEMENT_PROGRESS = {
    "triple_threat": lambda: (_invested_count(), len(CATEGORIES)),
    "quarter_dampening": lambda: (min(100, round(region.feedback_dampening_fraction() * 100)), 25),
    "half_dampening": lambda: (min(100, round(region.feedback_dampening_fraction() * 100)), 50),
    "max_dampening": lambda: (
        min(100, round(region.feedback_dampening_fraction() * 100)),
        round(MAX_FEEDBACK_DAMPENING * 100),
    ),
    "degree_saved_5": lambda: (max(0, min(5, round(region.temperature_saved()))), 5),
    "degree_saved_10": lambda: (max(0, min(10, round(region.temperature_saved()))), 10),
    "degree_saved_20": lambda: (max(0, min(20, round(region.temperature_saved()))), 20),
    "well_funded": lambda: (max(0, min(WELL_FUNDED_TARGET, round(region.funds))), WELL_FUNDED_TARGET),
    "long_haul": lambda: (min(region.round_number, LONG_HAUL_ROUND_TARGET), LONG_HAUL_ROUND_TARGET),
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field (ACHIEVEMENTS-SYSTEM-DESIGN.md). Always
    recomputed, never itself a save input."""
    return [entry["id"] for entry in ACHIEVEMENTS if ACHIEVEMENT_CHECKS[entry["id"]]()]


def achievements_summary():
    """The full catalog, in order, each entry annotated with whether it's
    currently earned and (where one exists) a live progress readout."""
    earned_ids = set(achievement_ids_earned())
    summary = []
    for entry in ACHIEVEMENTS:
        progress_fn = ACHIEVEMENT_PROGRESS.get(entry["id"])
        summary.append(
            {
                "id": entry["id"],
                "label": entry["label"],
                "description": entry["description"],
                "earned": entry["id"] in earned_ids,
                "progress": progress_fn() if progress_fn else None,
            }
        )
    return summary


achievements_open = False


def on_toggle_achievements(event=None):
    global achievements_open
    achievements_open = not achievements_open
    update_achievements_display()


def update_achievements_display():
    toggle = document.getElementById("achievements-toggle-button")
    panel = document.getElementById("achievements-panel")
    earned_count = len(achievement_ids_earned())
    toggle.innerText = (
        f"Hide Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
        if achievements_open
        else f"🏆 Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
    )
    panel.hidden = not achievements_open
    if not achievements_open:
        return

    panel.innerHTML = ""
    for entry in achievements_summary():
        card = document.createElement("div")
        card.className = "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"

        label = document.createElement("p")
        label.className = "achievement-card-label"
        label.innerText = f"🏆 {entry['label']}" if entry["earned"] else entry["label"]
        card.appendChild(label)

        description = document.createElement("p")
        description.className = "achievement-card-description"
        description.innerText = entry["description"]
        card.appendChild(description)

        if not entry["earned"] and entry["progress"] is not None:
            current, target = entry["progress"]
            progress = document.createElement("p")
            progress.className = "achievement-card-progress"
            progress.innerText = f"{current} of {target}"
            card.appendChild(progress)

        panel.appendChild(card)

    # A link out to the hub-wide achievements dashboard
    # (ACHIEVEMENTS-SYSTEM-DESIGN.md §5), same convention as every other
    # game's reference retrofit. Relative path, no leading "/" (site-level
    # milestone 7's GitHub Pages subpath fix). The hub-side script.js
    # registration that makes Thaw's save data actually show up on that
    # dashboard is a root-file change, out of scope for this
    # games/thaw/-only dispatch.
    hub_link = document.createElement("a")
    hub_link.innerText = "View the hub-wide achievements dashboard →"
    hub_link.href = "../../index.html#account-achievements-dashboard"
    hub_link.className = "achievements-hub-link"
    panel.appendChild(hub_link)


# Unlock toast (TODO.md "roll achievements out everywhere" — required on
# top of the base per-game rollout). Same pattern as every other game's
# reference retrofit: a snapshot of which ids were already earned as of
# the last seed point, so a fresh load or a loaded save doesn't flood the
# player with toasts for achievements it already satisfies.
_achievements_seen_ids = set()


def _seed_achievement_toast_baseline():
    global _achievements_seen_ids
    _achievements_seen_ids = set(achievement_ids_earned())


def _display_achievement_toast(message):
    toast = document.getElementById("achievement-toast")
    text = document.getElementById("achievement-toast-text")
    text.innerText = message
    toast.hidden = False
    toast.classList.add("visible")

    def _hide(*args):
        toast.hidden = True
        toast.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, 4000)


def _check_new_achievements_for_toast():
    """Called after every player action that could change earned status
    (invest/preset/advance round/reveal worst-case region) — never from
    render() itself, since load_state() also calls render() and a loaded
    save with several achievements already earned must not flood the
    player with toasts for all of them at once."""
    global _achievements_seen_ids
    earned_now = set(achievement_ids_earned())
    newly = earned_now - _achievements_seen_ids
    if newly:
        by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
        labels = [by_id[aid]["label"] for aid in newly if aid in by_id]
        if labels:
            if len(labels) == 1:
                _display_achievement_toast(f"🏆 Achievement unlocked: {labels[0]}")
            else:
                _display_achievement_toast(f"🏆 {len(labels)} achievements unlocked: " + ", ".join(labels))
    _achievements_seen_ids = earned_now


# G19: a per-browser "best run" — the highest temperature_saved()
# (the hope-angle payoff stat, per CLAUDE.md) any session on this device
# has ever reached, persisted via localStorage. Deliberately NOT part of
# get_state()/the save-code system — this tracks the best this *browser*
# has ever seen across every session/save on this device, not one save's
# snapshot, the same distinction Canopy's B14/Tide's D13 personal-best
# features already draw.
PERSONAL_BEST_STORAGE_KEY = "thaw_personal_best_v1"


def _read_local_storage_item(key):
    """Lazy `import js` (same convention as _read_achievements_json()) so
    this file stays importable outside a real browser. Broad except on
    the actual read/write below is deliberate: a real browser can refuse
    localStorage access entirely (private-browsing mode in some
    browsers), surfaced as a JS exception with no stable Python type to
    catch narrowly — this feature is a nice-to-have, not core gameplay,
    so it degrades to "no personal best recorded" rather than crashing
    the module import."""
    try:
        import js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        return None
    storage = getattr(js, "localStorage", None)
    if storage is None:
        return None
    try:
        return storage.getItem(key)
    except Exception:  # noqa: BLE001 -- see docstring above
        return None


def _write_local_storage_item(key, value):
    try:
        import js  # noqa: PLC0415
    except ImportError:
        return
    storage = getattr(js, "localStorage", None)
    if storage is None:
        return
    try:
        storage.setItem(key, value)
    except Exception:  # noqa: BLE001 -- see _read_local_storage_item's docstring
        pass


def load_personal_best():
    """Reads the stored best temperature_saved(), defaulting to 0.0 if
    nothing is stored yet, storage is unavailable, or the stored value is
    malformed (e.g. hand-edited or from a future incompatible format)."""
    raw = _read_local_storage_item(PERSONAL_BEST_STORAGE_KEY)
    if not raw:
        return {"temperature_saved": 0.0}
    try:
        data = json.loads(raw)
        return {"temperature_saved": float(data.get("temperature_saved", 0.0))}
    except (ValueError, TypeError, AttributeError):
        return {"temperature_saved": 0.0}


personal_best = load_personal_best()


def _maybe_update_personal_best():
    """Called every render(); bumps + persists personal_best whenever the
    live session exceeds it."""
    global personal_best
    saved = region.temperature_saved()
    if saved > personal_best["temperature_saved"]:
        personal_best["temperature_saved"] = saved
        _write_local_storage_item(PERSONAL_BEST_STORAGE_KEY, json.dumps(personal_best))


def render_personal_best():
    element = document.getElementById("personal-best-display")
    if element is None:
        return
    element.innerText = f"Personal best: {personal_best['temperature_saved']:.1f}° saved"


def render():
    render_info_page()
    document.getElementById("round-display").innerText = f"Round {region.round_number}"
    document.getElementById("funds-display").innerText = f"Funds: {region.funds:.0f}"
    document.getElementById("temperature-display").innerText = (
        f"Global temperature: +{region.temperature:.1f}°"
    )
    # G9: the temperature bar visually caps at TEMPERATURE_METER_MAX
    # (+30°) even though temperature itself keeps climbing past it —
    # without this note a maxed-out bar reads as "capped for real,"
    # which understates how far past +30° a long, unmanaged session can
    # actually reach.
    cap_note_el = document.getElementById("temperature-cap-note")
    if region.temperature > TEMPERATURE_METER_MAX:
        cap_note_el.innerText = (
            f"(meter shown capped at +{TEMPERATURE_METER_MAX:.0f}° — actual temperature is "
            f"+{region.temperature:.1f}°)"
        )
        cap_note_el.hidden = False
    else:
        cap_note_el.hidden = True
    document.getElementById("rise-rate-display").innerText = (
        f"Current warming rate: {region.current_rise_rate():.2f}°/round"
    )
    melt_status_el = document.getElementById("melt-status-display")
    status = _melt_status_label(region)
    if status == "critical":
        melt_status_el.innerText = (
            "Permafrost melt has reached a critical, fast-compounding pace — the feedback "
            "loop is running away."
        )
    elif status == "melting":
        melt_status_el.innerText = (
            "Permafrost is actively melting — methane feedback is accelerating warming."
        )
    else:
        melt_status_el.innerText = "Permafrost stable — no feedback yet."
    status_suffix = {
        "stable": "",
        "melting": " melt-status--active",
        "critical": " melt-status--critical",
    }[status]
    melt_status_el.className = "comparison-message" + status_suffix

    game_el = document.getElementById("game")
    if region.just_started_melting:
        game_el.className = "tipping-flash"
        region.just_started_melting = False
    else:
        game_el.className = ""

    # G10: the one-tick "intervention delayed a further warming
    # milestone" callout — a separate banner from the tipping-flash
    # above, since it can fire many rounds after melt already started.
    milestone_delay_el = document.getElementById("milestone-delay-callout")
    if region.just_delayed_milestone:
        milestone_delay_el.innerText = (
            f"Your preservation & monitoring investments just delayed reaching "
            f"+{SECOND_WARMING_MILESTONE:.0f}° warming — the unmitigated counterfactual has "
            f"already passed it."
        )
        milestone_delay_el.hidden = False
        region.just_delayed_milestone = False
    else:
        milestone_delay_el.hidden = True

    dampening_el = document.getElementById("dampening-display")
    dampening_el.innerText = f"Feedback dampening: {region.feedback_dampening_fraction() * 100:.0f}%"
    if region.just_invested_intervention:
        dampening_el.className = "status-line dampening-flash"
        region.just_invested_intervention = False
    else:
        dampening_el.className = "status-line"
    document.getElementById("intervention-feedback-display").innerText = (
        region.intervention_feedback_message()
    )
    document.getElementById("acceleration-display").innerText = region.acceleration_message()
    document.getElementById("acceleration-bar").style.width = (
        f"{min(1.0, (region.acceleration_factor() - 1) / 2) * 100:.0f}%"
    )
    document.getElementById("trajectory-display").innerText = region.trajectory_message()

    document.getElementById("temperature-bar").style.width = (
        f"{min(1.0, region.temperature / TEMPERATURE_METER_MAX) * 100:.0f}%"
    )
    document.getElementById("graph").innerHTML = mini_temp_graph_svg(region.temperature_history)

    for category in CATEGORIES:
        document.getElementById(f"{category}-name").innerText = (
            f"{CATEGORY_ICON[category]} {CATEGORY_LABEL[category]}"
        )
        document.getElementById(f"{category}-count").innerText = str(region.capacity[category])
        invest_button = document.getElementById(f"{category}-invest-button")
        invest_button.innerText = f"Invest ({INVEST_COST[category]})"
        invest_button.disabled = region.funds < INVEST_COST[category]

    # G12: a small inline forecast of each investment's effect, so a
    # player can see what a click would do before making it rather than
    # inferring it from the constants tables in How to Play.
    document.getElementById("output-forecast").innerText = f"+{OUTPUT_INCOME_PER_UNIT} funds/round"
    document.getElementById("preserve-forecast").innerText = (
        f"+{DAMPENING_PER_PRESERVE_UNIT * 100:.0f}% dampening"
    )
    document.getElementById("monitor-forecast").innerText = (
        f"+{DAMPENING_PER_MONITOR_UNIT * 100:.0f}% dampening"
    )

    for prefix, r in SECONDARY_REGIONS.items():
        render_secondary_region(prefix, r)

    worst_case_panel = document.getElementById("worst-case-panel")
    worst_case_panel.hidden = not worst_case_region_revealed
    if worst_case_region_revealed:
        render_worst_case_region()
    worst_case_toggle = document.getElementById("worst-case-toggle-button")
    worst_case_toggle.innerText = (
        "Hide the worst-case region" if worst_case_region_revealed else "Reveal a worst-case region"
    )

    # G2: an explicit "which region did best" comparison line, always
    # visible (not gated on an end-of-session state, since this game has
    # none) rather than only inferable by eyeballing three separate cards.
    document.getElementById("region-comparison-best-display").innerText = best_region_message()
    # G15: a hidden, machine-readable echo of the same comparison for the
    # plain-JS feedback-submission script below to fold into its rating
    # payload as an aggregate stat.
    document.getElementById("best-region-hidden").innerText = best_region_identifier()

    # G17: a next-round forecast, available as a hover tooltip on Advance
    # Round rather than a permanent line, since it's a "before you click"
    # preview rather than information about the current state.
    document.getElementById("advance-round-button").title = (
        f"Next round — Region A: +{region.current_rise_rate():.2f}°, "
        f"Region B: +{region_b.current_rise_rate():.2f}°, "
        f"Region C: +{region_c.current_rise_rate():.2f}°"
    )

    _maybe_update_personal_best()
    render_personal_best()
    update_achievements_display()


def _make_invest_handler(category):
    def handler(event=None):
        region.invest(category)
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_secondary_invest_handler(prefix, category):
    def handler(event=None):
        SECONDARY_REGIONS[prefix].invest(category)
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_preset_handler(prefix, preset_name):
    def handler(event=None):
        apply_preset(SECONDARY_REGIONS[prefix], preset_name)
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_strategy_label_handler(prefix):
    """G4: reads the input's current value straight off the DOM into
    state on every "input" event. Deliberately does NOT call render() —
    render() never writes this input's .value back (see setup()'s own
    comment), but avoiding the call entirely also sidesteps ever needing
    to reason about it, and there's nothing else on screen this label
    needs to update."""
    def handler(event=None):
        SECONDARY_REGIONS[prefix].strategy_label = document.getElementById(
            f"{prefix}-strategy-label-input"
        ).value
    return handler


def on_toggle_worst_case_region(event=None):
    global worst_case_region_revealed
    worst_case_region_revealed = not worst_case_region_revealed
    render()
    _check_new_achievements_for_toast()


def on_advance_round(event=None):
    region.advance_round()
    for r in SECONDARY_REGIONS.values():
        r.advance_round()
    _auto_play_worst_case_region()
    render()
    _check_new_achievements_for_toast()


# --- Save system (SAVE-BUTTON-INTEGRATION.md contract) ---
# Bridges to the shared shared/save-widget.js: get_state() returns a
# plain JSON-safe dict (the widget does its own JS<->Pyodide dict
# conversion), and load_state() is its exact inverse. SOL is the
# reference integration for this contract. Thaw tracks THREE independent
# regions (the original primary region, plus Pass 2's Region B and
# Region C) — all three must round-trip, not just the primary one.


def _region_state_dict(r):
    """One RegionState's fields as a plain, JSON-safe dict. `capacity`
    and `temperature_history` are copied here (dict()/list()), not just
    referenced, so continued play after taking a snapshot can't silently
    mutate a saved copy — same reasoning as SOL's serialize_state()
    docstring."""
    return {
        "round_number": r.round_number,
        "funds": r.funds,
        "capacity": dict(r.capacity),
        "temperature": r.temperature,
        "melt_started_round": r.melt_started_round,
        "just_started_melting": r.just_started_melting,
        "counterfactual_temperature": r.counterfactual_temperature,
        "temperature_history": list(r.temperature_history),
        "just_invested_intervention": r.just_invested_intervention,
        "strategy_label": r.strategy_label,
        "dampening_at_melt_start": r.dampening_at_melt_start,
        "just_delayed_milestone": r.just_delayed_milestone,
        "milestone_delay_announced": r.milestone_delay_announced,
    }


def _apply_region_state(r, data):
    """The exact inverse of _region_state_dict() — restores one
    RegionState's fields in place from a previously-saved dict.

    Every field is read with `.get(key, <current live value>)` rather than
    a bare `data["key"]` — a save may be a hand-edited/truncated payload,
    or simply come from a different build of this game with a different
    field set (an older save from before some field existed, or a newer
    one this build doesn't know about yet). A bare index raised a
    KeyError partway through these assignments, leaving some fields
    already overwritten from the save and others still at their pre-load
    values — worse than either a clean load or leaving the field alone.
    Falling back to the field's current value keeps a partial/malformed
    save loading everything it safely can instead of crashing outright.

    `capacity` is merged into the live dict key-by-key rather than
    replaced wholesale, same reasoning as above but at the nested-dict
    level: a save whose capacity is missing a category (an older save
    format from before that category existed, or a hand-edited/corrupted
    payload) must not wipe that category's key out of the live dict
    entirely — invest(), feedback_dampening_fraction() and render() all do
    unconditional capacity["monitor"]-style key access, so a missing key
    would crash the game on the very next call, including the re-render
    load_state() itself triggers. Same fix shape as SOL's planet_state and
    Continuum's resources/allocation/buildings dicts. Also mirrors Tide's
    load_state(), which already used this exact `.get()` pattern
    throughout (see that file's REVIEW(patterns) comment flagging Thaw,
    among others, as still doing bare data["key"] indexing)."""
    r.round_number = data.get("round_number", r.round_number)
    r.funds = data.get("funds", r.funds)
    saved_capacity = data.get("capacity")
    if isinstance(saved_capacity, dict):
        for category in CATEGORIES:
            if category in saved_capacity:
                r.capacity[category] = saved_capacity[category]
    r.temperature = data.get("temperature", r.temperature)
    r.melt_started_round = data.get("melt_started_round", r.melt_started_round)
    r.just_started_melting = data.get("just_started_melting", r.just_started_melting)
    r.counterfactual_temperature = data.get(
        "counterfactual_temperature", r.counterfactual_temperature
    )
    saved_history = data.get("temperature_history")
    if isinstance(saved_history, list):
        r.temperature_history = list(saved_history)
    r.just_invested_intervention = data.get(
        "just_invested_intervention", r.just_invested_intervention
    )
    r.strategy_label = data.get("strategy_label", r.strategy_label)
    r.dampening_at_melt_start = data.get("dampening_at_melt_start", r.dampening_at_melt_start)
    r.just_delayed_milestone = data.get("just_delayed_milestone", r.just_delayed_milestone)
    r.milestone_delay_announced = data.get(
        "milestone_delay_announced", r.milestone_delay_announced
    )


def get_state():
    """Return every module-level mutable global needed to fully
    reconstruct the game — all four regions (primary + Region B/C/D) plus
    the info-page toggle and the two achievement-only flags — as a plain,
    JSON-serialisable dict. No custom objects, no functions: just numbers,
    strings, lists, dicts, booleans.

    "achievements_earned" is a write-only projection
    (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) — always freshly recomputed here,
    never read back in load_state()."""
    return {
        "region": _region_state_dict(region),
        "region_b": _region_state_dict(region_b),
        "region_c": _region_state_dict(region_c),
        "region_d": _region_state_dict(region_d),
        "info_page_open": info_page_open,
        "worst_case_region_revealed": worst_case_region_revealed,
        "preset_used_ever": preset_used_ever,
        "achievements_earned": achievement_ids_earned(),
    }


def load_state(data):
    """Take the dict from get_state() (possibly from a previous session)
    and restore the game to that point, across all four regions, then
    re-render so the UI reflects the loaded state immediately. The exact
    inverse of get_state() (except "achievements_earned" -- see
    get_state()'s own comment, that key is never read back).

    A non-dict payload is rejected outright rather than raising. A dict
    missing "region_b"/"region_c"/"region_d" entirely — e.g. a save made
    before that region existed — leaves that region's live state
    untouched instead of crashing, same reasoning as every other
    per-field fallback in _apply_region_state()."""
    global info_page_open, worst_case_region_revealed, preset_used_ever
    if not isinstance(data, dict):
        return False
    region_data = data.get("region")
    if isinstance(region_data, dict):
        _apply_region_state(region, region_data)
    region_b_data = data.get("region_b")
    if isinstance(region_b_data, dict):
        _apply_region_state(region_b, region_b_data)
    region_c_data = data.get("region_c")
    if isinstance(region_c_data, dict):
        _apply_region_state(region_c, region_c_data)
    region_d_data = data.get("region_d")
    if isinstance(region_d_data, dict):
        _apply_region_state(region_d, region_d_data)
    info_page_open = data.get("info_page_open", info_page_open)
    worst_case_region_revealed = data.get(
        "worst_case_region_revealed", worst_case_region_revealed
    )
    preset_used_ever = data.get("preset_used_ever", preset_used_ever)
    document.getElementById("b-strategy-label-input").value = region_b.strategy_label
    document.getElementById("c-strategy-label-input").value = region_c.strategy_label
    render()
    _seed_achievement_toast_baseline()
    return True


def setup():
    for category in CATEGORIES:
        document.getElementById(f"{category}-invest-button").addEventListener(
            "click", create_proxy(_make_invest_handler(category))
        )
    for prefix in SECONDARY_REGIONS:
        for category in CATEGORIES:
            document.getElementById(f"{prefix}-{category}-invest-button").addEventListener(
                "click", create_proxy(_make_secondary_invest_handler(prefix, category))
            )
        for preset_name in PRESET_WEIGHTS:
            document.getElementById(f"{prefix}-preset-{preset_name}-button").addEventListener(
                "click", create_proxy(_make_preset_handler(prefix, preset_name))
            )
        # G4: "input" (not "change") so the label updates live as the
        # player types, without waiting for the field to lose focus.
        document.getElementById(f"{prefix}-strategy-label-input").addEventListener(
            "input", create_proxy(_make_strategy_label_handler(prefix))
        )
    document.getElementById("advance-round-button").addEventListener(
        "click", create_proxy(on_advance_round)
    )
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("worst-case-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_worst_case_region)
    )
    # Belt-and-suspenders: the toast starts hidden via the static
    # `hidden` attribute in index.html, but every other stateful element
    # in this file has its shown/hidden state actively driven by code
    # rather than left to rely on markup alone (matches Continuum's own
    # documented fix for exactly this gap).
    document.getElementById("achievement-toast").hidden = True
    render()
    _seed_achievement_toast_baseline()


setup()
