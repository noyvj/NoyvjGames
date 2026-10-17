"""The scientist's log (G19): events, pinning, filter and search, rendering, copy, and the automated Region D play."""

import narrative_log
from js import document

import thaw_runstate as runstate
from thaw_bridge import _escape
from thaw_model import deg, region, region_b, region_c, region_d
from thaw_rules import CASCADE_BUMP, INVEST_COST, SECOND_WARMING_MILESTONE


# G19: scientist's log -- a running, per-round record of key moments in the
# three managed regions. Newest last; capped so a long session (and the
# save payload) stays small.
#
# Z11 (planning/TODO.md, site-wide goal): the append-and-cap bookkeeping
# below delegates to shared/narrative_log.py -- the shared component this
# game's own pattern (alongside Continuum's "Chronicle") helped generalize.
# A pure refactor, not a behavior change: narrative_log.add_entry() trims
# exactly the way the old `del science_log[:-SCIENCE_LOG_MAX]` line always
# trimmed. This game's own rendering (science_log_html(), an HTML-string
# builder feeding a `<ol>`/`<li>` list inside a <details> disclosure) is
# deliberately NOT migrated onto the shared module's DOM-based `render()` --
# see this file's own CLAUDE.md Z11 build note for why forcing that
# render shape onto this already-shipped, differently-structured markup
# would be a rewrite, not a drop-in.
SCIENCE_LOG_MAX = 40
science_log = []

_EVENT_TEXT = {
    "melt": "permafrost began melting at {temp}.",
    "critical": "the feedback loop went critical ({accel:.1f}x background warming).",
    "milestone_delay": "intervention delayed reaching {milestone} warming.",
    "preempt": "pre-emptive protection ({damp:.0f}% dampening) was already in place when melt began.",
    "cascade": "a tipping cascade from the neighboring region added {bump} of warming.",
    "restoration": "the feedback loop held steady long enough for restoration to begin pulling warming back.",
}


def _record_round_events():
    for label, r in (("A", region), ("B", region_b), ("C", region_c)):
        for event in r.round_events:
            text = _EVENT_TEXT[event].format(
                temp=deg(r.temperature, plus=True),
                accel=r.acceleration_factor(),
                milestone=deg(SECOND_WARMING_MILESTONE, 0, plus=True),
                damp=(r.dampening_at_melt_start or 0.0) * 100,
                bump=deg(CASCADE_BUMP),
            )
            science_log.append({"region": label, "round": r.round_number - 1, "text": text})
    _cap_science_log()


# G-19: a pinned entry survives the 40-entry cap (at most MAX_PINNED pins, so the log can always make
# room) and is repeated in the Highlights recap. Pins ride the saved log as `"pinned": true`, written
# only on pinned entries.
MAX_PINNED = 10

# G-18: filter chips. An entry's kind is read from its text (so entries from older saves sort too):
# "tipping" (melt, critical, cascades), "milestone" (delays, restoration, balance, escalation, run end)
# and "invest" (pre-emptive protection, rescues, grants, convoys).
LOG_FILTERS = ("all", "tipping", "milestone", "invest", "pinned")
LOG_FILTER_LABEL = {
    "all": "All", "tipping": "Tipping", "milestone": "Milestones", "invest": "Invest", "pinned": "Pinned",
}
_LOG_KIND_WORDS = (
    ("tipping", ("began melting", "went critical", "cascade")),
    ("invest", ("pre-emptive", "rescue", "grant", "convoy", "supply crate")),
    ("milestone", ("delayed reaching", "restoration", "perfect-balance", "escalation", "the run is over")),
)


def log_kind(entry):
    text = str(entry.get("text", "")).lower()
    for kind, words in _LOG_KIND_WORDS:
        if any(word in text for word in words):
            return kind
    return "other"


def _cap_science_log(limit=None):
    """Trims the log to `limit` entries (default SCIENCE_LOG_MAX), dropping the oldest unpinned
    entries first. Pinned entries only go if there is nothing else to drop."""
    limit = SCIENCE_LOG_MAX if limit is None else limit
    if not any(entry.get("pinned") for entry in science_log):
        narrative_log.cap_entries(science_log, limit)  # the shared Z11 helper when nothing is pinned
        return
    unpinned = [i for i, entry in enumerate(science_log) if not entry.get("pinned")]
    excess = len(science_log) - limit
    if excess <= 0:
        return
    drop = set(unpinned[:excess])
    if len(drop) < excess:
        drop |= set(range(len(science_log))) - set(unpinned)
        drop = set(sorted(drop)[:excess])
    science_log[:] = [entry for i, entry in enumerate(science_log) if i not in drop]


