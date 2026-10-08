"""Continuum -- K-17: the rewind token.

A limited, earned way to unwind the last season. It is meant to be a real decision, not an
undo button:

* **Tokens are earned, lifetime and scarce.** One for every five achievements earned (across
  every settlement you have played), plus one or two from Dynasty perks. A token that is used
  is gone for good (`ui["rewind"]["used"]` is carried from settlement to settlement).
* **It costs something valuable.** Besides the token, rewinding takes a quarter of the
  knowledge you were holding (at least 2, never more than you have): the research you would
  have studied with it.
* **One season, once.** Only the most recent season can be unwound, and only before anything
  else has changed the world (an era transition, loading a save, founding a new settlement,
  starting a challenge run). Because the snapshot is taken in memory just before a season
  runs, anything you did after that season is undone too, and a reload forgets it.
* **It rests where comparability matters.** Not available during a challenge run (the daily
  challenge or a scenario-editor code) or a consulting case, so their scores stay comparable.

Pure functions only: `game.py` keeps the snapshot and does the rendering.
"""

import copy
import math

import dynasty

KEY = "rewind"
ACHIEVEMENTS_PER_TOKEN = 5
KNOWLEDGE_FRACTION = 0.25
KNOWLEDGE_MIN = 2.0
MAX_USED = 10**5

# Keys of the saved `ui` that are about the player, not the settlement's moment in time: a
# rewind must never roll these back.
_KEEP_KEYS = ("earned_before", "rewind", dynasty.KEY)


def clean(raw):
    """{'used': n}, validated."""
    used = 0
    if isinstance(raw, dict):
        value = raw.get("used")
        if not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value):
            used = min(max(int(value), 0), MAX_USED)
    return {"used": used}


def get(ui):
    return clean(ui.get(KEY)) if isinstance(ui, dict) else clean(None)


def put(ui, record):
    record = clean(record)
    if record["used"] == 0:
        ui.pop(KEY, None)
    else:
        ui[KEY] = record
    return record


def earned_tokens(achievement_count, perk_tokens=0):
    count = achievement_count if isinstance(achievement_count, int) and not isinstance(achievement_count, bool) else 0
    return max(0, count) // ACHIEVEMENTS_PER_TOKEN + max(0, int(perk_tokens))


def tokens_left(ui, achievement_count, perk_tokens=0):
    return max(0, earned_tokens(achievement_count, perk_tokens) - get(ui)["used"])


def knowledge_cost(knowledge):
    """How much knowledge a rewind takes from a store of `knowledge`."""
    if isinstance(knowledge, bool) or not isinstance(knowledge, (int, float)) or not math.isfinite(knowledge):
        return 0.0
    knowledge = max(0.0, float(knowledge))
    return min(knowledge, max(KNOWLEDGE_MIN, knowledge * KNOWLEDGE_FRACTION))


def capture(campaign):
    """An in-memory copy of the campaign just before a season runs (or None when it is not safe
    to rewind to, i.e. during a Look Back)."""
    if campaign.revisiting is not None:
        return None
    return {"season": campaign.state.season, "era": campaign.state.era, "data": copy.deepcopy(campaign.to_dict())}


def refusal(snapshot, campaign, tokens, resting):
    """Why a rewind cannot happen right now, or '' when it can."""
    if resting:
        return "Rewinding rests during a challenge run or consulting case, so their scores stay comparable."
    if campaign.revisiting is not None:
        return "Return to the present before rewinding."
    if tokens <= 0:
        return "No rewind tokens left. They come from achievements (one for every five) and Dynasty perks."
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("data"), dict):
        return "Nothing to rewind: play a season first. Only the most recent season can be unwound."
    state = campaign.state
    if snapshot.get("era") != state.era or snapshot.get("season") != state.season - 1:
        return "Nothing to rewind: only the most recent season can be unwound, and not across an era change."
    return ""


def preview(snapshot, campaign, tokens, resting):
    """The panel line for the rewind button: what it would do or why it cannot."""
    reason = refusal(snapshot, campaign, tokens, resting)
    if reason:
        return reason
    held = snapshot["data"].get("current_state", {}).get("city", {}).get("resources", {}).get("knowledge", 0.0)
    cost = knowledge_cost(held)
    return (
        f"Unwind season {campaign.state.season - 1} and put the settlement back as it stood before it. "
        f"Costs 1 token and {cost:.1f} knowledge."
    )


def apply(campaign, snapshot):
    """Restores `snapshot` into `campaign` in place. Returns (ok, knowledge_cost).

    The player-level records (the Dynasty, the tokens already used, the achievements carried
    over) are kept from the present; the settlement's own banking progress is kept too, so
    unwinding can never be used to bank the same points twice. The caller has already checked
    `refusal()`.
    """
    present_ui = copy.deepcopy(campaign.ui)
    present_run = dynasty.get_run(present_ui)
    if not campaign.load_dict(copy.deepcopy(snapshot["data"])):
        return False, 0.0
    ui = campaign.ui
    for key in _KEEP_KEYS:
        if key in present_ui:
            ui[key] = present_ui[key]
        else:
            ui.pop(key, None)
    restored_run = dynasty.get_run(ui)
    restored_run["banked"] = max(restored_run["banked"], present_run["banked"])
    restored_run["counted"] = restored_run["counted"] or present_run["counted"]
    restored_run["failed"] = restored_run["failed"] or present_run["failed"]
    dynasty.put_run(ui, restored_run)
    knowledge = campaign.state.resources.get("knowledge", 0.0)
    cost = knowledge_cost(knowledge)
    campaign.state.resources["knowledge"] = knowledge - cost
    record = get(ui)
    record["used"] += 1
    put(ui, record)
    return True, cost
