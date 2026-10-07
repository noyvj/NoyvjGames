/*
 * settings.html (Y-10): the hub's one settings page. It adds no new storage of its own where a key
 * already exists; it reads and writes the keys the rest of the site already uses:
 *
 *   theme                          shared/theme.js
 *   hub_reduced_motion             hub-prefs.js (new, hub pages only)
 *   <slug>-text-scale              each game's settings.js
 *   <slug>-reduced-motion          each game's settings.js
 *   autosave-enabled:<slug>        shared/save-widget.js
 *   hub_pageview_opt_in            script.js
 *   hub_shortcuts                  hub-shortcuts.js
 *   tutorial-seen:<slug>, hub-onboarding-seen, hub-new-player-banner-dismissed,
 *   hub_announcement_dismissed, pwa_install_banner_dismissed, claim_save_nudge_dismissed
 *
 * "Defaults for every game" writes the same key into every game, so each game picks it up the next
 * time it loads; the game's own panel can still change it afterwards. Turning a setting back off
 * removes the key (the game's own default applies) rather than writing "false".
 */
(function () {
  "use strict";

  // Games with no text-size / reduced-motion setting of their own (no games/<slug>/settings.js).
  const NO_DISPLAY_PREFS = ["champ-de-mots"];
  const SCALES = [0.9, 1, 1.1, 1.2, 1.3, 1.4, 1.5];
  const AUTH_KEYS = ["hub_bearer_token", "hub_account_username", "hub_account_since"];
  const SECRET_KEYS = ["hub_bearer_token"];
  const NOTICE_KEYS = ["hub_announcement_dismissed", "pwa_install_banner_dismissed", "claim_save_nudge_dismissed", "hub-new-player-banner-dismissed"];
  const TOUR_KEYS = ["tutorial-seen:hub", "hub-onboarding-seen", "hub-new-player-banner-dismissed"];

  const $ = (id) => document.getElementById(id);
  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } }
  function lsRemove(k) { try { localStorage.removeItem(k); } catch (e) { /* convenience only */ } }
  function lsKeys() {
    try { return Object.keys(localStorage); } catch (e) { return []; }
  }
  function say(id, text) {
    const el = $(id);
    if (el) el.textContent = text;
    // Every message follows a change to what is stored, so keep the data summary honest.
    if (typeof renderDataSummary === "function" && $("settings-data-summary")) renderDataSummary();
  }

  let games = [];
  const prefGames = () => games.filter((g) => NO_DISPLAY_PREFS.indexOf(g.slug) === -1);

  // A hub preference (as opposed to sign-in, a game's data or a game's own settings).
  function isHubPreferenceKey(key) {
    if (AUTH_KEYS.indexOf(key) !== -1) return false;
    return /^hub[_-]/.test(key) || key === "claim_save_nudge_dismissed" ||
      key === "pwa_install_banner_dismissed" || key === "tutorial-seen:hub";
  }

  // ---------- Look and feel ----------

  function initTheme() {
    const select = $("settings-theme");
    if (!select) return;
    function sync() { if (window.NoyvjTheme) select.value = window.NoyvjTheme.get(); }
    sync();
    document.addEventListener("noyvj-theme-change", sync);
    select.addEventListener("change", () => {
      if (window.NoyvjTheme) window.NoyvjTheme.set(select.value);
      say("settings-appearance-status", `Theme set to ${select.value}.`);
    });
  }

  function motionState() {
    const flags = prefGames().map((g) => lsGet(`${g.slug}-reduced-motion`) === "true");
    flags.push(lsGet("hub_reduced_motion") === "true");
    const on = flags.filter(Boolean).length;
    return on === 0 ? "off" : on === flags.length ? "on" : "mixed";
  }

  function renderMotion() {
    const box = $("settings-motion");
    const state = motionState();
    box.checked = state === "on";
    box.indeterminate = state === "mixed";
  }

  function initMotion() {
    const box = $("settings-motion");
    if (!box) return;
    renderMotion();
    box.addEventListener("change", () => {
      const on = box.checked;
      const apply = (key) => (on ? lsSet(key, "true") : lsRemove(key));
      apply("hub_reduced_motion");
      if (on) document.documentElement.setAttribute("data-hub-reduced-motion", "true");
      else document.documentElement.removeAttribute("data-hub-reduced-motion");
      prefGames().forEach((g) => apply(`${g.slug}-reduced-motion`));
      renderMotion();
      say("settings-appearance-status", on
        ? `Reduce motion is on for the hub and ${prefGames().length} games.`
        : "Reduce motion is off (each game goes back to its own default).");
    });
  }

  // ---------- Defaults for every game ----------

  function scaleLabel(value) {
    if (value === 1) return "Default (100%)";
    return `${Math.round(value * 100)}%`;
  }
  function readScale(slug) {
    const v = parseFloat(lsGet(`${slug}-text-scale`));
    return Number.isFinite(v) ? Math.round(v * 100) / 100 : 1;
  }

  function fillSelect(select, options, current) {
    select.textContent = "";
    options.forEach((o) => {
      const opt = document.createElement("option");
      opt.value = o.value;
      opt.textContent = o.label;
      select.appendChild(opt);
    });
    if (current === "mixed") {
      const mixed = document.createElement("option");
      mixed.value = "mixed";
      mixed.textContent = "Different per game";
      mixed.disabled = true;
      select.appendChild(mixed);
    }
    select.value = current;
  }

  function renderGameDefaults() {
    const list = prefGames();
    const scaleSelect = $("settings-scale");
    const autoSelect = $("settings-autosave");
    const disabled = list.length === 0;
    scaleSelect.disabled = autoSelect.disabled = disabled;
    if (disabled) {
      say("settings-games-status", "Could not read the game list, so these cannot be applied right now. Reload and try again.");
      return;
    }
    const scales = list.map((g) => readScale(g.slug));
    const scaleCurrent = scales.every((s) => s === scales[0]) ? String(scales[0]) : "mixed";
    const scaleOptions = SCALES.map((s) => ({ value: String(s), label: scaleLabel(s) }));
    if (scaleCurrent !== "mixed" && !SCALES.includes(Number(scaleCurrent))) {
      scaleOptions.push({ value: scaleCurrent, label: `${Math.round(Number(scaleCurrent) * 100)}% (set in a game)` });
    }
    fillSelect(scaleSelect, scaleOptions, scaleCurrent);

    const auto = games.map((g) => lsGet(`autosave-enabled:${g.slug}`) === "true");
    const autoCurrent = auto.every((a) => !a) ? "off" : auto.every(Boolean) ? "on" : "mixed";
    fillSelect(autoSelect, [{ value: "off", label: "Off in every game" }, { value: "on", label: "On in every game" }], autoCurrent);
  }

  function initGameDefaults() {
    const scaleSelect = $("settings-scale");
    const autoSelect = $("settings-autosave");
    scaleSelect.addEventListener("change", () => {
      const value = Number(scaleSelect.value);
      if (!Number.isFinite(value)) return;
      prefGames().forEach((g) => (value === 1 ? lsRemove(`${g.slug}-text-scale`) : lsSet(`${g.slug}-text-scale`, String(value))));
      renderGameDefaults();
      say("settings-games-status", `Text size set to ${scaleLabel(value).toLowerCase()} in ${prefGames().length} games. Open games pick it up on their next load.`);
    });
    autoSelect.addEventListener("change", () => {
      const on = autoSelect.value === "on";
      games.forEach((g) => (on ? lsSet(`autosave-enabled:${g.slug}`, "true") : lsRemove(`autosave-enabled:${g.slug}`)));
      renderGameDefaults();
      say("settings-games-status", on
        ? `Autosave is on in all ${games.length} games (every five minutes while a game is open).`
        : "Autosave is off in every game.");
    });
    renderGameDefaults();
  }

  // ---------- Privacy ----------

  function initPrivacy() {
    const box = $("settings-pageviews");
    box.checked = lsGet("hub_pageview_opt_in") === "1";
    box.addEventListener("change", () => lsSet("hub_pageview_opt_in", box.checked ? "1" : "0"));
  }

  // ---------- Tours and notices ----------

  function initTours() {
    $("settings-reset-tour").addEventListener("click", () => {
      TOUR_KEYS.forEach(lsRemove);
      say("settings-tours-status", "Done. The welcome survey and the tour will appear the next time you open the hub.");
    });
    $("settings-reset-game-tours").addEventListener("click", () => {
      games.forEach((g) => lsRemove(`tutorial-seen:${g.slug}`));
      say("settings-tours-status", `Done. Each of the ${games.length} games will offer its tutorial again the next time you open it.`);
    });
    $("settings-reset-notices").addEventListener("click", () => {
      NOTICE_KEYS.forEach(lsRemove);
      say("settings-tours-status", "Done. Notices you dismissed can appear again on the hub.");
    });
  }

  // ---------- Keyboard shortcuts (Y-19) ----------

  let capturing = null; // { id, button }

  function renderShortcuts() {
    const body = $("settings-keys-body");
    if (!body || !window.HubShortcuts) return;
    const current = window.HubShortcuts.bindings();
    body.textContent = "";
    window.HubShortcuts.ACTIONS.forEach((action) => {
      const row = document.createElement("tr");
      const label = document.createElement("td");
      label.textContent = action.label + (action.scope ? ` (${action.scope})` : "");
      const keys = document.createElement("td");
      const kbd = document.createElement("kbd");
      kbd.className = "hub-key";
      kbd.textContent = window.HubShortcuts.display(action, current[action.id]);
      keys.appendChild(kbd);
      const action2 = document.createElement("td");
      const change = document.createElement("button");
      change.type = "button";
      change.className = "secondary";
      change.textContent = "Change";
      change.setAttribute("aria-label", `Change the shortcut for: ${action.label}`);
      change.addEventListener("click", () => startCapture(action, change));
      action2.appendChild(change);
      row.append(label, keys, action2);
      body.appendChild(row);
    });
  }

  function stopCapture() {
    if (!capturing) return;
    document.removeEventListener("keydown", onCaptureKey, true);
    capturing.button.textContent = "Change";
    if (window.HubShortcuts) window.HubShortcuts.suspend(false);
    capturing = null;
  }

  function startCapture(action, button) {
    stopCapture();
    capturing = { action, button };
    window.HubShortcuts.suspend(true);
    button.textContent = "Press a key…";
    say("settings-keys-status", `Press the new key for "${action.label}". Esc cancels.`);
    document.addEventListener("keydown", onCaptureKey, true);
  }

  function onCaptureKey(event) {
    if (!capturing) return;
    if (event.key === "Escape") {
      event.preventDefault();
      const label = capturing.action.label;
      const button = capturing.button;
      stopCapture();
      say("settings-keys-status", `Cancelled. "${label}" is unchanged.`);
      button.focus();
      return;
    }
    if (event.key === "Shift" || event.key === "Control" || event.key === "Alt" || event.key === "Meta") return;
    if (event.key === "Tab") { // never trap keyboard focus: Tab leaves the capture and moves on
      stopCapture();
      say("settings-keys-status", "Cancelled. The shortcut is unchanged.");
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    const { action } = capturing;
    const key = event.key;
    const problem = window.HubShortcuts.conflict(action.id, key);
    if (problem) {
      say("settings-keys-status", `${problem} Press another key, or Esc to cancel.`);
      return;
    }
    window.HubShortcuts.setBinding(action.id, key);
    stopCapture();
    renderShortcuts();
    say("settings-keys-status", `Saved: "${action.label}" is now ${window.HubShortcuts.display(action, key)}.`);
  }

  function initShortcuts() {
    renderShortcuts();
    $("settings-keys-reset").addEventListener("click", () => {
      stopCapture();
      window.HubShortcuts.resetAll();
      renderShortcuts();
      say("settings-keys-status", "Shortcuts are back to their defaults.");
    });
  }

  // ---------- Your data ----------

  function renderDataSummary() {
    const keys = lsKeys();
    const hubPrefs = keys.filter(isHubPreferenceKey).length;
    const signedIn = Boolean(lsGet("hub_bearer_token"));
    $("settings-data-summary").textContent =
      `This browser holds ${keys.length} stored item${keys.length === 1 ? "" : "s"} for this site ` +
      `(${hubPrefs} hub preference${hubPrefs === 1 ? "" : "s"}, the rest belong to the games) and you are ` +
      `${signedIn ? "signed in" : "not signed in"}.`;
  }

  function exportEverything() {
    const items = {};
    lsKeys().filter((k) => SECRET_KEYS.indexOf(k) === -1).sort().forEach((k) => { items[k] = lsGet(k); });
    const payload = {
      exported_at: new Date().toISOString(),
      site: location.origin + location.pathname.replace(/[^/]*$/, ""),
      note: "Everything NoyvjGames stored in this browser's localStorage, minus the sign-in token. Save codes in here can open and overwrite their saves: keep this file private.",
      item_count: Object.keys(items).length,
      items,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `noyvjgames-export-${payload.exported_at.slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
    say("settings-data-status", `Exported ${payload.item_count} items.`);
  }

  async function clearOfflineCache() {
    if (typeof caches === "undefined") {
      say("settings-data-status", "This browser has no offline cache to clear.");
      return;
    }
    try {
      const names = await caches.keys();
      await Promise.all(names.map((n) => caches.delete(n)));
      say("settings-data-status", `Cleared ${names.length} offline cache${names.length === 1 ? "" : "s"}. They fill up again as you open pages and games.`);
    } catch (err) {
      say("settings-data-status", "Could not clear the offline cache.");
    }
  }

  // Two-step confirm without a native dialog: the question appears under the buttons.
  let pendingAction = null;
  function askConfirm(text, action) {
    pendingAction = action;
    $("settings-confirm-text").textContent = text;
    $("settings-confirm").hidden = false;
    $("settings-confirm-no").focus();
  }
  function closeConfirm() {
    pendingAction = null;
    $("settings-confirm").hidden = true;
  }

  function initClear() {
    $("settings-export").addEventListener("click", exportEverything);
    $("settings-clear-cache").addEventListener("click", clearOfflineCache);
    $("settings-clear-prefs").addEventListener("click", () => {
      const n = lsKeys().filter(isHubPreferenceKey).length;
      askConfirm(`Reset ${n} hub preference${n === 1 ? "" : "s"}? Your sign-in and every game's data stay.`, () => {
        lsKeys().filter(isHubPreferenceKey).forEach(lsRemove);
        document.documentElement.removeAttribute("data-hub-reduced-motion");
        say("settings-clear-status", `Reset ${n} hub preference${n === 1 ? "" : "s"}.`);
        renderMotion();
      });
    });
    $("settings-clear-all").addEventListener("click", () => {
      const n = lsKeys().length;
      askConfirm(`Erase all ${n} stored items, including your sign-in and any save code you have not claimed to an account? This cannot be undone.`, () => {
        try { localStorage.clear(); } catch (e) { /* nothing more to do */ }
        say("settings-clear-status", `Erased ${n} items. You are signed out and everything on this page is back to its default.`);
        renderGameDefaults();
        renderMotion();
        renderShortcuts();
        initPrivacyState();
      });
    });
    $("settings-confirm-yes").addEventListener("click", () => {
      const action = pendingAction;
      closeConfirm();
      if (action) action();
      renderDataSummary();
    });
    $("settings-confirm-no").addEventListener("click", () => {
      closeConfirm();
      say("settings-clear-status", "Cancelled. Nothing was changed.");
    });
  }

  function initPrivacyState() {
    $("settings-pageviews").checked = lsGet("hub_pageview_opt_in") === "1";
  }

  // ---------- boot ----------

  async function boot() {
    initTheme();
    initPrivacy();
    initTours();
    initShortcuts();
    initClear();
    renderDataSummary();
    games = await window.HubGames.load();
    initMotion();
    initGameDefaults();
    // The hub-only preference works without the list; the rest of the page is already usable.
    if (location.hash === "#shortcuts") {
      const section = $("shortcuts");
      if (section) section.scrollIntoView();
    }
  }
  boot();
})();
