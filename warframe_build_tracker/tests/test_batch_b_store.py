"""Batch B: save/load of every new key, plus the boot wiring that makes the extra modules loadable."""

import re
from pathlib import Path

import wf_store

from .helpers import known_state

ROOT = Path(__file__).resolve().parent.parent
NEW_KEYS = {"relics", "crafts", "pets", "forma", "imports", "readiness"}


def _fill(m):
    known_state(m)
    m.add_combo("Mine", ["Raplak Prism"])
    s = m.state
    s["relics"] = {"wants": ["Fang Prime Blade"], "owned": {"Lith A13": 2}, "custom": [{"n": "Neo O1", "v": True, "p": ["X"]}]}
    s["crafts"] = [{"n": "Excalibur Prime", "k": "warframe", "own": True, "imp": False, "needs": [{"n": "Neuroptics", "q": 1, "h": 1}]}]
    s["pets"] = [{"n": "Rex", "k": "kubrow", "i": 1, "m": "Bite", "t": ""}]
    s["forma"] = {"have": 2, "used": 3, "plans": [{"n": "Mine", "cur": ["madurai"], "want": ["vazarin"], "on": True}]}
    s["imports"] = {"last": {"t": "2026-09-27 10:00", "c": {"Ferrite": 5}, "o": []}, "prev": None}
    s["readiness"] = {"mods": [{"n": "Serration", "r": 3, "m": 10}]}


def test_defaults_write_nothing(game_env):
    m = game_env.module
    known_state(m)
    assert not NEW_KEYS & set(m.get_state())
    assert wf_store.export(m.state) == {}


def test_full_round_trip(game_env):
    m = game_env.module
    _fill(m)
    saved = m.get_state()
    assert NEW_KEYS <= set(saved)
    expected = {k: saved[k] for k in NEW_KEYS}
    m.state.update(wf_store.default_state())
    m.load_state(saved)
    assert {k: m.get_state()[k] for k in NEW_KEYS} == expected
    assert m.state["forma"]["plans"][0]["n"] == "Mine"  # combo names load before plans are validated


def test_old_saves_without_the_keys_load_to_defaults(game_env):
    m = game_env.module
    _fill(m)
    m.load_state({"parts": {}, "inventory": {}})
    assert m.state["relics"] == {"wants": [], "owned": {}, "custom": []} and m.state["crafts"] == [] and m.state["pets"] == []
    assert m.state["forma"] == {"have": 0, "used": 0, "plans": []} and m.state["imports"] == {"last": None, "prev": None}
    assert m.state["readiness"] == {"mods": []}


def test_garbage_in_every_key_is_dropped(game_env):
    m = game_env.module
    for junk in ("text", 5, [1, 2], {"a": 1}, None, True):
        m.load_state({key: junk for key in NEW_KEYS})
        assert wf_store.export(m.state) == {}
        m.render()  # and the page still renders


def test_removing_a_combo_prunes_forma_plans_but_keeps_the_rest(game_env):
    m = game_env.module
    _fill(m)
    m.remove_combo("Mine")
    assert m.state["forma"]["plans"] == [] and m.state["forma"]["have"] == 2
    assert m.state["relics"]["wants"] == ["Fang Prime Blade"]


def test_reset_inventory_keeps_the_planner_data(game_env):
    m = game_env.module
    _fill(m)
    game_env.reset()
    assert m.state["pets"] and m.state["crafts"] and m.state["relics"]["wants"]


def test_every_module_game_py_needs_is_loaded_by_the_page():
    html = (ROOT / "index.html").read_text()
    listed = set(re.search(r"WF_MODULES = \[(.*?)\]", html, re.S).group(1).replace('"', "").replace("\n", "").replace(" ", "").split(","))
    on_disk = {p.name for p in ROOT.glob("wf_*.py")}
    assert listed == on_disk
    # every wf_ module imported anywhere is one of them, and the write happens before game.py runs
    imported = set()
    for path in ROOT.glob("*.py"):
        imported |= {f"{name}.py" for name in re.findall(r"^\s*(?:import|from) (wf_\w+)", path.read_text(), re.M)}
    assert imported <= listed
    assert html.index("WF_MODULES") < html.index('fetch("game.py"')


def test_batch_b_light_theme_rules_come_after_the_light_theme_comment_and_base_rules_before_it():
    css = (ROOT / "style.css").read_text()
    marker = css.index("/* Light theme")
    assert css.index("#adv-section h3") < marker and css.index(".adv-card {") < marker  # dark/base rules
    after = css[marker:]
    for selector in ('html[data-theme="light"] #adv-section', 'html[data-theme="light"] .adv-card',
                     'html[data-theme="light"] .resource-tip'):
        assert selector in after


def test_every_batch_b_element_id_used_by_the_page_exists_in_the_fake_dom(game_env):
    html = (ROOT / "index.html").read_text()
    section = html[html.index('id="adv-section"'):html.index('id="shortcut-overlay"')]
    ids = set(re.findall(r'id="([^"]+)"', section))
    assert ids and ids <= set(game_env.elements)
