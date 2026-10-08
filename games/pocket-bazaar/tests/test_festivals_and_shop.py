import json

import pytest

import days
import festival
import game
import shop
from board import Board
from day import Day
from orders import Customer
from rng import Rng

from .bot import call, play_day


@pytest.fixture(autouse=True)
def fresh():
    game.stall.__init__()
    yield
    game.stall.__init__()


def C(items, patience=40, arch="regular", name="Tomas"):
    return Customer(name, arch, [[f, t, 0] for f, t in items], patience)


# ---- festivals -------------------------------------------------------------------------------------------
def test_festivals_rotate_by_day_number_alone_and_day_one_is_the_relaxed_one():
    assert festival.for_day(1) == "slow"
    assert [festival.for_day(n) for n in range(1, 9)] == ["slow", "harvest", "twin", "kite", "lantern", "bargain", "slow", "harvest"]
    assert festival.for_day(5) == festival.for_day(5)               # no clock, no randomness
    assert set(festival.ORDER) == set(festival.FESTIVALS)


def test_every_festival_says_plainly_what_it_does_and_how_hard_it_makes_the_day():
    for fid, f in festival.FESTIVALS.items():
        assert f["tone"] in ("relaxed", "tricky") and len(f["blurb"]) > 30 and f["name"]
        assert festival.info(fid)["id"] == fid


def test_a_festival_changes_a_copy_of_the_recipe_never_the_table():
    base = days.spec(5)
    slow = festival.apply_spec(base, "slow")
    assert slow["slack_pct"] == base["slack_pct"] * 150 // 100 and base["slack_pct"] == days.spec(5)["slack_pct"]
    harvest = festival.apply_spec(base, "harvest")
    weight = dict(base["archetypes"])["critic"]
    assert dict(harvest["archetypes"])["critic"] == weight * 2 and dict(days.spec(5)["archetypes"])["critic"] == weight
    assert festival.apply_spec(base, "twin") == base


