"""Tests for the "What's New" changelog panel (site-wide goal,
planning/TODO.md, origin K16: "Per-game in-game changelog panel, for every
game"). Mirrors test_achievements.py's shape: catalog/JSON sanity first,
then the in-game toggle/panel behavior, driven through the real toggle
button rather than poking module globals directly.
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
        datetime.date.fromisoformat(entry["date"])
        assert isinstance(entry["entry"], str) and entry["entry"].strip()


def test_no_duplicate_entries(game_env):
    module = game_env.module
    seen = [(entry["date"], entry["entry"]) for entry in module.CHANGELOG]
    assert len(seen) == len(set(seen))


# --- panel closed by default -------------------------------------------

def test_changelog_panel_starts_closed(game_env):
    assert game_env.elements["changelog-panel"].hidden is True
    assert game_env.module.changelog_open is False


# --- toggle behavior -----------------------------------------------------

def test_toggle_opens_and_closes_the_panel(game_env):
    game_env.toggle_changelog()
    assert game_env.module.changelog_open is True
    assert game_env.elements["changelog-panel"].hidden is False

    game_env.toggle_changelog()
    assert game_env.module.changelog_open is False
    assert game_env.elements["changelog-panel"].hidden is True


def test_toggle_button_label_reflects_open_state(game_env):
    toggle = game_env.elements["changelog-toggle-button"]
    assert toggle.innerText == "\U0001F4CB What's New"

    game_env.toggle_changelog()
    assert toggle.innerText == "Hide What's New"

    game_env.toggle_changelog()
    assert toggle.innerText == "\U0001F4CB What's New"


def test_open_panel_renders_one_card_per_entry(game_env):
    module = game_env.module
    game_env.toggle_changelog()
    panel = game_env.elements["changelog-panel"]
    assert len(panel.children) == len(module.CHANGELOG)


def test_open_panel_lists_entries_newest_first(game_env):
    module = game_env.module
    game_env.toggle_changelog()
    panel = game_env.elements["changelog-panel"]
    dates_in_panel = [card.children[0].innerText for card in panel.children]
    expected = sorted((entry["date"] for entry in module.CHANGELOG), reverse=True)
    assert dates_in_panel == expected


def test_open_panel_shows_the_real_entry_text(game_env):
    module = game_env.module
    game_env.toggle_changelog()
    panel = game_env.elements["changelog-panel"]
    rendered_texts = {card.children[1].innerText for card in panel.children}
    expected_texts = {entry["entry"] for entry in module.CHANGELOG}
    assert rendered_texts == expected_texts


def test_closing_the_panel_does_not_break_the_next_open(game_env):
    game_env.toggle_changelog()
    game_env.toggle_changelog()
    game_env.toggle_changelog()
    panel = game_env.elements["changelog-panel"]
    assert len(panel.children) == len(game_env.module.CHANGELOG)
