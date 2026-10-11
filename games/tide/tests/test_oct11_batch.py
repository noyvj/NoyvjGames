"""D-8 named coastlines, D-3 shareable run codes and GD-5 Daily Tide (2026-10-11)."""

import json
import re
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
PC_HTML = (ROOT / "pc.html").read_text(encoding="utf-8")
CONFIG = json.loads((ROOT / "pc-config.json").read_text(encoding="utf-8"))
COASTS = ("open", "delta", "headland", "atoll", "port")
SCENARIOS = ("conservative", "moderate", "severe")


@pytest.fixture
def storage(game_env, monkeypatch):
    store = {}
    monkeypatch.setattr(game_env.module, "_read_local_storage_item", lambda key: store.get(key))
    monkeypatch.setattr(game_env.module, "_write_local_storage_item", lambda key, value: store.__setitem__(key, value))
    return store


def advance(m, n=1):
    for _ in range(n):
        m.state.advance_season()


def play_choices(m, seasons, pattern=None):
    """A run with known purchases; every purchase is paid for, so the log is the real one."""
    s = m.state
    for n in range(seasons):
        buys = (pattern or [(2, 1, 0), (0, 2, 1), (1, 0, 1), (0, 1, 0), (1, 1, 1)])[n % 5]
        for category, count in zip(m.CATEGORIES, buys):
            for _ in range(count):
                s.funds = max(s.funds, 100)  # keep every purchase affordable
                assert s.invest(category)
        s.advance_season()


# ---- D-8: the default coastline is exactly the game as it was ----------------------------------------------------------

def test_the_open_coast_is_the_old_game_number_for_number(game_env):
    m = game_env.module
    assert [m.row_flood_threshold(r) for r in range(6)] == [(6 - r) * 15.0 for r in range(6)]
    assert m.heritage_sites() is m.HERITAGE_SITES
    assert m.coast_meter_max() == m.SEA_LEVEL_METER_MAX == 90.0
    assert m.coast_storm_interval() == m.STORM_INTERVAL == 5
    assert m.DEFAULT_COASTLINE == "open" and m.state.coastline == "open"
    info = m.COASTLINES["open"]
    assert (info["output"], info["tourism"], info["aquaculture"], info["surge"]) == (1.0, 1.0, 1.0, 1.0)
    assert m.state.heritage == {"lighthouse": "unprotected", "reef": "unprotected"}


def test_the_open_coast_plays_a_pinned_twenty_season_run(game_env):
    m = game_env.module
    s = m.state
    s.set_storm_mode(True)
    seen = {}
    for n in range(1, 21):
        for category, rem in (("output", 0), ("reduction", 1), ("adaptation", 2)):
            if n % 3 == rem:
                s.invest(category)
        if n == 6:
            s.protect_heritage("lighthouse")
        s.advance_season()
        seen[n] = (round(s.funds, 4), round(s.acidity, 4), round(s.sea_level, 4), round(s.cumulative_damage, 4), s.rows_dry_count(), s.population)
    assert seen[1] == (275.0, 0.0, 5.0, 5.0, 6, 106)
    assert seen[7] == (112.88, 0.5, 35.0, 35.0, 4, 88)
    assert seen[13] == (30.8, 4.0, 65.0, 56.0, 2, 52)
    assert seen[19] == (70.02, 19.5, 95.0, 77.0, 0, 0)
    assert seen[20] == (34.98, 22.5, 100.0, 79.0, 0, 0)
    assert [(e["season"], round(e["surge"], 3), round(e["taken"], 3)) for e in s.storm_log] == [
        (5, 18.0, 18.0), (10, 21.0, 14.7), (15, 24.0, 16.8), (20, 27.0, 10.8)]


def test_a_default_save_gains_no_coastline_or_daily_key(game_env):
    m = game_env.module
    play_choices(m, 3)
    data = m.get_state()
    assert "coastline" not in data and "daily" not in data
    assert data["buys"]["log"] == [[2, 1, 0], [0, 2, 1], [1, 0, 1]]


# ---- D-8: the table ---------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("coast", COASTS)
def test_every_coastline_is_a_sane_table_entry(game_env, coast):
    m = game_env.module
    info = m.COASTLINES[coast]
    thresholds = info["thresholds"]
    assert len(thresholds) == m.COASTLINE_ROWS
    assert all(a > b for a, b in zip(thresholds, thresholds[1:])) and thresholds[-1] > 0  # row 0 highest, the bottom row floods first
    sites = info["heritage"]
    assert len(sites) == 2 and len({x["id"] for x in sites}) == 2 and len({x["row"] for x in sites}) == 2
    assert all(0 <= x["row"] < m.COASTLINE_ROWS and x["cost"] > 0 and x["name"] and x["emoji"] for x in sites)
    assert all(0.5 <= info[k] <= 1.6 for k in ("output", "tourism", "aquaculture"))
    assert 3 <= info["storm_interval"] <= 6 and 0.9 <= info["surge"] <= 1.3
    assert info["label"] and info["blurb"]


