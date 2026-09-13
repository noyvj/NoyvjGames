"""Phase 5 — the state -> visual data contract (visual.py).

Covers the one thing this phase's Python side actually needs to prove:
visual_state()/get_visual_state() is a correct, JSON-safe, era-aware
snapshot of the settlement — never rendering itself, since the Three.js
layer that consumes this data can't reasonably be unit tested in this
stack (see CLAUDE.md's Phase 5 build notes for the live-verification
story instead).
"""

import json

import sim
import sustainability
import visual


def test_visual_state_is_json_serialisable(game_env):
    data = game_env.module.get_visual_state()
    # Round-tripping through json.dumps/loads is the same JSON-safety bar
    # save.py's get_state() is held to — nothing here may be a live object.
    json.loads(json.dumps(data))


def test_fresh_tribal_settlement_reports_expected_fields(game_env):
    state = game_env.state
    data = game_env.module.get_visual_state()

    assert data["era"] == "tribal"
    assert data["era_index"] == 0
    assert data["era_label"] == "Tribal"
    assert data["season"] == state.season
    assert data["population"] == state.population
    assert data["housing_capacity"] == state.housing_capacity(sim.NEUTRAL_EFFECTS)
    assert data["land_health"] == 1.0
    assert data["pollution"] == 0.0
    assert data["sprawl"] == 0.0
    # Not reached yet — the ratios read "not applicable" as None, not 0.0.
    assert data["habitat_layout_ratio"] is None
    assert data["public_works_coverage_ratio"] is None


def test_buildings_are_scoped_to_the_current_era(game_env):
    data = game_env.module.get_visual_state()
    assert set(data["buildings"].keys()) == set(sim.buildings_for_era("tribal"))
    # Buildings from eras not yet reached must not leak in, even as zeros —
    # the JS side should never have to know sim.BUILDINGS' full flat list.
    assert "farmland" not in data["buildings"]
    assert "habitat_rings" not in data["buildings"]


def test_building_counts_match_live_state(game_env):
    game_env.build("shelter")
    data = game_env.module.get_visual_state()
    assert data["buildings"]["shelter"] == game_env.state.buildings["shelter"]


def test_score_label_and_weakest_component_match_sustainability_directly(game_env):
    state = game_env.state
    effects = sim.NEUTRAL_EFFECTS
    data = game_env.module.get_visual_state()

    assert data["score"] == sustainability.score(state, effects)
    assert data["score_label"] == sustainability.score_label(data["score"])
    assert data["weakest_component"] == sustainability.weakest_component(state, effects)


def test_population_and_season_update_after_advancing(game_env):
    game_env.advance_season()
    data = game_env.module.get_visual_state()
    state = game_env.state
    assert data["season"] == state.season
    assert data["population"] == state.population


def test_public_works_coverage_ratio_is_none_before_medieval_and_a_ratio_after(game_env):
    state = game_env.state

    state.era = "classical"
    data = visual.visual_state(state, sim.NEUTRAL_EFFECTS)
    assert data["public_works_coverage_ratio"] is None

    state.era = "medieval"
    state.buildings["public_works"] = 2
    data = visual.visual_state(state, sim.NEUTRAL_EFFECTS)
    assert data["public_works_coverage_ratio"] is not None
    assert 0.0 <= data["public_works_coverage_ratio"] <= 1.0


def test_habitat_layout_ratio_is_none_before_space_age_and_a_ratio_after(game_env):
    state = game_env.state

    state.era = "digital"
    data = visual.visual_state(state, sim.NEUTRAL_EFFECTS)
    assert data["habitat_layout_ratio"] is None

    state.era = "space"
    state.buildings["habitat_rings"] = 3
    state.allocation["architects"] = 2
    data = visual.visual_state(state, sim.NEUTRAL_EFFECTS)
    assert data["habitat_layout_ratio"] is not None
    assert 0.0 <= data["habitat_layout_ratio"] <= 1.0


def test_pollution_and_sprawl_are_reported_directly_from_state(game_env):
    state = game_env.state
    state.pollution = 0.42
    state.sprawl = 0.17
    data = visual.visual_state(state, sim.NEUTRAL_EFFECTS)
    assert data["pollution"] == 0.42
    assert data["sprawl"] == 0.17


def test_visual_state_never_mutates_the_state_it_reads(game_env):
    import copy

    state = game_env.state
    before = copy.deepcopy(state.__dict__)
    visual.visual_state(state, sim.NEUTRAL_EFFECTS)
    after = copy.deepcopy(state.__dict__)
    assert before == after


def test_get_visual_state_reflects_a_real_era_transition(game_env):
    """End-to-end through game.py's own wrapper, not just visual.py
    directly -- confirms the seam game.py wires up (current_effects() +
    the live module-level state/tree) actually reaches visual.py. Reuses
    the same Tribal->Agrarian push test_agrarian_era.py's own
    push_to_agrarian_ready() helper establishes, since this test only
    cares that a real transition is visible through get_visual_state(),
    not about re-proving the transition system itself."""
    import transition

    state = game_env.state
    tree = game_env.module.tree
    state.resources["knowledge"] = 100.0
    tree.research("fire_keeping", state.resources)
    tree.research("foraging_lore", state.resources)
    state.population = 15

    before = game_env.module.get_visual_state()
    assert before["era"] == "tribal"
    assert "farmland" not in before["buildings"]

    assert transition.attempt_transition(game_env.module.campaign) is True

    after = game_env.module.get_visual_state()
    assert after["era"] == "agrarian"
    assert "farmland" in after["buildings"]
    assert after["population"] == game_env.state.population
