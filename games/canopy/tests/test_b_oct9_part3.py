"""B-2 (2026-10-09): the legacy bonus as a chip with a tooltip naming its source and the cap. (part 3 of 3 of the old test_b_oct9.py)."""

from .pagefiles import page_text

# ---- B-9: lifetime statistics ----

def _memory_storage(m):
    store = {}
    m._read_local_storage_item = lambda key: store.get(key)
    m._write_local_storage_item = lambda key, value: store.__setitem__(key, value)
    return store

# ---- GB-1 wildfire season ----

def _wildfire(m):
    m.current_difficulty = m.DIFFICULTY_WILDFIRE
    m._reset_fire()
    for p in m.plots:
        p.state, p.value, p.ticks_intact = m.PRESERVED, 20.0, 5
    m.heart_tree_index = None

def _first_summer_block(m):
    return next(b for b in range(0, 100) if m._season_at(b * m.FIRE_BLOCK_TICKS + 15) == "summer" and m.fire_ignition_tick(b) is not None)


def test_smoke_comes_three_ticks_before_the_spark_and_names_the_plot(game_env):
    m = game_env.module
    _wildfire(m)
    block = _first_summer_block(m)
    due = m.fire_ignition_tick(block)
    m.forest_tick = due - m.FIRE_WARNING_TICKS
    m._fire_tick()
    assert m.fire_warning is not None and m.fire_warning["ticks_left"] == m.FIRE_WARNING_TICKS
    target = m.fire_warning["plot"]
    assert "Smoke over" in m.fire_status_text()
    for _ in range(m.FIRE_WARNING_TICKS):
        m.forest_tick += 1
        m._fire_tick()
    assert target in m.fires and m.fire_warning is None


def test_fire_spreads_to_standing_neighbours_and_burns_out_to_bare(game_env):
    m = game_env.module
    _wildfire(m)
    m.forest_tick = 0  # a calm spring tick, so no new spark interferes
    centre = m.GRID_COLS + 1
    m._ignite(centre)
    m._fire_tick()
    assert set(m.fires) == {centre}
    m._fire_tick()  # age 2: spreads
    assert set(m._edge_neighbours(centre)) <= set(m.fires)
    for _ in range(m.FIRE_BURN_TICKS):
        m._fire_tick()
    assert m.plots[centre].state == m.BARE and m.plots[centre].clear_count == 0
    assert m.fire_value_lost >= 20.0


def test_bare_and_replanting_plots_are_firebreaks_and_the_heart_tree_never_burns(game_env):
    m = game_env.module
    _wildfire(m)
    m.forest_tick = 0
    start = m.GRID_COLS + 1
    left, right, up, down = start - 1, start + 1, start - m.GRID_COLS, start + m.GRID_COLS
    m.plots[left].state = m.BARE
    m.plots[right].state = m.REPLANTING
    m.heart_tree_index = up
    m._ignite(start)
    for _ in range(3):
        m._fire_tick()
    assert left not in m.fires and right not in m.fires and up not in m.fires and down in m.fires


def test_dampen_stops_a_fire_shields_the_plot_and_has_a_cooldown(game_env):
    m = game_env.module
    _wildfire(m)
    m.forest_tick = 0
    m._ignite(7)
    m.selected_index = 7
    assert m.can_dampen(7) is True and m.can_dampen(8) is False
    assert m.dampen_plot() is True
    assert 7 not in m.fires and m.fire_damp[7] == m.FIRE_DAMP_TICKS
    m._ignite(8)
    assert m.dampen_plot(8) is False  # cooling down
    for _ in range(m.FIRE_DAMPEN_COOLDOWN):
        m._fire_tick()
    m._ignite(9)
    assert m.can_dampen(9) is True  # the cooldown is over (the fire on 8 has burned out by now)
    m.fire_damp[10] = 5  # a damp neighbour is not set alight
    for _ in range(3):
        m._fire_tick()
    assert 10 not in m.fires


def test_dampening_the_smoking_plot_cancels_the_spark(game_env):
    m = game_env.module
    _wildfire(m)
    due = m.fire_ignition_tick(_first_summer_block(m))
    m.forest_tick = due - m.FIRE_WARNING_TICKS
    m._fire_tick()
    target = m.fire_warning["plot"]
    assert m.dampen_plot(target) is True and m.fire_warning is None
    for _ in range(5):
        m.forest_tick += 1
        m._fire_tick()
    assert target not in m.fires


