import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]


def test_borrow_confirm_sheet_exists():
    """Test that the borrow confirm sheet HTML element exists in the page."""
    with open(ROOT / "station-medic" / "index.html", "r") as f:
        content = f.read()

    assert 'id="borrow-confirm-sheet"' in content, "Borrow confirm sheet ID not found in index.html"
    assert 'id="borrow-confirm-text"' in content, "Borrow confirm text element not found in index.html"
    assert 'id="borrow-confirm-yes"' in content, "Borrow confirm yes button not found in index.html"
    assert 'id="borrow-confirm-no"' in content, "Borrow confirm no button not found in index.html"


def test_borrow_confirm_css_exists():
    """Test that the borrow confirm sheet CSS styles exist."""
    with open(ROOT / "station-medic" / "style.css", "r") as f:
        content = f.read()

    assert ".borrow-confirm-sheet" in content, "Borrow confirm sheet class not found in style.css"
    assert ".borrow-confirm-content" in content, "Borrow confirm content class not found in style.css"
    assert "@media (prefers-reduced-motion: reduce)" in content, "Reduced motion media query not found for borrow confirm"


def test_borrow_confirm_js_functions_exist():
    """Test that the borrow confirm JavaScript functions exist."""
    with open(ROOT / "station-medic" / "app.js", "r") as f:
        content = f.read()

    assert "_initBorrowConfirm" in content, "_initBorrowConfirm function not found in app.js"
    assert "showBorrowConfirm" in content, "showBorrowConfirm function not found in app.js"
    assert "hideBorrowConfirm" in content, "hideBorrowConfirm function not found in app.js"
    assert 'action: "borrow"' in content, "Borrow action not found in app.js"
