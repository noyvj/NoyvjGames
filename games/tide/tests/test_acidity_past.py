"""FY-2 (Tide D10): acidity from three seasons ago shown beside the current acidity."""


def test_text_before_three_seasons_are_banked(game_env):
    module = game_env.module
    module.state.acidity_history = [1.0, 2.0]
    assert "not yet played" in module.acidity_past_text()
    assert "2 of 3" in module.acidity_past_text()


def test_text_uses_the_third_most_recent_banked_value(game_env):
    module = game_env.module
    module.state.acidity_history = [9.0, 1.0, 2.0, 3.0]
    module.state.acidity = 4.5
    text = module.acidity_past_text()
    assert "acidity 1.0" in text and "now 4.5" in text and "up 3.5" in text


def test_text_reports_down_and_unchanged(game_env):
    module = game_env.module
    module.state.acidity_history = [5.0, 5.0, 5.0]
    module.state.acidity = 3.0
    assert "down 2.0" in module.acidity_past_text()
    module.state.acidity = 5.02
    assert "unchanged" in module.acidity_past_text()


def test_render_writes_the_line(game_env):
    module = game_env.module
    module.state.acidity_history = [1.0, 2.0, 3.0]
    module.state.acidity = 3.0
    module.render()
    assert game_env.elements["acidity-past-display"].innerText.startswith("Three seasons ago: acidity 1.0")


def test_nothing_is_saved_for_it(game_env):
    module = game_env.module
    assert not any("past" in k for k in module.get_state())
