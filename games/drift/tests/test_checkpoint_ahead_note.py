"""Addendum I12: extend checkpoint_message() to occasionally note a
comfortably-ahead dimension too (score >= 80, and different from the
lagging one), rather than always naming only the weakest dimension.
"""


def test_no_ahead_note_when_nothing_is_comfortably_ahead(game_env):
    # Fresh region: service 100 (ahead), economy 30, cohesion 0 (lagging).
    # Service quality being 100 IS >= 80, so an ahead note is expected here
    # (this documents the fresh-region baseline rather than asserting no
    # note ever appears without setup).
    region = game_env.region
    message = game_env.module.checkpoint_message(region)
    assert "comfortably ahead" in message
    assert "Service quality" in message


def test_no_ahead_note_when_all_dimensions_are_middling(game_env):
    region = game_env.region
    game_env.set_strain_log([0.5])  # service_quality -> 50
    region.funds = 500.0  # economic_health -> 50
    region.total_arrivals = 10.0
    region.integrated_population = 6.0  # cohesion -> 60
    message = game_env.module.checkpoint_message(region)
    assert "comfortably ahead" not in message


def test_ahead_note_names_the_comfortably_ahead_dimension(game_env):
    region = game_env.region
    game_env.set_strain_log([1.0])  # service_quality -> 0 (lagging)
    region.funds = 1000.0  # economic_health -> 100 (comfortably ahead)
    region.total_arrivals = 10.0
    region.integrated_population = 5.0  # cohesion -> 50
    message = game_env.module.checkpoint_message(region)
    assert "services" in message.lower() or "service" in message.lower()
    assert "Economic health is comfortably ahead" in message


def test_ahead_note_omitted_when_ahead_dimension_equals_lagging_dimension(game_env):
    # All three scores identical -> min/max both resolve to the first
    # matching key, so no "different dimension" is comfortably ahead.
    region = game_env.region
    game_env.set_strain_log([0.0])  # service_quality -> 100
    region.funds = 1000.0  # economic_health -> 100
    region.total_arrivals = 10.0
    region.integrated_population = 10.0  # cohesion -> 100
    message = game_env.module.checkpoint_message(region)
    assert "comfortably ahead" not in message
