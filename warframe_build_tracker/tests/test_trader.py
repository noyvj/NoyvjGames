"""Batch A #6: trader schedule tab (Baro Ki'Teer's two-week cycle)."""

from datetime import date

from .helpers import all_text, click, find_all, known_state


def _set(m, last):
    m.state["trader"]["last"] = last


def test_days_until_the_next_visit(game_env):
    m = game_env.module
    _set(m, "2026-09-01")
    # 2026-09-01 + 14 = 2026-09-15
    info = m.baro_reminder(date(2026, 9, 5))
    assert info == {"state": "waiting", "days": 10, "date": "2026-09-15"}
    assert m.baro_text(date(2026, 9, 5)) == "Baro is due back in 10 days (2026-09-15)."
    assert m.baro_text(date(2026, 9, 14)) == "Baro is due back in 1 day (2026-09-15)."


def test_arrival_day_and_the_forty_eight_hour_window(game_env):
    m = game_env.module
    _set(m, "2026-09-01")
    assert m.baro_reminder(date(2026, 9, 15))["state"] == "today"
    assert m.baro_reminder(date(2026, 9, 1))["state"] == "today"
    here = m.baro_reminder(date(2026, 9, 16))
    assert here["state"] == "here" and here["date"] == "2026-09-15"
    assert m.baro_reminder(date(2026, 9, 17)) == {"state": "waiting", "days": 12, "date": "2026-09-29"}


def test_a_future_date_counts_down_to_it(game_env):
    m = game_env.module
    _set(m, "2026-10-10")
    assert m.baro_reminder(date(2026, 10, 1)) == {"state": "future", "days": 9, "date": "2026-10-10"}


def test_no_date_or_a_bad_one(game_env):
    m = game_env.module
    assert m.baro_reminder() is None
    assert "Enter a date" in m.baro_text()
    _set(m, "junk")
    assert m.baro_reminder() is None


def test_watch_list(game_env):
    m = game_env.module
    assert m.add_watch("Primed Continuity")[0] is True
    assert m.add_watch("primed continuity")[0] is False
    assert m.add_watch("  ")[0] is False
    for i in range(m.WATCH_MAX):
        m.state["trader"]["watch"].append(f"x{i}")
    assert m.add_watch("more")[0] is False


def test_ui(game_env):
    m = game_env.module
    known_state(m)
    els = game_env.elements
    els["trader-date-input"].value = "2026-09-01"
    els["trader-date-input"].dispatch("change", None)
    assert m.state["trader"]["last"] == "2026-09-01"
    assert els["trader-reminder"].textContent.startswith("Baro ")
    els["trader-date-input"].value = "garbage"
    els["trader-date-input"].dispatch("change", None)
    assert m.state["trader"]["last"] == ""
    els["trader-item-input"].value = "Kuva Bramma"
    click(els["trader-add-button"])
    assert "Kuva Bramma" in all_text(els["trader-list"])
    click(find_all(els["trader-list"], tag="button")[0])
    assert m.state["trader"]["watch"] == []


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    assert "trader" not in m.get_state()
    m.state["trader"] = {"last": "2026-09-01", "watch": ["a"]}
    saved = m.get_state()
    m.state["trader"] = {"last": "", "watch": []}
    m.load_state(saved)
    assert m.state["trader"] == {"last": "2026-09-01", "watch": ["a"]}
    m.load_state({"trader": {"last": "2026-02-31", "watch": ["ok", "OK", "", 5, ["x"], "b"]}})
    assert m.state["trader"] == {"last": "", "watch": ["ok", "b"]}
    m.load_state({"trader": "x"})
    assert m.state["trader"] == {"last": "", "watch": []}
