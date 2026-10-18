"""Fixed numbers, content tables and pure rules (shocks, rival): no browser calls, no state."""


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
GAME_ID = "loop"
# GH-23: cosmetic ring themes, unlocked by what the career has done (all monotonic, so a theme never re-locks).
RING_THEME_UNLOCKS = {
    "neon": "Close the loop once, on any goods.",
    "blueprint": "Open the secret yard: close a loop on electronics, clothing and furniture.",
    "paper": "Earn three name plates.",
}
STRAIN_TIER_THRESHOLDS = (0.05, 0.15, 0.3, 0.5)  # GH-16: strain levels where each crack tier starts
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


# H-10 / H-28: the per-cycle ledger (a row per completed cycle, newest last) and its one-line notes.
LEDGER_MAX = 120
LEDGER_NOTE_MAX = 80
LEDGER_COLUMNS = (
    "cycle", "spent", "revenue", "export", "extraction_cost", "repair", "reuse", "recycle", "trade",
    "extraction", "damage", "multiplier", "partners", "funds_after", "note",
)
# H-1: finished (reset) chains kept for the Past Chains panel.
PAST_CHAINS_MAX = 20
PAST_CURVE_POINTS = 60

# H-26 / GH-28 / H-3: the six things a cycle's purchases can be, in a fixed order (the order of a buy-log row).
BUY_KINDS = ("repair", "reuse", "recycle", "trade", "regional", "overseas")
BUY_LABELS = {
    "repair": "Repair", "reuse": "Reuse", "recycle": "Recycling",
    "trade": "Trade Link", "regional": "Regional Partner", "overseas": "Overseas Consortium",
}
# H-8: Assist mode levels.
ASSIST_MODES = ("off", "hints", "guided")
BURST_MILESTONES = 4  # circular-fraction crosses each 25% step
PULSE_LARGE_UNITS = 20.0
PULSE_MEDIUM_UNITS = 8.0
STREAK_PROGRESS_STEP = 5  # H2: progress toward the next 5-cycle streak mark


# Iteration Pass 2 — single-item vignette: a concrete side-story
# following one representative product, alongside the abstract chain
# view, for a player who doesn't naturally read a flow diagram.


def clean_note(text):
    """H-28: a cycle note as stored: a plain single line, trimmed, at most LEDGER_NOTE_MAX characters."""
    if not isinstance(text, str):
        return ""
    return " ".join(text.split())[:LEDGER_NOTE_MAX]
