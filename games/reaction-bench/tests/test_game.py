"""The game layer: dials, the ledger in the view, product choice, Run, the shelf, the table and the gate."""

import json

import elements
import game
import reactions

from .helpers import call, open_chapter, solve


def test_a_fresh_view_is_the_first_order_with_a_live_ledger():
    v = call(action="open")
    rx = v["reaction"]
    assert rx["id"] == "carbon-dioxide" and rx["number"] == 1 and rx["of"] == 24 and rx["status"] == "open" and not rx["round"]
    assert [s["formula"] for s in rx["species"]] == ["C", "O2", "CO2"] and [s["coef"] for s in rx["species"]] == [1, 1, 1]
    assert rx["balanced"] and rx["can_run"] and rx["equation"] == "1 C + 1 O2 gives 1 CO2"
    assert v["totals"]["shelved"] == 0 and v["totals"]["orders"] == 24 and v["totals"]["elements"] == 0


def test_the_view_never_contains_an_unshelved_orders_answer_or_fact():
    r = reactions.BY_ID["water"]
    call(action="pick", reaction="water")
    text = json.dumps(call(action="open"))
    assert r.blurb not in text and "blurb" not in call(action="open")["reaction"]
    rx = call(action="open")["reaction"]
    assert '"answer":' not in text and "answer" not in rx and "right" not in rx and "choices" in rx and rx["choices"] is None
    for locked in reactions.CHAPTERS[1]["reactions"] + reactions.CHAPTERS[2]["reactions"]:
        assert locked.title not in text and locked.fennel not in text and locked.blurb not in text


def test_turning_a_dial_updates_the_ledger_with_signed_differences():
    call(action="pick", reaction="water")
    v = call(action="dial", index=0, value=3)
    rows = {row["symbol"]: row for row in v["reaction"]["ledger"]}
    assert rows["H"]["diff"] == -4 and rows["H"]["left"] == 6 and rows["H"]["right"] == 2 and not rows["H"]["ok"]
    assert rows["O"]["diff"] == -1 and "1 too few on the right" in rows["O"]["text"]
    assert not v["reaction"]["balanced"] and not v["reaction"]["can_run"]
    v = call(action="dial", index=2, value=4)
    rows = {row["symbol"]: row for row in v["reaction"]["ledger"]}
    assert rows["H"]["diff"] == 2 and "2 too many on the right" in rows["H"]["text"]


def test_the_dials_turn_by_steps_and_stay_between_1_and_12():
    call(action="pick", reaction="water")
    assert call(action="dial", index=0, delta=1)["reaction"]["species"][0]["coef"] == 2
    assert call(action="dial", index=0, delta=-1)["reaction"]["species"][0]["coef"] == 1
    v = call(action="dial", index=0, delta=-1)
    assert not v["ok"] and v["reaction"]["species"][0]["coef"] == 1
    call(action="dial", index=0, value=12)
    v = call(action="dial", index=0, delta=1)
    assert not v["ok"] and v["reaction"]["species"][0]["coef"] == 12
    for bad in ({"index": 9, "value": 2}, {"index": -1, "value": 2}, {"index": True, "value": 2}, {"index": 0, "value": 0}, {"index": 0, "value": 13},
                {"index": 0, "value": "2"}, {"index": 0, "value": 2.5}, {"index": 0, "value": True}, {"index": 0}, {"index": 0, "delta": "x"}):
        assert not call(action="dial", **bad)["ok"], bad


def test_every_dial_turn_and_run_moves_a_visible_count():
    call(action="pick", reaction="water")
    t0 = call(action="open")["tally"]
    assert call(action="dial", index=0, value=2)["tally"]["turns"] == t0["turns"] + 1
    v = call(action="dial", index=0, value=2)                              # no change, no count
    assert v["tally"]["turns"] == t0["turns"] + 1
    v = call(action="dial", index=2, value=2)
    assert v["tally"]["turns"] == t0["turns"] + 2 and v["totals"]["turns"] == 2
    assert call(action="dial", index=1, value=99)["tally"]["turns"] == 2   # a refused turn is not counted
    assert call(action="run")["tally"]["runs"] == 1
    assert call(action="run")["tally"]["runs"] == 2 and call(action="open")["totals"]["runs"] == 2


