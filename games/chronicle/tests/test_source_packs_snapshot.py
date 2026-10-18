"""data/<pack>.json: three packs of claims, each with three or more checked sources (tools/fetch_source_packs.py)."""
import json
import re
from pathlib import Path

import pytest

import setdata

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PACKS = ["history-of-computing", "history-of-food", "ancient-greece"]
COUNTS = {"history-of-computing": 8, "history-of-food": 3, "ancient-greece": 7}


def load(pack):
    return json.loads((DATA_DIR / (pack + ".json")).read_text(encoding="utf-8"))


@pytest.mark.parametrize("pack", PACKS)
def test_pack_has_its_claims_and_dates(pack):
    data = load(pack)
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", data["read"]) and data["item"] in ("CH-12", "R4-CLP-5")
    assert len(data["claims"]) == COUNTS[pack] == len(data["events"])
    assert len({c["id"] for c in data["claims"]}) == len(data["claims"])
    for c in data["claims"]:
        assert setdata.parse_date(c["value"]) is not None, c["id"]
        assert c["field"] == "date" and c["confidence"] in ("documented", "disputed", "traditional-but-doubtful")
        assert 30 <= len(c["text"]) <= 300 and c["subject"].startswith("e-")


@pytest.mark.parametrize("pack", PACKS)
def test_every_claim_has_three_distinct_sources_from_two_institutions(pack):
    data = load(pack)
    for c in data["claims"]:
        ids = [s["source"] for s in c["sources"]]
        assert len(ids) >= 3 and len(set(ids)) == len(ids), c["id"]
        assert len({data["sources"][i]["institution"] for i in ids}) >= 2, c["id"]
        for s in c["sources"]:
            assert 20 <= len(s["note"]) <= 260 and "“" not in s["note"], (c["id"], s["source"])


@pytest.mark.parametrize("pack", PACKS)
def test_every_source_was_fetched_and_its_text_checked(pack):
    data = load(pack)
    used = {s["source"] for c in data["claims"] for s in c["sources"]}
    assert used == set(data["sources"])
    for sid, src in data["sources"].items():
        assert re.fullmatch(r"[a-z0-9-]+", sid)
        assert src["title"] and src["institution"] and src["kind"]
        assert src["url"].startswith("https://") and src["http_status"] == 200
        assert src["read"] == data["read"] and src["text_checked_for"]


@pytest.mark.parametrize("pack", PACKS)
def test_events_follow_their_claims(pack):
    data = load(pack)
    claims = {c["id"]: c for c in data["claims"]}
    for e in data["events"]:
        assert claims[e["claim"]]["subject"] == e["id"] and claims[e["claim"]]["value"] == e["date"]


def test_known_dates():
    comp = {c["subject"]: c["value"] for c in load("history-of-computing")["claims"]}
    assert comp["e-baby"] == "1948-06-21" and comp["e-arpanet-first"] == "1969-10-29" and comp["e-web-proposal"] == "1989-03"
    greece = {c["subject"]: c["value"] for c in load("ancient-greece")["claims"]}
    assert greece["e-marathon"] == "-0490" and greece["e-socrates-trial"] == "-0399"
