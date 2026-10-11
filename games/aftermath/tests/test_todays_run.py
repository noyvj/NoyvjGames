"""Z-5c, "Today's run": the page's shared button (shared/seed.js) hands Aftermath the UTC date's shared seed. It starts a
challenge-style run on the classic schedule at that seed (the severity draw), only between runs, and finishing that run tells
the shared daily record once, only when the page says the seed is today's. The one new save key appears only for such a run."""
import sys
import types

TODAY = "2026-10-20"


class FakeDaily:
    """Stands in for window.NoyvjSeed: `today_seed` is the one seed the page would call today's."""

    def __init__(self, today_seed, fail=False):
        self.today_seed = today_seed
        self.fail = fail
        self.completed = []
        self.daily = types.SimpleNamespace(isDaily=self.is_daily, markCompleted=self.mark)

    def is_daily(self, game, seed):
        assert game == "aftermath"
        return seed == self.today_seed

    def mark(self, game, info):
        if self.fail:
            raise RuntimeError("storage blocked")
        self.completed.append((game, info.text))


def _install_page(m, today_seed, fail=False):
    js = sys.modules["js"]
    page = FakeDaily(today_seed, fail)
    js.window = types.SimpleNamespace(NoyvjSeed=page)
    js.Object = types.SimpleNamespace(new=lambda: types.SimpleNamespace())
    return page


def _today(m):
    return m.shared_seed.daily_seed("aftermath", TODAY)


def _finish(env):
    while not env.run.is_complete():
        env.resolve_event()


def test_the_button_starts_the_classic_schedule_at_todays_draw(game_env):
    m = game_env.module
    _install_page(m, _today(m))
    message = m.start_todays_run(_today(m))
    run = game_env.run
    assert message.startswith("Today's run started") and "finishing it counts for today" in message
    assert run.normalised and run.scenario == "classic" and not run.extended and run.custom_events is None
    assert run.draw == m.int_from_seed_text(_today(m))
    assert run.schedule == m.SCENARIOS["classic"]["schedule"]
    assert run.challenge["daily_seed"] == _today(m)
    assert game_env.elements["challenge-status"].innerText == ""     # the page shows the sentence beside the button
    assert "Today's run" in game_env.elements["challenge-banner"].innerText
    assert game_env.elements["challenge-banner"].hidden is False


def test_the_same_day_gives_the_same_events_and_another_day_a_different_draw(game_env):
    m = game_env.module

    def severities(seed):
        state, _e = m.challenge_run_from_code(m.daily_run_code(seed)[0])
        return [state.severity_at(i) for i in range(7)]

    today = _today(m)
    assert severities(today) == severities(today)
    seeds = [m.shared_seed.daily_seed("aftermath", "2026-10-%02d" % d) for d in range(10, 20)]
    assert len({tuple(severities(seed)) for seed in seeds}) > 1


def test_a_run_under_way_is_never_replaced(game_env):
    m = game_env.module
    _install_page(m, _today(m))
    game_env.resolve_event()
    before, resources = game_env.run, game_env.run.resources
    message = m.start_todays_run(_today(m))
    assert "under way" in message and "Nothing was changed" in message and "Finish your current run first" in message
    assert game_env.run is before and game_env.run.resources == resources and not game_env.run.normalised


def test_a_run_with_resources_already_spent_counts_as_under_way(game_env):
    m = game_env.module
    _install_page(m, _today(m))
    game_env.invest_resilience()
    before = game_env.run
    assert before.resources != before.starting_resources
    assert "Nothing was changed" in m.start_todays_run(_today(m))
    assert game_env.run is before


def test_a_fresh_or_finished_run_can_start_it(game_env):
    m = game_env.module
    _install_page(m, _today(m))
    assert m.start_todays_run(_today(m)).startswith("Today's run started")
    _finish(game_env)
    assert game_env.run.is_complete()
    assert m.start_todays_run(_today(m)).startswith("Today's run started")
    assert game_env.run.event_index == 0


def test_a_bad_or_foreign_seed_changes_nothing_and_says_why(game_env):
    m = game_env.module
    before = game_env.run
    assert "for TIDE" in m.start_todays_run("TIDE-K7F2Q")
    assert "Enter a seed" in m.start_todays_run("")
    assert game_env.run is before and not before.normalised


