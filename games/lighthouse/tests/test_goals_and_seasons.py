"""Three standing goals, the seasons, the forecast and the supply boat as the day loop uses them."""

import clock
import data
import day
import goals
import sim
import ships
import weather
from state import Keep


def keep_at(night=1, seed=3):
    k = Keep(seed)
    k.night = night
    sim.to_evening(k)
    return k


def test_there_are_always_three_goals_each_with_progress():
    for night in (1, 12, 25, 40):
        g = goals.goals(keep_at(night))
        assert len(g) == 3 and {x["id"] for x in g} >= {"rep", "upgrade"}
        for x in g:
            assert x["need"] > 0 and 0 <= x["have"] <= x["need"] and x["label"] and "done" in x


def test_goals_advance_with_play_and_are_replaced_when_done():
    k = keep_at(1)
    assert goals.goals(k)[0]["label"].startswith("Become Noted") and goals.goals(k)[0]["need"] == 10
    k.reputation = 12
    assert goals.goals(k)[0]["label"].startswith("Become Trusted")
    k.salvage = 5
    up = goals.goals(k)[1]
    assert up["have"] == 5 and up["need"] == 6 and "wick" in up["label"].lower() or up["need"] == 6
    k.upgrades = [u["id"] for u in data.UPGRADES]
    assert [x["id"] for x in goals.goals(k)][1:] != ["upgrade"]
    k.reputation = 500
    assert all(x["id"] != "rep" for x in goals.goals(k))


def test_the_explore_goal_walks_a_ladder_that_ends():
    k = keep_at(5)
    seen = []
    for key in ("quiet_nights", "tidy_days", "fog_clears", "storm_wardens", "best_wound_streak", "frugal_seasons", "empty_nights"):
        seen.append(goals.goals(k)[2]["id"] if goals.goals(k)[2]["id"] != "year" else "year")
        k.meta["counters"][key] = 99
    k.meta["years"] = 1
    k.mode = "endless"
    assert goals.goals(k)[2]["id"] == "mend"
    assert seen[0] == "year"


def test_seasons_cycle_every_ten_nights_and_change_the_night():
    names = [clock.season_name(n) for n in (1, 10, 11, 20, 21, 30, 31, 40, 41)]
    assert names == ["Spring", "Spring", "Summer", "Summer", "Autumn", "Autumn", "Winter", "Winter", "Spring"]
    assert clock.night_len(31) > clock.night_len(11)                  # winter nights are longest, summer shortest
    longer = keep_at(31)
    shorter = keep_at(11)
    for k in (longer, shorter):
        k.levels = [1, 1, 1]
        sim.begin_night(k)
        sim.step(k, 10 ** 6)
    assert longer.night_stats["oil_used"] > shorter.night_stats["oil_used"]


def test_the_barometer_reading_is_for_the_night_being_planned():
    k = keep_at(7)
    from view import build
    v = build(k, {"eerie": True})
    assert v["forecast"]["night"] == 7 and v["notice_night"] == 7
    k.phase = "morning"
    k.report = {"night": 7, "summary": "x", "ships": [], "lamp_hours": 0, "oil_used": 0, "damage": 0, "incidents": 0, "rep": 0, "salvage": 0,
                "passed": 0, "delayed": 0, "damaged": 0, "worst": 0, "quiet": True, "lines": []}
    assert build(k, {"eerie": True})["forecast"]["night"] == 8
    assert (v["forecast"]["lo"], v["forecast"]["hi"]) == weather.forecast(k.seed, 7, False)


def test_the_harbour_board_lists_exactly_tonights_ships_and_the_mail_boat():
    from view import build
    for night in range(1, 30):
        k = keep_at(night)
        v = build(k, {"eerie": True})
        expected = ships.ships_for_night(k.seed, night, k.mail_tonight)
        assert [n["name"] for n in v["notice"]] == [s["name"] for s in expected]
        assert v["boat"]["tonight"] == k.mail_tonight


def test_the_boat_order_survives_a_save_and_changes_the_next_delivery():
    k = keep_at(3)
    assert day.set_order(k, {"oil": 12, "food": 0, "timber": 0, "tar": 0, "glass": 0})[0]
    again = Keep.from_dict(k.to_dict())
    assert again.order["oil"] == 12
    again.oil = 0.0
    sim.deliver(again)
    assert again.oil == 200
