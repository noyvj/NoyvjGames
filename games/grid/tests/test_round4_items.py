"""Round-4 pass (2026-09-21): storage arbitrage (C9), emergency-response
scenario (C27), and persistence of the round-3 fields."""


def _mod(game_env):
    return game_env.module


# --- C9: storage arbitrage --------------------------------------------------


def test_arbitrage_button_disabled_without_battery(game_env):
    game_env.module.render()
    assert game_env.elements["arbitrage-mode-button"].disabled is True
    assert game_env.elements["arbitrage-status-display"].hidden is True


def test_arbitrage_button_enabled_and_cycles_modes(game_env):
    state = game_env.state
    state.funds = 10_000
    game_env.build("battery")
    button = game_env.elements["arbitrage-mode-button"]
    assert button.disabled is False
    assert "Idle" in button.innerText
    game_env.cycle_arbitrage_mode()
    assert state.arbitrage_mode == "charge" and "Charge" in button.innerText
    game_env.cycle_arbitrage_mode()
    assert state.arbitrage_mode == "discharge" and "Discharge" in button.innerText
    game_env.cycle_arbitrage_mode()
    assert state.arbitrage_mode == "idle"


def test_invalid_mode_rejected(game_env):
    assert game_env.state.set_arbitrage_mode("explode") is False
    assert game_env.state.arbitrage_mode == "idle"


def test_charge_banks_surplus_with_efficiency_loss(game_env):
    g = game_env.module
    state = game_env.state
    state.plant_counts["nuclear"] = 2  # 200 capacity vs 100 demand
    state.plant_counts["battery"] = 2  # rate 30, cap 60
    state.set_arbitrage_mode("charge")
    state.advance_round()
    assert abs(state.stored_energy - 30 * g.ARBITRAGE_EFFICIENCY) < 1e-9
    assert state.last_arbitrage["mode"] == "charge"


def test_charge_capped_by_storage_cap(game_env):
    state = game_env.state
    state.plant_counts["nuclear"] = 5
    state.plant_counts["battery"] = 1  # cap 30
    state.set_arbitrage_mode("charge")
    for _ in range(6):
        state.advance_round()
    assert state.stored_energy <= state.storage_cap() + 1e-9


def test_charge_does_nothing_without_surplus(game_env):
    state = game_env.state
    state.plant_counts["coal"] = 1  # 20 cap vs demand 100
    state.plant_counts["battery"] = 1
    state.set_arbitrage_mode("charge")
    state.advance_round()
    assert state.stored_energy == 0


def test_discharge_sells_into_shortfall_at_premium(game_env):
    g = game_env.module
    state = game_env.state
    state.plant_counts["coal"] = 1  # 20 cap vs 100 demand
    state.plant_counts["battery"] = 2  # rate 30
    state.stored_energy = 50.0
    state.set_arbitrage_mode("discharge")
    funds_before = state.funds
    state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    base = 20 * g.REVENUE_PER_UNIT_MET
    bonus = 30 * g.REVENUE_PER_UNIT_MET * g.ARBITRAGE_PEAK_PRICE_MULTIPLIER
    assert abs(state.funds - (funds_before + base + bonus)) < 1e-6
    assert abs(state.stored_energy - 20.0) < 1e-9
    assert abs(state.arbitrage_revenue_total - bonus) < 1e-6


def test_discharge_with_no_shortfall_or_stock_sells_nothing(game_env):
    state = game_env.state
    state.plant_counts["nuclear"] = 2
    state.plant_counts["battery"] = 1
    state.stored_energy = 10.0
    state.set_arbitrage_mode("discharge")
    state.advance_round()
    assert state.stored_energy == 10.0


def test_idle_mode_never_touches_storage(game_env):
    state = game_env.state
    state.plant_counts["nuclear"] = 2
    state.plant_counts["battery"] = 1
    state.advance_round()
    assert state.stored_energy == 0 and state.last_arbitrage is None


def test_retiring_battery_shrinks_stored_energy(game_env):
    state = game_env.state
    state.plant_counts["battery"] = 2
    state.stored_energy = 60.0
    state.plant_counts["battery"] = 1
    state.advance_round()
    assert state.stored_energy <= 30.0


def test_arbitrage_status_line_renders(game_env):
    state = game_env.state
    state.plant_counts["battery"] = 1
    state.plant_counts["coal"] = 1
    state.stored_energy = 20.0
    state.set_arbitrage_mode("discharge")
    game_env.advance_round()
    text = game_env.elements["arbitrage-status-display"].innerText
    assert "Stored" in text and "sold" in text


