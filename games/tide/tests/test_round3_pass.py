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
