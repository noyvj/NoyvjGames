"""Milestone 7: visual pass — icons on investment categories and a
temperature meter bar.
"""


def test_category_name_includes_icon(game_env):
    text = game_env.elements["output-name"].innerText
    assert game_env.module.CATEGORY_ICON["output"] in text
    assert "Output" in text


def test_all_categories_get_named_with_icons(game_env):
    for category in game_env.module.CATEGORIES:
        text = game_env.elements[f"{category}-name"].innerText
        assert game_env.module.CATEGORY_ICON[category] in text


def test_temperature_bar_starts_empty(game_env):
    assert game_env.elements["temperature-bar"].style.width == "0%"


def test_temperature_bar_fills_as_temperature_rises(game_env):
    game_env.advance_round()
    game_env.module.render()
    assert game_env.elements["temperature-bar"].style.width != "0%"


def test_temperature_bar_caps_at_full(game_env):
    game_env.region.temperature = 999.0
    game_env.module.render()
    assert game_env.elements["temperature-bar"].style.width == "100%"
