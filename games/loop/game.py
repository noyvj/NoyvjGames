"""Loop — Circular Economy & Overconsumption Game.

Runs in-browser via Pyodide. Milestone 2: circularity investments —
repair networks, reuse systems, and recycling loops that each supply
a chunk of the production target without new extraction. Investing
enough in any combination can push new extraction to zero: a fully
closed loop, the clearest win-state in the whole hub.
"""

import copy

import info_page
from js import document
from pyodide.ffi import create_proxy

STARTING_FUNDS = 300.0

# Every cycle, the chain must supply this many units of manufactured
# goods — a fixed target, not something that grows, so "close the loop"
# stays a meaningful, reachable state rather than a moving target.
PRODUCTION_TARGET = 50.0

EXTRACTION_COST_PER_UNIT = 2.0
SALE_PRICE_PER_UNIT = 5.0

# Circularity investments each add fixed supply toward the production
# target, sourced from repaired/reused/recycled material instead of new
# extraction. Recycling loops are the most potent (closest to the
# disposal end of the chain, recovering material that would otherwise be
# pure waste); repair networks the least (they only extend use-phase,
# not recover material outright) — reuse sits in between.
CIRCULARITY_INVESTMENTS = {
    "repair": {"cost": 20, "supply_per_unit": 3.0, "label": "Repair Networks", "icon": "\U0001F527"},
    "reuse": {"cost": 25, "supply_per_unit": 4.0, "label": "Reuse Systems", "icon": "\U0001F504"},
    "recycle": {"cost": 30, "supply_per_unit": 5.0, "label": "Recycling Loops", "icon": "♻️"},
}

# Environmental cost meter: cumulative new extraction leaves behind
# lasting land/emissions damage, which in turn makes further extraction
# progressively more expensive (degraded sites cost more to work) — a
# soft, compounding consequence with no hard fail-state. Circularity
# investment is the only way to avoid feeding this meter at all, since
# it substitutes for new extraction rather than merely paying its cost.
ENVIRONMENTAL_DAMAGE_SCALE = 500.0
MAX_COST_MULTIPLIER = 2.5

# Scoring: funds plus a direct bonus for lifetime circular share, so
# closing the loop is rewarded on its own terms, not just as a side
# effect of dodging rising extraction cost (though it dodges that too —
# simulation shows a circularity-first strategy roughly triples the
# funds of a pure-extraction strategy over 15 cycles, since escalating
# damage cost never gets the chance to compound).
CIRCULARITY_BONUS_WEIGHT = 300.0

# Iteration-pass additions: flavor naming so the abstract chain reads as
# a concrete product category, and a rough real-world circularity
# benchmark for context. The benchmark is an illustrative ballpark
# (global circular-economy reporting has put overall material
# circularity in the high single digits in recent years), not a
# precise or authoritative figure — framed that way in the UI.
GOODS_LABEL = "electronics"
REAL_WORLD_CIRCULARITY_BENCHMARK = 0.07

# Iteration Pass 2 — trade network: a basic bidirectional link with one
# neighboring system, not a full second economy. Import: investing in
# the link brings in reuse capacity from outside, counted toward
# closing the loop alongside repair/reuse/recycle. Export: whenever
# internal circularity investment produces more supply than this
# cycle's own production target needs, that surplus is sold outward to
# the neighbor rather than wasted — a natural thing to do with "too
# much" circularity once the loop's already closed internally.
TRADE_LINK_COST = 25
IMPORT_SUPPLY_PER_UNIT = 4.0
EXPORT_PRICE_PER_UNIT = 3.0

# Iteration Pass 2 — single-item vignette: a concrete side-story
# following one representative product, alongside the abstract chain
# view, for a player who doesn't naturally read a flow diagram.
VIGNETTE_ITEM = "a phone"


