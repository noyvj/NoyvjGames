"""Loop — Circular Economy & Overconsumption Game.

Runs in-browser via Pyodide. Milestone 2: circularity investments —
repair networks, reuse systems, and recycling loops that each supply
a chunk of the production target without new extraction. Investing
enough in any combination can push new extraction to zero: a fully
closed loop, the clearest win-state in the whole hub.

Post-milestone backlog pass (planning/TODO.md "Per-game: Loop" H1-H20,
H16 parked in LATER.md) added: a goods-category picker at game start
(H2/H20), a second, differently-priced trade partner (H8), a "Start New
Chain" reset control (H7), a closed-loop streak tracker (H19), a "time to
close the loop" projection (H6), decorative loop-ring highlighting tied
to real investment (H5), cost-per-unit-of-supply + running-contribution
readouts (H4/H15), a live score breakdown (H17), alternate real-world
sector comparisons (H9), a hard-ceiling note on the cost multiplier
(H10), a lighter first-cycle message (H11), alternate vignette phrasings
(H14), a first-time-closed-loop banner (H3), and reactive visual pulses
on funds/trade-network changes (H12/H18) — plus the hub-wide achievements
framework (ACHIEVEMENTS-SYSTEM-DESIGN.md), and an H1 bug fix (see
`ChainState.exportable_surplus()`'s docstring).
"""

import copy
import json
import math

import info_page
from js import document, setTimeout
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
# H10: MAX_COST_MULTIPLIER is a hard ceiling -- extraction cost never
# rises past this, no matter how much cumulative damage accumulates
# (see the damage info-toggle text in index.html, and
# extraction_cost_multiplier() below, which is a strict min(1.0, ...)*
# scale, mathematically incapable of exceeding it).
ENVIRONMENTAL_DAMAGE_SCALE = 500.0
MAX_COST_MULTIPLIER = 2.5

# Scoring: funds plus a direct bonus for lifetime circular share, so
# closing the loop is rewarded on its own terms, not just as a side
# effect of dodging rising extraction cost (though it dodges that too —
# simulation shows a circularity-first strategy roughly triples the
# funds of a pure-extraction strategy over 15 cycles, since escalating
# damage cost never gets the chance to compound).
CIRCULARITY_BONUS_WEIGHT = 300.0

# H2/H20: a small, pickable set of goods-flavor sets rather than a single
# hardcoded "electronics" framing. Chosen once at game start (while
# total_produced == 0 -- see render()'s goods-category-picker section)
# and locked in until "Start New Chain" resets back to a fresh pick.
# GOODS_LABEL/VIGNETTE_ITEM are kept as module constants (equal to the
# default category's own values) purely so old tests/callers that read
# them directly keep working -- current_goods_label()/current_vignette_item()
# below are what render()/vignette_message() actually use.
GOODS_CATEGORIES = {
    "electronics": {"label": "electronics", "vignette_item": "a phone", "icon": "\U0001F4F1"},
    "clothing": {"label": "clothing", "vignette_item": "a jacket", "icon": "\U0001F455"},
    "furniture": {"label": "furniture", "vignette_item": "a chair", "icon": "\U0001FA91"},
}
DEFAULT_GOODS_CATEGORY = "electronics"
GOODS_LABEL = GOODS_CATEGORIES[DEFAULT_GOODS_CATEGORY]["label"]
VIGNETTE_ITEM = GOODS_CATEGORIES[DEFAULT_GOODS_CATEGORY]["vignette_item"]

# Iteration-pass additions: flavor naming so the abstract chain reads as
# a concrete product category, and a rough real-world circularity
# benchmark for context. The benchmark is an illustrative ballpark
# (global circular-economy reporting has put overall material
# circularity in the high single digits in recent years), not a
# precise or authoritative figure — framed that way in the UI.
REAL_WORLD_CIRCULARITY_BENCHMARK = 0.07

# H9: a couple of alternate real-world sector ballparks beyond the single
# static benchmark above, so the comparison doesn't lean on one figure
# alone. Same "illustrative, not authoritative" hedge as
# real_world_comparison_message() -- these are ballpark figures pulled
# from general circular-economy reporting, not a precise dataset.
SECTOR_COMPARISONS = [
    ("textiles & apparel", 0.01),
    ("plastics", 0.09),
    ("metals", 0.33),
]

