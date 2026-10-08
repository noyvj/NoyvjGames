/*
 * Shared opt-in community leaderboard (planning/TODO.md A29 / E23 / F21),
 * talking to the backend's /leaderboards/<game>/<board> endpoints
 * (app/leaderboards.py lists the boards and the privacy rules).
 *
 * One script per board, included after shared/hub-auth.js:
 *   <div id="leaderboard-mount"></div>
 *   <script src="../../shared/leaderboard.js" data-game-id="sol"
 *           data-board="fastest_completion" data-order="asc"
 *           data-title="Fastest full completion" data-unit="ticks"
 *           data-mount="#leaderboard-mount"></script>
 *
 * What it does:
 *  - Renders a collapsed "Community leaderboard" disclosure. Opening it
 *    fetches the public top 10 (username, score, short detail: nothing else
 *    ever leaves the server).
 *  - Signed-in players get an opt-in checkbox. Nothing is sent until they
 *    tick it; unticking deletes their entry. Signed-out players just see the
 *    board plus a note that signing in on the hub lets them join.
 *  - Games report a result with
 *      window.NoyvjLeaderboard.report("<game>", "<board>", score, detail)
 *    which remembers the personal best in this browser and, only when the
 *    player has opted in and is signed in, submits it. The server keeps just
 *    the better score per account, so re-reporting is harmless.
 *
 * GENERAL BOARDS (planning/TODO.md W-5 / Z-4). The above is the original
 * one-script-per-board form (SOL, Signal, Aftermath, Herd) and is unchanged.
 * New boards use the general system in app/boards.py: daily / weekly /
 * all-time windows, entries anonymous by default ("Player 7F2Q") with one
 * account setting to show the username, opt-in enforced by the server. A game
 * adds one in a few lines, no markup of its own beyond a mount element:
 *   <div id="leaderboard-mount"></div>
 *   <script src="../../shared/leaderboard.js"></script>
 *   <script>
 *     NoyvjLeaderboard.addBoard({ game: "last-line", board: "endless_best_wave",
 *       title: "Endless: best wave", unit: "waves", order: "desc",
 *       windows: ["weekly", "alltime"], mount: "#leaderboard-mount" });
 *     // at the end of a run:
 *     NoyvjLeaderboard.report("last-line", "endless_best_wave", wave, "seed 4821");
 *   </script>
 * or declaratively with data-api="scores" on the script tag plus data-game-id,
 * data-board, data-order, data-title, data-unit, data-windows="daily,weekly,alltime"
 * and data-mount. The board must be registered in app/boards.py first. `mount`
 * is optional: without it the board has no panel and report() still works.
 *
 * Scores come from the client, so this is a friendly board, not an
 * anti-cheat one. Everything fails soft: any network/parse error leaves the
 * panel showing a short "unavailable" line and never touches gameplay.
 * Server-supplied text is only ever written with textContent.
 */
