/*
 * GN-18: the owner's "Playtest queue" on the hub, a scrolling row of cards for the games Claude most
 * wants played next. Each card gives the reason, how to try it and numbered questions with a small text
 * box each (max 400 characters) and a "Done" checkbox per item.
 *
 * Gate: shown only while signed in as the owner account "noyvj" (GET /users/me, token in
 * localStorage["hub_bearer_token"], the same check shared/owner-links.js makes). For anyone else the
 * mount stays empty and hidden and owner-playtest.json is never requested.
 *
 * Data: owner-playtest.json (items with id, game, title, since, why, how, questions[]). Malformed
 * entries are ignored. Every piece of text goes in with textContent.
 *
 * Answers: saved to localStorage["owner-playtest-v1"] on every keystroke, and pushed to the owner note
 * "playtest-notes" (PUT /owner/notes/playtest-notes, body {value: {version: 1, answers: {...}}}, the
 * same shape ideas.html uses for "game-notes") when a box loses focus, when a Done box is ticked and
 * when the page is hidden or closed. No timers. The note is pulled once when the queue opens and merged
 * per question, the newer edit wins. If the server cannot be reached the answers stay on this device
 * and the status line says so.
 *
 * Stored shape: { "<item id>": { q: { "0": { t: "text", u: ms, p: "the question" } }, d: 0|1, du: ms,
 *                                 g: "<game>", n: "<title>" } }
 */