def _log_action(label, text):
    """An invest-kind line for something the player just did between rounds (rescue, grant, convoy)."""
    _cap_science_log(SCIENCE_LOG_MAX - 1)
    science_log.append({"region": label, "round": region.round_number, "text": text})


def pinned_count():
    return sum(1 for entry in science_log if entry.get("pinned"))


def set_log_pinned(index, pinned):
    """Pins or unpins the entry at `index` in the stored log. Returns True if it changed."""
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(science_log):
        return False
    entry = science_log[index]
    if pinned:
        if entry.get("pinned") or pinned_count() >= MAX_PINNED:
            return False
        entry["pinned"] = True
        return True
    if not entry.get("pinned"):
        return False
    del entry["pinned"]
    return True


def set_log_filter(name):
    if name not in LOG_FILTERS:
        return False
    runstate.log_filter = name
    return True


def set_log_query(text):
    runstate.log_query = str(text or "").strip().lower()[:60]


def filtered_log():
    """[(stored index, entry)] for the entries the current chip and search let through, oldest first."""
    rows = []
    for index, entry in enumerate(science_log):
        if runstate.log_filter == "pinned" and not entry.get("pinned"):
            continue
        if runstate.log_filter in ("tipping", "milestone", "invest") and log_kind(entry) != runstate.log_filter:
            continue
        if runstate.log_query:
            haystack = f"round {entry['round']} region {entry['region']} {entry['text']}".lower()
            if runstate.log_query not in haystack:
                continue
        rows.append((index, entry))
    return rows


def science_log_html():
    if not science_log:
        return "<li>No key moments recorded yet.</li>"
    rows = filtered_log()
    if not rows:
        # empty text on purpose: the Desktop notifier announces row text, and the words come from CSS
        return '<li class="log-empty" data-empty="No entries match this filter."></li>'
    items = []
    for index, entry in reversed(rows):
        pinned = bool(entry.get("pinned"))
        label = "Unpin this entry" if pinned else "Pin this entry"
        items.append(
            f'<li class="{"log-entry log-entry--pinned" if pinned else "log-entry"}">'
            f"Round {entry['round']} \u2014 Region {entry['region']}: {_escape(entry['text'])} "
            f'<button type="button" class="log-pin-button" data-pin-index="{index}" '
            f'aria-pressed="{"true" if pinned else "false"}" aria-label="{label}" title="{label}">'
            f"</button></li>"
        )
    return "".join(items)


def science_log_text(only_pinned=False):
    """Plain text of the whole log (or just the pinned lines), oldest first, one line each."""
    rows = [e for e in science_log if e.get("pinned")] if only_pinned else list(science_log)
    return "\n".join(f"Round {e['round']} - Region {e['region']}: {e['text']}" for e in rows)


def pinned_highlight_lines():
    return [f"Pinned, round {e['round']}, Region {e['region']}: {e['text']}" for e in science_log if e.get("pinned")]


def render_science_log():
    document.getElementById("science-log-count").innerText = str(len(science_log))
    document.getElementById("science-log-list").innerHTML = science_log_html()
    for name in LOG_FILTERS:
        chip = document.getElementById(f"log-filter-{name}")
        label = LOG_FILTER_LABEL[name]
        chip.innerText = f"{label} ({pinned_count()})" if name == "pinned" else label
        chip.className = "log-chip log-chip--on" if name == runstate.log_filter else "log-chip"
        chip.setAttribute("aria-pressed", "true" if name == runstate.log_filter else "false")
    document.getElementById("log-pin-note").innerText = (
        f"Pinned entries ({pinned_count()} of {MAX_PINNED}) stay when older lines scroll off, "
        f"and appear in the Highlights recap."
    )


def _auto_play_worst_case_region():
    """Called once per Advance Round: spends every affordable unit of
    Region D's funds on Output only, then advances it — pure neglect,
    replayed automatically every round regardless of whether the panel
    revealing it is currently open.

    Region D's own neglect is what makes it a worst case: every round's
    income is `capacity["output"] * OUTPUT_INCOME_PER_UNIT`, all of which
    gets reinvested straight back into more output at a flat per-unit
    cost — a compounding ~30% growth in capacity every round. That
    exponential growth is the intended story ("look how much worse doing
    nothing gets"), but spending it one unit at a time via a `while
    region_d.invest("output"): pass` loop meant the SIMULATION cost grew
    exponentially with round count too — a long session's Advance Round
    click could take seconds by round 50+. Buying the affordable unit
    count directly is O(1) regardless of how large the region has grown,
    with the exact same end state `invest()` would have produced one unit
    at a time (same flat per-unit cost, no partial-unit spend)."""
    cost = INVEST_COST["output"]
    units = int(region_d.funds // cost)
    if units:
        region_d.funds -= units * cost
        region_d.capacity["output"] += units
    region_d.advance_round()
