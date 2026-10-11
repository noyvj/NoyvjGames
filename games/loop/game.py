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
import html
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

# GH-14: a secret fourth goods category, revealed once a loop has fully closed on
# each of the three ordinary categories. It is deliberately NOT in GOODS_CATEGORIES
# (which drives the picker, the relabel row, the weekly feature and the "collect
# every category" achievement); SECRET_GOODS_CATEGORY is looked up alongside it by
# ALL_GOODS. Its own flavour: a ship-breaking yard starts with a built-in scrap
# recovery line (SECRET_HEAD_START_UNITS of supply per cycle, counted as recycling),
# the yard's real trade being to take things apart.
SECRET_GOODS_CATEGORY = "shipyard"
SECRET_GOODS = {
    "label": "scrap steel",
    "vignette_item": "a ship's hull",
    "icon": "\U0001F6A2",
    "name": "Ship-Breaking Yard",
}
SECRET_HEAD_START_UNITS = 6.0
ALL_GOODS = {**GOODS_CATEGORIES, SECRET_GOODS_CATEGORY: SECRET_GOODS}

CATEGORY_LOOP_DETAIL[SECRET_GOODS_CATEGORY] = {
    "closed": [
        "its plates were cut free and rolled into new hull steel, its engines were "
        "rebuilt for another ship, and not a tonne was left on the beach",
        "every deck plate went back to the mill and every working pump was refitted "
        "somewhere else, so the old ship became the next one",
    ],
    "majority": [
        "most of its steel gets cut up for the mill and much of its machinery is "
        "stripped for refit before the rest is scrapped",
        "more often than not its engines and fittings are salvaged and its plate "
        "is melted down, with only the awkward remainder lost",
    ],
    "minority": [
        "some of its steel is cut up and sold on, though most of it is still hauled "
        "up a beach and abandoned",
        "a little of its metal is recovered, but the rest of the hull is left to "
        "rust where it was run aground",
    ],
    "none": [
        "run aground, picked over and left, with its steel and its oils soaking "
        "into the shore",
        "built from fresh steel, sailed hard, then beached; nothing about it "
        "goes back into the next hull",
    ],
}

# GH-12: the Perfect Cycle combo. Each consecutive cycle that needed zero new
# extraction raises the combo by one (it is the existing closed-loop streak). From
# the second perfect cycle on, the cycle earns a banked score bonus of
# COMBO_BONUS_PER_LEVEL times (combo - 1), with the combo counted up to COMBO_CAP.
# A cycle that needs extraction drops the combo to zero, but bonus already banked
# stays: it was earned.
COMBO_BONUS_PER_LEVEL = 3.0
COMBO_CAP = 10

# GH-24: streak insurance. Once per chain, pay INSURANCE_COST to freeze the
# closed-loop streak (and so the combo) through ONE cycle that needs extraction.
INSURANCE_COST = 10

# GH-25: a cycle projected to end within this many units of closing the loop (or within
# NEAR_MISS_STEP_UNITS of the next 25% step) gets a "so close" note with the cheapest
# single purchase.
NEAR_MISS_UNITS = 8.0
NEAR_MISS_STEP_UNITS = 5.0  # a tighter window for the 25% marks, which are only 12.5 units apart

# GH-15: name plates, earned by closing the loop with a recognisable supply mix. A
# source that supplies at least PLATE_DOMINANT_SHARE of the circular supply names
# the plate; otherwise the mix is balanced (The Allrounder).
PLATE_DOMINANT_SHARE = 0.5
PLATES = {
    "scrapper": {
        "name": "The Scrapper", "source": "recycle",
        "how": "Close the loop with Recycling supplying at least half of it.",
    },
    "fixer": {
        "name": "The Fixer", "source": "repair",
        "how": "Close the loop with Repair supplying at least half of it.",
    },
    "swapper": {
        "name": "The Swapper", "source": "reuse",
        "how": "Close the loop with Reuse supplying at least half of it.",
    },
    "diplomat": {
        "name": "The Diplomat", "source": "trade",
        "how": "Close the loop with trade partners supplying at least half of it.",
    },
    "allrounder": {
        "name": "The Allrounder", "source": None,
        "how": "Close the loop with no single source supplying half of it.",
    },
}
PLATE_FOR_SOURCE = {spec["source"]: key for key, spec in PLATES.items() if spec["source"]}

# GH-20: speed-loop achievements, judged on the chain's FIRST close and remembered
# across chains.
SPEED_CLOSE_CYCLE = 12
LEAN_CLOSE_EXTRACTION = 500.0

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

# H7: the traced unit is also a NAMED product with a small ongoing story. Each
# goods category follows one named item across cycles; each journey step gets a
# sentence written for that category and source, and every step that keeps the
# product in the loop adds a generation ("its 3rd life"), so the thread has a
# shape: mined, then lives again and again, or back to the mine.
PASSPORT_PRODUCT_NAME = {
    "electronics": "Nova, a phone",
    "clothing": "Juniper, a jacket",
    "furniture": "Oak, a chair",
    SECRET_GOODS_CATEGORY: "Argo, a ship",
}
PASSPORT_STORY = {
    "extraction": {
        "electronics": "{product} starts again from freshly mined metals and rare earths.",
        "clothing": "{product} starts again from new fibre, grown and dyed from scratch.",
        "furniture": "{product} starts again from newly felled timber.",
        "shipyard": "{product} starts again from freshly rolled steel plate.",
    },
    "repair": {
        "electronics": "A new screen and battery keep {product} going ({life}).",
        "clothing": "A patched elbow and fresh buttons keep {product} in wear ({life}).",
        "furniture": "A re-glued joint and a new seat keep {product} in use ({life}).",
        "shipyard": "A re-plated hull and a rebuilt engine keep {product} at sea ({life}).",
    },
    "reuse": {
        "electronics": "{product} is wiped and passed to a new owner ({life}).",
        "clothing": "{product} is passed on through a clothing swap ({life}).",
        "furniture": "{product} finds a second home through a resale shop ({life}).",
        "shipyard": "{product} is sold on to a new owner and a new trade route ({life}).",
    },
    "recycle": {
        "electronics": "{product} is stripped for its metals, which come back as a new device ({life}).",
        "clothing": "{product} is shredded and respun into new yarn ({life}).",
        "furniture": "{product} is chipped and pressed into new board ({life}).",
        "shipyard": "{product} is cut up and rolled into plate for the next hull ({life}).",
    },
    "trade": {
        "electronics": "A partner network ships {product}'s recovered parts in ({life}).",
        "clothing": "A partner network ships recovered fibre for {product} ({life}).",
        "furniture": "A partner network ships reclaimed wood for {product} ({life}).",
        "shipyard": "A partner yard ships salvaged plate and fittings for {product} ({life}).",
    },
}

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
PARTNER_COSTS = {"trade": TRADE_LINK_COST, "regional": REGIONAL_TRADE_COST, "overseas": OVERSEAS_TRADE_COST}
BUY_MULTIPLES = (1, 5, 10)  # H-14: the x1 / x5 / x10 chips
PARTNER_LABELS = {"trade": "Trade Link", "regional": "Regional Partner", "overseas": "Overseas Consortium"}

# GH-3 / FY-37: market shocks. An opt-in mode with a FIXED, public schedule (nothing random, the
# same for every player) so a shock can be planned for: in every block of SHOCK_PERIOD cycles a
# price spike lands on cycle 5, a three-cycle port strike on cycles 9 to 11 (a different trade
# partner each block) and a demand surge on cycle 13. Each is announced one cycle early. They only
# change the price of, the need for, or the supply from OUTSIDE, so a chain that already recovers
# its own material barely notices, and nothing ever fails or takes progress away.
SHOCK_PERIOD = 15
SHOCK_PRICE_AT = 5
SHOCK_STRIKE_AT = 9
SHOCK_STRIKE_CYCLES = 3
SHOCK_DEMAND_AT = 13
SHOCK_PRICE_MULTIPLIER = 1.5  # raw material costs this much more for the one cycle
SHOCK_DEMAND_MULTIPLIER = 1.2  # shoppers want this much more new goods for the one cycle
STRIKE_PARTNERS = ("trade", "regional", "overseas")
SHOCKED_CLOSE_TARGET = 5  # the Shock Absorber achievement: closed cycles that had a shock


def shock_for_cycle(cycle):
    """The shock on a given cycle number (1-based) as a dict, or None. Pure and public: the same
    schedule for everyone. `step` counts 1.. through a multi-cycle shock."""
    cycle = int(cycle)
    if cycle < 1:
        return None
    block, offset0 = divmod(cycle - 1, SHOCK_PERIOD)
    offset = offset0 + 1
    if offset == SHOCK_PRICE_AT:
        return {"kind": "price_spike", "step": 1, "length": 1, "start": cycle}
    if SHOCK_STRIKE_AT <= offset < SHOCK_STRIKE_AT + SHOCK_STRIKE_CYCLES:
        step = offset - SHOCK_STRIKE_AT + 1
        return {
            "kind": "port_strike", "partner": STRIKE_PARTNERS[block % len(STRIKE_PARTNERS)],
            "step": step, "length": SHOCK_STRIKE_CYCLES, "start": cycle - step + 1,
        }
    if offset == SHOCK_DEMAND_AT:
        return {"kind": "demand_surge", "step": 1, "length": 1, "start": cycle}
    return None


def shock_name(shock):
    if shock["kind"] == "price_spike":
        return "Price spike"
    if shock["kind"] == "port_strike":
        return f"Port strike at the {PARTNER_LABELS[shock['partner']]}"
    return "Demand surge"


def shock_effect(shock):
    if shock["kind"] == "price_spike":
        return f"raw material costs x{SHOCK_PRICE_MULTIPLIER:.1f} for one cycle"
    if shock["kind"] == "port_strike":
        return (
            f"the {PARTNER_LABELS[shock['partner']]} cannot deliver for {shock['length']} cycles "
            f"(cycles {shock['start']} to {shock['start'] + shock['length'] - 1})"
        )
    return (
        f"shoppers want {round((SHOCK_DEMAND_MULTIPLIER - 1) * 100)}% more new goods for one cycle, so the chain "
        f"needs {PRODUCTION_TARGET * SHOCK_DEMAND_MULTIPLIER:.0f} units of material instead of {PRODUCTION_TARGET:.0f}"
    )


# GH-5 / FY-38: Rival Corporation, a scripted comparison. It runs the same production target every
# cycle as a pure straight line: all of the material newly extracted, never an investment, so its
# extraction cost climbs with its own damage exactly as the player's would. It is a function of the
# cycle number alone (no randomness, no input from the player), so it is the same every time.
RIVAL_NAME = "Rival Corporation"


def rival_funds_after(cycles):
    """Rival's funds after `cycles` completed cycles."""
    funds = STARTING_FUNDS
    extracted = 0.0
    for _ in range(max(0, int(cycles))):
        damage = min(1.0, extracted / ENVIRONMENTAL_DAMAGE_SCALE)
        multiplier = 1.0 + damage * (MAX_COST_MULTIPLIER - 1.0)
        funds += PRODUCTION_TARGET * SALE_PRICE_PER_UNIT - PRODUCTION_TARGET * EXTRACTION_COST_PER_UNIT * multiplier
        extracted += PRODUCTION_TARGET
    return funds


def rival_extracted_after(cycles):
    return PRODUCTION_TARGET * max(0, int(cycles))


