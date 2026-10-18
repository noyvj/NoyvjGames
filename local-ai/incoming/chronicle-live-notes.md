# Chronicle: LA-7 live-data notes (2026-10-19)

Steps are in `local-ai/incoming/chronicle-live.txt` (lint: 0 problems), one chain `LA7-CHRONICLE` of 10 steps: a test file first, then for each of three sets the evidence files, the events, sections and readings, and the registration in `sets/index.json`. Data: `games/chronicle/data/history-of-computing.json`, `ancient-greece.json`, `history-of-food.json`, rebuilt and re-checked by `tools/fetch_source_packs.py`, tested by `tests/test_source_packs_snapshot.py`. I also assembled the three sets in a scratch folder with the steps' recipe and `setdata.validate` returned no problems for all three.

## What was frozen and checked
Every claim has three sources from at least two institutions or authors. Each page was fetched on 2026-10-19 (HTTP 200) and its text had to contain the dates or names the claim needs (the patterns are stored in the file). All sentences and notes are original; nothing is quoted. Pages that refused the script (HTTP 403: Encyclopaedia Britannica, the Smithsonian, the Library of Congress, UCL, the Met Museum rate limit) were not used.
| Pack | Item | Claims | Count asked | Sources |
|------|------|--------|-------------|---------|
| history-of-computing | R4-CLP-5 | 8: Lovelace's paper on the Analytical Engine (1843), ENIAC announced (1946-02-14), the transistor (1947-12), the Manchester Baby (1948-06-21), the first ARPANET message (1969-10-29), the IBM PC (1981-08-12), the ARPANET's TCP/IP switch (1983-01-01), the Web proposal (1989-03) | "a set" (no number) | Computer History Museum, IEEE ETHW, Bodleian Libraries, Science Museum Group, Penn Engineering, Nobel Prize Outreach, Science and Industry Museum, University of Manchester, SRI, IBM, Internet Society, RFC Editor, W3C, CERN |
| ancient-greece | CH-12 | 7: Cleisthenes (-0508), Marathon (-0490), Thermopylae (-0480), Salamis (-0480-09), the Parthenon begun (-0447), the trial of Socrates (-0399), the death of Alexander (-0323-06) | "a set" | World History Encyclopedia, Livius.org (Jona Lendering), Hellenic Heritage, the Acropolis Restoration Service, Stanford Encyclopedia of Philosophy, Internet Encyclopedia of Philosophy |
| history-of-food | CH-12 | 3: the Pure Food and Drugs Act (1906-06-30), Haber's ammonia synthesis honoured by the 1918 Nobel Prize, Borlaug's 1970 Nobel Peace Prize | "a set" | FDA, U.S. House History, Nobel Prize Outreach, Science History Institute, Texas A&M Borlaug Institute |

## Left out because three real pages could not be reached
For the food set I could not confirm three pages for: the oldest known bread (14,400 years, the PNAS paper and university pages refuse scripts), canning (Appert, 1810), pasteurisation, the Columbian Exchange, Vasco da Gama's arrival in Calicut (1498), and the potato famine (only one open page each). The Olympic Games of 776 BCE and the Peloponnesian War (431 to 404 BCE) had only one or two open pages. These can be added later; the script has one table to edit. Because of this the food set has 3 events, below the size a pleasant set needs; the steps use section size 2 for it.

## A list (`[local AI: in steps]`)
Assembling the three set folders from the packs and registering them as drafts. Choices fixed in the steps: two sections (s1, s2) per set, no people or places, no relations, one reading per section made of the claim texts, `status: draft`. Places, people, the cause web, accounts, decisions and "elsewhere" events are not stepped.

## C list (not for the local AI)
| Item | Label | Reason |
|------|-------|--------|
| More claims for CH-12 and R4-CLP-5 | `[Claude: live web data]` | Needs more research with three sources per claim (the list above). |
| Review of the sets | `[needs you]` | `review.html` shows every claim with its sources; the owner decides whether the three sets reach "reviewed". |

## For the Claude who audits
- Registering a set changes `core.SET_ORDER`; `tests/test_engine.py` pins the list of sets, and the tutorial text in `app-1-core.js` says "Today there is one". The last step tells the AI to fix the test pins only; update the tutorial text and the set picker copy yourself if wanted.
- Chronicle has no `sw.js` or `offline-manifest.json` entry yet, so there is nothing to register there.
