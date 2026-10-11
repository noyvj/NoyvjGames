"""Z-5c, "Today's run": the page's shared button (shared/seed.js) hands Grid the UTC date's shared seed; it becomes the run's
seed only before anything is built or advanced, and finishing that run (Career, Finish run) tells the shared daily record once,
only when the page says the seed is today's. Nothing new is saved: the run's seed is the whole of it."""
import sys
import types

from .test_career import _install_storage, _play

TODAY = "2026-10-20"


class FakeDaily:
    """Stands in for window.NoyvjSeed: `today` is the one seed the page would call today's."""

    def __init__(self, seed_lib, today_seed, fail=False):
        self.today_seed = today_seed
        self.fail = fail
        self.completed = []
        self.footer = []
        self.daily = types.SimpleNamespace(isDaily=self.is_daily, markCompleted=self.mark)
        self.set = self.footer.append
        self.seed_lib = seed_lib

    def is_daily(self, game, seed):
        assert game == "grid"
        return seed == self.today_seed

    def mark(self, game, info):
        if self.fail:
            raise RuntimeError("storage blocked")
        self.completed.append((game, info.text))


def _install_page(g, today_seed, fail=False):
    js = sys.modules["js"]
    js.window = types.SimpleNamespace(NoyvjSeed=FakeDaily(g.seed_lib, today_seed, fail))
    js.Object = types.SimpleNamespace(new=lambda: types.SimpleNamespace())
    return js.window.NoyvjSeed


def _today_seed(g):
    return g.seed_lib.daily_seed("grid", TODAY)


def test_the_button_sets_todays_seed_on_a_fresh_run(game_env):
    g = game_env.module
    page = _install_page(g, _today_seed(g))
    message = g.start_todays_run(_today_seed(g))
    assert game_env.state.seed == _today_seed(g) and game_env.state.unstarted()
    assert _today_seed(g) in message and "counts it for today" in message
    assert page.footer == [_today_seed(g)]


def test_the_same_day_gives_the_same_run_and_another_day_a_different_one(game_env):
    g = game_env.module

    def play(seed):
        s = g.GridState()
        s.seed = seed
        s.weather_variability_enabled = True
        s.plant_counts["coal"] = 3
        s.plant_counts["solar"] = 3
        for _ in range(12):
            s.advance_round()
        return repr((s.funds, s.emissions, [e["type"] for e in s.event_log], s.weather_log))

    today = _today_seed(g)
    assert play(today) == play(today)
    seeds = [g.seed_lib.daily_seed("grid", "2026-10-%02d" % d) for d in range(10, 20)]
    assert len({play(seed) for seed in seeds}) > 1


def test_a_run_already_under_way_is_never_replaced(game_env):
    g = game_env.module
    page = _install_page(g, _today_seed(g))
    old_seed = game_env.state.seed
    _play(game_env, 3)
    funds, rounds = game_env.state.funds, game_env.state.round_number
    message = g.start_todays_run(_today_seed(g))
    assert "Nothing was changed" in message and "Career, Finish run" in message
    assert game_env.state.seed == old_seed and game_env.state.funds == funds and game_env.state.round_number == rounds
    assert page.footer == [old_seed]       # the footer is given the run's own seed back


def test_one_build_is_enough_to_refuse(game_env):
    g = game_env.module
    _install_page(g, _today_seed(g))
    game_env.state.cumulative_built["solar"] = 1
    old = game_env.state.seed
    assert "Nothing was changed" in g.start_todays_run(_today_seed(g))
    assert game_env.state.seed == old


def test_the_sandbox_and_a_bad_seed_are_refused_in_words(game_env):
    g = game_env.module
    _install_page(g, _today_seed(g))
    old = game_env.state.seed
    g.sandbox_active = True
    assert "sandbox" in g.start_todays_run(_today_seed(g))
    g.sandbox_active = False
    assert "for TIDE" in g.start_todays_run("TIDE-K7F2Q")
    assert game_env.state.seed == old


def test_finishing_a_run_on_todays_seed_records_it_once(game_env):
    g = game_env.module
    page = _install_page(g, _today_seed(g))
    _install_storage()
    g.start_todays_run(_today_seed(g))
    game_env.state.plant_counts["solar"] = 5
    _play(game_env, 6)
    assert g.finish_run() is not None
    assert len(page.completed) == 1 and page.completed[0][0] == "grid" and page.completed[0][1].startswith("Grade ")
    assert game_env.state.seed != _today_seed(g)       # the next run is a fresh one


def test_an_ordinary_run_or_an_older_days_seed_records_nothing(game_env):
    g = game_env.module
    page = _install_page(g, _today_seed(g))
    _install_storage()
    game_env.state.plant_counts["solar"] = 5
    _play(game_env, 6)
    assert g.finish_run() is not None
    g.start_todays_run(g.seed_lib.daily_seed("grid", "2026-10-19"))     # yesterday's seed, begun today
    game_env.state.plant_counts["solar"] = 5
    _play(game_env, 6)
    assert g.finish_run() is not None
    assert page.completed == []


def test_a_short_run_that_banks_nothing_records_nothing(game_env):
    g = game_env.module
    page = _install_page(g, _today_seed(g))
    _install_storage()
    g.start_todays_run(_today_seed(g))
    _play(game_env, 2)
    assert g.finish_run() is None
    assert page.completed == []


def test_a_failing_shared_record_never_breaks_finishing(game_env):
    g = game_env.module
    _install_page(g, _today_seed(g), fail=True)
    _install_storage()
    g.start_todays_run(_today_seed(g))
    game_env.state.plant_counts["solar"] = 5
    _play(game_env, 6)
    assert g.finish_run() is not None
    assert g.career["runs"] == 1


def test_without_the_shared_script_nothing_happens_and_nothing_new_is_saved(game_env):
    g = game_env.module
    _install_storage()
    sys.modules["js"].window = types.SimpleNamespace()       # an old page: no NoyvjSeed at all
    before = set(g.get_state())
    g.start_todays_run(_today_seed(g))
    game_env.state.plant_counts["solar"] = 5
    _play(game_env, 6)
    assert g.finish_run() is not None
    assert set(g.get_state()) == before
    assert not [k for k in g.get_state() if "daily" in k or "today" in k]
    g.load_state(g.get_state())
