"""Regenerate tests/fixtures/puzzles_v1.json after a DELIBERATE generator change (bump SEED_VERSION first)."""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import puzzle as pz  # noqa: E402
import setdata  # noqa: E402

sample = setdata.load_set(HERE.parent / "sets" / "presidents-sample")
puzzles = {}
for sid in sample.section_ids:
    for r in range(2 * len(sample.section_pool(sid))):
        p = pz.make_puzzle(sample, sid, r)
        puzzles[p.code] = {"tray": p.tray, "answer": p.answer}
out = {"seed_version": pz.SEED_VERSION, "puzzles": puzzles}
(HERE / "fixtures" / "puzzles_v1.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
print("wrote", len(puzzles), "puzzles")
