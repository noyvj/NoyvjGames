/*
 * Account-synced site-wide settings (Y31). For a signed-in player, their theme
 * and lite mode (Z-31, shared/lite-mode.js; all pages) and, in the games that have a
 * settings panel (SOL, Continuum, Lexis), text scale and reduced motion follow them between devices via
 * GET/PUT /users/me/settings. Signed-out players are untouched: everything
 * stays per-device in localStorage exactly as before. Include AFTER
 * shared/theme.js on every page:
 *   <script src="../../shared/site-settings.js" data-game-id="<slug>"></script>
 * (data-game-id omitted on hub pages).
 *
 * Merge rule, deliberately simple: the account wins on page load (a value
 * saved on another device is applied here), and a local change made on this
 * device is pushed up straight away (theme) or when the page is hidden
 * (text scale / reduced motion, which the games' own settings.js writes to
 * localStorage without an event). Failures are silent: sync is a convenience.
 */
(function () {
  const API_BASE = "https://noyvjgames.fastapicloud.dev";
  const TOKEN_KEY = "hub_bearer_token";
  const SCRIPT = document.currentScript;
  const GAME_ID = SCRIPT && SCRIPT.dataset.gameId;

  // Games whose settings.js persists these two prefs, and the keys it uses.
  const GAME_KEYS = {
    sol: { scale: "sol-text-scale", motion: "sol-reduced-motion" },
    continuum: { scale: "continuum-text-scale", motion: "continuum-reduced-motion" },
    lexis: { scale: "lexis-text-scale", motion: "lexis-reduced-motion" },
    "logic-gates": { scale: "logic-gates-text-scale", motion: "logic-gates-reduced-motion" },
    "dead-reckoning": { scale: "dead-reckoning-text-scale", motion: "dead-reckoning-reduced-motion" },
    "pocket-bazaar": { scale: "pocket-bazaar-text-scale", motion: "pocket-bazaar-reduced-motion" },
    "lighthouse": { scale: "lighthouse-text-scale", motion: "lighthouse-reduced-motion" },
    "heist-committee": { scale: "heist-text-scale", motion: "heist-reduced-motion" },
  };
  const keys = GAME_ID ? GAME_KEYS[GAME_ID] : null;

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience */ } }
  const token = () => lsGet(TOKEN_KEY);
  if (!token()) return;

  const headers = () => ({ "Content-Type": "application/json", Authorization: `Bearer ${token()}` });

  function localScale() {
    const v = parseFloat(lsGet(keys.scale));
    return Number.isFinite(v) ? v : null;
  }
  function localMotion() {
    const v = lsGet(keys.motion);
    return v === "true" ? true : v === "false" ? false : v === "1" ? true : v === "0" ? false : null;
  }

  // Apply a remote text scale / reduced-motion to the live page and to the
  // game's own localStorage, mirroring what settings.js itself does.
  function applyScale(scale) {
    document.documentElement.style.setProperty("--text-scale", String(scale));
    document.documentElement.setAttribute("data-text-scale", String(scale));
    lsSet(keys.scale, String(scale));
  }
  function applyMotion(on) {
    document.documentElement.classList.toggle("reduce-motion", on);
    if (on) document.documentElement.setAttribute("data-reduced-motion", "true");
    else document.documentElement.removeAttribute("data-reduced-motion");
    lsSet(keys.motion, on ? "true" : "false");
  }

  let last = {};
  function snapshot() {
    const s = { theme: window.NoyvjTheme ? window.NoyvjTheme.get() : undefined };
    // Only a choice the player made is synced, never the automatic slow-device default.
    if (window.NoyvjLite && window.NoyvjLite.chosen() !== null) s.lite_mode = window.NoyvjLite.chosen();
    if (keys) {
      const scale = localScale();
      const motion = localMotion();
      if (scale !== null) s.text_scale = scale;
      if (motion !== null) s.reduced_motion = motion;
    }
    return s;
  }
  function changed(current) {
    const out = {};
    for (const k of Object.keys(current)) {
      if (current[k] !== undefined && current[k] !== last[k]) out[k] = current[k];
    }
    return out;
  }
  function push(useKeepalive) {
    const diff = changed(snapshot());
    if (!Object.keys(diff).length || !token()) return;
    fetch(`${API_BASE}/users/me/settings`, {
      method: "PUT", headers: headers(), body: JSON.stringify(diff), keepalive: Boolean(useKeepalive),
    }).then((res) => { if (res.ok) last = Object.assign({}, last, diff); }).catch(() => {});
  }

  fetch(`${API_BASE}/users/me/settings`, { headers: headers(), cache: "no-store" })
    .then((res) => (res.ok ? res.json() : null))
    .then((body) => {
      const remote = (body && body.settings) || {};
      last = Object.assign({}, remote);
      if (remote.theme && window.NoyvjTheme && remote.theme !== window.NoyvjTheme.get()) {
        window.NoyvjTheme.setFromSync(remote.theme);
      }
      if (typeof remote.lite_mode === "boolean" && window.NoyvjLite && remote.lite_mode !== window.NoyvjLite.chosen()) {
        window.NoyvjLite.setFromSync(remote.lite_mode);
      }
      if (keys) {
        if (typeof remote.text_scale === "number") applyScale(remote.text_scale);
        if (typeof remote.reduced_motion === "boolean") applyMotion(remote.reduced_motion);
      }
      // Anything this device has that the account doesn't yet: upload it.
      push(false);
    })
    .catch(() => {});

  document.addEventListener("noyvj-theme-change", (event) => {
    if (event.detail && event.detail.fromSync) return;
    push(false);
  });
  document.addEventListener("noyvj-lite-change", (event) => {
    if (event.detail && event.detail.fromSync) return;
    push(false);
  });
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") push(true); });
  window.addEventListener("pagehide", () => push(true));
})();
