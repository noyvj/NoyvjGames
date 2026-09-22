"""Milestone 15 -- Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md).

Follows SOL's reference integration and the design doc's own testing
standard: catalog sanity, nothing earned on a fresh settlement, every
individual achievement earned by driving the real game systems (assigning
workers, building, researching, advancing seasons, transitioning eras,
entering/exiting a revisit) rather than poking a synthetic "earned" flag,
progress readouts, a no-mutation check, and the toggle/panel/toast.

Two achievements are tested as pure functions of a hand-built score
history rather than through a full play-through (`thriving_once`'s
"already true at the very start" case aside): getting a real settlement to
genuinely collapse (<30) and then recover (>=70) through natural seasons
would take many turns to engineer reliably. `_replay_scores()` below drives
`state.record_score()` for each value in sequence -- the same real method
`game.py`'s `on_advance_season()` calls every season -- rather than setting
`state.score_history` directly, since Z25 moved the achievement's own
"ever collapsed then recovered" signal onto a sticky field
(`ever_recovered_from_collapse`) that only `record_score()` maintains;
assigning to `score_history` alone would no longer be enough to earn it.
This is called out explicitly rather than silently treated as equivalent
to a full playthrough.
"""

import research
import sim
import sustainability

from .test_space_age_era import (
    push_to_agrarian,
    push_to_classical,
    push_to_digital,
    push_to_industrial,
    push_to_medieval,
    push_to_space,
)


def _research_everything(tree, resources):
    """Researches every node the tree will ever allow, given unlimited
    knowledge -- loops because tier-gating means some nodes only become
    available once others are researched first. Real public API
    (`tree.research`), the same one every handler in game.py calls."""
    resources["knowledge"] = 10**9
    changed = True
    while changed:
        changed = False
        for node_id in list(tree.nodes):
            if not tree.is_researched(node_id) and tree.is_available(node_id):
                tree.research(node_id, resources)
                changed = True


# --- catalog sanity -------------------------------------------------------
def test_catalog_loads_and_ids_are_unique(game_env):
    achievements = game_env.module.ACHIEVEMENTS
    assert len(achievements) >= 5
    ids = [entry["id"] for entry in achievements]
    assert len(ids) == len(set(ids))


def test_every_catalog_entry_has_a_checker(game_env):
    module = game_env.module
    for entry in module.ACHIEVEMENTS:
        assert entry["id"] in module.ACHIEVEMENT_CHECKS


def test_every_progress_id_refers_to_a_real_achievement(game_env):
    module = game_env.module
    catalog_ids = {entry["id"] for entry in module.ACHIEVEMENTS}
    for achievement_id in module.ACHIEVEMENT_PROGRESS:
        assert achievement_id in catalog_ids


def test_nothing_is_earned_on_a_brand_new_settlement(game_env):
    # "thriving_once" is a real exception -- a fresh Tribal settlement's
    # score (~88) is already in the Thriving band by construction (see
    # sustainability.py's component weighting at population 6), so it is
    # legitimately earned from the very first render, not a bug.
    earned = set(game_env.module.achievement_ids_earned())
    assert earned <= {"thriving_once"}


# --- individual achievements, driven through real systems -----------------
def test_reached_agrarian_through_classical_through_the_real_era_button(game_env):
    push_to_agrarian(game_env)
    assert "reached_agrarian" in game_env.module.achievement_ids_earned()
    assert "reached_classical" not in game_env.module.achievement_ids_earned()
    push_to_classical(game_env)
    assert "reached_classical" in game_env.module.achievement_ids_earned()


def test_reached_medieval_through_real_transitions(game_env):
    # push_to_medieval() is NOT self-contained -- its own docstring says it
    # "continues past push_to_classical()" -- so it must be chained after
    # push_to_agrarian()/push_to_classical() on the same fresh env, the same
    # way test_space_age_era.py's own push_to_industrial() does internally.
    push_to_agrarian(game_env)
    push_to_classical(game_env)
    push_to_medieval(game_env)
    earned = set(game_env.module.achievement_ids_earned())
    assert {"reached_agrarian", "reached_classical", "reached_medieval"} <= earned
    assert "reached_industrial" not in earned


