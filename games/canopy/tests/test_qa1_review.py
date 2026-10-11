"""QA-1 code-review regressions: damaged saves must not break the game, a reforestation partnership survives a
save, and achievements already earned in this browser are not taken back by loading another forest's save."""

import copy

import pytest

JUNK = ["x", None, -5, 10 ** 12, 1.5, True, [], {}, [1, "a"], float("nan")]


def _played(game_env):
    game_env.select(0)
    game_env.clear()
    game_env.replant()
    game_env.tick(3)
    return game_env.module.get_state()


@pytest.mark.parametrize("junk", JUNK)
def test_a_damaged_top_level_field_never_breaks_a_load_or_the_next_ticks(game_env, junk):
    m = game_env.module
    base = _played(game_env)
    for key in base:
        state = copy.deepcopy(base)
        state[key] = junk
        assert m.load_state(state) is True, key
        game_env.tick(3)
        m.get_state()
        m.load_state(copy.deepcopy(base))


@pytest.mark.parametrize("junk", JUNK)
def test_a_damaged_plot_field_never_breaks_a_load_or_the_next_ticks(game_env, junk):
    m = game_env.module
    base = _played(game_env)
    for region in ("plots", "highland_plots"):
        for key in base[region][0]:
            state = copy.deepcopy(base)
            state[region][0][key] = junk
            assert m.load_state(state) is True, (region, key)
            game_env.tick(3)
            m.get_state()
            m.load_state(copy.deepcopy(base))


def test_a_damaged_value_keeps_the_live_one_and_indexes_are_range_checked(game_env):
    m = game_env.module
    base = _played(game_env)
    live = m.plots[1].value
    state = copy.deepcopy(base)
    state["plots"][1]["value"] = "lots"
    state["plots"][1]["state"] = "burning"
    state["selected_index"] = 9999
    state["adopted_plot_index"] = -1
    state["community_relations"] = 5000
    assert m.load_state(state) is True
    assert m.plots[1].value == live and m.plots[1].state in (m.PRESERVED, m.BARE, m.REPLANTING, m.RECOVERED)
    assert m.selected_index is None and m.adopted_plot_index is None
    assert m.community_relations == 100


def test_a_pending_request_the_game_could_not_have_made_is_dropped(game_env):
    m = game_env.module
    base = _played(game_env)
    for bad in ({"plot_index": 999, "reason": "housing"}, {"plot_index": 0, "reason": "nonsense"},
                {"plot_index": 0, "reason": "housing", "kind": "mystery"}, "x"):
        state = copy.deepcopy(base)
        state["pending_stakeholder_request"] = bad
        assert m.load_state(state) is True
        assert m.pending_stakeholder_request is None
    good = copy.deepcopy(base)
    reason = m.STAKEHOLDER_REASONS[0]
    good["pending_stakeholder_request"] = {"plot_index": 0, "reason": reason, "kind": m.STAKEHOLDER_KIND_CLEAR}
    m.load_state(good)
    assert m.pending_stakeholder_request["reason"] == reason


def test_load_state_of_something_that_is_not_a_dict_is_refused(game_env):
    assert game_env.module.load_state(None) is False
    assert game_env.module.load_state([1, 2]) is False


def test_a_reforestation_partnership_survives_a_save(game_env):
    m = game_env.module
    game_env.select(0)
    game_env.clear()
    assert m.plots[0].replant(partner=True)
    assert m.plots[0].partner_share == m.PARTNER_SHARE_RATIO
    saved = m.get_state()
    assert saved["plots"][0]["partner_share"] == m.PARTNER_SHARE_RATIO
    assert "partner_share" not in saved["plots"][1]            # the save shape only grows where it is used
    m.reset_session(_render_after=False)
    assert m.plots[0].partner_share == 0.0
    m.load_state(saved)
    assert m.plots[0].partner_share == m.PARTNER_SHARE_RATIO
    saved["plots"][0]["partner_share"] = 7                      # out of range: clamped, never more than the whole value
    m.load_state(saved)
    assert m.plots[0].partner_share == 1.0
    del saved["plots"][0]["partner_share"]
    m.load_state(saved)
    assert m.plots[0].partner_share == 0.0


def test_loading_another_forests_save_does_not_take_back_earned_achievements(game_env):
    m = game_env.module
    m.total_income = m.QUICK_MONEY_THRESHOLD
    assert "quick_money" in m.achievement_ids_earned()
    other_forest = {"plots": [], "achievements_earned": []}
    assert m.load_state(other_forest) is True
    assert "quick_money" in m.achievement_ids_earned()
