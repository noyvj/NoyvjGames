"""GG-26: the Tundra Tattler headline ticker."""


def _text(game_env):
    return game_env.elements["headline-ticker"].innerText


def test_every_mood_has_headlines_and_all_are_distinct(game_env):
    m = game_env.module
    seen = []
    for mood in m.HEADLINE_MOODS:
        assert m.HEADLINES[mood]
        seen.extend(m.HEADLINES[mood])
    assert len(seen) == len(set(seen))


def test_first_screen_uses_the_start_mood_and_says_fiction(game_env):
    m = game_env.module
    assert m.headline_mood() == "start"
    assert _text(game_env).startswith("\U0001F4F0 The Tundra Tattler (fiction): ")
    assert _text(game_env).endswith(m.HEADLINES["start"][0])


def test_calm_then_melting_then_critical(game_env):
    m = game_env.module
    game_env.advance_round()
    assert m.headline_mood() == "calm"
    for _ in range(10):
        game_env.advance_round()
    assert m.headline_mood() in ("melting", "critical")
    m.region.temperature = 40.0
    m.render()
    assert m.headline_mood() == "critical"
    assert any(line in _text(game_env) for line in m.HEADLINES["critical"])


def test_shield_mood_after_real_protection(game_env):
    m = game_env.module
    game_env.advance_round()
    m.region_b.capacity["preserve"] = 5  # 40% dampening
    m.render()
    assert m.headline_mood() == "shield"


def test_restoring_mood(game_env):
    m = game_env.module
    for _ in range(3):
        game_env.advance_round()
    m.region.temperature = 12.0
    m.region.capacity["preserve"] = 10
    m.region.stabilized_rounds = 3
    m.region_b.temperature = 5.0
    m.region_c.temperature = 5.0
    assert m.headline_mood() == "restoring"


def test_headline_is_deterministic_and_changes_with_the_round(game_env):
    m = game_env.module
    for _ in range(2):
        game_env.advance_round()
    first = m.current_headline()
    assert m.current_headline() == first
    game_env.advance_round()
    assert m.current_headline() != first or len(m.HEADLINES[m.headline_mood()]) == 1


def test_headlines_save_nothing(game_env):
    m = game_env.module
    game_env.advance_round()
    assert "headline" not in str(m.get_state()).lower()


def test_critical_headlines_always_point_at_something_to_do(game_env):
    m = game_env.module
    for line in m.HEADLINES["critical"]:
        lowered = line.lower()
        assert any(word in lowered for word in ("protect", "rescue", "every degree"))


def test_story_switch_covers_the_ticker():
    from pathlib import Path
    page = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
    assert "#headline-ticker" in page.split("data-story-selectors=")[1].split(">")[0]
