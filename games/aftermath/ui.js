/* Aftermath, page-level helpers shared by the Classic and Desktop pages. No game state here (that is
   all in game.py): this file only clicks buttons the game already wires up, focuses the skill tree,
   and animates one number.

   E-14  Game keys: 1 / 2 invest in Resilience / Growth at the chosen step, Enter Face Next Event,
         U undo the last investment click, T jump to the skill tree, H Past Runs, C Disaster Codex,
         S Lifetime Stats. Listed in the shared "?" overlay (index.html passes them as `extra`).
   E-5   Focus moves to a panel when it opens and back to its button when it closes (Classic layout);
         the skill tree moves with the arrow keys, Enter unlocks, P pins. E-30 keeps the "Saved Ns ago" age fresh.
   E-2   The skill map: pan (drag, Shift+arrows), zoom (+ / - / 0, the buttons, Ctrl+scroll) and arrow-key
         movement between nodes. game.py owns the nodes, the route and every rule; this only moves the view
         and focus, and clicks the buttons game.py wires (Enter on a node is a plain button press). M opens it.
   E-31  The achievements tree strip shows a node's name and description on hover or focus.
   GE-13 The "-58 damage prevented!" line counts up from 0 when a new event resolves (skipped under
         reduced motion; the final text is always already in the page, so this is only a flourish). */
