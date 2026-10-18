"""The region collection (titles, civic milestones), region skins, the achievement toast checks that unlock skins, star goals and the run history."""

import json

from js import document

import drift_runstate as runstate
from drift_achievements import (
    ACHIEVEMENTS, _display_achievement_toast, _story_reach_all, achievement_ids_earned, announce,
    fresh_glyph_ids, update_achievements_display,
)
from drift_model_region import region
from drift_pages import _read_local_storage_item, _write_local_storage_item
from drift_rules import (
    CAPACITY_TYPES, REGION_NAME_MAX_LENGTH, RUN_HISTORY_MAX, RUN_HISTORY_STORAGE_KEY,
    RUN_STARS_NET_POSITIVE_ROUND, RUN_STARS_ROI, RUN_STARS_ROUND, RUN_STARS_WELLBEING,
)
from drift_visuals import _set_pressed


def _seed_achievement_toast_baseline():
    runstate._achievements_seen_ids = set(achievement_ids_earned())
    _story_reach_all(runstate._achievements_seen_ids)  # W1: a loaded save's earned chapters come back too
    if unlock_skins(runstate._achievements_seen_ids):  # GI-25: a loaded save earns its skins quietly
        render_skins()


def _check_new_achievements_for_toast():
    """Called after every player action that could change earned status
    (invest/advance round/toggle coda) — never from render() itself,
    since load_state() also calls render() and a loaded save with
    several achievements already earned must not flood the player with
    toasts for all of them at once (see _seed_achievement_toast_baseline)."""
    earned_now = set(achievement_ids_earned())
    _story_reach_all(earned_now)
    newly = earned_now - runstate._achievements_seen_ids
    if newly:
        by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
        labels = [by_id[aid]["label"] for aid in newly if aid in by_id]
        if labels:
            if len(labels) == 1:
                _display_achievement_toast(f"🏆 Achievement unlocked: {labels[0]}")
                announce(f"Achievement unlocked: {labels[0]}")
            else:
                _display_achievement_toast(f"🏆 {len(labels)} achievements unlocked: " + ", ".join(labels))
                announce(f"{len(labels)} achievements unlocked: " + ", ".join(labels))
    _note_new_skins(earned_now)
    runstate._achievements_seen_ids = earned_now
    if newly:
        fresh_glyph_ids.update(newly)
        if runstate.achievements_open:
            update_achievements_display()  # draw the new badge in now, while the panel is open


def _note_new_skins(earned_ids):
    """GI-25: an achievement that opens a region skin says so (Settings note and a spoken line)."""
    newly = unlock_skins(earned_ids)
    if newly:
        names = ", ".join(skin["label"] for skin in newly)
        runstate.skin_note = f"New region skin unlocked: {names}. Choose it in Settings."
        announce(runstate.skin_note)
        render_skins()


# ---- GI-15 / GI-22: Region Collection (personality titles, civic milestones) -----
COLLECTION_STORAGE_KEY = "drift_collection_v1"
TITLE_MIN_ROUND = 8
TITLE_MIN_SPEND = 100.0
REGION_TITLES = {
    "builder": {
        "label": "The Builder",
        "hint": "Put at least half of everything you spend into Housing.",
        "text": "This region's funds went mostly into homes: roof first, everything else after.",
    },
    "educator": {
        "label": "The Educator",
        "hint": "Put at least half of everything you spend into Integration Services.",
        "text": "This region's funds went mostly into language, work and school access for newcomers.",
    },
    "engineer": {
        "label": "The Engineer",
        "hint": "Put at least 40% of everything you spend into Infrastructure.",
        "text": "This region's funds went mostly into the pipes, roads and clinics everyone shares.",
    },
    "reformer": {
        "label": "The Reformer",
        "hint": "Put at least 30% of everything you spend into the policy toolkit.",
        "text": "This region leaned on rules and programmes: credentialing, language access and sponsorship.",
    },
    "balancer": {
        "label": "The Balancer",
        "hint": "Keep Housing, Services and Infrastructure each above 15% of your spending, with no other title fitting.",
        "text": "This region spread its funds evenly and never bet on one lever.",
    },
}
TITLE_ORDER = ["builder", "educator", "engineer", "reformer", "balancer"]
_TITLE_THRESHOLDS = {"builder": 0.5, "educator": 0.5, "engineer": 0.4, "reformer": 0.3}
_TITLE_SPEND_KEY = {"builder": "housing", "educator": "services", "engineer": "infrastructure", "reformer": "policy"}


