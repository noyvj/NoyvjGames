"""L-26: player titles rise with the practice score (derived from the ledger, never saved)."""


def test_titles_follow_the_thresholds(game_env):
    module = game_env.module
    assert module.player_title(0) == ("Apprenti", "Jardinier", 25)
    assert module.player_title(24)[0] == "Apprenti"
    assert module.player_title(25) == ("Jardinier", "Fermier", 150)
    assert module.player_title(150)[0] == "Fermier"
    assert module.player_title(599)[0] == "Fermier"
    assert module.player_title(600) == ("Maître de Ferme", None, None)
    assert module.player_title(10**6)[0] == "Maître de Ferme"


def test_top_title_is_reachable_with_the_capped_ledger(game_env):
    module = game_env.module
    assert module.PLAYER_TITLES[-1][0] <= module.PRACTICE_MODE_CAP * len(module.PRACTICE_MODES)
    thresholds = [needed for needed, _ in module.PLAYER_TITLES]
    assert thresholds == sorted(thresholds) and thresholds[0] == 0


def test_text_and_tile_update_with_practice(game_env):
    module = game_env.module
    module.render()
    assert game_env.elements["player-title-display"].innerText == "Title: Apprenti (next: Jardinier at 25)"
    module.practice_ledger["blitz"]["points"] = 30
    module.render_practice_score()
    assert game_env.elements["player-title-display"].innerText == "Title: Jardinier (next: Fermier at 150)"
    for mode in ("blitz", "racer", "dash", "cafe", "conjugation"):
        if mode in module.practice_ledger:
            module.practice_ledger[mode]["points"] = 100
    module.practice_ledger["gender"]["points"] = 100
    module.render_practice_score()
    assert game_env.elements["player-title-display"].innerText.startswith("Title: ")


def test_title_is_not_saved(game_env):
    module = game_env.module
    assert "title" not in " ".join(module.get_state().keys()).lower()
