import json
from pathlib import Path

import pytest

import achievements
import decorations
import festival
import game
import regulars
import shop
from board import Board
from orders import Customer

from .bot import call, play_day

GAME_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def fresh():
    game.stall.__init__()
    yield
    game.stall.__init__()


def C(items, patience=60, arch="regular", name="Tomas", reg=""):
    return Customer(name, arch, [[f, t, 0] for f, t in items], patience, reg=reg)


def open_with(queue, board="P1 .. .. .. .."):
    call(action="start_day")
    day = game.stall.day
    day.queue, day.total = queue, len(queue)
    day.board = Board.from_text(board)
    return day


def ids():
    return {a["id"] for a in call(action="open")["achievements"] if a["earned"]}


# ---- the manifest ---------------------------------------------------------------------------------------------
def test_there_are_fourteen_achievements_and_the_manifest_matches_the_engine():
    data = json.loads((GAME_DIR / "achievements.json").read_text(encoding="utf-8"))["achievements"]
    assert [a["id"] for a in data] == list(achievements.IDS) and len(data) == 14
    for entry, (i, label, description, _fact, _need) in zip(data, achievements.ACHIEVEMENTS):
        assert entry == {"id": i, "label": label, "description": description}
    assert len(set(achievements.IDS)) == 14


def test_every_achievement_is_countable_and_none_rewards_time_or_logging_in():
    for _i, label, description, fact, need in achievements.ACHIEVEMENTS:
        assert need >= 1 and fact
        assert not any(w in (label + description).lower() for w in ("daily", "login", "streak of days", "hours", "minutes", "week"))


def test_progress_is_capped_and_goals_are_the_next_three_unearned_in_any_order():
    facts = {"days_played": 1, "orders": 4}
    view = {a["id"]: a for a in achievements.view(facts)}
    assert view["satisfied_customer"]["have"] == 4 and view["open_for_business"]["earned"]
    assert achievements.view({"orders": 99})[1]["have"] == 10
    goals = achievements.goals(facts)
    assert len(goals) == 3 and goals[0]["id"] == "satisfied_customer"
    assert achievements.goals({f: 99 for _i, _l, _d, f, _n in achievements.ACHIEVEMENTS}) == []


# ---- earning them by playing --------------------------------------------------------------------------------
def test_a_first_day_earns_open_for_business_perfect_day_and_full_combo():
    play_day()
    got = ids()
    assert {"open_for_business", "perfect_day", "full_combo"} <= got
    assert "satisfied_customer" not in got                  # day one serves six; ten orders take a second day
    assert game.stall.tally["orders"] >= 6


def test_ten_orders_earn_satisfied_customer():
    play_day()
    play_day()
    assert "satisfied_customer" in ids()


def test_a_four_link_chain_earns_chain_master_and_a_tier_five_earns_showpiece():
    day = open_with([C([("produce", 1)])], ".. P2 .. .. ..\nP3 P1 P4 .. ..\n.. P1 .. .. ..")
    call(action="drop", **{"from": 11, "to": 6})
    assert {"chain_master", "showpiece"} <= ids() and day.board.cells[6] == ("produce", 5)


def test_twin_day_twins_needs_five_free_goods_in_one_day():
    day = open_with([C([("produce", 1)])])
    day.rules["twin"] = True
    for _ in range(5):
        day.board.cells = [None] * 30
        day.board.cells[0] = day.board.cells[1] = ("produce", 2)
        call(action="drop", **{"from": 0, "to": 1})
    assert day.twins == 5 and "twin_twins" in ids()


def test_quiet_stall_is_a_slow_market_day_where_no_combo_ever_starts():
    call(action="start_day")
    day = game.stall.day
    for _ in range(400):
        if game.stall.day is None:
            break
        if game.stall.day.board.is_full():
            call(action="sell", at=0)
        call(action="crate", family="produce")
    assert game.stall.day is None and game.stall.last["festival"] == "slow" and "quiet" in game.stall.flags
    assert "quiet_stall" in ids() and day.best_mult == 1


def test_bargain_blitz_needs_a_bargain_day_with_nobody_leaving():
    call(action="start_day")
    day = game.stall.day
    day.festival, day.queue, day.total = "bargain", [], 0
    day.served = 3
    game.stall.close_day()
    assert "bargain_blitz" in ids()
    game.stall.__init__()
    call(action="start_day")
    day = game.stall.day
    day.festival, day.queue, day.total, day.served, day.left = "bargain", [], 3, 2, 1
    game.stall.close_day()
    assert "bargain_blitz" not in ids()


