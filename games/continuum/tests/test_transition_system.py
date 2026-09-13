"""Milestone 7 — the era-transition beat system.

Tests the generic framework directly against `save.Campaign`/`sim.CityState`
/`research.ResearchTree` objects — no DOM, no game.py involvement, per this
milestone's own scope note in transition.py: nothing is wired into the UI
yet, so there's nothing to click. What's tested is exactly what the
milestone table asks for: "transition-trigger logic."
"""

import research
import save
import sim
import sustainability
import transition


def fresh_campaign():
    return save.Campaign(sim.CityState(), research.build_tree())


def make_ready(campaign):
    """Pushes a fresh Tribal campaign past every Tribal->Agrarian
    requirement, without touching anything transition.py doesn't check."""
    campaign.state.resources["knowledge"] = 100.0
    campaign.tree.research("fire_keeping", campaign.state.resources)
    campaign.tree.research("foraging_lore", campaign.state.resources)
    campaign.state.population = 15
    return campaign


# --- next_era_for -----------------------------------------------------
def test_next_era_for_tribal_is_agrarian():
    assert transition.next_era_for("tribal") == "agrarian"


def test_next_era_for_an_era_with_no_requirements_yet_is_none():
    eras_with_requirements = set(transition.TRANSITION_REQUIREMENTS.keys())
    for era in sim.ERA_ORDER:
        if era in eras_with_requirements:
            continue
        assert transition.next_era_for(era) is None


# --- readiness -----------------------------------------------------------
def test_a_fresh_settlement_is_not_ready():
    campaign = fresh_campaign()
    effects = campaign.tree.effects()
    assert transition.transition_ready(campaign.state, campaign.tree, effects) is False


def test_missing_requirements_names_population_when_too_small():
    campaign = fresh_campaign()
    reasons = transition.missing_requirements(campaign.state, campaign.tree, campaign.tree.effects())
    assert any("population" in r.lower() for r in reasons)


def test_missing_requirements_names_research_when_tier_locked():
    campaign = fresh_campaign()
    campaign.state.population = 15  # population requirement alone satisfied
    reasons = transition.missing_requirements(campaign.state, campaign.tree, campaign.tree.effects())
    assert any("research" in r.lower() for r in reasons)


def test_missing_requirements_names_the_score_band_when_too_low():
    campaign = fresh_campaign()
    campaign.state.resources["knowledge"] = 100.0
    campaign.tree.research("fire_keeping", campaign.state.resources)
    campaign.tree.research("foraging_lore", campaign.state.resources)
    campaign.state.population = 15
    # Wreck the score without touching population/research.
    campaign.state.fed_fraction = 0.0
    campaign.state.land_health = 0.15
    campaign.state.resources["food"] = 0.0
    campaign.state.resources["tools"] = 0.0

    effects = campaign.tree.effects()
    label = sustainability.score_label(sustainability.score(campaign.state, effects))
    assert sustainability.SCORE_LABELS.index(label) < sustainability.SCORE_LABELS.index("Strained")

    reasons = transition.missing_requirements(campaign.state, campaign.tree, effects)
    assert any("Strained" in r for r in reasons)


def test_ready_once_every_requirement_is_met():
    campaign = make_ready(fresh_campaign())
    effects = campaign.tree.effects()
    assert transition.transition_ready(campaign.state, campaign.tree, effects) is True
    assert transition.missing_requirements(campaign.state, campaign.tree, effects) == []


def test_an_era_with_no_table_entry_reports_nothing_more_to_reach():
    campaign = fresh_campaign()
    campaign.state.era = "space"  # no transition defined from here
    reasons = transition.missing_requirements(campaign.state, campaign.tree, campaign.tree.effects())
    assert reasons == ["Nothing more to reach from here yet."]
    assert transition.transition_ready(campaign.state, campaign.tree, campaign.tree.effects()) is False


