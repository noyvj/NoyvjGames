"""J3 -- the Trade Guild: occasional optional bulk contracts."""

import json


def _seed(module, seed=1):
    module.guild_rng.seed(seed)


def _ready(module):
    """Enough sales that the guild is willing to make an offer."""
    module.total_sales_count = module.GUILD_MIN_SALES


def test_nothing_is_offered_before_a_few_sales(game_env):
    module = game_env.module
    for _ in range(module.GUILD_FIRST_OFFER_TICKS + 5):
        module.guild_tick()
    assert module.guild_state == "none"


def test_an_offer_appears_after_the_delay_once_sales_exist(game_env):
    module = game_env.module
    _seed(module)
    _ready(module)
    for _ in range(module.GUILD_FIRST_OFFER_TICKS):
        module.guild_tick()
    assert module.guild_state == "offered"
    c = module.guild_contract
    assert module.GUILD_UNITS_MIN <= c["units"] <= module.GUILD_UNITS_MAX
    assert c["destination"] in module.active_colony_ids()
    assert c["good"] == module.ALL_COLONIES[c["destination"]]["needs"]
    assert c["reward"] > 0


def test_accepting_starts_the_deadline_and_declining_clears_with_a_cooldown(game_env):
    module = game_env.module
    _seed(module)
    assert module.guild_accept() is False  # nothing offered
    assert module.guild_make_offer() is True
    assert module.guild_accept() is True
    assert module.guild_state == "active" and module.guild_contract["ticks_left"] == module.GUILD_DEADLINE_TICKS
    module._guild_clear()
    module.guild_make_offer()
    assert module.guild_decline() is True
    assert module.guild_state == "none" and module.guild_cooldown == module.GUILD_COOLDOWN_TICKS


def test_an_unanswered_offer_lapses_without_penalty(game_env):
    module = game_env.module
    _seed(module)
    module.guild_make_offer()
    for _ in range(module.GUILD_OFFER_LAPSE_TICKS):
        module.guild_tick()
    assert module.guild_state == "none" and module.guild_failed == 0


def test_delivering_the_contract_pays_the_bonus_once(game_env):
    module = game_env.module
    _seed(module)
    module.guild_make_offer()
    module.guild_accept()
    c = dict(module.guild_contract)
    before = module.total_profit
    module.guild_record_delivery(c["good"], c["destination"], c["units"] - 1)
    assert module.guild_state == "active" and module.total_profit == before
    module.guild_record_delivery(c["good"], c["destination"], 1)
    assert module.total_profit == before + c["reward"]
    assert module.guild_completed == 1 and module.guild_state == "none"
    assert "guild_partner" in module.achievement_ids_earned()


def test_only_the_right_good_to_the_right_colony_counts(game_env):
    module = game_env.module
    _seed(module)
    module.guild_make_offer()
    module.guild_accept()
    c = module.guild_contract
    other_dest = next(cid for cid in module.active_colony_ids() if cid != c["destination"])
    module.guild_record_delivery(c["good"], other_dest, 50)
    module.guild_record_delivery("not_the_good", c["destination"], 50)
    assert c["delivered"] == 0 and module.guild_state == "active"


def test_a_missed_deadline_costs_nothing_but_no_bonus(game_env):
    module = game_env.module
    _seed(module)
    module.guild_make_offer()
    module.guild_accept()
    before = module.total_profit
    for _ in range(module.GUILD_DEADLINE_TICKS):
        module.guild_tick()
    assert module.guild_state == "none" and module.guild_failed == 1 and module.total_profit == before


def test_a_real_delivery_through_the_game_counts(game_env):
    module = game_env.module
    module.guild_make_offer()
    module.guild_state = "active"
    module.guild_contract.update({"good": "ore", "destination": "ferrum", "units": 10, "delivered": 0, "ticks_left": 100, "reward": 777})
    game_env.load(ship_id="1")  # ship 1 starts at Aurum with ore
    game_env.depart("ferrum", ship_id="1")
    before = module.total_profit
    game_env.tick(module.TRAVEL_TICKS)
    assert module.guild_contract["delivered"] > 0 or module.guild_completed == 1
    assert module.total_profit > before


def test_five_completions_earn_the_favorite_achievement(game_env):
    module = game_env.module
    module.guild_completed = 5
    assert {"guild_partner", "guild_favorite"} <= set(module.achievement_ids_earned())


def test_panel_shows_the_offer_and_the_buttons(game_env):
    module = game_env.module
    _seed(module)
    module.render()
    assert game_env.elements["guild-accept-button"].hidden is True
    module.guild_make_offer()
    module.render()
    assert game_env.elements["guild-accept-button"].hidden is False
    assert "Trade Guild offers a contract" in game_env.elements["guild-status-display"].innerText
    game_env.elements["guild-accept-button"].dispatch("click", None)
    assert module.guild_state == "active"
    assert "Contract accepted" in game_env.elements["guild-status-display"].innerText
    assert game_env.elements["guild-accept-button"].hidden is True


def test_save_round_trip_and_default_save_is_unchanged(game_env):
    module = game_env.module
    assert "guild" not in module.get_state()
    _seed(module)
    module.guild_make_offer()
    module.guild_accept()
    module.guild_contract["delivered"] = 3
    module.guild_completed = 2
    saved = json.loads(json.dumps(module.get_state()))
    assert saved["guild"]["state"] == "active" and saved["guild"]["completed"] == 2
    module._guild_clear()
    module.guild_completed = 0
    assert module.load_state(saved) is True
    assert module.guild_state == "active" and module.guild_contract["delivered"] == 3 and module.guild_completed == 2


def test_tampered_guild_saves_fall_back_safely(game_env):
    module = game_env.module
    good = {"state": "active", "good": "grain", "destination": "aurum", "units": 12, "delivered": 2,
            "ticks_left": 50, "reward": 100, "completed": 1, "failed": 0}
    bad_variants = [
        {**good, "destination": "atlantis"},
        {**good, "good": "ore"},               # aurum needs grain, not ore
        {**good, "units": 9999},
        {**good, "delivered": 99},
        {**good, "ticks_left": 0},
        {**good, "reward": -5},
        {**good, "state": "weird"},
        {**good, "units": True},
        "not a dict",
        None,
    ]
    for variant in bad_variants:
        saved = module.get_state()
        saved["guild"] = variant
        module.load_state(saved)
        assert module.guild_state == "none", variant
    saved = module.get_state()
    saved["guild"] = good
    module.load_state(saved)
    assert module.guild_state == "active"


def test_an_expansion_contract_is_dropped_when_loaded_without_the_expansion(game_env):
    module = game_env.module
    saved = module.get_state()
    saved["guild"] = {"state": "active", "good": "biomass", "destination": "kepler_a", "units": 10,
                      "delivered": 0, "ticks_left": 20, "reward": 50, "completed": 0, "failed": 0}
    module.load_state(saved)
    assert module.guild_state == "none"


def test_founding_a_new_corporation_resets_the_guild(game_env):
    module = game_env.module
    _seed(module)
    module.guild_make_offer()
    module.guild_accept()
    module.endgame_reached = True
    module.found_new_corporation()
    assert module.guild_state == "none"