def region_title_key(region_state):
    """The personality title fitted by the lifetime spending split (capacity and
    policy spending; reallocation fees do not count), or None while too little
    has been spent to say."""
    parts = {k: region_state.spend_by_type[k] for k in ("housing", "services", "infrastructure", "policy")}
    total = sum(parts.values())
    if total < TITLE_MIN_SPEND:
        return None
    shares = {k: v / total for k, v in parts.items()}
    best = None
    best_margin = 0.0
    for key in ("builder", "educator", "engineer", "reformer"):
        margin = shares[_TITLE_SPEND_KEY[key]] - _TITLE_THRESHOLDS[key]
        if margin >= 0 and (best is None or margin > best_margin):
            best, best_margin = key, margin
    if best is not None:
        return best
    if min(shares["housing"], shares["services"], shares["infrastructure"]) >= 0.15:
        return "balancer"
    return None


# Each civic milestone: id, name, a hint shown while locked, one line shown once
# found, and a test (region, completed_round) -> bool. "By round N" means the
# round that just resolved is N or earlier. Cosmetic: they change no number.
CIVIC_MILESTONES = [
    {
        "id": "first_roof_fund", "name": "First Roof Fund",
        "hint": "Reach 100 Housing capacity by round 5.",
        "text": "A dedicated housing fund opened before most arrivals had even landed.",
        "test": lambda r, n: n <= 5 and r.capacity["housing"] >= 100,
    },
    {
        "id": "night_classes", "name": "Night Classes",
        "hint": "Reach 48 Integration Services capacity by round 8.",
        "text": "Evening language and skills classes were running before the first backlog formed.",
        "test": lambda r, n: n <= 8 and r.capacity["services"] >= 48,
    },
    {
        "id": "three_pillars", "name": "Three Pillars Compact",
        "hint": "Reach 60 capacity in Housing, Services and Infrastructure by round 12.",
        "text": "Homes, services and shared infrastructure were agreed as one package, not three separate fights.",
        "test": lambda r, n: n <= 12 and all(r.capacity[t] >= 60 for t in CAPACITY_TYPES),
    },
    {
        "id": "open_charter", "name": "Open Charter",
        "hint": "Have 80% of arrivals integrated by round 15 (at least 100 arrived).",
        "text": "The region's charter gave newcomers a clear route to work, school and services.",
        "test": lambda r, n: n <= 15 and r.total_arrivals >= 100 and r.integration_fraction() >= 0.8,
    },
    {
        "id": "ring_road", "name": "Ring Road",
        "hint": "Reach 120 Infrastructure capacity by round 20.",
        "text": "A ring road and shared clinics took the load off the old centre.",
        "test": lambda r, n: n <= 20 and r.capacity["infrastructure"] >= 120,
    },
    {
        "id": "skilled_welcome", "name": "Skilled Welcome",
        "hint": "Fund all three policies at least once by round 20.",
        "text": "Qualification recognition, language funding and sponsorship all opened in the same few years.",
        "test": lambda r, n: n <= 20 and all(level >= 1 for level in r.policy_level.values()),
    },
    {
        "id": "good_neighbours", "name": "Good Neighbours",
        "hint": "Send support to the neighbouring district by round 25.",
        "text": "A calm region shared its cushion with a district under more pressure.",
        "test": lambda r, n: n <= 25 and runstate.neighbor_support_sent > 0,
    },
    {
        "id": "harbour_lights", "name": "Harbour Lights",
        "hint": "Reach 100 Services and 100 Infrastructure capacity by round 30.",
        "text": "Services and infrastructure both passed a hundred: the lights stayed on at every hour.",
        "test": lambda r, n: n <= 30 and r.capacity["services"] >= 100 and r.capacity["infrastructure"] >= 100,
    },
    {
        "id": "steady_hands", "name": "Steady Hands",
        "hint": "Hold strain at stable for 20 rounds in a row by round 30.",
        "text": "Twenty calm rounds in a row: planning, not reacting.",
        "test": lambda r, n: n <= 30 and r.best_stable_streak >= 20,
    },
    {
        "id": "quiet_weather", "name": "Quiet Weather",
        "hint": "Hold through the second wave without strain reaching critical.",
        "text": "The second wave came and the region's institutions simply absorbed it.",
        "test": lambda r, n: r.second_wave_result == "held",
    },
]
CIVIC_BY_ID = {entry["id"]: entry for entry in CIVIC_MILESTONES}


