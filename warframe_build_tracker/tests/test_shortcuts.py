"""Batch A #11: keyboard shortcuts and the ? cheat sheet."""

from .fakes import FakeKeyEvent
from .helpers import all_text, click, known_state


def _press(game_env, key, **kwargs):
    event = FakeKeyEvent(key, **kwargs)
    game_env.js.document.dispatch("keydown", event)
    return event


def test_slash_focuses_search_and_is_consumed(game_env):
    known_state(game_env.module)
    event = _press(game_env, "/")
    assert game_env.elements["search-input"].focused is True
    assert event.default_prevented is True


def test_h_toggles_hide_completed(game_env):
    m = game_env.module
    known_state(m)
    assert m.state["prefs"]["hide_complete"] is False
    _press(game_env, "h")
    assert m.state["prefs"]["hide_complete"] is True
    assert game_env.elements["hide-complete-toggle"].checked is True
    _press(game_env, "H")
    assert m.state["prefs"]["hide_complete"] is False


def test_s_opens_the_shopping_list(game_env):
    known_state(game_env.module)
    assert game_env.elements["shopping-details"].open is False
    _press(game_env, "s")
    assert game_env.elements["shopping-details"].open is True


def test_question_mark_toggles_the_overlay_and_escape_closes_it(game_env):
    known_state(game_env.module)
    overlay = game_env.elements["shortcut-overlay"]
    overlay.hidden = True
    _press(game_env, "?")
    assert overlay.hidden is False
    _press(game_env, "Escape")
    assert overlay.hidden is True
    assert _press(game_env, "Escape").default_prevented is False  # nothing to close
    click(game_env.elements["shortcut-help-button"])
    assert overlay.hidden is False
    click(game_env.elements["shortcut-close-button"])
    assert overlay.hidden is True


def test_cheat_sheet_lists_every_shortcut(game_env):
    text = all_text(game_env.elements["shortcut-list"])
    for key in ("/", "h", "s", "?", "Esc"):
        assert key in text


def test_ignored_while_typing_and_with_browser_modifiers(game_env):
    m = game_env.module
    known_state(m)
    for tag in ("INPUT", "TEXTAREA", "SELECT"):
        event = _press(game_env, "h", tag=tag)
        assert event.default_prevented is False
    assert m.state["prefs"]["hide_complete"] is False
    for mod in ({"ctrl": True}, {"meta": True}, {"alt": True}):
        event = _press(game_env, "s", **mod)
        assert event.default_prevented is False
    assert game_env.elements["shopping-details"].open is False
    assert _press(game_env, "x").default_prevented is False
