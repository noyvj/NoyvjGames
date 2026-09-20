"""B21: one-time permanent plot specialization."""


def _ready(game_env, index=0):
    m = game_env.module
    m.plots[index].ticks_intact = m.SPECIALIST_MIN_TICKS_INTACT
    game_env.select(index)


def test_row_hidden_until_plot_is_old_enough(game_env):
    m = game_env.module
    game_env.select(0)
    assert game_env.elements["specialist-row"].hidden is True
    _ready(game_env)
    assert game_env.elements["specialist-row"].hidden is False


def test_row_hidden_without_selection(game_env):
    game_env.module.render()
    assert game_env.elements["specialist-row"].hidden is True


def test_economic_specialist_grows_faster(game_env):
    m = game_env.module
    base = m.Plot(0)
    spec = m.Plot(1)
    spec.specialization = m.SPECIALIZATION_ECONOMIC
    assert abs(spec.accrue_tick() - base.accrue_tick() * m.SPECIALIST_ECONOMIC_VALUE_MULTIPLIER) < 1e-9


def test_biodiversity_specialist_gains_more_biodiversity_not_value(game_env):
    m = game_env.module
    base = m.Plot(0)
    spec = m.Plot(1)
    spec.specialization = m.SPECIALIZATION_BIODIVERSITY
    assert spec.accrue_tick() == base.accrue_tick()
    assert abs(spec.biodiversity - base.biodiversity * m.SPECIALIST_BIODIVERSITY_MULTIPLIER) < 1e-9


def test_choice_is_one_time(game_env):
    m = game_env.module
    _ready(game_env)
    assert m.specialize_selected_plot(m.SPECIALIZATION_ECONOMIC) is True
    assert m.specialize_selected_plot(m.SPECIALIZATION_BIODIVERSITY) is False
    assert m.plots[0].specialization == m.SPECIALIZATION_ECONOMIC
    assert game_env.elements["specialist-row"].hidden is True


def test_too_young_or_no_selection_or_bad_kind_rejected(game_env):
    m = game_env.module
    assert m.specialize_selected_plot(m.SPECIALIZATION_ECONOMIC) is False
    game_env.select(0)
    assert m.specialize_selected_plot(m.SPECIALIZATION_ECONOMIC) is False
    _ready(game_env)
    assert m.specialize_selected_plot("nonsense") is False


def test_buttons_are_wired_and_work(game_env):
    m = game_env.module
    _ready(game_env)
    game_env.elements["specialize-biodiversity-button"].dispatch("click", None)
    assert m.plots[0].specialization == m.SPECIALIZATION_BIODIVERSITY
    assert "biodiversity specialist" in game_env.elements["plot-0"].getAttribute("data-tooltip")


def test_clearing_loses_specialization(game_env):
    m = game_env.module
    _ready(game_env)
    m.specialize_selected_plot(m.SPECIALIZATION_ECONOMIC)
    m.plots[0].clear()
    assert m.plots[0].specialization is None


def test_bare_plot_cannot_specialize(game_env):
    m = game_env.module
    m.plots[0].ticks_intact = 500
    m.plots[0].clear()
    m.plots[0].ticks_intact = 500
    assert not m.plots[0].can_specialize()


def test_specialization_round_trips_and_bad_values_are_ignored(game_env):
    m = game_env.module
    _ready(game_env)
    m.specialize_selected_plot(m.SPECIALIZATION_ECONOMIC)
    state = m.get_state()
    m.reset_session()
    m.load_state(state)
    assert m.plots[0].specialization == m.SPECIALIZATION_ECONOMIC
    state["plots"][0]["specialization"] = "hax"
    m.load_state(state)
    assert m.plots[0].specialization is None


def test_old_save_without_specialization_loads(game_env):
    m = game_env.module
    state = m.get_state()
    for plot in state["plots"]:
        del plot["specialization"]
    m.load_state(state)
    assert m.plots[0].specialization is None
