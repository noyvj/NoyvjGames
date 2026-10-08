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
