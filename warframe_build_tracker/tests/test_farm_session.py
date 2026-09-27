"""Batch B #4: the drop-source optimizer for the whole wishlist."""

import wf_plans

from .helpers import known_state


def _rows(m):
    _c, resources = m.calculate()
    return m.active_rows(resources)


def test_nothing_short_says_so(game_env):
    m = game_env.module
    known_state(m)
    session = wf_plans.farm_session(_rows(m), m.location_places)
    assert session["total"] == 0 and session["steps"] == []
    assert "Nothing left to farm" in wf_plans.session_lines(session)[0]


def test_greedy_order_and_coverage(game_env):
    m = game_env.module
    known_state(m, parts={"Rahn Prism": {"owned": 0}, "Kronsh Strike": {"owned": 0}, "Haymaker Grip": {"owned": 0, "target": 6}})
    rows = _rows(m)
    session = wf_plans.farm_session(rows, m.location_places)
    assert 1 <= len(session["steps"]) <= 3
    best = m.route_suggestions(rows)[0]
    assert session["steps"][0]["place"] == best["place"]  # builds on route_suggestions
    assert session["steps"][0]["resources"] == sorted(best["resources"])
    covered = [n for s in session["steps"] for n in s["resources"]]
    assert len(covered) == len(set(covered))  # each resource is counted at one stop only
    short = [r for r in rows if r["built_short"] > 0]
    assert session["total"] == len(short) and session["covered"] == len(covered)
    assert session["percent"] == round(len(covered) / len(short) * 100)
    assert set(session["unplaced"]) == {r["name"] for r in short if not m.location_places(r["location"])}
    text = "\n".join(wf_plans.session_lines(session))
    assert "covers where" in text and f"{session['percent']}%" in text


def test_stops_never_exceed_three_and_later_stops_add_new_resources(game_env):
    m = game_env.module
    known_state(m, parts={name: {"owned": 0} for name in list(m.RECIPES)[:20]})
    session = wf_plans.farm_session(_rows(m), m.location_places)
    assert len(session["steps"]) <= 3
    sets = [set(s["resources"]) for s in session["steps"]]
    for i, later in enumerate(sets):
        assert all(not (later & earlier) for earlier in sets[:i])
        assert later  # a stop is only taken if it adds something


def test_resources_marked_enough_are_left_out_and_ui_renders(game_env):
    m = game_env.module
    known_state(m, parts={"Ooltha Strike": {"owned": 0}})
    text = game_env.elements["session-text"].textContent
    assert "Plains of Eidolon" in text
    for resource in ("Fish Scales", "Iradite", "Pyrotic Alloy", "Tear Azurite"):
        m.set_enough(resource, True)
    m.render()
    assert "Nothing left to farm" in game_env.elements["session-text"].textContent


def test_tips_appear_only_when_the_wiki_page_gave_a_sentence(game_env):
    m = game_env.module
    known_state(m, parts={"Ooltha Strike": {"owned": 0}})
    session = wf_plans.farm_session(_rows(m), m.location_places)
    for step in session["steps"]:
        for tip in step["tips"]:
            assert tip["text"] and tip["date"] == "2026-09-27"
