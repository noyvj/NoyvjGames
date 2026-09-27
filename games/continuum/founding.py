"""Continuum -- O-5/O-7/O-8: founding a new settlement.

Continuum has no forced end state, so "starting over" is the player's call.
This module holds the pure (no DOM, no storage) half of that feature:

* `found_new()` -- resets the live campaign IN PLACE to a fresh Tribal start
  (the same restore-into-the-existing-objects discipline `save.Campaign`
  uses, so `game.py`'s module-level `state`/`tree`/`chronicle` aliases stay
  valid). It never archives anything itself: `game.py` files the departing
  settlement in the archive FIRST and only calls this once that succeeded,
  so a settlement that has not been archived is never thrown away.
* The founder's legacy (O-7) -- ONE small named bonus, derived from the most
  recent archived settlement's furthest era, delivered with the new
  settlement's first season. It rides in `campaign.ui["legacy"]`, validated
  on every read like every other `ui` entry.
* The lifetime "achievements earned before" list, so the badges a player
  has already earned are not lost the moment the settlement they were earned
  in is left behind (achievements are otherwise derived from the live
  campaign, "derive, don't track").
* The Refuge Start unlock rule (O-8).

Balance rule for the legacy: every bonus is a one-off, single-resource gift
no bigger than about one turn of a small opening's income, never an ongoing
effect, and never stacked: a new settlement carries exactly the legacy of
the settlement just before it.
"""

import consulting
import save
import sim

LEGACY_KEY = "legacy"
EARNED_KEY = "earned_before"
EARNED_MAX = 200

# Ordered by the era the previous settlement reached. `eras` are the
# `sim.ERA_ORDER` ids that map to this legacy. Every entry grants exactly
# one resource, one time. The amounts are deliberately tiny: one early
# research node costs 4 knowledge, one shelter costs 12 materials, a
# six-person opening eats 12 food a season, and a tool wears out at 8% a
# season -- so none of these outweighs a single season's play.
LEGACIES = {
    "seed_stock": {
        "label": "Seed Stock",
        "eras": ("tribal", "agrarian"),
        "resource": "food",
        "amount": 6.0,
        "blurb": "Dried stores and seed grain carried over from the last settlement.",
    },
    "builders_plans": {
        "label": "Master Builders' Plans",
        "eras": ("classical", "medieval"),
        "resource": "materials",
        "amount": 8.0,
        "blurb": "Marked-out plans and cut timber the last settlement's builders left behind.",
    },
    "recorded_lessons": {
        "label": "Recorded Lessons",
        "eras": ("industrial", "digital"),
        "resource": "knowledge",
        "amount": 4.0,
        "blurb": "Written-down lessons from the last settlement, enough to start one discovery.",
    },
    "salvage_kit": {
        "label": "Salvaged Tools",
        "eras": ("space", "relay"),
        "resource": "tools",
        "amount": 1.0,
        "blurb": "A well-made tool that outlived the last settlement.",
    },
}
LEGACY_LABEL_UNIT = {"food": "food", "materials": "materials", "knowledge": "knowledge", "tools": "tool"}


def legacy_id_for_era(era):
    """The legacy earned by reaching `era`, or None for an unknown era."""
    for legacy_id, legacy in LEGACIES.items():
        if era in legacy["eras"]:
            return legacy_id
    return None


def make_legacy(record):
    """A fresh, not-yet-delivered legacy entry from one archive record.

    `record` is an `archive.clean_record()` dict; its `era` is the furthest
    era that settlement reached, which is the "peak achievement" the
    legacy is derived from. Returns None for anything unusable.
    """
    if not isinstance(record, dict):
        return None
    era = record.get("era")
    legacy_id = legacy_id_for_era(era) if isinstance(era, str) else None
    if legacy_id is None:
        return None
    return {"id": legacy_id, "from_era": era, "applied": False}


def clean_legacy(raw):
    """Validates a saved legacy entry; None when absent or malformed."""
    if not isinstance(raw, dict):
        return None
    legacy_id = raw.get("id")
    from_era = raw.get("from_era")
    if not isinstance(legacy_id, str) or legacy_id not in LEGACIES:
        return None
    if not isinstance(from_era, str) or from_era not in LEGACIES[legacy_id]["eras"]:
        return None
    applied = raw.get("applied")
    return {"id": legacy_id, "from_era": from_era, "applied": applied is True}


def get_legacy(ui):
    """The validated legacy entry from `campaign.ui`, or None."""
    return clean_legacy(ui.get(LEGACY_KEY)) if isinstance(ui, dict) else None


