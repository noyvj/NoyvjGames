"""Authoring aid: turn specs.py + design.py + texts.py into the chapter data files (cases_1.py ... cases_5.py). The generated
files are plain data and are what the game reads; this script is only run by hand when a case is added or reworked.

    python3 tools/build_cases.py
"""

import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import design  # noqa: E402
import specs  # noqa: E402
import texts  # noqa: E402

CHAPTER_DOC = {
    "1": "Chapter 1, First Visits: houses that grow from three rooms to seven. Read the sheet, walk the rooms, pick a bag, name the spirit.",
    "2": "Chapter 2, Misleading Readings: a room's own feature can make a reading look positive. Trust the room the house does not fool.",
    "3": "Chapter 3, Two Presences: two spirits, each in its own room. Name both.",
    "4": "Chapter 4, Keepsakes: a keepsake swamps every reading in its room, and looking at it gives one more line of testimony.",
    "5": "Chapter 5, The Big Houses: ten to fourteen rooms, a bag of four and everything together.",
}


def lit(value, indent):
    if isinstance(value, str):
        pieces = textwrap.wrap(value, 110) or [""]
        if len(pieces) == 1:
            return repr(value)
        pad = " " * indent
        return "(" + ("\n" + pad).join(repr(p + (" " if i < len(pieces) - 1 else "")) for i, p in enumerate(pieces)) + ")"
    return repr(value)


def main():
    by_ch = {}
    for sp in specs.SPECS:
        found = design.design(sp)
        if found is None:
            raise SystemExit("no design for " + sp["id"])
        pool, acc, min_kit, statics = found
        title, client, intro, ending = texts.TEXTS[sp["id"]]
        lines = ["    C(%r, %r, %r, %r,\n" % (sp["id"], title, sp["layout"], sp["truth"][0] if len(sp["truth"]) == 1 else sp["truth"])]
        lines.append("      pool=%r,\n" % (tuple(sorted(pool)),))
        lines.append("      restless=%r,\n" % (sp["restless"],))
        lines.append("      kit=%d, accounts=%r,\n" % (sp["kit"], tuple(acc)))
        if sp["features"]:
            lines.append("      features=%r,\n" % (sp["features"],))
        if sp["keepsake"]:
            lines.append("      keepsake=%r,\n" % (sp["keepsake"],))
        lines.append("      client=%s,\n" % lit(client, 14))
        lines.append("      intro=%s,\n" % lit(intro, 13))
        lines.append("      ending=%s),\n" % lit(ending, 14))
        by_ch.setdefault(sp["id"][0], []).append("".join(lines) + "    # min bag %d, candidates before any reading %s\n" % (min_kit, statics))
    for ch, blocks in sorted(by_ch.items()):
        body = '"""%s"""\n\nfrom casekit import C\n\nCASES = [\n%s]\n' % (CHAPTER_DOC[ch], "".join(blocks))
        (ROOT / ("cases_%s.py" % ch)).write_text(body, encoding="utf-8")
        print("wrote cases_%s.py (%d cases)" % (ch, len(blocks)))


if __name__ == "__main__":
    main()
