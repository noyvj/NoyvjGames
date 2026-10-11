"""shared/ghost.py: the shared ghost-run trace (planning/TODO.md Z-3a). Recording, caps, cleaning on load,
reading a turn, comparing a live run with a stored best trace and the summary sentence. Pure Python, no
browser; the JavaScript twin is checked against the same functions in test_ghost_browser.py."""

import copy
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ghost as gh  # noqa: E402


def trace_of(values, label=""):
    return gh.make_trace(values, label=label)


# -- numbers ------------------------------------------------------------------------------------
@pytest.mark.parametrize("value", [None, "5", "x", [], [1], {}, True, False, float("nan"), float("inf"), float("-inf"), 10 ** 400])
def test_clean_number_refuses_what_is_not_a_finite_real_number(value):
    assert gh.clean_number(value) is None


def test_clean_number_clamps_and_rounds_half_up():
    assert gh.clean_number(1.005) == 1.0           # binary 1.005 is just below the half
    assert gh.clean_number(2.675) == 2.68          # 2.675 * 100 is exactly 267.5 in binary floating point, so it rounds up
    assert gh.clean_number(-2.5) == -2.5
    assert gh.clean_number(0.125) == 0.13          # an exact half rounds up (also for negatives: -0.125 -> -0.12)
    assert gh.clean_number(-0.125) == -0.12
    assert gh.clean_number(1e30) == gh.MAX_ABS and gh.clean_number(-1e30) == -gh.MAX_ABS
    assert math.copysign(1, gh.clean_number(-0.0)) == 1.0 and gh.clean_number(-0.001) == 0


def test_sanitise_drops_junk_keeps_order_and_thins_long_lists():
    assert gh.sanitise([1, "a", None, 2.5, float("nan"), True, 3, [4], float("inf")]) == [1, 2.5, 3]
    assert gh.sanitise("not a list") == [] and gh.sanitise(None) == [] and gh.sanitise({"a": 1}) == []
    long = list(range(1000))
    out = gh.sanitise(long)
    assert len(out) == gh.MAX_LEN and out[0] == 0 and out[-1] == 999
    assert out == sorted(out)
    assert gh.sanitise(list(range(gh.HARD_INPUT_LIMIT + 1))) == []      # hostile size: refused outright
    assert len(gh.sanitise(list(range(gh.HARD_INPUT_LIMIT)))) == gh.MAX_LEN
    assert gh.sanitise(long, 10)[0] == 0 and len(gh.sanitise(long, 10)) == 10


def test_clean_label():
    assert gh.clean_label("  Run   3\t\n") == "Run 3"
    assert gh.clean_label(None) == "" and gh.clean_label(5) == ""
    assert len(gh.clean_label("x" * 500)) == gh.LABEL_MAX
    assert gh.clean_label("a\x00b\u2028c\x7fd") == "a b c d"


# -- the trace ----------------------------------------------------------------------------------
def test_make_trace_and_round_trip_through_json():
    t = trace_of([0, 1.5, 3, 4.25], "Run 3")
    assert t == {"v": 1, "turns": 4, "values": [0, 1.5, 3, 4.25], "label": "Run 3"}
    assert gh.load(json.loads(json.dumps(t))) == t
    assert gh.to_dict(t) == t and gh.to_dict(t) is not t


def test_too_few_points_or_wrong_shape_is_no_ghost():
    assert trace_of([5]) is None and trace_of([]) is None and trace_of(["a", "b", None]) is None
    assert trace_of("abc") is None and gh.make_trace(list(range(gh.HARD_INPUT_LIMIT + 1))) is None
    for bad in (None, 5, "x", [], [1, 2, 3], {}, {"values": 5}, {"values": [1]}, {"values": ["a", "b"]},
                {"turns": 10}, True):
        assert gh.load(bad) is None


def test_old_saves_without_a_trace_load_as_none():
    assert gh.load(None) is None and gh.value_at(None, 1) is None
    assert gh.compare([1, 2, 3], None) is None


