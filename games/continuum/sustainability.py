"""Continuum — sustainability / livability score.

Milestone 2 of Phase 1, and per the design doc it exists from the very
first era rather than being introduced later.

The rule the whole module is built around, in the doc's own words: *"a
tribal settlement can be more sustainable than a poorly-planned industrial
one — the score needs to reflect that kind of nuance, not just scale with
city size."* So every input here is a **ratio**, never a count. Population,
building counts and stockpiles only ever appear divided by the number of
people they have to serve, or by the limit of the land they come from.
Doubling a settlement while doubling everything it needs is score-neutral;
doubling it without is a fall.

The score is a pure function of a `CityState` (plus the research effects
dict) — nothing here mutates state, and there is no hidden accumulator, so
it can be recomputed for any snapshot of any era at any time. That matters
for Milestone 4: a revisited era's score is just this function applied to
that era's snapshot.

Four components, per the doc's framing of SDG 11 ("livability, equity,
resource balance, resilience — not just raw growth"):

- **Livability** — are people fed, housed, and part of something? The
  average of the settlement's three basic provisions.
- **Equity** — is everyone provided for, or only some? Bounded by the
  *least*-met need rather than the average, and penalised further when
  provision is lopsided. A settlement with grand shelters and empty
  stomachs scores badly here even when its average looks fine.
- **Resource balance** — is the settlement living inside what the land can
  give? Land health, plus whether this season's harvest stayed under the
  land's sustainable yield; and, from Industrial on, how much industrial
  pollution the settlement has let build up — see the Milestone 11 build
  notes in CLAUDE.md. Pollution is also the tree's first adjustment with a
  real GROWTH-side consequence, not only a score-side one (see
  sim.CityState.advance_season()'s population step).
- **Resilience** — could it survive a bad season? Food buffer, tool stock,
  and how diversified the workforce is; from Classical on, whether the
  workforce has been hollowed out by overextending into administration;
  and from Medieval on, whether the settlement has actually paid ahead of
  time to blunt a shock (flood, disease, fire) rather than just being
  lucky enough not to have hit one yet — see the Classical and Medieval
  build notes in CLAUDE.md.

The four are weighted equally. That is a judgement call, not a finding;
`COMPONENT_WEIGHTS` is the single place to revisit it.
"""

import sim

COMPONENTS = ["livability", "equity", "balance", "resilience"]

COMPONENT_LABEL = {
    "livability": "Livability",
    "equity": "Equity",
    "balance": "Resource balance",
    "resilience": "Resilience",
}

COMPONENT_WEIGHTS = {
    "livability": 0.25,
    "equity": 0.25,
    "balance": 0.25,
    "resilience": 0.25,
}

# How hard lopsided provision is punished in the equity component: at 0.5,
# a settlement whose best-met need is fully met and whose worst is not met
# at all loses half of what its worst-met need earned it.
EQUITY_SPREAD_PENALTY = 0.5


def _clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def _ratio(have, needed):
    """`have / needed`, capped at 1 — surplus beyond a need doesn't score."""
    if needed <= 0:
        return 1.0
    return _clamp(have / needed)


# --- the three basic provisions ---------------------------------------
def food_security(state):
    """The share of the settlement that ate last season."""
    return _clamp(state.fed_fraction)


def shelter_adequacy(state, effects=None):
    return _ratio(state.housing_capacity(effects), state.population)


def social_provision(state, effects=None):
    """Whether the settlement's hearths/gathering places serve everyone."""
    return _ratio(state.culture_capacity(effects), state.population)


def provisions(state, effects=None):
    return [
        food_security(state),
        shelter_adequacy(state, effects),
        social_provision(state, effects),
    ]


# --- the four components (each 0..1) -----------------------------------
def livability(state, effects=None):
    """The average of the three basic provisions.

    Takes `effects` because shelter and social provision are read through
    capacities that research can raise; it has no bonus key of its own.
    """
    values = provisions(state, effects)
    return _clamp(sum(values) / len(values))


