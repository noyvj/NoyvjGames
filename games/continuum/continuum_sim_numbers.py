"""Continuum's simulation numbers: production, consumption, pollution, sprawl, habitat and relay constants, land health, growth,
NEUTRAL_EFFECTS (the effects seam) and the score-history limits. Ask for this file to tune a rate or a threshold.
Part of the split of the old single-file sim.py: see "File map" in games/continuum/CLAUDE.md.
"""

# --- production and consumption ---------------------------------------
FOOD_PER_FORAGER = 3.0
# Notably higher than foraging -- the real productivity jump settled
# agriculture gave over foraging/gathering (see
# continuum-real-world-sources.md's Agrarian sources, e.g. the National
# Geographic and HISTORY pieces on the Neolithic Revolution's storable
# surplus). Farmers still scale with the same tool_factor/land_health/
# food_yield_mult as foragers -- agriculture is better, not exempt from
# the land's own limits.
FOOD_PER_FARMER = 5.0
MATERIALS_PER_GATHERER = 2.0
TOOLS_PER_CRAFTER = 0.8
# Guild specialisation (Medieval+, see continuum-real-world-sources.md's
# Fiveable source on guild specialisation): a Guildmaster produces tools
# faster than an ordinary Crafter, the same "same job, more productive
# specialist" bump FOOD_PER_FARMER already gave Farmers over Foragers
# (roughly the same ~1.6x ratio). Guildmasters still route through the
# same craft_bonus/tool_yield_mult chain Crafters do -- one tool economy,
# not two, the same discipline Farmers/Farmland were held to.
TOOLS_PER_GUILDMASTER = 1.3
# Mechanization (Industrial+, see continuum-real-world-sources.md's
# Britannica source on 19th-century industrial growth and the Sociology
# Institute source on urban population rising from 3% to ~50% of the
# world): a Factory Worker's output is a categorically bigger jump over a
# Gatherer's than any previous era's role addition was over its
# predecessor (Farmers/Guildmasters were both roughly a ~1.6x bump per the
# earlier build notes) -- mechanization was a genuinely bigger leap
# historically, not just another same-sized step, so the ratio here is
# deliberately larger. Factory Workers still route through the same
# tool_factor/land_health/materials_yield_mult chain Gatherers do, and
# feed the same shared extraction total -- one materials economy, not two,
# the same discipline every prior era's new role has been held to.
MATERIALS_PER_FACTORY_WORKER = 5.0
MATERIALS_PER_TOOL = 1.0
KNOWLEDGE_PER_KEEPER = 0.6

FOOD_PER_PERSON = 2.0
BASE_FOOD_STORAGE = 30.0

# --- surplus and trade (Agrarian+) --------------------------------------
# Per continuum-real-world-sources.md's Agrarian sources (National
# Geographic/HISTORY on storable surplus; EBSCO on surplus enabling
# specialization), once a settlement has reached the Agrarian era, food
# that would otherwise spoil past storage capacity is partly preserved as
# `surplus` instead of pure waste -- an abstraction of early trade/barter
# networks absorbing what a purely subsistence settlement would have lost.
# The rest still spoils; see CityState.advance_season()'s spoilage step.
SURPLUS_CONVERSION_RATE = 0.4

# --- canals and coordinated labor (Classical+) --------------------------
# Per continuum-real-world-sources.md's Classical sources (The Getty and
# TheCollector on Uruk/Sumer): canal-fed irrigation is what let a city scale
# past what unaided farmland could feed, but the same sources are explicit
# that canal management required *centralized planning and coordinated
# labor* -- it wasn't self-running infrastructure. That's modelled directly:
# a canal's yield bonus is scaled by how fully it is staffed by
# Administrators (capped at 1.0), so a canal built with nobody assigned to
# run it contributes nothing yet -- the building alone isn't the lesson,
# the coordinated labor is. See CityState.advance_season()'s harvest step.
CANAL_YIELD_BONUS = 0.5  # additive multiplier on farmer food output per fully-staffed canal
ADMINISTRATORS_PER_CANAL = 2  # administrators needed to fully staff one canal

# --- public works and shock resilience (Medieval+) ----------------------
# Per continuum-real-world-sources.md's Medieval sources (SAGE's Coomans &
# Hermenault on Ghent, and JHU Press's Magnusson on medieval England), the
# Medieval era's public-works spending is documented as being specifically
# about mitigating risk -- floods, disease, military vulnerability -- not
# about raising output the way Farmland/Canals do. That's why Public Works
# is modelled entirely differently from every other building so far: it
# has NO production formula in this file at all, and is read only by
# sustainability.py's resilience() (see CLAUDE.md's Milestone 10 build
# notes for why a labor-staffing dependency like Canals/Administrators
# would have forced the wrong lesson onto a different source). What this
# file provides is the one number sustainability.py and game.py both need:
# how many people one Public Works building can meaningfully protect.
PUBLIC_WORKS_COVERAGE_PER_BUILDING = 15.0

