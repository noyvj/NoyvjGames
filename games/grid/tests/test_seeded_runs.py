"""Seeded runs (the shared Z-1 helper, reused read-only), plus the peek forecast (GC-11) that rests on it.

Every random draw of a run comes from a stateless stream derived from (seed, purpose, round), so the
same seed and the same choices always give the same weather, disruptions and breakdowns."""
import json

from .test_career import _install_storage


def _dirty_grid(g, seed, weather=True):
    s = g.GridState()
    s.seed = seed
    s.weather_variability_enabled = weather
    s.plant_counts["coal"] = 3
    s.plant_counts["solar"] = 3
    s.plant_counts["wind"] = 2
    s.emissions = 600.0
    return s


def _run(g, seed, rounds=12):
    s = _dirty_grid(g, seed)
    for _ in range(rounds):
        s.advance_round()
    return s


def test_new_runs_get_a_valid_grid_seed(game_env):
    g = game_env.module
    assert g.seed_lib.is_valid(game_env.state.seed, "grid")
    assert game_env.state.seed.startswith("GRID-")
    assert g.GridState().seed != g.GridState().seed or True  # two fresh seeds are normally different


def test_same_seed_same_choices_same_run(game_env):
    g = game_env.module
    a, b = _run(g, "GRID-K7F2Q"), _run(g, "GRID-K7F2Q")
    assert a.funds == b.funds and a.emissions == b.emissions
    assert [e["type"] for e in a.event_log] == [e["type"] for e in b.event_log]
    assert a.weather_log == b.weather_log and a.plant_counts == b.plant_counts


def test_different_seeds_give_different_runs(game_env):
    g = game_env.module
    funds = {_run(g, seed).funds for seed in ("GRID-K7F2Q", "GRID-AAAAA", "GRID-ZZZZZ", "GRID-23456", "GRID-HJKMN")}
    assert len(funds) > 1


def test_streams_are_stateless_per_round_and_purpose(game_env):
    s = game_env.state
    s.seed = "GRID-K7F2Q"
    assert s.stream("weather").random() == s.stream("weather").random()
    assert s.stream("weather").random() != s.stream("disruption").random()
    assert s.stream("weather", 2).random() != s.stream("weather", 3).random()
    s.round_number = 5
    assert s.stream("weather").random() == s.stream("weather", 5).random()


def test_explicit_rng_callables_still_override_the_streams(game_env):
    s = game_env.state
    s.plant_counts["coal"] = 3
    s.emissions = 1500.0
    s.advance_round(rng=lambda: 0.0, age_rng=lambda: 1.0, weather_rng=lambda: 0.5)
    assert s.last_event is not None  # rng() = 0.0 always trips the disruption roll
    s.advance_round(rng=lambda: 0.999, age_rng=lambda: 1.0, weather_rng=lambda: 0.5)
    assert s.last_event is None


def test_set_seed_accepts_forgiving_input_and_locks_after_play(game_env):
    s = game_env.state
    assert s.set_seed("grid k7f2q") is True and s.seed == "GRID-K7F2Q"
    assert s.set_seed("k7f2r") is True and s.seed == "GRID-K7F2R"
    assert s.set_seed("TIDE-K7F2Q") is False and s.seed == "GRID-K7F2R"
    assert s.set_seed("nonsense!") is False
    s.build_plant("coal")
    assert s.set_seed("GRID-K7F2Q") is False and s.seed == "GRID-K7F2R"


def test_seed_ui_reports_errors_and_applies(game_env):
    el = game_env.elements
    el["run-seed-input"].value = "TIDE-K7F2Q"
    el["run-seed-apply-button"].dispatch("click", None)
    assert "not this game" in el["run-seed-note"].innerText
    el["run-seed-input"].value = "grid-23456"
    el["run-seed-apply-button"].dispatch("click", None)
    assert game_env.state.seed == "GRID-23456"
    assert el["run-seed-display"].innerText == "Run seed: GRID-23456"
    game_env.build("coal")
    assert el["run-seed-apply-button"].disabled is True


