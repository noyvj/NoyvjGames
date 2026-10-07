"""GB-9: the Ranger contracts board (three open contracts, income rewards, ten collectable stamps)."""

import json

import pytest

from .gb_helpers import decline_requests, make_mature, toast_text


def board_types(m):
    return [c["type"] for c in m.contract_board]


def put_contract(m, type_id):
    """Replaces the board with one contract of `type_id` taken from the live forest."""
    target, base = m._contract_target_and_base(type_id)
    m.contract_board[:] = [{"type": type_id, "target": target, "base": base}]
    m.contract_refill_ticks = 99  # keep the empty slots empty so the test sees one contract
    return m.contract_board[0]


# --- the board ------------------------------------------------------------------------------------------------

def test_a_fresh_forest_opens_with_three_different_contracts(game_env):
    m = game_env.module
    assert len(m.contract_board) == m.CONTRACT_SLOTS == 3
    assert len(set(board_types(m))) == 3
    valid = {t[0] for t in m.CONTRACT_TYPES}
    assert set(board_types(m)) <= valid and len(valid) == 10


def test_no_contract_starts_already_finished(game_env):
    m = game_env.module
    for type_id, _icon, _name in m.CONTRACT_TYPES:
        target, base = m._contract_target_and_base(type_id)
        assert m._contract_progress({"type": type_id, "target": target, "base": base}) < target, type_id


