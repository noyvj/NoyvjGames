from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_mobile_swipe_container_wraps_game_and_neighbor():
    html = (ROOT / "games/drift/index.html").read_text()
    assert '<div id="mobile-swipe-container">' in html
    idx_game = html.find('<div id="game">')
    idx_neighbor = html.find('id="neighbor-panel"')
    idx_close_game = html.find("</div>", idx_game)
    assert idx_neighbor > idx_close_game, "neighbor-panel must be outside #game"


def test_mobile_swipe_media_query_exists():
    css = (ROOT / "games/drift/style.css").read_text()
    assert "@media (max-width: 600px)" in css
    assert "#mobile-swipe-container" in css
    assert "scroll-snap-type: x mandatory" in css


def test_mobile_swipe_handler_wired_in_ui_js():
    js = (ROOT / "games/drift/ui.js").read_text()
    assert 'mobileSwipe' in js
    assert 'scrollBy' in js
