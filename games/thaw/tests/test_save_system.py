"""Save system (SAVE-BUTTON-INTEGRATION.md) reference-pattern integration:
get_state()/load_state() package every module-level mutable global —
across all THREE regions (the primary region plus Pass 2's Region B and
Region C) — into a plain JSON-safe dict and back. SOL is the reference
integration for this contract; these tests mirror
games/sol/tests/test_save_system.py's coverage shape, adapted to Thaw's
multi-region state.
"""


def test_get_state_includes_every_expected_key(game_env):
    data = game_env.module.get_state()
    assert set(data.keys()) == {"region", "region_b", "region_c", "info_page_open"}


def test_get_state_region_dict_includes_every_expected_field(game_env):
    data = game_env.module.get_state()
    expected_fields = {
        "round_number",
        "funds",
        "capacity",
        "temperature",
        "melt_started_round",
        "just_started_melting",
        "counterfactual_temperature",
        "temperature_history",
        "just_invested_intervention",
    }
    assert set(data["region"].keys()) == expected_fields
    assert set(data["region_b"].keys()) == expected_fields
    assert set(data["region_c"].keys()) == expected_fields


def test_get_state_deep_copies_mutable_containers(game_env):
    module = game_env.module
    module.region.invest("preserve")
    data = module.get_state()

    # Mutating the live region after taking the snapshot must not leak
    # into the already-returned dict — capacity and temperature_history
    # are the two mutable containers per region.
    module.region.invest("preserve")
    module.region.temperature_history.append(999.0)

    assert data["region"]["capacity"]["preserve"] == 1
    assert 999.0 not in data["region"]["temperature_history"]


def test_load_state_full_round_trip_restores_primary_region(game_env):
    module = game_env.module
    game_env.invest("output")
    game_env.invest("preserve")
    game_env.advance_round()
    snapshot = module.get_state()
    funds_at_snapshot = module.region.funds
    temperature_at_snapshot = module.region.temperature
    capacity_at_snapshot = dict(module.region.capacity)

    # Diverge.
    game_env.invest("monitor")
    game_env.advance_round()
    assert module.region.funds != funds_at_snapshot
    assert module.region.temperature != temperature_at_snapshot

    result = module.load_state(snapshot)
    assert result is True
    assert module.region.funds == funds_at_snapshot
    assert module.region.temperature == temperature_at_snapshot
    assert module.region.capacity == capacity_at_snapshot


def test_load_state_full_round_trip_restores_all_three_regions(game_env):
    module = game_env.module

    # Give each region a distinct trajectory so a restore that silently
    # only covers the primary region would be caught.
    game_env.invest("output")
    game_env.invest_secondary("b", "preserve")
    game_env.invest_secondary("c", "monitor")
    game_env.advance_round()
    game_env.advance_round()

    snapshot = module.get_state()
    b_funds = module.region_b.funds
    b_capacity = dict(module.region_b.capacity)
    b_temperature = module.region_b.temperature
    b_history = list(module.region_b.temperature_history)
    c_funds = module.region_c.funds
    c_capacity = dict(module.region_c.capacity)
    c_temperature = module.region_c.temperature
    c_history = list(module.region_c.temperature_history)

    # Diverge every region, including B and C specifically.
    game_env.invest_secondary("b", "output")
    game_env.invest_secondary("c", "preserve")
    game_env.advance_round()
    assert module.region_b.funds != b_funds or module.region_b.capacity != b_capacity
    assert module.region_c.funds != c_funds or module.region_c.capacity != c_capacity

    result = module.load_state(snapshot)
    assert result is True

    assert module.region_b.funds == b_funds
    assert module.region_b.capacity == b_capacity
    assert module.region_b.temperature == b_temperature
    assert module.region_b.temperature_history == b_history

    assert module.region_c.funds == c_funds
    assert module.region_c.capacity == c_capacity
    assert module.region_c.temperature == c_temperature
    assert module.region_c.temperature_history == c_history


def test_load_state_restores_melt_state_and_fires_the_tipping_flash(game_env):
    module = game_env.module
    RegionState = module.RegionState

    # Push a region past the melt threshold so melt_started_round and the
    # feedback loop are actually exercised, not just zero defaults.
    melted = RegionState()
    while not melted.is_melting():
        melted.advance_round()
    assert melted.melt_started_round is not None
    assert melted.just_started_melting is True

    module.region.melt_started_round = melted.melt_started_round
    module.region.just_started_melting = True  # not yet consumed by a render
    module.region.temperature = melted.temperature
    module.region.counterfactual_temperature = melted.counterfactual_temperature
    module.region.temperature_history = list(melted.temperature_history)
    snapshot = module.get_state()
    assert snapshot["region"]["just_started_melting"] is True

    # Diverge: clear the flags/threshold state entirely.
    module.region.melt_started_round = None
    module.region.just_started_melting = False
    module.region.temperature = 0.0

    module.load_state(snapshot)
    # melt_started_round/temperature are restored and persist; the
    # one-tick just_started_melting flag is correctly restored too, but
    # load_state()'s own re-render immediately consumes it — the same
    # "fire once, then clear" behavior a live invest()->render() cycle
    # has. That consumption is visible here as the flash class actually
    # firing on this render.
    assert module.region.melt_started_round == melted.melt_started_round
    assert module.region.temperature == melted.temperature
    assert game_env.elements["game"].className == "tipping-flash"
    assert module.region.just_started_melting is False


def test_load_state_restores_intervention_state_and_fires_the_dampening_flash(game_env):
    module = game_env.module
    # Calls RegionState.invest() directly (not the DOM-click path) so the
    # one-tick flag is still True when the snapshot is taken — clicking
    # via game_env.invest() would trigger render() in the same handler
    # and consume it before get_state() ever sees it.
    module.region.invest("preserve")
    assert module.region.just_invested_intervention is True
    assert module.region.capacity["preserve"] == 1
    snapshot = module.get_state()

    module.region.just_invested_intervention = False
    module.region.capacity["preserve"] = 0

    module.load_state(snapshot)
    # Same one-tick "restore then immediately consume via re-render"
    # behavior as the tipping flash above, visible as the dampening-flash
    # class firing on the readout.
    assert module.region.capacity["preserve"] == 1
    assert "dampening-flash" in game_env.elements["dampening-display"].className
    assert module.region.just_invested_intervention is False


def test_load_state_restores_info_page_open(game_env):
    module = game_env.module
    game_env.toggle_info_page()
    assert module.info_page_open is True
    snapshot = module.get_state()

    module.info_page_open = False
    module.load_state(snapshot)
    assert module.info_page_open is True
    assert game_env.elements["info-page-panel"].hidden is False


def test_load_state_re_renders_the_ui(game_env):
    module = game_env.module
    game_env.invest("output")
    snapshot = module.get_state()

    module.region.capacity["output"] = 0
    module.load_state(snapshot)

    # render() should have refreshed the DOM to reflect the restored count.
    assert game_env.elements["output-count"].innerText == "1"


def test_load_state_is_the_exact_inverse_of_get_state(game_env):
    module = game_env.module
    game_env.invest("output")
    game_env.invest_secondary("b", "preserve")
    game_env.invest_secondary("c", "monitor")
    game_env.advance_round()
    snapshot = module.get_state()

    game_env.invest("monitor")
    game_env.invest_secondary("b", "output")
    game_env.invest_secondary("c", "output")
    game_env.advance_round()

    module.load_state(snapshot)
    assert module.get_state() == snapshot