def test_load_cleans_a_tampered_trace():
    t = gh.load({"v": 99, "turns": "lots", "values": [1, "x", float("nan"), 2, None, 3, 10 ** 400], "label": "\x00Best\n run\x00",
                 "extra": "ignored"})
    assert t == {"v": 1, "turns": 3, "values": [1, 2, 3], "label": "Best run"}
    huge = gh.load({"turns": 10 ** 12, "values": [1, 2, 3]})
    assert huge["turns"] == gh.MAX_TURNS
    assert gh.load({"turns": -5, "values": [1, 2, 3]})["turns"] == 3
    assert gh.load({"turns": 0, "values": [1, 2, 3]})["turns"] == 3
    assert gh.load({"turns": float("nan"), "values": [1, 2, 3]})["turns"] == 3
    assert gh.load({"turns": True, "values": [1, 2, 3]})["turns"] == 3
    # more points than turns: the shorter claim wins
    short = gh.load({"turns": 3, "values": list(range(10))})
    assert short["turns"] == 3 and len(short["values"]) == 3
    # oversized lists are thinned, never trusted
    big = gh.load({"turns": 3000, "values": list(range(3000))})
    assert len(big["values"]) == gh.MAX_LEN and big["turns"] == 3000
    assert gh.load({"turns": 3000, "values": list(range(gh.HARD_INPUT_LIMIT + 1))}) is None


def test_load_does_not_change_the_input():
    raw = {"turns": 5, "values": [1, "a", 3, 4, 5, 6], "label": "x"}
    snapshot = copy.deepcopy(raw)
    gh.load(raw)
    assert raw == snapshot


def test_value_at_reads_one_turn():
    t = trace_of([10, 20, 30, 40])
    assert [gh.value_at(t, i) for i in range(0, 7)] == [None, 10, 20, 30, 40, None, None]
    assert gh.value_at(t, 2.9) == 20
    for bad in (None, "2", True, float("nan"), float("inf"), [1]):
        assert gh.value_at(t, bad) is None


def test_value_at_spreads_a_thinned_run_over_its_length():
    t = {"turns": 1000, "values": list(range(0, 100))}
    assert gh.value_at(t, 1) == 0 and gh.value_at(t, 1000) == 99
    mid = gh.value_at(t, 500)
    assert 48 <= mid <= 51
    assert gh.value_at(t, 1001) is None
    last = [gh.value_at(t, i) for i in range(1, 1001)]
    assert last == sorted(last)


# -- the recorder -------------------------------------------------------------------------------
def test_recorder_keeps_one_number_per_turn_for_a_short_run():
    r = gh.Recorder()
    for v in (3, 5, 8, 13):
        r.record(v)
    assert r.trace("Run 1") == {"v": 1, "turns": 4, "values": [3, 5, 8, 13], "label": "Run 1"}


def test_recorder_needs_two_turns():
    r = gh.Recorder()
    assert r.trace() is None
    r.record(1)
    assert r.trace() is None
    r.record(2)
    assert r.trace()["turns"] == 2


