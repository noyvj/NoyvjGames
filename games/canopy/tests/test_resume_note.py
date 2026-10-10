"""QI-58: resume_note() gives the hub's "Pick up where you stopped" strip one plain line."""


def test_resume_note_is_one_short_plain_line(game_env):
    note = game_env.module.resume_note()
    assert note.endswith(str(round(game_env.module.standing_forest_value())))
    assert "plots" in note and "\n" not in note and len(note) <= 80
