import json

import pytest

import game
from board import Board
from orders import Customer


@pytest.fixture(autouse=True)
def fresh():
    game.stall.__init__()
    yield
    game.stall.__init__()


def call(**request):
    return json.loads(game.handle(json.dumps(request)))


def open_day(board_text=None, customers=None):
    """Open day 1 and optionally lay the counter and the queue out by hand."""
    call(action="start_day")
    day = game.stall.day
    if board_text is not None:
        day.board = Board.from_text(board_text)
    if customers is not None:
        day.queue = customers
        day.total = len(customers)
    return day


def customer(items, name="Tomas", arch="regular", patience=30):
    return Customer(name, arch, [[f, t, 0] for f, t in items], patience)


def test_nothing_can_be_done_before_the_stall_is_open():
    v = call(action="open")
    assert v["phase"] == "closed" and v["board"] is None and v["customers"] == [] and v["next_day"] == 1
    for act in ("crate", "drop", "deliver", "sell", "broom"):
        out = call(action=act, family="produce")
        assert out["ok"] is False and "Open the stall" in out["message"]


def test_opening_the_stall_gives_a_counter_three_customers_at_the_stall_and_a_line():
    v = call(action="start_day")
    assert v["phase"] == "open" and v["day"]["number"] == 1 and v["day"]["total"] == 6
    assert len(v["customers"]) == 3 and v["day"]["waiting"] == 3
    assert v["board"]["w"] == 5 and v["board"]["h"] == 6
    assert [c["family"] for c in v["crates"]] == ["produce", "textiles", "ceramics"]
    again = call(action="start_day")                         # pressing it twice never restarts the day
    assert again["day"]["beat"] == 0 and again["customers"] == v["customers"]


def test_the_same_day_always_has_the_same_customers():
    a = [c["name"] for c in call(action="start_day")["customers"]]
    game.stall.__init__()
    b = [c["name"] for c in call(action="start_day")["customers"]]
    assert a == b


def test_a_crate_puts_a_tier_one_good_on_the_first_free_cell_counts_and_is_a_beat():
    open_day()
    v = call(action="crate", family="textiles")
    assert v["board"]["cells"][0]["code"] == "T1" and v["tally"]["crates"] == 1 and v["day"]["beat"] == 1
    assert v["event"]["kind"] == "crate" and v["event"]["at"] == 0
    assert call(action="crate", family="produce")["board"]["cells"][1]["code"] == "P1"


def test_a_crate_not_open_yet_is_refused_without_a_beat():
    open_day()
    v = call(action="crate", family="sweets")
    assert v["ok"] is False and v["tally"]["crates"] == 0 and v["day"]["beat"] == 0
    assert call(action="crate", family=5)["ok"] is False


def test_a_full_counter_refuses_a_crate_without_a_beat_and_says_so():
    day = open_day()
    for _ in range(30):
        day.board.place(("textiles", 5))
    v = call(action="crate", family="produce")
    assert v["ok"] is False and "full" in v["message"] and v["day"]["beat"] == 0 and v["full"] is True


def test_merging_is_a_beat_and_moving_or_swapping_is_free():
    open_day("P1 P1 T1 .. ..")
    v = call(action="drop", **{"from": 0, "to": 1})
    assert v["board"]["cells"][1]["code"] == "P2" and v["tally"]["merges"] == 1 and v["day"]["beat"] == 1
    assert "Plum" in v["message"]
    v = call(action="drop", **{"from": 2, "to": 3})
    assert v["message"] == "Moved." and v["day"]["beat"] == 1
    v = call(action="drop", **{"from": 3, "to": 1})
    assert v["message"] == "Swapped them." and v["day"]["beat"] == 1


def test_a_refused_drop_costs_nothing():
    open_day("P1 T1 .. .. ..")
    v = call(action="drop", **{"from": 5, "to": 6})
    assert v["ok"] is False and v["day"]["beat"] == 0