class ChainState:
    def __init__(self):
        self.cycle_number = 1
        self.funds = STARTING_FUNDS
        self.total_extracted = 0.0
        self.total_produced = 0.0
        self.circularity_investment = {c: 0 for c in CIRCULARITY_INVESTMENTS}
        self.circular_fraction_log = []
        self.trade_link_investment = 0

    def internal_circular_supply(self):
        """Units of this cycle's production target met by repair/reuse/
        recycling instead of new extraction — the chain's own capacity,
        before anything crossing in from the trade network."""
        return sum(
            self.circularity_investment[c] * CIRCULARITY_INVESTMENTS[c]["supply_per_unit"]
            for c in CIRCULARITY_INVESTMENTS
        )

    def imported_supply(self):
        return self.trade_link_investment * IMPORT_SUPPLY_PER_UNIT

    def circular_supply(self):
        """Total supply toward closing the loop: internal circularity
        plus whatever the trade link imports from the neighboring
        system."""
        return self.internal_circular_supply() + self.imported_supply()

    def exportable_surplus(self):
        """Internal circular supply beyond what this cycle's own
        production target needs — sold outward to the neighboring
        system for extra revenue rather than going to waste. Only
        internal supply counts; imported supply isn't re-exported."""
        return max(0.0, self.internal_circular_supply() - PRODUCTION_TARGET)

    def new_extraction_needed(self):
        """The straight-line default: whatever circular supply doesn't
        cover has to come from newly extracted raw material. Floored at
        zero — enough circularity investment closes the loop entirely."""
        return max(0.0, PRODUCTION_TARGET - self.circular_supply())

    def invest_trade_link(self):
        if self.funds < TRADE_LINK_COST:
            return False
        self.funds -= TRADE_LINK_COST
        self.trade_link_investment += 1
        return True

    def is_loop_closed(self):
        return self.new_extraction_needed() <= 0.0

    def circular_fraction_this_cycle(self):
        """0..1 — the share of *this* cycle's production target that
        circularity investment covers, capped at 1 (fully closed)."""
        return (PRODUCTION_TARGET - self.new_extraction_needed()) / PRODUCTION_TARGET

    def lifetime_circular_fraction(self):
        """0..1 — the share of all production ever run through the chain
        that came from circular supply rather than new extraction."""
        if self.total_produced == 0:
            return 0.0
        circular_total = self.total_produced - self.total_extracted
        return circular_total / self.total_produced

    def invest_circularity(self, measure):
        cost = CIRCULARITY_INVESTMENTS[measure]["cost"]
        if self.funds < cost:
            return False
        self.funds -= cost
        self.circularity_investment[measure] += 1
        return True

    def damage_fraction(self):
        """0..1 — cumulative land/emissions damage from lifetime new
        extraction, capped so extraction never becomes literally
        impossible, just steadily more expensive."""
        return min(1.0, self.total_extracted / ENVIRONMENTAL_DAMAGE_SCALE)

    def extraction_cost_multiplier(self):
        return 1.0 + self.damage_fraction() * (MAX_COST_MULTIPLIER - 1.0)

    def advance_cycle(self):
        extraction = self.new_extraction_needed()
        cost = extraction * EXTRACTION_COST_PER_UNIT * self.extraction_cost_multiplier()
        revenue = PRODUCTION_TARGET * SALE_PRICE_PER_UNIT
        export_revenue = self.exportable_surplus() * EXPORT_PRICE_PER_UNIT
        self.funds += revenue - cost + export_revenue
        self.circular_fraction_log.append(self.circular_fraction_this_cycle())
        self.total_extracted += extraction
        self.total_produced += PRODUCTION_TARGET
        self.cycle_number += 1

    def score(self):
        """Profitability plus a direct reward for lifetime circular
        share — a fully closed, sustained loop earns the maximum bonus
        on top of whatever funds it generated."""
        return self.funds + self.lifetime_circular_fraction() * CIRCULARITY_BONUS_WEIGHT

    def circular_trend(self):
        """Compares the first half of cycles run to the second half —
        the hope-angle payoff: a visibly rising circular share is the
        direct reward for early circularity investment, not just a good
        final number."""
        n = len(self.circular_fraction_log)
        if n < 4:
            return None
        half = n // 2
        first_half_avg = sum(self.circular_fraction_log[:half]) / half
        second_half_avg = sum(self.circular_fraction_log[half:]) / (n - half)
        return first_half_avg, second_half_avg


