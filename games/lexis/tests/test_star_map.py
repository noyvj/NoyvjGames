import star_map
from game import get_state, load_state, state


def test_tune_star():
    discovered = set()
    assert star_map.tune_star("s1", discovered) == {"id": "s1", "x": 2, "y": 3, "strength": 4, "label": "Faint pulse"}
    assert "s1" in discovered
    assert star_map.tune_star("invalid", discovered) is None


def test_save_load_discovered():
    if not hasattr(state, "discovered_stars"):
        state.discovered_stars = set()
    state.discovered_stars = {"s1"}
    data = get_state()
    assert "discovered_stars" in data

    load_state(data)
    assert state.discovered_stars == {"s1"}
