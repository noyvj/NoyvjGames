"""Round-3 batch (2026-10-07): Round Ledger + recap (I-8, I-17), Reset this round
(I-15), Rewind Token (GI-18), Play 5 rounds (GI-30), Region Collection with
personality titles and civic milestones (GI-15, GI-22), live tab title (I-24).
"""

import json
import sys
import types


def _buy(game_env, kind, times=1):
    for _ in range(times):
        game_env.invest(kind)


def _fake_storage():
    """Installs a dict-backed localStorage on the fake js module."""
    store = {}

    class Storage:
        def getItem(self, key):
            return store.get(key)

        def setItem(self, key, value):
            store[key] = value

    sys.modules["js"].localStorage = Storage()
    return store


# --- I-8: Round Ledger --------------------------------------------------------

def test_every_advance_adds_a_ledger_row(game_env):
    game_env.advance_round()
    game_env.advance_round()
    rows = game_env.region.ledger
    assert [r["round"] for r in rows] == [1, 2]
    assert set(rows[0]) == set(game_env.module.LEDGER_FIELDS)


def test_ledger_row_records_spend_split_and_income(game_env):
    _buy(game_env, "housing", 2)
    _buy(game_env, "services")
    game_env.elements["policy-credentialing-button"].dispatch("click", None)
    funds_before = game_env.region.funds
    game_env.advance_round()
    row = game_env.region.ledger[-1]
    assert row["housing"] == 40 and row["services"] == 20 and row["policy"] == 60
    assert row["spent"] == 120
    assert row["arrivals"] == 5
    assert row["income"] == round(game_env.region.funds - funds_before, 2)
    assert row["funds"] == round(game_env.region.funds, 2)


def test_round_spend_resets_each_round_but_lifetime_spend_keeps_growing(game_env):
    _buy(game_env, "housing")
    game_env.advance_round()
    assert sum(game_env.region.round_spend.values()) == 0
    _buy(game_env, "housing")
    assert game_env.region.round_spend["housing"] == 20
    assert game_env.region.spend_by_type["housing"] == 40


def test_reallocation_fee_is_recorded_as_realloc_spend(game_env):
    _buy(game_env, "housing", 2)
    assert game_env.region.reallocate("housing", "services")
    game_env.advance_round()
    assert game_env.region.ledger[-1]["realloc"] == game_env.module.REALLOCATION_FUNDS_COST


def test_ledger_row_matches_what_the_player_sees_after_the_round(game_env):
    game_env.advance_round()
    row = game_env.region.ledger[-1]
    assert row["strain"] == round(game_env.region.strain_fraction(), 2)
    assert row["wellbeing"] == round(game_env.region.wellbeing_score(), 2)
    assert row["pending"] == round(game_env.region.pending_population(), 2)


def test_ledger_is_capped(game_env):
    module = game_env.module
    for _ in range(module.LEDGER_MAX_ENTRIES + 15):
        game_env.advance_round()
    assert len(game_env.region.ledger) == module.LEDGER_MAX_ENTRIES
    assert game_env.region.ledger[-1]["round"] == module.LEDGER_MAX_ENTRIES + 15


def test_ledger_sort_and_filter(game_env):
    _buy(game_env, "housing")
    game_env.advance_round()
    for _ in range(3):
        game_env.advance_round()
    module = game_env.module
    assert [r["round"] for r in module.ledger_rows("round_desc")] == [4, 3, 2, 1]
    assert [r["round"] for r in module.ledger_rows("round_asc")] == [1, 2, 3, 4]
    assert [r["round"] for r in module.ledger_rows("spent", "all")][0] == 1
    assert [r["round"] for r in module.ledger_rows("round_asc", "purchases")] == [1]
    assert [r["round"] for r in module.ledger_rows("round_asc", "no_purchases")] == [2, 3, 4]
    assert module.ledger_rows("round_asc", "auto") == []
    # Unknown keys fall back to the defaults rather than failing.
    assert len(module.ledger_rows("nonsense", "nonsense")) == 4


def test_strained_filter_finds_only_strained_rounds(game_env):
    _buy(game_env, "housing", 10)  # 100 capacity: calm at first, then arrivals outrun it
    for _ in range(12):
        game_env.advance_round()
    module = game_env.module
    strained = module.ledger_rows("round_asc", "strained")
    assert strained and all(r["strain"] >= 0.25 for r in strained)
    assert len(strained) < len(game_env.region.ledger)


