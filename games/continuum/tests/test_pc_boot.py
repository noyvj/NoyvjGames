"""The Desktop boot (pc.html), PC version plan phase 1.

pc.html is generated from index.html, so the two pages share every element id
that game.py looks up. These tests keep it that way, and check the one piece of
game logic the Desktop boot adds: the Hamlet view is on by default there.
"""

import pathlib
import re
import subprocess
import sys

GAME_DIR = pathlib.Path(__file__).resolve().parent.parent
ROOT = GAME_DIR.parent.parent
CLASSIC = (GAME_DIR / "index.html").read_text(encoding="utf-8")
DESKTOP = (GAME_DIR / "pc.html").read_text(encoding="utf-8")
GAME_PY = (GAME_DIR / "game.py").read_text(encoding="utf-8")


def _ids(html):
    return set(re.findall(r'\bid="([^"]+)"', html))


def test_pc_html_is_up_to_date_with_its_generator():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate-pc-pages.py"), "--check"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_every_id_game_py_looks_up_exists_in_both_pages():
    wanted = set(re.findall(r'getElementById\(\s*"([^"]+)"\s*\)', GAME_PY))
    assert wanted, "expected literal getElementById calls in game.py"
    # Ids game.py itself creates at run time are not in either page.
    created = set(re.findall(r'\.id\s*=\s*"([^"]+)"', GAME_PY))
    # Ids only the Desktop shell creates; game.py guards for their absence (Classic has none).
    created |= {"pc-open-pc-setup-panel"}
    for name, html in (("index.html", CLASSIC), ("pc.html", DESKTOP)):
        missing = sorted(wanted - created - _ids(html))
        assert not missing, f"{name} lacks ids game.py needs: {missing}"


def test_both_pages_use_the_same_game_id_so_saves_are_shared():
    for html in (CLASSIC, DESKTOP):
        assert 'data-game-id="continuum"' in html
    classic_ids = set(re.findall(r'data-game-id="([^"]+)"', CLASSIC))
    assert classic_ids == set(re.findall(r'data-game-id="([^"]+)"', DESKTOP))


def test_desktop_page_declares_its_layout_before_anything_else_loads():
    first_script = DESKTOP.index("<script")
    assert 'window.NOYVJ_LAYOUT = "pc"' in DESKTOP[first_script:first_script + 400]
    assert DESKTOP.index("NOYVJ_LAYOUT") < DESKTOP.index("layout-pref.js") < DESKTOP.index("pyodide.js")
    assert "NOYVJ_LAYOUT" not in CLASSIC


def test_classic_page_only_gains_the_redirect_script_and_the_tutorial_hook():
    assert "layout-pref.js" in CLASSIC and "pc.html" in CLASSIC
    assert "pc-shell" not in CLASSIC and "pc.css" not in CLASSIC
    assert "window.CONTINUUM_PC_TUTORIAL_STEPS || CONTINUUM_TUTORIAL_STEPS" in CLASSIC


def test_hamlet_is_the_way_to_play_on_the_desktop_boot(game_env, monkeypatch):
    m = game_env.module
    assert m._pc_layout() is False            # Classic and the test harness: unchanged

    class Window:
        NOYVJ_LAYOUT = "pc"

    monkeypatch.setattr(m, "_js_window", lambda: Window())
    assert m._pc_layout() is True

    class ClassicWindow:
        NOYVJ_LAYOUT = None

    monkeypatch.setattr(m, "_js_window", lambda: ClassicWindow())
    assert m._pc_layout() is False


def test_the_hamlet_toggle_is_hidden_on_the_desktop_boot(game_env, monkeypatch):
    m = game_env.module
    monkeypatch.setattr(m, "_hamlet_capable", lambda: True)
    m.hamlet_on = True
    m.render_hamlet()
    assert game_env.elements["hamlet-toggle-button"].hidden is False   # Classic keeps its toggle
    monkeypatch.setattr(m, "_pc_layout", lambda: True)
    m.render_hamlet()
    assert game_env.elements["hamlet-toggle-button"].hidden is True


def test_tutorial_steps_for_the_desktop_boot_only_point_at_things_that_exist_there():
    js = (GAME_DIR / "pc.js").read_text(encoding="utf-8")
    selectors = re.findall(r'selector:\s*"([^"]+)"', js)
    assert selectors
    page_ids = _ids(DESKTOP)
    zone_ids = {"pc-stagebar", "pc-stage", "pc-side", "pc-topbar", "pc-body", "pc-menu-button", "pc-hud"}   # built by shared/pc-shell.js
    for selector in selectors:
        assert selector.startswith("#")
        first_id = re.match(r"#([\w-]+)", selector).group(1)
        assert first_id in page_ids | zone_ids, selector
    # The Classic steps that the Hamlet layout hides must not be reused here.
    for hidden_panel in ("#work", "#buildings", "#research", "#era-progress"):
        assert hidden_panel not in selectors


