"""Regenerate the pinned puzzle fixtures after a DELIBERATE generator change (bump that generator's SEED_VERSION first):
puzzles_v1.json (timeline, puzzle.py), web_puzzles_v1.json (cause web, web.py), myth_puzzles_v1.json (myth or record, myth.py)."""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import myth as mq  # noqa: E402
import puzzle as pz  # noqa: E402
import setdata  # noqa: E402
import web as wb  # noqa: E402

sample = setdata.load_set(HERE.parent / "sets" / "presidents-sample")


def write(name, version, puzzles):
    out = {"seed_version": version, "puzzles": puzzles}
    (HERE / "fixtures" / name).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print("wrote", name, len(puzzles), "puzzles")


timeline = {}
for sid in sample.section_ids:
    for r in range(2 * len(sample.section_pool(sid))):
        p = pz.make_puzzle(sample, sid, r)
        timeline[p.code] = {"tray": p.tray, "answer": p.answer}
write("puzzles_v1.json", pz.SEED_VERSION, timeline)

webs = {}
for ch in sample.web_chapters:
    for r in range(2 * len(sample.chapter_relations(ch)) + 2):
        p = wb.make_web_puzzle(sample, ch["id"], r)
        webs[p.code] = {"cards": p.cards, "relations": p.relations}
write("web_puzzles_v1.json", wb.SEED_VERSION, webs)

myths = {}
for ch in sample.myth_chapters:
    for r in range(2 * len(ch["claims"])):
        p = mq.make_myth_puzzle(sample, ch["id"], r)
        myths[p.code] = {"tray": p.tray, "answer": p.answer}
write("myth_puzzles_v1.json", mq.SEED_VERSION, myths)
