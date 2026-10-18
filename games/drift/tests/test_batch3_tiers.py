"""I-9 named difficulty tiers and I-25 the per-tier best table."""

import json
import sys

from .fakes import FakeStorage
from .pagefiles import game_source


def _storage(initial=None):
    storage = FakeStorage(initial)
    sys.modules["js"].localStorage = storage
    return storage


def _click(env, element_id):
    env.elements[element_id].dispatch("click", None)


def test_four_named_tiers_cover_distinct_option_sets(game_env):
    m = game_env.module
    assert [t["name"] for t in m.TIERS] == ["Gentle", "Standard", "Rigorous", "Demanding"]
    combos = {(t["calendar"], t["accelerated"], t["crisis"]) for t in m.TIERS}
    assert len(combos) == 4


def test_a_fresh_region_is_gentle_and_the_summary_names_every_change(game_env):
    m = game_env.module
    assert m.current_tier_id() == "gentle"
    assert "no Crisis Calendar" in m.tier_summary_line("gentle")
    assert "Crisis Calendar" in m.tier_summary_line("standard")
    assert "Accelerated Severity" in m.tier_summary_line("rigorous") and "2x" in m.tier_summary_line("rigorous")
    assert "Crisis Start" in m.tier_summary_line("demanding") and "150" in m.tier_summary_line("demanding")
    game_env.module.render()
    assert game_env.elements["tier-summary"].innerText == "Difficulty tier: Gentle"
    assert "base game" in game_env.elements["tier-line"].innerText


def test_picking_a_tier_sets_the_existing_options(game_env):
    m = game_env.module
    region = game_env.region
    _click(game_env, "tier-rigorous-button")
    assert region.calendar_enabled and region.accelerated_severity_enabled and not region.crisis_start_enabled
    assert m.current_tier_id() == "rigorous"
    assert game_env.elements["tier-rigorous-button"].attributes["aria-pressed"] == "true"
    assert game_env.elements["tier-gentle-button"].attributes["aria-pressed"] == "false"
    assert "Rigorous" in game_env.elements["tier-note"].innerText
    _click(game_env, "tier-standard-button")
    assert region.calendar_enabled and not region.accelerated_severity_enabled


def test_demanding_sets_crisis_start_before_round_one(game_env):
    region = game_env.region
    _click(game_env, "tier-demanding-button")
    assert region.crisis_start_enabled and region.funds == game_env.module.CRISIS_START_FUNDS
    assert game_env.module.current_tier_id() == "demanding"
    _click(game_env, "tier-gentle-button")
    assert not region.crisis_start_enabled and region.funds == game_env.module.STARTING_FUNDS


def test_a_tier_that_needs_crisis_start_is_refused_after_round_one(game_env):
    m = game_env.module
    game_env.invest("housing")
    game_env.advance_round()
    assert not m.tier_available("demanding")
    assert game_env.elements["tier-demanding-button"].disabled
    before = (game_env.region.calendar_enabled, game_env.region.accelerated_severity_enabled)
    _click(game_env, "tier-demanding-button")
    assert (game_env.region.calendar_enabled, game_env.region.accelerated_severity_enabled) == before
    ok, message = m.apply_tier("demanding")
    assert not ok and "before round 1" in message
    assert m.tier_available("rigorous")


def test_other_mixes_read_as_custom(game_env):
    m = game_env.module
    game_env.region.accelerated_severity_enabled = True
    assert m.current_tier_id() == "custom"
    game_env.module.render()
    assert "Custom mix" in game_env.elements["tier-summary"].innerText


def test_accelerated_baseline_still_captured_once_through_a_tier(game_env):
    region = game_env.region
    assert region.severity_toggle_dot_baseline is None
    _click(game_env, "tier-rigorous-button")
    first = region.severity_toggle_dot_baseline
    assert first is not None
    _click(game_env, "tier-standard-button")
    _click(game_env, "tier-rigorous-button")
    assert region.severity_toggle_dot_baseline == first


def test_tier_does_not_gate_achievements():
    """Z27: tiers are labels for options that already existed; an achievement check never reads them."""
    source = game_source()
    start = source.index("ACHIEVEMENT_CHECKS")
    checks = source[start:start + 6000]
    assert "current_tier_id" not in checks and "assisted_run" not in checks