def test_ledger_csv_has_header_and_one_line_per_round(game_env):
    game_env.advance_round()
    game_env.advance_round()
    lines = game_env.module.ledger_csv().split("\n")
    assert lines[0].startswith("round,income,spent,")
    assert "strain_pct" in lines[0].split(",")
    assert len(lines) == 3
    assert lines[1].split(",")[0] == "1" and lines[2].split(",")[0] == "2"
    assert lines[1].split(",")[-1] == "no"


def test_ledger_panel_toggle_and_table(game_env):
    toggle = game_env.elements["ledger-toggle-button"]
    assert toggle.innerText == "📒 Round Ledger (0)"
    assert game_env.elements["ledger-panel"].hidden is True
    game_env.advance_round()
    assert toggle.innerText == "📒 Round Ledger (1)"
    toggle.dispatch("click", None)
    assert game_env.elements["ledger-panel"].hidden is False
    assert toggle.innerText == "Hide Round Ledger"
    assert "<table" in game_env.elements["ledger-table"].innerHTML
    assert "1 round(s) recorded" in game_env.elements["ledger-summary"].innerText
    toggle.dispatch("click", None)
    assert game_env.elements["ledger-panel"].hidden is True


def test_empty_ledger_says_so_and_cannot_be_copied(game_env):
    game_env.elements["ledger-toggle-button"].dispatch("click", None)
    assert "No rounds resolved yet" in game_env.elements["ledger-summary"].innerText
    assert game_env.elements["copy-ledger-csv-button"].disabled is True


def test_sort_and_filter_selects_drive_the_table(game_env):
    for _ in range(3):
        game_env.advance_round()
    game_env.elements["ledger-toggle-button"].dispatch("click", None)
    game_env.elements["ledger-sort-select"].value = "round_asc"
    game_env.elements["ledger-sort-select"].dispatch("change", None)
    html = game_env.elements["ledger-table"].innerHTML
    assert html.index("<td>1</td>") < html.index("<td>3</td>")
    game_env.elements["ledger-filter-select"].value = "purchases"
    game_env.elements["ledger-filter-select"].dispatch("change", None)
    assert "showing 0" in game_env.elements["ledger-summary"].innerText


def test_copy_csv_falls_back_to_a_text_box_without_a_clipboard(game_env):
    game_env.advance_round()
    game_env.elements["copy-ledger-csv-button"].dispatch("click", None)
    area = game_env.elements["ledger-copy-area"]
    assert area.hidden is False
    assert area.value.startswith("round,income")
    assert "Could not copy" in game_env.elements["ledger-copy-status"].innerText


def test_copy_csv_uses_the_clipboard_when_there_is_one(game_env):
    copied = []
    sys.modules["js"].navigator = types.SimpleNamespace(
        clipboard=types.SimpleNamespace(writeText=lambda text: copied.append(text))
    )
    game_env.advance_round()
    game_env.elements["copy-ledger-csv-button"].dispatch("click", None)
    assert copied and copied[0].startswith("round,income")
    assert game_env.elements["ledger-copy-area"].hidden is True
    assert "Copied" in game_env.elements["ledger-copy-status"].innerText


# --- I-17: recap line -----------------------------------------------------------

def test_recap_is_hidden_before_the_first_round_then_describes_the_last_one(game_env):
    assert game_env.elements["round-recap-details"].hidden is True
    _buy(game_env, "housing", 3)
    game_env.advance_round()
    assert game_env.elements["round-recap-details"].hidden is False
    text = game_env.elements["round-recap-display"].innerText
    assert text.startswith("Round 1: 5 arrived")
    assert "capacity covered everyone" in text
    assert "spent 60" in text


def test_recap_names_a_capacity_shortfall_and_strain_direction(game_env):
    for _ in range(6):
        game_env.advance_round()
    text = game_env.elements["round-recap-display"].innerText
    assert "people beyond capacity" in text
    assert "strain up" in text or "strain steady" in text


def test_recap_message_trend_words(game_env):
    module = game_env.module
    row = dict(round=3, arrivals=10.0, integrated_new=4.0, shortfall=0.0, strain=0.10, income=50.0, spent=0.0)
    assert "strain steady" in module.round_recap_message(row, 0.10)
    assert "strain down" in module.round_recap_message(row, 0.30)
    assert "strain up" in module.round_recap_message(row, 0.0)


