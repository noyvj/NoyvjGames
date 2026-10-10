"""A-2 / FY-50: System Anomalies on a fixed schedule, with a forecast strip."""

import json


def _on(env):
    env.local_storage.setItem("sol-anomalies", "on")


def _at(env, run_ticks):
    """Moves the run clock so the next tick lands on `run_ticks`."""
    m = env.module
    m.run_start_tick = 0
    m.total_ticks = run_ticks - 1


def test_first_anomaly_is_after_the_calm_stretch(game_env):
    m = game_env.module
    active, left, nxt, until = m.anomaly_schedule(0)
    assert active is None and nxt == "comet_pass" and until == m.ANOMALY_FIRST_AT
    active, left, nxt, until = m.anomaly_schedule(m.ANOMALY_FIRST_AT)
    assert active == "comet_pass" and left == m.ANOMALY_LENGTH and nxt == "solar_flare"


def test_each_anomaly_lasts_its_length_then_waits(game_env):
    m = game_env.module
    start = m.ANOMALY_FIRST_AT
    assert m.anomaly_schedule(start + m.ANOMALY_LENGTH - 1)[0] == "comet_pass"
    active, left, nxt, until = m.anomaly_schedule(start + m.ANOMALY_LENGTH)
    assert active is None and nxt == "solar_flare" and until == m.ANOMALY_PERIOD - m.ANOMALY_LENGTH
    assert m.anomaly_schedule(start + m.ANOMALY_PERIOD)[0] == "solar_flare"


def test_the_six_cycle_in_order_and_repeat(game_env):
    m = game_env.module
    seen = [m.anomaly_schedule(m.ANOMALY_FIRST_AT + k * m.ANOMALY_PERIOD)[0] for k in range(12)]
    assert seen[:6] == [a["id"] for a in m.ANOMALIES]
    assert seen[6:] == seen[:6]
    assert [a["kind"] for a in m.ANOMALIES] == ["boon", "strain"] * 3


def test_schedule_is_deterministic(game_env):
    m = game_env.module
    assert [m.anomaly_schedule(t) for t in range(0, 40000, 777)] == [m.anomaly_schedule(t) for t in range(0, 40000, 777)]


def test_off_by_default_in_the_fixture_and_no_strip(game_env):
    m = game_env.module
    _at(game_env, m.ANOMALY_FIRST_AT)
    m.tick()
    assert m._active_anomaly is None
    assert game_env.elements["anomaly-strip"].hidden is True
    assert m.anomaly_factor("produce") == 1.0


def test_comet_pass_boosts_production(game_env):
    m = game_env.module
    _on(game_env)
    m.planet_state["Earth"]["generator_count"] = 4
    m.planet_state["Earth"]["resource_count"] = 0.0
    m._simulate_planet("Earth", 0.0)
    plain = m.planet_state["Earth"]["resource_count"]
    _at(game_env, m.ANOMALY_FIRST_AT)
    m.tick()
    assert m._active_anomaly == "comet_pass"
    m.planet_state["Earth"]["resource_count"] = 0.0
    m._simulate_planet("Earth", 0.0)
    assert abs(m.planet_state["Earth"]["resource_count"] / plain - 1.25) < 1e-9


def test_strain_and_boon_factors(game_env):
    m = game_env.module
    _on(game_env)
    expect = {"solar_flare": ("decay", 1.5), "meteor_shower": ("click", 2.0), "magnetic_storm": ("trade", 0.5),
              "clear_skies": ("recycle", 1.5), "dust_cloud": ("terraform", 0.5)}
    for index, anomaly in enumerate(m.ANOMALIES):
        _at(game_env, m.ANOMALY_FIRST_AT + index * m.ANOMALY_PERIOD)
        m.tick()
        assert m._active_anomaly == anomaly["id"]
        if anomaly["id"] in expect:
            key, factor = expect[anomaly["id"]]
            assert m.anomaly_factor(key) == factor
        assert m.anomaly_factor("something_else") == 1.0


