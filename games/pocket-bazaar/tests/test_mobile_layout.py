import re
from pathlib import Path


def test_mobile_board_fills_width():
    """R4-PBMO-4: board and queue should fill phone width in mobile view."""
    css_path = Path(__file__).resolve().parent.parent / "style.css"
    with open(css_path, "r") as f:
        css = f.read()
    assert re.search(r'@media\s*\(\s*max-width:\s*600px\)', css), "Mobile media query missing"
    assert re.search(r'\.board\s*\{[^}]*width:\s*100%', css, re.DOTALL), "Board should fill width on mobile"
    assert re.search(r'\.queue\s*\{[^}]*width:\s*100%', css, re.DOTALL), "Queue should fill width on mobile"
