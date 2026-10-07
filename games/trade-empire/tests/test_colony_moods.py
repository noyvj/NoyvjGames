"""J-25/J-26 -- colony temperaments (Grateful, Demanding, Opportunistic): derived
from trade history, explained in the colony panel, drawn as a shape on the map,
and each changes how the colony treats the player."""

import pytest


def _trip(game_env, ship_id="1", destination="ferrum"):
    game_env.load(ship_id=ship_id)
    game_env.depart(destination, ship_id=ship_id)
    game_env.tick(game_env.module.TRAVEL_TICKS)


def _fill_calls(game_env):
    ctx = game_env.elements["map-canvas"].getContext("2d")
    ctx.calls.clear()
    game_env.module.render_map()
    return ctx


# ------------------------------------------------------------------ deriving

def test_every_new_colony_starts_opportunistic(game_env):
    m = game_env.module
    assert {s.temperament() for s in m.colony_states.values()} == {"opportunistic"}


def test_well_supplied_colonies_turn_grateful(game_env):
    state = game_env.module.colony_states["ferrum"]
    state.cumulative_delivered = game_env.module.GRATEFUL_DELIVERED - 1
    assert state.temperament() == "opportunistic"
    state.cumulative_delivered = game_env.module.GRATEFUL_DELIVERED
    assert state.temperament() == "grateful"


def test_a_granted_concession_makes_a_colony_grateful(game_env):
    m = game_env.module
    state = m.colony_states["aurum"]
    state.demand_ticks_left = 10
    state.demands_made = 1
    m.total_profit = 500
    assert m.grant_concession("aurum") is True
    assert state.concessions_granted == 1 and state.temperament() == "grateful"


def test_two_unanswered_demands_make_a_colony_demanding(game_env):
    m = game_env.module
    state = m.colony_states["aurum"]
    state.demands_made = 2
    assert state.lapsed_demands() == 2 and state.temperament() == "demanding"
    state.concessions_granted = 1
    assert state.lapsed_demands() == 1 and state.temperament() == "grateful"


def test_an_open_demand_is_not_yet_a_lapsed_one(game_env):
    state = game_env.module.colony_states["aurum"]
    state.demands_made = 2
    state.demand_ticks_left = 5
    assert state.lapsed_demands() == 1 and state.temperament() != "demanding"


def test_the_neglect_loop_counts_demands(game_env):
    m = game_env.module
    state = m.colony_states["aurum"]
    state.need_satisfaction = 0.0
    for _ in range(m.NEGLECT_DEMAND_TICKS):
        state.need_satisfaction = 0.0
        state.update_loyalty()
    assert state.has_demand() and state.demands_made == 1


def test_a_demanding_colony_can_be_won_back_by_answering(game_env):
    m = game_env.module
    state = m.colony_states["aurum"]
    state.demands_made = 3
    assert state.temperament() == "demanding"
    state.concessions_granted = 2
    assert state.temperament() == "grateful"


# ------------------------------------------------------------------- effects

def test_grateful_colonies_pay_a_premium_and_others_do_not(game_env):
    m = game_env.module
    assert m.colony_premium_multiplier("ferrum") == 1.0
    m.colony_states["ferrum"].cumulative_delivered = 80
    assert m.colony_premium_multiplier("ferrum") == pytest.approx(1.04)
    assert m.colony_premium_multiplier("not-a-colony") == 1.0


def test_the_premium_reaches_a_real_sale(game_env):
    m = game_env.module
    m.market_multiplier[m.ORE] = 1.0
    m.colony_states["ferrum"].cumulative_delivered = 80
    ship = m.ships["1"]
    ship.location = "aurum"
    ship.cargo_good, ship.cargo_qty = m.ORE, 10
    ship.depart("ferrum")
    game_env.tick(m.TRAVEL_TICKS)
    assert ship.total_earned == int(round(10 * m.SELL_PRICE[m.ORE] * 1.04))


def test_a_demanding_colony_answers_a_concession_more_strongly(game_env):
    m = game_env.module
    plain = m.colony_states["aurum"]
    plain.need_satisfaction = 0.1
    plain.demand_ticks_left = 5
    plain.demands_made = 1
    plain.grant_concession()
    assert plain.need_satisfaction == pytest.approx(0.1 + m.CONCESSION_SATISFACTION_BOOST)
    pushy = m.colony_states["verdant"]
    pushy.need_satisfaction = 0.1
    pushy.demands_made = 2
    pushy.demand_ticks_left = 0
    assert pushy.temperament() == "demanding"
    pushy.grant_concession()
    assert pushy.need_satisfaction == pytest.approx(0.1 + 0.45)


