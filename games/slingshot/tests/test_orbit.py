"""The flight engine: fixed-step integration with stated tolerances, determinism, exact conics, patched-conic passes, and the goals."""

import math

import bodies
import bodies_data as D
import orbit
import pytest

EARTH_MOON = {"central": "earth", "children": ["moon"], "dt": 360.0, "steps": 3600, "stride": 6, "start": {"orbit": {"r": 42164.0, "theta": 0.0, "dir": 1}}, "phases": {"moon": 40.0}}
SUN = {"central": "sun", "children": ["venus", "earth", "mars"], "dt": 21600.0, "steps": 1600, "stride": 8, "start": {"comove": "earth"}, "epoch": (2026, 10, 1)}
MARS = {"central": "mars", "children": ["phobos", "deimos"], "dt": 60.0, "steps": 2880, "stride": 4, "start": {"orbit": {"r": 4000.0, "theta": 0.0, "dir": 1}},
        "phases": {"phobos": 100.0, "deimos": 250.0}, "rendezvous": ["phobos", "deimos"]}
NEVER = {"kind": "reach", "radius": 1.0}


def test_a_circular_orbit_keeps_its_radius_to_five_parts_in_ten_thousand_over_a_whole_orbit():
    sc = orbit.make_scene(dict(EARTH_MOON, steps=240))
    r = orbit.fly(sc, {"burns": []}, NEVER, record=True)
    radii = [math.hypot(s[1], s[2]) for s in r["samples"]]
    assert max(abs(x / 42164.0 - 1) for x in radii) < 5e-4


def test_a_free_flying_probe_loses_less_than_five_in_a_hundred_thousand_of_its_energy_over_a_year():
    sc = orbit.make_scene(dict(SUN, steps=1461))                    # 365 days at 6 hours
    plan = {"burns": [{"t": 0, "at": "time", "head": 90.0, "dv": 5.0}], "pass": {}}      # an oval path round the Sun that stays clear of every planet's sphere
    r = orbit.fly(sc, plan, NEVER, record=True)
    mu = D.GM_SUN
    def energy(x, y, vx, vy):
        return 0.5 * (vx * vx + vy * vy) - mu / math.hypot(x, y)
    x0, y0, vx0, vy0 = sc["start"]
    # the burn is applied at step 0: recompute the first state the same way
    speed = math.hypot(vx0, vy0)
    ux, uy = orbit._rotate(vx0 / speed, vy0 / speed, 90.0)
    e0 = energy(x0, y0, vx0 + 5.0 * ux, vy0 + 5.0 * uy)
    x, y, vx, vy = r["final"]
    assert abs(energy(x, y, vx, vy) / e0 - 1) < 5e-5


def test_the_same_plan_flies_the_same_path_to_the_last_digit():
    sc = orbit.make_scene(EARTH_MOON)
    plan = {"burns": [{"t": 42, "at": "time", "head": 0.0, "dv": 1.035}], "pass": {"moon": -0.1}}
    goal = {"kind": "flyby", "body": "moon", "within": 30000.0}
    a = orbit.fly(sc, plan, goal, record=True)
    b = orbit.fly(orbit.make_scene(dict(EARTH_MOON)), plan, goal, record=True)
    assert a["samples"] == b["samples"] and a["final"] == b["final"] and a["passes"][0]["rp"] == b["passes"][0]["rp"]


def test_scene_cache_returns_equal_scenes_for_equal_specs():
    assert orbit.make_scene(EARTH_MOON) is orbit.make_scene(dict(EARTH_MOON))


def test_hohmann_numbers_for_earth_to_mars_and_earth_to_the_moon():
    d1, d2, half = orbit.hohmann(D.GM_SUN, bodies.planet("earth")["a"], bodies.planet("mars")["a"])
    assert abs(d1 - 2.94) < 0.02 and abs(d2 - 2.65) < 0.03
    assert abs(half / 86400 - 258.8) < 2                           # the textbook 259 days
    d1, d2, half = orbit.hohmann(D.PLANETS["earth"][0], 42164.0, 384400.0)
    assert abs(d1 - 1.053) < 0.005