(function () {
  "use strict";
  const OWNER = "noyvj";
  const API_BASE = "https://noyvjgames.fastapicloud.dev";
  const NOTE_URL = API_BASE + "/owner/notes/playtest-notes";
  const TOKEN_KEY = "hub_bearer_token";
  const USERNAME_KEY = "hub_account_username";
  const STORE_KEY = "owner-playtest-v1";
  const DATA_URL = "owner-playtest.json";
  const MAX_ANSWER = 400;

  const mount = document.getElementById("owner-playtest");
  if (!mount) return;

  const lsGet = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const lsSet = (k, v) => { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } };

  let items = [];
  let answers = {};
  let shown = false;
  let checkSeq = 0;
  let pushing = false;
  let pushAgain = false;
  let dirty = false;
  let ui = null;   // { section, track, prev, next, count, status, copyBtn }

  // ---- the owner check (same rules as shared/owner-links.js) --------------------------------------
  async function isOwner() {
    const token = lsGet(TOKEN_KEY);
    if (!token) return false;
    const stored = (lsGet(USERNAME_KEY) || "").toLowerCase() === OWNER;
    try {
      const res = await fetch(API_BASE + "/users/me", { headers: { Authorization: "Bearer " + token }, cache: "no-store" });
      if (res.ok) return String((await res.json()).username || "").toLowerCase() === OWNER;
      if (res.status === 401) return false;
      return stored;
    } catch (e) {
      return stored;
    }
  }

  // ---- data ----------------------------------------------------------------------------------------
  function cleanItems(raw) {
    const list = raw && Array.isArray(raw.items) ? raw.items : [];
    const seen = new Set();
    const out = [];
    for (const it of list) {
      if (!it || typeof it !== "object") continue;
      const id = typeof it.id === "string" ? it.id.trim() : "";
      const title = typeof it.title === "string" ? it.title.trim() : "";
      const game = typeof it.game === "string" ? it.game.trim() : "";
      if (!id || !title || !/^[a-z0-9-]+$/.test(game) || seen.has(id)) continue;
      const questions = Array.isArray(it.questions) ? it.questions.filter((q) => typeof q === "string" && q.trim()).map((q) => q.trim()) : [];
      seen.add(id);
      out.push({
        id, title, game, questions,
        since: typeof it.since === "string" ? it.since : "",
        why: typeof it.why === "string" ? it.why : "",
        how: typeof it.how === "string" ? it.how : "",
      });
    }
    return out;
  }

  function loadAnswers() {
    try {
      const parsed = JSON.parse(lsGet(STORE_KEY) || "{}");
      answers = parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
    } catch (e) { answers = {}; }
  }
  function saveAnswers() { return lsSet(STORE_KEY, JSON.stringify(answers)); }
  function entry(id) {
    if (!answers[id] || typeof answers[id] !== "object") answers[id] = {};
    if (!answers[id].q || typeof answers[id].q !== "object") answers[id].q = {};
    return answers[id];
  }
  const answerOf = (id, i) => { const a = answers[id] && answers[id].q && answers[id].q[i]; return a && typeof a.t === "string" ? a.t : ""; };
  const isDone = (id) => Boolean(answers[id] && answers[id].d);

  function gameName(slug) {
    if (slug === "hub") return "the hub";
    const link = document.querySelector('.title-card-link[href="games/' + slug + '/index.html"] .title-card-name');
    if (link && link.textContent.trim()) return link.textContent.trim();
    return slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  // ---- rendering -----------------------------------------------------------------------------------
  const reduced = () => {
    try {
      return window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
        document.documentElement.getAttribute("data-hub-reduced-motion") === "true" ||
        document.documentElement.getAttribute("data-lite") === "true";
    } catch (e) { return false; }
  };
  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };

  function updateScroll() {
    if (!ui) return;
    const t = ui.track;
    const max = t.scrollWidth - t.clientWidth;
    ui.section.classList.toggle("is-fit", max <= 2);
    ui.prev.disabled = t.scrollLeft <= 4;
    ui.next.disabled = t.scrollLeft >= max - 2;
  }

  function build() {
    mount.textContent = "";
    const section = el("div", "owner-playtest-inner");
    const head = el("div", "owner-playtest-head");
    const title = el("h2", "owner-playtest-title", "Playtest queue");
    title.id = "owner-playtest-heading";
    const count = el("span", "owner-playtest-count");
    const controls = el("div", "owner-playtest-controls");
    const mk = (dir, glyph) => {
      const b = el("button", null, glyph);
      b.type = "button";
      b.setAttribute("aria-label", "Scroll the Playtest queue " + dir);
      return b;
    };
    const prev = mk("left", "‹");
    const next = mk("right", "›");
    controls.append(prev, next);
    head.append(title, count, controls);
    const intro = el("p", "owner-playtest-intro",
      "Games Claude most wants played next, with the questions each playtest should answer. Only you can see this. " +
      "Answers save on this device as you type and sync to your account's playtest note, which Claude reads.");
    const track = el("div", "owner-playtest-track");
    track.tabIndex = 0;
    track.setAttribute("role", "region");
    track.setAttribute("aria-labelledby", title.id);
    const foot = el("div", "owner-playtest-foot");
    const copyBtn = el("button", "secondary owner-playtest-copy", "Copy all answers");
    copyBtn.type = "button";
    const status = el("p", "owner-playtest-status");
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    foot.append(copyBtn, status);
    section.append(head, intro, track, foot);
    mount.append(section);

    ui = { section, track, prev, next, count, status, copyBtn };
    const step = (dir) => () => {
      track.scrollBy({ left: dir * Math.max(200, Math.round(track.clientWidth * 0.85)), behavior: reduced() ? "auto" : "smooth" });
    };
    prev.addEventListener("click", step(-1));
    next.addEventListener("click", step(1));
    track.addEventListener("scroll", updateScroll, { passive: true });
    if (window.ResizeObserver) new ResizeObserver(updateScroll).observe(track);
    copyBtn.addEventListener("click", copyAll);
    // Saving to the server: when a box loses focus after a change (the "change" event) and via the Done box.
    track.addEventListener("change", (e) => {
      const t = e.target;
      if (t && t.classList && t.classList.contains("owner-playtest-answer")) syncNow();
    });
  }

  function doneCheckbox(item) {
    const label = el("label", "owner-playtest-done");
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = isDone(item.id);
    box.dataset.itemId = item.id;
    box.addEventListener("change", () => setDone(item, box.checked));
    label.append(box, el("span", null, "Done"));
    return label;
  }

  function card(item) {
    const done = isDone(item.id);
    const art = el("article", "owner-playtest-card" + (done ? " is-done" : ""));
    art.dataset.itemId = item.id;
    const h = el("h3", "owner-playtest-card-title", item.title);
    h.id = "pt-title-" + item.id;
    art.setAttribute("aria-labelledby", h.id);
    if (done) {
      art.classList.add("owner-playtest-card--collapsed");
      art.append(h, doneCheckbox(item));
      return art;
    }
    const meta = el("p", "owner-playtest-meta");
    const link = document.createElement("a");
    link.className = "owner-playtest-game";
    link.href = item.game === "hub" ? "index.html" : "games/" + item.game + "/index.html";
    link.textContent = item.game === "hub" ? "Open the hub" : "Play " + gameName(item.game);
    meta.append(link);
    if (item.since) meta.append(el("span", "owner-playtest-since", " Added " + item.since));
    art.append(h, meta);
    if (item.why) { const p = el("p", "owner-playtest-why"); p.append(el("strong", null, "Why: "), document.createTextNode(item.why)); art.append(p); }
    if (item.how) { const p = el("p", "owner-playtest-how"); p.append(el("strong", null, "How to try it: "), document.createTextNode(item.how)); art.append(p); }
    if (item.questions.length) {
      const ol = el("ol", "owner-playtest-questions");
      item.questions.forEach((q, i) => {
        const li = el("li", "owner-playtest-question");
        const id = "pt-" + item.id + "-" + i;
        const lab = el("label", "owner-playtest-qlabel", q);
        lab.htmlFor = id;
        const ta = document.createElement("textarea");
        ta.id = id;
        ta.className = "owner-playtest-answer";
        ta.rows = 2;
        ta.maxLength = MAX_ANSWER;
        ta.value = answerOf(item.id, i);
        ta.dataset.itemId = item.id;
        ta.dataset.q = String(i);
        ta.addEventListener("input", () => setAnswer(item, i, ta.value));
        li.append(lab, ta);
        ol.append(li);
      });
      art.append(ol);
    }
    art.append(doneCheckbox(item));
    return art;
  }

  function render() {
    if (!ui) return;
    const focusId = document.activeElement && document.activeElement.dataset ? document.activeElement.dataset.itemId : null;
    const open = items.filter((it) => !isDone(it.id));
    const finished = items.filter((it) => isDone(it.id));
    ui.track.textContent = "";
    ui.track.append(...open.map(card), ...finished.map(card));
    ui.count.textContent = open.length + " to try" + (finished.length ? ", " + finished.length + " done" : "");
    updateScroll();
    if (focusId && document.activeElement === document.body) {
      const again = ui.track.querySelector('input[type="checkbox"][data-item-id="' + focusId.replace(/[^a-z0-9-]/g, "") + '"]');
      if (again) again.focus();
    }
  }

  // ---- answers: local save, then server sync ---------------------------------------------------------
  function setStatus(text) { if (ui) ui.status.textContent = text; }
  function setAnswer(item, i, value) {
    const text = String(value || "").slice(0, MAX_ANSWER);
    const e = entry(item.id);
    e.g = item.game; e.n = item.title;
    e.q[i] = { t: text, u: Date.now(), p: item.questions[i] };
    dirty = true;
    setStatus(saveAnswers() ? "Saved on this device. Syncs when you leave the box." : "Could not save on this device (storage is blocked).");
  }
  function setDone(item, value) {
    const e = entry(item.id);
    e.g = item.game; e.n = item.title;
    e.d = value ? 1 : 0;
    e.du = Date.now();
    dirty = true;
    saveAnswers();
    render();
    syncNow();
  }

  function authHeaders() {
    const token = lsGet(TOKEN_KEY);
    return token ? { Authorization: "Bearer " + token, "Content-Type": "application/json" } : null;
  }
  async function syncNow(opts) {
    if (!shown || !dirty) return;
    const headers = authHeaders();
    if (!headers) { setStatus("Saved on this device only (sign in to sync)."); return; }
    if (pushing) { pushAgain = true; return; }
    pushing = true;
    setStatus("Saving…");
    try {
      const res = await fetch(NOTE_URL, {
        method: "PUT", headers, keepalive: Boolean(opts && opts.keepalive),
        body: JSON.stringify({ value: { version: 1, answers } }),
      });
      if (res.ok) { dirty = false; setStatus("Saved on this device and synced"); }
      else setStatus("Saved on this device, not synced (" + res.status + "). Your answers stay on this device.");
    } catch (e) {
      setStatus("Saved on this device, not synced (offline). Your answers stay on this device.");
    }
    pushing = false;
    if (pushAgain) { pushAgain = false; syncNow(); }
  }

  async function pull() {
    const headers = authHeaders();
    if (!headers) return;
    try {
      const res = await fetch(NOTE_URL, { headers, cache: "no-store" });
      if (!res.ok) return;
      const body = await res.json();
      const remote = body && body.value && body.value.answers;
      if (!remote || typeof remote !== "object") return;
      let changed = false;
      let mineNewer = false;
      for (const [id, theirs] of Object.entries(remote)) {
        if (!theirs || typeof theirs !== "object") continue;
        const mine = entry(id);
        for (const [qi, a] of Object.entries(theirs.q || {})) {
          if (!a || typeof a.t !== "string") continue;
          const own = mine.q[qi];
          if (!own || (a.u || 0) > (own.u || 0)) {
            mine.q[qi] = { t: a.t.slice(0, MAX_ANSWER), u: Number(a.u) || 0, p: typeof a.p === "string" ? a.p : "" };
            changed = true;
          }
        }
        if ((theirs.du || 0) > (mine.du || 0)) { mine.d = theirs.d ? 1 : 0; mine.du = Number(theirs.du) || 0; changed = true; }
        if (typeof theirs.g === "string" && !mine.g) mine.g = theirs.g;
        if (typeof theirs.n === "string" && !mine.n) mine.n = theirs.n;
      }
      for (const [id, mine] of Object.entries(answers)) {
        const theirs = remote[id] || {};
        if ((mine.du || 0) > (theirs.du || 0)) mineNewer = true;
        for (const [qi, a] of Object.entries(mine.q || {})) if (!theirs.q || !theirs.q[qi] || (a.u || 0) > (theirs.q[qi].u || 0)) mineNewer = true;
      }
      if (changed) {
        saveAnswers();
        const typing = document.activeElement && document.activeElement.classList && document.activeElement.classList.contains("owner-playtest-answer");
        if (!typing) render();
      }
      if (mineNewer) { dirty = true; await syncNow(); }
    } catch (e) { /* offline: the device copy stays */ }
  }

  // ---- copy all answers ------------------------------------------------------------------------------
  function markdown() {
    const lines = ["# Playtest answers", ""];
    for (const item of items) {
      lines.push("## " + item.title + (item.game === "hub" ? " (hub)" : " (" + item.game + ")") + (isDone(item.id) ? " [done]" : ""));
      if (!item.questions.length) lines.push("(no questions)");
      item.questions.forEach((q, i) => {
        const a = answerOf(item.id, i).trim();
        lines.push((i + 1) + ". " + q);
        lines.push("   Answer: " + (a ? a.replace(/\n+/g, " ") : "(not answered)"));
      });
      lines.push("");
    }
    return lines.join("\n").trimEnd() + "\n";
  }
  async function copyAll() {
    const text = markdown();
    try {
      await navigator.clipboard.writeText(text);
      setStatus("Copied all answers as Markdown.");
      return;
    } catch (e) { /* fall through to the old way */ }
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.append(ta);
      ta.select();
      const ok = document.execCommand("copy");
      ta.remove();
      setStatus(ok ? "Copied all answers as Markdown." : "Could not copy. Select the text yourself.");
    } catch (e) {
      setStatus("Could not copy on this browser.");
    }
  }

  // ---- show / hide -----------------------------------------------------------------------------------
  function hide() {
    shown = false;
    ui = null;
    mount.textContent = "";
    mount.hidden = true;
  }
  async function show() {
    if (shown) return;
    let raw = null;
    try {
      const res = await fetch(DATA_URL, { cache: "no-store" });
      if (res.ok) raw = await res.json();
    } catch (e) { raw = null; }
    items = cleanItems(raw);
    if (!items.length) { hide(); return; }
    shown = true;
    loadAnswers();
    build();
    render();
    mount.hidden = false;
    updateScroll();
    pull();
  }
  async function refresh() {
    const seq = ++checkSeq;
    const owner = await isOwner();
    if (seq !== checkSeq) return;
    if (owner) await show(); else hide();
  }

  window.NoyvjOwnerPlaytest = { refresh, markdown };

  // Leaving the page: push whatever has not gone yet.
  window.addEventListener("pagehide", () => syncNow({ keepalive: true }));
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") syncNow({ keepalive: true }); });
  // Signing in or out on the hub: script.js calls NoyvjOwnerLinks.refresh(), so follow it (this file loads after owner-links.js).
  if (window.NoyvjOwnerLinks && typeof window.NoyvjOwnerLinks.refresh === "function") {
    const original = window.NoyvjOwnerLinks.refresh;
    window.NoyvjOwnerLinks.refresh = function () {
      const result = original.apply(this, arguments);
      refresh();
      return result;
    };
  }
  window.addEventListener("storage", (e) => { if (e.key === TOKEN_KEY) refresh(); });

  if (lsGet(TOKEN_KEY)) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", refresh);
    else refresh();
  }
})();
