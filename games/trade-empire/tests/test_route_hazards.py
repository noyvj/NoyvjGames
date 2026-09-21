"""J11 -- opt-in route hazards and insurance: a loaded arrival can be
disrupted (cargo lost); insurance costs a premium per ship in transit and
refunds a share of the lost trip. Everything is off by default."""


class FixedRng:
    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value


def _ship_arriving(game, good, qty, origin="aurum", destination="ferrum"):
    ship = game.ships[next(iter(game.ships))]
    ship.location = None
    ship.origin = origin
    ship.destination = destination
    ship.cargo_good = good
    ship.cargo_qty = qty
    ship.transit_ticks_remaining = 1
    return ship


def test_off_by_default_so_arrivals_are_never_disrupted(game_env):
    game = game_env.module
    game.hazard_rng = FixedRng(0.0)  # would disrupt if hazards were on
    ship = _ship_arriving(game, game.ORE, 10)
    result = ship.advance_transit()
    assert result[1] == 10 and game.disruptions_suffered == 0


def test_a_disrupted_arrival_loses_the_cargo_and_pays_nothing_uninsured(game_env):
    game = game_env.module
    game.route_hazards_enabled = True
    game.hazard_rng = FixedRng(0.0)
    ship = _ship_arriving(game, game.ORE, 10)
    result = ship.advance_transit()
    assert result == (game.ORE, 0, 0)
    assert game.disruptions_suffered == 1 and ship.cargo_qty == 0 and ship.docked


def test_an_arrival_above_the_hazard_chance_is_a_normal_sale(game_env):
    game = game_env.module
    game.route_hazards_enabled = True
    game.hazard_rng = FixedRng(game.ROUTE_HAZARD_CHANCE + 0.01)
    result = _ship_arriving(game, game.ORE, 10).advance_transit()
    assert result[1] == 10 and result[2] > 0 and game.disruptions_suffered == 0


def test_insurance_refunds_a_share_of_the_lost_trip(game_env):
    game = game_env.module
    game.route_hazards_enabled = True
    game.route_insurance_enabled = True
    game.hazard_rng = FixedRng(0.0)
    expected_trip = int(round(10 * game.current_sell_price(game.ORE) * game.diplomacy_multiplier()))
    result = _ship_arriving(game, game.ORE, 10).advance_transit()
    assert result[2] == int(round(expected_trip * game.INSURANCE_COVERAGE)) > 0
    assert game.insurance_payouts == result[2]


def test_a_disruption_in_tick_credits_only_the_payout_and_skips_market_impact(game_env):
    game = game_env.module
    game.route_hazards_enabled = True
    game.route_insurance_enabled = True
    game.hazard_rng = FixedRng(0.0)
    multiplier_before = game.market_multiplier[game.ORE]
    profit_before = game.total_profit
    sales_before = game.total_sales_count
    _ship_arriving(game, game.ORE, 10)
    game.tick()
    assert game.total_sales_count == sales_before
    assert game.market_multiplier[game.ORE] >= multiplier_before
    assert game.total_profit > profit_before  # payout arrived (premium is small)


def test_premiums_are_charged_per_ship_in_transit_only_while_insured(game_env):
    game = game_env.module
    game.total_profit = 100
    ship = _ship_arriving(game, game.ORE, 10)
    ship.transit_ticks_remaining = 5
    game.route_hazards_enabled = True
    game.tick()
    assert game.total_profit == 100  # hazards on but not insured
    game.route_insurance_enabled = True
    game.tick()
    assert game.total_profit == 100 - game.INSURANCE_PREMIUM_PER_TICK
    assert game.premiums_paid == game.INSURANCE_PREMIUM_PER_TICK


def test_premiums_never_take_credits_below_zero(game_env):
    game = game_env.module
    game.total_profit = 0
    ship = _ship_arriving(game, game.ORE, 10)
    ship.transit_ticks_remaining = 5
    game.route_hazards_enabled = True
    game.route_insurance_enabled = True
    game.tick()
    assert game.total_profit == 0 and game.premiums_paid == 0


def test_buttons_toggle_the_modes_and_insurance_needs_hazards(game_env):
    game = game_env.module
    insurance = game_env.elements["route-insurance-toggle-button"]
    assert insurance.disabled is True
    game_env.elements["route-hazards-toggle-button"].dispatch("click", None)
    assert game.route_hazards_enabled is True and insurance.disabled is False
    insurance.dispatch("click", None)
    assert game.route_insurance_enabled is True
    assert "Hazards on" in game_env.elements["route-hazards-status"].innerText


def test_state_round_trips_and_tolerates_bad_saved_values(game_env):
    game = game_env.module
    game.route_hazards_enabled = True
    game.route_insurance_enabled = True
    game.disruptions_suffered, game.insurance_payouts, game.premiums_paid = 3, 40, 12
    saved = game.get_state()
    assert saved["route_hazards"] == {
        "hazards": True, "insurance": True, "disruptions": 3, "payouts": 40, "premiums": 12,
    }
    game.route_hazards_enabled = game.route_insurance_enabled = False
    game.disruptions_suffered = game.insurance_payouts = game.premiums_paid = 0
    game.load_state(saved)
    assert game.route_hazards_enabled and game.route_insurance_enabled
    assert (game.disruptions_suffered, game.insurance_payouts, game.premiums_paid) == (3, 40, 12)
    for bad in ("junk", None, 7, {"hazards": "yes", "insurance": 1, "disruptions": -1, "payouts": 1e30, "premiums": True}):
        saved["route_hazards"] = bad
        game.load_state(saved)
        assert game.route_hazards_enabled is False and game.route_insurance_enabled is False
        assert (game.disruptions_suffered, game.insurance_payouts, game.premiums_paid) == (0, 0, 0)
    del saved["route_hazards"]
    game.route_hazards_enabled = True
    game.load_state(saved)
    assert game.route_hazards_enabled is False