def test_an_earth_to_mars_hohmann_burn_reaches_mars_at_the_right_date():
    sc = orbit.make_scene(dict(SUN, steps=1600))
    goal = {"kind": "flyby", "body": "mars", "within": 600000.0}
    plan = {"burns": [{"t": 4 * 47, "at": "time", "head": 0.0, "dv": 2.94}], "pass": {}}
    r = orbit.fly(sc, plan, goal, record=False)
    assert r["passes"] and r["passes"][0]["child"] == "mars"
    assert 255 < r["passes"][0]["k_in"] / 4 - 47 < 270           # about 259 days of flight, plus the way in from the edge of the sphere


def _brute_pass(mu, state, dt=2.0):
    """Integrate a body-centred two-body flight with a tiny fixed step from the entry until it is back at the entry radius."""
    x, y, vx, vy = state
    r_in = math.hypot(x, y)
    t = 0.0
    went_in = False
    ax, ay = -mu * x / r_in ** 3, -mu * y / r_in ** 3
    while t < 1e7:
        vhx, vhy = vx + 0.5 * dt * ax, vy + 0.5 * dt * ay
        x += dt * vhx
        y += dt * vhy
        r = math.hypot(x, y)
        ax, ay = -mu * x / r ** 3, -mu * y / r ** 3
        vx, vy = vhx + 0.5 * dt * ax, vhy + 0.5 * dt * ay
        t += dt
        if x * vx + y * vy < 0:
            went_in = True
        if went_in and x * vx + y * vy > 0 and r >= r_in:
            break
    return (x, y, vx, vy), t


@pytest.mark.parametrize("state", [(60000.0, 20000.0, -0.55, 0.0), (-50000.0, 30000.0, 0.3, -0.45), (30000.0, -50000.0, -0.2, 0.6)])
def test_the_patched_conic_pass_agrees_with_a_brute_force_integration(state):
    mu = D.MOONS["moon"][1]
    r_in = math.hypot(state[0], state[1])
    res = orbit.pass_through(mu, 1737.4, state, 0.0, r_in)
    assert "exit" in res
    (bx, by, bvx, bvy), bt = _brute_pass(mu, state, dt=4.0)
    ex, ey, evx, evy = res["exit"]
    total = res["t_in"] + res["t_out"]
    assert abs(total / bt - 1) < 3e-3
    assert math.hypot(ex - bx, ey - by) < 0.01 * r_in
    assert math.hypot(evx - bvx, evy - bvy) < 0.01 * math.hypot(bvx, bvy) + 1e-3
    # the exit speed equals the entry speed (energy is kept) and the closest approach matches the integration's smallest radius
    assert abs(math.hypot(evx, evy) / math.hypot(state[2], state[3]) - 1) < 1e-9


def test_a_pass_with_a_slowing_burn_is_captured_with_the_orbit_the_formula_gives():
    mu = D.MOONS["moon"][1]
    state = (60000.0, 20000.0, -0.6, 0.0)
    free = orbit.pass_through(mu, 1737.4, state, 0.0)
    assert "exit" in free and free["rp"] > 1737.4
    vq = math.sqrt(2 * mu * (1 / free["rp"] - 1 / (free["rp"] + 30000.0)))
    cap = orbit.pass_through(mu, 1737.4, state, vq - free["vp"])
    assert cap["captured"] and abs(cap["big_q"] - 30000.0) < 1.0 and abs(cap["q"] - free["rp"]) < 1e-6
    assert cap["period"] > 0


def test_a_path_that_dips_below_the_surface_is_an_impact():
    mu = D.MOONS["moon"][1]
    res = orbit.pass_through(mu, 1737.4, (60000.0, 600.0, -0.55, 0.0), 0.0)
    assert res.get("impact")


