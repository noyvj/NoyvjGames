"""Chronicle -- the set format: loader and validation. No DOM, no network, no clock.

A SET is a folder of seven JSON files (see CLAUDE.md for the field-by-field description):

    meta.json       id, title, status ("sample-draft" | "draft" | "reviewed"), version, nuance_window_years
    sources.json    {source_id: {title, institution (or author), url, read, kind}}
    entities.json   {events: [...], people: [...], places: [...]}
    claims.json     [{id, subject, field, value, text, confidence, sources: [{source, note}], alternatives?}]
    relations.json  [{id, from, to, type, strength, claim}]            (cause links; the cause web mechanic uses these)
    sections.json   [{id, title, blurb, difficulty, size, min_gap_years, events | from_sections, requires, clear}]
    readings.json   [{id, section, title, text, claims}]
    chapters.json   OPTIONAL {"web": [{id, title, blurb, size, events}], "myth": [{id, title, blurb, size, claims}]}
                    the chapters of the cause web and of myth-or-record (a set without it simply has neither mechanic)

The rule that makes the whole game honest: EVERY fact the game shows is a claim, and EVERY claim links at
least three reputable, distinct sources, each with a title, an institution or author, a URL and the date it
was read. `validate()` returns every problem it can find (it never stops at the first), each prefixed with a
stable code such as `E_CLAIM_SOURCES`, so tests and the review page can say exactly what is wrong. A set that
fails validation is never loaded by the engine.

Dates are ISO strings: "1789", "1789-04", "1789-04-30"; a leading minus is a BCE year ("-0431" is 431 BCE;
there is no year zero). An event has one `date` or a `start` and an `end` (a range). Events carry an explicit
`seq` and the validator rejects a set whose `seq` order disagrees with its dates.
"""

import json
import re
from pathlib import Path
from urllib.parse import urlparse

FILES = ("meta", "sources", "entities", "claims", "relations", "sections", "readings")
OPTIONAL_FILES = ("chapters",)
CONFIDENCE = ("documented", "disputed", "traditional-but-doubtful")
STATUSES = ("sample-draft", "draft", "reviewed")
KINDS = ("event", "context")          # "context" = what else was happening elsewhere (the nuance strip)
MIN_SOURCES = 3
MIN_INSTITUTIONS = 2
STRENGTHS = ("direct", "contributing")
CHAPTER_SIZE = (3, 6)
MAX_SHORT = 60
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
DATE_RE = re.compile(r"^(-?\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")
ISO_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")


