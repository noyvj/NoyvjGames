
from glyphs import COMPONENT_PATHS, MARKER_PATHS, all_paths, covered_components, covered_markers, glyph_paths


def test_glyph_paths_empty_string():
    """glyph_paths should return an empty list for an empty string."""
    assert glyph_paths("") == []


def test_glyph_paths_single_valid_component():
    """glyph_paths should return a single-item list for one valid component letter."""
    result = glyph_paths("k")
    assert len(result) == 1
    assert result[0]["code"] == "k"
    assert result[0]["d"] == COMPONENT_PATHS["k"]


def test_glyph_paths_all_valid_components():
    """glyph_paths should return all five components in order when given the full set."""
    result = glyph_paths("komtu")
    assert len(result) == 5
    assert [p["code"] for p in result] == ["k", "o", "m", "t", "u"]


def test_glyph_paths_invalid_characters_rejected():
    """glyph_paths should silently skip characters that are not valid components."""
    result = glyph_paths("xyz")
    assert result == []


def test_covered_components_returns_boolean():
    """covered_components should return True when all components have paths defined."""
    assert covered_components() is True


def test_covered_markers_returns_boolean():
    """covered_markers should return True when all markers have paths defined."""
    assert covered_markers() is True


def test_all_paths_contains_expected_keys():
    """all_paths should return a dictionary with exactly the union of component and marker keys."""
    paths = all_paths()
    expected_keys = set(COMPONENT_PATHS) | set(MARKER_PATHS)
    assert set(paths.keys()) == expected_keys
    assert len(paths) == 8
