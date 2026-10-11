"""G-30: the last five community comparisons, kept in localStorage."""

import json
import sys

from .fakes import FakeStorage


def _storage(initial=None):
    storage = FakeStorage(initial)
    sys.modules["js"].localStorage = storage
    return storage


def test_starts_empty_with_a_hint(game_env):
    m = game_env.module
    assert m.compare_history == []
    game_env.toggle_community_compare()
    assert "last five comparisons will be listed" in game_env.elements["community-compare-panel"].innerHTML


def test_a_result_is_kept_and_shown_newest_first(game_env):
    m = game_env.module
    storage = _storage()
    game_env.toggle_community_compare()
    assert m.record_compare_result(70, 120) is True
    game_env.advance_round()
    assert m.record_compare_result(64, 130) is True
    html = game_env.elements["community-compare-panel"].innerHTML
    assert html.index("Round 2") < html.index("Round 1")
    assert "less than 64% of 130" in html
    assert json.loads(storage.data[m.COMPARE_HISTORY_KEY])[-1]["better_than"] == 64


def test_only_the_newest_five_stay(game_env):
    m = game_env.module
    _storage()
    for i in range(8):
        game_env.advance_round()
        m.record_compare_result(10 + i, 200)
    assert len(m.compare_history) == 5
    assert [e["better_than"] for e in m.compare_history] == [13, 14, 15, 16, 17]


def test_repeating_the_same_result_is_ignored(game_env):
    m = game_env.module
    _storage()
    assert m.record_compare_result(55, 90) is True
    assert m.record_compare_result(55, 90) is False
    assert len(m.compare_history) == 1
    assert m.record_compare_result(56, 90) is True


def test_nonsense_results_are_refused(game_env):
    m = game_env.module
    _storage()
    for better, count in ((-1, 10), (101, 10), (50, 0), ("x", 5), (None, None), (float("nan"), 5), (50.5, 10), (True, 5)):
        assert m.record_compare_result(better, count) is False, (better, count)
    assert m.compare_history == []


def test_history_is_read_back_and_cleaned(game_env):
    m = game_env.module
    good = {"round": 4, "better_than": 60, "count": 100, "factor": 1.4}
    junk = [
        {"round": 0, "better_than": 60, "count": 100, "factor": 1.4},
        {"round": 4, "better_than": 160, "count": 100, "factor": 1.4},
        {"round": 4, "better_than": 60, "count": 100},
        "x", 5, None,
    ]
    _storage({m.COMPARE_HISTORY_KEY: json.dumps(junk + [good] * 8)})
    loaded = m.load_compare_history()
    assert loaded == [good] * 5
    _storage({m.COMPARE_HISTORY_KEY: "{oops"})
    assert m.load_compare_history() == []
    _storage({m.COMPARE_HISTORY_KEY: json.dumps({"a": 1})})
    assert m.load_compare_history() == []


def test_recording_while_closed_does_not_open_the_panel(game_env):
    m = game_env.module
    _storage()
    m.record_compare_result(50, 50)
    assert game_env.elements["community-compare-panel"].hidden is True


def test_history_stays_out_of_the_save(game_env):
    m = game_env.module
    _storage()
    m.record_compare_result(50, 50)
    assert "compare" not in json.dumps(m.get_state())