class SetError(ValueError):
    """Raised by load_set_dict when validation finds problems; `.problems` lists them all."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems[:5]) + (" ..." if len(self.problems) > 5 else ""))


# --------------------------------------------------------------------------
# Dates


def parse_date(text):
    """'1789-04-30' -> (1789, 4, 30); '1789' -> (1789, None, None). None if malformed or impossible."""
    if not isinstance(text, str):
        return None
    m = DATE_RE.match(text)
    if not m:
        return None
    year = int(m.group(1))
    month = int(m.group(2)) if m.group(2) else None
    day = int(m.group(3)) if m.group(3) else None
    if year == 0:
        return None
    if month is not None and not 1 <= month <= 12:
        return None
    if day is not None:
        days = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)[month - 1]
        if not 1 <= day <= days:
            return None
        if month == 2 and day == 29 and year > 0 and not (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
            return None
    return (year, month, day)


def sort_key(text):
    """A tuple that orders dates; a missing month or day counts as the first of it."""
    parsed = parse_date(text)
    if parsed is None:
        raise ValueError("bad date %r" % (text,))
    return (parsed[0], parsed[1] or 1, parsed[2] or 1)


def format_date(text):
    """'1789-04-30' -> '30 April 1789'; '-0431' -> '431 BCE'; a range '1914/1918' -> '1914 to 1918'."""
    if isinstance(text, str) and "/" in text:
        a, b = text.split("/", 1)
        return "%s to %s" % (format_date(a), format_date(b))
    parsed = parse_date(text)
    if parsed is None:
        return str(text)
    year, month, day = parsed
    label = ("%d BCE" % -year) if year < 0 else str(year)
    if month is None:
        return label
    if day is None:
        return "%s %s" % (MONTHS[month - 1], label)
    return "%d %s %s" % (day, MONTHS[month - 1], label)


def event_start(event):
    return event.get("date") or event.get("start")


def event_value(event):
    """The string a date claim about this event must carry."""
    if event.get("date"):
        return event["date"]
    return "%s/%s" % (event.get("start"), event.get("end"))


def event_key(event):
    return sort_key(event_start(event))


def year_of(event):
    return parse_date(event_start(event))[0]


# --------------------------------------------------------------------------
# The loaded set


class ChronicleSet:
    """A validated set. Plain data plus a few lookups; nothing here mutates after load."""

    def __init__(self, files):
        self.files = files
        self.meta = files["meta"]
        self.id = self.meta["id"]
        self.title = self.meta["title"]
        self.status = self.meta["status"]
        self.status_label = self.meta.get("status_label") or self.status
        self.version = self.meta["version"]
        self.window = int(self.meta.get("nuance_window_years", 30))
        self.sources = files["sources"]
        ents = files["entities"]
        self.events = {e["id"]: e for e in ents["events"]}
        self.event_order = [e["id"] for e in sorted(ents["events"], key=lambda e: e["seq"])]
        self.people = {p["id"]: p for p in ents["people"]}
        self.places = {p["id"]: p for p in ents["places"]}
        self.claims = {c["id"]: c for c in files["claims"]}
        self.relations = files["relations"]
        self.sections = files["sections"]
        self.section_ids = [s["id"] for s in self.sections]
        self.readings = files["readings"]
        chapters = files.get("chapters") if isinstance(files.get("chapters"), dict) else {}
        self.web_chapters = list(chapters.get("web") or [])
        self.myth_chapters = list(chapters.get("myth") or [])
        self.relation_by_id = {r["id"]: r for r in self.relations}
        self._by_subject = {}
        for c in files["claims"]:
            self._by_subject.setdefault(c["subject"], []).append(c["id"])

    # -- lookups
    def section(self, section_id):
        for s in self.sections:
            if s["id"] == section_id:
                return s
        return None

    def section_pool(self, section_id):
        """Event ids a section draws its puzzles from, in seq order."""
        s = self.section(section_id)
        if s is None:
            return []
        if s.get("from_sections"):
            ids = []
            for sid in s["from_sections"]:
                ids.extend(self.section_pool(sid))
        else:
            ids = list(s["events"])
        return sorted(set(ids), key=lambda i: self.events[i]["seq"])

    def claims_for(self, subject_id):
        return [self.claims[i] for i in self._by_subject.get(subject_id, [])]

    def date_claim(self, event_id):
        for c in self.claims_for(event_id):
            if c["field"] == "date":
                return c
        return None

    def resolved_sources(self, claim):
        out = []
        for ref in claim["sources"]:
            s = self.sources[ref["source"]]
            out.append({"id": ref["source"], "title": s["title"], "institution": s.get("institution") or s.get("author"),
                        "url": s["url"], "read": s["read"], "note": ref.get("note", "")})
        return out

    def web_chapter(self, chapter_id):
        return next((c for c in self.web_chapters if c["id"] == chapter_id), None)

    def myth_chapter(self, chapter_id):
        return next((c for c in self.myth_chapters if c["id"] == chapter_id), None)

    def chapter_relations(self, chapter):
        """Relation ids with both ends inside a web chapter, in the set's own relation order."""
        inside = set(chapter["events"])
        return [r["id"] for r in self.relations if r["from"] in inside and r["to"] in inside]

    def web_relation_ids(self):
        """Every relation the cause web can reach (they all count toward the archive meter)."""
        out = []
        for c in self.web_chapters:
            for rid in self.chapter_relations(c):
                if rid not in out:
                    out.append(rid)
        return out

    def myth_claim_ids(self):
        """Every claim myth-or-record can reach, in chapter order."""
        out = []
        for c in self.myth_chapters:
            for cid in c["claims"]:
                if cid not in out:
                    out.append(cid)
        return out

    def causes_of(self, event_id):
        """Relations whose effect is this event (causes are plural: a moment can have several)."""
        return [r["id"] for r in self.relations if r["to"] == event_id]

    def event_ids(self, kind=None):
        return [i for i in self.event_order if kind is None or self.events[i]["kind"] == kind]


# --------------------------------------------------------------------------
# Validation


def _is_str(value):
    return isinstance(value, str) and value.strip() != ""


def _has_valid_url(value):
    if not _is_str(value):
        return False
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and "." in parsed.netloc and " " not in value