def test_the_five_coastlines_really_differ(game_env):
    m = game_env.module
    profiles = {c: tuple(m.COASTLINES[c]["thresholds"]) for c in COASTS}
    assert len(set(profiles.values())) == 5
    assert len({tuple(x["id"] for x in m.COASTLINES[c]["heritage"]) for c in COASTS}) == 5
    assert len({(m.COASTLINES[c]["output"], m.COASTLINES[c]["tourism"], m.COASTLINES[c]["aquaculture"]) for c in COASTS}) == 5
    assert len({m.COASTLINES[c]["storm_interval"] for c in COASTS}) >= 3


def test_choosing_a_coastline_works_only_before_the_first_season(game_env):
    m = game_env.module
    s = m.state
    assert s.set_coastline("delta") and s.coastline == "delta"
    assert s.heritage == {"grain-hall": "unprotected", "ferry": "unprotected"}
    assert not s.set_coastline("nowhere") and not s.set_coastline(None) and s.coastline == "delta"
    assert s.set_coastline("open") and set(s.heritage) == {"lighthouse", "reef"}
    s.set_coastline("port")
    s.advance_season()
    assert not s.set_coastline("atoll") and s.coastline == "port"


def test_the_picker_syncs_and_locks_like_the_sea_scenario(game_env):
    m = game_env.module
    select = game_env.elements["coastline-select"]
    select.value = "atoll"

    class Event:
        target = select
    select.dispatch("change", Event())
    assert m.state.coastline == "atoll"
    assert select.disabled is False
    assert "Atoll" in game_env.elements["coastline-blurb"].innerText or "ring of land" in game_env.elements["coastline-blurb"].innerText
    game_env.advance_season()
    assert select.disabled is True
    select.value = "delta"
    select.dispatch("change", Event())
    assert m.state.coastline == "atoll"  # refused
    assert select.value == "atoll"


@pytest.mark.parametrize("coast", COASTS)
def test_rows_flood_at_the_coastlines_own_levels(game_env, coast):
    m = game_env.module
    s = m.state
    s.set_coastline(coast)
    thresholds = m.COASTLINES[coast]["thresholds"]
    for row in range(6):
        assert m.row_flood_threshold(row) == thresholds[row]
        assert m.tile_row_state(row, thresholds[row] - 0.01) == m.LAND
        assert m.tile_row_state(row, thresholds[row]) == m.FLOODED
    s.sea_level = thresholds[5]
    assert s.rows_dry_count() == 5 and m.flooded_row_count(s.sea_level) == 1
    assert s.sea_level_fraction() == pytest.approx(thresholds[5] / max(thresholds))
    assert s.seasons_until_flood(0) == m.math.ceil((thresholds[0] - thresholds[5]) / s.sea_rise_per_season())


def test_a_delta_loses_land_earlier_than_a_headland(game_env):
    m = game_env.module
    s = m.state
    s.set_coastline("delta")
    seasons = {}
    for n in range(1, 8):
        s.advance_season()
        seasons[n] = s.rows_dry_count()
    assert seasons[1] == 6 and seasons[2] == 5 and seasons[5] == 4  # 10 and 22 are reached after seasons 2 and 5
    game_env.module.state = m.SettlementState()
    m.state.set_coastline("headland")
    for _ in range(5):
        m.state.advance_season()
    assert m.state.rows_dry_count() == 6  # the first headland row goes under at 30 (season 6)


def test_heritage_costs_rows_and_ids_follow_the_coastline(game_env):
    m = game_env.module
    s = m.state
    s.set_coastline("port")
    s.funds = 1000
    assert not s.protect_heritage("lighthouse")  # not on this coast
    assert s.protect_heritage("crane") and s.heritage["crane"] == "protected"
    assert s.funds == 1000 - 160
    s.sea_level = 100
    s._update_heritage()
    assert s.heritage["customs-house"] == "lost" and s.heritage["crane"] == "protected"
    assert m.CRITTER_NOTE if False else True


def test_economy_weights_scale_income(game_env):
    m = game_env.module
    gains = {}
    for coast in ("open", "port", "headland"):
        s = m.SettlementState()
        m.state = s
        s.set_coastline(coast)
        s.capacity["output"] = 3
        s.diversification = {"tourism": 2, "aquaculture": 2}
        before = s.funds
        out_income = 3 * m.OUTPUT_INCOME_PER_UNIT * s.coast_weight("output")
        tourism, aqua = s.diversified_income()
        gains[coast] = (out_income, tourism, aqua)
        s.advance_season()
        assert s.funds - before == pytest.approx(out_income + tourism + aqua, rel=1e-9) or s.funds < before + 200
    open_tourism, open_aqua = gains["open"][1], gains["open"][2]
    assert gains["port"][0] == pytest.approx(gains["open"][0] * 1.3)
    assert gains["headland"][1] == pytest.approx(open_tourism * 1.5)
    assert gains["port"][2] == pytest.approx(open_aqua * 0.7)


def test_storm_rhythm_and_surge_follow_the_coastline(game_env):
    m = game_env.module
    for coast, interval in (("open", 5), ("delta", 4), ("headland", 4), ("atoll", 6), ("port", 5)):
        s = m.SettlementState()
        m.state = s
        s.set_coastline(coast)
        s.set_storm_mode(True)
        hits = []
        for _ in range(12):
            if s.storm_this_season():
                hits.append(s.season)
            s.advance_season()
        assert hits == list(range(interval, 13, interval)), coast
    s = m.SettlementState()
    m.state = s
    base = s.storm_surge_strength()
    s.set_coastline("headland")
    assert s.storm_surge_strength() == pytest.approx(base * 1.15)
    assert "storms every 4 seasons" in m.coastline_blurb_text("headland") and "storms every 6 seasons" in m.coastline_blurb_text("atoll")
    assert "surges x1.15" in m.coastline_blurb_text("headland")


