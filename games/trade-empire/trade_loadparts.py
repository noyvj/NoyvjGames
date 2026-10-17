"""The per-feature loaders that read a save back (guild, career, charter, blackout, expedition, Meridian, Cartel, hub, blueprints, exchange, weather, captains, records, ghost)."""

import ghost as ghost_lib

import trade_runstate as runstate
from trade_blackout import BLACKOUT_INTEL, blackout_bought
from trade_blueprints import (
    BLUEPRINT_MAX_DESIGNS, BLUEPRINT_STAT_KEYS, _hull_ok, blueprints, reset_blueprint_draft,
)
from trade_captains import CAPTAINS, CAPTAIN_SWAPS_PER_CHARTER
from trade_cartel import CARTEL_BACKLASH_WINDOW, CARTEL_SLUMP_TICKS, CARTEL_SPIKE_TICKS, cartel_last
from trade_chain_logic import _chain_clean_best
from trade_charter import (
    CAREER_MAX_ENTRIES, CHARTER_COUNT_MAX, CHARTER_PERKS, CHARTER_POINTS_PER_RENEWAL, FOUNDING_SEED_MAX,
    LEDGER_MAX, charter_points_spent, guild_first_offer_ticks,
)
from trade_colony import active_colony_ids, colony_producing
from trade_crises import CRISES, CRISIS_MEDAL_RANK
from trade_effects import cartel_effects, guild_contract
from trade_exchange import (
    EXCHANGE_BOOK_ROWS, EXCHANGE_MAX_SLOTS, EXCHANGE_PERCENTS, exchange_fills, exchange_open,
    exchange_orders,
)
from trade_expedition import CURIO_IDS, EXPEDITION_TICKS
from trade_ghost import (
    GHOST_MIN_TICKS, GHOST_MODES, GHOST_STRIDE_MAX, _ghost_rec, _ghost_reset_live, _ghost_state, ghost_best,
)
from trade_guild import GUILD_DEADLINE_TICKS, GUILD_UNITS_MAX, GUILD_UNITS_MIN, _guild_clear
from trade_market import STOCKPILE_CAPACITY
from trade_meridian import MERIDIAN_CONTEST_TICKS, MERIDIAN_SHIELD_TICKS
from trade_records import RECORDS_COUNT_MAX, _fresh_records, _saved_int, records
from trade_rules import ALL_COLONIES, SELL_PRICE
from trade_ships import ships, trade_posts
from trade_weather import WEATHER_DURATION, WEATHER_GAP, WEATHER_HEADLINES


def _load_records(raw):
    """Restore the lifetime records from an untrusted save value (defaults for anything malformed)."""
    loaded = _fresh_records()
    if isinstance(raw, dict):
        for key in loaded:
            if key not in ("curios", "crisis_best", "chain_best"):
                loaded[key] = _saved_int(raw.get(key), 0, RECORDS_COUNT_MAX)
        best = raw.get("crisis_best")
        if isinstance(best, dict):
            for crisis_id, item in best.items():
                if not isinstance(crisis_id, str) or crisis_id not in CRISES or not isinstance(item, dict):
                    continue
                ticks = _saved_int(item.get("ticks"), 1, 1_000_000, 0)
                if isinstance(item.get("medal"), str) and item["medal"] in CRISIS_MEDAL_RANK and ticks:
                    loaded["crisis_best"][crisis_id] = {"medal": item["medal"], "ticks": ticks}
        chain = raw.get("chain_best")  # J-5: kept entry by entry, an impossible score is dropped
        if isinstance(chain, dict):
            for puzzle_id, item in chain.items():
                entry = _chain_clean_best(puzzle_id, item)
                if entry is not None:
                    loaded["chain_best"][puzzle_id] = entry
        curios = raw.get("curios")
        if isinstance(curios, list):
            known = [c for c in curios if isinstance(c, str) and c in CURIO_IDS]
            loaded["curios"] = list(dict.fromkeys(known))
    records.clear()
    records.update(loaded)


