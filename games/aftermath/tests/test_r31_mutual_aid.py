"""R-31: Mutual aid from neighbouring towns. Opt-in (Settings, default OFF); once the community's average tree
strength reaches the threshold, each run gets ONE fixed gift of resources before one fixed event, chosen from
the run number alone and shown beforehand. A run that got aid is tagged and kept off every comparison."""

import json
import sys
import types
from pathlib import Path

import pytest

GAME_DIR = Path(__file__).resolve().parent.parent
KEY = "aftermath-neighbour-aid"


class _Board:
    def __init__(self):
        self.calls = []

    def report(self, game, board, score, detail):
        self.calls.append((game, board, score, detail))


def _board():
    board = _Board()
    sys.modules["js"].window = types.SimpleNamespace(NoyvjLeaderboard=board)
    return board


def _on(env, community=4.0):
    env.local_storage.setItem(KEY, "true")
    if community is not None:
        env.module.set_community_resilience(community)


def _finish(env):
    while not env.run.is_complete():
        env.resolve_event()


def _rich(env):
    env.run.resources = 10 ** 6


# ---- the rule: off by default, fixed by the run number --------------------------------------------

def test_off_by_default_even_with_a_strong_community(game_env):
    m = game_env.module
    m.set_community_resilience(7.0)
    assert not m.neighbour_aid_enabled()
    assert m.neighbour_aid_plan(game_env.run) is None
    assert m.neighbour_aid_message() == ""
    assert game_env.elements["neighbour-aid-display"].hidden is True
    _finish(game_env)
    assert game_env.run.aid_given == 0
    assert all("aid" not in e for e in game_env.run.event_log)


def test_schedule_is_a_pure_function_of_the_run_number(game_env):
    m = game_env.module
    for run_number in range(1, 300):
        first = m.neighbour_aid_schedule(run_number, 7)
        assert first == m.neighbour_aid_schedule(run_number, 7)
        index, amount = first
        assert 1 <= index <= 5  # never the first or the last of seven events
        assert amount in m.NEIGHBOUR_AID_AMOUNTS
    spots = {m.neighbour_aid_schedule(n, 7) for n in range(1, 300)}
    assert {i for i, _ in spots} == {1, 2, 3, 4, 5}
    assert {a for _, a in spots} == set(m.NEIGHBOUR_AID_AMOUNTS)


def test_extended_runs_use_their_longer_schedule(game_env):
    m = game_env.module
    indexes = {m.neighbour_aid_schedule(n, 14)[0] for n in range(1, 300)}
    assert min(indexes) == 1 and max(indexes) == 12


def test_no_randomness_is_used(game_env, monkeypatch):
    m = game_env.module
    import random
    monkeypatch.setattr(random, "random", lambda: (_ for _ in ()).throw(AssertionError("random used")))
    _on(game_env)
    _rich(game_env)
    _finish(game_env)
    assert game_env.run.aid_given in m.NEIGHBOUR_AID_AMOUNTS
    block = (GAME_DIR / "game.py").read_text(encoding="utf-8").split("R-31: mutual aid")[1].split("class RunState")[0]
    assert "import random" not in block and "random." not in block


def test_aid_arrives_once_at_the_planned_event_and_adds_exactly_that_much(game_env):
    m = game_env.module
    _on(game_env)
    run = game_env.run
    _rich(game_env)
    plan = m.neighbour_aid_plan(run)
    assert plan["index"] == m.neighbour_aid_schedule(run.run_number, len(run.schedule))[0]
    assert plan["event"] == run.schedule[plan["index"]]
    while not run.is_complete():
        before = run.resources
        index = run.event_index
        income = run.growth_capacity * m.GROWTH_INCOME_PER_UNIT
        game_env.resolve_event()
        entry = run.event_log[-1]
        if index == plan["index"]:
            assert entry["aid"] == plan["amount"]
            assert run.resources == pytest.approx(max(0.0, before + income + plan["amount"] - entry["damage"]))
        else:
            assert "aid" not in entry
            assert run.resources == pytest.approx(max(0.0, before + income - entry["damage"]))
    assert [e for e in run.event_log if "aid" in e] == [run.event_log[plan["index"]]]
    assert run.aid_given == plan["amount"]
    assert m.neighbour_aid_plan(run) is None


def test_the_same_run_number_gets_the_same_help_every_time(game_env):
    m = game_env.module
    _on(game_env)
    first = m.neighbour_aid_plan(m.RunState(run_number=6))
    again = m.neighbour_aid_plan(m.RunState(run_number=6))
    assert first == again and first is not None