def _clean_collection(raw):
    """A well-formed collection dict from anything, dropping unknown ids and bad values."""
    out = {"titles": [], "civic": {}}
    if not isinstance(raw, dict):
        return out
    titles = raw.get("titles")
    if isinstance(titles, list):
        for key in TITLE_ORDER:
            if key in titles:
                out["titles"].append(key)
    civic = raw.get("civic")
    if isinstance(civic, dict):
        for entry in CIVIC_MILESTONES:
            found = civic.get(entry["id"])
            if isinstance(found, int) and not isinstance(found, bool) and found >= 1:
                out["civic"][entry["id"]] = found
    return out


def _load_collection():
    raw = _read_local_storage_item(COLLECTION_STORAGE_KEY)
    if not raw:
        return _clean_collection(None)
    try:
        return _clean_collection(json.loads(raw))
    except (ValueError, TypeError):
        return _clean_collection(None)


def _store_collection():
    _write_local_storage_item(COLLECTION_STORAGE_KEY, json.dumps(collection))


def merge_collection(other):
    """Union a (validated) collection into the live one; returns True if it grew."""
    other = _clean_collection(other)
    grew = False
    for key in other["titles"]:
        if key not in collection["titles"]:
            collection["titles"].append(key)
            grew = True
    collection["titles"].sort(key=TITLE_ORDER.index)
    for found_id, found_round in other["civic"].items():
        if found_id not in collection["civic"]:
            collection["civic"][found_id] = found_round
            grew = True
    if grew:
        _store_collection()
    return grew


collection = _load_collection()


def _collect_after_round(completed_round):
    """Record any civic milestone newly met and the personality title once the
    region has played TITLE_MIN_ROUND rounds. Returns the list of new names."""
    found = []
    for entry in CIVIC_MILESTONES:
        if entry["id"] in collection["civic"]:
            continue
        if entry["test"](region, completed_round):
            collection["civic"][entry["id"]] = completed_round
            found.append(f"Civic milestone: {entry['name']}")
    if completed_round >= TITLE_MIN_ROUND:
        title = region_title_key(region)
        if title is not None and title not in collection["titles"]:
            collection["titles"].append(title)
            collection["titles"].sort(key=TITLE_ORDER.index)
            found.append(f"Title: {REGION_TITLES[title]['label']}")
    if found:
        _store_collection()
        runstate.collection_note = "New in your collection: " + "; ".join(found) + "."
        _display_achievement_toast("🗂️ " + found[0] + (f" (+{len(found) - 1} more)" if len(found) > 1 else ""))
    banked = _bank_run_stars(completed_round)
    if banked:
        found.append(banked)
        runstate.collection_note = (runstate.collection_note + " " if runstate.collection_note else "") + banked
        _display_achievement_toast("⭐ " + banked)
    return found


def collection_counts():
    return len(collection["civic"]), len(CIVIC_MILESTONES), len(collection["titles"]), len(REGION_TITLES)


def share_result():
    """Z-20: the headline numbers for the shared "Copy result" button, as a JSON string the page
    reads (it calls this by name through window.pyodide). Wellbeing score, the projected
    long-horizon wellbeing the coda shows, people integrated and rounds played."""
    stats = []
    if region.has_long_horizon_story():
        stats.append(f"{region.projected_wellbeing_score():.0f} projected generations from now")
    stats.append({"n": round(region.integrated_population), "one": "person integrated", "many": "people integrated"})
    stats.append({"n": max(0, region.round_number - 1), "one": "round", "many": "rounds"})
    return json.dumps({
        "game": "Drift",
        "score": round(region.wellbeing_score()),
        "unit": "wellbeing",
        "stats": stats,
    })


