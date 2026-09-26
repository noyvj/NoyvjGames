"""Farming route planner: the single place that covers the most short resources."""

from .test_tracker import _reset_to_known_state


def _row(name, short, location):
    return {"name": name, "built_short": short, "location": location}


def test_places_are_read_from_free_text(game_env):
    m = game_env.module
    assert m.location_places("Plains of Eidolon (Earth)") == ["Plains of Eidolon"]
    assert m.location_places("Orb Vallis (Venus) -- fish part (Charamote)") == ["Orb Vallis"]
    assert m.location_places("Venus, Phobos, Ceres, Jupiter, Pluto, and Sedna") == [
        "Venus", "Phobos", "Ceres", "Jupiter", "Pluto", "Sedna",
    ]
    assert m.location_places("Saturn, Neptune, Eris, and Deimos") == ["Saturn", "Neptune", "Eris", "Deimos"]
    assert "Void" in m.location_places("Mercury, Earth, Lua, Neptune, and the Void")


def test_refined_and_unknown_locations_name_no_place(game_env):
    m = game_env.module
    assert m.location_places("Refined from Pyrol (see Pyrol's own Wiki page)") == []
    assert m.location_places("") == []
    assert m.location_places(None) == []
    assert m.location_places("Unknown -- not yet researched") == []


def test_every_recorded_location_is_understood_or_refined(game_env):
    m = game_env.module
    for name, where in m.RESOURCE_LOCATIONS.items():
        if where.startswith("Refined from"):
            continue
        assert m.location_places(where), (name, where)


def test_ranks_by_resource_count_then_units(game_env):
    m = game_env.module
    rows = [
        _row("A", 10, "Plains of Eidolon (Earth)"),
        _row("B", 5, "Plains of Eidolon (Earth)"),
        _row("C", 500, "Venus, Earth"),
        _row("D", 1, "Venus"),
        _row("E", 0, "Plains of Eidolon (Earth)"),  # covered: ignored
    ]
    picks = m.route_suggestions(rows)
    # Venus and the Plains each cover two; Venus wins the tie on units short.
    assert [p["place"] for p in picks[:2]] == ["Venus", "Plains of Eidolon"]
    assert picks[0]["resources"] == ["C", "D"] and picks[0]["units"] == 501
    assert picks[1]["resources"] == ["A", "B"] and picks[1]["units"] == 15
    assert picks[2]["place"] == "Earth"


def test_text_names_the_best_stop_and_runners_up(game_env):
    m = game_env.module
    rows = [_row("A", 1, "Orb Vallis (Venus)"), _row("B", 1, "Orb Vallis (Venus)"), _row("C", 1, "Cambion Drift (Deimos)")]
    text = m.route_text(rows)
    assert text.startswith("Best single stop to farm next: Orb Vallis, covering 2")
    assert "Cambion Drift (1)" in text
    assert m.route_text([]) == ""


def test_page_shows_it_only_when_something_is_short(game_env):
    m = game_env.module
    _reset_to_known_state(m)
    m.render()
    assert game_env.elements["route-planner"].hidden is True
    _reset_to_known_state(m, parts={"Raplak Prism": {"owned": 0, "target": 1}})
    m.render()
    box = game_env.elements["route-planner"]
    assert box.hidden is False and "Plains of Eidolon" in box.textContent
