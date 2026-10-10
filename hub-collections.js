/*
 * Hub personal collections (TODO Y-18), loaded on index.html after script.js.
 *
 * A collection is a list of games the player groups for themselves ("Cozy", "Play on phone",
 * "Class evidence"). They never change the shared tags on the title cards, which stay the same for
 * everyone. A card's "Collections" menu (inside Show more) adds or removes that game; once at
 * least one collection exists the lobby filter bar gets an "Any collection" dropdown.
 *
 * Stored on this device only, in localStorage["hub_collections_v1"]:
 *   { "version": 1, "collections": [ { "id": "c-k3f9", "name": "Cozy", "slugs": ["canopy", "herd"] } ] }
 * and the chosen filter in localStorage["hub_filter_collection"]. Syncing to the account would need
 * a new whitelisted key on the settings endpoint; see the note in the Y-18 report. Reading is
 * defensive: bad JSON, odd names and unknown slugs are dropped, never thrown on.
 *
 * window.HubCollections: list(), create(name), toggle(id, slug), includes(id, slug), rename(id, name),
 * remove(id), sanitize(raw), MAX_COLLECTIONS.
 */
(function () {
  "use strict";

  const KEY = "hub_collections_v1";
  const FILTER_KEY = "hub_filter_collection";
  const MAX_COLLECTIONS = 12;
  const MAX_NAME = 24;
  const SUGGESTIONS = ["Cozy", "Play on phone", "Class evidence"];
  const SLUG_RE = /^[a-z0-9-]{1,40}$/;
  const ID_RE = /^c-[a-z0-9]{1,12}$/;

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }

  function cleanName(text) {
    return typeof text === "string" ? text.replace(/\s+/g, " ").trim().slice(0, MAX_NAME) : "";
  }

  function sanitize(raw) {
    const out = [];
    if (!raw || typeof raw !== "object" || raw.version !== 1 || !Array.isArray(raw.collections)) return out;
    const names = new Set();
    raw.collections.forEach((c) => {
      if (out.length >= MAX_COLLECTIONS || !c || typeof c !== "object") return;
      const name = cleanName(c.name);
      if (!name || !ID_RE.test(String(c.id)) || names.has(name.toLowerCase()) || out.some((o) => o.id === c.id)) return;
      names.add(name.toLowerCase());
      const slugs = [];
      (Array.isArray(c.slugs) ? c.slugs : []).forEach((s) => { if (typeof s === "string" && SLUG_RE.test(s) && !slugs.includes(s)) slugs.push(s); });
      out.push({ id: c.id, name, slugs });
    });
    return out;
  }

  function read() {
    try { return sanitize(JSON.parse(lsGet(KEY))); } catch (e) { return []; }
  }
  function write(list) { lsSet(KEY, JSON.stringify({ version: 1, collections: list })); }

  function list() { return read(); }
  function includes(id, slug) {
    const c = read().find((x) => x.id === id);
    return Boolean(c && c.slugs.includes(slug));
  }

  /** { ok, id, error } */
  function create(name) {
    const clean = cleanName(name);
    const all = read();
    if (!clean) return { ok: false, error: "Give the collection a name." };
    if (all.length >= MAX_COLLECTIONS) return { ok: false, error: "You can keep up to " + MAX_COLLECTIONS + " collections. Delete one first." };
    if (all.some((c) => c.name.toLowerCase() === clean.toLowerCase())) return { ok: false, error: "You already have a collection called " + clean + "." };
    let id;
    do { id = "c-" + Math.random().toString(36).slice(2, 7); } while (all.some((c) => c.id === id) || !ID_RE.test(id));
    all.push({ id, name: clean, slugs: [] });
    write(all);
    return { ok: true, id };
  }
  function toggle(id, slug) {
    const all = read();
    const c = all.find((x) => x.id === id);
    if (!c || !SLUG_RE.test(String(slug))) return false;
    const i = c.slugs.indexOf(slug);
    if (i >= 0) c.slugs.splice(i, 1); else c.slugs.push(slug);
    write(all);
    return i < 0;
  }
  function rename(id, name) {
    const clean = cleanName(name);
    const all = read();
    const c = all.find((x) => x.id === id);
    if (!c || !clean) return { ok: false, error: "Give the collection a name." };
    if (all.some((x) => x.id !== id && x.name.toLowerCase() === clean.toLowerCase())) return { ok: false, error: "You already have a collection called " + clean + "." };
    c.name = clean;
    write(all);
    return { ok: true };
  }
  function remove(id) {
    write(read().filter((c) => c.id !== id));
    if (lsGet(FILTER_KEY) === id) lsSet(FILTER_KEY, "");
  }

  window.HubCollections = { list, create, toggle, includes, rename, remove, sanitize, MAX_COLLECTIONS, filterValue: () => (document.getElementById("game-collection-filter") || {}).value || "" };

  // ---- page ------------------------------------------------------------------------------------

  function el(tag, className, text) {
    const n = document.createElement(tag);
    if (className) n.className = className;
    if (text !== undefined) n.textContent = text;
    return n;
  }

  let uid = 0;
  const cards = [];

  function slugOf(card) {
    const w = card.querySelector(".review-widget");
    return w ? w.dataset.gameSlug : "";
  }

  function announce(text) {
    const region = document.getElementById("collections-live");
    if (region) region.textContent = text;
  }

  function buildCardMenu(card) {
    const slug = slugOf(card);
    const name = (card.querySelector(".title-card-name") || {}).textContent || slug;
    const actions = card.querySelector(".title-card-actions");
    if (!slug || !actions) return null;
    const details = el("details", "title-card-collections");
    const summary = el("summary", "collections-summary");
    details.appendChild(summary);
    const body = el("div", "collections-body");
    details.appendChild(body);
    const note = el("p", "collections-note");
    note.setAttribute("aria-live", "polite");
    actions.appendChild(details);
    actions.appendChild(note);
    uid += 1;
    const myUid = uid;

    function render() {
      const all = read();
      const mine = all.filter((c) => c.slugs.includes(slug));
      summary.textContent = mine.length ? "Collections (" + mine.length + ")" : "Add to a collection";
      note.textContent = mine.length ? "In your collections: " + mine.map((c) => c.name).join(", ") + "." : "";
      body.textContent = "";
      const field = el("fieldset", "collections-field");
      field.appendChild(el("legend", "collections-legend", "Put " + name + " in:"));
      if (!all.length) field.appendChild(el("p", "collections-empty", "You have no collections yet. Make one below."));
      all.forEach((c, i) => {
        const label = el("label", "collections-option");
        const box = document.createElement("input");
        box.type = "checkbox";
        box.id = "coll-" + myUid + "-" + i;
        box.checked = c.slugs.includes(slug);
        box.addEventListener("change", () => {
          const added = toggle(c.id, slug);
          changed();
          announce(name + (added ? " added to " : " removed from ") + c.name + ".");
        });
        label.append(box, " " + c.name);
        field.appendChild(label);
      });
      body.appendChild(field);

      const form = el("form", "collections-new");
      const input = document.createElement("input");
      input.type = "text";
      input.maxLength = MAX_NAME;
      input.id = "coll-new-" + myUid;
      input.placeholder = "New collection";
      input.setAttribute("aria-label", "Name for a new collection");
      const add = el("button", "secondary", "Create and add");
      add.type = "submit";
      const err = el("p", "collections-error");
      err.setAttribute("role", "alert");
      form.append(input, add);
      form.addEventListener("submit", (ev) => {
        ev.preventDefault();
        makeAndAdd(input.value, err);
      });
      body.append(form, err);

      const taken = new Set(all.map((c) => c.name.toLowerCase()));
      const chips = SUGGESTIONS.filter((s) => !taken.has(s.toLowerCase()));
      if (chips.length && all.length < MAX_COLLECTIONS) {
        const row = el("p", "collections-suggest", "Ideas: ");
        chips.forEach((s) => {
          const b = el("button", "collections-chip account-link-button", s);
          b.type = "button";
          b.addEventListener("click", () => makeAndAdd(s, err));
          row.appendChild(b);
        });
        body.appendChild(row);
      }
    }

    function makeAndAdd(text, err) {
      const made = create(text);
      if (!made.ok) { err.textContent = made.error; return; }
      toggle(made.id, slug);
      changed();
      announce(name + " added to the new collection " + cleanName(text) + ".");
    }

    cards.push(render);
    render();
    return details;
  }

  function filterSelect() { return document.getElementById("game-collection-filter"); }

  function renderFilter() {
    const select = filterSelect();
    if (!select) return;
    const all = read();
    const chosen = select.value || lsGet(FILTER_KEY) || "";
    select.textContent = "";
    const any = document.createElement("option");
    any.value = "";
    any.textContent = "Any collection";
    select.appendChild(any);
    all.forEach((c) => {
      const o = document.createElement("option");
      o.value = c.id;
      o.textContent = c.name + " (" + c.slugs.length + ")";
      select.appendChild(o);
    });
    select.value = all.some((c) => c.id === chosen) ? chosen : "";
    select.hidden = all.length === 0;
    renderManage();
  }

  function renderManage() {
    const box = document.getElementById("collection-manage");
    const select = filterSelect();
    if (!select || !box) return;
    box.textContent = "";
    const c = read().find((x) => x.id === select.value);
    box.hidden = !c;
    if (!c) return;
    box.appendChild(el("span", "collection-manage-text", c.name + ": " + (c.slugs.length === 1 ? "1 game" : c.slugs.length + " games") + ". "));
    const renameBtn = el("button", "account-link-button", "Rename");
    renameBtn.type = "button";
    const delBtn = el("button", "account-link-button", "Delete collection");
    delBtn.type = "button";
    renameBtn.addEventListener("click", () => {
      box.textContent = "";
      const input = document.createElement("input");
      input.type = "text";
      input.value = c.name;
      input.maxLength = MAX_NAME;
      input.setAttribute("aria-label", "New name for " + c.name);
      const save = el("button", "secondary", "Save");
      save.type = "button";
      const cancel = el("button", "account-link-button", "Cancel");
      cancel.type = "button";
      const err = el("span", "collections-error");
      err.setAttribute("role", "alert");
      save.addEventListener("click", () => {
        const r = rename(c.id, input.value);
        if (!r.ok) { err.textContent = r.error; return; }
        changed();
      });
      cancel.addEventListener("click", renderManage);
      box.append(input, save, cancel, err);
      input.focus();
    });
    delBtn.addEventListener("click", () => {
      box.textContent = "";
      box.appendChild(el("span", "collection-manage-text", "Delete " + c.name + "? The games stay in the lobby."));
      const yes = el("button", "secondary", "Yes, delete");
      yes.type = "button";
      const no = el("button", "account-link-button", "Keep it");
      no.type = "button";
      yes.addEventListener("click", () => { remove(c.id); changed(); const s = filterSelect(); if (s) s.focus(); });
      no.addEventListener("click", renderManage);
      box.append(yes, no);
      no.focus();
    });
    box.append(renameBtn, delBtn);
  }

  function refilter() {
    if (window.HubLobby) window.HubLobby.applyFilter();
  }

  function changed() {
    const focusedId = document.activeElement && document.activeElement.id;
    cards.forEach((render) => render());
    renderFilter();
    refilter();
    if (focusedId && focusedId.indexOf("coll-") === 0) {
      const again = document.getElementById(focusedId);
      if (again) again.focus();
    }
  }

  function start() {
    const lobby = window.HubLobby;
    if (!lobby) return;
    lobby.cards.forEach(buildCardMenu);
    renderFilter();
    const select = filterSelect();
    if (select) {
      select.addEventListener("change", () => {
        lsSet(FILTER_KEY, select.value);
        renderManage();
        refilter();
      });
    }
    refilter();
    window.addEventListener("storage", (ev) => { if (ev.key === KEY) changed(); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