def render_collection_summary():
    civic, civic_total, titles, titles_total = collection_counts()
    document.getElementById("collection-summary-display").innerText = (
        f"Collection: {civic}/{civic_total} civic milestones, {titles}/{titles_total} titles."
    )
    title_key = region_title_key(region)
    title_el = document.getElementById("region-title-display")
    if title_key is None:
        title_el.innerText = "Region personality: still forming (spend about 100 funds to see it)."
    else:
        extra = " In your collection." if title_key in collection["titles"] else f" Added to your collection at round {TITLE_MIN_ROUND}."
        title_el.innerText = f"Region personality: {REGION_TITLES[title_key]['label']}.{extra}"
    toggle = document.getElementById("collection-toggle-button")
    toggle.innerText = "Hide Collection" if runstate.collection_open else f"🗂️ Collection ({civic + titles}/{civic_total + titles_total})"
    panel = document.getElementById("collection-panel")
    panel.hidden = not runstate.collection_open
    if not runstate.collection_open:
        return
    lines = []
    note = runstate.collection_note
    if note:
        lines.append(f"<p class=\"collection-note\">{note}</p>")
    lines.append(f"<p class=\"meter-label\">Civic milestones ({civic}/{civic_total})</p><ul class=\"collection-list\">")
    for entry in CIVIC_MILESTONES:
        found = collection["civic"].get(entry["id"])
        if found is not None:
            lines.append(
                f"<li class=\"collection-found\"><strong>✓ {entry['name']}</strong> (round {found}): {entry['text']}</li>"
            )
        else:
            lines.append(f"<li class=\"collection-locked\"><strong>🔒 Locked</strong>. Hint: {entry['hint']}</li>")
    lines.append(f"</ul><p class=\"meter-label\">Region personality titles ({titles}/{titles_total})</p><ul class=\"collection-list\">")
    for key in TITLE_ORDER:
        info = REGION_TITLES[key]
        if key in collection["titles"]:
            lines.append(f"<li class=\"collection-found\"><strong>✓ {info['label']}</strong>: {info['text']}</li>")
        else:
            lines.append(f"<li class=\"collection-locked\"><strong>🔒 Locked</strong>. Hint: {info['hint']}</li>")
    lines.append("</ul>")
    lines.append(run_history_html())
    document.getElementById("collection-list").innerHTML = "".join(lines)


# ---- GI-13 / GI-2 / GI-11 / GI-1 / GI-5 / GI-21 / I-18: civic tools ----------------


# ---- GI-25: region skins (cosmetic building palettes for the skyline) --------------------------------
# Dusk is always there; each other skin unlocks when its achievement is earned in any region on this browser,
# and stays unlocked (kept like the collection, per browser). The choice is a display preference in
# localStorage, never part of a save. The palettes themselves are CSS (`.region-visual[data-skin=...]`).
SKIN_STORAGE_KEY = "drift_skins_v1"
SKIN_CHOICE_KEY = "drift-skin"
SKINS = [
    {"id": "dusk", "label": "Dusk", "unlock": None},
    {"id": "seaside", "label": "Seaside", "unlock": "full_capacity_portfolio"},
    {"id": "alpine", "label": "Alpine", "unlock": "turning_point_reached"},
    {"id": "desert", "label": "Desert", "unlock": "crisis_averted"},
    {"id": "neon", "label": "Neon Future", "unlock": "thriving_region"},
]
SKIN_BY_ID = {skin["id"]: skin for skin in SKINS}


def _clean_skin_unlocks(raw):
    """The skin ids (other than the always-open Dusk) that a stored value says are unlocked."""
    if not isinstance(raw, list):
        return []
    return [skin["id"] for skin in SKINS if skin["unlock"] and skin["id"] in raw]


def _load_skin_unlocks():
    raw = _read_local_storage_item(SKIN_STORAGE_KEY)
    if not raw:
        return []
    try:
        return _clean_skin_unlocks(json.loads(raw))
    except (ValueError, TypeError):
        return []


def skin_unlocked(skin_id):
    skin = SKIN_BY_ID.get(skin_id)
    return skin is not None and (skin["unlock"] is None or skin_id in skins_unlocked)


def _load_skin_choice():
    raw = _read_local_storage_item(SKIN_CHOICE_KEY)
    return raw if raw in SKIN_BY_ID and (SKIN_BY_ID[raw]["unlock"] is None or raw in skins_unlocked) else "dusk"


skins_unlocked = _load_skin_unlocks()
runstate.skin_choice = _load_skin_choice()


def skin_lock_hint(skin):
    """What to do to unlock a skin: the achievement's own name."""
    by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
    entry = by_id.get(skin["unlock"])
    return f"Locked: earn the achievement {entry['label'] if entry else skin['unlock']}"


def unlock_skins(earned_ids):
    """Unlocks every skin whose achievement is in `earned_ids`; returns the newly unlocked skins."""
    newly = [
        skin for skin in SKINS
        if skin["unlock"] and skin["unlock"] in earned_ids and skin["id"] not in skins_unlocked
    ]
    for skin in newly:
        skins_unlocked.append(skin["id"])
    if newly:
        _write_local_storage_item(SKIN_STORAGE_KEY, json.dumps(skins_unlocked))
    return newly


def choose_skin(skin_id):
    if not skin_unlocked(skin_id):
        return False
    runstate.skin_choice = skin_id
    _write_local_storage_item(SKIN_CHOICE_KEY, skin_id)
    return True


