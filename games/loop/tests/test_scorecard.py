"""H19: the circular economy scorecard (every benchmark at once)."""

import pytest


def test_one_row_per_benchmark_plus_the_overall_figure(game_env):
    m = game_env.module
    rows = m.scorecard_rows(0.2)
    assert len(rows) == 1 + len(m.SECTOR_COMPARISONS)
    assert rows[0]["label"] == "overall real-world average"
    assert [r["label"] for r in rows[1:]] == [label for label, _ in m.SECTOR_COMPARISONS]


def test_gap_and_verdict_above_below_and_level(game_env):
    m = game_env.module
    rows = {r["label"]: r for r in m.scorecard_rows(0.20)}
    assert rows["textiles & apparel"]["gap_points"] == pytest.approx(19.0)
    assert rows["textiles & apparel"]["verdict"] == "19 points above"
    assert rows["textiles & apparel"]["symbol"] == "▲"
    assert rows["metals"]["verdict"] == "13 points below" and rows["metals"]["symbol"] == "▼"
    level = m.scorecard_rows(m.REAL_WORLD_CIRCULARITY_BENCHMARK + 0.001)[0]
    assert level["verdict"] == "level with" and level["symbol"] == "◆"


def test_bar_widths_are_clamped_percentages(game_env):
    m = game_env.module
    for fraction in (0.0, 0.5, 1.0, 1.7):
        for row in m.scorecard_rows(fraction):
            assert 0 <= row["mine_width"] <= 100 and 0 <= row["benchmark_width"] <= 100
    assert m.scorecard_rows(1.0)[0]["mine_width"] == 100


def test_state_is_conveyed_by_text_and_shape_not_just_colour(game_env):
    m = game_env.module
    for row in m.scorecard_rows(0.4):
        assert row["symbol"] in "▲▼◆" and "point" in row["verdict"] or row["verdict"] == "level with"


def test_scorecard_renders_into_the_page(game_env):
    m = game_env.module
    m.render()
    container = game_env.elements["scorecard-list"]
    assert len(container.children) == 1 + len(m.SECTOR_COMPARISONS)
    first = container.children[0]
    assert "overall real-world average" in first.children[0].innerText


def test_scorecard_tracks_the_chain(game_env):
    m = game_env.module
    m.render()
    before = game_env.elements["scorecard-list"].children[1].children[0].innerText
    game_env.chain.total_extracted = 0.0
    game_env.chain.total_produced = 500.0  # a fully circular history
    m.render()
    after = game_env.elements["scorecard-list"].children[1].children[0].innerText
    assert before != after and "above" in after


def test_rerendering_replaces_rows_instead_of_appending(game_env):
    m = game_env.module
    for _ in range(3):
        m.render()
    assert len(game_env.elements["scorecard-list"].children) == 1 + len(m.SECTOR_COMPARISONS)


def test_scorecard_reads_state_only(game_env):
    m = game_env.module
    before = m.get_state()
    m.scorecard_rows(0.3)
    m.render_scorecard()
    assert m.get_state() == before