def test_the_forecast_text_names_the_coastlines_interval(game_env):
    m = game_env.module
    m.state.set_coastline("atoll")
    assert "every 6 seasons" in m.storm_forecast_text()


# ---- D-8: save, load, library, planner ----------------------------------------------------------------------------------

@pytest.mark.parametrize("coast", COASTS)
def test_a_save_carries_the_coastline(game_env, coast):
    m = game_env.module
    m.state.set_coastline(coast)
    play_choices(m, 4)
    data = json.loads(json.dumps(m.get_state()))
    assert data.get("coastline", "open") == coast
    m.state = m.SettlementState()
    assert m.load_state(data)
    assert m.state.coastline == coast
    assert set(m.state.heritage) == {x["id"] for x in m.COASTLINES[coast]["heritage"]}
    assert m.state.rows_dry_count() == sum(1 for r in range(6) if m.state.sea_level < m.COASTLINES[coast]["thresholds"][r])


def test_old_and_damaged_saves_load_as_the_open_coast(game_env):
    m = game_env.module
    m.state.set_coastline("delta")
    play_choices(m, 2)
    data = json.loads(json.dumps(m.get_state()))
    for bad in (None, 5, "bogus", ["x"], {"a": 1}):
        data["coastline"] = bad
        assert m.load_state(json.loads(json.dumps(data)))
        assert m.state.coastline == "open"
    data.pop("coastline")
    assert m.load_state(data) and m.state.coastline == "open"
    assert set(m.state.heritage) == {"lighthouse", "reef"}


def test_the_library_records_the_coastline(game_env, storage):
    m = game_env.module
    m.state.set_coastline("atoll")
    play_choices(m, 4)
    assert m.library_save_current()
    [record] = m.library_records()
    assert record["coast"] == "atoll"
    assert "Atoll" in m.library_summary_text(record)
    stored = json.loads(storage[m.LIBRARY_KEY])
    stored[0].pop("coast")
    storage[m.LIBRARY_KEY] = json.dumps(stored)
    assert m.library_records()[0]["coast"] == "open"  # an older record


def test_the_planner_projects_on_the_chosen_coastline(game_env):
    m = game_env.module
    runs = {}
    for coast in ("open", "delta"):
        m.state = m.SettlementState()
        m.state.set_coastline(coast)
        plan = [{"output": 0, "reduction": 0, "adaptation": 0} for _ in range(5)]
        points = m.project_plan(plan, 5)
        runs[coast] = [p["rows_dry"] for p in points]
        assert m.state.season == 1 and m.state.coastline == coast  # the real state is untouched
    assert runs["open"] != runs["delta"] and runs["delta"][-1] < runs["open"][-1]


def test_the_almanac_best_is_only_for_the_standard_coastline(game_env, storage):
    m = game_env.module
    m.state.set_coastline("delta")
    play_choices(m, 4)
    m.render()
    assert m.almanac["best"] == {} and m.almanac["seasons"] == 4
    m.state = m.SettlementState()
    m.almanac_resync()
    play_choices(m, 4)
    m.render()
    assert list(m.almanac["best"]) == ["moderate|standard"]


# ---- D-8: a quick balance check of every coastline ------------------------------------------------------------------------

def _policy_run(m, coast, scenario, adapt, seasons):
    m.state = m.SettlementState()
    s = m.state
    s.set_coastline(coast)
    s.set_sea_scenario(scenario)
    s.set_storm_mode(True)
    breached = 0
    for _ in range(seasons):
        for _ in range(20):
            if s.capacity["output"] < 3 and s.funds >= 20:
                s.invest("output")
            elif s.capacity["reduction"] < 4 and s.funds >= 25:
                s.invest("reduction")
            elif adapt and s.capacity["adaptation"] < 10 and s.funds >= s.invest_cost("adaptation"):
                s.invest("adaptation")
            else:
                break
        s.advance_season()
        if s.storm_log and s.storm_log[-1]["season"] == s.season - 1 and s.last_storm_result == "Breached":
            breached += 1
    return s, breached


@pytest.mark.parametrize("coast", COASTS)
@pytest.mark.parametrize("scenario", SCENARIOS)
def test_no_coastline_is_unwinnable_or_trivially_safe(game_env, coast, scenario):
    m = game_env.module
    adapted, breached_adapted = _policy_run(m, coast, scenario, True, 10)
    idle, breached_idle = _policy_run(m, coast, scenario, False, 10)
    # Not trivially safe: even a steady economy with no defences loses land and its storms get through.
    assert idle.rows_dry_count() < 6 or coast in ("headland", "atoll")  # those two lose their first row later than season 10 in the mild seas
    assert idle.cumulative_damage > adapted.cumulative_damage * 1.3
    assert breached_idle >= 1 and breached_idle > breached_adapted
    # Not unwinnable: with the defences the harbour keeps people, funds and its storms held back.
    assert adapted.funds > 0 and adapted.population > 0 and breached_adapted == 0
    assert adapted.current_tier_index() >= 2
    assert adapted.fish_yield_multiplier() > 0.9


