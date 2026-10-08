"""Continuum -- K-7: neighbouring settlements (computer-controlled).

Three invented neighbours share a small region with yours. Each has its own era, its own
needs and its own temper. You can **trade** with them (give what they need, take what they
offer), **share a discovery** for knowledge in return, and **bid for the Salt Flats**, a
contested site whose lease pays its holder every season. They never attack and never take
anything from you: the competition is a bidding contest, the cooperation is trade.

**All three are computer-controlled.** The owner approved neighbours as computer-controlled
only. Nothing here talks to a server and there is no real player on the other side.

**The slot interface.** The region is a list of *slots*. A slot has an id (`n1`..`n3`), a
`controller` and a `view()` of its public state (name, era, population, what it needs and
offers, its attitude toward you, its place on the map). Everything a controller can do is one
of three *intents* (`bid`, plus the player-initiated `trade` and `share`) applied through
`apply_trade`, `apply_share` and the auction in `resolve_auction`. The only controller that
exists is `"ai"` (`ai_bid`, below, in the `CONTROLLERS` registry). A later multiplayer mode
would add a `"player"` controller that supplies the same intents for the same slot; nothing
else in this file would need to change.

**No hidden randomness and nothing stored that can be derived.** A neighbour's era,
population, need and offer are pure functions of the saved seed, the slot and the season, so
the same save always shows the same neighbours. Only what *you* did is saved:
`ui["neighbours"]` = {seed, per-slot attitude and cool-downs and shared discoveries, the
lease, a short event log}. Every read is validated.

Interactions give or take ordinary resources and nothing else; they are switched off during a
Look Back and while a challenge run or consulting case is the active run (comparable runs).
"""

import math

import sim

KEY = "neighbours"
SLOT_IDS = ("n1", "n2", "n3")
MAX_EVENTS = 10
MAX_SEED = 2**31 - 1
ATTITUDE_MIN, ATTITUDE_MAX = -3, 5
ATTITUDE_WORDS = {-3: "hostile", -2: "cold", -1: "wary", 0: "neutral", 1: "warm", 2: "friendly", 3: "friendly", 4: "close", 5: "allied"}
TRADE_COOLDOWN = 3
SHARE_COOLDOWN = 4
SHARE_RETURN = 0.3   # knowledge returned, as a fraction of the shared discovery's cost
RESOURCES = ("food", "materials", "knowledge")

SITE_NAME = "the Salt Flats"
AUCTION_FIRST = 8
AUCTION_PERIOD = 10
LEASE_LENGTH = 10
LEASE_INCOME_BASE = 2
BID_CHOICES = (("modest", 0), ("firm", 3), ("lavish", 7))

NAMES = ("Brackenfold", "Saltmere", "Highwick", "Dunmarrow", "Thornreach", "Emberholt", "Wrenmouth", "Calderfen")
# Where the settlements sit on the 360x220 map.
PLAYER_POS = (58, 112)
SLOT_POS = {"n1": (214, 44), "n2": (308, 128), "n3": (196, 188)}
SITE_POS = (170, 112)
# Each neighbour's own tempo: (offset in seasons, seasons per era).
SLOT_TEMPO = {"n1": (15, 55), "n2": (0, 70), "n3": (40, 90)}


def _hash(*parts):
    value = 2166136261
    for part in parts:
        for ch in str(part):
            value = ((value ^ ord(ch)) * 16777619) & 0xFFFFFFFF
        value = ((value ^ 0x9E3779B9) * 16777619) & 0xFFFFFFFF
    return value


