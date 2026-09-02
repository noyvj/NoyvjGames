"""Herd — Industrial Agriculture & Methane Game.

Runs in-browser via Pyodide. Milestone 1: the core farm loop — herd
growth, income, and round progression. The methane meter (coupled to
herd size), decoupling investments, and soft consequences land in
later milestones.
"""

from js import document
from pyodide.ffi import create_proxy

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


class FarmState:
    def __init__(self):
        self.round_number = 1
        self.funds = STARTING_FUNDS
        self.herd_size = 0
        self.methane = 0.0
        self.decoupling_investment = {m: 0 for m in DECOUPLING_MEASURES}
        self.plant_pivot_investment = 0

    def _efficiency_coupling_ratio(self):
        """Methane produced per herd unit, per round, from the feed/caps/
        capture efficiency measures alone — floored so it never hits zero."""
        reduction = sum(
            self.decoupling_investment[m] * DECOUPLING_MEASURES[m]["ratio_reduction"]
            for m in DECOUPLING_MEASURES
        )
        return max(MIN_COUPLING_RATIO, BASE_COUPLING_RATIO - reduction)

    def plant_based_fraction(self):
        return min(MAX_PLANT_BASED_FRACTION, self.plant_pivot_investment * PLANT_PIVOT_FRACTION_PER_UNIT)

    def coupling_ratio(self):
        """The efficiency-measure ratio, further blended down by however
        much of the herd's output has pivoted to (near-zero-methane)
        plant-based production. Same public method every other Pass 1
        mechanic already reads from, so the gauge shows one unified
        number regardless of which lever moved it."""
        base = self._efficiency_coupling_ratio()
        fraction = self.plant_based_fraction()
        blended_multiplier = (1 - fraction) + fraction * PLANT_BASED_EMISSIONS_MULTIPLIER
        return max(MIN_COUPLING_RATIO, base * blended_multiplier)

    def invest_plant_pivot(self):
        if self.funds < PLANT_PIVOT_COST:
            return False
        self.funds -= PLANT_PIVOT_COST
        self.plant_pivot_investment += 1
        return True

    def methane_this_round(self):
        return self.herd_size * self.coupling_ratio()

    def grow_herd(self):
        if self.funds < HERD_GROWTH_COST:
            return False
        self.funds -= HERD_GROWTH_COST
        self.herd_size += 1
        return True

    def invest_decoupling(self, measure):
        cost = DECOUPLING_MEASURES[measure]["cost"]
        if self.funds < cost:
            return False
        self.funds -= cost
        self.decoupling_investment[measure] += 1
        return True

    def pressure_fraction(self):
        """Fraction of income lost to market/regulatory pressure and
        degraded yields, scaling with sustained methane. Capped so income
        never fully vanishes — a bad strategy gets worse, not impossible."""
        return min(MAX_PRESSURE, self.methane / PRESSURE_SCALE)

    def advance_round(self):
        fraction = self.plant_based_fraction()
        income_multiplier = (1 - fraction) + fraction * PLANT_BASED_INCOME_MULTIPLIER
        raw_income = self.herd_size * HERD_INCOME_PER_UNIT * income_multiplier
        self.funds += raw_income * (1 - self.pressure_fraction())
        self.methane += self.methane_this_round()
        self.round_number += 1

    def score(self):
        """Profitability weighted against sustained emissions — rewards
        decoupling specifically, not just growth or just restraint."""
        return self.funds - self.methane * METHANE_PENALTY_WEIGHT


farm = FarmState()