# --- attempt_transition: the mutating entry point -------------------------
def test_attempt_transition_does_nothing_when_not_ready():
    campaign = fresh_campaign()
    assert transition.attempt_transition(campaign) is False
    assert campaign.state.era == "tribal"
    assert campaign.era_snapshots == {}
    assert campaign.log.entries == []


def test_attempt_transition_advances_era_and_logs_a_beat():
    campaign = make_ready(fresh_campaign())

    assert transition.attempt_transition(campaign) is True

    assert campaign.state.era == "agrarian"
    assert campaign.tree.current_era == "agrarian"
    assert campaign.furthest_era == "agrarian"
    assert "tribal" in campaign.era_snapshots

    transitions = [e for e in campaign.log.entries if e.kind == "transition"]
    assert len(transitions) == 1
    assert transitions[0].text == transition.TRANSITION_BEATS[("tribal", "agrarian")]
    assert transitions[0].era == "agrarian"


def test_attempt_transition_calls_advance_to_era_for_real():
    """Explicitly the thing Milestone 7 is supposed to do, per CLAUDE.md:
    'this is what finally calls Campaign.advance_to_era()'."""
    campaign = make_ready(fresh_campaign())
    snapshot_before = dict(campaign.era_snapshots)

    transition.attempt_transition(campaign)

    assert snapshot_before == {}
    assert set(campaign.era_snapshots.keys()) == {"tribal"}
    assert campaign.era_snapshots["tribal"]["era"] == "tribal"


def test_attempt_transition_a_second_time_does_nothing_yet():
    """Agrarian has no requirements table entry yet (Milestone 8's job),
    so a settlement that just arrived there can't be swept straight into a
    third era it also has no content for."""
    campaign = make_ready(fresh_campaign())
    transition.attempt_transition(campaign)

    assert transition.attempt_transition(campaign) is False
    assert campaign.state.era == "agrarian"
    assert len([e for e in campaign.log.entries if e.kind == "transition"]) == 1


def test_attempt_transition_refuses_mid_revisit():
    campaign = make_ready(fresh_campaign())
    assert transition.attempt_transition(campaign) is True  # tribal -> agrarian

    # Re-ready the (now Agrarian) settlement for a transition that doesn't
    # exist yet, and revisit the completed Tribal era.
    assert campaign.enter_revisit("tribal") is True
    assert campaign.revisiting == "tribal"

    # Even if the parked Tribal snapshot still satisfies the Tribal->
    # Agrarian requirements, entering a real transition mid-revisit must
    # be refused -- it would yank the parked forward state out from under
    # the replay.
    result = transition.attempt_transition(campaign)
    assert result is False
    assert campaign.revisiting == "tribal"


def test_beat_text_falls_back_to_a_generic_line_for_an_undefined_pair():
    """Digital -> Space Age has no bespoke beat yet (that's a later
    milestone's job, and explicitly out of this one's scope) -- updated
    from Industrial -> Digital now that Milestone 12 gave that pair real
    prose, the same "next undefined pair" update Milestones 9-11 already
    made once each to this same test."""
    text = transition.beat_text("digital", "space")
    assert text == "The settlement has crossed into the Space Age era."


# --- Chronicle.log_transition (log.py's half of this seam) ---------------
def test_log_transition_adds_a_transition_kind_entry():
    campaign = fresh_campaign()
    campaign.log.log_transition(campaign.state.season, "agrarian", "A new era begins.")
    assert len(campaign.log.entries) == 1
    assert campaign.log.entries[0].kind == "transition"
    assert campaign.log.entries[0].text == "A new era begins."


def test_transition_beat_survives_a_save_round_trip():
    campaign = make_ready(fresh_campaign())
    transition.attempt_transition(campaign)

    data = campaign.to_dict()
    fresh = fresh_campaign()
    assert fresh.load_dict(data) is True

    transitions = [e for e in fresh.log.entries if e.kind == "transition"]
    assert len(transitions) == 1
    assert fresh.state.era == "agrarian"
    assert fresh.era_snapshots.get("tribal", {}).get("era") == "tribal"