def bonus_text(entry):
    """'+6 food' for a valid entry."""
    legacy = LEGACIES[entry["id"]]
    amount = legacy["amount"]
    shown = f"{amount:g}"
    return f"+{shown} {LEGACY_LABEL_UNIT[legacy['resource']]}"


def status_text(entry, consulting_active=False):
    """The one line the scenario panel shows, or '' with no legacy."""
    if entry is None:
        return ""
    legacy = LEGACIES[entry["id"]]
    origin = sim.ERA_LABEL[entry["from_era"]]
    head = f"Founder's legacy: {legacy['label']} ({bonus_text(entry)}), from a {origin}-era settlement."
    if entry["applied"]:
        return head + " Delivered with your first season."
    if consulting_active:
        return head + " Not used: a consulting case replaces the opening."
    return head + " Arrives with your first season."


def apply_legacy(campaign, consulting_active=False):
    """Delivers a pending legacy once, at the start of the opening season.

    Returns the entry that was delivered (with its `applied` flag now set),
    or None if there was nothing to deliver. A legacy is consumed either
    way after the first season starts: it never carries into a later season.
    """
    entry = get_legacy(campaign.ui)
    if entry is None or entry["applied"]:
        return None
    entry["applied"] = True
    campaign.ui[LEGACY_KEY] = entry
    if consulting_active or campaign.state.season > 1:
        return None
    legacy = LEGACIES[entry["id"]]
    resources = campaign.state.resources
    resources[legacy["resource"]] = resources[legacy["resource"]] + legacy["amount"]
    return entry


def clean_earned(raw, valid_ids):
    """The saved 'earned before' achievement ids, filtered to real ones."""
    if not isinstance(raw, list):
        return []
    valid = set(valid_ids)
    out = []
    for item in raw[:EARNED_MAX]:
        if isinstance(item, str) and item in valid and item not in out:
            out.append(item)
    return out


def earned_before(ui, valid_ids):
    return clean_earned(ui.get(EARNED_KEY), valid_ids) if isinstance(ui, dict) else []


def refuge_unlocked(earned_ids, archive_records):
    """True once any settlement, ever, has reached `sim.REFUGE_UNLOCK_ERA`.

    `earned_ids` is every achievement id currently earned (live plus carried
    over from earlier settlements); `archive_records` is the validated
    archive. Either source is enough, and both are only ever read, never
    trusted for anything but this one unlock.
    """
    unlock_index = sim.era_index(sim.REFUGE_UNLOCK_ERA)
    if "reached_space" in earned_ids or "reached_relay" in earned_ids:
        return True
    for record in archive_records:
        era = record.get("era") if isinstance(record, dict) else None
        if era in sim.ERA_ORDER and sim.era_index(era) >= unlock_index:
            return True
    return False


def is_pristine(campaign):
    """True for a settlement with nothing worth archiving: season 1, no
    research of its own, no completed eras. A consulting case that has not
    been played a season counts as untouched (its inherited research is not
    the player's)."""
    state = campaign.state
    inherited = set(consulting.inherited_for(campaign))
    own_research = [n for n in campaign.tree.researched if n not in inherited]
    return (
        campaign.revisiting is None
        and not campaign.era_snapshots
        and state.season <= 1
        and not own_research
        and campaign.furthest_era == state.era
    )


def found_new(campaign, chronicle, legacy_entry=None, earned_ids=()):
    """Resets `campaign` in place to a brand-new Tribal-era settlement.

    Never archives; the caller must already have filed the departing
    settlement (see the module docstring). `earned_ids` are the achievement
    ids the player has earned so far, kept in `ui["earned_before"]`;
    `legacy_entry` (from `make_legacy`) is the pending bonus, if any.
    Returns False, changing nothing, during a Look Back (the live state is
    then a past snapshot, not the settlement being left behind).
    """
    if campaign.revisiting is not None:
        return False
    fresh = save.Campaign()
    if not campaign.load_dict(fresh.to_dict()):
        return False
    # load_dict() keeps a live value when the save's is "absent" (None), so a
    # settlement's peak/lowest score would leak into the new one. Re-running
    # the constructor in place resets every field, saved or not, and keeps
    # the object identity game.py's `state` alias depends on.
    campaign.state.__init__()
    ui = {}
    kept = list(earned_ids)[:EARNED_MAX]
    if kept:
        ui[EARNED_KEY] = kept
    clean = clean_legacy(legacy_entry)
    if clean is not None:
        ui[LEGACY_KEY] = clean
    campaign.ui = ui
    if chronicle is not None:
        chronicle.bootstrap(campaign.state, campaign.tree, campaign.tree.effects())
    return True