# Iteration Pass 2 — trade network: a basic bidirectional link with one
# neighboring system, not a full second economy. Import: investing in
# the link brings in reuse capacity from outside, counted toward
# closing the loop alongside repair/reuse/recycle. Export: whenever
# this chain produces more supply than this cycle's own production
# target needs, that surplus is sold outward to the neighbor rather
# than wasted.
TRADE_LINK_COST = 25
IMPORT_SUPPLY_PER_UNIT = 4.0
EXPORT_PRICE_PER_UNIT = 3.0

# H8: a second, differently-priced trading partner. The Regional
# Distributor costs more per investment but supplies more import
# capacity per unit -- a genuine cost/supply trade-off against the
# original Local Trade Link, not just a reskinned duplicate. Export
# stays a single flat rate (EXPORT_PRICE_PER_UNIT above): the surplus is
# sold outward to "the trade network" collectively, not to a specific
# chosen partner, so this addition only varies the *import* side, which
# is the side H8 actually asks for ("trading partner" you invest in).
REGIONAL_TRADE_COST = 40
REGIONAL_IMPORT_SUPPLY_PER_UNIT = 6.0

# Iteration Pass 2 — single-item vignette: a concrete side-story
# following one representative product, alongside the abstract chain
# view, for a player who doesn't naturally read a flow diagram.


def current_goods_label():
    spec = GOODS_CATEGORIES.get(chain.goods_category, GOODS_CATEGORIES[DEFAULT_GOODS_CATEGORY])
    return spec["label"]


def current_vignette_item():
    spec = GOODS_CATEGORIES.get(chain.goods_category, GOODS_CATEGORIES[DEFAULT_GOODS_CATEGORY])
    return spec["vignette_item"]


class ChainState:
    def __init__(self):
        self.cycle_number = 1
        self.funds = STARTING_FUNDS
        self.total_extracted = 0.0
        self.total_produced = 0.0
        self.circularity_investment = {c: 0 for c in CIRCULARITY_INVESTMENTS}
        self.circular_fraction_log = []
        self.trade_link_investment = 0
        self.regional_trade_investment = 0
        self.goods_category = DEFAULT_GOODS_CATEGORY
        # Lifetime tallies + streak tracking added for the achievements
        # rollout and H19's closed-loop-streak tracker — all reset with a
        # fresh chain, same as every other field here (only
        # chains_completed_count/goods_categories_tried, module-level
        # below, are meant to survive a "Start New Chain" reset, since
        # their entire point is to measure things *across* resets).
        self.lifetime_investment_spend = 0.0
        self.lifetime_export_revenue = 0.0
        self.closed_loop_streak = 0
        self.best_closed_loop_streak = 0

    def internal_circular_supply(self):
        """Units of this cycle's production target met by repair/reuse/
        recycling instead of new extraction — the chain's own capacity,
        before anything crossing in from the trade network."""
        return sum(
            self.circularity_investment[c] * CIRCULARITY_INVESTMENTS[c]["supply_per_unit"]
            for c in CIRCULARITY_INVESTMENTS
        )

    def imported_supply(self):
        return (
            self.trade_link_investment * IMPORT_SUPPLY_PER_UNIT
            + self.regional_trade_investment * REGIONAL_IMPORT_SUPPLY_PER_UNIT
        )

    def circular_supply(self):
        """Total supply toward closing the loop: internal circularity
        plus whatever the trade link imports from the neighboring
        system(s)."""
        return self.internal_circular_supply() + self.imported_supply()

    def exportable_surplus(self):
        """H1 fix — the import/export asymmetry: this used to read
        `max(0.0, self.internal_circular_supply() - PRODUCTION_TARGET)`,
        so only excess *internal* circularity supply was ever sold
        outward for revenue. Excess *imported* supply (from either trade
        partner) simply evaporated — no revenue, no carry-over — even
        though the player paid real funds for that import capacity.
        That was an unjustified, wasteful asymmetry: internal overshoot
        was monetized every single cycle it persisted, imported
        overshoot never was. Fixed by looking at total circular_supply()
        (internal + imported) beyond the production target instead, so
        any supply this chain doesn't need this cycle — regardless of
        source — is sold outward rather than silently discarded."""
        return max(0.0, self.circular_supply() - PRODUCTION_TARGET)

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
        self.lifetime_investment_spend += TRADE_LINK_COST
        return True

    def invest_regional_trade(self):
        """H8: the second trading partner — costs more per investment
        than the Local Trade Link but supplies more import capacity per
        unit (see REGIONAL_TRADE_COST/REGIONAL_IMPORT_SUPPLY_PER_UNIT
        above for the exact trade-off)."""
        if self.funds < REGIONAL_TRADE_COST:
            return False
        self.funds -= REGIONAL_TRADE_COST
        self.regional_trade_investment += 1
        self.lifetime_investment_spend += REGIONAL_TRADE_COST
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
        self.lifetime_investment_spend += cost
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
        self.lifetime_export_revenue += export_revenue
        # H19: closed-loop streak -- sticky best-ever value, same shape as
        # Grid's best_clean_streak. A cycle only counts toward the streak
        # if it needed zero new extraction (fully closed), matching
        # is_loop_closed()'s own definition.
        if extraction <= 0.0:
            self.closed_loop_streak += 1
            self.best_closed_loop_streak = max(self.best_closed_loop_streak, self.closed_loop_streak)
        else:
            self.closed_loop_streak = 0
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

