"""F-30: friendly save recovery. A save that fails validation never touches the farm, the player
gets a plain reason for each problem, and can keep the current farm or load the save with defaults
in place of just the bad fields."""

import pytest


def _click(env, id_):
    env.elements[id_].dispatch("click", None)


def _good_save(env):
    env.farm.funds = 500.0
    env.farm.herd_size = 4
    return env.module.get_state()


def test_a_good_save_loads_and_shows_no_notice(game_env):
    state = _good_save(game_env)
    assert game_env.module.check_save(state) == []
    assert game_env.module.load_state(state) is True
    assert game_env.elements["save-recovery-panel"].hidden is True


def test_an_older_save_missing_fields_is_not_a_problem(game_env):
    old = {"round_number": 3, "funds": 120.0, "herd_size": 2}
    assert game_env.module.check_save(old) == []
    assert game_env.module.load_state(old) is True
    assert game_env.farm.round_number == 3


def test_a_bad_field_is_refused_with_a_plain_reason_and_the_farm_is_untouched(game_env):
    m = game_env.module
    game_env.farm.funds = 777.0
    with pytest.raises(ValueError):
        m.load_state({"funds": "lots", "herd_size": 9})
    assert game_env.farm.funds == 777.0 and game_env.farm.herd_size == 0
    panel = game_env.elements["save-recovery-panel"]
    assert panel.hidden is False
    reasons = game_env.elements["save-recovery-reasons"].innerHTML
    assert "Funds should be a number" in reasons and "&quot;lots&quot;" in reasons
    assert "has not been changed" in game_env.elements["save-recovery-note"].innerText


def test_every_kind_of_bad_value_is_caught(game_env):
    m = game_env.module
    bad = [
        {"herd_size": -2}, {"herd_size": 2.5}, {"funds": None}, {"funds": float("nan")},
        {"methane": float("inf")}, {"round_number": 0}, {"round_number": True},
        {"decoupling_investment": "x"}, {"decoupling_investment": {"feed": -1}},
        {"methane_history": []}, {"methane_history": ["a"]},
    ]
    for data in bad:
        assert m.check_save(data), data


def test_a_save_that_is_not_a_set_of_named_values_returns_false_and_shows_the_notice(game_env):
    assert game_env.module.load_state("nonsense") is False
    assert game_env.elements["save-recovery-panel"].hidden is False
    assert game_env.elements["save-recovery-defaults-button"].hidden is True


def test_keep_my_farm_hides_the_notice_and_changes_nothing(game_env):
    game_env.farm.funds = 321.0
    with pytest.raises(ValueError):
        game_env.module.load_state({"funds": "x"})
    _click(game_env, "save-recovery-dismiss-button")
    assert game_env.elements["save-recovery-panel"].hidden is True
    assert game_env.farm.funds == 321.0


def test_load_with_defaults_replaces_only_the_bad_fields(game_env):
    m = game_env.module
    state = _good_save(game_env)
    state["funds"] = "oops"
    state["herd_size"] = 7
    state["decoupling_investment"] = {"feed": 3, "caps": -4, "capture": 1}
    with pytest.raises(ValueError):
        m.load_state(state)
    assert game_env.elements["save-recovery-defaults-button"].hidden is False
    _click(game_env, "save-recovery-defaults-button")
    assert game_env.farm.funds == m.STARTING_FUNDS
    assert game_env.farm.herd_size == 7
    assert game_env.farm.decoupling_investment == {"feed": 3, "caps": 0, "capture": 1}
    assert game_env.elements["save-recovery-panel"].hidden is True


def test_a_later_good_load_clears_a_pending_notice(game_env):
    with pytest.raises(ValueError):
        game_env.module.load_state({"funds": "x"})
    assert game_env.elements["save-recovery-panel"].hidden is False
    game_env.module.load_state({"funds": 50.0})
    assert game_env.elements["save-recovery-panel"].hidden is True


def test_an_unforeseen_failure_puts_the_farm_back_exactly(game_env, monkeypatch):
    m = game_env.module
    game_env.farm.funds = 640.0
    game_env.farm.herd_size = 5
    m.load_state(m.get_state())  # settle the collection records so the comparison is exact
    before = m.get_state()

    real = m._load_progress_fields
    calls = []

    def boom(data):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("unexpected")
        return real(data)

    monkeypatch.setattr(m, "_load_progress_fields", boom)
    with pytest.raises(RuntimeError):
        m.load_state({"funds": 1.0, "herd_size": 99})
    assert m.get_state() == before
    assert game_env.elements["save-recovery-panel"].hidden is False
    assert "could not be read" in game_env.elements["save-recovery-reasons"].innerHTML


def test_only_a_handful_of_reasons_are_listed(game_env):
    m = game_env.module
    bad = {k: "x" for k in m.SAVE_NUMBER_FIELDS}
    bad["methane_history"] = "x"
    with pytest.raises(ValueError):
        m.load_state(bad)
    html = game_env.elements["save-recovery-reasons"].innerHTML
    assert html.count("<li>") == m.RECOVERY_MAX_REASONS + 1 and "more." in html


def test_reasons_are_escaped(game_env):
    with pytest.raises(ValueError):
        game_env.module.load_state({"funds": "<script>alert(1)</script>"})
    assert "<script>" not in game_env.elements["save-recovery-reasons"].innerHTML


def test_a_save_round_trips_through_the_new_wrapper(game_env):
    game_env.module.load_state(_good_save(game_env))
    state = game_env.module.get_state()
    game_env.module.load_state(state)
    assert game_env.module.get_state() == state