def test_help_is_shown_before_the_run_starts_and_names_event_and_amount(game_env):
    m = game_env.module
    _on(game_env)
    m.render()
    plan = m.neighbour_aid_plan(game_env.run)
    text = game_env.elements["neighbour-aid-display"].innerText
    assert game_env.elements["neighbour-aid-display"].hidden is False
    assert f"before event {plan['index'] + 1} ({m.EVENT_LABEL[plan['event']]})" in text
    assert f"+{plan['amount']} resources" in text
    assert "never luck" in text and "off the boards, no run code" in text


def test_after_the_gift_the_line_and_last_event_say_so(game_env):
    m = game_env.module
    _on(game_env)
    _rich(game_env)
    plan = m.neighbour_aid_plan(game_env.run)
    while game_env.run.event_index <= plan["index"]:
        game_env.resolve_event()
    text = game_env.elements["neighbour-aid-display"].innerText
    assert text.startswith(f"Neighbouring towns sent help before event {plan['index'] + 1}: +{plan['amount']} resources.")
    assert f"neighbours sent +{plan['amount']}" in game_env.elements["last-event-display"].innerText
    _finish(game_env)
    assert "sent help" in game_env.elements["neighbour-aid-display"].innerText  # still told on the summary screen


def test_new_run_gets_its_own_plan(game_env):
    m = game_env.module
    _on(game_env)
    _rich(game_env)
    _finish(game_env)
    first = game_env.run.aid_given
    game_env.start_new_run()
    assert game_env.run.aid_given == 0
    plan = m.neighbour_aid_plan(game_env.run)
    assert plan == {"index": plan["index"], "amount": m.neighbour_aid_schedule(2, 7)[1], "event": game_env.run.schedule[plan["index"]]}
    assert first in m.NEIGHBOUR_AID_AMOUNTS


# ---- fails soft -----------------------------------------------------------------------------------

def test_no_community_figure_means_no_event_and_says_why(game_env):
    m = game_env.module
    _on(game_env, community=None)
    assert m.community_resilience is None
    assert m.neighbour_aid_plan(game_env.run) is None
    assert "not available" in m.neighbour_aid_message()
    _rich(game_env)
    _finish(game_env)
    assert game_env.run.aid_given == 0


@pytest.mark.parametrize("value, helped", [(2.99, False), (3.0, True), (3.01, True), (7.0, True), (0.0, False)])
def test_threshold(game_env, value, helped):
    m = game_env.module
    _on(game_env, community=value)
    assert (m.neighbour_aid_plan(game_env.run) is not None) is helped
    if not helped:
        assert "below the 3 needed" in m.neighbour_aid_message()


@pytest.mark.parametrize("bad", [None, "4", float("nan"), float("inf"), -1, 7.5, True, [], {}])
def test_unusable_figures_are_no_figure(game_env, bad):
    m = game_env.module
    m.set_community_resilience(5.0)
    assert m.set_community_resilience(bad) is False
    assert m.community_resilience is None
    assert game_env.local_storage.getItem(m.COMMUNITY_RESILIENCE_CACHE_KEY) is None  # and no stale copy survives


def test_a_good_figure_is_cached_and_restored_without_touching_the_saved_badge(game_env):
    m = game_env.module
    marker = m._storage_state["last_ok"]
    assert m.set_community_resilience(4.5) is True
    assert m._storage_state["last_ok"] == marker  # a cached figure is not player progress
    stored = json.loads(game_env.local_storage.getItem(m.COMMUNITY_RESILIENCE_CACHE_KEY))
    assert stored["mean"] == 4.5
    m.community_resilience = None
    assert m.load_cached_community_resilience() is True
    assert m.community_resilience == 4.5


def test_a_stale_or_damaged_cache_is_ignored(game_env):
    m = game_env.module
    now = m._now()
    for raw in (
        None, "", "not json", "[]", json.dumps({"mean": 4, "at": now - 15 * 86400}),
        json.dumps({"mean": 9, "at": now}), json.dumps({"mean": 4}), json.dumps({"mean": "4", "at": now}),
        json.dumps({"mean": 4, "at": now + 10 * 86400}),
    ):
        m.community_resilience = None
        if raw is None:
            game_env.local_storage.removeItem(m.COMMUNITY_RESILIENCE_CACHE_KEY)
        else:
            game_env.local_storage.setItem(m.COMMUNITY_RESILIENCE_CACHE_KEY, raw)
        assert m.load_cached_community_resilience() is False
        assert m.community_resilience is None
    game_env.local_storage.setItem(m.COMMUNITY_RESILIENCE_CACHE_KEY, json.dumps({"mean": 4, "at": now - 13 * 86400}))
    assert m.load_cached_community_resilience() is True