def test_reached_industrial_through_real_transitions(game_env):
    # push_to_industrial() IS self-contained (it chains agrarian->classical
    # ->medieval->industrial_ready->click internally), so it takes a fresh
    # game_env on its own rather than continuing from a previous push.
    push_to_industrial(game_env)
    assert "reached_industrial" in game_env.module.achievement_ids_earned()


def test_reached_digital_through_real_transitions(game_env):
    push_to_digital(game_env)  # self-contained, same as push_to_industrial()
    assert "reached_digital" in game_env.module.achievement_ids_earned()


def test_reached_space_through_real_transitions(game_env):
    push_to_space(game_env)  # self-contained, same as push_to_industrial()
    assert "reached_space" in game_env.module.achievement_ids_earned()


def test_thriving_once_is_earned_immediately_by_a_fresh_settlement(game_env):
    # No action needed: this is the "already true at the start" case the
    # module docstring above and CLAUDE.md's build notes call out.
    assert "thriving_once" in game_env.module.achievement_ids_earned()


def _replay_scores(state, values):
    """Resets the score-history derivatives and replays `values` through
    the real `record_score()` method, in order -- the same call
    `on_advance_season()` makes every season (see the module docstring
    above for why this can't be a plain `score_history` assignment
    anymore)."""
    state.score_history = []
    state.peak_score = None
    state.lowest_score_seen = None
    state.ever_recovered_from_collapse = False
    for value in values:
        state.record_score(value)


def test_phoenix_settlement_needs_a_real_collapse_then_recovery(game_env):
    state = game_env.state
    assert "phoenix_settlement" not in game_env.module.achievement_ids_earned()

    _replay_scores(state, [88.0, 70.0, 45.0])
    assert "phoenix_settlement" not in game_env.module.achievement_ids_earned()  # never dropped below 30

    _replay_scores(state, [88.0, 25.0, 60.0])
    assert "phoenix_settlement" not in game_env.module.achievement_ids_earned()  # recovered, but not to 70+

    _replay_scores(state, [88.0, 25.0, 71.0])
    assert "phoenix_settlement" in game_env.module.achievement_ids_earned()


def test_phoenix_settlement_requires_the_recovery_to_come_after_the_collapse(game_env):
    """Order-sensitivity: a settlement that was fine, then collapsed, and
    has not yet recovered should NOT count -- even though its history
    contains the same two numbers (88, then eventually 25) that a genuine
    recovery case would also contain, just in the opposite order."""
    state = game_env.state
    _replay_scores(state, [88.0, 70.0, 45.0, 25.0])
    assert "phoenix_settlement" not in game_env.module.achievement_ids_earned()


def test_provision_community_craft_specialists_and_root_and_branch(game_env):
    tree = game_env.module.tree
    state = game_env.state
    earned_before = set(game_env.module.achievement_ids_earned())
    assert not {"provision_specialist", "community_specialist", "craft_specialist", "root_and_branch"} & earned_before

    push_to_space(game_env)
    _research_everything(tree, state.resources)

    earned = set(game_env.module.achievement_ids_earned())
    assert "provision_specialist" in earned
    assert "community_specialist" in earned
    assert "craft_specialist" in earned
    assert "root_and_branch" in earned
    assert len(tree.researched) == len(tree.nodes)


def test_built_to_last_needs_real_role_diversity(game_env):
    state = game_env.state
    assert "built_to_last" not in game_env.module.achievement_ids_earned()

    # resilience() (sustainability.py) averages three things: a food
    # buffer, tool readiness, and role_diversity() (sim.py) -- an exactly
    # even split across every Tribal role maximizes diversity to a real
    # 1.0 (sim.py's own role_diversity() docstring), and generous food/
    # tools push the other two components to their ratio cap, so all three
    # inputs are genuinely satisfied rather than only diversity.
    state.population = 8
    state.allocation = dict.fromkeys(sim.ROLES, 0)
    state.allocation["foragers"] = 2
    state.allocation["gatherers"] = 2
    state.allocation["crafters"] = 2
    state.allocation["keepers"] = 2
    state.resources["food"] = 10_000.0
    state.resources["tools"] = 10_000.0
    game_env.module.render()
    effects = game_env.module.current_effects()
    resilience = sustainability.components(state, effects)["resilience"]
    assert resilience >= game_env.module.BUILT_TO_LAST_MIN_RESILIENCE, resilience
    assert "built_to_last" in game_env.module.achievement_ids_earned()


