"""AN-13: a skill tree with no free refund lets you move ONE point for a small knowledge fee, never a restart."""


def _own(m, *skills, knowledge=0):
    m.skill_tree.unlocked = set(skills)
    m.skill_tree.knowledge_points = knowledge


def test_moving_one_skill_costs_the_fee_and_the_price_difference(game_env):
    m = game_env.module
    _own(m, "adaptive_growth", knowledge=2)            # owns a 4-cost skill, 2 spare
    ok, reason = m.skill_tree.move_check("adaptive_growth", "early_warning")   # 5 instead of 4, plus the fee: 2 spare is enough
    assert ok and reason == ""
    assert m.skill_tree.move("adaptive_growth", "early_warning") is True
    assert m.skill_tree.unlocked == {"early_warning"}
    assert m.skill_tree.knowledge_points == 2 + 4 - 5 - m.SKILL_MOVE_FEE


def test_a_cheaper_skill_gives_the_difference_back_minus_the_fee(game_env):
    m = game_env.module
    _own(m, "early_warning", knowledge=0)
    assert m.skill_tree.move("early_warning", "adaptive_growth") is True
    assert m.skill_tree.knowledge_points == 5 - 4 - m.SKILL_MOVE_FEE == 0


def test_lifetime_knowledge_never_changes_and_the_move_is_saved(game_env):
    m = game_env.module
    _own(m, "adaptive_growth", knowledge=5)
    m.skill_tree.lifetime_knowledge = 40
    m.skill_tree.move("adaptive_growth", "early_warning")
    assert m.skill_tree.lifetime_knowledge == 40
    reloaded = m.SkillTreeState.load()
    assert reloaded.unlocked == {"early_warning"} and reloaded.lifetime_knowledge == 40


def test_not_enough_knowledge_says_how_short_you_are(game_env):
    m = game_env.module
    _own(m, "adaptive_growth", knowledge=0)
    ok, reason = m.skill_tree.move_check("adaptive_growth", "early_warning")
    assert not ok and "2 knowledge short" in reason
    assert m.skill_tree.move("adaptive_growth", "early_warning") is False
    assert m.skill_tree.unlocked == {"adaptive_growth"} and m.skill_tree.knowledge_points == 0


def test_a_skill_other_skills_depend_on_cannot_be_moved(game_env):
    m = game_env.module
    _own(m, "reinforced_infrastructure", "community_reserves", "mutual_aid_network", knowledge=20)
    ok, reason = m.skill_tree.move_check("reinforced_infrastructure", "adaptive_growth")
    assert not ok and "needed by Mutual Aid Network" in reason
    ok, _ = m.skill_tree.move_check("mutual_aid_network", "adaptive_growth")      # the end of a chain can move
    assert ok


def test_the_destination_cannot_need_the_skill_being_given_up(game_env):
    m = game_env.module
    _own(m, "reinforced_infrastructure", "early_warning", knowledge=20)
    ok, reason = m.skill_tree.move_check("reinforced_infrastructure", "climate_hardening")
    assert not ok and "Reinforced Infrastructure" in reason


def test_bad_ids_and_same_skill_and_owned_destination_are_refused(game_env):
    m = game_env.module
    _own(m, "adaptive_growth", "early_warning", knowledge=20)
    for a, b in (("adaptive_growth", "adaptive_growth"), ("nope", "early_warning"), ("adaptive_growth", "nope"),
                 ("adaptive_growth", "early_warning"), ("community_reserves", "adaptive_growth")):
        assert m.skill_tree.move_check(a, b)[0] is False
        assert m.skill_tree.move(a, b) is False


def test_the_panel_is_hidden_with_nothing_owned_and_lists_owned_and_unowned(game_env):
    m = game_env.module
    _own(m, knowledge=9)
    m.render()
    assert game_env.elements["skill-move"].hidden is True
    _own(m, "adaptive_growth", knowledge=9)
    m.render()
    assert game_env.elements["skill-move"].hidden is False
    from_values = [o.value for o in game_env.elements["skill-move-from"].children]
    to_values = [o.value for o in game_env.elements["skill-move-to"].children]
    assert from_values == ["adaptive_growth"] and "adaptive_growth" not in to_values and "early_warning" in to_values


def test_pressing_the_button_moves_the_point_and_says_so(game_env):
    m = game_env.module
    _own(m, "adaptive_growth", knowledge=9)
    m.render()
    game_env.elements["skill-move-to"].value = "early_warning"
    m.on_skill_move_select()
    assert game_env.elements["skill-move-button"].disabled is False
    game_env.elements["skill-move-button"].dispatch("click", None)
    assert m.skill_tree.unlocked == {"early_warning"}
    assert "Moved from Adaptive Growth Practices to Early Warning Systems" in game_env.elements["skill-move-status"].innerText


def test_an_impossible_pick_disables_the_button_and_explains(game_env):
    m = game_env.module
    _own(m, "reinforced_infrastructure", "community_reserves", "mutual_aid_network", knowledge=0)
    m.render()
    game_env.elements["skill-move-from"].value = "reinforced_infrastructure"
    game_env.elements["skill-move-to"].value = "adaptive_growth"
    m.on_skill_move_select()
    assert game_env.elements["skill-move-button"].disabled is True
    assert "needed by" in game_env.elements["skill-move-status"].innerText