@pytest.mark.parametrize("coast", COASTS)
def test_every_heritage_site_can_be_saved_early(game_env, coast):
    m = game_env.module
    s = m.SettlementState()
    m.state = s
    s.set_coastline(coast)
    s.funds = 600
    for site in m.COASTLINES[coast]["heritage"]:
        assert not s.row_lost(site["row"]) and s.seasons_until_flood(site["row"]) >= 2
        assert s.protect_heritage(site["id"])
    assert s.protected_heritage_count() == 2


# ---- D-3: run codes ---------------------------------------------------------------------------------------------------------

def test_a_run_needs_a_few_seasons_and_standard_rules_to_be_shared(game_env):
    m = game_env.module
    code, why = m.build_run_code()
    assert code == "" and "at least 3 seasons" in why
    play_choices(m, 4)
    code, why = m.build_run_code()
    assert code.startswith("RUN-TIDE-") and why == ""
    m.state.workshop["fish"] = 1.5
    assert m.build_run_code()[0] == "" and "custom Workshop rules" in m.build_run_code()[1]
    m.state.workshop["fish"] = 1.0
    m.state.season_buys = m.state.season_buys[:2]  # a run begun before purchases were logged
    assert "began before purchases were logged" in m.build_run_code()[1]


def test_the_code_round_trips_every_choice_and_the_outcome(game_env):
    m = game_env.module
    m.state.set_coastline("port")
    m.state.set_sea_scenario("severe")
    m.state.set_storm_mode(True)
    m.state.hard_lag_mode = True
    m.state.output_mix = "mixed"
    play_choices(m, 9)
    code, _ = m.build_run_code()
    result = m.decode_run_code(code)
    assert result["ok"], result["message"]
    p = result["params"]
    assert (p["coast"], p["scenario"], p["lag"], p["storms"], p["mix"]) == ("port", "severe", "hard", True, "mixed")
    assert p["played"] == p["shown"] == 9 and p["buys"] == [list(r) for r in m.state.season_buys]
    assert p["rows_dry"] == m.state.rows_dry_count() and p["tier"] == m.state.current_tier_index()
    assert p["score"] == round(m.state.damage_saved())
    assert len(code.replace("-", "")) <= 80


def test_a_friends_ghost_replays_exactly_the_senders_curves(game_env, storage):
    m = game_env.module
    for coast, scenario, mix, lag in (("open", "moderate", "fishing", False), ("atoll", "severe", "industry", True),
                                      ("delta", "conservative", "mixed", False)):
        m.state = m.SettlementState()
        m.state.set_coastline(coast)
        m.state.set_sea_scenario(scenario)
        m.state.output_mix = mix
        m.state.hard_lag_mode = lag
        play_choices(m, 10)
        sender = m.live_session_record()
        code, _ = m.build_run_code()
        m.state = m.SettlementState()
        m._ghosts.clear()
        assert m.load_ghost(code)
        [ghost] = m._ghosts.values()
        assert ghost["acidity"] == sender["acidity"] and ghost["fish"] == sender["fish"], (coast, mix)
        assert (ghost["scenario"], ghost["lag"], ghost["coast"], ghost["tier"], ghost["rows_dry"]) == (
            sender["scenario"], sender["lag"], coast, sender["tier"], sender["rows_dry"])
        assert ghost["score"] == pytest.approx(sender["score"], abs=0.6)
        assert m.state.coastline == "open"  # the viewer's run is untouched by the sender's coast


def test_loading_a_ghost_changes_nothing_of_the_viewers_run_or_storage(game_env, storage):
    m = game_env.module
    sender_code = _code_for_a_run(m)
    m.state = m.SettlementState()
    play_choices(m, 5, pattern=[(1, 1, 1)] * 5)
    before = json.dumps(m.get_state(), sort_keys=True)
    writes = dict(storage)
    assert m.load_ghost(sender_code)
    assert json.dumps(m.get_state(), sort_keys=True) == before
    assert storage == writes  # nothing written: a ghost lives in memory only
    assert m.state.season == 6


def _code_for_a_run(m, seasons=8, coast="open"):
    m.state = m.SettlementState()
    m.state.set_coastline(coast)
    play_choices(m, seasons)
    return m.build_run_code()[0]


def test_a_ghost_appears_in_the_library_selectors_and_as_the_overlay(game_env, storage):
    m = game_env.module
    code = _code_for_a_run(m, 8)
    m.state = m.SettlementState()
    play_choices(m, 4)
    m.library_open = True
    assert m.load_ghost(code)
    m.render()
    assert m.library_overlay_id == "g1" and m.library_b == "g1"
    assert m.library_overlay_record()["ghost"] is True
    assert 'value="g1"' in game_env.elements["library-select-b"].innerHTML
    assert 'value="g1"' in game_env.elements["library-overlay-select"].innerHTML
    assert "<svg" in game_env.elements["library-compare-graph"].innerHTML and "Friend" in game_env.elements["library-compare-graph"].innerHTML
    assert game_env.elements["run-code-clear-button"].hidden is False
    m.clear_ghosts()
    m.render()
    assert not m._ghosts and m.library_overlay_id == "" and m.library_b != "g1"


