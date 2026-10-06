"""The ideas answer sheet is a private tool: unlisted, noindex, and free of the
Warframe tracker (which stays off every public page)."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_ideas_page_is_noindex_and_unlinked():
    assert 'name="robots" content="noindex, nofollow"' in (ROOT / "ideas.html").read_text(encoding="utf-8")
    pages = list(ROOT.glob("*.html")) + list((ROOT / "games").glob("*/index.html"))
    for page in pages:
        if page.name == "ideas.html":
            continue
        assert "ideas.html" not in page.read_text(encoding="utf-8"), page
    for name in ("script.js", "sw.js", "manifest.json"):
        assert "ideas.html" not in (ROOT / name).read_text(encoding="utf-8"), name


def test_ideas_data_has_no_warframe_and_no_answer_text():
    raw = (ROOT / "ideas-data.json").read_text(encoding="utf-8")
    assert "warframe" not in raw.lower()
    data = json.loads(raw)
    for rnd in data["rounds"]:
        for sec in rnd["sections"]:
            for item in sec["items"]:
                assert set(item) <= {"n", "tag", "text", "group", "answered"}


def test_owner_links_live_only_in_the_owner_script():
    js = (ROOT / "shared" / "owner-links.js").read_text(encoding="utf-8")
    assert 'const OWNER = "noyvj"' in js
    for link in ("admin.html", "ideas.html", "warframe_build_tracker/index.html"):
        assert link in js
    for name in ("index.html", "script.js", "style.css"):
        text = (ROOT / name).read_text(encoding="utf-8").lower()
        assert "warframe" not in text, name
        assert "owner-nav" not in text or name == "style.css", name
    assert "owner-links.js" in (ROOT / "index.html").read_text(encoding="utf-8")
