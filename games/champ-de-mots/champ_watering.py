"""The one watering rule (water_plot: the first correct answer for a plot each day waters it, a later one nudges it), today's
tally, and the coins and plot skins that watering earns.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

from champ_model import state
from champ_util import _element


REVIEW_NUDGE_DAYS = 1


def nudge_review_correct(plot, day):
    """A nudge is the small, second kind of credit a correct answer can give:
    it pushes the interval a little further out and records that the plot was
    seen today (so a save doesn't silently drop the nudge -- see get_state()'s
    "touched" rule), but never touches `correct_streak`, `ease_factor` or
    `stage`. See water_plot() for when an answer is a watering and when it is
    only a nudge."""
    plot.interval_days = max(1, plot.interval_days) + REVIEW_NUDGE_DAYS
    plot.next_due = day + plot.interval_days
    plot.last_reviewed = day


# ---------------------------------------------------------------------------
# Watering versus nudging (the single rule behind every plot-linked activity)
# ---------------------------------------------------------------------------
# WATER = a full SRS review of the plot: the interval ladder moves up one rung
# (1 day, 3 days, then interval x ease), the ease factor and the correct
# streak go up, and the plot may climb a visible growth stage.
# NUDGE = only the next review date moves a little (one day later): no growth
# stage, no streak, no ease change.
# Until 2026-10-08 only watering a plot on the farm (and the first correct
# Review or proficiency answer for a plot each day) was a watering; the arcade
# games could only nudge a plot that had already been watered. Now the FIRST
# correct answer for a plot on an in-game day, from ANY plot-linked activity
# (the farm, Review and every review-style mode, the proficiency tests and
# every arcade minigame), is a real watering, so a never-watered plot can be
# watered by a game and nothing is locked behind "Water the next plot". A later
# correct answer for the same plot the same day is a nudge (at most one nudge
# per plot per day, so a fast game cannot pile up days). A wrong answer in any
# of these activities changes nothing, and a stage never goes down. (Watering a
# plot on the farm keeps its older rule that a wrong answer there reschedules
# the plot for tomorrow, as section 6 of the design doc always said.)
WATER_FULL = "full"
WATER_NUDGE = "nudge"

# Plots watered / nudged on the current in-game day, by any activity. Session
# state only (it is recomputed from nothing after a reload, which is harmless:
# the saved `last_watered` day is what actually stops a double watering).
water_today = {"day": -1, "watered": set(), "nudged": set()}


def _water_today_tally():
    if water_today["day"] != state.current_day:
        water_today["day"] = state.current_day
        water_today["watered"] = set()
        water_today["nudged"] = set()
    return water_today


def water_today_text():
    tally = _water_today_tally()
    watered, nudged = len(tally["watered"]), len(tally["nudged"])
    if not watered and not nudged:
        return "Nothing watered yet today."
    parts = []
    if watered:
        parts.append(f"watered {watered} plot{'s' if watered != 1 else ''}")
    if nudged:
        parts.append(f"nudged {nudged}")
    return "Today: " + ", ".join(parts) + "."


def water_result_text(kind, plot_for_note=None):
    """One plain sentence saying what a correct answer just did to its plot."""
    if kind == WATER_FULL:
        suffix = f" Stage: {plot_for_note.stage.capitalize()}." if plot_for_note is not None else ""
        coin = f" +{COINS_PER_WATERING} coin."
        return "Watered: this plot's schedule and growth were updated." + suffix + coin
    if kind == WATER_NUDGE:
        return "Nudged: this plot was already watered today, so its next review just moved a day later."
    return "Already watered and nudged today, so nothing more changes for this plot."


# ---------------------------------------------------------------------------
# Farm shop: coins and plot skins (TODO L-1, the part the owner said yes to on
# 2026-10-08: coins earned from watering that unlock cosmetic skins)
# ---------------------------------------------------------------------------
# One coin source, spelled out in the shop panel: a FULL watering (the first
# correct answer for a plot each in-game day, from any plot-linked activity).
# A nudge, a wrong answer and every hand-written activity earn nothing, so the
# coin counter is exactly "plots watered, ever". Coins never touch the
# scheduler, and a skin only changes how the plot cells are framed: the stage
# sprite, its colour and every state cue (due, weeds, golden, stubborn) stay
# as they were. Saved as "coins" only once something has been earned.
COINS_PER_WATERING = 1
PLOT_SKINS = (
    ("clay", "Terracotta pots", 15, "Round clay pots around every plot."),
    ("stone", "Stone tiles", 30, "Square slabs of grey stone."),
    ("crate", "Wooden crates", 45, "Brown wooden frames."),
    ("lantern", "Lantern glow", 60, "A warm, lamp-lit edge."),
    ("hedge", "Berry hedge", 80, "A purple hedge border."),
    ("gilt", "Gilded frames", 120, "Gold frames with a pale inner ring."),
)
SKIN_IDS = {skin[0] for skin in PLOT_SKINS}
coins_state = {"earned": 0, "spent": 0, "owned": [], "equipped": ""}


shop_proxies = []
COIN_SOURCE_TEXT = (
    "Where coins come from: one coin for every full watering, which is the first correct answer for a plot "
    "each in-game day (watering it on the farm, Review, a proficiency test or any minigame). Nudges, wrong "
    "answers and the hand-written activities earn nothing. Coins never change how a plot is scheduled, and "
    "skins are cosmetic only: they frame the plots differently and nothing else."
)


def coin_balance():
    return max(0, coins_state["earned"] - coins_state["spent"])


def coins_text():
    balance = coin_balance()
    return f"🪙 {balance} coin{'s' if balance != 1 else ''}"


def coins_earned_today():
    return len(_water_today_tally()["watered"]) * COINS_PER_WATERING


def skin_info(skin_id):
    for skin in PLOT_SKINS:
        if skin[0] == skin_id:
            return skin
    return None


def earn_coins(amount=COINS_PER_WATERING):
    coins_state["earned"] += int(amount)


def buy_skin(skin_id):
    """"bought", "owned", "poor" (not enough coins) or "unknown"."""
    skin = skin_info(skin_id)
    if skin is None:
        return "unknown"
    if skin_id in coins_state["owned"]:
        return "owned"
    if coin_balance() < skin[2]:
        return "poor"
    coins_state["spent"] += skin[2]
    coins_state["owned"].append(skin_id)
    coins_state["equipped"] = skin_id
    return "bought"


def equip_skin(skin_id):
    """Use an owned skin, or "" for the plain plots. False when not owned."""
    if skin_id and skin_id not in coins_state["owned"]:
        return False
    coins_state["equipped"] = skin_id
    return True


def apply_skin():
    _element("farm").setAttribute("data-skin", coins_state["equipped"] or "none")


def _validated_coins(raw):
    """A saved "coins" record, or a blank one for anything that is not valid:
    non-negative whole numbers, only known skins, spent never above earned,
    the equipped skin one that is owned."""
    blank = {"earned": 0, "spent": 0, "owned": [], "equipped": ""}
    if not isinstance(raw, dict):
        return blank

    def whole(value):
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0

    earned = whole(raw.get("earned"))
    spent = min(whole(raw.get("spent")), earned)
    owned = []
    for skin_id in raw.get("owned") if isinstance(raw.get("owned"), list) else []:
        if isinstance(skin_id, str) and skin_id in SKIN_IDS and skin_id not in owned:
            owned.append(skin_id)
    equipped = raw.get("equipped")
    if not isinstance(equipped, str) or equipped not in owned:
        equipped = ""
    return {"earned": earned, "spent": spent, "owned": owned, "equipped": equipped}


def can_water_now(plot):
    """True while the plot has not had its full watering on the current day."""
    return plot.last_watered != state.current_day


def water_plot(plot, combo=0, confidence=None):
    """A CORRECT answer on a real plot, from any plot-linked activity.
    Returns WATER_FULL for the day's first one, WATER_NUDGE for a later one
    (once per plot per day), None when the plot has already been watered and
    nudged today (nothing more to add). `combo` and `confidence` only matter
    for the farm's own practice panel and feed the same scheduler arguments
    they always did."""
    if plot is None:
        return None
    day = state.current_day
    tally = _water_today_tally()
    plot.in_weeds = False
    plot.fail_run = 0
    if plot.last_watered != day:
        state.review(plot.plot_id, True, combo=combo, confidence=confidence)
        plot.last_watered = day
        plot.nudged_day = None
        tally["watered"].add(plot.plot_id)
        earn_coins()
        return WATER_FULL
    if plot.nudged_day != day:
        nudge_review_correct(plot, day)
        plot.nudged_day = day
        tally["nudged"].add(plot.plot_id)
        return WATER_NUDGE
    return None


def water_from_review(plot):
    """Kept for the Review code and its tests: True when the answer was the
    day's full watering, False when it was only a nudge (or nothing)."""
    return water_plot(plot) == WATER_FULL
