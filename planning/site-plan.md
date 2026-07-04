# Site Plan — Game Demo Portfolio (working name: CodingIsANoyvj)

## What this is
A personal hub site collecting small AI-assisted game demos, one of which (SOL) is the dual BCM114/BCM206 DA. The site itself — being publicly accessible and updated — is the "public availability" evidence for both subjects, replacing the need for a separate Instagram/devlog trail. Instagram stays optional/low-effort if 114's rubric wants audience-engagement content specifically (confirm once the outline drops July 27).

## Purpose
Equal parts: a real portfolio (future job/collaborator use), a personal creative outlet, and a way to test "do I want to be a game developer" by throwing ideas at a wall and seeing what people think. The DA requirement rides on top of this rather than driving it.

## Structure
- **Hub/lobby page** — "main menu" style. Title card (image placeholder + name) per game, grid or list layout, links into each game's own page.
- **Reviews/feedback** — star rating + comments per game, visible on the hub or each game's page. This is your public-feedback mechanism for both subjects.
  - **Open technical question:** needs shared/persistent storage (not localStorage — that's private per-browser). Depends on what your friend's hosting can support (database? just static files?). Until resolved, build the UI as a front-end stub with no real persistence, clearly marked TODO.
- **Individual game pages** — each fully free to look however it wants once you're inside it. No imposed styling beyond getting there via the hub.
- **Shared minimal shell** — hub nav/branding/title-card format/review widget stays consistent across the whole site; internals of each game do not have to match it or each other.

## Scope philosophy
- Each game gets as big as the idea wants — no forced "make it small" cap.
- The failure mode to actively avoid is polish-paralysis: endless refinement chasing "good enough to publish" that never ships. The bar is **visible and real**, not finished.
- If an idea is dumb and takes 2 minutes, ship it. If an idea has legs, let it grow. Either outcome is useful data.

## Pacing
- No fixed weekly cadence tied to specific games. The only hard rule: **something new or updated becomes visible on the site at least once every 2 weeks.**
- Each game internally still uses the SOL-style numbered milestone approach — one clearly separable, demonstrable stage at a time — but milestones aren't mapped 1:1 to calendar weeks. Build and tag whenever a milestone is actually done; only the "ship visibly" cadence is time-bound.
- Right now (pre-semester, boredom-driven) the pace can be aggressive. Once the semester starts and other subjects are live, pacing gets revisited for real — deliberately deferred rather than solved in advance.

## Branding
- Working site name: **CodingIsANoyvj** (placeholder — confirm before anything public launches)
- Hub-level visual identity: clean, simple, consistent — think a "school games site" main menu (title card + name per game), not a corporate portfolio.

## Hosting
- Friend-hosted (specifics TBD). Whatever the review/rating persistence solution ends up being will depend on what that hosting setup actually supports — revisit once known.
