"""QI-58: resume_note() gives the hub's "Pick up where you stopped" strip one plain line."""


def test_resume_note_names_the_season_and_funds(game_env):
    m = game_env.module
    note = m.resume_note()
    assert note == f"Season {m.state.season}, funds {round(m.state.funds)}"
    m.state.season = 7
    assert m.resume_note().startswith("Season 7")
    assert "\n" not in note and len(note) <= 80