def validate(files):
    """Every problem found in a set's files, as strings that start with a stable code. Empty list = valid."""
    problems = []

    def bad(code, message):
        problems.append("%s: %s" % (code, message))

    if not isinstance(files, dict):
        return ["E_FILES: the set is not a dict of files"]
    for name in FILES:
        if name not in files:
            bad("E_FILES", "missing %s.json" % name)
    if problems:
        return problems

    meta, sources, entities, claims = files["meta"], files["sources"], files["entities"], files["claims"]
    relations, sections, readings = files["relations"], files["sections"], files["readings"]

    # ---- meta
    if not isinstance(meta, dict):
        return ["E_META: meta.json is not an object"]
    if not (_is_str(meta.get("id")) and SLUG.match(meta["id"])):
        bad("E_META", "id must be a lowercase slug")
    if not _is_str(meta.get("title")):
        bad("E_META", "missing title")
    if meta.get("status") not in STATUSES:
        bad("E_META", "status must be one of %s" % ", ".join(STATUSES))
    if not isinstance(meta.get("version"), int) or isinstance(meta.get("version"), bool) or meta["version"] < 1:
        bad("E_META", "version must be a positive integer")
    window = meta.get("nuance_window_years", 30)
    if not isinstance(window, int) or isinstance(window, bool) or not 1 <= window <= 500:
        bad("E_META", "nuance_window_years must be an integer from 1 to 500")

    # ---- sources
    if not isinstance(sources, dict) or not sources:
        bad("E_SOURCE_FIELD", "sources.json must be a non-empty object")
        sources = {}
    for sid, s in sources.items():
        if not (_is_str(sid) and SLUG.match(sid)):
            bad("E_SOURCE_FIELD", "source id %r is not a slug" % (sid,))
        if not isinstance(s, dict):
            bad("E_SOURCE_FIELD", "source %s is not an object" % sid)
            continue
        if not _is_str(s.get("title")):
            bad("E_SOURCE_FIELD", "source %s has no title" % sid)
        if not (_is_str(s.get("institution")) or _is_str(s.get("author"))):
            bad("E_SOURCE_FIELD", "source %s has no institution or author" % sid)
        if not _has_valid_url(s.get("url")):
            bad("E_SOURCE_FIELD", "source %s has a missing or invalid URL" % sid)
        read = s.get("read")
        if not (_is_str(read) and ISO_DAY.match(read) and parse_date(read)):
            bad("E_SOURCE_FIELD", "source %s has a missing or invalid read date" % sid)

    # ---- entities
    if not isinstance(entities, dict):
        return problems + ["E_ENTITIES: entities.json is not an object"]
    events = entities.get("events") if isinstance(entities.get("events"), list) else []
    people = entities.get("people") if isinstance(entities.get("people"), list) else []
    places = entities.get("places") if isinstance(entities.get("places"), list) else []
    if not events:
        bad("E_ENTITIES", "no events")
    ids = {}
    for kind, group in (("event", events), ("person", people), ("place", places)):
        for e in group:
            if not isinstance(e, dict) or not (_is_str(e.get("id")) and SLUG.match(e["id"])):
                bad("E_ENTITIES", "a %s has a missing or invalid id" % kind)
                continue
            if e["id"] in ids:
                bad("E_ENTITIES", "duplicate id %s" % e["id"])
            ids[e["id"]] = kind
            if not _is_str(e.get("title" if kind == "event" else "name")):
                bad("E_ENTITIES", "%s %s has no %s" % (kind, e["id"], "title" if kind == "event" else "name"))
            if kind != "event" and not _is_str(e.get("match")):
                bad("E_ENTITIES", "%s %s has no `match` text (the words its claim must contain)" % (kind, e["id"]))
    person_ids = {p["id"] for p in people if isinstance(p, dict) and "id" in p}
    place_ids = {p["id"] for p in places if isinstance(p, dict) and "id" in p}
    event_ids = set()
    for e in events:
        if not isinstance(e, dict) or "id" not in e:
            continue
        event_ids.add(e["id"])
        if e.get("kind") not in KINDS:
            bad("E_EVENT", "event %s kind must be one of %s" % (e["id"], ", ".join(KINDS)))
        has_date, has_range = "date" in e, ("start" in e or "end" in e)
        if has_date == has_range:
            bad("E_EVENT_DATE", "event %s needs exactly one of `date` or `start`+`end`" % e["id"])
        elif has_date:
            if parse_date(e["date"]) is None:
                bad("E_EVENT_DATE", "event %s has a missing or invalid date %r" % (e["id"], e.get("date")))
        else:
            a, b = parse_date(e.get("start")), parse_date(e.get("end"))
            if a is None or b is None:
                bad("E_EVENT_DATE", "event %s has an invalid start or end" % e["id"])
            elif sort_key(e["start"]) > sort_key(e["end"]):
                bad("E_EVENT_DATE", "event %s ends before it starts" % e["id"])
        if not isinstance(e.get("seq"), int) or isinstance(e.get("seq"), bool):
            bad("E_EVENT", "event %s has no integer seq" % e["id"])
        if e.get("place") is not None and e["place"] not in place_ids:
            bad("E_EVENT", "event %s names unknown place %r" % (e["id"], e["place"]))
        for pid in e.get("people", []) or []:
            if pid not in person_ids:
                bad("E_EVENT", "event %s names unknown person %r" % (e["id"], pid))
        if e.get("kind") == "event" and not e.get("section"):
            bad("E_EVENT", "event %s is in no section" % e["id"])
        if e.get("kind") == "context" and e.get("section"):
            bad("E_EVENT", "context event %s must not belong to a section" % e["id"])

    # ---- claims
    if not isinstance(claims, list) or not claims:
        bad("E_CLAIM", "claims.json must be a non-empty list")
        claims = []
    claim_ids = {}
    for c in claims:
        if not isinstance(c, dict) or not (_is_str(c.get("id")) and SLUG.match(c["id"])):
            bad("E_CLAIM", "a claim has a missing or invalid id")
            continue
        cid = c["id"]
        if cid in claim_ids:
            bad("E_CLAIM", "duplicate claim id %s" % cid)
        claim_ids[cid] = c
        if c.get("subject") not in ids:
            bad("E_CLAIM", "claim %s has an unknown subject %r" % (cid, c.get("subject")))
        for key in ("field", "value", "text"):
            if not _is_str(c.get(key)):
                bad("E_CLAIM", "claim %s has no %s" % (cid, key))
        if "short" in c and not (_is_str(c["short"]) and len(c["short"]) <= MAX_SHORT):
            bad("E_CLAIM", "claim %s `short` must be a non-empty string of at most %d characters" % (cid, MAX_SHORT))
        if c.get("confidence") not in CONFIDENCE:
            bad("E_CLAIM", "claim %s confidence must be one of %s" % (cid, ", ".join(CONFIDENCE)))
        if c.get("confidence") in ("disputed", "traditional-but-doubtful"):
            alts = c.get("alternatives")
            if not (isinstance(alts, list) and alts and all(_is_str(a) for a in alts)):
                bad("E_CLAIM", "claim %s is %s and must list `alternatives`" % (cid, c.get("confidence")))
        refs = c.get("sources")
        if not isinstance(refs, list) or len(refs) < MIN_SOURCES:
            bad("E_CLAIM_SOURCES", "claim %s has %d source(s); at least %d are required"
                % (cid, len(refs) if isinstance(refs, list) else 0, MIN_SOURCES))
            refs = refs if isinstance(refs, list) else []
        seen_ids, seen_urls, institutions = set(), set(), set()
        for ref in refs:
            sid = ref.get("source") if isinstance(ref, dict) else None
            if sid not in sources:
                bad("E_CLAIM_SOURCES", "claim %s cites unknown source %r" % (cid, sid))
                continue
            if sid in seen_ids:
                bad("E_CLAIM_SOURCES", "claim %s cites source %s twice" % (cid, sid))
            seen_ids.add(sid)
            s = sources[sid]
            if not isinstance(s, dict):
                continue
            if not _has_valid_url(s.get("url")) or not (_is_str(s.get("read")) and parse_date(s.get("read"))):
                bad("E_CLAIM_SOURCE_INCOMPLETE", "claim %s cites source %s, which lacks a URL or a read date" % (cid, sid))
            else:
                if s["url"] in seen_urls:
                    bad("E_CLAIM_SOURCES", "claim %s cites the same URL twice (%s)" % (cid, s["url"]))
                seen_urls.add(s["url"])
            institutions.add((s.get("institution") or s.get("author") or "").strip().lower())
            if not _is_str(ref.get("note")):
                bad("E_CLAIM_SOURCES", "claim %s source %s has no note saying what it confirms" % (cid, sid))
        if refs and len(institutions - {""}) < MIN_INSTITUTIONS:
            bad("E_CLAIM_INSTITUTIONS", "claim %s needs sources from at least %d different institutions" % (cid, MIN_INSTITUTIONS))
        if len(seen_urls) < MIN_SOURCES and len(refs) >= MIN_SOURCES:
            bad("E_CLAIM_SOURCES", "claim %s has fewer than %d distinct source URLs" % (cid, MIN_SOURCES))

    # contradictions: one subject+field must have one value
    seen = {}
    for c in claims:
        if not isinstance(c, dict) or "subject" not in c or "field" not in c:
            continue
        key = (c["subject"], c["field"]) if c["field"] != "relation" else (c["subject"], c["field"], c.get("value"))
        if key in seen and seen[key]["value"] != c.get("value"):
            bad("E_CONTRADICTION", "claims %s and %s disagree about %s / %s (%r against %r)"
                % (seen[key]["id"], c.get("id"), key[0], key[1], seen[key]["value"], c.get("value")))
        elif key in seen:
            bad("E_CONTRADICTION", "claims %s and %s repeat %s / %s" % (seen[key]["id"], c.get("id"), key[0], key[1]))
        seen.setdefault(key, c)

    # every event: exactly one date claim that agrees with the event, naming its place and people
    by_event_date = {}
    for c in claims:
        if isinstance(c, dict) and c.get("field") == "date" and c.get("subject") in event_ids:
            by_event_date.setdefault(c["subject"], []).append(c)
    place_by_id = {p["id"]: p for p in places if isinstance(p, dict) and "id" in p}
    person_by_id = {p["id"]: p for p in people if isinstance(p, dict) and "id" in p}
    for e in events:
        if not isinstance(e, dict) or "id" not in e or e.get("kind") not in KINDS:
            continue
        found = by_event_date.get(e["id"], [])
        if not found:
            bad("E_EVENT_NO_CLAIM", "event %s has no date claim, so its date has no sources" % e["id"])
            continue
        claim = found[0]
        if "date" in e or ("start" in e and "end" in e):
            expected = event_value(e)
            if claim.get("value") != expected:
                bad("E_EVENT_DATE_CLAIM", "event %s date %s does not match its claim %s value %r"
                    % (e["id"], expected, claim.get("id"), claim.get("value")))
        text = (claim.get("text") or "").lower()
        if e.get("place") in place_by_id and place_by_id[e["place"]].get("match", "").lower() not in text:
            bad("E_PLACE_UNSUPPORTED", "event %s names place %s but its claim text never says %r"
                % (e["id"], e["place"], place_by_id[e["place"]].get("match")))
        for pid in e.get("people", []) or []:
            if pid in person_by_id and person_by_id[pid].get("match", "").lower() not in text:
                bad("E_PERSON_UNSUPPORTED", "event %s lists person %s but its claim text never says %r"
                    % (e["id"], pid, person_by_id[pid].get("match")))

    # order: seq must be unique and agree with the dates
    seqs = [e for e in events if isinstance(e, dict) and isinstance(e.get("seq"), int) and ("date" in e or "start" in e)]
    if len({e["seq"] for e in seqs}) != len(seqs):
        bad("E_ORDER", "two events share a seq")
    try:
        ordered = sorted(seqs, key=lambda e: e["seq"])
        for a, b in zip(ordered, ordered[1:]):
            if event_key(a) > event_key(b):
                bad("E_ORDER", "event %s (seq %d, %s) is listed before %s (seq %d, %s) but happens after it"
                    % (a["id"], a["seq"], event_start(a), b["id"], b["seq"], event_start(b)))
    except (ValueError, KeyError, TypeError):
        pass  # the bad dates were already reported

    # ---- relations
    rel_ids = set()
    rel_claims = {}
    graph = {}
    if not isinstance(relations, list):
        bad("E_RELATION", "relations.json must be a list")
        relations = []
    for r in relations:
        if not isinstance(r, dict) or not _is_str(r.get("id")):
            bad("E_RELATION", "a relation has no id")
            continue
        if r["id"] in rel_ids:
            bad("E_RELATION", "duplicate relation id %s" % r["id"])
        rel_ids.add(r["id"])
        if r.get("from") not in event_ids or r.get("to") not in event_ids:
            bad("E_RELATION", "relation %s must join two events" % r["id"])
            continue
        if r["from"] == r["to"]:
            bad("E_RELATION_CONTRADICTION", "relation %s joins an event to itself" % r["id"])
        if r.get("type") not in ("led_to",):
            bad("E_RELATION", "relation %s has unknown type %r" % (r["id"], r.get("type")))
        if r.get("strength") not in STRENGTHS:
            bad("E_RELATION", "relation %s strength must be direct or contributing" % r["id"])
        rc = claim_ids.get(r.get("claim"))
        if rc is None:
            bad("E_RELATION", "relation %s has no claim, so its evidence is unsourced" % r["id"])
        elif rc.get("field") != "relation":
            bad("E_RELATION", "relation %s claim %s must have field 'relation'" % (r["id"], rc.get("id")))
        else:
            if rc.get("value") != "%s>%s" % (r["from"], r["to"]):
                bad("E_RELATION_CLAIM", "relation %s: claim %s value must be %r (cause>effect)" % (r["id"], rc["id"], "%s>%s" % (r["from"], r["to"])))
            if rc.get("subject") != r["to"]:
                bad("E_RELATION_CLAIM", "relation %s: claim %s must be about the effect, %s" % (r["id"], rc["id"], r["to"]))
            if rc["id"] in rel_claims:
                bad("E_RELATION_CLAIM", "claim %s supports both %s and %s; each relation needs its own claim" % (rc["id"], rel_claims[rc["id"]], r["id"]))
            rel_claims.setdefault(rc["id"], r["id"])
        graph.setdefault(r["from"], set()).add(r["to"])
    for c in claims:
        if isinstance(c, dict) and c.get("field") == "relation" and c.get("id") not in rel_claims:
            bad("E_RELATION_CLAIM", "claim %s has field 'relation' but no relation uses it" % c.get("id"))
    ev_by_id = {e["id"]: e for e in events if isinstance(e, dict) and "id" in e}
    for r in relations:
        if not isinstance(r, dict) or r.get("from") not in ev_by_id or r.get("to") not in ev_by_id:
            continue
        try:
            if event_key(ev_by_id[r["from"]]) > event_key(ev_by_id[r["to"]]):
                bad("E_RELATION_ORDER", "relation %s says %s led to %s, which happened earlier" % (r["id"], r["from"], r["to"]))
        except (ValueError, KeyError):
            pass
        if r["from"] in graph.get(r["to"], ()):
            bad("E_RELATION_CONTRADICTION", "relation %s: %s and %s each lead to the other" % (r["id"], r["from"], r["to"]))
    # cycles (longer than two) in led_to
    state = {}

    def visit(node, trail):
        state[node] = 1
        for nxt in graph.get(node, ()):
            if state.get(nxt) == 1:
                bad("E_RELATION_CONTRADICTION", "cause cycle: %s" % " -> ".join(trail + [node, nxt]))
            elif state.get(nxt) is None:
                visit(nxt, trail + [node])
        state[node] = 2

    for node in list(graph):
        if state.get(node) is None:
            visit(node, [])

    # ---- sections
    if not isinstance(sections, list) or not sections:
        bad("E_SECTION", "sections.json must be a non-empty list")
        sections = []
    section_ids = []
    own_events = {}
    for s in sections:
        if not isinstance(s, dict) or not (_is_str(s.get("id")) and SLUG.match(s["id"])):
            bad("E_SECTION", "a section has a missing or invalid id")
            continue
        sid = s["id"]
        if sid in section_ids:
            bad("E_SECTION", "duplicate section id %s" % sid)
        for key in ("title", "blurb"):
            if not _is_str(s.get(key)):
                bad("E_SECTION", "section %s has no %s" % (sid, key))
        if s.get("difficulty") not in (1, 2, 3):
            bad("E_SECTION", "section %s difficulty must be 1, 2 or 3" % sid)
        if not isinstance(s.get("size"), int) or isinstance(s.get("size"), bool) or not 2 <= s["size"] <= 8:
            bad("E_SECTION", "section %s size must be an integer from 2 to 8" % sid)
        if not isinstance(s.get("min_gap_years"), int) or isinstance(s.get("min_gap_years"), bool) or s["min_gap_years"] < 0:
            bad("E_SECTION", "section %s min_gap_years must be a non-negative integer" % sid)
        for req in s.get("requires", []) or []:
            if req not in section_ids:
                bad("E_SECTION", "section %s requires %r, which is not an earlier section" % (sid, req))
        has_events, has_from = "events" in s, "from_sections" in s
        if has_events == has_from:
            bad("E_SECTION", "section %s needs exactly one of `events` or `from_sections`" % sid)
        if has_events:
            for eid in s["events"]:
                if eid not in ev_by_id:
                    bad("E_SECTION", "section %s lists unknown event %s" % (sid, eid))
                elif ev_by_id[eid].get("section") != sid:
                    bad("E_SECTION", "section %s lists %s but that event says section %r" % (sid, eid, ev_by_id[eid].get("section")))
                elif eid in own_events:
                    bad("E_SECTION", "event %s is in sections %s and %s" % (eid, own_events[eid], sid))
                own_events[eid] = sid
        if has_from:
            for other in s["from_sections"]:
                if other not in section_ids:
                    bad("E_SECTION", "section %s draws from %r, which is not an earlier section" % (sid, other))
        clear = s.get("clear")
        if not (isinstance(clear, dict) and (clear.get("type") == "learn_all"
                or (clear.get("type") == "solves" and isinstance(clear.get("n"), int) and clear["n"] >= 1))):
            bad("E_SECTION", "section %s needs clear = learn_all or solves with n" % sid)
        section_ids.append(sid)
    for e in events:
        if isinstance(e, dict) and e.get("kind") == "event" and e.get("section") and e["id"] not in own_events \
                and e["section"] in section_ids:
            bad("E_SECTION", "event %s says section %s but that section does not list it" % (e["id"], e["section"]))
        if isinstance(e, dict) and e.get("kind") == "event" and e.get("section") and e["section"] not in section_ids:
            bad("E_SECTION", "event %s is in unknown section %s" % (e["id"], e["section"]))

    # ---- readings
    if not isinstance(readings, list):
        bad("E_READING", "readings.json must be a list")
        readings = []
    for r in readings:
        if not isinstance(r, dict) or not _is_str(r.get("id")):
            bad("E_READING", "a reading has no id")
            continue
        if r.get("section") not in section_ids:
            bad("E_READING", "reading %s names unknown section %r" % (r["id"], r.get("section")))
        for key in ("title", "text"):
            if not _is_str(r.get(key)):
                bad("E_READING", "reading %s has no %s" % (r["id"], key))
        if _is_str(r.get("text")) and len(r["text"]) > 700:
            bad("E_READING", "reading %s is longer than 700 characters (readings are short)" % r["id"])
        cl = r.get("claims")
        if not (isinstance(cl, list) and cl and all(x in claim_ids for x in cl)):
            bad("E_READING", "reading %s must cite existing claims, so every fact in it has sources" % r["id"])

    # ---- chapters (optional): the cause web's and myth-or-record's sections
    _check_chapters(files.get("chapters"), event_ids, claim_ids, relations, bad)

    # ---- playability (only worth checking when the rest is sound)
    if not problems:
        try:
            _check_playable(ChronicleSet(files))
        except Exception as exc:  # noqa: BLE001 -- a validator reports, it never raises
            bad("E_SECTION_UNPLAYABLE", str(exc))
    return problems


