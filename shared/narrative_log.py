"""Shared narrative-log widget: a capped, append-only, dated feed of short
text entries.

Generalized from Continuum's own `log.py` "Chronicle" (Milestone 6) —
lightweight, milestone-triggered flavor text the player can glance at or
ignore, never a popup or a blocking prompt. Z11 (`planning/TODO.md`)
extracted the two genuinely reusable pieces of that pattern out into this
module: the "append, then drop the oldest once past a cap" bookkeeping
(`add_entry`), and the "render newest-first, capped to a smaller
on-screen count, with an empty-state fallback" display loop (`render`).

**What deliberately stayed OUT of this module**, per this module's own
narrow-API brief (`planning/TODO.md` Z11's own instruction not to force a
generic shape onto games whose actual needs differ): the "have we already
logged this" trigger bookkeeping (Continuum's `_population_milestones_hit`/
`_researched_seen`/`_last_score_label` sets), the entry's own field shape
(Continuum's `LogEntry` carries `season`/`era`/`kind`/`text`; Thaw's
scientist's-log entries carry `region`/`round`/`text`; Le Champ de Mots'
report log carries `day`/`topic`/`text` — three different shapes, none of
which this module tries to unify), and per-kind styling/icon lookups
(Continuum's `LOG_KIND_ICON`). Every one of those is genuinely specific to
one game's own mechanics and stays in that game's own `game.py`/engine
module, exactly the same "the shared module holds the DOM/bookkeeping
plumbing that used to be duplicated, not the content" split
`shared/info_page.py`'s own module docstring already establishes for the
info-page widget.

Loaded the same way as a game's own game.py/engine modules: each game's
index.html fetches this file's source and writes it into Pyodide's
virtual filesystem (as "narrative_log.py", so `import narrative_log`
resolves normally) *before* running the game's own code that imports it.
See continuum/thaw/champ-de-mots' index.html boot scripts for the exact
fetch/write (the same pattern `shared/info_page.py` already uses).

`render()`'s `from js import document` is deliberately a lazy,
function-local import rather than a module-level one (unlike
`shared/info_page.py`'s own top-level import). Continuum's `log.py`
imports this module from inside its own `save.py` import chain, which
several of Continuum's test files reach directly (`import save`) at
collection time, before the pytest fake-DOM harness has installed a fake
`js` module in `sys.modules` — a module-level `from js import document`
here would make every one of those collection-time imports crash under
plain CPython. `add_entry()`/`sanitize()` need no `js` at all and stay
free of this concern either way.
"""

# A default cap for a caller that doesn't have a stronger opinion of its
# own (Continuum's own MAX_ENTRIES is 60; a caller is free to pass any cap
# it likes to add_entry() -- this is only a fallback, not a hub-wide rule).
DEFAULT_CAP = 60


def cap_entries(entries, cap):
    """Trims `entries` in place down to at most `cap` items, oldest first.
    Mutates and returns `entries`.

    Exposed separately from `add_entry()` (which calls this after every
    single append) for a caller that appends zero, one, or several entries
    in one pass and needs the cap enforced exactly once at the end
    regardless of how many of those actually happened -- Thaw's own
    `_record_round_events()` is exactly this shape (a per-round loop that
    can append 0-3 entries depending on how many regions had something
    happen), and its pre-Z11 code enforced the cap with one unconditional
    `del science_log[:-SCIENCE_LOG_MAX]` after the loop, not one trim per
    append. Calling `add_entry()` in a loop would only trim on the calls
    that actually appended something, which is a real behavior
    difference from the original when a round appends nothing at all.
    """
    if len(entries) > cap:
        del entries[: len(entries) - cap]
    return entries