(function () {
  const API_BASE = "https://noyvjgames.fastapicloud.dev";
  // One registry per page even if several boards each include this script.
  const boards = (window.NoyvjLeaderboard && window.NoyvjLeaderboard._boards) || {}; // "game/board" -> { order, refresh }

  function optInKey(game, board) { return `lb-optin:${game}:${board}`; }
  function bestKey(game, board) { return `lb-best:${game}:${board}`; }

  function safeGet(key) {
    try { return localStorage.getItem(key); } catch (e) { return null; }
  }
  function safeSet(key, value) {
    try { localStorage.setItem(key, value); } catch (e) { /* convenience only */ }
  }
  function safeRemove(key) {
    try { localStorage.removeItem(key); } catch (e) { /* convenience only */ }
  }

  function authHeaders() {
    try {
      return typeof hubAuthHeaders === "function" ? hubAuthHeaders() : {};
    } catch (e) {
      return {};
    }
  }
  function signedIn() { return Boolean(authHeaders().Authorization); }
  function isOptedIn(game, board) { return safeGet(optInKey(game, board)) === "true"; }

  function better(order, a, b) { return order === "asc" ? a < b : a > b; }

  function readBest(game, board) {
    const raw = safeGet(bestKey(game, board));
    if (raw === null) return null;
    try {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed.score === "number" && Number.isFinite(parsed.score)) return parsed;
    } catch (e) { /* fall through */ }
    return null;
  }

  async function put(game, board, best) {
    const res = await fetch(`${API_BASE}/leaderboards/${game}/${board}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ score: best.score, detail: best.detail || "" }),
    });
    return res.ok ? res.json() : null;
  }

  async function report(game, board, score, detail) {
    if (typeof score !== "number" || !Number.isFinite(score)) return false;
    const registered = boards[`${game}/${board}`];
    if (registered && registered.kind === "scores") return reportScore(registered, score, detail);
    const order = boards[`${game}/${board}`] ? boards[`${game}/${board}`].order : "asc";
    const previous = readBest(game, board);
    if (previous && !better(order, score, previous.score)) return false;
    const best = { score, detail: typeof detail === "string" ? detail : "" };
    safeSet(bestKey(game, board), JSON.stringify(best));
    if (!isOptedIn(game, board) || !signedIn()) return false;
    try {
      const saved = await put(game, board, best);   // null when the server refused it
      const entry = boards[`${game}/${board}`];
      if (entry) entry.refresh();
      return saved !== null;
    } catch (e) {
      return false;
    }
  }

  function formatScore(score, unit) {
    const rounded = Math.abs(score) >= 100 ? Math.round(score) : Math.round(score * 100) / 100;
    return unit ? `${rounded} ${unit}` : String(rounded);
  }

  // ---- General boards (POST /scores, GET /leaderboard/<game>/<board>) ----

  const ALL_WINDOWS = ["daily", "weekly", "alltime"];
  const WINDOW_LABELS = { daily: "Today", weekly: "This week", alltime: "All time" };
  let nowFn = () => Date.now();   // tests can swap this (NoyvjLeaderboard._setNow)

  /** The period key the server uses for a moment: UTC date, ISO week ("2026-W41"), or "all". */
  function periodKey(windowName, when) {
    if (windowName === "alltime") return "all";
    const d = new Date(when === undefined ? nowFn() : when);
    const pad = (n) => String(n).padStart(2, "0");
    if (windowName === "daily") return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}`;
    if (windowName === "weekly") {
      const t = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
      t.setUTCDate(t.getUTCDate() + 4 - (t.getUTCDay() || 7));   // the Thursday decides the ISO year
      const year = t.getUTCFullYear();
      const week = Math.ceil(((t - Date.UTC(year, 0, 1)) / 86400000 + 1) / 7);
      return `${year}-W${pad(week)}`;
    }
    throw new Error(`unknown window ${windowName}`);
  }

  function best2Key(game, board) { return `lb2-best:${game}:${board}`; }

  /** Local bests per window: { alltime: {score, detail}, daily: {period, score, detail}, weekly: {...} }. */
  function readBests(game, board) {
    try {
      const parsed = JSON.parse(safeGet(best2Key(game, board)) || "null");
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (e) { return {}; }
  }
  function currentBest(bests, windowName) {
    const b = bests[windowName];
    if (!b || typeof b.score !== "number" || !Number.isFinite(b.score)) return null;
    if (windowName !== "alltime" && b.period !== periodKey(windowName)) return null;   // an old day or week
    return b;
  }

  async function postScore(game, board, score, detail, windows) {
    const res = await fetch(`${API_BASE}/scores`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ game, board, score, detail: detail || "", opt_in: true, windows }),
    });
    return res.ok ? res.json() : null;
  }

  async function reportScore(entry, score, detail) {
    const { game, board, order, windows } = entry;
    const bests = readBests(game, board);
    const improved = [];
    const clean = typeof detail === "string" ? detail : "";
    for (const w of windows) {
      const prev = currentBest(bests, w);
      if (!prev || better(order, score, prev.score)) {
        bests[w] = w === "alltime" ? { score, detail: clean } : { period: periodKey(w), score, detail: clean };
        improved.push(w);
      }
    }
    if (!improved.length) return false;
    safeSet(best2Key(game, board), JSON.stringify(bests));
    if (!isOptedIn(game, board) || !signedIn()) return false;
    try {
      const ok = await postScore(game, board, score, clean, improved);
      if (entry.refresh) entry.refresh();
      return Boolean(ok && ok.accepted);
    } catch (e) {
      return false;
    }
  }

  /** Sends whatever the player already earned on this device (called when they opt in). */
  async function sendStoredBests(entry) {
    const bests = readBests(entry.game, entry.board);
    for (const w of entry.windows) {
      const b = currentBest(bests, w);
      if (b) await postScore(entry.game, entry.board, b.score, b.detail, [w]);
    }
  }

  function injectGeneralStyle() {
    if (document.getElementById("noyvj-leaderboard-style")) return;
    const style = document.createElement("style");
    style.id = "noyvj-leaderboard-style";
    style.textContent =
      ".noyvj-lb-windows{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0}" +
      ".noyvj-lb-windows button{min-height:44px;padding:0 14px;font:inherit;color:inherit;background:transparent;" +
      "border:1px dashed currentColor;border-radius:8px;cursor:pointer}" +
      ".noyvj-lb-windows button[aria-pressed=true]{border-style:solid;font-weight:700}" +
      ".noyvj-lb-you{font-weight:700}" +
      ".noyvj-leaderboard-optin{display:block;margin:6px 0}" +
      ".noyvj-leaderboard [hidden]{display:none!important}";
    document.head.append(style);
  }

  function mountScores(config) {
    const { game, board, title, unit, order, windows } = config;
    const entry = { kind: "scores", game, board, order, windows, refresh: null };
    boards[`${game}/${board}`] = entry;
    const host = typeof config.mount === "string" ? document.querySelector(config.mount) : config.mount;
    if (!host) { entry.refresh = () => {}; return entry; }   // headless: report() still works

    injectGeneralStyle();
    let active = windows.includes("alltime") ? "alltime" : windows[0];
    const details = document.createElement("details");
    details.className = "context-toggle noyvj-leaderboard noyvj-leaderboard-general";
    const summary = document.createElement("summary");
    summary.textContent = `Community leaderboard: ${title}`;
    const tabs = document.createElement("div");
    tabs.className = "noyvj-lb-windows";
    tabs.setAttribute("role", "group");
    tabs.setAttribute("aria-label", "Leaderboard period");
    const tabButtons = {};
    for (const w of windows) {
      const b = document.createElement("button");
      b.type = "button";
      b.dataset.window = w;
      b.addEventListener("click", () => { active = w; refresh(); });
      tabButtons[w] = b;
      tabs.append(b);
    }
    const status = document.createElement("p");
    status.className = "comparison-message";
    status.setAttribute("aria-live", "polite");
    const list = document.createElement("ol");
    list.className = "noyvj-leaderboard-list";
    const mine = document.createElement("p");
    mine.className = "comparison-message";
    mine.hidden = true;
    const note = document.createElement("p");
    note.className = "comparison-message";
    note.textContent = "Days and weeks use UTC (weeks start on Monday). Scores are reported by your browser, so this is a friendly board.";

    const optRow = document.createElement("label");
    optRow.className = "noyvj-leaderboard-optin";
    const optBox = document.createElement("input");
    optBox.type = "checkbox";
    const optText = document.createElement("span");
    optText.textContent = " Post my best scores here (shown as an anonymous name like \"Player 7F2Q\" unless you choose otherwise below)";
    optRow.append(optBox, optText);
    const nameRow = document.createElement("label");
    nameRow.className = "noyvj-leaderboard-optin";
    const nameBox = document.createElement("input");
    nameBox.type = "checkbox";
    const nameText = document.createElement("span");
    nameText.textContent = " Show my username instead of an anonymous name (applies to every leaderboard you are on)";
    nameRow.append(nameBox, nameText);
    details.append(summary, tabs, status, list, mine, note, optRow, nameRow);
    host.append(details);

    async function refresh() {
      const signed = signedIn();
      optBox.checked = isOptedIn(game, board);
      optRow.hidden = !signed;
      nameRow.hidden = !signed;
      for (const w of windows) {
        const on = w === active;
        tabButtons[w].setAttribute("aria-pressed", String(on));
        tabButtons[w].textContent = `${on ? "✓ " : ""}${WINDOW_LABELS[w]}`;
      }
      let data = null;
      try {
        const res = await fetch(`${API_BASE}/leaderboard/${game}/${board}?window=${active}`, { headers: authHeaders(), cache: "no-store" });
        data = res.ok ? await res.json() : null;
      } catch (e) { data = null; }
      list.textContent = "";
      mine.hidden = true;
      if (!data || !Array.isArray(data.entries)) {
        status.textContent = "The leaderboard is unavailable right now.";
        return;
      }
      if (typeof data.shows_username === "boolean") nameBox.checked = data.shows_username;
      if (data.suppressed) {
        status.textContent = `This board shows names once at least ${data.min_visible} players have joined it.`;
      } else {
        status.textContent = signed ? "" : "Sign in on the hub to join the leaderboard.";
      }
      for (const row of data.entries) {
        const item = document.createElement("li");
        if (row.you) item.className = "noyvj-lb-you";
        const detail = row.detail ? ` (${row.detail})` : "";
        item.textContent = `${row.name}${row.you ? " (you)" : ""}: ${formatScore(row.score, unit)}${detail}`;
        list.append(item);
      }
      if (data.mine) {
        mine.hidden = false;
        mine.textContent = `Your entry: ${formatScore(data.mine.score, unit)}, rank ${data.mine.rank}, shown as ${data.mine.name}.`;
      }
    }
    entry.refresh = refresh;

    optBox.addEventListener("change", async () => {
      try {
        if (optBox.checked) {
          safeSet(optInKey(game, board), "true");
          if (signedIn()) await sendStoredBests(entry);
        } else {
          safeRemove(optInKey(game, board));
          await fetch(`${API_BASE}/scores/${game}/${board}`, { method: "DELETE", headers: authHeaders() });
        }
      } catch (e) { /* the refresh below shows the true state */ }
      refresh();
    });
    nameBox.addEventListener("change", async () => {
      try {
        await fetch(`${API_BASE}/users/me/leaderboard-privacy`, {
          method: "PUT",
          headers: { "Content-Type": "application/json", ...authHeaders() },
          body: JSON.stringify({ show_username: nameBox.checked }),
        });
      } catch (e) { /* the refresh below shows the true state */ }
      refresh();
    });
    details.addEventListener("toggle", () => { if (details.open) refresh(); });
    return entry;
  }

  /** The one-call entry for a game: registers (and, with `mount`, draws) a general board. */
  function addBoard(config) {
    const game = config && config.game;
    const board = config && config.board;
    if (typeof game !== "string" || typeof board !== "string" || !game || !board) return null;
    const windows = (Array.isArray(config.windows) && config.windows.length ? config.windows : ALL_WINDOWS)
      .filter((w) => ALL_WINDOWS.includes(w));
    return mountScores({
      game, board,
      title: config.title || "Community leaderboard",
      unit: config.unit || "",
      order: config.order === "asc" ? "asc" : "desc",
      windows: windows.length ? ALL_WINDOWS.filter((w) => windows.includes(w)) : ALL_WINDOWS,
      mount: config.mount || null,
    });
  }

  function mount(script) {
    if (script.dataset.api === "scores") {
      addBoard({
        game: script.dataset.gameId, board: script.dataset.board, title: script.dataset.title, unit: script.dataset.unit,
        order: script.dataset.order, windows: (script.dataset.windows || "").split(",").map((s) => s.trim()).filter(Boolean),
        mount: script.dataset.mount || "#leaderboard-mount",
      });
      return;
    }
    const game = script.dataset.gameId;
    const board = script.dataset.board;
    const order = script.dataset.order === "desc" ? "desc" : "asc";
    const title = script.dataset.title || "Community leaderboard";
    const unit = script.dataset.unit || "";
    const host = document.querySelector(script.dataset.mount || "#leaderboard-mount");
    if (!game || !board || !host) return;

    const details = document.createElement("details");
    details.className = "context-toggle noyvj-leaderboard";
    const summary = document.createElement("summary");
    summary.textContent = `Community leaderboard: ${title}`;
    const status = document.createElement("p");
    status.className = "comparison-message";
    const list = document.createElement("ol");
    list.className = "noyvj-leaderboard-list";
    const mine = document.createElement("p");
    mine.className = "comparison-message";
    mine.hidden = true;
    const optRow = document.createElement("label");
    optRow.className = "noyvj-leaderboard-optin";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    const optText = document.createElement("span");
    optText.textContent = " Show my best on this leaderboard (your username and score are public)";
    optRow.append(checkbox, optText);
    details.append(summary, status, list, mine, optRow);
    host.append(details);

    async function refresh() {
      checkbox.checked = isOptedIn(game, board);
      optRow.hidden = !signedIn();
      let data = null;
      try {
        const res = await fetch(`${API_BASE}/leaderboards/${game}/${board}`, { headers: authHeaders(), cache: "no-store" });
        data = res.ok ? await res.json() : null;
      } catch (e) { data = null; }
      list.textContent = "";
      if (!data || !Array.isArray(data.entries)) {
        status.textContent = "The leaderboard is unavailable right now.";
        return;
      }
      if (data.entries.length === 0) {
        status.textContent = "No one has joined this leaderboard yet.";
      } else {
        status.textContent = signedIn() ? "" : "Sign in on the hub to join the leaderboard.";
      }
      for (const entry of data.entries) {
        const item = document.createElement("li");
        const detail = entry.detail ? ` (${entry.detail})` : "";
        item.textContent = `${entry.username}: ${formatScore(entry.score, unit)}${detail}`;
        list.append(item);
      }
      mine.hidden = !data.mine;
      if (data.mine) mine.textContent = `Your entry: ${formatScore(data.mine.score, unit)}, rank ${data.mine.rank}.`;
    }

    checkbox.addEventListener("change", async () => {
      try {
        if (checkbox.checked) {
          safeSet(optInKey(game, board), "true");
          const best = readBest(game, board);
          if (best && signedIn()) await put(game, board, best);
        } else {
          safeRemove(optInKey(game, board));
          await fetch(`${API_BASE}/leaderboards/${game}/${board}`, { method: "DELETE", headers: authHeaders() });
        }
      } catch (e) { /* the refresh below shows the true state */ }
      refresh();
    });
    details.addEventListener("toggle", () => { if (details.open) refresh(); });
    boards[`${game}/${board}`] = { order, refresh };
  }

  window.NoyvjLeaderboard = {
    report, isOptedIn, addBoard, periodKey, _boards: boards,
    _setNow(fn) { nowFn = typeof fn === "function" ? fn : () => Date.now(); },
  };
  const script = document.currentScript;
  if (script) mount(script);
})();
