import pytest

import game
from .bot import call, play_day


@pytest.fixture(autouse=True)
def fresh():
    game.stall.__init__()
    yield
    game.stall.__init__()


def test_a_plain_greedy_bot_clears_the_ten_campaign_days_and_serves_most_customers():
    served = total = 0
    for expected in range(1, 11):
        view, steps = play_day()
        summary = view["summary"]
        assert summary["number"] == expected and view["phase"] == "closed" and steps < 3000
        assert summary["served"] + summary["left"] == summary["total"]
        served += summary["served"]
        total += summary["total"]
    assert served / total >= 0.75, f"bot served {served} of {total}"


def test_day_one_is_forgiving_even_for_a_sloppy_player():
    view, _steps = play_day()
    assert view["summary"]["left"] == 0 and view["summary"]["stars"] == 3


def test_the_bot_never_gets_stuck_with_a_full_counter_it_cannot_leave():
    call(action="start_day")
    for _ in range(40):                       # open crates until full without ever merging
        view = call(action="crate", family="produce")
        if view["full"]:
            break
    assert view["full"] or view["phase"] == "closed"
    if view["phase"] == "open":
        assert call(action="sell", at=0)["ok"]


# ---- regular bonds (M-4b-11): level 3 in about 12 to 14 days of play -------------------------------------------
def test_a_greedy_play_through_reaches_bond_level_three_with_a_regular_in_twelve_to_fourteen_days():
    """The first level 3 (the 'Regular' achievement) used to take about 20 days; the bot misses a few customers from
    day 5 on, like a casual player, and still gets there by day 14 -- but not before day 10 (three visits a regular
    makes, one every fourth day)."""
    import regulars
    reached = None
    for day in range(1, 15):
        play_day()
        if regulars.max_level(game.stall.visits) >= 3:
            reached = day
            break
    assert reached is not None and 10 <= reached <= 14, reached


def test_with_every_regular_served_each_visit_all_twelve_reach_level_three_by_day_thirteen():
    import regulars
    visits = {}
    third = {}
    for day in range(1, 30):
        for rid in regulars.rotation(day):
            visits[rid] = visits.get(rid, 0) + 1
            if regulars.level(visits[rid]) == 3:
                third.setdefault(rid, day)
    assert set(third) == set(regulars.IDS)
    assert min(third.values()) == 10 and 12 <= max(third.values()) <= 14
