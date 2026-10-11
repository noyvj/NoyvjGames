"""QA-1 code-review regressions: a damaged save field of an unhashable type (a list or a dict where a name is
expected) used to raise "unhashable type" while loading or drawing, and the season report was stored unchecked."""

import copy

import advisors
import archive
import challenges
import citizens
import log
import save
import sim

UNHASHABLE = ([], {}, [1, "a"], {"a": 1})


def test_a_log_entry_with_unhashable_fields_is_cleaned_not_raised():
    for junk in UNHASHABLE:
        entry = log.LogEntry.from_dict({"season": junk, "era": junk, "kind": junk, "text": "A line."})
        assert (entry.season, entry.era, entry.kind) == (0, "", "beat")
    assert log.LogEntry.from_dict({"text": ["x"]}) is None
    ok = log.LogEntry.from_dict({"season": 4, "era": "tribal", "kind": "beat", "text": "Fine."})
    assert (ok.season, ok.era, ok.kind, ok.text) == (4, "tribal", "beat", "Fine.")


def test_a_chronicle_restore_survives_unhashable_milestones_and_label():
    chronicle = log.Chronicle()
    chronicle.restore({"population_milestones_hit": [[1], {}, 10, True], "last_score_label": ["Steady"], "entries": []})
    assert chronicle._population_milestones_hit == {10}
    assert chronicle._last_score_label is None


def test_citizen_advisor_challenge_and_archive_cleaners_refuse_unhashable_ids():
    for junk in UNHASHABLE:
        assert citizens.clean_spot({"name": "A B", "line": "x", "season": 3, "event": junk}) is None
        assert advisors._clean_advice({"id": junk}) is None
        assert challenges.clean({"active": {"id": junk, "baseline": 1.0, "seasons_done": 0}}) == challenges.clean(None)
        record = archive.clean_record({
            "saved_on": "2026-09-21", "era": "tribal", "seasons": 5, "peak_population": 9, "peak_score": 80.0,
            "rank": None, "scenario": junk, "hard_mode": False, "achievements": 2,
        })
        assert record["scenario"] == sim.DEFAULT_SCENARIO


def test_the_season_report_is_none_or_a_dict_of_plain_numbers(game_env):
    base = game_env.module.get_state()
    game_env.advance_season(2)
    base = game_env.module.get_state()
    assert isinstance(base["current_state"]["city"]["last_report"], dict)
    for junk in ("x", -5, [], [1, 2], True, 3.5):
        data = copy.deepcopy(base)
        data["current_state"]["city"]["last_report"] = junk
        before = copy.deepcopy(game_env.module.state.last_report)
        assert game_env.module.load_state(data) is True
        assert game_env.module.state.last_report == before
        game_env.advance_season(1)
        game_env.module.get_state()
    data = copy.deepcopy(base)
    data["current_state"]["city"]["last_report"] = {"food_gathered": 4.5, "births": "many", "deaths": float("nan"), 7: 1}
    assert game_env.module.load_state(data) is True
    assert game_env.module.state.last_report == {"food_gathered": 4.5}
    data["current_state"]["city"]["last_report"] = None
    assert game_env.module.load_state(data) is True
    assert game_env.module.state.last_report is None


def test_a_save_version_of_infinity_is_refused_not_raised():
    campaign = save.Campaign()
    assert campaign.load_dict({"save_version": float("inf")}) is False
