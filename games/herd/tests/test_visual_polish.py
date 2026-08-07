"""Milestone 7: visual pass — icons on decoupling measures, and a
decoupling-percentage summary line.
"""


def test_measure_name_includes_icon(game_env):
    text = game_env.elements["feed-name"].innerText
    assert game_env.module.DECOUPLING_MEASURES["feed"]["icon"] in text
    assert "Feed Additives" in text


def test_all_measures_get_named_with_icons(game_env):
    for measure in game_env.module.DECOUPLING_MEASURES:
        text = game_env.elements[f"{measure}-name"].innerText
        assert game_env.module.DECOUPLING_MEASURES[measure]["icon"] in text


def test_decoupling_summary_starts_at_zero(game_env):
    text = game_env.elements["decoupling-summary-display"].innerText
    assert "0%" in text


def test_decoupling_summary_reflects_investment(game_env):
    game_env.invest_decoupling("capture")
    text = game_env.elements["decoupling-summary-display"].innerText
    assert "10%" in text
