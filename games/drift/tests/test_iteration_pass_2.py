"""Iteration Pass 2: long-horizon outcomes coda — a player-triggered
epilogue projecting the currently-integrated population's descendants
forward a few generations, framed institutionally (workforce,
community roles, regional contribution) per this game's sensitivity
note in CLAUDE.md's Tech notes section. The three-bar wellbeing
dashboard carries into the coda as a projected, visibly improved
continuation of the same numbers, not a disconnected screen.
"""


def test_no_long_horizon_story_before_any_integration(game_env):
    assert game_env.region.has_long_horizon_story() is False


def test_coda_button_hidden_before_any_integration(game_env):
    game_env.module.render()
    assert game_env.elements["coda-button"].hidden is True


def test_has_long_horizon_story_once_someone_is_integrated(game_env):
    game_env.region.integrated_population = 5.0
    assert game_env.region.has_long_horizon_story() is True


def test_coda_button_visible_once_someone_is_integrated(game_env):
    game_env.region.integrated_population = 5.0
    game_env.module.render()
    assert game_env.elements["coda-button"].hidden is False


def test_coda_section_hidden_by_default(game_env):
    game_env.region.integrated_population = 5.0
    game_env.module.render()
    assert game_env.elements["coda-section"].hidden is True


def test_coda_button_toggles_visibility(game_env):
    game_env.region.integrated_population = 5.0
    game_env.module.render()
    game_env.toggle_coda()
    assert game_env.elements["coda-section"].hidden is False
    game_env.toggle_coda()
    assert game_env.elements["coda-section"].hidden is True


def test_coda_stays_hidden_when_toggled_without_a_story(game_env):
    # No integration yet -- toggling shouldn't reveal an empty coda.
    game_env.toggle_coda()
    assert game_env.elements["coda-section"].hidden is True


def test_projected_generational_contribution_exceeds_current(game_env):
    game_env.region.integrated_population = 10.0
    assert game_env.region.integration_contribution() > 0.0
    assert game_env.region.projected_generational_contribution() > game_env.region.integration_contribution()


def test_projected_service_quality_moves_toward_ceiling(game_env):
    game_env.region.strain_log = [0.5, 0.5]  # service_quality() = 50
    current = game_env.region.service_quality()
    projected = game_env.region.projected_service_quality()
    assert projected > current
    assert projected <= 100.0


def test_projected_social_cohesion_moves_toward_ceiling(game_env):
    game_env.region.total_arrivals = 100.0
    game_env.region.integrated_population = 20.0  # cohesion = 20
    current = game_env.region.social_cohesion()
    projected = game_env.region.projected_social_cohesion()
    assert projected > current
    assert projected <= 100.0


def test_projected_economic_health_reflects_compounded_contribution(game_env):
    game_env.region.integrated_population = 20.0
    game_env.region.total_arrivals = 20.0
    current = game_env.region.economic_health()
    projected = game_env.region.projected_economic_health()
    assert projected >= current
    assert projected <= 100.0


def test_projected_wellbeing_at_least_current_wellbeing(game_env):
    game_env.region.integrated_population = 20.0
    game_env.region.total_arrivals = 30.0
    game_env.region.strain_log = [0.3]
    assert game_env.region.projected_wellbeing_score() >= game_env.region.wellbeing_score()


def test_coda_message_is_institutional_not_personal(game_env):
    game_env.region.integrated_population = 15.0
    message = game_env.module.long_horizon_coda_message(game_env.region)
    assert "workforce" in message.lower() or "institutions" in message.lower()


def test_render_populates_coda_message_when_visible(game_env):
    game_env.region.integrated_population = 15.0
    game_env.module.render()
    game_env.toggle_coda()
    assert len(game_env.elements["coda-message-display"].innerText) > 0


def test_render_populates_coda_wellbeing_bars_when_visible(game_env):
    game_env.region.integrated_population = 15.0
    game_env.module.render()
    game_env.toggle_coda()
    assert game_env.elements["coda-service-quality-bar"].style.width != "0%"
    assert "Projected" in game_env.elements["coda-wellbeing-display"].innerText
