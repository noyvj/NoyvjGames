"""R-23: the sentence under the title reacts to how the session is going."""


def test_default_line_at_the_start(game_env):
    m = game_env.module
    m.render()
    assert game_env.elements["tagline-display"].innerText == m.TAGLINE_DEFAULT


def test_methane_pressure_changes_it(game_env):
    m = game_env.module
    game_env.farm.methane = m.PRESSURE_SCALE * (m.PRESSURE_CALLOUT_THRESHOLD + 0.05)
    m.render()
    assert game_env.elements["tagline-display"].innerText == m.TAGLINE_PRESSURE


def test_half_decoupled_beats_pressure(game_env):
    m = game_env.module
    game_env.farm.methane = m.PRESSURE_SCALE
    game_env.farm.decoupling_investment["capture"] = 8
    m.render()
    assert game_env.farm.decoupled_fraction() >= m.HALF_DECOUPLED_CALLOUT_THRESHOLD
    assert game_env.elements["tagline-display"].innerText == m.TAGLINE_HALF


def test_certified_wins_and_it_never_changes_the_farm(game_env):
    m = game_env.module
    game_env.farm.certified = True
    before = (game_env.farm.funds, game_env.farm.methane, game_env.farm.round_number)
    m.render()
    assert game_env.elements["tagline-display"].innerText == m.TAGLINE_CERTIFIED
    assert (game_env.farm.funds, game_env.farm.methane, game_env.farm.round_number) == before


def test_html_default_matches_the_module_default():
    import pathlib
    html = (pathlib.Path(__file__).resolve().parent.parent / "index.html").read_text()
    from_module = "Grow a farm. Herd size and methane emissions are coupled by default"
    assert f'id="tagline-display" class="tagline">{from_module}' in html
