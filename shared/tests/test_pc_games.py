"""Checks that apply to EVERY game with a Desktop boot (games/<slug>/pc-config.json).

See planning/PC-GAME-CONVERSION-GUIDE.md. These keep the two pages of a game from drifting apart and
keep a game's pc-config.json honest, so converting a game needs no hand-written tests of its own
(game-specific behaviour can still get its own tests in the game's folder).
"""

import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONFIGS = sorted((ROOT / "games").glob("*/pc-config.json"))
SLUGS = [p.parent.name for p in CONFIGS]
SHELL_IDS = {"pc-stagebar", "pc-stage", "pc-side", "pc-topbar", "pc-body", "pc-menu-button", "pc-hud",
             "pc-readouts", "pc-menu-panel", "pc-hintbar", "pc-toasts", "pc-toolbar-source",
             "pc-hidden-readouts", "pc-fullscreen-button", "pc-classic-button", "pc-menu-display"}

_spec = importlib.util.spec_from_file_location("generate_pc_pages", ROOT / "scripts" / "generate-pc-pages.py")
generator = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(generator)


def _ids(html):
    return set(re.findall(r'\bid="([^"]+)"', html))


def _read(slug, name):
    return (ROOT / "games" / slug / name).read_text(encoding="utf-8")


def _cfg(slug):
    return json.loads(_read(slug, "pc-config.json"))


def _id_of(selector):
    match = re.match(r"^#([\w-]+)", selector)
    return match.group(1) if match else None


def test_at_least_one_game_has_a_desktop_boot():
    assert "continuum" in SLUGS


@pytest.mark.parametrize("slug", SLUGS)
def test_pc_html_is_up_to_date(slug):
    assert (ROOT / "games" / slug / "pc.html").read_text(encoding="utf-8") == generator.build(slug, _cfg(slug))


@pytest.mark.parametrize("slug", SLUGS)
def test_every_id_game_py_looks_up_exists_in_both_pages(slug):
    game_py = _read(slug, "game.py")
    wanted = set(re.findall(r'getElementById\(\s*"([^"]+)"\s*\)', game_py))
    created = set(re.findall(r'\.id\s*=\s*"([^"]+)"', game_py))
    wanted = {i for i in wanted - created if not i.startswith("pc-")}
    for name in ("index.html", "pc.html"):
        missing = sorted(wanted - _ids(_read(slug, name)))
        assert not missing, f"{slug}/{name} lacks ids game.py needs: {missing}"


@pytest.mark.parametrize("slug", SLUGS)
def test_both_pages_share_the_game_id_so_saves_are_shared(slug):
    classic, desktop = _read(slug, "index.html"), _read(slug, "pc.html")
    ids = set(re.findall(r'data-game-id="([^"]+)"', classic))
    assert ids == {slug}
    assert ids == set(re.findall(r'data-game-id="([^"]+)"', desktop))


@pytest.mark.parametrize("slug", SLUGS)
def test_classic_page_only_gains_the_layout_script_and_tutorial_hook(slug):
    classic = _read(slug, "index.html")
    assert f'src="../../shared/layout-pref.js" data-game-id="{slug}" data-pc-page="pc.html"' in classic
    assert "pc-shell" not in classic and "pc.css" not in classic and "NOYVJ_LAYOUT" not in classic.replace("window.NOYVJ_LAYOUT", "")


@pytest.mark.parametrize("slug", SLUGS)
def test_config_points_only_at_things_that_exist(slug):
    cfg, classic = _cfg(slug), _read(slug, "index.html")
    ids = _ids(classic)
    for panel, toggle, _title in cfg["windows"]:
        assert panel in ids, f"window panel #{panel}"
        assert toggle is None or toggle in ids, f"window toggle #{toggle}"
    for button_id, _emoji in cfg["toolbar"]["icons"]:
        assert button_id in ids, f"icon button #{button_id}"
    for group in cfg["toolbar"]["menu"]:
        for button_id in group["ids"]:
            assert button_id in ids, f"menu button #{button_id}"
    for composite in cfg.get("composites", []):
        for member in composite["members"]:
            first = _id_of(member)
            assert first is None or first in ids, f"composite member {member}"
    for readout in cfg.get("readouts", []):
        first = _id_of(readout[0])
        assert first is None or first in ids, f"readout {readout[0]}"
    for zone, selectors in cfg["zones"].items():
        for selector in selectors:
            first = _id_of(selector)
            assert first is None or first in ids, f"zone {zone}: {selector}"


@pytest.mark.parametrize("slug", SLUGS)
def test_no_classic_toolbar_button_is_dropped(slug):
    cfg, classic = _cfg(slug), _read(slug, "index.html")
    kept = {i for i, _ in cfg["toolbar"]["icons"]} | {i for g in cfg["toolbar"]["menu"] for i in g["ids"]}
    kept |= {toggle for _p, toggle, _t in cfg["windows"] if toggle}
    for block in re.findall(r'<div class="game-toolbar"[^>]*>(.*?)</div>', classic, flags=re.S):
        for button_id in re.findall(r'<button[^>]*\bid="([^"]+)"', block):
            assert button_id in kept, f"#{button_id} is in the Classic toolbar but neither an icon nor in the menu"


@pytest.mark.parametrize("slug", SLUGS)
def test_desktop_tutorial_steps_only_point_at_things_that_exist_there(slug):
    path = ROOT / "games" / slug / "pc.js"
    if not path.exists():
        pytest.skip("no Desktop tutorial")
    classic, desktop = _read(slug, "index.html"), _read(slug, "pc.html")
    assert "PC_TUTORIAL_STEPS" in classic, "index.html must use the Desktop steps when they exist"
    page_ids = _ids(desktop) | SHELL_IDS
    for selector in re.findall(r'selector:\s*"([^"]+)"', path.read_text(encoding="utf-8")):
        first = _id_of(selector)
        assert first is not None and first in page_ids, f"tutorial selector {selector}"
