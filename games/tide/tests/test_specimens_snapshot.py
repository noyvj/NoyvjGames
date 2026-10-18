"""data/specimens.json: 24 deep-water creatures from WoRMS and Wikipedia (tools/fetch_specimens.py)."""
import json
import re
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "specimens.json").read_text(encoding="utf-8"))
SPECIMENS = DATA["specimens"]


def test_sources_and_date():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", DATA["read"])
    assert len(DATA["sources"]) == 2
    for s in DATA["sources"]:
        for key in ("name", "publisher", "url", "licence"):
            assert s[key]
    assert DATA["live"] is True


def test_twenty_four_unique_accepted_marine_species():
    assert len(SPECIMENS) == 24
    assert len({s["scientific_name"] for s in SPECIMENS}) == 24 == len({s["aphia_id"] for s in SPECIMENS})
    for s in SPECIMENS:
        assert s["status"] == "accepted" and s["rank"] == "Species"
        assert s["worms_url"] == "https://www.marinespecies.org/aphia.php?p=taxdetails&id=%d" % s["aphia_id"]
        assert s["worms_lsid"] == "urn:lsid:marinespecies.org:taxname:%d" % s["aphia_id"]
        assert s["worms_citation"].startswith(("MolluscaBase", "WoRMS", "Froese", "Horton", "Eschmeyer", "FishBase", "Kirkendale")) or "World Register of Marine Species" in s["worms_citation"]
        assert s["taxonomy"]["kingdom"] == "Animalia" and s["taxonomy"]["genus"] == s["scientific_name"].split()[0]


def test_each_card_has_a_wikipedia_extract_and_link_and_sane_sizes():
    for s in SPECIMENS:
        w = s["wikipedia"]
        assert w["url"].startswith("https://en.wikipedia.org/wiki/") and 40 <= len(w["extract"]) <= 700 and w["title"]
        for b in s["body_size"]:
            assert 0 < float(b["value"]) < 100000 and b["unit"] in ("cm", "mm", "m"), (s["scientific_name"], b)
            assert b["reference"]


def test_a_few_names():
    by = {s["scientific_name"]: s for s in SPECIMENS}
    assert "vampire squid" in by["Vampyroteuthis infernalis"]["english_names"]
    assert by["Latimeria chalumnae"]["taxonomy"]["family"] == "Latimeriidae"