def test_clearing_a_burning_plot_puts_it_out_and_new_game_is_calm(game_env):
    m = game_env.module
    _wildfire(m)
    m.forest_tick = 0
    m._ignite(3)
    m.plots[3].clear()
    m._fire_tick()
    assert 3 not in m.fires
    m._ignite(4)
    m.reset_session()
    assert m.fires == {} and m.fire_warning is None


def test_tiles_show_a_glyph_and_the_button_follows_the_difficulty(game_env):
    m = game_env.module
    _wildfire(m)
    m._ignite(2)
    m.fire_warning = {"plot": 5, "ticks_left": 2}
    m.selected_index = 2
    m.render()
    grid = game_env.elements["plot-grid"].children
    assert "plot-burning" in grid[2].className and any(c.className == "fire-mark" for c in grid[2].children)
    assert "plot-smoke" in grid[5].className and "BURNING" in grid[2].getAttribute("data-tooltip")
    assert game_env.elements["dampen-button"].hidden is False and game_env.elements["dampen-button"].disabled is False
    assert game_env.elements["fire-status"].hidden is False
    m.current_difficulty = m.DIFFICULTY_NORMAL
    m.render()
    assert game_env.elements["dampen-button"].hidden is True


def test_wildfire_is_a_valid_difficulty_with_normal_soil_damage_and_a_tag(game_env):
    m = game_env.module
    m.reset_session(difficulty=m.DIFFICULTY_WILDFIRE)
    assert m.current_difficulty == m.DIFFICULTY_WILDFIRE
    assert m.current_degrade_per_clear() == m.DEGRADE_PER_CLEAR * m.vault_soil_factor()
    assert "Wildfire season" in m.session_tag_text()
    state = m.get_state()
    m.reset_session()
    m.load_state(state)
    assert m.current_difficulty == m.DIFFICULTY_WILDFIRE


# ---- GB-24 wetland tides ----

def _wet(m):
    m.wetland_unlocked = True
    m.forest_tick = 0


def test_tide_turns_every_six_ticks_and_half_the_plots_are_under_water(game_env):
    m = game_env.module
    _wet(m)
    n = len(m.wetland_plots)
    for tick in range(0, 30):
        flooded = [i for i in range(n) if m.wetland_plot_flooded(i, tick)]
        assert len(flooded) == n // 2
    assert m.wetland_tide_high(0) is False and m.wetland_tide_high(6) is True and m.wetland_tide_high(12) is False
    now = {i for i in range(n) if m.wetland_plot_flooded(i, 0)}
    later = {i for i in range(n) if m.wetland_plot_flooded(i, 6)}
    assert now.isdisjoint(later) and now | later == set(range(n))
    m.forest_tick = 4
    assert m.wetland_ticks_to_tide_turn() == 2


def test_seedlings_only_go_in_dry_plots_and_mangroves_only_in_flooded_ones(game_env):
    m = game_env.module
    _wet(m)
    flooded = next(i for i in range(len(m.wetland_plots)) if m.wetland_plot_flooded(i))
    dry = next(i for i in range(len(m.wetland_plots)) if not m.wetland_plot_flooded(i))
    for i in (flooded, dry):
        m.wetland_plots[i].state = m.BARE
    m.wetland_selected_index = flooded
    m.on_wetland_replant()
    assert m.wetland_plots[flooded].state == m.BARE
    assert m.on_wetland_mangrove() is True
    assert m.wetland_plots[flooded].state == m.REPLANTING and m.wetland_plots[flooded].species == m.SPECIES_MANGROVE
    m.wetland_selected_index = dry
    assert m.on_wetland_mangrove() is False and m.wetland_plots[dry].state == m.BARE
    m.on_wetland_replant()
    assert m.wetland_plots[dry].state == m.REPLANTING and m.wetland_plots[dry].species is None


def test_mangroves_recover_fast_and_the_flood_cannot_harm_them(game_env):
    m = game_env.module
    plot = m.Plot(0, region="wetland")
    plot.state = m.BARE
    plot.replant(species=m.SPECIES_MANGROVE)
    assert plot.replant_ticks_remaining == round(m.RECOVERY_TICKS * 0.6)
    plot.state, plot.value, plot.ticks_intact = m.PRESERVED, 50.0, 3
    assert m.wetland_flood_loss_fraction(plot) == 0.0
    other = m.Plot(1, region="wetland")
    other.state, other.value, other.ticks_intact = m.PRESERVED, 50.0, 3
    assert m.wetland_flood_loss_fraction(other) == m.WETLAND_FLOOD_LOSS_YOUNG


