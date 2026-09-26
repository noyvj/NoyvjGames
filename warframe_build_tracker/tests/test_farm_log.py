"""Session farming log: gains in a resource's total on hand, over time."""

import json

from .test_tracker import _reset_to_known_state


def _fix_clock(m, stamp):
    m._now_stamp = lambda: stamp


def _fresh(m):
    _reset_to_known_state(m)
    m.state["farm_log"] = []
    _fix_clock(m, "2026-09-26 10:00")


def test_only_increases_are_logged(game_env):
    m = game_env.module
    _fresh(m)
    assert m.log_gain("Ferrite", 100, 100) is False
    assert m.log_gain("Ferrite", 100, 40) is False
    assert m.log_gain("Ferrite", 100, 250) is True
    assert m.state["farm_log"] == [{"t": "2026-09-26 10:00", "r": "Ferrite", "d": 150}]


def test_same_minute_gains_of_one_resource_merge(game_env):
    m = game_env.module
    _fresh(m)
    m.log_gain("Ferrite", 0, 10)
    m.log_gain("Ferrite", 10, 25)
    assert m.state["farm_log"] == [{"t": "2026-09-26 10:00", "r": "Ferrite", "d": 25}]
    m.log_gain("Rubedo", 0, 5)
    _fix_clock(m, "2026-09-26 10:01")
    m.log_gain("Rubedo", 5, 6)
    assert [e["r"] for e in m.state["farm_log"]] == ["Ferrite", "Rubedo", "Rubedo"]


def test_log_is_capped(game_env):
    m = game_env.module
    _fresh(m)
    for i in range(m.FARM_LOG_MAX + 25):
        _fix_clock(m, f"2026-09-26 {i // 60 % 24:02d}:{i % 60:02d}")
        m.log_gain("Ferrite", 0, 1)
    assert len(m.state["farm_log"]) == m.FARM_LOG_MAX


def test_summary_splits_today_from_overall(game_env):
    m = game_env.module
    _fresh(m)
    _fix_clock(m, "2026-09-25 23:59")
    m.log_gain("Ferrite", 0, 100)
    _fix_clock(m, "2026-09-26 08:00")
    m.log_gain("Ferrite", 100, 130)
    m.log_gain("Rubedo", 0, 7)
    summary = m.farm_log_summary()
    assert summary["today"] == {"Ferrite": 30, "Rubedo": 7}
    assert summary["all"] == {"Ferrite": 130, "Rubedo": 7}


def test_editing_the_page_inputs_logs_a_gain(game_env):
    m = game_env.module
    _fresh(m)
    m.state["inventory"]["Ferrite"] = {"built": 10, "raw": 0}
    handler = m._make_resource_change_handler(
        "Ferrite", type("I", (), {"value": "0"})(), type("I", (), {"value": "60"})()
    )
    handler(None)
    assert m.state["farm_log"][-1] == {"t": "2026-09-26 10:00", "r": "Ferrite", "d": 50}
    assert "Ferrite +50" in game_env.elements["farm-log-text"].textContent


def test_an_import_logs_the_increase_only(game_env):
    m = game_env.module
    _fresh(m)
    m.state["inventory"]["Ferrite"] = {"built": 100, "raw": 0}
    m.state["inventory"]["Rubedo"] = {"built": 500, "raw": 0}
    payload = {"MiscItems": [
        {"ItemType": "/Lotus/Types/Items/MiscItems/Ferrite", "ItemCount": 160},
        {"ItemType": "/Lotus/Types/Items/MiscItems/Rubedo", "ItemCount": 200},
    ]}
    m.import_last_data(json.dumps(payload))
    assert m.state["farm_log"] == [{"t": "2026-09-26 10:00", "r": "Ferrite", "d": 60}]


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    _fresh(m)
    assert "farm_log" not in m.get_state()
    m.log_gain("Ferrite", 0, 12)
    saved = m.get_state()
    m.state["farm_log"] = []
    m.load_state(saved)
    assert m.state["farm_log"] == [{"t": "2026-09-26 10:00", "r": "Ferrite", "d": 12}]
    bad = {
        "farm_log": [
            {"t": "yesterday", "r": "Ferrite", "d": 5},
            {"t": "2026-09-26 10:00", "r": "Nonsense", "d": 5},
            {"t": "2026-09-26 10:00", "r": "Ferrite", "d": True},
            {"t": "2026-09-26 10:00", "r": "Ferrite", "d": -3},
            {"t": "2026-09-26 10:00", "r": "Rubedo", "d": 4},
            "junk",
        ]
    }
    m.load_state(bad)
    assert m.state["farm_log"] == [{"t": "2026-09-26 10:00", "r": "Rubedo", "d": 4}]
    m.load_state({"farm_log": "nope"})
    assert m.state["farm_log"] == []


def test_clear_button_and_empty_text(game_env):
    m = game_env.module
    _fresh(m)
    m.render()
    assert "Nothing logged yet" in game_env.elements["farm-log-text"].textContent
    m.log_gain("Ferrite", 0, 3)
    m.render()
    game_env.elements["clear-farm-log-button"].dispatch("click", None)
    assert m.state["farm_log"] == []
