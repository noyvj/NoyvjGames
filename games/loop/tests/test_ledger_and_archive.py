"""H-10 cycle ledger (sortable, CSV), H-28 cycle notes, H-1 Past Chains archive."""

import csv
import io
import json

import pytest


def play(env, cycles, buy=("recycle",)):
    env.chain.funds = 5000.0
    for kind in buy:
        env.invest_circularity(kind)
    for _ in range(cycles):
        env.advance_cycle()


# ------------------------------------------------------------------ ledger rows
def test_every_advance_adds_one_row_with_the_cycles_numbers(game_env):
    chain = game_env.chain
    chain.funds = 300.0
    game_env.invest_circularity("repair")  # 20 funds
    game_env.advance_cycle()
    row = chain.ledger[0]
    assert row["cycle"] == 1
    assert row["spent"] == 20.0
    assert row["revenue"] == 250.0 and row["export"] == 0.0
    assert row["extraction"] == 47.0 and row["extraction_cost"] == pytest.approx(94.0)
    assert row["repair"] == 3.0 and row["reuse"] == 0.0 and row["recycle"] == 0.0 and row["trade"] == 0.0
    assert row["damage"] == 0.0 and row["multiplier"] == 1.0
    assert row["partners"] == ""
    assert row["funds_after"] == pytest.approx(chain.funds, abs=0.1)
    assert chain.funds == pytest.approx(300 - 20 + 250 - 94)


def test_spent_is_what_left_the_pot_between_advances(game_env):
    chain = game_env.chain
    game_env.advance_cycle()
    after_first = chain.funds
    chain.funds = after_first
    game_env.invest_circularity("reuse")
    game_env.invest_circularity("reuse")
    game_env.advance_cycle()
    assert chain.ledger[1]["spent"] == 50.0


def test_rows_record_partners_and_trade_units(game_env):
    chain = game_env.chain
    chain.funds = 1000.0
    game_env.invest_trade_link()
    game_env.invest_overseas_trade()
    game_env.advance_cycle()
    row = chain.ledger[0]
    assert row["partners"] == "TO"
    assert row["trade"] == pytest.approx(4.0 + 15.0)


def test_a_port_strike_row_leaves_the_struck_partner_out(game_env):
    chain = game_env.chain
    chain.funds = 1000.0
    game_env.invest_trade_link()
    game_env.invest_regional_trade()
    chain.market_shocks = True
    chain.cycle_number = 9  # the first strike hits the Trade Link
    chain.advance_cycle()
    assert chain.ledger[0]["partners"] == "R"


def test_the_ledger_is_capped(game_env):
    chain = game_env.chain
    for _ in range(game_env.module.LEDGER_MAX + 15):
        chain.advance_cycle()
    assert len(chain.ledger) == game_env.module.LEDGER_MAX
    assert chain.ledger[-1]["cycle"] == game_env.module.LEDGER_MAX + 15


def test_funds_never_drop_on_a_bad_cycle(game_env):
    chain = game_env.chain
    chain.total_extracted = 5000.0  # maximum damage
    chain.market_shocks = True
    chain.cycle_number = 13  # demand surge: 60 units at x2.5
    chain.funds = 40.0
    chain.advance_cycle()
    assert chain.funds == 40.0
    assert all(v >= 0 for v in (chain.ledger[0]["extraction_cost"], chain.ledger[0]["funds_after"]))


# ------------------------------------------------------------------ notes
def test_a_note_lands_in_the_row_and_the_box_clears(game_env):
    box = game_env.elements["cycle-note-input"]
    box.value = "  tried   recycling first "
    game_env.advance_cycle()
    assert game_env.chain.ledger[0]["note"] == "tried recycling first"
    assert box.value == ""
    game_env.advance_cycle()
    assert game_env.chain.ledger[1]["note"] == ""


def test_notes_are_one_clean_line_of_limited_length(game_env):
    clean = game_env.module.clean_note
    assert clean("a\nb\tc") == "a b c"
    assert len(clean("x" * 500)) == game_env.module.LEDGER_NOTE_MAX
    assert clean(None) == "" and clean(5) == ""


def test_a_note_is_escaped_in_the_table(game_env):
    game_env.elements["cycle-note-input"].value = "<b>bold</b> & more"
    game_env.advance_cycle()
    html = game_env.elements["ledger-table"].innerHTML
    assert "<b>" not in html and "&lt;b&gt;bold&lt;/b&gt; &amp; more" in html


# ------------------------------------------------------------------ table, sort, CSV
def test_the_table_starts_empty_with_a_hint(game_env):
    assert "No cycles yet" in game_env.elements["ledger-table"].innerHTML


