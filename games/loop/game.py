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

# H20 (planning/TODO.md, completion-audit fix): the three goods-flavor
# sets above previously differed ONLY in the swapped noun (item/label/
# icon) -- every vignette sentence's actual repair/reuse/recycle
# mechanism was identical prose regardless of category. The user's
# answer was "distinct": each category now gets its own concrete,
# category-appropriate loop mechanics instead of a generic "repaired...
# recycled" phrase that happened to have a different noun plugged in.
# Keyed the same way vignette_message()'s existing fraction buckets are
# ("closed"/"majority"/"minority"/"none"); see _vignette_variants_for()
# below for how these combine with `item`.
CATEGORY_LOOP_DETAIL = {
    "electronics": {
        "closed": [
            "its battery was swapped for a fresh one, and when it finally died its "
            "circuit board's metals were reclaimed straight into the next batch",
            "a cracked screen got replaced, then every rare-earth trace inside it "
            "was recovered when it was finally retired",
        ],
        "majority": [
            "there's a good chance a worn battery gets swapped before the whole "
            "thing is written off, and its board's metals get reclaimed after",
            "more often than not it gets a battery or screen repair first, and its "
            "materials are recovered rather than landfilled once it's truly done",
        ],
        "minority": [
            "most units like it are used once and binned, though a growing share "
            "have their rare-earth metals recovered afterward",
            "repair almost never happens to it, but a small share still get their "
            "circuit boards stripped for reclaimable metals",
        ],
        "none": [
            "mined for rare metals, assembled, used until it's obsolete, then "
            "landfilled with those metals still locked inside",
            "extracted, assembled, discarded — none of its rare-earth content is "
            "ever recovered",
        ],
    },
    "clothing": {
        "closed": [
            "it was mended at a seam more than once, and when it finally wore "
            "through, its fabric was shredded into insulation for something else",
            "a button and a zipper were replaced along the way, then the fabric "
            "itself was rewoven into new thread once it was retired",
        ],
        "majority": [
            "there's a good chance a loose seam gets mended before it's given up "
            "on, and its fabric gets shredded into new material afterward",
            "more often than not it gets a repair first, and its fabric is "
            "recycled into something else rather than thrown out",
        ],
        "minority": [
            "most pieces like it are worn until they fall apart and binned, "
            "though a growing share have their fabric shredded for reuse after",
            "mending it almost never happens, but a small share still have their "
            "fabric recovered for insulation or new thread",
        ],
        "none": [
            "spun, sewn, worn until it frays, then landfilled — its fibers never "
            "come back as anything",
            "manufactured, worn briefly, discarded — none of its fabric is ever "
            "rewoven into anything new",
        ],
    },
    "furniture": {
        "closed": [
            "a broken leg was fixed once, and when it was finally past saving its "
            "wood was reclaimed and remilled into a new piece",
            "a loose joint was reglued along the way, then its timber was "
            "recovered and remilled once it was finally retired",
        ],
        "majority": [
            "there's a good chance a wobbly joint gets fixed before it's given "
            "up on, and its timber gets reclaimed for remilling afterward",
            "more often than not it gets a repair first, and its wood is "
            "recovered rather than sent to landfill once it's truly done",
        ],
        "minority": [
            "most pieces like it are used until they break and thrown out, "
            "though a growing share have their timber reclaimed afterward",
            "repair almost never happens to it, but a small share still have "
            "their wood salvaged and remilled",
        ],
        "none": [
            "milled, assembled, used until it breaks, then landfilled — its "
            "timber never comes back as anything",
            "manufactured, used briefly, discarded — none of its wood is ever "
            "reclaimed",
        ],
    },
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

# A couple of alternate real-world sector ballparks beyond the single
# static benchmark above, so the comparison doesn't lean on one figure
# alone. Same "illustrative, not authoritative" hedge as
# real_world_comparison_message() -- these are ballpark figures pulled
# from general circular-economy reporting, not a precise dataset.
# (This list shipped under an earlier round's H9 numbering -- see
# CLAUDE.md's "Post-milestone backlog pass" notes. The current
# planning/TODO.md's H9 is a different, later-numbered item -- "waste
# stream diversification" -- built separately below; don't confuse the
# two when reading old vs. new session notes.)
SECTOR_COMPARISONS = [
    ("textiles & apparel", 0.01),
    ("plastics", 0.09),
    ("metals", 0.33),
    ("packaging", 0.14),
]

# H9 (current numbering): waste stream diversification -- specialize
# recovery effort on ONE circularity measure for a supply bonus on that
# measure alone, the other two staying at their base rate. Framed as a
# standing emphasis rather than a purchase (freely switchable, no cost)
# since the real trade-off is structural -- only one measure can carry
# the bonus at a time -- not a friction point worth gating further.
WASTE_STREAM_SPECIALIZATION_BONUS = 0.25

# H3: supply chain redesign -- a late-game layer that only opens once the loop
# has closed at least once. Each measure can then be "redesigned" up to
# REDESIGN_MAX_LEVEL times: every level is a funds purchase (cost grows with the
# level) that makes that measure's supply count REDESIGN_SUPPLY_BONUS higher for
# good. Small on purpose ("a small efficiency bonus"), and it stacks additively
# with the H9 focus rather than compounding with it.
# H17: consumer behavior -- a DEMAND-side lever, distinct from every supply-side
# measure above. A repair-and-reuse culture campaign lowers how much material
# each cycle's production needs in the first place (products last longer, fewer
# are wanted), so it shrinks the gap that supply has to fill instead of adding
# supply. Each level costs more than the last and is worth CULTURE_DEMAND_REDUCTION
# of the production target's material need, up to CULTURE_MAX_LEVEL levels (a
# ceiling well short of removing demand: people still buy things).
# H21: the material passport -- one traced unit of material followed through
# the chain as a literal object. Each cycle the unit is either newly mined or
# recovered by one of the measures (or arrives by trade), chosen from the
# chain's real supply mix by a fixed golden-ratio sequence (no randomness, so a
# run is reproducible and the record matches the numbers). Capped so a long run
# never grows the save without bound.
PASSPORT_MAX_ENTRIES = 40
PASSPORT_SOURCES = ("extraction", "repair", "reuse", "recycle", "trade")
PASSPORT_SOURCE_LABEL = {
    "extraction": "newly mined",
    "repair": "kept in use by repair",
    "reuse": "passed on by reuse",
    "recycle": "recovered by recycling",
    "trade": "brought in by trade",
}
_GOLDEN = 0.6180339887498949

CULTURE_BASE_COST = 40
CULTURE_MAX_LEVEL = 5
CULTURE_DEMAND_REDUCTION = 0.04

REDESIGN_BASE_COST = 120
REDESIGN_MAX_LEVEL = 3
REDESIGN_SUPPLY_BONUS = 0.05

# H13: an opt-in harder variant, selectable only before the chain has
# produced anything (see ChainState.set_challenge_mode()) -- multiplies
# both internal and imported circular supply down, so closing the loop
# takes meaningfully more investment than the default chain.
CHALLENGE_MODE_SUPPLY_MULTIPLIER = 0.65

# H23: an opt-in "zero-waste" variant, also chosen only at game start --
# a soft, scored challenge (never a hard fail-state, per this hub's
# no-fail-state convention) tracking whether lifetime extraction ever
# exceeds this cap. Failing it doesn't block play; it just ends the
# challenge's own clean streak.
ZERO_WASTE_EXTRACTION_CAP = 150.0

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

# H1: a third trading partner with its own distinct cost/supply ratio --
# a big, expensive, high-capacity consortium (6.0 funds/unit, the best
# ratio of the three partners, but a 90-fund lump).
OVERSEAS_TRADE_COST = 90
OVERSEAS_IMPORT_SUPPLY_PER_UNIT = 15.0

# Round-2 (H6/H26/H27/H28): UI-only tuning.
BURST_MILESTONES = 4  # circular-fraction crosses each 25% step
PULSE_LARGE_UNITS = 20.0
PULSE_MEDIUM_UNITS = 8.0
STREAK_PROGRESS_STEP = 5  # H2: progress toward the next 5-cycle streak mark

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
        self.overseas_trade_investment = 0
        # H16: the cycle number the loop first closed on (None until then).
        self.first_loop_closed_cycle = None
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
        # H13/H23: opt-in start-of-chain modes (see can_choose_mode()).
        self.challenge_mode = False
        self.zero_waste = False
        # H9: the one circularity measure currently carrying the specialization
        # bonus (None = no emphasis).
        self.waste_focus = None
        # H3: redesign level per measure (0..REDESIGN_MAX_LEVEL).
        self.redesign_level = {m: 0 for m in CIRCULARITY_INVESTMENTS}
        # H17: demand-side campaign level (0..CULTURE_MAX_LEVEL).
        self.culture_level = 0
        # H21: [{"cycle": int, "source": one of PASSPORT_SOURCES}], oldest first.
        self.passport = []

    def can_choose_mode(self):
        """H13/H23: the modes change the rules of the whole chain, so they
        can only be picked before anything has been produced."""
        return self.total_produced == 0 and self.cycle_number == 1

    def set_challenge_mode(self, on):
        if not self.can_choose_mode():
            return False
        self.challenge_mode = bool(on)
        return True

    def set_zero_waste(self, on):
        if not self.can_choose_mode():
            return False
        self.zero_waste = bool(on)
        return True

    def supply_multiplier(self):
        return CHALLENGE_MODE_SUPPLY_MULTIPLIER if self.challenge_mode else 1.0

    def zero_waste_holding(self):
        """H23: still within the extraction cap. Soft by design: going over
        ends the challenge's own bragging rights, never blocks play."""
        return self.total_extracted <= ZERO_WASTE_EXTRACTION_CAP

    def measure_multiplier(self, measure):
        """H9: the focused measure's supply counts WASTE_STREAM_SPECIALIZATION_BONUS
        higher; the other two stay at their base rate."""
        focus = WASTE_STREAM_SPECIALIZATION_BONUS if self.waste_focus == measure else 0.0
        return 1.0 + focus + REDESIGN_SUPPLY_BONUS * self.redesign_level.get(measure, 0)

    def passport_source(self):
        """Where the traced unit comes from THIS cycle, drawn from the current
        supply mix (call before the cycle counter advances)."""
        need = self.material_need()
        extraction = self.new_extraction_needed()
        if need <= 0:
            return "extraction"
        shares = {"extraction": extraction / need}
        circular = 1.0 - shares["extraction"]
        parts = {
            m: self.circularity_investment[m] * CIRCULARITY_INVESTMENTS[m]["supply_per_unit"] * self.measure_multiplier(m)
            for m in CIRCULARITY_INVESTMENTS
        }
        parts["trade"] = self.imported_supply()
        total = sum(parts.values())
        for name in ("repair", "reuse", "recycle", "trade"):
            shares[name] = circular * (parts[name] / total) if total > 0 else 0.0
        point = (self.cycle_number * _GOLDEN) % 1.0
        running = 0.0
        for name in PASSPORT_SOURCES:
            running += shares.get(name, 0.0)
            if point < running:
                return name
        return "extraction" if shares["extraction"] > 0 else max(PASSPORT_SOURCES[1:], key=lambda n: shares.get(n, 0.0))

    def passport_summary(self):
        """Counts over the recorded journey: (mined, recovered, longest run of recoveries)."""
        mined = sum(1 for e in self.passport if e["source"] == "extraction")
        recovered = len(self.passport) - mined
        longest = run = 0
        for e in self.passport:
            run = run + 1 if e["source"] != "extraction" else 0
            longest = max(longest, run)
        return mined, recovered, longest

    def material_need(self):
        """H17: units of material one cycle's production actually needs, after
        any demand-side culture campaign. Equals PRODUCTION_TARGET with none."""
        return PRODUCTION_TARGET * (1.0 - CULTURE_DEMAND_REDUCTION * self.culture_level)

    def culture_cost(self):
        return CULTURE_BASE_COST * (self.culture_level + 1)

    def invest_culture(self):
        if self.culture_level >= CULTURE_MAX_LEVEL:
            return False
        cost = self.culture_cost()
        if self.funds < cost:
            return False
        self.funds -= cost
        self.culture_level += 1
        self.lifetime_investment_spend += cost
        return True

    def redesign_unlocked(self):
        """H3: opens once the loop has closed at least once."""
        return self.first_loop_closed_cycle is not None

    def redesign_cost(self, measure):
        return REDESIGN_BASE_COST * (self.redesign_level[measure] + 1)

    def redesign(self, measure):
        if measure not in self.redesign_level or not self.redesign_unlocked():
            return False
        if self.redesign_level[measure] >= REDESIGN_MAX_LEVEL:
            return False
        cost = self.redesign_cost(measure)
        if self.funds < cost:
            return False
        self.funds -= cost
        self.redesign_level[measure] += 1
        self.lifetime_investment_spend += cost
        return True

    def set_waste_focus(self, measure):
        """Freely switchable and free (the trade-off is structural: only one
        measure can carry the bonus at a time). None clears it."""
        if measure is not None and not (isinstance(measure, str) and measure in CIRCULARITY_INVESTMENTS):
            return False
        self.waste_focus = measure
        return True

    def internal_circular_supply(self):
        """Units of this cycle's production target met by repair/reuse/
        recycling instead of new extraction — the chain's own capacity,
        before anything crossing in from the trade network."""
        return self.supply_multiplier() * sum(
            self.circularity_investment[c] * CIRCULARITY_INVESTMENTS[c]["supply_per_unit"] * self.measure_multiplier(c)
            for c in CIRCULARITY_INVESTMENTS
        )

    def imported_supply(self):
        return self.supply_multiplier() * (
            self.trade_link_investment * IMPORT_SUPPLY_PER_UNIT
            + self.regional_trade_investment * REGIONAL_IMPORT_SUPPLY_PER_UNIT
            + self.overseas_trade_investment * OVERSEAS_IMPORT_SUPPLY_PER_UNIT
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
        return max(0.0, self.circular_supply() - self.material_need())

    def new_extraction_needed(self):
        """The straight-line default: whatever circular supply doesn't
        cover has to come from newly extracted raw material. Floored at
        zero — enough circularity investment closes the loop entirely."""
        return max(0.0, self.material_need() - self.circular_supply())

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

    def invest_overseas_trade(self):
        """H1: the third trading partner (see OVERSEAS_TRADE_COST)."""
        if self.funds < OVERSEAS_TRADE_COST:
            return False
        self.funds -= OVERSEAS_TRADE_COST
        self.overseas_trade_investment += 1
        self.lifetime_investment_spend += OVERSEAS_TRADE_COST
        return True

    def extraction_cost_trend(self):
        """H8: 'rising' if last cycle's extraction pushed the per-unit
        extraction cost multiplier up, else 'steady' (also before any
        cycle has run). Damage never decays, so it can never get cheaper
        -- the honest options are pricier or unchanged."""
        if not self.circular_fraction_log:
            return "steady"
        last_extraction = PRODUCTION_TARGET * (1.0 - self.circular_fraction_log[-1])
        prev_damage = min(1.0, max(0.0, self.total_extracted - last_extraction) / ENVIRONMENTAL_DAMAGE_SCALE)
        prev_mult = 1.0 + prev_damage * (MAX_COST_MULTIPLIER - 1.0)
        return "rising" if self.extraction_cost_multiplier() > prev_mult + 1e-9 else "steady"

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
        self.passport.append({"cycle": self.cycle_number, "source": self.passport_source()})
        del self.passport[:-PASSPORT_MAX_ENTRIES]
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
# H28: one-time Regional Partner hint; survives reset like the counters
# above (a player who has seen the explanation does not need it again).
regional_hint_seen = False
# H20: per-session random offset for which vignette variant a bucket
# starts on. 0 (deterministic) outside a real browser -- setup() sets it.
vignette_session_offset = 0


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


def scorecard_rows(lifetime_fraction):
    """H19: the player's lifetime circular share against EVERY benchmark at
    once (the overall real-world figure plus each sector), as plain data:
    label, the benchmark, the signed gap in percentage points and a text
    verdict. Same hedge as the two single-line comparisons above: ballparks,
    not a precise dataset."""
    rows = []
    entries = [("overall real-world average", REAL_WORLD_CIRCULARITY_BENCHMARK)] + list(SECTOR_COMPARISONS)
    for label, rate in entries:
        gap = (lifetime_fraction - rate) * 100
        if abs(gap) < 0.5:
            verdict = "level with"
            symbol = "\u25C6"
        elif gap > 0:
            verdict = f"{gap:.0f} points above"
            symbol = "\u25B2"
        else:
            verdict = f"{-gap:.0f} points below"
            symbol = "\u25BC"
        rows.append({
            "label": label, "benchmark": rate, "gap_points": gap, "verdict": verdict, "symbol": symbol,
            "mine_width": min(100.0, lifetime_fraction * 100), "benchmark_width": min(100.0, rate * 100),
        })
    return rows


def render_scorecard():
    container = document.getElementById("scorecard-list")
    container.innerHTML = ""
    for row in scorecard_rows(chain.lifetime_circular_fraction()):
        line = document.createElement("div")
        line.className = "scorecard-row"
        text = document.createElement("p")
        text.className = "scorecard-text"
        text.innerText = f"{row['symbol']} {row['verdict']} the ~{row['benchmark'] * 100:.0f}% for {row['label']}"
        line.appendChild(text)
        bars = document.createElement("div")
        bars.className = "scorecard-bars"
        mine = document.createElement("div")
        mine.className = "scorecard-bar scorecard-bar--mine"
        mine.style.width = f"{row['mine_width']:.0f}%"
        bench = document.createElement("div")
        bench.className = "scorecard-bar scorecard-bar--benchmark"
        bench.style.width = f"{row['benchmark_width']:.0f}%"
        bars.appendChild(mine)
        bars.appendChild(bench)
        line.appendChild(bars)
        container.appendChild(line)


def _request_community_comparison():
    """H5: asks the page's optional JS hook (window.loopCompare, see
    index.html) to fill #community-comparison-display with a real
    cross-player percentile for lifetime circular share, once the shared
    aggregate-stats endpoint (planning/TODO.md Z1) has enough saves to
    answer -- unlike real_world_comparison_message()/sector_comparison_message()
    above, which are static, hedged ballpark figures, not live player data.

    Same lazy `from js import window`/getattr-default shape as Grid's own
    `_request_comparison()` (games/grid/game.py C15) and this file's own
    `_confirm_dialog_ask()`: the pytest fake-DOM harness's `js` module only
    ever fakes `document`/`setTimeout` (see tests/conftest.py), never
    `window`, so this is a safe no-op under test, and a safe no-op on any
    page that never defines `window.loopCompare` either."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "loopCompare", None)
    if hook is not None:
        hook(chain.lifetime_circular_fraction())


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
    bucket = "closed" if fraction >= 1.0 else "majority" if fraction >= 0.5 else "minority" if fraction > 0.0 else "none"

    # H20: category-specific loop mechanics (see CATEGORY_LOOP_DETAIL's own
    # comment) instead of the same generic "repaired... recycled" phrase
    # regardless of which goods category is active. Falls back to the
    # original generic wording for any category not covered there, so an
    # unlisted/future category never crashes this function.
    details = CATEGORY_LOOP_DETAIL.get(chain.goods_category, {}).get(bucket)
    if details:
        variants = [f"Follow {item}: {detail}." for detail in details]
    elif bucket == "closed":
        variants = [
            f"Follow {item}: it was repaired once, then eventually recycled — "
            "its materials became part of the casing for the next one off the line.",
            f"Follow {item}: by the time it wore out, every stage of its journey "
            "looped back — nothing about it ended up as waste.",
        ]
    elif bucket == "majority":
        variants = [
            f"Follow {item}: it gets used, and there's a good chance it comes "
            "back through repair or recycling when its owner is done with it.",
            f"Follow {item}: more than half its journey loops back somewhere — "
            "repaired, reused, or recycled rather than simply discarded.",
        ]
    elif bucket == "minority":
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
# callout without a second, redundant toast system. (V-E-5 audit,
# planning/TODO.md: the one real overlap this created — "loop_closed"
# firing in the same action as the H3 loop-closed banner — is sequenced
# in `_run_action()`/`_check_new_achievements_for_toast()` below, not
# fixed by adding a new toast.)
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
    # H14: a badge for trying every goods-flavor set.
    "goods_collector": lambda: len(goods_categories_tried) >= len(GOODS_CATEGORIES),
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
    "goods_collector": lambda: (len(goods_categories_tried), len(GOODS_CATEGORIES)),
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
        card.dataset.achievementId = entry["id"]

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

    _request_achievement_stats()


def _request_achievement_stats():
    """Z27b: asks the page's optional JS hook (window.applyAchievementStats,
    shared/achievement-stats.js) to fill in each achievement card's own
    "Earned by N% of players" line from the cross-player stats endpoint
    (planning/TODO.md Z1). Absent hook (pytest, or a page without the
    shared script) leaves the cards exactly as rendered above -- same
    fails-soft shape as Grid's C15 window.gridCompare."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "applyAchievementStats", None)
    if hook is not None:
        hook()


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


def _check_new_achievements_for_toast(delay_ms=0):
    """Called after every player action that could change earned status
    — never from render() itself, since load_state() also calls render()
    and a loaded save with several achievements already earned must not
    flood the player with toasts for all of them at once.

    H13 audit fix (planning/TODO.md V-E-5): "loop_closed" is itself one of
    the checkable achievements, so the exact action that closes the loop
    for the first time earns it in the very same tick that
    `_show_loop_closed_banner()` (below) also fires — two one-shot
    notifications from one event. `_run_action()` passes a non-zero
    `delay_ms` (the loop-closed banner's own visible duration) on exactly
    that transition, so the toast waits its turn instead of stacking with
    the banner. Every other call site passes 0 (show immediately), the
    original behavior. Which achievement(s) newly unlocked — and whether
    they get shown at all — is decided the same way regardless of timing;
    only *when* the resulting toast becomes visible changes."""
    global _achievements_seen_ids
    earned_now = set(achievement_ids_earned())
    newly = earned_now - _achievements_seen_ids
    _achievements_seen_ids = earned_now
    if not newly:
        return

    by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
    labels = [by_id[aid]["label"] for aid in newly if aid in by_id]
    if not labels:
        return

    if len(labels) == 1:
        message = f"🏆 Achievement unlocked: {labels[0]}"
    else:
        message = f"🏆 {len(labels)} achievements unlocked: " + ", ".join(labels)

    if delay_ms <= 0:
        _display_achievement_toast(message)
        return

    def _show(*args):
        _display_achievement_toast(message)
        proxy.destroy()

    proxy = create_proxy(_show)
    setTimeout(proxy, delay_ms)


# H3: a first-time-closed-loop celebratory banner — distinct from (and in
# addition to) the achievement-unlock toast above, since H3 explicitly
# asks for its own celebratory moment, not a reuse of the small
# achievement toast. Tracks whether the loop was already closed
# immediately before the action that just ran, so this only fires on the
# false->true transition, never on every render while it stays closed.
def _trigger_circular_burst():
    """H6: a small particle burst when circular share crosses a 25% step."""
    el = document.getElementById("circular-burst")
    el.classList.add("circular-burst--active")

    def _clear(*args):
        el.classList.remove("circular-burst--active")
        proxy.destroy()

    proxy = create_proxy(_clear)
    setTimeout(proxy, 900)


def _milestone_step(fraction):
    return min(BURST_MILESTONES, int(fraction * BURST_MILESTONES + 1e-9))


# H13 audit fix: how long the loop-closed banner stays visible, shared with
# _run_action()'s toast-delay so the two constants can't drift apart.
LOOP_CLOSED_BANNER_DURATION_MS = 5000


def _show_loop_closed_banner():
    banner = document.getElementById("loop-closed-banner")
    # H16: name the exact cycle the loop first closed on.
    if chain.first_loop_closed_cycle is None:
        chain.first_loop_closed_cycle = chain.cycle_number
        text = (
            f"🔁 Loop closed for the first time, on cycle {chain.first_loop_closed_cycle} — 100% of "
            "this cycle's production came from repair, reuse & recycling. No new extraction needed."
        )
    else:
        text = (
            "🔁 Loop closed — 100% of this cycle's production came from repair, reuse & recycling. "
            "No new extraction needed."
        )
    document.getElementById("loop-closed-banner-text").innerText = text
    banner.hidden = False
    banner.classList.add("visible")

    def _hide(*args):
        banner.hidden = True
        banner.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, LOOP_CLOSED_BANNER_DURATION_MS)


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