(function () {
  "use strict";

  function isTyping(target) {
    if (!target || !target.tagName) return false;
    return /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName) || Boolean(target.isContentEditable);
  }

  // Anything modal in front of the game: the opening screen, tutorial, a confirm dialog or the "?" list.
  function modalShown() {
    const selectors = "#opening-screen, #tutorial-card, #confirm-dialog-overlay:not([hidden]), .confirm-dialog-overlay, #kb-shortcuts-panel:not([hidden])";
    return Array.from(document.querySelectorAll(selectors)).some(function (node) {
      return node.getBoundingClientRect().width > 0;
    });
  }

  // On the Desktop page an open window sits over the game: the turn keys stay off so nothing happens
  // behind it, while the panel keys still toggle their own panels.
  function windowOpen() {
    const backdrop = document.getElementById("pc-backdrop");
    return Boolean(backdrop && !backdrop.hidden);
  }

  function press(id) {
    const button = document.getElementById(id);
    if (button && !button.disabled && !button.hidden) button.click();
  }

  function focusTree() {
    const tree = document.getElementById("skill-tree");
    if (!tree) return;
    const target = tree.querySelector("button:not([disabled]):not([hidden])") || tree;
    target.focus({ preventScroll: true });
    if (target.scrollIntoView) target.scrollIntoView({ block: "center" });
  }

  // M: open the skill map (a Menu window on the Desktop layout, a section of the page in Classic) and
  // put keyboard focus on its current node.
  function openSkillMap() {
    const opener = document.getElementById("pc-open-pc-skillmap-panel");
    const panel = document.getElementById("skill-map-panel");
    if (opener) opener.click();
    else if (panel) {
      panel.open = true;
      if (panel.scrollIntoView) panel.scrollIntoView({ block: "start" });
    }
    window.setTimeout(function () {
      const viewport = document.getElementById("skill-map-viewport");
      if (!viewport) return;
      const current = viewport.getAttribute("data-current");
      const node = (current && document.getElementById("skill-map-node-" + current)) || viewport.querySelector(".skill-map-node");
      if (node) node.focus({ preventScroll: true });
    }, 60);
  }

  const TURN_KEYS = { 1: "resilience-invest-button", 2: "growth-invest-button", u: "undo-allocation-button" };
  const PANEL_KEYS = { h: "past-runs-toggle-button", c: "codex-toggle-button", s: "stats-toggle-button" };

  document.addEventListener("keydown", function (event) {
    if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return;
    if (isTyping(event.target) || modalShown()) return;
    const key = String(event.key || "").toLowerCase();
    if (PANEL_KEYS[key]) {
      event.preventDefault();
      press(PANEL_KEYS[key]);
      return;
    }
    if (windowOpen()) return;
    if (TURN_KEYS[key]) {
      event.preventDefault();
      press(TURN_KEYS[key]);
    } else if (key === "t") {
      event.preventDefault();
      focusTree();
    } else if (key === "m") {
      event.preventDefault();
      openSkillMap();
    } else if (key === "enter") {
      // Enter on a focused button or link already activates it; only act from the bare page.
      const tag = event.target && event.target.tagName;
      if (tag && /^(BUTTON|A|SUMMARY|DETAILS)$/.test(tag)) return;
      event.preventDefault();
      press("resolve-event-button");
    }
  });

  // ---- GE-13 count-up --------------------------------------------------------------------------
  function reducedMotion() {
    const root = document.documentElement;
    if (root.getAttribute("data-reduced-motion") === "true") return true;
    return Boolean(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }

  let lastKey = "";
  function watchPopup() {
    const popup = document.getElementById("damage-prevented-popup");
    if (!popup) return;
    lastKey = popup.dataset.eventKey || "";
    function check() {
      const key = popup.dataset.eventKey;
      if (!key || key === lastKey) return;
      lastKey = key;
      if (reducedMotion()) return; // static number
      const target = Number(popup.dataset.prevented);
      const finalText = popup.textContent;
      if (!(target >= 1)) return;
      const steps = 12;
      let step = 0;
      const timer = window.setInterval(function () {
        step += 1;
        if (step >= steps) {
          window.clearInterval(timer);
          popup.textContent = finalText;
          return;
        }
        popup.textContent = "-" + Math.round((target * step) / steps) + " damage prevented!";
      }, 40);
    }
    new MutationObserver(check).observe(popup, { attributes: true, attributeFilter: ["data-event-key"] });
  }

  // E-17: hovering or focusing a chip in the schedule strip shows that event's details in the line
  // under it; leaving the strip restores the next event's details. The same text is on each chip as
  // its title and aria-label, so nothing depends on this script.
  function watchSchedule() {
    const strip = document.getElementById("schedule-strip");
    const detail = document.getElementById("schedule-detail");
    if (!strip || !detail) return;
    function show(event) {
      const chip = event.target && event.target.closest ? event.target.closest("li[data-detail]") : null;
      if (chip) detail.textContent = chip.getAttribute("data-detail");
    }
    function reset() {
      detail.textContent = detail.getAttribute("data-default") || "";
    }
    strip.addEventListener("mouseover", show);
    strip.addEventListener("focusin", show);
    strip.addEventListener("mouseleave", reset);
    strip.addEventListener("focusout", reset);
  }

  // E-5: focus management for the Classic layout. When a panel opens, focus moves to it (so a keyboard or
  // screen-reader user lands on what they asked for); when it closes, focus goes back to the button that
  // opened it. The Desktop layout (shared/pc-shell.js) already does this for its windows, so this stays off there.
  const PANEL_PAIRS = [
    ["howto-toggle-button", "howto-panel"],
    ["settings-toggle-button", "settings-panel"],
    ["info-page-toggle-button", "info-page-panel"],
    ["achievements-toggle-button", "achievements-panel"],
    ["past-runs-toggle-button", "past-runs-panel"],
    ["codex-toggle-button", "codex-panel"],
    ["stats-toggle-button", "stats-panel"],
    ["changelog-toggle-button", "changelog-panel"],
  ];

  function isDesktopLayout() {
    return window.NOYVJ_LAYOUT === "pc" || document.documentElement.getAttribute("data-layout") === "pc";
  }

  function watchPanelFocus() {
    if (isDesktopLayout()) return;
    PANEL_PAIRS.forEach(function (pair) {
      const toggle = document.getElementById(pair[0]);
      const panel = document.getElementById(pair[1]);
      if (!toggle || !panel) return;
      panel.setAttribute("tabindex", "-1");
      panel.setAttribute("role", "region");
      let wasHidden = panel.hidden;
      function label() {
        const text = (toggle.textContent || "").replace(/^[^A-Za-z0-9]+/, "").replace(/^(Hide|Review|Show)\s+/i, "").replace(/^[^A-Za-z0-9]+/, "").replace(/\s*\(\d[^)]*\)\s*$/, "").trim();
        panel.setAttribute("aria-label", text || pair[1]);
      }
      label();
      new MutationObserver(function () {
        const hiddenNow = panel.hidden;
        if (hiddenNow === wasHidden) return;
        wasHidden = hiddenNow;
        if (!hiddenNow) {
          label();
          panel.focus();
        } else {
          const active = document.activeElement;
          if (!active || active === document.body || panel.contains(active)) toggle.focus({ preventScroll: true });
        }
      }).observe(panel, { attributes: true, attributeFilter: ["hidden"] });
    });
  }

  // E-5: keyboard operation of the skill tree. Each skill is a labelled group; Up and Down (or Home and End)
  // move between the visible ones, Enter unlocks the focused skill if it can be bought, P pins or unpins it.
  // Every Unlock and Pin button is still a plain button reachable with Tab.
  function watchTree() {
    const tree = document.getElementById("skill-tree");
    if (!tree) return;
    Array.prototype.forEach.call(tree.querySelectorAll(".skill-row"), function (row) {
      const id = row.getAttribute("data-skill");
      row.setAttribute("tabindex", "-1");
      row.setAttribute("role", "group");
      row.setAttribute("aria-labelledby", "skill-" + id + "-status");
    });
    function visibleRows() {
      return Array.prototype.filter.call(tree.querySelectorAll(".skill-row"), function (row) { return !row.hidden; });
    }
    tree.addEventListener("keydown", function (event) {
      if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return;
      if (isTyping(event.target)) return;
      const row = event.target && event.target.closest ? event.target.closest(".skill-row") : null;
      if (!row) return;
      const rows = visibleRows();
      const at = rows.indexOf(row);
      let next = null;
      if (event.key === "ArrowDown") next = rows[Math.min(rows.length - 1, at + 1)];
      else if (event.key === "ArrowUp") next = rows[Math.max(0, at - 1)];
      else if (event.key === "Home") next = rows[0];
      else if (event.key === "End") next = rows[rows.length - 1];
      if (next) {
        event.preventDefault();
        next.focus();
        return;
      }
      if (event.target !== row) return; // Enter and P act only from the row itself, never on a button inside it
      const id = row.getAttribute("data-skill");
      if (event.key === "Enter") {
        event.preventDefault();
        const unlock = row.querySelector("[id$='-unlock-button']");
        if (unlock && !unlock.hidden && !unlock.disabled) unlock.click();
      } else if (event.key === "p" || event.key === "P") {
        event.preventDefault();
        const pin = row.querySelector("[id$='-pin-button']");
        if (pin && !pin.hidden) pin.click();
      }
    });
  }

  // E-2: the skill map's view. game.py builds the nodes once and updates them in place; this keeps the pan and
  // zoom on the canvas (a CSS transform), moves keyboard focus between nodes by where they are on the map and
  // keeps the focused node in view. Nothing here changes a game rule.
  function watchSkillMap() {
    const viewport = document.getElementById("skill-map-viewport");
    const canvas = document.getElementById("skill-map-canvas");
    if (!viewport || !canvas) return;
    const MIN = 0.4;
    const MAX = 2.5;
    const view = { x: 0, y: 0, k: 1 };
    let touched = false;

    function clamp(k) { return Math.min(MAX, Math.max(MIN, k)); }
    function apply() {
      canvas.style.transform = "translate(" + Math.round(view.x) + "px, " + Math.round(view.y) + "px) scale(" + view.k.toFixed(3) + ")";
      viewport.setAttribute("data-zoom", String(Math.round(view.k * 100)));
    }
    function keepInReach() {
      const vw = viewport.clientWidth;
      const vh = viewport.clientHeight;
      const w = canvas.offsetWidth * view.k;
      const h = canvas.offsetHeight * view.k;
      view.x = Math.min(vw - 60, Math.max(60 - w, view.x));
      view.y = Math.min(vh - 60, Math.max(60 - h, view.y));
    }
    function fit() {
      const vw = viewport.clientWidth;
      const vh = viewport.clientHeight;
      if (!vw || !vh || !canvas.offsetWidth) return;
      view.k = clamp(Math.min(1, (vw - 16) / canvas.offsetWidth, (vh - 16) / canvas.offsetHeight));
      view.x = (vw - canvas.offsetWidth * view.k) / 2;
      view.y = (vh - canvas.offsetHeight * view.k) / 2;
      apply();
    }
    function zoom(factor, px, py) {
      const next = clamp(view.k * factor);
      const ratio = next / view.k;
      if (px === undefined) { px = viewport.clientWidth / 2; py = viewport.clientHeight / 2; }
      view.x = px - (px - view.x) * ratio;
      view.y = py - (py - view.y) * ratio;
      view.k = next;
      touched = true;
      keepInReach();
      apply();
    }
    function pan(dx, dy) {
      view.x += dx;
      view.y += dy;
      touched = true;
      keepInReach();
      apply();
    }

    // Nodes that take part in keyboard movement: not hidden and not filtered out (the list hides those too).
    function nodes() {
      return Array.prototype.filter.call(canvas.querySelectorAll(".skill-map-node"), function (n) {
        return n.getAttribute("data-filtered") !== "true";
      });
    }
    function box(n) {
      return { x: parseFloat(n.style.left) || 0, y: parseFloat(n.style.top) || 0, w: n.offsetWidth, h: n.offsetHeight };
    }
    function ensureVisible(node) {
      const b = box(node);
      const m = 16;
      const left = view.x + b.x * view.k;
      const top = view.y + b.y * view.k;
      const right = left + b.w * view.k;
      const bottom = top + b.h * view.k;
      if (left < m) view.x += m - left;
      else if (right > viewport.clientWidth - m) view.x -= right - (viewport.clientWidth - m);
      if (top < m) view.y += m - top;
      else if (bottom > viewport.clientHeight - m) view.y -= bottom - (viewport.clientHeight - m);
      apply();
    }
    function nextNode(from, key) {
      const here = box(from);
      const dir = { ArrowRight: [1, 0], ArrowLeft: [-1, 0], ArrowDown: [0, 1], ArrowUp: [0, -1] }[key];
      let best = null;
      let bestScore = Infinity;
      nodes().forEach(function (n) {
        if (n === from) return;
        const b = box(n);
        const dx = (b.x + b.w / 2) - (here.x + here.w / 2);
        const dy = (b.y + b.h / 2) - (here.y + here.h / 2);
        const along = dx * dir[0] + dy * dir[1];
        if (along <= 0) return;
        const across = Math.abs(dx * dir[1]) + Math.abs(dy * dir[0]);
        const score = along + across * 2;
        if (score < bestScore) { bestScore = score; best = n; }
      });
      return best;
    }
    function focusNode(n) {
      if (!n) return;
      n.focus({ preventScroll: true });
      ensureVisible(n);
    }

    viewport.addEventListener("focusin", function (event) {
      const node = event.target && event.target.closest ? event.target.closest(".skill-map-node") : null;
      if (!node) return;
      viewport.setAttribute("data-current", node.getAttribute("data-skill"));
      Array.prototype.forEach.call(canvas.querySelectorAll(".skill-map-node"), function (n) {
        n.setAttribute("tabindex", n === node ? "0" : "-1");
      });
    });

    viewport.addEventListener("keydown", function (event) {
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      const node = event.target && event.target.closest ? event.target.closest(".skill-map-node") : null;
      const key = event.key;
      if (key === "Escape") {
        const clear = document.getElementById("skill-map-clear-button");
        if (clear && !clear.disabled) {
          event.preventDefault();
          event.stopPropagation(); // clear the selection first; a second Escape closes the window
          clear.click();
          const again = node && document.getElementById(node.id);
          if (again) again.focus({ preventScroll: true });
        }
        return;
      }
      if (key === "+" || key === "=") { event.preventDefault(); zoom(1.25); return; }
      if (key === "-" || key === "_") { event.preventDefault(); zoom(0.8); return; }
      if (key === "0") { event.preventDefault(); touched = false; fit(); return; }
      if (!/^Arrow(Up|Down|Left|Right)$/.test(key) && key !== "Home" && key !== "End") return;
      if (event.shiftKey && /^Arrow/.test(key)) {
        event.preventDefault();
        const step = 48;
        pan(key === "ArrowLeft" ? step : key === "ArrowRight" ? -step : 0, key === "ArrowUp" ? step : key === "ArrowDown" ? -step : 0);
        return;
      }
      const all = nodes();
      if (!all.length) return;
      event.preventDefault();
      if (key === "Home") { focusNode(all[0]); return; }
      if (key === "End") { focusNode(all[all.length - 1]); return; }
      if (!node) { focusNode(all[0]); return; }
      focusNode(nextNode(node, key));
    });

    // Mouse and touch: drag the background (or a node: a drag is not a click) to pan; Ctrl or Cmd with the wheel zooms.
    let drag = null;
    viewport.addEventListener("pointerdown", function (event) {
      if (event.button !== 0 && event.pointerType === "mouse") return;
      drag = { x: event.clientX, y: event.clientY, vx: view.x, vy: view.y, moved: false, id: event.pointerId };
    });
    viewport.addEventListener("pointermove", function (event) {
      if (!drag || event.pointerId !== drag.id) return;
      const dx = event.clientX - drag.x;
      const dy = event.clientY - drag.y;
      if (!drag.moved && Math.abs(dx) + Math.abs(dy) < 6) return;
      if (!drag.moved) {
        drag.moved = true;
        viewport.classList.add("skill-map-dragging");
        try { viewport.setPointerCapture(event.pointerId); } catch (e) { /* synthetic events have no active pointer */ }
      }
      view.x = drag.vx + dx;
      view.y = drag.vy + dy;
      touched = true;
      keepInReach();
      apply();
    });
    function endDrag(event) {
      if (!drag || event.pointerId !== drag.id) return;
      const moved = drag.moved;
      drag = null;
      viewport.classList.remove("skill-map-dragging");
      if (moved) {
        // The press that ended a drag must not also select the node under the pointer.
        const swallow = function (e) { e.stopPropagation(); e.preventDefault(); };
        viewport.addEventListener("click", swallow, { capture: true, once: true });
        window.setTimeout(function () { viewport.removeEventListener("click", swallow, true); }, 0);
      }
    }
    viewport.addEventListener("pointerup", endDrag);
    viewport.addEventListener("pointercancel", endDrag);
    viewport.addEventListener("wheel", function (event) {
      if (!event.ctrlKey && !event.metaKey) return;
      event.preventDefault();
      const rect = viewport.getBoundingClientRect();
      zoom(event.deltaY < 0 ? 1.15 : 1 / 1.15, event.clientX - rect.left, event.clientY - rect.top);
    }, { passive: false });

    [["skill-map-zoom-in", function () { zoom(1.25); }], ["skill-map-zoom-out", function () { zoom(0.8); }],
     ["skill-map-fit", function () { touched = false; fit(); }]].forEach(function (pair) {
      const button = document.getElementById(pair[0]);
      if (button) button.addEventListener("click", pair[1]);
    });

    // The map is hidden until its section or window opens, so fit it the first time it has a size, and
    // keep it reachable if the window is resized afterwards.
    if (window.ResizeObserver) {
      new ResizeObserver(function () {
        if (!viewport.clientWidth) return;
        if (!touched) fit();
        else { keepInReach(); apply(); }
      }).observe(viewport);
    }
    fit();
  }

  // E-30: the save badge says "Saved 12s ago"; game.py writes the moment of the last save into
  // data-saved-at, and this keeps the age fresh between renders (only while the state is "saved").
  function watchSaveHealth() {
    const badge = document.getElementById("save-health");
    const text = document.getElementById("save-health-text");
    if (!badge || !text) return;
    function age(seconds) {
      seconds = Math.max(0, Math.floor(seconds));
      if (seconds < 5) return "just now";
      if (seconds < 60) return seconds + "s ago";
      if (seconds < 3600) return Math.floor(seconds / 60) + " min ago";
      return Math.floor(seconds / 3600) + " h ago";
    }
    window.setInterval(function () {
      if (badge.getAttribute("data-state") !== "saved") return;
      const at = Number(badge.getAttribute("data-saved-at"));
      if (!at) return;
      text.textContent = "\u2713 Saved " + age((Date.now() - at) / 1000);
    }, 5000);
  }

  // E-31: hovering or focusing a node on the achievements tree reads its name and description in the
  // line under it; leaving restores the hint. Each node already carries its name as its aria-label and
  // title, so nothing depends on this script.
  function watchAchievementStrip() {
    const strip = document.getElementById("achievement-strip");
    const detail = document.getElementById("achievement-strip-detail");
    if (!strip || !detail) return;
    function show(event) {
      const node = event.target && event.target.closest ? event.target.closest("[data-detail]") : null;
      if (node) detail.textContent = node.getAttribute("data-detail");
    }
    function reset() {
      detail.textContent = detail.getAttribute("data-default") || "";
    }
    strip.addEventListener("mouseover", show);
    strip.addEventListener("focusin", show);
    strip.addEventListener("mouseleave", reset);
    strip.addEventListener("focusout", reset);
  }

  function start() {
    watchPopup();
    watchAchievementStrip();
    watchSchedule();
    watchPanelFocus();
    watchTree();
    watchSkillMap();
    watchSaveHealth();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