# Module-level state that deliberately survives a "Start New Chain" reset
# (H7) -- these two counters exist specifically to measure something
# *across* resets/chains, so resetting `chain` must never touch them.
# Both ride get_state()/load_state() as top-level (not chain-scoped) keys.
chains_completed_count = 0
goods_categories_tried = {DEFAULT_GOODS_CATEGORY}


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


def sector_comparison_message(lifetime_fraction):
    """H9: a few alternate real-world sector comparisons beyond the
    single static REAL_WORLD_CIRCULARITY_BENCHMARK line above, so the
    player sees more than one real-world reference point. Same hedge
    language throughout — these are ballpark figures, not a precise or
    authoritative dataset."""
    clauses = []
    for label, rate in SECTOR_COMPARISONS:
        rate_pct = rate * 100
        relation = "above" if lifetime_fraction > rate else "below"
        clauses.append(f"{relation} the ~{rate_pct:.0f}% estimated for {label}")
    return "For context, your circular share is also " + "; ".join(clauses) + " (again, ballpark figures, not precise benchmarks)."


def vignette_message(fraction, item=None, variant_seed=0):
    """A concrete, one-item side-story tracking the same underlying
    circular_fraction_this_cycle() the abstract chain view already
    shows — makes the abstraction tangible for a player who doesn't
    naturally read a flow diagram.

    H14: each fraction bucket now has a couple of alternate phrasings
    instead of exactly one. `variant_seed` (render() passes
    chain.cycle_number) picks among them so replaying doesn't always
    show identical text — defaults to 0 (the first/original phrasing in
    each bucket) so every existing direct call to this function keeps
    its original behavior."""
    item = item or current_vignette_item()
    if fraction >= 1.0:
        variants = [
            f"Follow {item}: it was repaired once, then eventually recycled — "
            "its materials became part of the casing for the next one off the line.",
            f"Follow {item}: by the time it wore out, every stage of its journey "
            "looped back — nothing about it ended up as waste.",
        ]
    elif fraction >= 0.5:
        variants = [
            f"Follow {item}: it gets used, and there's a good chance it comes "
            "back through repair or recycling when its owner is done with it.",
            f"Follow {item}: more than half its journey loops back somewhere — "
            "repaired, reused, or recycled rather than simply discarded.",
        ]
    elif fraction > 0.0:
        variants = [
            f"Follow {item}: it gets used, then thrown away — though a little of "
            "what's inside it might still come back as recycled material someday.",
            f"Follow {item}: most of its journey is still a straight line, but a "
            "small share of what made it does loop back eventually.",
        ]
    else:
        variants = [
            f"Follow {item}: mined, made, used once, thrown away. Nothing about it "
            "comes back.",
            f"Follow {item}: extracted, manufactured, used briefly, discarded — "
            "nowhere in this chain does it loop back.",
        ]
    return variants[variant_seed % len(variants)]


def chain_flow_message(fraction, cycle_number=1):
    """H11: cycle 1's straight-line message (before the player has had a
    chance to invest in anything) is deliberately lighter than the
    starker framing shown from cycle 2 onward if the chain is still
    uninvested — an encouraging nudge for a brand-new player rather than
    a discouraging "still 100% extraction" statement on the very first
    screen they see."""
    if fraction <= 0.0:
        if cycle_number <= 1:
            return (
                "You're just getting started — invest in circularity below to "
                "start looping supply back instead of extracting new material."
            )
        return "Straight line: 100% of production needs new extraction."
    if fraction >= 1.0:
        return "Loop closed: 100% of production comes from repair, reuse & recycling. No new extraction needed."
    return f"{fraction * 100:.0f}% of the chain is looping back — {100 - fraction * 100:.0f}% still needs new extraction."


