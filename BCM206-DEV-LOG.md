# BCM206 Dev Log — Infrastructure Design

This log tracks the **Infrastructure Design** Digital Artefact for BCM206: the site itself — hosting, the save system, accounts, deployment, and any platform/backend work. It is the evidence base for the Operation criterion (chains of build → test → adapt) and for Contextualisation (linking infra decisions to subject theory — Networked Society, Splinternet, AI and Future Networks, or whatever's live in Module II by the time this is written).

**This file is a running log, not a report.** Keep entries short and factual. The BCM206 contextual report gets written *from* this later — don't try to write the polished version here.

---

## Instructions for Claude Code

> Claude: at the end of any session where you touch site infrastructure — hosting/deployment config, the save system, accounts/auth, the database (Neon/FastAPI), the PWA setup, or any backend plumbing — append a new entry to the **Log** section below, in this exact format:
>
> ```
> ### YYYY-MM-DD
> **Touched:** [files/systems changed]
> **Did:** [2-4 sentences — what changed and why]
> **Result:** [what works now that didn't before, or what broke/what's still open]
> ```
>
> Append below the most recent entry — never edit or delete a past entry. If a session touches BOTH infrastructure and individual game content/mechanics, log the infra parts here and log the game-content parts in `BCM114-DEV-LOG.md` instead — split the same session across both files if needed.

---

## Log

*(entries appended below, most recent last)*
