"""Tests for A4 (a lifetime-stats screen) and A8 (a shareable "my solar
system" end-state summary card), consolidated into one "Stats & Share"
toolbar panel (games/sol/game.py's update_stats_panel_display() +
build_share_card_text()) rather than two separate panels -- both are
read-only "look back at your progress" views, documented as a deliberate
consolidation given the toolbar already carries several other buttons."""


def _all_texts(element):
    texts = [element.innerText]
    for child in element.children:
        texts.extend(_all_texts(child))
    return texts


def test_panel_hidden_by_default(game_env):
    assert game_env.elements["stats-panel"].hidden is True


def test_toggle_opens_and_closes_the_panel(game_env):
    game_env.toggle_stats()
    assert game_env.elements["stats-panel"].hidden is False
    assert "Hide" in game_env.elements["stats-toggle-button"].innerText

    game_env.toggle_stats()
    assert game_env.elements["stats-panel"].hidden is True


# --- lifetime stats (A4) -------------------------------------------------

def test_manual_clicks_are_counted(game_env):
    for _ in range(5):
        game_env.click("Earth")
    game_env.toggle_stats()
    texts = _all_texts(game_env.elements["stats-panel-content"])
    assert any("Manual clicks: 5" in text for text in texts)


def test_resources_mined_by_hand_are_tracked(game_env):
    for _ in range(3):
        game_env.click("Earth")
    assert game_env.module.lifetime_resources_mined_by_click == 3.0


def test_resources_generated_by_automation_are_tracked(game_env):
    game_env.earth["resource_count"] = 10
    game_env.buy_generator("Earth")
    game_env.timers.tick_intervals(10)  # 1 second
    assert game_env.module.lifetime_resources_generated_by_automation > 0.0


def test_buildings_built_are_counted_lifetime(game_env):
    game_env.earth["resource_count"] = 1000
    game_env.buy_generator("Earth")
    game_env.buy_generator("Earth")
    game_env.buy_recycler("Earth")
    module = game_env.module
    assert module.lifetime_generators_built == 2
    assert module.lifetime_recyclers_built == 1


def test_lifetime_counters_do_not_decrease_after_a_world_reset(game_env):
    """A18's "reset this world" clears the CURRENT building counts, but
    lifetime stats are a history, not a live gauge -- they must not go
    back down just because the buildings that earned them were scrapped."""
    module = game_env.module
    game_env.earth["resource_count"] = 1000
    game_env.buy_generator("Earth")
    built_before = module.lifetime_generators_built

    game_env.reset_world("Earth")

    assert module.lifetime_generators_built == built_before


def test_playtime_is_derived_from_ticks_not_wall_clock(game_env):
    module = game_env.module
    game_env.timers.tick_intervals(10)  # 1 second of ticks
    assert module._lifetime_playtime_seconds() == 1.0


def test_stats_panel_shows_playtime_and_research_and_prestige_rows(game_env):
    game_env.toggle_stats()
    texts = _all_texts(game_env.elements["stats-panel-content"])
    assert any("Time played" in text for text in texts)
    assert any("Research tiers completed: 0/2" in text for text in texts)
    assert any("Prestige level: 0" in text for text in texts)


def test_format_duration_handles_seconds_minutes_and_hours(game_env):
    fmt = game_env.module._format_duration
    assert fmt(5) == "5s"
    assert fmt(65) == "1m 5s"
    assert fmt(3665) == "1h 1m"


# --- shareable summary card (A8) -----------------------------------------

def test_share_card_includes_key_progress_figures(game_env):
    module = game_env.module
    game_env.click("Earth")
    text = module.build_share_card_text()
    assert "My Solar System" in text
    assert "Worlds visited: 1/" in text
    assert f"Achievements: {len(module.achievement_ids_earned())}/{len(module.ACHIEVEMENTS)}" in text


def test_share_card_text_rendered_into_the_panel(game_env):
    game_env.toggle_stats()
    assert "My Solar System" in game_env.elements["share-card-text"].innerText


def test_copy_button_updates_status_text(game_env):
    game_env.elements["copy-share-card-button"].dispatch("click", None)
    status = game_env.elements["copy-share-card-status"].innerText
    assert status  # something was written, browser-only clipboard or not


def test_copy_button_wired_up_exactly_once(game_env):
    """update_stats_panel_display() rebuilds stats-panel-content every
    tick the panel is open, but the copy button lives outside that rebuilt
    subtree specifically so its listener (bound once in setup()) is never
    re-created -- re-creating it every tick would leak a proxy each time,
    the same class of bug press_feedback() already had to fix once."""
    button = game_env.elements["copy-share-card-button"]
    assert len(button._listeners["click"]) == 1
    game_env.toggle_stats()
    game_env.timers.tick_intervals(20)
    assert len(button._listeners["click"]) == 1
