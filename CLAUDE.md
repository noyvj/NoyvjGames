# CodingIsANoyvj — Game Demo Hub

Personal portfolio site collecting small AI-assisted game demos. One demo, SOL, is also a dual BCM114/BCM206 university digital artefact — the site's public availability + update history is the evidence for that requirement.

## Structure
```
/ (site root)
  index.html        <- hub/lobby page: title cards, links to each game
  style.css          <- shared minimal shell (nav, title-card grid, review widget)
  script.js          <- hub-only interaction (star rating + review widget, backed by /app)
  manifest.json       <- PWA manifest
  sw.js               <- service worker, stale-while-revalidate (serves cache instantly, refreshes it in the background every request)
  ad-bar.css           <- shared ad bar partial (hub + every game page)
  icons/               <- PWA icons (placeholder art)
  BCM114-DEV-LOG.md    <- running log: individual game content/mechanics/style (see Session logging below)
  BCM206-DEV-LOG.md    <- running log: site infrastructure (hosting, save system, accounts, backend)
  /app
    main.py            <- FastAPI ratings API (POST/GET /ratings), deployed to FastAPI Cloud
    database.py
    models.py
    pyproject.toml     <- dependency manifest; scoped as FastAPI Cloud's Application Directory
  /games
    /sol
      index.html
      style.css
      game.py
      CLAUDE.md      <- SOL-specific context (design, milestones)
      tests/         <- SOL's pytest suite (fake-DOM/Pyodide harness)
    /<future-game>
      ...
  /planning
    site-plan.md
    game-template.md
    pwa-and-ads-setup.md  <- manifest/service worker/ad bar reference
    SAVE-SYSTEM-DESIGN.md  <- save codes + accounts spec — Phase 1 (save codes) built and live, SOL is the reference integration
    <game>-plan.md   <- pre-build groundwork notes per game, before folders exist
```

## Site-level rules
- **Shared shell, free internals.** The hub (nav, title cards, review widget) stays visually consistent. Individual game pages are free to look however they want — no imposed styling once you're inside a game.
- **Cadence:** something new or updated must become visible on the site at least once every 2 weeks. Not every-game-every-week — just *something*.
- **Scope philosophy:** let each game be as big or small as the idea wants. The bar is "visible and real," not "polished/finished." Don't let polish-chasing block shipping.
- **Reviews/ratings:** star rating + comments per game is the public-feedback mechanism for both subjects. Live and persistent: hub's review widget calls the `/app` FastAPI backend (deployed on FastAPI Cloud, Neon Postgres) — see `planning/pwa-and-ads-setup.md` and `app/main.py`.

## Session logging (do this every session, before ending)
Two running logs live at the repo root: `BCM206-DEV-LOG.md` (site infrastructure — hosting, save system, accounts, deployment, backend) and `BCM114-DEV-LOG.md` (individual game content — mechanics, style, narrative, GenAI prompt iteration).

Before ending any session where code or content changed, append one dated entry to whichever log(s) apply — split across both if the session touched both. Follow the entry format already defined inside each log file. Append only — never edit or remove a past entry. If nothing meaningfully changed, skip logging rather than writing a filler entry.

## Per-game conventions (apply inside every `/games/<slug>/`)
- Default stack: Python via Pyodide, plain HTML/CSS, no build step. Deviating (e.g. plain JS for something trivial) is a deliberate documented exception, not a default.
- Each game keeps its own `CLAUDE.md` with concept, constraints, and a numbered milestone table — same format as SOL's.
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag <game-slug>-milestone-0N`.
- Update each game's milestone Status column as work happens, so context here always reflects real state.

## Current games
| Slug | Name | Status |
|------|------|--------|
| sol | SOL | Milestone 11 done (Full system endgame) — all 17 milestones complete, shared save-widget reference integration |
| canopy | Canopy | All 7 milestones + Pass 2 + Pass 3 + Info Page + shared save widget complete, first of the BCM114 climate quartet |
| grid | Grid | All 6 milestones + Pass 2 + Pass 3 + Info Page + shared save widget complete, second of the BCM114 climate quartet |
| tide | Tide | All 7 milestones + Pass 2 + Pass 3 + Info Page + shared save widget complete, third of the BCM114 climate quartet |
| aftermath | Aftermath | All 7 milestones + Pass 2 + Pass 3 + Info Page + shared save widget complete, fourth of the BCM114 climate quartet |
| herd | Herd | All 7 milestones + Pass 2 + Pass 3 + Info Page + shared save widget complete, first of the second climate-quartet set |
| thaw | Thaw | All 7 milestones + Pass 2 + Pass 3 + Info Page + shared save widget complete, second of the second climate-quartet set |
| loop | Loop | All 7 milestones + Pass 2 + Pass 3 + Info Page + shared save widget complete, third of the second climate-quartet set |
| drift | Drift | All 7 milestones + Pass 2 + Pass 3 + Info Page + shared save widget complete, fourth of the second climate-quartet set |
| trade-empire | Trade Empire (working title) | Milestone 14 done (Endgame) — all 14 milestones complete, not yet hub-linked |
| continuum | Continuum (working title) | Phase 1 (Foundation) complete — core sim, sustainability score, research tree, save schema. Flagship BCM114 Round 2 DA (SDG 11). Not yet hub-linked |
| champ-de-mots | Le Champ de Mots (working title) | All 7 milestones complete — SRS engine, runtime question generator, farm grid UI, shared save widget, row-unlock pacing. Personal project (FREN151/152 study tool), not tied to any BCM assessment. Hub-linked, no BCM tag |

## Site-level milestones (separate from per-game milestones)
| # | Milestone | Status |
|---|-----------|--------|
| 1 | Hub shell built (index.html, style.css, title-card layout) | Done |
| 2 | SOL moved into /games/sol, linked from hub | Done |
| 3 | Review/rating UI stub added (no persistence yet) | Done |
| 4 | Site hosting: GitHub Pages + PWA shell + labeled ad bar + ratings backend live (FastAPI Cloud + Neon) | Done — tagged `site-hosting-v1` |
| 5 | Save system Phase 1: save codes (no accounts) live via FastAPI + Neon, SOL reference integration | Done — tagged `save-system-v1` |
| 6 | Accounts (Phase 2, username + password, revised from the original magic-link plan) + save-claim + site-wide feedback: backend + frontend built | Built and committed, not yet deployed/pushed to production — see `planning/ACCOUNTS-AND-FEEDBACK-DESIGN.md` |
| 7 | Shared save widget (`shared/save-widget.js`) rolled out to SOL + all 8 climate games; fixed a site-wide bug where every absolute root-relative path 404'd on GitHub Pages' `/NoyvjGames/` subpath | Done — see `planning/SAVE-BUTTON-INTEGRATION.md` |

## Working notes
- Pre-semester (now): pace can be aggressive, this is largely a boredom-driven creative project.
- Once BCM114/206 outlines drop (~July 27): revisit whether the site alone satisfies "public availability," or whether audience-engagement content (e.g. Instagram) needs to be added back in for BCM114 specifically.
- Once semester workload is live: revisit pacing/scope guardrails for real — deliberately not enforced yet.
