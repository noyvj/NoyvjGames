"""The practice generator: codes, repeatability, and a solvability fuzz. DR_FUZZ=<n> sets the charts per difficulty
(default 30; the plan's full run is DR_FUZZ=5000, which takes the better part of an hour)."""

import copy
import os
import time
from xml.dom import minidom

import pytest

import charts
import gen
import sim
import solver
from geom import dist, point_in_polygon
from render import chart_notes, render_chart

FUZZ = int(os.environ.get("DR_FUZZ", "30"))
TIME_CEILING = 4.0          # seconds for one chart on CPython (Pyodide is a few times slower, still well under a wait)


def test_codes_round_trip_and_reject_junk():
    assert gen.code_of(3, 46655) == "DR3-ZZZ" and gen.chart_id(3, 46655) == "practice-3-zzz"
    assert gen.parse("DR3-ZZZ") == (3, 46655) and gen.parse("  dr3-zzz ") == (3, 46655) and gen.parse("practice-3-zzz") == (3, 46655)
    assert gen.parse("DR1-0") == (1, 0)
    for bad in ("", "DR6-1", "DR0-1", "DR3-", "DR3-ZZZZZZZ", "XX3-AB", None, 5, "DR3-1 2", "practice-9-1"):
        assert gen.parse(bad) is None, bad
    for n in (0, 1, 35, 36, 123456, gen.SEED_LIMIT - 1):
        assert gen.parse(gen.code_of(2, n)) == (2, n)


def test_a_chart_is_a_pure_function_of_difficulty_and_seed():
    a = gen.make_chart(3, 1234)
    gen._CACHE.clear()
    b = gen.make_chart(3, 1234)
    assert a is not None and a == b and a is not b
    assert gen.make_chart(3, 1235) != a and gen.make_chart(2, 1234) != a
    assert gen.from_id("DR3-" + gen.to_base36(1234).upper()) == a


def test_out_of_range_requests_make_nothing():
    for d, s in ((0, 1), (6, 1), (3, -1), (3, gen.SEED_LIMIT), (3, "x"), (3, True), ("3", 1)):
        assert gen.make_chart(d, s) is None


def test_the_next_seed_is_repeatable_and_moves_on():
    assert gen.next_seed(0, 2) == gen.next_seed(0, 2) and gen.next_seed(1, 2) != gen.next_seed(0, 2) and gen.next_seed(0, 2, 1) != gen.next_seed(0, 2)
    assert all(0 <= gen.next_seed(n, d) < gen.SEED_LIMIT for n in range(50) for d in gen.DIFFICULTIES)


def test_the_registry_makes_practice_charts_on_demand_and_never_for_junk():
    cid = gen.chart_id(2, 77)
    c = charts.get_chart(cid)
    assert c is not None and c["id"] == cid and charts.is_unlocked(cid, {}) and charts.par_legs(cid)
    assert charts.get_chart("practice-9-1") is None and charts.get_chart("practice-2-" + "z" * 9) is None
    assert cid not in charts.CHARTS and cid not in charts.ORDER


@pytest.mark.parametrize("difficulty", gen.DIFFICULTIES)
def test_every_generated_chart_is_valid_and_solvable(difficulty):
    made = 0
    for k in range(FUZZ):
        seed = (k * 7919 + difficulty * 31) % gen.SEED_LIMIT
        t0 = time.time()
        c = gen.make_chart(difficulty, seed)
        assert time.time() - t0 < TIME_CEILING, (difficulty, seed)
        if c is None:
            continue                       # allowed (the game falls back), but it must be rare: checked below
        made += 1
        size = c["size"]
        assert 0 < c["start"][0] < size and 0 < c["dest"][1] < size and dist(c["start"], c["dest"]) >= 0.6 * size
        for h in c["hazards"]:
            assert 0 <= h["x"] <= size and h["r"] > 0
            assert dist(c["start"], (h["x"], h["y"])) > h["r"] + 1.0 and dist(c["dest"], (h["x"], h["y"])) > h["r"] + c["arrival_radius"]
        for land in c["land"]:
            poly = [tuple(p) for p in land["poly"]]
            assert not point_in_polygon(tuple(c["start"]), poly) and not point_in_polygon(tuple(c["dest"]), poly)
        for z in c["currents"]:
            lo, hi = z["drift_range"]
            assert lo <= z["true_drift"] <= hi and hi - lo <= 1.0 and abs((z["true_set"] - z["set"] + 180) % 360 - 180) <= 10
        if c.get("wind"):
            assert c["wind"]["range"][0] <= c["wind"]["true"] <= c["wind"]["range"][1]
        if c.get("compass"):
            assert c["compass"]["range"][0] <= c["compass"]["true"] <= c["compass"]["range"][1]
        legs = c["par_legs"]
        assert legs and len(legs) <= 12 and legs == sim.clean_legs(c, legs)
        res = sim.sail(c, legs, seed=seed)
        sc = sim.score(c, legs, res)
        assert res["aground"] is None and res["close"] == [] and sc["arrived"] and sc["on_time"] and sc["clear"], (difficulty, seed, sc["criteria"])
        fl, _ = solver.route(c, [tuple(p) for p in c["waypoints"]], model="charted", seed=seed,
                             wait=legs[0]["hours"] if legs[0]["speed"] == 0 else 0.0)
        fres = sim.sail(c, fl, seed=seed)
        assert fres["aground"] is None and dist(fres["end"], c["dest"]) <= c["arrival_radius"], "the printed midpoints must be enough to make landfall"
    assert made >= FUZZ * 0.9, "generation must almost never fail"


@pytest.mark.parametrize("difficulty", (1, 3, 5))
def test_a_generated_chart_draws_and_describes_itself(difficulty):
    c = gen.make_chart(difficulty, 4242)
    minidom.parseString(render_chart(c))
    assert chart_notes(c)
    if difficulty == 5:
        assert c["fog"] and any(not h["charted"] for h in c["hazards"])
        assert all(h["name"] not in render_chart(c) for h in c["hazards"] if not h["charted"])


def test_difficulty_adds_the_mechanics_in_order():
    def has(d, key):
        return any(bool(gen.make_chart(d, s).get(key)) for s in range(1, 8) if gen.make_chart(d, s))
    assert not has(1, "wind") and not has(2, "wind") and has(3, "wind") and has(4, "compass") and not has(3, "compass") and has(5, "fog")
    assert all(not gen.make_chart(1, s)["currents"] for s in range(1, 8))
    assert any(z.get("tide") for s in range(1, 12) for z in gen.make_chart(4, s)["currents"])
    assert copy.deepcopy(gen.SPEC)[5]["unmarked"] == 2
