"""GF-12 cow reactions: mood classes, a dry one-liner on click or Listen, never a change to the farm."""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def _grow(env, count=3):
    env.farm.funds = 5000.0
    for _ in range(count):
        env.farm.grow_herd()
    env.module.render()


def _cow_classes(env):
    return set(env.elements["pasture-cow-a"].classList._classes)


def test_a_new_farm_is_calm(game_env):
    _grow(game_env)
    assert game_env.module.herd_mood() == "graze"
    assert not _cow_classes(game_env) & {"cow-mood-hop", "cow-mood-nap"}
    assert "calm" in game_env.elements["cow-listen-button"].innerText


def test_a_well_cared_for_clean_herd_hops(game_env):
    _grow(game_env)
    game_env.farm.decoupling_investment.update({"feed": 4, "caps": 4, "capture": 4})
    game_env.module.render()
    assert game_env.module.herd_mood() == "hop"
    assert "cow-mood-hop" in _cow_classes(game_env) and "hopping" in game_env.elements["cow-listen-button"].innerText


def test_a_strained_herd_naps_with_text_not_only_motion(game_env):
    _grow(game_env)
    game_env.farm.methane = 45.0
    game_env.farm.pressure_fraction()
    game_env.farm.methane = 60.0
    game_env.module.render()
    assert game_env.module.herd_mood() == "nap"
    assert "cow-mood-nap" in _cow_classes(game_env) and "napping" in game_env.elements["cow-listen-button"].innerText
    css = (HERE / "style.css").read_text(encoding="utf-8")
    assert 'content: "z z"' in css


def test_clicking_a_cow_names_that_animal_and_shows_a_line(game_env):
    m = game_env.module
    _grow(game_env, 3)
    game_env.elements["pasture-cow-b"].dispatch("click", None)  # the third animal (index 2)
    bubble = game_env.elements["cow-bubble"]
    assert bubble.hidden is False and bubble.innerText.startswith(m.cow_name(2) + ":")
    game_env.timers.flush()
    assert bubble.hidden is True


def test_listen_button_is_the_keyboard_way_and_rotates_lines_without_luck(game_env):
    m = game_env.module
    _grow(game_env, 2)
    seen = []
    for _ in range(4):
        game_env.elements["cow-listen-button"].dispatch("click", None)
        seen.append(game_env.elements["cow-bubble"].innerText.split(": ", 1)[1])
    assert seen == m.COW_QUIPS["graze"]
    game_env.elements["cow-listen-button"].dispatch("click", None)
    assert game_env.elements["cow-bubble"].innerText.split(": ", 1)[1] == m.COW_QUIPS["graze"][0]


def test_an_empty_pasture_has_nothing_to_say_and_the_button_is_off(game_env):
    game_env.module.render()
    assert game_env.elements["cow-listen-button"].disabled
    assert "empty" in game_env.module.cow_quip()


def test_a_stale_timer_does_not_hide_a_newer_line(game_env):
    _grow(game_env, 2)
    game_env.elements["cow-listen-button"].dispatch("click", None)
    first_timer = game_env.timers.pending[-1][0]
    game_env.elements["cow-listen-button"].dispatch("click", None)
    first_timer()
    assert game_env.elements["cow-bubble"].hidden is False


def test_moods_never_change_the_farm_or_the_save(game_env):
    _grow(game_env, 3)
    before = json.dumps(game_env.module.get_state(), sort_keys=True)
    game_env.elements["cow-listen-button"].dispatch("click", None)
    game_env.elements["pasture-cow-a"].dispatch("click", None)
    assert json.dumps(game_env.module.get_state(), sort_keys=True) == before


def test_every_quip_is_short_and_there_are_four_per_mood(game_env):
    for lines in game_env.module.COW_QUIPS.values():
        assert len(lines) == 4 and all(len(line.split()) <= 18 for line in lines)


def test_pages_and_css_gates():
    for page in ("index.html", "pc.html"):
        html = (HERE / page).read_text(encoding="utf-8")
        assert 'id="cow-listen-button"' in html and 'id="cow-bubble"' in html
    css = (HERE / "style.css").read_text(encoding="utf-8")
    assert 'html[data-reduced-motion="true"] .pasture-visual-cow.cow-mood-hop' in css
    cfg = json.loads((HERE / "pc-config.json").read_text(encoding="utf-8"))
    assert ".cow-chat" in cfg["zones"]["stage"]
