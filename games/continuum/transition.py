"""Continuum — the era-transition beat system.

Milestone 7 of Phase 2. A generic framework, reusable across all six
transitions the arc will eventually need (Tribal→Agrarian, Agrarian→
Classical, ... Digital→Space), for the "bigger narrative moment when the
city crosses into a new era" the design doc's Core system 4 asks for.
This module is what finally calls `Campaign.advance_to_era()` — Milestone
4 built and tested that method's own bookkeeping (snapshot the era being
left, move `furthest_era`, retarget the research tree), but nothing called
it until now. Read `save.Campaign.advance_to_era()` and its tests first;
this module is deliberately thin on top of it.

## Scope note — why this doesn't have a button yet

This milestone builds and tests the *framework*: is a transition allowed
right now, what happens to state/tree/chronicle when one fires, and how a
transition beat differs from an ordinary `log.py` entry (longer text, its
own "transition" kind, one per era crossing rather than per season). It
deliberately does **not** wire a live "Advance to Agrarian" control into
`index.html` yet, and only defines real requirements/beat text for the one
transition that is even reachable right now (Tribal → Agrarian).

The reason: `sim.py`'s roles/buildings/production constants are still
Tribal-only module-level tables (see that module's own docstring — "Only
the Tribal era is modelled so far"). Wiring a working transition control
today would let a player flip `state.era` to `"agrarian"` while every
role/building label and every production number stayed exactly what they
were in Tribal — the header would say "Agrarian era" over content that is
still, mechanically, Tribal. That is exactly the "looks shipped, isn't"
gap the hub's own cadence rule warns against.

Milestone 8 is where Agrarian gets real sim content, and per its own
description this is the milestone that "exercises the full save/revisit
and transition-beat systems end to end" — i.e. it is what wires this
framework into the UI for real, once there is somewhere real to transition
to. Until then, `attempt_transition()` is fully implemented, fully tested,
and callable by name (from a test, or from Milestone 8's own button
handler once it exists) — it just isn't reachable by clicking anything in
the shipped page yet.
"""

import research
import sim
import sustainability

