import pytest

import days
import orders
from board import Board
from day import Day
from orders import Customer, make_queue, order_is_reachable, patience_for
from rng import Rng

THREE = ["produce", "textiles", "ceramics"]


def C(items, arch="regular", patience=30, name="Tomas"):
    return Customer(name, arch, [[f, t, 0] for f, t in items], patience)


def test_a_regular_takes_the_tier_asked_or_better_of_the_same_family():
    c = C([("produce", 2)])
    assert c.match(("produce", 2)) == 0 and c.match(("produce", 4)) == 0
    assert c.match(("produce", 1)) is None and c.match(("textiles", 5)) is None
    assert c.match(None) is None and c.match(("wild", 1)) is None


def test_a_critic_wants_exactly_the_tier_and_says_so():
    c = C([("produce", 2)], "critic")
    assert c.match(("produce", 2)) == 0 and c.match(("produce", 3)) is None
    assert "exactly" in c.why_not(("produce", 3))


def test_the_tightest_fit_fills_the_item_it_suits_best():
    c = C([("produce", 1), ("produce", 3)])
    assert c.match(("produce", 3)) == 1                       # the tier-3 item, not the tier-1 one
    assert c.match(("produce", 2)) == 0
    c.items[1][2] = 1
    assert c.match(("produce", 3)) == 0


def test_reasons_are_plain_sentences():
    c = C([("produce", 2)])
    assert "not asking" in c.why_not(("textiles", 1))
    assert "better" in c.why_not(("produce", 1))
    assert "wildcard" in c.why_not(("wild", 1))
    c.items[0][2] = 1
    assert "everything" in c.why_not(("produce", 1))


def test_payment_follows_the_archetype_and_a_tip_needs_half_the_patience_left():
    plain = C([("produce", 3)], patience=20)
    haggler = C([("produce", 3)], "haggler", patience=20)
    assert plain.pay() == 24 and haggler.pay() == 36
    assert plain.tip() == 6                                   # a quarter, because patience is untouched
    plain.left = 9
    assert plain.tip() == 0
    plain.left = 10
    assert plain.tip() == 6
    assert C([("produce", 1)]).pay() == 4 and C([("produce", 1)] * 3, "bulk").pay() == 13


def test_patience_comes_from_the_orders_own_build_cost():
    assert patience_for([["produce", 1, 0]], "regular", 400) == 20               # (1 + 1 + 3) * 4
    assert patience_for([["produce", 3, 0]], "regular", 300) == 33               # (7 + 1 + 3) * 3
    assert patience_for([["produce", 3, 0]], "haggler", 300) < 33 < patience_for([["produce", 4, 0]], "regular", 300)
    assert patience_for([["produce", 1, 0]], "regular", 1) == 6                  # never absurdly small


def test_every_customer_save_round_trips_and_rejects_junk():
    c = C([("produce", 2), ("textiles", 1)])
    c.items[0][2] = 1
    c.left = 7
    again = Customer.from_dict(c.to_dict(), THREE)
    assert again.to_dict() == c.to_dict() and again.items == c.items and again.left == 7
    good = c.to_dict()
    for bad in (None, [], {}, {**good, "arch": "x"}, {**good, "items": "x"}, {**good, "items": []},
                {**good, "items": [{"f": "sweets", "t": 1}]}, {**good, "items": [{"f": "produce", "t": 9}]},
                {**good, "items": [{"f": "produce", "t": True}]}, {**good, "items": [5]}, {**good, "max": 0},
                {**good, "left": 99}, {**good, "left": "3"}, {**good, "name": 5}, {**good, "name": ""}):
        with pytest.raises(ValueError):
            Customer.from_dict(bad, THREE)


def test_the_day_table_ramps_up_and_never_asks_for_more_than_the_game_has():
    previous = 0
    for n in range(1, 41):
        s = days.spec(n)
        assert 6 <= s["customers"] <= days.MAX_CUSTOMERS and 1 <= s["max_tier"] <= 5 and s["max_items"] <= 3
        assert s["customers"] >= previous
        previous = s["customers"]
    assert days.spec(1)["customers"] == 6 and days.spec(10)["customers"] == 12 and days.spec(40)["customers"] == 16
    assert all(a == "regular" for a, _w in days.spec(1)["archetypes"])
    with pytest.raises(ValueError):
        days.spec(0)


def test_the_archetype_filter_never_leaves_a_day_without_customers():
    assert days.spec(4, unlocked_archetypes={"haggler"})["archetypes"] == (("haggler", 1),)
    assert days.spec(4, unlocked_archetypes=set())["archetypes"] == (("regular", 1),)


