"""The word tables page (games/champ-de-mots/study-table.html) is generated from the game's own catalog and never drifts from it."""

import html
import json
import subprocess
import sys
from pathlib import Path

GAME = Path(__file__).resolve().parents[1]
ROOT = GAME.parents[1]


def test_the_page_is_up_to_date_with_the_catalog():
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "generate-champ-study-table.py"), "--check"])
    assert result.returncode == 0, "run: python3 scripts/generate-champ-study-table.py"


def test_every_catalog_entry_is_on_the_page_and_the_page_has_no_scripts():
    page = (GAME / "study-table.html").read_text(encoding="utf-8")
    catalog = json.loads((GAME / "fren_combined_catalog.json").read_text(encoding="utf-8"))
    for week in catalog["weeks"]:
        assert f'id="week-{week["sequence"]}"' in page
        for topic in week["topics"]:
            assert html.escape(topic["title"], quote=True) in page
            for item in topic["items"]:
                assert html.escape(item["fr"], quote=True) in page
                assert html.escape(item["en"], quote=True) in page
    assert "<script" not in page.lower()
