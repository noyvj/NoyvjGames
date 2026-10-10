/*
 * Shared screen-reader announcer (planning/TODO.md B-7): one place a game says "Flood hit, 42 damage, 18
 * prevented" or "Season 7 begins" so a screen reader reads it, without each game keeping its own live region.
 *
 *   <script src="../../shared/announcer.js"></script>
 *   NoyvjAnnounce.say("Plot 3 cleared");                         // polite: read when the reader is idle
 *   NoyvjAnnounce.say("Storm arrives next season", { priority: "assertive" });   // interrupts: use rarely
 *   NoyvjAnnounce.mount("#sr-announcer");                        // optional: adopt a region the page already has
 *
 * What it does:
 *   * Two visually hidden regions are made on first use (role="status" aria-live="polite" and role="alert"
 *     aria-live="assertive", both aria-atomic), so a game needs no markup. mount(el) adopts an existing
 *     element as the polite region instead.
 *   * Everything said in the same tick is joined into ONE announcement ("Plot 3 cleared. Income 40") so a
 *     burst from one render does not talk over itself. At most MAX_QUEUED messages are kept per tick (the
 *     newest). The same sentence said twice in a row is still announced again (a trailing zero-width mark
 *     flips), and an exact repeat inside one tick is dropped.
 *   * Text goes in with textContent only. No timers (a microtask flushes the queue), no network, nothing stored.
 *   * history(n) returns the last n announcements (for tests and for a game that wants a "what was said" list).
 *
 * API (window.NoyvjAnnounce): say(text, {priority}), mount(selectorOrElement), clear(), history(n), flush(),
 * MAX_QUEUED.
 */
(function () {
  "use strict";
  if (window.NoyvjAnnounce) return;

  const MAX_QUEUED = 8;
  const MAX_HISTORY = 50;
  const MAX_LENGTH = 400;
  const FLIP = "​";
  const queues = { polite: [], assertive: [] };
  const regions = { polite: null, assertive: null };
  const flips = { polite: false, assertive: false };
  const log = [];
  let scheduled = false;

  const HIDDEN_STYLE = "position:absolute;width:1px;height:1px;margin:-1px;padding:0;border:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;";

  function ensure(priority) {
    if (regions[priority] && regions[priority].isConnected) return regions[priority];
    const node = document.createElement("div");
    node.setAttribute("data-noyvj-announcer", priority);
    node.setAttribute("role", priority === "assertive" ? "alert" : "status");
    node.setAttribute("aria-live", priority);
    node.setAttribute("aria-atomic", "true");
    node.style.cssText = HIDDEN_STYLE;
    (document.body || document.documentElement).append(node);
    regions[priority] = node;
    return node;
  }

  function clean(text) {
    return String(text === undefined || text === null ? "" : text).replace(/\s+/g, " ").trim().replace(/[.\s]+$/, "").slice(0, MAX_LENGTH);
  }

  function flush() {
    scheduled = false;
    ["assertive", "polite"].forEach((priority) => {
      const queue = queues[priority];
      if (!queue.length) return;
      const joined = queue.splice(0, queue.length).join(". ");
      const region = ensure(priority);
      flips[priority] = !flips[priority];
      region.textContent = joined + (flips[priority] ? FLIP : "");
      log.push({ text: joined, priority });
      while (log.length > MAX_HISTORY) log.shift();
    });
  }

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    Promise.resolve().then(flush);
  }

  function say(text, opts) {
    const message = clean(text);
    if (!message) return false;
    const priority = opts && opts.priority === "assertive" ? "assertive" : "polite";
    const queue = queues[priority];
    if (queue.indexOf(message) >= 0) return true;        // an exact repeat in the same tick adds nothing
    queue.push(message);
    while (queue.length > MAX_QUEUED) queue.shift();
    schedule();
    return true;
  }

  function mount(target) {
    const node = typeof target === "string" ? document.querySelector(target) : target;
    if (!node) return null;
    node.setAttribute("role", "status");
    node.setAttribute("aria-live", "polite");
    node.setAttribute("aria-atomic", "true");
    regions.polite = node;
    return node;
  }

  function clear() {
    queues.polite.length = 0;
    queues.assertive.length = 0;
    ["polite", "assertive"].forEach((priority) => { if (regions[priority]) regions[priority].textContent = ""; });
  }

  function history(count) {
    const n = Number.isFinite(count) ? Math.max(0, Math.floor(count)) : log.length;
    return log.slice(-n).map((entry) => ({ text: entry.text, priority: entry.priority }));
  }

  window.NoyvjAnnounce = { say, mount, clear, history, flush, MAX_QUEUED };
})();