def test_a_chain_and_a_three_way_bonus_are_reported_and_counted():
    open_day(".. P2 .. .. ..\nP3 P1 P4 .. ..\n.. P1 .. .. ..")
    v = call(action="drop", **{"from": 11, "to": 6})
    assert v["best_chain"] == 4 and v["tally"]["merges"] == 4 and "4-link chain" in v["message"]
    assert v["day"]["beat"] == 1                      # a whole chain is one beat
    open_day("P1 P1 P1 .. ..")
    v = call(action="drop", **{"from": 0, "to": 1})
    assert v["tally"]["triples"] == 1 and "Three-way" in v["message"]


def test_selling_pays_the_sell_price_and_is_not_a_beat():
    open_day("P1 C4 .. .. ..")
    v = call(action="sell", at=1)
    assert v["coins"] == 14 and v["tally"]["sold"] == 1 and v["day"]["beat"] == 0
    assert call(action="sell", at=1)["ok"] is False and game.stall.coins == 14
    assert call(action="sell", at=0)["coins"] == 15


def test_the_broom_sweeps_for_free_but_is_a_beat():
    open_day("P1 .. .. .. ..")
    v = call(action="broom", at=0)
    assert v["ok"] and v["coins"] == 0 and v["tally"]["swept"] == 1 and v["day"]["beat"] == 1
    assert call(action="broom", at=0)["ok"] is False


def test_handing_over_the_right_good_serves_the_customer_and_pays():
    open_day("P2 .. .. .. ..", [customer([("produce", 2)]), customer([("textiles", 1)], "Ines")])
    v = call(action="deliver", **{"from": 0, "to": 0})
    assert v["ok"] and "happy" in v["message"] and v["tally"]["orders"] == 1
    assert v["coins"] >= 10 and v["day"]["served"] == 1 and v["board"]["cells"][0] is None
    assert v["customers"][0]["name"] == "Ines"
    assert v["event"]["served"] is True


def test_a_wrong_hand_over_is_refused_with_a_reason_and_costs_nothing():
    open_day("T1 P1 .. .. ..", [customer([("produce", 2)])])
    v = call(action="deliver", **{"from": 0, "to": 0})
    assert v["ok"] is False and "not asking" in v["message"] and v["day"]["beat"] == 0
    v = call(action="deliver", **{"from": 1, "to": 0})
    assert v["ok"] is False and "better" in v["message"]
    assert call(action="deliver", **{"from": 9, "to": 0})["ok"] is False
    assert call(action="deliver", **{"from": 1, "to": 5})["ok"] is False


def test_the_last_customer_closes_the_day_and_shows_a_summary():
    open_day("P1 .. .. .. ..", [customer([("produce", 1)])])
    v = call(action="deliver", **{"from": 0, "to": 0})
    assert v["phase"] == "closed" and v["board"] is None and v["next_day"] == 2 and v["days_played"] == 1
    assert v["summary"]["number"] == 1 and v["summary"]["served"] == 1 and v["summary"]["stars"] == 3
    assert "done" in v["message"]
    assert call(action="start_day")["day"]["number"] == 2 and call(action="open")["summary"] is None


def test_partners_and_deliverable_help_the_view():
    open_day("P1 P1 T1 .. ..", [customer([("produce", 1)]), customer([("textiles", 1)], "Ines")])
    v = call(action="open")
    assert v["partners"] == {"0": [1], "1": [0]}
    assert v["deliverable"] == {"0": [0], "1": [0], "2": [1]}


def test_junk_requests_never_crash_the_engine():
    open_day("P1 P1 .. .. ..")
    assert "error" in json.loads(game.handle("not json"))
    assert "error" in json.loads(game.handle("[]"))
    assert "error" in call(action="dance")
    for junk in ("x", -1, 99, True, None, 1.5, [1]):
        assert call(action="sell", at=junk)["ok"] is False
        assert call(action="broom", at=junk)["ok"] is False
        assert call(action="drop", **{"from": junk, "to": 0})["ok"] is False
        assert call(action="drop", **{"from": 0, "to": junk})["ok"] is False
        assert call(action="deliver", **{"from": junk, "to": 0})["ok"] is False
        assert call(action="deliver", **{"from": 0, "to": junk})["ok"] is False


