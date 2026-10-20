"""Edge-case tests for the low-poly globe generator."""


def test_globe_svg_zero_lamps():
    """Test globe with zero lamps produces valid SVG structure without circles."""
    from globes import globe_svg
    svg = globe_svg(0)
    assert "<svg" in svg
    assert "</svg>" in svg
    assert svg.count('<circle') == 0


def test_globe_svg_max_lamps():
    """Test globe with the maximum allowed lamp count (7)."""
    from globes import globe_svg
    svg = globe_svg(7)
    assert "<svg" in svg
    assert "</svg>" in svg
    assert svg.count('<circle') == 7


def test_globe_svg_negative_lamps():
    """Test that a negative lamp count does not crash and produces valid SVG structure."""
    from globes import globe_svg
    svg = globe_svg(-1)
    assert "<svg" in svg
    assert "</svg>" in svg
    assert svg.count('<circle') == 0


def test_globe_svg_zero_dimensions():
    """Test globe with zero width and height does not crash."""
    from globes import globe_svg
    svg = globe_svg(3, width=0, height=0)
    assert "<svg" in svg
    assert "</svg>" in svg


def test_globe_svg_large_dimensions():
    """Test globe with large width and height produces valid SVG structure."""
    from globes import globe_svg
    svg = globe_svg(4, width=1000, height=1000)
    assert "<svg" in svg
    assert "</svg>" in svg
