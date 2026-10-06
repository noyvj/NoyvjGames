# Chronicle (working title): a history game built from expandable idea sets, groundwork plan

Status: PLAN ONLY, decisions recorded 2026-10-07 (see below). No `games/chronicle/` folder exists yet. Written 2026-10-06 after the user asked: "can we build a history teaching game? somehow gamifying learning about big events or small nuances. ancient greece, wwii, history of food, american presidents, etc. this has a ton of places to expand to through idea sets."

## Decisions (the user, 2026-10-07)

- **Audience:** the user and general players, not a classroom product.
- **Core mechanic first:** the timeline builder, then the cause web.
- **First set: American presidents** (not the history of food as originally recommended). The structured terms/elections/events data proves the format at scale; every characterisation needs sources and the set must stay balanced and non-partisan.
- **Content:** the assistant writes the sets (the user does not hand-write claims), and **every claim links three reputable sources**. The user asked for a **report feature** so a player can flag a claim that looks wrong (same pattern as Le Champ de Mots' answer reports: a button on each claim, a backend table, a mark-as-done list on the admin page).
- **Structure:** one game with a set picker, many sets.
- **Order:** Noy2 finishes the first Lexis milestones this round; the Noyvj session builds Chronicle. This is for this round of the TODO only, not a permanent split.
- Milestone 8 below therefore authors the presidents set first (three sources per claim, a review page, then the user's review); the history of food and Ancient Greece follow.

## 1. One-line pitch
One game engine, many history "sets": each set is a data pack (Ancient Greece, the history of food, American presidents, WWII...) that the same game plays, so adding a topic is adding data, not code.

## 2. What makes this different from a quiz
A quiz checks recall. The aim here, matching the user's "big events or small nuances", is understanding: when things happened relative to each other, why they happened, who is telling the story and how reliable they are, and what is a myth. Each mechanic below trains one of those, and none of them is multiple choice for its own sake.

## 3. Mechanics (pick a core, add the rest as milestones)
| Mechanic | What the player does | What it teaches |
|---|---|---|
| **Timeline builder** | Drag event cards onto a timeline; a "nuance" strip shows what else was happening elsewhere | Order, scale, simultaneity (what happened in Persia while Athens had its golden age) |
| **Cause web** | Connect cards with "led to" threads; the game confirms only the links that are well supported and shows the strength of the evidence | Cause and consequence, and that most causes are plural |
| **Whose account?** | Read two short sources about the same event and answer "who wrote this, what did they want, what did they leave out" | Source evaluation, bias, primary against secondary |
| **Myth or record?** | Sort claims into "documented", "disputed" and "myth", with a short explanation each | Nuance, and why popular stories (for example the Marie Antoinette cake line) are often not what happened |
| **Decision points** | See the choices a historical figure actually faced, choose, then see what they did and what followed | Contingency. Labelled honestly as "what they chose", never as alternate history presented as fact |
| **The archive (collection)** | Every set has a gallery of artefacts, people and places that fill in as you learn them, with a completion meter | Completionist reward (the user likes collections); easy to 100% with no luck |
| **Review** | The same facts return later at spaced intervals using the existing spaced-repetition idea from Le Champ de Mots | Retention |

No roguelike or deck mechanics (user preference). Effects get off switches. Everything deterministic and easy to 100%.

## 4. The part that must not go wrong: accuracy
A history game that teaches wrong history is worse than none. So the data format enforces evidence:
- **Every claim carries at least one source** (title, author or institution, URL where one exists, the date it was read), shown to the player in an Info-page style panel, as the other games do.
- **Claims have a confidence level** (documented, disputed, traditional-but-doubtful). The game never presents a disputed claim as settled; "myth or record" is built from the same field.
- **A test fails if any claim lacks a source or a date**, and if two claims in a set contradict each other. A second test checks that every event has a year or a range and that timeline order matches the dates.
- **Human review gate:** the user spot-checks each set before it ships (a review page that lists every claim with its source, written as part of the pipeline). Agent-drafted content is a draft until reviewed.
- **Sensitive sets (WWII, slavery, genocide)** get a content note, plain factual language, and are built after the engine has been proven on lighter sets.
- **Copyright:** original text only; facts are not copyrightable, sentences are, so nothing is copied from textbooks or sites. Images only from public-domain or openly licensed collections with the licence recorded, never generated images (project rule).

## 5. Architecture sketch
- A **set** is a folder of JSON: `entities` (events, people, places, artefacts), `relations` (cause links, with evidence strength), `claims` (each with sources and confidence), `sources`, `sections` (how the set unlocks in order), `reading` (short texts), and optional `timeline_context` (what else was happening).
- A pure-Python engine (the Signal and Continuum pattern): loads a set, builds puzzles from it deterministically (so a puzzle is testable and reproducible), grades answers, tracks progress and review schedule, and saves compactly. A thin view per mechanic.
- The hub gets one game (Chronicle) with a set picker; each set shows its own progress. Sets can be added without redeploying the engine.

## 6. Which sets first
Recommended order, easiest to verify and least risky first:
1. **The history of food**: broad, fun, lots of nuance and myth to bust (the Columbian exchange, how spices were really priced, the invention of the sandwich legend), low sensitivity, and easy for the user to spot-check.
2. **Ancient Greece**: a classic, rich in sources, good for the timeline and "whose account" mechanics (Herodotus against Thucydides).
3. **American presidents**: highly structured (terms, elections, events) so it proves the data format at scale; needs care to stay balanced and non-partisan, with sources for every characterisation.
4. **WWII**: after the engine is proven; with content notes and the "whose account" mechanic at its centre.
Further sets come from the same pipeline (the user's "ton of places to expand to").

## 7. Draft milestones
| # | Milestone |
|---|---|
| 1 | Set format, loader, validation tests (sources, dates, contradictions), a tiny sample set |
| 2 | Timeline builder mechanic and its engine, playable on the sample set |
| 3 | The archive (collection) and progress save; save widget, achievements, tutorial, hub registration |
| 4 | Cause web mechanic |
| 5 | Myth or record, plus the Info page with sources shown for every claim |
| 6 | Whose account? mechanic |
| 7 | Review (spaced repetition) and decision points |
| 8 | Set 1 authored in full (American presidents, three sources per claim, a report-a-problem button on every claim) with the review page, then user review |
| 9 | Set 2 (history of food), then Ancient Greece, and the set picker |
| 10 | Polish, accessibility, Desktop boot |

## 8. Risks
- **Content volume and correctness** are the real cost. The validation tests and the review page exist to make wrong content hard to ship, not to make it fast.
- **Scope creep across topics.** The rule is: the engine is done when set 2 plays without engine changes.
- **Tone.** History touches real suffering. Sensitive sets wait, and use plain, factual language.
- **Reading load.** Keep readings short and reward understanding over memorising dates.

## 9. Questions for the user (each has a recommendation)
1. **Who is it for?** Recommended: you and general players, not a classroom product. If a class is the audience (for a BCM assessment), say so, because it changes how formal the sourcing and the reading level need to be.
2. **Which core mechanic feels most like the game you want?** Recommended: timeline builder first (it works for every set), then the cause web.
3. **Which set first?** Recommended: the history of food.
4. **Content drafting.** Recommended: I (and delegated agents) draft sets from sources read live, you review each set on a review page before it ships. Or you prefer to write the claims yourself?
5. **Is it one game with a set picker, or a separate game per set?** Recommended: one game, many sets.
6. **Order against the other work** (Lexis milestones, the Desktop conversions): recommended to queue it behind Lexis milestone 5.
