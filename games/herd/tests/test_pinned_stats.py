"""F-16 pin-a-stat strip (planning/TODO.md "GF + F. Herd")."""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def _tick(env, stat, on=True):
    box = env.elements["pin-" + stat.replace("_", "-")]
    box.checked = on
    box.dispatch("click", None)


def test_nothing_is_pinned_at_first_and_the_strip_is_hidden(game_env):
    game_env.module.render()
    assert game_env.module.pinned_stats == []
    assert game_env.elements["pinned-strip"].hidden


def test_pinning_shows_live_values_in_the_strip(game_env):
    m = game_env.module
    _tick(game_env, "funds")
    _tick(game_env, "welfare")
    _tick(game_env, "income")
    strip = game_env.elements["pinned-strip"]
    assert not strip.hidden
    assert "Funds" in strip.innerHTML and "300" in strip.innerHTML and "50/100" in strip.innerHTML
    assert "Income per round" in strip.innerHTML
    game_env.farm.herd_size = 4
    m.render()
    assert f"{game_env.farm.income_breakdown()['total']:.1f}" in strip.innerHTML


def test_a_fourth_pin_is_refused_and_the_rest_are_disabled(game_env):
    m = game_env.module
    for stat in ("funds", "welfare", "income"):
        _tick(game_env, stat)
    assert m.set_pin("score", True) is False
    assert m.pinned_stats == ["funds", "welfare", "income"]
    assert game_env.elements["pin-score"].disabled
    assert not game_env.elements["pin-funds"].disabled
    assert "3 of 3" in game_env.elements["pin-note"].innerText
    _tick(game_env, "funds", on=False)
    assert not game_env.elements["pin-score"].disabled


def test_pins_are_remembered_in_the_browser_not_the_save(game_env):
    m = game_env.module
    _tick(game_env, "methane")
    assert json.loads(game_env.local_storage.getItem("herd-pinned-stats")) == ["methane"]
    assert "pinned" not in json.dumps(m.get_state())
    module = game_env.reload()
    assert module.pinned_stats == ["methane"]


def test_junk_pins_are_cleaned(game_env):
    m = game_env.module
    assert m.clean_pins(["funds", "funds", "bogus", 3, "score", "herd", "welfare"]) == ["funds", "score", "herd"]
    assert m.clean_pins("funds") == [] and m.clean_pins(None) == []
    game_env.local_storage.setItem("herd-pinned-stats", "not json")
    assert m.load_pins() == []
    assert m.set_pin("bogus", True) is False


def test_every_stat_has_a_checkbox_on_both_pages_and_the_strip_is_in_the_desktop_side_column():
    for page in ("index.html", "pc.html"):
        html = (HERE / page).read_text(encoding="utf-8")
        assert 'id="pinned-strip"' in html
        for stat in ("funds", "income", "welfare", "methane-round", "methane", "score", "herd", "pressure"):
            assert f'id="pin-{stat}"' in html
    cfg = json.loads((HERE / "pc-config.json").read_text(encoding="utf-8"))
    assert cfg["zones"]["side"][0] == "#pinned-strip"


def test_the_strip_is_sticky_and_text_labelled():
    css = (HERE / "style.css").read_text(encoding="utf-8")
    block = css[css.index(".pinned-strip {"):css.index(".pin-chip-label {")]
    assert "position: sticky" in block