def test_the_main_forest_picker_never_offers_or_accepts_a_mangrove(game_env):
    m = game_env.module
    m.species_choice = m.SPECIES_MANGROVE
    m.plots[0].state = m.BARE
    m.selected_index = 0
    m.on_replant()
    assert m.plots[0].species is None
    store = _memory_storage(m)
    store[m.SPECIES_CHOICE_KEY] = "mangrove"
    m.load_species_choice()
    assert m.species_choice == m.SPECIES_STANDARD


def test_tidal_wildlife_appears_in_the_almanac_once_the_wetland_is_open(game_env):
    m = game_env.module
    assert "Tidal wildlife" not in [t for t, _ in m.almanac_sections()]
    _wet(m)
    sections = dict(m.almanac_sections())
    assert [e[2] for e in sections["Tidal wildlife"]] == [False, False]
    for i in range(3):
        m.wetland_plots[i].state, m.wetland_plots[i].species = m.PRESERVED, m.SPECIES_MANGROVE
    m.note_wetland_wildlife()
    assert [e[2] for e in dict(m.almanac_sections())["Tidal wildlife"]] == [True, False]
    m.wetland_plots[0].ticks_intact = m.MATURITY_TICKS
    m.note_wetland_wildlife()
    for p in m.wetland_plots:
        p.species, p.state = None, m.BARE  # losing the mangroves does not un-find the wildlife
    assert [e[2] for e in dict(m.almanac_sections())["Tidal wildlife"]] == [True, True]


def test_tides_show_on_tiles_and_in_the_status_and_the_wildlife_is_saved(game_env):
    m = game_env.module
    _wet(m)
    m.render_wetland_grid()
    tiles = game_env.elements["wetland-plot-grid"].children
    flooded = [i for i, t in enumerate(tiles) if "plot-tidal" in t.className]
    assert flooded == [i for i in range(len(tiles)) if m.wetland_plot_flooded(i)]
    assert "under water now" in tiles[flooded[0]].getAttribute("data-tooltip")
    assert "Tide: low" in m.wetland_tide_text()
    m.wetland_wildlife_found.add("heron")
    state = m.get_state()
    assert state["wetland_wildlife"] == ["heron"]
    m.wetland_wildlife_found.clear()
    m.load_state(state)
    assert m.wetland_wildlife_found == {"heron"}


# ---- GB-29 carbon-credit market ----

def test_price_follows_a_known_bounded_cycle(game_env):
    m = game_env.module
    prices = [m.carbon_price(t) for t in range(0, 400)]
    assert prices == [m.carbon_price(t) for t in range(0, 400)]
    assert min(prices) > m.CARBON_BASE_PRICE * 0.5 and max(prices) < m.CARBON_BASE_PRICE * 1.5
    assert len({round(p, 1) for p in prices}) > 50  # it really moves
    assert m.carbon_trend(0) in ("rising", "falling", "steady")
    trends = {m.carbon_trend(t) for t in range(0, 200)}
    assert {"rising", "falling"} <= trends


def test_standing_plots_earn_credits_up_to_a_cap(game_env):
    m = game_env.module
    m._carbon_tick()
    assert abs(m.carbon["credits"] - len(m.plots) * m.CARBON_CREDIT_PER_PLOT_TICK) < 1e-9
    m.carbon["credits"] = m.CARBON_CREDIT_CAP - 0.001
    m._carbon_tick()
    assert m.carbon["credits"] == m.CARBON_CREDIT_CAP
    for p in m.plots:
        p.state = m.BARE
    before = m.carbon["credits"]
    m._carbon_tick()
    assert m.carbon["credits"] == before  # nothing standing, nothing earned


def test_selling_pays_now_and_slows_growth_for_a_while(game_env):
    m = game_env.module
    m.forest_tick = 20
    m.carbon["credits"] = 40.0
    preview = m.sale_preview()
    assert preview["income"] == round(40.0 * m.carbon_price(), 2) and preview["slump_ticks"] == m.CARBON_SLUMP_BASE_TICKS + 20
    income = m.total_income
    paid = m.sell_carbon(1.0)
    assert paid == preview["income"] and m.total_income == income + paid
    assert m.carbon["credits"] == 0.0 and m.carbon["slump"] == preview["slump_ticks"] and m.carbon["sold"] == 40.0
    assert m.carbon_slump_multiplier() == m.CARBON_SLUMP_MULTIPLIER
    a, b = m.Plot(0), m.Plot(1)
    a.state = b.state = m.PRESERVED
    slow = a.accrue_tick()
    m.carbon["slump"] = 0
    normal = b.accrue_tick()
    assert slow < normal


