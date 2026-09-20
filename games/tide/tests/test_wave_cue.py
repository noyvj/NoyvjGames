"""D4 (planning/TODO.md, Per-game: Tide): a small wave/tide animation cue
tied to the sea-level meter's current percentage, purely decorative.

`#sea-level-wave-cue` is a separate strip from `#sea-level-bar` itself --
game.py only ever sets its `animationDuration` inline style (the CSS
`@keyframes` in style.css never changes), and that must never touch the
meter's own numeric text or width.
"""


def test_wave_cue_element_exists(game_env):
    assert "sea-level-wave-cue" in game_env.elements


def test_wave_cue_duration_is_slowest_at_zero_sea_level(game_env):
    game_env.module.render()
    cue = game_env.elements["sea-level-wave-cue"]
    assert cue.style.animationDuration == "6.00s"


def test_wave_cue_speeds_up_as_sea_level_rises(game_env):
    state = game_env.state
    cue = game_env.elements["sea-level-wave-cue"]

    durations = []
    for sea_level in (0.0, 40.0, 80.0, 120.0, 999999.0):
        state.sea_level = sea_level
        game_env.module.render()
        durations.append(float(cue.style.animationDuration.rstrip("s")))

    # Strictly non-increasing as the fraction climbs, and strictly faster
    # once it actually moves off zero.
    assert durations[0] > durations[1] > durations[2] > durations[3]
    # Fully flooded (fraction clamped to 1.0) sits at the fast end.
    assert durations[4] == durations[3]


def test_wave_cue_duration_clamped_to_fast_end_at_full_meter(game_env):
    game_env.state.sea_level = 10 ** 9
    game_env.module.render()
    cue = game_env.elements["sea-level-wave-cue"]
    assert cue.style.animationDuration == "1.50s"


def test_wave_cue_duration_helper_matches_render(game_env):
    module = game_env.module
    assert module.sea_level_wave_cue_duration(0.0) == module.SEA_LEVEL_WAVE_CUE_MAX_DURATION
    assert module.sea_level_wave_cue_duration(1.0) == module.SEA_LEVEL_WAVE_CUE_MIN_DURATION
    mid = module.sea_level_wave_cue_duration(0.5)
    assert module.SEA_LEVEL_WAVE_CUE_MIN_DURATION < mid < module.SEA_LEVEL_WAVE_CUE_MAX_DURATION


def test_wave_cue_never_touches_meter_text_or_width(game_env):
    state = game_env.state
    display = game_env.elements["sea-level-display"]
    bar = game_env.elements["sea-level-bar"]

    state.sea_level = 0.0
    game_env.module.render()
    text_before, width_before = display.innerText, bar.style.width

    state.sea_level = 45.0
    game_env.module.render()
    # The meter's own readouts change with sea_level exactly as before --
    # the wave cue rides alongside them, it doesn't replace or gate them.
    assert display.innerText != text_before
    assert bar.style.width != width_before
    assert "Sea level: 45" in display.innerText
    assert bar.style.width == f"{state.sea_level_fraction() * 100:.0f}%"


def test_wave_cue_survives_missing_element_gracefully(game_env):
    # Mirrors this game's existing "if el is not None" guards elsewhere --
    # render() shouldn't blow up if the decorative element isn't present
    # (e.g. an older cached page).
    del game_env.elements["sea-level-wave-cue"]
    game_env.module.render()