# One entry per transition this build actually knows how to make, keyed by
# the era being LEFT. Phase 3 adds five more as each remaining era gets
# built — the same incremental table pattern info_content.py already uses
# for the real-world info panel, and TRANSITION_BEATS below follows suit.
TRANSITION_REQUIREMENTS = {
    "tribal": {
        "to_era": "agrarian",
        # The settlement has outgrown a single "everyone knows everyone"
        # band — matches the ~15-person layer Dunbar's research (cited by
        # the Tribal info panel, Milestone 5) puts just above a
        # settlement's smallest close-knit group, and lines up with
        # log.POPULATION_MILESTONES[1].
        "min_population": 15,
        # The late Tribal research tier has to be UNLOCKED (two early-tier
        # nodes researched), not necessarily finished — a soft bar, the
        # same spirit as the tier-gate itself rather than a checklist.
        "min_tier": research.era_tiers("tribal")[-1],
        # Reuses the same five-band scale the UI already narrates the
        # score with. A settlement that is Collapsing or Failing has no
        # business being told it's ready to move on, whatever its
        # population or research says.
        "min_score_label": "Strained",
    },
    # Milestone 9 — the same three-part shape as Tribal->Agrarian above,
    # reused verbatim rather than re-litigated: Milestone 7's own build
    # notes flagged this as worth revisiting "once more than one era
    # transition exists and a pattern... becomes clearer." With a second
    # data point in hand, the pattern held — the only real judgement call
    # left was which numbers, not which shape (see CLAUDE.md's Milestone 9
    # build notes for why "Strained" and not a higher bar).
    "agrarian": {
        "to_era": "classical",
        # The next Dunbar-ish layer up from Tribal->Agrarian's 15 --
        # log.POPULATION_MILESTONES[2], "outgrown a size a handful of
        # people can hold together by memory alone," which is exactly the
        # real-world shift this era's own sources describe (temple-directed
        # administration replacing kinship-scale coordination).
        "min_population": 25,
        # The late Agrarian research tier has to be UNLOCKED (two
        # early-Agrarian nodes researched) -- same soft-bar spirit as the
        # Tribal requirement above.
        "min_tier": research.era_tiers("agrarian")[-1],
        "min_score_label": "Strained",
    },
    # Milestone 10 -- the same three-part shape a third time. See
    # CLAUDE.md's Milestone 10 build notes for why "Strained" was kept
    # rather than raised, the same judgement Milestone 9 already made once.
    "classical": {
        "to_era": "medieval",
        # The next population milestone up from Agrarian->Classical's 25 --
        # log.POPULATION_MILESTONES[3], the point log.py's own text calls
        # "no longer a matter of luck." A fitting hinge into an era whose
        # own sources are specifically about planning AHEAD of a shock
        # (flood, disease, fire) rather than absorbing one by luck.
        "min_population": 40,
        # The late Classical research tier has to be UNLOCKED (two tier-5
        # nodes researched) -- same soft-bar spirit as every prior era.
        "min_tier": research.era_tiers("classical")[-1],
        "min_score_label": "Strained",
    },
    # Milestone 11 -- the same three-part shape a fourth time. See
    # CLAUDE.md's Milestone 11 build notes for why "Strained" was kept
    # rather than raised, the same judgement every prior era has made.
    "medieval": {
        "to_era": "industrial",
        # The next population milestone up from Classical->Medieval's 40 --
        # log.POPULATION_MILESTONES[4], the point log.py's own text calls
        # "something closer to a town." A fitting hinge into an era whose
        # own sources describe global urban population rising from roughly
        # 3% (1800) to nearly 50% (2000) -- a settlement genuinely becoming
        # town-scale is exactly the real-world shift Industrial is meant to
        # dramatize.
        "min_population": 60,
        # The late Medieval research tier has to be UNLOCKED (two tier-7
        # nodes researched) -- same soft-bar spirit as every prior era.
        "min_tier": research.era_tiers("medieval")[-1],
        "min_score_label": "Strained",
    },
    # Milestone 12 -- the same three-part shape a fifth time. See
    # CLAUDE.md's Milestone 12 build notes for why "Strained" was kept
    # rather than raised, the same judgement every prior era has made.
    "industrial": {
        "to_era": "digital",
        # The last of log.POPULATION_MILESTONES -- 100, the point log.py's
        # own text calls "however this got built, it wasn't an accident."
        # Fitting for the era whose own sources describe cities crossing
        # into being the dominant, present-day human settlement pattern
        # (per the ECLAC source's own 70%-by-2050 figure).
        "min_population": 100,
        # The late Industrial research tier has to be UNLOCKED (two tier-9
        # nodes researched) -- same soft-bar spirit as every prior era.
        "min_tier": research.era_tiers("industrial")[-1],
        "min_score_label": "Strained",
    },
    # Milestone 13 -- the sixth and FINAL transition this arc needs. Same
    # three-part shape a sixth time, per every prior era's own notes that
    # the shape had already proven itself and didn't need re-litigating.
    # See CLAUDE.md's Milestone 13 build notes for why Space Age's own
    # content doesn't touch this shape at all, despite reusing it here.
    "digital": {
        "to_era": "space",
        # log.POPULATION_MILESTONES' new, final entry -- literally Dunbar's
        # own number (150), the point past which no one person can hold
        # everyone else in mind at once. A fitting hinge into the one era
        # whose sources describe leaving the planet that number was ever
        # measured on.
        "min_population": 150,
        # The late Digital research tier has to be UNLOCKED (two tier-11
        # nodes researched) -- same soft-bar spirit as every prior era.
        "min_tier": research.era_tiers("digital")[-1],
        "min_score_label": "Strained",
    },
    # Space Age intentionally has NO entry here -- it is the true, permanent
    # end of sim.ERA_ORDER, not merely "the next era hasn't shipped yet" the
    # way every earlier era's absence from this table was. next_era_for()
    # and missing_requirements() below already treat a missing entry as
    # "nothing more to reach" regardless of which of those two reasons is
    # why it's missing, so no new code was needed to make that distinction
    # real -- see CLAUDE.md's Milestone 13 build notes and
    # tests/test_space_age_era.py's own end-to-end test for the first time
    # this fallback path is exercised for a genuinely true ending.
}


