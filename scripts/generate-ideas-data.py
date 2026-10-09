#!/usr/bin/env python3
"""Regenerate the data behind the hidden ideas answer sheet (`ideas.html`).

Parses planning/IMPROVEMENT-IDEAS-ROUND-2.md and -ROUND-3.md and writes:

  ideas-data.json            committed. The questions only (section, number,
                             tag, text) plus a boolean `answered` per item, so
                             the page can hide what the docs already answer.
                             Contains no answer text.
  ideas-answers.local.json   NOT committed (listed in .git/info/exclude). The
                             existing answers parsed from each doc's answer
                             sheet, so the page can pre-fill them when it is
                             served from this checkout. Absent on GitHub Pages.

Run by hand after the ideas docs change (no CI):

    python3 scripts/generate-ideas-data.py

The docs themselves are never modified.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLANNING = ROOT / "planning"

ROUNDS = [
    {"id": "round-4", "title": "Round 4", "file": "IMPROVEMENT-IDEAS-ROUND-4.md", "answers_marker": r"^# PART 4"},
    {"id": "round-3", "title": "Round 3", "file": "IMPROVEMENT-IDEAS-ROUND-3.md", "answers_marker": r"^# PART 4"},
    {"id": "round-2", "title": "Round 2", "file": "IMPROVEMENT-IDEAS-ROUND-2.md", "answers_marker": r"^## [A-Z]{1,2}\s*$"},
]

QUESTION_HEADING = re.compile(r"^## ([A-Z]{1,4})\. (.+?)\s*$")
ITEM = re.compile(r"^(\d+)\. (.*)$")
TAG = re.compile(r"^\*\*\[(BIG|SMALL)\]\*\*\s*")
# Round 3 answers: "### GB — Canopy (gamified)"; round 2 answers: "## A"
ANSWER_HEADING = re.compile(r"^#{2,3} ([A-Z]{1,2})(?:\s+[—-]\s+.*)?\s*$")
ANSWER_LINE = re.compile(r"^(\d+)(?:\s*-\s*(\d+))?\.\s?(.*)$")

R_CODES = {"R"}  # "returning later" sections answer now / later / drop


def split_parts(lines, marker):
    pattern = re.compile(marker)
    for i, line in enumerate(lines):
        if pattern.match(line):
            return lines[:i], lines[i:]
    return lines, []


def parse_questions(lines):
    sections = []
    current = None
    last_item = None
    pending = []  # paragraph lines seen between items
    blank_before = True

    def flush_pending(section, before_item):
        nonlocal pending
        text = " ".join(p.strip() for p in pending).strip()
        pending = []
        if not text:
            return
        if before_item is not None:
            before_item["group"] = text
        elif section is not None:
            if section["items"]:
                section["notes"] = (section.get("notes", "") + " " + text).strip()
            else:
                section["intro"] = (section.get("intro", "") + " " + text).strip()

    for line in lines:
        heading = QUESTION_HEADING.match(line)
        if heading:
            if current is not None:
                flush_pending(current, None)
            code, title = heading.groups()
            current = {"code": code, "title": title.strip(), "items": []}
            sections.append(current)
            last_item = None
            pending = []
            blank_before = True
            continue
        if line.startswith("#"):  # PART banners and any other heading end the section
            if current is not None:
                flush_pending(current, None)
            current = None
            last_item = None
            pending = []
            continue
        if current is None:
            continue
        if line.strip() == "---":
            continue
        item = ITEM.match(line)
        if item:
            n, text = int(item.group(1)), item.group(2).strip()
            entry = {"n": n}
            tag = TAG.match(text)
            if tag:
                entry["tag"] = tag.group(1).lower()
                text = text[tag.end():]
            entry["text"] = text
            flush_pending(current, entry)
            current["items"].append(entry)
            last_item = entry
            blank_before = False
            continue
        if not line.strip():
            blank_before = True
            continue
        if last_item is not None and not blank_before and (line.startswith(" ") or line.startswith("\t")):
            last_item["text"] += " " + line.strip()  # wrapped continuation of an item
        else:
            pending.append(line)
        blank_before = False
    if current is not None:
        flush_pending(current, None)
    sections = [s for s in sections if s["items"]]
    for s in sections:
        # Short display titles: drop explanatory parentheticals except "(gamified)".
        s["title"] = re.sub(r"\s*\((?!gamified\))[^)]*\)", "", s["title"]).strip()
    # The Warframe tracker stays off every public page, this one included:
    # drop its section and any item (numbering is kept) that mentions it.
    sections = [s for s in sections if "warframe" not in s["title"].lower()]
    for s in sections:
        s["items"] = [i for i in s["items"] if "warframe" not in i["text"].lower()]
    return sections


def parse_answers(lines):
    """code -> {item number -> raw answer text}; ranges like '2-5.' fan out."""
    answers = {}
    code = None
    last_numbers = []
    for line in lines:
        heading = ANSWER_HEADING.match(line)
        if heading:
            code = heading.group(1)
            answers.setdefault(code, {})
            last_numbers = []
            continue
        if code is None:
            continue
        match = ANSWER_LINE.match(line)
        if match:
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else start
            text = match.group(3).strip()
            last_numbers = list(range(start, end + 1))
            for n in last_numbers:
                answers[code][n] = text
        elif line.strip() and last_numbers and not line.startswith("#"):
            for n in last_numbers:  # wrapped continuation of the previous answer
                answers[code][n] = (answers[code][n] + " " + line.strip()).strip()
    return answers


def interpret(text):
    """Split free text into (choice, comment). choice in yes/later/no or ''."""
    t = text.strip()
    if not t:
        return "", ""
    first = re.match(r"^([A-Za-z]+)\b[\s,.;:!-]*(.*)$", t, flags=re.S)
    word = first.group(1).lower() if first else ""
    rest = first.group(2).strip() if first else t
    table = {"yes": "yes", "yeah": "yes", "yep": "yes", "now": "yes", "approved": "yes",
             "no": "no", "nope": "no", "drop": "no",
             "later": "later", "maybe": "later", "parked": "later"}
    if word in table:
        return table[word], rest
    return "", t  # a comment with no clear verdict


def parse_for_you():
    """The open entries of planning/FOR-YOU.md as one section of questions for the owner: each `### ` heading
    under "Action items" becomes an item (its number or letter id is kept, e.g. "0d"), text = the heading in
    bold plus the paragraphs joined. Entries that mention the Warframe tracker are left out, like everywhere
    else on the public page data."""
    path = PLANNING / "FOR-YOU.md"
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8").splitlines()
    items, current = [], None
    in_actions = False
    for line in lines:
        if line.startswith("## "):
            in_actions = line.startswith("## Action items")
            current = None
            continue
        if not in_actions:
            continue
        heading = re.match(r"^### (\w+)\.\s+(.*)$", line)
        if heading:
            current = {"n": heading.group(1), "title": heading.group(2).strip(), "body": []}
            items.append(current)
        elif current is not None and line.strip():
            current["body"].append(line.strip())
    out = []
    for entry in items:
        text = f"**{entry['title']}** " + " ".join(entry["body"])
        # "the Warframe tracker" becomes "the tracker"; any other mention drops the item.
        text = re.sub(r"(?i)warframe(?: build)?(?: resource)? tracker", "tracker", text)
        if "warframe" in text.lower():
            continue
        out.append({"n": entry["n"], "text": text, "answered": False})
    if not out:
        return None
    return {"code": "FY", "title": "Open questions from me", "vocab": "recommend", "items": out}


def parse_survey():
    """planning/PLAYER-SURVEY.md as the "About you" round: every `## X. Title` is a section and every numbered
    line a free-text question (vocab "survey": the page shows only a text box, no yes/later/no)."""
    path = PLANNING / "PLAYER-SURVEY.md"
    if not path.exists():
        return None
    sections = parse_questions(path.read_text(encoding="utf-8").splitlines())
    for section in sections:
        section["vocab"] = "survey"
        for item in section["items"]:
            item["answered"] = False
    return sections or None


def parse_dream_game_ideas():
    """planning/DREAM-GAME-IDEAS.md as the "Dream game" round (yes / later / no per puzzle idea per building)."""
    path = PLANNING / "DREAM-GAME-IDEAS.md"
    if not path.exists():
        return None
    sections = parse_questions(path.read_text(encoding="utf-8").splitlines())
    for section in sections:
        for item in section["items"]:
            item["answered"] = False
    return sections or None


def parse_quick_ideas():
    """planning/QUICK-IDEAS.md as the "Quick ideas" round: ordinary yes / later / no items (same item format as
    the ideas rounds), written from the player profile. Answers live only on the page and in the owner account."""
    path = PLANNING / "QUICK-IDEAS.md"
    if not path.exists():
        return None
    sections = parse_questions(path.read_text(encoding="utf-8").splitlines())
    for section in sections:
        for item in section["items"]:
            item["answered"] = False
    return sections or None


def main():
    rounds_out = []
    answers_out = {}
    for spec in ROUNDS:
        lines = (PLANNING / spec["file"]).read_text(encoding="utf-8").splitlines()
        q_lines, a_lines = split_parts(lines, spec["answers_marker"])
        sections = parse_questions(q_lines)
        raw = parse_answers(a_lines)
        round_answers = {}
        for section in sections:
            code = section["code"]
            if code in R_CODES:
                section["vocab"] = "decide"
            section_raw = raw.get(code, {})
            for item in section["items"]:
                text = section_raw.get(item["n"], "")
                choice, comment = interpret(text)
                item["answered"] = bool(text)
                if text:
                    round_answers.setdefault(code, {})[str(item["n"])] = {"c": choice, "m": comment, "raw": text}
        rounds_out.append({"id": spec["id"], "title": spec["title"], "sections": sections})
        answers_out[spec["id"]] = round_answers

    fy = parse_for_you()
    if fy:
        rounds_out.insert(0, {"id": "for-you", "title": "For you", "sections": [fy]})
        answers_out["for-you"] = {}
    dream = parse_dream_game_ideas()
    if dream:
        rounds_out.insert(1 if fy else 0, {"id": "dream-game", "title": "Dream game", "sections": dream})
        answers_out["dream-game"] = {}
    quick = parse_quick_ideas()
    if quick:
        rounds_out.insert(1 if fy else 0, {"id": "quick-ideas", "title": "Quick ideas", "sections": quick})
        answers_out["quick-ideas"] = {}
    survey = parse_survey()
    if survey:
        rounds_out.insert(1 if fy else 0, {"id": "about-you", "title": "About you", "sections": survey})
        answers_out["about-you"] = {}
    (ROOT / "ideas-data.json").write_text(
        json.dumps({"rounds": rounds_out}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (ROOT / "ideas-answers.local.json").write_text(
        json.dumps(answers_out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    for rnd in rounds_out:
        total = sum(len(s["items"]) for s in rnd["sections"])
        done = sum(1 for s in rnd["sections"] for i in s["items"] if i["answered"])
        print(f"{rnd['title']}: {len(rnd['sections'])} sections, {total} items, {done} answered, {total - done} open")


if __name__ == "__main__":
    main()
