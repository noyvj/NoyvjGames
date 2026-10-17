"""The Settlement Chronicle and the Second Founding panel."""

from js import document

import aftermath_runstate as runstate
from aftermath_bonuses import founding_owned
from aftermath_pastruns import new_record_run_indexes
from aftermath_persist import (
    CHRONICLE_KINDS, CHRONICLE_MAX, FOUNDING_MAX_STARS, FOUNDING_SKILLS, FOUNDING_STAR_RESOURCES,
    SOCIETAL_MEMORY_BONUS, SOCIETAL_MEMORY_LABEL, _el, _sanitize_chronicle, run_log_history, save_meta,
)
from aftermath_rules import EVENT_LABEL, SKILLS, entry_is_flawless


# ===========================================================================
# GE-10: the Second Founding (optional prestige). Constants, the saved shape (meta["founding"]) and the
# bonus hooks are above (before _sanitize_meta and _unlocked_or_tree); this is the action and the panel.
# Strictly optional: nothing in the game asks for it, every effect is a flat number, a Founding skill can be put
# away for a full refund, and a challenge run ignores all of it (like the rest of the tree).
# ===========================================================================


def founding_ready():
    """The Second Founding opens once EVERY skill is owned and a star is still to be had."""
    return len(runstate.skill_tree.unlocked & set(SKILLS)) == len(SKILLS) and runstate.meta["founding"]["stars"] < FOUNDING_MAX_STARS


def founding_stars_text():
    stars = runstate.meta["founding"]["stars"]
    return "★" * stars + "☆" * (FOUNDING_MAX_STARS - stars) + f" {stars} of {FOUNDING_MAX_STARS} Founding stars"


def founding_status_text():
    owned = len(runstate.skill_tree.unlocked & set(SKILLS))
    stars = runstate.meta["founding"]["stars"]
    if stars >= FOUNDING_MAX_STARS:
        return f"{founding_stars_text()}: all three earned. There is nothing further to begin."
    if founding_ready():
        return f"{founding_stars_text()}. You own all {len(SKILLS)} skills, so you may begin a Second Founding whenever you like."
    return f"{founding_stars_text()}. Own all {len(SKILLS)} skills to begin one ({owned} of {len(SKILLS)} so far)."


def founding_refund_total():
    return sum(FOUNDING_SKILLS[s]["cost"] for s in founding_owned())


def founding_kept_lost_text():
    """What the confirm dialog and the panel say, in the same words: what is lost, what is kept, what is gained."""
    spent = sum(SKILLS[s]["cost"] for s in runstate.skill_tree.unlocked if s in SKILLS)
    stars = runstate.meta["founding"]["stars"] + 1
    held = founding_owned()
    lost = (f"Lost: all {len(runstate.skill_tree.unlocked & set(SKILLS))} skills you own, and the {spent} knowledge they cost "
            "is not refunded, so you buy the tree again from the start.")
    if held:
        lost += f" Any Founding skills you hold are put away for a full refund ({founding_refund_total()} knowledge)."
    kept = (f"Kept: the {runstate.skill_tree.knowledge_points + founding_refund_total()} knowledge you will have in hand, your lifetime knowledge, "
            "skill ranks, run history, achievements, settlement memory and legacy, presets, schedules and notes.")
    gained = (f"Gained: Founding star {stars} of {FOUNDING_MAX_STARS} (+{FOUNDING_STAR_RESOURCES} starting resources every run, "
              "for good) and the three Founding skills to buy, each with a strong trade-off.")
    return " ".join((lost, kept, gained))


def founding_skill_status(skill_id):
    """locked (no star yet) / owned / affordable / short."""
    if skill_id not in FOUNDING_SKILLS or runstate.meta["founding"]["stars"] < 1:
        return "locked"
    if skill_id in founding_owned():
        return "owned"
    return "affordable" if runstate.skill_tree.knowledge_points >= FOUNDING_SKILLS[skill_id]["cost"] else "short"


def buy_founding_skill(skill_id):
    if founding_skill_status(skill_id) != "affordable":
        return False
    runstate.skill_tree.knowledge_points -= FOUNDING_SKILLS[skill_id]["cost"]
    runstate.skill_tree.save()
    runstate.meta["founding"]["owned"] = [s for s in FOUNDING_SKILLS if s in founding_owned() or s == skill_id]
    save_meta()
    return True


def put_away_founding_skill(skill_id):
    """A Founding skill can be swapped any time for a full refund (they are trade-offs, so trying them is free)."""
    if skill_id not in founding_owned():
        return False
    runstate.skill_tree.knowledge_points += FOUNDING_SKILLS[skill_id]["cost"]
    runstate.skill_tree.save()
    runstate.meta["founding"]["owned"] = [s for s in FOUNDING_SKILLS if s in founding_owned() and s != skill_id]
    save_meta()
    return True