def next_era_for(current_era):
    """The era `current_era` would transition into next, or None if this
    build has no transition defined from there yet (including the true
    end of the arc, Space Age, which never gets an entry)."""
    requirement = TRANSITION_REQUIREMENTS.get(current_era)
    return requirement["to_era"] if requirement else None


def transition_ready(state, tree, effects=None):
    """Whether `state.era`'s transition requirements are currently met.

    A pure function of state/tree, the same convention sustainability.py
    and research.py already follow — safe to call every render without
    side effects, and cheap to test directly against a hand-built state
    rather than needing to actually play a whole era to reach it.
    """
    return not missing_requirements(state, tree, effects)


def missing_requirements(state, tree, effects=None):
    """Human-readable reasons a transition isn't available yet.

    Doubles as `transition_ready()`'s own implementation and as what the
    UI would show for a not-yet-ready transition — the same "one
    description of why not, not two" pattern research.py's own
    `missing_requirements()` already established.
    """
    requirement = TRANSITION_REQUIREMENTS.get(state.era)
    if requirement is None:
        return ["Nothing more to reach from here yet."]

    reasons = []
    if state.population < requirement["min_population"]:
        reasons.append(
            f"Needs a population of at least {requirement['min_population']} "
            f"(currently {state.population})."
        )
    if not tree.tier_unlocked(requirement["min_tier"]):
        reasons.append("Needs more of this era's research discovered first.")

    label = sustainability.score_label(
        sustainability.score(state, effects), sustainability.is_hard_mode(state)
    )
    needed_label = requirement["min_score_label"]
    if sustainability.SCORE_LABELS.index(label) < sustainability.SCORE_LABELS.index(needed_label):
        reasons.append(f'The settlement needs to be at least "{needed_label}", not "{label}".')

    return reasons


