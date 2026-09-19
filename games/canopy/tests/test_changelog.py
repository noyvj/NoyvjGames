"""Tests for the "What's New" changelog panel (site-wide goal,
planning/TODO.md, origin K16): Canopy's own changelog.json catalog and the
in-game toggle/panel. Same shape as test_achievements.py's own coverage of
its sibling panel."""


def _all_texts(element):
    texts = [element.innerText]
    for child in element.children:
        texts.extend(_all_texts(child))
    return texts


# --- the catalog itself -----------------------------------------------

def test_changelog_loads_from_json_with_a_reasonable_count(game_env):
    module = game_env.module
    assert 1 <= len(module.CHANGELOG) <= 30


def test_every_entry_has_a_date_and_text(game_env):
    module = game_env.module
    for entry in module.CHANGELOG:
        assert entry["date"]
        assert entry["entry"]


def test_entries_are_authored_newest_first_in_the_json(game_env):
    """changelog.json is hand-authored newest-first already -- the panel
    trusts that order rather than re-sorting it (same posture ACHIEVEMENTS
    takes toward achievements.json's own order)."""
    module = game_env.module
    dates = [entry["date"] for entry in module.CHANGELOG]
    assert dates == sorted(dates, reverse=True)


# --- the toggle + panel --------------------------------------------------

def test_panel_is_hidden_until_toggled(game_env):
    assert game_env.module.changelog_open is False
    assert game_env.elements["changelog-panel"].hidden is True


def test_toggling_opens_and_closes_the_panel(game_env):
    module = game_env.module
    module.on_toggle_changelog()
    assert module.changelog_open is True
    assert game_env.elements["changelog-panel"].hidden is False
    assert "Hide" in game_env.elements["changelog-toggle-button"].innerText

    module.on_toggle_changelog()
    assert module.changelog_open is False
    assert game_env.elements["changelog-panel"].hidden is True


def test_toggle_button_is_wired_up_by_setup(game_env):
    button = game_env.elements["changelog-toggle-button"]
    assert "click" in button._listeners
    assert len(button._listeners["click"]) == 1


def test_toggle_helper_dispatches_the_same_click(game_env):
    game_env.toggle_changelog()
    assert game_env.module.changelog_open is True


def test_panel_lists_every_entry_with_date_and_text(game_env):
    module = game_env.module
    module.on_toggle_changelog()
    texts = _all_texts(game_env.elements["changelog-panel"])
    for entry in module.CHANGELOG:
        assert any(entry["date"] in text for text in texts)
        assert any(entry["entry"] in text for text in texts)


def test_panel_shows_entries_newest_first(game_env):
    module = game_env.module
    module.on_toggle_changelog()
    panel = game_env.elements["changelog-panel"]
    rendered_dates = [
        child.children[0].innerText for child in panel.children if child.children
    ]
    assert rendered_dates == [entry["date"] for entry in module.CHANGELOG]


def test_render_keeps_the_open_panel_live(game_env):
    """Pins that update_changelog_display() is wired into render() (called
    on every tick/action), not only into on_toggle_changelog() -- mirrors
    test_achievements.py's own liveness coverage for its panel."""
    module = game_env.module
    module.on_toggle_changelog()
    game_env.select(0)
    game_env.clear()
    assert game_env.elements["changelog-panel"].hidden is False