def _int(value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return low
    if isinstance(value, float) and not math.isfinite(value):
        return low
    return min(max(int(value), low), high)


# --- saved record ----------------------------------------------------------------------------
def default():
    return {
        "seed": 0,
        "slots": {sid: {"attitude": 0, "next_trade": 0, "next_share": 0, "shared": [], "trades": 0} for sid in SLOT_IDS},
        "lease": {"holder": "none", "until": 0, "pending": 0, "auctions": 0},
        "events": [],
    }


def clean(raw):
    out = default()
    if not isinstance(raw, dict):
        return out
    out["seed"] = _int(raw.get("seed"), 0, MAX_SEED)
    slots = raw.get("slots")
    for sid in SLOT_IDS:
        item = slots.get(sid) if isinstance(slots, dict) else None
        if not isinstance(item, dict):
            continue
        slot = out["slots"][sid]
        attitude = item.get("attitude")
        if isinstance(attitude, (int, float)) and not isinstance(attitude, bool) and math.isfinite(attitude):
            slot["attitude"] = max(ATTITUDE_MIN, min(ATTITUDE_MAX, int(attitude)))
        slot["next_trade"] = _int(item.get("next_trade"), 0, 10**7)
        slot["next_share"] = _int(item.get("next_share"), 0, 10**7)
        slot["trades"] = _int(item.get("trades"), 0, 10**6)
        shared = item.get("shared")
        names = []
        for node_id in shared if isinstance(shared, list) else []:
            if isinstance(node_id, str) and 0 < len(node_id) <= 60 and node_id not in names:
                names.append(node_id)
        slot["shared"] = names[-400:]
    lease = raw.get("lease")
    if isinstance(lease, dict):
        holder = lease.get("holder")
        out["lease"]["holder"] = holder if holder in ("none", "you") + SLOT_IDS else "none"
        out["lease"]["until"] = _int(lease.get("until"), 0, 10**7)
        out["lease"]["pending"] = _int(lease.get("pending"), 0, 10**5)
        out["lease"]["auctions"] = _int(lease.get("auctions"), 0, 10**5)
    events = raw.get("events")
    for item in events if isinstance(events, list) else []:
        if isinstance(item, dict) and isinstance(item.get("text"), str) and item["text"].strip():
            season = item.get("season")
            if not isinstance(season, bool) and isinstance(season, int) and season >= 1:
                out["events"].append({"season": min(season, 10**7), "text": item["text"].strip()[:200]})
    out["events"] = out["events"][-MAX_EVENTS:]
    return out


def get(ui):
    return clean(ui.get(KEY)) if isinstance(ui, dict) else default()


def put(ui, record):
    record = clean(record)
    if record == default():
        ui.pop(KEY, None)
    else:
        ui[KEY] = record
    return record


def ensure(ui, seed_hint=1):
    """The record with a seed (assigned, and stored, the first time)."""
    record = get(ui)
    if not record["seed"]:
        record["seed"] = _int(seed_hint, 1, MAX_SEED) or 1
        put(ui, record)
    return record


# --- the slots (pure views) ----------------------------------------------------------------
def slot_name(seed, sid):
    """Distinct invented names: slots take the three lowest hashes."""
    ranked = sorted(NAMES, key=lambda name: _hash(seed, name))
    return ranked[SLOT_IDS.index(sid)]


def neighbour_era(seed, sid, season):
    offset, pace = SLOT_TEMPO[sid]
    return min(len(sim.ERA_ORDER) - 1, (max(1, season) + offset) // pace)


def view(record, sid, season, player_era_index):
    """The public view of one slot at `season`. Pure: derived from the saved seed and the season."""
    seed = record["seed"] or 1
    slot = record["slots"][sid]
    era_index = neighbour_era(seed, sid, season)
    offset, pace = SLOT_TEMPO[sid]
    need = RESOURCES[_hash(seed, sid, (max(1, season) + offset) // 12, "need") % 3]
    others = [r for r in RESOURCES if r != need]
    offer = others[_hash(seed, sid, (max(1, season) + offset) // 12, "offer") % 2]
    rate = trade_rate(slot["attitude"])
    batch = batch_size(player_era_index)
    return {
        "id": sid,
        "controller": "ai",
        "name": slot_name(seed, sid),
        "era": sim.ERA_ORDER[era_index],
        "era_label": sim.ERA_LABEL[sim.ERA_ORDER[era_index]],
        "era_index": era_index,
        "population": 6 + era_index * 8 + ((max(1, season) + offset) % pace) // 8,
        "need": need,
        "offer": offer,
        "attitude": slot["attitude"],
        "attitude_word": ATTITUDE_WORDS[slot["attitude"]],
        "give": batch,
        "get": max(1, int(round(batch * rate))),
        "x": SLOT_POS[sid][0],
        "y": SLOT_POS[sid][1],
        "trade_ready_in": max(0, slot["next_trade"] - season),
        "share_ready_in": max(0, slot["next_share"] - season),
    }


def views(ui, season, player_era_index):
    record = get(ui)
    return [view(record, sid, season, player_era_index) for sid in SLOT_IDS]


def trade_rate(attitude):
    return max(0.4, 0.75 + 0.07 * attitude)


def batch_size(player_era_index):
    return 4 + 2 * max(0, min(player_era_index, len(sim.ERA_ORDER) - 1))


# --- trade -----------------------------------------------------------------------------------
def can_trade(record, sid, season, resources, player_era_index):
    """(ok, reason). The player must hold the batch the neighbour needs, and wait out the cool-down."""
    if sid not in SLOT_IDS:
        return False, "No such neighbour."
    seed_view = view(record, sid, season, player_era_index)
    if season < record["slots"][sid]["next_trade"]:
        return False, f"{seed_view['name']} will trade again in {seed_view['trade_ready_in']} seasons."
    have = resources.get(seed_view["need"], 0.0)
    if have < seed_view["give"]:
        return False, f"You need {seed_view['give']} {seed_view['need']} to trade with {seed_view['name']}."
    return True, ""


def apply_trade(ui, sid, season, resources, player_era_index):
    """Trades one batch. Mutates `resources` and `ui`. Returns (ok, message)."""
    record = ensure(ui)
    ok, reason = can_trade(record, sid, season, resources, player_era_index)
    if not ok:
        return False, reason
    v = view(record, sid, season, player_era_index)
    resources[v["need"]] = resources[v["need"]] - v["give"]
    resources[v["offer"]] = resources.get(v["offer"], 0.0) + v["get"]
    slot = record["slots"][sid]
    slot["attitude"] = min(ATTITUDE_MAX, slot["attitude"] + 1)
    slot["next_trade"] = season + TRADE_COOLDOWN
    slot["trades"] += 1
    text = f"Traded with {v['name']}: gave {v['give']} {v['need']}, received {v['get']} {v['offer']}."
    _log(record, season, text)
    put(ui, record)
    return True, text


# --- share research --------------------------------------------------------------------------
def next_share_candidate(record, sid, researched, costs):
    """The most recently studied discovery not yet shared with `sid`, or None. `costs` maps node id
    to its cost."""
    shared = set(record["slots"][sid]["shared"])
    for node_id in reversed(list(researched)):
        if isinstance(node_id, str) and node_id not in shared and node_id in costs:
            return node_id
    return None


def apply_share(ui, sid, season, researched, costs, names, player_era_index):
    """Shares the latest unshared discovery with a neighbour for knowledge. Returns
    (ok, message, knowledge_gained)."""
    if sid not in SLOT_IDS:
        return False, "No such neighbour.", 0.0
    record = ensure(ui)
    slot = record["slots"][sid]
    v = view(record, sid, season, player_era_index)
    if season < slot["next_share"]:
        return False, f"{v['name']} is still studying the last one: ready in {v['share_ready_in']} seasons.", 0.0
    node_id = next_share_candidate(record, sid, researched, costs)
    if node_id is None:
        return False, f"You have no discovery {v['name']} has not already heard.", 0.0
    lore = 1.0 + max(0, v["era_index"] - player_era_index) * 0.25
    gained = round(costs[node_id] * SHARE_RETURN * lore, 1)
    slot["shared"].append(node_id)
    slot["attitude"] = min(ATTITUDE_MAX, slot["attitude"] + 1)
    slot["next_share"] = season + SHARE_COOLDOWN
    text = f"Shared {names.get(node_id, node_id)} with {v['name']}; they sent back {gained:g} knowledge."
    _log(record, season, text)
    put(ui, record)
    return True, text, gained


# --- the Salt Flats auction ------------------------------------------------------------------
def lease_income(player_era_index):
    return LEASE_INCOME_BASE + max(0, player_era_index)


def bid_base(player_era_index):
    return 6 + 2 * max(0, player_era_index)


def next_auction_season(record):
    """The season the next auction is settled in."""
    lease = record["lease"]
    return AUCTION_FIRST + lease["auctions"] * AUCTION_PERIOD


def bid_options(player_era_index):
    base = bid_base(player_era_index)
    return [(name, base + extra) for name, extra in BID_CHOICES]


def ai_bid(seed, sid, auction_no, attitude, player_era_index):
    """The AI controller's bid: a base that grows with the player's era, a deterministic spread of
    0-4, and a friendly neighbour (attitude above zero) asks less of you."""
    spread = _hash(seed, sid, auction_no, "bid") % 5
    return max(1, bid_base(player_era_index) - 2 + spread - max(0, attitude) + max(0, -attitude))


CONTROLLERS = {"ai": ai_bid}


def rival_range(record, season, player_era_index):
    """(low, high) of what the rivals might bid next time, as a hint without giving it away."""
    base = bid_base(player_era_index)
    return max(1, base - 5), base + 4


def place_bid(ui, amount, resources, season, player_era_index):
    """Reserves `amount` materials for the coming auction. Returns (ok, message)."""
    record = ensure(ui)
    lease = record["lease"]
    if lease["pending"]:
        return False, "You already have a bid in for the next auction."
    amount = _int(amount, 0, 10**5)
    if amount < 1:
        return False, "A bid must be at least 1 material."
    if resources.get("materials", 0.0) < amount:
        return False, f"You need {amount} materials to place that bid."
    resources["materials"] = resources["materials"] - amount
    lease["pending"] = amount
    _log(record, season, f"You bid {amount} materials for the lease on {SITE_NAME}.")
    put(ui, record)
    return True, f"Bid of {amount} materials placed. It is settled in season {next_auction_season(record)}."


def resolve_auction(ui, season, resources, player_era_index):
    """Settles an auction when its season has come. Returns a list of event texts (possibly empty).
    A tie goes to you. The winner's bid is paid; yours is refunded if you lose."""
    record = ensure(ui)
    lease = record["lease"]
    if season < next_auction_season(record):
        return []
    # An auction left unattended for a long time is not replayed one by one: skip to the current one.
    auction_no = max(lease["auctions"], (season - AUCTION_FIRST) // AUCTION_PERIOD)
    bids = {sid: CONTROLLERS["ai"](record["seed"], sid, auction_no, record["slots"][sid]["attitude"], player_era_index)
            for sid in SLOT_IDS}
    mine = lease["pending"]
    texts = []
    best_sid = max(SLOT_IDS, key=lambda sid: (bids[sid], -SLOT_IDS.index(sid)))
    best = bids[best_sid]
    if mine and mine >= best:
        lease["holder"] = "you"
        for sid in SLOT_IDS:
            if bids[sid] >= mine - 2:
                record["slots"][sid]["attitude"] = max(ATTITUDE_MIN, record["slots"][sid]["attitude"] - 1)
        texts.append(
            f"You won the lease on {SITE_NAME} with a bid of {mine} (the best rival offered {best}). "
            f"It pays {lease_income(player_era_index)} materials a season for {LEASE_LENGTH} seasons."
        )
    else:
        lease["holder"] = best_sid
        if mine:
            resources["materials"] = resources.get("materials", 0.0) + mine
            texts.append(
                f"{slot_name(record['seed'], best_sid)} won the lease on {SITE_NAME} with {best}; "
                f"your bid of {mine} is returned."
            )
        else:
            texts.append(f"{slot_name(record['seed'], best_sid)} took the lease on {SITE_NAME} with a bid of {best}.")
    lease["until"] = season + LEASE_LENGTH
    lease["pending"] = 0
    lease["auctions"] = auction_no + 1
    for text in texts:
        _log(record, season, text)
    put(ui, record)
    return texts


def pay_lease(ui, season, resources, player_era_index):
    """Pays the season's income if you hold a live lease. Returns the amount paid (0 if none)."""
    record = get(ui)
    lease = record["lease"]
    if lease["holder"] != "you" or season > lease["until"]:
        return 0
    income = lease_income(player_era_index)
    resources["materials"] = resources.get("materials", 0.0) + income
    return income


def after_season(ui, season, resources, player_era_index):
    """Everything that happens when a season ends: the auction settles, the lease pays. Returns
    the event texts."""
    if not isinstance(ui, dict) or KEY not in ui:
        return []
    texts = resolve_auction(ui, season, resources, player_era_index)
    paid = pay_lease(ui, season, resources, player_era_index)
    if paid:
        texts.append(f"The lease on {SITE_NAME} paid {paid} materials.")
    return texts


def _log(record, season, text):
    record["events"].append({"season": season, "text": text})
    record["events"] = record["events"][-MAX_EVENTS:]


def lease_text(record, season):
    lease = record["lease"]
    next_no = next_auction_season(record)
    holder = lease["holder"]
    if holder == "you" and season <= lease["until"]:
        who = f"You hold the lease on {SITE_NAME} until season {lease['until']}."
    elif holder in SLOT_IDS and season <= lease["until"]:
        who = f"{slot_name(record['seed'] or 1, holder)} holds the lease on {SITE_NAME} until season {lease['until']}."
    else:
        who = f"Nobody holds the lease on {SITE_NAME} right now."
    pending = f" Your bid of {lease['pending']} materials is in." if lease["pending"] else ""
    when = f" The next auction is settled in season {next_no}." if next_no > season else " The auction is settled this season."
    return who + pending + when


# --- the map ---------------------------------------------------------------------------------
def map_svg(slot_views, record, season, player_label):
    """The regional map as an SVG string: roads from your settlement, the contested site, and
    each neighbour with its era written out. Attitude is shown in words and in the road's style
    (solid when friendly or neutral, dashed when cold), never by colour alone."""
    lease = record["lease"]
    holder = lease["holder"] if season <= lease["until"] else "none"
    parts = [
        '<svg viewBox="0 0 360 220" class="views-svg nb-map" role="img" '
        'aria-label="Regional map: your settlement, three neighbouring settlements and the contested Salt Flats">',
        '<rect x="0" y="0" width="360" height="220" class="map-bg"/>',
    ]
    px, py = PLAYER_POS
    for v in slot_views:
        style = "nb-road" if v["attitude"] >= 0 else "nb-road nb-road--cold"
        parts.append(f'<line x1="{px}" y1="{py}" x2="{v["x"]}" y2="{v["y"]}" class="{style}"/>')
    sx, sy = SITE_POS
    site_state = "nb-site nb-site--yours" if holder == "you" else ("nb-site nb-site--rival" if holder in SLOT_IDS else "nb-site")
    parts.append(
        f'<polygon points="{sx},{sy - 11} {sx + 11},{sy} {sx},{sy + 11} {sx - 11},{sy}" class="{site_state}"/>'
        f'<text x="{sx}" y="{sy + 25}" text-anchor="middle" class="map-label">Salt Flats</text>'
    )
    holder_word = "yours" if holder == "you" else (
        slot_name(record["seed"] or 1, holder) if holder in SLOT_IDS else "unclaimed"
    )
    parts.append(f'<text x="{sx}" y="{sy + 36}" text-anchor="middle" class="map-count">{holder_word}</text>')
    parts.append(
        f'<rect x="{px - 12}" y="{py - 12}" width="24" height="24" rx="3" class="nb-home"/>'
        f'<text x="{px}" y="{py + 28}" text-anchor="middle" class="map-label">{player_label}</text>'
        f'<text x="{px}" y="{py + 39}" text-anchor="middle" class="map-count">you</text>'
    )
    for v in slot_views:
        parts.append(
            f'<circle cx="{v["x"]}" cy="{v["y"]}" r="11" class="nb-town"/>'
            f'<text x="{v["x"]}" y="{v["y"] - 17}" text-anchor="middle" class="map-label">{v["name"]}</text>'
            f'<text x="{v["x"]}" y="{v["y"] + 25}" text-anchor="middle" class="map-count">{v["era_label"]}, {v["attitude_word"]}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def map_caption(slot_views):
    return " ".join(
        f"{v['name']} ({v['era_label']}, {v['attitude_word']}) needs {v['need']} and offers {v['offer']}."
        for v in slot_views
    )
