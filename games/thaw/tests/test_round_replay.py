"""G-3: the round-replay scrubber."""


def _slide(game_env, value):
    game_env.elements["replay-slider"].value = str(value)
    game_env.elements["replay-slider"].dispatch("input")


def test_empty_before_the_first_round(game_env):
    assert "Play a round" in game_env.elements["replay-label"].innerText
    assert game_env.elements["replay-chart"].innerHTML == ""
    assert game_env.elements["replay-slider"].disabled is True


def test_follows_the_latest_round_until_moved(game_env):
    for _ in range(4):
        game_env.advance_round()
    assert game_env.elements["replay-slider"].value == "4"
    assert game_env.elements["replay-slider"].max == "4"
    assert game_env.elements["replay-label"].innerText == "Round 4 of 4"


def test_sliding_back_shows_that_rounds_numbers(game_env):
    m = game_env.module
    for _ in range(6):
        game_env.advance_round()
    _slide(game_env, 2)
    assert game_env.elements["replay-label"].innerText == "Round 2 of 6"
    html = game_env.elements["replay-readouts"].innerHTML
    assert m.deg(m.region.temperature_history[1], plus=True) in html
    assert "Region A" in html and "Region B" in html and "Region C" in html


def test_staying_back_while_new_rounds_arrive(game_env):
    for _ in range(5):
        game_env.advance_round()
    _slide(game_env, 2)
    game_env.advance_round()
    assert game_env.elements["replay-slider"].value == "2"
    assert game_env.elements["replay-slider"].max == "6"
    _slide(game_env, 6)
    game_env.advance_round()
    assert game_env.elements["replay-slider"].value == "7"


def test_status_flips_to_melting_at_the_threshold(game_env):
    m = game_env.module
    for _ in range(12):
        game_env.advance_round()
    _slide(game_env, 3)
    assert "stable" in game_env.elements["replay-readouts"].innerHTML.split("<li>")[1]
    _slide(game_env, 12)
    assert "melting" in game_env.elements["replay-readouts"].innerHTML.split("<li>")[1]
    assert m.replay_state_at(m.region, 12)[1] == "melting"


def test_log_entries_are_pinned_to_their_round(game_env):
    m = game_env.module
    for _ in range(12):
        game_env.advance_round()
    melt_round = m.region.melt_started_round
    _slide(game_env, melt_round)
    assert "began melting" in game_env.elements["replay-log"].innerHTML
    _slide(game_env, 2)
    assert "Nothing was logged" in game_env.elements["replay-log"].innerHTML
    chart = game_env.elements["replay-chart"].innerHTML
    assert "replay-mark" in chart and "replay-cursor" in chart


def test_chart_has_a_line_per_region_and_a_text_alternative(game_env):
    for _ in range(3):
        game_env.advance_round()
    chart = game_env.elements["replay-chart"].innerHTML
    for key in "abc":
        assert f"replay-line--{key}" in chart
    assert 'role="img"' in chart and "cursor is at round 3" in chart


def test_step_buttons_clamp_at_the_ends(game_env):
    for _ in range(4):
        game_env.advance_round()
    game_env.elements["replay-first"].dispatch("click")
    assert game_env.elements["replay-slider"].value == "1"
    game_env.elements["replay-back"].dispatch("click")
    assert game_env.elements["replay-slider"].value == "1"
    game_env.elements["replay-forward"].dispatch("click")
    assert game_env.elements["replay-slider"].value == "2"
    game_env.elements["replay-last"].dispatch("click")
    assert game_env.elements["replay-slider"].value == "4"
    game_env.elements["replay-forward"].dispatch("click")
    assert game_env.elements["replay-slider"].value == "4"


def test_bad_slider_values_are_clamped(game_env):
    m = game_env.module
    for _ in range(3):
        game_env.advance_round()
    for raw in ("", "abc", "-5", "9999", "nan"):
        game_env.elements["replay-slider"].value = raw
        assert 1 <= m.replay_selected() <= 3


def test_replay_never_changes_the_game(game_env):
    m = game_env.module
    for _ in range(5):
        game_env.advance_round()
    before = m.get_state()
    _slide(game_env, 1)
    game_env.elements["replay-last"].dispatch("click")
    assert m.get_state() == before


def test_region_d_row_appears_when_revealed(game_env):
    for _ in range(3):
        game_env.advance_round()
    assert "Region D" not in game_env.elements["replay-readouts"].innerHTML
    game_env.toggle_worst_case_region()
    assert "Region D" in game_env.elements["replay-readouts"].innerHTML