def test_slump_runs_out_and_a_tiny_balance_does_not_sell(game_env):
    m = game_env.module
    m.carbon["slump"] = 2
    m._carbon_tick()
    m._carbon_tick()
    assert m.carbon_slump_multiplier() == 1.0
    m.carbon["credits"] = 0.3
    assert m.sell_carbon(1.0) == 0.0 and m.carbon["credits"] == 0.3
    m.carbon["credits"] = 10.0
    m.sell_carbon(0.5)
    assert abs(m.carbon["credits"] - 5.0) < 1e-9


def test_slump_length_is_capped(game_env):
    m = game_env.module
    assert m.carbon_slump_ticks_for(1000) == m.CARBON_SLUMP_MAX_TICKS


def test_carbon_offer_from_the_broker_gifts_credits(game_env):
    m = game_env.module
    m.plots[14].value = 10.0
    m.pending_stakeholder_request = {"plot_index": 14, "reason": "carbon_credit", "kind": m.STAKEHOLDER_KIND_INCENTIVE}
    m.grant_stakeholder_request()
    assert m.carbon["credits"] == m.CARBON_OFFER_CREDITS
    m.pending_stakeholder_request = {"plot_index": 14, "reason": "ecotourism", "kind": m.STAKEHOLDER_KIND_INCENTIVE}
    m.grant_stakeholder_request()
    assert m.carbon["credits"] == m.CARBON_OFFER_CREDITS


def test_chart_text_and_buttons(game_env):
    import xml.etree.ElementTree as ET
    m = game_env.module
    m.forest_tick = 30
    svg = m.carbon_chart_svg()
    ET.fromstring(svg)
    assert "stroke-dasharray" in svg  # the forecast is dotted
    m.carbon["credits"] = 12.0
    m.render_carbon()
    assert "Carbon credits: 12.0" in game_env.elements["carbon-status"].innerText
    assert game_env.elements["carbon-sell-button"].disabled is False
    m.carbon["credits"] = 0.0
    m.render_carbon()
    assert game_env.elements["carbon-sell-button"].disabled is True


def test_carbon_saves_only_when_used_validates_and_resets(game_env):
    m = game_env.module
    assert "carbon" not in m.get_state()
    m.carbon.update({"credits": 7.5, "slump": 3, "sold": 20.0, "earned_from_sales": 300.0})
    state = m.get_state()
    m.reset_session()
    assert m.carbon["credits"] == 0.0
    m.load_state(state)
    assert m.carbon["credits"] == 7.5 and m.carbon["slump"] == 3 and m.carbon["sold"] == 20.0
    state["carbon"] = {"credits": 99999, "slump": -4, "sold": "x"}
    m.load_state(state)
    assert m.carbon["credits"] == m.CARBON_CREDIT_CAP and m.carbon["slump"] == 0 and m.carbon["sold"] == 0.0


# ---- GB-19 community plot ----

class _FakePool:
    def __init__(self):
        self.added = []

    def add(self, game, pool, amount):
        self.added.append((game, pool, amount))


class _FakeBoard:
    def __init__(self):
        self.reports = []

    def report(self, game, board, score, detail=""):
        self.reports.append((game, board, score))


def _community_setup(m, enabled=True):
    store = _memory_storage(m)
    pool, board = _FakePool(), _FakeBoard()
    window = type("W", (), {"NoyvjPool": pool, "NoyvjLeaderboard": board})()
    m._community_js = lambda: window
    m.ui_pref = lambda key, default="": "true" if (enabled and key == m.UI_PREF_COMMUNITY) else default
    return store, pool, board


def test_nothing_is_sent_unless_the_setting_is_on(game_env):
    m = game_env.module
    store, pool, board = _community_setup(m, enabled=False)
    for _ in range(40):
        m._community_tick()
    assert pool.added == [] and board.reports == [] and m.COMMUNITY_STORAGE_KEY not in store


