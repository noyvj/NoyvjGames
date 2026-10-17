"""Ranch Rules (F-1): setting, resetting, remembering and describing the four custom rules.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

import json

from js import document

import herd_runstate as runstate
from herd_rules import RULES_STORAGE_KEY, RULE_SPECS
from herd_util import _read_local_storage_item, _write_local_storage_item
from herd_model import clean_rule_value, rules_are_custom, rules_unranked
from herd_loadouts import farm_is_pristine


def _store_rules():
    """Remembers the rules in this browser so a new farm starts on the same ones (F-1)."""
    _write_local_storage_item(RULES_STORAGE_KEY, json.dumps({n: v for n, v in runstate.ranch_rules.items()}))


def _load_stored_rules():
    raw = _read_local_storage_item(RULES_STORAGE_KEY)
    if not raw:
        return
    try:
        saved = json.loads(raw)
    except (ValueError, TypeError):
        return
    if not isinstance(saved, dict):
        return
    for name in RULE_SPECS:
        cleaned = clean_rule_value(name, saved.get(name))
        if cleaned is not None:
            runstate.ranch_rules[name] = cleaned


# ===========================================================================
# Round-6 batch (planning/TODO.md "GF + F. Herd").
# ===========================================================================

# ---- F-1 Ranch Rules ----------------------------------------------------------------------
def rule_id(name):
    return "rule-" + name.replace("_", "-")


def format_rule(name, value):
    spec = RULE_SPECS[name]
    number = f"{value:g}" if abs(value - round(value)) > 1e-9 else f"{int(round(value))}"
    return f"{number}{spec['unit']}"


def set_rule(name, value):
    """Changes one rule. Returns True when the value really changed. Pace and penalty rules apply at
    once; a new starting purse applies right away only to a farm that has not started."""
    cleaned = clean_rule_value(name, value)
    if runstate.sandbox_active or cleaned is None or abs(cleaned - runstate.ranch_rules[name]) < 1e-9:  # GF-24: rules are locked in the sandbox
        return False
    old = runstate.ranch_rules[name]
    runstate.ranch_rules[name] = cleaned
    if name == "starting_funds" and farm_is_pristine():
        delta = cleaned - old
        runstate.farm.funds += delta
        runstate.farm.counterfactual_funds += delta
        if runstate.farm.funds_history and runstate.farm.funds_history[0] is not None:
            runstate.farm.funds_history[0] += delta
    if rules_are_custom():
        runstate.farm.custom_rules_used = True
    elif farm_is_pristine():
        runstate.farm.custom_rules_used = False
    _store_rules()
    return True


def reset_rules():
    changed = False
    for name, spec in RULE_SPECS.items():
        changed = set_rule(name, spec["default"]) or changed
    return changed


def _load_rules_from_save(data):
    """A save brings its own rules (standard ones when it has none); values are clamped and snapped."""
    saved = data.get("ranch_rules")
    for name, spec in RULE_SPECS.items():
        runstate.ranch_rules[name] = spec["default"]
        if isinstance(saved, dict):
            cleaned = clean_rule_value(name, saved.get(name))
            if cleaned is not None:
                runstate.ranch_rules[name] = cleaned
    _store_rules()


def rules_summary_message():
    custom = [f"{RULE_SPECS[n]['label']} {format_rule(n, v)}" for n, v in runstate.ranch_rules.items()
              if abs(v - RULE_SPECS[n]["default"]) > 1e-9]
    if custom:
        return (
            "Custom rules: " + ", ".join(custom) + ". This run is unranked: it stays off the community "
            "leaderboard and out of the other-farms comparison."
        )
    if runstate.farm.custom_rules_used:
        return "The rules are standard again, but this run already used custom rules, so it stays unranked."
    if runstate.farm.loadout != "standard":
        return "Standard rules, but a starting loadout makes this run unranked."
    return "Standard rules: this run can be ranked."


def rules_badge_message():
    if not rules_unranked():
        return ""
    if runstate.farm.custom_rules_used or rules_are_custom():
        return "Custom ranch rules: this run is unranked."
    return "Starting loadout: this run is unranked."


def rules_start_note():
    if farm_is_pristine():
        return "A new starting purse applies right now, because the farm has not started."
    return "A new starting purse applies to the next new farm or handover; the other rules apply at once."


def render_rules():
    for name, value in runstate.ranch_rules.items():
        slider = document.getElementById(rule_id(name))
        slider.value = f"{value:g}"
        document.getElementById(rule_id(name) + "-value").innerText = format_rule(name, value)
    document.getElementById("rules-summary").innerText = rules_summary_message()
    document.getElementById("rules-start-note").innerText = rules_start_note()
    badge = document.getElementById("rules-badge")
    text = rules_badge_message()
    badge.innerText = text
    badge.hidden = not text