def test_all_festivals_needs_a_finished_day_under_each_of_the_six():
    for _ in range(6):
        play_day()
    assert game.stall.festivals_seen == list(festival.ORDER) and "all_festivals" in ids()


def test_well_stocked_and_decorator_are_bought_with_coins():
    game.stall.coins = 10 ** 5
    for u in shop.UPGRADES:
        call(action="buy", id=u["id"])
    assert "well_stocked" in ids() and "decorator" not in ids()
    for d in decorations.ids()[:10]:
        call(action="buy_decor", id=d)
    assert "decorator" in ids()


def test_thirty_days_counts_finished_days_only():
    game.stall.days_played = 29
    assert "thirty_days" not in ids()
    play_day()
    assert "thirty_days" in ids() and game.stall.days_played == 30


def test_every_achievement_can_be_earned_in_one_continuous_game():
    """Easy to 100%: a single game that finishes the six festival days, buys everything and keeps going gets them all."""
    game.stall.coins = 10 ** 6
    for u in shop.UPGRADES:
        call(action="buy", id=u["id"])
    for d in decorations.ids():
        call(action="buy_decor", id=d)
    for _ in range(8):
        play_day()
    game.stall.days_played = 29
    game.stall.visits = {"mira": 5}
    for flag in ("bargain", "twin5", "quiet", "showpiece"):
        game.stall.set_flag(flag)
    game.stall.best_chain = 4
    play_day()
    missing = set(achievements.IDS) - ids()
    assert not missing, missing


def test_earned_achievements_are_written_for_the_hub_and_never_read_back():
    assert "achievements_earned" not in game.get_state()
    play_day()
    saved = json.loads(json.dumps(game.get_state()))
    assert "open_for_business" in saved["achievements_earned"]
    forged = {"achievements_earned": list(achievements.IDS)}
    game.stall.__init__()
    game.load_state(forged)
    assert ids() == set()


def test_the_goals_are_in_the_view_and_shrink_as_things_are_earned():
    v = call(action="open")
    assert [g["id"] for g in v["goals"]] == ["open_for_business", "satisfied_customer", "chain_master"]
    play_day()
    assert "open_for_business" not in [g["id"] for g in call(action="open")["goals"]]


# ---- the regulars ---------------------------------------------------------------------------------------------
def test_three_named_regulars_step_up_each_day_after_the_first_in_a_fixed_rotation():
    assert regulars.rotation(1) == [] and len(regulars.rotation(2)) == 3
    assert regulars.rotation(2) == regulars.rotation(6) and regulars.rotation(2) != regulars.rotation(3)
    seen = set()
    for n in range(2, 6):
        seen |= set(regulars.rotation(n))
    assert seen == set(regulars.IDS) and len(regulars.IDS) == 12


def test_a_day_two_queue_has_the_regulars_named_and_with_their_favourite_goods():
    game.stall.next_day = 2
    game.stall.open_day()
    named = [c for c in game.stall.day.queue if c.reg]
    assert [c.reg for c in named] == regulars.rotation(2)
    for c in named:
        assert c.name == regulars.BY_ID[c.reg][1] and c.archetype == "regular"
        assert {f for f, _t, _d in c.items} == {regulars.BY_ID[c.reg][2]}
        assert c.max >= c.cost_in_beats()
    game.stall.__init__()
    game.stall.open_day()
    assert not [c for c in game.stall.day.queue if c.reg]


def test_serving_a_regular_raises_the_bond_with_a_message_and_a_story_line_at_each_level():
    open_with([C([("produce", 1)], name="Mira", reg="mira") for _ in range(6)], "P1 P1 P1 P1 P1\nP1 .. .. .. ..")
    levels = []
    for visit in range(3):
        v = call(action="deliver", **{"from": visit, "to": 0})
        levels.append(regulars.level(game.stall.visits["mira"]))
        if regulars.level(game.stall.visits["mira"]) > (levels[-2] if len(levels) > 1 else 0):
            assert "bond level" in v["message"] and v["flavor"] and v["flavor"][-1].startswith("Mira: ")
    assert levels == [1, 2, 3] and "regular" in ids()


def test_the_regulars_page_hides_lines_not_yet_earned_and_names_unmet_regulars_as_unmet():
    game.stall.visits = {"mira": 2}
    page = {r["id"]: r for r in call(action="open")["regulars"]}
    assert page["mira"]["level"] == 2 and len(page["mira"]["lines"]) == 2 and page["mira"]["next_at"] == 3
    assert page["brandt"]["visits"] == 0 and page["brandt"]["lines"] == []
    assert call(action="open")["regulars_met"] == 1


