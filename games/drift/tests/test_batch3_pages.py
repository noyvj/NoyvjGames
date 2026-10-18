"""Oct 11 batch 3: every new element exists on both pages, the Desktop boot reaches the new window, and the
changelog and fake DOM list stay in step."""

import json
import re
from pathlib import Path

from .pagefiles import game_css, game_source, page_text

GAME_DIR = Path(__file__).resolve().parent.parent

NEW_IDS = [
    "tier-details", "tier-summary", "tier-line", "tier-gentle-button", "tier-standard-button", "tier-rigorous-button",
    "tier-demanding-button", "tier-note", "tier-best-table", "tier-best-note",
    "assist-off-button", "assist-suggest-button", "assist-explain-button", "assist-note", "assist-suggestion", "assist-reasons",
    "confirm-threshold-select", "confirm-threshold-note",
    "save-nudge-box", "save-nudge", "save-nudge-dismiss",
    "glossary-capacity-button", "glossary-strain-button", "glossary-integration-button", "glossary-control-button",
    "glossary-pop", "glossary-pop-text", "glossary-more-button",
    "report-toggle-button", "report-panel", "report-card", "report-copy-button", "report-print-button",
    "report-copy-status", "report-copy-area", "report-print-sheet",
    "band-confetti", "band-change-note",
]


def test_every_new_element_exists_in_both_pages():
    for page in ("index.html", "pc.html"):
        html = (GAME_DIR / page).read_text(encoding="utf-8")
        for element_id in NEW_IDS:
            assert f'id="{element_id}"' in html, f"{element_id} missing from {page}"


def test_every_id_game_py_looks_up_for_batch_3_is_in_the_fake_dom_list(game_env):
    source = game_source()
    block = source[source.index("# Oct 11 batch 3"):source.index("def get_state():")]
    used = set(re.findall(r'getElementById\("([a-z0-9-]+)"\)', block))
    used |= {f"tier-{t}-button" for t in ("gentle", "standard", "rigorous", "demanding")}
    missing = [i for i in used if i not in game_env.elements]
    assert missing == []


def test_the_report_is_a_desktop_window_and_a_menu_entry():
    config = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    assert ["report-panel", "report-toggle-button", "Region Report"] in config["windows"]
    records = next(g for g in config["toolbar"]["menu"] if g["heading"] == "Records")
    assert "report-toggle-button" in records["ids"]
    html = (GAME_DIR / "pc.html").read_text(encoding="utf-8")
    assert "Region Report" in html


def test_new_controls_sit_in_zones_the_desktop_shows():
    config = json.loads((GAME_DIR / "pc-config.json").read_text(encoding="utf-8"))
    assert "#status" in config["zones"]["stage"]  # tiers, glossary and the save nudge live in the status block
    assert "#round-tools" in config["zones"]["side"]  # planner assist lives in Round tools
    assert "#wellbeing" in config["zones"]["stage"]  # confetti


def test_the_print_sheet_is_a_direct_child_of_the_body_so_print_css_can_isolate_it():
    html = (GAME_DIR / "index.html").read_text(encoding="utf-8")
    assert re.search(r'</div>\n\s*<!-- I-4: print-only copy[^\n]*\n\s*<div id="report-print-sheet"', html)
    css = game_css()
    assert "body > *:not(#report-print-sheet) { display: none !important; }" in css


def test_the_report_has_a_keyboard_panel_entry():
    html = page_text("index.html")
    assert '{ toggle: "report-toggle-button", panel: "report-panel" }' in html


def test_changelog_mentions_each_new_feature():
    entries = json.loads((GAME_DIR / "changelog.json").read_text(encoding="utf-8"))
    text = " ".join(e["entry"] for e in entries[:7])
    for word in ("Region Report", "confetti", "glossary", "save reminder", "Confirm large moves", "planner assist", "difficulty tiers"):
        assert word.lower() in text.lower(), word
