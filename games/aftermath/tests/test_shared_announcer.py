"""B-7: the game speaks through shared/announcer.js when the page loads it, else through its own live region."""

def test_announcements_go_through_the_shared_announcer_when_the_page_has_it(game_env):
    import sys
    import types

    said = []
    sys.modules["js"].window = types.SimpleNamespace(NoyvjAnnounce=types.SimpleNamespace(say=said.append))
    try:
        game_env.module.announce("Flood hit, 42 damage, 18 prevented")
        assert said == ["Flood hit, 42 damage, 18 prevented"]
        assert game_env.elements["event-announcer"].innerText == ""
        game_env.module.announce("")                       # clearing never speaks
        assert said == ["Flood hit, 42 damage, 18 prevented"]
    finally:
        del sys.modules["js"].window


def test_without_the_shared_announcer_the_games_own_region_still_speaks(game_env):
    game_env.module.announce("Flood hit")
    assert game_env.elements["event-announcer"].innerText == "Flood hit"