def founding_skill_text(skill_id):
    skill = FOUNDING_SKILLS[skill_id]
    state = founding_skill_status(skill_id)
    head = f"{skill['label']} (costs {skill['cost']} knowledge): {skill['gain']}. The price: {skill['price']}."
    if state == "locked":
        return head + " Locked until you have a Founding star."
    if state == "owned":
        return head + " Yours. Put it away for a full refund any time."
    if state == "short":
        return head + f" You need {skill['cost'] - runstate.skill_tree.knowledge_points} more knowledge."
    return head + " You can buy it now."


_founding_parts = {}


def build_founding_panel():
    holder = _el("founding-skills")
    if holder is None or _founding_parts:
        return
    holder.innerHTML = ""
    for skill_id in FOUNDING_SKILLS:
        item = document.createElement("li")
        item.className = "founding-skill"
        text = document.createElement("p")
        text.className = "founding-skill-text"
        buy = document.createElement("button")
        buy.className = "secondary"
        buy.setAttribute("type", "button")
        buy.setAttribute("data-action", "buy")
        buy.setAttribute("data-founding", skill_id)
        away = document.createElement("button")
        away.className = "secondary"
        away.setAttribute("type", "button")
        away.setAttribute("data-action", "away")
        away.setAttribute("data-founding", skill_id)
        item.appendChild(text)
        item.appendChild(buy)
        item.appendChild(away)
        holder.appendChild(item)
        _founding_parts[skill_id] = {"item": item, "text": text, "buy": buy, "away": away}


def render_founding():
    status = _el("founding-status")
    if status is None:
        return
    build_founding_panel()
    status.innerText = founding_status_text()
    kept = _el("founding-kept-lost")
    if kept is not None:
        kept.innerText = founding_kept_lost_text() if founding_ready() else (
            "Beginning one would cost you every skill you own (their knowledge is not refunded) and give you a permanent "
            f"Founding star, +{FOUNDING_STAR_RESOURCES} starting resources every run and three Founding skills. "
            "Everything else is kept: knowledge in hand, lifetime knowledge, ranks, run history, achievements, memory, presets and notes."
        )
    begin = _el("founding-begin-button")
    if begin is not None:
        begin.disabled = not founding_ready()
    message = _el("founding-message")
    if message is not None:
        message.innerText = runstate.founding_message_text
    for skill_id, parts in _founding_parts.items():
        state = founding_skill_status(skill_id)
        parts["text"].innerText = founding_skill_text(skill_id)
        parts["item"].setAttribute("data-state", state)
        parts["buy"].innerText = f"Buy ({FOUNDING_SKILLS[skill_id]['cost']})"
        parts["buy"].hidden = state in ("locked", "owned")
        parts["buy"].disabled = state != "affordable"
        parts["away"].innerText = f"Put away (refund {FOUNDING_SKILLS[skill_id]['cost']})"
        parts["away"].hidden = state != "owned"


# ---------------------------------------------------------------------------
# E-7: the Settlement Chronicle. A scrollable timeline across runs: the first time each event was weathered,
# the worst disaster so far (when a later run beats it), new best scores, the first Flawless Defense (all worked
# out from the run history) and the lines in meta["chronicle"] (skills adopted, points moved, a societal memory
# that formed, a curriculum lesson finished, a Second Founding). Viewable in a panel and copyable as text.
# ---------------------------------------------------------------------------
def chronicle_note(kind, text, after=None):
    """Adds one stored line (the newest CHRONICLE_MAX are kept) and saves."""
    if kind not in CHRONICLE_KINDS:
        return False
    cleaned = _sanitize_chronicle([{"after": runstate.highest_awarded_run if after is None else after, "kind": kind, "text": text}])
    if not cleaned:
        return False
    runstate.meta["chronicle"] = (runstate.meta["chronicle"] + cleaned)[-CHRONICLE_MAX:]
    save_meta()
    return True


def _chronicle_payout_notes(finished_run):
    """Called once per paid-out run (inside the same run-number guard as the knowledge payout)."""
    if runstate.memory_just_formed:
        bonus = round(SOCIETAL_MEMORY_BONUS[runstate.memory_just_formed] * 100)
        chronicle_note(
            "memory", f"The settlement will remember {SOCIETAL_MEMORY_LABEL[runstate.memory_just_formed]}: {bonus}% less damage from that kind of shock.",
            after=finished_run.run_number,
        )
    if runstate.curriculum_just_completed:
        chronicle_note("lesson", f"Curriculum lesson complete: {runstate.curriculum_just_completed['title']}.", after=finished_run.run_number)


