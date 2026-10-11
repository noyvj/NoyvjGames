"""Z-5c, "Today's run": the page's shared button (shared/seed.js, in the Expedition panel) hands Canopy the UTC date's shared seed.
Today's run is an Expedition on that seed (the same map for everyone that day). It asks first when a forest would be given up,
does nothing when that very run is already under way, and finishing it tells the shared daily record once, only when the page
says the seed is today's. Nothing new is saved: the Expedition's own seed is the whole of it."""
import sys
import types

import seed as seed_lib

from .gb_helpers import advance_to

TODAY = "2026-10-20"


class FakeDaily:
    """Stands in for window.NoyvjSeed: `today_seed` is the one seed the page would call today's."""

    def __init__(self, today_seed, fail=False):
        self.today_seed = today_seed
        self.fail = fail
        self.completed = []
        self.footer = []
        self.daily = types.SimpleNamespace(isDaily=self.is_daily, markCompleted=self.mark)
        self.set = self.footer.append

    def is_daily(self, game, seed):
        assert game == "canopy"
        return seed == self.today_seed

    def mark(self, game, info):
        if self.fail:
            raise RuntimeError("storage blocked")
        self.completed.append((game, info.score, info.text))


def _today():
    return seed_lib.daily_seed("canopy", TODAY)


def _install_page(env, fail=False, dialog=None):
    js = sys.modules["js"]
    page = FakeDaily(_today(), fail)
    js.window = types.SimpleNamespace(NoyvjSeed=page, **({"ConfirmDialog": dialog} if dialog else {}))
    js.Object = types.SimpleNamespace(new=lambda: types.SimpleNamespace())
    return page


def _untouched(m):
    m.total_income = 0.0
    for plot in m.plots:
        plot.value = 0.0


def test_the_button_starts_an_expedition_on_todays_seed(game_env):
    m = game_env.module
    page = _install_page(game_env)
    _untouched(m)
    message = m.start_todays_run(_today())
    assert m.current_expedition == {"seed": _today(), "owned": [], "done_tick": None, "score": None}
    assert _today() in message and "same for everyone today" in message and "counts for today" in message
    assert m.expedition_map(_today()) == m.expedition_map(seed_lib.daily_seed("canopy", TODAY))
    assert page.footer[-1] == _today()


def test_another_day_gives_another_map(game_env):
    m = game_env.module
    maps = {str(m.expedition_map(seed_lib.daily_seed("canopy", "2026-10-%02d" % d))) for d in range(10, 20)}
    assert len(maps) > 1


def test_a_forest_at_stake_is_asked_about_first_and_cancel_loses_nothing(game_env, fake_confirm_dialog):
    m = game_env.module
    page = _install_page(game_env, dialog=fake_confirm_dialog)
    game_env.elements["expedition-toggle-button"].dispatch("click", None)    # the panel is open, so its message line is drawn
    m.total_income = 25.0
    message = m.start_todays_run(_today())
    assert m.current_expedition is None and "Nothing has changed yet" in message
    assert "25.0 income" in fake_confirm_dialog.asks[-1]["message"] and _today() in fake_confirm_dialog.asks[-1]["message"]
    assert fake_confirm_dialog.asks[-1]["allowSkip"] is False
    fake_confirm_dialog.cancel()
    assert m.current_expedition is None and m.total_income == 25.0
    assert page.footer[-1] == ""                      # the footer is given back what it showed before
    m.start_todays_run(_today())
    fake_confirm_dialog.confirm()
    assert m.current_expedition["seed"] == _today() and m.total_income == 0.0
    assert "Today's run is on" in game_env.elements["expedition-seed-message"].innerText
    assert page.footer[-1] == _today()


def test_the_run_already_under_way_is_never_restarted(game_env):
    m = game_env.module
    _install_page(game_env)
    _untouched(m)
    m.start_todays_run(_today())
    game_env.tick(30)
    tick, income = m.forest_tick, m.total_income
    message = m.start_todays_run(_today())
    assert "already playing today's run" in message and "Nothing was changed" in message
    assert m.forest_tick == tick == 30 and m.total_income == income and m.current_expedition["seed"] == _today()


def test_a_different_expedition_under_way_is_asked_about_not_replaced(game_env, fake_confirm_dialog):
    m = game_env.module
    _install_page(game_env, dialog=fake_confirm_dialog)
    _untouched(m)
    m.start_expedition("CANOPY-K7F2Q")
    game_env.tick(20)
    m.total_income = 12.0
    m.start_todays_run(_today())
    assert m.current_expedition["seed"] == "CANOPY-K7F2Q" and fake_confirm_dialog.asks
    fake_confirm_dialog.cancel()
    assert m.current_expedition["seed"] == "CANOPY-K7F2Q" and m.forest_tick == 20


def test_a_bad_or_foreign_seed_changes_nothing_and_says_why(game_env):
    m = game_env.module
    _install_page(game_env)
    assert "for TIDE" in m.start_todays_run("TIDE-K7F2Q")
    assert "Enter a seed" in m.start_todays_run("")
    assert m.current_expedition is None


def test_finishing_todays_run_records_it_once(game_env):
    m = game_env.module
    page = _install_page(game_env)
    _untouched(m)
    m.start_todays_run(_today())
    advance_to(game_env, m.EXPEDITION_TICKS + 20)
    assert m.expedition_finished()
    assert len(page.completed) == 1
    game, score, text = page.completed[0]
    assert game == "canopy" and score == m.current_expedition["score"] and text == f"Expedition score {score}"


def test_an_older_days_seed_or_another_seed_records_nothing(game_env):
    m = game_env.module
    page = _install_page(game_env)
    _untouched(m)
    m.start_todays_run(seed_lib.daily_seed("canopy", "2026-10-19"))     # yesterday's seed, begun today
    advance_to(game_env, m.EXPEDITION_TICKS)
    assert m.expedition_finished() and m.expedition_meta["finished"] == 1
    m.start_expedition("CANOPY-K7F2Q")
    advance_to(game_env, m.EXPEDITION_TICKS)
    assert m.expedition_finished() and page.completed == []


def test_a_failing_shared_record_never_breaks_finishing(game_env):
    m = game_env.module
    _install_page(game_env, fail=True)
    _untouched(m)
    m.start_todays_run(_today())
    advance_to(game_env, m.EXPEDITION_TICKS)
    assert m.expedition_finished() and m.expedition_meta["finished"] == 1


def test_without_the_shared_script_nothing_happens_and_nothing_new_is_saved(game_env):
    m = game_env.module
    sys.modules["js"].window = types.SimpleNamespace()               # an old page: no NoyvjSeed at all
    _untouched(m)
    m.start_todays_run(_today())
    advance_to(game_env, m.EXPEDITION_TICKS)
    assert m.expedition_finished()
    assert "expedition" in m.get_state()                              # the Expedition's own key, as for any Expedition
    assert not [k for k in m.get_state() if "daily" in k or "today" in k]
    m.load_state(m.get_state())
    assert m.current_expedition["seed"] == _today()


def test_a_saved_expedition_from_an_older_day_finishes_without_counting(game_env):
    m = game_env.module
    page = _install_page(game_env)
    _untouched(m)
    m.start_todays_run(seed_lib.daily_seed("canopy", "2026-10-19"))
    game_env.tick(10)
    state = m.get_state()
    m.load_state(state)
    advance_to(game_env, m.EXPEDITION_TICKS)
    assert m.expedition_finished() and page.completed == []