def test_finishing_todays_run_records_it_once_and_pays_nothing(game_env):
    m = game_env.module
    page = _install_page(m, _today(m))
    kp, history, awarded = m.skill_tree.knowledge_points, list(m.run_history), m.highest_awarded_run
    m.start_todays_run(_today(m))
    _finish(game_env)
    assert len(page.completed) == 1 and page.completed[0][0] == "aftermath" and page.completed[0][1].startswith("Ended with ")
    assert (m.skill_tree.knowledge_points, m.run_history, m.highest_awarded_run) == (kp, history, awarded)
    text = game_env.elements["run-summary-display"].innerText
    assert text.startswith("Today's run finished: you ended with") and "same events" in text and "earns no knowledge" in text
    assert "Their run" not in text and "missed" not in text.lower()
    assert m.meta["challenge_runs"] == 1


def test_an_older_days_seed_a_friends_challenge_and_an_ordinary_run_record_nothing(game_env):
    m = game_env.module
    page = _install_page(m, _today(m))
    _finish(game_env)                                       # an ordinary run
    m.start_todays_run(m.shared_seed.daily_seed("aftermath", "2026-10-19"))     # yesterday's seed, begun today
    _finish(game_env)
    code = m.shared_run_code.encode({"game": "aftermath", "seed": _today(m), "mode": "classic", "score": 150})
    m.start_challenge(code)                                  # a friend's code that happens to carry today's seed
    assert "daily_seed" not in game_env.run.challenge
    _finish(game_env)
    assert page.completed == []


def test_a_failing_shared_record_never_breaks_finishing(game_env):
    m = game_env.module
    _install_page(m, _today(m), fail=True)
    m.start_todays_run(_today(m))
    _finish(game_env)
    assert game_env.run.is_complete() and m.meta["challenge_runs"] == 1


def test_without_the_shared_script_nothing_happens(game_env):
    m = game_env.module
    sys.modules["js"].window = types.SimpleNamespace()          # an old page: no NoyvjSeed at all
    m.start_todays_run(_today(m))
    _finish(game_env)
    assert game_env.run.is_complete()


def test_the_save_gains_one_key_only_for_todays_run_and_it_round_trips(game_env):
    m = game_env.module
    page = _install_page(m, _today(m))
    assert "challenge_daily" not in m.get_state()                       # an ordinary run
    m.start_challenge(m.shared_run_code.encode({"game": "aftermath", "seed": m.seed_text_for_int(7), "mode": "classic"}))
    assert "challenge_code" in m.get_state() and "challenge_daily" not in m.get_state()
    game_env.run.event_index = 0
    m.start_todays_run(_today(m))
    game_env.resolve_event()
    state = m.get_state()
    assert state["challenge_daily"] is True and "challenge_code" in state
    m.load_state(state)
    assert game_env.run.challenge["daily_seed"] == _today(m) and game_env.run.event_index == 1
    assert "Today's run" in game_env.elements["challenge-banner"].innerText
    _finish(game_env)
    assert len(page.completed) == 1


def test_old_or_damaged_saves_load_unchanged(game_env):
    m = game_env.module
    m.start_challenge(m.shared_run_code.encode({"game": "aftermath", "seed": m.seed_text_for_int(7), "mode": "classic"}))
    state = m.get_state()
    for bad in ("yes", 1, None, False, ["x"]):
        m.load_state({**state, "challenge_daily": bad})
        assert game_env.run.normalised and "daily_seed" not in game_env.run.challenge
    m.load_state(state)                                                 # no key at all: a friend's challenge, as before
    assert "daily_seed" not in game_env.run.challenge
    plain = {k: v for k, v in state.items() if not k.startswith("challenge")}
    m.load_state({**plain, "challenge_daily": True})                    # a stray key without a code does nothing
    assert not game_env.run.normalised


def test_leaving_an_unfinished_todays_run_loses_nothing(game_env):
    m = game_env.module
    _install_page(m, _today(m))
    awarded = m.highest_awarded_run
    m.start_todays_run(_today(m))
    game_env.resolve_event()
    m.leave_challenge()
    assert not game_env.run.normalised and m.highest_awarded_run == awarded