def test_equity_champion_needs_population_and_a_genuinely_balanced_settlement(game_env):
    state = game_env.state
    state.population = 25
    state.allocation = dict.fromkeys(sim.ROLES, 0)
    state.allocation["foragers"] = 10
    state.allocation["gatherers"] = 8
    state.allocation["crafters"] = 4
    state.allocation["keepers"] = 3
    state.resources["food"] = 500.0
    # sim.py's real building keys are "granary" (Storage Pit) and "hearth"
    # (Fire Circle) -- generously sized so shelter_adequacy/social_provision
    # both hit their 1.0 ratio cap; food_security is a fresh CityState's
    # default fed_fraction (1.0), so this settlement's worst-met provision
    # is a genuine 1.0, not merely "no era-specific penalty applies yet".
    state.buildings["shelter"] = 10
    state.buildings["granary"] = 5
    state.buildings["hearth"] = 5
    game_env.module.render()
    effects = game_env.module.current_effects()
    components = sustainability.components(state, effects)
    # Sanity check this scenario actually reaches the threshold before
    # asserting the achievement follows from it -- if the balance tuning
    # above ever needs adjusting, this fails with a clear number instead of
    # a confusing achievement-not-earned assertion.
    assert components["equity"] >= game_env.module.EQUITY_CHAMPION_MIN_EQUITY, components
    assert "equity_champion" in game_env.module.achievement_ids_earned()


def test_full_coordination_needs_a_fully_staffed_canal(game_env):
    push_to_classical(game_env)
    state = game_env.state
    state.buildings["canals"] = 1
    state.allocation["administrators"] = sim.ADMINISTRATORS_PER_CANAL
    game_env.advance_season()
    assert "full_coordination" in game_env.module.achievement_ids_earned()


def test_nobody_exposed_needs_public_works_covering_the_whole_population(game_env):
    push_to_medieval(game_env)
    state = game_env.state
    state.population = 5
    state.buildings["public_works"] = 5
    game_env.advance_season()
    assert "nobody_exposed" in game_env.module.achievement_ids_earned()


def test_well_designed_rings_needs_fully_staffed_habitat_rings(game_env):
    push_to_space(game_env)  # leaves population at 150 (push_to_space_ready)
    state = game_env.state
    # One ring only serves RING_CAPACITY_PER_BUILDING (30) people well even
    # at full staffing -- match population down to that so "fully covered"
    # is actually reachable with a single ring, the real public field the
    # same way every push_to_* helper above already sets population.
    state.population = int(sim.RING_CAPACITY_PER_BUILDING)
    state.buildings["habitat_rings"] = 1
    state.allocation["architects"] = sim.ARCHITECTS_PER_RING
    game_env.advance_season()
    assert "well_designed_rings" in game_env.module.achievement_ids_earned()


def test_a_real_city_needs_population_100(game_env):
    assert "a_real_city" not in game_env.module.achievement_ids_earned()
    game_env.state.population = 100
    game_env.module.render()
    assert "a_real_city" in game_env.module.achievement_ids_earned()


def test_looking_back_is_earned_by_actually_using_the_revisit_ui(game_env):
    push_to_agrarian(game_env)
    assert "looking_back" not in game_env.module.achievement_ids_earned()

    button = game_env.elements["revisit-tribal-button"]
    button.dispatch("click", None)
    assert "looking_back" in game_env.module.achievement_ids_earned()
    assert game_env.module.campaign.revisiting == "tribal"

    game_env.elements["exit-revisit-button"].dispatch("click", None)
    assert game_env.module.campaign.revisiting is None
    # Monotonic: still earned after returning to the present.
    assert "looking_back" in game_env.module.achievement_ids_earned()


# --- progress readouts -----------------------------------------------------
def test_progress_readouts_track_real_counts(game_env):
    module = game_env.module
    tree = module.tree
    state = game_env.state

    current, target = module.ACHIEVEMENT_PROGRESS["root_and_branch"]()
    assert (current, target) == (len(tree.researched), len(tree.nodes))

    current, target = module.ACHIEVEMENT_PROGRESS["a_real_city"]()
    assert current == state.population
    assert target == module.A_REAL_CITY_POPULATION


