"""The chart validator: every authored chart is checked against the rules that make the campaign fair. Runs over every chart, so
a new chart file is covered the moment it is registered."""

from xml.dom import minidom

import pytest

import charts
import sim
import solver
from geom import dist, point_in_polygon, seg_polygon_dist
from render import chart_notes, render_chart
from state import MAX_LEGS

ALL = charts.all_charts()
IDS = [c["id"] for c in ALL]
KINDS = {"reef", "shoal", "rock"}
LOG_KEYS = {"arrived", "missed", "aground", "late"}


def inside(chart, pt, pad=0.0):
    return pad <= pt[0] <= chart["size"] - pad and pad <= pt[1] <= chart["size"] - pad


def test_there_are_at_least_the_twelve_launch_charts_and_ids_and_names_are_unique():
    assert len(ALL) >= 12
    assert len(set(IDS)) == len(IDS) and len({c["name"] for c in ALL}) == len(ALL)
    assert set(IDS) == set(charts.CHARTS) == set(charts.ORDER)


def test_every_chart_belongs_to_exactly_one_chapter_in_order():
    seen = []
    for chapter in charts.CHAPTERS:
        for c in chapter["charts"]:
            assert c["chapter"] == chapter["id"], c["id"]
            seen.append(c["id"])
    assert seen == charts.ORDER and len(set(seen)) == len(seen)


@pytest.mark.parametrize("cid", IDS)
def test_schema_and_story_fields(cid):
    c = charts.get_chart(cid)
    for key in ("id", "name", "chapter", "size", "start", "dest", "arrival_radius", "deadline", "speeds", "land", "hazards", "currents",
                "landmarks", "waypoints", "intro", "log"):
        assert key in c, key
    assert c["size"] in (20, 30, 40) and 0.5 <= c["arrival_radius"] <= 2.5 and c["deadline"] > 0
    lo, hi = c["speeds"]
    assert 0 < lo <= hi and lo % 0.5 == 0 and hi % 0.5 == 0
    assert c["intro"].strip() and set(c["log"]) == LOG_KEYS and all(c["log"][k].strip() for k in LOG_KEYS)
    for hz in c["hazards"]:
        assert hz["kind"] in KINDS and hz["r"] > 0 and hz["name"] and isinstance(hz.get("charted", True), bool)
    ids = [h["id"] for h in c["hazards"]] + [land["id"] for land in c["land"]] + [z["id"] for z in c["currents"]] + [m["id"] for m in c["landmarks"]]
    assert len(set(ids)) == len(ids), "ids must be unique within a chart"


@pytest.mark.parametrize("cid", IDS)
def test_everything_is_inside_the_chart_and_the_ends_are_clear_water(cid):
    c = charts.get_chart(cid)
    assert inside(c, c["start"], 1.0) and inside(c, c["dest"], c["arrival_radius"])
    for hz in c["hazards"]:
        assert inside(c, (hz["x"], hz["y"]), 0.0)
        assert dist(c["start"], (hz["x"], hz["y"])) > hz["r"] + 1.0, "hazard on the start"
        assert dist(c["dest"], (hz["x"], hz["y"])) > hz["r"] + c["arrival_radius"], "hazard inside the arrival ring"
    for land in c["land"]:
        poly = land["poly"]
        assert all(inside(c, p) for p in poly)
        assert not point_in_polygon(tuple(c["start"]), poly) and seg_polygon_dist(tuple(c["start"]), tuple(c["start"]), poly) > 1.0
        assert not point_in_polygon(tuple(c["dest"]), poly) and seg_polygon_dist(tuple(c["dest"]), tuple(c["dest"]), poly) > c["arrival_radius"]
    for m in c["landmarks"]:
        assert inside(c, (m["x"], m["y"])) and m["kind"] in ("lighthouse", "headland", "buoy")
    for z in c["currents"]:
        x0, y0, x1, y1 = z["rect"]
        assert x0 < x1 and y0 < y1 and x1 > 0 and y1 > 0 and x0 < c["size"] and y0 < c["size"]
    for p in c["waypoints"]:
        assert inside(c, p)


