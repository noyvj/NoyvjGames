"""U2: the optional Hamlet view.

Two halves, matching how the feature is split. `hamlet.py` is the pure engine
half (which buildings exist, where they stand, what each one says) and is
tested directly. game.py's `render_hamlet()` is the DOM half, tested through
the fake-DOM harness like every other panel: the point of most of these tests
is that a click on a hamlet building goes through the SAME handlers as the
ordinary Work / Build / Research panels, so the two can never disagree.

hamlet.js (3D buildings, pointer picking, chip projection) and the CSS that
hides the ordinary panels are verified live in a browser, not here.
"""

import math
import pathlib

import pytest

import hamlet
import sim

GAME_DIR = pathlib.Path(__file__).resolve().parent.parent


# --- engine: the station list ---------------------------------------------

def test_station_ids_and_slots_are_unique_and_on_the_ring():
    ids = [s["id"] for s in hamlet.STATIONS]
    slots = [s["slot"] for s in hamlet.STATIONS]
    assert len(ids) == len(set(ids))
    assert len(slots) == len(set(slots))
    assert all(0 <= slot < hamlet.SLOT_COUNT for slot in slots)
    for station in hamlet.STATIONS:
        x, z = hamlet.position(station)
        assert math.isclose(math.hypot(x, z), hamlet.RING_RADIUS, abs_tol=0.01)


def test_every_role_and_building_appears_in_exactly_one_station():
    roles = [s["role"] for s in hamlet.STATIONS if s["role"]]
    buildings = [s["building"] for s in hamlet.STATIONS if s["building"]]
    assert sorted(roles) == sorted(sim.ROLES)
    assert sorted(buildings) == sorted(sim.BUILDINGS)


def test_station_era_matches_the_era_its_role_or_building_unlocks():
    for station in hamlet.STATIONS:
        for key, table in (("role", sim.ERA_ROLES), ("building", sim.ERA_BUILDINGS)):
            if station[key]:
                assert station[key] in table[station["era"]]


def test_stations_grow_with_the_era_and_keep_a_stable_order():
    previous = []
    for era in sim.ERA_ORDER:
        ids = [s["id"] for s in hamlet.stations_for_era(era)]
        assert ids[: len(previous)] == previous or set(previous) <= set(ids)
        assert ids[0] == hamlet.TOWN_ID
        assert len(ids) > len(previous)
        previous = ids
    assert len(hamlet.stations_for_era(sim.ERA_ORDER[-1])) == len(hamlet.STATIONS)


def test_flat_percent_keeps_every_station_inside_the_stage():
    for station in hamlet.STATIONS:
        left, top = hamlet.flat_percent(*hamlet.position(station))
        assert 0 < left < 100 and 0 < top < 100


# --- engine: what a station says -----------------------------------------------

def _state():
    return sim.CityState()


def test_structure_station_builds_and_blocks_when_materials_are_short():
    state = _state()
    view = hamlet.station_view(hamlet.STATIONS_BY_ID["shelter"], state)
    assert view["primary"] == "build" and view["primary_ok"] is True
    assert view["cost"] == sim.BUILDING_COST["shelter"]
    assert "Shelter" in view["aria_label"] and "12" in view["aria_label"]
    state.resources["materials"] = 0.0
    blocked = hamlet.station_view(hamlet.STATIONS_BY_ID["shelter"], state)
    assert blocked["primary_ok"] is False
    assert "more needed" in blocked["aria_label"]


def test_workplace_station_assigns_and_blocks_when_nobody_is_idle():
    state = _state()
    state.allocation = {role: 0 for role in state.allocation}
    view = hamlet.station_view(hamlet.STATIONS_BY_ID["foragers"], state)
    assert view["primary"] == "assign" and view["has_build_button"] is False
    assert view["primary_ok"] is (state.idle_workers() > 0)
    for role in state.allocation:
        state.allocation[role] = 0
    state.allocation["foragers"] = state.population
    full = hamlet.station_view(hamlet.STATIONS_BY_ID["foragers"], state)
    assert full["primary_ok"] is False and full["can_unassign"] is True
    assert "idle" in full["aria_label"]


