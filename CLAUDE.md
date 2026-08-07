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
    <game>-plan.md   <- pre-build groundwork notes per game, before folders exist
```

## Site-level rules
- **Shared shell, free internals.** The hub (nav, title cards, review widget) stays visually consistent. Individual game pages are free to look however they want — no imposed styling once you're inside a game.
- **Cadence:** something new or updated must become visible on the site at least once every 2 weeks. Not every-game-every-week — just *something*.
- **Scope philosophy:** let each game be as big or small as the idea wants. The bar is "visible and real," not "polished/finished." Don't let polish-chasing block shipping.
- **Reviews/ratings:** star rating + comments per game is the public-feedback mechanism for both subjects. Live and persistent: hub's review widget calls the `/app` FastAPI backend (deployed on FastAPI Cloud, Neon Postgres) — see `planning/pwa-and-ads-setup.md` and `app/main.py`.

## Per-game conventions (apply inside every `/games/<slug>/`)
- Default stack: Python via Pyodide, plain HTML/CSS, no build step. Deviating (e.g. plain JS for something trivial) is a deliberate documented exception, not a default.
- Each game keeps its own `CLAUDE.md` with concept, constraints, and a numbered milestone table — same format as SOL's.
- Commit + tag per milestone: `git commit -m "Milestone N: <name>"` then `git tag <game-slug>-milestone-0N`.
- Update each game's milestone Status column as work happens, so context here always reflects real state.

## Current games
| Slug | Name | Status |
|------|------|--------|
| sol | SOL | Milestone 11 done (Full system endgame) — all 17 milestones complete |
| canopy | Canopy | Milestone 7 done (Visual pass + hub integration) — all 7 milestones complete, first of the BCM114 climate quartet |
| grid | Grid | Milestone 6 done (UI/visual pass + hub integration) — all 6 milestones complete, second of the BCM114 climate quartet |
| tide | Tide | Milestone 7 done (Visual/UI pass + hub integration) — all 7 milestones complete, third of the BCM114 climate quartet |
| aftermath | Aftermath | Milestone 7 done (Visual/UI pass + hub integration) — all 7 milestones complete, fourth of the BCM114 climate quartet |
| herd | Herd | Milestone 7 done (Visual/UI pass + hub integration) — all 7 milestones complete, first of the second climate-quartet set |
| thaw | Thaw | Milestone 7 done (Visual/UI pass + hub integration) — all 7 milestones complete, second of the second climate-quartet set |
| loop | Loop | Milestone 7 done (Visual/UI pass + hub integration) — all 7 milestones complete, third of the second climate-quartet set |
| drift | Drift | Milestone 1 done (Core allocation loop) — 1 of 7 milestones, fourth of the second climate-quartet set |

## Site-level milestones (separate from per-game milestones)
| # | Milestone | Status |
|---|-----------|--------|
| 1 | Hub shell built (index.html, style.css, title-card layout) | Done |
| 2 | SOL moved into /games/sol, linked from hub | Done |
| 3 | Review/rating UI stub added (no persistence yet) | Done |
| 4 | Site hosting: GitHub Pages + PWA shell + labeled ad bar + ratings backend live (FastAPI Cloud + Neon) | Done — tagged `site-hosting-v1` |

## Working notes
- Pre-semester (now): pace can be aggressive, this is largely a boredom-driven creative project.
- Once BCM114/206 outlines drop (~July 27): revisit whether the site alone satisfies "public availability," or whether audience-engagement content (e.g. Instagram) needs to be added back in for BCM114 specifically.
- Once semester workload is live: revisit pacing/scope guardrails for real — deliberately not enforced yet.
