"""H-31: earned achievements in a closed-loop ring, a one-time unlock flourish, and a more visible entry point."""

from pathlib import Path
from .pagefiles import game_css

HERE = Path(__file__).resolve().parent.parent
CSS = game_css()
PC_JS = (HERE / "pc.js").read_text(encoding="utf-8")
INDEX = (HERE / "index.html").read_text(encoding="utf-8")


def cards(env):
    return env.elements["achievements-panel"].children


def toggle(env):
    return env.elements["achievements-toggle-button"]


def test_an_earned_card_has_a_ring_icon_and_an_unearned_one_does_not(game_env):
    game_env.invest_circularity("repair")  # first_fix
    game_env.toggle_achievements()
    earned = [c for c in cards(game_env) if "achievement-card--earned" in getattr(c, "className", "")]
    locked = [c for c in cards(game_env) if getattr(c, "className", "") == "achievement-card"]
    assert len(earned) == 1 and locked
    ring = earned[0].children[0]
    assert ring.className == "achievement-ring" and ring.attributes["aria-hidden"] == "true"
    assert not any(child.className == "achievement-ring" for c in locked for child in c.children)


def test_the_button_shows_a_progress_step_and_the_count(game_env):
    module = game_env.module
    assert "achievements-toggle--p0" in toggle(game_env).classList
    game_env.invest_circularity("repair")
    total = len(module.ACHIEVEMENTS)
    earned = len(module.achievement_ids_earned())
    step = round(10 * earned / total)
    assert f"achievements-toggle--p{step}" in toggle(game_env).classList
    assert "achievements-toggle--p0" not in toggle(game_env).classList or step == 0
    assert f"({earned}/{total})" in toggle(game_env).innerText


def test_a_new_unlock_makes_the_button_glow_until_the_panel_is_opened(game_env):
    module = game_env.module
    assert "achievements-toggle--new" not in toggle(game_env).classList
    game_env.invest_circularity("repair")
    assert "achievements-toggle--new" in toggle(game_env).classList
    assert " new" in toggle(game_env).innerText
    game_env.toggle_achievements()
    assert "achievements-toggle--new" not in toggle(game_env).classList
    game_env.toggle_achievements()  # closed again
    assert "achievements-toggle--new" not in toggle(game_env).classList and " new" not in toggle(game_env).innerText


def test_a_loaded_save_does_not_glow(game_env):
    module = game_env.module
    game_env.invest_circularity("repair")
    state = module.get_state()
    game_env.toggle_achievements()
    game_env.toggle_achievements()
    module.load_state(state)
    assert "achievements-toggle--new" not in toggle(game_env).classList


def test_the_flourish_plays_once_on_the_first_open_after_unlocking(game_env):
    game_env.invest_circularity("repair")
    game_env.toggle_achievements()
    first = [c for c in cards(game_env) if "achievement-card--new" in c.className]
    assert len(first) == 1 and "achievement-card--earned" in first[0].className
    game_env.module.render()  # a re-render of the open panel must not replay it
    assert not [c for c in cards(game_env) if "achievement-card--new" in c.className]
    game_env.toggle_achievements()
    game_env.toggle_achievements()
    assert not [c for c in cards(game_env) if "achievement-card--new" in c.className]


def test_an_unlock_while_the_panel_is_open_flourishes_at_once(game_env):
    game_env.toggle_achievements()
    game_env.invest_circularity("repair")
    assert [c for c in cards(game_env) if "achievement-card--new" in c.className]


def test_the_test_suite_still_sees_the_old_markers(game_env):
    game_env.invest_circularity("repair")
    game_env.toggle_achievements()
    assert len([c for c in cards(game_env) if "achievement-card--earned" in c.className]) == 1


def test_the_flourish_honours_reduced_motion():
    assert 'html[data-reduced-motion="true"] .achievement-card--new' in CSS
    assert "@media (prefers-reduced-motion: reduce)" in CSS.split(".achievement-card--new")[-1]
    assert 'html[data-reduced-motion="true"] .achievements-toggle--new::after' in CSS


def test_every_progress_step_has_a_style():
    for step in range(11):
        assert f".achievements-toggle--p{step} " in CSS


def test_desktop_carries_the_glow_to_the_icon():
    assert "achievements-toggle--new" in PC_JS and ".pc-icon-button" in PC_JS
    assert 'class="secondary achievements-toggle"' in INDEX
