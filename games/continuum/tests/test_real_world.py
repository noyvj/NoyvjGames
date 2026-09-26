"""W2-continuum: a sourced "In the real world" example beside each era."""

import info_content
import sim

from .test_relay_era import push_to_relay
from .test_space_age_era import push_to_agrarian


def test_every_era_has_a_sourced_example():
    assert set(info_content.REAL_WORLD_EXAMPLES) == set(sim.ERA_ORDER)
    for era, ex in info_content.REAL_WORLD_EXAMPLES.items():
        assert ex["title"] and len(ex["text"]) > 80, era
        assert ex["source"], era
        assert ex["url"].startswith("https://"), era


def test_every_example_source_is_a_page_read_from_an_allowed_host():
    """The examples were read from Wikipedia and NASA pages only (the
    UNESCO pages refused the fetch and are not cited)."""
    for era, ex in info_content.REAL_WORLD_EXAMPLES.items():
        assert ex["url"].startswith(("https://en.wikipedia.org/wiki/", "https://www.nasa.gov/")), era
        assert "unesco" not in ex["url"], era


def test_read_date_is_recorded():
    assert info_content.REAL_WORLD_READ_DATE == "2026-09-27"


def test_note_is_shown_for_the_current_era_and_names_the_example(game_env):
    m = game_env.module
    m.render()
    ex = info_content.REAL_WORLD_EXAMPLES["tribal"]
    assert game_env.elements["real-world-note"].hidden is False
    text = game_env.elements["real-world-text"].innerText
    assert text.startswith("In the real world: ") and ex["title"] in text and ex["text"] in text


def test_source_line_names_the_page_read_date_and_link(game_env):
    game_env.module.render()
    link = game_env.elements["real-world-source"]
    ex = info_content.REAL_WORLD_EXAMPLES["tribal"]
    assert link.innerText == f"Source: {ex['source']} (read {info_content.REAL_WORLD_READ_DATE})"
    assert link.href == ex["url"]


def test_the_note_follows_the_era(game_env):
    push_to_agrarian(game_env)
    game_env.module.render()
    ex = info_content.REAL_WORLD_EXAMPLES["agrarian"]
    assert ex["title"] in game_env.elements["real-world-text"].innerText
    push_to_relay(game_env)
    game_env.module.render()
    assert info_content.REAL_WORLD_EXAMPLES["relay"]["title"] in game_env.elements["real-world-text"].innerText


def test_an_unknown_era_hides_the_note(game_env):
    game_env.state.era = "not_an_era_this_build_knows"
    game_env.module.render_real_world()
    assert game_env.elements["real-world-note"].hidden is True
    assert info_content.real_world_example("not_an_era_this_build_knows") is None


def test_it_never_changes_the_game(game_env):
    m = game_env.module
    before = (m.state.population, dict(m.state.resources), m.state.season, m.state.land_health)
    m.render()
    m.render_real_world()
    assert (m.state.population, dict(m.state.resources), m.state.season, m.state.land_health) == before
