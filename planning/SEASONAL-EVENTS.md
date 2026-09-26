# Seasonal events (Round 3 N, redone around real big dates)

**Your direction (Round 3 N):** events are the big "oh, it's Halloween, maybe the site has an event" moments (Christmas, Halloween, New Year, Easter, Hanukkah, Thanksgiving, 4th of July, Valentine's Day and other big ones, and you are still weighing how American-centric to be). Each must be doable within about 15 minutes of starting a game, so a visitor gets a taste and may come back. A game with no natural fit gets a temporary stand-in tied to the date. The next round's section M should list games that could easily host a mode that fits each event.

**Built (groundwork, W-4):** `shared/seasonal_events.py` answers "which events are active on this date" (fixed dates, Easter, nth-weekday holidays such as Thanksgiving, and a sourced table for moving holidays: Hanukkah 2026-2028, Lunar New Year 2026-2032, Diwali 2026-2028, read from Wikipedia on 2026-09-27); `shared/seasonal-dates.json` holds those tables; 11 tests. `DEFAULT_EVENTS` is the starting list and is only data: change it freely.

## The event list and where each lives (proposal: nothing here is built yet, please react)

Each event: a window of days, a flavour banner, one small task doable in about 15 minutes, a badge named `<event>-<year>` (shown on the player's game page and the hub, granted through the existing achievements path; no numeric bonus, no backend).

| Event (window) | Host game | 15-minute task | Fit |
|---|---|---|---|
| New Year (Dec 30 to Jan 3) | SOL | Fund the Near Bodies research tier (the Quick Start goal) during the window: "New Horizons" | natural |
| Valentine's Day (Feb 11 to 15) | Le Champ de Mots | Answer 10 review questions in the French love and friendship vocabulary week during the window | natural (French) |
| Lunar New Year (Feb 16 to 22 in 2026) | Trade Empire | Sell 20 goods to earn the "Festival Market" badge | stand-in (trade fairs) |
| Easter (the four days around it) | Canopy | Find 5 golden seedlings (GB-2): an egg hunt | natural once GB-2 ships |
| 4th of July (Jul 1 to 5) | Grid | Light the grid: reach 50% clean capacity in a session (fireworks-night banner) | stand-in; see the inclusivity note below |
| Halloween (Oct 25 to Nov 1) | Aftermath | Survive one run of storms with resources left ("Night of Storms" flavour) | natural (spooky) |
| Diwali (Nov 5 to 10 in 2026) | Loop | Close the loop once, "festival of lights" banner | stand-in |
| Thanksgiving (the week around it) | Herd | Feed the farm: reach a herd of 10 with methane pressure under 25% ("harvest") | stand-in |
| Hanukkah (its eight days) | Grid | Eight nights: go 8 rounds without a disruption | natural (eight) |
| Christmas (Dec 18 to 26) | Canopy | Replant 5 plots ("Holiday Tree-Planting Drive", your own Round 2 example) | natural |

A game can carry two events at most, and Grid carries two (July and Hanukkah) on purpose: Grid has the "lights" theme.

**Inclusivity note.** This list has three Christian-tradition dates (Easter, Christmas, Halloween's roots), two American-only (4th of July, Thanksgiving), one Jewish, one Hindu, one Chinese and Valentine's and New Year as near-universal. If you want fewer American-centric ones: swap July 4 for a Northern-summer "Midsummer" or a Southern-summer "Long Day" (Australia), and Thanksgiving for a generic "Harvest Festival" (harvest festivals exist worldwide). The engine treats all of these as data, so this is a one-line change per event.

**Southern hemisphere.** Your own timezone is Australian; dates are the same but seasons are flipped, so flavour text should say "harvest" or "long days" rather than "autumn" or "midsummer".

## How an event works (technical sketch)

1. A game lists the event ids it hosts and a small task predicate in its own `game.py` (for example `qualifies(state) -> bool`).
2. On load and each render the game asks `seasonal_events.active_events(today)` for the current events, filters to the ones it hosts, shows a one-line banner (flavour text, the task, a progress count), and checks `qualifies`.
3. When the task completes, the game records the badge id `seasonal_events.badge_id(event)` (for example `halloween-2026`) in its achievements structure (a new `seasonal_badges` list in `achievements_earned`, which the save and account system already carry) and shows a toast.
4. Testing uses a date override (`?event-date=2026-10-31` in the URL, read by the game and passed in as `today`), so every event can be tested any day of the year.
5. The hub shows earned badges next to the player's account achievements.

Nothing needs a new backend or a new save format beyond one optional list.

## Build order

1. First event end to end on Canopy's Christmas drive or SOL's New Year (whichever host game is free first), including the banner, the date override, the badge list and the hub display.
2. Then each remaining event as a small per-game addition using the same module.
3. The Round 4 section M lists games that could easily host a mode for each date (this is your request; the table above is the first draft of that thinking).

## Questions for you (also in FOR-YOU.md)

1. Is the host-game mapping above acceptable, or do you want different games for any date?
2. Which of the American-centric dates do you want to keep, replace or drop?
3. Should badges appear only in the game, or also on the hub next to account achievements? (I recommend both.)
