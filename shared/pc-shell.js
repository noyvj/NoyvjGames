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
