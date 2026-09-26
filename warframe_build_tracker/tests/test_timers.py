"""Batch A #2: foundry timer notes and the optional notification."""

import types

from .helpers import all_text, click, known_state

BASE = 1_790_000_000_000  # 2026-09-21, inside the accepted range


def _clock(m, ms=BASE):
    m._now_ms = lambda: ms


def test_duration_parsing(game_env):
    p = game_env.module.parse_duration_minutes
    assert p("12h") == 720
    assert p("12") == 720  # a bare number is hours
    assert p("1d 2h 30m") == 1590
    assert p("90m") == 90
    assert p("1.5h") == 90
    for bad in ("", "abc", "12x", "0", "0m", "-3h", "h12", "91d", None):
        assert p(bad) is None, bad


def test_add_timer_from_start_plus_duration_and_from_ready_at(game_env):
    m = game_env.module
    _clock(m)
    assert m.add_timer("Kitgun chamber", start_ms=BASE, duration_min=720)[0] is True
    assert m.add_timer("Zaw strike", ready_ms=BASE + 3_600_000, notify=True)[0] is True
    assert [t["n"] for t in m.state["timers"]] == ["Zaw strike", "Kitgun chamber"]  # soonest first
    assert m.state["timers"][1]["ms"] == BASE + 720 * 60000


def test_add_timer_validation(game_env):
    m = game_env.module
    assert m.add_timer("", ready_ms=BASE)[0] is False
    assert m.add_timer("x")[0] is False  # nothing to compute a time from
    assert m.add_timer("x", start_ms=BASE)[0] is False  # start with no duration
    assert m.add_timer("x", ready_ms=5)[0] is False  # out of range
    assert m.add_timer("x", ready_ms=True)[0] is False
    for i in range(m.TIMER_MAX):
        assert m.add_timer(f"t{i}", ready_ms=BASE + i)[0] is True
    assert m.add_timer("one more", ready_ms=BASE)[0] is False


def test_remaining_text_and_line(game_env):
    m = game_env.module
    assert m.format_remaining(0) == "ready now"
    assert m.format_remaining(-5) == "ready now"
    assert m.format_remaining(5 * 60000) == "in 5m"
    assert m.format_remaining(125 * 60000) == "in 2h 5m"
    assert m.format_remaining(60 * 60 * 1000 * 50) == "in 2d 2h"
    m.add_timer("Craft", ready_ms=BASE + 90 * 60000)
    line = m.timer_line(m.state["timers"][0], BASE)
    assert line.startswith("Craft: ready at ") and "in 1h 30m" in line


def test_render_lists_timers_and_remove(game_env):
    m = game_env.module
    known_state(m)
    _clock(m)
    m.add_timer("Craft", ready_ms=BASE + 90 * 60000)
    m.render()
    assert "Craft: ready at" in all_text(game_env.elements["timer-list"])
    from .helpers import find_all
    click(find_all(game_env.elements["timer-list"], tag="button")[0])
    assert m.state["timers"] == []


def test_add_button_reads_the_inputs(game_env):
    m = game_env.module
    known_state(m)
    els = game_env.elements
    els["timer-name-input"].value = "Kitgun"
    els["timer-start-input"].value = "2026-09-27T10:00"
    els["timer-duration-input"].value = "12h"
    click(els["timer-add-button"])
    assert len(m.state["timers"]) == 1
    # outside a browser the input is read as UTC
    assert m.state["timers"][0]["ms"] == m.parse_local_datetime("2026-09-27T22:00")
    assert els["timer-name-input"].value == ""
    els["timer-name-input"].value = "Bad"
    els["timer-duration-input"].value = "soon"
    els["timer-start-input"].value = "2026-09-27T10:00"
    click(els["timer-add-button"])
    assert len(m.state["timers"]) == 1
    assert "Duration should look like" in els["timer-message"].textContent


def test_notification_api_missing_degrades_silently(game_env):
    m = game_env.module
    known_state(m)
    assert m.notification_permission() is None
    assert m.request_notification_permission() is False
    assert m.schedule_notifications() == 0
    m.add_timer("Craft", ready_ms=BASE + 90 * 60000, notify=True)
    m.render()  # must not raise
    assert game_env.elements["timer-notify-button"].hidden is True
    assert "no notification support" in game_env.elements["timer-hint"].textContent
    click(game_env.elements["timer-notify-button"])  # explicit click on unsupported browser
    assert "cannot show notifications" in game_env.elements["timer-message"].textContent


def test_permission_is_only_requested_from_the_button(game_env):
    m = game_env.module
    calls = []

    class FakeNotification:
        permission = "default"

        @staticmethod
        def requestPermission():  # noqa: N802
            calls.append("ask")

    game_env.js.Notification = FakeNotification
    known_state(m)
    m.add_timer("Craft", ready_ms=BASE + 90 * 60000, notify=True)
    m.render()
    assert calls == []  # adding/rendering never asks
    assert game_env.elements["timer-notify-button"].hidden is False
    click(game_env.elements["timer-notify-button"])
    assert calls == ["ask"]


def test_granted_permission_schedules_only_future_notify_timers(game_env):
    m = game_env.module
    _clock(m)
    game_env.js.Notification = types.SimpleNamespace(permission="granted")
    m.add_timer("soon", ready_ms=BASE + 60_000, notify=True)
    m.add_timer("quiet", ready_ms=BASE + 90_000, notify=False)
    m.add_timer("past", ready_ms=BASE - 60_000, notify=True)
    assert m.schedule_notifications(BASE) == 1
    assert len(game_env.js.timers.pending) == 1
    assert list(game_env.js.timers.pending.values())[0][1] == 60_000


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    assert "timers" not in m.get_state()
    m.add_timer("Craft", ready_ms=BASE, notify=True)
    saved = m.get_state()
    m.state["timers"] = []
    m.load_state(saved)
    assert m.state["timers"] == [{"n": "Craft", "ms": BASE, "notify": True}]
    m.load_state({"timers": [
        {"n": "ok", "ms": BASE, "notify": False},
        {"n": "", "ms": BASE, "notify": False},
        {"n": "no bool", "ms": BASE, "notify": "yes"},
        {"n": "float", "ms": 1.5e12, "notify": False},
        {"n": "old", "ms": 5, "notify": False},
        {"n": "bool ms", "ms": True, "notify": False},
        "junk", 7, None,
    ]})
    assert m.state["timers"] == [{"n": "ok", "ms": BASE, "notify": False}]
    m.load_state({"timers": "x"})
    assert m.state["timers"] == []
