"""Tests for the Milestone 1 core click loop, on Earth (game.py)."""


def test_setup_configures_button(game_env):
    button = game_env.elements["click-button"]
    assert button.innerText == "Mine Iron"
    assert button.disabled is False


def test_setup_registers_click_listener(game_env):
    button = game_env.elements["click-button"]
    assert "click" in button._listeners
    assert len(button._listeners["click"]) == 1


def test_initial_resource_count_is_zero(game_env):
    assert game_env.earth["resource_count"] == 0
    assert game_env.elements["resource-count"].innerText == "0"


def test_single_click_increments_resource_count(game_env):
    game_env.click()
    assert game_env.earth["resource_count"] == 1


def test_single_click_updates_display(game_env):
    game_env.click()
    assert game_env.elements["resource-count"].innerText == "1"


def test_multiple_clicks_accumulate(game_env):
    for _ in range(5):
        game_env.click()
    assert game_env.earth["resource_count"] == 5
    assert game_env.elements["resource-count"].innerText == "5"


def test_click_calling_on_earth_click_directly_also_increments(game_env):
    game_env.module.on_earth_click(None)
    assert game_env.earth["resource_count"] == 1


def test_click_adds_pressed_class_immediately(game_env):
    button = game_env.elements["click-button"]
    assert not button.classList.contains("pressed")
    game_env.click()
    assert button.classList.contains("pressed")


def test_pressed_class_persists_until_timer_flushed(game_env):
    button = game_env.elements["click-button"]
    game_env.click()
    assert button.classList.contains("pressed")
    # No time has "passed" yet — the fake timer queue hasn't been flushed.
    assert button.classList.contains("pressed")


def test_pressed_class_removed_after_timer_flush(game_env):
    button = game_env.elements["click-button"]
    game_env.click()
    game_env.timers.flush()
    assert not button.classList.contains("pressed")


def test_clear_pressed_scheduled_with_120ms_delay(game_env):
    game_env.click()
    assert len(game_env.timers.pending) == 1
    _callback, delay = game_env.timers.pending[0]
    assert delay == 120


def test_rapid_clicks_each_schedule_their_own_clear(game_env):
    button = game_env.elements["click-button"]
    game_env.click()
    game_env.click()
    game_env.click()
    assert len(game_env.timers.pending) == 3
    assert button.classList.contains("pressed")

    game_env.timers.flush()
    assert not button.classList.contains("pressed")
    assert game_env.earth["resource_count"] == 3


def test_resource_label_untouched_by_clicks(game_env):
    # Milestone 1 doesn't rewrite the label — only the count — on click.
    label = game_env.elements["resource-label"]
    original = label.innerText
    game_env.click()
    assert label.innerText == original


def test_update_resource_display_reflects_arbitrary_module_state(game_env):
    game_env.earth["resource_count"] = 42
    game_env.module.update_resource_display("Earth")
    assert game_env.elements["resource-count"].innerText == "42"


def test_game_env_fixture_gives_isolated_state_per_test(game_env):
    # Guards against state leaking across tests via Python's import cache.
    assert game_env.earth["resource_count"] == 0