@pytest.mark.parametrize("cid", IDS)
def test_charted_ranges_contain_the_truth(cid):
    c = charts.get_chart(cid)
    for z in c["currents"]:
        lo, hi = z["drift_range"]
        assert 0 < lo <= z["true_drift"] <= hi, z["id"]
        diff = abs((z["true_set"] - z["set"] + 180) % 360 - 180)
        assert diff <= 10, "the true set lies within 10 degrees of the charted set"
        assert hi - lo <= 1.0, "a range wider than a knot would be unfair"
    if c.get("wind"):
        lo, hi = c["wind"]["range"]
        assert lo <= c["wind"]["true"] <= hi and hi - lo <= 10
    if c.get("compass"):
        lo, hi = c["compass"]["range"]
        assert lo <= c["compass"]["true"] <= hi and hi - lo <= 4


@pytest.mark.parametrize("cid", IDS)
def test_the_par_plan_exists_and_lands_three_stars_cleanly(cid):
    c = charts.get_chart(cid)
    legs = charts.par_legs(cid)
    assert legs and len(legs) <= MAX_LEGS
    assert legs == sim.clean_legs(c, legs), "par legs must already be on the legal grid"
    res = sim.sail(c, legs)
    sc = sim.score(c, legs, res)
    assert res["aground"] is None and res["close"] == [], "the par plan never touches or brushes a hazard"
    assert sc["arrived"] and sc["on_time"] and sc["clear"] and sc["stars"] == 3, sc["criteria"]
    assert sc["hours"] <= 0.9 * c["deadline"], "the deadline leaves some slack over the par"


@pytest.mark.parametrize("cid", IDS)
def test_the_honest_forecast_is_good_enough_to_make_landfall(cid):
    """The chart's printed midpoints, followed carefully, must be enough to arrive: ranges are never a trap."""
    c = charts.get_chart(cid)
    legs, _ = solver.route(c, [tuple(p) for p in c["waypoints"]], model="charted", wait=c.get("par_wait", 0.0))
    res = sim.sail(c, legs)
    sc = sim.score(c, legs, res)
    assert res["aground"] is None and sc["arrived"], (res["aground"], sc["miss_nm"])


@pytest.mark.parametrize("cid", IDS)
def test_the_naive_plan_fails_exactly_where_the_chart_says_it_should(cid):
    c = charts.get_chart(cid)
    miss = sim.naive_miss(c)
    if c["naive_fails"]:
        assert miss > c["arrival_radius"], "this chart is meant to defeat steering straight at the flag"
    else:
        assert miss <= c["arrival_radius"], "this chart is meant to be solved by steering straight at the flag"


@pytest.mark.parametrize("cid", IDS)
def test_the_chart_draws_and_describes_itself(cid):
    c = charts.get_chart(cid)
    minidom.parseString(render_chart(c, reveal=True))
    notes = " ".join(chart_notes(c))
    for hz in c["hazards"]:
        if hz.get("charted", True):
            assert hz["name"] in notes


def test_chapter_gates_open_after_four_charts_are_cleared():
    records = {}
    assert charts.unlocked_chapters(records) == ["open"]
    first = charts.CHAPTERS[0]["charts"]
    for c in first[:3]:
        records[c["id"]] = {"stars": 1}
    assert charts.unlocked_chapters(records) == ["open"]
    records[first[3]["id"]] = {"stars": 1}
    assert charts.unlocked_chapters(records) == ["open", "wind"]
    assert charts.is_unlocked("wind-01", records) and not charts.is_unlocked("wind-01", {})


def test_next_chart_follows_the_campaign_order_and_ends():
    assert charts.next_chart_id("open-01") == "open-02" and charts.next_chart_id(charts.ORDER[-1]) is None and charts.next_chart_id("x") is None


def test_the_campaign_has_a_long_route_for_the_long_way_round_achievement():
    from sim import plan_distance
    longest = max(plan_distance(charts.par_legs(c["id"])) for c in ALL)
    assert longest > 60.0


WATCH_IDS = [c["id"] for c in ALL if "watch" in c.get("modes", ())]
FIX_IDS = [c["id"] for c in ALL if c["chapter"] == "fixes"]


