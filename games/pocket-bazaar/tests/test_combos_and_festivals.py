import json

import pytest

import days
import festival
import game
import renown
from board import Board
from day import Day
from goods import FAMILIES
from orders import ARCHETYPES, Customer, make_queue, order_is_reachable
from rng import Rng

from .bot import call, play_day


@pytest.fixture(autouse=True)
def fresh():
    game.stall.__init__()
    yield
    game.stall.__init__()


def C(items, patience=60, arch="regular", name="Tomas", group=0):
    return Customer(name, arch, [[f, t, 0] for f, t in items], patience, group=group)


def serve_n(day, n):
    for i in range(n):
        day.board.place(("produce", 1))
        day.deliver(day.board.first_empty() - 1, 0)


def fresh_day(n=12, rules=None):
    return Day(1, Board(), [C([("produce", 1)], name=f"N{i}") for i in range(n)], Rng(1), rules)


# ---- the order combo -------------------------------------------------------------------------------------
def test_the_combo_goes_x1_x2_x3_as_orders_are_served_in_a_row():
    day = fresh_day()
    seen = []
    for _ in range(6):
        seen.append(day.multiplier())
        serve_n(day, 1)
    assert seen == [1, 1, 2, 2, 3, 3] and day.best_mult == 3 and day.best_streak == 6
    assert day.to_next() == 0


def test_to_next_counts_orders_still_needed():
    day = fresh_day()
    assert (day.multiplier(), day.to_next()) == (1, 2)
    serve_n(day, 1)
    assert day.to_next() == 1
    serve_n(day, 1)
    assert (day.multiplier(), day.to_next()) == (2, 2)


def test_the_combo_multiplies_the_payment_but_not_the_tip():
    day = fresh_day()
    paid = []
    for _ in range(4):
        day.board.place(("produce", 1))
        paid.append(day.deliver(day.board.first_empty() - 1, 0)["coins"])
    assert paid == [4 + 1, 4 + 1, 8 + 1, 8 + 1]


def test_a_customer_leaving_resets_the_combo_and_a_new_day_starts_it_fresh():
    queue = [C([("produce", 1)], name="A"), C([("produce", 1)], name="B"), C([("produce", 3)], name="Z", patience=3)]
    day = Day(1, Board(), queue, Rng(1))
    serve_n(day, 2)
    assert day.streak == 2
    out = day.crate("textiles")                          # Z waits no longer
    assert day.streak == 0 and "Combo reset." in out["notes"]
    assert fresh_day().streak == 0                       # nothing carries over between days


def test_there_is_no_cross_day_combo_in_the_save():
    assert call(action="start_day")["day"]["streak"] == 0
    assert "streak" not in game.get_state()
    play_day()
    saved = game.get_state()
    assert "streak" not in saved and saved["best"]["combo"] >= 1       # only the personal best is kept


def test_kite_day_starts_the_combo_at_x2():
    day = fresh_day(rules={"combo_floor": 2})
    assert day.multiplier() == 2
    serve_n(day, 4)
    assert day.multiplier() == 3


# ---- chain bonus and wildcards -----------------------------------------------------------------------
def test_a_chain_pays_a_coin_bonus_per_extra_link():
    day = Day(1, Board.from_text(".. P2 .. .. ..\nP3 P1 P4 .. ..\n.. P1 .. .. .."), [C([("produce", 1)])], Rng(1))
    out = day.drop(11, 6)
    assert out["merge"].links == 4 and day.chain_coins == 4 + 6 + 8 and day.coins == 18
    assert out["coins"] == 18 and "Chain bonus +18" in out["message"]
    plain = Day(1, Board.from_text("P1 P1 .. .. .."), [C([("produce", 1)])], Rng(1))
    assert plain.drop(0, 1)["coins"] == 0


def test_a_wildcard_appears_every_four_orders_and_merges_with_anything_below_a_showpiece():
    day = fresh_day()
    serve_n(day, 4)
    assert day.wilds == 1 and ("wild", 1) in day.board.cells
    cell = day.board.cells.index(("wild", 1))
    day.board.place(("textiles", 2))
    other = day.board.cells.index(("textiles", 2))
    assert day.drop(cell, other)["merge"].good == ("textiles", 3)


def test_a_wildcard_can_not_be_handed_over():
    day2 = Day(1, Board.from_text("** .. .. .. .."), [C([("produce", 1)])], Rng(1))
    refused = day2.deliver(0, 0)
    assert refused["ok"] is False and "wildcard" in refused["message"]


