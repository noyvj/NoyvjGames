#!/usr/bin/env python3
"""Freeze wildlife conservation statuses into data/wildlife_status.json (dev tool, never run by the game).

Sources (open, no key; both answer with access-control-allow-origin: *, checked 2026-10-19, so the game's page can read them live):
  GBIF species API  https://api.gbif.org/v1/species/match?name=<scientific name>              the GBIF key
                    https://api.gbif.org/v1/species/<key>/iucnRedListCategory                 the IUCN Red List category (204 = not assessed)
        GBIF publishes the IUCN Red List category and the IUCN taxon id for each species it matches. The IUCN's own API needs a key, so GBIF is the open door
        to the same category. (A status can be newer on the IUCN site than in GBIF: the page says "as published through GBIF on <date>".)
  Wikipedia REST summary  https://en.wikipedia.org/api/rest_v1/page/summary/<name>            first two sentences of the article extract (CC BY-SA 4.0)

Three lists: "current" = one representative species for each of the six wildlife icons in Canopy's wildlife log (owl, fox, deer, frog, butterfly, woodpecker; the choice
of species is a design choice for the owner, the status is not), "boreal" and "tropical" = wildlife for the two new regions.
Usage: python3 tools/fetch_wildlife.py [--read YYYY-MM-DD]      (stdlib only; one request per resource, paced)
"""
import argparse
import datetime
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GAME = Path(__file__).resolve().parent.parent
UA = "NoyvjGames-snapshot/1 (https://noyvj.github.io/NoyvjGames/)"
SPECIES = [
    ("current", "owl", "Tawny owl", "Strix aluco"), ("current", "fox", "Red fox", "Vulpes vulpes"), ("current", "deer", "Red deer", "Cervus elaphus"),
    ("current", "frog", "Common frog", "Rana temporaria"), ("current", "butterfly", "Monarch butterfly", "Danaus plexippus"),
    ("current", "woodpecker", "Great spotted woodpecker", "Dendrocopos major"),
    ("boreal", None, "Canada lynx", "Lynx canadensis"), ("boreal", None, "Reindeer or caribou", "Rangifer tarandus"), ("boreal", None, "Wolverine", "Gulo gulo"),
    ("boreal", None, "Boreal owl", "Aegolius funereus"), ("boreal", None, "Moose", "Alces alces"), ("boreal", None, "Canada warbler", "Cardellina canadensis"),
    ("tropical", None, "Jaguar", "Panthera onca"), ("tropical", None, "Harpy eagle", "Harpia harpyja"), ("tropical", None, "Red-eyed tree frog", "Agalychnis callidryas"),
    ("tropical", None, "Brown-throated sloth", "Bradypus variegatus"), ("tropical", None, "Bornean orangutan", "Pongo pygmaeus"), ("tropical", None, "Toco toucan", "Ramphastos toco"),
    ("tropical", None, "Scarlet macaw", "Ara macao"), ("tropical", None, "Blue morpho", "Morpho menelaus"),
]


def get(url, pause=0.6, allow_empty=False):
    for wait in (pause, 5, 20, 60):
        time.sleep(wait)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"}), timeout=60) as reply:
                raw = reply.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else None
        except urllib.error.HTTPError as err:
            if err.code == 429:
                continue
            raise SystemExit("HTTP %d for %s" % (err.code, url))
    raise SystemExit("still rate limited: " + url)


def two_sentences(text):
    return " ".join(re.split(r"(?<=[.!?])\s+(?=[A-Z])", text.strip())[:2])


def one(group, icon, common, sci):
    match = get("https://api.gbif.org/v1/species/match?name=" + urllib.parse.quote(sci))
    if match.get("matchType") != "EXACT" or match.get("status") != "ACCEPTED" or match.get("canonicalName") != sci:
        raise SystemExit("GBIF does not give one accepted exact match for " + sci)
    key = match["usageKey"]
    iucn = get("https://api.gbif.org/v1/species/%d/iucnRedListCategory" % key)          # None when GBIF answers 204 (not assessed)
    wiki = get("https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(sci.replace(" ", "_")), pause=1.5)
    return {"group": group, "log_icon": icon, "common_name": common, "scientific_name": sci, "gbif_key": key,
            "gbif_url": "https://www.gbif.org/species/%d" % key,
            "iucn": None if not iucn else {"code": iucn.get("code"), "category": iucn.get("category"), "iucn_taxon_id": iucn.get("iucnTaxonID"),
                                          "scientific_name_in_iucn": iucn.get("scientificName"), "taxonomic_status": iucn.get("taxonomicStatus")},
            "wikipedia": {"title": wiki["title"], "url": wiki["content_urls"]["desktop"]["page"], "extract": two_sentences(wiki["extract"])}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--read", default=datetime.date.today().isoformat())
    args = ap.parse_args(argv)
    out = {"topic": "wildlife_status", "read": args.read,
           "sources": [{"name": "GBIF species API (IUCN Red List category as published through GBIF)", "publisher": "Global Biodiversity Information Facility; category from the IUCN Red List of Threatened Species",
                        "url": "https://www.gbif.org/developer/species", "licence": "GBIF API data CC0 / CC BY as marked per dataset; the IUCN Red List terms ask for credit to IUCN"},
                       {"name": "Wikipedia REST page summary", "publisher": "Wikimedia Foundation", "url": "https://en.wikipedia.org/api/rest_v1/",
                        "licence": "CC BY-SA 4.0 (article text); credit Wikipedia and link the article"}],
           "category_words": {"LC": "Least Concern", "NT": "Near Threatened", "VU": "Vulnerable", "EN": "Endangered", "CR": "Critically Endangered", "DD": "Data Deficient",
                              "EW": "Extinct in the Wild", "EX": "Extinct"},
           "live": True, "live_note": "CORS open. Live: GET gbif_key's iucnRedListCategory URL; a 204 answer means not assessed. Fallback: this file.",
           "species": [one(*s) for s in SPECIES]}
    (GAME / "data").mkdir(exist_ok=True)
    (GAME / "data" / "wildlife_status.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote data/wildlife_status.json: %d species, %d with an IUCN category" % (len(out["species"]), sum(1 for s in out["species"] if s["iucn"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