# REVIEW(reuse): byte-identical implementation in games/canopy/game.py.
# Low urgency at only 2 occurrences, but worth a shared color-utility module
# if a third game ever needs a hex-color lerp.
def _lerp_color(start_hex, end_hex, t):
    """Linear-interpolates between two #rrggbb colors at t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(start_hex[1:3], 16), int(start_hex[3:5], 16), int(start_hex[5:7], 16)
    r2, g2, b2 = int(end_hex[1:3], 16), int(end_hex[3:5], 16), int(end_hex[5:7], 16)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b = round(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def coupling_gauge_svg(fraction):
    """Semi-circle dial gauge: 0 = fully decoupled (green), 1 = fully
    coupled at baseline (red). Iteration-pass addition — the single
    most prominent UI element, replacing a plain ratio number with an
    at-a-glance dial for the mechanic the whole lesson depends on."""
    fraction = max(0.0, min(1.0, fraction))
    color = _lerp_color(GAUGE_LOW_COLOR, GAUGE_HIGH_COLOR, fraction)
    dash = fraction * 100
    return (
        '<svg viewBox="0 0 120 66" class="coupling-gauge-svg">'
        '<path d="M 10 60 A 50 50 0 0 1 110 60" class="gauge-track" pathLength="100" />'
        f'<path d="M 10 60 A 50 50 0 0 1 110 60" class="gauge-fill" pathLength="100" '
        f'stroke="{color}" stroke-dasharray="{dash:.1f} 100" />'
        "</svg>"
    )


# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
INFO_PAGE = {
    "framing": (
        "Livestock digestion is a major, distinct source of methane — a "
        "gas that traps far more heat than CO2 in the short term, but "
        "also breaks down faster, which makes reducing it one of the "
        "fastest-acting climate levers available. Herd's coupling gauge "
        "and its plant-based pivot are built around that real reduction "
        "pathway."
    ),
    "mechanic_tie_in": (
        "Herd's plant-based pivot mechanic is grounded in a real "
        "documented case — a roughly 42% methane-intensity reduction "
        "achieved through better farm practices — showing decoupling "
        "herd size from methane is achievable, not hypothetical."
    ),
    "sources": [
        {
            "label": "FAO — Livestock and enteric methane",
            "url": "https://www.fao.org/in-action/enteric-methane/en",
            "note": "The definitive real-world figures behind Herd's core mechanic — agriculture's share of methane emissions and where it comes from.",
        },
        {
            "label": "Clean Air Task Force — Accelerating climate solutions in agriculture",
            "url": "https://www.catf.us/2024/10/accelerating-climate-solutions-agriculture-why-reducing-methane-livestock-urgent-opportunity/",
            "note": "Documents a real ~42% methane-intensity reduction from better farm practices — directly supports Herd's decoupling hope angle.",
        },
        {
            "label": "US EPA — Agriculture and Aquaculture: Food for Thought",
            "url": "https://www.epa.gov/snep/agriculture-and-aquaculture-food-thought",
            "note": "Explains why methane's short-lived-but-potent warming profile makes it a distinct lever from CO2.",
        },
    ],
}
info_page_open = False


# REVIEW(reuse): render_info_page()/on_toggle_info_page() (~25+4 lines) are\n# logically identical across all 8 climate games (canopy, grid, tide,\n# aftermath, herd, thaw, loop, drift) -- only the per-game INFO_PAGE data\n# dict differs. Matching HTML/CSS (.info-page-* rules, #info-page-panel\n# markup) is duplicated the same way. A shared JS-driven widget or small\n# shared Python helper, driven by each game's own INFO_PAGE dict -- the same\n# pattern already used for shared/save-widget.js -- would remove ~250 lines\n# of duplication.
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
    coupling_fraction = farm.coupling_ratio() / BASE_COUPLING_RATIO
    document.getElementById("coupling-gauge").innerHTML = coupling_gauge_svg(coupling_fraction)
    document.getElementById("coupling-gauge-label").innerText = (
        f"Emissions per herd unit: {farm.coupling_ratio():.2f} methane/round"
    )

    document.getElementById("haze-overlay").style.opacity = (
        f"{(farm.pressure_fraction() / MAX_PRESSURE) * MAX_HAZE_OPACITY:.3f}"
    )

    document.getElementById("round-display").innerText = f"Round {farm.round_number}"
    document.getElementById("funds-display").innerText = f"Funds: {farm.funds:.0f}"
    document.getElementById("herd-display").innerText = f"Herd size: {farm.herd_size}"
    document.getElementById("methane-display").innerText = f"Methane: {farm.methane:.0f}"
    document.getElementById("coupling-display").innerText = (
        f"Coupling ratio: {farm.coupling_ratio():.2f} methane/herd/round"
    )
    document.getElementById("pressure-display").innerText = (
        f"Market/regulatory pressure: {farm.pressure_fraction() * 100:.0f}% income loss"
    )
    document.getElementById("methane-bar").style.width = (
        f"{min(1.0, farm.methane / PRESSURE_SCALE) * 100:.0f}%"
    )
    document.getElementById("score-display").innerText = f"Score: {farm.score():.0f}"

    grow_button = document.getElementById("grow-herd-button")
    grow_button.innerText = f"Grow Herd ({HERD_GROWTH_COST})"
    grow_button.disabled = farm.funds < HERD_GROWTH_COST

    for measure, spec in DECOUPLING_MEASURES.items():
        document.getElementById(f"{measure}-name").innerText = f"{spec['icon']} {spec['label']}"
        document.getElementById(f"{measure}-count").innerText = str(
            farm.decoupling_investment[measure]
        )
        button = document.getElementById(f"{measure}-invest-button")
        button.innerText = f"{spec['label']} ({spec['cost']})"
        button.disabled = farm.funds < spec["cost"]

    decoupled_fraction = 1 - (farm.coupling_ratio() / BASE_COUPLING_RATIO)
    document.getElementById("decoupling-summary-display").innerText = (
        f"Decoupled: {decoupled_fraction * 100:.0f}% below baseline emissions per herd unit"
    )

    plant_fraction = farm.plant_based_fraction()
    document.getElementById("plant-pivot-count").innerText = str(farm.plant_pivot_investment)
    document.getElementById("plant-pivot-display").innerText = (
        f"{plant_fraction * 100:.0f}% of output shifted to plant-based production"
    )
    plant_pivot_button = document.getElementById("plant-pivot-invest-button")
    plant_pivot_button.innerText = f"Plant-Based Pivot ({PLANT_PIVOT_COST})"
    plant_pivot_button.disabled = farm.funds < PLANT_PIVOT_COST or plant_fraction >= MAX_PLANT_BASED_FRACTION


def on_grow_herd(event=None):
    farm.grow_herd()
    render()


def _make_decoupling_handler(measure):
    def handler(event=None):
        farm.invest_decoupling(measure)
        render()
    return handler


def on_invest_plant_pivot(event=None):
    farm.invest_plant_pivot()
    render()


def on_advance_round(event=None):
    farm.advance_round()
    render()


# SAVE-BUTTON-INTEGRATION.md contract for the shared shared/save-widget.js:
# get_state() returns every module-level mutable game-state field as one
# plain, JSON-safe dict, and load_state() is its exact inverse. SOL is the
# reference integration for this contract. decoupling_investment is copied
# (not handed back by reference) so continued play after taking a
# "snapshot" can't silently mutate it, same reasoning as SOL's
# serialize_state() docstring. info_page_open is deliberately excluded —
# it's a cosmetic panel toggle, not tracked game progress.
def get_state():
    return {
        "round_number": farm.round_number,
        "funds": farm.funds,
        "herd_size": farm.herd_size,
        "methane": farm.methane,
        "decoupling_investment": dict(farm.decoupling_investment),
        "plant_pivot_investment": farm.plant_pivot_investment,
    }


def load_state(data):
    farm.round_number = data["round_number"]
    farm.funds = data["funds"]
    farm.herd_size = data["herd_size"]
    farm.methane = data["methane"]
    # Merge key-by-key rather than replacing the dict outright: a save
    # missing a measure (an older save format from before that measure
    # existed, or a hand-edited/corrupted payload) must not wipe that
    # measure's key out of the live dict entirely -- render() and
    # _efficiency_coupling_ratio() both do decoupling_investment[measure]
    # for every measure in DECOUPLING_MEASURES unconditionally, so a
    # missing key would crash the game on the very next render/round.
    farm.decoupling_investment = {m: 0 for m in DECOUPLING_MEASURES}
    farm.decoupling_investment.update(data["decoupling_investment"])
    farm.plant_pivot_investment = data["plant_pivot_investment"]
    render()
    return True


def setup():
    document.getElementById("grow-herd-button").addEventListener(
        "click", create_proxy(on_grow_herd)
    )
    document.getElementById("advance-round-button").addEventListener(
        "click", create_proxy(on_advance_round)
    )
    for measure in DECOUPLING_MEASURES:
        document.getElementById(f"{measure}-invest-button").addEventListener(
            "click", create_proxy(_make_decoupling_handler(measure))
        )
    document.getElementById("plant-pivot-invest-button").addEventListener(
        "click", create_proxy(on_invest_plant_pivot)
    )
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    render()


setup()