def test_paired_station_has_both_a_worker_action_and_a_build_button():
    view = hamlet.station_view(hamlet.STATIONS_BY_ID["fire_circle"], _state())
    assert view["primary"] == "assign"
    assert view["has_build_button"] is True
    assert view["cost"] == sim.BUILDING_COST["hearth"]
    assert "separate button" in view["aria_label"]


def test_town_centre_view_opens_a_panel():
    view = hamlet.station_view(hamlet.STATIONS_BY_ID[hamlet.TOWN_ID], _state())
    assert view["primary"] == "open" and view["primary_ok"] is True
    assert view["aria_label"].startswith("Town Centre")


def test_researchable_nodes_are_available_unknown_and_cheapest_first(game_env):
    tree = game_env.module.tree
    nodes = hamlet.researchable_nodes(tree)
    assert nodes
    assert all(tree.is_available(n.node_id) and not tree.is_researched(n.node_id) for n in nodes)
    costs = [n.cost for n in nodes]
    assert costs == sorted(costs)
    assert hamlet.locked_count(tree) > 0


# --- the game: off by default -------------------------------------------------

def test_hamlet_is_off_by_default_and_changes_nothing(game_env):
    m, e = game_env.module, game_env.elements
    assert m.hamlet_on is False
    assert e["hamlet-stage"].hidden is True
    assert not e["game"].classList.contains("hamlet-on")
    assert e["hamlet-toggle-button"].innerText == "🏘 Hamlet view: Off"
    assert e["hamlet-toggle-button"].attributes["aria-pressed"] == "false"
    assert e["hamlet-chips"].children == []
    # The ordinary panels are still rendered as usual.
    assert e["work-list"].children and e["buildings-list"].children


def test_toggle_turns_it_on_and_remembers_the_choice(game_env, monkeypatch):
    m, e = game_env.module, game_env.elements
    saved = []
    monkeypatch.setattr(m, "_hamlet_storage_set", lambda value: saved.append(value) or True)
    e["hamlet-toggle-button"].dispatch("click", None)
    assert m.hamlet_on is True and saved == ["on"]
    assert e["game"].classList.contains("hamlet-on")
    assert e["hamlet-stage"].hidden is False
    assert e["hamlet-toggle-button"].innerText == "🏘 Hamlet view: On"
    assert e["hamlet-toggle-button"].attributes["aria-pressed"] == "true"
    e["hamlet-toggle-button"].dispatch("click", None)
    assert saved == ["on", "off"]
    assert not e["game"].classList.contains("hamlet-on")
    assert e["hamlet-stage"].hidden is True


def test_saved_preference_is_read_at_load(game_env, monkeypatch):
    m, e = game_env.module, game_env.elements
    monkeypatch.setattr(m, "_hamlet_storage_get", lambda: "on")
    m.setup()
    assert m.hamlet_on is True
    assert e["game"].classList.contains("hamlet-on")
    monkeypatch.setattr(m, "_hamlet_storage_get", lambda: None)
    m.setup()
    assert m.hamlet_on is False


def test_storage_helpers_survive_a_missing_or_broken_window(game_env, monkeypatch):
    m = game_env.module
    assert m._hamlet_storage_get() is None       # no window under the harness
    assert m._hamlet_storage_set("on") is False

    class Boom:
        @property
        def localStorage(self):
            raise RuntimeError("blocked")

    monkeypatch.setattr(m, "_js_window", lambda: Boom())
    assert m._hamlet_storage_get() is None
    assert m._hamlet_storage_set("on") is False


def test_a_screen_that_cannot_host_it_falls_back_to_the_normal_panels(game_env, monkeypatch):
    m, e = game_env.module, game_env.elements
    m.hamlet_on = True
    monkeypatch.setattr(m, "_hamlet_capable", lambda: False)
    m.render()
    assert e["hamlet-toggle-button"].hidden is True
    assert e["hamlet-stage"].hidden is True
    assert not e["game"].classList.contains("hamlet-on")
    assert m.hamlet_active() is False


def test_capability_check_uses_the_desktop_media_query(game_env, monkeypatch):
    m = game_env.module
    seen = []

    class Query:
        matches = False

    class Window:
        def matchMedia(self, query):
            seen.append(query)
            return Query()

    monkeypatch.setattr(m, "_js_window", lambda: Window())
    assert m._hamlet_capable() is False
    assert seen == [m.HAMLET_MEDIA_QUERY]
    assert "pointer: fine" in m.HAMLET_MEDIA_QUERY and "min-width" in m.HAMLET_MEDIA_QUERY


