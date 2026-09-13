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


def test_only_unlocked_weeks_notes_are_shown(game_env):
    """Sequence 17 (FREN152) has a cultural note in the real supplementary
    file but starts locked; sequence 1 (FREN151, catch-up zone) also has
    one and is open from the start."""
    module, state = game_env.module, game_env.state
    assert 1 in module.CULTURAL_NOTES_BY_SEQUENCE
    assert 17 in module.CULTURAL_NOTES_BY_SEQUENCE
    assert state.is_row_unlocked(1) is True
    assert state.is_row_unlocked(17) is False

    module.on_toggle_cultural_notes()
    panel_text = " ".join(
        grandchild.innerText
        for child in game_env.elements["cultural-notes-panel"].children
        for grandchild in child.children
    )
    week_1_note = module.CULTURAL_NOTES_BY_SEQUENCE[1]
    week_17_note = module.CULTURAL_NOTES_BY_SEQUENCE[17]
    assert week_1_note in panel_text
    assert week_17_note not in panel_text


def test_a_note_never_grows_a_plant_or_touches_unlock_state(game_env):
    """Purely informational, like the proficiency test and bonus section --
    opening the panel must not be a second, hidden way to make progress."""
    module, state = game_env.module, game_env.state
    stages_before = [p.stage for p in state.plots]
    module.on_toggle_cultural_notes()
    stages_after = [p.stage for p in state.plots]
    assert stages_before == stages_after
