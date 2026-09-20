"""Round-3 pass (planning/TODO.md D-list): D7 delayed-consequence timeline,
D8 tide indicator, D29 settlement name and chronicle."""


def _round_trip(game_env):
    data = game_env.module.get_state()
    game_env.module.load_state(data)
    return data


# ---- D7 -----------------------------------------------------------------


def test_d7_no_history_means_no_graph(game_env):
    assert game_env.module.delayed_consequence_svg() == ""
    assert "Advance a season" in game_env.state.delayed_consequence_text()


def test_d7_rows_arrive_lag_seasons_later(game_env):
    game_env.invest("output")
    game_env.advance_season()
    game_env.advance_season()
    rows = game_env.state.delayed_consequence_rows()
    assert len(rows) == 2
    season, fraction, arrival, projected = rows[0]
    assert season == 1 and arrival == 1 + game_env.module.FISH_LAG_SEASONS
    assert 0 < fraction <= 1 and projected < 1.0


def test_d7_hard_lag_shifts_arrival(game_env):
    game_env.invest("output")
    game_env.advance_season()
    game_env.toggle_hard_lag()
    assert game_env.state.delayed_consequence_rows()[0][2] == 1 + game_env.module.FISH_LAG_SEASONS_HARD


def test_d7_svg_and_text_rendered(game_env):
    game_env.invest("output")
    game_env.advance_season()
    assert "<svg" in game_env.elements["delayed-consequence-graph"].innerHTML
    assert "Season 1 reaches fish stocks" in game_env.elements["delayed-consequence-text"].innerText


# ---- D8 -----------------------------------------------------------------


def test_d8_tide_is_deterministic_and_bounded(game_env):
    m = game_env.module
    for season in range(1, 40):
        game_env.state.season = season
        assert abs(game_env.state.tide_offset()) <= m.TIDE_AMPLITUDE
        assert game_env.state.tide_offset() == game_env.state.tide_offset()
        assert game_env.state.tide_label() in ("High", "Mid", "Low")


def test_d8_tidal_rows_are_dry_but_reachable(game_env):
    st = game_env.state
    m = game_env.module
    for season in range(1, 40):
        st.season = season
        for sea in (0.0, 13.0, 44.0):
            st.sea_level = sea
            for row in st.tidal_rows():
                assert m.tile_row_state(row, sea) == m.LAND
                assert m.row_flood_threshold(row) <= sea + st.tide_offset()


def test_d8_low_tide_reaches_nothing(game_env):
    st = game_env.state
    for season in range(1, 20):
        st.season = season
        if st.tide_offset() <= 0:
            st.sea_level = 14.0
            assert st.tidal_rows() == []
            return
    raise AssertionError("no low tide found")


def test_d8_tidal_tile_class_and_indicator_text(game_env):
    st = game_env.state
    for season in range(1, 20):
        st.season = season
        st.sea_level = 13.0  # row 5 floods at 15
        if st.tidal_rows():
            game_env.module.render()
            tiles = [e for k, e in game_env.elements.items() if k.startswith("coastline-tile-5-0")]
            assert tiles and "coastline-tidal" in tiles[0].className
            assert "Tide this season" in game_env.elements["tide-indicator"].innerText
            return
    raise AssertionError("no tidal season found")


# ---- D29 ----------------------------------------------------------------


def test_d29_name_is_cleaned_and_capped(game_env):
    st = game_env.state
    assert st.set_settlement_name("  Port   Salt  ")
    assert st.settlement_name == "Port Salt"
    st.set_settlement_name("x" * 100)
    assert len(st.settlement_name) == game_env.module.SETTLEMENT_NAME_MAX
    assert not st.set_settlement_name(42)
    assert st.display_name() == "x" * game_env.module.SETTLEMENT_NAME_MAX


def test_d29_default_display_name(game_env):
    assert game_env.state.display_name() == "Your settlement"


def test_d29_chronicle_records_tier_and_first_flood(game_env):
    for _ in range(3):
        game_env.invest("adaptation")
    for _ in range(4):
        game_env.advance_season()
    text = " ".join(game_env.state.chronicle_lines())
    assert "Sandbag berms completed" in text
    assert "went under" in text


def test_d29_chronicle_is_capped(game_env):
    for _ in range(100):
        game_env.state._chronicle_event("x")
    assert len(game_env.state.chronicle) == game_env.module.CHRONICLE_LIMIT