def test_run_only_works_when_the_ledger_reads_equal():
    call(action="pick", reaction="water")
    v = call(action="run")
    assert not v["ok"] and v["totals"]["shelved"] == 0 and v["tally"]["runs"] == 0
    call(action="dial", index=0, value=2)
    call(action="dial", index=2, value=2)
    v = call(action="run")
    assert v["ok"] and v["totals"]["shelved"] == 1 and v["reaction"]["status"] == "shelved" and v["just"]["first"]
    assert v["reaction"]["blurb"].startswith("A water molecule")
    assert set(v["just"]["elements"]) == {"H", "O"}


def test_a_balanced_but_not_smallest_setting_runs_and_says_so():
    call(action="pick", reaction="water")
    for i, c in enumerate([4, 2, 4]):
        v = call(action="dial", index=i, value=c)
    assert v["reaction"]["balanced"] and not v["reaction"]["lowest"] and call(action="run")["ok"]


def test_running_again_adds_a_run_but_not_a_second_shelf_place():
    solve("water")
    v = call(action="run")
    assert v["totals"]["shelved"] == 1 and v["reaction"]["runs"] == 2 and not v["just"]["first"] and "again" in v["message"]
    assert call(action="open")["orders"][0]["orders"][2]["runs"] == 2


def test_nothing_goes_back_down_the_shelf_stays():
    solve("water")
    call(action="dial", index=0, value=5)
    call(action="reset_dials")
    for _ in range(20):
        call(action="dial", index=1, delta=1)
    v = call(action="open")
    assert v["totals"]["shelved"] == 1 and v["reaction"]["status"] == "shelved"


def test_reset_dials_puts_every_dial_back_to_one():
    call(action="pick", reaction="water")
    call(action="dial", index=0, value=5)
    v = call(action="reset_dials")
    assert [s["coef"] for s in v["reaction"]["species"]] == [1, 1, 1]
    assert game.get_state() == {"schema": 1, "cur": "water", "tally": {"turns": 1}}


def test_new_elements_light_tiles_only_when_an_order_is_run():
    v = call(action="open")
    assert {c["state"] for c in v["table"]["cells"] if c["z"] == 6} == {"bench"} and v["table"]["found"] == 0
    v = solve("carbon-dioxide")
    states = {c["z"]: c["state"] for c in v["table"]["cells"]}
    assert states[6] == "found" and states[8] == "found" and states[1] == "bench" and states[10] == "off"
    assert v["table"]["found"] == 2 and "New on the table" in v["message"] and set(v["just"]["elements"]) == {"C", "O"}
    v = solve("water")
    assert v["just"]["elements"] == ["H"] and v["table"]["found"] == 3          # oxygen was already lit
    v = call(action="run")
    assert v["just"]["elements"] == [] and "New on the table" not in v["message"]


def test_a_dark_tile_gives_nothing_away_and_a_lit_one_has_a_card():
    v = call(action="open")
    dark = [c for c in v["table"]["cells"] if c["state"] == "bench"]
    assert dark and all("symbol" not in c and "name" not in c for c in dark) and v["table"]["cards"] == {}
    v = solve("table-salt")
    card = v["table"]["cards"]["Na"]
    assert card["name"] == "Sodium" and card["number"] == 11 and card["group"] == 1 and card["period"] == 3
    assert card["reactions"] == ["Table salt"] and card["use"] == elements.BENCH["Na"]["use"] and card["mass"] == "22.9897693"
    assert card["snapshot"] == "2026-10-12" and "Cl" in v["table"]["cards"] and "Fe" not in v["table"]["cards"]
    assert "Iron" not in json.dumps([c for c in v["table"]["cells"] if c["state"] == "bench"])


