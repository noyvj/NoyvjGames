"""Edge-case tests for info_content.py."""

import info_content
import sim


def test_real_world_example_returns_data_for_known_eras():
    """real_world_example should return a dict with required keys for every era in sim.ERA_ORDER."""
    for era in sim.ERA_ORDER:
        ex = info_content.real_world_example(era)
        assert ex is not None, f"Missing example for {era}"
        assert "title" in ex and "text" in ex and "source" in ex and "url" in ex


def test_real_world_example_handles_empty_and_none_input():
    """real_world_example should return None for empty strings or None."""
    assert info_content.real_world_example("") is None
    assert info_content.real_world_example(None) is None


def test_era_info_page_returns_data_for_known_eras():
    """era_info_page should return a dict with required keys for every era in sim.ERA_ORDER."""
    for era in sim.ERA_ORDER:
        page = info_content.era_info_page(era)
        assert page is not None, f"Missing info page for {era}"
        assert "framing" in page and "mechanic_tie_in" in page and "sources" in page


def test_era_info_page_returns_pending_for_unknown_input():
    """era_info_page should return the _PENDING placeholder dict for unknown eras."""
    pending = info_content.era_info_page("nonexistent_era")
    assert pending is not None
    assert pending["framing"] == (
        "Real-world sources for this era haven't been written yet — Phase "
        "3 adds one era's content at a time, from "
        "continuum-real-world-sources.md."
    )
    assert pending["mechanic_tie_in"] == ""
    assert pending["sources"] == []


def test_era_keys_match_sim_order():
    """ERA_INFO_PAGE and REAL_WORLD_EXAMPLES must cover exactly the eras in sim.ERA_ORDER."""
    era_set = set(sim.ERA_ORDER)
    assert set(info_content.ERA_INFO_PAGE.keys()) == era_set
    assert set(info_content.REAL_WORLD_EXAMPLES.keys()) == era_set


def test_real_world_example_text_length():
    """Each real-world example text should be substantial (> 80 chars)."""
    for ex in info_content.REAL_WORLD_EXAMPLES.values():
        assert len(ex["text"]) > 80, f"Text too short for {ex['title']}"


def test_era_info_page_sources_structure():
    """Each source in ERA_INFO_PAGE should have label and url."""
    for era, page in info_content.ERA_INFO_PAGE.items():
        for src in page["sources"]:
            assert "label" in src and "url" in src, f"Bad source structure in {era}"
