"""I8: replace the coda's three bare meter bars with a clearer
before/after comparison -- a thin marker showing today's value, the fill
bar keeping the projected (generations-from-now) value it always had,
and a text line spelling both numbers out.
"""


def _reach_coda(game_env):
    """Gets at least one person integrated (so the coda becomes
    available) and opens it."""
    game_env.invest("services")
    for _ in range(5):
        game_env.advance_round()
    assert game_env.region.has_long_horizon_story()
    game_env.toggle_coda()


def test_before_marker_reflects_current_value(game_env):
    _reach_coda(game_env)
    region = game_env.region
    marker = game_env.elements["coda-service-quality-before-marker"]
    assert marker.style.left == f"{region.service_quality():.0f}%"


def test_bar_still_reflects_projected_value(game_env):
    _reach_coda(game_env)
    region = game_env.region
    bar = game_env.elements["coda-service-quality-bar"]
    assert bar.style.width == f"{region.projected_service_quality():.0f}%"


def test_values_line_shows_both_numbers(game_env):
    _reach_coda(game_env)
    region = game_env.region
    values_text = game_env.elements["coda-service-quality-values"].innerText
    assert f"{region.service_quality():.0f}" in values_text
    assert f"{region.projected_service_quality():.0f}" in values_text
    assert "→" in values_text


def test_all_three_dimensions_get_a_comparison(game_env):
    _reach_coda(game_env)
    for dimension in ("service-quality", "economic-health", "social-cohesion"):
        assert game_env.elements[f"coda-{dimension}-values"].innerText != ""
        assert game_env.elements[f"coda-{dimension}-before-marker"].style.left != ""
