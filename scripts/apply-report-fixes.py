#!/usr/bin/env python3
"""Tick "fixed" (with a one-line note) on the live Le Champ de Mots answer reports that the data review fixed.

Reads games/champ-de-mots/tests/report_review.json (written by the 2026-10-08 review) and, for every report
whose outcome is "fixed", calls PATCH /answer-reports/{id}/fixed on the live backend with the AI admin token
from the gitignored `.ai-admin-token` file at the repo root (the token is only ever sent as the X-Admin-Token
header and is never printed).

    python3 scripts/apply-report-fixes.py                   # dry run: lists what it would tick
    python3 scripts/apply-report-fixes.py --apply            # ticks them
    python3 scripts/apply-report-fixes.py --apply --include needs-code
                                                            # also tick the ones that needed a game.py change,
                                                            # once that change has shipped

Run it only after the backend has been redeployed with the `is_fixed` column (the route answers 404 or 405
before that). It never ticks "done" (that stays the owner's), never touches reports whose outcome is not-a-bug,
duplicate, test-row, needs-owner, and is safe to re-run (it skips reports that are already fixed).
"""
import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REVIEW = ROOT / "games" / "champ-de-mots" / "tests" / "report_review.json"
API = "https://noyvjgames.fastapicloud.dev"


def review_rows():
    data = json.loads(REVIEW.read_text(encoding="utf-8"))
    stack, rows = [data], []
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            if "report_id" in item and "outcome" in item:
                rows.append(item)
            else:
                stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
    return rows


def call(method, path, token, body=None):
    request = urllib.request.Request(
        API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
        headers={"X-Admin-Token": token, "Content-Type": "application/json", "User-Agent": "noyvjgames-apply-report-fixes/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="really tick them (default is a dry run)")
    parser.add_argument("--include", action="append", default=[], help="extra outcome to tick, e.g. needs-code")
    args = parser.parse_args()
    wanted = {"fixed", *args.include}
    rows = [r for r in review_rows() if r["outcome"].split(":")[0] in wanted]
    print(f"{len(rows)} reports with outcome in {sorted(wanted)}")
    token_file = ROOT / ".ai-admin-token"
    if args.apply and not token_file.exists():
        sys.exit("No .ai-admin-token file at the repo root.")
    token = token_file.read_text().strip() if token_file.exists() else ""
    live = {}
    if args.apply:
        for report in call("GET", "/answer-reports?game_id=champ-de-mots", token):
            live[report["id"]] = report
    done = skipped = failed = 0
    for row in rows:
        if args.apply and len(row["report_id"]) < 36:
            # Reports reviewed later carry the 8-character prefix of their id.
            full = [rid for rid in live if rid.startswith(row["report_id"])]
            if len(full) != 1:
                failed += 1
                print(f"  FAILED {row['report_id']}: {len(full)} live reports match that prefix")
                continue
            row = dict(row, report_id=full[0])
        note = (row.get("note") or "Fixed in the 2026-10-08 data review")[:300]
        if not args.apply:
            print(f"  would tick {row['report_id'][:8]}  {row['item_id']}: {note[:90]}")
            continue
        if live.get(row["report_id"], {}).get("is_fixed"):
            skipped += 1
            continue
        try:
            call("PATCH", f"/answer-reports/{row['report_id']}/fixed", token, {"fixed": True, "note": note})
            done += 1
        except urllib.error.HTTPError as error:
            failed += 1
            print(f"  FAILED {row['report_id'][:8]}: HTTP {error.code}")
    if args.apply:
        print(f"ticked {done}, already fixed {skipped}, failed {failed}")


if __name__ == "__main__":
    main()
