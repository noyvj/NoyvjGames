"""H13 (circular design challenge) and H23 (zero-waste challenge): the two
opt-in start-of-chain modes."""


def _click(env, id_):
    env.elements[id_].dispatch("click", None)


def test_modes_off_by_default(game_env):
    m = game_env.module
    assert game_env.chain.challenge_mode is False and game_env.chain.zero_waste is False
    assert game_env.chain.supply_multiplier() == 1.0
    m.render()
    assert game_env.elements["mode-status"].hidden is True


def test_challenge_toggle_button(game_env):
    _click(game_env, "challenge-mode-button")
    assert game_env.chain.challenge_mode is True
    assert "✓" in game_env.elements["challenge-mode-button"].innerText
    assert "65%" in game_env.elements["mode-status"].innerText
    _click(game_env, "challenge-mode-button")
    assert game_env.chain.challenge_mode is False


def test_zero_waste_toggle_button(game_env):
    _click(game_env, "zero-waste-mode-button")
    assert game_env.chain.zero_waste is True
    assert "under the cap" in game_env.elements["mode-status"].innerText


def test_challenge_scales_internal_and_imported_supply(game_env):
    m = game_env.module
    c = game_env.chain
    c.funds = 5000
    c.invest_circularity("recycle")
    c.invest_trade_link()
    base_internal, base_import = c.internal_circular_supply(), c.imported_supply()
    c.challenge_mode = True
    assert abs(c.internal_circular_supply() - base_internal * m.CHALLENGE_MODE_SUPPLY_MULTIPLIER) < 1e-9
    assert abs(c.imported_supply() - base_import * m.CHALLENGE_MODE_SUPPLY_MULTIPLIER) < 1e-9


def test_challenge_makes_closing_the_loop_harder(game_env):
    m = game_env.module
    c = game_env.chain
    per_unit = m.CIRCULARITY_INVESTMENTS["recycle"]["supply_per_unit"]
    units = int(m.PRODUCTION_TARGET / per_unit) + 1  # just enough to close the loop
    c.circularity_investment["recycle"] = units
    assert c.is_loop_closed()
    c.challenge_mode = True
    assert c.new_extraction_needed() > 0


def test_modes_locked_once_production_starts(game_env):
    game_env.advance_cycle()
    assert game_env.chain.can_choose_mode() is False
    _click(game_env, "challenge-mode-button")
    _click(game_env, "zero-waste-mode-button")
    assert game_env.chain.challenge_mode is False and game_env.chain.zero_waste is False


def test_modes_can_be_combined_and_status_shows_both(game_env):
    _click(game_env, "challenge-mode-button")
    _click(game_env, "zero-waste-mode-button")
    text = game_env.elements["mode-status"].innerText
    assert "Circular design challenge" in text and "Zero-waste challenge" in text


def test_zero_waste_is_soft_and_reports_a_miss(game_env):
    m = game_env.module
    c = game_env.chain
    c.zero_waste = True
    c.total_extracted = m.ZERO_WASTE_EXTRACTION_CAP
    assert c.zero_waste_holding() is True
    c.total_extracted = m.ZERO_WASTE_EXTRACTION_CAP + 1
    assert c.zero_waste_holding() is False
    m.render()
    assert "missed" in game_env.elements["mode-status"].innerText
    game_env.advance_cycle()  # play carries on; nothing blocks it
    assert c.cycle_number == 2


def test_zero_waste_status_tracks_extraction(game_env):
    _click(game_env, "zero-waste-mode-button")
    game_env.advance_cycle()  # straight-line chain extracts 50 units
    assert "50 of 150" in game_env.elements["mode-status"].innerText


def test_mode_status_stays_visible_after_the_picker_hides(game_env):
    _click(game_env, "zero-waste-mode-button")
    game_env.advance_cycle()
    assert game_env.elements["goods-category-picker"].hidden is True
    assert game_env.elements["mode-status"].hidden is False


def test_save_round_trip(game_env):
    m = game_env.module
    _click(game_env, "challenge-mode-button")
    _click(game_env, "zero-waste-mode-button")
    data = m.get_state()
    assert data["challenge_mode"] is True and data["zero_waste"] is True
    game_env.chain.challenge_mode = False
    game_env.chain.zero_waste = False
    m.load_state(data)
    assert game_env.chain.challenge_mode is True and game_env.chain.zero_waste is True


def test_default_save_omits_mode_keys(game_env):
    data = game_env.module.get_state()
    assert "challenge_mode" not in data and "zero_waste" not in data


def test_load_rejects_non_boolean_mode_values(game_env):
    m = game_env.module
    for bad in ("true", 1, [True], {"a": 1}, None):
        data = m.get_state()
        data["challenge_mode"] = bad
        data["zero_waste"] = bad
        m.load_state(data)
        assert game_env.chain.challenge_mode is False and game_env.chain.zero_waste is False


def test_starting_a_new_chain_resets_modes(game_env):
    _click(game_env, "challenge-mode-button")
    game_env.advance_cycle()
    game_env.elements["reset-chain-button"].dispatch("click", None)
    assert game_env.chain.challenge_mode is False