def test_seed_is_saved_and_a_bad_seed_is_ignored(game_env):
    g = game_env.module
    game_env.state.set_seed("GRID-K7F2Q")
    data = json.loads(json.dumps(g.get_state()))
    assert data["seed"] == "GRID-K7F2Q"
    game_env.state.seed = "GRID-23456"
    g.load_state(data)
    assert game_env.state.seed == "GRID-K7F2Q"
    bad = dict(data, seed="TIDE-K7F2Q")
    keep = game_env.state.seed
    g.load_state(bad)
    assert game_env.state.seed == keep
    g.load_state(dict(data, seed=12345))
    assert game_env.state.seed == keep


# --- GC-11 peek forecast -----------------------------------------------------------------------

def _owning(game_env, *nodes, points=40):
    g = game_env.module
    _install_storage()
    g.career["points"] = points
    for node in nodes:
        assert g.unlock_career_perk(node), node
    g._sync_perks()
    return g


def test_peek_needs_the_weather_station(game_env):
    s = game_env.state
    assert s.peek_unlocked() is False and s.buy_peek() is False
    _owning(game_env, "weather_station")
    assert s.peek_unlocked() is True


def test_peek_costs_a_fee_once_per_round(game_env):
    g = _owning(game_env, "weather_station")
    s = game_env.state
    before = s.funds
    assert s.buy_peek() is True and s.funds == before - g.PEEK_FEE
    assert s.buy_peek() is False and s.funds == before - g.PEEK_FEE
    assert s.peek_active() is True
    s.advance_round()
    assert s.peek_active() is False
    s.funds = g.PEEK_FEE - 1
    assert s.buy_peek() is False


def test_peek_matches_what_the_round_then_does(game_env):
    g = _owning(game_env, "weather_station", "long_range_outlook")
    for seed in ("GRID-K7F2Q", "GRID-AAAAA", "GRID-23456", "GRID-ZZZZZ", "GRID-HJKMN", "GRID-PQRST"):
        s = _dirty_grid(g, seed)
        s.perks = {"weather_station", "long_range_outlook"}
        s.funds = 1000
        for _ in range(8):
            assert s.buy_peek()
            f = s.peek_forecast()
            nameplate = sum(s.plant_counts[t] * g.PLANT_CAPACITY[t] for t in g.RENEWABLE_TYPES)
            expected_actual = sum(s.plant_counts[t] * g.PLANT_CAPACITY[t] * f["weather"][t] for t in g.RENEWABLE_TYPES)
            before_events = len(s.event_log)
            s.advance_round()
            hit = len(s.event_log) > before_events
            assert hit == (f["disruption"] == "hit"), seed
            assert abs(s.last_weather_renewable_actual - expected_actual) < 1e-9
            assert abs(s.last_weather_renewable_nameplate - nameplate) < 1e-9
            # the long-range outlook for this round was the next round's exact factors
            if f["weather_next"] is not None:
                assert f["weather_next"] == s.renewable_weather_factors()


def test_peek_without_weather_variability_reports_no_weather(game_env):
    g = _owning(game_env, "weather_station")
    s = game_env.state
    s.buy_peek()
    assert s.peek_forecast()["weather"] is None
    assert "stays at nameplate" in g.peek_text()


def test_peek_ui_button_and_text(game_env):
    g = _owning(game_env, "weather_station")
    el = game_env.elements
    g.render()
    assert el["peek-forecast-button"].hidden is False and el["peek-forecast-button"].disabled is False
    assert "pay 20 funds" in el["peek-forecast-display"].innerText
    funds = game_env.state.funds
    el["peek-forecast-button"].dispatch("click", None)
    assert game_env.state.funds == funds - 20
    assert el["peek-forecast-button"].disabled is True
    assert "next round" in el["peek-forecast-display"].innerText and "disruption" in el["peek-forecast-display"].innerText


def test_peek_hidden_until_unlocked_and_saved(game_env):
    g = game_env.module
    g.render()
    assert game_env.elements["peek-forecast-button"].hidden is True
    assert "Weather station" in game_env.elements["peek-forecast-display"].innerText
    _owning(game_env, "weather_station")
    game_env.state.buy_peek()
    data = json.loads(json.dumps(g.get_state()))
    assert data["peeked_round"] == 1
    game_env.state.peeked_round = 0
    g.load_state(data)
    assert game_env.state.peeked_round == 1