# --- pollution and the growth-side cost of industry (Industrial+) -------
# Per continuum-real-world-sources.md's Industrial sources -- Britannica on
# 19th-century industrial growth outpacing planning (slums and disease
# before sanitation reform caught up), and, more specifically, the Economic
# Journal (Oxford Academic) study showing industrial pollution measurably
# reduced long-run city growth -- Industrial is the first era where the
# game's central growth-vs-livability tension has to be a real MECHANICAL
# trade-off, not only a sustainability-score-side one the way Agrarian's
# hoarding penalty, Classical's overextension penalty and Medieval's
# public-works bonus all were. `CityState.pollution` is a lagged 0..1
# stock, modelled with the exact same shape `land_health` already uses
# (see the season loop's step 8 below): what happens this season updates
# the stock for the NEXT season's growth check, rather than this one's --
# so a settlement doesn't feel a pollution spike until the season after it
# happened, the same way over-harvesting the land doesn't tank growth the
# instant it happens either. Factory Workers are the only source of it;
# Sanitation Works (built, not staffed -- see the Public Works precedent
# and CLAUDE.md's Milestone 11 build notes for why staffing wasn't the
# right shape here either) is the only thing that absorbs it, and a small
# natural decay (weather, dilution, simply not being added to) always
# pulls it back down on its own even with no Sanitation Works built at
# all, so an idle-but-already-polluted settlement isn't stuck forever.
POLLUTION_PER_FACTORY_WORKER = 0.02  # pollution added per assigned factory worker per season
POLLUTION_NATURAL_DECAY = 0.015  # baseline pollution lost per season regardless of sanitation
SANITATION_ABSORPTION_PER_BUILDING = 0.05  # pollution absorbed per Sanitation Works per season
# How much of GROWTH_RATE is lost at full (1.0) pollution -- the direct
# mechanical read of the Economic Journal source's "measurably reduced
# long-run city growth" finding. Deliberately a SOFT, proportional cost
# (scales the growth rate down) rather than land_health's HARD gate
# (blocks growth outright below GROWTH_MIN_LAND_HEALTH) -- a different
# shape on purpose, since the source describes pollution slowing growth,
# not stopping it dead the way a truly exhausted plot of land would.
POLLUTION_GROWTH_PENALTY_WEIGHT = 0.6

# --- sprawl and the growth-side cost of unmanaged density (Digital+) ----
# Per continuum-real-world-sources.md's Current/Digital sources -- most
# directly National Geographic Education's finding that urban areas grew
# 1.28 times faster than their populations between 2000 and 2014, i.e.
# cities spreading outward faster than they're actually filling up -- this
# is Digital's own growth-vs-livability tension, and the task that spec'd
# this milestone was explicit it should have a real mechanical consequence,
# not just another additive score bonus/penalty the way Agrarian/Classical/
# Medieval's adjustments were. `CityState.sprawl` is a second lagged 0..1
# stock, the same shape POLLUTION_PER_FACTORY_WORKER's model already
# established, but DELIBERATELY WIRED INTO A DIFFERENT LEVER than
# pollution's direct GROWTH_RATE multiplier: sprawl amplifies how much land
# pressure the settlement's existing extraction creates (see the season
# loop's step 8 below), reusing Phase 1's own land_health/
# GROWTH_MIN_LAND_HEALTH machinery instead of stacking a second bespoke
# growth-rate penalty next to Industrial's. Population growth that outpaces
# density investment produces it (unmanaged growth spreads outward, per the
# source); Urban Planners (a role, working proactively every season) and
# Transit Hubs (a building, absorbing what has already accumulated -- the
# same "built, not staffed" shape Public Works/Sanitation Works already
# established) both bring it back down, and a small natural decay (infill,
# slow densification even with no dedicated investment) always pulls it
# down a little on its own, the same "nothing is stuck forever" discipline
# pollution's own decay already uses.
SPRAWL_PER_NEW_RESIDENT = 0.05  # sprawl added per person of season growth, left unmanaged
PLANNER_SPRAWL_MITIGATION = 0.03  # sprawl reduced per assigned planner per season
TRANSIT_HUB_ABSORPTION_PER_BUILDING = 0.05  # sprawl absorbed per Transit Hub per season
SPRAWL_NATURAL_DECAY = 0.01  # baseline sprawl lost per season regardless of investment
# How much extra land pressure the same extraction creates at full (1.0)
# sprawl -- a sprawled-out settlement needs more roads, pipes and cleared
# land to support the same production, so the SAME extraction total leaves
# a bigger real footprint. This is genuinely different in shape from
# POLLUTION_GROWTH_PENALTY_WEIGHT: pollution scales GROWTH_RATE directly
# (a new lever), sprawl instead scales `extraction` itself (an existing
# lever, present since Phase 1) before it's compared against the land's
# sustainable yield -- so a heavily-sprawled Digital settlement can trip
# land_health's existing hard GROWTH_MIN_LAND_HEALTH gate for the exact
# same reason an over-harvesting Tribal one always could, not through a
# second, parallel growth formula.
SPRAWL_EXTRACTION_PENALTY_WEIGHT = 0.5

