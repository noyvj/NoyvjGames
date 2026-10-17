#!/usr/bin/env python3
"""Writes games/champ-de-mots/study-table.html: every French word, phrase and grammar example of the course, week by week,
as plain tables to read and study (no scripts, no quiz, nothing to click except the week links at the top).

    python3 scripts/generate-champ-study-table.py           # write the page
    python3 scripts/generate-champ-study-table.py --check   # exit 1 if the page is out of date

The data is games/champ-de-mots/fren_combined_catalog.json, the same file the game reads, so the page never drifts from the game.
"""
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "games" / "champ-de-mots" / "fren_combined_catalog.json"
OUT = ROOT / "games" / "champ-de-mots" / "study-table.html"

KIND = {"vocab": "words", "phrase": "phrases", "grammar": "grammar", "phonetic": "sounds"}


def esc(text):
    return html.escape(str(text), quote=True)


def week_id(w):
    return f"week-{w['sequence']}"


def build():
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    chapters = {}
    for c in data["chapters"]:
        for wk in c["weeks"]:
            # A chapter lists the course weeks it covers; FREN151 and FREN152 both number their weeks.
            chapters.setdefault((c["number"], wk), c["title"])
    weeks = data["weeks"]
    total = sum(len(t["items"]) for w in weeks for t in w["topics"])

    nav = "".join(
        f'<li><a href="#{week_id(w)}">{esc(w["course"])} week {w["week"]}</a></li>' for w in weeks
    )
    sections = []
    for w in weeks:
        title = chapters.get((w["chapter"], w["week"]), "")
        n_items = sum(len(t["items"]) for t in w["topics"])
        parts = [
            f'<section id="{week_id(w)}" class="week">',
            f'<h2>{esc(w["course"])} · week {w["week"]} <span class="sub">chapter {esc(w["chapter"])}'
            f'{": " + esc(title) if title else ""} · {n_items} entries</span></h2>',
            '<div class="topics">',
        ]
        for t in w["topics"]:
            rows = "".join(
                f'<tr><td lang="fr">{esc(i["fr"])}</td><td lang="en">{esc(i["en"])}</td></tr>' for i in t["items"]
            )
            rule = f'<p class="rule">{esc(t["rule"])}</p>' if t.get("rule") else ""
            parts.append(
                f'<div class="topic"><h3>{esc(t["title"])} <span class="kind">{esc(KIND.get(t["topic_type"], t["topic_type"]))}</span></h3>'
                f'{rule}<table><thead><tr><th scope="col">Français</th><th scope="col">English</th></tr></thead><tbody>{rows}</tbody></table></div>'
            )
        parts.append("</div></section>")
        sections.append("".join(parts))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex">
<title>Le Champ de Mots: word tables by week</title>
<style>
:root {{ --bg: #f6f7fb; --ink: #1b2033; --soft: #4a5275; --line: #c9cfe4; --panel: #ffffff; --accent: #1f4fa3; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg: #0e1020; --ink: #e8e9f0; --soft: #aab0c8; --line: #343a5a; --panel: #181b2b; --accent: #9dbbff; }} }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--ink); font-family: system-ui, sans-serif; line-height: 1.45; }}
main {{ max-width: 1200px; margin: 0 auto; padding: 1rem 1rem 3rem; }}
h1 {{ margin: 0 0 0.3rem; font-size: 1.5rem; }}
.note {{ color: var(--soft); margin: 0.2rem 0 0.8rem; }}
nav ul {{ list-style: none; padding: 0; margin: 0.5rem 0 1.2rem; display: flex; flex-wrap: wrap; gap: 0.4rem; }}
nav a {{ display: inline-block; padding: 0.35rem 0.7rem; border: 1px solid var(--line); border-radius: 999px; color: var(--accent); text-decoration: none; background: var(--panel); }}
nav a:focus-visible, nav a:hover {{ outline: 2px solid var(--accent); }}
.week {{ margin: 0 0 2rem; }}
.week h2 {{ font-size: 1.2rem; margin: 0 0 0.6rem; padding-bottom: 0.3rem; border-bottom: 2px solid var(--accent); }}
.sub {{ font-weight: 400; font-size: 0.9rem; color: var(--soft); }}
.topics {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(21rem, 1fr)); gap: 0.8rem; align-items: start; }}
.topic {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 0.6rem 0.7rem; break-inside: avoid; }}
.topic h3 {{ margin: 0 0 0.3rem; font-size: 1rem; }}
.kind {{ font-size: 0.75rem; font-weight: 400; color: var(--soft); border: 1px solid var(--line); border-radius: 999px; padding: 0 0.45rem; margin-left: 0.3rem; }}
.rule {{ margin: 0 0 0.4rem; font-size: 0.88rem; color: var(--soft); }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.95rem; }}
th {{ text-align: left; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--soft); border-bottom: 1px solid var(--line); padding: 0.15rem 0.3rem; }}
td {{ padding: 0.2rem 0.3rem; border-bottom: 1px solid var(--line); vertical-align: top; }}
td:first-child {{ font-weight: 600; width: 48%; }}
tr:last-child td {{ border-bottom: 0; }}
@media print {{
  :root {{ --bg: #fff; --ink: #000; --soft: #333; --line: #999; --panel: #fff; --accent: #000; }}
  nav {{ display: none; }}
  .week {{ break-before: page; }}
  .topics {{ grid-template-columns: repeat(2, 1fr); }}
}}
</style>
</head>
<body>
<main>
<h1>Le Champ de Mots: every word, week by week</h1>
<p class="note">{len(weeks)} weeks, {total} entries, copied from the game's own word list. FREN151 weeks 1 to 11, then FREN152 weeks 2 to 13. A page to read, with nothing to click or answer.</p>
<nav aria-label="Weeks"><ul>{nav}</ul></nav>
{chr(10).join(sections)}
</main>
</body>
</html>
"""


def main():
    page = build()
    if "--check" in sys.argv:
        sys.exit(0 if OUT.exists() and OUT.read_text(encoding="utf-8") == page else 1)
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(page)} bytes)")


if __name__ == "__main__":
    main()