def test_default_order_is_newest_first_and_sorting_works(game_env):
    chain = game_env.chain
    chain.funds = 5000.0
    for _ in range(3):
        chain.advance_cycle()
    chain.ledger[1]["extraction"] = 99.0
    m = game_env.module
    assert [r["cycle"] for r in m.sorted_ledger()] == [3, 2, 1]
    select = game_env.elements["ledger-sort-select"]
    select.value = "oldest"
    select.dispatch("change", None)
    assert [r["cycle"] for r in m.sorted_ledger()] == [1, 2, 3]
    select.value = "extraction"
    select.dispatch("change", None)
    assert m.sorted_ledger()[0]["cycle"] == 2
    html = game_env.elements["ledger-table"].innerHTML
    assert html.index("<td>2</td>") < html.index("<td>1</td>")


def test_an_unknown_sort_is_ignored(game_env):
    select = game_env.elements["ledger-sort-select"]
    select.value = "hax"
    select.dispatch("change", None)
    assert game_env.module.ledger_sort == "newest"


def test_the_table_shows_only_the_latest_rows_but_the_csv_has_all(game_env):
    chain = game_env.chain
    for _ in range(55):
        chain.advance_cycle()
    game_env.module.render()
    assert game_env.elements["ledger-table"].innerHTML.count("<tr>") == game_env.module.LEDGER_ROWS_SHOWN + 1
    assert "Showing 40 of 55" in game_env.elements["ledger-table"].innerHTML
    assert len(game_env.module.ledger_csv().splitlines()) == 56


def test_csv_round_trips_through_a_csv_reader(game_env):
    game_env.elements["cycle-note-input"].value = 'said "hello", then left'
    game_env.chain.funds = 5000.0
    game_env.invest_circularity("recycle")
    game_env.advance_cycle()
    rows = list(csv.DictReader(io.StringIO(game_env.module.ledger_csv())))
    assert len(rows) == 1
    row = rows[0]
    assert row["cycle"] == "1" and row["recycle_units"] == "5.0"
    assert row["note"] == 'said "hello", then left'
    assert row["partners"] == "-"
    assert float(row["net"]) == float(row["funds_in"]) - float(row["extraction_cost"])


def test_copy_button_reports_the_outcome(game_env):
    game_env.advance_cycle()
    game_env.elements["ledger-copy-button"].dispatch("click", None)
    assert game_env.elements["ledger-copy-status"].innerText.startswith(("Copied 1 cycle", "Could not copy"))


# ------------------------------------------------------------------ ledger saves
def test_the_ledger_round_trips(game_env):
    m = game_env.module
    game_env.elements["cycle-note-input"].value = "first"
    play(game_env, 3)
    saved = json.loads(json.dumps(m.get_state()))
    assert len(saved["ledger"]) == 3 and len(saved["ledger"][0]) == len(m.LEDGER_COLUMNS)
    before = [dict(r) for r in game_env.chain.ledger]
    game_env.chain.ledger = []
    m.load_state(saved)
    assert game_env.chain.ledger == before


def test_no_ledger_key_when_there_is_nothing(game_env):
    assert "ledger" not in game_env.module.get_state()


def test_old_saves_load_with_an_empty_ledger(game_env):
    m = game_env.module
    play(game_env, 2)
    state = m.get_state()
    state.pop("ledger")
    m.load_state(state)
    assert game_env.chain.ledger == []
    game_env.advance_cycle()
    assert game_env.chain.ledger[0]["spent"] is None  # unknown: the earlier cycles were not recorded


@pytest.mark.parametrize("bad", [
    "text", 5, [[1, 2, 3]], [["x"] * 15], [[0] + [0] * 14], [[1, -5] + [0] * 13],
    [[1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 150, 1, "", 0, ""]],      # damage over 100
    [[1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, "XYZ", 0, ""]],     # unknown partner letters
    [[1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, "", 0, 7]],         # note not a string
    [[True, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, "", 0, ""]],
    [[1, float("nan")] + [0] * 13],
])
def test_malformed_ledgers_are_dropped(game_env, bad):
    m = game_env.module
    play(game_env, 1)
    state = m.get_state()
    state["ledger"] = bad
    m.load_state(state)
    assert game_env.chain.ledger == []


def test_good_rows_survive_beside_bad_ones(game_env):
    m = game_env.module
    play(game_env, 2)
    state = m.get_state()
    state["ledger"] = [["junk"], state["ledger"][0], 7, state["ledger"][1]]
    m.load_state(state)
    assert [r["cycle"] for r in game_env.chain.ledger] == [1, 2]


def test_a_rewind_takes_the_row_back(game_env):
    game_env.advance_cycle()
    game_env.advance_cycle()
    assert len(game_env.chain.ledger) == 2
    game_env.chain.rewind()
    assert len(game_env.chain.ledger) == 1


def test_cycle_summary_uses_real_extraction_during_a_surge(game_env):
    chain = game_env.chain
    chain.market_shocks = True
    chain.advance_cycle()
    chain.cycle_number = 13
    chain.advance_cycle()
    assert "extraction up 10" in game_env.module.cycle_summary_text()