# ---- the six festivals -------------------------------------------------------------------------------
def test_all_six_festivals_exist_rotate_and_are_each_described():
    assert festival.ORDER == ("slow", "harvest", "twin", "kite", "lantern", "bargain")
    assert {festival.for_day(n) for n in range(1, 7)} == set(festival.FESTIVALS)
    for fid in festival.ORDER:
        assert festival.FESTIVALS[fid]["tone"] in ("relaxed", "tricky")


def test_kite_day_is_a_five_by_five_counter_and_x2_combo():
    game.stall.next_day = 4
    v = call(action="start_day")
    assert v["festival"]["id"] == "kite" and (v["board"]["w"], v["board"]["h"]) == (5, 5)
    assert v["day"]["mult"] == 2


def test_lantern_night_pays_and_sells_ceramics_half_again_as_much():
    c = C([("ceramics", 3)])
    assert c.pay(family_pct={"ceramics": 150}) == 36 and c.pay() == 24
    day = Day(5, Board.from_text("C2 P2 .. .. .."), [c], Rng(1), {"family_pct": {"ceramics": 150}})
    assert day.sell(0)["sold"] == 3 and day.sell(1)["sold"] == 2


def test_lantern_night_brings_rush_crowds_and_bargain_hunt_only_hagglers():
    spec = festival.apply_spec(days.spec(5), "lantern")
    assert dict(spec["archetypes"])["crowd"] == 3
    queues = [make_queue(Rng(seed), spec, ["produce", "textiles", "ceramics"]) for seed in range(1, 11)]
    assert any(c.group for q in queues for c in q) and all(len(q) == spec["customers"] for q in queues)
    bargain = festival.apply_spec(days.spec(6), "bargain")
    assert bargain["archetypes"] == (("haggler", 1),)
    assert all(c.archetype == "haggler" for c in make_queue(Rng(4), bargain, ["produce"]))


def test_every_festival_day_is_playable_by_the_bot_and_every_festival_is_previewed_the_day_before():
    for n in range(1, 13):
        v = call(action="start_day")
        assert v["festival"]["id"] == festival.for_day(n)
        v, _steps = play_day(v)
        assert v["festival"]["id"] == festival.for_day(n + 1) and v["summary_festival"]["id"] == festival.for_day(n)


# ---- new customers ------------------------------------------------------------------------------------
def test_a_child_is_patient_tips_big_and_orders_something_tiny():
    child = C([("produce", 1)], arch="child", patience=20)
    assert child.pay() == 2 and child.tip() == 2
    assert ARCHETYPES["child"]["wait_pct"] == 150
    for seed in range(30):
        q = make_queue(Rng(seed), dict(days.spec(6), archetypes=(("child", 1),)), ["produce", "textiles"])
        assert all(len(c.items) == 1 and c.items[0][1] <= 2 for c in q)


def test_a_tourist_takes_any_tier_and_is_paid_by_the_tier_handed_over():
    t = C([("produce", 1)], arch="tourist")
    assert t.match(("produce", 4)) == 0 and t.match(("textiles", 4)) is None
    day = Day(1, Board.from_text("P4 .. .. .. .."), [t], Rng(1))
    out = day.deliver(0, 0)
    assert out["ok"] and day.coins == 56 * 55 // 100 + (56 * 55 // 100) * 25 // 100


def test_a_rush_crowd_pays_a_group_bonus_only_if_all_three_are_served():
    def crowd_day():
        queue = [C([("produce", 1)], arch="crowd", name=n, group=1) for n in ("A", "B", "C")]
        return Day(1, Board(), queue, Rng(1))
    day = crowd_day()
    serve_n(day, 3)
    gross = 5 + 5 + 9
    assert day.coins == gross + gross // 2
    day = crowd_day()
    day.queue[2].left = 1
    serve_n(day, 2)
    day.crate("textiles")                                # C loses patience and leaves
    assert day.coins == 5 + 5 and day.groups[1][1] == 1


def test_crowd_members_share_a_family_and_the_queue_length_is_exact():
    spec = dict(days.spec(8), archetypes=(("crowd", 5), ("regular", 1)))
    for seed in range(20):
        q = make_queue(Rng(seed), spec, ["produce", "textiles", "ceramics"])
        assert len(q) == spec["customers"]
        for gid in {c.group for c in q if c.group}:
            members = [c for c in q if c.group == gid]
            assert len(members) == 3 and len({f for c in members for f, _t, _d in c.items}) == 1
            assert [c for c in q].index(members[0]) + 2 == [c for c in q].index(members[2])       # arrive together


