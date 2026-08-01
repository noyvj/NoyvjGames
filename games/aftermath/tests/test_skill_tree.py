"""Milestone 3: skill tree structure — persistent (via localStorage),
separate from run state, unlockable with knowledge points earned from
runs.
"""


def test_skill_tree_starts_empty(game_env):
    assert game_env.skill_tree.knowledge_points == 0
    assert game_env.skill_tree.unlocked == set()


def test_cannot_unlock_without_enough_points(game_env):
    assert game_env.skill_tree.can_unlock("reinforced_infrastructure") is False


def test_can_unlock_with_enough_points(game_env):
    game_env.skill_tree.add_knowledge(3)
    assert game_env.skill_tree.can_unlock("reinforced_infrastructure") is True


def test_unlock_deducts_cost_and_marks_unlocked(game_env):
    game_env.skill_tree.add_knowledge(3)
    result = game_env.skill_tree.unlock("reinforced_infrastructure")
    assert result is True
    assert game_env.skill_tree.knowledge_points == 0
    assert "reinforced_infrastructure" in game_env.skill_tree.unlocked


def test_unlock_fails_if_already_unlocked(game_env):
    game_env.skill_tree.add_knowledge(10)
    game_env.skill_tree.unlock("reinforced_infrastructure")
    points_before = game_env.skill_tree.knowledge_points
    result = game_env.skill_tree.unlock("reinforced_infrastructure")
    assert result is False
    assert game_env.skill_tree.knowledge_points == points_before


def test_unlock_fails_if_insufficient_points(game_env):
    game_env.skill_tree.add_knowledge(1)
    result = game_env.skill_tree.unlock("reinforced_infrastructure")  # costs 3
    assert result is False
    assert game_env.skill_tree.knowledge_points == 1


def test_completing_a_run_awards_knowledge_to_skill_tree(game_env):
    for _ in range(5):
        game_env.resolve_event()
    assert game_env.skill_tree.knowledge_points == game_env.run.knowledge_points_earned()


def test_completing_a_run_does_not_double_award(game_env):
    for _ in range(5):
        game_env.resolve_event()
    points_after_run = game_env.skill_tree.knowledge_points
    game_env.resolve_event()  # run already complete, no-op
    assert game_env.skill_tree.knowledge_points == points_after_run


def test_unlock_persists_to_local_storage(game_env):
    game_env.skill_tree.add_knowledge(3)
    game_env.skill_tree.unlock("reinforced_infrastructure")
    saved_raw = game_env.local_storage.getItem(game_env.module.SKILL_TREE_STORAGE_KEY)
    assert saved_raw is not None
    assert "reinforced_infrastructure" in saved_raw


def test_skill_tree_loads_from_local_storage(game_env):
    game_env.skill_tree.add_knowledge(5)
    game_env.skill_tree.unlock("community_reserves")
    game_env.skill_tree.save()

    loaded = game_env.module.SkillTreeState.load()
    assert loaded.knowledge_points == game_env.skill_tree.knowledge_points
    assert loaded.unlocked == game_env.skill_tree.unlocked


def test_skill_tree_load_with_no_saved_data_starts_fresh(game_env):
    fresh = game_env.module.SkillTreeState.load()
    assert fresh.knowledge_points == 0
    assert fresh.unlocked == set()


def test_render_shows_knowledge_points(game_env):
    game_env.skill_tree.add_knowledge(7)
    game_env.module.render()
    assert "7" in game_env.elements["knowledge-points-display"].innerText


def test_render_disables_unlock_button_when_unaffordable(game_env):
    assert game_env.elements["skill-reinforced_infrastructure-unlock-button"].disabled is True


def test_render_enables_unlock_button_when_affordable(game_env):
    game_env.skill_tree.add_knowledge(3)
    game_env.module.render()
    assert game_env.elements["skill-reinforced_infrastructure-unlock-button"].disabled is False


def test_render_hides_unlock_button_once_unlocked(game_env):
    game_env.skill_tree.add_knowledge(3)
    game_env.unlock_skill("reinforced_infrastructure")
    assert game_env.elements["skill-reinforced_infrastructure-unlock-button"].hidden is True
    assert "unlocked" in game_env.elements["skill-reinforced_infrastructure-status"].innerText
