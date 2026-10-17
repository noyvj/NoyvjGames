from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def test_advance_round_wrap_exists():
    with open(GAME_DIR / "index.html", "r") as f:
        html = f.read()
    assert '<div id="advance-round-wrap">' in html


def test_strain_ring_media_query_exists():
    with open(GAME_DIR / "style.css", "r") as f:
        css = f.read()
    assert "@media (max-width: 600px)" in css
    assert "#advance-round-button::before" in css


def test_advance_ring_observer_wired():
    with open(GAME_DIR / "ui.js", "r") as f:
        js = f.read()
    assert 'data-strain' in js
    assert 'strain--critical' in js
    assert 'strain--strained' in js
