"""Shared save widget integration (SAVE-BUTTON-INTEGRATION.md): get_state()/
load_state() package every module-level mutable global (the `chain`
ChainState instance) into a JSON-safe dict and back. SOL is the reference
integration for this contract; these tests mirror its save-system test
suite for Loop's own state shape.
"""

import pytest


def test_get_state_includes_every_expected_key(game_env):
    data = game_env.module.get_state()
    assert set(data.keys()) == {
        "cycle_number",
        "funds",
        "total_extracted",
        "total_produced",
        "circularity_investment",
        "circular_fraction_log",
        "trade_link_investment",
    }


def test_get_state_deep_copies_circularity_investment(game_env):
    game_env.chain.invest_circularity("repair")
    data = game_env.module.get_state()

    game_env.chain.invest_circularity("repair")  # diverge after snapshot
    assert data["circularity_investment"]["repair"] == 1
    assert game_env.chain.circularity_investment["repair"] == 2


def test_get_state_deep_copies_circular_fraction_log(game_env):
    game_env.chain.advance_cycle()
    data = game_env.module.get_state()

    game_env.chain.advance_cycle()  # diverge after snapshot
    assert len(data["circular_fraction_log"]) == 1
    assert len(game_env.chain.circular_fraction_log) == 2


def test_load_state_restores_scalar_fields(game_env):
    game_env.chain.invest_circularity("recycle")
    game_env.chain.invest_trade_link()
    game_env.chain.advance_cycle()
    snapshot = game_env.module.get_state()

    game_env.chain.advance_cycle()  # diverge
    game_env.chain.invest_trade_link()

    result = game_env.module.load_state(snapshot)
    assert result is True
    assert game_env.chain.cycle_number == snapshot["cycle_number"]
    assert game_env.chain.funds == snapshot["funds"]
    assert game_env.chain.total_extracted == snapshot["total_extracted"]
    assert game_env.chain.total_produced == snapshot["total_produced"]
    assert game_env.chain.trade_link_investment == snapshot["trade_link_investment"]


def test_load_state_restores_circularity_investment(game_env):
    game_env.chain.invest_circularity("repair")
    game_env.chain.invest_circularity("reuse")
    game_env.chain.invest_circularity("recycle")
    snapshot = game_env.module.get_state()

    game_env.chain.invest_circularity("repair")  # diverge
    assert game_env.chain.circularity_investment["repair"] == 2

    game_env.module.load_state(snapshot)
    assert game_env.chain.circularity_investment == {
        "repair": 1,
        "reuse": 1,
        "recycle": 1,
    }


def test_load_state_restores_circular_fraction_log(game_env):
    game_env.chain.invest_circularity("recycle")
    game_env.chain.advance_cycle()
    game_env.chain.advance_cycle()
    snapshot = game_env.module.get_state()
    expected_log = list(game_env.chain.circular_fraction_log)

    game_env.chain.advance_cycle()  # diverge
    assert len(game_env.chain.circular_fraction_log) == 3

    game_env.module.load_state(snapshot)
    assert game_env.chain.circular_fraction_log == expected_log


def test_load_state_restores_trade_link_investment(game_env):
    game_env.chain.invest_trade_link()
    game_env.chain.invest_trade_link()
    snapshot = game_env.module.get_state()

    game_env.chain.invest_trade_link()  # diverge
    assert game_env.chain.trade_link_investment == 3

    game_env.module.load_state(snapshot)
    assert game_env.chain.trade_link_investment == 2
    assert game_env.chain.imported_supply() == pytest.approx(
        2 * game_env.module.IMPORT_SUPPLY_PER_UNIT
    )


def test_full_save_diverge_load_round_trip_restores_every_field(game_env):
    """The full contract: invest across every system (circularity +
    trade network), advance a couple of cycles, snapshot, diverge hard,
    then confirm load_state() restores the entire chain — not just one
    field — back to the snapshot."""
    game_env.chain.invest_circularity("repair")
    game_env.chain.invest_circularity("reuse")
    game_env.chain.invest_trade_link()
    game_env.chain.advance_cycle()
    game_env.chain.invest_circularity("recycle")
    game_env.chain.invest_trade_link()
    game_env.chain.advance_cycle()

    snapshot = game_env.module.get_state()
    expected = {
        "cycle_number": game_env.chain.cycle_number,
        "funds": game_env.chain.funds,
        "total_extracted": game_env.chain.total_extracted,
        "total_produced": game_env.chain.total_produced,
        "circularity_investment": dict(game_env.chain.circularity_investment),
        "circular_fraction_log": list(game_env.chain.circular_fraction_log),
        "trade_link_investment": game_env.chain.trade_link_investment,
    }

    # Diverge hard from the snapshot.
    game_env.chain.invest_circularity("recycle")
    game_env.chain.invest_trade_link()
    game_env.chain.advance_cycle()
    game_env.chain.advance_cycle()
    assert game_env.chain.cycle_number != expected["cycle_number"]

    result = game_env.module.load_state(snapshot)
    assert result is True
    assert game_env.chain.cycle_number == expected["cycle_number"]
    assert game_env.chain.funds == expected["funds"]
    assert game_env.chain.total_extracted == expected["total_extracted"]
    assert game_env.chain.total_produced == expected["total_produced"]
    assert game_env.chain.circularity_investment == expected["circularity_investment"]
    assert game_env.chain.circular_fraction_log == expected["circular_fraction_log"]
    assert game_env.chain.trade_link_investment == expected["trade_link_investment"]


