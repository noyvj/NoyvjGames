#!/usr/bin/env python3
"""Freeze 30 ice cores, one per era, into data/ice_cores.json (dev tool, never run by the game).

Source: NOAA National Centers for Environmental Information (NCEI), World Data Service for Paleoclimatology, Paleo Search API
  https://www.ncei.noaa.gov/access/paleo-search/study/search.json?searchText=ice%20core&limit=1000&skip=<n>
  (answers with access-control-allow-origin: *, checked 2026-10-19, so the game's page can read it live; the response is large, about 20 MB for
  the whole text search, so a page should ask for ONE study by its id instead: https://www.ncei.noaa.gov/access/paleo-search/study/search.json?NOAAStudyId=<id>)
Each study has a dataType; only "ICE CORES" studies are used. Each study lists sites (name, place, latitude and longitude, elevation) and data tables with the
age span (earliestYearBP / mostRecentYearBP, years before 1950) and the core length in metres.

Choosing the 30 (deterministic): a dataset is kept only if its study covers ONE site that is a single point, the study title states a span (such as "800KYr
Deuterium Data" or "110,000 Year Ions Data") that agrees within 15% with the span NOAA records, and it is not a cave, ice patch, outcrop, sediment or composite
record. Each site keeps its longest dataset. Then for 30 targets spaced evenly on a log scale from 150 to 800,000 years take the unused site whose span is
closest in log terms. So the collection runs from the last few centuries to eight hundred thousand years, one core per step.
IMPORTANT for the game's wording: the span is that of the NOAA DATASET named in "study_name", which can be shorter than the whole core.

Usage: python3 tools/fetch_ice_cores.py [--read YYYY-MM-DD]      (stdlib only)
"""
import argparse
import datetime
import json
import math
import re
import sys
import time
import urllib.request
from pathlib import Path

GAME = Path(__file__).resolve().parent.parent
UA = "NoyvjGames-snapshot/1 (https://noyvj.github.io/NoyvjGames/)"
SEARCH = "https://www.ncei.noaa.gov/access/paleo-search/study/search.json?searchText=ice%20core&limit=1000&skip="
COUNT, LOW, HIGH = 30, 150, 800000


def get(url):
    time.sleep(1.0)
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=180) as reply:
        return json.loads(reply.read().decode("utf-8"))


def studies():
    out, skip = [], 0
    while True:
        page = get(SEARCH + str(skip))
        out += [s for s in page["study"] if s.get("dataType") == "ICE CORES"]
        if not page["page"][0]["next"] or not page["study"]:
            return out
        skip += 1000


def point(site):
    coords = ((site.get("geo") or {}).get("geometry") or {}).get("coordinates") or []
    if len(coords) != 2:
        return None
    try:
        lat, lon = float(coords[0]), float(coords[1])
    except ValueError:
        return None
    return (lat, lon) if -90 <= lat <= 90 and -180 <= lon <= 180 and "." not in str(coords[1])[:1] else None


SKIP_WORDS = ("patch", "cave", "outcrop", "composite", "sediment", "crater", "cariaco", "speleothem")
GENERIC_SITES = {"greenland", "global", "antarctica", "antarctic composite"}


def title_span(title):
    """The longest span, in years, that the study title states ('800KYr', '110,000 Year', '9-57KYrBP', '0-68ka'), or None."""
    best = None
    for m in re.finditer(r"(\d[\d,]*(?:\.\d+)?)\s*-?\s*(K\s?Yr|ka|Year|Yr)", title, re.I):
        years = float(m.group(1).replace(",", "")) * (1 if m.group(2).lower() in ("year", "yr") else 1000)
        best = years if best is None or years > best else best
    return best


def candidates(all_studies):
    """One entry per site: the dataset whose title states a span that agrees (within 15%) with the span NOAA records for the study."""
    best = {}
    for study in all_studies:
        sites = study.get("site", [])
        old, new = study.get("earliestYearBP"), study.get("mostRecentYearBP")
        stated = title_span(study["studyName"])
        if len(sites) != 1 or not old or new is None or not stated or abs(stated - old) / old > 0.15 or not LOW <= old <= HIGH + 10000:
            continue                      # several cores in one study, or a title that does not state the same span NOAA records
        site = sites[0]
        loc = point(site)
        name = (site.get("siteName") or "").strip()
        text = (name + " " + study["studyName"]).lower()
        if not loc or not name or name.lower() in GENERIC_SITES or any(w in text for w in SKIP_WORDS):
            continue
        props = (site.get("geo") or {}).get("properties") or {}
        elev = props.get("maxElevationMeters")
        if elev not in (None, "") and float(elev) < 0:
            continue
        lengths = [t["coreLengthMeters"] for t in site.get("paleoData", []) if t.get("coreLengthMeters")]
        entry = {"site_name": name, "place": site.get("locationName"), "latitude": loc[0], "longitude": loc[1],
                 "elevation_m": float(elev) if elev not in (None, "") else None,
                 "core_length_m": float(max(lengths)) if lengths else None,
                 "dataset_oldest_year_bp": old, "dataset_newest_year_bp": new,
                 "study_name": study["studyName"], "noaa_study_id": study["NOAAStudyId"], "study_url": study["onlineResourceLink"],
                 "doi": study.get("doi"), "investigators": study.get("investigators"), "contribution_date": study.get("contributionDate"),
                 "publication": ((study.get("publication") or [{}])[0]).get("citation")}
        rank = (entry["dataset_oldest_year_bp"], -int(entry["noaa_study_id"]))
        if name not in best or rank > (best[name]["dataset_oldest_year_bp"], -int(best[name]["noaa_study_id"])):
            best[name] = entry
    return sorted(best.values(), key=lambda e: (e["dataset_oldest_year_bp"], e["site_name"]))


def choose(pool):
    chosen, used = [], set()
    for i in range(COUNT):
        target = math.log(LOW) + (math.log(HIGH) - math.log(LOW)) * i / (COUNT - 1)
        options = [e for e in pool if e["site_name"] not in used]
        pick = min(options, key=lambda e: (abs(math.log(max(e["dataset_oldest_year_bp"], 1)) - target), e["site_name"]))
        used.add(pick["site_name"])
        chosen.append(pick)
    return sorted(chosen, key=lambda e: (e["dataset_oldest_year_bp"], e["site_name"]))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--read", default=datetime.date.today().isoformat())
    args = ap.parse_args(argv)
    pool = candidates(studies())
    cores = choose(pool)
    out = {"topic": "ice_cores", "read": args.read,
           "source": {"name": "NCEI/WDS Paleoclimatology Paleo Search API (ice core studies)", "publisher": "NOAA National Centers for Environmental Information",
                      "url": "https://www.ncei.noaa.gov/access/paleo-search/", "api": SEARCH + "0",
                      "licence": "NOAA data are public; NOAA asks that the original publication, online resource, dataset DOI and access date are cited"},
           "live": True, "live_note": "CORS open. Ask for one study: .../study/search.json?NOAAStudyId=<noaa_study_id>; fall back to this file.",
           "age_unit": "years before present (BP, before 1950); newest can be negative for cores drilled after 1950",
           "candidates_considered": len(pool), "ice_cores": cores}
    (GAME / "data").mkdir(exist_ok=True)
    (GAME / "data" / "ice_cores.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote data/ice_cores.json: %d cores chosen from %d candidate sites (longest %s BP, shortest %s BP)" % (
        len(cores), len(pool), cores[-1]["dataset_oldest_year_bp"], cores[0]["dataset_oldest_year_bp"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