def pulse_tier(delta_units):
    """H26: 'small' / 'medium' / 'large' by the size of the supply change."""
    delta = abs(delta_units)
    if delta >= PULSE_LARGE_UNITS:
        return "large"
    if delta >= PULSE_MEDIUM_UNITS:
        return "medium"
    return "small"


def _trigger_trade_network_pulse(delta_units=PULSE_MEDIUM_UNITS):
    """H18: a brief visible pulse on the trade-network readout whenever
    its rendered numbers actually change. H26: intensity varies with the
    size of the change (a tier class alongside the base pulse class)."""
    el = document.getElementById("trade-network-display")
    tier_class = f"trade-network-display--pulse-{pulse_tier(delta_units)}"
    el.classList.add("trade-network-display--pulse")
    el.classList.add(tier_class)

    def _clear(*args):
        el.classList.remove("trade-network-display--pulse")
        el.classList.remove(tier_class)
        proxy.destroy()

    proxy = create_proxy(_clear)
    setTimeout(proxy, 700)


# ===========================================================================
# K16 (planning/TODO.md "What's New" changelog, site-wide goal): a small
# in-game "what's new" panel, same shape as the achievements catalog above
# -- a flat JSON list fetched into the Pyodide boot sequence and handed to
# Python as a window global (see index.html), rendered into a
# hidden-until-opened panel. Unlike achievements.json this catalog isn't a
# set of checkable conditions -- it's just curated highlight text -- so
# there's no earned/unearned state, only a newest-first list.
# ===========================================================================
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    """Same loading contract as _read_achievements_json(): the boot script
    fetches changelog.json and hands it to Python as a window global before
    this file runs; the pytest harness's fake `js` module has no such
    attribute, so this falls through to reading the file straight off disk,
    keeping the module importable outside a real browser."""
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "CHANGELOG_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 -- only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, CHANGELOG_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to "no changelog" rather than crashing this module's whole
# import -- same defensive shape as ACHIEVEMENTS above, since a "what's
# new" panel is additive, not core to Loop's gameplay.
try:
    CHANGELOG = sorted(json.loads(_read_changelog_json()), key=lambda entry: entry["date"], reverse=True)
