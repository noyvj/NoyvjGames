"""Round-2 backlog items (planning/TODO.md, Per-game: Loop): H1, H2, H4,
H6, H8, H12, H14, H15, H16, H18, H20, H22, H24, H26, H27, H28, H30."""


# --- H1: third trading partner --------------------------------------------

def test_overseas_partner_costs_funds_and_adds_import(game_env):
    game_env.chain.funds = 200
    game_env.invest_overseas_trade()
    assert game_env.chain.overseas_trade_investment == 1
    assert game_env.chain.funds == 200 - game_env.module.OVERSEAS_TRADE_COST
    assert game_env.chain.imported_supply() == game_env.module.OVERSEAS_IMPORT_SUPPLY_PER_UNIT


def test_overseas_partner_blocked_when_unaffordable(game_env):
    game_env.chain.funds = 10
    game_env.invest_overseas_trade()
    assert game_env.chain.overseas_trade_investment == 0
    assert game_env.elements["overseas-trade-invest-button"].disabled is True


def test_overseas_ratio_is_distinct_from_other_partners(game_env):
    m = game_env.module
    ratios = {
        m.TRADE_LINK_COST / m.IMPORT_SUPPLY_PER_UNIT,
        m.REGIONAL_TRADE_COST / m.REGIONAL_IMPORT_SUPPLY_PER_UNIT,
        m.OVERSEAS_TRADE_COST / m.OVERSEAS_IMPORT_SUPPLY_PER_UNIT,
    }
    assert len(ratios) == 3


def test_overseas_saves_and_old_saves_default(game_env):
    game_env.chain.funds = 500
    game_env.invest_overseas_trade()
    snap = game_env.module.get_state()
    assert snap["overseas_trade_investment"] == 1
    for key in ("overseas_trade_investment", "first_loop_closed_cycle", "regional_hint_seen"):
        snap.pop(key)
    game_env.module.load_state(snap)
    assert game_env.chain.overseas_trade_investment == 0
    assert game_env.chain.first_loop_closed_cycle is None


# --- H2 / H24: streak progress, cycles since extraction -------------------

def test_streak_progress_text_counts_toward_next_mark(game_env):
    game_env.chain.closed_loop_streak = 2
    assert "2 of 5" in game_env.module.streak_progress_text()
    game_env.chain.closed_loop_streak = 5
    assert "5 of 10" in game_env.module.streak_progress_text()


def test_since_extraction_line_hidden_until_circularity_high(game_env):
    game_env.advance_cycle()
    assert game_env.elements["streak-since-display"].hidden is True
    game_env.chain.funds = 100_000
    for _ in range(10):
        game_env.invest_circularity("recycle")
    assert game_env.elements["streak-since-display"].hidden is False


# --- H4: cosmetic relabel --------------------------------------------------

def test_relabel_hidden_until_chain_started_then_cosmetic_only(game_env):
    panel = game_env.elements["relabel-goods-panel"]
    assert panel.hidden is True
    game_env.advance_cycle()
    assert panel.hidden is False
    tried_before = set(game_env.module.goods_categories_tried)
    funds = game_env.chain.funds
    game_env.elements["relabel-clothing-button"].dispatch("click", None)
    assert game_env.chain.goods_category == "clothing"
    assert game_env.module.goods_categories_tried == tried_before
    assert game_env.chain.funds == funds


# --- H6: burst on 25% milestone crossings ----------------------------------

def test_burst_fires_on_crossing_25_percent_step_only(game_env):
    burst = game_env.elements["circular-burst"]
    game_env.chain.funds = 100_000
    game_env.invest_circularity("recycle")  # 5/50 = 10%: no step crossed
    assert not burst.classList.contains("circular-burst--active")
    game_env.invest_circularity("recycle")  # 20%
    game_env.invest_circularity("recycle")  # 30% -> crosses 25%
    assert burst.classList.contains("circular-burst--active")
    game_env.timers.flush()
    assert not burst.classList.contains("circular-burst--active")
    game_env.invest_circularity("recycle")  # 40%, same step
    assert not burst.classList.contains("circular-burst--active")


# --- H8 / H22 --------------------------------------------------------------

def test_cost_trend_rising_only_when_extraction_raised_cost(game_env):
    assert game_env.chain.extraction_cost_trend() == "steady"
    game_env.advance_cycle()
    assert game_env.chain.extraction_cost_trend() == "rising"
    assert "pricier" in game_env.elements["damage-display"].innerText


def test_cost_trend_steady_when_loop_closed(game_env):
    game_env.chain.funds = 100_000
    for _ in range(10):
        game_env.invest_circularity("recycle")
    game_env.advance_cycle()
    assert game_env.chain.extraction_cost_trend() == "steady"
    assert "pricier" not in game_env.elements["damage-display"].innerText


def test_damage_tooltip_states_ceiling_multiplier(game_env):
    assert "x2.50" in game_env.elements["damage-display"].title


# --- H12 -------------------------------------------------------------------

def test_score_pie_percentages_sum_to_100(game_env):
    game_env.chain.total_produced = 100
    game_env.chain.total_extracted = 0  # fully circular lifetime
    funds_pct, bonus_pct = game_env.module.score_pie_percentages()
    assert funds_pct + bonus_pct == 100
    assert bonus_pct == 50  # 300 funds vs 300 bonus
    game_env.module.render()
    assert "50%" in game_env.elements["score-pie-legend"].innerText


