"""Milestone 13: galaxy scaling. A second system, the Kepler Cluster,
gated behind a research node. It's a self-contained three-good need-
triangle (own goods, not shared with the home system's five) so
colony_needing()/colony_producing() stay single-valued across the whole
galaxy without ever needing two colonies to want or make the same good.
Colony state for the cluster isn't created until the research unlocks
it, so it can't be picked as Milestone 12's "most urgent" colony (and
sent ships chasing an unreachable destination) before that.
"""


def test_kepler_cluster_is_not_reachable_by_default(game_env):
    module = game_env.module
    assert "kepler_a" not in module.active_colony_ids()
    assert "kepler_a" not in module.colony_states


def test_unlocking_galaxy_expansion_makes_the_cluster_reachable(game_env):
    module = game_env.module
    module.research_points = 100
    game_env.unlock_research("galaxy_expansion")
    assert "kepler_a" in module.active_colony_ids()
    assert "kepler_b" in module.active_colony_ids()
    assert "kepler_c" in module.active_colony_ids()


def test_unlocking_galaxy_expansion_creates_kepler_colony_state(game_env):
    module = game_env.module
    module.research_points = 100
    game_env.unlock_research("galaxy_expansion")
    for colony_id in ("kepler_a", "kepler_b", "kepler_c"):
        assert colony_id in module.colony_states
        assert module.colony_states[colony_id].need_satisfaction == module.STARTING_NEED_SATISFACTION


def test_kepler_cluster_is_a_closed_triangle_of_its_own_goods(game_env):
    module = game_env.module
    produced = {c["produces"] for c in module.EXPANSION_COLONIES.values()}
    needed = {c["needs"] for c in module.EXPANSION_COLONIES.values()}
    assert produced == needed
    assert produced.isdisjoint({module.ORE, module.GRAIN, module.MACHINERY, module.WATER, module.ENERGY})


def test_colony_needing_and_producing_stay_single_valued_across_the_galaxy(game_env):
    module = game_env.module
    module.research_points = 100
    game_env.unlock_research("galaxy_expansion")
    for good in module.SELL_PRICE:
        needers = [cid for cid, c in module.ALL_COLONIES.items() if c["needs"] == good]
        producers = [cid for cid, c in module.ALL_COLONIES.items() if c["produces"] == good]
        assert len(needers) <= 1
        assert len(producers) <= 1


def test_ship_cannot_depart_to_kepler_before_unlock(game_env):
    ship = game_env.ship("1")
    ship.load()
    assert ship.depart("kepler_a") is False
    assert ship.docked  # never left


def test_ship_can_depart_to_kepler_once_unlocked(game_env):
    module = game_env.module
    module.research_points = 100
    game_env.unlock_research("galaxy_expansion")
    ship = game_env.ship("1")  # docked at aurum, empty
    assert ship.reposition("kepler_a") is True
    assert ship.destination == "kepler_a"


def test_fleet_priority_ignores_kepler_before_it_is_unlocked(game_env):
    # Regression guard for the exact bug this design was built to avoid:
    # an unreached, always-decaying Kepler colony must never win
    # most_urgent_colony() while it isn't even reachable yet.
    module = game_env.module
    game_env.tick(50)  # plenty of time for an eagerly-created colony to decay to the bottom
    assert module.most_urgent_colony() in module.COLONIES


def test_developed_kepler_colony_secondary_need_reaches_the_home_system(game_env):
    module = game_env.module
    module.research_points = 100
    game_env.unlock_research("galaxy_expansion")
    state = module.colony_states["kepler_a"]
    assert state.secondary_need() == module.ENERGY  # reaches back into the home system


def test_kepler_colony_specialization_activates_once_developed(game_env):
    module = game_env.module
    module.research_points = 100
    game_env.unlock_research("galaxy_expansion")
    state = module.colony_states["kepler_a"]
    state.cumulative_delivered = module.DEVELOPMENT_THRESHOLD
    state.deliver(0)  # re-triggers the level-2 check with the threshold already met
    assert state.is_developed()
    assert module.SPECIALIZATION["kepler_a"]["name"] == "Deep-Core Extractor"


def test_route_edges_exclude_kepler_before_unlock(game_env):
    module = game_env.module
    edges = module.route_edges()
    origins = {edge[0] for edge in edges}
    assert origins.isdisjoint({"kepler_a", "kepler_b", "kepler_c"})


def test_route_edges_include_kepler_after_unlock(game_env):
    module = game_env.module
    module.research_points = 100
    game_env.unlock_research("galaxy_expansion")
    edges = dict(module.route_edges())
    # kepler_a produces rare metals, which kepler_c needs (kepler_c -> kepler_a's produce is
    # the reverse); kepler_b produces biomass, which kepler_a needs.
    assert edges["kepler_a"] == "kepler_c"
    assert edges["kepler_b"] == "kepler_a"
    assert edges["kepler_c"] == "kepler_b"


def test_kepler_depart_buttons_hidden_before_unlock(game_env):
    game_env.load(ship_id="1")
    button = game_env.elements["ship-1-depart-kepler_a-button"]
    assert button.hidden is True


def test_kepler_depart_buttons_appear_after_unlock_when_loaded(game_env):
    module = game_env.module
    module.research_points = 100
    game_env.unlock_research("galaxy_expansion")
    game_env.load(ship_id="1")
    button = game_env.elements["ship-1-depart-kepler_a-button"]
    assert button.hidden is False


def test_expansion_colonies_panel_hidden_before_unlock(game_env):
    assert game_env.elements["expansion-colonies-panel"].hidden is True


def test_expansion_colonies_panel_visible_after_unlock(game_env):
    module = game_env.module
    module.research_points = 100
    game_env.unlock_research("galaxy_expansion")
    module.render()
    assert game_env.elements["expansion-colonies-panel"].hidden is False