def test_chapter_three_is_watch_by_watch_and_earlier_chapters_are_not():
    assert len(FIX_IDS) >= 5
    for c in ALL:
        if c["chapter"] == "fixes":
            assert c["modes"] == ["watch", "plan"] and c["default_mode"] == "watch" and c["landmarks"]
        elif c["chapter"] != "fog":
            assert "watch" not in c.get("modes", ())


@pytest.mark.parametrize("cid", FIX_IDS)
def test_a_careful_watch_by_watch_player_lands_without_grounding(cid):
    """Sail at most two hours, believe the true position (a perfect fix), plan the next watch from the printed midpoints."""
    c = charts.get_chart(cid)
    legs = solver.watch_route(c, [tuple(p) for p in c["waypoints"]])
    res = sim.sail(c, legs)
    sc = sim.score(c, legs, res)
    assert res["aground"] is None and sc["arrived"], (sc["miss_nm"], len(legs))
    assert len(legs) >= 2, "a watch-by-watch passage is more than one leg"


@pytest.mark.parametrize("cid", FIX_IDS)
def test_a_landmark_is_in_sight_somewhere_along_the_par_route(cid):
    from geom import dist
    c = charts.get_chart(cid)
    track = sim.sail(c, charts.par_legs(cid))["track"]
    assert any(dist((x, y), (m["x"], m["y"])) <= m["visible"] for _t, x, y in track for m in c["landmarks"])


FOG_IDS = [c["id"] for c in ALL if c["chapter"] == "fog"]
TIDE_IDS = [c["id"] for c in ALL if any(z.get("tide") for z in c["currents"])]
COMPASS_IDS = [c["id"] for c in ALL if c.get("compass")]


def test_the_later_chapters_exist_in_order():
    assert [ch["id"] for ch in charts.CHAPTERS] == ["open", "wind", "fixes", "fog", "tides", "compass"]
    assert len(FOG_IDS) == 4 and len(TIDE_IDS) >= 4 and len(COMPASS_IDS) >= 4
    assert len(ALL) >= 27


@pytest.mark.parametrize("cid", FOG_IDS)
def test_fog_charts_hide_landmarks_and_have_unmarked_dangers(cid):
    c = charts.get_chart(cid)
    assert c["fog"] and not c["landmarks"]
    assert any(not h.get("charted", True) for h in c["hazards"])
    assert "Fog" in " ".join(chart_notes(c)) and all(h["name"] not in " ".join(chart_notes(c)) for h in c["hazards"] if not h.get("charted", True))
    plain = render_chart(c)
    assert all(h["name"] not in plain for h in c["hazards"] if not h.get("charted", True))


@pytest.mark.parametrize("cid", FOG_IDS)
def test_every_unmarked_danger_can_be_found_by_sailing_into_it(cid):
    c = charts.get_chart(cid)
    for h in c["hazards"]:
        if h.get("charted", True):
            continue
        leg = solver.shoot(c, c["start"], (h["x"], h["y"]), model="true", speed=5.0)
        leg = dict(leg, hours=min(sim.MAX_LEG_HOURS, leg["hours"] + 2.0))
        # a straight run at the hazard's own position grounds on it, or on something in the way
        assert sim.sail(c, [leg])["aground"] is not None


@pytest.mark.parametrize("cid", TIDE_IDS)
def test_tide_charts_have_a_timetable_and_the_par_rides_a_fair_stream(cid):
    c = charts.get_chart(cid)
    assert "the stream peaks toward" in " ".join(chart_notes(c))
    for z in c["currents"]:
        if z.get("tide"):
            assert z["tide"]["period"] == 12.0 and 0 <= z["tide"]["phase"] < 12
    res = sim.sail(c, charts.par_legs(cid))
    assert res["tide_fair"] is not None
    if c["fair_ok"]:
        assert res["tide_fair"] >= 0.6, "Riding the Tide must be possible on this chart"
    assert c["par_wait"] == 0 or charts.par_legs(cid)[0]["speed"] == 0


@pytest.mark.parametrize("cid", COMPASS_IDS)
def test_compass_charts_print_the_error_in_the_picture_and_in_words(cid):
    c = charts.get_chart(cid)
    assert "Compass error" in render_chart(c) and "Compass error" in " ".join(chart_notes(c))
    assert sim.compass_error(c, "true") != 0.0
