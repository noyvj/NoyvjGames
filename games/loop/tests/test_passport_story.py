"""H7: the traced unit is a named product with an ongoing story."""


def _entries(*sources):
    return [{"cycle": i + 1, "source": s} for i, s in enumerate(sources)]


def test_every_category_and_source_has_a_sentence(game_env):
    m = game_env.module
    for category in m.GOODS_CATEGORIES:
        assert category in m.PASSPORT_PRODUCT_NAME
        for source in m.PASSPORT_SOURCES:
            assert category in m.PASSPORT_STORY[source]


def test_sentences_name_the_product_and_differ_by_category(game_env):
    m = game_env.module
    seen = set()
    for category in m.GOODS_CATEGORIES:
        name = m.PASSPORT_PRODUCT_NAME[category].split(",")[0]
        (cycle, text), = m.passport_story_lines(_entries("recycle"), category)
        assert name in text
        seen.add(text)
    assert len(seen) == len(m.GOODS_CATEGORIES)


def test_lives_count_up_while_in_the_loop_and_reset_on_mining(game_env):
    m = game_env.module
    lines = m.passport_story_lines(_entries("extraction", "repair", "reuse", "recycle", "extraction", "reuse"), "electronics")
    texts = [t for _, t in lines]
    assert "life 2" in texts[1] and "life 3" in texts[2] and "life 4" in texts[3]
    assert "life" not in texts[4]  # a fresh mining is life 1, no suffix
    assert "life 2" in texts[5]


def test_cycle_numbers_are_carried_through(game_env):
    m = game_env.module
    assert [c for c, _ in m.passport_story_lines(_entries("extraction", "reuse", "recycle"), "clothing")] == [1, 2, 3]


def test_unknown_category_falls_back_to_the_default(game_env):
    m = game_env.module
    default = m.passport_story_lines(_entries("reuse"), m.DEFAULT_GOODS_CATEGORY)
    assert m.passport_story_lines(_entries("reuse"), "not-a-category") == default


def test_panel_shows_the_story_for_the_chosen_goods(game_env):
    game_env.chain.goods_category = "furniture"
    game_env.chain.circularity_investment["recycle"] = 40
    game_env.advance_cycle()
    assert "Oak, a chair" in game_env.elements["passport-summary"].innerText
    assert "chipped and pressed into new board" in game_env.elements["passport-list"].children[0].innerText


def test_story_lines_do_not_change_saved_state(game_env):
    m = game_env.module
    game_env.advance_cycle()
    before = m.get_state()
    m.passport_story_lines(game_env.chain.passport, "electronics")
    m.render()
    assert m.get_state() == before