def test_hotkey_hints_only_name_shortcuts_the_game_really_has():
    panel = CLASSIC[CLASSIC.index('id="shortcuts-panel"'):]
    panel = panel[:panel.index("</div>")]
    hints = re.search(r"window\.NOYVJ_PC_HINTS = (\[.*?\]);", DESKTOP).group(1)
    import json
    for key, _label in json.loads(hints):
        for part in re.split(r"–|-", key):
            assert f"<kbd>{part}</kbd>" in panel or part in "1234", f"hint key {key!r} is not in the shortcuts panel"


def test_notifications_watch_a_list_that_exists_on_both_pages():
    selector = re.search(r'window\.NOYVJ_PC_NOTIFY = \{"list": "#([^"]+)"\}', DESKTOP).group(1)
    assert selector in _ids(CLASSIC) and selector in _ids(DESKTOP)


def test_every_condensed_toolbar_button_exists_on_both_pages():
    import json
    cfg = json.loads(re.search(r"window\.NOYVJ_PC_TOOLBAR = (\{.*?\});", DESKTOP).group(1))
    ids = [i for i, _emoji in cfg["icons"]] + [i for group in cfg["menu"] for i in group["ids"]]
    assert ids
    for name, html in (("index.html", CLASSIC), ("pc.html", DESKTOP)):
        missing = [i for i in ids if i not in _ids(html)]
        assert not missing, f"{name} lacks toolbar ids: {missing}"
    # Nothing that used to be in the toolbar may be silently dropped.
    toolbar = CLASSIC[CLASSIC.index('class="game-toolbar"'):]
    toolbar = toolbar[:toolbar.index("</div>")]
    for button_id in re.findall(r'<button id="([^"]+)"', toolbar):
        assert button_id in ids, f"{button_id} is in the Classic toolbar but neither an icon nor in the menu"


# --- the HUD that replaces the side column on the Desktop boot -------------------------

def _desktop_game(game_env, monkeypatch):
    m = game_env.module
    monkeypatch.setattr(m, "_pc_layout", lambda: True)
    monkeypatch.setattr(m, "_hamlet_capable", lambda: True)
    m.hamlet_on = True
    m.render()
    return m


def test_the_hud_has_one_chip_per_readout_and_each_has_a_dropdown(game_env, monkeypatch):
    m = _desktop_game(game_env, monkeypatch)
    assert [key for key, _icon, _label in m.PC_HUD_CHIPS] == [
        "population", "food", "materials", "tools", "knowledge", "sustainability"]
    for key, _icon, _label in m.PC_HUD_CHIPS:
        els = m._pc_hud_els[key]
        assert els["toggle"].attributes["data-pc-dropdown"] == "1"
        assert els["toggle"].attributes["aria-expanded"] == "false"
        assert els["dropdown"].hidden is True
        assert els["value"].innerText


def test_the_people_dropdown_states_the_trend_per_season(game_env, monkeypatch):
    m = _desktop_game(game_env, monkeypatch)
    dropdown = m._pc_hud_els["population"]["dropdown"]
    text = " ".join(child.innerText for child in dropdown.children)
    assert "per season" in text or "birth" in text


def test_the_scenario_chip_only_shows_before_the_first_season(game_env, monkeypatch):
    m = _desktop_game(game_env, monkeypatch)
    chip = m._pc_hud_els["_setup"]["el"]
    assert chip.hidden is False and "Standard Start" in chip.innerText
    game_env.advance_season()
    game_env.advance_season()
    m.render()
    assert chip.hidden is True


def test_the_classic_page_never_builds_the_hud(game_env):
    game_env.module.render()
    assert game_env.module._pc_hud_els == {}


def test_a_failing_forecast_does_not_break_the_render(game_env, monkeypatch):
    m = _desktop_game(game_env, monkeypatch)

    def boom(*args, **kwargs):
        raise RuntimeError("probe failed")

    monkeypatch.setattr(m.forecast, "preview", boom)
    m.render()   # must not raise
    dropdown = m._pc_hud_els["food"]["dropdown"]
    assert any("unavailable" in child.innerText for child in dropdown.children)