chain = ChainState()


def circular_trend_message(trend):
    if trend is None:
        return "Not enough cycles yet to show a trend."
    first_half_avg, second_half_avg = trend
    first_pct, second_pct = first_half_avg * 100, second_half_avg * 100
    if second_half_avg > first_half_avg:
        return f"Your chain is closing the loop over time ({first_pct:.0f}% → {second_pct:.0f}% circular) — the redesign is paying off."
    if second_half_avg < first_half_avg:
        return f"Your chain has drifted back toward a straight line ({first_pct:.0f}% → {second_pct:.0f}% circular)."
    return f"Your chain's circular share has held steady at {second_pct:.0f}%."


def real_world_comparison_message(lifetime_fraction):
    """Iteration-pass addition: a rough, honestly-hedged real-world
    comparison point for the player's lifetime circular share."""
    pct = lifetime_fraction * 100
    benchmark_pct = REAL_WORLD_CIRCULARITY_BENCHMARK * 100
    if lifetime_fraction > REAL_WORLD_CIRCULARITY_BENCHMARK:
        return (
            f"Your chain is running at {pct:.0f}% circular — well above the "
            f"roughly {benchmark_pct:.0f}% average estimated for real-world material "
            f"circularity today (a ballpark figure, not a precise benchmark)."
        )
    return (
        f"Your chain is running at {pct:.0f}% circular, versus a roughly "
        f"{benchmark_pct:.0f}% estimated real-world average today (a ballpark figure, "
        f"not a precise benchmark)."
    )


def vignette_message(fraction):
    """A concrete, one-item side-story tracking the same underlying
    circular_fraction_this_cycle() the abstract chain view already
    shows — makes the abstraction tangible for a player who doesn't
    naturally read a flow diagram."""
    if fraction >= 1.0:
        return (
            f"Follow {VIGNETTE_ITEM}: it was repaired once, then eventually recycled — "
            "its materials became part of the casing for the next one off the line."
        )
    if fraction >= 0.5:
        return (
            f"Follow {VIGNETTE_ITEM}: it gets used, and there's a good chance it comes "
            "back through repair or recycling when its owner is done with it."
        )
    if fraction > 0.0:
        return (
            f"Follow {VIGNETTE_ITEM}: it gets used, then thrown away — though a little of "
            "what's inside it might still come back as recycled material someday."
        )
    return (
        f"Follow {VIGNETTE_ITEM}: mined, made, used once, thrown away. Nothing about it "
        "comes back."
    )


def chain_flow_message(fraction):
    if fraction <= 0.0:
        return "Straight line: 100% of production needs new extraction."
    if fraction >= 1.0:
        return "Loop closed: 100% of production comes from repair, reuse & recycling. No new extraction needed."
    return f"{fraction * 100:.0f}% of the chain is looping back — {100 - fraction * 100:.0f}% still needs new extraction."


# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
INFO_PAGE = {
    "framing": (
        "Most of the modern economy still runs in a straight line — "
        "extract, make, use, discard — even though a genuinely circular "
        "alternative (eliminate waste, circulate materials, regenerate "
        "nature) is well-documented and already improving outcomes where "
        "it's tried. Loop's chain-visualization mechanic is a direct "
        "simplification of that real framework."
    ),
    "mechanic_tie_in": (
        "Loop's three circularity investments (repair, reuse, recycling) "
        "map onto the three real circular-economy design principles this "
        "whole field is built around."
    ),
    "sources": [
        {
            "label": "Ellen MacArthur Foundation — The Circular Economy: Definition & Model Explained",
            "url": "https://www.ellenmacarthurfoundation.org/topics/circular-economy-introduction/overview",
            "note": "The standard-setting definition of circular economy — Loop's core mechanic is a direct translation of this framework.",
        },
        {
            "label": "Ellen MacArthur Foundation — Circular Economy Principles",
            "url": "https://www.ellenmacarthurfoundation.org/circular-economy-principles",
            "note": "Breaks circularity into three concrete design principles, structuring Loop's three types of circularity investment.",
        },
        {
            "label": "Mongabay — The circular economy: Sustainable solutions to solve planetary overshoot?",
            "url": "https://news.mongabay.com/2023/07/the-circular-economy-sustainable-solutions-to-solve-planetary-overshoot/",
            "note": "Accessible journalism with a concrete example (recycled steel's emissions/water savings) for the framing paragraph.",
        },
        {
            "label": "PMC/NCBI — Waste metrics in the framework of circular economy",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10693739/",
            "note": "A more academic treatment connecting overconsumption directly to circular economy metrics.",
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


def render():
    render_info_page()
    fraction = chain.circular_fraction_this_cycle()
    flow_el = document.getElementById("chain-flow")
    flow_el.className = "chain-flow chain-flow--closed" if fraction >= 1.0 else "chain-flow"
    extract_stage = document.getElementById("stage-extract")
    extract_stage.className = "chain-stage chain-stage--inactive" if fraction >= 1.0 else "chain-stage"
    document.getElementById("chain-flow-message").innerText = chain_flow_message(fraction)

    return_flow_row = document.getElementById("return-flow-row")
    return_flow_row.style.opacity = f"{fraction:.2f}"

    import_fraction = min(1.0, chain.imported_supply() / PRODUCTION_TARGET)
    import_flow_row = document.getElementById("import-flow-row")
    import_flow_row.style.opacity = f"{import_fraction:.2f}"

    document.getElementById("vignette-display").innerText = vignette_message(fraction)

    document.getElementById("cycle-display").innerText = f"Cycle {chain.cycle_number}"
    document.getElementById("funds-display").innerText = f"Funds: {chain.funds:.0f}"
    document.getElementById("extraction-display").innerText = (
        "Loop closed — no new extraction needed" if chain.is_loop_closed()
        else f"New extraction this cycle: {chain.new_extraction_needed():.0f} units of raw material for {GOODS_LABEL}"
    )
    document.getElementById("production-display").innerText = (
        f"Production target: {PRODUCTION_TARGET:.0f} units of {GOODS_LABEL} per cycle"
    )
    document.getElementById("total-extracted-display").innerText = (
        f"Total raw material extracted (lifetime): {chain.total_extracted:.0f} units"
    )
    document.getElementById("damage-display").innerText = (
        f"Environmental damage: {chain.damage_fraction() * 100:.0f}% "
        f"(extraction cost x{chain.extraction_cost_multiplier():.2f})"
    )
    document.getElementById("damage-bar").style.width = f"{chain.damage_fraction() * 100:.0f}%"

    document.getElementById("circular-fraction-display").innerText = (
        f"Circular this cycle: {chain.circular_fraction_this_cycle() * 100:.0f}%"
    )
    document.getElementById("lifetime-circular-display").innerText = (
        f"Lifetime circular share: {chain.lifetime_circular_fraction() * 100:.0f}%"
    )
    document.getElementById("circular-bar").style.width = (
        f"{chain.circular_fraction_this_cycle() * 100:.0f}%"
    )
    document.getElementById("score-display").innerText = f"Score: {chain.score():.0f}"
    document.getElementById("trend-display").innerText = circular_trend_message(chain.circular_trend())
    document.getElementById("real-world-comparison-display").innerText = (
        real_world_comparison_message(chain.lifetime_circular_fraction())
    )

    for measure, spec in CIRCULARITY_INVESTMENTS.items():
        document.getElementById(f"{measure}-name").innerText = f"{spec['icon']} {spec['label']}"
        document.getElementById(f"{measure}-count").innerText = str(
            chain.circularity_investment[measure]
        )
        button = document.getElementById(f"{measure}-invest-button")
        button.innerText = f"{spec['label']} ({spec['cost']})"
        button.disabled = chain.funds < spec["cost"]

    document.getElementById("trade-link-count").innerText = str(chain.trade_link_investment)
    trade_link_button = document.getElementById("trade-link-invest-button")
    trade_link_button.innerText = f"Trade Link ({TRADE_LINK_COST})"
    trade_link_button.disabled = chain.funds < TRADE_LINK_COST
    document.getElementById("trade-network-display").innerText = (
        f"Importing {chain.imported_supply():.0f} units/cycle from the trade network; "
        f"exporting {chain.exportable_surplus():.0f} units/cycle of surplus this cycle."
    )


def on_advance_cycle(event=None):
    chain.advance_cycle()
    render()


def _make_circularity_handler(measure):
    def handler(event=None):
        chain.invest_circularity(measure)
        render()
    return handler


def on_invest_trade_link(event=None):
    chain.invest_trade_link()
    render()


# SAVE-BUTTON-INTEGRATION.md contract for the shared shared/save-widget.js:
# get_state()/load_state() are the per-game contract the widget calls
# (get_state()/load_state() on save/load respectively). SOL is the
# reference integration for this contract; Loop follows the same
# thin/direct pattern rather than reinventing it.


def get_state():
    """Return every piece of Loop's tracked state as a plain, JSON-safe
    dict. `chain` is the one stateful object in the game — its dict/list
    attributes (`circularity_investment`, `circular_fraction_log`) are
    deep-copied so the saved snapshot doesn't alias a live reference;
    continued play after saving would otherwise silently mutate it, same
    reasoning as SOL's serialize_state()."""
    return {
        "cycle_number": chain.cycle_number,
        "funds": chain.funds,
        "total_extracted": chain.total_extracted,
        "total_produced": chain.total_produced,
        "circularity_investment": copy.deepcopy(chain.circularity_investment),
        "circular_fraction_log": copy.deepcopy(chain.circular_fraction_log),
        "trade_link_investment": chain.trade_link_investment,
    }


def load_state(data):
    """Take the dict from get_state() (possibly from a previous session)
    and restore `chain` to that point — the exact inverse of
    get_state() — then re-render so the UI reflects the loaded state
    immediately.

    `circularity_investment` is merged key-by-key against the current
    CIRCULARITY_INVESTMENTS schema rather than wholesale-replaced: every
    render() reads chain.circularity_investment[measure] for every measure
    currently in CIRCULARITY_INVESTMENTS, so a snapshot missing a key (an
    older/hand-edited save) would otherwise leave that key absent entirely
    and crash the very next render with a KeyError. Merging also drops any
    stale key no longer in CIRCULARITY_INVESTMENTS (e.g. a retired
    measure) instead of letting it linger in the live dict forever."""
    chain.cycle_number = data["cycle_number"]
    chain.funds = data["funds"]
    chain.total_extracted = data["total_extracted"]
    chain.total_produced = data["total_produced"]
    saved_investment = data["circularity_investment"]
    chain.circularity_investment = {
        measure: saved_investment.get(measure, 0) for measure in CIRCULARITY_INVESTMENTS
    }
    chain.circular_fraction_log = list(data["circular_fraction_log"])
    # A save from before the trade-network field existed (Pass 2) won't
    # have this key — default to 0 (a fresh chain's own starting value)
    # rather than raising KeyError and failing the whole load.
    chain.trade_link_investment = data.get("trade_link_investment", 0)
    render()
    return True


def setup():
    document.getElementById("advance-cycle-button").addEventListener(
        "click", create_proxy(on_advance_cycle)
    )
    for measure in CIRCULARITY_INVESTMENTS:
        document.getElementById(f"{measure}-invest-button").addEventListener(
            "click", create_proxy(_make_circularity_handler(measure))
        )
    document.getElementById("trade-link-invest-button").addEventListener(
        "click", create_proxy(on_invest_trade_link)
    )
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    render()


setup()