# --- ledger and spend in the save --------------------------------------------------

def test_fresh_region_save_gains_no_new_keys(game_env):
    data = game_env.module.get_state()
    for key in ("ledger", "spend_by_type", "round_spend", "rewind_used_round", "collection"):
        assert key not in data


def test_ledger_and_spend_round_trip_through_a_save(game_env):
    _buy(game_env, "services", 2)
    game_env.advance_round()
    _buy(game_env, "housing")
    data = json.loads(json.dumps(game_env.module.get_state()))
    assert len(data["ledger"][0]) == len(game_env.module.LEDGER_FIELDS)
    before = [dict(r) for r in game_env.region.ledger]
    game_env.module.load_state(data)
    assert game_env.region.ledger == before
    assert game_env.region.spend_by_type["services"] == 40
    assert game_env.region.round_spend["housing"] == 20


def test_old_save_without_ledger_keys_loads_with_an_empty_ledger(game_env):
    game_env.advance_round()
    data = game_env.module.get_state()
    for key in ("ledger", "spend_by_type", "round_spend", "collection", "rewind_used_round"):
        data.pop(key, None)
    game_env.module.load_state(data)
    assert game_env.region.ledger == []
    assert game_env.region.spend_by_type["housing"] == 0


def test_corrupt_ledger_rows_are_skipped(game_env):
    game_env.advance_round()
    data = game_env.module.get_state()
    good = data["ledger"][0]
    bad_len = good[:-1]
    bad_round = [0] + good[1:]
    bad_number = [good[0], float("nan")] + good[2:]
    bad_type = ["x"] + good[1:]
    data["ledger"] = [bad_len, bad_round, bad_number, bad_type, "nope", good]
    game_env.module.load_state(data)
    assert len(game_env.region.ledger) == 1


def test_non_list_ledger_loads_empty(game_env):
    game_env.advance_round()
    data = game_env.module.get_state()
    data["ledger"] = {"a": 1}
    game_env.module.load_state(data)
    assert game_env.region.ledger == []


# --- I-15: Reset this round -------------------------------------------------------

def test_reset_is_disabled_until_a_decision_is_made(game_env):
    button = game_env.elements["reset-round-button"]
    assert button.disabled is True
    _buy(game_env, "housing")
    assert button.disabled is False
    assert "1 decision)" in button.innerText


def test_reset_refunds_purchases_policies_and_reallocations(game_env):
    start_funds = game_env.region.funds
    _buy(game_env, "housing", 2)
    _buy(game_env, "services")
    game_env.elements["policy-sponsorship-button"].dispatch("click", None)
    assert game_env.region.round_buys == 4
    game_env.elements["reset-round-button"].dispatch("click", None)
    region = game_env.region
    assert region.funds == start_funds
    assert region.total_capacity() == 0
    assert region.policy_level["sponsorship"] == 0
    assert region.cumulative_services_investment == 0
    assert all(v == 0 for v in region.spend_by_type.values())
    assert all(v == 0 for v in region.round_spend.values())
    assert region.round_buys == 0
    assert game_env.elements["reset-round-button"].disabled is True
    assert "refunded" in game_env.elements["round-tools-note"].innerText


def test_reset_only_goes_back_to_the_start_of_this_round(game_env):
    _buy(game_env, "housing", 2)
    game_env.advance_round()
    funds = game_env.region.funds
    capacity = game_env.region.capacity["housing"]
    _buy(game_env, "housing")
    game_env.elements["reset-round-button"].dispatch("click", None)
    assert game_env.region.funds == funds
    assert game_env.region.capacity["housing"] == capacity


def test_reset_and_rewind_do_not_replay_achievement_toasts(game_env):
    _buy(game_env, "housing")
    assert game_env.elements["achievement-toast"].hidden is False  # first investment
    game_env.elements["achievement-toast"].hidden = True
    game_env.elements["reset-round-button"].dispatch("click", None)
    assert game_env.elements["achievement-toast"].hidden is True


def test_reset_with_nothing_to_undo_changes_nothing(game_env):
    assert game_env.module.reset_round() is False


