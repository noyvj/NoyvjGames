"""V-CD-4 (planning/TODO.md completion audit, section N): the welcome-back
toast's original static current-standing snapshot (see test_achievements.py's
own A3 tests, still valid for the first-load case) revised to a genuine
"+X since last time" delta -- comparing this load's numbers against what
this same BROWSER (localStorage, never the save code itself) last recorded.
"""

import json


def test_first_ever_load_falls_back_to_the_static_snapshot(game_env):
    """No stored snapshot yet (fresh localStorage, this browser's first-ever
    load) -- nothing to diff against, so the original static "N/8 worlds
    visited" wording is used, not a nonsensical "+N since never"."""
    module = game_env.module
    module.load_state(module.get_state())

    text = game_env.elements["achievement-toast-text"].innerText
    assert "Welcome back" in text
    assert "since you were last here" not in text
    assert "worlds visited" in text
    assert "1/" in text  # Earth only, no travel yet

    # The snapshot is stored after this first load, ready to diff next time.
    stored = json.loads(game_env.local_storage.getItem(module.WELCOME_BACK_SNAPSHOT_STORAGE_KEY))
    assert stored == {"worlds_visited": 1, "achievements_earned": 0, "machines_built": 0, "manual_clicks": 0}


def test_genuine_positive_delta_shown_on_a_later_load(game_env):
    """A real increase in both stats between two loads in the same browser
    shows the actual difference, not a re-stated current total."""
    module = game_env.module
    module.load_state(module.get_state())  # establishes the baseline snapshot

    game_env.click()  # mines Iron on Earth -> first_ore achievement
    module.unlocked_bodies.add("Mars")
    game_env.travel_to("Mars")  # second visited world -> off_world achievement

    module.load_state(module.get_state())

    text = game_env.elements["achievement-toast-text"].innerText
    assert "Welcome back" in text
    assert "since you were last here" in text
    assert "+1 world(s) visited" in text
    assert "+2 achievement(s)" in text


def test_same_or_lower_values_do_not_show_a_negative_delta(game_env):
    """Loading an older/different save code with equal-or-lower numbers
    than the stored snapshot must never show a "-N" as though something
    was lost -- falls back to the static wording instead."""
    module = game_env.module
    saved_old = module.get_state()  # Earth only, no progress yet

    game_env.click()
    module.unlocked_bodies.add("Mars")
    game_env.travel_to("Mars")
    module.load_state(module.get_state())  # stores a "high" snapshot (2 worlds, 2 achievements)
    stored = json.loads(game_env.local_storage.getItem(module.WELCOME_BACK_SNAPSHOT_STORAGE_KEY))
    assert stored["worlds_visited"] == 2
    assert stored["achievements_earned"] == 2

    module.load_state(saved_old)  # an OLDER save, loaded into the same browser

    text = game_env.elements["achievement-toast-text"].innerText
    assert "Welcome back" in text
    assert "since you were last here" not in text
    assert "-" not in text  # no negative delta anywhere in the message


def test_stored_snapshot_updates_correctly_across_two_consecutive_loads(game_env):
    """Each load updates the stored snapshot to ITS OWN current values
    (computed against the old stored values first), so the next visit
    compares against this one rather than some frozen baseline."""
    module = game_env.module
    module.load_state(module.get_state())
    first_stored = json.loads(game_env.local_storage.getItem(module.WELCOME_BACK_SNAPSHOT_STORAGE_KEY))
    assert first_stored == {"worlds_visited": 1, "achievements_earned": 0, "machines_built": 0, "manual_clicks": 0}

    game_env.click()
    module.unlocked_bodies.add("Mars")
    game_env.travel_to("Mars")
    module.load_state(module.get_state())
    second_stored = json.loads(game_env.local_storage.getItem(module.WELCOME_BACK_SNAPSHOT_STORAGE_KEY))
    assert second_stored["worlds_visited"] == 2
    assert second_stored["achievements_earned"] == 2
    assert second_stored != first_stored


def test_load_welcome_back_snapshot_defaults_on_malformed_storage(game_env):
    module = game_env.module
    game_env.local_storage.setItem(module.WELCOME_BACK_SNAPSHOT_STORAGE_KEY, "not json")
    assert module._load_welcome_back_snapshot() is None


def test_welcome_back_snapshot_is_not_part_of_get_state(game_env):
    module = game_env.module
    assert "welcome_back" not in json.dumps(module.get_state()).lower()


def test_r9_machines_and_clicks_show_in_the_delta(game_env):
    """R-9: the welcome-back line also reports machines built and hand-mined loads."""
    module = game_env.module
    game_env.local_storage.setItem(
        module.WELCOME_BACK_SNAPSHOT_STORAGE_KEY,
        json.dumps({"worlds_visited": 1, "achievements_earned": 0, "machines_built": 2, "manual_clicks": 10}),
    )
    module.lifetime_generators_built = 7
    module.total_manual_clicks = 55
    module._show_welcome_back_toast()
    text = game_env.elements["achievement-toast-text"].innerText
    assert "+5 machine(s) built" in text and "+45 hand-mined load(s)" in text and "since you were last here" in text


def test_r9_an_old_snapshot_without_the_new_fields_still_works(game_env):
    module = game_env.module
    game_env.local_storage.setItem(
        module.WELCOME_BACK_SNAPSHOT_STORAGE_KEY, json.dumps({"worlds_visited": 1, "achievements_earned": 0})
    )
    module.lifetime_generators_built = 3
    module._show_welcome_back_toast()
    text = game_env.elements["achievement-toast-text"].innerText
    assert "machine(s)" not in text
    stored = json.loads(game_env.local_storage.getItem(module.WELCOME_BACK_SNAPSHOT_STORAGE_KEY))
    assert stored["machines_built"] == 3


def test_r9_a_lower_machine_count_never_shows_a_negative(game_env):
    module = game_env.module
    game_env.local_storage.setItem(
        module.WELCOME_BACK_SNAPSHOT_STORAGE_KEY,
        json.dumps({"worlds_visited": 1, "achievements_earned": 0, "machines_built": 9, "manual_clicks": 0}),
    )
    module.lifetime_generators_built = 2
    module._show_welcome_back_toast()
    text = game_env.elements["achievement-toast-text"].innerText
    assert "since you were last here" not in text and "-" not in text.split("Welcome back")[1][:4]


def test_r9_junk_snapshot_values_are_ignored(game_env):
    module = game_env.module
    game_env.local_storage.setItem(
        module.WELCOME_BACK_SNAPSHOT_STORAGE_KEY,
        json.dumps({"worlds_visited": 1, "achievements_earned": 0, "machines_built": True, "manual_clicks": "x"}),
    )
    snapshot = module._load_welcome_back_snapshot()
    assert snapshot["machines_built"] is None and snapshot["manual_clicks"] is None
