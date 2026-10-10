"""G-12: the board-room table of all regions with sortable columns, sparklines and Region D greyed."""


def _order(m):
    return [row["label"] for row in m.sorted_board_rows()]


def _play(game_env, rounds=6):
    for _ in range(rounds):
        game_env.advance_round()


def test_default_order_is_a_b_c_without_d(game_env):
    assert _order(game_env.module) == ["A", "B", "C"]


def test_region_d_joins_greyed_and_last_once_revealed(game_env):
    m = game_env.module
    game_env.toggle_worst_case_region()
    assert _order(m) == ["A", "B", "C", "D"]
    html = game_env.elements["board-body"].innerHTML
    assert html.count("board-row--grey") == 1
    assert "Region D (worst case)" in html
    assert "—" in html  # no best-ever for D


def test_region_d_stays_last_whatever_the_sort(game_env):
    m = game_env.module
    game_env.toggle_worst_case_region()
    _play(game_env)
    for key, _label in m.BOARD_COLUMNS:
        m.set_board_sort(key)
        assert _order(m)[-1] == "D", key
        m.set_board_sort(key)
        assert _order(m)[-1] == "D", key


def test_sorting_by_funds_and_back(game_env):
    m = game_env.module
    m.region_b.funds = 900
    m.region.funds = 100
    m.region_c.funds = 500
    m.render()
    game_env.elements["board-sort-funds"].dispatch("click")
    assert _order(m) == ["A", "C", "B"]
    game_env.elements["board-sort-funds"].dispatch("click")
    assert _order(m) == ["B", "C", "A"]


def test_aria_sort_and_arrow_follow_the_choice(game_env):
    m = game_env.module
    game_env.elements["board-sort-temp"].dispatch("click")
    assert game_env.elements["board-th-temp"].attributes["aria-sort"] == "ascending"
    assert game_env.elements["board-th-region"].attributes["aria-sort"] == "none"
    assert game_env.elements["board-sort-temp"].innerText.endswith("▲")
    game_env.elements["board-sort-temp"].dispatch("click")
    assert game_env.elements["board-th-temp"].attributes["aria-sort"] == "descending"
    assert game_env.elements["board-sort-temp"].innerText.endswith("▼")
    assert "descending" in game_env.elements["board-caption"].innerText
    assert m.board_sort == "temp"


def test_unknown_sort_key_is_ignored(game_env):
    m = game_env.module
    assert m.set_board_sort("nope") is False
    assert m.board_sort == "region"


def test_values_match_the_regions(game_env):
    m = game_env.module
    _play(game_env, 12)
    rows = {row["label"]: row for row in m.board_rows()}
    assert rows["A"]["temp"] == m.region.temperature
    assert rows["B"]["text"]["temp"] == m.deg(m.region_b.temperature, plus=True)
    assert rows["C"]["text"]["damp"] == f"{m.region_c.feedback_dampening_fraction() * 100:.0f}%"
    assert rows["A"]["best"] == m.climate_archive["A"]["best_saved"]


def test_since_column_says_none_yet_before_a_tipping_event(game_env):
    m = game_env.module
    assert m.board_rows()[0]["text"]["since"] == "0 (none yet)"
    _play(game_env, 12)
    assert "none yet" not in m.board_rows()[0]["text"]["since"]


def test_sparkline_appears_after_two_rounds(game_env):
    html = game_env.elements["board-body"].innerHTML
    assert "board-spark" not in html and "after round 2" in html
    _play(game_env, 3)
    html = game_env.elements["board-body"].innerHTML
    assert html.count("board-spark-line") == 3
    assert "role=\"img\"" in html


def test_ties_keep_region_order(game_env):
    m = game_env.module
    m.set_board_sort("funds")
    assert _order(m) == ["A", "B", "C"]


def test_temperature_unit_flows_into_the_table(game_env):
    m = game_env.module
    _play(game_env, 2)
    m.set_temp_unit("f")
    m.render()
    assert "°F" in game_env.elements["board-body"].innerHTML


def test_text_helper_escapes_markup(game_env):
    assert game_env.module._escape("<b>&") == "&lt;b&gt;&amp;"