# --- Agrarian+ : surplus hoarding (Milestone 8) --------------------------
# continuum-real-world-sources.md's Agrarian sources are explicit that
# surplus is what created the first social hierarchies and property
# accumulation (the TxWes Pressbooks source), so once a settlement can
# actually accumulate `surplus` at all, banking a lot of it per person
# costs equity here too — the same real-world link the era's own info
# panel cites. Ratio-based like everything else in this file: surplus PER
# CAPITA against a fixed "fair share" line, capped at 1, so a bigger
# settlement isn't penalised just for having a bigger raw number of it.
SURPLUS_FAIR_SHARE = 20.0  # surplus-per-capita above this reads as "hoarded"
SURPLUS_HOARDING_PENALTY_WEIGHT = 0.3  # max equity knocked off at full pressure


def _surplus_hoarding_penalty(state):
    """0..SURPLUS_HOARDING_PENALTY_WEIGHT — zero for any era before
    Agrarian, so every pre-Milestone-8 Tribal-era equity() result is
    unchanged by this function's mere existence."""
    if sim.era_index(state.era) < sim.era_index("agrarian"):
        return 0.0
    if state.population <= 0:
        return 0.0
    per_capita = state.resources.get("surplus", 0.0) / state.population
    pressure = _clamp(per_capita / SURPLUS_FAIR_SHARE)
    return pressure * SURPLUS_HOARDING_PENALTY_WEIGHT


def equity(state, effects=None):
    """Bounded by the least-met need, then penalised for lopsidedness (and,
    from the Agrarian era on, for hoarding surplus per capita).

    Using the minimum rather than the mean is the whole point: a need met
    for 40% of people means 60% of people go without, and no amount of
    over-provision elsewhere makes that equitable.
    """
    effects = sim.effects_or_neutral(effects)
    values = provisions(state, effects)
    worst = min(values)
    spread = max(values) - worst
    base = worst * (1.0 - EQUITY_SPREAD_PENALTY * spread)
    base -= _surplus_hoarding_penalty(state)
    return _clamp(base + effects["equity_bonus"])


def balance(state, effects=None):
    """Land health, and whether the last harvest stayed within its limit
    (and, from the Industrial era on, how much pollution has built up).

    Takes `effects` only to match the shared component signature — the land
    modifiers reach this through `last_sustainable_yield`, which the season
    loop has already computed with them applied.
    """
    extraction = state.last_extraction
    limit = state.last_sustainable_yield
    # `extraction <= 0` is redundant for any sane limit, and deliberately
    # kept: it is what stops a corrupt save with a negative limit from
    # dividing by a zero extraction below.
    if extraction <= limit or extraction <= 0:
        harvest = 1.0
    else:
        harvest = _clamp(limit / extraction)
    base = _clamp((_clamp(state.land_health) + harvest) / 2.0)
    base -= _industrial_pollution_penalty(state)
    return _clamp(base)


# --- Industrial+ : pollution's environmental cost (Milestone 11) --------
# continuum-real-world-sources.md's Industrial sources describe a genuinely
# different shape from every prior era-specific adjustment above: Agrarian's
# hoarding penalty, Classical's overextension penalty and Medieval's
# public-works bonus all worked purely through the sustainability score.
# The Economic Journal (Oxford Academic) source is explicit that industrial
# pollution had a real, PROVABLE GROWTH cost, not just a moral one -- so
# pollution also gets a real growth-side consequence (see
# sim.CityState.advance_season()'s population step, and
# sim.POLLUTION_GROWTH_PENALTY_WEIGHT's own comment for why that's a soft
# proportional slowdown rather than land_health's hard gate). This function
# is only the SCORE-side half of the same mechanic: pollution also drags
# down resource balance, the same way land overuse already does, since both
# are forms of "the settlement taking more from its surroundings than it
# puts back" -- Britannica's framing of industrial growth outpacing
# planning and producing slums and disease is the real-world anchor for
# treating this as an environmental-balance question rather than, say,
# folding it into equity or resilience the way earlier eras' adjustments
# were.
INDUSTRIAL_POLLUTION_PENALTY_WEIGHT = 0.3  # max balance knocked off at full (1.0) pollution