def test_share_grows_with_how_much_of_the_forest_is_standing(game_env):
    m = game_env.module
    full = m.community_share_this_tick()
    assert abs(full - m.COMMUNITY_PER_TICK) < 1e-9
    for p in m.plots[: len(m.plots) // 2]:
        p.state = m.BARE
    assert abs(m.community_share_this_tick() - m.COMMUNITY_PER_TICK / 2) < 1e-9
    for p in m.plots:
        p.state = m.BARE
    assert m.community_share_this_tick() == 0.0


def test_ticks_add_to_the_pool_and_to_todays_total(game_env):
    m = game_env.module
    store, pool, board = _community_setup(m)
    for _ in range(10):
        assert m._community_tick() > 0
    assert len(pool.added) == 10 and all(a[:2] == ("canopy", "community_plot") for a in pool.added)
    assert abs(m.community_today_total() - 10 * m.COMMUNITY_PER_TICK) < 0.01
    assert max(a[2] for a in pool.added) <= 60.0  # under the server's per-request cap even when batched for a while


def test_the_board_gets_the_day_total_every_thirty_ticks(game_env):
    m = game_env.module
    store, pool, board = _community_setup(m)
    m._community_ticks = 0
    for _ in range(m.COMMUNITY_REPORT_EVERY):
        m._community_tick()
    assert len(board.reports) == 1 and board.reports[0][:2] == ("canopy", "community_investment")
    assert board.reports[0][2] == round(m.community_today_total(), 2)


def test_a_new_utc_day_starts_from_zero_and_bad_data_is_ignored(game_env):
    m = game_env.module
    store, pool, board = _community_setup(m)
    store[m.COMMUNITY_STORAGE_KEY] = '{"day": "1999-01-01", "amount": 12.5}'
    assert m.community_today_total() == 0.0
    assert abs(m.community_today_total("1999-01-01") - 12.5) < 1e-9
    store[m.COMMUNITY_STORAGE_KEY] = "garbage"
    assert m.community_today_total() == 0.0
    store[m.COMMUNITY_STORAGE_KEY] = '{"day": "%s", "amount": "x"}' % m._utc_day()
    assert m.community_today_total() == 0.0


def test_a_missing_or_broken_shared_script_never_breaks_a_tick(game_env):
    m = game_env.module
    _memory_storage(m)
    m.ui_pref = lambda key, default="": "true" if key == m.UI_PREF_COMMUNITY else default
    m._community_js = lambda: None
    assert m._community_tick() > 0

    class Boom:
        def add(self, *a):
            raise RuntimeError("network")
    m._community_js = lambda: type("W", (), {"NoyvjPool": Boom(), "NoyvjLeaderboard": Boom()})()
    m._community_ticks = m.COMMUNITY_REPORT_EVERY - 1
    assert m._community_tick() > 0


def test_note_explains_the_state_and_the_page_loads_the_shared_scripts(game_env):
    import os
    m = game_env.module
    _community_setup(m, enabled=False)
    m.render_community_note()
    assert "Off" in game_env.elements["community-plot-note"].innerText
    _community_setup(m, enabled=True)
    m.render_community_note()
    assert "watered the community plot" in game_env.elements["community-plot-note"].innerText
    html = page_text("index.html")
    assert 'shared/community-pool.js" data-game-id="canopy" data-pool="community_plot"' in html
    assert 'data-board="community_investment"' in html and 'id="leaderboard-mount"' in html


def test_sandbox_forests_never_water_the_shared_plot(game_env):
    m = game_env.module
    store, pool, board = _community_setup(m)
    m.lab["maturity"] = 2.0
    assert m._community_tick() == 0.0 and pool.added == []


# ---- B-29 custom layouts ----

def test_presets_make_valid_shapes_of_the_right_size(game_env):
    m = game_env.module
    n = m.GRID_ROWS * m.GRID_COLS
    for kind in m.LAYOUT_PRESET_LABELS:
        cells = m.layout_preset_cells(kind)
        assert len(cells) == n and set(cells) <= {"0", "1"} and m.clean_layout_cells(cells) == cells
        assert 0 < cells.count("0") < n  # a real shape: some open ground, some plots
    ring = m.layout_preset_cells("ring")
    assert ring[0] == "1" and ring[m.GRID_COLS + 1] == "0"  # forest around the edge, open ground inside
    plus = m.layout_preset_cells("plus")
    assert plus[0] == "0" and plus[m.GRID_COLS * (m.GRID_ROWS // 2) + 1] == "1"


def test_layout_cells_are_validated(game_env):
    m = game_env.module
    n = m.GRID_ROWS * m.GRID_COLS
    assert m.clean_layout_cells("1" * n) == "1" * n
    assert m.clean_layout_cells("1" * (n - 1)) is None and m.clean_layout_cells("2" * n) is None
    assert m.clean_layout_cells("0" * n) is None and m.clean_layout_cells(("1" * 3) + "0" * (n - 3)) is None
    assert m.clean_layout_cells(None) is None


def test_starting_a_layout_blocks_the_open_ground_and_it_never_counts(game_env):
    m = game_env.module
    cells = m.layout_preset_cells("ring")
    assert m.start_layout(cells, "My ring") is True
    assert m.layout_active() and m.current_layout["name"] == "My ring"
    n_open = cells.count("0")
    assert sum(1 for p in m.plots if p.blocked) == n_open
    assert all(p.state == m.BARE for p in m.plots if p.blocked)
    assert m.active_plot_count() == len(m.plots) - n_open
    assert sum(m.state_breakdown().values()) == m.active_plot_count()
    blocked = next(p for p in m.plots if p.blocked)
    assert blocked.clear() is None and blocked.replant() is False
    m.select_plot(blocked.index)
    assert m.selected_index != blocked.index
    for _ in range(5):
        m.tick()
    assert all(p.value == 0 and p.state == m.BARE for p in m.plots if p.blocked)
    assert m.counterfactual_standing_value() == m.active_plot_count() * m._ideal_accrual_for_ticks(m._session_ticks)


def test_blocked_cells_are_never_targets(game_env):
    m = game_env.module
    m.start_layout(m.layout_preset_cells("plus"), "")
    for p in m.plots:
        if not p.blocked:
            p.state = m.PRESERVED
    assert m._replant_grant_target_index() is None  # only open ground is "bare"
    first_open = next(p for p in m.plots if p.blocked)
    assert first_open.state == m.BARE and m._replant_grant_target_index() is None


def test_tiles_for_open_ground_are_disabled_and_unmarked(game_env):
    m = game_env.module
    m.start_layout(m.layout_preset_cells("ring"), "")
    tiles = game_env.elements["plot-grid"].children
    for plot, tile in zip(m.plots, tiles):
        assert ("plot-blocked" in tile.className) == plot.blocked
        assert tile.disabled == plot.blocked
        if plot.blocked:
            assert tile.children == [] and "Open ground" in tile.getAttribute("aria-label")


def test_layout_survives_a_save_and_is_dropped_by_clashing_settings(game_env):
    m = game_env.module
    m.start_layout(m.layout_preset_cells("river"), "River")
    state = m.get_state()
    assert state["layout"]["name"] == "River" and state["layout"]["cells"] == m.layout_preset_cells("river")
    m.reset_session(layout=None)
    assert not m.layout_active() and "layout" not in m.get_state()
    m.load_state(state)
    assert m.layout_active() and sum(1 for p in m.plots if p.blocked) == m.layout_preset_cells("river").count("0")
    m.reset_session(difficulty=m.DIFFICULTY_RANGER)
    assert m.layout_active()  # difficulty and Reset keep the shape
    m.reset_session()
    assert m.layout_active()
    m.reset_session(scenario=next(iter(m.SCENARIO_SPECS)))
    assert not m.layout_active() and not any(p.blocked for p in m.plots)
    m.start_layout(m.layout_preset_cells("ring"), "")
    m.reset_session(grid_size="large")
    assert not m.layout_active()


def test_a_layout_clears_scenario_challenge_and_level(game_env):
    m = game_env.module
    m.reset_session(scenario=next(iter(m.SCENARIO_SPECS)))
    assert m.current_scenario != m.SCENARIO_NONE
    m.start_layout(m.layout_preset_cells("plus"), "")
    assert m.current_scenario == m.SCENARIO_NONE and m.current_challenge == m.CHALLENGE_NONE and m.current_level is None


def test_bad_saved_layouts_are_ignored_on_load(game_env):
    m = game_env.module
    state = m.get_state()
    for bad in ({"cells": "101"}, {"cells": 5}, "nope", {"cells": "x" * (m.GRID_ROWS * m.GRID_COLS)}):
        state["layout"] = bad
        m.load_state(state)
        assert not m.layout_active() and not any(p.blocked for p in m.plots)


def test_named_layouts_are_stored_with_their_own_best(game_env):
    m = game_env.module
    store = _memory_storage(m)
    cells = m.layout_preset_cells("island")
    assert m.save_layout("  My   island ", cells) == "My island"
    assert m.save_layout("bad", "11") is None
    saved = m.load_saved_layouts()
    assert saved[0]["best"] == 0.0 and saved[0]["rows"] == m.GRID_ROWS and saved[0]["cells"] == cells
    m.start_layout(cells, "My island")
    m.plots[next(i for i, c in enumerate(cells) if c == "1")].value = 123.0
    m._update_layout_best()
    assert m.load_saved_layouts()[0]["best"] == 123.0
    assert "best standing 123.0" in m.layout_best_text()
    m.save_layout("My island", cells)  # re-saving keeps the best
    assert m.load_saved_layouts()[0]["best"] == 123.0
    for i in range(8):
        m.save_layout(f"L{i}", cells)
    assert len(m.load_saved_layouts()) == m.LAYOUT_MAX_SAVED
    store[m.LAYOUT_STORAGE_KEY] = "broken"
    assert m.load_saved_layouts() == []


def test_editor_toggles_cells_applies_and_reports(game_env):
    m = game_env.module
    m.layout_draft = None
    m.render_layout_editor()
    grid = game_env.elements["layout-grid"]
    assert len(grid.children) == m.GRID_ROWS * m.GRID_COLS
    m.toggle_draft_cell(0)
    assert m._draft_cells()[0] == "0" and grid.children[0].className.endswith("off")
    m.on_layout_preset("plus")
    assert m._draft_cells() == m.layout_preset_cells("plus")
    assert "Draft:" in game_env.elements["layout-status"].innerText
    game_env.elements["layout-name"].value = "Cross"
    m.on_layout_apply()
    assert m.layout_active() and m.current_layout["name"] == "Cross"
    assert game_env.elements["layout-banner"].hidden is False and "community comparison" in game_env.elements["layout-banner"].innerText
    m.on_layout_clear()
    assert not m.layout_active() and game_env.elements["layout-banner"].hidden is True


def test_the_apply_button_needs_enough_plots(game_env):
    m = game_env.module
    m.layout_draft = "0" * (m.GRID_ROWS * m.GRID_COLS - 3) + "111"
    m.render_layout_editor()
    assert game_env.elements["layout-apply-button"].disabled is True
    m.layout_draft = "1" * (m.GRID_ROWS * m.GRID_COLS)
    m.render_layout_editor()
    assert game_env.elements["layout-apply-button"].disabled is False


def test_custom_layouts_stay_out_of_the_standard_best_and_averages(game_env):
    import json
    m = game_env.module
    store = _memory_storage(m)
    m.start_layout(m.layout_preset_cells("plus"), "")
    m._session_ticks = 30
    m.plots[next(p.index for p in m.plots if not p.blocked)].value = 400.0
    m._maybe_update_personal_best()
    assert m.PERSONAL_BEST_STORAGE_KEY not in store
    m._bank_lifetime()
    assert json.loads(store[m.LIFETIME_STORAGE_KEY])["by_difficulty"] == {}
    assert json.loads(store[m.LIFETIME_STORAGE_KEY])["sessions"] == 1


# ---- GB-12 rival logging company ----

def _rival(m):
    m.current_difficulty = m.DIFFICULTY_RIVAL
    m._reset_rival()
    for p in m.plots:
        p.state, p.value, p.ticks_intact = m.PRESERVED, 40.0, 5
    m.heart_tree_index = None
    m.total_income = 500.0


def test_nothing_happens_on_other_difficulties(game_env):
    m = game_env.module
    m.forest_tick = 500
    for _ in range(100):
        m.forest_tick += 1
        m._rival_tick()
    assert m.rival_notice is None and m.rival_claims == {} and m.rival_status_text() == ""


def test_a_bid_is_flagged_on_an_edge_plot_ten_ticks_ahead(game_env):
    m = game_env.module
    _rival(m)
    m.forest_tick = m.RIVAL_FIRST_BID_TICKS
    m._rival_tick()
    assert m.rival_notice is not None and m.rival_notice["ticks_left"] == m.RIVAL_NOTICE_TICKS
    target = m.rival_notice["plot"]
    assert m._is_edge(target) and m.plots[target].state == m.PRESERVED
    assert "bidding on" in m.rival_status_text() and "easement" in m.rival_status_text()
    assert any(e["kind"] == "rival" for e in m.forest_log)


def test_an_unanswered_bid_becomes_a_claim_that_expires_and_the_plot_comes_back(game_env):
    m = game_env.module
    _rival(m)
    m.forest_tick = m.RIVAL_FIRST_BID_TICKS
    m._rival_tick()
    target = m.rival_notice["plot"]
    for _ in range(m.RIVAL_NOTICE_TICKS):
        m.forest_tick += 1
        m._rival_tick()
    assert m.rival_notice is None and target in m.rival_claims
    assert m.plots[target].state == m.BARE and m.plots[target].clear_count == 0 and m.plots[target].value == 0.0
    assert m.plots[target].replant() is False  # a mining claim cannot be planted
    for _ in range(m.RIVAL_CLAIM_TICKS):
        m.forest_tick += 1
        m._rival_tick()
    assert target not in m.rival_claims and m.plots[target].replant() is True


def test_an_easement_costs_a_share_of_the_plots_value_and_protects_it_for_good(game_env):
    m = game_env.module
    _rival(m)
    m.forest_tick = m.RIVAL_FIRST_BID_TICKS
    m._rival_tick()
    target = m.rival_notice["plot"]
    m.plots[target].value = 200.0
    assert m.easement_cost(target) == 30.0
    m.total_income = 500.0
    assert m.lock_easement() is True
    assert m.total_income == 470.0 and target in m.rival_locked and m.rival_notice is None
    assert target not in m._rival_candidates()
    m.total_income = 5.0
    other = next(i for i in range(len(m.plots)) if i != target)
    assert m.can_lock(other) is False  # not enough income: the choice is simply unavailable, never a penalty
    assert m.easement_cost(other) == max(m.RIVAL_EASEMENT_MIN, round(0.15 * m.plots[other].value, 1))


def test_a_locked_plot_survives_its_notice(game_env):
    m = game_env.module
    _rival(m)
    m.rival_notice = {"plot": 0, "ticks_left": 1}
    m.rival_locked.add(0)
    m._rival_tick()
    assert m.plots[0].state == m.PRESERVED and 0 not in m.rival_claims


def test_buying_out_a_claim_frees_the_plot_at_once(game_env):
    m = game_env.module
    _rival(m)
    m.plots[0].state, m.plots[0].value = m.BARE, 0.0
    m.rival_claims[0] = 30
    m.selected_index = 0
    income = m.total_income
    assert m.can_buy_out(0) and m.buy_out_claim() is True
    assert m.total_income == income - m.RIVAL_BUYOUT_COST and 0 not in m.rival_claims and m.plots[0].replant() is True
    m.rival_claims[1] = 5
    m.total_income = 1.0
    assert m.can_buy_out(1) is False


def test_bids_come_faster_down_to_a_floor(game_env):
    m = game_env.module
    _rival(m)
    intervals = []
    for bids in range(0, 20):
        m.rival_state["bids"] = bids
        intervals.append(m.rival_bid_interval())
    assert intervals == sorted(intervals, reverse=True) and intervals[0] == m.RIVAL_INTERVAL_TICKS and intervals[-1] == m.RIVAL_INTERVAL_FLOOR


def test_rival_state_saves_validates_and_resets(game_env):
    m = game_env.module
    m.reset_session(difficulty=m.DIFFICULTY_RIVAL)
    assert "rival" not in m.get_state()
    m.rival_claims[3] = 12
    m.rival_locked.update({1, 2})
    m.rival_notice = {"plot": 5, "ticks_left": 4}
    m.rival_state.update({"next_bid": 90, "bids": 2})
    state = m.get_state()
    m.reset_session(difficulty=m.DIFFICULTY_RIVAL)
    assert m.rival_claims == {} and m.rival_locked == set() and m.rival_notice is None
    m.load_state(state)
    assert m.rival_claims == {3: 12} and m.rival_locked == {1, 2} and m.rival_notice == {"plot": 5, "ticks_left": 4}
    assert m.rival_state == {"next_bid": 90, "bids": 2}
    state["rival"] = {"claims": {"x": 5, "99": 5, "3": 9999}, "locked": [-1, "a", 2], "notice": {"plot": 99, "ticks_left": 3}}
    m.load_state(state)
    assert m.rival_claims == {} and m.rival_locked == {2} and m.rival_notice is None


def test_tiles_show_a_glyph_for_bids_claims_and_easements(game_env):
    m = game_env.module
    _rival(m)
    m.rival_notice = {"plot": 0, "ticks_left": 6}
    m.rival_locked.add(1)
    m.plots[2].state = m.BARE
    m.rival_claims[2] = 20
    m.render()
    tiles = game_env.elements["plot-grid"].children
    assert "plot-bid" in tiles[0].className and "plot-easement" in tiles[1].className and "plot-claimed" in tiles[2].className
    assert all(any(c.className == "rival-mark" for c in tiles[i].children) for i in (0, 1, 2))
    assert game_env.elements["rival-lock-button"].hidden is False and game_env.elements["rival-status"].hidden is False
    m.current_difficulty = m.DIFFICULTY_NORMAL
    m.render()
    assert game_env.elements["rival-lock-button"].hidden is True
    assert "Rival logging company" not in m.session_tag_text()
    m.current_difficulty = m.DIFFICULTY_RIVAL
    assert "Rival logging company" in m.session_tag_text()


# ---- R-27 community comparison of standing value ----

def test_the_save_carries_a_read_only_standing_value_the_stats_backend_reads(game_env):
    import os
    m = game_env.module
    m.plots[0].value = 123.4
    state = m.get_state()
    assert state["standing_value"] == round(m.standing_forest_value(), 1)
    before = m.standing_forest_value()
    state["standing_value"] = 99999
    m.load_state(state)
    assert abs(m.standing_forest_value() - before) < 1e-6  # ignored on load: the plots are the truth
    root = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    stats = open(os.path.join(root, "app", "stats.py"), encoding="utf-8").read()
    assert '"standing_value"' in stats
    html = page_text("index.html")
    assert '["standing_value", "Standing forest value"]' in html