def _chronicle_events(entry):
    return [e for e in (entry.get("event_log") or []) if isinstance(e, dict) and e.get("type") in EVENT_LABEL
            and isinstance(e.get("damage"), (int, float)) and not isinstance(e.get("damage"), bool)]


def chronicle_derived():
    """[(run number, kind, text)] worked out from run_log_history, oldest first. The first run only sets the
    baselines: it has no 'worst so far' and no 'best score' line, because there was nothing to beat."""
    lines = []
    records = new_record_run_indexes()
    seen_types = set()
    worst = None
    flawless_done = False
    first = True
    for index, entry in enumerate(run_log_history):
        if not isinstance(entry, dict):
            continue
        number = entry.get("run_number")
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            continue
        log = _chronicle_events(entry)
        score = entry.get("score", 0)
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            score = 0
        if first:
            lines.append((number, "run", f"The first trial is over: score {score:.0f}."))
            first = False
        for event in log:
            if event["type"] not in seen_types:
                seen_types.add(event["type"])
                lines.append((number, "first", f"First {EVENT_LABEL[event['type']]} weathered: {event['damage']:.0f} damage."))
        if log:
            top = max(log, key=lambda e: e["damage"])
            if worst is not None and top["damage"] > worst + 0.5:
                lines.append((number, "worst", f"Worst disaster yet: {EVENT_LABEL[top['type']]}, {top['damage']:.0f} damage."))
            worst = top["damage"] if worst is None else max(worst, top["damage"])
        if not flawless_done:
            for event in log:
                if entry_is_flawless(event):
                    flawless_done = True
                    lines.append((number, "flawless", f"First Flawless Defense: {EVENT_LABEL[event['type']]} held to {event['damage']:.0f} damage."))
                    break
        if index in records:
            lines.append((number, "record", f"New best score: {score:.0f}."))
    return lines


CHRONICLE_DERIVED_ICONS = {"run": "\U0001f3d8", "first": "\U0001f4cd", "worst": "\u26a0", "flawless": "\U0001f6e1", "record": "\U0001f3c5"}
CHRONICLE_RUN_KINDS = ("memory", "lesson")  # stored lines that belong to a run itself, not to the gap after it


def chronicle_entries():
    """The whole timeline as [{"label", "icon", "text"}], oldest first: a run's own lines (worked out or stored at
    payout), then what was done after it (skills adopted, points moved, a Second Founding)."""
    rows = []
    for position, (number, kind, text) in enumerate(chronicle_derived()):
        rows.append(((number, 0, position), f"Run {number}", CHRONICLE_DERIVED_ICONS[kind], text))
    for position, item in enumerate(runstate.meta["chronicle"]):
        in_run = item["kind"] in CHRONICLE_RUN_KINDS
        label = f"Run {item['after']}" if in_run else (f"After run {item['after']}" if item["after"] else "Before the first run")
        rows.append(((item["after"], 1 if in_run else 2, position), label, CHRONICLE_KINDS[item["kind"]], item["text"]))
    rows.sort(key=lambda r: r[0])
    return [{"label": label, "icon": icon, "text": text} for _key, label, icon, text in rows]


def chronicle_text():
    name = runstate.meta["settlement_name"] or "My settlement"
    lines = [f"Aftermath: the chronicle of {name}"]
    lines += [f"{e['label']}: {e['text']}" for e in chronicle_entries()]
    return "\n".join(lines)


def render_chronicle():
    toggle = _el("chronicle-toggle-button")
    panel = _el("chronicle-panel")
    if toggle is None or panel is None:
        return  # a cached older page without the chronicle
    entries = chronicle_entries()
    toggle.innerText = "Hide Chronicle" if runstate.chronicle_open else f"\U0001f4d6 Chronicle ({len(entries)})"
    panel.hidden = not runstate.chronicle_open
    if not runstate.chronicle_open:
        return
    list_el = _el("chronicle-list")
    if list_el is None:
        return
    list_el.innerHTML = ""
    if not entries:
        empty = document.createElement("li")
        empty.className = "chronicle-empty"
        empty.innerText = "Nothing written yet. Finish a run and its first lines appear here; skills you adopt are added as you buy them."
        list_el.appendChild(empty)
    for entry in entries:
        item = document.createElement("li")
        item.className = "chronicle-entry"
        label = document.createElement("span")
        label.className = "chronicle-entry-label"
        label.innerText = entry["label"]
        item.appendChild(label)
        text = document.createElement("span")
        text.className = "chronicle-entry-text"
        text.innerText = f"{entry['icon']} {entry['text']}"
        item.appendChild(text)
        list_el.appendChild(item)