def test_a_broken_storage_reads_as_switched_off(game_env, monkeypatch):
    m = game_env.module

    def boom(key):
        raise RuntimeError("blocked")

    monkeypatch.setattr(game_env.local_storage, "getItem", boom)
    assert m.neighbour_aid_enabled() is False
    assert m.load_cached_community_resilience() is False


def test_enabling_after_the_help_point_has_passed_gives_nothing(game_env):
    m = game_env.module
    _rich(game_env)
    plan_index = m.neighbour_aid_schedule(game_env.run.run_number, 7)[0]
    while game_env.run.event_index <= plan_index:
        game_env.resolve_event()
    _on(game_env)
    assert m.neighbour_aid_plan(game_env.run) is None
    assert "has passed" in m.neighbour_aid_message()
    _finish(game_env)
    assert game_env.run.aid_given == 0


def test_challenge_runs_and_built_schedules_never_get_aid(game_env):
    m = game_env.module
    _on(game_env)
    challenge = m.RunState(run_number=2, normalised=True, draw=5)
    custom = m.RunState(run_number=2, custom_events=["flood", "storm", "heatwave"], custom_name="mine")
    for run in (challenge, custom):
        assert m.neighbour_aid_plan(run) is None
        assert "does not apply" in m.neighbour_aid_message(run)
        run.resources = 10 ** 6
        while not run.is_complete():
            run.resolve_next_event()
        assert run.aid_given == 0


# ---- tagged runs stay out of every comparison -----------------------------------------------------

def test_an_aided_run_never_reaches_the_hardest_schedule_board(game_env):
    board = _board()
    _on(game_env)
    _rich(game_env)
    _finish(game_env)
    assert game_env.run.aid_given > 0
    assert board.calls == []


def test_an_unaided_run_still_reports(game_env):
    board = _board()
    _rich(game_env)
    _finish(game_env)
    assert len(board.calls) == 1 and board.calls[0][1] == "hardest_schedule"


def test_run_log_entry_is_tagged(game_env):
    m = game_env.module
    _on(game_env)
    _rich(game_env)
    _finish(game_env)
    entry = m.run_log_history[-1]
    assert entry["neighbour_aid"] == game_env.run.aid_given > 0
    assert sum(e.get("aid", 0) for e in entry["event_log"]) == entry["neighbour_aid"]


def test_an_unaided_run_log_entry_has_no_tag(game_env):
    m = game_env.module
    _rich(game_env)
    _finish(game_env)
    assert "neighbour_aid" not in m.run_log_history[-1]


def _severe_entry(run_number, aid=None):
    return {
        "run_number": run_number, "score": 120.0, "resilience_capacity": 2, "growth_capacity": 1,
        "damage_taken": 90.0, "knowledge_earned": 6, "skill_strength": 3,
        "event_log": [{"type": "flood", "damage": 30.0, "severity": 1.2}] * 7,
        **({"neighbour_aid": aid} if aid else {}),
    }


def test_toughest_run_badge_ignores_aided_runs(game_env):
    m = game_env.module
    m.run_log_history[:] = [_severe_entry(2, aid=20)]
    assert m.toughest_survived_run_badge_earned() is False
    assert "not earned yet" in m.toughest_badge_title()
    m.run_log_history.append(_severe_entry(3))
    assert m.toughest_survived_run_badge_earned() is True
    assert "run 3" in m.toughest_badge_title()


def test_aided_runs_are_never_a_record_and_set_no_bar(game_env):
    m = game_env.module
    plain = lambda n, score: dict(_severe_entry(n), score=score)  # noqa: E731
    aided = dict(plain(3, 900.0), neighbour_aid=25)
    m.run_log_history[:] = [plain(1, 100.0), plain(2, 200.0), aided, plain(4, 150.0), plain(5, 250.0)]
    assert m.new_record_run_indexes() == {1, 4}


def test_a_past_runs_card_names_the_aid(game_env):
    m = game_env.module
    card = m._past_run_card(0, _severe_entry(2, aid=20), False)
    assert "neighbour aid +20" in card.children[0].innerText
    plain = m._past_run_card(0, _severe_entry(2), False)
    assert "neighbour aid" not in plain.children[0].innerText


def test_aided_runs_get_no_run_code_and_say_so(game_env):
    m = game_env.module
    _on(game_env)
    _rich(game_env)
    _finish(game_env)
    assert m.run_code_fields() is None and m.make_run_code() is None
    m.render()
    assert "no run code" in game_env.elements["run-end-code-note"].innerText
    assert game_env.elements["run-end-code-wrap"].hidden is True  # no (stale) code box to copy from
    # an ordinary finished run still has one
    game_env.local_storage.setItem(KEY, "false")
    game_env.start_new_run()
    _rich(game_env)
    _finish(game_env)
    assert m.run_code_fields() is not None
    assert game_env.elements["run-end-code-wrap"].hidden is False