def test_slow_market_pays_a_fifth_less_and_leaves_customers_waiting_longer():
    game.stall.open_day()
    day = game.stall.day
    assert day.festival == "slow" and day.rules["pay_pct"] == 80
    normal = days.spec(1)
    first = day.queue[0]
    from orders import patience_for
    assert first.max == patience_for(first.items, first.archetype, normal["slack_pct"] * 150 // 100)
    day.queue = [C([("produce", 3)])]
    day.board = Board.from_text("P3 .. .. .. ..")
    day.total = 1
    out = day.deliver(0, 0)
    assert out["coins"] == 24 * 80 // 100 + (24 * 80 // 100) * 25 // 100


def test_harvest_fair_gives_tier_two_produce_about_half_the_time_and_replays_exactly():
    day = Day(2, Board(), [C([("produce", 1)])], Rng(9), {"crate_t2": {"produce": (1, 2)}, "festival": "harvest"})
    tiers = []
    for _ in range(200):
        tiers.append(day.crate_tier("produce"))
    assert 70 < tiers.count(2) < 130 and set(tiers) == {1, 2}
    again = Day(2, Board(), [C([("produce", 1)])], Rng(9), {"crate_t2": {"produce": (1, 2)}})
    assert [again.crate_tier("produce") for _ in range(200)] == tiers
    assert all(day.crate_tier("textiles") == 1 for _ in range(50))          # only produce crates


def test_twin_day_spawns_a_free_tier_one_beside_each_new_tier_three():
    day = Day(3, Board.from_text("P2 P2 .. .. .."), [C([("produce", 3)])], Rng(1), {"twin": True, "festival": "twin"})
    out = day.drop(0, 1)
    assert out["merge"].spawned and day.board.count() == 2
    assert day.board.cells[out["merge"].spawned[0]] == ("produce", 1)


def test_the_festival_is_shown_for_today_and_for_the_day_after():
    v = call(action="open")
    assert v["festival"]["id"] == "slow" and v["phase"] == "closed"
    v = call(action="start_day")
    assert v["festival"]["id"] == "slow" and "Slow Market" in v["message"]
    play_day(v)
    v = call(action="open")
    assert v["summary_festival"]["id"] == "slow" and v["festival"]["id"] == "harvest"       # tomorrow's, shown on the summary


# ---- the shop ---------------------------------------------------------------------------------------------
def test_there_are_six_upgrades_each_with_a_cost_and_a_plain_blurb():
    assert len(shop.UPGRADES) == 6 and len(set(shop.ids())) == 6
    assert all(u["cost"] > 0 and len(u["blurb"]) > 20 for u in shop.UPGRADES)


def test_can_buy_gives_a_reason_for_every_refusal():
    assert shop.can_buy([], "broom", 120) == (True, "")
    assert not shop.can_buy([], "broom", 119)[0] and "120" in shop.can_buy([], "broom", 5)[1]
    assert shop.can_buy(["broom"], "broom", 999) == (False, "You already have that.")
    assert shop.can_buy([], "gems", 999)[0] is False and shop.can_buy([], None, 999)[0] is False


def test_buying_spends_coins_once_and_only_between_days():
    game.stall.coins = 500
    v = call(action="buy", id="broom")
    assert v["ok"] and v["coins"] == 380 and [u["id"] for u in v["upgrades"] if u["owned"]] == ["broom"]
    assert call(action="buy", id="broom")["ok"] is False and game.stall.coins == 380
    assert call(action="buy", id="counter")["ok"] is False and game.stall.coins == 380      # 400 > 380
    for junk in (None, 5, [], {}, "nope", True):
        assert call(action="buy", id=junk)["ok"] is False
    call(action="start_day")
    refused = call(action="buy", id="tipjar")
    assert refused["ok"] is False and "between days" in refused["message"] and game.stall.coins == 380


def test_upgrades_are_saved_only_when_owned_and_junk_is_ignored():
    assert "upgrades" not in game.get_state()
    game.stall.coins = 1000
    call(action="buy", id="scales")
    call(action="buy", id="broom")
    data = json.loads(json.dumps(game.get_state()))
    assert data["upgrades"] == ["broom", "scales"] and data["coins"] == 1000 - 300 - 120
    game.stall.__init__()
    game.load_state({"upgrades": ["scales", "gems", 5, None, "scales", "counter"]})
    assert game.stall.upgrades == ["scales", "counter"]
    game.load_state({"upgrades": "all"})
    assert game.stall.upgrades == []


def test_the_wider_counter_adds_a_sixth_column_from_the_next_day():
    assert call(action="start_day")["board"]["w"] == 5
    game.stall.day = None
    game.stall.upgrades = ["counter"]
    v = call(action="start_day")
    assert (v["board"]["w"], v["board"]["h"]) == (6, 6) and len(v["board"]["cells"]) == 36


def test_the_display_shelf_keeps_its_good_from_day_to_day_and_through_a_save():
    game.stall.upgrades = ["shelf"]
    v = call(action="start_day")
    assert v["board"]["shelf"] and len(v["board"]["cells"]) == 31
    day = game.stall.day
    day.board.cells[30] = ("ceramics", 4)
    day.queue = [C([("produce", 1)])]
    day.total = 1
    day.board.place(("produce", 1))
    call(action="deliver", **{"from": 0, "to": 0})
    assert game.stall.shelf == ("ceramics", 4)
    data = json.loads(json.dumps(game.get_state()))
    assert data["shelf"] == {"f": "ceramics", "t": 4}
    game.stall.__init__()
    game.load_state(data)
    assert call(action="start_day")["board"]["cells"][30]["code"] == "C4"
    game.stall.__init__()
    game.load_state({k: v for k, v in data.items() if k != "upgrades"})
    assert game.stall.shelf is None                                  # no shelf owned, so no shelf good


def test_fine_scales_pay_a_tenth_more_for_tier_three_and_up_only():
    c3, c2 = C([("produce", 3)]), C([("produce", 2)])
    assert c3.pay() == 24 and c3.pay(scales=True) == 26
    assert c2.pay(scales=True) == c2.pay() == 10


def test_broom_polish_gives_a_coin_back_and_the_tip_jar_makes_tips_bigger():
    day = Day(1, Board.from_text("P1 .. .. .. .."), [C([("produce", 1)])], Rng(1), {"broom_refund": 1})
    out = day.broom(0)
    assert out["coins"] == 1 and "+1 coin back" in out["message"] and day.coins == 1
    plain = C([("produce", 3)])
    assert plain.tip() == 6 and plain.tip(tip_pct=40) == 9
    day = Day(1, Board.from_text("P3 .. .. .. .."), [C([("produce", 3)])], Rng(1), {"tip_pct": 40})
    assert day.deliver(0, 0)["coins"] == 24 + 9


def test_the_queue_preview_shows_who_is_next_only_when_bought():
    assert call(action="start_day")["upcoming"] is None
    game.stall.day = None
    game.stall.upgrades = ["preview"]
    v = call(action="start_day")
    assert v["upcoming"]["name"] == game.stall.day.queue[3].name and v["upcoming"]["items"]


def test_every_upgrade_can_be_bought_with_coins_earned_in_play_and_never_otherwise():
    """The pledge: one currency, earned only by play. Nothing but a day's earnings or a sale adds coins."""
    start = game.stall.coins
    assert start == 0
    for _ in range(3):
        play_day()
    earned = game.stall.coins
    assert earned > 0
    bought = 0
    for u in shop.UPGRADES:
        v = call(action="buy", id=u["id"])
        if v["ok"]:
            bought += u["cost"]
    assert game.stall.coins == earned - bought and game.stall.coins >= 0


# ---- the campaign ---------------------------------------------------------------------------------------
def test_the_ten_day_campaign_then_free_stall_keeps_going_with_the_festival_rotation():
    seen = []
    for n in range(1, 13):
        v = call(action="start_day")
        assert v["campaign"]["day"] == n and v["campaign"]["mode"] == ("campaign" if n <= 10 else "free")
        seen.append(v["festival"]["id"])
        play_day(v)
        for u in shop.UPGRADES:                 # spend as soon as it is possible, like a keen player
            call(action="buy", id=u["id"])
    assert seen[:6] == list(festival.ORDER) and seen[6:8] == ["slow", "harvest"] and len(seen) == 12
    assert game.stall.days_played == 12 and game.stall.next_day == 13 and game.stall.coins >= 0
    assert game.stall.upgrades                    # the economy lets a keen player buy something


def test_the_first_upgrade_is_within_reach_after_a_few_days_but_not_everything_at_once():
    for _ in range(3):
        play_day()
    assert game.stall.coins >= 150
    assert game.stall.coins < sum(u["cost"] for u in shop.UPGRADES)