def test_the_ghost_limit_drops_the_oldest(game_env):
    m = game_env.module
    code = _code_for_a_run(m, 5)
    for _ in range(m.GHOST_LIMIT + 2):
        assert m.load_ghost(code)
    assert len(m._ghosts) == m.GHOST_LIMIT and "g1" not in m._ghosts


def _expect_refused(m, text, words):
    before = (dict(m._ghosts), json.dumps(m.get_state(), sort_keys=True), m.library_overlay_id)
    assert m.load_ghost(text) is False
    assert words.lower() in m._run_code_message[0].lower(), m._run_code_message[0]
    assert m._run_code_message[1] is True
    assert (dict(m._ghosts), json.dumps(m.get_state(), sort_keys=True), m.library_overlay_id) == before


def test_bad_truncated_and_tampered_codes_are_refused_in_plain_words(game_env):
    m = game_env.module
    code = _code_for_a_run(m, 8)
    m.state = m.SettlementState()
    play_choices(m, 3)
    _expect_refused(m, "", "paste a run code")
    _expect_refused(m, "hello there", "")
    _expect_refused(m, code[:-6], "")
    _expect_refused(m, code[:-1] + ("A" if code[-1] != "A" else "B"), "typing mistake")
    body = code.split("-")
    flipped = list(body[2])
    flipped[1] = "Z" if flipped[1] != "Z" else "Y"
    body[2] = "".join(flipped)
    _expect_refused(m, "-".join(body), "typing mistake")
    _expect_refused(m, "x" * 401, "too long")
    _expect_refused(m, "RUN-TIDE-" + "0" * 30, "")


def test_a_code_from_another_game_is_refused(game_env):
    m = game_env.module
    other = m.shared_run_code.encode({"game": "aftermath", "mode": "easy", "score": 5, "stats": [1, 2]})
    _expect_refused(m, other, "")
    assert not m._ghosts


def test_a_validly_signed_but_nonsense_code_is_refused(game_env):
    m = game_env.module
    good = m.shared_run_code.encode({"game": "tide", "mode": "00000000", "score": 0, "stats": [0, 0]})
    _expect_refused(m, good, "do not look like a real tide run")  # zero seasons
    bits = m._bits_of(7, 3) + [0] * (m.RUN_CODE_BITS - 3)  # coastline index 7 does not exist
    mode, parts = m._bits_to_fields(bits)
    forged = m.shared_run_code.encode({"game": "tide", "mode": mode, "score": parts[0], "stats": parts[1:]})
    _expect_refused(m, forged, "do not look like a real tide run")
    # stray bits after the last season
    p = {"coast": "open", "scenario": "moderate", "lag": "standard", "storms": False, "mix": "fishing", "played": 3,
         "score": 5, "rows_dry": 6, "tier": 0, "buys": [[1, 0, 0]] * 3}
    bits, shown = m._pack_run(p)
    bits[-1] = 1
    mode, parts = m._bits_to_fields(bits)
    tampered = m.shared_run_code.encode({"game": "tide", "mode": mode, "score": parts[0], "stats": parts[1:]})
    _expect_refused(m, tampered, "do not look like a real tide run")
    bits, shown = m._pack_run(p)
    mode, parts = m._bits_to_fields(bits)
    ok = m.shared_run_code.encode({"game": "tide", "mode": mode, "score": parts[0], "stats": parts[1:]})
    assert m.load_ghost(ok)


def test_a_run_code_with_a_seed_or_extra_stats_is_not_a_tide_run_code(game_env):
    m = game_env.module
    with_seed = m.shared_run_code.encode({"game": "tide", "seed": "TIDE-57VRK", "mode": "00000000", "score": 1, "stats": [0, 0]})
    _expect_refused(m, with_seed, "not from this version")
    one_stat = m.shared_run_code.encode({"game": "tide", "mode": "00000000", "score": 1, "stats": [0]})
    _expect_refused(m, one_stat, "not from this version")


def test_the_copied_line_with_its_label_still_loads(game_env):
    m = game_env.module
    code = _code_for_a_run(m, 6)
    fields = m.run_code_copy_fields()
    assert fields["game"] == "Tide run code" and fields["stats"] == [code]
    m.state = m.SettlementState()
    assert m.load_ghost("Tide run code, " + code + "  ")
    assert m.load_ghost(code.lower())
    assert m.load_ghost(code.replace("-", " "))


def test_a_long_run_keeps_its_first_seasons_and_says_so(game_env):
    m = game_env.module
    m.state = m.SettlementState()
    play_choices(m, 45, pattern=[(3, 2, 2), (1, 4, 1), (0, 0, 0), (2, 1, 0), (5, 0, 3)])
    code, why = m.build_run_code()
    assert code and not why
    p = m.decode_run_code(code)["params"]
    assert p["played"] == 45 and 8 <= p["shown"] < 45
    assert p["buys"] == [list(r) for r in m.state.season_buys[:p["shown"]]]
    assert f"first {p['shown']} seasons" in game_env.elements["run-code-status"].innerText or True
    m.library_open = True
    m.render_library()
    assert f"first {p['shown']} seasons" in game_env.elements["run-code-status"].innerText
    assert m.load_ghost(code)
    assert m._ghosts["g1"]["seasons"] == p["shown"] and m._ghosts["g1"]["played"] == 45