def test_load_state_re_renders_vignette_and_trade_network_display(game_env):
    """Pass 2 additions aren't stored as separate fields — the vignette
    and trade-network text are derived from `chain` at render time — so
    the regression to guard is that load_state() actually calls render()
    and the restored chain state flows through to those displays."""
    game_env.chain.invest_circularity("recycle")
    game_env.chain.invest_circularity("recycle")
    game_env.chain.invest_circularity("recycle")
    game_env.chain.invest_circularity("recycle")
    game_env.chain.invest_trade_link()
    game_env.module.render()
    snapshot = game_env.module.get_state()
    expected_vignette = game_env.elements["vignette-display"].innerText
    expected_trade_display = game_env.elements["trade-network-display"].innerText

    # Diverge to a state with different circularity/trade investment.
    fresh_chain = game_env.module.ChainState()
    game_env.module.chain.__dict__.update(fresh_chain.__dict__)
    game_env.module.render()
    assert game_env.elements["vignette-display"].innerText != expected_vignette

    game_env.module.load_state(snapshot)
    assert game_env.elements["vignette-display"].innerText == expected_vignette
    assert game_env.elements["trade-network-display"].innerText == expected_trade_display


def test_load_state_tolerates_a_circularity_investment_dict_missing_a_key(game_env):
    """load_state() currently does `dict(data["circularity_investment"])`,
    a wholesale replace rather than a key-by-key merge against the current
    CIRCULARITY_INVESTMENTS schema. A save snapshot that is missing one of
    the three keys (e.g. one saved by an earlier build, before a measure
    existed, or simply hand-edited/corrupted) leaves `chain.circularity_investment`
    without that key entirely — and every render() call unconditionally
    reads `chain.circularity_investment[measure]` for every measure in
    CIRCULARITY_INVESTMENTS, so the very next render crashes with a
    KeyError instead of just treating the missing measure as zero."""
    game_env.chain.invest_circularity("repair")
    snapshot = game_env.module.get_state()
    snapshot["circularity_investment"] = {"repair": 2}  # "reuse"/"recycle" missing

    result = game_env.module.load_state(snapshot)
    assert result is True
    assert game_env.chain.circularity_investment == {
        "repair": 2,
        "reuse": 0,
        "recycle": 0,
    }
    # render() (called by load_state itself) must not have raised, and must
    # reflect the restored/defaulted counts.
    assert game_env.elements["repair-count"].innerText == "2"
    assert game_env.elements["reuse-count"].innerText == "0"
    assert game_env.elements["recycle-count"].innerText == "0"


def test_load_state_drops_a_stale_circularity_investment_key(game_env):
    """The flip side of the merge: a key in the save data that no longer
    exists in CIRCULARITY_INVESTMENTS (e.g. a retired measure from an old
    build) shouldn't linger in `chain.circularity_investment` forever —
    a key-by-key merge against the current schema drops it."""
    snapshot = game_env.module.get_state()
    snapshot["circularity_investment"] = {
        "repair": 1,
        "reuse": 1,
        "recycle": 1,
        "retired_measure": 5,
    }

    game_env.module.load_state(snapshot)
    assert game_env.chain.circularity_investment == {
        "repair": 1,
        "reuse": 1,
        "recycle": 1,
    }


def test_load_state_tolerates_a_save_missing_trade_link_investment(game_env):
    """PR #1 (sean-hart) review finding: unlike circularity_investment
    above, trade_link_investment was restored via a direct
    data["trade_link_investment"] subscript with no default. A save
    written before the Pass 2 trade-network field existed (or a
    hand-edited/corrupted payload) is missing this key entirely, so
    load_state() raised KeyError and the whole load failed — not just a
    later render, the load itself. Defaulting to 0 (a fresh chain's own
    starting value) makes an old save loadable instead of rejected."""
    snapshot = game_env.module.get_state()
    del snapshot["trade_link_investment"]

    result = game_env.module.load_state(snapshot)
    assert result is True
    assert game_env.chain.trade_link_investment == 0
    assert game_env.elements["trade-link-count"].innerText == "0"


def test_get_state_matches_shape_after_load_state_round_trip(game_env):
    game_env.chain.invest_circularity("reuse")
    game_env.chain.advance_cycle()
    snapshot = game_env.module.get_state()

    game_env.module.load_state(snapshot)
    assert game_env.module.get_state() == snapshot
