"""Playing through the engine API exactly as app.js does."""

import json


def boot(g):
    resp = g.call("boot")
    assert resp["ok"], resp
    return resp["view"]


def test_boot_opens_todays_easy_daily(g):
    view = boot(g)
    assert view["session"]["type"] == "daily" and view["session"]["mode"] == "easy"
    assert view["session"]["date"] == g.m.EPOCH and view["session"]["number"] == 1
    assert view["board"]["n"] == 9 and view["board"]["k"] == 2 and view["board"]["budget"] == 8
    assert view["status"] == "inprogress" and view["pings"] == [] and view["pings_left"] == 8
    assert view["first_run"] is True
    assert view["truth"] is None  # never sent until the puzzle is finished


def test_unbooted_engine_asks_for_boot(g):
    resp = g.call("ping", r=1, c=1)
    assert resp["ok"] is False and "boot" in resp["error"]


def test_garbage_requests_never_raise(g):
    boot(g)
    for bad in (None, 5, [], {"action": 3}, {"action": "nope"}, {}):
        assert g.m.handle_dict(bad)["ok"] is False
    assert json.loads(g.m.handle("not json"))["ok"] is False
    assert json.loads(g.m.handle(json.dumps({"action": "view"})))["ok"] is True


def test_ping_returns_the_true_reading_and_spends_a_ping(g):
    boot(g)
    resp = g.call("ping", r=4, c=4)
    assert resp["ok"] and resp["dirty"]
    board = g.m.board_for("easy")
    expected = g.m.reading_at(board, g.truth(), 4 * 9 + 4)
    ping = resp["view"]["pings"][0]
    assert ping["v"] == expected and ping["label"] == "E5"
    assert resp["view"]["pings_left"] == 7
    assert "E5 reads %d" % expected in resp["message"]
    assert 0 <= ping["level"] <= 7 and 0 <= ping["fill"] <= 1 and len(ping["glyph"]) == 1
    assert resp["view"]["first_run"] is False


def test_repeat_out_of_range_and_bad_pings_are_refused(g):
    boot(g)
    assert g.call("ping", r=4, c=4)["ok"]
    assert g.call("ping", r=4, c=4)["ok"] is False
    for bad in ({"r": 9, "c": 0}, {"r": -1, "c": 0}, {"r": "1", "c": 1}, {"r": True, "c": 1}, {"r": 1.0, "c": 1}, {"r": None, "c": 1}, {}):
        assert g.call("ping", **bad)["ok"] is False
    assert len(g.call("view")["view"]["pings"]) == 1


def test_ping_budget_is_enforced_and_commit_is_still_allowed(g):
    boot(g)
    cells = [(r, c) for r in range(9) for c in range(9)]
    for r, c in cells[:8]:
        assert g.call("ping", r=r, c=c)["ok"]
    resp = g.call("ping", r=8, c=8)
    assert resp["ok"] is False and "Out of pings" in resp["error"]
    assert resp["view"]["pings_left"] == 0
    for r, c in g.truth_rc():
        g.call("mark", r=r, c=c)
    assert g.call("commit")["view"]["status"] == "won"


def test_marks_toggle_are_limited_and_interior_only(g):
    boot(g)
    assert g.call("mark", r=0, c=3)["ok"] is False  # outer ring
    assert g.call("mark", r=3, c=8)["ok"] is False
    assert g.call("mark", r=3, c=3)["view"]["marks"] == [[3, 3]]
    assert g.call("mark", r=3, c=3)["view"]["marks"] == []  # toggles off
    g.call("mark", r=3, c=3)
    g.call("mark", r=5, c=5)
    third = g.call("mark", r=6, c=6)
    assert third["ok"] is False and "Clear one first" in third["error"]
    assert g.call("clear_marks")["view"]["marks"] == []


def test_commit_needs_exactly_k_marks(g):
    boot(g)
    g.call("mark", r=3, c=3)
    resp = g.call("commit")
    assert resp["ok"] is False and "exactly 2" in resp["error"]
    assert resp["view"]["can_commit"] is False


def test_winning_reveals_truth_and_records_a_daily(g):
    boot(g)
    resp = g.win_current(pings=3)
    view = resp["view"]
    assert view["status"] == "won" and view["result"]["won"] is True
    assert sorted(map(tuple, view["truth"])) == sorted(map(tuple, g.truth_rc()))
    assert view["result"]["pings_used"] == 3 and view["result"]["par"] == g.m._cur["puzzle"].par
    rec = g.m.S["days"]["%s:easy" % g.m.EPOCH]
    assert rec["kind"] == "daily" and rec["result"] == "won" and rec["par"] == view["result"]["par"]
    assert view["stats"]["streak"] == 1
    assert g.call("ping", r=0, c=0)["ok"] is False  # finished