def add_entry(entries, entry, cap=DEFAULT_CAP):
    """Appends `entry` (any JSON-safe value -- a plain dict in every
    integration so far, but this function has no opinion on its shape) to
    `entries` in place, then trims the list down to at most `cap` items
    via `cap_entries()`. Mutates and returns `entries`, so a caller that
    keeps its log as a module-level or instance-level list can use either
    the mutation or the return value, whichever reads better at the call
    site.

    Matches Continuum's own pre-Z11 `Chronicle._add()` exactly (append,
    then drop from the front down to the cap) -- a byte-identical
    behavior, not a reinterpretation, which is what makes migrating it
    onto this a pure refactor rather than a rewrite. A caller whose own
    append pattern doesn't fit "one entry in, cap enforced immediately"
    (see `cap_entries()`'s own docstring) should call `cap_entries()`
    directly instead.
    """
    entries.append(entry)
    return cap_entries(entries, cap)


def sanitize(data, cap, is_valid=None):
    """Returns a safe list of entries from `data` (arbitrary save input):
    a non-list becomes an empty list, and only dict entries that also
    satisfy `is_valid(entry)` (when given) are kept, capped to the last
    `cap` of them -- the same "only trust the shape this field can
    legitimately have" gate every per-game restore path in this hub
    already repeats by hand (see Continuum's `Chronicle.restore()`/
    Thaw's `load_state()`).

    This only handles the generic "is this even a well-formed list of
    dict entries, capped to a sane length" check. A caller whose entries
    need their own per-field coercion (Continuum casting `season` to an
    int, Thaw slicing `region` to one character) does that inside
    `is_valid` or in a follow-up pass over the cleaned list -- this
    function has no per-game field knowledge to add.
    """
    if not isinstance(data, list):
        return []
    cleaned = [e for e in data if isinstance(e, dict) and (is_valid is None or is_valid(e))]
    if len(cleaned) > cap:
        cleaned = cleaned[-cap:]
    return cleaned


def render(container_id, entries, build_row, empty_text="Nothing to report yet.",
           max_visible=20, count_element_id=None, count_text=None):
    """Renders `entries` (newest first, capped to `max_visible` on-screen
    rows independent of how many the caller keeps for its own save file --
    the same "the render path caps independently and more tightly" split
    Continuum's own `game.LOG_VISIBLE_ENTRIES` already drew against
    `log.MAX_ENTRIES`) into the DOM element with id `container_id`.

    `build_row(entry)` turns one domain-specific entry into a real DOM
    element (via `document.createElement`, the caller's own choice of tag
    and CSS classes) -- deliberately left to the caller rather than this
    module dictating one fixed row shape, since Continuum's existing log
    rows (a `.row-top`/`.row-name` heading plus a `.row-blurb` body,
    styled per `kind`), Le Champ de Mots' single-line dashboard-style rows,
    and any future integration's own shape are all genuinely different
    markup, not the same structure with different CSS. This module still
    owns the part that WAS genuinely duplicated: clearing the container,
    the newest-first/capped slice, the empty-state fallback, and the
    optional entry-count label -- exactly the boilerplate every one of
    this hub's own render_log()-shaped functions repeated by hand.

    Every row is real DOM built by `build_row`, never an HTML string handed
    to `innerHTML` -- matching the rest of this hub's save-derived-text
    discipline (Continuum's own Phase 4 audit note: "every place a
    save-derived string reaches the DOM is written through .innerText,
    never .innerHTML"), so a hostile string riding in a save can never
    execute as markup through this shared path.
    """
    from js import document  # noqa: PLC0415 -- Pyodide-only, deliberately lazy (see module docstring)

    if count_element_id is not None:
        count_el = document.getElementById(count_element_id)
        if count_el is not None:
            count_el.innerText = count_text if count_text is not None else f"{len(entries)} entries"

    container = document.getElementById(container_id)
    container.innerHTML = ""

    if not entries:
        empty = document.createElement("p")
        empty.className = "row-blurb"
        empty.innerText = empty_text
        container.appendChild(empty)
        return

    for entry in reversed(entries[-max_visible:]):
        container.appendChild(build_row(entry))