def test_reset_starts_over():
    open_day("P1 .. .. .. ..")
    call(action="sell", at=0)
    v = call(action="reset")
    assert v["coins"] == 0 and v["tally"]["sold"] == 0 and v["phase"] == "closed"


# ---- the save contract -----------------------------------------------------------------------------------
def test_a_fresh_game_saves_nothing_and_only_non_default_keys_appear():
    assert game.get_state() == {}
    open_day()
    assert set(game.get_state()) == {"day"}
    call(action="crate", family="produce")
    assert set(game.get_state()) == {"day", "tally"}


def test_save_round_trip_mid_day_is_exact_and_json_safe():
    open_day("P1 P1 T1 C5 ..")
    call(action="drop", **{"from": 0, "to": 1})
    call(action="sell", at=3)
    call(action="crate", family="ceramics")
    data = json.loads(json.dumps(game.get_state()))
    before = json.dumps(game.get_state(), sort_keys=True)
    view_before = call(action="open")
    game.stall.__init__()
    game.load_state(data)
    assert json.dumps(game.get_state(), sort_keys=True) == before
    assert call(action="open") == view_before


def test_the_day_continues_exactly_after_a_reload():
    """Closing the tab mid-day resumes exactly: the same next customer, the same patience, the same board."""
    open_day()
    call(action="crate", family="produce")
    call(action="crate", family="textiles")
    data = json.loads(json.dumps(game.get_state()))
    game.stall.__init__()
    game.load_state(data)
    v = call(action="open")
    assert v["day"]["beat"] == 2 and v["customers"][0]["patience"] == v["customers"][0]["max"] - 2


def test_a_finished_day_round_trips_with_its_summary():
    open_day("P1 .. .. .. ..", [customer([("produce", 1)])])
    call(action="deliver", **{"from": 0, "to": 0})
    data = json.loads(json.dumps(game.get_state()))
    assert set(data) >= {"coins", "last", "next_day", "days_played", "renown"} and "day" not in data
    game.stall.__init__()
    game.load_state(data)
    v = call(action="open")
    assert v["summary"]["served"] == 1 and v["next_day"] == 2 and v["phase"] == "closed"


JUNK = [None, [], "x", 5, {}, {"day": 5}, {"day": {"number": 1}}, {"coins": -5}, {"coins": "9"}, {"coins": True},
        {"coins": 10 ** 12}, {"tally": []}, {"tally": {"merges": -1, "sold": "x"}}, {"best_chain": 99},
        {"next_day": 0}, {"next_day": "3"}, {"last": 5}, {"last": {"number": 0}}, {"last": {"number": 1, "stars": 9}}]


@pytest.mark.parametrize("junk", JUNK)
def test_load_state_survives_any_junk_with_safe_defaults(junk):
    open_day()
    game.load_state(junk)
    v = call(action="open")
    assert v["ok"] and 0 <= v["coins"] <= game.MAX_COINS and v["best_chain"] <= 5 and v["next_day"] >= 1
    assert all(n >= 0 for n in v["tally"].values())


def _good_day():
    open_day()
    call(action="crate", family="produce")
    return json.loads(json.dumps(game.get_state()))["day"]


@pytest.mark.parametrize("damage", [
    lambda d: d.update(total=2), lambda d: d.update(served=9), lambda d: d.update(queue=[]), lambda d: d.update(queue="x"),
    lambda d: d.update(rng={"seed": -1, "draws": 0}), lambda d: d.update(rng=None), lambda d: d.update(number=0),
    lambda d: d["board"].update(w=1), lambda d: d["queue"][0].update(arch="wizard"),
    lambda d: d["queue"][0].update(items=[]), lambda d: d["queue"][0]["items"][0].update(f="sweets"),
    lambda d: d["queue"][0]["items"][0].update(t=9), lambda d: d["queue"][0].update(left=999),
    lambda d: d["queue"][0].update(name=""), lambda d: d["queue"][0].update(name="x" * 99),
])
def test_a_damaged_day_is_dropped_but_the_rest_of_the_save_survives(damage):
    day = _good_day()
    damage(day)
    game.stall.__init__()
    game.load_state({"coins": 40, "day": day})
    v = call(action="open")
    assert v["phase"] == "closed" and v["coins"] == 40
