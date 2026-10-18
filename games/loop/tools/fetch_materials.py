#!/usr/bin/env python3
"""Freeze a short real-world fact for each of 24 materials into data/materials.json (dev tool, never run by the game).

Source: Wikipedia REST page summary   https://en.wikipedia.org/api/rest_v1/page/summary/<title>
(access-control-allow-origin: *, checked 2026-10-19, so the game's page can read one material live; this file is the fallback).
The fact is the first two sentences of the article's `extract`, copied exactly. Text under CC BY-SA 4.0: the card must name Wikipedia, link the article and say the licence.

Six materials for each of Loop's three goods categories (electronics, clothing, furniture) and six for the secret Ship-Breaking Yard (GH-14).
Which material belongs to which category is the game's own choice (a design choice for the owner); the facts are Wikipedia's.
Usage: python3 tools/fetch_materials.py [--read YYYY-MM-DD]      (stdlib only; 1.5 s between requests; output in the order below)
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
MATERIALS = {
    "electronics": ["Copper", "Gold", "Lithium", "Cobalt", "Silicon", "Aluminium"],
    "clothing": ["Cotton", "Wool", "Polyester", "Nylon", "Linen", "Silk"],
    "furniture": ["Oak", "Pine", "Bamboo", "Rattan", "Glass", "Polyurethane"],
    "shipyard": ["Iron", "Steel", "Nickel", "Chromium", "Manganese", "Zinc"],
}


def get(title):
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title)
    for wait in (1.5, 8, 30, 90):
        time.sleep(wait)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"}), timeout=60) as reply:
                return json.loads(reply.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            if err.code != 429:
                raise SystemExit("HTTP %d for %s" % (err.code, url))
    raise SystemExit("still rate limited: " + url)


def two_sentences(text):
    return " ".join(re.split(r"(?<=[.!?])\s+(?=[A-Z])", text.strip())[:2])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--read", default=datetime.date.today().isoformat())
    args = ap.parse_args(argv)
    out = []
    for category, titles in MATERIALS.items():
        for title in titles:
            page = get(title)
            if page.get("type") != "standard" or not page.get("extract"):
                raise SystemExit("no standard article for " + title)
            out.append({"category": category, "material": title, "article_title": page["title"], "fact": two_sentences(page["extract"]),
                        "url": page["content_urls"]["desktop"]["page"], "api": "https://en.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(title),
                        "revision": page.get("revision"), "page_timestamp": page.get("timestamp")})
    data = {"topic": "materials", "read": args.read,
            "source": {"name": "Wikipedia REST page summary", "publisher": "Wikimedia Foundation", "url": "https://en.wikipedia.org/api/rest_v1/",
                       "licence": "CC BY-SA 4.0 (article text); credit Wikipedia, link the article, say the licence"},
            "live": True, "live_note": "CORS open. Live: fetch the material's `api` URL and take `extract` (first two sentences); fall back to this file's `fact`.",
            "materials": out}
    (GAME / "data").mkdir(exist_ok=True)
    (GAME / "data" / "materials.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote data/materials.json: %d materials" % len(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
