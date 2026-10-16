from pathlib import Path


def test_magnifier_bubble_element_exists_in_css():
    """Verify the magnifier-bubble class is defined in style.css."""
    css = (Path(__file__).resolve().parent.parent / "style.css").read_text(encoding="utf-8")
    assert ".magnifier-bubble" in css


def test_magnifier_bubble_respects_reduced_motion():
    """Verify the magnifier bubble respects reduced motion preference."""
    css = (Path(__file__).resolve().parent.parent / "style.css").read_text(encoding="utf-8")
    assert 'html[data-reduced-motion="true"] .magnifier-bubble' in css


def test_magnifier_bubble_has_coord_and_preview():
    """Verify the magnifier bubble has coord and preview elements."""
    css = (Path(__file__).resolve().parent.parent / "style.css").read_text(encoding="utf-8")
    assert ".magnifier-bubble .coord" in css
    assert ".magnifier-bubble .preview" in css