def cycles_to_close_loop_message():
    """H6: a rough plain-language projection of how many more cycles, at
    the chain's current rate of improvement, before the loop closes
    completely. Reuses circular_trend()'s own first-half/second-half
    comparison rather than inventing a second trend calculation, so this
    projection can never disagree with the trend line already shown."""
    fraction = chain.circular_fraction_this_cycle()
    if fraction >= 1.0:
        return "The loop is already closed."
    trend = chain.circular_trend()
    if trend is None:
        return "Not enough cycles yet to project when the loop might close."
    first_half_avg, second_half_avg = trend
    n = len(chain.circular_fraction_log)
    half = n // 2
    window = max(1, n - half)
    rate_per_cycle = (second_half_avg - first_half_avg) / window
    if rate_per_cycle <= 0:
        return "At the current rate, the loop isn't projected to close — try increasing circularity investment."
    cycles_needed = math.ceil((1.0 - fraction) / rate_per_cycle)
    cycle_word = "cycle" if cycles_needed == 1 else "cycles"
    return f"At the current rate of improvement, the loop could close in roughly {cycles_needed} more {cycle_word}."


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


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — following SOL's reference
# integration. Every achievement's earned status is a pure function of
# state that already exists elsewhere in this module, recomputed fresh
# every call — never a separately hand-maintained "earned" flag.
# ===========================================================================
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract as the other climate games' reference
    integrations: the boot script fetches achievements.json and hands it
    to Python as a window global before this file runs; the pytest
    harness's fake `js` module has no such attribute, so this falls
    through to reading the file straight off disk, keeping the module
    importable outside a real browser."""
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
# whole import — achievements are additive, not core to Loop's gameplay.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

CAPITAL_COMMITTED_TARGET = 300.0
TRADE_SURPLUS_TARGET = 500.0
STREAK_5_TARGET = 5
STREAK_10_TARGET = 10
CLEAN_HANDS_MIN_CYCLES = 10
LIFETIME_MAJORITY_MIN_CYCLES = 5
SCORE_PRAGMATIST_TARGET = 1000.0
SCORE_PRAGMATIST_MIN_FRACTION = 0.5
SCORE_PRAGMATIST_MIN_CYCLES = 10
SCORE_MASTER_TARGET = 2000.0
SCORE_MASTER_MIN_FRACTION = 0.9
SCORE_MASTER_MIN_CYCLES = 15
SERIAL_REDESIGNER_TARGET = 2
GOODS_EXPLORER_TARGET = 2

# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is ever cached or hand-flagged. The four fraction-tier
# achievements (quarter/half/three_quarter/loop_closed) also double as
# H13's "toast callouts at circular-fraction milestones" — they're keyed
# to exactly those 25/50/75/100% thresholds on circular_fraction_this_cycle(),
# so the existing achievement-unlock toast (below) already delivers that
# callout without a second, redundant toast system.
ACHIEVEMENT_CHECKS = {
    "first_fix": lambda: any(chain.circularity_investment[m] >= 1 for m in CIRCULARITY_INVESTMENTS),
    "full_toolkit": lambda: all(chain.circularity_investment[m] >= 1 for m in CIRCULARITY_INVESTMENTS),
    "trade_partner": lambda: chain.trade_link_investment >= 1 or chain.regional_trade_investment >= 1,
    "dual_sourcing": lambda: chain.trade_link_investment >= 1 and chain.regional_trade_investment >= 1,
    "quarter_loop": lambda: chain.circular_fraction_this_cycle() >= 0.25,
    "half_loop": lambda: chain.circular_fraction_this_cycle() >= 0.5,
    "three_quarter_loop": lambda: chain.circular_fraction_this_cycle() >= 0.75,
    "loop_closed": lambda: chain.is_loop_closed(),
    "lifetime_majority": lambda: (
        chain.lifetime_circular_fraction() >= 0.5
        and len(chain.circular_fraction_log) >= LIFETIME_MAJORITY_MIN_CYCLES
    ),
    "beyond_benchmark": lambda: chain.lifetime_circular_fraction() > REAL_WORLD_CIRCULARITY_BENCHMARK,
    "first_export": lambda: chain.lifetime_export_revenue > 0.0,
    "trade_surplus_500": lambda: chain.lifetime_export_revenue >= TRADE_SURPLUS_TARGET,
    "streak_5": lambda: chain.best_closed_loop_streak >= STREAK_5_TARGET,
    "streak_10": lambda: chain.best_closed_loop_streak >= STREAK_10_TARGET,
    "clean_hands": lambda: (
        len(chain.circular_fraction_log) >= CLEAN_HANDS_MIN_CYCLES and chain.total_extracted == 0.0
    ),
    "capital_committed": lambda: chain.lifetime_investment_spend >= CAPITAL_COMMITTED_TARGET,
    "score_pragmatist": lambda: (
        chain.score() >= SCORE_PRAGMATIST_TARGET
        and chain.lifetime_circular_fraction() >= SCORE_PRAGMATIST_MIN_FRACTION
        and len(chain.circular_fraction_log) >= SCORE_PRAGMATIST_MIN_CYCLES
    ),
    "score_master": lambda: (
        chain.score() >= SCORE_MASTER_TARGET
        and chain.lifetime_circular_fraction() >= SCORE_MASTER_MIN_FRACTION
        and len(chain.circular_fraction_log) >= SCORE_MASTER_MIN_CYCLES
    ),
    "serial_redesigner": lambda: chains_completed_count >= SERIAL_REDESIGNER_TARGET,
    "goods_explorer": lambda: len(goods_categories_tried) >= GOODS_EXPLORER_TARGET,
}

# Progress readouts, only for achievements with a natural numeric scale-up
# — a plain earned/not-yet is the honest shape for a one-shot milestone
# like "invest in either trade partner for the first time".
ACHIEVEMENT_PROGRESS = {
    "full_toolkit": lambda: (
        sum(1 for m in CIRCULARITY_INVESTMENTS if chain.circularity_investment[m] >= 1),
        len(CIRCULARITY_INVESTMENTS),
    ),
    "quarter_loop": lambda: (min(100, round(chain.circular_fraction_this_cycle() * 100)), 25),
    "half_loop": lambda: (min(100, round(chain.circular_fraction_this_cycle() * 100)), 50),
    "three_quarter_loop": lambda: (min(100, round(chain.circular_fraction_this_cycle() * 100)), 75),
    "lifetime_majority": lambda: (min(100, round(chain.lifetime_circular_fraction() * 100)), 50),
    "trade_surplus_500": lambda: (
        min(round(chain.lifetime_export_revenue), int(TRADE_SURPLUS_TARGET)),
        int(TRADE_SURPLUS_TARGET),
    ),
    "streak_5": lambda: (min(chain.best_closed_loop_streak, STREAK_5_TARGET), STREAK_5_TARGET),
    "streak_10": lambda: (min(chain.best_closed_loop_streak, STREAK_10_TARGET), STREAK_10_TARGET),
    "capital_committed": lambda: (
        min(round(chain.lifetime_investment_spend), int(CAPITAL_COMMITTED_TARGET)),
        int(CAPITAL_COMMITTED_TARGET),
    ),
    "score_pragmatist": lambda: (
        min(round(chain.score()), int(SCORE_PRAGMATIST_TARGET)),
        int(SCORE_PRAGMATIST_TARGET),
    ),
    "score_master": lambda: (
        min(round(chain.score()), int(SCORE_MASTER_TARGET)),
        int(SCORE_MASTER_TARGET),
    ),
    "serial_redesigner": lambda: (min(chains_completed_count, SERIAL_REDESIGNER_TARGET), SERIAL_REDESIGNER_TARGET),
    "goods_explorer": lambda: (min(len(goods_categories_tried), GOODS_EXPLORER_TARGET), GOODS_EXPLORER_TARGET),
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

    # A link out to the hub-wide achievements dashboard (root index.html's
    # #account-achievements-dashboard, ACHIEVEMENTS-SYSTEM-DESIGN.md §5).
    # Relative path, no leading "/" (site-level milestone 7's GitHub Pages
    # subpath fix). Rebuilt each open alongside the cards since the panel
    # is cleared first. The hub-side script.js registration that makes
    # Loop's save data actually show up on that dashboard is a root-file
    # change, out of scope for this games/loop/-only dispatch.
    hub_link = document.createElement("a")
    hub_link.innerText = "View the hub-wide achievements dashboard →"
    hub_link.href = "../../index.html#account-achievements-dashboard"
    hub_link.className = "achievements-hub-link"
    panel.appendChild(hub_link)


# Unlock toast (site-wide "roll achievements out everywhere" requirement,
# on top of the base per-game rollout). A snapshot of which ids were
# already earned as of the last seed point, so a fresh load or a loaded
# save doesn't flood the player with toasts for achievements it already
# satisfies.
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
    — never from render() itself, since load_state() also calls render()
    and a loaded save with several achievements already earned must not
    flood the player with toasts for all of them at once."""
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


