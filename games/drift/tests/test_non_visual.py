import drift_runstate as runstate


def test_non_visual_mode_defaults_false():
    """I-5: non_visual_mode starts False."""
    assert runstate.non_visual_mode is False


def test_non_visual_mode_in_live_names():
    """I-5: non_visual_mode is tracked in LIVE_NAMES."""
    assert "non_visual_mode" in runstate.LIVE_NAMES


def test_non_visual_toggle_button_exists():
    """I-5: HTML contains the toggle button."""
    from tests.pagefiles import page_text
    html = page_text()
    assert 'id="non-visual-toggle-button"' in html


def test_non_visual_tables_exist():
    """I-5: HTML contains the non-visual tables container and bodies."""
    from tests.pagefiles import page_text
    html = page_text()
    assert 'id="non-visual-tables"' in html
    assert 'id="nv-status-body"' in html
    assert 'id="nv-arrival-body"' in html
    assert 'id="nv-gauges-body"' in html


def test_non_visual_summary_aria_live():
    """I-5: HTML contains the aria-live summary region."""
    from tests.pagefiles import page_text
    html = page_text()
    assert 'id="non-visual-summary"' in html
    assert 'aria-live="polite"' in html
