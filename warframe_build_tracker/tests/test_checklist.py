"""Batch A #13: daily / weekly checklist with UTC resets (daily 0:00 UTC,
weekly Monday 0:00 UTC, per the Warframe Wiki reset page read 2026-09-27)."""

from datetime import datetime, timezone

from .helpers import all_text, click, find_all, known_state


def utc(y, mo, d, h=0, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


def test_period_stamps_use_utc_date_and_monday(game_env):
    m = game_env.module
    # 2026-09-27 is a Sunday; the week began Monday 2026-09-21
    assert m.period_stamps(utc(2026, 9, 27, 23, 59)) == {"daily": "2026-09-27", "weekly": "2026-09-21"}
    assert m.period_stamps(utc(2026, 9, 28, 0, 0)) == {"daily": "2026-09-28", "weekly": "2026-09-28"}


def test_daily_ticks_clear_at_utc_midnight_but_weekly_ones_stay(game_env):
    m = game_env.module
    m.add_check_item("Login", "daily")
    m.add_check_item("Sortie", "weekly")
    assert m.toggle_check("Login", "daily", utc(2026, 9, 27, 23, 59))
    assert m.toggle_check("Sortie", "weekly", utc(2026, 9, 27, 23, 59))
    assert m.roll_checklist(utc(2026, 9, 27, 23, 59)) is False
    assert m.state["checklist"]["ticks"]["daily"]["done"] == ["Login"]
    m.roll_checklist(utc(2026, 9, 28, 0, 0))  # daily reset AND a new week (Monday)
    assert m.state["checklist"]["ticks"]["daily"] == {"stamp": "2026-09-28", "done": []}
    assert m.state["checklist"]["ticks"]["weekly"] == {"stamp": "2026-09-28", "done": []}


def test_weekly_ticks_survive_a_midweek_daily_reset(game_env):
    m = game_env.module
    m.add_check_item("Login", "daily")
    m.add_check_item("Sortie", "weekly")
    m.toggle_check("Login", "daily", utc(2026, 9, 22, 10))
    m.toggle_check("Sortie", "weekly", utc(2026, 9, 22, 10))
    m.roll_checklist(utc(2026, 9, 23, 0, 1))
    assert m.state["checklist"]["ticks"]["daily"]["done"] == []
    assert m.state["checklist"]["ticks"]["weekly"]["done"] == ["Sortie"]


def test_untick_and_unknown_task(game_env):
    m = game_env.module
    m.add_check_item("Login", "daily")
    now = utc(2026, 9, 27, 10)
    m.toggle_check("Login", "daily", now)
    m.toggle_check("Login", "daily", now)
    assert m.state["checklist"]["ticks"]["daily"]["done"] == []
    assert m.toggle_check("Nope", "daily", now) is False


def test_next_reset_times(game_env):
    m = game_env.module
    now = utc(2026, 9, 27, 18, 30)  # Sunday
    assert m.next_reset("daily", now) == utc(2026, 9, 28)
    assert m.next_reset("weekly", now) == utc(2026, 9, 28)
    assert m.next_reset("weekly", utc(2026, 9, 28, 0, 0)) == utc(2026, 10, 5)
    assert m.next_reset("weekly", utc(2026, 9, 30, 12)) == utc(2026, 10, 5)
    text = m.check_reset_text(now)
    assert "Daily reset in 5h 30m" in text and "Weekly reset in 5h 30m" in text and "0:00 UTC" in text


def test_add_and_remove_validation(game_env):
    m = game_env.module
    assert m.add_check_item("", "daily")[0] is False
    assert m.add_check_item("x", "monthly")[0] is False
    assert m.add_check_item("Login", "daily")[0] is True
    assert m.add_check_item("login", "daily")[0] is False
    assert m.add_check_item("Login", "weekly")[0] is True  # same name, other period
    m.toggle_check("Login", "daily")
    assert m.remove_check_item("Login", "daily") is True
    assert m.state["checklist"]["ticks"]["daily"]["done"] == []
    assert m.remove_check_item("Login", "daily") is False


def test_ui_clears_stale_ticks_on_render(game_env):
    m = game_env.module
    known_state(m)
    els = game_env.elements
    els["checklist-name-input"].value = "Login"
    els["checklist-kind-select"].value = "daily"
    click(els["checklist-add-button"])
    box = find_all(els["checklist-daily"], tag="input")[0]
    box.checked = True
    box.dispatch("change", None)
    assert m.state["checklist"]["ticks"]["daily"]["done"] == ["Login"]
    m.state["checklist"]["ticks"]["daily"]["stamp"] = "2001-01-01"  # a stale save
    m.render()
    assert m.state["checklist"]["ticks"]["daily"]["done"] == []
    assert "Login" in all_text(els["checklist-daily"])
    assert "No weekly tasks yet" in all_text(els["checklist-weekly"])


def test_minute_tick_rerenders_only_when_a_period_changed(game_env):
    m = game_env.module
    known_state(m)
    assert m.tick_minute() is False
    m._now_utc = lambda: utc(2030, 1, 1, 0, 0)
    assert m.tick_minute() is True
    assert m.tick_minute() is False


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    assert "checklist" not in m.get_state()
    m.add_check_item("Login", "daily")
    m.add_check_item("Sortie", "weekly")
    m.toggle_check("Login", "daily", utc(2026, 9, 27, 10))
    saved = m.get_state()
    assert saved["checklist"]["ticks"]["daily"] == {"stamp": "2026-09-27", "done": ["Login"]}
    m.state["checklist"] = {"items": [], "ticks": {"daily": {"stamp": "", "done": []}, "weekly": {"stamp": "", "done": []}}}
    m._now_utc = lambda: utc(2026, 9, 27, 12)  # load_state() renders, which applies any reset that has passed
    m.load_state(saved)
    assert m.state["checklist"]["items"] == [{"n": "Login", "k": "daily"}, {"n": "Sortie", "k": "weekly"}]
    assert m.state["checklist"]["ticks"]["daily"]["done"] == ["Login"]
    m.load_state({"checklist": {
        "items": [{"n": "A", "k": "daily"}, {"n": "a", "k": "daily"}, {"n": "B", "k": "yearly"}, {"n": "", "k": "daily"}, "x"],
        "ticks": {"daily": {"stamp": "2026-09-27", "done": ["A", "Ghost", 4]}, "weekly": {"stamp": "junk", "done": ["A"]}, "extra": 1},
    }})
    assert m.state["checklist"]["items"] == [{"n": "A", "k": "daily"}]
    assert m.state["checklist"]["ticks"]["daily"] == {"stamp": "2026-09-27", "done": ["A"]}
    # the junk weekly stamp was dropped, so the render that follows load_state() restamped it fresh
    assert m.state["checklist"]["ticks"]["weekly"] == {"stamp": "2026-09-21", "done": []}
    m.load_state({"checklist": "x"})
    assert m.state["checklist"]["items"] == []
