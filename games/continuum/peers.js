/*
 * Continuum -- R-33 (the parked K30): the "another settlement" ghost, browser half.
 *
 * Python decides WHAT to send and how to draw it (peers.py, game.py's peer_* functions); this file only
 * owns the network calls, the Settings switch and the two buttons that need the network. The backend half
 * is app/ghosts.py. Every number it sends or draws is a per-season list the game already keeps.
 *
 * Two separate, optional things, both off until the player does something:
 *
 *   1. Sharing (Settings): "Share my settlement's trajectory anonymously". Off by default, only possible
 *      while signed in. When on, the series is sent when you switch it on and again every few seasons.
 *      Turning it off deletes what was shared. Only the numbers (season, era, people, score) leave the
 *      page: no name, no username, no save.
 *   2. Looking ("Show another settlement"): one press fetches ONE anonymous series. Nothing is stored
 *      in the save, and any failure shows one plain message and changes nothing in the game.
 *
 * Nothing here blocks or changes play: every call is wrapped, a missing Python function or a failed
 * network call simply ends in a message.
 */
(function () {
  "use strict";

  var API = "https://noyvjgames.fastapicloud.dev";
  var GAME = "continuum";
  var STORE_KEY = "continuum-peer-publish";
  var STATE = { on: false, user: "", pendingDelete: false };
  var lastSent = { season: -1, era: -1 };
  var busy = { publish: false, show: false };

  function byId(id) { return document.getElementById(id); }

  // ---- storage (a per-browser convenience; the server is the truth about what is published) ----
  function loadState() {
    try {
      var raw = window.localStorage.getItem(STORE_KEY);
      var parsed = raw ? JSON.parse(raw) : null;
      if (parsed && typeof parsed === "object") {
        STATE.on = parsed.on === true;
        STATE.user = typeof parsed.user === "string" ? parsed.user.slice(0, 64) : "";
        STATE.pendingDelete = parsed.pendingDelete === true;
      }
    } catch (e) { /* storage blocked or junk: stays off */ }
  }
  function saveState() {
    try { window.localStorage.setItem(STORE_KEY, JSON.stringify(STATE)); } catch (e) { /* convenience only */ }
  }

  // ---- helpers ----
  function authHeaders() {
    try { return typeof hubAuthHeaders === "function" ? hubAuthHeaders() : {}; } catch (e) { return {}; }
  }
  function signedIn() { return Boolean(authHeaders().Authorization); }

  // Calls a Python function defined in game.py (null when the game has not booted or it is missing).
  function py(name) {
    try {
      var fn = window.pyodide && window.pyodide.globals.get(name);
      if (!fn) return null;
      var args = Array.prototype.slice.call(arguments, 1);
      var result = fn.apply(null, args);
      if (fn.destroy) fn.destroy();
      return result;
    } catch (e) {
      return null;
    }
  }
  function message(kind) { var text = py("peer_message", kind); return typeof text === "string" ? text : ""; }

  function setText(id, text) { var el = byId(id); if (el) el.textContent = text; }
  function setPublishNote(text) { setText("peer-publish-note", text); }
  function setStatus(text) { setText("peer-status", text); }

  var DEFAULT_NOTE =
    "Off by default and optional. Needs an account. Only a list of numbers per season is sent (season, era, " +
    "people, sustainability score): no name, no username, no save. Anyone who presses \"Show another " +
    "settlement\" may see that list, with nothing to say whose it is. Switching this off removes it.";

  async function getJson(path, options) {
    var res = await window.fetch(API + path, options);
    var body = null;
    try { body = await res.json(); } catch (e) { body = null; }
    return { ok: res.ok, status: res.status, body: body };
  }

  // ---- the Settings switch ----
  function refreshPublishUi() {
    var box = byId("peer-publish-checkbox");
    if (!box) return;
    var ok = signedIn();
    box.disabled = !ok && !box.checked;
    box.checked = ok && STATE.on;
    if (!ok) {
      setPublishNote("Sign in on the hub page to share. " + DEFAULT_NOTE);
    } else if (!box.checked) {
      setPublishNote(DEFAULT_NOTE);
    }
  }

  async function whoAmI() {
    var res = await getJson("/users/me", { headers: authHeaders() });
    if (!res.ok || !res.body || typeof res.body.username !== "string") return "";
    return res.body.username;
  }

  // Sends the current series if Python says one is due (pass force to ignore the schedule).
  async function publishNow(force, knownUser) {
    if (busy.publish || !STATE.on || !signedIn()) return;
    busy.publish = true;
    try {
      var plan = py("peer_publish_plan", force ? -1 : lastSent.season, force ? -1 : lastSent.era);
      if (!plan) {
        if (force) setPublishNote("Sharing is on. Your settlement will be shared once it has a few seasons behind it.");
        return;
      }
      var user = knownUser || await whoAmI();
      if (!user || (STATE.user && user !== STATE.user)) {
        STATE.on = false; saveState(); refreshPublishUi();
        setPublishNote("Sharing was switched off because you are signed in as a different account. Tick the box again to share from this one.");
        return;
      }
      var payload = JSON.parse(plan);
      var res = await getJson("/ghosts", {
        method: "POST",
        headers: Object.assign({ "Content-Type": "application/json" }, authHeaders()),
        body: plan,
      });
      if (res.ok && res.body && res.body.accepted) {
        var last = payload.series[payload.series.length - 1];
        lastSent = { season: last[0], era: last[1] };
        setPublishNote("Shared " + payload.series.length + " seasons, anonymously. Switch this off to remove them.");
      } else if (res.ok) {
        setPublishNote("The server did not take this one (test accounts are not shared).");
      } else if (res.status >= 400 && res.status < 500 && res.status !== 429) {
        STATE.on = false; saveState(); refreshPublishUi();
        setPublishNote("Sharing was switched off: the server refused it. Nothing was shared.");
      } else {
        setPublishNote("Could not share just now; it will try again in a few seasons.");
      }
    } catch (e) {
      setPublishNote("Could not share just now; it will try again in a few seasons.");
    } finally {
      busy.publish = false;
    }
  }

  async function deleteShared() {
    try {
      var res = await getJson("/ghosts/" + GAME, { method: "DELETE", headers: authHeaders() });
      if (res.ok) { STATE.pendingDelete = false; saveState(); return true; }
    } catch (e) { /* retried at the next load */ }
    return false;
  }

  async function onPublishChange() {
    var box = byId("peer-publish-checkbox");
    if (!box) return;
    if (box.checked) {
      if (!signedIn()) { box.checked = false; refreshPublishUi(); return; }
      setPublishNote("Checking your account...");
      var user = "";
      try { user = await whoAmI(); } catch (e) { user = ""; }
      if (!user) {
        box.checked = false;
        setPublishNote("Could not check your account just now, so nothing is shared. Try again later.");
        return;
      }
      STATE.on = true; STATE.user = user; STATE.pendingDelete = false; saveState();
      lastSent = { season: -1, era: -1 };
      await publishNow(true, user);
    } else {
      STATE.on = false; STATE.pendingDelete = true; saveState();
      lastSent = { season: -1, era: -1 };
      setPublishNote("Removing what was shared...");
      var gone = signedIn() ? await deleteShared() : false;
      setPublishNote(gone
        ? "Stopped sharing. What you shared has been removed."
        : "Stopped sharing. We could not reach the server to remove it; it will be removed the next time you open the game while signed in.");
    }
  }

  // ---- looking at another settlement ----
  function shownGhostId() { var id = py("peer_ghost_id"); return typeof id === "string" ? id : ""; }

  async function onShow() {
    if (busy.show) return;
    busy.show = true;
    var button = byId("peer-show-button");
    if (button) button.disabled = true;
    setStatus("Looking for another settlement...");
    try {
      var rawQuery = py("peer_query_json", shownGhostId());
      var query = rawQuery ? JSON.parse(rawQuery) : null;
      if (!query) { setStatus(message("unavailable")); return; }
      var params = new URLSearchParams({ scenario: query.scenario, era: String(query.era), hard: String(query.hard) });
      if (query.exclude) params.set("exclude", query.exclude);
      var res = await getJson("/ghosts/" + GAME + "/peer?" + params.toString(), { headers: authHeaders() });
      if (!res.ok || !res.body) { setStatus(message("unavailable")); return; }
      if (!res.body.ghost) { setStatus(message(typeof res.body.reason === "string" ? res.body.reason : "unavailable")); return; }
      var shown = py("peer_show", JSON.stringify(res.body.ghost));
      if (shown === true) {
        setStatus(message("shown"));
        var report = byId("peer-report-button");
        if (report) { report.disabled = false; report.textContent = "Report this settlement"; }
      } else {
        setStatus(message("unavailable"));
      }
    } catch (e) {
      setStatus(message("unavailable"));
    } finally {
      busy.show = false;
      if (button) button.disabled = false;
    }
  }

  async function onReport() {
    var id = shownGhostId();
    var button = byId("peer-report-button");
    if (!id || !button) return;
    button.disabled = true;
    try {
      var res = await getJson("/ghosts/report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ game: GAME, ghost_id: id, reason: "implausible" }),
      });
      if (res.ok) {
        button.textContent = "Reported, thank you";
        setStatus("Thank you. The report was sent; the owner reviews them.");
        return;
      }
    } catch (e) { /* fall through */ }
    button.disabled = false;
    setStatus("Could not send the report just now. Nothing was changed.");
  }

  // Called by game.py after every completed season (a no-op unless sharing is on and a publish is due).
  function seasonDone() {
    if (STATE.on) publishNow(false);
  }

  function init() {
    loadState();
    var box = byId("peer-publish-checkbox");
    if (box) box.addEventListener("change", onPublishChange);
    var show = byId("peer-show-button");
    if (show) show.addEventListener("click", onShow);
    var report = byId("peer-report-button");
    if (report) report.addEventListener("click", onReport);
    var settings = byId("settings-toggle-button");
    if (settings) settings.addEventListener("click", refreshPublishUi);
    window.addEventListener("focus", refreshPublishUi);
    refreshPublishUi();
    verifyOwner();
  }

  // The switch belongs to the account that ticked it. If a different account is signed in now, the
  // switch is turned off (nothing is deleted or sent), and a removal left pending by the earlier account
  // is only retried while that same account is signed in.
  async function verifyOwner() {
    if (!signedIn() || !(STATE.on || STATE.pendingDelete)) return;
    var user = "";
    try { user = await whoAmI(); } catch (e) { return; }
    if (!user) return;
    if (STATE.user && user !== STATE.user) {
      if (STATE.on) {
        STATE.on = false; saveState(); refreshPublishUi();
        setPublishNote("Sharing was switched off because you are signed in as a different account. Tick the box again to share from this one.");
      }
      return;
    }
    if (STATE.pendingDelete && !STATE.on) deleteShared();
  }

  window.ContinuumPeers = { seasonDone: seasonDone, refreshPublishUi: refreshPublishUi, _state: STATE };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