# --- the beat itself ------------------------------------------------------
# Longer than an ordinary log.py entry — this is the "bigger narrative
# moment" the doc's Core system 4 asks for, not another one-line flavor
# entry. Keyed by (from_era, to_era) rather than just the destination, in
# case a later era ever has more than one place it could lead (not true
# today, but cheap to allow now rather than assume a single line forever).
TRANSITION_BEATS = {
    ("tribal", "agrarian"): (
        "The land around the settlement is no longer just where food is "
        "found — it's where food is grown. Somewhere in the last stretch "
        "of seasons, gathering gave way to tending, and the wandering the "
        "elders still tell stories about has quietly stopped. What began "
        "as a scatter of shelters around a fire now looks like it might "
        "stay exactly where it is."
    ),
    ("agrarian", "classical"): (
        "Nobody can name the day it happened, but the settlement stopped "
        "being a place where everyone's face is known and became a place "
        "that needs people whose job is simply to keep track — who tends "
        "which field, whose grain sits in which store, whose turn it is to "
        "walk the canal banks. The canals themselves came first, dug to "
        "carry water further than any one family could carry it by hand; "
        "the administrators came after, because a canal nobody is "
        "responsible for is just a ditch that floods when it shouldn't and "
        "runs dry when it matters. What is rising past the fields now "
        "looks less like a large village and more like a city."
    ),
    ("classical", "medieval"): (
        "The canals still run and the temple still keeps its records, but "
        "the city has started building things nobody asked for on behalf "
        "of any single harvest — drains that carry away what nobody wants "
        "to look at, banks raised as much against a flood that hasn't come "
        "yet as against anything that has. It costs the same stone and "
        "labor whether or not the season that would have needed it ever "
        "arrives, which is exactly why administrators alone were never "
        "going to be the ones to order it built. Meanwhile the toolworks "
        "no longer belongs to whoever happens to be free that day — a "
        "guild has claimed it, trains its own, and answers for the quality "
        "of what leaves under its own mark. Nobody put a single person in "
        "charge of any of this. Somewhere in the last stretch of seasons, "
        "the city started answering to itself."
    ),
    ("medieval", "industrial"): (
        "A chimney went up before anyone had really decided the skyline "
        "should change, and then there were more of them than anyone "
        "bothered to count. Whatever the guildhalls used to make by hand, "
        "somewhere is now making faster, louder, and in numbers the old "
        "workshops never could — and whatever those chimneys are putting "
        "into the air over the rooftops isn't going anywhere on its own. "
        "The city is growing quicker than it has ever grown before; it is "
        "also, for the first time, growing sicker while it does. Barely a "
        "thirtieth of the world lives anywhere like this yet. That will "
        "not stay true for long."
    ),
    ("industrial", "digital"): (
        "The smoke has mostly cleared, or at least moved somewhere it's "
        "measured instead of just breathed. What's changed more is how the "
        "city decides where it goes next — less by whoever gets there "
        "first and clears the ground, more by maps, counts, and people "
        "arguing in rooms about which block gets which kind of building. "
        "It hasn't stopped growing, and growing has its own quiet way of "
        "spreading a city thinner than it means to — new edges reaching "
        "further out than the people actually living in them would "
        "explain, if nobody was steering it. Whether this city ends up "
        "dense or sprawling from here isn't going to be an accident either "
        "way. Most of the world, by now, lives somewhere like this."
    ),
    ("digital", "space"): (
        "Nobody alive remembers deciding to leave — only the seasons it "
        "took to actually go. What launched first wasn't people, but the "
        "parts of a home: modules built to fold, seal, and hold against a "
        "vacuum this city has never once had to plan around before. By the "
        "time it arrives, it already carries the one lesson its six "
        "previous ages spent this long teaching it, plainly enough now to "
        "look almost obvious: that a place is only as good as what it can "
        "recover, not what it can produce. That lesson used to be about "
        "land, and land forgave slowly if you let it. Out here there is no "
        "slow forgiveness left to lean on — no wind to carry anything away, "
        "no ground to rest fallow, no elsewhere for a mistake to become "
        "someone else's problem. Whatever this settlement is now, sealed "
        "inside its rings, it is going to have to be its own weather, "
        "start to finish. A hundred and fifty of them made the crossing — "
        "past the point, fittingly, where any one of them could still hold "
        "everyone else in mind without help. Nobody has had to design a "
        "home for that many people with no outside left to escape a bad "
        "design into. Somebody is going to have to now."
    ),
}


def beat_text(from_era, to_era):
    return TRANSITION_BEATS.get(
        (from_era, to_era),
        f"The settlement has crossed into the {sim.ERA_LABEL.get(to_era, to_era)} era.",
    )


def attempt_transition(campaign):
    """The one entry point: advances `campaign` to its next era if (and
    only if) it is ready, logging a transition beat when it does.

    Returns True if a transition happened, False otherwise — the same
    boolean-refusal convention every other mutating engine call in this
    game already uses (`ResearchTree.research()`, `CityState.build()`,
    `Campaign.advance_to_era()` itself, ...).
    """
    from_era = campaign.state.era
    to_era = next_era_for(from_era)
    if to_era is None:
        return False

    effects = campaign.tree.effects()
    if not transition_ready(campaign.state, campaign.tree, effects):
        return False

    if not campaign.advance_to_era(to_era):
        # Defensive only: transition_ready() doesn't check `revisiting`
        # (it has no Campaign to check it on), but `advance_to_era()`
        # refuses mid-revisit on its own — so a ready settlement currently
        # being revisited correctly does nothing here rather than
        # transitioning the parked forward state out from under a replay.
        return False

    campaign.log.log_transition(campaign.state.season, to_era, beat_text(from_era, to_era))
    return True