except (ValueError, OSError, NameError, KeyError):
    CHANGELOG = []

changelog_open = False


def on_toggle_changelog(event=None):
    global changelog_open
    changelog_open = not changelog_open
    update_changelog_display()


def update_changelog_display():
    toggle = document.getElementById("changelog-toggle-button")
    panel = document.getElementById("changelog-panel")
    toggle.innerText = "Hide What's New" if changelog_open else f"\U0001f4cb What's New ({len(CHANGELOG)})"
    panel.hidden = not changelog_open
    if not changelog_open:
        return

    panel.innerHTML = ""
    if not CHANGELOG:
        empty = document.createElement("p")
        empty.innerText = "Nothing logged yet."
        panel.appendChild(empty)
        return

    for entry in CHANGELOG:
        row = document.createElement("div")
        row.className = "changelog-entry"

        date = document.createElement("p")
        date.className = "changelog-entry-date"
        date.innerText = entry["date"]
        row.appendChild(date)

        text = document.createElement("p")
        text.className = "changelog-entry-text"
        text.innerText = entry["entry"]
        row.appendChild(text)

        panel.appendChild(row)


# ===========================================================================
# Round-2 helpers (H2, H12, H15, H18, H25a/H29a, H27, H30). Pure functions of
# state, so they are directly testable.
# ===========================================================================
def streak_progress_text():
    """H2: a small text progress bar toward the next 5-cycle streak mark.
    Deliberately neutral (no flame/guilt framing): a plain 'x of 5'."""
    streak = chain.closed_loop_streak
    into = streak % STREAK_PROGRESS_STEP
    target = (streak // STREAK_PROGRESS_STEP + 1) * STREAK_PROGRESS_STEP
    bar = "\u25b0" * into + "\u25b1" * (STREAK_PROGRESS_STEP - into)
    return f"{bar}  {streak} of {target} cycles toward the next streak mark"


def score_pie_percentages():
    """H12: (funds_pct, bonus_pct) shares of the score, summing to 100."""
    bonus = chain.lifetime_circular_fraction() * CIRCULARITY_BONUS_WEIGHT
    total = chain.funds + bonus
    if total <= 0:
        return (100, 0)
    bonus_pct = round(bonus / total * 100)
    return (100 - bonus_pct, bonus_pct)


def score_pie_style():
    funds_pct, _ = score_pie_percentages()
    return f"conic-gradient(#e0c24c 0 {funds_pct}%, #4c9c6e {funds_pct}% 100%)"


def top_investment_measure():
    """H18: the circularity measure with the most invested (ties broken by
    catalog order); None if nothing is invested yet."""
    best, best_count = None, 0
    for measure in CIRCULARITY_INVESTMENTS:
        if chain.circularity_investment[measure] > best_count:
            best, best_count = measure, chain.circularity_investment[measure]
    return best


def _partner_options():
    """(label, cost, supply_per_unit) for every purchasable supply source."""
    options = [
        (spec["label"], spec["cost"], spec["supply_per_unit"]) for spec in CIRCULARITY_INVESTMENTS.values()
    ]
    options.append(("Trade Link", TRADE_LINK_COST, IMPORT_SUPPLY_PER_UNIT))
    options.append(("Regional Partner", REGIONAL_TRADE_COST, REGIONAL_IMPORT_SUPPLY_PER_UNIT))
    options.append(("Overseas Consortium", OVERSEAS_TRADE_COST, OVERSEAS_IMPORT_SUPPLY_PER_UNIT))
    return options


def audit_lines():
    """H15: where supply/money is being wasted right now, with an
    actionable suggestion each. Always returns at least one line."""
    lines = []
    gap = chain.new_extraction_needed()
    surplus = chain.exportable_surplus()
    if gap > 0:
        cost = gap * EXTRACTION_COST_PER_UNIT * chain.extraction_cost_multiplier()
        lines.append(
            f"New extraction is {gap:.0f} units this cycle, costing about {cost:.0f} funds "
            f"(and adding to lasting damage)."
        )
        label, unit_cost, supply = min(_partner_options(), key=lambda o: o[1] / o[2])
        buys = math.ceil(gap / supply)
        lines.append(
            f"Cheapest way to cover it: {label} at {unit_cost / supply:.1f} funds/unit -- "
            f"about {buys} purchase(s), {buys * unit_cost} funds."
        )
    if surplus > 0:
        lines.append(
            f"{surplus:.0f} units of supply exceed the production target; they sell for only "
            f"{EXPORT_PRICE_PER_UNIT:.0f}/unit versus {SALE_PRICE_PER_UNIT:.0f} for goods, so more investment "
            f"here adds little."
        )
    if chain.extraction_cost_multiplier() > 1.5:
        lines.append(
            f"Damage has pushed extraction cost to x{chain.extraction_cost_multiplier():.2f}; "
            "each extracted unit now costs noticeably more."
        )
    if not lines:
        lines.append("Nothing is being wasted right now: supply matches the production target.")
    return lines


def network_map_text():
    """H25a/H29a: a simple, everywhere-works text map of the chain, the
    internal recovery loop, and every trade partner's flow."""
    internal = chain.internal_circular_supply()
    parts = " / ".join(
        f"{CIRCULARITY_INVESTMENTS[m]['icon']} {chain.circularity_investment[m] * CIRCULARITY_INVESTMENTS[m]['supply_per_unit']:.0f}"
        for m in CIRCULARITY_INVESTMENTS
    )
    lines = [
        "Extract -> Manufacture -> Use -> Discard",
        f"   new extraction: {chain.new_extraction_needed():.0f}/cycle",
        f"Internal loop back into Manufacture: {internal:.0f}/cycle  ({parts})",
        "Trade partners:",
        f"  Trade Link          in +{chain.trade_link_investment * IMPORT_SUPPLY_PER_UNIT:.0f}",
        f"  Regional Partner    in +{chain.regional_trade_investment * REGIONAL_IMPORT_SUPPLY_PER_UNIT:.0f}",
        f"  Overseas Consortium in +{chain.overseas_trade_investment * OVERSEAS_IMPORT_SUPPLY_PER_UNIT:.0f}",
        f"  surplus out -> {chain.exportable_surplus():.0f}/cycle",
    ]
    return "\n".join(lines)


def featured_goods_category(week_index=None):
    """H27: the 'challenge of the week' goods category -- deterministic
    rotation by week number, so no backend is needed and every player
    sees the same one. `week_index` defaults to the current UTC week."""
    if week_index is None:
        import time  # noqa: PLC0415
        week_index = int(time.time() // (7 * 24 * 3600))
    keys = list(GOODS_CATEGORIES)
    return keys[week_index % len(keys)]


def reset_chain_message():
    """H30: the confirmation shown after Start New Chain, naming the two
    lifetime counters that survive it."""
    return (
        f"New chain started. Kept from before: {chains_completed_count} chain(s) completed, "
        f"{len(goods_categories_tried)} goods categor{'y' if len(goods_categories_tried) == 1 else 'ies'} tried."
    )


def render():
    render_info_page()
    update_achievements_display()
    update_changelog_display()

    picker = document.getElementById("goods-category-picker")
    picker.hidden = chain.total_produced > 0
    for key in GOODS_CATEGORIES:
        button = document.getElementById(f"goods-category-{key}-button")
        if key == chain.goods_category:
            button.classList.add("selected")
        else:
            button.classList.remove("selected")

    # H13/H23: the two opt-in modes live in the picker (so they vanish with
    # it after the first cycle); their status line stays visible.
    for which, active in (("challenge", chain.challenge_mode), ("zero-waste", chain.zero_waste)):
        mode_button = document.getElementById(f"{which}-mode-button")
        if active:
            mode_button.classList.add("selected")
        else:
            mode_button.classList.remove("selected")
        mode_button.innerText = (
            ("\u2713 " if active else "")
            + ("Circular design challenge" if which == "challenge" else "Zero-waste challenge")
        )
    culture_button = document.getElementById("culture-invest-button")
    if chain.culture_level >= CULTURE_MAX_LEVEL:
        culture_button.innerText = "Culture campaign (max)"
        culture_button.disabled = True
    else:
        culture_button.innerText = f"Culture campaign ({chain.culture_cost()})"
        culture_button.disabled = chain.funds < chain.culture_cost()
    document.getElementById("culture-count").innerText = str(chain.culture_level)
    document.getElementById("culture-stats").innerText = (
        f"Each level trims {CULTURE_DEMAND_REDUCTION * 100:.0f}% off the material a cycle needs · "
        f"now {chain.material_need():.0f} of {PRODUCTION_TARGET:.0f} units"
    )
    render_passport()
    mode_text = mode_status_text()
    mode_el = document.getElementById("mode-status")
    mode_el.innerText = mode_text
    mode_el.hidden = mode_text == ""

    # H4: relabel panel only once the picker itself is gone.
    document.getElementById("relabel-goods-panel").hidden = not picker.hidden
    for key in GOODS_CATEGORIES:
        rb = document.getElementById(f"relabel-{key}-button")
        if key == chain.goods_category:
            rb.classList.add("selected")
        else:
            rb.classList.remove("selected")
    featured = featured_goods_category()
    document.getElementById("featured-goods-display").innerText = (
        f"Challenge of the week: try a chain of {GOODS_CATEGORIES[featured]['label']} "
        f"{GOODS_CATEGORIES[featured]['icon']}."
    )

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
    document.getElementById("vignette-display").innerText = vignette_message(
        fraction, variant_seed=vignette_variant + vignette_session_offset
    )

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
    # H8: a small trend arrow on the per-unit extraction cost; H22: the
    # hard-ceiling multiplier spelled out in the tooltip.
    trend_word = chain.extraction_cost_trend()
    trend_note = " \u2197 pricier than last cycle" if trend_word == "rising" else ""
    document.getElementById("damage-display").innerText += trend_note
    document.getElementById("damage-display").title = (
        f"Extraction cost has a hard ceiling of x{MAX_COST_MULTIPLIER:.2f} -- it can never rise above that, "
        f"however much damage accumulates. Currently x{chain.extraction_cost_multiplier():.2f}."
    )
    # V-E-4 (H10): the same ceiling note as visible text, not only a hover tooltip.
    document.getElementById("damage-ceiling-note").innerText = (
        f"Extraction cost has a hard ceiling of x{MAX_COST_MULTIPLIER:.2f}: it can never rise above that, "
        f"however much damage accumulates. Currently x{chain.extraction_cost_multiplier():.2f}."
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
    render_scorecard()
    # H5: live cross-player comparison, distinct from the two static
    # real-world/sector comparisons just above -- see
    # _request_community_comparison()'s own docstring.
    _request_community_comparison()
    document.getElementById("streak-display").innerText = (
        f"Closed-loop streak: {chain.closed_loop_streak} cycle(s) (best: {chain.best_closed_loop_streak})"
    )

    # H2 / H24: streak progress, and cycles since last new extraction.
    document.getElementById("streak-progress").innerText = streak_progress_text()
    since = document.getElementById("streak-since-display")
    since.hidden = chain.circular_fraction_this_cycle() < 0.75
    since.innerText = f"Cycles since last new extraction: {chain.closed_loop_streak}"
    # H12: score-source pie, H15: audit.
    funds_pct, bonus_pct = score_pie_percentages()
    document.getElementById("score-pie").style.background = score_pie_style()
    document.getElementById("score-pie-legend").innerText = (
        f"Score sources: funds {funds_pct}% (gold), circular bonus {bonus_pct}% (green)"
    )
    document.getElementById("audit-body").innerHTML = "".join(f"<p>{line}</p>" for line in audit_lines())

    top_measure = top_investment_measure()
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
        contribution = (
            chain.circularity_investment[measure] * spec["supply_per_unit"]
            * chain.supply_multiplier() * chain.measure_multiplier(measure)
        )
        focus_note = " · focus +25%" if chain.waste_focus == measure else ""
        if chain.redesign_level[measure]:
            focus_note += f" · redesign +{round(REDESIGN_SUPPLY_BONUS * chain.redesign_level[measure] * 100)}%"
        redesign_button = document.getElementById(f"redesign-{measure}-button")
        if chain.redesign_level[measure] >= REDESIGN_MAX_LEVEL:
            redesign_button.innerText = "Redesigned (max)"
            redesign_button.disabled = True
        elif not chain.redesign_unlocked():
            redesign_button.innerText = "Redesign (unlocks once the loop closes)"
            redesign_button.disabled = True
        else:
            redesign_button.innerText = f"Redesign ({chain.redesign_cost(measure)})"
            redesign_button.disabled = chain.funds < chain.redesign_cost(measure)
        document.getElementById(f"{measure}-stats").innerText = (
            f"{cost_per_unit:.1f} funds/unit · supplying {contribution:.0f}/cycle{focus_note}"
        )
        focus_button = document.getElementById(f"focus-{measure}-button")
        if chain.waste_focus == measure:
            focus_button.classList.add("focus-button--on")
        else:
            focus_button.classList.remove("focus-button--on")
        focus_button.innerText = "\u2605 Focused" if chain.waste_focus == measure else "Focus"

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
        # H18: extra glow on the node receiving the most investment.
        if measure == top_measure:
            node.className += " loop-ring-node--top"

    document.getElementById("trade-link-count").innerText = str(chain.trade_link_investment)
    trade_link_button = document.getElementById("trade-link-invest-button")
    trade_link_button.innerText = f"Trade Link ({TRADE_LINK_COST})"
    trade_link_button.disabled = chain.funds < TRADE_LINK_COST
    # Onboarding-tooltip coverage (planning/TODO.md, origin A14): the two
    # trade-partner buttons look interchangeable at a glance and the
    # section's own "i" toggle only explains Trade Link generally, never
    # mentioning Regional Partner exists or how the two differ. A returning
    # player who forgot the H8 second-partner mechanic had nothing in the
    # permanent UI to explain the choice. `title` states each one's real
    # cost-per-unit so the two buttons self-explain on hover/long-press.
    trade_link_button.title = (
        f"{TRADE_LINK_COST} funds for {IMPORT_SUPPLY_PER_UNIT:.0f} imported units/cycle "
        f"({TRADE_LINK_COST / IMPORT_SUPPLY_PER_UNIT:.2f} funds/unit)."
    )

    document.getElementById("regional-trade-count").innerText = str(chain.regional_trade_investment)
    regional_trade_button = document.getElementById("regional-trade-invest-button")
    regional_trade_button.innerText = f"Regional Partner ({REGIONAL_TRADE_COST})"
    regional_trade_button.disabled = chain.funds < REGIONAL_TRADE_COST
    regional_trade_button.title = (
        f"{REGIONAL_TRADE_COST} funds for {REGIONAL_IMPORT_SUPPLY_PER_UNIT:.0f} imported units/cycle "
        f"({REGIONAL_TRADE_COST / REGIONAL_IMPORT_SUPPLY_PER_UNIT:.2f} funds/unit) — a separate trade "
        f"partner from Trade Link, so both can be invested in at once."
    )

    document.getElementById("overseas-trade-count").innerText = str(chain.overseas_trade_investment)
    overseas_button = document.getElementById("overseas-trade-invest-button")
    overseas_button.innerText = f"Overseas Consortium ({OVERSEAS_TRADE_COST})"
    overseas_button.disabled = chain.funds < OVERSEAS_TRADE_COST
    overseas_button.title = (
        f"{OVERSEAS_TRADE_COST} funds for {OVERSEAS_IMPORT_SUPPLY_PER_UNIT:.0f} imported units/cycle "
        f"({OVERSEAS_TRADE_COST / OVERSEAS_IMPORT_SUPPLY_PER_UNIT:.2f} funds/unit) -- the best price per unit "
        f"of the three partners, but a big single purchase."
    )
    # H28: one-time hint the first time the Regional Partner is affordable.
    document.getElementById("regional-hint").hidden = not (
        chain.funds >= REGIONAL_TRADE_COST and not regional_hint_seen
    )
    document.getElementById("network-map-display").innerText = network_map_text()

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


def on_invest_overseas_trade(event=None):
    _run_action(chain.invest_overseas_trade)


def on_dismiss_regional_hint(event=None):
    global regional_hint_seen
    regional_hint_seen = True
    render()


def _make_relabel_handler(category):
    """H4: cosmetic-only -- changes labels/vignette item, deliberately
    does NOT add to goods_categories_tried (that counter and the
    achievements built on it measure real picks at chain start)."""
    def handler(event=None):
        def _do_relabel():
            chain.goods_category = category
        _run_action(_do_relabel)
    return handler


def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm):
    """Routes a guarded action through the shared shared/confirm-dialog.js
    widget when it's available, or runs the action immediately when it
    isn't -- same lazy `from js import window`/getattr-default shape as
    Grid's/Herd's/Trade Empire's own `_confirm_dialog_ask()` helpers. The
    pytest fake-DOM harness's `js` module only ever fakes `document`/
    `setTimeout` (see tests/conftest.py), never `window`, so `from js
    import window` raises ImportError there and this falls straight
    through to calling on_confirm() synchronously -- which is exactly
    what the existing reset-chain test already expects."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        on_confirm()
        return
    confirm_dialog = getattr(window, "ConfirmDialog", None)
    if confirm_dialog is None:
        on_confirm()
        return
    confirm_dialog.ask(
        id=action_id,
        message=message,
        confirmLabel=confirm_label,
        onConfirm=create_proxy(on_confirm),
    )


def on_reset_chain(event=None):
    """H7: an in-game "Start New Chain" reset control. Wipes the current
    chain back to a fresh ChainState() (funds, cycle number, every
    investment) — the two module-level counters that exist specifically
    to measure things *across* resets (chains_completed_count,
    goods_categories_tried) are deliberately not touched here.

    Z22 cross-game audit: unlike every other game's reset/retire-style
    action, this one fired instantly with no confirmation at all --
    gated now behind the shared ConfirmDialog (same helper shape as
    Grid's retire-last-plant and Herd's pivot-investment guards) rather
    than left as a silent one-click wipe."""

    def _do_reset():
        global chain
        chain = ChainState()

    def _confirmed():
        global chains_completed_count
        chains_completed_count += 1
        _run_action(_do_reset)
        message = document.getElementById("reset-chain-message")
        message.innerText = reset_chain_message()
        message.hidden = False

    _confirm_dialog_ask(
        action_id="loop-reset-chain",
        message=(
            "Start a new chain? This wipes your current funds, cycle, and every "
            "circularity/trade investment. Chains completed and goods categories "
            "tried are kept."
        ),
        confirm_label="Start New Chain",
        on_confirm=_confirmed,
    )


def _make_goods_category_handler(category):
    def handler(event=None):
        def _do_select():
            chain.goods_category = category
            goods_categories_tried.add(category)
        _run_action(_do_select)
    return handler


def render_passport():
    """H21: the traced unit's journey, newest first, plus a one-line tally."""
    container = document.getElementById("passport-list")
    container.innerHTML = ""
    summary = document.getElementById("passport-summary")
    if not chain.passport:
        summary.innerText = f"Unit #1 of {current_goods_label()} hasn't started its journey yet: advance a cycle."
        return
    mined, recovered, longest = chain.passport_summary()
    summary.innerText = (
        f"Unit #1 of {current_goods_label()}: newly mined {mined} time(s), kept in the loop {recovered} time(s), "
        f"longest unbroken run in the loop {longest} cycle(s)."
    )
    for entry in reversed(chain.passport[-8:]):
        row = document.createElement("li")
        row.className = "passport-entry"
        row.innerText = f"Cycle {entry['cycle']}: {PASSPORT_SOURCE_LABEL[entry['source']]}"
        container.appendChild(row)


def on_invest_culture(event=None):
    _run_action(chain.invest_culture)


def _make_redesign_handler(measure):
    def handler(event=None):
        _run_action(lambda: chain.redesign(measure))
    return handler


def _make_focus_handler(measure):
    def handler(event=None):
        def _do_focus():
            # Clicking the focused measure again clears the emphasis.
            chain.set_waste_focus(None if chain.waste_focus == measure else measure)
        _run_action(_do_focus)
    return handler


def mode_status_text():
    """H13/H23: one line describing the modes in force, or '' for none."""
    parts = []
    if chain.challenge_mode:
        parts.append(
            f"Circular design challenge: all circular supply counts at "
            f"{CHALLENGE_MODE_SUPPLY_MULTIPLIER * 100:.0f}%, so closing the loop takes more investment."
        )
    if chain.zero_waste:
        used = chain.total_extracted
        if chain.zero_waste_holding():
            parts.append(
                f"Zero-waste challenge: {used:.0f} of {ZERO_WASTE_EXTRACTION_CAP:.0f} units extracted "
                f"\u2014 still under the cap."
            )
        else:
            parts.append(
                f"Zero-waste challenge missed: {used:.0f} units extracted, over the "
                f"{ZERO_WASTE_EXTRACTION_CAP:.0f} cap. Play carries on."
            )
    return " ".join(parts)


def _make_mode_handler(which):
    def handler(event=None):
        def _do_toggle():
            if which == "challenge":
                chain.set_challenge_mode(not chain.challenge_mode)
            else:
                chain.set_zero_waste(not chain.zero_waste)
        _run_action(_do_toggle)
    return handler


def supply_after_minus(supply_before):
    return chain.imported_supply() + chain.exportable_surplus() - supply_before


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
    step_before = _milestone_step(chain.circular_fraction_this_cycle())
    supply_before = chain.imported_supply() + chain.exportable_surplus()

    mutate_fn()
    render()

    # H6: burst on crossing upward through a 25% step (not on every render).
    if _milestone_step(chain.circular_fraction_this_cycle()) > step_before:
        _trigger_circular_burst()

    if chain.lifetime_export_revenue > export_before:
        _trigger_funds_burst()
    if document.getElementById("trade-network-display").innerText != trade_text_before:
        _trigger_trade_network_pulse(supply_after_minus(supply_before))
    # H13 audit fix (planning/TODO.md V-E-5): closing the loop for the
    # first time also satisfies the "loop_closed" achievement check, so
    # without this the loop-closed banner and the achievement-unlock toast
    # would both appear on screen from this exact same action. Sequence
    # them instead of suppressing either: the banner (the bigger, rarer,
    # H3-specific celebratory moment) shows immediately as before, and any
    # achievement toast this same action also earned is held back until
    # the banner's own visible window has passed.
    loop_just_closed = chain.is_loop_closed() and not was_closed
    if loop_just_closed:
        _show_loop_closed_banner()
    _check_new_achievements_for_toast(delay_ms=LOOP_CLOSED_BANNER_DURATION_MS if loop_just_closed else 0)


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
    state = {
        "cycle_number": chain.cycle_number,
        "funds": chain.funds,
        "total_extracted": chain.total_extracted,
        "total_produced": chain.total_produced,
        # H5: a derived, read-only field -- not restored by load_state()
        # below, just recomputed fresh from total_extracted/total_produced
        # every call. Exposed here purely so app/stats.py's STATS_FIELDS
        # whitelist (a plain top-level get_state() field, planning/TODO.md
        # Z1) can read it directly instead of a consumer having to derive
        # the fraction itself from two separate raw-count fields.
        "lifetime_circular_fraction": chain.lifetime_circular_fraction(),
        "circularity_investment": copy.deepcopy(chain.circularity_investment),
        "circular_fraction_log": copy.deepcopy(chain.circular_fraction_log),
        "trade_link_investment": chain.trade_link_investment,
        "regional_trade_investment": chain.regional_trade_investment,
        "overseas_trade_investment": chain.overseas_trade_investment,
        "first_loop_closed_cycle": chain.first_loop_closed_cycle,
        "regional_hint_seen": regional_hint_seen,
        "goods_category": chain.goods_category,
        "lifetime_investment_spend": chain.lifetime_investment_spend,
        "lifetime_export_revenue": chain.lifetime_export_revenue,
        "closed_loop_streak": chain.closed_loop_streak,
        "best_closed_loop_streak": chain.best_closed_loop_streak,
        "chains_completed_count": chains_completed_count,
        "goods_categories_tried": sorted(goods_categories_tried),
        "achievements_earned": achievement_ids_earned(),
    }
    # H13/H23: written only when a mode is on, so older/default saves are unchanged.
    if chain.challenge_mode:
        state["challenge_mode"] = True
    if chain.zero_waste:
        state["zero_waste"] = True
    if chain.waste_focus is not None:
        state["waste_focus"] = chain.waste_focus
    if any(chain.redesign_level.values()):
        state["redesign_level"] = dict(chain.redesign_level)
    if chain.culture_level:
        state["culture_level"] = chain.culture_level
    if chain.passport:
        state["passport"] = [dict(e) for e in chain.passport]
    return state


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
    global chains_completed_count, goods_categories_tried, regional_hint_seen

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
    chain.overseas_trade_investment = data.get("overseas_trade_investment", 0)
    chain.first_loop_closed_cycle = data.get("first_loop_closed_cycle", None)
    regional_hint_seen = bool(data.get("regional_hint_seen", False))
    chain.goods_category = data.get("goods_category", DEFAULT_GOODS_CATEGORY)
    # H13/H23: strictly booleans; anything else loads as off.
    chain.challenge_mode = data.get("challenge_mode") is True
    chain.zero_waste = data.get("zero_waste") is True
    saved_focus = data.get("waste_focus")
    chain.waste_focus = saved_focus if isinstance(saved_focus, str) and saved_focus in CIRCULARITY_INVESTMENTS else None
    saved_culture = data.get("culture_level")
    chain.culture_level = (
        saved_culture
        if isinstance(saved_culture, int) and not isinstance(saved_culture, bool) and 0 <= saved_culture <= CULTURE_MAX_LEVEL
        else 0
    )
    chain.passport = []
    saved_passport = data.get("passport")
    if isinstance(saved_passport, list):
        for entry in saved_passport:
            if (
                isinstance(entry, dict)
                and isinstance(entry.get("cycle"), int) and not isinstance(entry.get("cycle"), bool)
                and entry["cycle"] >= 1
                and isinstance(entry.get("source"), str) and entry["source"] in PASSPORT_SOURCES
            ):
                chain.passport.append({"cycle": entry["cycle"], "source": entry["source"]})
        del chain.passport[:-PASSPORT_MAX_ENTRIES]
    chain.redesign_level = {m: 0 for m in CIRCULARITY_INVESTMENTS}
    saved_redesign = data.get("redesign_level")
    if isinstance(saved_redesign, dict):
        for m in CIRCULARITY_INVESTMENTS:
            level = saved_redesign.get(m)
            if isinstance(level, int) and not isinstance(level, bool) and 0 <= level <= REDESIGN_MAX_LEVEL:
                chain.redesign_level[m] = level
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
    document.getElementById("culture-invest-button").addEventListener("click", create_proxy(on_invest_culture))
    for measure in CIRCULARITY_INVESTMENTS:
        document.getElementById(f"focus-{measure}-button").addEventListener(
            "click", create_proxy(_make_focus_handler(measure))
        )
        document.getElementById(f"redesign-{measure}-button").addEventListener(
            "click", create_proxy(_make_redesign_handler(measure))
        )
    for which in ("challenge", "zero-waste"):
        document.getElementById(f"{which}-mode-button").addEventListener(
            "click", create_proxy(_make_mode_handler("challenge" if which == "challenge" else "zero"))
        )
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    document.getElementById("overseas-trade-invest-button").addEventListener(
        "click", create_proxy(on_invest_overseas_trade)
    )
    document.getElementById("regional-hint-dismiss-button").addEventListener(
        "click", create_proxy(on_dismiss_regional_hint)
    )
    for category in GOODS_CATEGORIES:
        document.getElementById(f"relabel-{category}-button").addEventListener(
            "click", create_proxy(_make_relabel_handler(category))
        )
    document.getElementById("reset-chain-message").hidden = True
    document.getElementById("regional-hint").hidden = True
    # H20: random per-session vignette-variant offset (real browser only;
    # the pytest fake `js` has no Math, so tests stay deterministic).
    global vignette_session_offset
    try:
        from js import Math  # noqa: PLC0415
        vignette_session_offset = int(Math.random() * 1000)
    except ImportError:
        vignette_session_offset = 0
    _seed_achievement_toast_baseline()
    render()


setup()
