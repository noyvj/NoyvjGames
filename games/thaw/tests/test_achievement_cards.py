"""G-27 progress bars and remaining amounts on locked achievement cards, G-31 frost glyphs and the
one-time unlock flourish."""


def _card(game_env, achievement_id):
    for card in game_env.elements["achievements-panel"].children:
        if getattr(card.dataset, "achievementId", None) == achievement_id:
            return card
    raise AssertionError(f"no card for {achievement_id}")


def _classes(card):
    return {c.className for c in card.children}


def test_glyph_table_covers_the_catalog(game_env):
    module = game_env.module
    for entry in module.ACHIEVEMENTS:
        assert entry["id"] in module.ACHIEVEMENT_GLYPHS
    assert module.achievement_glyph("not-a-real-id") == module.DEFAULT_ACHIEVEMENT_GLYPH


def test_locked_card_with_a_goal_has_a_bar_and_remaining_text(game_env):
    game_env.toggle_achievements()
    card = _card(game_env, "quarter_dampening")
    assert "achievement-card-bar" in _classes(card)
    progress = next(c for c in card.children if c.className == "achievement-card-progress")
    assert progress.innerText == "0 of 25 — 25 more per cent of dampening to go"
    assert "25 more per cent" in card.title


def test_bar_fill_follows_progress(game_env):
    game_env.region.capacity["preserve"] = 2  # 16% dampening
    game_env.module.render()
    game_env.toggle_achievements()
    card = _card(game_env, "quarter_dampening")
    bar = next(c for c in card.children if c.className == "achievement-card-bar")
    assert bar.children[0].style.width == "64%"


def test_earned_card_has_no_bar_and_says_earned(game_env):
    game_env.region.capacity["output"] = 1
    game_env.module.render()
    game_env.toggle_achievements()
    card = _card(game_env, "first_output")
    assert "achievement-card--earned" in card.className
    label = next(c for c in card.children if c.className == "achievement-card-label")
    assert label.innerText.startswith("Earned:")
    assert "achievement-card-bar" not in _classes(card)


def test_one_shot_achievements_have_no_bar(game_env):
    game_env.toggle_achievements()
    card = _card(game_env, "tipping_point_witnessed")
    assert "achievement-card-bar" not in _classes(card)
    assert "achievement-card-progress" not in _classes(card)


def test_flourish_class_only_on_first_render_of_an_earned_card(game_env):
    game_env.region.capacity["output"] = 1
    game_env.module.render()
    game_env.toggle_achievements()
    assert "achievement-card--new" in _card(game_env, "first_output").className
    game_env.toggle_achievements()
    game_env.toggle_achievements()
    assert "achievement-card--new" not in _card(game_env, "first_output").className


def test_new_progress_scales(game_env):
    module = game_env.module
    assert module.ACHIEVEMENT_PROGRESS["comparison_engaged"]() == (0, 2)
    module.region_b.capacity["output"] = 1
    assert module.ACHIEVEMENT_PROGRESS["comparison_engaged"]() == (1, 2)
    assert module.ACHIEVEMENT_PROGRESS["slow_burn"]() == (0, 15)
    assert module.ACHIEVEMENT_PROGRESS["beat_both_regions"]() == (1, 15)


def test_remaining_text_is_empty_when_met_or_unscaled(game_env):
    module = game_env.module
    assert module.achievement_remaining_text("long_haul", (25, 25)) == ""
    assert module.achievement_remaining_text("long_haul", None) == ""
    assert module.achievement_remaining_text("long_haul", (24, 25)) == "1 more round to go"