@pytest.mark.parametrize("number", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 14, 25, 60])
def test_the_order_generator_never_asks_for_an_unreachable_good(number):
    """Solver-style check: for many seeds, every good in every order can be built from an empty counter within
    the order's own patience, and uses only families and tiers the day allows."""
    spec = days.spec(number)
    for seed in range(1, 21):
        for c in make_queue(Rng(seed * 31 + number), spec, THREE):
            assert 1 <= len(c.items) <= orders.MAX_ITEMS
            assert order_is_reachable(c, Board())
            assert order_is_reachable(c, Board(4, 4))
            for f, t, _d in c.items:
                assert f in THREE and t <= spec["max_tier"]
            assert c.max >= c.cost_in_beats()                # patience always covers building the order alone
            if c.archetype == "bulk":
                assert len({(f, t) for f, t, _d in c.items}) == 1 and c.items[0][1] <= 2
            if c.archetype in ("haggler", "critic"):
                assert len(c.items) <= 2


def test_generation_is_exactly_reproducible_and_names_rarely_repeat():
    a = make_queue(Rng(77), days.spec(8), THREE)
    b = make_queue(Rng(77), days.spec(8), THREE)
    assert [c.to_dict() for c in a] == [c.to_dict() for c in b]
    assert len({c.name for c in a}) >= 8


def test_a_day_costs_a_beat_only_for_the_four_things_that_are_beats():
    queue = [C([("produce", 3)], patience=50)]
    day = Day(1, Board.from_text("P1 P1 T1 .. .."), queue, Rng(1))
    day.drop(0, 3)                                            # a move: free
    day.drop(3, 0)                                            # a move back: free
    day.sell(2)                                               # free
    assert day.beat == 0 and queue[0].left == 50
    day.drop(0, 1)                                            # a merge: one beat
    day.crate("produce")                                      # a crate: one beat
    day.broom(day.board.first_empty() - 1)                    # sweeping the new crate: one beat
    assert day.beat == 3 and queue[0].left == 47
    assert day.deliver(5, 0)["ok"] is False and day.beat == 3  # a refused hand-over: free


def test_only_the_three_at_the_stall_lose_patience():
    queue = [C([("produce", 1)], name=f"N{i}", patience=10) for i in range(5)]
    day = Day(1, Board(), queue, Rng(1))
    day.crate("produce")
    assert [c.left for c in queue] == [9, 9, 9, 10, 10]


def test_a_customer_leaves_when_patience_runs_out_and_the_next_one_steps_up_fresh():
    queue = [C([("produce", 1)], name="Ines", patience=2), C([("produce", 1)], name="Bao", patience=9),
             C([("produce", 1)], name="Cy", patience=9), C([("produce", 1)], name="Di", patience=9)]
    day = Day(1, Board(), queue, Rng(1))
    first = day.crate("produce")
    assert not first["notes"] and queue[0].left == 1
    second = day.crate("produce")
    assert "Ines could not wait" in second["notes"][0] and day.left == 1
    assert [c.name for c in day.window()] == ["Bao", "Cy", "Di"] and day.queue[2].left == 9   # Di did not lose a beat yet
    assert day.is_over() is False


def test_a_customer_who_got_some_of_the_order_still_pays_for_it_when_they_leave():
    c = C([("produce", 1), ("textiles", 1)], patience=2, name="Ines")
    day = Day(1, Board.from_text("P1 .. .. .. .."), [c], Rng(1))
    day.deliver(0, 0)                                         # one beat: 1 left
    out = day.crate("ceramics")
    assert day.left == 1 and out["coins"] == 4 and "Paid 4" in out["notes"][0] and day.coins == 4


def test_serving_the_customer_does_not_cost_them_a_beat_and_the_others_still_pay_one():
    queue = [C([("produce", 1)], name="A", patience=10), C([("produce", 1)], name="B", patience=10)]
    day = Day(1, Board.from_text("P1 .. .. .. .."), queue, Rng(1))
    out = day.deliver(0, 0)
    assert out["ok"] and day.served == 1 and out["coins"] == 4 + 1       # pay + tip (patience untouched)
    assert [c.left for c in day.queue] == [9]


def test_the_day_ends_when_the_line_is_empty():
    queue = [C([("produce", 1)], name=f"N{i}") for i in range(4)]
    day = Day(1, Board(), queue, Rng(1))
    for served in range(4):
        assert not day.is_over()
        day.board.place(("produce", 1))
        day.deliver(day.board.first_empty() - 1, 0)
        assert day.served == served + 1
    assert day.is_over() and day.summary()["served"] == 4 and day.waiting() == 0


def test_stars_come_from_the_share_of_customers_served():
    day = Day(1, Board(), [C([("produce", 1)])], Rng(1))
    day.total = 10
    for served, stars in ((10, 3), (9, 3), (8, 2), (6, 2), (5, 1), (0, 1)):
        day.served = served
        assert day.summary()["stars"] == stars, served


def test_patience_never_moves_without_a_player_action():
    """The pledge in one test: no method of a Day advances patience on its own, and `Day` reads no clock."""
    queue = [C([("produce", 3)], patience=12)]
    day = Day(1, Board(), queue, Rng(1))
    for _ in range(100):
        day.window()
        day.deliverable()
        day.summary()
        day.to_dict()
    assert queue[0].left == 12 and day.beat == 0