# --- the game: chips ----------------------------------------------------------

@pytest.fixture
def hamlet_env(game_env):
    game_env.elements["hamlet-toggle-button"].dispatch("click", None)
    assert game_env.module.hamlet_on
    return game_env


def _main(env, station_id):
    return env.elements[f"hamlet-{station_id}-main"]


def test_tribal_hamlet_has_one_chip_per_station_in_order(hamlet_env):
    chips = hamlet_env.elements["hamlet-chips"].children
    expected = [s["id"] for s in hamlet.stations_for_era("tribal")]
    assert [c.attributes["data-station"] for c in chips] == expected
    assert len(chips) == 7


def test_hud_shows_the_headline_numbers(hamlet_env):
    hud = hamlet_env.elements["hamlet-hud"].innerText
    for fragment in ("👥", "🍖", "🪵", "💡", "Tribal", "score"):
        assert fragment in hud


def test_every_building_is_a_keyboard_reachable_labelled_button(hamlet_env):
    for chip in hamlet_env.elements["hamlet-chips"].children:
        sid = chip.attributes["data-station"]
        main = _main(hamlet_env, sid)
        assert main.attributes["type"] == "button"
        assert main.attributes["aria-label"].strip()
        assert main.attributes["aria-disabled"] in ("true", "false")
        # A blocked building must stay focusable (aria-disabled, never `disabled`).
        assert main.disabled is False
        assert chip.attributes["role"] == "group"
        for suffix in ("unassign", "build"):
            extra = hamlet_env.elements.get(f"hamlet-{sid}-{suffix}")
            if extra is not None:
                assert extra.attributes["aria-label"].strip()
                assert extra.disabled is False


def test_chips_carry_the_data_the_3d_layer_reads(hamlet_env):
    for chip in hamlet_env.elements["hamlet-chips"].children:
        station = hamlet.STATIONS_BY_ID[chip.attributes["data-station"]]
        x, z = hamlet.position(station)
        assert chip.attributes["data-shape"] == station["shape"]
        assert float(chip.attributes["data-hx"]) == x
        assert float(chip.attributes["data-hz"]) == z
        # Flat (no-WebGL) positions are already set in percent.
        assert chip.style.left.endswith("%") and chip.style.top.endswith("%")


def test_clicking_a_structure_builds_it_through_the_normal_handler(hamlet_env):
    e, state = hamlet_env.elements, hamlet_env.state
    before_count, before_mats = state.buildings["shelter"], state.resources["materials"]
    minutes_before = len(hamlet_env.module.minutes.entries(hamlet_env.module.campaign.ui))
    _main(hamlet_env, "shelter").dispatch("click", None)
    assert state.buildings["shelter"] == before_count + 1
    assert state.resources["materials"] == before_mats - sim.BUILDING_COST["shelter"]
    # Same side effects as the Build panel: the council minutes got a motion.
    assert len(hamlet_env.module.minutes.entries(hamlet_env.module.campaign.ui)) == minutes_before + 1
    assert "Built Shelter" in e["hamlet-live"].innerText
    # The ordinary Build panel shows the same new count.
    assert e["shelter-count"].innerText == str(state.buildings["shelter"])


def test_clicking_a_structure_you_cannot_afford_does_nothing_and_says_why(hamlet_env):
    e, state = hamlet_env.elements, hamlet_env.state
    state.resources["materials"] = 1.0
    hamlet_env.module.render()
    assert _main(hamlet_env, "granary").attributes["aria-disabled"] == "true"
    count = state.buildings["granary"]
    _main(hamlet_env, "granary").dispatch("click", None)
    assert state.buildings["granary"] == count and state.resources["materials"] == 1.0
    assert "Not enough materials" in e["hamlet-live"].innerText


def test_clicking_a_workplace_assigns_a_worker_and_minus_takes_one_off(hamlet_env):
    e, state = hamlet_env.elements, hamlet_env.state
    state.allocation = {role: 0 for role in state.allocation}
    hamlet_env.module.render()
    _main(hamlet_env, "gatherers").dispatch("click", None)
    assert state.allocation["gatherers"] == 1
    assert "Gatherers: 1 working" in e["hamlet-live"].innerText
    assert e["gatherers-count"].innerText == "1"      # the ordinary Work panel agrees
    e["hamlet-gatherers-unassign"].dispatch("click", None)
    assert state.allocation["gatherers"] == 0
    e["hamlet-gatherers-unassign"].dispatch("click", None)
    assert "Nobody is working" in e["hamlet-live"].innerText