def test_meteor_shower_doubles_a_click(game_env):
    m = game_env.module
    _on(game_env)
    game_env.earth["resource_count"] = 0.0
    game_env.click()
    single = game_env.earth["resource_count"]
    _at(game_env, m.ANOMALY_FIRST_AT + 2 * m.ANOMALY_PERIOD)
    m.tick()
    game_env.earth["resource_count"] = 0.0
    game_env.click()
    assert abs(game_env.earth["resource_count"] / single - 2.0) < 1e-9


def test_dust_cloud_slows_terraforming_but_never_reverses_it(game_env):
    m = game_env.module
    _on(game_env)
    m.planet_state["Earth"]["generator_count"] = 1
    full = m.terraform_rate("Earth")
    _at(game_env, m.ANOMALY_FIRST_AT + 5 * m.ANOMALY_PERIOD)
    m.tick()
    assert 0 < m.terraform_rate("Earth") < full


def test_forecast_text_names_the_next_anomaly_in_words(game_env):
    m = game_env.module
    _on(game_env)
    _at(game_env, 1)
    m.tick()
    text = game_env.elements["anomaly-strip"].innerText
    assert text.startswith("Next anomaly: Comet Pass in 5:00") and "a boon" in text
    assert game_env.elements["anomaly-strip"].hidden is False
    _at(game_env, m.ANOMALY_FIRST_AT + m.ANOMALY_PERIOD)
    m.tick()
    text = game_env.elements["anomaly-strip"].innerText
    assert "Strain" in text and "Solar Flare" in text and "Next: Meteor Shower" in text


def test_switching_it_off_clears_the_effect_and_strip(game_env):
    m = game_env.module
    _on(game_env)
    _at(game_env, m.ANOMALY_FIRST_AT)
    m.tick()
    assert m._active_anomaly
    game_env.local_storage.setItem("sol-anomalies", "off")
    m.tick()
    assert m._active_anomaly is None and game_env.elements["anomaly-strip"].hidden is True


def test_sandbox_has_no_anomalies(game_env):
    m = game_env.module
    _on(game_env)
    for p in m.PLANETS:
        m.planet_state[p]["terraform_progress"] = m.TERRAFORM_MAX
    m.sandbox_mode = True
    _at(game_env, m.ANOMALY_FIRST_AT)
    m.tick()
    assert m._active_anomaly is None


def test_a_new_run_restarts_the_calm_stretch(game_env):
    m = game_env.module
    _on(game_env)
    m.total_ticks = 99999
    m.run_start_tick = 99999 - 100
    assert m._run_ticks() == 100
    assert m.anomaly_schedule(m._run_ticks())[0] is None


def test_seen_anomalies_are_collected_and_saved(game_env):
    m = game_env.module
    _on(game_env)
    assert "anomalies_seen" not in m.serialize_state()
    _at(game_env, m.ANOMALY_FIRST_AT)
    m.tick()
    assert m.anomalies_seen == {"comet_pass"}
    state = json.loads(json.dumps(m.serialize_state()))
    assert state["anomalies_seen"] == ["comet_pass"]
    m.anomalies_seen.clear()
    m.deserialize_state(state)
    assert m.anomalies_seen == {"comet_pass"}


def test_bad_saved_anomalies_are_dropped(game_env):
    m = game_env.module
    for bad in ("comet_pass", 3, None, [1, "nope", None]):
        m.deserialize_state({"anomalies_seen": bad})
        assert m.anomalies_seen == set()
    m.deserialize_state({"anomalies_seen": ["dust_cloud", "bogus"]})
    assert m.anomalies_seen == {"dust_cloud"}


def test_setting_is_wired_in_the_page():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    assert 'id="anomalies-checkbox"' in (root / "index.html").read_text()
    assert '"sol-anomalies"' in (root / "settings.js").read_text()
    assert '"#anomaly-strip"' in (root / "pc-config.json").read_text()
