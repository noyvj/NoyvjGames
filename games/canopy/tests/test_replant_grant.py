"""B25: "community grant" -- a stakeholder offers funding specifically for
replanting a bare plot."""


def _drive_to_request(game_env, n, keep_bare=None):
    """Ticks until the n-th request (1-based) is pending, declining earlier
    ones. `keep_bare` plot indices are cleared first so a grant is possible."""
    m = game_env.module
    for i in keep_bare or []:
        m.plots[i].clear()
    for _ in range(n - 1):
        game_env.tick(m.STAKEHOLDER_EVENT_INTERVAL_TICKS)
        assert m.pending_stakeholder_request is not None
        game_env.decline_stakeholder()
    game_env.tick(m.STAKEHOLDER_EVENT_INTERVAL_TICKS)


def test_eighth_request_is_a_replant_grant_when_a_plot_is_bare(game_env):
    m = game_env.module
    _drive_to_request(game_env, 8, keep_bare=[0])
    req = m.pending_stakeholder_request
    assert req["kind"] == m.STAKEHOLDER_KIND_REPLANT_GRANT
    assert m.plots[req["plot_index"]].state == m.BARE


def test_eighth_request_falls_back_to_normal_incentive_without_bare_plots(game_env):
    m = game_env.module
    _drive_to_request(game_env, 8)
    assert m.pending_stakeholder_request["kind"] == m.STAKEHOLDER_KIND_INCENTIVE


def test_first_incentive_is_unchanged_even_with_bare_plots(game_env):
    m = game_env.module
    _drive_to_request(game_env, 4, keep_bare=[0])
    assert m.pending_stakeholder_request["kind"] == m.STAKEHOLDER_KIND_INCENTIVE


def test_accepting_replants_and_pays_grant(game_env):
    m = game_env.module
    _drive_to_request(game_env, 8, keep_bare=[0])
    idx = m.pending_stakeholder_request["plot_index"]
    income = m.total_income
    relations = m.community_relations
    replants = m.total_replants
    m.grant_stakeholder_request()
    assert m.plots[idx].state == m.REPLANTING
    assert m.total_income == income + m.REPLANT_GRANT_INCOME_BONUS
    assert m.community_relations == min(100, relations + m.REPLANT_GRANT_RELATIONS_DELTA)
    assert m.total_replants == replants + 1
    assert any(e["kind"] == "replant" and "grant" in e["text"] for e in m.forest_log)


def test_declining_costs_nothing(game_env):
    m = game_env.module
    _drive_to_request(game_env, 8, keep_bare=[0])
    idx = m.pending_stakeholder_request["plot_index"]
    relations = m.community_relations
    income = m.total_income
    m.decline_stakeholder_request()
    assert m.plots[idx].state == m.BARE
    assert m.community_relations == relations
    assert m.total_income == income
    assert m.plots[idx].requests_survived == 0


def test_message_and_labels(game_env):
    m = game_env.module
    _drive_to_request(game_env, 8, keep_bare=[0])
    m.render()
    assert "replant" in m.stakeholder_request_message().lower()
    assert game_env.elements["stakeholder-grant-button"].innerText == "Accept"
    assert "replants" in game_env.elements["stakeholder-grant-button"].title
    assert "Incentive" in game_env.elements["stakeholder-badge"].innerText


def test_stale_when_target_is_replanted_directly(game_env):
    m = game_env.module
    _drive_to_request(game_env, 8, keep_bare=[0])
    idx = m.pending_stakeholder_request["plot_index"]
    game_env.select(idx)
    game_env.replant()
    game_env.tick(1)
    assert m.pending_stakeholder_request is None or m.pending_stakeholder_request["plot_index"] != idx


def test_grant_with_stale_target_is_a_noop(game_env):
    m = game_env.module
    _drive_to_request(game_env, 8, keep_bare=[0])
    idx = m.pending_stakeholder_request["plot_index"]
    m.plots[idx].replant()
    income = m.total_income
    assert m.grant_stakeholder_request() is False
    assert m.total_income == income