def test_reset_undoes_neighbour_moves_too(game_env):
    module = game_env.module
    for _ in range(3):
        game_env.advance_round()
    game_env.region.funds = 500.0
    game_env.region.capacity["housing"] = 2000.0  # calm, so support is allowed
    module.round_start_snapshot = module._take_round_start_snapshot()
    assert module.open_neighbor()
    snapshot = module._take_round_start_snapshot()
    module.round_start_snapshot = snapshot
    funds = game_env.region.funds
    neighbor_funds = module.neighbor.funds
    assert module.invest_neighbor("services")
    assert module.support_neighbor()
    assert game_env.region.round_buys == 2
    assert module.reset_round()
    assert game_env.region.funds == funds
    assert module.neighbor.funds == neighbor_funds
    assert module.neighbor_support_sent == 0


def test_reset_is_not_possible_right_after_loading_a_save(game_env):
    _buy(game_env, "housing")
    data = game_env.module.get_state()
    game_env.module.load_state(data)
    assert game_env.region.round_buys == 0
    assert game_env.elements["reset-round-button"].disabled is True


def test_crisis_start_toggle_does_not_get_undone_by_reset(game_env):
    game_env.elements["crisis-start-toggle-button"].dispatch("click", None)
    funds = game_env.region.funds
    assert funds == game_env.module.CRISIS_START_FUNDS
    _buy(game_env, "housing")
    game_env.elements["reset-round-button"].dispatch("click", None)
    assert game_env.region.funds == funds


# --- GI-18: Rewind Token -----------------------------------------------------------

def test_rewind_is_unavailable_before_any_advance(game_env):
    button = game_env.elements["rewind-button"]
    assert button.disabled is True
    assert game_env.module.use_rewind_token() is False


def test_rewind_needs_two_clicks_and_restores_the_pre_advance_state(game_env):
    _buy(game_env, "housing", 2)
    expected_funds = game_env.region.funds
    game_env.advance_round()
    assert game_env.region.round_number == 2
    button = game_env.elements["rewind-button"]
    assert button.disabled is False and "1 left" in button.innerText
    button.dispatch("click", None)
    assert game_env.region.round_number == 2  # armed only
    assert button.innerText.startswith("Confirm")
    button.dispatch("click", None)
    region = game_env.region
    assert region.round_number == 1
    assert region.funds == expected_funds
    assert region.capacity["housing"] == 20
    assert region.ledger == []
    assert region.strain_log == [] and region.total_arrivals == 0
    assert region.rewind_used_round == 1
    assert "Rewind Token used in round 1" in button.innerText
    assert button.disabled is True
    assert "Rewound" in game_env.elements["round-tools-note"].innerText


def test_arming_is_cancelled_by_any_other_action(game_env):
    game_env.advance_round()
    button = game_env.elements["rewind-button"]
    button.dispatch("click", None)
    assert button.innerText.startswith("Confirm")
    _buy(game_env, "housing")
    assert not button.innerText.startswith("Confirm")
    button.dispatch("click", None)
    assert game_env.region.round_number == 2  # only armed again, not rewound


def test_rewind_can_only_be_used_once_per_region(game_env):
    game_env.advance_round()
    assert game_env.module.use_rewind_token() is True
    game_env.advance_round()
    assert game_env.module.rewind_available() is False
    assert game_env.module.use_rewind_token() is False
    assert game_env.region.round_number == 2


def test_rewind_returns_to_a_round_you_can_still_change(game_env):
    _buy(game_env, "housing", 3)
    game_env.advance_round()
    game_env.module.use_rewind_token()
    _buy(game_env, "services")
    game_env.advance_round()
    assert game_env.region.ledger[-1]["services"] == 20
    assert game_env.region.ledger[-1]["housing"] == 60  # the earlier purchases came back with it


def test_reset_after_a_rewind_goes_back_to_that_rounds_start(game_env):
    game_env.advance_round()
    _buy(game_env, "housing")
    game_env.advance_round()
    funds_at_round_two_start = game_env.region.ledger[0]["funds"]
    game_env.module.use_rewind_token()  # back to just before round 2 resolved
    _buy(game_env, "infrastructure")
    game_env.elements["reset-round-button"].dispatch("click", None)
    # The rewind restored round 2 with its housing purchase; Reset then goes back to round 2's start.
    assert round(game_env.region.funds, 2) == funds_at_round_two_start
    assert game_env.region.capacity["housing"] == 0


