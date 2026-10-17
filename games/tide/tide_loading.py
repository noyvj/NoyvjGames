"""load_state(): restores a save into the live game, then redraws."""

import copy

import tide_runstate as runstate
from tide_achievements import _earned_snapshot
from tide_almanac import almanac_resync
from tide_bridge import _clamped_int, _finite_number
from tide_coastline import _resync_previous_flooded_rows
from tide_coasts import clean_coastline, heritage_sites
from tide_daily import clean_daily
from tide_flavour import CRITTERS
from tide_readouts import GOALS
from tide_renderer import render
from tide_rules import (
    ADAPTATION_TIERS, BRACE_STEP, CATEGORIES, CHECKPOINT_FORESIGHT_LIMIT, CHESS_RUNOFF_LAG, CHRONICLE_LIMIT,
    CITIZEN_SCIENCE_FACTS, COASTLINE_ROWS, CREW, CREW_MAX, DIVERSIFY_COST, DIVERSIFY_MAX_LEVEL,
    DOMINO_DISCOUNT_SEASONS, HERITAGE_LOST, HERITAGE_PROTECTED, HERITAGE_UNPROTECTED, LEDGER_KEYS,
    LEDGER_LIMIT, MARKET_KINDS, OUTPUT_MIX, POP_START, RETREAT_MAX_STEPS, SEA_SCENARIOS,
    SETTLEMENT_NAME_MAX, SNAPSHOT_LIMIT, STORM_RESULT_TIERS, WORKSHOP_DEFAULTS,
)
from tide_workshop import _autosave_info, clean_workshop_value


def _load_ledger(saved):
    """D-1: keeps only entries that carry every column as a sane number; a
    save without a ledger (or with a damaged one) loads an empty ledger."""
    if not isinstance(saved, list):
        return []
    ranges = {
        "season": (1, 10**6), "funds": (0, 1e9), "acidity": (0, 1e6), "fish_yield": (0, 1),
        "damage": (0, 1e9), "rows_dry": (0, COASTLINE_ROWS), "population": (0, 10**6),
        "tier": (0, len(ADAPTATION_TIERS) - 1), "invested": (0, 10**6),
    }
    entries = []
    for item in saved:
        if not isinstance(item, dict) or not all(_finite_number(item.get(k), *ranges[k]) for k in LEDGER_KEYS):
            continue
        entries.append(
            {
                "season": int(item["season"]), "funds": float(item["funds"]),
                "acidity": float(item["acidity"]), "fish_yield": float(item["fish_yield"]),
                "damage": float(item["damage"]), "rows_dry": int(item["rows_dry"]),
                "population": int(item["population"]), "tier": int(item["tier"]),
                "invested": int(item["invested"]),
            }
        )
    return entries[-LEDGER_LIMIT:]


def _load_snapshots(saved):
    """D-4: keeps only well-formed [season, sea_level, heritage code, retreat rows]
    entries; a save without them (or with damaged ones) simply has nothing to scrub
    back to for those seasons."""
    if not isinstance(saved, list):
        return []
    entries = []
    allowed = set("upl")
    for item in saved:
        if not (isinstance(item, list) and len(item) == 4):
            continue
        season, sea, code, retreat = item
        if (
            isinstance(season, int) and not isinstance(season, bool) and 1 <= season <= 10**6
            and _finite_number(sea, 0, 1e6)
            and isinstance(code, str) and len(code) == len(heritage_sites()) and set(code) <= allowed
            and isinstance(retreat, list) and len(retreat) <= RETREAT_MAX_STEPS
            and all(isinstance(r, int) and not isinstance(r, bool) and 0 <= r < COASTLINE_ROWS for r in retreat)
        ):
            entries.append([season, float(sea), code, list(retreat)])
    return entries[-SNAPSHOT_LIMIT:]


def _load_sister(data):
    """D3: a save without a valid 'sister' block loads with the sister off."""
    runstate.state.sister_enabled = False
    runstate.state.sister_cumulative_damage = 0.0
    runstate.state.sister_net_funds = 0.0
    saved = data.get("sister")
    if not isinstance(saved, dict):
        return
    runstate.state.sister_enabled = True
    damage = saved.get("damage")
    net = saved.get("net_funds")
    if isinstance(damage, (int, float)) and not isinstance(damage, bool) and damage == damage and 0 <= damage < 1e9:
        runstate.state.sister_cumulative_damage = float(damage)
    if isinstance(net, (int, float)) and not isinstance(net, bool) and net == net and abs(net) < 1e9:
        runstate.state.sister_net_funds = float(net)


