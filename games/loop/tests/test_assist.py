"""H-8: Assist mode (Off / Hints / Guided); assisted chains are tagged and kept out of mastery records."""

import pytest


def set_assist(env, mode):
    env.elements["assist-select"].value = mode
    env.elements["assist-select"].dispatch("change", None)


def best_buttons(env):
    ids = ("repair-invest-button", "reuse-invest-button", "recycle-invest-button", "trade-link-invest-button",
           "regional-trade-invest-button", "overseas-trade-invest-button")
    return [i for i in ids if "assist-best" in env.elements[i].classList]


def test_assist_starts_off_and_says_so(game_env):
    chain = game_env.chain
    assert chain.assist == "off" and chain.assist_used is False
    assert best_buttons(game_env) == []
    assert game_env.elements["assist-hint"].hidden is True
    assert "Off" in game_env.elements["assist-status"].innerText


def test_unknown_modes_are_refused(game_env):
    chain = game_env.chain
    assert chain.set_assist("loud") is False and chain.set_assist(None) is False and chain.set_assist(3) is False
    assert chain.assist == "off" and chain.assist_used is False


def test_switching_it_on_tags_the_chain_for_good(game_env):
    chain = game_env.chain
    set_assist(game_env, "hints")
    assert chain.assist == "hints" and chain.assist_used is True
    set_assist(game_env, "off")
    assert chain.assist == "off" and chain.assist_used is True
    assert "stays tagged" in game_env.elements["assist-status"].innerText


def test_hints_pick_the_most_supply_per_fund_that_is_actually_used(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 500.0
    best_now, best_any = module.assist_best()
    # Recycling (5 units for 30) and the Overseas Consortium (15 for 90) tie at 6 funds a unit; the earlier kind wins
    assert best_now["kind"] == "recycle" and best_any["kind"] == "recycle"
    set_assist(game_env, "hints")
    assert best_buttons(game_env) == ["recycle-invest-button"]
    assert "Best value right now: Recycling" in game_env.elements["assist-hint"].innerText


def test_a_focused_measure_changes_the_best_buy(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 500.0
    chain.set_waste_focus("repair")  # 3 units x 1.25 = 3.75 for 20 funds = 0.1875 a fund
    best_now, _ = module.assist_best()
    assert best_now["kind"] == "repair"


def test_unaffordable_best_is_named_but_not_highlighted_as_a_buy(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 25.0  # a Recycling Loops costs 30
    set_assist(game_env, "hints")
    best_now, best_any = module.assist_best()
    assert best_now["kind"] == "reuse" and best_any["kind"] == "recycle"
    assert "Recycling is better value but costs 30" in game_env.elements["assist-hint"].innerText
    chain.funds = 5.0
    game_env.module.render()
    hint = game_env.elements["assist-hint"].innerText
    assert "cannot afford anything yet" in hint and "Recycling" in hint


def test_supply_beyond_what_the_cycle_needs_does_not_count(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 5000.0
    for _ in range(9):
        chain.invest_circularity("recycle")
    chain.invest_circularity("repair")  # 48 of 50 units: 2 still needed
    options = {o["kind"]: o for o in module.assist_options()}
    assert options["overseas"]["used"] == pytest.approx(2.0) and options["overseas"]["units"] == 15.0
    best_now, _ = module.assist_best()
    assert best_now["kind"] == "repair"  # 2 units used for 20 funds beats 2 used for 30 or 90


def test_a_closed_loop_needs_no_more(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 5000.0
    for _ in range(10):
        chain.invest_circularity("recycle")
    set_assist(game_env, "hints")
    assert module.assist_best() == (None, None)
    assert "loop is closed" in game_env.elements["assist-hint"].innerText
    assert best_buttons(game_env) == []


def test_a_port_strike_removes_that_partner_from_the_options(game_env):
    module, chain = game_env.module, game_env.chain
    chain.market_shocks = True
    chain.cycle_number = 9  # the first strike shuts the Trade Link
    options = {o["kind"]: o for o in module.assist_options()}
    assert options["trade"]["units"] == 0.0 and options["trade"]["used"] == 0.0
    assert options["regional"]["units"] > 0


def test_guided_adds_the_reason_with_the_audit_numbers(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 500.0
    set_assist(game_env, "guided")
    text = game_env.elements["assist-hint"].innerText
    assert "Why: it takes this cycle's new extraction from 50 to 45 units" in text
    assert "saves about 10 funds" in text and "2.00 funds a unit" in text
    set_assist(game_env, "hints")
    assert "Why:" not in game_env.elements["assist-hint"].innerText


def test_assist_does_not_change_any_rule(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 500.0
    plain = ChainFacts(chain)
    set_assist(game_env, "guided")
    assert ChainFacts(chain) == plain


class ChainFacts:
    def __init__(self, chain):
        self.facts = (chain.funds, chain.new_extraction_needed(), chain.circular_supply(), chain.score())

    def __eq__(self, other):
        return self.facts == other.facts


def test_an_assisted_chain_adds_no_speed_flags_or_bests(game_env):
    module, chain = game_env.module, game_env.chain
    set_assist(game_env, "hints")
    chain.funds = 5000.0
    for _ in range(10):
        game_env.invest_circularity("recycle")
    game_env.advance_cycle()
    assert chain.first_loop_closed_cycle == 1
    assert module.career_speed == set() and module.career_best == {}
    # what you tried still counts: the category and plate are progress, not mastery
    assert "electronics" in module.career_closed_categories


def test_an_unassisted_chain_still_records_everything(game_env):
    module, chain = game_env.module, game_env.chain
    chain.funds = 5000.0
    for _ in range(10):
        game_env.invest_circularity("recycle")
    game_env.advance_cycle()
    assert "cycle12" in module.career_speed and module.career_best["electronics"]["fastest_close"] == 1


def test_an_assisted_chain_is_tagged_in_past_chains(game_env):
    module, chain = game_env.module, game_env.chain
    set_assist(game_env, "hints")
    game_env.advance_cycle()
    assert module.archive_chain() is True
    assert module.past_chains[-1]["assisted"] is True
    assert "Assisted." in module.past_chain_line(1, module.past_chains[-1])
    restored = module.past_chains_from_save(module.get_state()["past_chains"])
    assert restored[-1]["assisted"] is True
    module.past_chains[:] = []
    game_env.advance_cycle()
    module.chain.assist_used = False
    module.archive_chain()
    assert "assisted" not in module.past_chains[-1]


def test_assist_is_saved_only_when_used_and_loads_strictly(game_env):
    module, chain = game_env.module, game_env.chain
    state = module.get_state()
    assert "assist" not in state and "assist_used" not in state
    set_assist(game_env, "guided")
    state = module.get_state()
    assert state["assist"] == "guided" and state["assist_used"] is True
    module.load_state(state)
    assert module.chain.assist == "guided" and module.chain.assist_used is True
    state["assist"] = "shouting"
    state["assist_used"] = "yes"
    module.load_state(state)
    assert module.chain.assist == "off" and module.chain.assist_used is False
    names = [name for name, _ in module.load_report]
    assert "Assist mode" in names


def test_off_but_used_survives_a_save(game_env):
    module = game_env.module
    set_assist(game_env, "hints")
    set_assist(game_env, "off")
    state = module.get_state()
    assert "assist" not in state and state["assist_used"] is True
    module.load_state(state)
    assert module.chain.assist == "off" and module.chain.assist_used is True


def test_a_new_chain_is_untagged(game_env):
    module = game_env.module
    set_assist(game_env, "hints")
    game_env.reset_chain()
    assert module.chain.assist == "off" and module.chain.assist_used is False
