"""W2-aftermath: a sourced real-world example beside each kind of shock."""


def test_every_event_type_has_a_sourced_example(game_env):
    m = game_env.module
    assert set(m.REAL_WORLD_EXAMPLES) == set(m.EVENT_LABEL)
    for kind, ex in m.REAL_WORLD_EXAMPLES.items():
        assert ex["title"] and len(ex["text"]) > 80, kind
        assert ex["url"].startswith("https://") and ex["source"], kind


def test_note_shows_the_next_event_before_any_and_the_last_after(game_env):
    m = game_env.module
    m.render()
    first = m.run.schedule[0]
    text = game_env.elements["real-world-text"].innerText
    assert m.REAL_WORLD_EXAMPLES[first]["title"] in text
    assert game_env.elements["real-world-note"].hidden is False
    game_env.resolve_event()
    last = m.run.event_log[-1]["type"]
    assert m.REAL_WORLD_EXAMPLES[last]["title"] in game_env.elements["real-world-text"].innerText


def test_source_line_names_the_page_and_read_date(game_env):
    m = game_env.module
    m.render()
    link = game_env.elements["real-world-source"]
    assert m.REAL_WORLD_READ_DATE in link.innerText and "Source:" in link.innerText
    assert link.href.startswith("https://en.wikipedia.org/")


def test_no_note_when_a_run_is_over_and_has_no_history(game_env):
    m = game_env.module
    m.run.event_log = []
    m.run.event_index = len(m.run.schedule)
    m.render()
    assert game_env.elements["real-world-note"].hidden is True


def test_it_never_changes_a_run(game_env):
    m = game_env.module
    before = (m.run.resources, m.run.event_index)
    m.render()
    assert (m.run.resources, m.run.event_index) == before
