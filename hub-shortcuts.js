/*
 * Hub keyboard shortcuts (Y-19), the hub-side twin of shared/keyboard-shortcuts.js's "?" convention.
 *
 *   /        focus the search box (the hub's game search, or the Help page's search)
 *   ?        list the shortcuts
 *   g then a letter   go to a hub page (g r = Roadmap, g s = Settings, ...)
 *
 * Included on the hub and its plain pages. Every key is rebindable on settings.html: the choice
 * lives in localStorage["hub_shortcuts"] as {actionId: key}; anything missing or invalid falls back
 * to the default. Shortcuts never fire while typing in a field, with Ctrl/Cmd/Alt held, or while
 * the first-visit survey is open.
 *
 * window.HubShortcuts is the small API settings.html uses to show and edit the bindings.
 */
(function () {
  "use strict";

  const STORAGE_KEY = "hub_shortcuts";
  const PREFIX = "g";
  const SEQUENCE_WINDOW_MS = 1500;

  // type "single": one key. type "go": the prefix key, then this key.
  const ACTIONS = [
    { id: "search", type: "single", key: "/", label: "Focus the search box", scope: "hub and Help pages" },
    { id: "help", type: "single", key: "?", label: "Show this shortcut list" },
    { id: "home", type: "go", key: "h", label: "Go to the hub (games)", href: "index.html" },
    { id: "achievements", type: "go", key: "a", label: "Go to Achievements", href: "achievements.html" },
    { id: "whatsnew", type: "go", key: "w", label: "Go to What's New", href: "whats-new.html" },
    { id: "roadmap", type: "go", key: "r", label: "Go to the Roadmap", href: "roadmap.html" },
    { id: "faq", type: "go", key: "f", label: "Go to Help & FAQ", href: "help.html" },
    { id: "settings", type: "go", key: "s", label: "Go to Settings", href: "settings.html" },
    { id: "credits", type: "go", key: "c", label: "Go to Credits & Thanks", href: "credits.html" },
    { id: "sources", type: "go", key: "o", label: "Go to Sources", href: "sources.html" },
    { id: "terms", type: "go", key: "t", label: "Go to Terms & Privacy", href: "terms.html" },
  ];

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }

  // A key is usable when it is one visible character that is not a space and not the prefix
  // (the prefix is what starts a sequence, so it cannot also be a binding).
  function validKey(key) {
    return typeof key === "string" && key.length === 1 && key.trim() === key && key !== " " &&
      key.toLowerCase() !== PREFIX;
  }

  function stored() {
    try {
      const parsed = JSON.parse(lsGet(STORAGE_KEY) || "{}");
      return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
    } catch (e) {
      return {};
    }
  }

  // Resolves each action to the key in use. A stored key is ignored when it is invalid, or when it
  // clashes with another action of the same type that was resolved first (so a hand-edited or
  // half-saved value can never produce two actions on one key).
  function bindings() {
    const saved = stored();
    const used = { single: new Set(), go: new Set() };
    const out = {};
    ACTIONS.forEach((action) => {
      let key = action.key;
      const candidate = saved[action.id];
      if (validKey(candidate) && !used[action.type].has(candidate.toLowerCase())) key = candidate;
      if (used[action.type].has(key.toLowerCase())) key = null;
      if (key) used[action.type].add(key.toLowerCase());
      out[action.id] = key;
    });
    return out;
  }

  // Returns "" when `key` can be given to `actionId`, otherwise a sentence saying why not.
  function conflict(actionId, key) {
    const action = ACTIONS.find((a) => a.id === actionId);
    if (!action) return "Unknown shortcut.";
    if (!validKey(key)) {
      return key && key.toLowerCase() === PREFIX
        ? `"${PREFIX}" starts the go-to shortcuts, so it cannot be used as a key.`
        : "Use a single letter, number or symbol.";
    }
    const current = bindings();
    const clash = ACTIONS.find(
      (a) => a.id !== actionId && a.type === action.type && current[a.id] &&
        current[a.id].toLowerCase() === key.toLowerCase()
    );
    return clash ? `"${key}" is already used for: ${clash.label}.` : "";
  }

  function save(map) {
    lsSet(STORAGE_KEY, JSON.stringify(map));
  }
  function setBinding(actionId, key) {
    if (conflict(actionId, key)) return false;
    const saved = stored();
    saved[actionId] = key;
    save(saved);
    return true;
  }
  function resetAll() {
    try { localStorage.removeItem(STORAGE_KEY); } catch (e) { /* convenience only */ }
  }

  function display(action, key) {
    if (!key) return "unassigned";
    return action.type === "go" ? `${PREFIX} then ${key}` : key;
  }

  // ---------- behaviour ----------

  let suspended = false;
  let waitingForSecond = false;
  let sequenceTimer = null;
  let overlay = null;
  let lastFocus = null;

  function isTypingTarget(target) {
    if (!target) return false;
    const tag = target.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || Boolean(target.isContentEditable);
  }

  function hint(text) {
    let el = document.getElementById("hub-shortcut-hint");
    if (!text) {
      if (el) el.hidden = true;
      return;
    }
    if (!el) {
      el = document.createElement("div");
      el.id = "hub-shortcut-hint";
      el.className = "hub-shortcut-hint";
      el.setAttribute("role", "status");
      document.body.appendChild(el);
    }
    el.textContent = text;
    el.hidden = false;
  }

  function endSequence() {
    waitingForSecond = false;
    clearTimeout(sequenceTimer);
    hint("");
  }

  function closeOverlay() {
    if (!overlay) return;
    overlay.remove();
    overlay = null;
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  function openOverlay() {
    if (overlay) return;
    lastFocus = document.activeElement;
    const current = bindings();
    overlay = document.createElement("div");
    overlay.id = "hub-shortcuts-overlay";
    overlay.className = "hub-shortcuts-overlay";
    const panel = document.createElement("div");
    panel.className = "hub-shortcuts-panel";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-modal", "true");
    panel.setAttribute("aria-label", "Keyboard shortcuts");
    const title = document.createElement("h2");
    title.textContent = "Keyboard shortcuts";
    panel.appendChild(title);
    const list = document.createElement("dl");
    list.className = "hub-shortcuts-list";
    ACTIONS.forEach((action) => {
      const dt = document.createElement("dt");
      const kbd = document.createElement("kbd");
      kbd.textContent = display(action, current[action.id]);
      dt.appendChild(kbd);
      const dd = document.createElement("dd");
      dd.textContent = action.label + (action.scope ? ` (${action.scope})` : "");
      list.appendChild(dt);
      list.appendChild(dd);
    });
    panel.appendChild(list);
    const foot = document.createElement("p");
    foot.className = "hub-shortcuts-foot";
    foot.appendChild(document.createTextNode("Shortcuts are off while you type in a field. Change any of them in "));
    const link = document.createElement("a");
    link.href = "settings.html#shortcuts";
    link.textContent = "Settings";
    foot.appendChild(link);
    foot.appendChild(document.createTextNode(". Press Esc to close."));
    panel.appendChild(foot);
    const close = document.createElement("button");
    close.type = "button";
    close.className = "secondary";
    close.textContent = "Close";
    close.addEventListener("click", closeOverlay);
    panel.appendChild(close);
    overlay.appendChild(panel);
    overlay.addEventListener("click", (event) => { if (event.target === overlay) closeOverlay(); });
    document.body.appendChild(overlay);
    close.focus();
  }

  function onKeyDown(event) {
    if (suspended) return;
    if (event.key === "Escape" && overlay) {
      closeOverlay();
      event.preventDefault();
      return;
    }
    if (event.key === "Escape" && waitingForSecond) {
      endSequence();
      return;
    }
    if (event.ctrlKey || event.metaKey || event.altKey || event.isComposing) return;
    if (isTypingTarget(event.target)) return;
    if (document.getElementById("onboarding-survey-overlay")) return;
    if (event.key.length !== 1) return; // Shift, Tab, arrows, ...
    const key = event.key.toLowerCase();
    const current = bindings();

    if (waitingForSecond) {
      endSequence();
      const action = ACTIONS.find((a) => a.type === "go" && current[a.id] && current[a.id].toLowerCase() === key);
      if (action) {
        event.preventDefault();
        const here = location.pathname.split("/").pop() || "index.html";
        if (action.href === here || (action.href === "index.html" && here === "")) {
          window.scrollTo(0, 0);
        } else {
          location.href = action.href;
        }
      }
      return;
    }

    if (key === PREFIX) {
      if (overlay) return;
      waitingForSecond = true;
      hint(`${PREFIX} … (then a letter, Esc to cancel)`);
      sequenceTimer = setTimeout(endSequence, SEQUENCE_WINDOW_MS);
      event.preventDefault();
      return;
    }

    const single = ACTIONS.find((a) => a.type === "single" && current[a.id] && current[a.id].toLowerCase() === key);
    if (!single) return;
    if (single.id === "help") {
      event.preventDefault();
      if (overlay) closeOverlay(); else openOverlay();
    } else if (single.id === "search") {
      const input = document.getElementById("game-search-input") || document.querySelector("[data-hub-search]");
      if (input) {
        event.preventDefault();
        input.focus();
        input.select();
      }
    }
  }

  document.addEventListener("keydown", onKeyDown);

  window.HubShortcuts = {
    ACTIONS,
    PREFIX,
    bindings,
    conflict,
    setBinding,
    resetAll,
    display,
    // settings.html pauses the shortcuts while it is capturing a new key.
    suspend(value) { suspended = Boolean(value); if (suspended) endSequence(); },
  };
})();
