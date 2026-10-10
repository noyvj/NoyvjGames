"""Streaks are derived from `days`; achievements are earned once, kept forever."""

import datetime


def play_day(g, offset, mode="easy", win=True, pings=2):
    day = g.set_day(offset)
    g.call("boot")
    g.call("open", date=day, mode=mode)
    return g.win_current(pings=pings) if win else g.lose_current()


def earned(g):
    return {a["id"] for a in g.call("achievements")["achievements"] if a["earned"]}


def test_streak_counts_consecutive_daily_wins(g):
    for offset in range(4):
        play_day(g, offset)
    stats = g.call("stats")["stats"]["easy"]["daily"]
    assert stats["streak"] == 4 and stats["best_streak"] == 4 and stats["won"] == 4
    assert stats["last_played_utc"] == "2026-09-30"


def test_a_missed_day_ends_the_streak_after_it_passes(g):
    play_day(g, 0)
    play_day(g, 1)
    g.set_day(2)  # a day with no play yet: streak is still alive through yesterday
    g.call("boot")
    assert g.call("stats")["stats"]["easy"]["daily"]["streak"] == 2
    g.set_day(3)  # yesterday was skipped
    g.call("boot")
    daily = g.call("stats")["stats"]["easy"]["daily"]
    assert daily["streak"] == 0 and daily["best_streak"] == 2


def test_a_loss_breaks_the_streak_immediately(g):
    play_day(g, 0)
    play_day(g, 1)
    play_day(g, 2, win=False)
    daily = g.call("stats")["stats"]["easy"]["daily"]
    assert daily["streak"] == 0 and daily["best_streak"] == 2 and daily["played"] == 3


def test_streaks_are_per_mode_and_recomputed_not_trusted(g):
    g.call("boot")
    g.call("settings", show_streaks=True)
    for offset in range(3):
        play_day(g, offset, mode="hard")
    stats = g.call("stats")
    assert stats["stats"]["hard"]["daily"]["streak"] == 3 and stats["stats"]["easy"]["daily"]["streak"] == 0
    assert stats["best_streak"] == 3
    # a save that claims a huge streak changes nothing: streaks come from `days`
    forged = g.m.get_state()
    forged["stats"]["hard"]["streak"] = 999
    forged["stats"]["hard"]["best_streak"] = 999
    g.m.reset_engine()
    g.m.load_state(forged)
    assert g.m.get_state()["stats"]["hard"]["best_streak"] == 3


def test_histogram_buckets_wins_by_pings_used(g):
    play_day(g, 0, pings=2)
    play_day(g, 1, pings=2)
    play_day(g, 2, pings=5)
    hist = g.call("stats")["stats"]["easy"]["daily"]["pings_hist"]
    assert hist[1] == 2 and hist[4] == 1 and sum(hist) == 3 and len(hist) == 8


def test_leaderboard_event_reports_best_streak_on_daily_wins_only(g):
    g.call("boot")
    g.call("settings", show_streaks=True)
    play_day(g, 0)
    resp = play_day(g, 1)
    ev = [e for e in resp["events"] if e["type"] == "leaderboard"]
    assert ev == [{"type": "leaderboard", "game": "signal", "board": "best_streak", "score": 2, "detail": "easy streak"}]
    g.set_day(3)
    g.call("boot")
    g.call("open", date="2026-09-27", mode="hard")  # archive replay
    assert [e for e in g.win_current(pings=1)["events"] if e["type"] == "leaderboard"] == []
    g.call("practice", mode="easy")
    assert g.win_current(pings=1)["events"] == []
    lost = play_day(g, 4, win=False)
    assert lost["events"] == []


def test_first_contact_static_and_lucky_guess(g):
    play_day(g, 0, pings=1)  # a win with 7 of 8 pings unused
    assert {"first_contact", "lucky_guess"} <= earned(g)
    assert "static" not in earned(g)
    play_day(g, 1, win=False)
    assert "static" in earned(g)


def test_par_based_achievements(g):
    day = g.set_day(0)
    g.call("boot")
    par = g.m._cur["puzzle"].par
    g.win_current(pings=par)
    assert "clean_signal" in earned(g) and "under_par" not in earned(g)
    g.set_day(1)
    g.call("boot")
    par = g.m._cur["puzzle"].par
    g.win_current(pings=par - 1)
    assert "under_par" in earned(g)
    assert day == g.m.EPOCH


def test_last_gasp_needs_the_final_ping(g):
    g.call("boot")
    g.win_current(pings=8)
    assert "last_gasp" in earned(g)


def test_hard_copy_and_both_bands(g):
    day = g.set_day(0)
    g.call("boot")
    g.call("open", date=day, mode="easy")
    g.win_current(pings=2)
    assert "both_bands" not in earned(g)
    g.call("open", date=day, mode="hard")
    g.win_current(pings=2)
    assert {"hard_copy", "both_bands"} <= earned(g)