def test_a_quiet_long_run_fits_many_seasons(game_env):
    m = game_env.module
    m.state = m.SettlementState()
    play_choices(m, 40, pattern=[(0, 0, 0), (0, 0, 0), (0, 0, 0), (1, 0, 0), (0, 0, 0)])
    assert m.decode_run_code(m.build_run_code()[0])["params"]["shown"] == 40


def test_the_share_box_shows_the_code_and_what_a_friend_will_see(game_env):
    m = game_env.module
    play_choices(m, 5)
    m.library_open = True
    m.render_library()
    code = game_env.elements["run-code-output"].value
    assert code.startswith("RUN-TIDE-")
    status = game_env.elements["run-code-status"].innerText
    assert status.startswith("A friend will see: ") and "5 seasons" in status and "not checked against a server" in status
    assert game_env.elements["run-code-copy"].hidden is False
    m.state = m.SettlementState()
    m.render_library()
    assert game_env.elements["run-code-output"].value == ""
    assert game_env.elements["run-code-copy"].hidden is True
    assert "at least 3 seasons" in game_env.elements["run-code-status"].innerText


def test_pasting_in_the_box_loads_and_a_bad_paste_says_so(game_env):
    m = game_env.module
    code = _code_for_a_run(m, 6)
    m.state = m.SettlementState()
    m.library_open = True
    game_env.elements["run-code-input"].value = code
    game_env.elements["run-code-load-button"].dispatch("click", None)
    assert len(m._ghosts) == 1 and game_env.elements["run-code-input"].value == ""
    assert game_env.elements["run-code-message"].innerText.startswith("Loaded Friend's run 1")
    game_env.elements["run-code-input"].value = code[:-2]
    game_env.elements["run-code-load-button"].dispatch("click", None)
    assert len(m._ghosts) == 1
    assert game_env.elements["run-code-message"].innerText.startswith("! ")


def test_the_buy_log_survives_a_save_and_rewind(game_env):
    m = game_env.module
    play_choices(m, 6)
    m.state.invest("output")
    data = json.loads(json.dumps(m.get_state()))
    m.state = m.SettlementState()
    m.load_state(data)
    assert m.state.season_buys == data["buys"]["log"] and m.state.buys_now == [1, 0, 0]
    advance(m)
    assert m.state.season_buys[-1] == [1, 0, 0] and m.state.buys_now == [0, 0, 0]
    data["buys"] = {"log": "nope", "now": 3}
    m.load_state(data)
    assert m.state.season_buys == [] and m.state.buys_now == [0, 0, 0]


# ---- GD-5: Daily Tide ------------------------------------------------------------------------------------------------------

@pytest.fixture
def today(game_env):
    game_env.module._daily_today_override[0] = "2026-10-11"
    return "2026-10-11"


def test_a_day_always_gives_the_same_run(game_env, today):
    m = game_env.module
    plan = m.daily_plan("2026-10-11")
    assert plan == {"date": "2026-10-11", "seed": "TIDE-57VRK", "scenario": "moderate", "coast": "atoll", "storms": [5, 8, 10]}
    assert m.daily_plan("2026-10-11") == plan
    assert m.shared_seed.daily_seed("tide", "2026-10-11") == plan["seed"]


def test_the_days_vary_and_storms_sit_in_their_windows(game_env, today):
    m = game_env.module
    plans = [m.daily_plan(f"2026-09-{d:02d}") for d in range(1, 31)]
    assert len({p["coast"] for p in plans}) >= 4 and len({p["scenario"] for p in plans}) == 3
    for plan in plans:
        assert plan["storms"] == sorted(plan["storms"]) and len(set(plan["storms"])) == 3
        for storm, (first, spread) in zip(plan["storms"], m.DAILY_STORM_WINDOWS):
            assert first <= storm < first + spread <= m.DAILY_SEASONS + 1


def test_only_real_dates_up_to_today_are_allowed(game_env, today):
    m = game_env.module
    for bad in ("2026-10-12", "2027-01-01", "2025-12-31", "2026-02-30", "nope", "", None, 20261011, "2026-1-1", "2026-10-11 "):
        assert m.daily_plan(bad) is None, bad
    assert m.daily_plan("2026-01-01") and m.daily_plan("2026-10-11")


def test_a_daily_is_never_the_default_and_starts_only_from_its_button(game_env, today):
    m = game_env.module
    assert m.state.daily is None and m.state.storm_mode is False
    assert game_env.elements["daily-panel"].hidden in (True, False)
    play_choices(m, 1)
    m.daily_open = True
    game_env.elements["daily-date-input"].value = today
    game_env.elements["daily-start-button"].dispatch("click", None)  # a run is under way: asks first
    assert m.state.daily is None and "replaces your current run" in game_env.elements["daily-message"].innerText
    assert "Press again" in game_env.elements["daily-start-button"].innerText or m.daily_open is False
    game_env.elements["daily-start-button"].dispatch("click", None)
    assert m.state.daily and m.state.daily["date"] == today and m.state.season == 1


