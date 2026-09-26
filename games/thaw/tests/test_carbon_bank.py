"""G3: the permafrost carbon bank."""


def test_starts_empty_and_buttons_disabled(game_env):
    m = game_env.module
    m.render()
    assert m.carbon_bank == 0
    assert "0 credits" in game_env.elements["carbon-bank-display"].innerText
    for key in "abc":
        assert game_env.elements[f"carbon-bank-{key}-button"].disabled is True


def test_no_credit_without_preservation(game_env):
    m = game_env.module
    assert m.bank_carbon_credits() == 0
    assert m.carbon_bank == 0


def test_region_with_preservation_and_low_acceleration_earns_one(game_env):
    m = game_env.module
    m.region.capacity["preserve"] = 1
    assert m.bank_carbon_credits() == 1
    assert m.carbon_bank == 1


def test_each_qualifying_region_earns_its_own_credit(game_env):
    m = game_env.module
    for r in (m.region, m.region_b, m.region_c):
        r.capacity["preserve"] = 1
    assert m.bank_carbon_credits() == 3


def test_region_d_never_earns(game_env):
    m = game_env.module
    m.region_d.capacity["preserve"] = 5
    assert m.bank_carbon_credits() == 0


def test_runaway_region_does_not_earn(game_env):
    m = game_env.module
    m.region.capacity["preserve"] = 1
    m.region.temperature = 30.0  # feedback far above the 1.2x bar
    assert m.bank_carbon_credits() == 0


def test_advance_round_banks_credits(game_env):
    m = game_env.module
    m.region.capacity["preserve"] = 1
    game_env.advance_round()
    game_env.advance_round()
    assert m.carbon_bank == 2


def test_bank_is_capped(game_env):
    m = game_env.module
    for r in (m.region, m.region_b, m.region_c):
        r.capacity["preserve"] = 1
    for _ in range(40):
        m.bank_carbon_credits()
    assert m.carbon_bank == m.CARBON_BANK_CAP


def test_spending_needs_enough_credits(game_env):
    m = game_env.module
    m.carbon_bank = m.CARBON_CREDITS_PER_GRANT - 1
    funds = m.region_b.funds
    assert m.spend_carbon_credits("b") is False
    assert m.region_b.funds == funds and m.carbon_bank == m.CARBON_CREDITS_PER_GRANT - 1


def test_spending_grants_funds_to_the_chosen_region_only(game_env):
    m = game_env.module
    m.carbon_bank = 12
    a, b, c = m.region.funds, m.region_b.funds, m.region_c.funds
    assert m.spend_carbon_credits("b") is True
    assert m.region_b.funds == b + m.CARBON_GRANT_FUNDS
    assert (m.region.funds, m.region_c.funds) == (a, c)
    assert m.carbon_bank == 12 - m.CARBON_CREDITS_PER_GRANT


def test_unknown_target_rejected(game_env):
    m = game_env.module
    m.carbon_bank = 30
    for bad in ("d", "x", "", None, 1):
        assert m.spend_carbon_credits(bad) is False
    assert m.carbon_bank == 30


def test_buttons_enable_and_spend_through_the_ui(game_env):
    m = game_env.module
    m.carbon_bank = 10
    m.render()
    button = game_env.elements["carbon-bank-c-button"]
    assert button.disabled is False
    funds = m.region_c.funds
    button.dispatch("click", None)
    assert m.region_c.funds == funds + m.CARBON_GRANT_FUNDS
    assert m.carbon_bank == 0 and button.disabled is True


def test_save_round_trip(game_env):
    m = game_env.module
    m.carbon_bank = 17
    data = m.get_state()
    assert data["carbon_bank"] == 17
    m.carbon_bank = 0
    m.load_state(data)
    assert m.carbon_bank == 17


def test_empty_bank_not_saved(game_env):
    assert "carbon_bank" not in game_env.module.get_state()


def test_load_rejects_bad_bank_values(game_env):
    m = game_env.module
    for bad in ("9", -1, 51, 2.5, True, None, [3], float("nan")):
        data = m.get_state()
        data["carbon_bank"] = bad
        m.carbon_bank = 20
        m.load_state(data)
        assert m.carbon_bank == 0
