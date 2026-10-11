"""GG-15: the snow hare and the arctic fox."""


def _text(game_env):
    return game_env.elements["mascots"].innerHTML


def test_both_mascots_speak_from_the_first_round(game_env):
    html = _text(game_env)
    assert "Hare:" in html and "Fox:" in html
    assert "mascot--calm" in html


def test_pose_follows_the_mood(game_env):
    m = game_env.module
    game_env.advance_round()
    assert "mascot--calm" in _text(game_env)
    m.region.temperature = 12.0
    m.region.melt_started_round = 2
    m.render()
    assert m.headline_mood() == "melting"
    assert "mascot--shiver" in _text(game_env)
    m.region.temperature = 25.0
    m.region.counterfactual_temperature = 40.0
    m.region.melt_started_round = 2
    m.render()
    assert m.headline_mood() == "critical"
    assert "mascot--faint" in _text(game_env)


def test_cheer_when_protection_is_up(game_env):
    m = game_env.module
    game_env.advance_round()
    m.region.funds = 1000
    for _ in range(4):
        game_env.invest("preserve")
    assert m.headline_mood() == "shield"
    assert "mascot--cheer" in _text(game_env)


def test_every_fourth_round_they_bicker(game_env):
    m = game_env.module
    normal = m.mascot_lines()
    for _ in range(4):
        game_env.advance_round()
    assert m.region.round_number == 5
    bicker = m.mascot_lines()
    assert bicker != normal
    assert {who for who, _t in bicker} == {"Hare", "Fox"}
    assert bicker in [list(pair) for pair in m.MASCOT_BICKER]


def test_lines_are_deterministic(game_env):
    m = game_env.module
    for _ in range(6):
        assert m.mascot_lines() == m.mascot_lines()
        game_env.advance_round()


def test_every_mood_has_a_pair_and_a_pose(game_env):
    m = game_env.module
    for mood in m.HEADLINE_MOODS:
        assert mood in m.MASCOT_LINES and mood in m.MASCOT_POSES
        assert [who for who, _t in m.MASCOT_LINES[mood]] == ["Hare", "Fox"]
        assert m.MASCOT_POSES[mood] in m.MASCOT_FACE


def test_the_critical_lines_point_at_something_to_do(game_env):
    m = game_env.module
    joined = " ".join(text.lower() for _who, text in m.MASCOT_LINES["critical"])
    assert "helping" in joined or "rescue" in joined or "protection" in joined
    for mood, pair in m.MASCOT_LINES.items():
        for _who, text in pair:
            for word in ("hopeless", "doomed", "give up", "nothing matters"):
                assert word not in text.lower()


def test_text_is_escaped_and_nothing_is_saved(game_env):
    m = game_env.module
    assert "<script" not in _text(game_env)
    assert "mascot" not in str(m.get_state())


def test_story_switch_selector_and_setting_hook_exist(game_env):
    from pathlib import Path

    page = (Path(__file__).resolve().parent.parent / "index.html").read_text()
    assert "#mascots" in page.split("data-story-selectors=")[1].split(">")[0]
    css = (Path(__file__).resolve().parent.parent / "style.css").read_text()
    assert 'html[data-hide-mascots="true"] .mascots' in css
    js = (Path(__file__).resolve().parent.parent / "settings.js").read_text()
    assert "thaw-hide-mascots" in js