def test_an_opportunistic_colony_discounts_an_invest_while_its_need_is_low(game_env):
    m = game_env.module
    state = m.colony_states["aurum"]
    state.need_satisfaction = 0.5
    assert m.colony_invest_cost_for("aurum") == m.colony_invest_cost()
    state.need_satisfaction = 0.49
    assert m.colony_invest_cost_for("aurum") == int(round(m.colony_invest_cost() * 0.75))
    m.total_profit = 1000
    assert m.invest_in_colony("aurum") is True
    assert m.total_profit == 1000 - int(round(60 * 0.75))


def test_a_grateful_colony_gets_no_invest_discount(game_env):
    m = game_env.module
    state = m.colony_states["aurum"]
    state.need_satisfaction = 0.1
    state.concessions_granted = 1
    assert m.colony_invest_cost_for("aurum") == m.colony_invest_cost()


def test_the_invest_button_shows_the_discounted_cost(game_env):
    m = game_env.module
    m.colony_states["aurum"].need_satisfaction = 0.2
    m.total_profit = 500
    m.render()
    assert game_env.elements["colony-aurum-invest-button"].innerText == "Invest (45)"


# ------------------------------------------------------------------ explaining

def test_the_colony_panel_explains_the_mood_and_the_history(game_env):
    m = game_env.module
    m.render()
    text = game_env.elements["colony-aurum-temperament"].innerText
    assert "Opportunistic" in text and "square on the map" in text and "25% discount" in text
    m.colony_states["aurum"].cumulative_delivered = 60
    m.colony_states["aurum"].concessions_granted = 2
    m.render()
    text = game_env.elements["colony-aurum-temperament"].innerText
    assert "Grateful" in text and "circle on the map" in text and "60 delivered" in text and "2 concession(s)" in text


def test_every_mood_names_its_glyph_with_a_legend_in_the_page(game_env):
    m = game_env.module
    assert {t["glyph"] for t in m.TEMPERAMENTS.values()} == {"circle", "triangle", "square"}
    html = (__import__("pathlib").Path(m.__file__).parent / "index.html").read_text(encoding="utf-8")
    for word in ("grateful", "demanding", "opportunistic"):
        assert word in html.split('id="map-legend"')[1].split("</p>")[0]


# ------------------------------------------------------------------------ map

def test_glyph_shapes_are_a_circle_a_triangle_and_a_square(game_env):
    m = game_env.module
    assert len(m.temperament_glyph_points("triangle", 0, 0)) == 3
    assert len(m.temperament_glyph_points("square", 0, 0)) == 4
    ring = m.temperament_glyph_points("circle", 0, 0, 5)
    assert len(ring) == 12 and all(abs((x * x + y * y) ** 0.5 - 5) < 1e-9 for x, y in ring)


def test_the_map_draws_one_filled_mood_glyph_per_colony_without_new_arcs_or_strokes(game_env):
    m = game_env.module
    ctx = _fill_calls(game_env)
    arcs_before = sum(1 for n, _ in ctx.calls if n == "arc")
    strokes_before = sum(1 for n, _ in ctx.calls if n == "stroke")
    closes = sum(1 for n, _ in ctx.calls if n == "closePath")
    assert closes >= len(m.COLONIES)
    assert strokes_before == len(m.route_edges())
    assert arcs_before == len(m.COLONIES) + sum(1 for s in m.ships.values() if s.purchased)


def test_a_changed_mood_changes_the_drawn_shape(game_env):
    m = game_env.module
    ctx = _fill_calls(game_env)
    square_corners = sum(1 for n, _ in ctx.calls if n == "lineTo")
    m.colony_states["aurum"].cumulative_delivered = 80  # square (3 lineTo) becomes a 12-gon (11 lineTo)
    ctx = _fill_calls(game_env)
    assert sum(1 for n, _ in ctx.calls if n == "lineTo") == square_corners + 8


# ------------------------------------------------------------------------ save

def test_the_history_counters_round_trip(game_env):
    m = game_env.module
    state = m.colony_states["aurum"]
    state.demands_made, state.concessions_granted = 4, 1
    saved = m.get_state()
    state.demands_made = state.concessions_granted = 0
    m.load_state(saved)
    assert (state.demands_made, state.concessions_granted) == (4, 1)


@pytest.mark.parametrize("bad", [True, -3, 10**9, "7", None, 2.5, [1]])
def test_tampered_history_counters_fall_back_to_zero(game_env, bad):
    m = game_env.module
    saved = m.get_state()
    saved["colony_states"]["aurum"]["demands_made"] = bad
    saved["colony_states"]["aurum"]["concessions_granted"] = bad
    m.load_state(saved)
    state = m.colony_states["aurum"]
    assert (state.demands_made, state.concessions_granted) == (0, 0)


def test_old_saves_without_the_counters_load_as_opportunistic(game_env):
    m = game_env.module
    saved = m.get_state()
    for entry in saved["colony_states"].values():
        entry.pop("demands_made")
        entry.pop("concessions_granted")
    m.load_state(saved)
    assert m.colony_states["aurum"].temperament() == "opportunistic"