# ---- I-25: bests per tier ---------------------------------------------------------------------------
def test_no_best_is_recorded_before_a_round_is_played(game_env):
    storage = _storage()
    game_env.module.render()
    assert game_env.module.tier_bests == {}
    assert "drift_tier_bests_v1" not in storage.data


def test_playing_records_the_current_tier_best(game_env):
    m = game_env.module
    storage = _storage()
    m._today = lambda: "2026-10-11"
    game_env.invest("housing")
    game_env.invest("services")
    game_env.advance_round()
    entry = m.tier_bests["gentle"]
    assert entry["date"] == "2026-10-11" and entry["score"] > 0
    assert entry["band"] == m.wellbeing_band(entry["score"])
    saved = json.loads(storage.data["drift_tier_bests_v1"])
    assert saved["gentle"]["date"] == "2026-10-11"


def test_best_only_moves_up_and_net_positive_only_gets_faster(game_env):
    m = game_env.module
    _storage()
    m._today = lambda: "2026-10-01"
    game_env.invest("housing")
    game_env.advance_round()
    m.tier_bests["gentle"]["score"] = 99.0
    m.tier_bests["gentle"]["net_positive"] = 4
    game_env.advance_round()
    assert m.tier_bests["gentle"]["score"] == 99.0  # a lower score never replaces it
    game_env.region.net_positive_round = 9
    game_env.module.render()
    assert m.tier_bests["gentle"]["net_positive"] == 4  # slower does not replace faster
    game_env.region.net_positive_round = 2
    m._today = lambda: "2026-10-02"
    game_env.module.render()
    assert m.tier_bests["gentle"]["net_positive"] == 2 and m.tier_bests["gentle"]["date"] == "2026-10-02"


def test_each_tier_keeps_its_own_best(game_env):
    m = game_env.module
    _storage()
    game_env.invest("housing")
    game_env.advance_round()
    _click(game_env, "tier-standard-button")
    game_env.advance_round()
    assert set(m.tier_bests) == {"gentle", "standard"}


def test_custom_mix_never_updates_a_tier_best(game_env):
    m = game_env.module
    _storage()
    game_env.region.accelerated_severity_enabled = True
    game_env.advance_round()
    assert m.tier_bests == {}


def test_table_lists_every_tier_and_marks_unplayed_ones(game_env):
    m = game_env.module
    _storage()
    game_env.invest("housing")
    game_env.advance_round()
    html = m.tier_best_table_html()
    for name in ("Gentle", "Standard", "Rigorous", "Demanding"):
        assert name in html
    assert html.count("not played yet") == 3
    assert "Date" in html and "Fastest net-positive" in html and "Best band" in html
    assert game_env.elements["tier-best-table"].innerHTML == html or "Gentle" in game_env.elements["tier-best-table"].innerHTML


def test_stored_bests_load_and_junk_is_dropped(game_env):
    m = game_env.module
    cleaned = m._clean_tier_bests({
        "gentle": {"score": 72.5, "net_positive": 14, "date": "2026-09-30"},
        "standard": {"score": "high", "net_positive": 3, "date": "x"},
        "rigorous": {"score": 140, "net_positive": 3, "date": "2026-01-01"},
        "demanding": {"score": 50, "net_positive": -2, "date": "not a date"},
        "bogus": {"score": 10},
    })
    assert set(cleaned) == {"gentle", "demanding"}
    assert cleaned["gentle"]["band"] == "Thriving" and cleaned["gentle"]["net_positive"] == 14
    assert cleaned["demanding"]["net_positive"] is None and cleaned["demanding"]["date"] == ""
    assert m._clean_tier_bests("nonsense") == {}
    _storage({"drift_tier_bests_v1": "{not json"})
    assert m._load_tier_bests() == {}


def test_blocked_storage_does_not_break_play(game_env):
    class Blocked:
        def getItem(self, key):
            raise RuntimeError("blocked")

        def setItem(self, key, value):
            raise RuntimeError("blocked")

    sys.modules["js"].localStorage = Blocked()
    game_env.invest("housing")
    game_env.advance_round()
    assert "gentle" in game_env.module.tier_bests
