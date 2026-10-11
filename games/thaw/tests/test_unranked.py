"""FY-32: runs that use custom rules are marked unranked and kept out of the community comparison."""
import json


def _open_panel(game_env):
    game_env.toggle_community_compare()
    return game_env.elements["community-compare-panel"].innerHTML


def test_standard_run_is_ranked(game_env):
    game = game_env.module
    assert game.unranked_reasons() == []
    assert game.run_unranked() is False
    assert game.unranked_note() == ""
    assert "unranked" not in game.get_state()
    assert game.COMMUNITY_COMPARE_FALLBACK in _open_panel(game_env)


def test_long_game_is_unranked(game_env):
    game = game_env.module
    assert game.set_long_game(True)
    assert game.unranked_reasons() == ["the long game"]
    assert game.get_state()["unranked"] is True
    assert "Unranked run" in game.unranked_note()
    assert "kept out of the community comparison" in game.long_game_text()


def test_hold_the_line_is_unranked(game_env):
    game = game_env.module
    assert game.set_hold_the_line(True)
    assert game.unranked_reasons() == ["Hold the Line"]
    assert "unranked" in game.hold_line_status().lower()
    assert game.get_state()["unranked"] is True


def test_hard_mode_and_custom_preset_do_not_count(game_env):
    game = game_env.module
    assert game.set_hard_mode(True)
    game.custom_preset = {"output": 1, "preserve": 1, "monitor": 1}
    assert game.run_unranked() is False
    assert "unranked" not in game.get_state()


def test_unranked_panel_skips_the_percentile_request(game_env, monkeypatch):
    game = game_env.module
    game.set_long_game(True)
    calls = []
    monkeypatch.setattr(game, "_request_community_comparison", lambda: calls.append(1))
    html = _open_panel(game_env)
    assert "Unranked run" in html
    assert calls == []


def test_ranked_panel_still_asks(game_env, monkeypatch):
    game = game_env.module
    calls = []
    monkeypatch.setattr(game, "_request_community_comparison", lambda: calls.append(1))
    _open_panel(game_env)
    assert calls == [1]


def test_marker_round_trips_without_being_trusted(game_env):
    game = game_env.module
    game.set_long_game(True)
    state = json.loads(json.dumps(game.get_state()))
    game.set_long_game(False) if game.can_toggle_long_game() else None
    game.load_state(state)
    assert game.long_game is True
    assert game.run_unranked() is True
    # a forged marker on a standard save changes nothing
    standard = json.loads(json.dumps(game.get_state()))
    standard.pop("long_game", None)
    standard.pop("unranked", None)
    game.load_state(standard)
    forged = dict(standard, unranked=True)
    game.load_state(forged)
    assert game.run_unranked() is False
    assert "unranked" not in game.get_state()