@pytest.mark.parametrize("turns", [2, 50, 119, 120, 121, 240, 241, 1000, 5001])
def test_recorder_is_hard_capped_and_keeps_the_ends(turns):
    r = gh.Recorder()
    for i in range(turns):
        r.record(i)
    t = r.trace()
    assert len(t["values"]) <= gh.MAX_LEN and len(r.values) <= gh.MAX_LEN
    assert t["turns"] == turns
    assert t["values"][0] == 0 and t["values"][-1] == turns - 1
    assert t["values"] == sorted(t["values"])
    if turns <= gh.MAX_LEN - 1:
        assert t["values"] == list(range(turns))
    assert gh.value_at(t, turns) == turns - 1 and gh.value_at(t, 1) == 0
    # a thinned reading is close to the truth everywhere
    for turn in range(1, turns + 1, max(1, turns // 40)):
        assert abs(gh.value_at(t, turn) - (turn - 1)) <= turns / gh.MAX_LEN * 2 + 1


def test_recorder_never_exceeds_max_turns():
    r = gh.Recorder(max_len=5)
    for i in range(gh.MAX_TURNS + 50):
        r.record(i)
    assert r.turns == gh.MAX_TURNS and len(r.trace()["values"]) <= 5


def test_recorder_repeats_the_previous_number_for_a_bad_value():
    r = gh.Recorder()
    for v in (None, 4, "x", float("nan"), 6, float("inf")):
        r.record(v)
    assert r.trace()["values"] == [0, 4, 4, 4, 6, 6]
    assert r.trace()["turns"] == 6


def test_recorder_max_len_is_clamped_and_reset_works():
    assert gh.Recorder(max_len=10 ** 6).max_len == gh.MAX_LEN
    assert gh.Recorder(max_len=0).max_len == gh.MIN_POINTS + 1
    r = gh.Recorder()
    for i in range(10):
        r.record(i)
    r.reset()
    assert r.turns == 0 and r.values == [] and r.trace() is None


def test_recording_is_deterministic():
    def run():
        r = gh.Recorder()
        for i in range(777):
            r.record((i * 37) % 101 / 3)
        return json.dumps(r.trace("x"), sort_keys=True)
    assert run() == run()


# -- comparing ----------------------------------------------------------------------------------
BEST = {"turns": 6, "values": [0, 10, 20, 30, 40, 50]}


def test_compare_behind_ahead_level_and_ended():
    behind = gh.compare([0, 8, 15], BEST)
    assert behind["status"] == "behind" and behind["lead"] == 5 and behind["turn"] == 3 and behind["ghost"] == 20
    assert behind["gap"] == -5 and behind["best_turn"] == 3 and behind["best_gap"] == 5
    ahead = gh.compare([0, 12, 30], BEST)
    assert ahead["status"] == "ahead" and ahead["lead"] == 10 and ahead["best_turn"] is None and ahead["best_gap"] == 0
    level = gh.compare([0, 10, 20.004], BEST)
    assert level["status"] == "level" and level["lead"] == 0
    ended = gh.compare([0, 10, 20, 30, 40, 50, 60], BEST)
    assert ended["status"] == "ended" and ended["ghost"] is None and ended["gap"] is None


def test_compare_lower_is_better():
    r = gh.compare([0, 8, 15], BEST, higher_is_better=False)
    assert r["status"] == "ahead" and r["lead"] == 5
    r = gh.compare([0, 12, 30], BEST, higher_is_better=False)
    assert r["status"] == "behind" and r["lead"] == 10 and r["best_turn"] == 3 and r["best_gap"] == 10


def test_compare_best_gap_is_the_worst_moment_so_far():
    r = gh.compare([0, 10, 5, 29, 40], BEST)
    assert r["best_turn"] == 3 and r["best_gap"] == 15 and r["status"] == "level"


def test_compare_cleans_the_live_numbers():
    r = gh.compare([0, "bad", 8, None, float("nan")], BEST)
    assert r["turn"] == 5 and r["live"] == 8
    for bad in (None, [], "abc", 5, {}):
        assert gh.compare(bad, BEST) is None
    assert gh.compare(list(range(gh.HARD_INPUT_LIMIT + 1)), BEST) is None


def test_compare_does_not_change_its_inputs():
    live = [0, 1, "x"]
    best = copy.deepcopy(BEST)
    gh.compare(live, best)
    assert live == [0, 1, "x"] and best == BEST


# -- the sentence -------------------------------------------------------------------------------
def test_summary_wording():
    assert gh.summary(gh.compare([0, 8, 15], BEST)) == "ghost: your best run was 5 ahead at turn 3"
    assert gh.summary(gh.compare([0, 12, 30], BEST)) == "ghost: you are 10 ahead of your best run at turn 3"
    assert gh.summary(gh.compare([0, 10, 20], BEST)) == "ghost: level with your best run at turn 3"
    assert gh.summary(gh.compare([0] * 8, BEST)) == "ghost: your best run ended before turn 8"
    assert gh.summary(None) == "ghost: no earlier run to race yet"
    assert gh.summary(gh.compare([0, 8, 15], BEST), unit="%") == "ghost: your best run was 5% ahead at turn 3"
    assert gh.summary(gh.compare([0, 8, 15.5], BEST), label=" your Run 3 ") == "ghost: your Run 3 was 4.5 ahead at turn 3"


def test_format_number():
    assert [gh.format_number(x) for x in (0, -0.0, 5, 5.0, 5.5, 5.25, 5.254, 5.256, 1234567.891, 0.005)] == [
        "0", "0", "5", "5", "5.5", "5.25", "5.25", "5.26", "1234567.89", "0.01"]