def test_rewind_used_marker_survives_a_save_but_not_the_snapshot(game_env):
    game_env.advance_round()
    game_env.module.use_rewind_token()
    data = json.loads(json.dumps(game_env.module.get_state()))
    assert data["rewind_used_round"] == 1
    game_env.module.load_state(data)
    assert game_env.region.rewind_used_round == 1
    assert game_env.elements["rewind-button"].disabled is True


def test_a_loaded_save_has_nothing_to_rewind(game_env):
    game_env.advance_round()
    game_env.module.load_state(game_env.module.get_state())
    assert game_env.module.rewind_available() is False
    assert game_env.elements["rewind-button"].disabled is True


def test_bad_rewind_marker_in_a_save_loads_as_unused(game_env):
    data = game_env.module.get_state()
    for bad in (0, -3, "x", True, 2.5):
        data["rewind_used_round"] = bad
        game_env.module.load_state(data)
        assert game_env.region.rewind_used_round is None


def test_rewind_restores_the_neighbour_too(game_env):
    module = game_env.module
    for _ in range(3):
        game_env.advance_round()
    module.open_neighbor()
    neighbor_round = module.neighbor.round_number
    game_env.advance_round()
    assert module.neighbor.round_number == neighbor_round + 1
    module.use_rewind_token()
    assert module.neighbor.round_number == neighbor_round


# --- GI-30: Play 5 rounds ---------------------------------------------------------

def test_play_rounds_advances_five_rounds_when_nothing_interrupts(game_env):
    _buy(game_env, "housing", 12)  # 120 capacity covers the next five rounds' arrivals
    game_env.elements["play-rounds-button"].dispatch("click", None)
    assert game_env.region.round_number == 6
    assert all(r["auto"] for r in game_env.region.ledger)
    assert "Played 5 rounds with your current allocation" in game_env.elements["round-tools-note"].innerText


def test_play_rounds_stops_after_the_round_strain_rises_a_level(game_env):
    game_env.elements["play-rounds-button"].dispatch("click", None)
    advanced = game_env.region.round_number - 1
    assert 1 <= advanced < 5
    note = game_env.elements["round-tools-note"].innerText
    assert "stopped early: strain rose to" in note
    assert game_env.region.strain_level() != "stable"


def test_play_rounds_stops_when_a_second_wave_is_announced(game_env):
    module = game_env.module
    region = game_env.region
    region.capacity["services"] = 400.0
    region.capacity["housing"] = 600.0  # keeps strain at zero
    region.round_number = 9
    region.total_arrivals = 100.0
    region.integrated_population = 95.0
    advanced, reason = module.play_rounds()
    assert region.second_wave_status == "warned"
    assert reason == "a second wave was announced"
    assert advanced == 2  # rounds 9 and 10: the warning comes when round 10 resolves


def test_play_rounds_logs_and_flags_are_counted_in_the_ledger_filter(game_env):
    game_env.elements["play-rounds-button"].dispatch("click", None)
    assert len(game_env.module.ledger_rows("round_asc", "auto")) == game_env.region.round_number - 1


def test_play_rounds_does_not_buy_anything(game_env):
    start = game_env.region.funds
    game_env.elements["play-rounds-button"].dispatch("click", None)
    assert game_env.region.total_capacity() == 0
    assert game_env.region.funds >= start  # income only


def test_rewind_after_play_rounds_undoes_only_the_last_round(game_env):
    _buy(game_env, "housing", 12)
    game_env.elements["play-rounds-button"].dispatch("click", None)
    assert game_env.region.round_number == 6
    game_env.module.use_rewind_token()
    assert game_env.region.round_number == 5


def test_play_rounds_stops_when_the_neighbour_goes_critical(game_env):
    module = game_env.module
    for _ in range(3):
        game_env.advance_round()
    game_env.region.capacity["housing"] = 5000.0  # the main region stays calm
    module.open_neighbor()
    module.neighbor.capacity["housing"] = 100.0
    module.neighbor.total_arrivals = 100.0
    module.neighbor.background_severity = 100.0  # next round's arrivals swamp it
    assert module.neighbor_spillover() == 0.0
    advanced, reason = module.play_rounds()
    assert advanced == 1
    assert reason == "the neighbouring district went critical and is sending people your way"


# --- GI-15: personality titles ------------------------------------------------------

