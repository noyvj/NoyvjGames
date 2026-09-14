"""B11 (planning/TODO.md "Per-game: Canopy"): diversify stakeholder
requests so they sometimes offer a positive trade-off (an "incentive"
request) instead of always asking the player to give up a plot (a "clear"
request). Incentive requests never clear the target plot -- accepting
keeps it standing and pays a relations boost + funding bonus; declining
costs nothing."""


def _advance_to_request(game_env, n=1):
    """Ticks through `n` stakeholder-request cycles, declining each one
    along the way (declining a "clear" request is free of side effects on
    plot state, so this is a safe way to fast-forward past earlier
    requests to reach a specific one in the cycle)."""
    m = game_env.module
    for _ in range(n - 1):
        game_env.tick(m.STAKEHOLDER_EVENT_INTERVAL_TICKS)
        game_env.decline_stakeholder()
    game_env.tick(m.STAKEHOLDER_EVENT_INTERVAL_TICKS)


def test_first_three_requests_are_still_clear_kind_in_order(game_env):
    """Preserves the pre-B11 cycling behavior exactly for the first full
    pass through STAKEHOLDER_REASONS."""
    m = game_env.module
    seen = []
    for _ in range(3):
        game_env.tick(m.STAKEHOLDER_EVENT_INTERVAL_TICKS)
        seen.append(
            (m.pending_stakeholder_request["kind"], m.pending_stakeholder_request["reason"])
        )
        game_env.decline_stakeholder()
    assert seen == [
        (m.STAKEHOLDER_KIND_CLEAR, "housing"),
        (m.STAKEHOLDER_KIND_CLEAR, "farming"),
        (m.STAKEHOLDER_KIND_CLEAR, "resources"),
    ]


def test_fourth_request_is_an_incentive(game_env):
    m = game_env.module
    _advance_to_request(game_env, 4)
    assert m.pending_stakeholder_request["kind"] == m.STAKEHOLDER_KIND_INCENTIVE
    assert m.pending_stakeholder_request["reason"] in m.STAKEHOLDER_INCENTIVE_REASONS


def test_incentive_message_uses_accept_framing(game_env):
    m = game_env.module
    _advance_to_request(game_env, 4)
    message = m.stakeholder_request_message()
    assert "Accept" in message
    assert "decline" in message.lower()


def test_grant_button_relabels_to_accept_for_incentive(game_env):
    m = game_env.module
    _advance_to_request(game_env, 4)
    m.render()
    assert game_env.elements["stakeholder-grant-button"].innerText == "Accept"


def test_grant_button_stays_grant_for_clear_request(game_env):
    m = game_env.module
    game_env.tick(m.STAKEHOLDER_EVENT_INTERVAL_TICKS)
    assert m.pending_stakeholder_request["kind"] == m.STAKEHOLDER_KIND_CLEAR
    m.render()
    assert game_env.elements["stakeholder-grant-button"].innerText == "Grant"


def test_accepting_an_incentive_does_not_clear_the_plot(game_env):
    m = game_env.module
    _advance_to_request(game_env, 4)
    target = m.pending_stakeholder_request["plot_index"]
    value_before = m.plots[target].value

    game_env.grant_stakeholder()

    assert m.plots[target].state in m.ACCRUING_STATES  # still standing
    assert m.plots[target].value >= value_before  # untouched (may have accrued this tick)


def test_accepting_an_incentive_pays_a_funding_bonus_and_relations(game_env):
    m = game_env.module
    _advance_to_request(game_env, 4)
    income_before = m.total_income
    relations_before = m.community_relations

    game_env.grant_stakeholder()

    assert m.total_income == income_before + m.STAKEHOLDER_INCENTIVE_INCOME_BONUS
    assert m.community_relations == min(
        100, relations_before + m.STAKEHOLDER_INCENTIVE_ACCEPT_RELATIONS_DELTA
    )
    assert m.pending_stakeholder_request is None


def test_declining_an_incentive_costs_nothing(game_env):
    m = game_env.module
    _advance_to_request(game_env, 4)
    relations_before = m.community_relations
    income_before = m.total_income

    game_env.decline_stakeholder()

    assert m.community_relations == relations_before
    assert m.total_income == income_before
    assert m.pending_stakeholder_request is None


def test_missing_kind_defaults_to_clear_behavior(game_env):
    """A request dict lacking "kind" entirely (an old save predating B11,
    or a hand-built test fixture) must behave exactly like a "clear"
    request rather than crashing on a missing key."""
    m = game_env.module
    m.pending_stakeholder_request = {"plot_index": 0, "reason": "housing"}
    message = m.stakeholder_request_message()
    assert "Grant the request" in message

    relations_before = m.community_relations
    income_before = m.total_income
    m.plots[0].value = 5.0
    game_env.grant_stakeholder()
    assert m.plots[0].state == m.BARE  # cleared, same as a normal "clear" grant
    assert m.total_income == income_before + 5.0
    assert m.community_relations == relations_before + m.STAKEHOLDER_GRANT_RELATIONS_DELTA


def test_incentive_request_still_respects_staleness_guard(game_env):
    """The same clear-directly-instead-of-using-buttons staleness guard
    that protects "clear" requests must also protect incentive ones."""
    m = game_env.module
    _advance_to_request(game_env, 4)
    target = m.pending_stakeholder_request["plot_index"]
    game_env.select(target)
    game_env.clear()  # bypasses Accept/Decline -- request is now stale

    relations_before = m.community_relations
    result = m.grant_stakeholder_request()

    assert result is False
    assert m.community_relations == relations_before
    assert m.pending_stakeholder_request is None
