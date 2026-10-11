"""Round-4 visual batch (2026-10-11): building pop (GI-14), strain heartbeat (GI-19),
animation speed (I-21) and density (I-19) settings."""

from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _read(name):
    return (GAME_DIR / name).read_text(encoding="utf-8")


# --- GI-14: building pop ------------------------------------------------------

def test_a_newly_revealed_building_pops_first(game_env):
    assert game_env.module.building_to_pop(1, 2, 7) == 1
    assert game_env.module.building_to_pop(3, 4, 0) == 3


def test_otherwise_the_pops_take_turns_along_the_skyline(game_env):
    picks = [game_env.module.building_to_pop(3, 3, n) for n in range(6)]
    assert picks == [0, 1, 2, 0, 1, 2]


def test_the_pop_index_never_leaves_the_six_authored_buildings(game_env):
    assert game_env.module.building_to_pop(6, 6, 40) in range(6)
    assert game_env.module.building_to_pop(0, 0, 3) == 0


def test_an_investment_pops_a_building_and_the_class_is_removed_later(game_env):
    game_env.invest("housing")
    building = game_env.elements["region-visual-building-a"]
    assert building.classList.contains("building-pop-a")
    game_env.timers.flush()
    assert not building.classList.contains("building-pop-a")


def test_a_second_pop_before_the_first_ends_uses_the_other_class(game_env):
    game_env.invest("housing")
    game_env.invest("housing")  # capacity 20 reveals the second building, which pops
    assert game_env.elements["region-visual-building-b"].classList.contains("building-pop-a")
    game_env.invest("housing")
    game_env.invest("housing")  # pops cycle: back to a building already carrying a class
    classes = [
        game_env.elements[f"region-visual-building-{k}"].classList
        for k in ("a", "b")
    ]
    assert any(c.contains("building-pop-b") for c in classes)


def test_a_refused_investment_pops_nothing(game_env):
    game_env.region.funds = 0
    game_env.invest("housing")
    for key in "abcdef":
        classes = game_env.elements[f"region-visual-building-{key}"].classList
        assert not classes.contains("building-pop-a") and not classes.contains("building-pop-b")


def test_policies_and_autopilot_do_not_pop_buildings(game_env):
    game_env.region.funds = 500
    game_env.elements["policy-credentialing-button"].dispatch("click", None)
    assert game_env.module.building_pop_count == 0


# --- GI-19: strain heartbeat --------------------------------------------------

def test_heartbeat_quickens_as_strain_level_rises(game_env):
    seconds = game_env.module.strain_heartbeat_seconds
    assert seconds("stable") > seconds("strained") > seconds("critical")
    assert seconds("nonsense") == seconds("stable")


def test_render_puts_the_heartbeat_on_the_bar_and_the_readout(game_env):
    game_env.module.render()
    bar = game_env.elements["strain-bar"]
    text = game_env.elements["strain-display"]
    assert "strain-heartbeat" in bar.className and "strain-heartbeat-text" in text.className
    assert "6.00s" in bar.style.animationDuration and "6.00s" in text.style.animationDuration


def test_heartbeat_speeds_up_in_critical_strain_and_calms_after(game_env):
    region = game_env.region
    region.total_arrivals = 100.0
    game_env.module.render()
    assert region.strain_level() == "critical"
    assert "1.20s" in game_env.elements["strain-bar"].style.animationDuration
    region.capacity["housing"] = 500.0
    game_env.module.render()
    assert region.strain_level() == "stable"
    assert "6.00s" in game_env.elements["strain-bar"].style.animationDuration


def test_durations_follow_the_animation_speed_scale(game_env):
    assert game_env.module.scaled_seconds(2.5) == "calc(2.50s * var(--drift-anim-scale, 1))"


# --- I-21 / I-19: settings ----------------------------------------------------

def test_animation_speed_and_density_controls_exist_with_their_hooks():
    html = _read("index.html")
    for speed in ("slow", "normal", "fast", "off"):
        assert f'id="anim-speed-{speed}-button"' in html and f'data-speed="{speed}"' in html
    for density in ("comfortable", "compact"):
        assert f'id="density-{density}-button"' in html and f'data-density="{density}"' in html
    assert 'id="anim-speed-group"' in html and 'id="density-group"' in html


def test_settings_js_stores_validates_and_resets_the_two_choices():
    js = _read("settings.js")
    assert '"drift-anim-speed"' in js and '"drift-density"' in js
    assert "--drift-anim-scale" in js and "data-anim-speed" in js and "data-density" in js
    # unknown stored values fall back to the defaults
    assert 'readChoice(ANIM_SPEED_KEY, Object.keys(ANIM_SCALES), "normal")' in js
    assert 'readChoice(DENSITY_KEY, DENSITIES, "comfortable")' in js
    # Reset to Default puts both back
    reset_block = js[js.index("settingsResetButton.addEventListener"):]
    assert 'applyAnimSpeed("normal")' in reset_block and 'applyDensity("comfortable")' in reset_block


def test_css_stops_the_animations_when_speed_is_off_and_respects_reduce_motion():
    css = _read("style.css")
    assert 'html[data-anim-speed="off"] .arrival-dot' in css
    assert "animation: none !important" in css
    assert 'html[data-density="compact"] .section' in css
    assert ".reduce-motion *" in css  # the global override covers the new animations too
