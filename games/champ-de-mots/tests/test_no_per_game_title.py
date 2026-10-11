"""AN-16: the per-game player title (L-26) was replaced by account-wide titles on the profile page.
The practice score stays; nothing about a title is drawn, computed or saved here any more."""


def test_per_game_title_code_is_gone(game_env):
    module = game_env.module
    assert not hasattr(module, "PLAYER_TITLES") and not hasattr(module, "player_title")
    assert not hasattr(module, "player_title_text")


def test_practice_score_line_still_renders_without_a_title(game_env):
    module = game_env.module
    module.render()
    assert game_env.elements["practice-score-display"].innerText == "Practice score: 0"
    module.practice_ledger["blitz"]["points"] = 30
    module.render_practice_score()
    assert game_env.elements["practice-score-display"].innerText == "Practice score: 30"
    assert "player-title-display" not in game_env.elements


def test_no_title_in_the_saved_state_or_the_pages():
    import pathlib
    here = pathlib.Path(__file__).resolve().parent.parent
    for name in ("index.html", "pc.html", "pc-config.json"):
        assert "player-title" not in (here / name).read_text(encoding="utf-8"), name
