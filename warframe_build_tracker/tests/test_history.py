"""Batch A #14: progress history snapshots and the inline SVG chart."""

import json

from .helpers import click, known_state


def test_snapshot_records_the_completion_percentage(game_env):
    m = game_env.module
    known_state(m, parts={"Rahn Prism": {"owned": 0, "target": 1}})
    m._now_stamp = lambda: "2026-09-27 10:00"
    assert m.take_snapshot() == {"t": "2026-09-27 10:00", "p": 97}  # 32 of 33 parts
    m._now_stamp = lambda: "2026-09-27 10:00"
    m.state["parts"]["Rahn Prism"]["owned"] = 1
    m.take_snapshot()
    assert m.state["history"] == [{"t": "2026-09-27 10:00", "p": 100}]  # same minute replaces


def test_keeps_only_the_last_sixty(game_env):
    m = game_env.module
    known_state(m)
    for i in range(75):
        m._now_stamp = lambda i=i: f"2026-09-27 {i // 60:02d}:{i % 60:02d}"
        m.take_snapshot()
    assert len(m.state["history"]) == 60
    assert m.state["history"][0]["t"] == "2026-09-27 00:15"


def test_import_takes_a_snapshot_and_button_takes_one_on_demand(game_env):
    m = game_env.module
    known_state(m)
    m._now_stamp = lambda: "2026-09-27 10:00"
    m.import_last_data(json.dumps({"MiscItems": []}))
    assert len(m.state["history"]) == 1
    m._now_stamp = lambda: "2026-09-27 10:05"
    click(game_env.elements["history-snapshot-button"])
    assert len(m.state["history"]) == 2
    click(game_env.elements["history-clear-button"])
    assert m.state["history"] == []


def test_summary_text(game_env):
    m = game_env.module
    assert "No snapshots yet" in m.history_summary([])
    assert m.history_summary([{"t": "2026-09-27 10:00", "p": 40}]) == "1 snapshot: 40% of parts complete on 2026-09-27 10:00."
    two = [{"t": "2026-09-01 10:00", "p": 40}, {"t": "2026-09-27 10:00", "p": 55}]
    assert m.history_summary(two) == "2 snapshots: from 40% on 2026-09-01 10:00 to 55% on 2026-09-27 10:00 (up 15 points)."
    assert "down 5 points" in m.history_summary([{"t": "2026-09-01 10:00", "p": 60}, {"t": "2026-09-02 10:00", "p": 55}])
    assert "unchanged" in m.history_summary([{"t": "2026-09-01 10:00", "p": 60}, {"t": "2026-09-02 10:00", "p": 60}])


def test_svg_is_accessible_and_scaled(game_env):
    m = game_env.module
    assert m.history_chart_svg([]) == ""
    history = [{"t": "2026-09-01 10:00", "p": 0}, {"t": "2026-09-02 10:00", "p": 100}]
    svg = m.history_chart_svg(history)
    assert svg.startswith("<svg") and 'role="img"' in svg and "aria-label=" in svg
    assert m.history_summary(history) in svg
    assert 'points="14.0,106.0 306.0,14.0"' in svg  # 0% at the bottom, 100% at the top
    single = m.history_chart_svg([{"t": "2026-09-01 10:00", "p": 50}])
    assert "<circle" in single


def test_render_fills_chart_and_summary(game_env):
    m = game_env.module
    known_state(m)
    m.take_snapshot()
    m.render()
    assert game_env.elements["history-chart"].innerHTML.startswith("<svg")
    assert "1 snapshot" in game_env.elements["history-summary"].textContent


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    assert "history" not in m.get_state()
    m.state["history"] = [{"t": "2026-09-27 10:00", "p": 50}]
    saved = m.get_state()
    m.state["history"] = []
    m.load_state(saved)
    assert m.state["history"] == [{"t": "2026-09-27 10:00", "p": 50}]
    m.load_state({"history": [{"t": "bad", "p": 5}, {"t": "2026-09-27 10:00", "p": 101}, {"t": "2026-09-27 10:00", "p": -1},
                              {"t": "2026-09-27 10:00", "p": True}, {"t": "2026-09-27 10:00", "p": 2.5}, "x",
                              {"t": "2026-09-27 10:01", "p": 7}]})
    assert m.state["history"] == [{"t": "2026-09-27 10:01", "p": 7}]
    m.load_state({"history": [{"t": f"2026-09-27 10:{i % 60:02d}", "p": 1} for i in range(80)]})
    assert len(m.state["history"]) == 60