def _check_chapters(chapters, event_ids, claim_ids, relations, bad):
    if chapters is None:
        return
    if not isinstance(chapters, dict) or set(chapters) - {"web", "myth"}:
        bad("E_CHAPTER", "chapters.json must be an object with only `web` and `myth` lists")
        return
    lo, hi = CHAPTER_SIZE
    rels = [r for r in relations if isinstance(r, dict) and r.get("from") in event_ids and r.get("to") in event_ids]
    seen_ids = set()

    def common(kind, ch):
        if not isinstance(ch, dict) or not (_is_str(ch.get("id")) and SLUG.match(ch["id"])):
            bad("E_CHAPTER", "a %s chapter has a missing or invalid id" % kind)
            return False
        if (kind, ch["id"]) in seen_ids:
            bad("E_CHAPTER", "duplicate %s chapter id %s" % (kind, ch["id"]))
        seen_ids.add((kind, ch["id"]))
        for key in ("title", "blurb"):
            if not _is_str(ch.get(key)):
                bad("E_CHAPTER", "%s chapter %s has no %s" % (kind, ch["id"], key))
        if not isinstance(ch.get("size"), int) or isinstance(ch.get("size"), bool) or not lo <= ch["size"] <= hi:
            bad("E_CHAPTER", "%s chapter %s size must be an integer from %d to %d" % (kind, ch["id"], lo, hi))
            return False
        return True

    covered = set()
    web = chapters.get("web", [])
    if not isinstance(web, list):
        bad("E_CHAPTER", "`web` must be a list")
        web = []
    for ch in web:
        if not common("web", ch):
            continue
        evs = ch.get("events")
        if not (isinstance(evs, list) and len(set(evs)) == len(evs) and all(e in event_ids for e in evs)):
            bad("E_CHAPTER", "web chapter %s `events` must be a list of distinct, existing events" % ch["id"])
            continue
        if len(evs) < ch["size"]:
            bad("E_CHAPTER", "web chapter %s has fewer events than its puzzle size" % ch["id"])
        inside = [r for r in rels if r["from"] in evs and r["to"] in evs]
        if not inside:
            bad("E_CHAPTER_EMPTY", "web chapter %s contains no relation, so there is nothing to connect" % ch["id"])
        covered |= {r["id"] for r in inside}
    if web:
        for r in rels:
            if r["id"] not in covered:
                bad("E_CHAPTER_UNREACHABLE", "relation %s is in no web chapter, so a player could never find it" % r["id"])

    myth = chapters.get("myth", [])
    if not isinstance(myth, list):
        bad("E_CHAPTER", "`myth` must be a list")
        myth = []
    used = set()
    for ch in myth:
        if not common("myth", ch):
            continue
        ids = ch.get("claims")
        if not (isinstance(ids, list) and len(set(ids)) == len(ids) and all(i in claim_ids for i in ids)):
            bad("E_CHAPTER", "myth chapter %s `claims` must be a list of distinct, existing claims" % ch["id"])
            continue
        if len(ids) < ch["size"]:
            bad("E_CHAPTER", "myth chapter %s has fewer claims than its puzzle size" % ch["id"])
        for cid in ids:
            c = claim_ids[cid]
            if c.get("field") == "relation":
                bad("E_CHAPTER", "myth chapter %s lists relation claim %s (the cause web owns those)" % (ch["id"], cid))
            if c.get("subject") not in event_ids:
                bad("E_CHAPTER", "myth chapter %s: claim %s must be about an event, so the player has met it" % (ch["id"], cid))
            if not _is_str(c.get("short")):
                bad("E_CHAPTER", "myth chapter %s: claim %s needs a `short` name for the archive" % (ch["id"], cid))
        levels = {claim_ids[i].get("confidence") for i in ids}
        if "documented" not in levels or not (levels - {"documented"}):
            bad("E_CHAPTER_MIX", "myth chapter %s needs at least one documented claim and at least one disputed or doubtful claim" % ch["id"])
        used |= set(ids)
    if myth:
        for cid, c in claim_ids.items():
            if c.get("confidence") in ("disputed", "traditional-but-doubtful") and c.get("field") != "relation" \
                    and c.get("subject") in event_ids and cid not in used:
                bad("E_CHAPTER_UNREACHABLE", "claim %s is %s but is in no myth chapter" % (cid, c["confidence"]))