def test_score_pie_style_is_conic_gradient(game_env):
    assert game_env.module.score_pie_style().startswith("conic-gradient(")


# --- H14 -------------------------------------------------------------------

def test_goods_collector_needs_every_category(game_env):
    assert "goods_collector" not in game_env.module.achievement_ids_earned()
    game_env.select_goods_category("clothing")
    game_env.select_goods_category("furniture")
    assert "goods_collector" in game_env.module.achievement_ids_earned()


# --- H15 -------------------------------------------------------------------

def test_audit_suggests_cheapest_source_when_extracting(game_env):
    lines = game_env.module.audit_lines()
    assert any("Cheapest way" in line for line in lines)
    assert "<p>" in game_env.elements["audit-body"].innerHTML


def test_audit_reports_surplus(game_env):
    game_env.chain.circularity_investment["recycle"] = 15  # 75 units vs 50 target
    assert any("exceed the production target" in line for line in game_env.module.audit_lines())


def test_audit_all_clear_when_matched(game_env):
    game_env.chain.circularity_investment["recycle"] = 10  # exactly 50
    assert "Nothing is being wasted" in game_env.module.audit_lines()[0]


# --- H16 -------------------------------------------------------------------

def test_banner_names_first_closed_cycle(game_env):
    game_env.advance_cycle()
    game_env.advance_cycle()
    game_env.chain.funds = 100_000
    for _ in range(10):
        game_env.invest_circularity("recycle")
    assert game_env.chain.first_loop_closed_cycle == 3
    assert "cycle 3" in game_env.elements["loop-closed-banner-text"].innerText


def test_first_closed_cycle_saved_and_restored(game_env):
    game_env.chain.funds = 100_000
    for _ in range(10):
        game_env.invest_circularity("recycle")
    snap = game_env.module.get_state()
    assert snap["first_loop_closed_cycle"] == 1
    game_env.module.load_state(snap)
    assert game_env.chain.first_loop_closed_cycle == 1


# --- H18 -------------------------------------------------------------------

def test_top_investment_node_glows(game_env):
    assert game_env.module.top_investment_measure() is None
    game_env.chain.funds = 1000
    game_env.invest_circularity("repair")
    game_env.invest_circularity("reuse")
    game_env.invest_circularity("reuse")
    assert game_env.module.top_investment_measure() == "reuse"
    assert "loop-ring-node--top" in game_env.elements["loop-ring-node-reuse"].className
    assert "loop-ring-node--top" not in game_env.elements["loop-ring-node-repair"].className


# --- H20 -------------------------------------------------------------------

def test_vignette_session_offset_rotates_variant(game_env):
    game_env.module.vignette_session_offset = 1
    game_env.module.render()
    text_offset = game_env.elements["vignette-display"].innerText
    game_env.module.vignette_session_offset = 0
    game_env.module.render()
    assert game_env.elements["vignette-display"].innerText != text_offset


# --- H26 -------------------------------------------------------------------

def test_pulse_tier_by_size(game_env):
    m = game_env.module
    assert m.pulse_tier(2) == "small"
    assert m.pulse_tier(-10) == "medium"
    assert m.pulse_tier(25) == "large"


def test_pulse_applies_tier_class_and_clears(game_env):
    game_env.chain.funds = 1000
    game_env.invest_trade_link()  # +4 imported units: small
    el = game_env.elements["trade-network-display"]
    assert el.classList.contains("trade-network-display--pulse-small")
    game_env.timers.flush()
    assert not el.classList.contains("trade-network-display--pulse-small")


# --- H27 -------------------------------------------------------------------

def test_featured_category_rotates_weekly(game_env):
    m = game_env.module
    keys = list(m.GOODS_CATEGORIES)
    assert [m.featured_goods_category(w) for w in range(3)] == keys
    assert m.featured_goods_category(3) == keys[0]
    assert "Challenge of the week" in game_env.elements["featured-goods-display"].innerText


# --- H28 -------------------------------------------------------------------

def test_regional_hint_shows_once_then_dismissed(game_env):
    hint = game_env.elements["regional-hint"]
    game_env.chain.funds = 10
    game_env.module.render()
    assert hint.hidden is True
    game_env.chain.funds = 100
    game_env.module.render()
    assert hint.hidden is False
    game_env.elements["regional-hint-dismiss-button"].dispatch("click", None)
    assert hint.hidden is True
    assert game_env.module.get_state()["regional_hint_seen"] is True
    game_env.module.render()
    assert hint.hidden is True


# --- H30 -------------------------------------------------------------------

def test_reset_message_names_surviving_counters(game_env):
    game_env.select_goods_category("clothing")
    game_env.reset_chain()
    msg = game_env.elements["reset-chain-message"]
    assert msg.hidden is False
    assert "1 chain(s) completed" in msg.innerText
    assert "2 goods categories tried" in msg.innerText


def test_ceiling_note_is_visible_text_near_damage_meter(game_env):
    text = game_env.elements["damage-ceiling-note"].innerText
    assert "hard ceiling of x2.50" in text