def test_no_title_until_enough_has_been_spent(game_env):
    module = game_env.module
    assert module.region_title_key(game_env.region) is None
    _buy(game_env, "housing", 2)
    assert module.region_title_key(game_env.region) is None
    assert "still forming" in game_env.elements["region-title-display"].innerText


def test_each_title_fits_its_spending_pattern(game_env):
    module = game_env.module
    region = game_env.region
    cases = {
        "builder": {"housing": 200, "services": 40, "infrastructure": 25, "policy": 0},
        "educator": {"housing": 20, "services": 200, "infrastructure": 25, "policy": 0},
        "engineer": {"housing": 60, "services": 60, "infrastructure": 150, "policy": 0},
        "reformer": {"housing": 60, "services": 60, "infrastructure": 25, "policy": 120},
        "balancer": {"housing": 80, "services": 80, "infrastructure": 75, "policy": 0},
    }
    for expected, split in cases.items():
        region.spend_by_type.update(split)
        assert module.region_title_key(region) == expected, expected


def test_lopsided_but_below_every_threshold_has_no_title(game_env):
    region = game_env.region
    region.spend_by_type.update({"housing": 90, "services": 10, "infrastructure": 60, "policy": 40})
    assert game_env.module.region_title_key(region) is None


def test_the_strongest_pattern_wins_when_two_qualify(game_env):
    region = game_env.region
    region.spend_by_type.update({"housing": 100, "services": 0, "infrastructure": 0, "policy": 100})
    # builder qualifies at exactly 50% (margin 0); reformer is at 50% against a 30% bar (margin 0.2)
    assert game_env.module.region_title_key(region) == "reformer"


def test_title_is_collected_only_from_round_eight_and_persisted(game_env):
    store = _fake_storage()
    module = game_env.module
    game_env.region.spend_by_type.update({"housing": 200, "services": 0, "infrastructure": 0, "policy": 0})
    for _ in range(module.TITLE_MIN_ROUND - 1):
        game_env.advance_round()
    assert module.collection["titles"] == []
    game_env.advance_round()
    assert module.collection["titles"] == ["builder"]
    assert json.loads(store[module.COLLECTION_STORAGE_KEY])["titles"] == ["builder"]
    assert "The Builder" in game_env.elements["region-title-display"].innerText
    assert game_env.elements["achievement-toast"].hidden is False


def test_collection_loads_from_storage_at_start(game_env):
    store = _fake_storage()
    store["drift_collection_v1"] = json.dumps({"titles": ["educator", "bogus"], "civic": {"ring_road": 14, "x": 3, "night_classes": 0}})
    loaded = game_env.module._load_collection()
    assert loaded == {"titles": ["educator"], "civic": {"ring_road": 14}}


def test_collection_ignores_garbage_storage(game_env):
    store = _fake_storage()
    for raw in ("not json", "[1,2]", json.dumps({"titles": "x", "civic": 5}), "null", ""):
        store["drift_collection_v1"] = raw
        assert game_env.module._load_collection() == {"titles": [], "civic": {}}


def test_clean_collection_validates_every_field(game_env):
    clean = game_env.module._clean_collection
    assert clean(None) == {"titles": [], "civic": {}}
    out = clean({"titles": ["builder", "builder", "nope", 3], "civic": {"first_roof_fund": True, "ring_road": 2.5, "steady_hands": 9}})
    assert out == {"titles": ["builder"], "civic": {"steady_hands": 9}}


# --- GI-22: civic milestones ----------------------------------------------------------

def test_first_roof_fund_is_found_by_round_five_and_not_later(game_env):
    module = game_env.module
    _buy(game_env, "housing", 10)
    game_env.advance_round()
    assert module.collection["civic"] == {"first_roof_fund": 1}
    assert "First Roof Fund" in game_env.elements["achievement-toast-text"].innerText
    assert "New in your collection" in module.collection_note


def test_a_milestone_missed_by_its_round_stays_locked(game_env):
    module = game_env.module
    for _ in range(6):
        game_env.advance_round()
    _buy(game_env, "housing", 12)
    game_env.advance_round()
    assert "first_roof_fund" not in module.collection["civic"]


def test_found_milestones_are_never_lost_or_found_twice(game_env):
    module = game_env.module
    _buy(game_env, "housing", 10)
    game_env.advance_round()
    game_env.region.capacity["housing"] = 0.0
    game_env.advance_round()
    assert module.collection["civic"] == {"first_roof_fund": 1}
    assert module.collection_note == ""


