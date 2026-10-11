"""The About page and sources.json: every real-world fact names a source and the date it was read live, and the bundled sources list matches."""

import json
import re
from pathlib import Path

import game
import info

GAME_DIR = Path(__file__).resolve().parent.parent
SOURCES = json.loads((GAME_DIR / "sources.json").read_text(encoding="utf-8"))
APP = (GAME_DIR / "app.js").read_text(encoding="utf-8")
HTML = (GAME_DIR / "index.html").read_text(encoding="utf-8")


def test_every_fact_has_a_heading_a_tie_in_and_a_named_source_with_a_read_date():
    assert len(info.FACTS) >= 4
    assert len({f["id"] for f in info.FACTS}) == len(info.FACTS)
    for f in info.FACTS:
        assert f["heading"] and 60 < len(f["fact"]) < 600 and f["tie_in"], f["id"]
        s = f["source"]
        assert s["title"] and s["publisher"] and s["url"].startswith("https://"), f["id"]
    v = info.view()
    assert all(f["source"]["date_read"] == info.DATE_READ for f in v["facts"]) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", info.DATE_READ)


def test_the_page_says_plainly_that_the_game_is_a_simplification():
    text = info.FRAMING.lower()
    assert "not an optics simulator" in text and "prism" in text and "two" in text
    assert any("simplified" in f["tie_in"].lower() for f in info.FACTS)


def test_there_is_a_fact_about_each_thing_the_player_does():
    headings = " ".join(f["heading"].lower() for f in info.FACTS)
    for word in ("mirror", "prism", "filter"):
        assert word in headings


def test_sources_json_matches_the_about_page():
    assert SOURCES["game"] == "mirror-lab" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", SOURCES["updated"])
    research = {(r["title"], r["url"], r["read"]) for r in SOURCES["research"]}
    expected = {(f["source"]["title"], f["source"]["url"], info.DATE_READ) for f in info.FACTS}
    assert research == expected
    for r in SOURCES["research"]:
        assert r["by"] and r["note"]
    assert any(o["title"] == "Pyodide" for o in SOURCES["other"]) and SOURCES["inspiration"] == []


def test_the_view_carries_the_about_page_and_the_page_draws_it_with_the_source_and_date():
    v = game.game.view()
    assert v["info"] == info.view() and v["info"]["pledge"] and v["info"]["how"]
    for needle in ("fact.source.url", "fact.source.date_read", "Read on", "noopener noreferrer", "info-page-sources"):
        assert needle in APP
    for needle in ('id="info-page-panel"', 'id="info-page-toggle-button"', 'id="info-page-sources"', "About Mirror Lab"):
        assert needle in HTML


def test_the_pledge_is_true():
    text = " ".join(info.PLEDGE).lower()
    for claim in ("no timer", "nothing is lost", "no randomness", "free", "no sound"):
        assert claim in text
