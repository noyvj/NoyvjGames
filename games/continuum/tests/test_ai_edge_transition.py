"""Edge-case tests for transition.py.

Tests limits of public functions: missing eras, boundary populations,
score thresholds, and fallback text paths. Uses game_env fixture to
build state objects exactly as the rest of the test suite does.
"""

import transition


def test_next_era_for_known_era(game_env):
    """next_era_for returns the correct target era for a valid input."""
    assert transition.next_era_for("tribal") == "agrarian"
    assert transition.next_era_for("agrarian") == "classical"


def test_next_era_for_last_era_returns_none(game_env):
    """next_era_for returns None when there is no defined transition."""
    # Relay Age is the current end of the arc and has no entry in TRANSITION_REQUIREMENTS.
    assert transition.next_era_for("relay") is None


def test_next_era_for_empty_string_returns_none(game_env):
    """next_era_for returns None for empty or invalid inputs."""
    assert transition.next_era_for("") is None
    assert transition.next_era_for("nonexistent_era") is None


def test_missing_requirements_population_boundary(game_env):
    """missing_requirements correctly flags population just below threshold."""
    state = game_env.state
    tree = game_env.module.tree

    # Set era to tribal, which requires min_population of 15.
    state.era = "tribal"

    # Zero population should definitely fail.
    state.population = 0
    reasons = transition.missing_requirements(state, tree)
    assert any("population" in r.lower() for r in reasons)

    # Smallest allowed value (exactly the threshold) should pass the population check.
    state.population = 15
    reasons = transition.missing_requirements(state, tree)
    assert not any("population" in r.lower() for r in reasons)


def test_missing_requirements_tier_gate(game_env):
    """missing_requirements correctly flags missing research tier."""
    state = game_env.state
    tree = game_env.module.tree

    state.era = "tribal"
    state.population = 100  # Satisfies population requirement

    reasons = transition.missing_requirements(state, tree)
    assert any("research" in r.lower() for r in reasons)


def test_transition_ready_boundary_population(game_env):
    """transition_ready returns False when population is at zero."""
    state = game_env.state
    tree = game_env.module.tree
    state.era = "tribal"
    state.population = 0
    assert transition.transition_ready(state, tree) is False


def test_beat_text_known_transition(game_env):
    """beat_text returns the specific narrative text for a known transition."""
    text = transition.beat_text("tribal", "agrarian")
    assert len(text) > 50
    assert "food" in text.lower() or "grown" in text.lower()


def test_beat_text_unknown_transition_fallback(game_env):
    """beat_text returns a generic fallback string for unknown transitions."""
    text = transition.beat_text("unknown_era", "another_era")
    assert "crossed into the" in text.lower()

    # Empty strings should also hit the fallback path.
    text_empty = transition.beat_text("", "")
    assert "crossed into the" in text_empty.lower()
