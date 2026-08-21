"""Thaw — Permafrost Feedback Loop Game.

Runs in-browser via Pyodide. Milestone 1: the background trajectory and
core loop — global temperature rises on a fixed schedule each round,
independent of the player, while the player allocates regional resources
across output/preserve/monitor. The permafrost melt + methane feedback
loop (the entire point of this game) lands in Milestone 2.
"""

from js import document
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
        trigger this session finally kicks in."""
        dampening = self.feedback_dampening_fraction()
        if dampening <= 0.0:
            return "No preservation or monitoring investment yet — a future melt would hit at full force."
        return (
            f"Preservation & monitoring investment is already dampening the feedback loop by "
            f"{dampening * 100:.0f}% — that protection is in place now, whether or not melt has "
            f"started yet."
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

        counterfactual_excess = max(0.0, self.counterfactual_temperature - MELT_THRESHOLD)
        counterfactual_rate = BASE_TEMP_RISE_PER_ROUND + (
            counterfactual_excess * FEEDBACK_RATE_PER_DEGREE_OVER
        )
        self.counterfactual_temperature += counterfactual_rate

        self.round_number += 1
        self.temperature_history.append(self.temperature)

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
SECONDARY_REGION_LABEL = {"b": "Region B", "c": "Region C"}

MINI_GRAPH_WIDTH = 120
MINI_GRAPH_HEIGHT = 40


def mini_temp_graph_svg(history):
    """A compact single-line temperature trend for one region's card —
    deliberately tiny and unlabeled beyond its axis-free shape, since the
    point is the divergence *between* regions' graphs, not reading any
    one of them precisely."""
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
    return (
        f'<svg viewBox="0 0 {MINI_GRAPH_WIDTH} {MINI_GRAPH_HEIGHT}" class="mini-temp-graph-svg">'
        f'<polyline points="{points}" class="mini-temp-line" />'
        f"</svg>"
    )


def render_secondary_region(prefix, r):
    """Renders one of the two added regions into its `{prefix}-*`
    elements. Deliberately separate from the primary region's inline
    render code below (rather than a shared helper for all three) so
    the original Pass 1 behavior for "Region A" — including its
    whole-page tipping-flash — stays byte-for-byte unchanged."""
    document.getElementById(f"{prefix}-temperature-display").innerText = f"+{r.temperature:.1f}°"
    document.getElementById(f"{prefix}-funds-display").innerText = f"Funds: {r.funds:.0f}"
    document.getElementById(f"{prefix}-graph").innerHTML = mini_temp_graph_svg(r.temperature_history)

    melt_status_el = document.getElementById(f"{prefix}-melt-status-display")
    melt_status_el.innerText = "Melting" if r.is_melting() else "Stable"
    melt_status_el.className = "region-melt-status" + (
        " melt-status--active" if r.is_melting() else ""
    )

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


def render_info_page():
    panel = document.getElementById("info-page-panel")
    panel.hidden = not info_page_open
    toggle_button = document.getElementById("info-page-toggle-button")
    toggle_button.innerText = "Hide The Real Story" if info_page_open else "The Real Story"
    if not info_page_open:
        return
    document.getElementById("info-page-framing").innerText = INFO_PAGE["framing"]
    document.getElementById("info-page-tie-in").innerText = INFO_PAGE["mechanic_tie_in"]
    list_el = document.getElementById("info-page-sources")
    list_el.innerHTML = ""
    for source in INFO_PAGE["sources"]:
        item = document.createElement("li")
        item.className = "info-page-source"
        link = document.createElement("a")
        link.href = source["url"]
        link.target = "_blank"
        link.rel = "noopener noreferrer"
        link.innerText = source["label"]
        item.appendChild(link)
        note = document.createElement("p")
        note.className = "info-page-source-note"
        note.innerText = source["note"]
        item.appendChild(note)
        list_el.appendChild(item)


def on_toggle_info_page(event=None):
    global info_page_open
    info_page_open = not info_page_open
    render()


def render():
    render_info_page()
    document.getElementById("round-display").innerText = f"Round {region.round_number}"
    document.getElementById("funds-display").innerText = f"Funds: {region.funds:.0f}"
    document.getElementById("temperature-display").innerText = (
        f"Global temperature: +{region.temperature:.1f}°"
    )
    document.getElementById("rise-rate-display").innerText = (
        f"Current warming rate: {region.current_rise_rate():.2f}°/round"
    )
    melt_status_el = document.getElementById("melt-status-display")
    melt_status_el.innerText = (
        "Permafrost is actively melting — methane feedback is accelerating warming."
        if region.is_melting()
        else "Permafrost stable — no feedback yet."
    )
    melt_status_el.className = "comparison-message" + (
        " melt-status--active" if region.is_melting() else ""
    )

    game_el = document.getElementById("game")
    if region.just_started_melting:
        game_el.className = "tipping-flash"
        region.just_started_melting = False
    else:
        game_el.className = ""
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

    for prefix, r in SECONDARY_REGIONS.items():
        render_secondary_region(prefix, r)


def _make_invest_handler(category):
    def handler(event=None):
        region.invest(category)
        render()
    return handler


def _make_secondary_invest_handler(prefix, category):
    def handler(event=None):
        SECONDARY_REGIONS[prefix].invest(category)
        render()
    return handler


def on_advance_round(event=None):
    region.advance_round()
    for r in SECONDARY_REGIONS.values():
        r.advance_round()
    render()


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
    document.getElementById("advance-round-button").addEventListener(
        "click", create_proxy(on_advance_round)
    )
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    render()


setup()