def rival_profit_in_cycle(cycle):
    """What the rival earns in its `cycle`-th cycle (1-based): falls to zero as its damage climbs."""
    return rival_funds_after(cycle) - rival_funds_after(cycle - 1)


BURST_MILESTONES = 4  # circular-fraction crosses each 25% step
PULSE_LARGE_UNITS = 20.0
PULSE_MEDIUM_UNITS = 8.0
STREAK_PROGRESS_STEP = 5  # H2: progress toward the next 5-cycle streak mark

# Iteration Pass 2 — single-item vignette: a concrete side-story
# following one representative product, alongside the abstract chain
# view, for a player who doesn't naturally read a flow diagram.


def current_goods_label():
    spec = ALL_GOODS.get(chain.goods_category, GOODS_CATEGORIES[DEFAULT_GOODS_CATEGORY])
    return spec["label"]


def current_vignette_item():
    spec = ALL_GOODS.get(chain.goods_category, GOODS_CATEGORIES[DEFAULT_GOODS_CATEGORY])
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
        # H11: opt-in donation of the cycle's surplus to the shared regional
        # recycling pool instead of selling it. `last_donation` is the units
        # given in the most recent cycle (transient, never saved).
        self.donate_surplus = False
        self.lifetime_pool_donated = 0.0
        self.last_donation = 0.0
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
        # GH-14: the goods category PICKED at chain start (the relabel panel only changes
        # goods_category, so it cannot be used to unlock or record anything), and the
        # secret category's built-in scrap supply (units per cycle, 0 for the others).
        self.picked_category = DEFAULT_GOODS_CATEGORY
        self.head_start = 0.0
        # GH-12 / GH-24: banked combo score, and the once-per-chain streak insurance.
        self.perfect_bonus = 0.0
        self.insurance_used = False
        self.insurance_armed = False
        # Transient notes about the cycle that just ran (never saved).
        self.last_cycle_mix = None  # shares by source when that cycle needed no extraction
        self.last_combo_gain = 0.0
        self.last_insurance_saved = False
        # GH-20: the chain's first close, for the speed achievements (saved when set).
        self.first_close_extracted = None
        self.first_close_trade_free = None
        # GH-3 / FY-37: the opt-in market-shock mode (saved when on), and how many closed
        # cycles landed on a shock (saved when above zero).
        self.market_shocks = False
        self.shocks_shrugged = 0
        # GH-5 / FY-38: the opt-in Rival Corporation race, and the completed-cycle count at which the
        # player first pulled ahead of it (saved when on / when set).
        self.rival_on = False
        self.rival_crossover_cycle = None
        # GH-18 / FY-39: one rewind per chain. The undo point is a transient copy of the whole chain
        # taken just before each Advance Cycle (never saved); only the spent token is saved.
        self.rewind_used = False
        self.rewind_snapshot = None

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
        parts = {m: self.measure_supply(m) for m in CIRCULARITY_INVESTMENTS}
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
        need = PRODUCTION_TARGET * (1.0 - CULTURE_DEMAND_REDUCTION * self.culture_level)
        shock = self.active_shock()
        if shock is not None and shock["kind"] == "demand_surge":
            need *= SHOCK_DEMAND_MULTIPLIER
        return need

    def active_shock(self):
        """GH-3: this cycle's shock, or None (always None with the mode off)."""
        return shock_for_cycle(self.cycle_number) if self.market_shocks else None

    def next_shock(self):
        """GH-3: a NEW shock that starts next cycle (the early warning), else None."""
        if not self.market_shocks:
            return None
        coming = shock_for_cycle(self.cycle_number + 1)
        return coming if coming is not None and coming["step"] == 1 else None

    def blocked_partner(self):
        """GH-3: the trade partner a port strike has shut this cycle, or None."""
        shock = self.active_shock()
        return shock["partner"] if shock is not None and shock["kind"] == "port_strike" else None

    def shock_price_multiplier(self):
        shock = self.active_shock()
        return SHOCK_PRICE_MULTIPLIER if shock is not None and shock["kind"] == "price_spike" else 1.0

    def price_multiplier(self):
        """What a unit of new extraction actually costs this cycle: the damage multiplier times
        any price spike."""
        return self.extraction_cost_multiplier() * self.shock_price_multiplier()

    def partner_supply(self, kind):
        """Units one trade partner imports per cycle (0 while a port strike shuts it)."""
        if kind == self.blocked_partner():
            return 0.0
        owned, per_unit = {
            "trade": (self.trade_link_investment, IMPORT_SUPPLY_PER_UNIT),
            "regional": (self.regional_trade_investment, REGIONAL_IMPORT_SUPPLY_PER_UNIT),
            "overseas": (self.overseas_trade_investment, OVERSEAS_IMPORT_SUPPLY_PER_UNIT),
        }[kind]
        return self.supply_multiplier() * owned * per_unit

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

    def measure_supply(self, measure):
        """Units one measure supplies per cycle, after every multiplier. The secret
        yard's built-in scrap line (GH-14) counts as recycling, so every view of the
        supply (maps, passport, contribution lines) keeps summing to the same total."""
        base = (
            self.circularity_investment[measure] * CIRCULARITY_INVESTMENTS[measure]["supply_per_unit"]
            * self.measure_multiplier(measure)
        )
        if measure == "recycle":
            base += self.head_start
        return self.supply_multiplier() * base

    def internal_circular_supply(self):
        """Units of this cycle's production target met by repair/reuse/
        recycling instead of new extraction — the chain's own capacity,
        before anything crossing in from the trade network."""
        return sum(self.measure_supply(c) for c in CIRCULARITY_INVESTMENTS)

    def supply_mix(self):
        """GH-15: each source's share (0..1) of the circular supply right now, over
        repair, reuse, recycle and trade; empty when nothing is supplied."""
        units = {m: self.measure_supply(m) for m in CIRCULARITY_INVESTMENTS}
        units["trade"] = self.imported_supply()
        total = sum(units.values())
        if total <= 0:
            return {}
        return {name: value / total for name, value in units.items()}

    def combo_level(self):
        """GH-12: the Perfect Cycle combo, the closed-loop streak counted up to COMBO_CAP."""
        return min(self.closed_loop_streak, COMBO_CAP)

    def next_combo_gain(self):
        """Bonus the NEXT perfect cycle would bank (0 for the first of a run)."""
        level = min(self.closed_loop_streak + 1, COMBO_CAP)
        return COMBO_BONUS_PER_LEVEL * max(0, level - 1)

    def can_buy_insurance(self):
        """GH-24: once per chain, and only with a streak worth protecting."""
        return (
            not self.insurance_used and self.closed_loop_streak >= 1 and self.funds >= INSURANCE_COST
        )

    def buy_insurance(self):
        if not self.can_buy_insurance():
            return False
        self.funds -= INSURANCE_COST
        self.insurance_used = True
        self.insurance_armed = True
        return True

    def note_loop_closed(self):
        """Records the chain's FIRST close (called by the closing action)."""
        if self.first_loop_closed_cycle is not None:
            return False
        self.first_loop_closed_cycle = self.cycle_number
        self.first_close_extracted = self.total_extracted
        self.first_close_trade_free = (
            self.trade_link_investment == 0
            and self.regional_trade_investment == 0
            and self.overseas_trade_investment == 0
        )
        return True

    def imported_supply(self):
        return sum(self.partner_supply(kind) for kind in PARTNER_COSTS)

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

    def unit_cost(self, kind):
        """H-14: the price of ONE purchase of `kind` (a circularity measure or a trade partner)."""
        if kind in CIRCULARITY_INVESTMENTS:
            return CIRCULARITY_INVESTMENTS[kind]["cost"]
        return PARTNER_COSTS[kind]

    def affordable_count(self, kind, wanted):
        """H-14: how many of `wanted` purchases of `kind` the funds cover right now."""
        cost = self.unit_cost(kind)
        return max(0, min(int(wanted), int(self.funds // cost)))

    def invest_many(self, kind, count):
        """H-14: buys up to `count` of `kind`, one after the other, stopping when the funds run
        out. Returns how many were bought. Every purchase is the ordinary single purchase, so
        the lifetime tallies and the rules are exactly the same as clicking `count` times."""
        step = {
            "trade": self.invest_trade_link,
            "regional": self.invest_regional_trade,
            "overseas": self.invest_overseas_trade,
        }.get(kind)
        bought = 0
        for _ in range(max(0, int(count))):
            ok = step() if step else self.invest_circularity(kind)
            if not ok:
                break
            bought += 1
        return bought

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
        # Floored at zero: a demand surge can need more than the target in new material.
        return max(0.0, (PRODUCTION_TARGET - self.new_extraction_needed()) / PRODUCTION_TARGET)

    def lifetime_circular_fraction(self):
        """0..1 — the share of all production ever run through the chain
        that came from circular supply rather than new extraction."""
        if self.total_produced == 0:
            return 0.0
        circular_total = self.total_produced - self.total_extracted
        return max(0.0, circular_total / self.total_produced)

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

    def _snapshot(self):
        """A deep copy of every chain field except the undo point itself."""
        return copy.deepcopy({k: v for k, v in self.__dict__.items() if k != "rewind_snapshot"})

    def rewind_block_reason(self):
        """GH-18: None when a rewind is possible, else a short plain reason."""
        if self.rewind_used:
            return "used"
        if self.rewind_snapshot is None:
            return "no_point"
        if self.last_donation > 0:
            return "donated"
        return None

    def can_rewind(self):
        return self.rewind_block_reason() is None

    def rewind(self):
        """GH-18 / FY-39: one per chain. Puts the chain back exactly as it was before the last
        Advance Cycle (purchases made since are undone too) and spends the token. The career
        records, name plates and goods tried are NOT taken back: they record what happened."""
        if not self.can_rewind():
            return False
        saved = self.rewind_snapshot
        self.__dict__.clear()
        self.__dict__.update(copy.deepcopy(saved))
        self.rewind_used = True
        self.rewind_snapshot = None
        return True

    def advance_cycle(self):
        self.rewind_snapshot = self._snapshot()
        extraction = self.new_extraction_needed()
        cost = extraction * EXTRACTION_COST_PER_UNIT * self.price_multiplier()
        if extraction <= 0.0 and self.active_shock() is not None:
            self.shocks_shrugged += 1  # GH-3: a closed cycle that landed on a shock
        revenue = PRODUCTION_TARGET * SALE_PRICE_PER_UNIT
        surplus = self.exportable_surplus()
        if self.donate_surplus and surplus > 0:
            # H11: the surplus goes to the regional pool, not to market.
            export_revenue = 0.0
            self.last_donation = surplus
            self.lifetime_pool_donated += surplus
        else:
            export_revenue = surplus * EXPORT_PRICE_PER_UNIT
            self.last_donation = 0.0
        self.funds += revenue - cost + export_revenue
        self.lifetime_export_revenue += export_revenue
        # H19: closed-loop streak -- sticky best-ever value, same shape as
        # Grid's best_clean_streak. A cycle only counts toward the streak
        # if it needed zero new extraction (fully closed), matching
        # is_loop_closed()'s own definition.
        self.last_combo_gain = 0.0
        self.last_insurance_saved = False
        self.last_cycle_mix = None
        if extraction <= 0.0:
            # GH-12: the combo bonus uses the streak INCLUDING this cycle.
            self.last_cycle_mix = self.supply_mix()
            self.closed_loop_streak += 1
            self.best_closed_loop_streak = max(self.best_closed_loop_streak, self.closed_loop_streak)
            self.last_combo_gain = COMBO_BONUS_PER_LEVEL * max(0, min(self.closed_loop_streak, COMBO_CAP) - 1)
            self.perfect_bonus += self.last_combo_gain
        elif self.insurance_armed:
            # GH-24: the armed insurance freezes the streak through this one bad cycle.
            self.insurance_armed = False
            self.last_insurance_saved = True
        else:
            self.closed_loop_streak = 0
        self.passport.append({"cycle": self.cycle_number, "source": self.passport_source()})
        del self.passport[:-PASSPORT_MAX_ENTRIES]
        self.circular_fraction_log.append(self.circular_fraction_this_cycle())
        self.total_extracted += extraction
        self.total_produced += PRODUCTION_TARGET
        self.cycle_number += 1
        done = self.cycle_number - 1
        if self.rival_on and self.rival_crossover_cycle is None and self.funds > rival_funds_after(done):
            self.rival_crossover_cycle = done

    def score(self):
        """Profitability plus a direct reward for lifetime circular
        share — a fully closed, sustained loop earns the maximum bonus
        on top of whatever funds it generated."""
        return self.funds + self.lifetime_circular_fraction() * CIRCULARITY_BONUS_WEIGHT + self.perfect_bonus

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

# GH-14/GH-15/GH-20 + H-9: the career, which like the two counters above survives
# "Start New Chain". Everything here is a pure record of what happened (never an input
# to the sums), and rides get_state()/load_state() as one "career" key.
career_closed_categories = set()  # picked categories that ran a fully closed cycle
career_plates = set()  # PLATES keys earned
career_speed = set()  # {"cycle12", "lean", "no_trade"}: speed-loop flags (GH-20)
career_best = {}  # picked category -> {"fastest_close", "lowest_extraction", "best_score", "best_streak"}
CAREER_SPEED_FLAGS = ("cycle12", "lean", "no_trade")
CAREER_BEST_FIELDS = ("fastest_close", "lowest_extraction", "best_score", "best_streak")


def secret_unlocked():
    """GH-14: the secret category opens once every ordinary category has had a fully
    closed cycle."""
    return set(GOODS_CATEGORIES) <= career_closed_categories


def secret_progress():
    return len(career_closed_categories & set(GOODS_CATEGORIES)), len(GOODS_CATEGORIES)


def plate_for_mix(shares):
    """GH-15: which plate a supply mix earns, or None when nothing is supplied."""
    if not shares:
        return None
    source, share = max(shares.items(), key=lambda kv: kv[1])
    if share >= PLATE_DOMINANT_SHARE:
        return PLATE_FOR_SOURCE.get(source, "allrounder")
    return "allrounder"


def _update_career():
    """Idempotent: folds the current chain into the career records. Called after every
    action, so it must only ever add or improve."""
    category = chain.picked_category
    if chain.last_cycle_mix is not None:  # the last cycle ran fully closed
        career_closed_categories.add(category)
        plate = plate_for_mix(chain.last_cycle_mix)
        if plate:
            career_plates.add(plate)
    if chain.first_loop_closed_cycle is not None:
        if chain.first_loop_closed_cycle <= SPEED_CLOSE_CYCLE:
            career_speed.add("cycle12")
        if chain.first_close_extracted is not None and chain.first_close_extracted < LEAN_CLOSE_EXTRACTION:
            career_speed.add("lean")
        if chain.first_close_trade_free:
            career_speed.add("no_trade")
    if chain.total_produced > 0:
        best = career_best.setdefault(category, {})
        score = chain.score()
        if score > best.get("best_score", float("-inf")):
            best["best_score"] = score
        if chain.best_closed_loop_streak > best.get("best_streak", 0):
            best["best_streak"] = chain.best_closed_loop_streak
        if chain.first_loop_closed_cycle is not None:
            fastest = best.get("fastest_close")
            if fastest is None or chain.first_loop_closed_cycle < fastest:
                best["fastest_close"] = chain.first_loop_closed_cycle
            if chain.first_close_extracted is not None:
                lowest = best.get("lowest_extraction")
                if lowest is None or chain.first_close_extracted < lowest:
                    best["lowest_extraction"] = chain.first_close_extracted


def career_state():
    """JSON-safe copy of the career (empty dict when there is nothing to save)."""
    if not (career_closed_categories or career_plates or career_speed or career_best):
        return {}
    return {
        "closed": sorted(career_closed_categories),
        "plates": sorted(career_plates),
        "speed": sorted(career_speed),
        "best": {cat: dict(rec) for cat, rec in sorted(career_best.items())},
    }


def _finite_number(value, low=0.0, high=1e9):
    return (
        isinstance(value, (int, float)) and not isinstance(value, bool)
        and value == value and low <= value <= high
    )


def load_career(data):
    """Validates a saved career key by key; anything unknown or malformed is dropped."""
    career_closed_categories.clear()
    career_plates.clear()
    career_speed.clear()
    career_best.clear()
    if not isinstance(data, dict):
        return
    valid_categories = set(ALL_GOODS)
    closed = data.get("closed")
    if isinstance(closed, list):
        career_closed_categories.update(c for c in closed if isinstance(c, str) and c in valid_categories)
    plates = data.get("plates")
    if isinstance(plates, list):
        career_plates.update(p for p in plates if isinstance(p, str) and p in PLATES)
    speed = data.get("speed")
    if isinstance(speed, list):
        career_speed.update(f for f in speed if isinstance(f, str) and f in CAREER_SPEED_FLAGS)
    best = data.get("best")
    if isinstance(best, dict):
        for category, record in best.items():
            if not (isinstance(category, str) and category in valid_categories and isinstance(record, dict)):
                continue
            clean = {}
            for field in CAREER_BEST_FIELDS:
                value = record.get(field)
                if field in ("fastest_close", "best_streak"):
                    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 100000:
                        clean[field] = value
                elif _finite_number(value, -1e9, 1e9):
                    clean[field] = float(value)
            if clean:
                career_best[category] = clean


def career_reset():
    load_career(None)


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
    "goods_collector": lambda: len(goods_categories_tried & set(GOODS_CATEGORIES)) >= len(GOODS_CATEGORIES),
    # GH-20: speed-loop achievements, remembered across chains (see career_speed).
    "speed_close": lambda: "cycle12" in career_speed,
    "lean_close": lambda: "lean" in career_speed,
    "no_trade_close": lambda: "no_trade" in career_speed,
    # GH-15 / GH-14: the plate collection and the secret yard.
    "plate_collector": lambda: len(career_plates) >= len(PLATES),
    "yard_boss": lambda: SECRET_GOODS_CATEGORY in career_closed_categories,
    # GH-3: closed cycles that landed on a market shock (the mode is opt-in).
    "shock_absorber": lambda: chain.shocks_shrugged >= SHOCKED_CLOSE_TARGET,
    # GH-5: pulled ahead of the scripted Rival Corporation (the race is opt-in).
    "rival_overtaken": lambda: chain.rival_crossover_cycle is not None,
}

# GH-20: shown in the achievements panel only, never as an unlock toast.
SILENT_ACHIEVEMENTS = {"speed_close", "lean_close", "no_trade_close"}

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
    "goods_collector": lambda: (len(goods_categories_tried & set(GOODS_CATEGORIES)), len(GOODS_CATEGORIES)),
    "plate_collector": lambda: (len(career_plates), len(PLATES)),
    "shock_absorber": lambda: (min(chain.shocks_shrugged, SHOCKED_CLOSE_TARGET), SHOCKED_CLOSE_TARGET),
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
    _story_reach_all(_achievements_seen_ids)  # W1: a loaded save's earned chapters come back too


def _story_reach_all(earned_ids):
    """W1: unlocks the story chapter for every earned achievement (and the
    opening one) via the shared story-chapters.js. Idempotent and silent: no
    story script, or a chapter id it does not know, simply does nothing.
    Story progress lives in the browser's localStorage, never in the save."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    story = getattr(window, "NoyvjStory", None)
    if story is None:
        return
    story.reach("begin")
    for achievement_id in sorted(earned_ids):
        story.reach(achievement_id)


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
    _story_reach_all(earned_now)
    newly = earned_now - _achievements_seen_ids
    _achievements_seen_ids = earned_now
    if not newly:
        return

    by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
    labels = [by_id[aid]["label"] for aid in sorted(newly) if aid in by_id and aid not in SILENT_ACHIEVEMENTS]
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


def _show_loop_closed_banner(first=None):
    banner = document.getElementById("loop-closed-banner")
    # H16: name the exact cycle the loop first closed on.
    if first is None:
        first = chain.note_loop_closed()
    if first:
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
    bonus = chain.lifetime_circular_fraction() * CIRCULARITY_BONUS_WEIGHT + chain.perfect_bonus
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
        cost = gap * EXTRACTION_COST_PER_UNIT * chain.price_multiplier()
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


def _strike_note(kind):
    return "  (port strike: shut)" if chain.blocked_partner() == kind else ""


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
        f"  Trade Link          in +{chain.partner_supply('trade'):.0f}{_strike_note('trade')}",
        f"  Regional Partner    in +{chain.partner_supply('regional'):.0f}{_strike_note('regional')}",
        f"  Overseas Consortium in +{chain.partner_supply('overseas'):.0f}{_strike_note('overseas')}",
        f"  surplus out -> {chain.exportable_surplus():.0f}/cycle",
    ]
    return "\n".join(lines)


# ===========================================================================
# H25b/H29b: richer, opt-in SVG versions of the trade network (H25a) and the
# circular supply chain map (H29a). Every number is read from the live
# ChainState (nothing invented); the simple text versions above stay the
# default and keep working everywhere. The SVG is built here as plain
# strings (pure functions of state, so directly testable); the wide-screen
# breakout, tooltips, animation and the narrow-screen fallback note are CSS
# and rich-maps.js. Browser preference only (never part of a save code).
# ===========================================================================
RICH_MIN_WIDTH_PX = 900  # mirrors the @media breakpoint in style.css


def _esc(value):
    return html.escape(str(value), quote=True)


def _fmt(units):
    """Units per cycle: whole numbers plain, fractional ones to 1 dp."""
    return f"{units:.0f}" if abs(units - round(units)) < 0.05 else f"{units:.1f}"


def _flow_width(units, scale):
    """Stroke width (viewBox units) for a flow; 0 means no flow at all.
    Proportional to units over the largest flow in the same map."""
    if units <= 0:
        return 0.0
    return 3.0 + 25.0 * min(1.0, units / max(scale, 1.0))


def _node_radius(units, scale, base=22.0, extra=18.0):
    """Node radius, growing with the square root of its share of the
    largest flow (so area, not width, tracks the amount)."""
    if units <= 0:
        return base - 4.0
    return base + extra * math.sqrt(min(1.0, units / max(scale, 1.0)))


def _cubic(p0, c1, c2, p3, t):
    u = 1.0 - t
    x = u**3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t**3 * p3[0]
    y = u**3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t**3 * p3[1]
    dx = 3 * u * u * (c1[0] - p0[0]) + 6 * u * t * (c2[0] - c1[0]) + 3 * t * t * (p3[0] - c2[0])
    dy = 3 * u * u * (c1[1] - p0[1]) + 6 * u * t * (c2[1] - c1[1]) + 3 * t * t * (p3[1] - c2[1])
    return (x, y), (dx, dy)


def _edge_point(centre, radius, toward):
    """The point on a node's circle facing `toward`."""
    dx, dy = toward[0] - centre[0], toward[1] - centre[1]
    length = math.hypot(dx, dy) or 1.0
    return (centre[0] + dx / length * radius, centre[1] + dy / length * radius)


def _straight(a, ra, b, rb):
    """Endpoints of a straight flow between two nodes' circle edges."""
    p0 = _edge_point(a, ra, b)
    p3 = _edge_point(b, rb, a)
    c1 = (p0[0] + (p3[0] - p0[0]) / 3.0, p0[1] + (p3[1] - p0[1]) / 3.0)
    c2 = (p0[0] + 2.0 * (p3[0] - p0[0]) / 3.0, p0[1] + 2.0 * (p3[1] - p0[1]) / 3.0)
    return p0, c1, c2, p3


def _svg_flow(kind, units, scale, geometry, tip):
    """One flow: a thickness-scaled band, an animated direction overlay, an
    arrowhead (so direction survives reduced motion), and a focusable,
    labelled hover target carrying the real numbers."""
    p0, c1, c2, p3 = geometry
    d = f"M{p0[0]:.1f},{p0[1]:.1f} C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p3[0]:.1f},{p3[1]:.1f}"
    width = _flow_width(units, scale)
    idle = width <= 0
    classes = f"rich-hit rich-flow rf--{kind}" + (" rf--idle" if idle else "")
    parts = [
        f'<g class="{classes}" tabindex="0" role="img" aria-label="{_esc(tip)}" data-tip="{_esc(tip)}">',
        f'<path class="rf-hit" d="{d}" />',
        f'<path class="rf-base" d="{d}" stroke-width="{max(width, 2.0):.1f}" />',
    ]
    if not idle:
        parts.append(f'<path class="rf-dash" d="{d}" />')
        (mx, my), (tx, ty) = _cubic(p0, c1, c2, p3, 0.55)
        length = math.hypot(tx, ty) or 1.0
        ux, uy = tx / length, ty / length
        size = 7.0 + width * 0.45
        tip_pt = (mx + ux * size, my + uy * size)
        base_l = (mx - ux * size * 0.6 - uy * size * 0.75, my - uy * size * 0.6 + ux * size * 0.75)
        base_r = (mx - ux * size * 0.6 + uy * size * 0.75, my - uy * size * 0.6 - ux * size * 0.75)
        parts.append(
            f'<polygon class="rf-arrow" points="{tip_pt[0]:.1f},{tip_pt[1]:.1f} '
            f'{base_l[0]:.1f},{base_l[1]:.1f} {base_r[0]:.1f},{base_r[1]:.1f}" />'
        )
    parts.append("</g>")
    return "".join(parts)


def _svg_node(kind, centre, radius, icon, label, value, tip, label_at="below"):
    x, y = centre
    if label_at == "above":
        lx, ly, anchor = x, y - radius - 24, "middle"
    elif label_at == "right":
        lx, ly, anchor = x + radius + 10, y - 2, "start"
    elif label_at == "corner":
        lx, ly, anchor = x + radius * 0.72 + 8, y + radius * 0.9 + 10, "start"
    else:
        lx, ly, anchor = x, y + radius + 16, "middle"
    return (
        f'<g class="rich-hit rich-node rn--{kind}" tabindex="0" role="img" '
        f'aria-label="{_esc(tip)}" data-tip="{_esc(tip)}">'
        f'<circle class="rn-shape" cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" />'
        f'<text class="rn-icon" x="{x:.1f}" y="{y + 7:.1f}" text-anchor="middle">{icon}</text>'
        f'<text class="rn-label" x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}">{_esc(label)}</text>'
        f'<text class="rn-value" x="{lx:.1f}" y="{ly + 16:.1f}" text-anchor="{anchor}">{_esc(value)}</text>'
        f"</g>"
    )


def _legend_html(items, note):
    entries = "".join(
        f'<li><span class="rich-swatch rich-swatch--{kind}" aria-hidden="true"></span>{_esc(text)}</li>'
        for kind, text in items
    )
    return f'<ul class="rich-legend">{entries}</ul><p class="rich-legend-note">{_esc(note)}</p>'


def trade_partner_flows():
    """Real per-partner import flows: (key, label, icon, owned, units/cycle,
    funds per unit). Units include the challenge-mode multiplier so they sum
    to exactly chain.imported_supply()."""
    rows = []
    for key, label, icon, owned, per_unit, cost in (
        ("link", "Trade Link", "\U0001F310", chain.trade_link_investment, IMPORT_SUPPLY_PER_UNIT, TRADE_LINK_COST),
        (
            "regional", "Regional Partner", "\U0001F69A", chain.regional_trade_investment,
            REGIONAL_IMPORT_SUPPLY_PER_UNIT, REGIONAL_TRADE_COST,
        ),
        (
            "overseas", "Overseas Consortium", "\U0001F6A2", chain.overseas_trade_investment,
            OVERSEAS_IMPORT_SUPPLY_PER_UNIT, OVERSEAS_TRADE_COST,
        ),
    ):
        rows.append((key, label, icon, owned, chain.partner_supply("trade" if key == "link" else key), cost / per_unit))
    return rows


def internal_measure_flows():
    """Real per-measure recovery flows (key, label, icon, owned, units/cycle),
    summing to exactly chain.internal_circular_supply()."""
    return [
        (key, spec["label"], spec["icon"], chain.circularity_investment[key], chain.measure_supply(key))
        for key, spec in CIRCULARITY_INVESTMENTS.items()
    ]


def _multiplier_note():
    return " (counted at 65% in the Circular design challenge)" if chain.challenge_mode else ""


def trade_network_visual_html():
    """H25b: the rich trade-network map. A hub-and-spoke SVG: three partners
    feeding the chain from the left, the internal recovery loop and new
    extraction above/below, and surplus export on the right. Node size and
    flow thickness scale with the real units per cycle."""
    partners = trade_partner_flows()
    internal = chain.internal_circular_supply()
    imported = chain.imported_supply()
    extraction = chain.new_extraction_needed()
    surplus = chain.exportable_surplus()
    need = chain.material_need()
    scale = max([need, internal, imported, extraction, surplus] + [p[4] for p in partners] + [1.0])
    mnote = _multiplier_note()

    hub = (430.0, 200.0)
    hub_r = 52.0
    parts = []

    # Flows first, so nodes draw on top of their ends.
    ys = {"link": 60.0, "regional": 200.0, "overseas": 340.0}
    nodes = []
    for key, label, icon, owned, units, funds_per_unit in partners:
        centre = (110.0, ys[key])
        radius = _node_radius(units, scale)
        tip = (
            f"{label}: {owned} owned, importing {_fmt(units)} units per cycle{mnote}. "
            f"Costs {funds_per_unit:.2f} funds per unit of supply."
        )
        parts.append(_svg_flow("trade", units, scale, _straight(centre, radius, hub, hub_r), tip))
        nodes.append(_svg_node("trade", centre, radius, icon, label, f"+{_fmt(units)}/cycle", tip))

    int_centre = (430.0, 48.0)
    int_r = _node_radius(internal, scale, base=24.0)
    int_tip = (
        f"Internal loop: repair, reuse and recycling return {_fmt(internal)} units per cycle to manufacturing"
        f"{mnote}."
    )
    parts.append(_svg_flow("internal", internal, scale, _straight(int_centre, int_r, hub, hub_r), int_tip))
    nodes.append(_svg_node("internal", int_centre, int_r, "♻️", "Internal loop",
                           f"+{_fmt(internal)}/cycle", int_tip, label_at="right"))

    ext_centre = (430.0, 352.0)
    ext_r = _node_radius(extraction, scale, base=24.0)
    ext_tip = (
        f"New extraction: {_fmt(extraction)} units per cycle of freshly mined material, the gap the loop "
        f"and trade supply do not cover."
    )
    parts.append(_svg_flow("extract", extraction, scale, _straight(ext_centre, ext_r, hub, hub_r), ext_tip))
    nodes.append(_svg_node("extract", ext_centre, ext_r, "⛏️", "New extraction",
                           f"{_fmt(extraction)}/cycle", ext_tip, label_at="right"))

    exp_centre = (750.0, 200.0)
    exp_r = _node_radius(surplus, scale)
    exp_tip = (
        f"Surplus export: {_fmt(surplus)} units per cycle of supply beyond this cycle's need are sold outward "
        f"at {EXPORT_PRICE_PER_UNIT:.0f} funds per unit."
    )
    parts.append(_svg_flow("export", surplus, scale, _straight(hub, hub_r, exp_centre, exp_r), exp_tip))
    nodes.append(_svg_node("export", exp_centre, exp_r, "\U0001F4B0", "Surplus export",
                           f"{_fmt(surplus)}/cycle", exp_tip))

    hub_tip = (
        f"Your chain: needs {_fmt(need)} units per cycle. Supply this cycle: {_fmt(internal)} internal "
        f"+ {_fmt(imported)} imported; {_fmt(extraction)} newly extracted; {_fmt(surplus)} surplus exported."
    )
    nodes.append(_svg_node("hub", hub, hub_r, "\U0001F3ED", "Your chain", f"needs {_fmt(need)}/cycle",
                           hub_tip, label_at="corner"))

    summary = (
        f"Trade network map. Your chain needs {_fmt(need)} units per cycle: {_fmt(internal)} from the internal "
        f"loop, {_fmt(imported)} imported from trade partners, {_fmt(extraction)} newly extracted, "
        f"{_fmt(surplus)} surplus exported. Focus any node or flow for details."
    )
    svg = (
        f'<svg class="rich-svg" viewBox="0 0 860 430" role="group" aria-label="{_esc(summary)}" '
        f'xmlns="http://www.w3.org/2000/svg">' + "".join(parts) + "".join(nodes) + "</svg>"
    )
    legend = _legend_html(
        [
            ("trade", "Imported from a trade partner"),
            ("internal", "Internal loop (repair, reuse, recycling)"),
            ("extract", "New extraction"),
            ("export", "Surplus sold outward"),
        ],
        "Node size and line thickness scale with units per cycle. Animated dashes show direction; "
        "with reduced motion on, the arrowheads show it instead.",
    )
    caption = f'<p class="rich-caption">{_esc(summary.replace("Trade network map. ", ""))}</p>'
    return caption + svg + legend


def supply_map_visual_html():
    """H29b: the rich circular supply chain map. Four stages around a
    diamond (Extract, Manufacture, Use, Discard), the goods flow between
    them, three proportional return lanes from Discard back to Manufacture
    (repair, reuse, recycling), trade imports and surplus export at the top."""
    need = chain.material_need()
    extraction = chain.new_extraction_needed()
    internal_rows = internal_measure_flows()
    internal = chain.internal_circular_supply()
    imported = chain.imported_supply()
    surplus = chain.exportable_surplus()
    unrecovered = max(0.0, need - internal)
    scale = max([need, extraction, imported, surplus] + [row[4] for row in internal_rows] + [1.0])
    mnote = _multiplier_note()

    r = 38.0
    manuf = (430.0, 95.0)
    use = (640.0, 245.0)
    discard = (430.0, 395.0)
    extract = (220.0, 245.0)
    trade_node = (100.0, 95.0)
    export_node = (760.0, 95.0)
    parts, nodes = [], []

    ext_tip = f"Extract to Manufacture: {_fmt(extraction)} units per cycle of newly extracted material."
    parts.append(_svg_flow("extract", extraction, scale, _straight(extract, r, manuf, r), ext_tip))
    goods_tip = f"Goods: {_fmt(need)} units per cycle of material made into goods and put to use."
    parts.append(_svg_flow("goods", need, scale, _straight(manuf, r, use, r), goods_tip))
    disc_tip = f"Use to Discard: {_fmt(need)} units per cycle of goods reach the end of their life."
    parts.append(_svg_flow("goods", need, scale, _straight(use, r, discard, r), disc_tip))

    # Three return lanes Discard -> Manufacture, bowed apart so thick lines
    # never overlap; each ends on the node's edge at its own offset.
    for row, bow in zip(internal_rows, (-90.0, 0.0, 90.0)):
        key, label, icon, owned, units = row
        off = bow / 4.0
        dy = math.sqrt(max(r * r - off * off, 1.0))
        p0 = (discard[0] + off, discard[1] - dy)
        p3 = (manuf[0] + off, manuf[1] + dy)
        geometry = (p0, (430.0 + bow, 300.0), (430.0 + bow, 190.0), p3)
        tip = (
            f"{label}: {owned} owned, returning {_fmt(units)} units per cycle from Discard to "
            f"Manufacture{mnote}."
        )
        parts.append(_svg_flow(key, units, scale, geometry, tip))
        # Lane label sits beside the lane's midpoint.
        lx = 430.0 + bow * 0.75
        parts.append(
            f'<text class="rich-lane-label" x="{lx:.1f}" y="{228:.1f}" text-anchor="middle" aria-hidden="true">'
            f'{icon} {_fmt(units)}</text>'
        )

    trade_units = imported
    trade_tip = (
        f"Trade partners: {_fmt(imported)} units per cycle imported into Manufacture from all partners"
        f"{mnote}."
    )
    parts.append(_svg_flow("trade", trade_units, scale, _straight(trade_node, 34.0, manuf, r), trade_tip))
    exp_tip = (
        f"Surplus export: {_fmt(surplus)} units per cycle leave Manufacture, supply beyond this cycle's need, "
        f"sold at {EXPORT_PRICE_PER_UNIT:.0f} funds per unit."
    )
    parts.append(_svg_flow("export", surplus, scale, _straight(manuf, r, export_node, 34.0), exp_tip))

    stages = (
        ("stage", extract, "⛏️", "Extract", f"{_fmt(extraction)} new/cycle",
         f"Extract: {_fmt(extraction)} units per cycle of newly mined material, adding to lasting damage."),
        ("stage", manuf, "\U0001F3ED", "Manufacture", f"needs {_fmt(need)}/cycle",
         f"Manufacture: needs {_fmt(need)} units per cycle; receives {_fmt(extraction)} new, "
         f"{_fmt(internal)} internal, {_fmt(imported)} imported."),
        ("stage", use, "\U0001F6CD️", "Use", f"{_fmt(need)}/cycle",
         f"Use: {_fmt(need)} units per cycle of goods in use."),
        ("stage", discard, "\U0001F5D1️", "Discard", f"{_fmt(unrecovered)} not recovered",
         f"Discard: {_fmt(need)} units per cycle arrive; {_fmt(internal)} are recovered by repair, reuse and "
         f"recycling, {_fmt(unrecovered)} are not recovered internally this cycle."),
    )
    for kind, centre, icon, label, value, tip in stages:
        at = "above" if label == "Manufacture" else "below"
        nodes.append(_svg_node(kind, centre, r, icon, label, value, tip, label_at=at))
    nodes.append(_svg_node("trade", trade_node, 34.0, "\U0001F310", "Trade partners",
                           f"+{_fmt(imported)}/cycle", trade_tip))
    nodes.append(_svg_node("export", export_node, 34.0, "\U0001F4B0", "Surplus export",
                           f"{_fmt(surplus)}/cycle", exp_tip))

    share = chain.circular_fraction_this_cycle()
    summary = (
        f"Circular supply chain map. Production needs {_fmt(need)} units per cycle. Recovered internally: "
        + ", ".join(f"{row[1]} {_fmt(row[4])}" for row in internal_rows)
        + f". Imported {_fmt(imported)}, newly extracted {_fmt(extraction)}, surplus exported {_fmt(surplus)}. "
        f"Circular share this cycle {share * 100:.0f}%. Focus any stage or flow for details."
    )
    svg = (
        f'<svg class="rich-svg" viewBox="0 0 860 470" role="group" aria-label="{_esc(summary)}" '
        f'xmlns="http://www.w3.org/2000/svg">' + "".join(parts) + "".join(nodes) + "</svg>"
    )
    legend = _legend_html(
        [
            ("extract", "New extraction"),
            ("goods", "Goods through Manufacture, Use and Discard"),
            ("repair", "Repair returning to Manufacture"),
            ("reuse", "Reuse returning to Manufacture"),
            ("recycle", "Recycling returning to Manufacture"),
            ("trade", "Trade imports"),
            ("export", "Surplus export"),
        ],
        "Line thickness scales with units per cycle. Animated dashes show direction; with reduced motion on, "
        "the arrowheads show it instead.",
    )
    caption = f'<p class="rich-caption">{_esc(summary.replace("Circular supply chain map. ", ""))}</p>'
    return caption + svg + legend


# Opt-in toggles. `pref` is the localStorage key (via window.loopVisual in
# rich-maps.js); the choice is a browser preference, never part of a save.
VISUAL_VIEWS = {
    "trade": {
        "button": "trade-visual-toggle-button",
        "panel": "trade-visual",
        "body": "trade-visual-body",
        "note": "trade-visual-unsupported",
        "host": "trade-network",
        "host_class": "rich-trade-on",
        "pref": "loop-visual-trade",
        "builder": "trade_network_visual_html",
        "label": "network",
    },
    "chain": {
        "button": "supply-visual-toggle-button",
        "panel": "supply-visual",
        "body": "supply-visual-body",
        "note": "supply-visual-unsupported",
        "host": "network-map-panel",
        "host_class": "rich-chain-on",
        "pref": "loop-visual-chain",
        "builder": "supply_map_visual_html",
        "label": "supply chain",
    },
}
visual_view = {"trade": False, "chain": False}


def _visual_hook():
    """The optional rich-maps.js bridge (window.loopVisual): preference
    storage and an SVG-support check. Lazy import and getattr default so
    it is a safe no-op under pytest and on any page without the script."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return None
    return getattr(window, "loopVisual", None)


def _visual_supported():
    hook = _visual_hook()
    if hook is None:
        return True
    try:
        return bool(hook.supported())
    except Exception:  # noqa: BLE001 -- a broken bridge must never break the game
        return False


def _load_visual_prefs():
    hook = _visual_hook()
    if hook is None or not _visual_supported():
        return
    for kind, spec in VISUAL_VIEWS.items():
        try:
            visual_view[kind] = hook.get(spec["pref"]) == "1"
        except Exception:  # noqa: BLE001
            visual_view[kind] = False


def _save_visual_pref(kind):
    hook = _visual_hook()
    if hook is None:
        return
    try:
        hook.set(VISUAL_VIEWS[kind]["pref"], "1" if visual_view[kind] else "0")
    except Exception:  # noqa: BLE001
        pass


def render_visual_views():
    """Syncs both opt-in views with the live state. Only builds the SVG for
    a view that is switched on; an off view is emptied so nothing stale
    lingers."""
    supported = _visual_supported()
    for kind, spec in VISUAL_VIEWS.items():
        asked = visual_view[kind]
        on = asked and supported
        button = document.getElementById(spec["button"])
        panel = document.getElementById(spec["panel"])
        body = document.getElementById(spec["body"])
        host = document.getElementById(spec["host"])
        button.innerText = (
            f"\U0001F3A8 Hide visual {spec['label']} view" if asked else f"\U0001F3A8 Show visual {spec['label']} view"
        )
        button.setAttribute("aria-pressed", "true" if asked else "false")
        # The panel shows whenever the player asked for the visual view, so
        # its notes (unsupported here / needs a wider screen) stay visible
        # even where the drawing itself cannot appear.
        panel.hidden = not asked
        document.getElementById(spec["note"]).hidden = supported
        if on:
            host.classList.add(spec["host_class"])
            body.innerHTML = globals()[spec["builder"]]()
        else:
            host.classList.remove(spec["host_class"])
            body.innerHTML = ""


def _make_visual_toggle_handler(kind):
    def handler(event=None):
        visual_view[kind] = not visual_view[kind]
        _save_visual_pref(kind)
        render_visual_views()

    return handler


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
        f"{len(goods_categories_tried)} goods categor{'y' if len(goods_categories_tried) == 1 else 'ies'} tried, "
        f"{len(career_plates)} name plate(s) and your records."
    )


# ===========================================================================
# Round-3 helpers (GH-12/14/15/24/25, H-4/9/15/22/23). Pure functions of state
# (plus the career records), so they are directly testable.
# ===========================================================================
def _supply_options():
    """(label, cost, units supplied per purchase) for every single purchase that adds
    supply right now, with every multiplier applied."""
    mult = chain.supply_multiplier()
    options = [
        (spec["label"], spec["cost"], spec["supply_per_unit"] * chain.measure_multiplier(m) * mult)
        for m, spec in CIRCULARITY_INVESTMENTS.items()
    ]
    options.append(("Trade Link", TRADE_LINK_COST, IMPORT_SUPPLY_PER_UNIT * mult))
    options.append(("Regional Partner", REGIONAL_TRADE_COST, REGIONAL_IMPORT_SUPPLY_PER_UNIT * mult))
    options.append(("Overseas Consortium", OVERSEAS_TRADE_COST, OVERSEAS_IMPORT_SUPPLY_PER_UNIT * mult))
    return options


def near_miss_info():
    """GH-25: None, or (units_short, goal_text, fix_text). 'Short' is how far the
    current mix falls below closing the loop or reaching the next 25% step, only when
    that is within NEAR_MISS_UNITS."""
    gap = chain.new_extraction_needed()
    if gap <= 0:
        return None
    fraction = chain.circular_fraction_this_cycle()
    next_step = (math.floor(fraction * BURST_MILESTONES + 1e-9) + 1) / BURST_MILESTONES
    short = gap - (1.0 - next_step) * PRODUCTION_TARGET
    limit = NEAR_MISS_UNITS if next_step >= 1.0 else NEAR_MISS_STEP_UNITS
    if short <= 1e-9 or short > limit:
        return None
    goal = "closing the loop" if next_step >= 1.0 else f"the {next_step * 100:.0f}% mark"
    options = _supply_options()
    single = [o for o in options if o[2] >= short - 1e-9]
    if single:
        label, cost, supply = min(single, key=lambda o: (o[1], -o[2]))
        fix = f"{label} ({cost} funds, +{supply:.0f} units) covers it"
    else:
        label, cost, supply = min(options, key=lambda o: math.ceil(short / o[2]) * o[1])
        count = math.ceil(short / supply)
        fix = f"{count} x {label} ({count * cost} funds) would cover it"
    return short, goal, fix


def near_miss_message():
    info = near_miss_info()
    if info is None:
        return ""
    short, goal, fix = info
    shown = math.ceil(short - 1e-9)
    text = f"So close: {shown} unit{'' if shown == 1 else 's'} short of {goal}! Cheapest fix: {fix}."
    cost_note = None
    for label, cost, supply in _supply_options():
        if fix.startswith(label) or f" x {label}" in fix:
            cost_note = cost
            break
    if cost_note is not None and chain.funds < cost_note:
        text += f" You have {chain.funds:.0f} funds, so you need {cost_note - chain.funds:.0f} more."
    return text


def cycle_summary_text():
    """H-4: one plain sentence about the cycle that just finished, for the screen-reader
    live region ('' before any cycle has run)."""
    log = chain.circular_fraction_log
    if not log:
        return ""
    done = chain.cycle_number - 1
    now = PRODUCTION_TARGET * (1.0 - log[-1])
    text = f"Cycle {done} complete: {log[-1] * 100:.0f}% circular"
    if len(log) >= 2:
        before = PRODUCTION_TARGET * (1.0 - log[-2])
        delta = round(before - now)
        if delta > 0:
            text += f", extraction down {delta} unit{'' if delta == 1 else 's'}"
        elif delta < 0:
            text += f", extraction up {-delta} unit{'' if delta == -1 else 's'}"
        else:
            text += ", extraction unchanged"
    else:
        text += f", {now:.0f} units extracted"
    text += "."
    if now <= 0:
        text += f" Loop closed. Combo times {chain.combo_level()}."
    if chain.last_insurance_saved:
        text += " Streak insurance held your streak."
    return text


def cost_equation_text():
    """H-15: the extraction price worked out, so the number is not a mystery."""
    mult = chain.extraction_cost_multiplier()
    spike = chain.shock_price_multiplier()
    if spike != 1.0:
        return (
            f"Each extracted unit costs: base {EXTRACTION_COST_PER_UNIT:.1f} x damage multiplier {mult:.2f} "
            f"(cap {MAX_COST_MULTIPLIER:.1f}) x price spike {spike:.1f} = "
            f"{EXTRACTION_COST_PER_UNIT * mult * spike:.2f} funds."
        )
    return (
        f"Each extracted unit costs: base {EXTRACTION_COST_PER_UNIT:.1f} x damage multiplier {mult:.2f} "
        f"(cap {MAX_COST_MULTIPLIER:.1f}) = {EXTRACTION_COST_PER_UNIT * mult:.2f} funds."
    )


def combo_text():
    """GH-12: the Perfect Cycle combo line."""
    level = chain.combo_level()
    gain = chain.next_combo_gain()
    line = f"Perfect combo: x{level}"
    if level == 0:
        line += " (close the loop for a full cycle to start one)"
    else:
        line += f", {chain.closed_loop_streak} perfect cycle{'' if chain.closed_loop_streak == 1 else 's'} in a row"
    if gain > 0:
        line += f". Next perfect cycle banks +{gain:.0f}"
    else:
        line += ". Banking starts with the second perfect cycle in a row"
    line += f". Banked so far: {chain.perfect_bonus:.0f}."
    if level >= COMBO_CAP:
        line += " (combo maxed)"
    return line


def insurance_text():
    if chain.insurance_armed:
        return "Streak insurance is armed: your next cycle that needs extraction will not reset the streak."
    if chain.insurance_used:
        return "Streak insurance already used on this chain."
    if chain.closed_loop_streak < 1:
        return "Streak insurance (once per chain) protects a streak: close the loop for a cycle first."
    return (
        f"Pay {INSURANCE_COST} funds, once per chain, to freeze your {chain.closed_loop_streak}-cycle "
        "streak through one cycle that needs extraction."
    )


def rival_lines():
    """GH-5: the comparison lines under the switch ('' list when the rival is off)."""
    if not chain.rival_on:
        return []
    done = chain.cycle_number - 1
    mine = chain.funds
    theirs = rival_funds_after(done)
    gap = mine - theirs
    if done == 0:
        lines = [f"Both of you start with {mine:.0f} funds. Advance a cycle and the race begins."]
    elif abs(gap) < 0.5:
        lines = [f"After {done} cycle{'' if done == 1 else 's'}: level on funds ({mine:.0f} each)."]
    else:
        word = "ahead of" if gap > 0 else "behind"
        lines = [
            f"After {done} cycle{'' if done == 1 else 's'}: you have {mine:.0f} funds, {RIVAL_NAME} has "
            f"{theirs:.0f}. You are {abs(gap):.0f} {word} it."
        ]
    extracted_rival = rival_extracted_after(done)
    saved = extracted_rival - chain.total_extracted
    if done > 0:
        if saved >= 0:
            lines.append(
                f"{RIVAL_NAME} has dug up {extracted_rival:.0f} units; you have dug up {chain.total_extracted:.0f}, "
                f"{saved:.0f} fewer."
            )
        else:
            lines.append(
                f"{RIVAL_NAME} has dug up {extracted_rival:.0f} units; you have dug up {chain.total_extracted:.0f}, "
                f"{-saved:.0f} more (a demand surge can cause that)."
            )
        profit = rival_profit_in_cycle(done)
        damage = min(1.0, extracted_rival / ENVIRONMENTAL_DAMAGE_SCALE)
        if profit < 0.5:
            lines.append(
                f"Its damage is at {damage * 100:.0f}%, so its raw material now costs x{MAX_COST_MULTIPLIER:.1f} "
                "and it earns nothing more from a cycle."
            )
        else:
            lines.append(
                f"Its damage is at {damage * 100:.0f}%, so it now makes only {profit:.0f} funds a cycle "
                "and every extra unit it digs up costs more."
            )
    if chain.rival_crossover_cycle is not None:
        lines.append(f"You pulled ahead of {RIVAL_NAME} on cycle {chain.rival_crossover_cycle}.")
    elif done > 0 and gap < 0:
        lines.append("Circularity costs funds up front, so a rival that only digs and sells looks ahead early on. Its costs only climb.")
    return lines


def rival_bar_widths():
    """GH-5: (you %, rival %) bar widths, each against the larger of the two."""
    done = chain.cycle_number - 1
    mine, theirs = max(0.0, chain.funds), max(0.0, rival_funds_after(done))
    top = max(mine, theirs, 1.0)
    return round(mine / top * 100), round(theirs / top * 100)


def rival_status_text():
    if chain.rival_on:
        return f"{RIVAL_NAME} is racing you. It is a fixed script, the same every time, and changes nothing for you."
    return (
        f"{RIVAL_NAME} is a straight-line competitor: it makes the same goods every cycle but digs up all of "
        "the material new and never invests in repair, reuse or recycling. Switch it on to race it. It is "
        "only a comparison: nothing you do depends on it."
    )


def on_toggle_rival(event=None):
    _run_action(lambda: setattr(chain, "rival_on", not chain.rival_on))


def shock_banner_text():
    """GH-3: the one-line notice shown in the status block ('' when there is nothing to say)."""
    if not chain.market_shocks:
        return ""
    active = chain.active_shock()
    coming = chain.next_shock()
    parts = []
    if active is not None:
        label = f"Market shock now: {shock_name(active)}, {shock_effect(active)}"
        if active["length"] > 1:
            label += f" (day {active['step']} of {active['length']})"
        parts.append(label + ".")
    if coming is not None:
        parts.append(f"Heads-up for next cycle: {shock_name(coming)}, {shock_effect(coming)}.")
    return " ".join(parts)


def shock_status_text():
    """GH-3: the always-visible explanation under the Market shocks switch."""
    if not chain.market_shocks:
        return (
            "Off. Turn it on for a fixed, announced schedule of price spikes, port strikes and demand surges. "
            "There is nothing random in it, every shock is shown one cycle early, and a chain that recovers "
            "its own material barely notices them."
        )
    text = (
        f"On. Every {SHOCK_PERIOD} cycles: a price spike on cycle {SHOCK_PRICE_AT}, a {SHOCK_STRIKE_CYCLES}-cycle "
        f"port strike from cycle {SHOCK_STRIKE_AT} (a different trade partner each round) and a demand surge on "
        f"cycle {SHOCK_DEMAND_AT}. Nothing is ever lost for good."
    )
    if chain.shocks_shrugged:
        text += f" Closed cycles that landed on a shock so far: {chain.shocks_shrugged}."
    return text


def on_toggle_market_shocks(event=None):
    _run_action(lambda: setattr(chain, "market_shocks", not chain.market_shocks))


def rewind_token_text():
    return "Rewind: spent" if chain.rewind_used else "Rewind: 1 left"


def rewind_text():
    """GH-18: what the rewind token can do right now."""
    reason = chain.rewind_block_reason()
    if reason == "used":
        return "The rewind token on this chain is spent. A new chain gets a new one."
    if reason == "no_point":
        return "One rewind per chain. The undo point is set each time you advance a cycle, so advance one to use it."
    if reason == "donated":
        return "That cycle gave surplus to the regional pool, which cannot be taken back, so it cannot be rewound."
    return (
        f"One rewind per chain: go back to the start of cycle {chain.rewind_snapshot['cycle_number']}, "
        "undoing the last Advance Cycle and anything you bought since."
    )


def on_rewind(event=None):
    """GH-18 / FY-39: spend the chain's one rewind token (asks first, since it is used up)."""
    if not chain.can_rewind():
        render()
        return
    target = chain.rewind_snapshot["cycle_number"]

    def _confirmed():
        _run_action(chain.rewind)
        _seed_achievement_toast_baseline()
        document.getElementById("cycle-live-summary").innerText = f"Rewound to the start of cycle {target}."

    _confirm_dialog_ask(
        action_id="loop-rewind",
        message=(
            f"Rewind to the start of cycle {target}? The last cycle and anything you bought since are undone, "
            "and this chain's rewind token is spent."
        ),
        confirm_label="Rewind",
        on_confirm=_confirmed,
    )


def summary_blocks(fractions, width=40):
    """H-23: a block-character row, one block per cycle (the last `width`)."""
    blocks = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"
    return "".join(blocks[max(0, min(7, round(f * 7)))] for f in fractions[-width:])


def summary_text():
    """H-23: plain text a player can paste anywhere."""
    spec = ALL_GOODS.get(chain.goods_category, GOODS_CATEGORIES[DEFAULT_GOODS_CATEGORY])
    name = spec.get("name") or spec["label"].capitalize()
    if chain.first_loop_closed_cycle is not None:
        head = f"Loop {name} - closed cycle {chain.first_loop_closed_cycle} - score {chain.score():.0f}"
    else:
        head = (
            f"Loop {name} - cycle {chain.cycle_number} - "
            f"{chain.circular_fraction_this_cycle() * 100:.0f}% circular - score {chain.score():.0f}"
        )
    row = summary_blocks(chain.circular_fraction_log)
    return head + ("\n" + row if row else "")


def plate_rows():
    """GH-15: (key, name, how, earned) in catalog order."""
    return [(key, spec["name"], spec["how"], key in career_plates) for key, spec in PLATES.items()]


def live_plate_text():
    shares = chain.supply_mix()
    key = plate_for_mix(shares)
    if key is None:
        return "Your supply mix right now would earn no plate: buy some circular supply first."
    top, share = max(shares.items(), key=lambda kv: kv[1])
    return (
        f"Your mix right now ({top} {share * 100:.0f}% of supply) would earn {PLATES[key]['name']} "
        "if you close the loop with it."
    )


def career_record_lines():
    """H-9: one line per goods category with any record."""
    lines = []
    for category in ALL_GOODS:
        record = career_best.get(category)
        if not record:
            continue
        name = ALL_GOODS[category].get("name") or ALL_GOODS[category]["label"].capitalize()
        parts = []
        if "fastest_close" in record:
            parts.append(f"first close on cycle {record['fastest_close']}")
        if "lowest_extraction" in record:
            parts.append(f"{record['lowest_extraction']:.0f} units extracted by then")
        if "best_score" in record:
            parts.append(f"best score {record['best_score']:.0f}")
        if record.get("best_streak"):
            parts.append(f"longest perfect run {record['best_streak']}")
        lines.append(f"{name}: " + ", ".join(parts))
    return lines


def secret_text():
    done, total = secret_progress()
    if secret_unlocked():
        return f"Secret category unlocked: {SECRET_GOODS['icon']} {SECRET_GOODS['name']}, shown with the goods choices at the start of a chain."
    missing = [GOODS_CATEGORIES[c]["label"] for c in GOODS_CATEGORIES if c not in career_closed_categories]
    return (
        f"\U0001F512 A fourth goods category is hidden. Run one fully closed cycle on each of the "
        f"{total} ordinary categories to reveal it ({done} of {total} done; still to close: {', '.join(missing)})."
    )


def accessible_chain_lines():
    """H-4: the ring, the trade partners and the meters as plain list lines, in reading order."""
    lines = [
        f"Cycle {chain.cycle_number}. Funds {chain.funds:.0f}.",
        f"New extraction this cycle: {chain.new_extraction_needed():.0f} of {chain.material_need():.0f} units needed.",
    ]
    for measure, spec in CIRCULARITY_INVESTMENTS.items():
        lines.append(
            f"{spec['label']}: {chain.circularity_investment[measure]} bought, supplying "
            f"{chain.measure_supply(measure):.0f} units per cycle."
        )
    for key, label, _icon, owned, units, _cost in trade_partner_flows():
        lines.append(f"{label}: {owned} bought, importing {units:.0f} units per cycle.")
    lines.append(f"Surplus sold or donated: {chain.exportable_surplus():.0f} units per cycle.")
    lines.append(
        f"Environmental damage {chain.damage_fraction() * 100:.0f}%, extraction cost x{chain.extraction_cost_multiplier():.2f}."
    )
    lines.append(
        f"Circular this cycle {chain.circular_fraction_this_cycle() * 100:.0f}%, lifetime "
        f"{chain.lifetime_circular_fraction() * 100:.0f}%. Score {chain.score():.0f}."
    )
    return lines


def _copy_to_clipboard(text):
    """Best effort: True when the browser accepted it. Never raises."""
    try:
        from js import navigator  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        navigator.clipboard.writeText(text)
        return True
    except Exception:  # noqa: BLE001 -- no clipboard (tests, insecure page): the text is shown instead
        return False


def share_result():
    """Z-20: the headline numbers for the shared "Copy result" button, as a JSON string the page
    reads (it calls this by name through window.pyodide). Score, cycles run, lifetime circular
    share and, once it has happened, the cycle the loop first closed."""
    stats = [
        {"n": max(0, chain.cycle_number - 1), "one": "cycle", "many": "cycles"},
        f"{chain.lifetime_circular_fraction() * 100:.0f}% circular",
    ]
    if chain.first_loop_closed_cycle is not None:
        stats.append(f"loop closed in cycle {chain.first_loop_closed_cycle}")
    return json.dumps({"game": "Loop", "score": round(chain.score()), "unit": "points", "stats": stats})


def on_copy_summary(event=None):
    text = summary_text()
    status = document.getElementById("copy-summary-status")
    status.innerText = "Copied to the clipboard." if _copy_to_clipboard(text) else "Select the text above to copy it."


def on_buy_insurance(event=None):
    _run_action(chain.buy_insurance)


def render_career():
    """GH-14/15, H-9/23: the Career panel (plates, secret category, records, summary)."""
    plates = document.getElementById("plates-list")
    plates.innerHTML = ""
    for _key, name, how, earned in plate_rows():
        row = document.createElement("li")
        row.className = "plate-row plate-row--earned" if earned else "plate-row"
        mark = "\u2713" if earned else "\u25cb"
        row.innerText = f"{mark} {name}: {how}"
        plates.appendChild(row)
    document.getElementById("plates-count").innerText = f"{len(career_plates)} of {len(PLATES)} plates earned"
    document.getElementById("plate-live").innerText = live_plate_text()
    document.getElementById("secret-progress").innerText = secret_text()
    records = document.getElementById("career-records")
    records.innerHTML = ""
    lines = career_record_lines()
    if not lines:
        lines = ["No records yet: advance a cycle and they start filling in."]
    for line in lines:
        row = document.createElement("li")
        row.innerText = line
        records.appendChild(row)
    document.getElementById("summary-text").innerText = summary_text()


def render():
    render_info_page()
    update_achievements_display()
    update_changelog_display()

    for count in BUY_MULTIPLES:
        chip = document.getElementById(f"buy-x{count}-button")
        chip.setAttribute("aria-pressed", "true" if buy_multiple == count else "false")
        if buy_multiple == count:
            chip.classList.add("selected")
        else:
            chip.classList.remove("selected")

    picker = document.getElementById("goods-category-picker")
    picker.hidden = chain.total_produced > 0
    for key in GOODS_CATEGORIES:
        button = document.getElementById(f"goods-category-{key}-button")
        if key == chain.goods_category:
            button.classList.add("selected")
        else:
            button.classList.remove("selected")

    # GH-14: the secret category, hidden until every ordinary category has had a closed cycle.
    secret_button = document.getElementById("goods-category-shipyard-button")
    secret_button.hidden = not secret_unlocked()
    if chain.goods_category == SECRET_GOODS_CATEGORY:
        secret_button.classList.add("selected")
    else:
        secret_button.classList.remove("selected")
    secret_hint = document.getElementById("secret-category-hint")
    secret_hint.innerText = secret_text()
    secret_hint.hidden = secret_unlocked()

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
    # H-15: the extraction price as a worked equation (visible text, also the tooltip).
    equation = cost_equation_text()
    equation_el = document.getElementById("cost-equation-display")
    equation_el.innerText = equation
    equation_el.title = equation
    # GH-25: a "so close" note with the cheapest single fix.
    near_text = near_miss_message()
    near_el = document.getElementById("near-miss-display")
    near_el.innerText = near_text
    near_el.hidden = near_text == ""
    # GH-12 / GH-24: the Perfect Cycle combo and the streak insurance.
    document.getElementById("combo-display").innerText = combo_text()
    insurance_button = document.getElementById("insurance-button")
    if chain.insurance_armed:
        insurance_button.innerText = "Streak insurance: armed"
    elif chain.insurance_used:
        insurance_button.innerText = "Streak insurance: used"
    else:
        insurance_button.innerText = f"Streak insurance ({INSURANCE_COST})"
    insurance_button.disabled = not chain.can_buy_insurance()
    document.getElementById("insurance-status").innerText = insurance_text()
    # GH-5 / FY-38: the Rival Corporation race.
    rival_button = document.getElementById("rival-button")
    rival_button.innerText = f"{RIVAL_NAME}: on" if chain.rival_on else f"{RIVAL_NAME}: off"
    rival_button.setAttribute("aria-pressed", "true" if chain.rival_on else "false")
    document.getElementById("rival-status").innerText = rival_status_text()
    document.getElementById("rival-lines").innerHTML = "".join(f"<li>{html.escape(line)}</li>" for line in rival_lines())
    document.getElementById("rival-race").hidden = not chain.rival_on
    you_pct, rival_pct = rival_bar_widths()
    document.getElementById("rival-bar-you").style.width = f"{you_pct}%"
    document.getElementById("rival-bar-rival").style.width = f"{rival_pct}%"
    # GH-3 / FY-37: the market-shock switch and notice.
    shock_button = document.getElementById("market-shocks-button")
    shock_button.innerText = "Market shocks: on" if chain.market_shocks else "Market shocks: off"
    shock_button.setAttribute("aria-pressed", "true" if chain.market_shocks else "false")
    document.getElementById("shock-status").innerText = shock_status_text()
    banner_text = shock_banner_text()
    banner = document.getElementById("shock-banner")
    banner.innerText = banner_text
    banner.hidden = banner_text == ""
    # GH-18 / FY-39: the one rewind token.
    document.getElementById("rewind-token-display").innerText = rewind_token_text()
    rewind_button = document.getElementById("rewind-button")
    rewind_button.innerText = "Rewind used" if chain.rewind_used else "Rewind last cycle"
    rewind_button.disabled = not chain.can_rewind()
    document.getElementById("rewind-status").innerText = rewind_text()
    # H-4: the same numbers as a plain list (screen readers, and anyone who prefers text).
    document.getElementById("a11y-chain-list").innerHTML = "".join(
        f"<li>{html.escape(line)}</li>" for line in accessible_chain_lines()
    )
    # H-22: a live tab title.
    document.title = f"Loop - C{chain.cycle_number} - {chain.circular_fraction_this_cycle() * 100:.0f}% circular"
    render_career()

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
    combo_part = f" + combo bonus ({chain.perfect_bonus:.0f})" if chain.perfect_bonus > 0 else ""
    document.getElementById("score-breakdown-display").innerText = (
        f"Score = funds ({chain.funds:.0f}) + circular bonus ({bonus_component:.0f}){combo_part} = {chain.score():.0f}"
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
        button.innerText = purchase_label(measure, spec["label"])
        button.disabled = chain.funds < spec["cost"]

        # H4 + H15: cost-per-unit-of-supply, and each measure's running
        # supply contribution per cycle, next to its owned count.
        cost_per_unit = spec["cost"] / spec["supply_per_unit"]
        contribution = chain.measure_supply(measure)
        focus_note = " · focus +25%" if chain.waste_focus == measure else ""
        if measure == "recycle" and chain.head_start > 0:
            focus_note += f" · yard scrap line +{chain.head_start:.0f}"
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
    trade_link_button.innerText = purchase_label("trade", "Trade Link")
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
    regional_trade_button.innerText = purchase_label("regional", "Regional Partner")
    regional_trade_button.disabled = chain.funds < REGIONAL_TRADE_COST
    regional_trade_button.title = (
        f"{REGIONAL_TRADE_COST} funds for {REGIONAL_IMPORT_SUPPLY_PER_UNIT:.0f} imported units/cycle "
        f"({REGIONAL_TRADE_COST / REGIONAL_IMPORT_SUPPLY_PER_UNIT:.2f} funds/unit) — a separate trade "
        f"partner from Trade Link, so both can be invested in at once."
    )

    document.getElementById("overseas-trade-count").innerText = str(chain.overseas_trade_investment)
    overseas_button = document.getElementById("overseas-trade-invest-button")
    overseas_button.innerText = purchase_label("overseas", "Overseas Consortium")
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
    render_visual_views()
    render_pool_donation()

    document.getElementById("trade-network-display").innerText = (
        f"Importing {chain.imported_supply():.0f} units/cycle from the trade network; "
        f"exporting {chain.exportable_surplus():.0f} units/cycle of surplus this cycle."
    )


def _report_pool_donation():
    """H11: hands this cycle's donated units to the shared community-pool
    client (batched and rate limited there). Silent without the script."""
    if chain.last_donation <= 0:
        return
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    pool = getattr(window, "NoyvjPool", None)
    if pool is not None:
        pool.add("loop", "recovered_units", float(chain.last_donation))


def pool_donation_text():
    if chain.donate_surplus:
        return (
            f"Donating surplus to the regional pool instead of selling it. You have given "
            f"{chain.lifetime_pool_donated:.0f} units so far."
        )
    return (
        "Surplus supply is sold outward for funds. Donate it instead and it joins the regional "
        "recycling pool that every player shares (you forgo the sale price)."
    )


def render_pool_donation():
    button = document.getElementById("pool-donate-button")
    button.innerText = "Surplus donation: on" if chain.donate_surplus else "Surplus donation: off"
    button.setAttribute("aria-pressed", "true" if chain.donate_surplus else "false")
    document.getElementById("pool-donate-status").innerText = pool_donation_text()


def on_toggle_pool_donation(event=None):
    chain.donate_surplus = not chain.donate_surplus
    render()


def on_advance_cycle(event=None):
    _run_action(chain.advance_cycle)
    _report_pool_donation()
    # H-4: announce the finished cycle in the polite live region.
    document.getElementById("cycle-live-summary").innerText = cycle_summary_text()


def _window():
    """The browser window, or None under pytest (the fake `js` module only fakes document and
    setTimeout). One lazy import in one place, like the other optional bridges below."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return None
    return window


def _setting_number(name, default=0):
    """A number read from a LoopSettings getter (settings.js), or `default` when the bridge is
    missing or returns something odd. Browser preferences only, never part of a save."""
    window = _window()
    getter = getattr(getattr(window, "LoopSettings", None), name, None) if window is not None else None
    if getter is None:
        return default
    try:
        value = float(getter())
    except (TypeError, ValueError):
        return default
    return value if value == value else default


# H-14: the x1 / x5 / x10 chips (a browser-session choice, not saved).
buy_multiple = 1


def _requested_count(event=None):
    """How many purchases one click asks for: the chip, or x5 for a shift-click on x1."""
    if buy_multiple == 1 and getattr(event, "shiftKey", False) is True:
        return 5
    return buy_multiple


def purchase_label(kind, label):
    """H-14: button text with a running total. x1 keeps the plain 'Label (cost)'."""
    cost = chain.unit_cost(kind)
    if buy_multiple == 1:
        return f"{label} ({cost})"
    count = max(1, chain.affordable_count(kind, buy_multiple))
    return f"{label} x{count} ({count * cost})"


def spend_confirm_text(count, cost, label):
    return f"Spend {count * cost} of {chain.funds:.0f} funds on {count} x {label}?"


def _purchase(kind, label, event=None):
    """One click on a buy button: applies the chip count, asking first when the spend crosses the
    optional confirmation threshold from Settings (H-20; off by default)."""
    count = chain.affordable_count(kind, _requested_count(event))
    if count <= 0:
        render()  # nothing affordable: keep the buttons' disabled state honest, as before
        return
    total = count * chain.unit_cost(kind)
    percent = _setting_number("confirmThreshold", 0)

    def _do():
        _run_action(lambda: chain.invest_many(kind, count))

    if percent > 0 and chain.funds > 0 and total > chain.funds * percent / 100.0:
        _confirm_dialog_ask(
            action_id="loop-spend",
            message=spend_confirm_text(count, chain.unit_cost(kind), label),
            confirm_label="Spend",
            on_confirm=_do,
        )
    else:
        _do()


def _make_circularity_handler(measure):
    def handler(event=None):
        _purchase(measure, CIRCULARITY_INVESTMENTS[measure]["label"], event)
    return handler


def on_invest_trade_link(event=None):
    _purchase("trade", "Trade Link", event)


def on_invest_regional_trade(event=None):
    _purchase("regional", "Regional Partner", event)


def on_invest_overseas_trade(event=None):
    _purchase("overseas", "Overseas Consortium", event)


def _make_buy_multiple_handler(count):
    def handler(event=None):
        global buy_multiple
        buy_multiple = count
        render()
    return handler


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
            if category == SECRET_GOODS_CATEGORY:
                # GH-14: only once unlocked, and only before the chain has produced
                # anything (the yard's scrap line changes the numbers).
                if not secret_unlocked() or chain.total_produced > 0:
                    return
                chain.head_start = SECRET_HEAD_START_UNITS
            else:
                chain.head_start = 0.0
            chain.goods_category = category
            chain.picked_category = category
            goods_categories_tried.add(category)
        _run_action(_do_select)
    return handler


def passport_story_lines(entries, goods_category):
    """H7: (cycle, sentence) for each recorded step, oldest first. A step that
    keeps the product in the loop is its next 'life'; a fresh mining resets the
    count. Falls back to the default category for an unknown one."""
    category = goods_category if goods_category in PASSPORT_PRODUCT_NAME else DEFAULT_GOODS_CATEGORY
    product = PASSPORT_PRODUCT_NAME[category].split(",")[0]  # "Nova", not "Nova, a phone"
    lives = 1
    lines = []
    for entry in entries:
        source = entry["source"]
        if source == "extraction":
            lives = 1
            text = PASSPORT_STORY["extraction"][category].format(product=product)
        else:
            lives += 1
            text = PASSPORT_STORY[source][category].format(product=product, life=f"life {lives}")
        lines.append((entry["cycle"], text))
    return lines


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
        f"{PASSPORT_PRODUCT_NAME.get(chain.goods_category, PASSPORT_PRODUCT_NAME[DEFAULT_GOODS_CATEGORY])}: "
        f"newly mined {mined} time(s), kept in the loop {recovered} time(s), "
        f"longest unbroken run in the loop {longest} cycle(s)."
    )
    for cycle, sentence in reversed(passport_story_lines(chain.passport, chain.goods_category)[-8:]):
        row = document.createElement("li")
        row.className = "passport-entry"
        row.innerText = f"Cycle {cycle}: {sentence}"
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
    # GH-20: the chain's first close is noted BEFORE the render, so the career panel and
    # the achievements count the render shows already include it.
    loop_just_closed = chain.is_loop_closed() and not was_closed
    first_close = chain.note_loop_closed() if loop_just_closed else False
    _update_career()
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
    if loop_just_closed:
        _show_loop_closed_banner(first_close)
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
        **({"donate_surplus": True} if chain.donate_surplus else {}),
        **({"lifetime_pool_donated": chain.lifetime_pool_donated} if chain.lifetime_pool_donated > 0 else {}),
        "closed_loop_streak": chain.closed_loop_streak,
        "best_closed_loop_streak": chain.best_closed_loop_streak,
        "chains_completed_count": chains_completed_count,
        "goods_categories_tried": sorted(goods_categories_tried),
        "summary": steward_summary(),  # B-23: write-only, never read back
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
    # Round 3 additions: each is written only when it differs from a fresh chain, so older
    # and default saves keep exactly the shape they had.
    if chain.picked_category != chain.goods_category:
        state["picked_category"] = chain.picked_category
    if chain.head_start > 0:
        state["head_start"] = chain.head_start
    if chain.perfect_bonus > 0:
        state["perfect_bonus"] = chain.perfect_bonus
    if chain.insurance_used:
        state["insurance_used"] = True
    if chain.insurance_armed:
        state["insurance_armed"] = True
    if chain.first_close_extracted is not None:
        state["first_close_extracted"] = chain.first_close_extracted
    if chain.first_close_trade_free is not None:
        state["first_close_trade_free"] = chain.first_close_trade_free
    if chain.rewind_used:
        state["rewind_used"] = True
    if chain.rival_on:
        state["rival_on"] = True
    if chain.rival_crossover_cycle is not None:
        state["rival_crossover_cycle"] = chain.rival_crossover_cycle
    if chain.market_shocks:
        state["market_shocks"] = True
    if chain.shocks_shrugged:
        state["shocks_shrugged"] = chain.shocks_shrugged
    career = career_state()
    if career:
        state["career"] = career
    return state


# B-23: a few honest, already-computed numbers for the hub's Climate Steward page. Written into the save as a
# read-only `summary` list ({label, value, unit, note?}); never read back by load_state().
def steward_summary():
    return [
        {"label": "Circular share of all production", "value": round(chain.lifetime_circular_fraction() * 100), "unit": "%"},
        {"label": "Goods categories tried", "value": len(goods_categories_tried & set(GOODS_CATEGORIES)),
         "unit": f"of {len(GOODS_CATEGORIES)}"},
        {"label": "Chains completed", "value": int(chains_completed_count), "unit": ""},
    ]


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
    picked = data.get("picked_category")
    chain.picked_category = picked if isinstance(picked, str) and picked in ALL_GOODS else chain.goods_category
    head_start = data.get("head_start")
    chain.head_start = float(head_start) if _finite_number(head_start, 0.0, 1000.0) else 0.0
    perfect = data.get("perfect_bonus")
    chain.perfect_bonus = float(perfect) if _finite_number(perfect, 0.0, 1e9) else 0.0
    chain.insurance_used = data.get("insurance_used") is True
    chain.insurance_armed = data.get("insurance_armed") is True
    if chain.insurance_armed:
        chain.insurance_used = True
    first_extracted = data.get("first_close_extracted")
    chain.first_close_extracted = (
        float(first_extracted) if _finite_number(first_extracted, 0.0, 1e12) else None
    )
    trade_free = data.get("first_close_trade_free")
    chain.first_close_trade_free = trade_free if isinstance(trade_free, bool) else None
    chain.last_cycle_mix = None
    chain.last_combo_gain = 0.0
    chain.last_insurance_saved = False
    chain.rewind_used = data.get("rewind_used") is True
    chain.market_shocks = data.get("market_shocks") is True
    chain.rival_on = data.get("rival_on") is True
    crossover = data.get("rival_crossover_cycle")
    chain.rival_crossover_cycle = (
        crossover if isinstance(crossover, int) and not isinstance(crossover, bool) and 1 <= crossover <= 1_000_000 else None
    )
    shrugged = data.get("shocks_shrugged")
    chain.shocks_shrugged = (
        shrugged if isinstance(shrugged, int) and not isinstance(shrugged, bool) and 0 <= shrugged <= 1_000_000 else 0
    )
    chain.rewind_snapshot = None  # the undo point is a visit-only thing: advance a cycle to set a new one
    load_career(data.get("career"))
    chain.lifetime_investment_spend = data.get("lifetime_investment_spend", 0.0)
    chain.lifetime_export_revenue = data.get("lifetime_export_revenue", 0.0)
    chain.donate_surplus = data.get("donate_surplus") is True
    donated = data.get("lifetime_pool_donated")
    chain.lifetime_pool_donated = (
        float(donated)
        if isinstance(donated, (int, float)) and not isinstance(donated, bool) and donated == donated and 0 <= donated < 1e12
        else 0.0
    )
    chain.last_donation = 0.0
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

    document.getElementById("pool-donate-button").addEventListener("click", create_proxy(on_toggle_pool_donation))
    for count in BUY_MULTIPLES:
        document.getElementById(f"buy-x{count}-button").addEventListener(
            "click", create_proxy(_make_buy_multiple_handler(count))
        )
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
    for category in ALL_GOODS:
        document.getElementById(f"goods-category-{category}-button").addEventListener(
            "click", create_proxy(_make_goods_category_handler(category))
        )
    document.getElementById("insurance-button").addEventListener("click", create_proxy(on_buy_insurance))
    document.getElementById("rewind-button").addEventListener("click", create_proxy(on_rewind))
    document.getElementById("market-shocks-button").addEventListener("click", create_proxy(on_toggle_market_shocks))
    document.getElementById("rival-button").addEventListener("click", create_proxy(on_toggle_rival))
    document.getElementById("copy-summary-button").addEventListener("click", create_proxy(on_copy_summary))
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
    # H25b/H29b: opt-in rich map toggles (remembered per browser).
    for kind, spec in VISUAL_VIEWS.items():
        document.getElementById(spec["button"]).addEventListener(
            "click", create_proxy(_make_visual_toggle_handler(kind))
        )
    _load_visual_prefs()
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