def test_every_archetype_is_reachable_with_all_five_families():
    spec = dict(days.spec(10), archetypes=tuple((a, 1) for a in ARCHETYPES))
    for seed in range(1, 15):
        for c in make_queue(Rng(seed), spec, list(FAMILIES)):
            assert order_is_reachable(c, Board()) and c.max >= c.cost_in_beats()


def test_group_and_tourist_saves_round_trip():
    day = Day(1, Board(), [C([("produce", 1)], arch="crowd", group=2), C([("textiles", 1)], arch="tourist")], Rng(1))
    day.groups[2] = [1, 0, 12]
    day.streak, day.best_streak, day.wilds = 3, 3, 1
    again = Day.from_dict(json.loads(json.dumps(day.to_dict())), list(FAMILIES))
    assert again.to_dict() == day.to_dict() and again.groups == {2: [1, 0, 12]} and again.queue[0].group == 2
    for bad in ({"groups": []}, {"groups": {"x": [1, 2, 3]}}, {"groups": {"1": [1, 2]}}, {"groups": {"1": [1, 2, True]}},
                {"queue": [dict(day.queue[0].to_dict(), grp=99)]}):
        broken = dict(day.to_dict(), **bad)
        with pytest.raises(ValueError):
            Day.from_dict(broken, list(FAMILIES))


# ---- renown --------------------------------------------------------------------------------------------
def test_renown_opens_crates_and_customers_in_order_and_never_goes_down():
    assert renown.families(0) == ["produce", "textiles", "ceramics"]
    assert renown.families(50) == ["produce", "textiles", "ceramics", "spices"] and renown.families(110)[-1] == "sweets"
    assert renown.archetypes(0) == set() and renown.archetypes(30) == {"child", "tourist"} and "crowd" in renown.archetypes(75)
    assert renown.newly_unlocked(9, 11) == ["child"]
    assert set(renown.newly_unlocked(0, 200)) == set(renown.UNLOCK_NAMES)
    assert renown.next_unlock(0) == {"name": "children with a coin", "need": 10} and renown.next_unlock(500) is None
    assert renown.gain(6, 3) == 9


def test_finishing_days_unlocks_things_and_the_summary_says_so():
    unlocked, crates = [], []
    for _ in range(8):
        v, _s = play_day()
        unlocked += v["summary"]["unlocks"]
        crates.append(len(v["crates"]))
    assert "child" in unlocked and "spices" in unlocked and crates[-1] >= 4
    assert game.stall.renown > 50


def test_a_locked_family_never_appears_in_an_order():
    game.stall.open_day()
    assert {f for c in game.stall.day.queue for f, _t, _d in c.items} <= {"produce", "textiles", "ceramics"}
    game.stall.renown = 120
    game.stall.day = None
    game.stall.open_day()
    assert {f for c in game.stall.day.queue for f, _t, _d in c.items} - {"produce", "textiles", "ceramics"}


# ---- personal bests ------------------------------------------------------------------------------------
def test_personal_bests_flag_only_real_improvements_and_are_saved():
    v, _s = play_day()
    assert set(v["summary"]["new_bests"]) == {"combo", "day_coins"}
    first = dict(v["best"])
    game.stall.best = {"combo": 99, "day_coins": 99999}
    v, _s = play_day()
    assert v["summary"]["new_bests"] == [] and v["best"] == {"combo": 99, "day_coins": 99999}
    data = json.loads(json.dumps(game.get_state()))
    assert data["best"] == {"combo": 99, "day_coins": 99999} and first["combo"] >= 1
    game.stall.__init__()
    game.load_state(data)
    assert game.stall.best["combo"] == 99


@pytest.mark.parametrize("junk", [{"best": 5}, {"best": {"combo": -1, "day_coins": "x"}}, {"best": {"combo": True}},
                                  {"last": {"number": 1, "stars": 2, "unlocks": "child", "new_bests": [5, "combo", "bogus"]}},
                                  {"last": {"number": 1, "stars": 2, "unlocks": ["child", "bogus", 3]}}])
def test_new_save_fields_survive_junk(junk):
    game.load_state(junk)
    v = call(action="open")
    assert v["ok"] and all(n >= 0 for n in v["best"].values())
    if v["summary"]:
        assert set(v["summary"]["new_bests"]) <= {"combo", "day_coins"} and set(v["summary"]["unlocks"]) <= set(renown.UNLOCK_NAMES)