def test_the_table_has_a_cell_for_every_element_and_names_only_lit_or_off_ones():
    v = call(action="open")
    cells = v["table"]["cells"]
    assert len(cells) == 118 and v["table"]["all"] == 118 and v["table"]["bench"] == 11
    assert sum(c["state"] == "bench" for c in cells) == 11 and sum(c["state"] == "off" for c in cells) == 107
    assert len({(c["row"], c["col"]) for c in cells}) == 118


def test_the_card_counts_open_orders_that_still_use_the_element():
    v = solve("carbon-dioxide")
    assert v["table"]["cards"]["O"]["more"] == 4 and v["table"]["cards"]["O"]["reactions"] == ["Carbon dioxide"]


def test_a_product_round_hides_the_products_until_the_right_list_is_chosen():
    open_chapter(1)
    call(action="pick", reaction="methane")
    v = call(action="open")
    rx = v["reaction"]
    assert rx["round"] and not rx["picked"] and [s["formula"] for s in rx["species"]] == ["CH4", "O2"] and rx["ledger"] == []
    assert len(rx["choices"]) == 4 and not rx["can_run"] and rx["equation"] == ""
    assert not call(action="dial", index=0, value=2)["ok"]                 # the dials are closed
    assert not call(action="run")["ok"]
    assert "right" not in json.dumps(rx["choices"])


def test_a_wrong_choice_costs_nothing_and_says_why_and_the_right_one_opens_the_dials():
    open_chapter(1)
    call(action="pick", reaction="methane")
    v = call(action="choose", option=0)                                    # CO2 alone
    assert not v["ok"] and "Hydrogen" in v["message"] and v["reaction"]["choices"][0]["tried"] and "Hydrogen" in v["reaction"]["choices"][0]["reason"]
    assert v["tally"]["tries"] == 1 and v["reaction"]["choices"][1]["tried"] is False and "reason" not in v["reaction"]["choices"][1]
    v = call(action="choose", option=0)                                    # again: not counted twice
    assert v["tally"]["tries"] == 1
    v = call(action="choose", option=2)
    assert v["ok"] and v["reaction"]["picked"] and v["reaction"]["choices"] is None
    assert [s["formula"] for s in v["reaction"]["species"]] == ["CH4", "O2", "CO2", "H2O"]
    assert call(action="dial", index=1, value=2)["ok"]
    assert not call(action="choose", option=2)["ok"]                       # already chosen
    assert game.game.first == set()                                        # not right first time


def test_right_first_time_is_recorded_in_the_save():
    open_chapter(1)
    call(action="pick", reaction="methane")
    call(action="choose", option=2)
    assert "methane" in game.get_state()["first"]
    call(action="pick", reaction="propane")
    call(action="choose", option=0)
    call(action="choose", option=1)
    assert "propane" not in game.get_state()["first"]


def test_choose_refuses_bad_options_and_orders_without_a_choice():
    call(action="pick", reaction="water")
    assert not call(action="choose", option=0)["ok"]
    open_chapter(1)
    call(action="pick", reaction="methane")
    for bad in (-1, 4, "1", None, True, 1.5):
        assert not call(action="choose", option=bad)["ok"], bad


def test_every_round_can_be_played_through_to_the_shelf():
    open_chapter(1)
    for r in reactions.CHAPTERS[1]["reactions"][:5]:
        pass
    for r in reactions.CHAPTERS[1]["reactions"]:
        v = solve(r.id)
        assert v["ok"] and v["reaction"]["status"] == "shelved", r.id
    v = call(action="open")
    assert v["orders"][2]["open"] and v["totals"]["shelved"] == 5 + 8


def test_every_order_in_every_chapter_can_be_balanced_and_shelved():
    for chapter in reactions.CHAPTERS:
        for r in chapter["reactions"]:
            if not reactions.chapter_open(game.game.shelf, r.chapter):
                open_chapter(r.chapter)
            assert solve(r.id)["ok"], r.id
    v = call(action="open")
    assert v["totals"]["shelved"] == 24 and v["totals"]["elements"] == 11 == v["totals"]["bench"] and v["totals"]["chapters_done"] == 3
    assert sorted(v["table"]["cards"]) == sorted(reactions.BENCH_ELEMENTS)