# --- no mutation ------------------------------------------------------------
def test_computing_achievements_never_mutates_other_state(game_env):
    push_to_classical(game_env)
    before = game_env.module.campaign.to_dict()
    game_env.module.achievement_ids_earned()
    game_env.module.achievements_summary()
    after = game_env.module.campaign.to_dict()
    assert before == after


# --- panel toggle/render ----------------------------------------------------
def test_achievements_panel_hidden_by_default_and_toggles(game_env):
    panel = game_env.elements["achievements-panel"]
    toggle = game_env.elements["achievements-toggle-button"]
    assert panel.hidden is True

    toggle.dispatch("click", None)
    assert panel.hidden is False
    assert "0/" in toggle.innerText or "Hide" in toggle.innerText

    toggle.dispatch("click", None)
    assert panel.hidden is True


def test_achievements_panel_renders_every_catalog_entry_and_marks_earned(game_env):
    game_env.elements["achievements-toggle-button"].dispatch("click", None)
    panel = game_env.elements["achievements-panel"]
    # One card per catalog entry, plus the hub-dashboard link appended last.
    assert len(panel.children) == len(game_env.module.ACHIEVEMENTS) + 1
    earned_cards = [c for c in panel.children[:-1] if "achievement-card--earned" in c.className]
    assert len(earned_cards) == len(game_env.module.achievement_ids_earned())


def test_achievements_panel_stays_live_across_a_season_advance(game_env):
    game_env.elements["achievements-toggle-button"].dispatch("click", None)
    push_to_agrarian(game_env)
    toggle = game_env.elements["achievements-toggle-button"]
    earned_count = len(game_env.module.achievement_ids_earned())
    assert f"({earned_count}/" in toggle.innerText


# --- unlock toast ------------------------------------------------------------
def test_a_newly_earned_achievement_shows_a_toast(game_env):
    toast = game_env.elements["achievement-toast"]
    assert toast.hidden is True

    push_to_agrarian(game_env)  # earns reached_agrarian via the real button

    assert toast.hidden is False
    text = game_env.elements["achievement-toast-text"]
    assert "Beyond the Tribe" in text.innerText or "unlocked" in text.innerText.lower()


def test_the_toast_auto_dismisses_after_its_timeout(game_env):
    push_to_agrarian(game_env)
    toast = game_env.elements["achievement-toast"]
    assert toast.hidden is False
    game_env.timers.flush()
    assert toast.hidden is True


def test_a_save_that_already_has_achievements_does_not_flood_toasts_on_load(game_env):
    push_to_agrarian(game_env)
    game_env.elements["achievement-toast"].hidden = True  # simulate it already faded
    data = game_env.module.get_state()
    assert "reached_agrarian" in data["achievements_earned"]

    # Loading a save with achievements already earned must not re-toast them.
    game_env.module.load_state(data)
    assert game_env.elements["achievement-toast"].hidden is True


# --- get_state()/load_state() contract ---------------------------------
def test_achievements_earned_is_write_only(game_env):
    push_to_agrarian(game_env)
    data = game_env.module.get_state()
    assert "reached_agrarian" in data["achievements_earned"]

    # Tamper with the saved list, then load -- it must not come back as
    # live state; achievement_ids_earned() always recomputes fresh.
    data["achievements_earned"] = ["not_a_real_id"]
    game_env.module.load_state(data)
    assert "not_a_real_id" not in game_env.module.achievement_ids_earned()
    assert "reached_agrarian" in game_env.module.achievement_ids_earned()


def test_has_revisited_round_trips_through_a_save(game_env):
    push_to_agrarian(game_env)
    game_env.elements["revisit-tribal-button"].dispatch("click", None)
    game_env.elements["exit-revisit-button"].dispatch("click", None)

    data = game_env.module.get_state()
    assert data["has_revisited"] is True

    fresh_data = {**data}
    fresh_data["has_revisited"] = False
    game_env.module.load_state(fresh_data)
    assert game_env.module.campaign.has_revisited is False


def test_a_save_missing_has_revisited_loads_as_false(game_env):
    push_to_agrarian(game_env)
    data = game_env.module.get_state()
    del data["has_revisited"]
    assert game_env.module.load_state(data) is True
    assert game_env.module.campaign.has_revisited is False
