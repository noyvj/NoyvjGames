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
    const order = boards[`${game}/${board}`] ? boards[`${game}/${board}`].order : "asc";
    const previous = readBest(game, board);
    if (previous && !better(order, score, previous.score)) return false;
    const best = { score, detail: typeof detail === "string" ? detail : "" };
    safeSet(bestKey(game, board), JSON.stringify(best));
    if (!isOptedIn(game, board) || !signedIn()) return false;
    try {
      await put(game, board, best);
      const entry = boards[`${game}/${board}`];
      if (entry) entry.refresh();
      return true;
    } catch (e) {
      return false;
    }
  }

  function formatScore(score, unit) {
    const rounded = Math.abs(score) >= 100 ? Math.round(score) : Math.round(score * 100) / 100;
    return unit ? `${rounded} ${unit}` : String(rounded);
  }

  function mount(script) {
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

  window.NoyvjLeaderboard = { report, isOptedIn, _boards: boards };
  const script = document.currentScript;
  if (script) mount(script);
})();
