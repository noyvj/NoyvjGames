"""2026-10-09 pass: D-19 affordability and pin, D-20 net-funds chip, GD-19 pinned goal, GD-25 quiet seasons,
GD-26 harbour-name dice."""

import pytest


@pytest.fixture
def storage(game_env, monkeypatch):
    store = {}
    monkeypatch.setattr(game_env.module, "_read_local_storage_item", lambda key: store.get(key))
    monkeypatch.setattr(game_env.module, "_write_local_storage_item", lambda key, value: store.__setitem__(key, value))
    return store


# ---- D-20 net-funds chip ----

def test_preview_shows_funds_after_buying_and_after_upkeep(game_env):
    m = game_env.module
    assert m.net_funds_preview("output")["after_purchase"] == m.STARTING_FUNDS - m.INVEST_COST["output"]
    assert m.net_funds_preview("output")["upkeep"] == 0
    m.state.heritage["lighthouse"] = m.HERITAGE_PROTECTED
    p = m.net_funds_preview("output")
    assert p["upkeep"] == m.HERITAGE_UPKEEP and p["after_upkeep"] == p["after_purchase"] - m.HERITAGE_UPKEEP
    assert "after this season's upkeep of 6" in m.net_funds_text("output")


def test_preview_says_what_is_missing_when_unaffordable(game_env):
    m = game_env.module
    m.state.funds = 10
    p = m.net_funds_preview("adaptation")
    assert p["affordable"] is False
    assert "20 more funds are needed" in m.net_funds_text("adaptation")
    assert m.net_funds_text("nonsense") == ""


def test_chip_follows_hover_and_clears_on_leave(game_env):
    chip = game_env.elements["net-funds-chip"]
    game_env.elements["output-invest-button"].dispatch("mouseenter", None)
    assert "Output" in chip.innerText and "after buying" in chip.innerText
    game_env.elements["output-invest-button"].dispatch("mouseleave", None)
    assert chip.innerText == ""
    game_env.elements["reduction-invest-button"].dispatch("focus", None)
    assert "Acidity Reduction" in chip.innerText
    game_env.elements["reduction-invest-button"].dispatch("blur", None)
    assert chip.innerText == ""


# ---- D-19 affordability ----

def test_seasons_to_afford(game_env):
    m = game_env.module
    assert m.seasons_to_afford(100, funds=150, income=5) == 0
    assert m.seasons_to_afford(100, funds=40, income=20) == 3
    assert m.seasons_to_afford(100, funds=40, income=0) is None
    assert m.seasons_to_afford(100, funds=40, income=-3) is None


def test_net_income_uses_output_diversification_and_upkeep(game_env):
    m = game_env.module
    assert m.season_net_income() == 0
    m.state.capacity["output"] = 5
    income = m.season_net_income()
    assert income == pytest.approx(5 * m.OUTPUT_INCOME_PER_UNIT * m.state.fish_yield_multiplier())
    m.state.heritage["lighthouse"] = m.HERITAGE_PROTECTED
    assert m.season_net_income() == pytest.approx(income - m.HERITAGE_UPKEEP)


def test_targets_list_the_tiers_ahead_and_open_diversification(game_env):
    m = game_env.module
    ids = [t[0] for t in m.afford_targets()]
    assert ids[:4] == ["tier1", "tier2", "tier3", "tier4"] and "div-tourism" in ids and "div-aquaculture" in ids
    cost_tier1 = dict((t[0], t[2]) for t in m.afford_targets())["tier1"]
    assert cost_tier1 == 3 * m.INVEST_COST["adaptation"]
    m.state.capacity["adaptation"] = 6
    assert [t[0] for t in m.afford_targets()][0] == "tier3"
    m.state.diversification["tourism"] = m.DIVERSIFY_MAX_LEVEL
    assert "div-tourism" not in [t[0] for t in m.afford_targets()]


def test_lines_say_when_and_mark_the_pinned_target(game_env, storage):
    m = game_env.module
    m.state.funds = 1000
    assert any("tier 1" in l and "affordable now" in l for l in m.afford_lines())
    m.state.funds = 0
    assert any("not affordable at current income" in l for l in m.afford_lines())
    m.state.capacity["output"] = 10
    assert any("affordable in" in l and "season" in l for l in m.afford_lines())


def test_pin_is_remembered_and_shown(game_env, storage):
    m = game_env.module
    game_env.elements["afford-pin-select"].value = "tier2"
    m.on_afford_pin_change()
    assert storage[m.AFFORD_PIN_KEY] == "tier2"
    assert any(l.startswith("\U0001F4CC") for l in m.afford_lines())
    assert "Seawalls" in game_env.elements["afford-pinned"].innerText
    m.load_afford_pin()
    assert m.afford_pin == "tier2"
    m.state.capacity["adaptation"] = 6  # the pinned tier is reached: the pin quietly drops from the list
    m.render_afford()
    assert game_env.elements["afford-pinned"].innerText == ""


