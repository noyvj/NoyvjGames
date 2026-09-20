"""Tests for the "What's New" changelog panel (site-wide goal,
planning/TODO.md, origin K16: "Per-game in-game changelog panel, for every
game"). Mirrors test_achievements.py's shape: catalog/JSON sanity first,
then the in-game toggle/panel behavior, driven through the module's own
on_toggle_changelog() the same way test_achievements.py drives
on_toggle_achievements() directly rather than through a GameEnv helper.

Unlike the achievements panel (a tiered summary built from several nested
elements), render_changelog() renders a flat list -- one <p class=
"changelog-row"> per entry, "{date} — {entry}" -- reusing this game's own
dashboard-row idiom (see game.py's own build note on render_changelog())
rather than the two-part card shape some other hub games use for their own
changelog panel. Tests below are written against that flat shape.
"""

import datetime


# --- the catalog itself -----------------------------------------------


def test_changelog_loads_from_json_with_a_reasonable_count(game_env):
    module = game_env.module
    assert 1 <= len(module.CHANGELOG) <= 25


def test_every_entry_has_a_real_date_and_nonempty_text(game_env):
    module = game_env.module
    for entry in module.CHANGELOG:
        assert set(entry.keys()) == {"date", "entry"}
        # Raises ValueError on a malformed date (e.g. a typo'd "2026-13-01")
        # rather than letting a bad string silently reach the panel.
        datetime.date.fromisoformat(entry["date"])
        assert isinstance(entry["entry"], str) and entry["entry"].strip()


def test_no_duplicate_entries(game_env):
    module = game_env.module
    seen = [(entry["date"], entry["entry"]) for entry in module.CHANGELOG]
    assert len(seen) == len(set(seen))


# --- panel closed by default -------------------------------------------


def test_changelog_panel_starts_closed(game_env):
    module = game_env.module
    assert module.changelog_open is False
    assert game_env.elements["changelog-panel"].hidden is True


# --- toggle behavior -----------------------------------------------------


def test_toggling_opens_and_closes_the_panel(game_env):
    module = game_env.module
    module.on_toggle_changelog()
    assert module.changelog_open is True
    assert game_env.elements["changelog-panel"].hidden is False

    module.on_toggle_changelog()
    assert module.changelog_open is False
    assert game_env.elements["changelog-panel"].hidden is True


def test_toggle_button_label_reflects_open_state(game_env):
    module = game_env.module
    toggle = game_env.elements["changelog-toggle-button"]

    module.on_toggle_changelog()
    assert toggle.innerText == "Hide What's New"

    module.on_toggle_changelog()
    assert toggle.innerText == "📋 What's New"


def test_open_panel_renders_one_row_per_entry(game_env):
    module = game_env.module
    module.on_toggle_changelog()
    panel = game_env.elements["changelog-panel"]
    assert len(panel.children) == len(module.CHANGELOG)
    for row in panel.children:
        assert row.className == "changelog-row"


def test_open_panel_lists_entries_newest_first(game_env):
    module = game_env.module
    module.on_toggle_changelog()
    panel = game_env.elements["changelog-panel"]
    dates_in_panel = [row.innerText.split(" — ")[0] for row in panel.children]
    expected = sorted((entry["date"] for entry in module.CHANGELOG), reverse=True)
    assert dates_in_panel == expected


def test_open_panel_shows_the_real_entry_text(game_env):
    module = game_env.module
    module.on_toggle_changelog()
    panel = game_env.elements["changelog-panel"]
    rendered_texts = {row.innerText.split(" — ", 1)[1] for row in panel.children}
    expected_texts = {entry["entry"] for entry in module.CHANGELOG}
    assert rendered_texts == expected_texts


def test_closing_the_panel_does_not_poison_the_next_open(game_env):
    module = game_env.module
    module.on_toggle_changelog()
    module.on_toggle_changelog()
    module.on_toggle_changelog()
    panel = game_env.elements["changelog-panel"]
    assert len(panel.children) == len(module.CHANGELOG)


def test_toggling_the_panel_never_mutates_farm_state(game_env):
    module, state = game_env.module, game_env.state
    stages_before = [p.stage for p in state.plots]
    module.on_toggle_changelog()
    assert [p.stage for p in state.plots] == stages_before
