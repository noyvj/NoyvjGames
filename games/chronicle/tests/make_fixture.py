"""Regenerate the pinned puzzle fixtures after a DELIBERATE generator change (bump that generator's SEED_VERSION first):
puzzles_v1.json (timeline, puzzle.py), web_puzzles_v1.json (cause web, web.py), myth_puzzles_v1.json (myth or record, myth.py),
account_puzzles_v1.json (whose account?, account.py), decision_orders_v1.json (decision.py), review_questions_v1.json (review.py)."""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import account as ac  # noqa: E402
import decision as dc  # noqa: E402
import myth as mq  # noqa: E402
import puzzle as pz  # noqa: E402
import review as rv  # noqa: E402
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

accounts = {}
for a in sample.accounts:
    for r in range(2 * len(a["passages"])):
        p = ac.make_account_puzzle(sample, a["id"], r)
        accounts[p.code] = {"order": p.order, "focus": p.focus, "questions": [{"id": q["id"], "options": q["options"], "answer": q["answer"]} for q in p.questions]}
write("account_puzzles_v1.json", ac.SEED_VERSION, accounts)

orders = {d["id"]: dc.option_order(sample, d["id"]) for d in sample.decisions}
write("decision_orders_v1.json", dc.SEED_VERSION, orders)

LABELS = {"confidence": {k: k for k in ("documented", "disputed", "traditional-but-doubtful")}, "strength": {"direct": "direct", "contributing": "contributing"}}
prog = {"learned": set(sample.events), "sorted": set(sample.myth_claim_ids()), "threads": set(sample.web_relation_ids()),
        "decided": {d["id"]: {"picked": d["chosen"]} for d in sample.decisions}}
reviews = {}
for key in rv.all_keys(sample, prog):
    for asked in range(3):
        q = rv.make_question(sample, prog, key, asked, LABELS)
        reviews["%s#%d" % (key, asked)] = {"options": [o["id"] for o in q["options"]], "answer": q["answer"]}
write("review_questions_v1.json", rv.SEED_VERSION, reviews)
