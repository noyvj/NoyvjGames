/*
 * PC shell (Desktop boot), see planning/PC-VERSION-PLAN.md.
 *
 * Included only by a game's generated pc.html. It does not touch game logic:
 * it wraps the game's "open on demand" panels in windows, adds a backdrop and
 * Escape-to-close, and adds a few desktop controls to the toolbar. Every panel
 * keeps its own id and node, so game code keeps finding and toggling it.
 *
 * pc.html defines window.NOYVJ_PC_WINDOWS = [{panel, toggle, title}]: the panel
 * element id, the id of the button that opens/closes it (null = just hide it),
 * and the window title.
 */
(function () {
  "use strict";
  const specs = window.NOYVJ_PC_WINDOWS || [];
  const open = []; // frames, most recently opened last
  let backdrop = null;
  const lastOpener = new Map();

  function closeFrame(frame) {
    const spec = frame._spec, panel = frame._panel;
    if (panel.hidden) return;
    const toggle = spec.toggle && document.getElementById(spec.toggle);
    if (toggle) toggle.click(); else panel.hidden = true;
    if (!panel.hidden) panel.hidden = true; // a toggle that did not close it: force it
  }

  function sync(frame) {
    const shown = !frame._panel.hidden;
    frame.hidden = !shown;
    const at = open.indexOf(frame);
    if (shown && at === -1) {
      open.push(frame);
      lastOpener.set(frame, document.activeElement);
      const bar = frame.querySelector(".pc-window-close");
      if (bar) bar.focus({ preventScroll: true });
    } else if (!shown && at !== -1) {
      open.splice(at, 1);
      const back = lastOpener.get(frame);
      if (back && document.contains(back) && !back.hidden) back.focus({ preventScroll: true });
    }
    open.forEach((f, i) => { f.style.zIndex = String(900 + i); });
    backdrop.hidden = open.length === 0;
    if (open.length) backdrop.style.zIndex = String(899 + open.length - 1);
  }

  function wrap(spec) {
    const panel = document.getElementById(spec.panel);
    if (!panel) return;
    const frame = document.createElement("div");
    frame.className = "pc-window-frame";
    frame.setAttribute("role", "dialog");
    frame.setAttribute("aria-label", spec.title);
    frame.hidden = true;
    const bar = document.createElement("div");
    bar.className = "pc-window-bar";
    const title = document.createElement("h2");
    title.textContent = spec.title;
    const close = document.createElement("button");
    close.type = "button";
    close.className = "pc-window-close";
    close.textContent = "✕";
    close.setAttribute("aria-label", "Close " + spec.title);
    close.title = "Close (Esc)";
    bar.append(title, close);
    panel.parentNode.insertBefore(frame, panel);
    frame.append(bar, panel);
    frame._spec = spec;
    frame._panel = panel;
    close.addEventListener("click", () => closeFrame(frame));
    new MutationObserver(() => sync(frame)).observe(panel, { attributes: true, attributeFilter: ["hidden"] });
    sync(frame);
  }

  function addToolbarControls() {
    const toolbar = document.querySelector(".game-toolbar");
    if (!toolbar) return;
    const full = document.createElement("button");
    full.type = "button";
    full.className = "secondary pc-toolbar-button";
    full.id = "pc-fullscreen-button";
    full.textContent = "⛶ Fullscreen";
    full.title = "Toggle fullscreen (F11 also works)";
    full.addEventListener("click", () => {
      if (document.fullscreenElement) document.exitFullscreen();
      else if (document.documentElement.requestFullscreen) document.documentElement.requestFullscreen().catch(() => {});
    });
    toolbar.appendChild(full);
    if (window.NoyvjLayout) {
      const classic = document.createElement("button");
      classic.type = "button";
      classic.className = "secondary pc-toolbar-button";
      classic.id = "pc-classic-button";
      classic.textContent = "Classic layout";
      classic.title = "Switch to the Classic layout (your save carries over)";
      classic.addEventListener("click", () => window.NoyvjLayout.switchTo("classic"));
      toolbar.appendChild(classic);
    }
  }

  // Moves (never copies) existing elements into a frame: a top bar, then a body with a
  // stage (the thing you look at) and a side column. Ids and listeners survive, so game
  // code is unaffected. window.NOYVJ_PC_ZONES = {topbar, stagebar, stage, side}, each a list of selectors.
  function buildZones() {
    const zones = window.NOYVJ_PC_ZONES;
    const game = document.getElementById("game");
    if (!zones || !game) return;
    const mk = (id) => { const d = document.createElement("div"); d.id = id; return d; };
    const top = mk("pc-topbar"), body = mk("pc-body"), stage = mk("pc-stage"), side = mk("pc-side");
    const stagebar = mk("pc-stagebar");
    stagebar.setAttribute("role", "group");
    stagebar.setAttribute("aria-label", "Scene controls");
    side.setAttribute("role", "complementary");
    side.setAttribute("aria-label", "Readouts and log");
    stage.append(stagebar);
    body.append(stage, side);
    game.prepend(body);
    game.prepend(top);
    for (const [zone, el] of [["topbar", top], ["stagebar", stagebar], ["stage", stage], ["side", side]]) {
      for (const selector of zones[zone] || []) {
        const node = game.querySelector(selector);
        if (node) el.appendChild(node);
      }
    }
  }

  // A thin bar of the hotkeys that work in this game: window.NOYVJ_PC_HINTS = [["P", "Pause"], ...].
  function addHintBar() {
    const hints = window.NOYVJ_PC_HINTS;
    const stage = document.getElementById("pc-stage");
    if (!hints || !hints.length || !stage) return;
    const bar = document.createElement("div");
    bar.id = "pc-hintbar";
    bar.setAttribute("aria-label", "Keyboard shortcuts");
    hints.forEach(([key, label]) => {
      const item = document.createElement("span");
      const kbd = document.createElement("kbd");
      kbd.textContent = key;
      item.append(kbd, " " + label);
      bar.appendChild(item);
    });
    stage.appendChild(bar);
  }

  // The floating "Story: on/off" pill (shared/story-toggle.js) would sit on the scene; the
  // Desktop boot keeps it in the toolbar instead. It is created after load, so wait for it.
  function homeStoryToggle() {
    const toolbar = document.querySelector(".game-toolbar");
    if (!toolbar) return;
    const move = () => {
      const pill = document.getElementById("story-toggle");
      if (!pill) return false;
      pill.classList.add("secondary", "pc-toolbar-button");
      toolbar.appendChild(pill);
      return true;
    };
    if (move()) return;
    const observer = new MutationObserver(() => { if (move()) observer.disconnect(); });
    observer.observe(document.body, { childList: true });
    setTimeout(() => observer.disconnect(), 8000);
  }

  // New entries in a game's own log appear briefly as a small stack of notifications over the
  // scene, so you notice them without reading the side column. The log stays the history.
  // window.NOYVJ_PC_NOTIFY = { list: "#log-list" }. Entries present at load (a continued save) are
  // not announced: the stack stays quiet until the opening screen has been answered.
  function startNotifications() {
    const cfg = window.NOYVJ_PC_NOTIFY;
    const list = cfg && document.querySelector(cfg.list);
    const stage = document.getElementById("pc-stage");
    if (!list || !stage) return;
    const stack = document.createElement("div");
    stack.id = "pc-toasts";
    stack.setAttribute("role", "log");
    stack.setAttribute("aria-live", "polite");
    stage.appendChild(stack);
    const seen = new Set();
    let armed = false;
    const rows = () => [...list.children].map((row) => row.innerText.replace(/\s+/g, " ").trim()).filter(Boolean);
    const arm = () => setTimeout(() => { rows().forEach((t) => seen.add(t)); armed = true; }, 1500);
    const choice = window.NoyvjOpeningScreen && window.NoyvjOpeningScreen.choice;
    if (choice) choice.then(arm); else arm();
    function toast(text) {
      const item = document.createElement("div");
      item.className = "pc-toast";
      item.textContent = text;
      item.addEventListener("click", () => item.remove());
      stack.appendChild(item);
      while (stack.children.length > 3) stack.firstChild.remove();
      setTimeout(() => item.remove(), 8000);
    }
    new MutationObserver(() => {
      const now = rows();
      if (!armed) { now.forEach((t) => seen.add(t)); return; }
      now.filter((t) => !seen.has(t)).reverse().forEach((t) => { seen.add(t); toast(t); });
    }).observe(list, { childList: true, subtree: true, characterData: true });
  }

  function init() {
    document.documentElement.classList.add("pc-shell");
    buildZones();
    backdrop = document.createElement("div");
    backdrop.id = "pc-backdrop";
    backdrop.hidden = true;
    backdrop.addEventListener("click", () => { if (open.length) closeFrame(open[open.length - 1]); });
    document.body.appendChild(backdrop);
    specs.forEach(wrap);
    addToolbarControls();
    addHintBar();
    homeStoryToggle();
    startNotifications();
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape" || !open.length) return;
      const inner = document.getElementById("hamlet-town-panel");
      if (inner && !inner.hidden) return; // the game's own Esc handling comes first
      if (document.querySelector("#opening-screen, .confirm-dialog-overlay")) return;
      e.preventDefault();
      closeFrame(open[open.length - 1]);
    });
  }

  window.NoyvjPcShell = { closeTopWindow() { if (open.length) closeFrame(open[open.length - 1]); } };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
