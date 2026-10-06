import re

from compound import COMPONENTS
from bridge import MARKERS
from glyphs import BOX, COMPONENT_PATHS, MARKER_PATHS, all_paths, covered_components, covered_markers, glyph_paths


def test_every_component_has_a_path_and_nothing_extra():
    assert covered_components()


def test_paths_stay_inside_the_box_and_are_distinct():
    seen = set()
    for code, d in COMPONENT_PATHS.items():
        coords = [int(n) for n in re.findall(r"\d+", d)]
        assert coords and all(0 <= c <= BOX for c in coords), code
        assert d not in seen
        seen.add(d)


def test_glyphs_draw_their_components_in_order():
    assert [p["code"] for p in glyph_paths("ku")] == ["k", "u"]
    assert glyph_paths("zz") == []


def test_no_path_is_named_after_what_it_means():
    # A component's drawing must not give the answer away; the code and the path are both opaque.
    for code, (meaning, _slot) in COMPONENTS.items():
        assert meaning not in COMPONENT_PATHS[code].lower()


def test_every_marker_has_a_path_inside_the_box_distinct_from_every_other_sign():
    assert covered_markers() and set(MARKER_PATHS) == {"p", "n", "q"}
    assert not set(MARKER_PATHS) & set(COMPONENT_PATHS)                    # letters never collide
    everything = all_paths()
    assert len(everything) == 8 and len(set(everything.values())) == 8      # eight different drawings
    for letter, d in MARKER_PATHS.items():
        coords = [int(n) for n in re.findall(r"\d+", d)]
        assert coords and all(0 <= c <= BOX for c in coords), letter
        assert d.startswith("M") and "." not in d


def test_marker_drawings_do_not_give_their_meaning_away():
    for letter, role in MARKERS.items():
        assert role not in MARKER_PATHS[letter].lower()