def test_assigning_with_nobody_idle_is_refused_with_a_message(hamlet_env):
    e, state = hamlet_env.elements, hamlet_env.state
    for role in state.allocation:
        state.allocation[role] = 0
    state.allocation["foragers"] = state.population
    hamlet_env.module.render()
    assert _main(hamlet_env, "gatherers").attributes["aria-disabled"] == "true"
    _main(hamlet_env, "gatherers").dispatch("click", None)
    assert state.allocation["gatherers"] == 0
    assert "No one is idle" in e["hamlet-live"].innerText


def test_a_pair_builds_from_its_own_button_and_assigns_from_the_building(hamlet_env):
    e, state = hamlet_env.elements, hamlet_env.state
    state.resources["materials"] = 100.0
    state.allocation = {role: 0 for role in state.allocation}
    hamlet_env.module.render()
    hearths = state.buildings["hearth"]
    e["hamlet-fire_circle-build"].dispatch("click", None)
    assert state.buildings["hearth"] == hearths + 1
    _main(hamlet_env, "fire_circle").dispatch("click", None)
    assert state.allocation["keepers"] == 1


def test_chips_are_updated_in_place_so_keyboard_focus_survives_a_season(hamlet_env):
    e = hamlet_env.elements
    before = {sid: els["main"] for sid, els in hamlet_env.module._hamlet_els.items()}
    chips_before = list(e["hamlet-chips"].children)
    hamlet_env.advance_season(3)
    hamlet_env.module.render()
    after = {sid: els["main"] for sid, els in hamlet_env.module._hamlet_els.items()}
    assert all(after[sid] is main for sid, main in before.items())
    assert e["hamlet-chips"].children == chips_before


def test_a_new_era_adds_its_stations(hamlet_env):
    e = hamlet_env.elements
    hamlet_env.state.era = "agrarian"
    hamlet_env.module.render()
    ids = [c.attributes["data-station"] for c in e["hamlet-chips"].children]
    assert "farm" in ids and len(ids) == 8
    hamlet_env.state.era = sim.ERA_ORDER[-1]
    hamlet_env.module.render()
    assert len(e["hamlet-chips"].children) == len(hamlet.STATIONS)
    assert "hamlet-rings-build" in e


def test_hamlet_click_handlers_do_not_leak_proxies_when_chips_are_rebuilt(hamlet_env):
    m = hamlet_env.module
    old = list(m._hamlet_proxies)
    assert old
    hamlet_env.state.era = "agrarian"
    m.render()
    assert all(proxy.destroyed for proxy in old)


# --- the game: the Town Centre ---------------------------------------------------

def test_town_centre_panel_opens_and_closes(hamlet_env):
    e = hamlet_env.elements
    assert e["hamlet-town-panel"].hidden is True
    _main(hamlet_env, hamlet.TOWN_ID).dispatch("click", None)
    assert e["hamlet-town-panel"].hidden is False
    assert _main(hamlet_env, hamlet.TOWN_ID).attributes["aria-expanded"] == "true"
    e["hamlet-town-close"].dispatch("click", None)
    assert e["hamlet-town-panel"].hidden is True
    assert _main(hamlet_env, hamlet.TOWN_ID).attributes["aria-expanded"] == "false"


def test_town_centre_studies_research_through_the_normal_handler(hamlet_env):
    e, state, tree = hamlet_env.elements, hamlet_env.state, hamlet_env.module.tree
    _main(hamlet_env, hamlet.TOWN_ID).dispatch("click", None)
    node = hamlet.researchable_nodes(tree)[0]
    button = e[f"hamlet-study-{node.node_id}"]
    assert button.attributes["aria-disabled"] == "true"          # no knowledge yet
    button.dispatch("click", None)
    assert not tree.is_researched(node.node_id)
    assert "Not enough knowledge" in e["hamlet-live"].innerText

    state.resources["knowledge"] = 50.0
    hamlet_env.module.render()
    e[f"hamlet-study-{node.node_id}"].dispatch("click", None)
    assert tree.is_researched(node.node_id)
    assert state.resources["knowledge"] == pytest.approx(50.0 - node.cost)
    assert f"Studied {node.name}" in e["hamlet-live"].innerText
    # The study row is gone from the panel once known, as in the Research panel.
    assert f"hamlet-study-{node.node_id}" not in [
        c.id for row in e["hamlet-town-panel"].children for c in getattr(row, "children", [])
    ]


