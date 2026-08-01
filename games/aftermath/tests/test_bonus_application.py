"""Milestone 4: unlocked skill-tree bonuses actually modify a new run's
starting conditions and event resolution — not just decorative unlocks.
"""

import pytest


def test_new_run_has_no_bonuses_with_nothing_unlocked(game_env):
    fresh = game_env.module.RunState()
    assert fresh.resources == 200.0
    assert fresh.resilience_capacity == 0


def test_community_reserves_adds_starting_resources(game_env):
    game_env.skill_tree.add_knowledge(3)
    game_env.skill_tree.unlock("community_reserves")
    fresh = game_env.module.RunState()
    assert fresh.resources == 250.0


def test_reinforced_infrastructure_adds_starting_resilience(game_env):
    game_env.skill_tree.add_knowledge(3)
    game_env.skill_tree.unlock("reinforced_infrastructure")
    fresh = game_env.module.RunState()
    assert fresh.resilience_capacity == 2


def test_early_warning_adds_flat_mitigation_bonus(game_env):
    game_env.skill_tree.add_knowledge(5)
    game_env.skill_tree.unlock("early_warning")
    fresh = game_env.module.RunState()
    assert fresh.mitigation_fraction() == 0.10  # 0 resilience capacity + 10% bonus


def test_early_warning_stacks_with_resilience_capacity(game_env):
    game_env.skill_tree.add_knowledge(5)
    game_env.skill_tree.unlock("early_warning")
    fresh = game_env.module.RunState()
    fresh.resilience_capacity = 4  # 20% from resilience
    assert fresh.mitigation_fraction() == pytest.approx(0.30)  # 20% + 10% bonus


def test_multiple_bonuses_apply_together(game_env):
    game_env.skill_tree.add_knowledge(11)
    game_env.skill_tree.unlock("community_reserves")
    game_env.skill_tree.unlock("reinforced_infrastructure")
    game_env.skill_tree.unlock("early_warning")
    fresh = game_env.module.RunState()
    assert fresh.resources == 250.0
    assert fresh.resilience_capacity == 2
    assert fresh.mitigation_fraction() == 0.20  # 2*0.05 + 0.10


def test_bonuses_still_cap_at_max_mitigation(game_env):
    game_env.skill_tree.add_knowledge(5)
    game_env.skill_tree.unlock("early_warning")
    fresh = game_env.module.RunState()
    fresh.resilience_capacity = 1000
    assert fresh.mitigation_fraction() == 0.85


def test_start_new_run_replaces_global_run_with_bonuses_applied(game_env):
    for _ in range(5):
        game_env.resolve_event()  # complete the first run, earn a knowledge point
    game_env.skill_tree.add_knowledge(3)  # ensure enough for the cheapest skill
    game_env.unlock_skill("community_reserves")
    game_env.start_new_run()
    assert game_env.run.event_index == 0
    assert game_env.run.resources == 250.0


def test_new_run_button_hidden_mid_run(game_env):
    assert game_env.elements["new-run-button"].hidden is True


def test_new_run_button_visible_after_completion(game_env):
    for _ in range(5):
        game_env.resolve_event()
    assert game_env.elements["new-run-button"].hidden is False
