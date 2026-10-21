import pathlib

GAME_DIR = pathlib.Path(__file__).resolve().parent.parent


def test_year_lookup_markup_exists():
    html = (GAME_DIR / "index.html").read_text()
    assert 'id="year-toggle-button"' in html
    assert '<section id="year-panel" class="panel" hidden' in html
    assert 'id="year-input"' in html
    assert 'id="year-go-button"' in html
    assert 'id="year-body"' in html


def test_year_panel_in_keyboard_shortcuts():
    html = (GAME_DIR / "index.html").read_text()
    start = html.find('panels: [')
    end = html.find(']', start) + 1
    panels_str = html[start:end]
    assert '{ toggle: "year-toggle-button", panel: "year-panel" }' in panels_str


def test_toggle_before_panel():
    html = (GAME_DIR / "index.html").read_text()
    toggle_pos = html.find('id="year-toggle-button"')
    panel_pos = html.find('id="year-panel"')
    assert toggle_pos != -1 and panel_pos != -1
    assert toggle_pos < panel_pos
