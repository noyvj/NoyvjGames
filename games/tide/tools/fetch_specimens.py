#!/usr/bin/env python3
"""Freeze 24 deep-water creatures for Specimen Jars into data/specimens.json (dev tool, never run by the game).

Sources (all open, no key, all answer with access-control-allow-origin: * on 2026-10-19, so the game's page can read them live):
  World Register of Marine Species (WoRMS) REST API  https://www.marinespecies.org/rest/
      AphiaRecordsByName/<name>?like=false&marine_only=true     accepted name, authority, rank, status, taxonomy, AphiaID, LSID, citation
      AphiaVernacularsByAphiaID/<id>                             common names (English kept)
      AphiaAttributesByAphiaID/<id>                              "Body size" entries with unit, dimension and the reference WoRMS cites
  Wikipedia REST summary  https://en.wikipedia.org/api/rest_v1/page/summary/<title>     the first two sentences of the article's extract (CC BY-SA 4.0)
Values are copied as returned, nothing is estimated; a creature whose WoRMS record is not an accepted name is stopped on, not guessed.
Usage: python3 tools/fetch_specimens.py [--read YYYY-MM-DD]      (stdlib only; one request per resource, 0.5 s apart, 1.5 s for Wikipedia; output in the order of SPECIMENS)
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
# scientific name, Wikipedia article title (the species name: Wikipedia redirects it to the right page)
SPECIMENS = [
    ("Vampyroteuthis infernalis", "Vampyroteuthis infernalis"),
    ("Architeuthis dux", "Architeuthis dux"),
    ("Mesonychoteuthis hamiltoni", "Mesonychoteuthis hamiltoni"),
    ("Eurypharynx pelecanoides", "Eurypharynx pelecanoides"),
    ("Chauliodus sloani", "Chauliodus sloani"),
    ("Melanocetus johnsonii", "Melanocetus johnsonii"),
    ("Anoplogaster cornuta", "Anoplogaster cornuta"),
    ("Stomias boa", "Stomias boa"),
    ("Opisthoproctus soleatus", "Opisthoproctus soleatus"),
    ("Macropinna microstoma", "Macropinna microstoma"),
    ("Grimpoteuthis bathynectes", "Grimpoteuthis bathynectes"),
    ("Bathynomus giganteus", "Bathynomus giganteus"),
    ("Stygiomedusa gigantea", "Stygiomedusa gigantea"),
    ("Atolla wyvillei", "Atolla wyvillei"),
    ("Chimaera monstrosa", "Chimaera monstrosa"),
    ("Chlamydoselachus anguineus", "Chlamydoselachus anguineus"),
    ("Mitsukurina owstoni", "Mitsukurina owstoni"),
    ("Latimeria chalumnae", "Latimeria chalumnae"),
    ("Himantolophus groenlandicus", "Himantolophus groenlandicus"),
    ("Pyrosoma atlanticum", "Pyrosoma atlanticum"),
    ("Riftia pachyptila", "Riftia pachyptila"),
    ("Kiwa hirsuta", "Kiwa hirsuta"),
    ("Pseudoliparis swirei", "Pseudoliparis swirei"),
    ("Bathypterois grallator", "Bathypterois grallator"),
]


def get(url, pause=0.5):
    for wait in (pause, 5, 20, 60):                                # a 429 (too many requests) is answered by waiting longer, never by hurrying
        time.sleep(wait)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"}), timeout=60) as reply:
                raw = reply.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else []
        except urllib.error.HTTPError as err:
            if err.code != 429:
                raise SystemExit("HTTP %d for %s" % (err.code, url))
    raise SystemExit("still rate limited: " + url)


def two_sentences(text):
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text.strip())
    return " ".join(parts[:2])


def one(name, title):
    rec = get("https://www.marinespecies.org/rest/AphiaRecordsByName/%s?like=false&marine_only=true" % urllib.parse.quote(name))
    rec = [r for r in rec if r["scientificname"] == name]
    if len(rec) != 1 or rec[0]["status"] != "accepted":
        raise SystemExit("WoRMS has no single accepted record for " + name)
    rec = rec[0]
    aid = rec["AphiaID"]
    names = [v["vernacular"] for v in (get("https://www.marinespecies.org/rest/AphiaVernacularsByAphiaID/%d" % aid) or []) if v.get("language_code") == "eng"]
    sizes = []
    for attr in get("https://www.marinespecies.org/rest/AphiaAttributesByAphiaID/%d" % aid) or []:
        if attr.get("measurementType") == "Body size":
            kids = {c["measurementType"]: c["measurementValue"] for c in attr.get("children", [])}
            sizes.append({"value": attr["measurementValue"], "unit": kids.get("Unit"), "dimension": kids.get("Dimension"), "reference": attr["reference"]})
    wiki = get("https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title.replace(" ", "_")), pause=1.5)
    return {"scientific_name": rec["scientificname"], "authority": rec["authority"], "english_names": names, "aphia_id": aid,
            "rank": rec["rank"], "status": rec["status"],
            "taxonomy": {k: rec[k] for k in ("kingdom", "phylum", "class", "order", "family", "genus")},
            "worms_url": rec["url"], "worms_lsid": rec["lsid"], "worms_citation": rec["citation"], "worms_modified": rec["modified"],
            "body_size": sizes,
            "wikipedia": {"title": wiki["title"], "url": wiki["content_urls"]["desktop"]["page"], "extract": two_sentences(wiki["extract"]), "revision": wiki.get("revision")}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--read", default=datetime.date.today().isoformat())
    args = ap.parse_args(argv)
    out = {"topic": "specimens", "read": args.read,
           "sources": [{"name": "World Register of Marine Species (WoRMS) REST API", "publisher": "WoRMS Editorial Board, Flanders Marine Institute (VLIZ)",
                        "url": "https://www.marinespecies.org/rest/", "licence": "CC BY 4.0 (WoRMS data); cite the record's own citation string"},
                       {"name": "Wikipedia REST page summary", "publisher": "Wikimedia Foundation",
                        "url": "https://en.wikipedia.org/api/rest_v1/", "licence": "CC BY-SA 4.0 (article text); credit Wikipedia and link the article"}],
           "live": True, "live_note": "Both APIs allow cross-origin reads; the page may fetch them and must fall back to this file, naming this file's read date.",
           "specimens": [one(name, title) for name, title in SPECIMENS]}
    (GAME / "data").mkdir(exist_ok=True)
    (GAME / "data" / "specimens.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote data/specimens.json: %d specimens, %d with a WoRMS body size" % (len(out["specimens"]), sum(1 for s in out["specimens"] if s["body_size"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
