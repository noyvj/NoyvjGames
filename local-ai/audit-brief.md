# Brief: audit one game's waiting local-AI ideas (agents: follow local-ai/AUDIT.md; this is the checklist)

The default tooling does the free steps for you: `python3 scripts/audit_local_ai.py prepare <slug>` builds the audit worktree and prints the report; `live <slug>` runs the single browser pass; the main session runs `finish`. Use `/usr/bin/python3` if `python3` has no pytest.

Repo: /Users/alexhart/BCM Project folder/bcm206 (NoyvjGames: static Pyodide/Python browser games). The owner's local model (weaker than Claude) pushed branch `origin/local-ai/stack-<slug>` with one commit per Round 4 idea (`local-ai: R4-XXXX-n: ...`). Your job: audit that branch like a careful reviewer, fix small problems, and produce an accept/reject list. Read first: root CLAUDE.md, games/<slug>/CLAUDE.md, local-ai/RULES.md (the rules the local model was given), planning/TODO-NEXT.md entries for your R4 ids (grep "R4-<code>-"; the owner's answer/comment text on each item is the spec).


## Order of work (saves usage): static read FIRST, browser LAST
Phase A, no browser, no server: read every idea commit's diff and fix or revert from the code alone. Use grep to run these mechanical checks on each commit before judging it:
1. Every `getElementById("x")`, `$("x")`, `querySelector("#x")` and `setEnabled("x")` in new JS must have `id="x"` in index.html (or be created by the same code before use).
2. Code that looks up elements at top level of a script loaded in the page head (pc.js, new *.js files) must wait for DOMContentLoaded or be loaded after the DOM.
3. Custom events: the dispatching target (`window.` vs `document.`) must match the target that `addEventListener` uses for that event name.
4. Any `data-*` attribute read by JS must be written by something (grep for where it is set).
5. Any global/function called must be defined somewhere (grep its name across the game folder and shared/).
6. Settings: every new setting needs a control in index.html AND a read on load AND a reset; per-device ones in localStorage not saves.
7. Reduced-motion checks: confirm the condition is not constant-true (e.g. matchMedia result used correctly).
8. Mobile CSS: any `position: fixed` panel must have something that opens it; no renamed existing ids (compare removed/added ids in the diff against other references and shortcuts).
9. Engine actions sent from JS must exist in game.py's handle()/dispatcher and be sent with the arguments it requires.
10. Elements the CSS styles must exist; elements JS adds must have CSS (no stray unstyled visible blocks); pc.css rules must be scoped to the desktop layout.
11. Save contract: get_state key only when non-default; load_state reads it back and validates.
12. A test file tests/test_ai_*.py exists for new Python/behaviour and asserts something real.
Fix what the read finds (small) or revert (not small). Run the game's pytest + flake8 + pc.html regeneration/`--check` after Phase A. 
Phase B, ONE browser session at the end (not per commit): start the server once, verify the surviving features at 1440x900 and 360x740 on index.html and pc.html in a single scripted Playwright pass (console errors, reachability, overflow). Fix whatever that shows. Do not open the browser earlier than this.

Setup (do this inside your own isolated worktree, never in the main checkout):
1. `git fetch -q` ; `git checkout -B audit/<slug> origin/local-ai/stack-<slug>` (the worktree you were given starts on main; this switches it).
2. List what the branch adds on top of main: `git log --format='%h %s' origin/main..HEAD` and `git diff --stat $(git merge-base origin/main HEAD) HEAD`. The commits with subjects NOT starting `R4-`-style idea ids ("local-ai: long-context mode...", "Scripts: start a new game...", "Start 31 planned games...", "local-ai: make_todo_tasks..." etc.) are shared tooling commits the main session reviews separately: ignore them and do not edit their files (scripts/, local-ai/, games/<other>/ scaffolds).

For EACH idea commit (one at a time, in order):
- Scope: it must change only files inside games/<slug>/ (plus tests there). Anything outside = reject or revert that part and say so.
- Read the diff against the idea text and the standing rules: nothing timed, nothing lost or punishing, no luck needed for 100%, no audio files, every new animation/effect respects reduced motion and has an off switch, accessibility (labels, 44px targets, keyboard path, aria-live), light theme contrast, phone width 360px with no horizontal scroll, Desktop (pc.html) path where relevant.
- Save contract: new keys appear in get_state() only when non-default, load_state accepts saves missing them, every loaded value validated; per-device settings in localStorage not saves; data that must survive reload is both in get_state() AND read back in load_state() (the model has lost data this way before).
- Real wiring check, not just tests: the new UI must actually be reachable (an element id that exists in index.html AND is referenced by JS; a panel that has a way to open; handlers bound to ids that exist; no undefined variables). The model's previous batches had: undefined variable in a drag handler, a panel with no way to open it, a handler matching nothing, loading before the shell built its DOM, wrong save shape. Look hard for exactly these.
- Tests it added are meaningful (not deleted assertions, not tautologies), and test files are named tests/test_ai_*.py.
Then run the game's tests: `cd games/<slug> && python3 -m pytest -q` (that game only; never pkill pytest), `python3 -m flake8 --extend-ignore=E501 games/<slug>` and the narrow shared checks `python3 -m pytest -q shared/tests -k "<slug> or site_includes or hidden_attribute or pc"` ; regenerate this game's pc.html ONLY via importlib `build("<slug>", cfg)` from scripts/generate-pc-pages.py (it RETURNS the html string; write it yourself; never run the all-games generator), then `python3 scripts/generate-pc-pages.py --check`. Verify live in headless Playwright against http://localhost:8073 (start `python3 -m http.server 8073` from the worktree root only if nothing serves it; stop it if you started it; for the worktree, serve the worktree's own directory, e.g. a different port such as 8074 if 8073 is taken) at 1440x900 and 360x740 on index.html and pc.html: no console errors, the new features really reachable and working, no horizontal overflow. Never submit anything to the live backend.

Fix policy: fix SMALL problems yourself on branch `audit/<slug>` with a separate commit per fix (message `Audit fix <R4 id>: ...`, ending with the line `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`; commit with explicit paths inside games/<slug>/ only, never git add -A, never push, stash or reset --hard, never touch main). If an idea is broken beyond a small fix, REVERT it with `git revert` in its own commit and list it as rejected with the reason. Do not edit planning/ files, shared/, sw.js, app/, hub root files or other games; list needed changes there in your report instead.

Final report (short, structured): (1) ACCEPTED ids (working, rules-compliant, owner's item satisfied in full) ; (2) PARTIAL ids (what is done, what remains, so the TODO item stays open) ; (3) REJECTED/REVERTED ids with reason ; (4) fixes you made with commit hashes ; (5) final test count, flake8 and --check status ; (6) precache needs (new files the game fetches at load not in sw.js) ; (7) owner questions ; (8) what you could not verify. The branch name to merge is `audit/<slug>`.
