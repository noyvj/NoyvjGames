"""Tests for the low-poly globe generator."""


def test_globe_svg_structure():
    from globes import globe_svg
    svg = globe_svg(3)
    assert "<svg" in svg
    assert "</svg>" in svg
    assert 'fill="hsl(' in svg
    assert 'stroke="#1b2744"' in svg


def test_globe_lamp_count():
    from globes import globe_svg
    svg_0 = globe_svg(0)
    svg_5 = globe_svg(5)
    # Count circles (lamps)
    assert svg_0.count('<circle') == 0
    assert svg_5.count('<circle') == 5


def test_globe_deterministic():
    from globes import globe_svg
    assert globe_svg(4) == globe_svg(4)