def _industrial_pollution_penalty(state):
    """0..INDUSTRIAL_POLLUTION_PENALTY_WEIGHT — zero for any era before
    Industrial, so every pre-Milestone-11 balance() result is unchanged by
    this function's mere existence. `state.pollution` is already a 0..1
    ratio-like stock (see sim.py's own build-up/decay model), not a raw
    count, so — unlike every prior era-specific adjustment in this file —
    no extra per-capita ratio work is needed here to keep it scale-neutral."""
    if sim.era_index(state.era) < sim.era_index("industrial"):
        return 0.0
    return _clamp(state.pollution) * INDUSTRIAL_POLLUTION_PENALTY_WEIGHT


# --- Classical+ : administrative overextension (Milestone 9) ------------
# continuum-real-world-sources.md's Classical sources (The Getty,
# TheCollector) are explicit that canal-fed irrigation only worked because
# it was *centrally planned and coordinated* -- administration was real
# labor, not a free multiplier. That cuts both ways: a settlement that
# pours a large share of its workforce into Administrators, beyond what its
# canals actually need staffed, isn't investing in coordination so much as
# hollowing out its own productive capacity — coordinating labor that has
# nothing left to coordinate is exactly the kind of top-heavy arrangement
# that has nothing to fall back on if a season goes badly. That is a
# resilience question ("could it survive a bad season?"), not an equity one
# the way Agrarian's surplus-hoarding penalty was — nobody is being denied
# anything here, the settlement is just structurally top-heavy. Ratio-based
# like every other input in this file: the *share* of the assigned
# workforce in Administrators, not the raw headcount, so a bigger
# settlement isn't penalised just for having a bigger raw number of them.
ADMIN_SHARE_FAIR_LIMIT = 0.2  # administrator share of the workforce below this is unpenalised
ADMIN_OVEREXTENSION_PENALTY_WEIGHT = 0.25  # max resilience knocked off at full pressure


def _administrative_overextension_penalty(state):
    """0..ADMIN_OVEREXTENSION_PENALTY_WEIGHT — zero for any era before
    Classical, so every pre-Milestone-9 resilience() result is unchanged by
    this function's mere existence."""
    if sim.era_index(state.era) < sim.era_index("classical"):
        return 0.0
    assigned = state.assigned_workers()
    if assigned <= 0:
        return 0.0
    share = state.allocation.get("administrators", 0) / assigned
    pressure = _clamp((share - ADMIN_SHARE_FAIR_LIMIT) / (1.0 - ADMIN_SHARE_FAIR_LIMIT))
    return pressure * ADMIN_OVEREXTENSION_PENALTY_WEIGHT


# --- Medieval+ : public-works shock resilience (Milestone 10) -----------
# continuum-real-world-sources.md's Medieval sources (SAGE's Coomans &
# Hermenault on Ghent, and JHU Press's Magnusson on medieval England,
# literally titled "Urban Infrastructure in Medieval England: Sustainability
# and Resilience") are explicit that medieval public-works spending was
# specifically *risk mitigation* -- floods, disease, military vulnerability
# -- not output growth. That is a genuinely different shape from both prior
# eras' adjustments: Agrarian's surplus-hoarding penalty punished a
# hoarding *imbalance*, and Classical's administrative-overextension
# penalty punished a labor-allocation *imbalance*; Medieval's sources
# describe no equivalent imbalance to punish -- investing in flood/disease/
# fire mitigation ahead of a bad season is simply, unconditionally a good
# hedge, so this is deliberately the tree's first BONUS rather than another
# penalty (see CLAUDE.md's Milestone 10 build notes for the fuller
# reasoning, including why this doesn't force Classical's staffing-
# dependency shape onto a source that isn't about coordinated labor).
# Ratio-based like every other input in this file: per-capita COVERAGE
# (state.public_works_coverage()), not a raw building count, so a bigger
# settlement isn't credited just for building more in absolute terms.
PUBLIC_WORKS_RESILIENCE_BONUS_WEIGHT = 0.2  # max resilience GAINED at full per-capita coverage


