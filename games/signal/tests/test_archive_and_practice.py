"""Archive rules (no future, never a streak) and endless practice."""

import re


def boot(g):
    return g.call("boot")["view"]


def test_future_and_pre_epoch_dates_are_refused(g):
    boot(g)
    assert g.call("open", date="2026-09-28", mode="easy")["ok"] is False
    assert "not been broadcast" in g.call("open", date="2027-01-01", mode="easy")["error"]
    g.set_day(10)
    assert g.call("open", date="2026-09-26", mode="easy")["ok"] is False
    assert g.call("open", date="2026-09-27", mode="easy")["ok"]
    for bad in ("nonsense", None, 5, "2026-13-01"):
        assert g.call("open", date=bad, mode="easy")["ok"] is False
    for bad_mode in ("wide", "bigsky", "x", None, ["easy"]):
        assert g.call("open", date="2026-09-27", mode=bad_mode)["ok"] is False


def test_past_date_is_an_archive_and_todays_is_a_daily(g):
    boot(g)
    g.set_day(5)
    view = g.call("open", date="2026-09-30", mode="hard")["view"]
    assert view["session"]["type"] == "archive" and view["session"]["number"] == 4
    assert "Archive" in view["session"]["label"]
    view = g.call("open", date="2026-10-02", mode="hard")["view"]
    assert view["session"]["type"] == "daily"


def test_archive_wins_never_touch_the_streak(g):
    boot(g)
    g.set_day(3)
    for offset in range(3):
        date = "2026-09-%d" % (27 + offset)
        g.call("open", date=date, mode="easy")
        g.win_current(pings=2)
        assert g.m.S["days"]["%s:easy" % date]["kind"] == "archive"
    stats = g.call("stats")["stats"]["easy"]
    assert stats["daily"]["played"] == 0 and stats["daily"]["streak"] == 0
    assert stats["archive"]["played"] == 3 and stats["archive"]["won"] == 3
    assert g.call("stats")["best_streak"] == 0


def test_a_puzzle_is_daily_only_if_its_first_ping_is_on_its_own_date(g):
    boot(g)
    g.call("open", date=g.m.EPOCH, mode="easy")
    g.call("ping", r=4, c=4)  # first ping on its own UTC day
    g.set_day(1)  # midnight passes mid-puzzle
    g.call("open", date=g.m.EPOCH, mode="easy")
    rec = g.m.S["days"]["%s:easy" % g.m.EPOCH]
    assert rec["kind"] == "daily"  # stays daily even though it is now the past
    # the same puzzle opened for the first time a day late would be an archive
    g.call("open", date=g.m.EPOCH, mode="hard")
    g.call("ping", r=4, c=4)
    assert g.m.S["days"]["%s:hard" % g.m.EPOCH]["kind"] == "archive"


def test_boot_resumes_archive_sessions_and_moves_stale_dailies(g):
    boot(g)
    g.set_day(2)
    g.call("open", date="2026-09-28", mode="hard")
    view = boot(g)
    assert view["session"]["type"] == "archive" and view["session"]["date"] == "2026-09-28"
    # a daily left open on an old date becomes today's daily after midnight
    g.call("open", date="2026-09-29", mode="easy")
    g.set_day(3)
    view = boot(g)
    assert view["session"]["type"] == "daily" and view["session"]["date"] == "2026-09-30"


def test_both_modes_can_be_played_on_the_same_day(g):
    boot(g)
    g.call("open", date=g.m.EPOCH, mode="easy")
    g.win_current(pings=1)
    g.call("open", date=g.m.EPOCH, mode="hard")
    g.win_current(pings=1)
    assert set(g.m.S["days"]) == {"2026-09-27:easy", "2026-09-27:hard"}


def test_reopening_a_finished_puzzle_shows_the_result(g):
    boot(g)
    g.win_current(pings=2)
    g.call("open", date=g.m.EPOCH, mode="hard")
    view = g.call("open", date=g.m.EPOCH, mode="easy")["view"]
    assert view["status"] == "won" and view["truth"] is not None and len(view["pings"]) == 2


def test_practice_new_puzzle_has_a_shareable_code(g):
    boot(g)
    view = g.call("practice", mode="hard")["view"]
    code = view["session"]["code"]
    assert re.fullmatch(r"P-H[0-9A-Z]{5}", code) and view["session"]["type"] == "practice"
    assert view["board"]["n"] == 9 and g.m.S["settings"]["last_preset"] == "hard"
    assert view["stats"] is None and view["session"]["number"] is None


def test_practice_code_reproduces_the_same_puzzle(g):
    boot(g)
    view = g.call("practice", mode="wide")["view"]
    code = view["session"]["code"]
    truth = g.truth()
    g.call("practice", mode="easy")
    assert g.truth() != truth
    again = g.call("practice", code=code.lower())["view"]
    assert again["session"]["code"] == code and again["board"]["n"] == 13
    assert g.truth() == truth


def test_practice_bad_inputs(g):
    boot(g)
    for bad in ({"code": "P-Z99999"}, {"code": ""}, {"code": 5}, {"mode": "nope"}, {"mode": ["easy"]}, {"mode": None}):
        assert g.call("practice", **bad)["ok"] is False


def test_practice_results_go_to_their_own_bucket(g):
    boot(g)
    g.call("practice", mode="easy")
    g.win_current(pings=2)
    stats = g.call("stats")
    assert stats["stats"]["easy"]["practice"]["won"] == 1
    assert stats["stats"]["easy"]["practice"]["pings_hist"][1] == 1
    assert stats["stats"]["easy"]["daily"]["played"] == 0 and g.m.S["days"] == {}
    share = g.call("share")["text"]
    assert share.startswith("Signal practice P-E") and "#" not in share.splitlines()[0]


def test_practice_in_progress_survives_reboot_and_resumes(g):
    boot(g)
    view = g.call("practice", mode="easy")["view"]
    g.call("ping", r=4, c=4)
    resumed = boot(g)
    assert resumed["session"]["code"] == view["session"]["code"] and len(resumed["pings"]) == 1


def test_practice_big_boards_are_playable_and_solvable(g):
    boot(g)
    for mode, n in (("wide", 13), ("bigsky", 15)):
        view = g.call("practice", mode=mode)["view"]
        assert view["board"]["n"] == n and view["board"]["par"] <= view["board"]["budget"] - 2
        resp = g.win_current(pings=1)
        assert resp["view"]["status"] == "won"
    assert "Wide Open" in [a["label"] for a in g.call("achievements")["achievements"] if a["earned"]]
