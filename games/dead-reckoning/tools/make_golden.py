"""Rewrite tests/golden/*.svg from the current renderer (run after an intentional change to render.py)."""

import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "tests"))

import golden_charts  # noqa: E402

for name, svg in golden_charts.build().items():
    (root / "tests" / "golden" / (name + ".svg")).write_text(svg + "\n", encoding="utf-8")
    print("wrote", name, len(svg))
