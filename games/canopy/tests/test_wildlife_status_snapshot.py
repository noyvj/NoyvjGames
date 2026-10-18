"""data/wildlife_status.json: IUCN categories (via GBIF) for the wildlife log and the two new regions (tools/fetch_wildlife.py)."""
import json
import re
from pathlib import Path

DATA = json.loads((Path(__file__).resolve().parent.parent / "data" / "wildlife_status.json").read_text(encoding="utf-8"))
SPECIES = DATA["species"]
ICONS = ["owl", "fox", "deer", "frog", "butterfly", "woodpecker"]


def test_sources_and_date():
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", DATA["read"])
    assert len(DATA["sources"]) == 2
    for s in DATA["sources"]:
        for key in ("name", "publisher", "url", "licence"):
            assert s[key]
    assert DATA["live"] is True


def test_three_groups_with_the_six_log_icons_first():
    groups = [s["group"] for s in SPECIES]
    assert groups.count("current") == 6 and groups.count("boreal") == 6 and groups.count("tropical") == 8
    assert [s["log_icon"] for s in SPECIES if s["group"] == "current"] == ICONS
    assert len({s["scientific_name"] for s in SPECIES}) == len(SPECIES)


def test_every_species_has_gbif_link_status_and_extract():
    words = DATA["category_words"]
    for s in SPECIES:
        assert s["gbif_url"] == "https://www.gbif.org/species/%d" % s["gbif_key"]
        assert s["iucn"]["code"] in set(words) | {"NE"} and s["iucn"]["category"], s["scientific_name"]
        assert s["iucn"]["scientific_name_in_iucn"].startswith(s["scientific_name"])
        w = s["wikipedia"]
        assert w["url"].startswith("https://en.wikipedia.org/wiki/") and 40 <= len(w["extract"]) <= 700


def test_known_statuses():
    by = {s["scientific_name"]: s["iucn"]["code"] for s in SPECIES}
    assert by["Pongo pygmaeus"] == "CR" and by["Strix aluco"] == "LC"
    assert by["Rangifer tarandus"] in ("VU", "EN")
