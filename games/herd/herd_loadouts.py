"""Starting loadouts (GF-23) and the stewardship audits (GF-3), plus farm_is_pristine().
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

from js import document

import herd_runstate as runstate
from herd_rules import (
    AUDIT_LOG_MAX, AUDIT_PERKS, AUDIT_PERK_REPEAT_FUNDS, AUDIT_TRUST_ROUNDS, AUDIT_WARNING_ROUNDS,
)
from herd_util import _is_finite_number, _safe_int
from herd_model import audit_coupling_target, audit_welfare_target
from herd_achievements import achievement_ids_earned
from herd_barns import _achievement_label


def farm_is_pristine():
    """No round played, nothing bought: the only moment a changed starting purse can still apply."""
    granted = LOADOUTS[runstate.farm.loadout] if runstate.farm.loadout in LOADOUTS else LOADOUTS["standard"]  # GF-23: a loadout's gifts are not "play"
    return (
        runstate.farm.round_number == 1 and runstate.farm.herd_size == granted.get("herd", 0) and not runstate.farm.lever_log
        and runstate.farm.poultry_size == granted.get("poultry", 0) and runstate.farm.plant_pivot_investment == 0
    )


# ---- GF-23 starting loadouts -------------------------------------------------------------------
# Four ways to open a farm, each unlocked by an achievement and kept for good. A loadout bends the
# opening funds and levers (every one is a trade, not a free gift) and applies to an untouched farm
# right away and to every later generation. A run with a loadout is unranked, like custom ranch rules.
# Deltas are written once and applied or taken back symmetrically, so changing the choice on an
# untouched farm never leaves anything behind (legacy perks already on the farm are not touched).
LOADOUTS = {
    "standard": {"label": "Standard start", "unlock": None, "herd": 0, "funds": 0, "cf_funds": 0, "levers": {}, "poultry": 0,
                 "methane": 0.0, "blurb": "The farm as it always began."},
    "big_herd": {"label": "Big Herd", "unlock": "major_operation", "herd": 4, "funds": -90, "cf_funds": -90, "levers": {},
                 "poultry": 0, "methane": 0.0, "blurb": "Four animals already in the paddock for 90 less funds (their emissions start at once)."},
    "lean_green": {"label": "Lean Green", "unlock": "all_three_measures", "herd": 0, "funds": -50, "cf_funds": 0,
                   "levers": {"feed": 1, "caps": 1, "capture": 1}, "poultry": 0, "methane": 0.0,
                   "blurb": "One of each decoupling measure fitted on day one for 50 funds, but no herd yet."},
    "poultry_start": {"label": "Poultry Start", "unlock": "sustainably_certified", "herd": 0, "funds": -25, "cf_funds": -25,
                      "levers": {}, "poultry": 2, "methane": 0.0,
                      "blurb": "The poultry flock is open from round 1 with two birds already in, for 25 funds."},
    "cash_rich": {"label": "Cash Rich", "unlock": "score_400", "herd": 0, "funds": 150, "cf_funds": 150, "levers": {},
                  "poultry": 0, "methane": 12.0, "blurb": "150 more funds to start, but 12 methane already on the books from old operations."},
}
LOADOUT_IDS = list(LOADOUTS)


def loadout_is_unlocked(loadout_id):
    return loadout_id == "standard" or loadout_id in runstate.loadouts_unlocked


def _shift_loadout(target, loadout_id, sign):
    """Applies (+1) or takes back (-1) one loadout's changes on a farm object."""
    spec = LOADOUTS[loadout_id]
    target.herd_size += sign * spec["herd"]
    target.funds += sign * spec["funds"]
    target.counterfactual_funds += sign * spec["cf_funds"]
    for measure, units in spec["levers"].items():
        target.decoupling_investment[measure] += sign * units
    target.poultry_size += sign * spec["poultry"]
    target.methane += sign * spec["methane"]
    target.counterfactual_methane += sign * spec["methane"]
    if target.methane_history:
        target.methane_history[-1] += sign * spec["methane"]
    if target.funds_history and target.funds_history[-1] is not None:
        target.funds_history[-1] += sign * spec["funds"]