def _public_works_resilience_bonus(state, effects=None):
    """0..PUBLIC_WORKS_RESILIENCE_BONUS_WEIGHT — zero for any era before
    Medieval, so every pre-Milestone-10 resilience() result is unchanged by
    this function's mere existence. Building-based, not allocation-based,
    so — unlike the Classical overextension penalty — it has no interaction
    with role_diversity() to isolate against: it doesn't touch `allocation`
    at all."""
    if sim.era_index(state.era) < sim.era_index("medieval"):
        return 0.0
    if state.population <= 0:
        return 0.0
    effects = sim.effects_or_neutral(effects)
    coverage_ratio = _ratio(state.public_works_coverage(effects), state.population)
    return coverage_ratio * PUBLIC_WORKS_RESILIENCE_BONUS_WEIGHT


def resilience(state, effects=None):
    effects = sim.effects_or_neutral(effects)
    seasons_of_food = state.population * sim.FOOD_PER_PERSON * sim.BUFFER_SEASONS
    food_buffer = _ratio(state.resources["food"], seasons_of_food)
    tool_readiness = _ratio(state.resources["tools"], state.population)
    diversity = _clamp(state.role_diversity())
    base = (food_buffer + tool_readiness + diversity) / 3.0
    base -= _administrative_overextension_penalty(state)
    base += _public_works_resilience_bonus(state, effects)
    return _clamp(base + effects["resilience_bonus"])


COMPONENT_FUNCTIONS = {
    "livability": livability,
    "equity": equity,
    "balance": balance,
    "resilience": resilience,
}


def components(state, effects=None):
    """All four components as 0..1 values, keyed by component id."""
    return {name: COMPONENT_FUNCTIONS[name](state, effects) for name in COMPONENTS}


def _weighted(values):
    """The 0..100 headline number for an already-computed component dict."""
    total = sum(values[name] * COMPONENT_WEIGHTS[name] for name in COMPONENTS)
    weight = sum(COMPONENT_WEIGHTS[name] for name in COMPONENTS)
    return _clamp(total / weight, 0.0, 1.0) * 100.0


def score(state, effects=None):
    """The headline sustainability/livability score, 0..100."""
    return _weighted(components(state, effects))


def evaluate(state, effects=None):
    """Score plus components, all on the 0..100 scale the UI displays.

    Both halves come out of one `components()` call: the render path asks
    for the score and the breakdown together every frame, so recomputing
    the four components for the score would be doing the same work twice.
    """
    values = components(state, effects)
    return {
        "score": _weighted(values),
        "components": {name: values[name] * 100.0 for name in COMPONENTS},
    }


# --- narration ----------------------------------------------------------
# The five score bands, ascending. Exposed as a constant (rather than only
# implicit in score_label()'s if/elif chain below) so other modules that
# need to compare "did this get better or worse" -- log.py's
# livability-shift trigger, transition.py's transition-readiness check
# (Milestone 6/7) -- share one source of truth for the ordering instead of
# each keeping its own copy in sync by hand.
SCORE_LABELS = ["Collapsing", "Failing", "Strained", "Steady", "Thriving"]


def score_label(value):
    if value >= 85:
        return SCORE_LABELS[4]
    if value >= 70:
        return SCORE_LABELS[3]
    if value >= 50:
        return SCORE_LABELS[2]
    if value >= 30:
        return SCORE_LABELS[1]
    return SCORE_LABELS[0]


def _weakest(values):
    return min(COMPONENTS, key=lambda name: values[name])


def weakest_component(state, effects=None):
    """The component the UI highlights — one definition of "worst", shared
    with `score_note()` so the highlighted line and the note can't disagree."""
    return _weakest(components(state, effects))


def score_note(state, effects=None):
    """One line naming what is dragging the settlement down."""
    values = components(state, effects)
    weakest = _weakest(values)
    if values[weakest] >= 0.85:
        return "Nothing here is going badly. This is a good place to live."
    return {
        "livability": "People are going without — food, shelter, or somewhere to gather.",
        "equity": "The settlement provides well for some and poorly for others.",
        "balance": "The settlement is taking more from the land than it gives back.",
        "resilience": "Nothing is held in reserve. One bad season would be very bad.",
    }[weakest]
