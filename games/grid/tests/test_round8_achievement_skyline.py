"""Round-8 pass: achievement cards in the skyline look (C-31)."""
from .test_round7_trend import _tick


def _open_panel(env):
    env.toggle_achievements()
    return env.elements["achievements-panel"]


def _cards(panel):
    return [c for c in panel.children if getattr(c, "dataset", None) is not None and hasattr(c.dataset, "achievementId")]


def test_every_card_has_a_building_icon_with_a_text_label(game_env):
    panel = _open_panel(game_env)
    cards = _cards(panel)
    assert len(cards) == len(game_env.module.ACHIEVEMENTS) > 0
    for card in cards:
        icons = [c for c in card.children if c.className == "achievement-card-icon"]
        assert len(icons) == 1
        assert "<svg" in icons[0].innerHTML and 'aria-label="Not earned yet"' in icons[0].innerHTML


def test_locked_building_is_a_dark_outline_without_windows(game_env):
    svg = game_env.module.achievement_icon_svg("first_watt", False)
    assert "sky-building--dark" in svg and "sky-window" not in svg and "Not earned yet" in svg


def test_earned_building_is_lit_with_windows(game_env):
    svg = game_env.module.achievement_icon_svg("first_watt", True)
    assert "sky-building--lit" in svg and svg.count("sky-window") >= 3 and 'aria-label="Earned"' in svg


def test_each_building_shape_follows_the_manifest_order(game_env):
    g = game_env.module
    ids = [a["id"] for a in g.ACHIEVEMENTS]
    assert g.achievement_building_index(ids[0]) == 0
    assert g.achievement_building_index(ids[1]) == 1
    assert g.achievement_building_index("no such id") == 0
    shapes = {g.achievement_building_index(i) for i in ids}
    assert len(shapes) == min(len(ids), len(g.SKYLINE_BUILDINGS))


def test_a_new_unlock_gets_one_powerup_flash_then_none(game_env):
    game_env.build("coal")  # First Watt
    panel = _open_panel(game_env)
    first = [c for c in _cards(panel) if c.dataset.achievementId == "first_watt"][0]
    assert "achievement-card--earned" in first.className and "achievement-card--powerup" in first.className
    assert any(c.className == "achievement-card-fresh" and c.innerText == "Just powered up" for c in first.children)
    assert all(not c.className.startswith("achievement-card--powerup") for c in [])
    # Drawn again: the flash was used up.
    game_env.module.update_achievements_display()
    again = [c for c in _cards(game_env.elements["achievements-panel"]) if c.dataset.achievementId == "first_watt"][0]
    assert "achievement-card--powerup" not in again.className
    assert not any(c.className == "achievement-card-fresh" for c in again.children)
    assert "achievement-card--earned" in again.className


def test_a_loaded_save_with_earned_achievements_does_not_flash(game_env):
    g = game_env.module
    game_env.build("coal")
    snapshot = g.get_state()
    game_env.module.update_achievements_display()
    g.load_state(snapshot)
    panel = _open_panel(game_env)
    assert not any("powerup" in c.className for c in _cards(panel))


def test_flash_checkbox_turns_the_motion_off_but_keeps_the_words(game_env):
    _tick(game_env, "pref-unlock-flash", False)
    assert game_env.module.prefs["unlock_flash"] is False
    game_env.build("coal")
    panel = _open_panel(game_env)
    first = [c for c in _cards(panel) if c.dataset.achievementId == "first_watt"][0]
    assert "achievement-card--still" in first.className
    assert any(c.className == "achievement-card-fresh" for c in first.children)


def test_flash_preference_is_not_part_of_a_save(game_env):
    assert "unlock_flash" not in game_env.module.get_state()
    assert game_env.elements["pref-unlock-flash"].checked is True
