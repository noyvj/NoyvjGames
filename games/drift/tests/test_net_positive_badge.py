"""Addendum I19: turn the net-positive turning-point message into a
small persistent badge in the top status readouts, in addition to (not
replacing) the existing one-off callout in the Integration section --
so the milestone stays visible even after a player scrolls past that
callout.
"""


def test_net_positive_badge_text_none_before_turning_point(game_env):
    assert game_env.module.net_positive_badge_text(game_env.region) is None


def test_net_positive_badge_text_after_turning_point(game_env):
    region = game_env.region
    region.net_positive_round = 9
    text = game_env.module.net_positive_badge_text(region)
    assert "round 9" in text
    assert "Net-positive" in text


def test_render_hides_badge_before_turning_point(game_env):
    game_env.module.render()
    assert game_env.elements["net-positive-badge"].hidden is True


def test_render_shows_badge_after_turning_point(game_env):
    game_env.region.net_positive_round = 3
    game_env.module.render()
    el = game_env.elements["net-positive-badge"]
    assert el.hidden is False
    assert "round 3" in el.innerText