def loadout_can_apply_now():
    """True while the farm is still the one the loadout opened with (round 1, nothing bought)."""
    return farm_is_pristine()


def _sync_loadouts():
    new = []
    earned = None
    for loadout_id, spec in LOADOUTS.items():
        if spec["unlock"] is None or loadout_id in runstate.loadouts_unlocked:
            continue
        if earned is None:
            earned = set(achievement_ids_earned())
        if spec["unlock"] in earned:
            runstate.loadouts_unlocked.append(loadout_id)
            new.append(f"new starting loadout {spec['label']}")
    return new


def _load_loadouts(data):
    raw = data.get("loadouts_unlocked")
    runstate.loadouts_unlocked = []
    if isinstance(raw, list):
        for value in raw:
            if isinstance(value, str) and value in LOADOUTS and value != "standard" and value not in runstate.loadouts_unlocked:
                runstate.loadouts_unlocked.append(value)
    chosen = data.get("loadout_choice")
    runstate.loadout_choice = chosen if isinstance(chosen, str) and chosen in LOADOUTS and loadout_is_unlocked(chosen) else "standard"
    own = data.get("loadout")
    runstate.farm.loadout = own if isinstance(own, str) and own in LOADOUTS else "standard"


def choose_loadout(loadout_id):
    """Picks the starting loadout. On an untouched farm it applies at once (the old one is taken back);
    otherwise it waits for the next generation. Returns "applied", "saved" or None when refused."""
    if loadout_id not in LOADOUTS or not loadout_is_unlocked(loadout_id):
        return None
    runstate.loadout_choice = loadout_id
    if loadout_can_apply_now():
        if runstate.farm.loadout != loadout_id:
            _shift_loadout(runstate.farm, runstate.farm.loadout, -1)
            _shift_loadout(runstate.farm, loadout_id, +1)
            runstate.farm.loadout = loadout_id
        return "applied"
    return "saved"


def loadout_message():
    spec = LOADOUTS[runstate.loadout_choice]
    here = LOADOUTS[runstate.farm.loadout]["label"]
    if runstate.farm.loadout == runstate.loadout_choice:
        where = f"This farm began with: {here}."
    else:
        where = f"This farm began with: {here}. {spec['label']} opens your next generation."
    return f"{spec['blurb']} {where}"


def loadout_list_html():
    rows = []
    for loadout_id, spec in LOADOUTS.items():
        if loadout_is_unlocked(loadout_id):
            note = "unlocked" if spec["unlock"] else "always available"
        else:
            note = f"locked: earn {_achievement_label(spec['unlock'])}"
        rows.append(f'<li><strong>{spec["label"]}</strong>: {spec["blurb"]} ({note})</li>')
    return "".join(rows)


def render_loadouts():
    select = document.getElementById("loadout-select")
    options = "".join(
        f'<option value="{loadout_id}"{" selected" if loadout_id == runstate.loadout_choice else ""}{"" if loadout_is_unlocked(loadout_id) else " disabled"}>'
        f'{spec["label"]}{"" if loadout_is_unlocked(loadout_id) else " (locked)"}</option>'
        for loadout_id, spec in LOADOUTS.items()
    )
    if options != runstate._loadout_options_key:  # rebuild only when something unlocked, so an open list is not disturbed
        select.innerHTML = options
        runstate._loadout_options_key = options
    select.value = runstate.loadout_choice
    document.getElementById("loadout-summary").innerText = (
        f"Starting loadouts unlocked: {1 + len(runstate.loadouts_unlocked)} of {len(LOADOUTS)}. A loadout makes the run unranked."
    )
    document.getElementById("loadout-note").innerText = loadout_message()
    document.getElementById("loadout-list").innerHTML = loadout_list_html()
    document.getElementById("loadout-status").innerText = runstate.loadout_status_text


