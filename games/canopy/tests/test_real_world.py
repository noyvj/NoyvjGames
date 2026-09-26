"""W2-canopy: a sourced real-world example beside what the player just did."""


def _shown(game_env):
    m = game_env.module
    m.render()
    return game_env.elements["real-world-text"].innerText


def test_every_example_is_sourced(game_env):
    m = game_env.module
    assert set(m.REAL_WORLD_EXAMPLES) == set(m.REAL_WORLD_ORDER)
    assert set(m.REAL_WORLD_LOG_TOPICS.values()) <= set(m.REAL_WORLD_EXAMPLES)
    assert 4 <= len(m.REAL_WORLD_EXAMPLES) <= 6
    for topic, ex in m.REAL_WORLD_EXAMPLES.items():
        assert ex["title"] and len(ex["text"]) > 80, topic
        assert ex["url"].startswith("https://") and ex["source"], topic


def test_note_is_visible_and_rotates_deterministically_on_a_fresh_forest(game_env):
    m = game_env.module
    seen = []
    for _ in range(len(m.REAL_WORLD_ORDER)):
        text = _shown(game_env)
        seen.append(m.real_world_topic())
        assert m.REAL_WORLD_EXAMPLES[seen[-1]]["title"] in text
        m.forest_tick += m.REAL_WORLD_ROTATE_TICKS
    assert seen == m.REAL_WORLD_ORDER
    assert game_env.elements["real-world-note"].hidden is False


def test_clearing_a_plot_shows_forest_loss_and_replanting_shows_restoration(game_env):
    m = game_env.module
    m.select_plot(0)
    m.on_clear()
    assert m.real_world_topic() == "forest_loss"
    assert m.REAL_WORLD_EXAMPLES["forest_loss"]["title"] in game_env.elements["real-world-text"].innerText
    m.on_replant()
    assert m.real_world_topic() == "restoration"
    assert m.REAL_WORLD_EXAMPLES["restoration"]["title"] in game_env.elements["real-world-text"].innerText


def test_wildlife_and_maturity_events_pick_their_examples(game_env):
    m = game_env.module
    m._log_event("wildlife", "A fox appeared", 0)
    assert m.real_world_topic() == "wildlife"
    m._log_event("mature", "Plot reached full maturity", 0)
    assert m.real_world_topic() == "carbon"
    m._log_event("flood", "A flood", 0)  # unmapped kinds fall back to the last mapped one
    assert m.real_world_topic() == "carbon"


def test_stakeholder_requests_pick_community_or_funding_examples(game_env):
    m = game_env.module
    m.pending_stakeholder_request = {"plot_index": 0, "reason": "housing", "kind": m.STAKEHOLDER_KIND_CLEAR}
    assert m.real_world_topic() == "community"
    m.pending_stakeholder_request = {"plot_index": 0, "reason": "incentive", "kind": m.STAKEHOLDER_KIND_INCENTIVE}
    assert m.real_world_topic() == "funded_restoration"
    m.pending_stakeholder_request = {"plot_index": 0, "reason": "replant_fund", "kind": m.STAKEHOLDER_KIND_REPLANT_GRANT}
    assert m.real_world_topic() == "funded_restoration"
    assert m.REAL_WORLD_EXAMPLES["funded_restoration"]["title"] in _shown(game_env)


def test_source_line_names_the_page_and_read_date(game_env):
    m = game_env.module
    for topic, ex in m.REAL_WORLD_EXAMPLES.items():
        m.pending_stakeholder_request = None
        m.forest_log.clear()
        m.forest_tick = m.REAL_WORLD_ORDER.index(topic) * m.REAL_WORLD_ROTATE_TICKS
        m.render()
        link = game_env.elements["real-world-source"]
        assert link.innerText == f"Source: {ex['source']} (read 2026-09-27)"
        assert link.href == ex["url"]


def test_it_never_changes_a_run(game_env):
    m = game_env.module
    m.select_plot(0)
    before = (m.get_state(), m.total_income, m.community_relations)
    for _ in range(3):
        m.render()
    assert (m.get_state(), m.total_income, m.community_relations) == before
