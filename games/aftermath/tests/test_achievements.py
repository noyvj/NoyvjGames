"""Tests for the ACHIEVEMENTS-SYSTEM-DESIGN.md rollout to Aftermath: the
achievements.json catalog, the checkers/progress readouts in game.py, the
in-game toggle/panel, and the unlock toast + hub-dashboard link (the
site-wide "on top of the base rollout" requirements from
planning/TODO.md). Every achievement's earned status is meant to be a pure
function of state that already exists elsewhere in this module -- these
tests exercise that by driving the real game systems (investing, resolving
events, unlocking skills, starting new runs) rather than poking an
`_earned` flag that doesn't exist.
"""


def _complete_run(game_env):
    for _ in range(len(game_env.module.EVENT_SCHEDULE)):
        game_env.resolve_event()


# --- the catalog itself -----------------------------------------------


def test_achievements_catalog_loads_from_json_with_a_reasonable_count(game_env):
    module = game_env.module
    assert 5 <= len(module.ACHIEVEMENTS) <= 30
    ids = [entry["id"] for entry in module.ACHIEVEMENTS]
    assert len(ids) == len(set(ids))  # no duplicate ids


def test_every_catalog_entry_has_a_matching_checker(game_env):
    module = game_env.module
    for entry in module.ACHIEVEMENTS:
        assert entry["id"] in module.ACHIEVEMENT_CHECKS
        assert callable(module.ACHIEVEMENT_CHECKS[entry["id"]])


def test_every_progress_entry_refers_to_a_real_achievement(game_env):
    module = game_env.module
    catalog_ids = {entry["id"] for entry in module.ACHIEVEMENTS}
    assert set(module.ACHIEVEMENT_PROGRESS).issubset(catalog_ids)


# --- nothing earned on a fresh game ------------------------------------


def test_nothing_is_earned_on_a_fresh_game(game_env):
    assert game_env.module.achievement_ids_earned() == []


def test_summary_shows_every_entry_as_not_earned_initially(game_env):
    summary = game_env.module.achievements_summary()
    assert len(summary) == len(game_env.module.ACHIEVEMENTS)
    assert all(entry["earned"] is False for entry in summary)


# --- individual achievements, driven through real game systems --------


def test_first_event_faced_after_resolving_one_event(game_env):
    assert "first_event_faced" not in game_env.module.achievement_ids_earned()
    game_env.resolve_event()
    assert "first_event_faced" in game_env.module.achievement_ids_earned()


def test_first_event_faced_survives_a_new_run(game_env):
    """A per-run fact (an event was resolved) must be backed by persistent
    tracked state, not the current RunState's own event_log -- otherwise
    the achievement would flicker unearned the instant a new run starts."""
    game_env.resolve_event()
    _complete_run(game_env)
    game_env.start_new_run()
    assert game_env.run.event_index == 0
    assert "first_event_faced" in game_env.module.achievement_ids_earned()


def test_first_resilience_investment(game_env):
    assert "first_resilience_investment" not in game_env.module.achievement_ids_earned()
    game_env.invest_resilience()
    assert "first_resilience_investment" in game_env.module.achievement_ids_earned()


def test_first_resilience_investment_survives_a_new_run(game_env):
    game_env.invest_resilience()
    _complete_run(game_env)
    game_env.start_new_run()
    assert game_env.run.resilience_capacity == 0
    assert "first_resilience_investment" in game_env.module.achievement_ids_earned()


def test_first_growth_investment(game_env):
    assert "first_growth_investment" not in game_env.module.achievement_ids_earned()
    game_env.invest_growth()
    assert "first_growth_investment" in game_env.module.achievement_ids_earned()


def test_run_complete_1_after_a_single_completed_run(game_env):
    assert "run_complete_1" not in game_env.module.achievement_ids_earned()
    _complete_run(game_env)
    assert "run_complete_1" in game_env.module.achievement_ids_earned()
    assert "run_complete_5" not in game_env.module.achievement_ids_earned()


def test_run_complete_5_and_10(game_env):
    module = game_env.module
    for i in range(10):
        _complete_run(game_env)
        if i < 9:
            game_env.start_new_run()
    assert len(game_env.run_history) == 10
    assert "run_complete_5" in module.achievement_ids_earned()
    assert "run_complete_10" in module.achievement_ids_earned()


def test_skill_unlock_achievements(game_env):
    module = game_env.module
    game_env.skill_tree.add_knowledge(3)
    assert "unlock_reinforced_infrastructure" not in module.achievement_ids_earned()
    game_env.unlock_skill("reinforced_infrastructure")
    assert "unlock_reinforced_infrastructure" in module.achievement_ids_earned()
    assert "full_skill_tree" not in module.achievement_ids_earned()


