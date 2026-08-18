"""Info Page: an optional, player-triggered "The Real Story" panel with
curated real-world sources backing the game's mechanics. Never shown by
default -- the mechanic teaches first, this is a supplement for players
who want to go deeper.
"""


def test_info_page_hidden_by_default(game_env):
    assert game_env.elements["info-page-panel"].hidden is True


def test_toggling_info_page_reveals_it(game_env):
    game_env.toggle_info_page()
    assert game_env.elements["info-page-panel"].hidden is False


def test_toggling_twice_hides_it_again(game_env):
    game_env.toggle_info_page()
    game_env.toggle_info_page()
    assert game_env.elements["info-page-panel"].hidden is True


def test_framing_text_is_populated_when_open(game_env):
    game_env.toggle_info_page()
    framing = game_env.elements["info-page-framing"].innerText
    assert framing == game_env.module.INFO_PAGE["framing"]


def test_sources_list_has_one_entry_per_source(game_env):
    game_env.toggle_info_page()
    sources_el = game_env.elements["info-page-sources"]
    assert len(sources_el.children) == len(game_env.module.INFO_PAGE["sources"])


def test_each_source_link_has_a_real_url_and_label(game_env):
    game_env.toggle_info_page()
    sources_el = game_env.elements["info-page-sources"]
    for item, source in zip(sources_el.children, game_env.module.INFO_PAGE["sources"]):
        link = item.children[0]
        assert link.href == source["url"]
        assert link.innerText == source["label"]


def test_toggle_button_label_reflects_state(game_env):
    button = game_env.elements["info-page-toggle-button"]
    assert "Real Story" in button.innerText
    game_env.toggle_info_page()
    assert "Hide" in button.innerText