def render_skins():
    document.getElementById("region-visual").dataset.skin = runstate.skin_choice
    for skin in SKINS:
        button = document.getElementById(f"skin-{skin['id']}-button")
        open_ = skin_unlocked(skin["id"])
        button.disabled = not open_
        button.title = "" if open_ else skin_lock_hint(skin)
        button.innerText = skin["label"] if open_ else f"🔒 {skin['label']}"
        _set_pressed(button, skin["id"] == runstate.skin_choice)
    document.getElementById("skin-note").innerText = runstate.skin_note


def star_goals(r=None):
    """Stars (0 to 3) on the three goals: wellbeing, speed to net-positive, efficiency of funds."""
    r = region if r is None else r
    wellbeing = sum(1 for bound in RUN_STARS_WELLBEING if r.wellbeing_score() >= bound)
    speed = 0
    if r.net_positive_round is not None:
        speed = sum(1 for bound in RUN_STARS_NET_POSITIVE_ROUND if r.net_positive_round <= bound)
    roi = r.investment_roi()
    efficiency = 0 if roi is None else sum(1 for bound in RUN_STARS_ROI if roi >= bound)
    return {"wellbeing": wellbeing, "speed": speed, "efficiency": efficiency}


def stars_text(count):
    return "★" * count + "☆" * (3 - count)


def run_stars_message():
    goals = star_goals()
    parts = (
        f"Wellbeing {stars_text(goals['wellbeing'])}  Speed {stars_text(goals['speed'])}  "
        f"Efficiency {stars_text(goals['efficiency'])}"
    )
    if region.stars_banked is not None:
        return f"Run stars: {parts}. Banked into your run history at round {region.stars_banked}."
    return f"Run stars so far: {parts}. They are banked into your run history when round {RUN_STARS_ROUND} finishes."


def _clean_run_history(raw):
    out = []
    if not isinstance(raw, list):
        return out
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        stars = entry.get("stars")
        token = entry.get("token")
        if (
            not isinstance(stars, list) or len(stars) != 3 or not isinstance(token, str)
            or not all(isinstance(n, int) and not isinstance(n, bool) and 0 <= n <= 3 for n in stars)
        ):
            continue
        name = entry.get("name")
        rounds = entry.get("round")
        out.append({
            "name": name[:REGION_NAME_MAX_LENGTH] if isinstance(name, str) else "",
            "round": rounds if isinstance(rounds, int) and not isinstance(rounds, bool) and rounds >= 1 else RUN_STARS_ROUND,
            "stars": list(stars),
            "token": token[:80],
        })
    return out[-RUN_HISTORY_MAX:]


def _load_run_history():
    raw = _read_local_storage_item(RUN_HISTORY_STORAGE_KEY)
    if not raw:
        return []
    try:
        return _clean_run_history(json.loads(raw))
    except (ValueError, TypeError):
        return []


run_history = _load_run_history()


def _run_token():
    return f"{region.region_name}|{region.total_arrivals:.1f}|{region.cumulative_integration_contribution:.1f}"


def _bank_run_stars(completed_round):
    """Bank the run's stars once, when round RUN_STARS_ROUND has finished. Returns a message or None."""
    if completed_round < RUN_STARS_ROUND or region.stars_banked is not None:
        return None
    region.stars_banked = completed_round
    goals = star_goals()
    token = _run_token()
    if any(entry["token"] == token for entry in run_history):
        return None
    run_history.append({
        "name": region.region_name, "round": completed_round,
        "stars": [goals["wellbeing"], goals["speed"], goals["efficiency"]], "token": token,
    })
    del run_history[:-RUN_HISTORY_MAX]
    _write_local_storage_item(RUN_HISTORY_STORAGE_KEY, json.dumps(run_history))
    total = sum(run_history[-1]["stars"])
    return f"Run banked at round {completed_round}: {total} of 9 stars."


def run_history_html():
    if not run_history:
        return "<p class=\"collection-locked\">No banked runs yet. Reach the end of round " + str(RUN_STARS_ROUND) + " to bank your first.</p>"
    best = sorted(run_history, key=lambda e: (-sum(e["stars"]), run_history.index(e)))[:5]
    items = []
    for entry in best:
        label = entry["name"] or "Unnamed region"
        s = entry["stars"]
        items.append(
            f"<li><strong>{stars_text(s[0])} {stars_text(s[1])} {stars_text(s[2])}</strong> "
            f"({sum(s)} of 9) {label}, round {entry['round']}</li>"
        )
    return (
        "<p class=\"meter-label\">Best star combinations (wellbeing, speed, efficiency)</p>"
        "<ul class=\"collection-list\">" + "".join(items) + "</ul>"
    )
