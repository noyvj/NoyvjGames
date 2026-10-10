# Making the site an installable app, with some games only playable there (talk, not a plan)

Written 2026-10-09 because you asked (FOR-YOU Fg24) to talk about it. Nothing here is decided.

## What you already have
The site is a PWA: it has a manifest and a service worker, "Download for offline" and a phone app shell. On a phone or in Chrome or Edge it can be installed to the home screen and opens without the browser bar. That is the cheapest "app form" and it works today for every game.

## What a real app would add
- A **desktop app** (a small wrapper such as Tauri or Electron) could give: bigger local storage, saves in a folder you can back up, offline use without the browser's cache rules, full-screen and window controls, controller support, and the option to ship larger files than a web page should (many images, a bigger 3D scene).
- A **phone app** (a wrapper such as Capacitor) could give: store presence, push notifications (which your pledge says you do not want), and native file saving.
- Both are the same web code in a shell, so the games would still be Python in Pyodide and plain HTML.

## What "some games only playable in the app" would mean
- A game with large assets (the dream game's side-view buildings, many sprites) or heavy computation could be too big for a quick web load; shipping it only in the app avoids slow first loads.
- Costs: a second release process (builds for each system), code signing, store reviews if on phones, updates, and the site would stop being "open the link and play" for those games. The hub could still list them with an "App only" badge.
- Risk: your friends play your games because a link just works; app-only games would be harder to share. It also adds ongoing work for every update.

## A middle path
Keep every game on the web, and let the app be an optional extra that unlocks bigger assets and offline folders for the same games; a game that really needs it (the dream game later) can be flagged "best in the app".

## Questions for you (on the ideas page)
Whether the app should be desktop first or phone first, whether any game may be app-only, and whether to try a Tauri desktop shell for one existing game as an experiment.

## Your answers (Ap1 to Ap3, applied 2026-10-11)

- **You play on an iPhone at night and on a Mac in class, and your PC takes a long time to start up.** So if there is ever a desktop app, it targets **the Mac first**, and the **phone web experience stays first-class** (every game keeps working and looking right at phone width, with touch targets and no sideways scroll). That is already how every game is tested.
- **Every game stays on the web and none is app-only** (Ap2). The "best in the app" flag from the middle path above stays an idea for the dream game only, and only if you later say so.
- **A small desktop-app experiment later** (Ap3): when you say go, wrap one existing game (Canopy or Le Champ de Mots are the likeliest, because both are quiet and offline-friendly) in a Mac shell to see what actually improves (a saves folder you can back up, offline use, full screen). Nothing is built for it yet and it does not change the web version.

