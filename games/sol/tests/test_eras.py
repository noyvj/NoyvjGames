"""A-21: prestige Eras (a name per level band, a static colour shift and a tagline)."""

from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _set_level(env, level):
    m = env.module
    m.prestige_level = level
    m.update_win_display()


def test_era_bands(game_env):
    m = game_env.module
    names = {lvl: m.era_for_level(lvl)["id"] for lvl in range(0, 12)}
    assert names[0] == "pioneer"
    assert names[1] == names[2] == "steward"
    assert names[3] == names[4] == names[5] == "architect"
    assert names[6] == names[11] == "custodian"


def test_fresh_game_has_no_tagline_and_no_badge(game_env):
    m = game_env.module
    m.update_win_display()
    assert game_env.elements["era-tagline"].hidden is True
    assert game_env.elements["prestige-badge"].hidden is True
    assert game_env.module.document.documentElement.getAttribute("data-era") == "pioneer"


def test_badge_names_the_era_and_keeps_the_level(game_env):
    _set_level(game_env, 3)
    badge = game_env.elements["prestige-badge"]
    assert badge.innerText == "Architect · Prestige 3"
    _set_level(game_env, 1)
    assert badge.innerText == "Steward · Prestige 1"


def test_html_attribute_and_tagline_follow_the_level(game_env):
    m = game_env.module
    for level, era in ((1, "steward"), (4, "architect"), (7, "custodian")):
        _set_level(game_env, level)
        assert m.document.documentElement.getAttribute("data-era") == era
        tagline = game_env.elements["era-tagline"]
        assert tagline.hidden is False and tagline.innerText.startswith(f"Era of the {era.capitalize()}")


def test_the_setting_turns_the_look_off_but_not_the_name(game_env):
    game_env.local_storage.setItem("sol-era-look", "off")
    _set_level(game_env, 2)
    assert game_env.elements["era-tagline"].hidden is True
    assert game_env.elements["prestige-badge"].innerText.startswith("Steward")


def test_a_prestige_moves_into_the_next_era(game_env):
    m = game_env.module
    m.prestige_level = 2
    for p in m.PLANETS:
        m.planet_state[p]["terraform_progress"] = m.TERRAFORM_MAX
    game_env.prestige()
    assert m.prestige_level == 3 and m.document.documentElement.getAttribute("data-era") == "architect"


def test_page_and_css_wiring_is_static_and_scoped():
    html = (GAME_DIR / "index.html").read_text()
    assert 'id="era-tagline"' in html and 'id="era-look-checkbox"' in html
    assert '"sol-era-look"' in (GAME_DIR / "settings.js").read_text()
    css = (GAME_DIR / "style.css").read_text()
    block = css[css.index("A-21: prestige Eras"):css.index("Y11b light-theme polish (2026-09-27)")]
    assert 'html[data-era-look="on"]' in block
    assert "animation" not in block and "transition" not in block  # nothing moves, so Reduce motion needs no case
    assert '"#era-tagline"' in (GAME_DIR / "pc-config.json").read_text()
