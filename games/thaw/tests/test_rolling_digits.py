"""GG-19: the temperature readout counts up after Advance Round, unless motion is reduced."""


def _rolling(m, monkeypatch=None):
    m._digits_instant = lambda: False


def test_instant_in_the_test_harness_by_default(game_env):
    m = game_env.module
    assert m._digits_instant() is True
    game_env.advance_round()
    assert game_env.timers.pending == []
    assert game_env.elements["temperature-display"].innerText == "Global temperature: +1.0°"


def test_roll_values_end_exactly_on_the_target(game_env):
    m = game_env.module
    values = m.roll_values(2.0, 3.0)
    assert len(values) == m.ROLL_STEPS
    assert values[-1] == 3.0
    assert values == sorted(values)
    assert values[0] > 2.0
    assert m.roll_values(5.0, 3.0)[0] < 5.0  # also counts down (a rewind)
    assert m.roll_values(1.0, 2.0, steps=0) == [2.0]


def test_step_time_shrinks_with_acceleration_but_has_a_floor(game_env):
    m = game_env.module
    assert m.roll_step_ms(1.0) == m.ROLL_BASE_MS
    assert m.roll_step_ms(2.0) < m.roll_step_ms(1.0)
    assert m.roll_step_ms(1000) == m.ROLL_MIN_MS
    assert m.roll_step_ms(0.2) == m.ROLL_BASE_MS
    assert m.roll_step_ms("x") == m.ROLL_BASE_MS


def test_advance_starts_a_roll_that_lands_on_the_real_figure(game_env):
    m = game_env.module
    _rolling(m)
    game_env.advance_round()
    text = game_env.elements["temperature-display"]
    assert text.innerText == "Global temperature: +0.0°"  # starts at the old value
    shown = []
    for _ in range(40):
        if not game_env.timers.pending:
            break
        game_env.timers.flush()
        shown.append(text.innerText)
    assert len(shown) == m.ROLL_STEPS
    assert shown[-1] == "Global temperature: +1.0°"
    assert game_env.timers.pending == []


def test_a_later_render_cancels_the_roll(game_env):
    m = game_env.module
    _rolling(m)
    game_env.advance_round()
    game_env.timers.flush()  # one step shown
    m.render()  # e.g. an invest click: writes the final figure
    final = game_env.elements["temperature-display"].innerText
    assert final == "Global temperature: +1.0°"
    game_env.timers.flush()
    assert game_env.elements["temperature-display"].innerText == final


def test_a_second_advance_replaces_the_first_roll(game_env):
    m = game_env.module
    _rolling(m)
    game_env.advance_round()
    game_env.advance_round()
    for _ in range(40):
        if not game_env.timers.pending:
            break
        game_env.timers.flush()
    assert game_env.elements["temperature-display"].innerText == "Global temperature: +2.0°"


def test_no_roll_when_the_temperature_did_not_change(game_env):
    m = game_env.module
    _rolling(m)
    assert m.start_temperature_roll(3.0, 3.0) is False
    assert m.start_temperature_roll(None, 3.0) is False
    assert game_env.timers.pending == []


def test_rolling_never_changes_the_real_state(game_env):
    m = game_env.module
    plain = m.get_state()
    _rolling(m)
    game_env.advance_round()
    game_env.timers.flush()
    assert m.region.temperature == 1.0
    assert m.get_state()["region"]["temperature"] == 1.0
    assert plain["region"]["temperature"] == 0.0


def test_instant_switches_are_checked(game_env):
    import sys
    import types

    m = game_env.module

    def root(**attrs):
        return types.SimpleNamespace(getAttribute=lambda name: attrs.get(name))

    def window(attrs, reduce=False):
        media = types.SimpleNamespace(matches=reduce)
        return types.SimpleNamespace(
            document=types.SimpleNamespace(documentElement=root(**attrs)), matchMedia=lambda q: media
        )

    sys.modules["js"].window = window({})
    assert m._digits_instant() is False
    for attr in ("data-instant-digits", "data-reduced-motion", "data-lite"):
        sys.modules["js"].window = window({attr: "true"})
        assert m._digits_instant() is True, attr
    sys.modules["js"].window = window({}, reduce=True)
    assert m._digits_instant() is True