def test_full_skill_tree_requires_every_skill(game_env):
    module = game_env.module
    # E2 added a fourth and fifth skill node, raising the total cost to
    # unlock every skill above the pre-E2 20-point allowance.
    game_env.skill_tree.add_knowledge(sum(skill["cost"] for skill in module.SKILLS.values()))
    for skill_id in module.SKILLS:
        game_env.unlock_skill(skill_id)
    assert "full_skill_tree" in module.achievement_ids_earned()
    assert "unlock_reinforced_infrastructure" in module.achievement_ids_earned()
    assert "unlock_community_reserves" in module.achievement_ids_earned()
    assert "unlock_early_warning" in module.achievement_ids_earned()


def test_knowledge_lifetime_achievements_track_total_ever_earned_not_current_balance(game_env):
    module = game_env.module
    game_env.skill_tree.add_knowledge(25)
    assert "knowledge_25" in module.achievement_ids_earned()
    # Spending it back down must not un-earn the achievement -- it's a
    # lifetime total, not the current spendable balance.
    game_env.skill_tree.unlock("early_warning")  # costs 5
    assert game_env.skill_tree.knowledge_points == 20
    assert "knowledge_25" in module.achievement_ids_earned()
    assert "knowledge_100" not in module.achievement_ids_earned()
    game_env.skill_tree.add_knowledge(80)
    assert "knowledge_100" in module.achievement_ids_earned()


def test_iron_defenses_at_max_mitigation(game_env):
    module = game_env.module
    game_env.run.resources = 10_000
    assert "iron_defenses" not in module.achievement_ids_earned()
    for _ in range(20):  # 20 * 5% = 100%, capped at 85% -- well past the cap
        game_env.invest_resilience()
    assert module.run.mitigation_fraction() == module.MAX_MITIGATION
    assert "iron_defenses" in module.achievement_ids_earned()


def test_iron_defenses_survives_a_new_run(game_env):
    module = game_env.module
    game_env.run.resources = 10_000
    for _ in range(20):
        game_env.invest_resilience()
    _complete_run(game_env)
    game_env.start_new_run()
    assert game_env.run.resilience_capacity == 0
    assert "iron_defenses" in module.achievement_ids_earned()


def test_severe_survivor_requires_a_severe_event_survived(game_env):
    module = game_env.module
    # Run 1 is always "typical" severity (event_severity() returns 1.0
    # unconditionally when run_number <= 1) -- no severe event is possible
    # without at least a second run underway.
    _complete_run(game_env)
    assert "severe_survivor" not in module.achievement_ids_earned()
    game_env.start_new_run()
    game_env.run.resources = 10_000  # ensure it survives whatever hits
    found_severe = False
    for _ in range(len(module.EVENT_SCHEDULE)):
        idx = game_env.run.event_index
        severity = module.event_severity(game_env.run.run_number, idx, module.skill_tree_strength())
        if module.severity_label(severity) == "severe":
            found_severe = True
        game_env.resolve_event()
    if found_severe:
        assert "severe_survivor" in module.achievement_ids_earned()


def test_profitable_run_earned_when_final_resources_exceed_starting(game_env):
    module = game_env.module
    game_env.invest_growth()
    game_env.invest_growth()
    assert "profitable_run" not in module.achievement_ids_earned()
    _complete_run(game_env)
    # Whether it actually nets positive depends on the fixed event
    # schedule's damage vs. the growth income earned -- just check the
    # achievement's truth matches the actual final-vs-starting comparison.
    if game_env.run.resources > game_env.run.starting_resources:
        assert "profitable_run" in module.achievement_ids_earned()
    else:
        assert "profitable_run" not in module.achievement_ids_earned()


def test_growth_focused_and_resilience_focused_are_mutually_exclusive_playstyles(game_env):
    module = game_env.module
    game_env.run.resources = 10_000
    for _ in range(4):
        game_env.invest_growth()
    _complete_run(game_env)
    assert "growth_focused" in module.achievement_ids_earned()
    assert "resilience_focused" not in module.achievement_ids_earned()

    game_env.start_new_run()
    game_env.run.resources = 10_000
    for _ in range(4):
        game_env.invest_resilience()
    _complete_run(game_env)
    assert "resilience_focused" in module.achievement_ids_earned()


def test_balanced_strategy_requires_equal_meaningful_investment(game_env):
    module = game_env.module
    game_env.run.resources = 10_000
    for _ in range(3):
        game_env.invest_resilience()
        game_env.invest_growth()
    _complete_run(game_env)
    assert "balanced_strategy" in module.achievement_ids_earned()


def test_come_back_stronger_requires_improvement_over_the_first_run(game_env):
    module = game_env.module
    _complete_run(game_env)  # run 1
    first_score = game_env.run_history[0]
    game_env.start_new_run()
    game_env.run.resources = 10_000  # guarantee a higher final score than run 1
    _complete_run(game_env)
    assert game_env.run_history[-1] > first_score
    assert "come_back_stronger" in module.achievement_ids_earned()