def test_town_centre_lists_only_studyable_nodes(hamlet_env):
    e, tree = hamlet_env.elements, hamlet_env.module.tree
    _main(hamlet_env, hamlet.TOWN_ID).dispatch("click", None)
    wanted = {n.node_id for n in hamlet.researchable_nodes(tree)}
    present = {
        key[len("hamlet-study-"):] for key in e
        if key.startswith("hamlet-study-") and key[len("hamlet-study-"):] in tree.nodes
    }
    assert wanted <= present


def test_town_centre_accepts_and_abandons_a_civic_challenge(hamlet_env):
    e, state = hamlet_env.elements, hamlet_env.state
    _main(hamlet_env, hamlet.TOWN_ID).dispatch("click", None)
    assert state.challenge["active"] is None
    offered = hamlet_env.module.challenges.offered(state, hamlet_env.module.current_effects())
    assert offered
    e[f"hamlet-challenge-{offered[0]}"].dispatch("click", None)
    assert state.challenge["active"]["id"] == offered[0]
    e["hamlet-challenge-abandon"].dispatch("click", None)
    assert state.challenge["active"] is None


def test_town_centre_advance_era_is_blocked_until_ready_then_moves_on(hamlet_env):
    e, state, m = hamlet_env.elements, hamlet_env.state, hamlet_env.module
    _main(hamlet_env, hamlet.TOWN_ID).dispatch("click", None)
    button = e["hamlet-advance-era"]
    assert button.attributes["aria-disabled"] == "true"
    era = state.era
    button.dispatch("click", None)
    assert state.era == era
    # Make the settlement genuinely ready, then use the same button.
    state.population = 40
    while not m.transition.transition_ready(state, m.tree, m.current_effects()):
        candidates = [n for n in m.tree.nodes if m.tree.is_available(n) and not m.tree.is_researched(n)]
        if not candidates:
            pytest.skip("could not make the settlement era-ready in this build")
        state.resources["knowledge"] = 1000.0
        m.tree.research(candidates[0], state.resources)
    m.render()
    assert e["hamlet-advance-era"].attributes["aria-disabled"] == "false"
    e["hamlet-advance-era"].dispatch("click", None)
    assert state.era != era


def test_town_panel_only_rebuilds_when_its_contents_change(hamlet_env):
    m, e = hamlet_env.module, hamlet_env.elements
    _main(hamlet_env, hamlet.TOWN_ID).dispatch("click", None)
    button = e["hamlet-town-close"]
    m.render()
    assert e["hamlet-town-close"] is button                     # untouched by a plain render
    hamlet_env.state.resources["knowledge"] = 3.5
    m.render()
    assert e["hamlet-town-knowledge"].innerText == "Knowledge: 3.5"


# --- wiring in the page ------------------------------------------------------------

def test_page_wires_the_hamlet_pieces():
    html = (GAME_DIR / "index.html").read_text()
    css = (GAME_DIR / "style.css").read_text()
    assert '"hamlet.py"' in html                      # fetched into Pyodide's filesystem
    assert '<script src="hamlet.js">' in html
    for element_id in ("hamlet-toggle-button", "hamlet-stage", "hamlet-chips", "hamlet-town-panel",
                       "hamlet-hud", "hamlet-live", "visual-stage"):
        assert f'id="{element_id}"' in html
    # The toggle starts hidden (game.py shows it only on a desktop-class screen).
    assert 'id="hamlet-toggle-button"' in html and "hidden>🏘" in html
    for panel in ("#work", "#buildings", "#research", "#civic", "#era-progress"):
        assert f"#game.hamlet-on {panel}" in css
    assert (GAME_DIR / "hamlet.js").exists()


def test_hamlet_module_has_no_dom_or_game_state_side_effects():
    source = (GAME_DIR / "hamlet.py").read_text()
    assert "from js" not in source and "import js" not in source
    assert "create_proxy" not in source