# ---- GF-3 regulator audits: the panel and messages ---------------------------------------------
def _load_audits(data):
    runstate.farm.audits_done = _safe_int(data.get("audits_done"), 0)
    runstate.farm.audit_log = []
    log = data.get("audit_log")
    if runstate.farm.audits_done > 0 and isinstance(log, list):
        for entry in log[-AUDIT_LOG_MAX:]:
            if (
                isinstance(entry, (list, tuple)) and len(entry) == 3 and all(_is_finite_number(v) for v in entry)
                and entry[2] in (0, 1) and entry[0] >= 1 and entry[1] >= 1
            ):
                runstate.farm.audit_log.append([int(entry[0]), int(entry[1]), int(entry[2])])
    perks = data.get("audit_perks")
    runstate.farm.audit_perks = []
    if isinstance(perks, list):
        known = [entry["id"] for entry in AUDIT_PERKS]
        for perk in perks:
            if isinstance(perk, str) and perk in known and perk not in runstate.farm.audit_perks:
                runstate.farm.audit_perks.append(perk)
    runstate.farm.trust_rounds_left = min(AUDIT_TRUST_ROUNDS, _safe_int(data.get("trust_rounds_left"), 0))
    runstate.farm.just_audit = None


def audit_perk_label(perk_id):
    for entry in AUDIT_PERKS:
        if entry["id"] == perk_id:
            return entry["label"]
    return perk_id


def audits_passed():
    return sum(1 for _n, _r, ok in runstate.farm.audit_log if ok)


def audit_result_message(result):
    number, passed, fine, perk = result
    if passed:
        reward = (
            f"You earned the perk {audit_perk_label(perk)}." if perk else f"You earned {AUDIT_PERK_REPEAT_FUNDS} funds (every perk is already yours)."
        )
        return f"Regulator audit {number}: passed. {reward}"
    return (
        f"Regulator audit {number}: not passed. A fine of {fine:g} funds and market trust is shaken "
        f"for {runstate.farm.trust_rounds_left} rounds."
    )


def audit_report_line():
    perks = ", ".join(audit_perk_label(p) for p in runstate.farm.audit_perks) or "none yet"
    return f"Regulator audits: {audits_passed()} passed of {runstate.farm.audits_done}. Perks: {perks}."


def audit_target_lines():
    number = runstate.farm.audits_done + 1
    ratio_target, welfare_target = audit_coupling_target(number), audit_welfare_target(number)
    ratio_ok = runstate.farm.coupling_ratio() <= ratio_target + 1e-9
    welfare_ok = runstate.farm.welfare() >= welfare_target - 1e-9
    return (
        f"Coupling ratio {ratio_target:.2f} or lower: now {runstate.farm.coupling_ratio():.2f} ({'met' if ratio_ok else 'not met yet'}).",
        f"Welfare {welfare_target:.0f} or more: now {runstate.farm.welfare():.0f} ({'met' if welfare_ok else 'not met yet'}).",
    )


def audit_headline():
    number = runstate.farm.audits_done + 1
    when = runstate.farm.next_audit_round()
    left = when - runstate.farm.round_number
    if left == 0:
        return f"Audit {number} is at the end of this round."
    plural = "s" if left != 1 else ""
    text = f"Audit {number} is at the end of round {when} ({left} round{plural} from now)."
    if left <= AUDIT_WARNING_ROUNDS:
        text = "Warning: " + text[0].lower() + text[1:]
    return text


def render_audit():
    left = runstate.farm.next_audit_round() - runstate.farm.round_number
    warning = left <= AUDIT_WARNING_ROUNDS
    panel = document.getElementById("audit-panel")
    if warning:
        panel.classList.add("audit-warning")
    else:
        panel.classList.remove("audit-warning")
    document.getElementById("audit-headline").innerText = audit_headline()
    coupling_line, welfare_line = audit_target_lines()
    document.getElementById("audit-target-coupling").innerText = coupling_line
    document.getElementById("audit-target-welfare").innerText = welfare_line
    document.getElementById("audit-reward").innerText = (
        "Pass: a permanent perk for this farm. Fail: a fine of one round's income and a few rounds of shaken market trust."
    )
    perks = ", ".join(audit_perk_label(p) for p in runstate.farm.audit_perks)
    record = f"Audits passed: {audits_passed()} of {runstate.farm.audits_done}." if runstate.farm.audits_done else "No audit yet."
    if perks:
        record += f" Perks: {perks}."
    if runstate.farm.trust_rounds_left > 0:
        record += f" Market trust is shaken for {runstate.farm.trust_rounds_left} more rounds."
    document.getElementById("audit-record").innerText = record
