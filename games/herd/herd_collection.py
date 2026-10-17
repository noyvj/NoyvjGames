"""Breeds and combos (GF-16, GF-5), rating titles, the highlights reel, lever efficiency, cap headroom and the lever history.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

from js import document

import herd_runstate as runstate
from herd_rules import (
    DECOUPLING_MEASURES, LEVER_LABELS, PERFECT_STREAK_BONUSES, PLANT_PIVOT_COST, POULTRY_MEASURES,
    REGIONAL_CAP,
)
from herd_achievements import _display_milestone_toast
from herd_barns import _sync_barns
from herd_loadouts import _sync_loadouts


# ===========================================================================
# GF-16 breed collection, GF-5 decoupling combos, GF-22 rating titles,
# GF-29 highlights reel, F-13 lever efficiency, F-24 cap headroom and F-17
# lever history. All of it is derived from state that already exists (plus the
# funds history and purchase log on FarmState) except the two collections,
# which are module-level like the succession perks: a handover restarts the
# farm but never empties the shelf or the combo book.
# ===========================================================================
COMBO_REWARD_FUNDS = 20
RATING_FIRST_MESSAGE = "Advance a round to start your highlight reel."

# GF-16: breeds are a collector shelf. Each is earned once, for good, by reaching a
# state on any farm. The last one is hidden until earned (its silhouette shows a
# rumour, not the rule), but every breed can be earned in a normal game.
BREEDS = [
    {"id": "clover_calf", "label": "Clover Calf", "glyph": "\U0001F42E",
     "how": "Own your first animal.", "check": lambda f: f.herd_size >= 1},
    {"id": "brindle_belle", "label": "Brindle Belle", "glyph": "\U0001F404",
     "how": "Grow the herd to 10.", "check": lambda f: f.herd_size >= 10},
    {"id": "prairie_patriarch", "label": "Prairie Patriarch", "glyph": "\U0001F402",
     "how": "Grow the herd to 25.", "check": lambda f: f.herd_size >= 25},
    {"id": "sage_grazer", "label": "Sage Grazer", "glyph": "\U0001F33E",
     "how": "Buy 3 Feed Additives.", "check": lambda f: f.decoupling_investment["feed"] >= 3},
    {"id": "roomy_ruminant", "label": "Roomy Ruminant", "glyph": "\U0001F6A7",
     "how": "Buy 3 Herd Caps.", "check": lambda f: f.decoupling_investment["caps"] >= 3},
    {"id": "biogas_bessie", "label": "Biogas Bessie", "glyph": "♻️",
     "how": "Buy 3 Capture Systems.", "check": lambda f: f.decoupling_investment["capture"] >= 3},
    {"id": "meadow_mooncow", "label": "Meadow Mooncow", "glyph": "\U0001F33F",
     "how": "Shift 20% of output to plant-based (4 Pivots).", "check": lambda f: f.plant_pivot_investment >= 4},
    {"id": "coop_champion", "label": "Coop Champion", "glyph": "\U0001F414",
     "how": "Raise a flock of 5.", "check": lambda f: f.poultry_size >= 5},
    {"id": "hilltop_wanderer", "label": "Hilltop Wanderer", "glyph": "⛰️",
     "how": "Grow the satellite herd to 3.", "check": lambda f: f.satellite_open and f.satellite_size >= 3},
    {"id": "certified_jersey", "label": "Certified Jersey", "glyph": "\U0001F3C5",
     "how": "Earn sustainable certification.", "check": lambda f: f.certified},
    {"id": "methane_eater_cow", "label": "Methane-Eater Cow", "glyph": "✨", "hidden": True,
     "hint": "Rumoured: a herd that is both very clean and very well cared for.",
     "how": "Coupling ratio under 0.25 with herd welfare at 90 or more.",
     "check": lambda f: f.coupling_ratio() < 0.25 and f.welfare() >= 90},
]

# GF-5: named combos of levers held together, each paid once (to the real farm only,
# like the streak bonuses). The book shows the rule for every entry but hides the
# name until it is found.
COMBOS = [
    {"id": "circular_barn", "label": "Circular Barn", "how": "3 Capture Systems and 2 Feed Additives.",
     "check": lambda f: f.decoupling_investment["capture"] >= 3 and f.decoupling_investment["feed"] >= 2},
    {"id": "happy_herd", "label": "Happy Herd", "how": "Herd welfare 70 or more and 2 Herd Caps.",
     "check": lambda f: f.welfare() >= 70 and f.decoupling_investment["caps"] >= 2},
    {"id": "green_gourmet", "label": "Green Gourmet", "how": "3 Plant-Based Pivots and 2 Processing & Distribution.",
     "check": lambda f: f.plant_pivot_investment >= 3 and f.supply_chain_investment >= 2},
    {"id": "full_stack", "label": "Full Stack", "how": "At least one of every lever on the main farm: Feed, Caps, Capture, Pivot, Breeding (matured) and Processing.",
     "check": lambda f: (
         all(f.decoupling_investment[m] >= 1 for m in DECOUPLING_MEASURES)
         and f.plant_pivot_investment >= 1 and f.genetics_active >= 1 and f.supply_chain_investment >= 1)},
    {"id": "poultry_partners", "label": "Poultry Partners", "how": "A flock of 3 with Litter Management and a Biofilter.",
     "check": lambda f: f.poultry_size >= 3 and f.poultry_investment["litter"] >= 1 and f.poultry_investment["biofilter"] >= 1},
    {"id": "twin_barns", "label": "Twin Barns", "how": "Open the satellite farm and retrofit it 3 times.",
     "check": lambda f: f.satellite_open and f.satellite_retrofits >= 3},
    {"id": "slow_burn", "label": "Slow Burn", "how": "Two breeding lines matured.",
     "check": lambda f: f.genetics_active >= 2},
    {"id": "biogas_baron", "label": "Biogas Baron", "how": "5 Capture Systems, so surplus gas is sold.",
     "check": lambda f: f.decoupling_investment["capture"] >= 5},
]


def _sync_collection(award=True):
    """Marks every breed and combo the current farm qualifies for. With award=True
    (normal play) a new combo pays its reward and a toast names what was found;
    with award=False (loading a save) it only records, so a load never changes
    funds. Returns the list of newly found labels."""
    if runstate.sandbox_active:  # GF-24: no breed, combo, barn or loadout is ever found in the sandbox
        return []
    found = []
    for breed in BREEDS:
        if breed["id"] not in runstate.breeds_collected and breed["check"](runstate.farm):
            runstate.breeds_collected.append(breed["id"])
            found.append(f"new breed {breed['label']}")
    for combo in COMBOS:
        if combo["id"] not in runstate.combos_found and combo["check"](runstate.farm):
            runstate.combos_found.append(combo["id"])
            if award:
                runstate.farm.funds += COMBO_REWARD_FUNDS
            found.append(f"combo {combo['label']}" + (f" (+{COMBO_REWARD_FUNDS} funds)" if award else ""))
    found.extend(_sync_barns())
    found.extend(_sync_loadouts())
    if award and found:
        _display_milestone_toast("\U0001F4D6 Collection: " + ", ".join(found) + ".")
    return found


def _valid_ids(raw, catalog):
    if not isinstance(raw, list):
        return []
    known = {entry["id"] for entry in catalog}
    result = []
    for value in raw:
        if isinstance(value, str) and value in known and value not in result:
            result.append(value)
    return result


def breed_shelf_html():
    cards = []
    for breed in BREEDS:
        earned = breed["id"] in runstate.breeds_collected
        hidden = breed.get("hidden", False)
        classes = "breed-card"
        if earned:
            classes += " breed-card--earned" + (" breed-card--legend" if hidden else "")
            name, detail, glyph = breed["label"], breed["how"], breed["glyph"]
        else:
            classes += " breed-card--locked"
            name = "???" if hidden else breed["label"]
            detail = breed["hint"] if hidden else breed["how"]
            glyph = "❔" if hidden else breed["glyph"]
        status = "collected" if earned else "not collected yet"
        cards.append(
            f'<li class="{classes}"><span class="breed-glyph" aria-hidden="true">{glyph}</span>'
            f'<span class="breed-name">{name}</span>'
            f'<span class="breed-detail">{detail}</span>'
            f'<span class="sr-only">{status}</span></li>'
        )
    return "".join(cards)


def combo_book_html():
    rows = []
    for combo in COMBOS:
        found = combo["id"] in runstate.combos_found
        name = combo["label"] if found else "???"
        mark = f"found, paid {COMBO_REWARD_FUNDS} funds" if found else "not found yet"
        classes = "combo-card combo-card--found" if found else "combo-card combo-card--locked"
        rows.append(
            f'<li class="{classes}"><span class="combo-name">{name}</span>'
            f'<span class="combo-detail">{combo["how"]}</span>'
            f'<span class="sr-only">{mark}</span></li>'
        )
    return "".join(rows)


def collection_summary_message():
    return (
        f"Breeds {len(runstate.breeds_collected)}/{len(BREEDS)}  |  Combos {len(runstate.combos_found)}/{len(COMBOS)}  |  "
        f"Best perfect-round streak {runstate.farm.best_perfect_streak}"
    )


# GF-22: a rating ladder, highest rung currently satisfied wins. Pure functions of state.
def _decoupled_at_least(share):
    # Epsilon: ten 1% steps of float arithmetic must still count as exactly 10%.
    return runstate.farm.decoupled_fraction() >= share - 1e-9


def _score_beat_pct():
    baseline = runstate.farm.counterfactual_score()
    if abs(baseline) < 1e-9:
        return 0.0
    return (runstate.farm.score() - baseline) / abs(baseline) * 100


RATING_TITLES = [
    ("Hobby Farmer", "\U0001F9D1‍\U0001F33E", "Start a farm.", lambda: True),
    ("Feed Hand", "\U0001F33E", "Decouple 10% below baseline.", lambda: _decoupled_at_least(0.10)),
    ("Careful Rancher", "\U0001F920", "Decouple 25% below baseline.", lambda: _decoupled_at_least(0.25)),
    ("Ahead of the Curve", "\U0001F4C8", "Decouple 40% and score above the pure-growth baseline.",
     lambda: _decoupled_at_least(0.40) and runstate.farm.score() > runstate.farm.counterfactual_score()),
    ("Certified Steward", "\U0001F3C5", "Earn sustainable certification.", lambda: runstate.farm.certified),
    ("Methane Cutter", "✂️", "Decouple 70% and beat the baseline score by 25%.",
     lambda: _decoupled_at_least(0.70) and _score_beat_pct() >= 25),
    ("Decoupling Legend", "\U0001F451", "Decouple 80%, certified, and beat the baseline score by 50%.",
     lambda: runstate.farm.certified and _decoupled_at_least(0.80) and _score_beat_pct() >= 50),
]


def rating_index():
    current = 0
    for index, (_name, _glyph, _need, check) in enumerate(RATING_TITLES):
        if check():
            current = index
    return current


def rating_message():
    index = rating_index()
    name, glyph, _need, _check = RATING_TITLES[index]
    text = f"{glyph} Rating: {name}."
    if index + 1 < len(RATING_TITLES):
        next_name, _g, need, _c = RATING_TITLES[index + 1]
        text += f" Next, {next_name}: {need}"
    else:
        text += " The top of the ladder."
    return text


def streak_message():
    streak = runstate.farm.perfect_streak
    upcoming = [length for length in sorted(PERFECT_STREAK_BONUSES) if length > streak]
    text = f"\U0001F525 Perfect-round streak: {streak} (best {runstate.farm.best_perfect_streak})."
    if upcoming:
        text += f" Bonus at {upcoming[0]}: +{PERFECT_STREAK_BONUSES[upcoming[0]]} funds."
    return text + " A perfect round adds less methane than the last and still ends with more funds."


# GF-29: three screenshot-friendly lines from the per-round histories.
def highlights_lines():
    gains = [
        (index, runstate.farm.funds_history[index] - runstate.farm.funds_history[index - 1])
        for index in range(1, len(runstate.farm.funds_history))
        if runstate.farm.funds_history[index] is not None and runstate.farm.funds_history[index - 1] is not None
    ]
    increments = [
        runstate.farm.methane_history[index] - runstate.farm.methane_history[index - 1]
        for index in range(1, len(runstate.farm.methane_history))
    ]
    if not increments:
        return [RATING_FIRST_MESSAGE]
    lines = []
    if gains:
        index, gain = max(gains, key=lambda pair: pair[1])
        lines.append(f"Biggest single round: round {index}, {gain:+.0f} funds.")
    drops = [(i + 2, increments[i] - increments[i + 1]) for i in range(len(increments) - 1)]
    drops = [pair for pair in drops if pair[1] > 1e-9]
    if drops:
        round_number, drop = max(drops, key=lambda pair: pair[1])
        lines.append(f"Best methane cut in one round: round {round_number}, {drop:.1f} less than the round before.")
    else:
        lines.append("Best methane cut in one round: none yet. Invest in decoupling to bend the curve.")
    flock = f" plus a flock of {runstate.farm.poultry_size}" if runstate.farm.poultry_size else ""
    lines.append(
        f"Herd peaked at {runstate.farm.herd_size} animals{flock}; longest perfect-round streak {runstate.farm.best_perfect_streak}."
    )
    return lines


def highlights_html():
    items = "".join(f"<li>{line}</li>" for line in highlights_lines())
    return f'<div class="highlights-reel"><p class="meter-label">Highlights</p><ul>{items}</ul></div>'


# F-13: funds per methane saved, for the lever list.
EFFICIENCY_NONE = "No methane saved at your current herd."


def lever_efficiency_message(key, cost):
    saved = runstate.farm.methane_saved_by(key)
    if saved <= 1e-9:
        return EFFICIENCY_NONE
    return f"Saves {saved:.2f} methane/round: about {cost / saved:.1f} funds per methane saved."


def _lever_cost(key):
    if key in DECOUPLING_MEASURES:
        return runstate.farm.decoupling_cost(key)
    if key == "pivot":
        return PLANT_PIVOT_COST
    return POULTRY_MEASURES[key]["cost"]


# F-24: headroom under the regional cap.
def cap_headroom_message():
    if not runstate.farm.regional_cap_enabled:
        return ""
    headroom = runstate.farm.cap_headroom()
    rounds = runstate.farm.rounds_until_cap()
    if rounds == 0:
        tail = "The next animal is blocked. Decouple to make room."
    elif rounds is None:
        tail = "The herd is not growing, so the cap is not close."
    else:
        tail = (
            f"At your pace so far ({runstate.farm.growth_pace():.1f} animals a round) you must decouple within "
            f"{rounds} round{'s' if rounds != 1 else ''}."
        )
    return f"Headroom: {headroom:.1f} methane/round free under the cap. {tail}"


LEVER_HISTORY_SHOWN = 40


def lever_history_html():
    entries = [e for e in runstate.farm.lever_log if runstate.lever_history_filter in ("all", e[1])]
    if not entries:
        return "<li>Nothing bought yet.</li>"
    shown = entries[::-1][:LEVER_HISTORY_SHOWN]
    rows = "".join(
        f"<li>Round {r}: bought {LEVER_LABELS.get(k, k)} (-{c:g})</li>" for r, k, c in shown
    )
    if len(entries) > len(shown):
        rows += f"<li>and {len(entries) - len(shown)} earlier</li>"
    return rows


def on_lever_history_filter(event=None):
    value = getattr(document.getElementById("lever-history-filter"), "value", "all")
    runstate.lever_history_filter = value if value == "all" or value in LEVER_LABELS else "all"
    render_progress_extras()


def render_progress_extras():
    """Everything the new collector and progress features draw. Runs from render()."""
    document.getElementById("rating-display").innerText = rating_message()
    streak = document.getElementById("streak-display")
    streak.innerText = streak_message()
    streak.hidden = runstate.farm.round_number <= 1
    document.getElementById("collection-summary").innerText = collection_summary_message()
    document.getElementById("breed-shelf-grid").innerHTML = breed_shelf_html()
    document.getElementById("combo-book-list").innerHTML = combo_book_html()
    document.getElementById("lever-history-list").innerHTML = lever_history_html()
    cap_text = cap_headroom_message()
    meter = document.getElementById("cap-headroom-meter")
    meter.hidden = not cap_text
    document.getElementById("cap-headroom-display").innerText = cap_text
    document.getElementById("cap-headroom-bar").style.width = (
        f"{min(1.0, runstate.farm.methane_this_round() / REGIONAL_CAP) * 100:.0f}%"
    )
    for key in ("feed", "caps", "capture", "pivot", "litter", "biofilter"):
        element = document.getElementById(f"{key}-efficiency")
        element.innerText = lever_efficiency_message(key, _lever_cost(key))