# ------------------------------------------------------------------ past chains
def reset_with_confirm(env):
    env.reset_chain()  # no shared dialog in the fake DOM, so it just goes ahead


def test_a_chain_that_never_ran_is_not_archived(game_env):
    reset_with_confirm(game_env)
    assert game_env.module.past_chains == []
    assert game_env.elements["past-chains-empty"].hidden is False


def test_a_reset_files_the_chain_with_its_numbers(game_env):
    m = game_env.module
    chain = game_env.chain
    chain.funds = 5000.0
    for _ in range(11):
        game_env.invest_circularity("recycle")
    game_env.advance_cycle()
    game_env.advance_cycle()
    score = chain.score()
    reset_with_confirm(game_env)
    assert len(m.past_chains) == 1
    record = m.past_chains[0]
    assert record["cycles"] == 2 and record["closed"] == 1
    assert record["recycle"] == 11 and record["extracted"] == 0.0
    assert record["score"] == pytest.approx(score, abs=0.1)
    assert record["category"] == "electronics" and record["curve"] == [1.0, 1.0]
    assert game_env.chain.cycle_number == 1  # and a fresh chain started


def test_only_the_latest_chains_are_kept(game_env):
    m = game_env.module
    for _ in range(m.PAST_CHAINS_MAX + 4):
        game_env.advance_cycle()
        reset_with_confirm(game_env)
    assert len(m.past_chains) == m.PAST_CHAINS_MAX


def test_long_curves_are_thinned(game_env):
    m = game_env.module
    for _ in range(200):
        game_env.chain.advance_cycle()
    reset_with_confirm(game_env)
    assert len(m.past_chains[0]["curve"]) <= m.PAST_CURVE_POINTS


def test_the_panel_lists_chains_newest_first_and_draws_a_chart(game_env):
    m = game_env.module
    game_env.advance_cycle()
    reset_with_confirm(game_env)
    game_env.chain.funds = 5000.0
    game_env.invest_circularity("recycle")
    game_env.advance_cycle()
    reset_with_confirm(game_env)
    game_env.advance_cycle()
    html = game_env.elements["past-chains-list"].innerHTML
    assert html.index("Chain 2:") < html.index("Chain 1:")
    assert game_env.elements["past-chains-empty"].hidden is True
    svg = game_env.elements["past-chains-chart"].innerHTML
    assert svg.startswith("<svg") and svg.count("<polyline") == 3  # two past chains and the one in play
    assert "stroke-dasharray" in svg and ">now<" in svg
    assert m.past_chains_svg() == svg


def test_the_chart_shows_at_most_five_past_chains(game_env):
    for _ in range(8):
        game_env.advance_cycle()
        reset_with_confirm(game_env)
    svg = game_env.module.past_chains_svg()
    assert svg.count("<polyline") == 5


def test_past_chains_survive_a_new_chain_and_ride_the_save(game_env):
    m = game_env.module
    game_env.advance_cycle()
    reset_with_confirm(game_env)
    state = json.loads(json.dumps(m.get_state()))
    assert len(state["past_chains"]) == 1
    m.past_chains.clear()
    m.load_state(state)
    assert len(m.past_chains) == 1 and m.past_chains[0]["cycles"] == 1


def test_a_save_without_past_chains_clears_them(game_env):
    m = game_env.module
    game_env.advance_cycle()
    reset_with_confirm(game_env)
    state = m.get_state()
    state.pop("past_chains")
    m.load_state(state)
    assert m.past_chains == []


@pytest.mark.parametrize("bad", [
    "x", 3, [1], [{}],
    [{"category": "nope", "cycles": 1, "closed": None, "extracted": 0, "score": 0,
      "repair": 0, "reuse": 0, "recycle": 0, "trade": 0, "curve": [0.5]}],
    [{"category": "clothing", "cycles": 0, "closed": None, "extracted": 0, "score": 0,
      "repair": 0, "reuse": 0, "recycle": 0, "trade": 0, "curve": [0.5]}],
    [{"category": "clothing", "cycles": 3, "closed": "x", "extracted": 0, "score": 0,
      "repair": 0, "reuse": 0, "recycle": 0, "trade": 0, "curve": [0.5]}],
    [{"category": "clothing", "cycles": 3, "closed": None, "extracted": 0, "score": 0,
      "repair": -1, "reuse": 0, "recycle": 0, "trade": 0, "curve": [0.5]}],
    [{"category": "clothing", "cycles": 3, "closed": None, "extracted": 0, "score": 0,
      "repair": 0, "reuse": 0, "recycle": 0, "trade": 0, "curve": []}],
    [{"category": "clothing", "cycles": 3, "closed": None, "extracted": 0, "score": 0,
      "repair": 0, "reuse": 0, "recycle": 0, "trade": 0, "curve": [1.5]}],
])
def test_malformed_past_chains_are_dropped(game_env, bad):
    m = game_env.module
    state = m.get_state()
    state["past_chains"] = bad
    m.load_state(state)
    assert m.past_chains == []
