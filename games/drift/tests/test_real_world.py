"""W2-drift: a sourced real-world example beside the region's situation."""


def _shown(game_env):
    game_env.module.render()
    return game_env.elements["real-world-text"].innerText


def test_every_example_is_sourced(game_env):
    m = game_env.module
    assert set(m.REAL_WORLD_EXAMPLES) == set(m.REAL_WORLD_ORDER)
    assert set(m.REAL_WORLD_POLICY_TOPICS) <= set(m.POLICIES)
    assert 4 <= len(m.REAL_WORLD_EXAMPLES) <= 6
    for topic, ex in m.REAL_WORLD_EXAMPLES.items():
        assert ex["title"] and len(ex["text"]) > 80, topic
        assert ex["url"].startswith("https://") and ex["source"], topic


def test_fresh_region_rotates_deterministically_by_round(game_env):
    m = game_env.module
    seen = []
    for _ in range(len(m.REAL_WORLD_ORDER)):
        m.region.strain_log = []
        topic = m.real_world_topic()
        assert m.REAL_WORLD_EXAMPLES[topic]["title"] in _shown(game_env)
        seen.append(topic)
        m.region.round_number += 1
    assert sorted(seen) == sorted(m.REAL_WORLD_ORDER)
    assert game_env.elements["real-world-note"].hidden is False


def test_strain_shows_the_services_strain_example(game_env):
    m = game_env.module
    m.region.total_arrivals = 500.0  # far above capacity
    assert m.region.strain_level() != "stable"
    assert m.real_world_topic() == "services_strain"
    assert m.REAL_WORLD_EXAMPLES["services_strain"]["title"] in _shown(game_env)


def test_a_second_wave_shows_the_surge_example_ahead_of_strain(game_env):
    m = game_env.module
    m.region.total_arrivals = 500.0
    for status in ("warned", "active"):
        m.region.second_wave_status = status
        assert m.real_world_topic() == "surge"
    assert m.REAL_WORLD_EXAMPLES["surge"]["title"] in _shown(game_env)


def test_each_funded_policy_shows_its_own_example(game_env):
    m = game_env.module
    m.region.total_arrivals = 0.0
    for policy in m.REAL_WORLD_POLICY_TOPICS:
        m.region.policy_level = {p: 0 for p in m.POLICIES}
        m.region.policy_level[policy] = 1
        assert m.region.strain_level() == "stable"
        assert m.real_world_topic() == policy
        assert m.REAL_WORLD_EXAMPLES[policy]["title"] in _shown(game_env)


def test_several_funded_policies_alternate_by_round(game_env):
    m = game_env.module
    m.region.policy_level = {p: 1 for p in m.POLICIES}
    picks = set()
    for _ in range(3):
        picks.add(m.real_world_topic())
        m.region.round_number += 1
    assert picks == set(m.REAL_WORLD_POLICY_TOPICS)


def test_source_line_names_the_page_and_read_date(game_env):
    m = game_env.module
    for topic, ex in m.REAL_WORLD_EXAMPLES.items():
        m.region.second_wave_status = None
        m.region.policy_level = {p: 0 for p in m.POLICIES}
        m.region.total_arrivals = 0.0
        if topic == "surge":
            m.region.second_wave_status = "active"
        elif topic == "services_strain":
            m.region.total_arrivals = 500.0
        elif topic in m.REAL_WORLD_POLICY_TOPICS:
            m.region.policy_level[topic] = 1
        else:
            m.region.round_number = m.REAL_WORLD_ORDER.index(topic)
        assert m.real_world_topic() == topic
        m.render()
        link = game_env.elements["real-world-source"]
        assert link.innerText == f"Source: {ex['source']} (read 2026-09-27)"
        assert link.href == ex["url"]


def test_it_never_changes_a_run(game_env):
    m = game_env.module
    before = m.get_state()
    for _ in range(3):
        m.render()
    assert m.get_state() == before