# H3: a first-time-closed-loop celebratory banner — distinct from (and in
# addition to) the achievement-unlock toast above, since H3 explicitly
# asks for its own celebratory moment, not a reuse of the small
# achievement toast. Tracks whether the loop was already closed
# immediately before the action that just ran, so this only fires on the
# false->true transition, never on every render while it stays closed.
def _show_loop_closed_banner():
    banner = document.getElementById("loop-closed-banner")
    banner.hidden = False
    banner.classList.add("visible")

    def _hide(*args):
        banner.hidden = True
        banner.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, 5000)


def _trigger_funds_burst():
    """H12: a brief visible pulse on the funds display when export
    revenue is earned, instead of the number just silently changing."""
    el = document.getElementById("funds-display")
    el.classList.add("funds-display--burst")

    def _clear(*args):
        el.classList.remove("funds-display--burst")
        proxy.destroy()

    proxy = create_proxy(_clear)
    setTimeout(proxy, 700)


def _trigger_trade_network_pulse():
    """H18: a brief visible pulse on the trade-network readout whenever
    its rendered numbers actually change."""
    el = document.getElementById("trade-network-display")
    el.classList.add("trade-network-display--pulse")

    def _clear(*args):
        el.classList.remove("trade-network-display--pulse")
        proxy.destroy()

    proxy = create_proxy(_clear)
    setTimeout(proxy, 700)