def test_every_milestone_is_reachable_with_a_plain_strategy(game_env):
    """A single scripted region that builds everything early finds all ten, so the
    collection is completable and no hint is a lie."""
    module = game_env.module
    region = game_env.region
    # Round 1: spend on the early bars (200 housing funds, 120 services funds).
    _buy(game_env, "housing", 10)
    _buy(game_env, "services", 6)
    game_env.advance_round()
    for round_number in range(2, 31):
        region.funds = max(region.funds, 400.0)
        if round_number == 3:
            module.open_neighbor()
        if round_number == 4:
            region.funds = 600.0
            module.support_neighbor()
        housing_limit = 120 if round_number < 10 else 700
        for kind, limit in (("housing", housing_limit), ("services", 110), ("infrastructure", 125)):
            while region.capacity[kind] < limit and region.funds >= module.INVEST_COST[kind]:
                game_env.invest(kind)
        for policy in ("credentialing", "language_access", "sponsorship"):
            game_env.elements[f"policy-{policy.replace('_', '-')}-button"].dispatch("click", None)
        game_env.advance_round()
    found = set(module.collection["civic"])
    expected = {entry["id"] for entry in module.CIVIC_MILESTONES}
    assert found >= expected - {"quiet_weather"}, expected - found
    # Quiet Weather needs the second wave to hold; check its test directly.
    region.second_wave_result = "held"
    assert module.CIVIC_BY_ID["quiet_weather"]["test"](region, 40)


def test_every_milestone_has_a_name_hint_and_line(game_env):
    for entry in game_env.module.CIVIC_MILESTONES:
        assert entry["name"] and entry["hint"] and entry["text"]
    ids = [e["id"] for e in game_env.module.CIVIC_MILESTONES]
    assert len(ids) == len(set(ids)) == 10


def test_collection_panel_shows_hints_for_locked_and_text_for_found(game_env):
    game_env.elements["collection-toggle-button"].dispatch("click", None)
    html = game_env.elements["collection-list"].innerHTML
    assert html.count("Locked") == 10 + 5
    assert "Hint: Reach 100 Housing capacity by round 5." in html
    assert "First Roof Fund" not in html  # a locked entry does not give its name away
    _buy(game_env, "housing", 10)
    game_env.advance_round()
    html = game_env.elements["collection-list"].innerHTML
    assert "✓ First Roof Fund" in html
    assert game_env.elements["collection-summary-display"].innerText == "Collection: 1/10 civic milestones, 0/5 titles."


def test_collection_button_shows_progress_and_toggles(game_env):
    toggle = game_env.elements["collection-toggle-button"]
    assert toggle.innerText == "🗂️ Collection (0/15)"
    toggle.dispatch("click", None)
    assert toggle.innerText == "Hide Collection"
    assert game_env.elements["collection-panel"].hidden is False
    toggle.dispatch("click", None)
    assert game_env.elements["collection-panel"].hidden is True


def test_collection_rides_the_save_and_merges_into_the_browsers_collection(game_env):
    module = game_env.module
    _buy(game_env, "housing", 10)
    game_env.advance_round()
    data = json.loads(json.dumps(module.get_state()))
    assert data["collection"]["civic"] == {"first_roof_fund": 1}
    module.collection["civic"].clear()
    module.collection["civic"]["ring_road"] = 12
    module.load_state(data)
    assert module.collection["civic"] == {"ring_road": 12, "first_roof_fund": 1}


def test_a_bad_collection_in_a_save_is_ignored(game_env):
    data = game_env.module.get_state()
    data["collection"] = {"titles": ["builder", 7], "civic": {"first_roof_fund": "x", "ring_road": 5}}
    game_env.module.load_state(data)
    assert game_env.module.collection == {"titles": ["builder"], "civic": {"ring_road": 5}}
    data["collection"] = "garbage"
    assert game_env.module.load_state(data) is True


# --- I-24: tab title ------------------------------------------------------------------

def test_tab_title_tracks_round_strain_and_region_name(game_env):
    module = game_env.module
    assert module.tab_title() == "Drift - R1 - Stable"
    game_env.region.region_name = "Harbourside"
    game_env.advance_round()
    assert module.tab_title().startswith("Drift - R2 - ")
    assert module.tab_title().endswith(" - Harbourside")
    assert sys.modules["js"].document.title == module.tab_title()