def test_wrong_commit_loses_and_reveals(g):
    boot(g)
    resp = g.lose_current()
    assert resp["view"]["status"] == "lost" and resp["view"]["truth"]
    assert resp["view"]["stats"]["streak"] == 0
    assert "Static" in [a["label"] for a in resp["new"]]


def test_near_miss_message_reports_how_many_were_right(g):
    boot(g)
    truth = g.truth_rc()
    board = g.m.board_for("easy")
    g.call("mark", r=truth[0][0], c=truth[0][1])
    other = next(c for c in board.cells if c not in g.truth())
    g.call("mark", r=other // 9, c=other % 9)
    assert "1 of 2 were right" in g.call("commit")["message"]


def test_give_up_counts_as_a_loss_even_with_no_marks(g):
    boot(g)
    resp = g.call("give_up")
    assert resp["view"]["status"] == "lost" and resp["view"]["guess"] == []
    assert g.m.S["days"]["%s:easy" % g.m.EPOCH]["result"] == "lost"


def test_blind_commit_with_zero_pings_can_win(g):
    boot(g)
    resp = g.win_current(pings=0)
    assert resp["view"]["status"] == "won" and resp["view"]["result"]["pings_used"] == 0


def test_marks_made_before_the_first_ping_are_kept(g):
    boot(g)
    g.call("mark", r=3, c=3)
    assert g.m.S["session"]["marks"] == [[3, 3]] and not g.m.S["days"]
    g.call("ping", r=4, c=4)
    rec = g.m.S["days"]["%s:easy" % g.m.EPOCH]
    assert rec["marks"] == [[3, 3]] and g.m.S["session"]["marks"] == []


def test_hard_mode_daily_and_no_assist(g):
    boot(g)
    resp = g.call("open", date=g.m.EPOCH, mode="hard")
    assert resp["ok"] and resp["view"]["board"]["k"] == 4 and resp["view"]["board"]["budget"] == 9
    g.call("ping", r=4, c=4)
    assert g.call("view")["view"]["possible"] is None  # hard has no shading assist


def test_easy_assist_shading_never_hides_the_truth(g):
    boot(g)
    for r, c in ((4, 4), (2, 2), (6, 6)):
        view = g.call("ping", r=r, c=c)["view"]
    possible = {tuple(p) for p in view["possible"]}
    assert {tuple(t) for t in g.truth_rc()} <= possible
    assert len(possible) < 49
    assert g.call("settings", assist_shading=False)["view"]["possible"] is None


def test_share_requires_a_finished_puzzle_and_marks_the_flag(g):
    boot(g)
    assert g.call("share")["ok"] is False
    g.win_current(pings=2)
    resp = g.call("share")
    assert resp["ok"] and resp["text"].startswith("Signal #1 easy 2/8")
    assert g.m.S["flags"]["shared"] is True
    assert "Show Off" in [a["label"] for a in resp["new"]]
    ascii_resp = g.call("share", ascii=True)
    assert ascii_resp["text"].isascii() and g.m.S["settings"]["ascii_share"] is True


def test_settings_validation(g):
    boot(g)
    assert g.call("settings", assist_shading="yes")["ok"] is False
    assert g.call("settings", ascii_share=1)["ok"] is False
    assert g.call("settings", last_preset="bogus")["ok"] is False
    assert g.call("settings", last_preset=["easy"])["ok"] is False
    assert g.call("settings", last_preset="wide")["ok"] and g.m.S["settings"]["last_preset"] == "wide"


def test_replaying_queued_taps_equals_playing_them_live(g):
    """app.js queues taps made before the engine is ready and replays them in
    order; the engine is deterministic, so both paths reach the same state."""
    taps = [("ping", 4, 4), ("ping", 2, 6), ("mark", 3, 3), ("ping", 6, 2), ("mark", 5, 5)]
    boot(g)
    for action, r, c in taps:
        g.call(action, r=r, c=c)
    live = json.dumps(g.m.get_state(), sort_keys=True)
    g.m.reset_engine()
    boot(g)
    replayed = [g.call(a, r=r, c=c) for a, r, c in taps]
    assert all(x["ok"] for x in replayed)
    assert json.dumps(g.m.get_state(), sort_keys=True) == live


def test_ack_onboarding_and_achievement_actions(g):
    boot(g)
    assert g.call("ack_onboarding")["view"]["first_run"] is False
    cat = g.call("achievements")["achievements"]
    assert len(cat) == 18 and all(set(a) >= {"id", "label", "description", "earned"} for a in cat)
    assert g.call("view")["view"]["ach"]["total"] == 18


def test_reset_clears_everything(g):
    boot(g)
    g.win_current(pings=2)
    g.call("share")
    resp = g.call("reset")
    assert resp["ok"] and resp["view"]["status"] == "inprogress"
    assert g.m.S["days"] == {} and g.m.S["earned"] == {} and g.m.S["flags"]["shared"] is False