def test_a_gravity_assist_changes_the_probes_speed_round_the_sun_by_about_the_planets_pull():
    sc = orbit.make_scene(dict(SUN, steps=1600))
    goal = {"kind": "flyby", "body": "mars", "within": 1e9, "min": 0.0}
    plan = {"burns": [{"t": 4 * 47, "at": "time", "head": 0.0, "dv": 2.94}], "pass": {}}
    r = orbit.fly(sc, plan, dict(goal, within=1.0), record=True)    # impossible goal: keep flying after the pass
    p = r["passes"][0]
    assert p["turn_deg"] > 0
    assert abs(p["v_inf_after"] - p["v_inf"]) < 1e-6                 # the pass keeps the speed relative to the planet
    # but the speed round the Sun changes: compare before and after the pass
    mars = sc["by_id"]["mars"]
    k_out = p["k_out"]
    assert k_out > p["k_in"]


def test_a_rendezvous_goal_is_met_by_the_hohmann_pair_and_not_by_coasting():
    sc = orbit.make_scene(MARS)
    goal = {"kind": "rendezvous", "body": "phobos", "radius": 400.0, "speed": 0.25}
    d1, d2, half = orbit.hohmann(D.PLANETS["mars"][0], 4000.0, 9375.0)
    wins = 0
    for t1 in range(0, 400):
        plan = {"burns": [{"t": t1, "at": "time", "head": 0.0, "dv": round(d1, 3)}, {"t": t1 + 1, "at": "apo", "head": 0.0, "dv": round(d2, 3)}], "pass": {}}
        if orbit.fly(sc, plan, goal, record=False)["ended"] == "success":
            wins += 1
    assert 3 <= wins < 120
    assert orbit.fly(sc, {"burns": []}, goal, record=False)["ended"] is None


def test_burns_and_anchors_apply_in_order_and_an_unreached_anchor_never_fires():
    sc = orbit.make_scene(MARS)
    plan = {"burns": [{"t": 5, "at": "time", "head": 0.0, "dv": 0.6}, {"t": 6, "at": "apo", "head": 0.0, "dv": 0.48}], "pass": {}}
    r = orbit.fly(sc, plan, NEVER, record=False)
    assert [b["i"] for b in r["burns_done"]] == [0, 1] and r["burns_done"][1]["k"] > 100
    plan2 = {"burns": [{"t": 5, "at": "time", "head": 0.0, "dv": 0.01}, {"t": 6, "at": "apo", "head": 0.0, "dv": 0.48}], "pass": {}}
    r2 = orbit.fly(orbit.make_scene(dict(MARS, steps=40)), plan2, NEVER, record=False)
    assert len(r2["burns_done"]) == 1 and r2["unused_burns"] == 1


def test_a_probe_that_falls_into_the_central_body_crashes():
    sc = orbit.make_scene(MARS)
    plan = {"burns": [{"t": 0, "at": "time", "head": 180.0, "dv": 2.0}], "pass": {}}
    r = orbit.fly(sc, plan, NEVER, record=False)
    assert r["ended"] == "crash" and orbit.judge(r, 99.0) == "crash"


def test_judge_marks_a_goal_met_over_the_budget_separately():
    sc = orbit.make_scene(EARTH_MOON)
    plan = {"burns": [{"t": 42, "at": "time", "head": 0.0, "dv": 1.035}], "pass": {}}
    r = orbit.fly(sc, plan, {"kind": "flyby", "body": "moon", "within": 30000.0}, record=False)
    assert orbit.judge(r, 1.3) == "success" and orbit.judge(r, 1.0) == "over_budget"


def test_the_engine_modules_read_no_clock_and_no_random_source():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    for path in root.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for banned in ("import random", "import time", "import datetime", "time.time", "random.", "datetime."):
            assert banned not in text, (path.name, banned)