def load_state(data):
    if not isinstance(data, dict):
        _autosave_info["load_failed"] = True  # D-11: the restore panel opens itself
        return False
    runstate.state.season = data.get("season", runstate.state.season)
    runstate.state.coastline = clean_coastline(data.get("coastline"))  # D-8: before anything reads the heritage sites or rows
    runstate.state.funds = data.get("funds", runstate.state.funds)
    saved_capacity = data.get("capacity")
    if isinstance(saved_capacity, dict):
        for category in CATEGORIES:
            if category in saved_capacity:
                runstate.state.capacity[category] = saved_capacity[category]
    runstate.state.acidity = data.get("acidity", runstate.state.acidity)
    saved_acidity_history = data.get("acidity_history")
    if isinstance(saved_acidity_history, list):
        runstate.state.acidity_history = copy.deepcopy(saved_acidity_history)
    runstate.state.sea_level = data.get("sea_level", runstate.state.sea_level)
    runstate.state.cumulative_damage = data.get("cumulative_damage", runstate.state.cumulative_damage)
    runstate.state.undampened_damage_total = data.get(
        "undampened_damage_total", runstate.state.undampened_damage_total
    )
    saved_damage_log = data.get("damage_log")
    if isinstance(saved_damage_log, list):
        runstate.state.damage_log = copy.deepcopy(saved_damage_log)
    saved_ticker_log = data.get("ticker_log")
    if isinstance(saved_ticker_log, list):
        runstate.state.ticker_log = copy.deepcopy(saved_ticker_log)
    runstate.state.trend_flattening_announced = data.get(
        "trend_flattening_announced", runstate.state.trend_flattening_announced
    )

    # Every field below predates a feature added after this game's initial
    # save-system integration -- a save from before any of them simply
    # lacks the key, so each falls back to whatever's already live (the
    # fresh-module default) rather than crashing on a missing key, same
    # discipline as every field above.
    saved_ticker_full_history = data.get("ticker_full_history")
    if isinstance(saved_ticker_full_history, list):
        runstate.state.ticker_full_history = copy.deepcopy(saved_ticker_full_history)
    runstate.state.hard_lag_mode = bool(data.get("hard_lag_mode", runstate.state.hard_lag_mode))
    _load_sister(data)
    saved_output_mix = data.get("output_mix")
    if saved_output_mix in OUTPUT_MIX:
        runstate.state.output_mix = saved_output_mix
    saved_fish_yield_history = data.get("fish_yield_history")
    if isinstance(saved_fish_yield_history, list):
        runstate.state.fish_yield_history = copy.deepcopy(saved_fish_yield_history)
    runstate.state.first_flood_announced = bool(
        data.get("first_flood_announced", runstate.state.first_flood_announced)
    )
    runstate.state.baseline_season = data.get("baseline_season", runstate.state.baseline_season)
    runstate.state.baseline_sea_level = data.get("baseline_sea_level", runstate.state.baseline_sea_level)
    runstate.state.baseline_damage = data.get("baseline_damage", runstate.state.baseline_damage)

    # Achievements' new tracked state -- belt-and-suspenders backfill
    # (same idea as SOL's visited_bodies) for a save predating these
    # fields: the restored acidity/funds/fish-yield values are themselves
    # valid lower/upper bounds on what the "ever" extremes must have been.
    runstate.state.min_fish_yield_ever = min(
        data.get("min_fish_yield_ever", runstate.state.min_fish_yield_ever),
        runstate.state.fish_yield_multiplier(),
    )
    runstate.state.max_acidity_ever = max(
        data.get("max_acidity_ever", runstate.state.max_acidity_ever), runstate.state.acidity
    )
    runstate.state.max_funds_ever = max(
        data.get("max_funds_ever", runstate.state.max_funds_ever), runstate.state.funds
    )
    saved_ranks = data.get("ranks") if isinstance(data.get("ranks"), dict) else {}  # D-10
    runstate.state.storms_weathered = _clamped_int(saved_ranks.get("storms_weathered"), 0, 10**6)
    runstate.state.storms_clean = min(runstate.state.storms_weathered, _clamped_int(saved_ranks.get("storms_clean"), 0, 10**6))
    runstate.state.early_retreats = min(RETREAT_MAX_STEPS, _clamped_int(saved_ranks.get("early_retreats"), 0, 10**6))
    runstate.state.fortified_in_time_earned = bool(
        data.get("fortified_in_time_earned", runstate.state.fortified_in_time_earned)
    )

    saved_tier_log = data.get("tier_log")
    if isinstance(saved_tier_log, list):
        runstate.state.tier_log = [
            t for t in saved_tier_log if isinstance(t, int) and 0 <= t < len(ADAPTATION_TIERS)
        ]
    runstate.state.hard_lag_note_seen = bool(data.get("hard_lag_note_seen", runstate.state.hard_lag_note_seen))
    runstate.state.fish_crash_open = bool(data.get("fish_crash_open", runstate.state.fish_crash_open))
    saved_recovery = data.get("recovery_celebrated_season", runstate.state.recovery_celebrated_season)
    runstate.state.recovery_celebrated_season = saved_recovery if isinstance(saved_recovery, int) else 0
    saved_scenario = data.get("sea_scenario")
    if saved_scenario in SEA_SCENARIOS:
        runstate.state.sea_scenario = saved_scenario

    saved_name = data.get("settlement_name")
    runstate.state.settlement_name = (
        " ".join(saved_name.split())[:SETTLEMENT_NAME_MAX] if isinstance(saved_name, str) else ""
    )
    saved_chronicle = data.get("chronicle")
    if isinstance(saved_chronicle, list):
        runstate.state.chronicle = [
            {"season": e["season"], "text": e["text"][:200]}
            for e in saved_chronicle
            if isinstance(e, dict)
            and isinstance(e.get("season"), int)
            and isinstance(e.get("text"), str)
        ][-CHRONICLE_LIMIT:]
    else:
        runstate.state.chronicle = []

    saved_heritage = data.get("heritage")
    runstate.state.heritage = {site["id"]: HERITAGE_UNPROTECTED for site in heritage_sites()}
    if isinstance(saved_heritage, dict):
        for site in heritage_sites():
            if saved_heritage.get(site["id"]) in (HERITAGE_UNPROTECTED, HERITAGE_PROTECTED, HERITAGE_LOST):
                runstate.state.heritage[site["id"]] = saved_heritage[site["id"]]
    runstate.state.monitoring_reports = _clamped_int(
        data.get("monitoring_reports"), 0, len(CITIZEN_SCIENCE_FACTS)
    )
    runstate.state.monitoring_last_season = _clamped_int(data.get("monitoring_last_season"), 0, 10**6)
    runstate.state.storm_mode = bool(data.get("storm_mode", False))
    saved_storm_log = data.get("storm_log")
    runstate.state.storm_log = (
        [
            {k: float(e[k]) if k != "season" else int(e[k]) for k in ("season", "surge", "taken", "blocked")}
            for e in saved_storm_log
            if isinstance(e, dict)
            and all(isinstance(e.get(k), (int, float)) and not isinstance(e.get(k), bool) for k in ("season", "surge", "taken", "blocked"))
        ][-20:]
        if isinstance(saved_storm_log, list)
        else []
    )

    saved_retreat = data.get("retreat_rows")
    retreat_rows = []
    if isinstance(saved_retreat, list):
        for row in saved_retreat:
            if (
                isinstance(row, int)
                and not isinstance(row, bool)
                and 0 <= row < COASTLINE_ROWS
                and row not in retreat_rows
                and len(retreat_rows) < RETREAT_MAX_STEPS
            ):
                retreat_rows.append(row)
    runstate.state.retreat_rows = retreat_rows
    runstate.state.population = _clamped_int(data.get("population"), 0, 10**5) or POP_START
    runstate.state.peak_population = max(runstate.state.population, _clamped_int(data.get("peak_population"), 0, 10**5))
    runstate.state.displaced_total = _clamped_int(data.get("displaced_total"), 0, 10**7)
    runstate.state.relocated_total = _clamped_int(data.get("relocated_total"), 0, 10**7)
    saved_diversification = data.get("diversification")
    runstate.state.diversification = {
        kind: _clamped_int(
            saved_diversification.get(kind) if isinstance(saved_diversification, dict) else 0,
            0,
            DIVERSIFY_MAX_LEVEL,
        )
        for kind in DIVERSIFY_COST
    }
    saved_checkpoint = data.get("checkpoint")
    runstate.state.checkpoint = (
        copy.deepcopy(saved_checkpoint)
        if isinstance(saved_checkpoint, dict)
        and isinstance(saved_checkpoint.get("season"), int)
        and not isinstance(saved_checkpoint.get("season"), bool)
        and saved_checkpoint["season"] >= 1
        else None
    )
    saved_foresight = data.get("foresight")
    runstate.state.foresight = (
        [
            {
                "season": e["season"],
                "fish_yield": float(e["fish_yield"]),
                "damage": float(e["damage"]),
                "flooded": e["flooded"],
            }
            for e in saved_foresight
            if isinstance(e, dict)
            and isinstance(e.get("season"), int)
            and isinstance(e.get("flooded"), int)
            and all(isinstance(e.get(k), (int, float)) for k in ("fish_yield", "damage"))
        ][:CHECKPOINT_FORESIGHT_LIMIT]
        if isinstance(saved_foresight, list)
        else []
    )
    runstate.state.replay_count = _clamped_int(data.get("replay_count"), 0, 10**4)
    runstate.state.season_ledger = _load_ledger(data.get("season_ledger"))
    runstate.state.season_snapshots = _load_snapshots(data.get("season_snapshots"))
    saved_run = data.get("run_stats")  # GD-20/23/24: bad or missing values fall back to a fresh run's defaults
    runstate.state.rewind_used, runstate.state.hard_lag_all_run, runstate.state.ironman_earned = False, True, False
    runstate.state.actions_count, runstate.state.active_seconds, runstate.state.maxtier_actions, runstate.state.maxtier_seconds = 0, 0.0, None, None
    if isinstance(saved_run, dict):
        runstate.state.rewind_used = saved_run.get("rewind_used") is True
        runstate.state.hard_lag_all_run = saved_run.get("hard_lag_all_run") is not False
        runstate.state.ironman_earned = saved_run.get("ironman") is True
        runstate.state.actions_count = _clamped_int(saved_run.get("actions"), 0, 10**6)
        seconds = saved_run.get("seconds")
        runstate.state.active_seconds = float(seconds) if isinstance(seconds, (int, float)) and not isinstance(seconds, bool) and 0 <= seconds < 1e8 else 0.0
        mt_a, mt_s = saved_run.get("maxtier_actions"), saved_run.get("maxtier_seconds")
        if isinstance(mt_a, int) and not isinstance(mt_a, bool) and 0 <= mt_a < 10**6 and isinstance(mt_s, (int, float)) and not isinstance(mt_s, bool) and 0 <= mt_s < 1e8:
            runstate.state.maxtier_actions, runstate.state.maxtier_seconds = mt_a, float(mt_s)
    saved_workshop = data.get("workshop")  # D-5: bad values fall back to the standard dial
    source = saved_workshop if isinstance(saved_workshop, dict) else {}
    runstate.state.workshop = {k: clean_workshop_value(k, source.get(k, WORKSHOP_DEFAULTS[k])) for k in WORKSHOP_DEFAULTS}
    saved_boss = data.get("acid_boss")  # GD-12
    runstate.state.acid_boss_mode, runstate.state.acid_braced, runstate.state.acid_boss_result = False, False, ""
    if isinstance(saved_boss, dict):
        runstate.state.acid_boss_mode = saved_boss.get("mode") is True
        runstate.state.acid_braced = saved_boss.get("braced") is True
        runstate.state.acid_boss_result = saved_boss.get("result") if saved_boss.get("result") in ("survived", "hit") else ""
    saved_brace = data.get("brace")  # GD-3: bad amounts are dropped
    runstate.state.brace = {"barriers": 0, "stockpile": 0, "evacuate": False}
    if isinstance(saved_brace, dict):
        for kind in ("barriers", "stockpile"):
            amount = saved_brace.get(kind)
            if isinstance(amount, int) and not isinstance(amount, bool) and 0 <= amount <= 10**5 and amount % BRACE_STEP == 0:
                runstate.state.brace[kind] = amount
        runstate.state.brace["evacuate"] = saved_brace.get("evacuate") is True
    result = data.get("storm_result")
    runstate.state.last_storm_result = result if result in [label for _l, label in STORM_RESULT_TIERS] else ""
    saved_chess = data.get("chess")  # GD-4: bad values leave Tidal Chess off
    runstate.state.chess_mode, runstate.state.runoff_queue, runstate.state.chess_dips = False, [], 0
    if isinstance(saved_chess, dict) and saved_chess.get("on") is True:
        runstate.state.chess_mode = True
        queue = saved_chess.get("runoff")
        if isinstance(queue, list):
            runstate.state.runoff_queue = [float(x) for x in queue[:CHESS_RUNOFF_LAG + 1]
                                  if isinstance(x, (int, float)) and not isinstance(x, bool) and 0 <= x < 10**6]
        runstate.state.chess_dips = _clamped_int(saved_chess.get("dips"), 0, 10**4)
    saved_crew = data.get("crew")  # GD-11: unknown ids, repeats and anything past the cap are dropped
    runstate.state.crew = []
    if isinstance(saved_crew, list):
        for item in saved_crew:
            if item in CREW and item not in runstate.state.crew and len(runstate.state.crew) < CREW_MAX:
                runstate.state.crew.append(item)
    saved_market = data.get("market")  # GD-8: bad values leave no deal, no dip
    runstate.state.market_event, runstate.state.market_accepted, runstate.state.income_dip_seasons = None, 0, 0
    if isinstance(saved_market, dict):
        runstate.state.market_accepted = _clamped_int(saved_market.get("accepted"), 0, 10**4)
        runstate.state.income_dip_seasons = _clamped_int(saved_market.get("dip"), 0, 2)
        event = saved_market.get("event")
        if (isinstance(event, dict) and event.get("kind") in MARKET_KINDS
                and isinstance(event.get("gain"), (int, float)) and not isinstance(event.get("gain"), bool) and 0 <= event["gain"] < 10**5
                and isinstance(event.get("season"), int) and not isinstance(event.get("season"), bool)):
            runstate.state.market_event = {"kind": event["kind"], "gain": float(event["gain"]), "season": event["season"]}
    saved_sightings = data.get("sightings")  # GD-18: unknown ids and duplicates are dropped
    runstate.state.sightings = []
    if isinstance(saved_sightings, list):
        for item in saved_sightings:
            if item in CRITTERS and item not in runstate.state.sightings:
                runstate.state.sightings.append(item)
    saved_balance = data.get("balance")  # GD-14
    runstate.state.balance_streak, runstate.state.season_invested = 0, set()
    if isinstance(saved_balance, dict):
        runstate.state.balance_streak = _clamped_int(saved_balance.get("streak"), 0, 10**4)
        invested = saved_balance.get("invested")
        if isinstance(invested, list):
            runstate.state.season_invested = {c for c in invested if c in CATEGORIES}
    saved_domino = data.get("domino")  # GD-28
    runstate.state.domino_seasons_left, runstate.state.domino_count = 0, 0
    if isinstance(saved_domino, dict):
        runstate.state.domino_seasons_left = _clamped_int(saved_domino.get("left"), 0, DOMINO_DISCOUNT_SEASONS)
        runstate.state.domino_count = _clamped_int(saved_domino.get("count"), 0, 10**4)
    saved_goal = data.get("pinned_goal")  # GD-19: an unknown goal id or a bad shape just means no pinned goal
    runstate.state.pinned_goal, runstate.state.pinned_goal_reached = "", False
    if isinstance(saved_goal, dict) and saved_goal.get("id") in GOALS:
        runstate.state.pinned_goal = saved_goal["id"]
        runstate.state.pinned_goal_reached = saved_goal.get("reached") is True

    runstate.state.daily = clean_daily(data.get("daily"))  # GD-5
    saved_buys = data.get("buys")  # D-3: bad shapes are dropped, which only means this run cannot be shared as a code
    runstate.state.season_buys, runstate.state.buys_now = [], [0, 0, 0]
    if isinstance(saved_buys, dict):
        log, now = saved_buys.get("log"), saved_buys.get("now")
        if isinstance(log, list):
            runstate.state.season_buys = [
                [_clamped_int(n, 0, 10**4) for n in row] for row in log[-LEDGER_LIMIT:]
                if isinstance(row, list) and len(row) == 3
            ]
        if isinstance(now, list) and len(now) == 3:
            runstate.state.buys_now = [_clamped_int(n, 0, 10**4) for n in now]

    # D8's flash-tracking global and the achievements toast-diffing
    # baseline both need to resync to the just-loaded state before
    # render() below draws anything or checks for newly-earned
    # achievements -- otherwise a loaded save could flash every already-
    # flooded row, or toast every already-earned achievement, as if they
    # had all just happened this instant.
    _resync_previous_flooded_rows()
    almanac_resync()
    runstate._previously_earned_ids = _earned_snapshot()

    render()
    return True
