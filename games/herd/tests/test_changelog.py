"""Tests for the K16 "What's New" changelog panel (planning/TODO.md,
site-wide goal): the changelog.json catalog, its newest-first ordering, and
the in-game toggle/panel. Same idiom as test_achievements.py, minus any
earned/unearned state -- a changelog entry is just curated highlight text,
not a checkable condition.
"""

import re


def test_changelog_loads_with_a_reasonable_count(game_env):
    module = game_env.module
    assert 1 <= len(module.CHANGELOG) <= 30


def test_every_entry_has_a_date_and_nonempty_text(game_env):
    for entry in game_env.module.CHANGELOG:
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", entry["date"])
        assert entry["entry"].strip()


def test_changelog_is_sorted_newest_first(game_env):
    dates = [entry["date"] for entry in game_env.module.CHANGELOG]
    assert dates == sorted(dates, reverse=True)


def test_changelog_panel_is_hidden_by_default(game_env):
    assert game_env.elements["changelog-panel"].hidden is True


def test_toggle_opens_and_closes_the_panel(game_env):
    game_env.toggle_changelog()
    assert game_env.elements["changelog-panel"].hidden is False
    game_env.toggle_changelog()
    assert game_env.elements["changelog-panel"].hidden is True


def test_toggle_button_shows_entry_count_while_closed(game_env):
    module = game_env.module
    text = game_env.elements["changelog-toggle-button"].innerText
    assert f"({len(module.CHANGELOG)})" in text


def _all_texts(element):
    texts = [element.innerText]
    for child in element.children:
        texts.extend(_all_texts(child))
    return texts


def test_panel_renders_every_entrys_date_and_text(game_env):
    module = game_env.module
    game_env.toggle_changelog()
    panel = game_env.elements["changelog-panel"]
    rendered = " ".join(text for row in panel.children for text in _all_texts(row))
    for entry in module.CHANGELOG:
        assert entry["date"] in rendered
        assert entry["entry"] in rendered


def test_panel_does_not_render_while_closed(game_env):
    panel = game_env.elements["changelog-panel"]
    assert panel.innerHTML == "" or len(panel.children) == 0


def test_checking_changelog_never_mutates_game_state(game_env):
    module = game_env.module
    game_env.grow_herd()
    before = module.get_state()
    game_env.toggle_changelog()
    game_env.toggle_changelog()
    after = module.get_state()
    assert before == after