def test_every_regular_has_a_family_a_role_and_three_distinct_lines_that_fit_a_phone():
    for rid, name, family, role, lines in regulars.REGULARS:
        assert family in ("produce", "textiles", "ceramics", "spices", "sweets") and role and len(name) <= 24
        assert len(lines) == 3 and len(set(lines)) == 3 and all(20 < len(line) < 140 for line in lines)


def test_regular_saves_survive_junk():
    game.stall.visits = {"mira": 4, "cato": 1}
    again = json.loads(json.dumps(game.get_state()))
    assert again["reg"] == {"mira": 4, "cato": 1}
    for junk in ({"reg": 5}, {"reg": {"nobody": 3, "mira": -1, "cato": "x"}}, {"reg": {"mira": True}}, {"flags": "all"}, {"seen": [5, "slow", "bogus"]}):
        game.load_state(junk)
        v = call(action="open")
        assert v["ok"] and all(r["visits"] >= 0 for r in v["regulars"])
    game.load_state({"seen": [5, "slow", "bogus"]})
    assert game.stall.festivals_seen == ["slow"]
    bad = C([("produce", 1)], reg="mira").to_dict()
    bad["reg"] = "ghost"
    with pytest.raises(ValueError):
        Customer.from_dict(bad, ["produce"])
    ok = Customer.from_dict(C([("produce", 1)], reg="mira").to_dict(), ["produce"])
    assert ok.reg == "mira"


# ---- decorations ------------------------------------------------------------------------------------------------
def test_forty_decorations_in_six_slots_and_they_are_only_cosmetic():
    assert len(decorations.DECORATIONS) == 40 and len(decorations.SLOTS) == 6
    assert all(d[1] in decorations.SLOT_IDS and d[3] > 0 for d in decorations.DECORATIONS)
    game.stall.next_day = 3
    game.stall.open_day()
    before = json.dumps(game.stall.day.to_dict(), sort_keys=True)
    game.stall.__init__()
    game.stall.coins = 10 ** 5
    for d in decorations.ids():
        call(action="buy_decor", id=d)
    game.stall.next_day = 3
    game.stall.open_day()
    assert json.dumps(game.stall.day.to_dict(), sort_keys=True) == before          # not one customer or rule changed


def test_buying_puts_it_out_and_you_can_swap_among_owned_ones_in_a_slot():
    game.stall.coins = 500
    v = call(action="buy_decor", id="awning_striped")
    assert v["ok"] and v["coins"] == 460 and game.stall.decor_put == {"awning": "awning_striped"}
    call(action="buy_decor", id="awning_scalloped")
    assert game.stall.decor_put["awning"] == "awning_scalloped"
    assert call(action="put_decor", id="awning_striped")["ok"] and game.stall.decor_put["awning"] == "awning_striped"
    assert call(action="put_decor", id="awning_gilded")["ok"] is False
    assert call(action="buy_decor", id="awning_striped")["ok"] is False
    assert call(action="buy_decor", id="awning_gilded")["ok"] is False and game.stall.coins == 500 - 40 - 80
    for junk in (None, 5, [], "nope"):
        assert call(action="buy_decor", id=junk)["ok"] is False and call(action="put_decor", id=junk)["ok"] is False


def test_decoration_saves_round_trip_and_ignore_junk():
    game.stall.coins = 400
    call(action="buy_decor", id="cat_tabby")
    call(action="buy_decor", id="plant_fern")
    data = json.loads(json.dumps(game.get_state()))
    assert data["decor"] == ["cat_tabby", "plant_fern"] and data["put"] == {"cat": "cat_tabby", "plant": "plant_fern"}
    game.stall.__init__()
    game.load_state(data)
    assert game.stall.decor_put == {"cat": "cat_tabby", "plant": "plant_fern"}
    game.load_state({"decor": ["cat_tabby", "nope", 5], "put": {"cat": "plant_fern", "banner": "cat_tabby", "plant": 5, "bogus": "x"}})
    assert game.stall.decor_owned == ["cat_tabby"] and game.stall.decor_put == {}
    game.load_state({"decor": "all", "put": []})
    assert game.stall.decor_owned == [] and game.stall.decor_put == {}


def test_a_whole_stall_of_state_stays_small_and_clock_free():
    game.stall.coins = 10 ** 5
    for u in shop.UPGRADES:
        call(action="buy", id=u["id"])
    for d in decorations.ids():
        call(action="buy_decor", id=d)
    for _ in range(3):
        play_day()
    text = json.dumps(game.get_state())
    assert len(text) < 4000