# --- C27: emergency response --------------------------------------------------


def test_emergency_is_last_scenario_and_sets_crisis(game_env):
    state = game_env.state
    assert state.apply_scenario("emergency") is True
    assert state.demand == 180
    assert state.total_capacity() < state.demand
    assert state.emergency == {"status": "active", "rounds_left": 6, "hold": 0}
    banner = game_env.elements["emergency-status-display"]
    game_env.module.render()
    assert banner.hidden is False and "EMERGENCY" in banner.innerText


def test_scenario_button_cycles_into_emergency(game_env):
    for _ in range(3):
        game_env.elements["scenario-toggle-button"].dispatch("click", None)
    assert game_env.state.scenario == "emergency"
    game_env.elements["scenario-toggle-button"].dispatch("click", None)
    assert game_env.state.scenario == "standard"
    assert game_env.state.emergency is None
    assert game_env.state.demand == 100


def test_emergency_stabilizes_after_holding_capacity(game_env):
    state = game_env.state
    state.apply_scenario("emergency")
    state.plant_counts["nuclear"] = 2  # capacity 275 > demand
    state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    assert state.emergency["status"] == "active" and state.emergency["hold"] == 1
    state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    assert state.emergency["status"] == "stabilized"


def test_emergency_hold_resets_when_capacity_drops(game_env):
    state = game_env.state
    state.apply_scenario("emergency")
    state.plant_counts["nuclear"] = 2
    state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    state.plant_counts["nuclear"] = 0
    state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    assert state.emergency["hold"] == 0


def test_emergency_missed_is_not_game_over(game_env):
    g = game_env.module
    state = game_env.state
    state.apply_scenario("emergency")
    for _ in range(g.EMERGENCY_ROUNDS):
        state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    assert state.emergency["status"] == "missed"
    assert "no game over" in g.emergency_message()
    state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)  # play continues
    assert state.emergency["status"] == "missed"


def test_emergency_only_starts_before_first_build(game_env):
    state = game_env.state
    state.funds = 1000
    game_env.build("coal")
    assert state.apply_scenario("emergency") is False


# --- persistence of round-3/4 fields -----------------------------------------


def test_round3_and_round4_fields_roundtrip(game_env):
    g = game_env.module
    state = game_env.state
    state.apply_scenario("emergency")
    state.demand_response_level = 3
    state.weather_log = ["Round 1: x"]
    state.active_policy = {"type": "carbon_pricing", "rounds_remaining": 2}
    state.maintenance_schedule["coal"] = 5
    state.plant_counts["battery"] = 2
    state.stored_energy = 40.0
    state.arbitrage_mode = "charge"
    snap = g.get_state()
    state.demand_response_level = 0
    state.active_policy = None
    state.maintenance_schedule["coal"] = 0
    state.stored_energy = 0
    state.emergency = None
    g.load_state(snap)
    assert state.demand_response_level == 3
    assert state.weather_log == ["Round 1: x"]
    assert state.active_policy == {"type": "carbon_pricing", "rounds_remaining": 2}
    assert state.maintenance_schedule["coal"] == 5
    assert state.stored_energy == 40.0 and state.arbitrage_mode == "charge"
    assert state.emergency["status"] == "active"


def test_corrupt_new_fields_fall_back_to_defaults(game_env):
    g = game_env.module
    state = game_env.state
    snap = g.get_state()
    snap.update(
        {
            "demand_response_level": "lots",
            "weather_log": "nope",
            "active_policy": {"type": "bogus", "rounds_remaining": 3},
            "maintenance_schedule": {"coal": 7, "gas": True, "solar": 3},
            "stored_energy": -50,
            "arbitrage_mode": "turbo",
            "emergency": {"status": "weird"},
            "policy_lever_available": "yes",
        }
    )
    g.load_state(snap)
    assert state.demand_response_level == 0
    assert state.active_policy is None
    assert state.maintenance_schedule["coal"] == 0
    assert state.maintenance_schedule["gas"] == 0
    assert state.maintenance_schedule["solar"] == 3
    assert state.stored_energy == 0
    assert state.arbitrage_mode == "idle"
    assert state.emergency is None
    assert state.policy_lever_available is False


def test_old_save_without_new_keys_loads(game_env):
    g = game_env.module
    snap = g.get_state()
    for key in ("demand_response_level", "stored_energy", "emergency", "active_policy", "maintenance_schedule"):
        snap.pop(key)
    assert g.load_state(snap) is True
