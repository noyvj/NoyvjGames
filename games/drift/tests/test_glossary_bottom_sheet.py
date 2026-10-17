from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_glossary_bottom_sheet_element_exists():
    """R4-DRMO-9: the bottom-sheet container is present in index.html."""
    html = (ROOT / "games/drift/index.html").read_text()
    assert 'id="glossary-bottom-sheet"' in html
    assert 'class="glossary-bottom-sheet"' in html


def test_glossary_bottom_sheet_wired_in_ui_js():
    """R4-DRMO-9: ui.js contains the long-press handler and references the sheet."""
    ui = (ROOT / "games/drift/ui.js").read_text()
    assert "glossary-bottom-sheet" in ui
    assert "touchstart" in ui or "mousedown" in ui