def test_come_back_stronger_not_earned_after_only_one_run(game_env):
    _complete_run(game_env)
    assert "come_back_stronger" not in game_env.module.achievement_ids_earned()


# --- progress readouts --------------------------------------------------


def test_progress_readout_for_run_complete_5(game_env):
    module = game_env.module
    _complete_run(game_env)
    current, target = module.ACHIEVEMENT_PROGRESS["run_complete_5"]()
    assert current == 1
    assert target == 5


def test_progress_readout_for_full_skill_tree(game_env):
    module = game_env.module
    game_env.skill_tree.add_knowledge(3)
    game_env.unlock_skill("reinforced_infrastructure")
    current, target = module.ACHIEVEMENT_PROGRESS["full_skill_tree"]()
    assert current == 1
    assert target == len(module.SKILLS)


def test_progress_readout_for_knowledge_caps_at_target(game_env):
    module = game_env.module
    game_env.skill_tree.add_knowledge(500)
    current, target = module.ACHIEVEMENT_PROGRESS["knowledge_100"]()
    assert current == target == 100


# --- no mutation as a side effect ---------------------------------------


def test_checking_achievements_never_mutates_other_state(game_env):
    module = game_env.module
    game_env.invest_resilience()
    game_env.invest_growth()
    before = module.get_state()
    module.achievement_ids_earned()
    module.achievement_ids_earned()
    module.achievements_summary()
    after = module.get_state()
    before.pop("achievements_earned")
    after.pop("achievements_earned")
    assert before == after


# --- toggle / panel ------------------------------------------------------


def _all_texts(element):
    texts = [element.innerText]
    for child in element.children:
        texts.extend(_all_texts(child))
    return texts


def test_achievements_panel_is_hidden_by_default(game_env):
    assert game_env.elements["achievements-panel"].hidden is True


def test_toggle_opens_and_closes_the_panel(game_env):
    game_env.toggle_achievements()
    assert game_env.elements["achievements-panel"].hidden is False
    game_env.toggle_achievements()
    assert game_env.elements["achievements-panel"].hidden is True


def test_toggle_button_shows_earned_over_total_count(game_env):
    module = game_env.module
    game_env.resolve_event()  # earns first_event_faced
    game_env.toggle_achievements()
    text = game_env.elements["achievements-toggle-button"].innerText
    assert f"1/{len(module.ACHIEVEMENTS)}" in text or f"({1}/{len(module.ACHIEVEMENTS)})" in text


def test_panel_renders_every_catalog_entrys_label_and_description(game_env):
    module = game_env.module
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    rendered = " ".join(text for card in panel.children for text in _all_texts(card))
    for entry in module.ACHIEVEMENTS:
        assert entry["label"] in rendered
        assert entry["description"] in rendered


def test_earned_card_is_marked_distinctly(game_env):
    game_env.resolve_event()
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    earned_cards = [c for c in panel.children if "achievement-card--earned" in c.className]
    assert len(earned_cards) == 1


def test_panel_includes_a_link_to_the_hub_dashboard(game_env):
    game_env.toggle_achievements()
    panel = game_env.elements["achievements-panel"]
    links = [c for c in panel.children if getattr(c, "className", "") == "achievements-hub-link"]
    assert len(links) == 1
    assert "index.html#account-achievements-dashboard" in links[0].href


def test_panel_stays_live_across_resolve_event(game_env):
    game_env.toggle_achievements()
    game_env.resolve_event()
    text = game_env.elements["achievements-toggle-button"].innerText
    assert "1/" in text


# --- unlock toast --------------------------------------------------------


def test_toast_shows_on_a_newly_earned_achievement(game_env):
    toast = game_env.elements["achievement-toast"]
    assert toast.hidden is True
    game_env.resolve_event()  # earns first_event_faced
    assert toast.hidden is False
    assert "Facing It Head-On" in game_env.elements["achievement-toast-text"].innerText


def test_toast_auto_hides_after_its_timer_fires(game_env):
    game_env.resolve_event()
    assert game_env.elements["achievement-toast"].hidden is False
    game_env.timers.flush()
    assert game_env.elements["achievement-toast"].hidden is True


def test_toast_does_not_refire_for_an_already_earned_achievement(game_env):
    game_env.resolve_event()
    game_env.timers.flush()
    game_env.elements["achievement-toast"].hidden = True  # simulate it having closed
    game_env.resolve_event()  # first_event_faced already earned; nothing new
    assert game_env.elements["achievement-toast"].hidden is True


def test_loading_a_save_with_earned_achievements_does_not_flood_toasts(game_env):
    module = game_env.module
    game_env.resolve_event()
    game_env.invest_resilience()
    snapshot = module.get_state()
    game_env.elements["achievement-toast"].hidden = True  # reset from the actions above

    module.load_state(snapshot)

    assert game_env.elements["achievement-toast"].hidden is True
