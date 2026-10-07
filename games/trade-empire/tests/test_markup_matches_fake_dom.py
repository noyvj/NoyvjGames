"""Every element id the fake DOM registers (and so every id game.py looks up) must
exist in both pages, so a new panel cannot work in pytest yet be missing live."""

from pathlib import Path

from .conftest import ELEMENT_IDS

BASE = Path(__file__).resolve().parent.parent


def test_every_registered_id_is_in_classic_and_desktop_markup():
    for page in ("index.html", "pc.html"):
        html = (BASE / page).read_text(encoding="utf-8")
        missing = [i for i in ELEMENT_IDS if f'id="{i}"' not in html]
        assert missing == [], (page, missing)


def test_new_toolbar_and_panels_are_in_the_desktop_config():
    import json
    cfg = json.loads((BASE / "pc-config.json").read_text(encoding="utf-8"))
    assert ["captains-panel", "captains-toggle-button", "Fleet Captains"] in cfg["windows"]
    assert "#ledger-ribbon" in cfg["zones"]["stage"]