def _load_ghost(raw):
    """Restore the ghost from an untrusted save value: anything unreadable is dropped (no ghost, nothing breaks)."""
    ghost_best.clear()
    _ghost_reset_live()
    if not isinstance(raw, dict):
        return
    best = raw.get("best")
    if isinstance(best, dict):
        for mode in GHOST_MODES:
            item = best.get(mode)
            if not isinstance(item, dict):
                continue
            trace = ghost_lib.load(item.get("trace"))
            ticks = _saved_int(item.get("ticks"), GHOST_MIN_TICKS, ghost_lib.MAX_TURNS, 0)
            if trace is not None and ticks and trace["turns"] == ticks:
                ghost_best[mode] = {"ticks": ticks, "trace": trace}
    live = raw.get("live")
    if not isinstance(live, dict):
        return
    if live.get("tainted") is True:
        _ghost_state["tainted"] = True
        return
    turns = _saved_int(live.get("turns"), 1, ghost_lib.MAX_TURNS, 0)
    stride = _saved_int(live.get("stride"), 1, GHOST_STRIDE_MAX, 0)
    values = live.get("values")
    if not (turns and stride and stride & (stride - 1) == 0 and isinstance(values, list)):
        return
    clean = [ghost_lib.clean_number(v) for v in values[:ghost_lib.MAX_LEN]]
    if len(values) >= ghost_lib.MAX_LEN or None in clean or len(clean) != -(-turns // stride):
        return                              # a recording the recorder could not have made
    endgame = _saved_int(live.get("endgame"), 1, turns, 0) or None
    if endgame is not None and endgame != turns:
        return                              # recording stops the moment the endgame is reached
    _ghost_rec.values, _ghost_rec.turns, _ghost_rec.stride, _ghost_rec._last = clean, turns, stride, clean[-1]
    _ghost_state["endgame"] = endgame


def _load_guild(raw):
    """Restore the guild from an untrusted save value; anything malformed or
    referring to a colony that isn't reachable falls back to 'none'."""
    _guild_clear(guild_first_offer_ticks())
    runstate.guild_completed = runstate.guild_failed = runstate.guild_offers = 0
    if not isinstance(raw, dict):
        return

    def as_int(value, low, high):
        return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else None

    runstate.guild_completed = as_int(raw.get("completed"), 0, 10_000_000) or 0
    runstate.guild_failed = as_int(raw.get("failed"), 0, 10_000_000) or 0
    runstate.guild_offers = as_int(raw.get("offers"), 0, 10_000_000) or 0
    state_name = raw.get("state")
    if state_name not in ("offered", "active"):
        return
    good, destination = raw.get("good"), raw.get("destination")
    units = as_int(raw.get("units"), GUILD_UNITS_MIN, GUILD_UNITS_MAX)
    delivered = as_int(raw.get("delivered"), 0, GUILD_UNITS_MAX)
    ticks_left = as_int(raw.get("ticks_left"), 1, GUILD_DEADLINE_TICKS)
    reward = as_int(raw.get("reward"), 0, 10_000_000)
    valid = (
        destination in ALL_COLONIES
        and destination in active_colony_ids()
        and good == ALL_COLONIES[destination]["needs"]
        and None not in (units, delivered, ticks_left, reward)
        and delivered <= units
    )
    if not valid:
        return
    runstate.guild_state = state_name
    guild_contract.update({
        "good": good, "destination": destination, "units": units,
        "delivered": delivered, "ticks_left": ticks_left, "reward": reward,
    })


def _load_career(raw, charters_done):
    """J-14 -- the career log from an untrusted save: only whole entries with
    sane numbers survive, never more than the charters actually completed."""
    if not isinstance(raw, list) or charters_done <= 0:
        return []
    entries = []
    for item in raw[:CAREER_MAX_ENTRIES * 2]:
        if not isinstance(item, dict):
            continue
        n = _saved_int(item.get("n"), 1, CHARTER_COUNT_MAX, 0)
        units = _saved_int(item.get("units"), 0, LEDGER_MAX, -1)
        routes = _saved_int(item.get("routes"), 0, 10_000, -1)
        peak = _saved_int(item.get("peak"), 0, LEDGER_MAX, -1)
        perks = _saved_int(item.get("perks"), 0, len(CHARTER_PERKS), -1)
        if n == 0 or -1 in (units, routes, peak, perks) or not isinstance(item.get("hard"), bool):
            continue
        entry = {"n": n, "hard": item["hard"], "units": units, "routes": routes, "peak": peak, "perks": perks}
        if item.get("dark") is True:
            entry["dark"] = True
        entries.append(entry)
    return entries[-min(CAREER_MAX_ENTRIES, charters_done):]


def _load_charter(charter_raw, ledger_raw):
    """Restore the charter tree, founding seed, hard-charter flags and the
    lifetime ledger from untrusted save values. Anything missing or malformed
    falls back to its default; a save from before O-1 that carries a J21
    legacy level is migrated as that many completed charters."""
    runstate.charters_completed = runstate.charter_points_earned = runstate.founding_seed = 0
    runstate.charter_perks = set()
    runstate.hard_charter_active = runstate.hard_charter_next = False
    runstate.ledger_units_moved = runstate.ledger_routes_established = runstate.ledger_hard_completed = 0
    runstate.ledger_routes_seen = set()
    runstate.ledger_charter_units = 0
    runstate.charter_career = []

    if isinstance(charter_raw, dict):
        runstate.charters_completed = _saved_int(charter_raw.get("completed"), 0, CHARTER_COUNT_MAX)
        runstate.charter_points_earned = _saved_int(charter_raw.get("points"), 0, CHARTER_COUNT_MAX * 10)
        runstate.founding_seed = _saved_int(charter_raw.get("seed"), 0, FOUNDING_SEED_MAX)
        raw_perks = charter_raw.get("perks")
        if isinstance(raw_perks, list):
            # Known string ids only (type-checked before the membership test so
            # an unhashable or non-string entry can't crash it), then drop any
            # perk whose prerequisites aren't also present.
            wanted = {p for p in raw_perks if isinstance(p, str) and p in CHARTER_PERKS}
            changed = True
            while changed:
                changed = False
                for perk_id in sorted(wanted):
                    if any(r not in wanted for r in CHARTER_PERKS[perk_id]["requires"]):
                        wanted.discard(perk_id)
                        changed = True
            runstate.charter_perks = wanted
            if charter_points_spent() > runstate.charter_points_earned:
                runstate.charter_perks = set()  # a save can't own more than it earned
        runstate.hard_charter_active = charter_raw.get("hard") is True and runstate.charters_completed >= 1
        runstate.hard_charter_next = charter_raw.get("hard_next") is True
        runstate.charter_career = _load_career(charter_raw.get("career"), runstate.charters_completed)
    elif runstate.legacy_level > 0:
        runstate.charters_completed = runstate.legacy_level
        runstate.charter_points_earned = CHARTER_POINTS_PER_RENEWAL * runstate.legacy_level
    if runstate.charters_completed == 0:
        runstate.founding_seed = 0

    if isinstance(ledger_raw, dict):
        runstate.ledger_units_moved = _saved_int(ledger_raw.get("units"), 0, LEDGER_MAX)
        runstate.ledger_routes_established = _saved_int(ledger_raw.get("routes"), 0, LEDGER_MAX)
        runstate.ledger_hard_completed = _saved_int(ledger_raw.get("hard_completed"), 0, CHARTER_COUNT_MAX)
        runstate.ledger_charter_units = min(runstate.ledger_units_moved, _saved_int(ledger_raw.get("charter_units"), 0, LEDGER_MAX))
        seen_raw = ledger_raw.get("routes_seen")
        if isinstance(seen_raw, list):
            for pair in seen_raw[:100]:
                if (
                    isinstance(pair, list) and len(pair) == 2
                    and all(isinstance(c, str) and c in ALL_COLONIES for c in pair)
                    and pair[0] != pair[1]
                ):
                    runstate.ledger_routes_seen.add(frozenset(pair))


def _load_blackout(raw):
    """J-29 -- restore Blackout from an untrusted save value (off unless it says a real True)."""
    runstate.blackout_enabled = runstate.blackout_clean = runstate.blackout_done = False
    blackout_bought.clear()
    if not isinstance(raw, dict):
        return
    runstate.blackout_enabled = raw.get("enabled") is True
    runstate.blackout_clean = runstate.blackout_enabled and raw.get("clean") is True
    runstate.blackout_done = raw.get("done") is True
    bought = raw.get("bought")
    if isinstance(bought, list):
        blackout_bought.update(kind for kind in bought if isinstance(kind, str) and kind in BLACKOUT_INTEL)


def _load_expedition(raw):
    """J-23 -- an expedition under way, from an untrusted save: only for a real, docked, empty, unautomated ship."""
    runstate.expedition, runstate.expedition_log = None, ""
    if not isinstance(raw, dict):
        return
    ship_id, left = raw.get("ship"), _saved_int(raw.get("left"), 1, EXPEDITION_TICKS, 0)
    ship = ships.get(ship_id) if isinstance(ship_id, str) else None
    if ship is None or not left or not ship.purchased or ship.location is None or ship.loaded:
        return
    runstate.expedition = {"ship": ship_id, "left": left}


def _load_timed_good(raw, longest):
    """{"good", "left"} from an untrusted save value, or None."""
    if not isinstance(raw, dict):
        return None
    good, left = raw.get("good"), _saved_int(raw.get("left"), 1, longest, 0)
    if not isinstance(good, str) or good not in SELL_PRICE or colony_producing(good) not in active_colony_ids() or not left:
        return None
    return {"good": good, "left": left}


def _load_meridian(raw):
    """J-11 -- the rival firm's clock, contest and shield from an untrusted save value."""
    runstate.meridian_enabled, runstate.meridian_ticks, runstate.meridian_contest, runstate.meridian_shield = False, 0, None, None
    runstate.meridian_units, runstate.meridian_intel_bought = 0, False
    if not isinstance(raw, dict):
        return
    runstate.meridian_enabled = raw.get("enabled") is True
    runstate.meridian_ticks = _saved_int(raw.get("ticks"), 0, 100_000_000)
    runstate.meridian_units = _saved_int(raw.get("units"), 0, 100_000)
    runstate.meridian_intel_bought = raw.get("intel") is True
    runstate.meridian_contest = _load_timed_good(raw.get("contest"), MERIDIAN_CONTEST_TICKS)
    runstate.meridian_shield = _load_timed_good(raw.get("shield"), MERIDIAN_SHIELD_TICKS)


def _load_cartel(raw):
    """J-3 -- active cartel effects and backlash windows from an untrusted save value."""
    cartel_effects.clear()
    cartel_last.clear()
    if not isinstance(raw, dict):
        return
    effects, last = raw.get("effects"), raw.get("last")
    if isinstance(effects, dict):
        for good, effect in effects.items():
            if not isinstance(good, str) or good not in SELL_PRICE or colony_producing(good) not in active_colony_ids():
                continue
            if not isinstance(effect, dict) or effect.get("kind") not in ("spike", "slump"):
                continue
            longest = CARTEL_SPIKE_TICKS if effect["kind"] == "spike" else CARTEL_SLUMP_TICKS
            left = _saved_int(effect.get("left"), 1, longest, 0)
            if left:
                cartel_effects[good] = {"kind": effect["kind"], "left": left}
    if isinstance(last, dict):
        for good, age in last.items():
            if isinstance(good, str) and good in SELL_PRICE and _saved_int(age, 0, CARTEL_BACKLASH_WINDOW - 1, -1) >= 0:
                cartel_last[good] = age


def _load_hub(raw):
    """J-21 -- the Distribution Hub from an untrusted save value: a reachable colony id, else none."""
    runstate.hub_colony = raw if isinstance(raw, str) and raw in active_colony_ids() else None


def _load_blueprints(raw):
    """J-19 -- the saved hull designs from an untrusted save value (only valid ones, at most four)."""
    blueprints.clear()
    reset_blueprint_draft()
    if not isinstance(raw, list):
        return
    for item in raw[:BLUEPRINT_MAX_DESIGNS * 2]:
        if _hull_ok(item) and len(blueprints) < BLUEPRINT_MAX_DESIGNS:
            blueprints.append({k: item[k] for k in (*BLUEPRINT_STAT_KEYS, "name")})
            blueprints[-1]["name"] = blueprints[-1]["name"].strip()


def _load_exchange(raw):
    """J-27 -- standing orders and the order book from an untrusted save value (only valid, in-range entries)."""
    exchange_orders.clear()
    exchange_fills.clear()
    if not isinstance(raw, dict) or not exchange_open():
        return
    orders = raw.get("orders")
    if isinstance(orders, list):
        for item in orders[:EXCHANGE_MAX_SLOTS * 2]:
            if not isinstance(item, dict):
                continue
            kind, good, pct = item.get("kind"), item.get("good"), item.get("pct")
            if (
                kind in ("buy", "sell") and isinstance(good, str) and good in SELL_PRICE
                and colony_producing(good) in active_colony_ids()
                and isinstance(pct, int) and not isinstance(pct, bool) and pct in EXCHANGE_PERCENTS
                and not any(o["kind"] == kind and o["good"] == good for o in exchange_orders)
                and len(exchange_orders) < min(EXCHANGE_MAX_SLOTS, 1 + len(trade_posts))
            ):
                exchange_orders.append({"kind": kind, "good": good, "pct": pct})
    fills = raw.get("fills")
    if isinstance(fills, list):
        for item in fills[-EXCHANGE_BOOK_ROWS:]:
            if not isinstance(item, dict):
                continue
            kind, good = item.get("kind"), item.get("good")
            qty = _saved_int(item.get("qty"), 1, STOCKPILE_CAPACITY, 0)
            price = _saved_int(item.get("price"), 0, 1_000_000, -1)
            if kind in ("buy", "sell") and isinstance(good, str) and good in SELL_PRICE and qty and price >= 0:
                exchange_fills.append({"kind": kind, "good": good, "qty": qty, "price": price})


def _load_weather(raw):
    """J-17 -- restore Market Weather from an untrusted save value; a bad event is dropped (a new one is rolled)."""
    runstate.weather_enabled, runstate.weather_n, runstate.weather_event = False, 0, None
    if not isinstance(raw, dict):
        return
    runstate.weather_enabled = raw.get("enabled") is True
    runstate.weather_n = _saved_int(raw.get("n"), 0, RECORDS_COUNT_MAX)
    ev = raw.get("event")
    if not isinstance(ev, dict):
        return
    good, kind, style = ev.get("good"), ev.get("kind"), ev.get("style")
    wait = _saved_int(ev.get("wait"), 0, WEATHER_GAP[1], -1)
    dur = _saved_int(ev.get("dur"), WEATHER_DURATION[0], WEATHER_DURATION[1], -1)
    left = _saved_int(ev.get("left"), 0, WEATHER_DURATION[1], -1)
    if (
        not isinstance(good, str) or good not in SELL_PRICE or colony_producing(good) not in active_colony_ids()
        or kind not in WEATHER_HEADLINES or style not in (0, 1) or isinstance(style, bool)
        or -1 in (wait, dur, left) or left > dur or left == 0
    ):
        return
    runstate.weather_event = {"good": good, "kind": kind, "style": style, "wait": wait, "left": left, "dur": dur}


def _load_captains(raw):
    """J-7 -- restore fleet captains from an untrusted save. Runs after the
    ships are loaded: a captain only stays on a purchased ship that has earned
    a seat, one captain per ship and one ship per captain."""
    runstate.captain_earned = set()
    runstate.captain_assignments = {perk_id: 0 for perk_id in CAPTAINS}
    runstate.captains_met = set()
    if isinstance(raw, dict):
        earned_raw = raw.get("earned")
        if isinstance(earned_raw, list):
            runstate.captain_earned = {s_id for s_id in earned_raw if isinstance(s_id, str) and s_id in ships}
        assign_raw = raw.get("assignments")
        if isinstance(assign_raw, dict):
            for perk_id in CAPTAINS:
                runstate.captain_assignments[perk_id] = _saved_int(assign_raw.get(perk_id), 0, 1 + CAPTAIN_SWAPS_PER_CHARTER)
        met_raw = raw.get("met")
        if isinstance(met_raw, list):
            runstate.captains_met = {p for p in met_raw if isinstance(p, str) and p in CAPTAINS}
    seen = set()
    for ship in ships.values():
        valid = (
            ship.captain in CAPTAINS and ship.captain not in seen
            and ship.purchased and ship.id in runstate.captain_earned
        )
        if valid:
            seen.add(ship.captain)
            runstate.captain_assignments[ship.captain] = max(runstate.captain_assignments[ship.captain], 1)
            runstate.captains_met.add(ship.captain)
        else:
            ship.captain = None
            ship.captain_deliveries = 0