# ---- GD-25 quiet seasons ----

def test_quiet_seasons_count_back_from_the_latest(game_env):
    m = game_env.module
    s = m.state
    assert s.quiet_seasons() == 0
    s.acidity_history = [0.0, 0.0, 0.0]
    assert s.quiet_seasons() == 3
    s.acidity_history = [1.0, 2.0, 2.0, 1.5, 1.5]
    assert s.quiet_seasons() == 3
    s.acidity_history = [1.0, 2.0, 3.0]
    assert s.quiet_seasons() == 0


def test_quiet_display_gets_a_star_frame_at_five_and_ten(game_env):
    m = game_env.module
    el = game_env.elements["quiet-seasons-display"]
    m.state.acidity_history = [0.0] * 4
    m.render_quiet()
    assert "quiet-glow" not in el.className and "★" not in el.innerText
    m.state.acidity_history = [0.0] * 5
    m.render_quiet()
    assert "quiet-glow-5" in el.className and el.innerText.endswith("★")
    m.state.acidity_history = [0.0] * 10
    m.render_quiet()
    assert "quiet-glow-10" in el.className and el.innerText.endswith("★★")


# ---- GD-19 pinned goal ----

def test_pinning_and_progress(game_env):
    m = game_env.module
    assert m.goal_progress() is None
    assert m.pin_goal("nope") is False
    assert m.pin_goal("rows4") is True
    label, current, target, reached = m.goal_progress()
    assert label == "Keep 4 rows dry" and target == 4 and reached == (current >= 4)
    assert m.pin_goal("") is True and m.goal_progress() is None


def test_the_ping_fires_once_when_the_goal_is_reached(game_env):
    m = game_env.module
    m.pin_goal("funds500")
    assert m.check_pinned_goal() is False
    m.state.funds = 600
    assert m.check_pinned_goal() is True
    assert any("Goal reached" in line for line in m.state.ticker_log)
    assert any("Goal reached" in e["text"] for e in m.state.chronicle)
    assert m.check_pinned_goal() is False  # once only


def test_pinning_a_goal_already_met_does_not_ping(game_env):
    m = game_env.module
    m.state.funds = 900
    m.pin_goal("funds500")
    assert m.state.pinned_goal_reached is True and m.check_pinned_goal() is False


def test_goal_is_checked_after_investing_and_advancing(game_env):
    m = game_env.module
    m.state.capacity["adaptation"] = 2
    m.pin_goal("tier3")
    m.state.funds = 1000
    for _ in range(4):
        game_env.invest("adaptation")
    assert not m.state.pinned_goal_reached  # tier 3 needs 10
    m.state.capacity["adaptation"] = 9
    game_env.invest("adaptation")
    assert m.state.pinned_goal_reached is True


def test_goal_ui_and_save(game_env):
    m = game_env.module
    game_env.elements["goal-select"].value = "pop200"
    m.on_goal_change()
    assert m.state.pinned_goal == "pop200"
    assert "Pinned goal" not in game_env.elements["goal-text"].innerText and "Reach 200 population" in game_env.elements["goal-text"].innerText
    assert "pinned_goal" in m.get_state() and m.get_state()["pinned_goal"]["id"] == "pop200"
    state = m.get_state()
    m.pin_goal("")
    assert "pinned_goal" not in m.get_state()
    m.load_state(state)
    assert m.state.pinned_goal == "pop200"
    state["pinned_goal"] = {"id": "nonsense", "reached": True}
    m.load_state(state)
    assert m.state.pinned_goal == "" and m.state.pinned_goal_reached is False
    state["pinned_goal"] = "oops"
    m.load_state(state)
    assert m.state.pinned_goal == ""


# ---- GD-26 name dice ----

def test_names_walk_the_list_and_never_repeat_the_current_one(game_env):
    m = game_env.module
    seen = [m.roll_harbor_name() for _ in range(len(m.HARBOR_NAMES))]
    assert all(n in m.HARBOR_NAMES for n in seen) and len(set(seen)) > len(seen) // 2
    m.state.settlement_name = seen[0]
    assert all(m.roll_harbor_name() != seen[0] for _ in range(40))


def test_rolling_sets_the_name_the_input_and_the_chronicle(game_env):
    m = game_env.module
    game_env.elements["roll-name-button"].dispatch("click", None)
    name = m.state.settlement_name
    assert name in m.HARBOR_NAMES and game_env.elements["settlement-name-input"].value == name
    assert any(e["text"] == f"Founded as {name}." for e in m.state.chronicle)
    game_env.elements["roll-name-button"].dispatch("click", None)
    second = m.state.settlement_name
    assert second != name and any(e["text"] == f"The harbour came to be called {second}." for e in m.state.chronicle)
    assert len(m.state.settlement_name) <= m.SETTLEMENT_NAME_MAX
    assert all(len(n) <= m.SETTLEMENT_NAME_MAX for n in m.HARBOR_NAMES)