def test_d29_name_input_event_and_founding_line(game_env):
    game_env.elements["settlement-name-input"].value = "Saltmere"
    field = game_env.elements["settlement-name-input"]
    field.dispatch("change", _Ev(field))
    assert game_env.state.settlement_name == "Saltmere"
    assert "Founded as Saltmere" in game_env.elements["settlement-chronicle"].innerHTML
    assert "Saltmere" in game_env.elements["settlement-heading"].innerText


class _Ev:
    def __init__(self, target):
        self.target = target


def test_d29_save_round_trip_and_bad_data(game_env):
    st = game_env.state
    st.set_settlement_name("Saltmere")
    st._chronicle_event("hello")
    data = game_env.module.get_state()
    st.settlement_name = ""
    st.chronicle = []
    game_env.module.load_state(data)
    assert st.settlement_name == "Saltmere" and st.chronicle[-1]["text"] == "hello"
    bad = dict(data, settlement_name=7, chronicle=[{"season": "x"}, 5, {"season": 1, "text": "ok"}])
    game_env.module.load_state(bad)
    assert st.settlement_name == ""
    assert st.chronicle == [{"season": 1, "text": "ok"}]
    game_env.module.load_state({k: v for k, v in data.items() if k not in ("chronicle", "settlement_name")})
    assert st.chronicle == [] and st.settlement_name == ""


# ---- D17 heritage -------------------------------------------------------


def test_d17_protect_costs_funds_once(game_env):
    st = game_env.state
    st.funds = 500
    assert st.protect_heritage("lighthouse")
    assert st.funds == 500 - 120
    assert st.heritage["lighthouse"] == "protected"
    assert not st.protect_heritage("lighthouse")  # already protected
    assert not st.protect_heritage("nope")


def test_d17_cannot_protect_without_funds_or_after_flood(game_env):
    st = game_env.state
    st.funds = 10
    assert not st.protect_heritage("reef")
    st.funds = 500
    st.sea_level = 20.0  # row 5 (threshold 15) already flooded
    assert not st.protect_heritage("reef")


def test_d17_unprotected_site_is_lost_protected_survives(game_env):
    st = game_env.state
    st.funds = 500
    st.protect_heritage("reef")
    st.sea_level = 14.0
    game_env.advance_season()  # sea 19 -> row 5 floods
    assert st.heritage["reef"] == "protected"
    st.sea_level = 30.0
    game_env.advance_season()  # row 4 (threshold 30) floods
    assert st.heritage["lighthouse"] == "lost"
    assert any("lost to the sea" in m for m in st.ticker_full_history)


def test_d17_upkeep_charged_per_protected_site_and_floored(game_env):
    st = game_env.state
    st.funds = 500
    st.protect_heritage("lighthouse")
    before = st.funds
    game_env.advance_season()
    assert st.funds == before - game_env.module.HERITAGE_UPKEEP
    st.funds = 2
    game_env.advance_season()
    assert st.funds == 0


def test_d17_tile_marker_and_button(game_env):
    st = game_env.state
    st.funds = 500
    game_env.module.render()
    tile = game_env.elements["coastline-tile-5-3"]
    assert tile.innerText == "🦪" and "coastline-heritage--unprotected" in tile.className
    game_env.elements["heritage-protect-1"].dispatch("click", None)
    assert st.heritage["reef"] == "protected"
    assert "coastline-heritage--protected" in game_env.elements["coastline-tile-5-3"].className
    assert game_env.elements["heritage-protect-1"].disabled


def test_d17_save_round_trip_and_bad_data(game_env):
    st = game_env.state
    st.funds = 500
    st.protect_heritage("reef")
    data = game_env.module.get_state()
    st.heritage["reef"] = "unprotected"
    game_env.module.load_state(data)
    assert st.heritage["reef"] == "protected"
    game_env.module.load_state(dict(data, heritage={"reef": "banana", "lighthouse": 5}))
    assert st.heritage == {"lighthouse": "unprotected", "reef": "unprotected"}
    game_env.module.load_state(dict(data, heritage="x"))
    assert st.heritage == {"lighthouse": "unprotected", "reef": "unprotected"}


# ---- D21 citizen science ------------------------------------------------


