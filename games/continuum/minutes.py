"""K5 (planning/TODO.md): the "Council Minutes" policy log.

A running, dated ledger of every major decision the player makes --
researching a discovery, raising a building, entering a new era -- worded
like the minutes of a city council meeting. Pure logic, no DOM (game.py
owns the panel), riding in `campaign.ui["policy_log"]` exactly like the
founder's log (K15): plain saved dicts, validated on every read so an old
or hand-edited save can never break the panel.

Distinct from `log.Chronicle` (what HAPPENED to the settlement -- growth,
livability shifts) and the founder's log (the player's own notes): this is
what the player DECIDED.
"""

import sim

MAX_ENTRIES = 80
TEXT_MAX = 160
KEY = "policy_log"
KINDS = ("research", "build", "era")

_VERB = {
    "research": "Motion carried: the council resolves to study {subject}.",
    "build": "Motion carried: the council resolves to build {subject}.",
    "era": "Motion carried: the settlement enters {subject}.",
}


def motion_text(kind, subject):
    return _VERB[kind].format(subject=subject)


def clean(raw):
    """Validated entries from whatever a save handed back (may be junk)."""
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw[-MAX_ENTRIES:]:
        if not isinstance(item, dict):
            continue
        kind, era, season, text = item.get("kind"), item.get("era"), item.get("season"), item.get("text")
        if kind not in KINDS or era not in sim.ERA_LABEL:
            continue
        if isinstance(season, bool) or not isinstance(season, int) or season < 1:
            continue
        if not isinstance(text, str) or not text.strip():
            continue
        out.append({"kind": kind, "era": era, "season": season, "text": text[:TEXT_MAX]})
    return out


def entries(ui):
    return clean(ui.get(KEY))


def record(ui, kind, subject, era, season):
    """Append one motion; returns False for a malformed request."""
    if kind not in KINDS or not isinstance(subject, str) or not subject.strip():
        return False
    if era not in sim.ERA_LABEL or isinstance(season, bool) or not isinstance(season, int) or season < 1:
        return False
    log = entries(ui)
    log.append({"kind": kind, "era": era, "season": season, "text": motion_text(kind, subject.strip())[:TEXT_MAX]})
    ui[KEY] = log[-MAX_ENTRIES:]
    return True