def _check_playable(cset):
    """Every section must be able to generate a puzzle for every anchor, and every elsewhere event must be
    within the nuance window of some playable event (so a player can always reach 100%)."""
    from puzzle import make_puzzle

    for s in cset.sections:
        pool = cset.section_pool(s["id"])
        if len(pool) < s["size"]:
            raise ValueError("section %s has %d events but puzzles need %d" % (s["id"], len(pool), s["size"]))
        for r in range(len(pool)):
            make_puzzle(cset, s["id"], r)
    from myth import make_myth_puzzle
    from web import make_web_puzzle

    for ch in cset.web_chapters:
        for r in range(len(cset.chapter_relations(ch))):
            make_web_puzzle(cset, ch["id"], r)
    for ch in cset.myth_chapters:
        for r in range(len(ch["claims"])):
            make_myth_puzzle(cset, ch["id"], r)
    playable_years = [year_of(cset.events[i]) for i in cset.event_ids("event")]
    for cid in cset.event_ids("context"):
        y = year_of(cset.events[cid])
        if not any(abs(y - p) <= cset.window for p in playable_years):
            raise ValueError("elsewhere event %s is not within %d years of any playable event" % (cid, cset.window))


# --------------------------------------------------------------------------
# Loading


def load_set_dict(files):
    """Validate and wrap an in-memory set; raises SetError listing every problem."""
    problems = validate(files)
    if problems:
        raise SetError(problems)
    return ChronicleSet(files)


def read_set_files(folder):
    """Read the seven JSON files of a set folder (plus the optional chapters.json) into a dict (a missing file is simply absent)."""
    folder = Path(folder)
    files = {}
    for name in FILES:
        path = folder / ("%s.json" % name)
        if path.exists():
            files[name] = json.loads(path.read_text(encoding="utf-8"))
    for name in OPTIONAL_FILES:
        path = folder / ("%s.json" % name)
        if path.exists():
            files[name] = json.loads(path.read_text(encoding="utf-8"))
    return files


def load_set(folder):
    return load_set_dict(read_set_files(folder))
