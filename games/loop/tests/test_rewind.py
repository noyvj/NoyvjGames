"""GH-18 / FY-39: one rewind token per chain that undoes the last Advance Cycle."""

import pytest


def asked_confirms(game_env, monkeypatch):
    asked = []
    monkeypatch.setattr(
        game_env.module, "_confirm_dialog_ask",
        lambda action_id, message, confirm_label, on_confirm: asked.append((action_id, message, confirm_label, on_confirm)),
    )
    return asked


def rewind_click(env):
    env.elements["rewind-button"].dispatch("click", None)


def test_a_fresh_chain_has_a_token_but_nothing_to_rewind(game_env):
    chain = game_env.chain
    assert chain.rewind_used is False and chain.rewind_snapshot is None
    assert chain.can_rewind() is False
    assert game_env.elements["rewind-token-display"].innerText == "Rewind: 1 left"
    assert game_env.elements["rewind-button"].disabled is True
    assert "advance one" in game_env.elements["rewind-status"].innerText


def test_advancing_sets_the_undo_point_and_enables_the_button(game_env):
    game_env.advance_cycle()
    assert game_env.chain.can_rewind() is True
    assert game_env.elements["rewind-button"].disabled is False
    assert "start of cycle 1" in game_env.elements["rewind-status"].innerText


def test_rewind_restores_the_chain_exactly(game_env):
    chain = game_env.chain
    chain.funds = 500.0
    game_env.invest_circularity("recycle")
    before = chain._snapshot()
    game_env.advance_cycle()
    assert chain.cycle_number == 2
    assert chain.rewind()
    after = chain._snapshot()
    after["rewind_used"] = False  # the only difference allowed: the spent token
    assert after == before
    assert chain.rewind_used is True and chain.rewind_snapshot is None


def test_rewind_also_undoes_purchases_made_after_the_advance(game_env):
    chain = game_env.chain
    chain.funds = 500.0
    game_env.advance_cycle()
    game_env.invest_circularity("recycle")
    game_env.invest_circularity("recycle")
    funds_before_advance = chain.rewind_snapshot["funds"]
    chain.rewind()
    assert chain.circularity_investment["recycle"] == 0
    assert chain.funds == pytest.approx(funds_before_advance)
    assert chain.cycle_number == 1


def test_only_one_rewind_per_chain(game_env):
    chain = game_env.chain
    game_env.advance_cycle()
    assert chain.rewind() is True
    game_env.advance_cycle()
    assert chain.can_rewind() is False
    assert chain.rewind() is False
    assert game_env.elements["rewind-button"].innerText == "Rewind used"
    assert game_env.elements["rewind-token-display"].innerText == "Rewind: spent"


def test_the_button_asks_first_and_does_nothing_until_confirmed(game_env, monkeypatch):
    asked = asked_confirms(game_env, monkeypatch)
    game_env.advance_cycle()
    rewind_click(game_env)
    assert len(asked) == 1
    action_id, message, label, on_confirm = asked[0]
    assert action_id == "loop-rewind" and label == "Rewind"
    assert "cycle 1" in message
    assert game_env.chain.cycle_number == 2
    on_confirm()
    assert game_env.chain.cycle_number == 1
    assert game_env.chain.rewind_used is True
    assert game_env.elements["cycle-live-summary"].innerText == "Rewound to the start of cycle 1."


def test_confirmed_rewind_runs_without_the_shared_dialog(game_env):
    game_env.advance_cycle()
    rewind_click(game_env)  # no ConfirmDialog in the fake DOM, so it just goes ahead
    assert game_env.chain.cycle_number == 1


def test_a_clicked_rewind_with_no_point_does_nothing(game_env):
    rewind_click(game_env)
    assert game_env.chain.rewind_used is False


def test_a_cycle_that_donated_to_the_pool_cannot_be_rewound(game_env):
    chain = game_env.chain
    chain.funds = 5000.0
    for _ in range(14):
        game_env.invest_circularity("recycle")
    chain.donate_surplus = True
    game_env.advance_cycle()
    assert chain.last_donation > 0
    assert chain.can_rewind() is False
    assert "regional pool" in game_env.elements["rewind-status"].innerText


def test_start_new_chain_brings_back_the_token(game_env):
    game_env.advance_cycle()
    game_env.chain.rewind()
    assert game_env.chain.rewind_used is True
    game_env.reset_chain()
    assert game_env.chain.rewind_used is False
    assert game_env.elements["rewind-token-display"].innerText == "Rewind: 1 left"


def test_career_records_are_not_taken_back(game_env):
    m = game_env.module
    chain = game_env.chain
    chain.funds = 5000.0
    for _ in range(10):
        game_env.invest_circularity("recycle")
    game_env.advance_cycle()  # a fully closed cycle: the career notes it
    assert m.career_closed_categories
    chain.rewind()
    assert m.career_closed_categories  # it happened, so the record stays


def test_only_the_spent_token_is_saved_never_the_undo_point(game_env):
    m = game_env.module
    game_env.advance_cycle()
    assert "rewind_used" not in m.get_state()
    assert "rewind_snapshot" not in m.get_state()
    game_env.chain.rewind()
    state = m.get_state()
    assert state["rewind_used"] is True
    game_env.advance_cycle()
    m.load_state(m.get_state())
    assert game_env.chain.rewind_used is True
    assert game_env.chain.rewind_snapshot is None  # a loaded visit has to set a fresh undo point


def test_old_saves_load_with_a_fresh_token(game_env):
    m = game_env.module
    state = m.get_state()
    state.pop("rewind_used", None)
    m.load_state(state)
    assert game_env.chain.rewind_used is False


@pytest.mark.parametrize("bad", ["yes", 1, [], None, "True"])
def test_a_malformed_saved_flag_loads_as_unspent(game_env, bad):
    m = game_env.module
    state = m.get_state()
    state["rewind_used"] = bad
    m.load_state(state)
    assert game_env.chain.rewind_used is False


def test_the_snapshot_is_not_aliased_to_live_lists(game_env):
    chain = game_env.chain
    game_env.advance_cycle()
    chain.circular_fraction_log.append(0.9)
    chain.passport.append({"cycle": 99, "source": "extraction"})
    chain.rewind()
    assert len(chain.circular_fraction_log) == 0
    assert chain.passport == []
