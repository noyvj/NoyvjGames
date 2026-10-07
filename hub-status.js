/*
 * Hub status helpers, loaded after script.js on index.html only.
 *
 *  - Y-25 offline banner: while navigator.onLine is false, show a banner and grey out every game
 *    card that this device could not open offline (the game's page is not in the service
 *    worker's cache, or the Python runtime it needs has never been downloaded here). Online
 *    again, everything is restored. Nothing is fetched: it only asks the Cache API.
 *  - Y-27 site status dot: one GET /health on the backend, shown in the footer as a dot plus a
 *    sentence. Green only when the server answers and its database answers; amber when the
 *    server is slow, unreachable or its database is not answering; grey when the check cannot
 *    say (still loading, offline, or an older backend without /health).
 *
 * Everything here is a convenience: any failure leaves the hub exactly as it was.
 */
(function () {
  "use strict";

  const API_BASE = "https://noyvjgames.fastapicloud.dev";
  const HEALTH_TIMEOUT_MS = 8000;

  // ---------- Y-25: offline banner ----------

  const banner = document.getElementById("offline-banner");
  const bannerText = document.getElementById("offline-banner-text");
  const cards = Array.from(document.querySelectorAll(".title-card"));
  let offlineRun = 0;

  function isOnline() {
    return navigator.onLine !== false;
  }

  function cardLink(card) {
    return card.querySelector(".title-card-link");
  }

  function markCard(card, unavailable, reason) {
    const link = cardLink(card);
    let note = card.querySelector(".title-card-offline-note");
    card.classList.toggle("title-card--offline", unavailable);
    if (link) {
      if (unavailable) link.setAttribute("aria-disabled", "true");
      else link.removeAttribute("aria-disabled");
    }
    if (unavailable) {
      if (!note) {
        note = document.createElement("p");
        note.className = "title-card-offline-note";
        if (link) link.insertAdjacentElement("afterend", note);
        else card.appendChild(note);
      }
      note.textContent = reason;
      note.hidden = false;
    } else if (note) {
      note.hidden = true;
    }
  }

  // The Python runtime lives on a CDN and is cached by the service worker only after a game has
  // loaded it once. Without it no game can start, whatever else is cached.
  async function runtimeCached() {
    const names = await caches.keys();
    for (const name of names) {
      const cache = await caches.open(name);
      const requests = await cache.keys();
      if (requests.some((r) => /pyodide(\.asm)?\.(js|wasm)/.test(r.url))) return true;
    }
    return false;
  }

  async function shellCached(card) {
    const link = cardLink(card);
    if (!link) return false;
    const hit = await caches.match(new URL(link.getAttribute("href"), location.href).href);
    return Boolean(hit);
  }

  async function goOffline() {
    const run = ++offlineRun;
    if (banner) banner.hidden = false;
    checkHealth();
    if (bannerText) bannerText.textContent = "You are offline. Checking which games this device can still open…";
    if (typeof caches === "undefined") {
      if (bannerText) bannerText.textContent = "You are offline. Games that were opened before may still work, but ratings, accounts and saves need a connection.";
      return;
    }
    let runtime = false;
    let results = [];
    try {
      runtime = await runtimeCached();
      results = await Promise.all(cards.map((card) => shellCached(card)));
    } catch (err) {
      console.error("hub-status offline check failed:", err);
      if (run === offlineRun && bannerText) {
        bannerText.textContent = "You are offline. Games that were opened before may still work, but ratings, accounts and saves need a connection.";
      }
      return;
    }
    if (run !== offlineRun || isOnline()) return; // went back online (or offline again) meanwhile
    let playable = 0;
    cards.forEach((card, i) => {
      if (!runtime) {
        markCard(card, true, "Not available offline: the Python runtime has not been downloaded on this device yet.");
      } else if (!results[i]) {
        markCard(card, true, "Not available offline: open this game once while online first.");
      } else {
        markCard(card, false, "");
        playable += 1;
      }
    });
    if (bannerText && !runtime) {
      bannerText.textContent = "You are offline, and the Python runtime every game needs has not been downloaded on this device yet (it is fetched the first time a game opens while online), so no game can open right now.";
    } else if (bannerText) {
      bannerText.textContent = playable
        ? `You are offline. ${playable} of ${cards.length} games are stored on this device and should still open; the greyed-out ones need a connection. Ratings, accounts and cloud saves wait until you are back online.`
        : "You are offline, and no game has been stored on this device yet, so none can open. Games become available offline after you have opened them once while online.";
    }
  }

  function goOnline() {
    offlineRun += 1;
    if (banner) banner.hidden = true;
    cards.forEach((card) => markCard(card, false, ""));
    checkHealth();
  }

  // Blocks the click on a greyed-out card (the link is still a real link, so the browser's own
  // error page would otherwise replace the hub).
  document.addEventListener("click", (event) => {
    const link = event.target.closest && event.target.closest(".title-card-link[aria-disabled='true']");
    if (link) event.preventDefault();
  });

  window.addEventListener("offline", goOffline);
  window.addEventListener("online", goOnline);

  // ---------- Y-27: site status dot ----------

  const statusEl = document.getElementById("site-status");
  const statusText = document.getElementById("site-status-text");

  function setStatus(state, text, title) {
    if (!statusEl) return;
    statusEl.dataset.state = state;
    if (statusText) statusText.textContent = text;
    statusEl.title = title;
  }

  async function checkHealth() {
    if (!statusEl) return;
    if (!isOnline()) {
      setStatus("unknown", "Offline", "This device is offline, so the server cannot be checked.");
      return;
    }
    setStatus("checking", "Checking site status…", "Checking whether the ratings, accounts and save server is answering.");
    const controller = typeof AbortController === "function" ? new AbortController() : null;
    const timer = controller ? setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS) : null;
    try {
      const res = await fetch(`${API_BASE}/health`, { cache: "no-store", signal: controller ? controller.signal : undefined });
      if (res.status === 404) {
        // An older deploy of the backend that predates /health: say nothing alarming.
        setStatus("unknown", "Site status unavailable", "The server does not offer a status check yet, so this dot cannot say whether ratings and saves are working.");
        return;
      }
      if (!res.ok) throw new Error(`status ${res.status}`);
      const body = await res.json();
      if (body && body.status === "ok" && body.db === true) {
        setStatus("ok", "All systems normal", "The server and its database are answering, so ratings, accounts and saves should work. The games themselves run in your browser and never depend on this.");
      } else {
        setStatus("degraded", "Some features may be unavailable", "The server is up but its database is not answering, so ratings, accounts and saves may fail for now. The games themselves still play.");
      }
    } catch (err) {
      setStatus("degraded", "Some features may be unavailable", "The server did not answer in time (it may be waking up or down), so ratings, accounts and saves may fail for now. The games themselves still play.");
    } finally {
      if (timer) clearTimeout(timer);
    }
  }

  checkHealth();
  if (!isOnline()) goOffline(); // opened while already offline
})();