def render():
    render_info_page()
    update_achievements_display()

    picker = document.getElementById("goods-category-picker")
    picker.hidden = chain.total_produced > 0
    for key in GOODS_CATEGORIES:
        button = document.getElementById(f"goods-category-{key}-button")
        if key == chain.goods_category:
            button.classList.add("selected")
        else:
            button.classList.remove("selected")

    fraction = chain.circular_fraction_this_cycle()
    flow_el = document.getElementById("chain-flow")
    flow_el.className = "chain-flow chain-flow--closed" if fraction >= 1.0 else "chain-flow"
    extract_stage = document.getElementById("stage-extract")
    extract_stage.className = "chain-stage chain-stage--inactive" if fraction >= 1.0 else "chain-stage"
    document.getElementById("chain-flow-message").innerText = chain_flow_message(fraction, chain.cycle_number)

    return_flow_row = document.getElementById("return-flow-row")
    return_flow_row.style.opacity = f"{fraction:.2f}"

    import_fraction = min(1.0, chain.imported_supply() / PRODUCTION_TARGET)
    import_flow_row = document.getElementById("import-flow-row")
    import_flow_row.style.opacity = f"{import_fraction:.2f}"

    vignette_variant = (chain.cycle_number - 1) if chain.cycle_number > 0 else 0
    document.getElementById("vignette-display").innerText = vignette_message(fraction, variant_seed=vignette_variant)

    document.getElementById("cycle-display").innerText = f"Cycle {chain.cycle_number}"
    document.getElementById("funds-display").innerText = f"Funds: {chain.funds:.0f}"
    document.getElementById("extraction-display").innerText = (
        "Loop closed — no new extraction needed" if chain.is_loop_closed()
        else f"New extraction this cycle: {chain.new_extraction_needed():.0f} units of raw material for {current_goods_label()}"
    )
    document.getElementById("production-display").innerText = (
        f"Production target: {PRODUCTION_TARGET:.0f} units of {current_goods_label()} per cycle"
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
    # H17: a live score breakdown, always visible, instead of the score
    # figure only being explained on click through the info-toggle below.
    bonus_component = chain.lifetime_circular_fraction() * CIRCULARITY_BONUS_WEIGHT
    document.getElementById("score-breakdown-display").innerText = (
        f"Score = funds ({chain.funds:.0f}) + circular bonus ({bonus_component:.0f}) = {chain.score():.0f}"
    )
    document.getElementById("trend-display").innerText = circular_trend_message(chain.circular_trend())
    document.getElementById("loop-projection-display").innerText = cycles_to_close_loop_message()
    document.getElementById("real-world-comparison-display").innerText = (
        real_world_comparison_message(chain.lifetime_circular_fraction())
    )
    document.getElementById("sector-comparison-display").innerText = (
        sector_comparison_message(chain.lifetime_circular_fraction())
    )
    document.getElementById("streak-display").innerText = (
        f"Closed-loop streak: {chain.closed_loop_streak} cycle(s) (best: {chain.best_closed_loop_streak})"
    )

    for measure, spec in CIRCULARITY_INVESTMENTS.items():
        document.getElementById(f"{measure}-name").innerText = f"{spec['icon']} {spec['label']}"
        document.getElementById(f"{measure}-count").innerText = str(
            chain.circularity_investment[measure]
        )
        button = document.getElementById(f"{measure}-invest-button")
        button.innerText = f"{spec['label']} ({spec['cost']})"
        button.disabled = chain.funds < spec["cost"]

        # H4 + H15: cost-per-unit-of-supply, and each measure's running
        # supply contribution per cycle, next to its owned count.
        cost_per_unit = spec["cost"] / spec["supply_per_unit"]
        contribution = chain.circularity_investment[measure] * spec["supply_per_unit"]
        document.getElementById(f"{measure}-stats").innerText = (
            f"{cost_per_unit:.1f} funds/unit · supplying {contribution:.0f}/cycle"
        )

        # H5: highlight the decorative loop-ring nodes proportional to
        # real investment instead of leaving them purely static.
        node = document.getElementById(f"loop-ring-node-{measure}")
        base_class = f"loop-ring-node loop-ring-node--{measure}"
        count = chain.circularity_investment[measure]
        if count >= 5:
            node.className = f"{base_class} loop-ring-node--charged"
        elif count >= 1:
            node.className = f"{base_class} loop-ring-node--active"
        else:
            node.className = base_class

    document.getElementById("trade-link-count").innerText = str(chain.trade_link_investment)
    trade_link_button = document.getElementById("trade-link-invest-button")
    trade_link_button.innerText = f"Trade Link ({TRADE_LINK_COST})"
    trade_link_button.disabled = chain.funds < TRADE_LINK_COST

    document.getElementById("regional-trade-count").innerText = str(chain.regional_trade_investment)
    regional_trade_button = document.getElementById("regional-trade-invest-button")
    regional_trade_button.innerText = f"Regional Partner ({REGIONAL_TRADE_COST})"
    regional_trade_button.disabled = chain.funds < REGIONAL_TRADE_COST

    document.getElementById("trade-network-display").innerText = (
        f"Importing {chain.imported_supply():.0f} units/cycle from the trade network; "
        f"exporting {chain.exportable_surplus():.0f} units/cycle of surplus this cycle."
    )


def on_advance_cycle(event=None):
    _run_action(chain.advance_cycle)


def _make_circularity_handler(measure):
    def handler(event=None):
        _run_action(lambda: chain.invest_circularity(measure))
    return handler


def on_invest_trade_link(event=None):
    _run_action(chain.invest_trade_link)


def on_invest_regional_trade(event=None):
    _run_action(chain.invest_regional_trade)


def on_reset_chain(event=None):
    """H7: an in-game "Start New Chain" reset control. Wipes the current
    chain back to a fresh ChainState() (funds, cycle number, every
    investment) — the two module-level counters that exist specifically
    to measure things *across* resets (chains_completed_count,
    goods_categories_tried) are deliberately not touched here."""
    global chains_completed_count

    def _do_reset():
        global chain
        chain = ChainState()

    chains_completed_count += 1
    _run_action(_do_reset)


def _make_goods_category_handler(category):
    def handler(event=None):
        def _do_select():
            chain.goods_category = category
            goods_categories_tried.add(category)
        _run_action(_do_select)
    return handler


def _run_action(mutate_fn):
    """Shared wrapper for every state-mutating action: snapshot whatever
    "before" state the reactive effects below need, run the mutation,
    re-render, then fire any effect the mutation triggered (funds burst,
    trade-network pulse, loop-closed banner, achievement toast). Kept in
    one place so every handler gets the same reactive behavior instead of
    re-implementing this comparison per handler."""
    trade_text_before = document.getElementById("trade-network-display").innerText
    export_before = chain.lifetime_export_revenue
    was_closed = chain.is_loop_closed()

    mutate_fn()
    render()

    if chain.lifetime_export_revenue > export_before:
        _trigger_funds_burst()
    if document.getElementById("trade-network-display").innerText != trade_text_before:
        _trigger_trade_network_pulse()
    if chain.is_loop_closed() and not was_closed:
        _show_loop_closed_banner()
    _check_new_achievements_for_toast()


# SAVE-BUTTON-INTEGRATION.md contract for the shared shared/save-widget.js:
# get_state()/load_state() are the per-game contract the widget calls
# (get_state()/load_state() on save/load respectively). SOL is the
# reference integration for this contract; Loop follows the same
# thin/direct pattern rather than reinventing it.


def get_state():
    """Return every piece of Loop's tracked state as a plain, JSON-safe
    dict. `chain` is the primary stateful object in the game — its dict/
    list attributes (`circularity_investment`, `circular_fraction_log`)
    are deep-copied so the saved snapshot doesn't alias a live reference;
    continued play after saving would otherwise silently mutate it, same
    reasoning as SOL's serialize_state(). `chains_completed_count`/
    `goods_categories_tried` are module-level (not on `chain`) since they
    deliberately survive a "Start New Chain" reset. `achievements_earned`
    is always freshly recomputed and never read back by load_state()
    (ACHIEVEMENTS-SYSTEM-DESIGN.md §1)."""
    return {
        "cycle_number": chain.cycle_number,
        "funds": chain.funds,
        "total_extracted": chain.total_extracted,
        "total_produced": chain.total_produced,
        "circularity_investment": copy.deepcopy(chain.circularity_investment),
        "circular_fraction_log": copy.deepcopy(chain.circular_fraction_log),
        "trade_link_investment": chain.trade_link_investment,
        "regional_trade_investment": chain.regional_trade_investment,
        "goods_category": chain.goods_category,
        "lifetime_investment_spend": chain.lifetime_investment_spend,
        "lifetime_export_revenue": chain.lifetime_export_revenue,
        "closed_loop_streak": chain.closed_loop_streak,
        "best_closed_loop_streak": chain.best_closed_loop_streak,
        "chains_completed_count": chains_completed_count,
        "goods_categories_tried": sorted(goods_categories_tried),
        "achievements_earned": achievement_ids_earned(),
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
    measure) instead of letting it linger in the live dict forever.

    Every field added after the original save contract (regional trade
    investment, goods category, the lifetime tallies/streaks, the two
    module-level reset-survivor counters) defaults defensively via
    `.get(..., <safe default>)` so a save from before that field existed
    loads cleanly instead of raising KeyError."""
    global chains_completed_count, goods_categories_tried

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
    chain.regional_trade_investment = data.get("regional_trade_investment", 0)
    chain.goods_category = data.get("goods_category", DEFAULT_GOODS_CATEGORY)
    chain.lifetime_investment_spend = data.get("lifetime_investment_spend", 0.0)
    chain.lifetime_export_revenue = data.get("lifetime_export_revenue", 0.0)
    chain.closed_loop_streak = data.get("closed_loop_streak", 0)
    chain.best_closed_loop_streak = data.get("best_closed_loop_streak", 0)

    chains_completed_count = data.get("chains_completed_count", 0)
    # Backfill (same pattern as SOL's visited_bodies): a save predating
    # this field won't list the restored chain's own category as
    # "tried" yet — add it unconditionally so goods_explorer's count
    # never undercounts a category the player is demonstrably playing.
    goods_categories_tried = set(data.get("goods_categories_tried", []))
    goods_categories_tried.add(chain.goods_category)

    render()
    _seed_achievement_toast_baseline()
    return True


def setup():
    # index.html already marks these hidden via the `hidden` attribute, but
    # that markup default doesn't exist for the pytest fake-DOM harness (a
    # FakeElement starts with hidden=False) -- setting it explicitly here
    # keeps both environments consistent and costs nothing in a real
    # browser, where it's already true. Same pattern as Grid's setup().
    document.getElementById("achievement-toast").hidden = True
    document.getElementById("loop-closed-banner").hidden = True

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
    document.getElementById("regional-trade-invest-button").addEventListener(
        "click", create_proxy(on_invest_regional_trade)
    )
    document.getElementById("reset-chain-button").addEventListener(
        "click", create_proxy(on_reset_chain)
    )
    for category in GOODS_CATEGORIES:
        document.getElementById(f"goods-category-{category}-button").addEventListener(
            "click", create_proxy(_make_goods_category_handler(category))
        )
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    _seed_achievement_toast_baseline()
    render()


setup()
