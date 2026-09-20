"""Improvement Ideas addendum (2026-09-13), §4: optional cultural/usage
notes. Off the main screen by default, toggled by the player, scoped to
rows already unlocked -- same spoiler-avoidance stance the proficiency
tests and bonus sections already take toward locked weeks.
"""


def test_cultural_notes_loaded_from_the_supplementary_file(game_env):
    module = game_env.module
    assert module.CULTURAL_NOTES_BY_SEQUENCE  # the real file has 5 entries
    assert all(isinstance(seq, int) for seq in module.CULTURAL_NOTES_BY_SEQUENCE)
    assert all(note.strip() for note in module.CULTURAL_NOTES_BY_SEQUENCE.values())


def test_the_panel_is_hidden_until_toggled(game_env):
    module = game_env.module
    assert module.cultural_notes_open is False
    assert game_env.elements["cultural-notes-panel"].hidden is True


def test_toggling_opens_and_closes_the_panel(game_env):
    module = game_env.module
    module.on_toggle_cultural_notes()
    assert module.cultural_notes_open is True
    assert game_env.elements["cultural-notes-panel"].hidden is False
    assert "Hide" in game_env.elements["cultural-notes-toggle-button"].innerText

    module.on_toggle_cultural_notes()
    assert module.cultural_notes_open is False
    assert game_env.elements["cultural-notes-panel"].hidden is True


def test_every_weeks_note_is_shown_now_that_nothing_is_locked(game_env):
    """Before L4a removed the row-unlock gate, sequence 17 (FREN152) had a
    cultural note but started locked, so `render_cultural_notes()`'s
    `state.is_row_unlocked()` filter (kept in place per game.py's
    `is_row_unlocked()` docstring, dormant rather than torn out) hid it.
    Sequence 1's note was always shown, being in the FREN151 catch-up zone.
    With every row unlocked from the start, both notes -- and every other
    week's -- render; this is a regression guard that the dormant filter
    genuinely never suppresses anything anymore, not just an absence of the
    old locked-week case."""
    module, state = game_env.module, game_env.state
    assert 1 in module.CULTURAL_NOTES_BY_SEQUENCE
    assert 17 in module.CULTURAL_NOTES_BY_SEQUENCE
    assert state.is_row_unlocked(1) is True
    assert state.is_row_unlocked(17) is True

    module.on_toggle_cultural_notes()
    panel_text = " ".join(
        grandchild.innerText
        for child in game_env.elements["cultural-notes-panel"].children
        for grandchild in child.children
    )
    week_1_note = module.CULTURAL_NOTES_BY_SEQUENCE[1]
    week_17_note = module.CULTURAL_NOTES_BY_SEQUENCE[17]
    assert week_1_note in panel_text
    assert week_17_note in panel_text


def test_a_note_never_grows_a_plant_or_touches_unlock_state(game_env):
    """Purely informational, like the proficiency test and bonus section --
    opening the panel must not be a second, hidden way to make progress."""
    module, state = game_env.module, game_env.state
    stages_before = [p.stage for p in state.plots]
    module.on_toggle_cultural_notes()
    stages_after = [p.stage for p in state.plots]
    assert stages_before == stages_after
