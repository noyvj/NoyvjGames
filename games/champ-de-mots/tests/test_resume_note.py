"""QI-58: resume_note() gives the hub's "Pick up where you stopped" strip one plain line."""


def test_resume_note_names_the_day_and_how_many_plots_are_ready(game_env):
    m = game_env.module
    note = m.resume_note()
    assert note.startswith("Day 0, ") and note.endswith("ready for water")
    assert str(len(m.state.due_plots())) in note
    assert "\n" not in note and len(note) <= 80


def test_resume_note_singular(game_env):
    m = game_env.module
    m.state.due_plots = lambda: [object()]
    assert m.resume_note() == "Day 0, 1 plot ready for water"