def test_d21_monitoring_reveals_facts_in_order_with_cooldown(game_env):
    st = game_env.state
    m = game_env.module
    st.funds = 1000
    assert st.fund_monitoring()
    assert st.revealed_facts() == m.CITIZEN_SCIENCE_FACTS[:1]
    assert st.funds == 1000 - m.MONITOR_COST
    assert not st.fund_monitoring()  # cooldown
    game_env.advance_season()
    game_env.advance_season()
    assert st.fund_monitoring()
    assert len(st.revealed_facts()) == 2
    assert m.CITIZEN_SCIENCE_FACTS[0] in st.ticker_full_history[-2] or any(
        m.CITIZEN_SCIENCE_FACTS[0] in t for t in st.ticker_full_history
    )


def test_d21_needs_funds_and_caps_at_all_facts(game_env):
    st = game_env.state
    m = game_env.module
    st.funds = 10
    assert not st.fund_monitoring()
    st.funds = 100000
    for _ in range(len(m.CITIZEN_SCIENCE_FACTS) + 3):
        st.fund_monitoring()
        st.season += m.MONITOR_COOLDOWN_SEASONS
    assert st.monitoring_reports == len(m.CITIZEN_SCIENCE_FACTS)
    assert not st.can_monitor()


def test_d21_button_and_log_render(game_env):
    st = game_env.state
    st.funds = 500
    game_env.module.render()
    assert not game_env.elements["monitor-button"].disabled
    game_env.elements["monitor-button"].dispatch("click", None)
    assert game_env.elements["monitor-button"].disabled
    assert "1. " in game_env.elements["monitor-log"].innerHTML


def test_d21_save_validation(game_env):
    st = game_env.state
    data = game_env.module.get_state()
    game_env.module.load_state(dict(data, monitoring_reports=999, monitoring_last_season="x"))
    assert st.monitoring_reports == len(game_env.module.CITIZEN_SCIENCE_FACTS)
    assert st.monitoring_last_season == 0
    game_env.module.load_state(dict(data, monitoring_reports=-4))
    assert st.monitoring_reports == 0
    game_env.module.load_state(dict(data, monitoring_reports=True))
    assert st.monitoring_reports == 0


# ---- D13 storms ---------------------------------------------------------


def test_d13_off_by_default_changes_nothing(game_env):
    st = game_env.state
    for _ in range(12):
        game_env.advance_season()
    assert st.storm_log == [] and st.seasons_until_storm() is None


def test_d13_storm_fires_every_interval_when_on(game_env):
    st = game_env.state
    m = game_env.module
    st.set_storm_mode(True)
    for _ in range(m.STORM_INTERVAL * 2):
        game_env.advance_season()
    assert [e["season"] for e in st.storm_log] == [m.STORM_INTERVAL, 2 * m.STORM_INTERVAL]
    assert st.storm_log[1]["surge"] > st.storm_log[0]["surge"]


def test_d13_adaptation_holds_back_the_surge(game_env):
    m = game_env.module

    def run(adaptation):
        game_env.state.storm_log = []
        game_env.state.season = m.STORM_INTERVAL
        game_env.state.funds = 1000
        game_env.state.capacity["adaptation"] = adaptation
        game_env.state.set_storm_mode(True)
        game_env.advance_season()
        return game_env.state.storm_log[-1]["taken"]

    assert run(10) < run(0)
    assert run(15) < run(10)


def test_d13_funds_never_negative_and_forecast(game_env):
    st = game_env.state
    st.set_storm_mode(True)
    st.season = 5
    st.funds = 1
    game_env.advance_season()
    assert st.funds >= 0
    assert st.seasons_until_storm() == 4
    game_env.module.render()
    assert "Forecast" in game_env.elements["storm-forecast"].innerText


def test_d13_toggle_and_save_validation(game_env):
    st = game_env.state
    game_env.elements["storm-toggle-button"].dispatch("click", None)
    assert st.storm_mode
    data = game_env.module.get_state()
    game_env.module.load_state(dict(data, storm_mode=False, storm_log=[{"season": "x"}, 3, {"season": 5, "surge": 1, "taken": 1, "blocked": 0}]))
    assert not st.storm_mode
    assert len(st.storm_log) == 1
    game_env.module.load_state(dict(data, storm_log="nope"))
    assert st.storm_log == []
