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

  // The toolbar of a dozen text buttons is condensed into a few icon buttons for what is used
  // during play, plus one Menu window (also opened with Escape when nothing else is open) that
  // holds the rest. Every original button keeps its node and handlers: the icons forward clicks
  // to them, and the menu holds the real buttons, so labels like "Hide Achievements" stay live.
  // window.NOYVJ_PC_TOOLBAR = { icons: [[buttonId, emoji], ...],
  //                             menu: [{ heading, ids: [buttonId, ...] }, ...] }
  const stripIcon = (text) => text.replace(/^[^\p{L}\p{N}]+/u, "").trim();

  function menuGroup(heading) {
    const group = document.createElement("div");
    group.className = "pc-menu-group";
    const h = document.createElement("h3");
    h.textContent = heading;
    group.appendChild(h);
    return group;
  }

  function buildToolbar() {
    const cfg = window.NOYVJ_PC_TOOLBAR;
    const toolbar = document.querySelector(".game-toolbar");
    const game = document.getElementById("game");
    if (!cfg || !toolbar || !game) return;

    // Icon buttons: proxies that keep the original (hidden) button as the source of truth.
    const source = document.createElement("div");
    source.id = "pc-toolbar-source";
    source.hidden = true;
    game.appendChild(source);
    for (const [id, emoji] of cfg.icons || []) {
      const original = document.getElementById(id);
      if (!original) continue;
      source.appendChild(original);
      const proxy = document.createElement("button");
      proxy.type = "button";
      proxy.className = "secondary pc-icon-button";
      proxy.textContent = emoji;
      const sync = () => {
        const name = stripIcon(original.textContent);
        proxy.title = name;
        proxy.setAttribute("aria-label", name);
      };
      sync();
      new MutationObserver(sync).observe(original, { childList: true, characterData: true, subtree: true });
      proxy.addEventListener("click", () => original.click());
      toolbar.appendChild(proxy);
    }

    // The menu window: grouped real buttons, plus the shell's own Display controls.
    const panel = document.createElement("div");
    panel.id = "pc-menu-panel";
    panel.className = "section";
    panel.hidden = true;
    const groups = new Map();
    for (const spec of cfg.menu || []) {
      const group = menuGroup(spec.heading);
      for (const id of spec.ids) {
        const node = document.getElementById(id);
        if (node) group.appendChild(node);
      }
      groups.set(spec.heading, group);
      panel.appendChild(group);
    }
    // Each composite window gets an opener button in the group it names.
    for (const spec of window.NOYVJ_PC_COMPOSITES || []) {
      if (!document.getElementById(spec.id)) continue;
      let group = groups.get(spec.group);
      if (!group) { group = menuGroup(spec.group); groups.set(spec.group, group); panel.appendChild(group); }
      const opener = document.createElement("button");
      opener.type = "button";
      opener.className = "secondary";
      opener.id = "pc-open-" + spec.id;
      opener.textContent = spec.label;
      opener.addEventListener("click", () => { document.getElementById(spec.id).hidden = false; });
      group.appendChild(opener);
    }
    const display = menuGroup("Display");
    display.id = "pc-menu-display";
    const full = document.createElement("button");
    full.type = "button";
    full.className = "secondary";
    full.id = "pc-fullscreen-button";
    full.textContent = "\u26F6 Fullscreen";
    full.title = "Toggle fullscreen (F11 also works)";
    full.addEventListener("click", () => {
      if (document.fullscreenElement) document.exitFullscreen();
      else if (document.documentElement.requestFullscreen) document.documentElement.requestFullscreen().catch(() => {});
    });
    display.appendChild(full);
    if (window.NoyvjLayout) {
      const classic = document.createElement("button");
      classic.type = "button";
      classic.className = "secondary";
      classic.id = "pc-classic-button";
      classic.textContent = "Classic layout";
      classic.title = "Switch to the Classic layout (your save carries over)";
      classic.addEventListener("click", () => window.NoyvjLayout.switchTo("classic"));
      display.appendChild(classic);
    }
    panel.appendChild(display);
    // Choosing anything in the menu closes it (after that button's own handler has run).
    panel.addEventListener("click", (e) => {
      if (e.target.closest("button")) setTimeout(() => { panel.hidden = true; }, 0);
    });
    game.appendChild(panel);
    wrap({ panel: "pc-menu-panel", toggle: null, title: "Menu" });
    panel.parentNode.classList.add("pc-menu-frame");

    const menuButton = document.createElement("button");
    menuButton.type = "button";
    menuButton.id = "pc-menu-button";
    menuButton.className = "secondary pc-icon-button";
    menuButton.textContent = "\u2630";
    menuButton.title = "Menu (Esc)";
    menuButton.setAttribute("aria-label", "Menu");
    menuButton.addEventListener("click", () => { panel.hidden = !panel.hidden; });
    toolbar.appendChild(menuButton);
  }

  // Moves (never copies) existing elements into a frame: a top bar, then a body with a stage
  // (the thing you look at) and, optionally, a side column. Ids and listeners survive, so game
  // code is unaffected. window.NOYVJ_PC_ZONES = {topbar, stagebar, stage, side, hidden}, each a
  // list of selectors.
  function buildZones() {
    const zones = window.NOYVJ_PC_ZONES;
    const game = document.getElementById("game");
    if (!zones || !game) return;
    const mk = (id) => { const d = document.createElement("div"); d.id = id; return d; };
    const top = mk("pc-topbar"), body = mk("pc-body"), stage = mk("pc-stage");
    const stagebar = mk("pc-stagebar");
    stagebar.setAttribute("role", "group");
    stagebar.setAttribute("aria-label", "Scene controls");
    stage.append(stagebar);
    body.append(stage);
    const targets = [["topbar", top], ["stagebar", stagebar], ["stage", stage]];
    // An optional side column. Games that fold everything into the scene leave it out.
    if ((zones.side || []).length) {
      const side = mk("pc-side");
      side.setAttribute("role", "complementary");
      side.setAttribute("aria-label", "Readouts and log");
      body.append(side);
      body.classList.add("pc-has-side");
      targets.push(["side", side]);
    }
    // Elements the game still updates by id but that the Desktop layout shows another way
    // (here: a HUD built from the same numbers). They stay in the page, just out of the layout.
    const hidden = mk("pc-hidden-readouts");
    hidden.hidden = true;
    targets.push(["hidden", hidden]);
    game.prepend(body);
    game.prepend(top);
    game.appendChild(hidden);
    for (const [zone, el] of targets) {
      for (const selector of zones[zone] || []) {
        const node = game.querySelector(selector);
        if (node) el.appendChild(node);
      }
    }
    // [node selector, destination selector]: the node is moved to the start of the destination.
    for (const [from, into] of window.NOYVJ_PC_ADOPT || []) {
      const node = game.querySelector(from), dest = game.querySelector(into);
      if (node && dest) dest.prepend(node);
    }
  }

  // Composite windows: several existing sections shown together in one window that the Menu
  // opens (their own hidden/visible logic keeps working inside it, because the nodes are
  // moved, not copied or re-created). window.NOYVJ_PC_COMPOSITES =
  // [{id, title, members: [selectors], group: "menu heading", label}].
  function buildComposites() {
    const game = document.getElementById("game");
    for (const spec of window.NOYVJ_PC_COMPOSITES || []) {
      const panel = document.createElement("div");
      panel.id = spec.id;
      panel.className = "section pc-composite";
      panel.hidden = true;
      for (const selector of spec.members) {
        const node = game.querySelector(selector);
        if (node) panel.appendChild(node);
      }
      game.appendChild(panel);
      wrap({ panel: spec.id, toggle: null, title: spec.title });
    }
  }

  // Dropdowns (a HUD chip that opens a small panel of detail). Markup is built by the game:
  //   <div class="pc-dropdown-wrap"><button data-pc-dropdown aria-expanded="false">..</button>
  //   <div class="pc-dropdown" hidden>..</div></div>
  // One open at a time; a click anywhere else, or Escape, closes it. Delegated, so a game can
  // rebuild or update its chips freely.
  function startDropdowns() {
    const closeAll = (except) => {
      document.querySelectorAll(".pc-dropdown:not([hidden])").forEach((d) => {
        if (d === except) return;
        d.hidden = true;
        const toggle = d.parentNode.querySelector("[data-pc-dropdown]");
        if (toggle) toggle.setAttribute("aria-expanded", "false");
      });
    };
    document.addEventListener("click", (e) => {
      const toggle = e.target.closest && e.target.closest("[data-pc-dropdown]");
      if (!toggle) { if (!(e.target.closest && e.target.closest(".pc-dropdown"))) closeAll(null); return; }
      const dropdown = toggle.parentNode.querySelector(".pc-dropdown");
      if (!dropdown) return;
      closeAll(dropdown);
      dropdown.hidden = !dropdown.hidden;
      toggle.setAttribute("aria-expanded", String(!dropdown.hidden));
    });
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape" || !document.querySelector(".pc-dropdown:not([hidden])")) return;
      closeAll(null);
      e.__pcMenuOpened = true; // consumed: do not also open the Menu
      e.stopPropagation();
    }, true);
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
  // Desktop boot keeps it in the menu's Display group instead. It is created after load.
  function homeStoryToggle() {
    const group = document.getElementById("pc-menu-display");
    if (!group) return;
    const move = () => {
      const pill = document.getElementById("story-toggle");
      if (!pill) return false;
      pill.classList.add("secondary", "pc-menu-story");
      group.appendChild(pill);
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
    buildComposites();
    buildToolbar();
    startDropdowns();
    addHintBar();
    homeStoryToggle();
    startNotifications();
    // Escape with nothing else open opens the menu, as in a PC game. Decided in the capture phase
    // so the game's own Escape handling (closing the Town panel or shortcuts) is not mistaken for
    // "nothing was open".
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape" || open.length || e.__pcMenuOpened) return;
      const blockers = "#opening-screen, .confirm-dialog-overlay, #tutorial-card, #hamlet-town-panel:not([hidden])";
      const shown = [...document.querySelectorAll(blockers)].some((n) => n.getBoundingClientRect().width > 0);
      const typing = /^(INPUT|TEXTAREA|SELECT)$/.test((e.target && e.target.tagName) || "");
      if (shown || typing) return;
      const menu = document.getElementById("pc-menu-panel");
      if (menu) { e.preventDefault(); e.__pcMenuOpened = true; menu.hidden = false; }
    }, true);
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape" || !open.length || e.__pcMenuOpened) return;
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