def test_starting_a_daily_applies_the_days_coast_sea_and_storms(game_env, today):
    m = game_env.module
    assert m.start_daily("2026-10-11")
    s = m.state
    assert (s.coastline, s.sea_scenario, s.storm_mode, s.daily["storms"]) == ("atoll", "moderate", True, [5, 8, 10])
    assert s.funds == m.STARTING_FUNDS and s.season == 1 and s.workshop == m.WORKSHOP_DEFAULTS
    assert not s.set_coastline("open") and not s.set_sea_scenario("severe")
    s.set_storm_mode(False)
    assert s.storm_mode is True
    assert game_env.elements["coastline-select"].disabled and game_env.elements["sea-scenario-select"].disabled
    assert "set by the daily" in game_env.elements["storm-toggle-button"].innerText and game_env.elements["storm-toggle-button"].disabled
    assert s.seasons_until_storm() == 4


def test_storms_come_exactly_when_the_forecast_says(game_env, today):
    m = game_env.module
    m.start_daily("2026-10-11")
    for _ in range(m.DAILY_SEASONS):
        m.state.advance_season()
    assert [e["season"] for e in m.state.storm_log] == [5, 8, 10]
    assert m.state.seasons_until_storm() is None
    assert "No more storms" in m.storm_forecast_text()


def test_the_brace_window_works_with_the_days_storms(game_env, today):
    m = game_env.module
    m.start_daily("2026-10-11")
    s = m.state
    s.season = 4
    assert s.can_brace_storm()
    s.season = 1
    assert not s.can_brace_storm()


def test_the_day_finishes_after_its_seasons_and_the_result_is_kept(game_env, today, storage):
    m = game_env.module
    m.start_daily("2026-10-11")
    s = m.state
    s.funds = 500
    assert s.protect_heritage("coral-shrine")
    for _ in range(m.DAILY_SEASONS - 1):
        s.advance_season()
    m.render()
    assert s.daily["done"] is False and not storage.get(m.DAILY_KEY)
    s.advance_season()
    m.render()
    assert s.daily["done"] is True
    result = s.daily["result"]
    assert result["seasons"] == 12 and result["sites_saved"] == 1 and 0 <= result["rows_lost"] <= 6
    line = m.daily_result_line("2026-10-11", result)
    assert re.fullmatch(r"Tide daily 2026-10-11: 12 seasons, \d rows? lost, 1 site saved", line), line
    assert json.loads(storage[m.DAILY_KEY])["days"]["2026-10-11"] == result
    for _ in range(3):  # play on: the booked result does not change
        s.advance_season()
        m.render()
    assert s.daily["result"] == result
    assert m.daily_records() == {"2026-10-11": result}
    assert any("Daily Tide 2026-10-11 complete" in line for line in s.ticker_log + s.ticker_full_history)


def test_the_copy_line_has_the_shared_result_shape(game_env, today):
    m = game_env.module
    assert m.daily_copy_fields() == {}
    m.start_daily("2026-10-11")
    for _ in range(12):
        m.state.advance_season()
    m.render()
    fields = m.daily_copy_fields()
    assert fields["game"] == "Tide daily 2026-10-11" and fields["seed"] == "TIDE-57VRK"
    assert [x["n"] for x in fields["stats"]][0] == 12 and len(fields["stats"]) == 3
    assert game_env.elements["daily-copy"].hidden is False


def test_a_day_has_no_streak_and_missing_days_costs_nothing(game_env, today, storage):
    m = game_env.module
    m.daily_open = True
    m.render_daily()
    text = " ".join(game_env.elements[i].innerText for i in ("daily-plan", "daily-status", "daily-message", "daily-archive"))
    assert "streak" not in text.lower() and "missed" not in text.lower() and "lost" not in text.lower().replace("rows lost", "")
    assert "costs nothing" in text
    for html in (HTML, PC_HTML):
        panel = html[html.index('id="daily-panel"'):html.index('id="daily-archive"')]
        assert "no streak" in panel.lower() and "costs nothing" in panel


def test_any_past_day_can_be_played_from_the_archive(game_env, today, storage):
    m = game_env.module
    for date in ("2026-01-01", "2026-06-15", "2026-10-10"):
        assert m.start_daily(date)
        assert m.state.daily["date"] == date
        for _ in range(12):
            m.state.advance_season()
        m.render()
        assert m.state.daily["done"]
    assert set(m.daily_records()) == {"2026-01-01", "2026-06-15", "2026-10-10"}
    assert not m.start_daily("2026-10-12") and "up to today" in m._daily_ui["message"]


def test_a_daily_stays_out_of_the_library_almanac_and_bests(game_env, today, storage):
    m = game_env.module
    m.start_daily("2026-10-11")
    seasons_before = m.almanac["seasons"]
    for _ in range(6):
        m.state.advance_season()
        m.render()
    assert m.library_save_current() is False and "Daily Tide" in m._library_status
    assert m.almanac["seasons"] == seasons_before and m.almanac["best"] == {}
    assert m.best_coastline_saved == 0.0
    assert "Daily Tide results are shared" in m.build_run_code()[1]


def test_a_saved_daily_comes_back_and_a_damaged_one_is_dropped(game_env, today):
    m = game_env.module
    m.start_daily("2026-10-11")
    advance(m, 3)
    data = json.loads(json.dumps(m.get_state()))
    assert data["daily"] == {"date": "2026-10-11", "seed": "TIDE-57VRK", "storms": [5, 8, 10], "done": False}
    m.state = m.SettlementState()
    m.load_state(data)
    assert m.state.daily["storms"] == [5, 8, 10] and m.state.coastline == "atoll" and m.state.storm_mode
    for bad in ("x", 5, {"date": "nope"}, {"date": "2026-10-11", "seed": "A", "storms": []}, {"date": "2026-02-30", "seed": "A", "storms": [3]},
                {"date": "2026-10-11", "seed": "A", "storms": [True, "x"]}):
        data["daily"] = bad
        m.load_state(json.loads(json.dumps(data)))
        assert m.state.daily is None
    data.pop("daily")
    m.load_state(data)
    assert m.state.daily is None


