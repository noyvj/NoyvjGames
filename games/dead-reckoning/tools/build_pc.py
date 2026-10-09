"""Regenerate pc.html for THIS game only (never the all-games generator): index.html + pc-config.json -> pc.html.

    python3 games/dead-reckoning/tools/build_pc.py
"""

import importlib.util
import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("generate_pc_pages", root / "scripts" / "generate-pc-pages.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
game = root / "games" / "dead-reckoning"
cfg = json.loads((game / "pc-config.json").read_text(encoding="utf-8"))
(game / "pc.html").write_text(generator.build("dead-reckoning", cfg), encoding="utf-8")
print("wrote", game / "pc.html")