# --- off-world habitat layout and usability (Space Age+) ----------------
# Per continuum-real-world-sources.md's Space Age sources -- most directly
# the Dagstuhl/SpaceCHI 2025 source on how modular space habitat layouts
# affect real usability "at scale," and Planetizen's framing of NASA's 1977
# "Space Settlements: A Design Study" as literally an urban-planning policy
# document (residential space, schools, transit) rather than something
# categorically different from ordinary city planning. This is deliberately
# NOT a seventh copy of Industrial/Digital's growth-side stock-and-penalty
# shape: "post-scarcity" genuinely changes what the settlement's central
# tension is about, and the task that spec'd this milestone was explicit
# that defaulting to another growth lever just because the last two eras
# used one would be the wrong call here. Habitat Architects and Habitat
# Rings never touch production, extraction, or growth anywhere in this
# file -- `habitat_capacity()` below is read only by sustainability.py's
# provisions(), as a brand-new fourth basic need alongside food/shelter/
# culture, from Space Age on. See CLAUDE.md's Milestone 13 build notes for
# the full reasoning, including why livability/equity (not a bolt-on
# penalty/bonus function) is genuinely the right home for this one.
#
# The shape reused here is deliberately Classical's canal/administrator
# pairing, not Medieval/Industrial/Digital's "unstaffed building" one: a
# Habitat Ring's usefulness is scaled by how many Architects actually
# designed its layout (capped at 1.0), because the Dagstuhl source's whole
# point is that a modular structure's raw capacity and its real usability
# are different things -- the same lesson Classical's canals taught about
# coordinated labor, now applied to coordinated design instead.
RING_CAPACITY_PER_BUILDING = 30.0  # people one FULLY-architected ring can serve well
ARCHITECTS_PER_RING = 3  # architects needed to fully realise one ring's layout

# --- regional relay network (Relay Age+) ------------------------------
# The eighth era (R2-K26). Grounded in the sources listed in
# info_content.py's "relay" entry: the UN's own SDG 11 target 11.a (positive
# links between urban, peri-urban and rural areas through regional
# development planning), the economic-geography idea of a core and a
# periphery (peripheral regions supplying the core, or depending on it), and
# NASA's real Commercial Resupply Services model for keeping an outpost
# alive by regular cargo flights. It is deliberately a THIRD shape: not a
# lagged growth-side stock like pollution/sprawl, and not a fourth basic
# provision like Space Age's habitat usability, but the first mechanic that
# treats the settlement as a NETWORK -- a core plus holdings -- and scores
# whether the two are treated fairly.
#
#   - Each Relay Station houses HOLDING_RESIDENTS_PER_RELAY people in a
#     holding at the far end of its link (they count toward `population` and
#     the settlement's housing) and, while that holding is kept supplied,
#     opens RELAY_LAND_YIELD of extra sustainable land yield for the whole
#     settlement (new land is what regional expansion is FOR).
#   - What a relay moves is banked `surplus`: every season each holding
#     resident needs OUTLYING_SUPPLY_PER_RESIDENT of it. It can only be
#     carried as fast as Wayfinders haul it (WAYFINDER_CARRY each) AND as fast
#     as the stations allow (RELAY_THROUGHPUT each) -- the smaller of the two,
#     and never more than the surplus actually in store.
#   - `outlying_served` (0..1, a lagged stock like land_health) is the share
#     of that need last season's delivery met. It scales the land bonus above
#     and, in sustainability.py, drives an inter-site equity gap.
HOLDING_RESIDENTS_PER_RELAY = 6
RELAY_LAND_YIELD = 6.0
OUTLYING_SUPPLY_PER_RESIDENT = 1.0
WAYFINDER_CARRY = 2.0
RELAY_THROUGHPUT = 9.0

# Tools multiply every gathering yield, capped at one tool per person —
# a settlement can't get more out of the land by hoarding axes nobody holds.
TOOL_EFFECT = 0.5
TOOL_DECAY_RATE = 0.08

# --- land ---------------------------------------------------------------
# The heart of the sustainability model, and the reason a small settlement
# can out-score a large one: the land yields a finite amount per season, and
# taking more than that degrades it, which cuts every future yield. Staying
# under the line lets it recover.
LAND_SUSTAINABLE_YIELD = 26.0
LAND_DEGRADE_PER_UNIT = 0.006
LAND_REGEN = 0.03
MIN_LAND_HEALTH = 0.15

