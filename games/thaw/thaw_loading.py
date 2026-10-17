"""load_state(): restores a save into the live game, then redraws."""

import math

from js import document

import thaw_runstate as runstate
from thaw_achievements import _seed_achievement_toast_baseline
from thaw_bridge import _num
from thaw_mechanics import CARBON_BANK_CAP, CRATE_MAX, FRAMINGS
from thaw_model import region, region_b, region_c, region_d
from thaw_presets import _clean_custom_preset
from thaw_renderer import render
from thaw_saveparts import _apply_region_state, load_problems, render_load_notice, sanitize_save
from thaw_sciencelog import MAX_PINNED, _cap_science_log, science_log


def load_state(data):
    """Take the dict from get_state() (possibly from a previous session)
    and restore the game to that point, across all four regions, then
    re-render so the UI reflects the loaded state immediately. The exact
    inverse of get_state() (except "achievements_earned" -- see
    get_state()'s own comment, that key is never read back).

    A non-dict payload is rejected outright rather than raising. A dict
    missing "region_b"/"region_c"/"region_d" entirely — e.g. a save made
    before that region existed — leaves that region's live state
    untouched instead of crashing, same reasoning as every other
    per-field fallback in _apply_region_state()."""
    if not isinstance(data, dict):
        load_problems[:] = ["the whole save (it is not a game save at all)"]
        render_load_notice()
        return False
    data, found = sanitize_save(data)
    load_problems[:] = found
    runstate.undo_used = data.get("undo_used") is True
    runstate._undo_snapshot = None
    runstate.long_game = data.get("long_game") is True
    runstate.hard_mode = data.get("hard_mode") is True
    runstate.custom_preset = _clean_custom_preset(data.get("custom_preset"))
    if "custom_preset" in data and runstate.custom_preset is None:
        load_problems.append("custom preset")
    # GG-2: strict bool; never together with the long game; the run result only counts if the mode
    # is on and every field is in range.
    runstate.hold_the_line = data.get("hold_the_line") is True and not runstate.long_game
    runstate.run_over = False
    runstate.run_result = None
    runstate.just_escalated = 0
    saved_run = data.get("run")
    if runstate.hold_the_line and isinstance(saved_run, dict):
        survived = saved_run.get("survived")
        saved_avg = saved_run.get("saved")
        reason = saved_run.get("reason")
        if (
            _num(survived, 0, 1000000) and isinstance(survived, int)
            and _num(saved_avg, -1000000, 1000000000) and reason in ("tipped", "limit")
        ):
            runstate.run_over = True
            runstate.run_result = {"survived": survived, "saved": float(saved_avg), "reason": reason}
    region_data = data.get("region")
    if isinstance(region_data, dict):
        _apply_region_state(region, region_data)
    region_b_data = data.get("region_b")
    if isinstance(region_b_data, dict):
        _apply_region_state(region_b, region_b_data)
    region_c_data = data.get("region_c")
    if isinstance(region_c_data, dict):
        _apply_region_state(region_c, region_c_data)
    region_d_data = data.get("region_d")
    if isinstance(region_d_data, dict):
        _apply_region_state(region_d, region_d_data)
    runstate.info_page_open = data.get("info_page_open", runstate.info_page_open)
    runstate.worst_case_region_revealed = data.get(
        "worst_case_region_revealed", runstate.worst_case_region_revealed
    )
    runstate.preset_used_ever = data.get("preset_used_ever", runstate.preset_used_ever)
    runstate.worst_case_intro_seen = data.get("worst_case_intro_seen", runstate.worst_case_intro_seen)
    # G27: validated -- non-negative ints with hits never above total; the
    # locked-in guess and last result are per-session and reset on load.
    runstate.forecast_guess = None
    runstate.forecast_last = None
    runstate.forecast_total = 0
    runstate.forecast_hits = 0
    runstate.forecast_miss_total = 0.0
    saved_bank = data.get("carbon_bank")
    if isinstance(saved_bank, int) and not isinstance(saved_bank, bool) and 0 <= saved_bank <= CARBON_BANK_CAP:
        runstate.carbon_bank = saved_bank
    else:
        runstate.carbon_bank = 0
    runstate.convoys_sent = 0
    runstate.convoy_tax_lost = 0.0
    saved_routing = data.get("routing")
    if isinstance(saved_routing, dict):
        convoys = saved_routing.get("convoys")
        lost = saved_routing.get("tax_lost")
        if (
            isinstance(convoys, int) and not isinstance(convoys, bool) and 0 <= convoys <= 1000000
            and isinstance(lost, (int, float)) and not isinstance(lost, bool)
            and math.isfinite(lost) and 0 <= lost <= 100000000
        ):
            runstate.convoys_sent = convoys
            runstate.convoy_tax_lost = float(lost)
    runstate.crates_delivered = 0
    runstate.crates_opened = 0
    runstate._crate_just_opened = None
    saved_crates = data.get("crates")
    if isinstance(saved_crates, dict):
        delivered = saved_crates.get("delivered")
        opened = saved_crates.get("opened")
        if (
            isinstance(delivered, int) and not isinstance(delivered, bool)
            and isinstance(opened, int) and not isinstance(opened, bool)
            and 0 <= opened <= delivered <= CRATE_MAX
        ):
            runstate.crates_delivered = delivered
            runstate.crates_opened = opened
        else:
            load_problems.append("supply crates")
    saved_balance = data.get("balance_bonuses")
    if isinstance(saved_balance, int) and not isinstance(saved_balance, bool) and 0 <= saved_balance <= 1000000:
        runstate.balance_bonuses = saved_balance
    else:
        runstate.balance_bonuses = 0
    runstate.just_balanced = False
    saved_framing = data.get("framing")
    runstate.framing = saved_framing if saved_framing in FRAMINGS else "regional"
    saved_forecast = data.get("forecast")
    if isinstance(saved_forecast, dict):
        total = saved_forecast.get("total")
        hits = saved_forecast.get("hits")
        if (
            isinstance(total, int) and not isinstance(total, bool)
            and isinstance(hits, int) and not isinstance(hits, bool)
            and 0 <= hits <= total <= 1000000
        ):
            runstate.forecast_total = total
            runstate.forecast_hits = hits
            miss = saved_forecast.get("miss")
            if _num(miss, 0, 1000000000):
                runstate.forecast_miss_total = float(miss)
    saved_log = data.get("science_log")
    if isinstance(saved_log, list):
        science_log[:] = [
            {"region": str(e.get("region", "A"))[:3], "round": int(e.get("round", 0)),
             "text": str(e.get("text", "")), **({"pinned": True} if e.get("pinned") is True else {})}
            for e in saved_log
            if isinstance(e, dict) and isinstance(e.get("round", 0), (int, float))
        ]
        # at most MAX_PINNED pins survive a load, then the usual cap (oldest unpinned first)
        seen = 0
        for entry in science_log:
            if entry.get("pinned"):
                seen += 1
                if seen > MAX_PINNED:
                    del entry["pinned"]
        _cap_science_log()
    document.getElementById("b-strategy-label-input").value = region_b.strategy_label
    document.getElementById("c-strategy-label-input").value = region_c.strategy_label
    render()
    _seed_achievement_toast_baseline()
    return True
