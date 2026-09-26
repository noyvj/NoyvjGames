/*
 * Shared community pool client (planning/TODO.md H11, and the daily community
 * plot idea). Talks to the backend's anonymous /pools/<game>/<pool> endpoints
 * (app/pools.py: capped, rate limited, per-UTC-day totals, nothing personal).
 *
 *   <p id="pool-display" hidden></p>
 *   <script src="../../shared/community-pool.js" data-game-id="loop"
 *     data-pool="recovered_units" data-target="#pool-display"
 *     data-template="The region has recycled {total} units in all; {today} today (best day: {best})."></script>
 *
 * Games add to the pool with window.NoyvjPool.add(game, pool, amount). Adds are
 * batched: at most one request every FLUSH_MS, plus a best-effort flush when the
 * page is hidden. The display line refreshes after each flush and every
 * REFRESH_MS. Placeholders: {total}, {today}, {best}, {contributions}. Every
 * failure fails soft (the line just stays hidden) and text is set with
 * textContent only.
 */
(function () {
  const API_BASE = "https://noyvjgames.fastapicloud.dev";
  const FLUSH_MS = 20000;
  const REFRESH_MS = 60000;
  const pending = {}; // "game/pool" -> amount not yet sent
  const timers = {};
  const displays = []; // { game, pool, target, template }

  function fmt(value) {
    if (typeof value !== "number" || !Number.isFinite(value)) return "0";
    return String(Math.round(value));
  }

  function fill(template, data) {
    const best = data.best_day ? data.best_day.total : 0;
    return template
      .replace(/\{total\}/g, fmt(data.total))
      .replace(/\{today\}/g, fmt(data.today && data.today.total))
      .replace(/\{best\}/g, fmt(best))
      .replace(/\{contributions\}/g, fmt(data.today && data.today.contributions));
  }

  async function refresh(display) {
    try {
      const res = await fetch(`${API_BASE}/pools/${display.game}/${display.pool}`, { cache: "no-store" });
      if (!res.ok) return;
      const data = await res.json();
      display.target.textContent = fill(display.template, data);
      display.target.hidden = false;
    } catch (e) { /* stay hidden */ }
  }

  async function flush(game, pool) {
    const key = `${game}/${pool}`;
    const amount = pending[key] || 0;
    pending[key] = 0;
    timers[key] = null;
    if (amount <= 0) return false;
    try {
      const res = await fetch(`${API_BASE}/pools/${game}/${pool}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount }),
        keepalive: true,
      });
      displays.filter((d) => d.game === game && d.pool === pool).forEach(refresh);
      return res.ok;
    } catch (e) {
      return false;
    }
  }

  function add(game, pool, amount) {
    if (typeof amount !== "number" || !Number.isFinite(amount) || amount <= 0) return false;
    const key = `${game}/${pool}`;
    pending[key] = (pending[key] || 0) + amount;
    if (!timers[key]) timers[key] = setTimeout(() => flush(game, pool), FLUSH_MS);
    return true;
  }

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      Object.keys(pending).forEach((key) => {
        const [game, pool] = key.split("/");
        if (pending[key] > 0) flush(game, pool);
      });
    }
  });

  window.NoyvjPool = { add, flush, _pending: pending };

  const script = document.currentScript;
  if (script && script.dataset.gameId && script.dataset.pool && script.dataset.template) {
    const target = document.querySelector(script.dataset.target || "#pool-display");
    if (target) {
      const display = { game: script.dataset.gameId, pool: script.dataset.pool, target, template: script.dataset.template };
      displays.push(display);
      refresh(display);
      setInterval(() => refresh(display), REFRESH_MS);
    }
  }
})();