def test_a_closed_chapter_cannot_be_entered_and_opens_after_five():
    v = call(action="pick", reaction="methane")
    assert not v["ok"] and "5 orders in Bench Basics" in v["message"] and v["reaction"]["id"] == "carbon-dioxide"
    assert not call(action="pick", reaction="nonsense")["ok"] and not call(action="pick", reaction=5)["ok"]
    orders = call(action="open")["orders"]
    assert orders[1]["open"] is False and orders[1]["need"] == 5 and orders[1]["orders"] == [] and orders[1]["name"] == "Burning"
    ids = [r.id for r in reactions.CHAPTERS[0]["reactions"]]
    for rid in ids[:4]:
        solve(rid)
    assert not call(action="pick", reaction="methane")["ok"]
    solve(ids[7])
    v = call(action="pick", reaction="methane")
    assert v["ok"] and v["reaction"]["id"] == "methane"
    assert call(action="open")["orders"][1]["open"] is True


def test_next_goes_to_the_next_open_order_that_is_not_shelved():
    solve("carbon-dioxide")
    v = call(action="next")
    assert v["reaction"]["id"] == "table-salt"
    solve("table-salt")
    call(action="pick", reaction="carbon-dioxide")
    assert call(action="next")["reaction"]["id"] == "water"
    for r in reactions.CHAPTERS[0]["reactions"]:
        solve(r.id)
    for r in reactions.CHAPTERS[1]["reactions"][:3]:
        pass
    assert call(action="next")["reaction"]["id"] == "methane"              # chapter 2 is open now


def test_next_with_nothing_left_says_so_and_stays():
    for chapter in reactions.CHAPTERS:
        for r in chapter["reactions"]:
            if not reactions.chapter_open(game.game.shelf, r.chapter):
                open_chapter(r.chapter)
            solve(r.id)
    v = call(action="next")
    assert not v["ok"] and "on the shelf" in v["message"]


def test_reset_starts_over():
    solve("water")
    v = call(action="reset")
    assert v["totals"]["shelved"] == 0 and v["reaction"]["id"] == "carbon-dioxide" and game.get_state() == {"schema": 1}


def test_bad_requests_are_refused_not_crashed():
    assert json.loads(game.handle("not json")) == {"error": "bad request"}
    assert "error" in call(action="nope")
    assert json.loads(game.handle("[]")) == {"error": "bad request"}
    assert call(action="dial")["ok"] is False


def test_the_view_is_json_and_deterministic():
    a = game.handle(json.dumps({"action": "open"}))
    b = game.handle(json.dumps({"action": "open"}))
    assert a == b and json.loads(a)["info"]["facts"]
    game.game.__init__()
    assert game.handle(json.dumps({"action": "open"})) == a


def test_the_equation_words_include_every_coefficient():
    call(action="pick", reaction="rust")
    for i, c in enumerate([4, 3, 2]):
        v = call(action="dial", index=i, value=c)
    assert v["reaction"]["equation"] == "4 Fe + 3 O2 gives 2 Fe2O3"


def test_species_carry_the_drawing_tree_for_brackets():
    open_chapter(2)
    call(action="pick", reaction="slaked-lime")
    call(action="choose", option=2)
    prod = [s for s in call(action="open")["reaction"]["species"] if s["role"] == "product"][0]
    assert prod["formula"] == "Ca(OH)2" and prod["tree"][1]["t"] == "group" and prod["tree"][1]["n"] == 2 and prod["name"].startswith("calcium hydroxide")


def test_the_order_board_lists_open_orders_only_with_their_state():
    solve("carbon-dioxide")
    orders = call(action="open")["orders"]
    first = orders[0]["orders"]
    assert len(first) == 8 and first[0]["shelved"] and first[0]["makes"] == "carbon dioxide" and first[0]["formula"] == "CO2"
    assert not first[1]["shelved"] and "makes" not in first[1]
    assert orders[0]["shelved"] == 1 and orders[0]["total"] == 8