def test_shared_texts_mention_the_aid(game_env):
    m = game_env.module
    _on(game_env)
    _rich(game_env)
    _finish(game_env)
    assert f"with neighbour aid +{game_env.run.aid_given}" in m.run_summary_text()
    assert any("neighbour aid" in str(s) for s in m.copy_result_fields()["stats"])


def test_achievements_do_not_depend_on_aid(game_env):
    """Every achievement stays reachable without aid: the setting is off by default and none of the achievement
    code or catalog mentions aid. (The existing achievement tests earn them all with it off.)"""
    m = game_env.module
    import inspect
    catalog = (GAME_DIR / "achievements.json").read_text(encoding="utf-8").lower()
    assert "aid" not in catalog and "neighbour" not in catalog
    source = inspect.getsource(m.achievement_ids_earned) + inspect.getsource(m._note_achievement_progress)
    assert "aid" not in source.lower()
    assert m.neighbour_aid_enabled() is False


# ---- saves ----------------------------------------------------------------------------------------

def test_save_and_load_keep_the_plan_and_never_pay_twice(game_env):
    m = game_env.module
    _on(game_env)
    _rich(game_env)
    plan = m.neighbour_aid_plan(game_env.run)
    before = m.get_state()
    m.load_state(json.loads(json.dumps(before)))
    assert m.neighbour_aid_plan(game_env.run) == plan
    while game_env.run.event_index <= plan["index"]:
        game_env.resolve_event()
    assert game_env.run.aid_given == plan["amount"]
    saved = json.loads(json.dumps(m.get_state()))
    m.load_state(saved)
    assert game_env.run.aid_given == plan["amount"]
    assert m.neighbour_aid_plan(game_env.run) is None
    _finish(game_env)
    assert game_env.run.aid_given == plan["amount"]


def test_older_saves_load_with_no_aid(game_env):
    m = game_env.module
    data = m.get_state()
    assert all("aid" not in e for e in data["event_log"])
    m.load_state(data)
    assert game_env.run.aid_given == 0


def test_damaged_aid_values_in_a_save_count_as_none(game_env):
    m = game_env.module
    _rich(game_env)
    game_env.resolve_event()
    data = json.loads(json.dumps(m.get_state()))
    data["event_log"][0]["aid"] = "lots"
    m.load_state(data)
    assert game_env.run.aid_given == 0


# ---- the Settings switch and the page --------------------------------------------------------------

def test_the_checkbox_change_redraws_the_line(game_env):
    m = game_env.module
    m.set_community_resilience(5.0)
    assert game_env.elements["neighbour-aid-display"].hidden is True
    game_env.local_storage.setItem(KEY, "true")
    game_env.elements["neighbour-aid-checkbox"].dispatch("change", None)
    assert game_env.elements["neighbour-aid-display"].hidden is False
    game_env.local_storage.setItem(KEY, "false")
    game_env.elements["neighbour-aid-checkbox"].dispatch("change", None)
    assert game_env.elements["neighbour-aid-display"].hidden is True


def test_receiving_the_figure_redraws_the_line(game_env):
    game_env.local_storage.setItem(KEY, "true")
    game_env.module.render()
    assert "not available" in game_env.elements["neighbour-aid-display"].innerText
    game_env.module.set_community_resilience(4.0)
    assert "will send help" in game_env.elements["neighbour-aid-display"].innerText


@pytest.mark.parametrize("page", ["index.html", "pc.html"])
def test_both_pages_have_the_switch_the_line_and_the_fetch(page):
    html = (GAME_DIR / page).read_text(encoding="utf-8")
    assert 'id="neighbour-aid-checkbox"' in html and 'id="neighbour-aid-display"' in html
    checkbox = html[html.index('id="neighbour-aid-checkbox"'):][:80]
    assert "checked" not in checkbox  # default OFF
    assert "set_community_resilience" in html and "/stats/games/aftermath" in html
    assert "skill_tree_strength" in html and "hub_reduce_data" in html


def test_settings_js_and_game_py_agree_on_the_key_and_reset_turns_it_off():
    js = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
    py = (GAME_DIR / "game.py").read_text(encoding="utf-8")
    assert f'NEIGHBOUR_AID_KEY = "{KEY}"' in js
    assert f'NEIGHBOUR_AID_STORAGE_KEY = "{KEY}"' in py
    reset = js[js.index("settingsResetButton.addEventListener"):]
    assert 'setItem(NEIGHBOUR_AID_KEY, "false")' in reset
