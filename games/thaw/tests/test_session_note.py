"""G-22: the round-counter note with an estimated session length and a safe-to-save nudge."""


def _note(game_env):
    return game_env.elements["session-note"].innerText


def test_first_round_estimates_remaining_rounds(game_env):
    text = _note(game_env)
    assert "Round 1 of a typical 20-round session" in text
    assert "20 rounds (around 20 minutes) to go" in text
    assert "save" not in text.lower()


def test_estimate_counts_down_as_rounds_pass(game_env):
    game_env.advance_round()
    assert "19 rounds (around 19 minutes) to go" in _note(game_env)


def test_last_round_uses_singular(game_env):
    for _ in range(19):
        game_env.advance_round()
    assert "about 1 round (around 1 minute) to go" in _note(game_env)


def test_save_nudge_every_fifth_round_only(game_env):
    for played in range(1, 11):
        game_env.advance_round()
        has_nudge = "Good moment to save" in _note(game_env)
        assert has_nudge == (played % 5 == 0), played


def test_past_the_typical_length_says_it_is_a_fine_place_to_stop(game_env):
    for _ in range(20):
        game_env.advance_round()
    assert "past a typical session of about 20 rounds" in _note(game_env)
    assert "progress is kept if you save" in _note(game_env)


def test_long_game_stretches_the_estimate(game_env):
    assert game_env.module.set_long_game(True)
    game_env.module.render()
    assert game_env.module.session_target_rounds() == 50
    assert "typical 50-round session" in _note(game_env)


def test_hold_the_line_has_its_own_note(game_env):
    assert game_env.module.set_hold_the_line(True)
    game_env.module.render()
    assert "Hold the Line run usually lasts" in _note(game_env)


def test_note_never_blames_or_threatens(game_env):
    for _ in range(12):
        game_env.advance_round()
        text = _note(game_env).lower()
        for bad in ("lose", "lost", "failed", "hurry"):
            assert bad not in text