def test_both_bands_needs_the_same_day(g):
    play_day(g, 0, mode="easy")
    play_day(g, 1, mode="hard")
    assert "both_bands" not in earned(g)


def test_streak_achievements_thresholds(g):
    g.call("boot")
    g.call("settings", show_streaks=True)
    for offset in range(2):
        play_day(g, offset)
    assert "three_in_a_row" not in earned(g)
    play_day(g, 2)
    assert "three_in_a_row" in earned(g) and "week_on_air" not in earned(g)
    for offset in range(3, 7):
        play_day(g, offset)
    assert "week_on_air" in earned(g) and "month_on_air" not in earned(g)


def test_month_on_air_after_thirty_days(g):
    g.call("boot")
    g.call("settings", show_streaks=True)
    for offset in range(30):
        play_day(g, offset)
    assert "month_on_air" in earned(g)


def test_overlap_and_silent_night(g):
    g.call("boot")
    board = g.m.board_for("easy")
    truth = g.truth()
    # an "overlap" reading is one a single transmitter (max = radius) cannot give
    stacked = [c for c in range(81) if g.m.reading_at(board, truth, c) > board.radius]
    if stacked:
        g.call("ping", r=stacked[0] // 9, c=stacked[0] % 9)
        assert "overlap" in earned(g)
    zeros = [c for c in range(81) if g.m.reading_at(board, truth, c) == 0][:3]
    for c in zeros:
        g.call("ping", r=c // 9, c=c % 9)
    assert "silent_night" in earned(g)


def test_overlap_is_earnable_for_sure_on_a_constructed_board(g, game):
    """Two transmitters 3 apart share a tile that reads more than the radius."""
    board = game.board_for("easy")
    truth = (2 * 9 + 2, 2 * 9 + 5)
    mid = 2 * 9 + 3
    assert game.reading_at(board, truth, mid) == 3 + 2 and game.reading_at(board, truth, mid) > board.radius


def test_archivist_after_ten_archive_puzzles(g):
    g.set_day(10)
    g.call("boot")
    for i in range(9):
        g.call("open", date=(datetime.date(2026, 9, 27) + datetime.timedelta(days=i)).isoformat(), mode="easy")
        g.lose_current()
    assert "archivist" not in earned(g)
    g.call("open", date="2026-10-06", mode="easy")
    g.lose_current()
    assert "archivist" in earned(g)


def test_practice_achievements(g):
    g.call("boot")
    for i in range(5):
        g.call("practice", mode="easy")
        g.win_current(pings=1)
        if i < 4:
            assert "dial_practice" not in earned(g)
    assert {"dial_practice", "first_contact"} <= earned(g)
    g.call("practice", mode="hard")
    g.win_current(pings=1)
    assert "hard_copy" in earned(g)


def test_puzzle_100_needs_a_daily_finish_on_puzzle_number_100(g):
    play_day(g, 98)
    assert "puzzle_100" not in earned(g)
    play_day(g, 99)
    assert "puzzle_100" in earned(g)


def test_earned_is_permanent_after_days_are_pruned(g):
    play_day(g, 0, pings=1)
    assert "lucky_guess" in earned(g)
    g.m.S["days"].clear()
    g.m.evaluate_achievements()
    assert "lucky_guess" in earned(g)
    assert g.m.get_state()["achievements_earned"] == [a for a in g.m.ACHIEVEMENT_IDS if a in g.m.S["earned"]]


def test_new_achievements_are_reported_once(g):
    resp = play_day(g, 0, pings=1)
    assert {a["id"] for a in resp["new"]} >= {"first_contact", "lucky_guess"}
    assert g.call("view")["new"] == []


# ---- AN-11: no streak by default ----

def test_streaks_are_off_by_default_nothing_is_shown_or_reported_or_earned(g):
    g.call("boot")
    assert g.m.S["settings"]["show_streaks"] is False
    for offset in range(8):
        resp = play_day(g, offset)
        assert [e for e in resp["events"] if e["type"] == "leaderboard"] == []
    assert g.call("stats")["best_streak"] is None
    got = earned(g)
    assert not ({"three_in_a_row", "week_on_air", "month_on_air"} & got)


def test_switching_streaks_on_later_awards_what_the_history_already_earned_and_nothing_was_lost(g):
    g.call("boot")
    for offset in range(8):
        play_day(g, offset)
    resp = g.call("settings", show_streaks=True)
    assert {a["id"] for a in resp["new"]} == {"three_in_a_row", "week_on_air"}
    assert g.call("stats")["best_streak"] == 8
    off = g.call("settings", show_streaks=False)
    assert off["new"] == [] and g.call("stats")["best_streak"] is None
    assert {"three_in_a_row", "week_on_air"} <= earned(g)          # earned badges are permanent


def test_show_streaks_must_be_a_real_boolean(g):
    g.call("boot")
    assert g.call("settings", show_streaks="yes")["ok"] is False
    assert g.m.S["settings"]["show_streaks"] is False
