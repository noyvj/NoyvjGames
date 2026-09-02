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
  land's sustainable yield.
- **Resilience** — could it survive a bad season? Food buffer, tool stock,
  and how diversified the workforce is.

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


def equity(state, effects=None):
    """Bounded by the least-met need, then penalised for lopsidedness.

    Using the minimum rather than the mean is the whole point: a need met
    for 40% of people means 60% of people go without, and no amount of
    over-provision elsewhere makes that equitable.
    """
    effects = sim.effects_or_neutral(effects)
    values = provisions(state, effects)
    worst = min(values)
    spread = max(values) - worst
    base = worst * (1.0 - EQUITY_SPREAD_PENALTY * spread)
    return _clamp(base + effects["equity_bonus"])


def balance(state, effects=None):
    """Land health, and whether the last harvest stayed within its limit.

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
    return _clamp((_clamp(state.land_health) + harvest) / 2.0)


def resilience(state, effects=None):
    effects = sim.effects_or_neutral(effects)
    seasons_of_food = state.population * sim.FOOD_PER_PERSON * sim.BUFFER_SEASONS
    food_buffer = _ratio(state.resources["food"], seasons_of_food)
    tool_readiness = _ratio(state.resources["tools"], state.population)
    diversity = _clamp(state.role_diversity())
    base = (food_buffer + tool_readiness + diversity) / 3.0
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
def score_label(value):
    if value >= 85:
        return "Thriving"
    if value >= 70:
        return "Steady"
    if value >= 50:
        return "Strained"
    if value >= 30:
        return "Failing"
    return "Collapsing"


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
