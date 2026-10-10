"""Round-7 pass: the city skyline strip (GC-8)."""
from .test_career import _play
from .test_round7_trend import _tick


def test_skyline_is_on_by_default_and_has_a_caption(game_env):
    game_env.module.render()
    strip = game_env.elements["skyline-strip"]
    assert strip.hidden is False
    assert game_env.elements["pref-skyline"].checked is True
    assert "0 of 16 buildings lit" in game_env.elements["skyline-caption"].innerText
    assert "<svg" in game_env.elements["skyline-graphic"].innerHTML


def test_checkbox_hides_the_strip(game_env):
    _tick(game_env, "pref-skyline", False)
    assert game_env.elements["skyline-strip"].hidden is True
    assert game_env.module.prefs["skyline"] is False
    _tick(game_env, "pref-skyline", True)
    assert game_env.elements["skyline-strip"].hidden is False


def test_buildings_light_with_coverage(game_env):
    g = game_env.module
    s = game_env.state
    assert g.skyline_status()["lit"] == 0
    s.plant_counts["coal"] = 3  # 60 of demand 100
    status = g.skyline_status()
    assert abs(status["coverage"] - 0.6) < 1e-9 and status["lit"] == round(16 * 0.6)
    s.plant_counts["nuclear"] = 2
    assert g.skyline_status()["lit"] == 16  # covered, never more than all of them


def test_lit_buildings_have_windows_and_dark_ones_do_not(game_env):
    g = game_env.module
    game_env.state.plant_counts["coal"] = 3
    svg = g.skyline_svg(g.skyline_status())
    lit = g.skyline_status()["lit"]
    assert svg.count("sky-building--lit") == lit and svg.count("sky-building--dark") == 16 - lit
    assert svg.count('class="sky-window"') > 0
    assert "sky-window--dim" not in svg and "skyline-svg--flicker" not in svg


def test_a_brownout_round_dims_and_flickers_with_words(game_env):
    g = game_env.module
    game_env.state.plant_counts["coal"] = 6
    game_env.state.last_event = {"type": "brownout", "severity": 0.2, "revenue_loss": 10}
    status = g.skyline_status()
    assert status["brownout"] is True
    svg = g.skyline_svg(status)
    assert "sky-window--dim" in svg and "skyline-svg--flicker" in svg
    assert "Lights dimmed by last round's disruption" in g.skyline_caption(status)
    game_env.state.last_event = None
    assert g.skyline_status()["brownout"] is False


def test_haze_follows_the_emissions_meter(game_env):
    g = game_env.module
    s = game_env.state
    assert g.skyline_haze_word(g.skyline_status()["haze"]) == "clear air"
    s.emissions = g.EMISSIONS_METER_MAX * 0.2
    assert "light haze" in g.skyline_caption(g.skyline_status())
    s.emissions = g.EMISSIONS_METER_MAX * 0.5
    assert "thick haze" in g.skyline_caption(g.skyline_status())
    s.emissions = g.EMISSIONS_METER_MAX * 5
    status = g.skyline_status()
    assert status["haze"] == 1.0 and "heavy smog" in g.skyline_caption(status)
    assert f"opacity:{g.SKYLINE_MAX_HAZE:.2f}" in g.skyline_svg(status)


def test_the_svg_has_a_text_alternative(game_env):
    g = game_env.module
    svg = g.skyline_svg(g.skyline_status())
    assert 'role="img"' in svg and "aria-label=\"City: 0 of 16 buildings lit" in svg


def test_every_building_fits_inside_the_picture(game_env):
    g = game_env.module
    for x, width, height in g.SKYLINE_BUILDINGS:
        assert x >= 0 and x + width <= g.SKYLINE_WIDTH and 0 < height <= g.SKYLINE_HEIGHT


def test_skyline_updates_each_round_and_never_touches_the_save(game_env):
    g = game_env.module
    before = g.get_state()
    game_env.state.plant_counts["gas"] = 7
    _play(game_env, 2)
    g.render()
    assert "buildings lit" in game_env.elements["skyline-caption"].innerText
    assert "skyline" not in " ".join(g.get_state().keys())
    del before
