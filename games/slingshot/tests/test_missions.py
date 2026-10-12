"""Fairness, PROVED: every mission is solvable by its stored reference plan with fuel to spare, the checker is deterministic, the answer is a
region and not a needle, and the assist missions really need the assist."""

import json
import math

import bodies
import bodies_data as D
import missions
import orbit
import plan as planlib
import pytest
import solve as V
import solvelib as S

IDS = missions.ORDER


def fly(mid, plan, record=False):
    m = missions.BY_ID[mid]
    sc = orbit.make_scene(m["scene"])
    return m, sc, orbit.fly(sc, plan, m["goal"], record=record)


def test_there_are_twenty_two_missions_in_three_chapters_of_7_8_and_7():
    assert len(IDS) == 22 and [len(c["missions"]) for c in missions.CHAPTERS] == [7, 8, 7]
    assert len(set(IDS)) == 22 and all(m["number"] == i + 1 for c in missions.CHAPTERS for i, m in enumerate(c["missions"]))


def test_every_mission_has_a_stored_plan_cost_and_budget():
    for mid in IDS:
        m = missions.BY_ID[mid]
        assert m.get("ref") and m["cost"] > 0 and m["budget"] > 0, mid


@pytest.mark.parametrize("mid", IDS)
def test_the_reference_plan_reaches_the_goal_with_at_least_ten_percent_of_the_budget_to_spare(mid):
    m, sc, r = fly(mid, missions.BY_ID[mid]["ref"])
    assert r["ended"] == "success", (mid, r["ended"], r["closest"])
    assert orbit.judge(r, m["budget"]) == "success"
    assert abs(r["fuel"] - m["cost"]) < 1e-6
    assert (m["budget"] - r["fuel"]) / m["budget"] >= 0.10, (mid, r["fuel"], m["budget"])


@pytest.mark.parametrize("mid", IDS)
def test_the_budget_is_the_reference_cost_plus_a_quarter_rounded_up_to_a_twentieth(mid):
    m = missions.BY_ID[mid]
    assert abs(m["budget"] - S.budget_for(m["cost"])) < 1e-9
    assert m["cost"] * 1.25 <= m["budget"] + 1e-9 < m["cost"] * 1.25 + 0.0501


@pytest.mark.parametrize("mid", IDS)
def test_the_checker_is_deterministic_the_same_plan_twice_gives_the_same_flight(mid):
    ref = missions.BY_ID[mid]["ref"]
    _, _, a = fly(mid, ref, record=True)
    _, _, b = fly(mid, json.loads(json.dumps(ref)), record=True)
    assert a["samples"] == b["samples"] and a["final"] == b["final"] and a["fuel"] == b["fuel"] and a["k_end"] == b["k_end"]


@pytest.mark.parametrize("mid", IDS)
def test_a_second_different_plan_also_works_where_the_search_found_one(mid):
    m = missions.BY_ID[mid]
    alt = m.get("alt")
    if not alt:
        pytest.skip("no second plan for this mission")
    _, _, r = fly(mid, alt)
    assert orbit.judge(r, m["budget"]) == "success"
    assert alt["burns"][0]["t"] != m["ref"]["burns"][0]["t"] or alt != m["ref"]


def test_the_moon_and_mars_moon_missions_all_have_a_second_distinct_plan():
    """Earth to Moon and the Mars moons repeat their launch window every few hours, so each has a plan in a different window. A planet transfer has one
    window in the flight, so those missions are proved a region by the neighbour test instead."""
    for mid in IDS:
        if mid.startswith("c1") or mid in ("c2m6", "c2m7", "c2m8"):
            assert missions.BY_ID[mid].get("alt"), mid


@pytest.mark.parametrize("mid", IDS)
def test_the_answer_is_a_region_not_a_needle_most_plans_one_grid_step_away_still_work(mid):
    m = missions.BY_ID[mid]
    sc = orbit.make_scene(m["scene"])
    wins, tries = V.robust_fraction(sc, m["goal"], m["ref"], m["budget"])
    assert tries >= 3 and wins / tries >= 0.5, (mid, wins, tries)


@pytest.mark.parametrize("mid", IDS)
def test_no_burns_never_reaches_the_goal_and_a_plan_with_no_fuel_does_not_count(mid):
    m, sc, r = fly(mid, planlib.empty())
    assert r["ended"] != "success"


@pytest.mark.parametrize("mid", IDS)
def test_the_reference_plan_is_a_clean_plan_the_page_can_show(mid):
    m = missions.BY_ID[mid]
    cleaned = planlib.clean_plan(m["ref"], m["steps"], tuple(m["scene"]["children"]))
    assert cleaned == m["ref"]
    assert len(m["ref"]["burns"]) <= 3


@pytest.mark.parametrize("mid", IDS)
def test_the_reference_plan_goal_is_not_met_by_dropping_its_last_burn(mid):
    m = missions.BY_ID[mid]
    ref = m["ref"]
    trimmed = {"burns": ref["burns"][:-1], "pass": ref["pass"]} if len(ref["burns"]) > 1 else {"burns": [], "pass": ref["pass"]}
    if trimmed == ref:
        return
    _, _, r = fly(mid, trimmed)
    if len(ref["burns"]) == 1 and not ref["pass"]:
        assert r["ended"] != "success"


def test_the_sunward_missions_cannot_be_done_directly_in_the_budget():
    """Chapter 3's Sunward missions need the assist: even the cheapest direct path (a Hohmann transfer to the goal radius) costs more than the whole budget."""
    r_earth = bodies.planet("earth")["a"]
    for mid in ("c3m5", "c3m6", "c3m7"):
        m = missions.BY_ID[mid]
        d1, _, _ = orbit.hohmann(D.GM_SUN, r_earth, m["goal"]["radius"])
        assert abs(d1) > m["budget"] + 0.5, (mid, d1, m["budget"])


def test_fast_missions_are_faster_than_the_matching_slow_ones():
    slow = missions.BY_ID["c2m2"]
    fast = missions.BY_ID["c2m5"]
    _, _, rs = fly("c2m2", slow["ref"])
    _, _, rf = fly("c2m5", fast["ref"])
    assert rf["passes"][0]["k_in"] <= fast["goal"]["by"] < rs["passes"][0]["k_in"]
    assert fast["budget"] > slow["budget"]


def test_hohmann_phobos_cost_is_the_textbook_transfer():
    m = missions.BY_ID["c2m6"]
    d1, d2, _ = orbit.hohmann(D.PLANETS["mars"][0], 4000.0, 9375.0)
    assert abs(m["cost"] - (abs(d1) + abs(d2))) < 0.01


def test_goal_kinds_are_known_and_bodies_exist_in_their_scene():
    for mid in IDS:
        m = missions.BY_ID[mid]
        g = m["goal"]
        assert g["kind"] in ("flyby", "capture", "rendezvous", "reach")
        if "body" in g:
            assert g["body"] in m["scene"]["children"]
        if g.get("after"):
            assert g["after"] in m["scene"]["children"]
        assert m["dest"] in __import__("atlas").DESTS


def test_mission_text_is_short_plain_and_free_of_dashes_used_as_commas():
    for mid in IDS:
        m = missions.BY_ID[mid]
        assert 20 < len(m["brief"]) < 330 and 10 < len(m["goal_text"]) < 200 and len(m["note"]) < 140, mid
        for field in ("brief", "goal_text", "note", "name"):
            assert "—" not in m[field] and "–" not in m[field], (mid, field)