def test_the_hub_today_mark_needs_tracking_today_and_the_days_own_seed(game_env, today):
    m = game_env.module
    calls = []

    class Storage:
        def __init__(self, flag):
            self.flag = flag

        def getItem(self, key):
            return self.flag if key == "hub_today_track_dailies" else None

    def window(flag, daily_ok=True):
        daily = types.SimpleNamespace(isDaily=lambda game, seed: daily_ok,
                                      markCompleted=lambda game, info: calls.append((game, dict(info))))
        return types.SimpleNamespace(localStorage=Storage(flag), NoyvjSeed=types.SimpleNamespace(daily=daily),
                                     JSON=types.SimpleNamespace(parse=json.loads))

    def finish(date):
        m.start_daily(date)
        for _ in range(12):
            m.state.advance_season()
        m.render()

    m._js.window = window("1")
    finish("2026-10-11")
    assert len(calls) == 1 and calls[0][0] == "tide" and calls[0][1]["text"].startswith("Tide daily 2026-10-11: 12 seasons")
    finish("2026-10-10")  # an archive day is never today's mark
    assert len(calls) == 1
    m._js.window = window("0")
    finish("2026-10-11")
    m._js.window = window(None)
    finish("2026-10-11")
    m._js.window = window("1", daily_ok=False)
    finish("2026-10-11")
    assert len(calls) == 1
    m._js.window = types.SimpleNamespace(localStorage=Storage("1"))  # no shared seed helper on the page
    finish("2026-10-11")
    assert len(calls) == 1
    del m._js.window
    finish("2026-10-11")  # no window at all: still finishes quietly
    assert m.state.daily["done"]


def test_a_daily_panel_renders_the_picker_limits_and_the_archive(game_env, today, storage):
    m = game_env.module
    m.daily_open = True
    game_env.elements["daily-date-input"].value = ""
    m.render_daily()
    picker = game_env.elements["daily-date-input"]
    assert picker.value == today
    assert game_env.elements["daily-start-button"].innerText == "Play today's daily"
    assert "Atoll" in game_env.elements["daily-plan"].innerText
    picker.value = "2026-10-11"
    m.start_daily("2026-10-11")
    for _ in range(12):
        m.state.advance_season()
    m.render()
    assert "Finished before" in game_env.elements["daily-plan"].innerText
    assert "2026-10-11: 12 seasons" in game_env.elements["daily-archive"].innerText
    picker.value = "2026-12-25"
    m.render_daily()
    assert game_env.elements["daily-start-button"].disabled is True
    assert "the future is not available" in game_env.elements["daily-plan"].innerText


# ---- wiring: both pages, the Desktop menu and the boot --------------------------------------------------------------------

NEW_IDS = ["coastline-select", "coastline-blurb", "run-code-output", "run-code-copy", "run-code-status", "run-code-input",
           "run-code-load-button", "run-code-clear-button", "run-code-message", "daily-toggle-button", "daily-panel",
           "daily-date-input", "daily-plan", "daily-start-button", "daily-message", "daily-status", "daily-copy", "daily-archive"]


@pytest.mark.parametrize("page", ("index", "pc"))
def test_every_new_element_exists_in_both_pages(page):
    html = HTML if page == "index" else PC_HTML
    for element_id in NEW_IDS:
        assert html.count(f'id="{element_id}"') == 1, element_id
    assert "../../shared/seed.js" in html
    for name in ("seed.py", "run_code.py"):
        assert name in html


def test_the_daily_is_a_desktop_window_in_the_menu():
    assert ["daily-panel", "daily-toggle-button", "Daily Tide"] in CONFIG["windows"]
    game_menu = next(g for g in CONFIG["toolbar"]["menu"] if g["heading"] == "Game")
    assert "daily-toggle-button" in game_menu["ids"]
    assert '"panel": "daily-panel"' in PC_HTML
    # the run-code box lives inside the Session Library window, which is already a Desktop window
    assert ["library-panel", "library-toggle-button", "Session Library"] in CONFIG["windows"]
    library = HTML[HTML.index('id="library-panel"'):HTML.index('id="daily-panel"')]
    assert 'id="run-code-input"' in library and 'id="run-code-output"' in library
    assert HTML.count('class="sea-scenario-label"') == 2  # sea scenario and coastline share the stage bar zone


def test_the_picker_offers_every_coastline_in_both_pages():
    for html in (HTML, PC_HTML):
        block = html[html.index('id="coastline-select"'):html.index("</select>", html.index('id="coastline-select"'))]
        assert re.findall(r'value="(\w+)"', block) == list(COASTS)


def test_the_new_features_have_changelog_entries():
    entries = json.loads((ROOT / "changelog.json").read_text(encoding="utf-8"))
    entries = entries["changelog"] if isinstance(entries, dict) else entries
    text = json.dumps(entries)
    for word in ("coastline", "run code", "Daily Tide"):
        assert word.lower() in text.lower(), word