@pytest.mark.parametrize("size,plots", [("small", 16), ("normal", 36), ("large", 72)])
def test_targets_and_rewards_scale_with_the_grid(game_env, size, plots):
    m = game_env.module
    m.reset_session(grid_size=size)
    assert m.contract_reward() == m.CONTRACT_REWARD_PER_PLOT * plots
    assert m._contract_target_and_base("mature")[0] == max(2, plots // 6)
    assert m._contract_target_and_base("wildlife")[0] == max(3, plots // 5)
    assert m._contract_target_and_base("standing")[0] >= 60 * plots


def test_the_board_is_deterministic(game_env):
    m = game_env.module
    first = [dict(c) for c in m.contract_board]
    m.reset_session()
    assert [dict(c) for c in m.contract_board] == first


def test_every_contract_has_readable_text(game_env):
    m = game_env.module
    for type_id, _icon, _name in m.CONTRACT_TYPES:
        target, base = m._contract_target_and_base(type_id)
        text = m.contract_text({"type": type_id, "target": target, "base": base})
        assert text and "{" not in text


# --- completing each kind ---------------------------------------------------------------------------------------

def test_replant_contract(game_env):
    m = game_env.module
    put_contract(m, "replant")
    for index in range(3):
        game_env.select(index)
        game_env.clear()
        game_env.replant()
    game_env.tick()
    assert m.contracts_completed == 1 and "replant" in m.contract_stamps


def test_mature_contract(game_env):
    m = game_env.module
    contract = put_contract(m, "mature")
    for index in range(contract["target"]):
        make_mature(m, index)
    game_env.tick()
    assert m.contracts_completed == 1 and "mature" in m.contract_stamps


def test_wildlife_contract(game_env):
    m = game_env.module
    contract = put_contract(m, "wildlife")
    for index in range(contract["target"]):
        m.plots[index].biodiversity = m.BIODIVERSITY_WILDLIFE_THRESHOLD + 1
    game_env.tick()
    assert "wildlife" in m.contract_stamps


def test_decline_contract_counts_declines_after_it_was_offered(game_env):
    m = game_env.module
    m.stakeholder_declines_count = 5  # earlier declines do not count
    put_contract(m, "decline")
    decline_requests(game_env, 0, 1)
    game_env.tick()
    assert m.contracts_completed == 0
    decline_requests(game_env, 1, 1)
    game_env.tick()
    assert "decline" in m.contract_stamps


def test_accept_contract_counts_a_granted_request(game_env):
    m = game_env.module
    put_contract(m, "accept")
    m.pending_stakeholder_request = {"plot_index": 4, "reason": "housing", "kind": "clear"}
    game_env.grant_stakeholder()
    game_env.tick()
    assert "accept" in m.contract_stamps


def test_tend_contract(game_env):
    m = game_env.module
    put_contract(m, "tend")
    game_env.tick(2)
    assert m.tend_plot(0) is True
    game_env.tick(m.TEND_DURATION_TICKS + m.TEND_COOLDOWN_TICKS)
    assert m.contracts_completed == 0 and m.tends_done == 1
    assert m.tend_plot(1) is True
    game_env.tick()
    assert "tend" in m.contract_stamps and m.tends_done == 2


def test_seedling_contract(game_env):
    m = game_env.module
    put_contract(m, "seedling")
    game_env.select(2)
    game_env.clear()
    m.golden_seedling = {"plot": 2, "ticks_left": 3}
    assert m.collect_golden_seedling() is True
    assert m.seedlings_caught == 1
    game_env.tick()
    assert "seedling" in m.contract_stamps


def test_standing_contract(game_env):
    m = game_env.module
    contract = put_contract(m, "standing")
    for plot in m.plots:
        plot.value = contract["target"] / len(m.plots) + 5
    game_env.tick()
    assert "standing" in m.contract_stamps


def test_calm_contract_restarts_when_a_plot_is_cleared(game_env):
    m = game_env.module
    put_contract(m, "calm")
    game_env.tick(m.CONTRACT_CALM_TICKS - 5)
    game_env.select(0)
    game_env.clear()
    game_env.tick(10)
    assert m.contracts_completed == 0
    assert m.contract_last_clear_tick >= m.CONTRACT_CALM_TICKS - 4
    game_env.tick(m.CONTRACT_CALM_TICKS)
    assert "calm" in m.contract_stamps


def test_an_undone_clear_does_not_restart_the_calm_clock(game_env):
    m = game_env.module
    game_env.tick(3)
    before = m.contract_last_clear_tick
    game_env.select(0)
    game_env.clear()
    m.undo_last_clear()
    game_env.tick()
    assert m.contract_last_clear_tick == before


def test_trust_contract(game_env):
    m = game_env.module
    contract = put_contract(m, "trust")
    assert contract["target"] > m.community_relations
    m.community_relations = contract["target"]
    game_env.tick()
    assert "trust" in m.contract_stamps


def test_trust_is_not_offered_when_relations_are_already_near_full(game_env):
    m = game_env.module
    m.community_relations = 95
    m.contract_board[:] = []
    for tick in range(60):
        m.forest_tick = tick
        assert m._pick_contract_type() != "trust"


# --- rewards, stamps, refills, ranks ---------------------------------------------------------------------------

def test_completing_a_contract_pays_logs_toasts_and_stamps(game_env):
    m = game_env.module
    put_contract(m, "replant")
    income_before = m.total_income
    for index in range(3):
        game_env.select(index)
        game_env.clear()
        game_env.replant()
    cleared_income = m.total_income
    game_env.tick()
    assert m.total_income - cleared_income >= m.contract_reward()
    assert m.total_income > income_before
    assert any(e["kind"] == "contract" for e in m.forest_log)
    assert "Contract done" in toast_text(game_env) and "Replanter" in toast_text(game_env)
    assert m.contracts_completed == 1 and m.contract_board == []


def test_a_finished_slot_refills_after_the_wait_and_prefers_unstamped_types(game_env):
    m = game_env.module
    put_contract(m, "tend")
    m.contract_refill_ticks = 0
    m.tends_done = 5
    m.contract_board[0]["base"] = 0
    game_env.tick()
    assert m.contracts_completed == 1 and m.contract_board == []
    game_env.tick(m.CONTRACT_REFILL_TICKS - 1)
    assert m.contract_board == []  # the slot waits CONTRACT_REFILL_TICKS ticks after the completion tick
    game_env.tick()
    assert len(m.contract_board) == 1
    assert "tend" not in board_types(m)  # already stamped, and unstamped types come first


def test_stamps_are_never_reissued_while_others_remain(game_env):
    m = game_env.module
    names = [t[0] for t in m.CONTRACT_TYPES]
    m.contract_board[:] = []
    m.contract_stamps[:] = names[:9]
    m.community_relations = 50
    picked = m._pick_contract_type()
    assert picked == names[9]
    m.contract_stamps[:] = names
    assert m._pick_contract_type() in names  # once all ten are stamped, any type can come round again


def test_ranks_follow_the_completed_count(game_env):
    m = game_env.module
    for done, rank in ((0, "Trainee"), (3, "Ranger"), (8, "Senior ranger"), (15, "Warden"), (30, "Chief warden")):
        m.contracts_completed = done
        assert m.contract_rank() == rank


def test_contracts_cannot_pay_twice_for_the_same_progress(game_env):
    m = game_env.module
    put_contract(m, "standing")
    for plot in m.plots:
        plot.value = 5000.0
    game_env.tick()
    income_after_first = m.total_income
    game_env.tick()
    assert m.contracts_completed == 1
    assert m.total_income - income_after_first < m.contract_reward()


# --- challenge runs close the board -----------------------------------------------------------------------------

def test_the_board_is_closed_during_a_challenge(game_env):
    m = game_env.module
    m.reset_session(challenge="pacifist")
    assert m.contract_board == []
    game_env.tick(10)
    assert m.contract_board == [] and m.contracts_completed == 0
    assert "closed" in game_env.elements["contracts-toggle-button"].innerText
    game_env.toggle_contracts()
    panel = game_env.elements["contracts-panel"]
    assert any("closed during a challenge" in getattr(c, "innerText", "") for c in panel.children)
    assert "ranger_contracts" not in m.get_state()


def test_leaving_the_challenge_reopens_the_board(game_env):
    m = game_env.module
    m.reset_session(challenge="sprint")
    m.reset_session(challenge="none")
    assert len(m.contract_board) == 3


# --- the panel ---------------------------------------------------------------------------------------------------

def test_the_panel_opens_closes_and_lists_every_open_contract(game_env):
    m = game_env.module
    panel = game_env.elements["contracts-panel"]
    toggle = game_env.elements["contracts-toggle-button"]
    assert panel.hidden is True and "3 open" in toggle.innerText
    game_env.toggle_contracts()
    assert panel.hidden is False and toggle.innerText.startswith("Hide Contracts")
    lists = [c for c in panel.children if c.className == "contracts-list"]
    assert len(lists) == 1 and len(lists[0].children) == 3
    card = lists[0].children[0]
    assert [c.className for c in card.children] == ["contract-card-label", "contract-card-progress", "contract-card-bar"]
    assert card.children[2].max == m.contract_board[0]["target"]
    game_env.toggle_contracts()
    assert panel.hidden is True


def test_the_panel_stays_live_as_progress_moves(game_env):
    m = game_env.module
    put_contract(m, "tend")
    game_env.toggle_contracts()
    game_env.tick(2)
    m.tend_plot(0)
    panel = game_env.elements["contracts-panel"]
    card = [c for c in panel.children if c.className == "contracts-list"][0].children[0]
    assert card.children[1].innerText == "1 of 2"


def test_the_panel_shows_stamps_as_silhouettes_until_earned(game_env):
    m = game_env.module
    m.contract_stamps[:] = ["tend"]
    game_env.toggle_contracts()
    panel = game_env.elements["contracts-panel"]
    headings = [c.innerText for c in panel.children if c.className == "almanac-heading"]
    assert "Stamps (1/10)" in headings
    row = [c for c in panel.children if c.className == "almanac-list"][0]
    names = [item.children[1].innerText for item in row.children]
    assert names.count("???") == 9 and "Gardener" in names


def test_an_empty_board_says_when_the_next_contract_comes(game_env):
    m = game_env.module
    m.contract_board[:] = []
    m.contract_refill_ticks = 4
    game_env.toggle_contracts()
    panel = game_env.elements["contracts-panel"]
    board = [c for c in panel.children if c.className == "contracts-list"][0]
    assert "Next contract in 4 ticks" in board.children[0].innerText


# --- saves -------------------------------------------------------------------------------------------------------

def test_a_fresh_forest_writes_no_contract_key(game_env):
    assert "ranger_contracts" not in game_env.module.get_state()


def test_the_board_stamps_and_counters_survive_a_save_and_load(game_env):
    m = game_env.module
    put_contract(m, "replant")
    for index in range(3):
        game_env.select(index)
        game_env.clear()
        game_env.replant()
    game_env.tick(3)
    m.tends_done = 4
    snapshot = json.loads(json.dumps(m.get_state()))
    board = [dict(c) for c in m.contract_board]
    assert snapshot["ranger_contracts"]["stamps"] == ["replant"]
    m.reset_session()
    m.load_state(snapshot)
    assert [dict(c) for c in m.contract_board] == board
    assert m.contract_stamps == ["replant"] and m.contracts_completed == 1 and m.tends_done == 4


def test_loading_an_older_save_gives_a_fresh_board(game_env):
    m = game_env.module
    game_env.tick(2)
    snapshot = json.loads(json.dumps(m.get_state()))
    m.contract_board[:] = []
    m.contracts_completed = 9
    m.load_state(snapshot)
    assert len(m.contract_board) == 3 and m.contracts_completed == 0


@pytest.mark.parametrize("junk", [
    "board", 5, None, [], {"board": "x"}, {"board": [1, "a", None]},
    {"board": [{"type": "nope", "target": 3}]},
    {"board": [{"type": "tend", "target": float("nan")}]},
    {"board": [{"type": "tend", "target": "3"}]},
    {"board": [{"type": "tend", "target": 0}]},
    {"board": [{"type": "tend", "target": True}]},
    {"board": [{"type": ["tend"], "target": 2}]},
    {"stamps": "x", "completed": "many", "refill": [], "tends": -4, "seedlings": float("inf")},
])
def test_malformed_contract_blobs_never_break_the_game(game_env, junk):
    m = game_env.module
    snapshot = json.loads(json.dumps(m.get_state()))
    snapshot["ranger_contracts"] = junk
    assert m.load_state(snapshot) is True
    game_env.tick(5)
    assert len(m.contract_board) <= m.CONTRACT_SLOTS
    assert all(c["type"] in {t[0] for t in m.CONTRACT_TYPES} and c["target"] >= 1 for c in m.contract_board)
    assert m.contracts_completed >= 0 and m.tends_done >= 0 and m.seedlings_caught >= 0


def test_a_save_keeps_at_most_three_distinct_contracts(game_env):
    m = game_env.module
    snapshot = json.loads(json.dumps(m.get_state()))
    snapshot["ranger_contracts"] = {"board": [
        {"type": "tend", "target": 2, "base": 0}, {"type": "tend", "target": 2, "base": 0},
        {"type": "calm", "target": 30}, {"type": "replant", "target": 3}, {"type": "trust", "target": 70},
    ]}
    m.load_state(snapshot)
    assert board_types(m) == ["tend", "calm", "replant"]