# --- population dynamics ------------------------------------------------
# Growth accrues as progress rather than firing on a dice roll, so growth is
# a readable consequence of surplus and housing rather than luck.
GROWTH_RATE = 0.35
STARVATION_SEVERITY = 0.5
GROWTH_MIN_LAND_HEALTH = 0.3

# Seasons of stored food that counts as a full buffer (used by the
# resilience half of the sustainability score, and as the growth threshold).
BUFFER_SEASONS = 3.0


# --- research effects seam ---------------------------------------------
# Milestone 3's research tree aggregates its researched nodes into a dict
# of exactly these keys. Milestone 1 runs on the neutral version, so the
# simulation never needs to know whether a tree exists.
NEUTRAL_EFFECTS = {
    "food_yield_mult": 1.0,
    "materials_yield_mult": 1.0,
    "tool_yield_mult": 1.0,
    "knowledge_mult": 1.0,
    "regen_mult": 1.0,  # raises the land's sustainable yield and recovery rate
    "extraction_efficiency": 1.0,  # <1 = less land pressure per unit harvested
    "food_storage_bonus": 0.0,
    "housing_bonus": 0.0,
    "culture_bonus": 0.0,
    "equity_bonus": 0.0,  # consumed by sustainability.py, not by the sim
    "resilience_bonus": 0.0,  # ditto
    # Additive on top of SURPLUS_CONVERSION_RATE (Milestone 8) -- still the
    # one research seam, just one more key in the same dict.
    "surplus_conversion_bonus": 0.0,
    # Additive on top of CANAL_YIELD_BONUS (Milestone 9) -- same seam again.
    "canal_yield_bonus": 0.0,
    # Additive multiplier on Public Works' per-building coverage (Milestone
    # 10) -- same shape as housing_bonus/culture_bonus above (a capacity
    # multiplier), not a yield key, since Public Works has no production
    # formula for a yield key to modify in the first place.
    "public_works_bonus": 0.0,
    # Industrial (Milestone 11) -- a multiplicative key at a 1.0 base, same
    # as food_yield_mult/materials_yield_mult above: reduces how much
    # pollution a Factory Worker generates per season (smoke-abatement
    # research, not sanitation infrastructure -- see sanitation_bonus below
    # for the building-side lever).
    "pollution_output_mult": 1.0,
    # Additive multiplier on Sanitation Works' per-building absorption --
    # same capacity-multiplier shape as public_works_bonus above.
    "sanitation_bonus": 0.0,
    # Digital (Milestone 12) -- a multiplicative key at a 1.0 base, same
    # shape as pollution_output_mult above: reduces how much sprawl a
    # season of unmanaged population growth produces (data-driven zoning
    # research, not Transit Hubs' own building-side lever -- see
    # transit_bonus below for that).
    "sprawl_output_mult": 1.0,
    # Additive multiplier on Transit Hubs' per-building absorption -- same
    # capacity-multiplier shape as public_works_bonus/sanitation_bonus.
    "transit_bonus": 0.0,
    # Space Age (Milestone 13) -- additive on top of how far Architects'
    # staffing already stretches a Habitat Ring's layout quality (see
    # habitat_capacity() below), the same capacity-multiplier shape as
    # public_works_bonus/sanitation_bonus/transit_bonus above.
    "habitat_layout_bonus": 0.0,
    # Relay Age (R2-K26) -- additive multiplier on each Relay Station's
    # throughput ceiling (see relay_throughput() below), the same capacity-
    # multiplier shape as the *_bonus keys above.
    "relay_bonus": 0.0,
}


def effects_or_neutral(effects):
    """Fills in any missing keys, so a partial effects dict is always safe."""
    if not effects:
        return dict(NEUTRAL_EFFECTS)
    merged = dict(NEUTRAL_EFFECTS)
    merged.update(effects)
    return merged


# Z25 (planning/TODO.md): score_history was append-only and uncapped, and
# every one of the seven possible era_snapshots embeds a full copy of it at
# time-of-snapshot -- so the save grew faster than linearly as more eras
# completed, the same shape log.Chronicle's own MAX_ENTRIES cap already
# guards against elsewhere in this game. Capped here, the same 60-entry
# size as Chronicle, for consistency rather than a separately-tuned number.
SCORE_HISTORY_MAX_ENTRIES = 60
# The two thresholds `_ever_recovered_from_collapse`-shaped logic has always
# used (see game.py's achievement check) -- named here now that the
# "lowest ever seen, then later recovered" tracking moved onto CityState
# itself so the cap above can't quietly break that achievement.
SCORE_COLLAPSE_THRESHOLD = 30
SCORE_RECOVERY_THRESHOLD = 70
