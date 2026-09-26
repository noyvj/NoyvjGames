/*
 * Continuum -- U2: the optional Hamlet view (browser half).
 *
 * WHAT THIS FILE IS FOR. game.py (render_hamlet) builds the whole Hamlet
 * overlay as ordinary DOM: one real <button>-based "chip" per building in
 * #hamlet-chips, each wired to the very same handlers the Work / Build /
 * Research panels use. This file adds only the visual, pointer-side glue:
 *
 *   - Draws a low-poly building in the 3D scene for each chip (read from
 *     the chip's data-* attributes; nothing here knows the game's rules)
 *     and keeps each chip pinned over its building as the camera moves.
 *   - Lets a click on a 3D building press that building's main button, and
 *     highlights the building when its chip is hovered or focused (and the
 *     chip when the building is hovered), so mouse and keyboard agree.
 *   - When there is no 3D scene (no WebGL, Three.js missing, or the 2D view
 *     chosen) it puts the chips at their flat top-down positions instead, so
 *     the mode degrades to a plain map rather than disappearing.
 *   - Escape closes the Town Centre panel; crossing the desktop screen-size
 *     threshold re-runs game.py's render so the mode switches without a
 *     reload.
 *
 * TESTING REALITY, same standard as render3d.js: none of this is covered by
 * the pytest suite (no WebGL or real layout in the harness); it is verified
 * live in a browser. The Python half (hamlet.py, game.py's render_hamlet) is.
 */
(function () {
  "use strict";

  const RING_REACH = 5.0; // hamlet.RING_RADIUS + 1.4, keep in step with hamlet.flat_percent()
  const NOTE_FLAT = "The 3D view is off, so the buildings are shown on a flat map. Everything works the same.";

  let group = null;          // the hamlet's 3D buildings (a child of the scene)
  let meshKey = "";
  let hoverId = null;
  let wasOn = false;
  let wasIn3d = false;
  let framed = false;        // camera already set to the hamlet angle for this stay in the mode
  let scheduled = false;
  let registered = false;
  let downAt = null;

  function api() { return window.ContinuumScene; }
  function gameEl() { return document.getElementById("game"); }
  function hamletOn() { const g = gameEl(); return !!(g && g.classList.contains("hamlet-on")); }
  function in3d() { return hamletOn() && !!api() && api().is3dVisible(); }
  function chipEls() { return Array.prototype.slice.call(document.querySelectorAll("#hamlet-chips .hamlet-chip")); }

  // --- 3D buildings ---------------------------------------------------------

  function shapeFor(shape, H) {
    const g = new THREE.Group();
    const plot = H.cylinder(0.78, 0.84, 0.06, 0x5a5040, 18);
    g.add(plot);
    const at = function (mesh, x, y, z) { mesh.position.set(x, y, z); return mesh; };
    switch (shape) {
      case "town_centre": {
        const hall = at(H.box(1.15, 0.7, 0.8, 0xcdb890), 0, 0.41, 0);
        const roof = at(H.coneRoof(0.95, 0.55, 0xa9482f, 4), 0, 1.03, 0);
        roof.rotation.y = Math.PI / 4;
        const pole = H.cylinder(0.03, 0.03, 1.5, 0x6b4a2a, 5);
        pole.position.x = 0.55; pole.position.z = 0.3;
        const flag = at(H.box(0.32, 0.17, 0.03, 0xe0b374), 0.72, 1.32, 0.3);
        g.add(hall, roof, pole, flag);
        break;
      }
      case "shelter":
        g.add(at(H.buildHut(0xc9a066, 0x8a5a34), 0, 0.06, 0));
        break;
      case "granary":
        g.add(at(H.cylinder(0.32, 0.36, 0.7, 0xb08d57, 10), 0, 0.41, 0));
        g.add(at(H.coneRoof(0.42, 0.32, 0x7a5a34, 10), 0, 0.92, 0));
        break;
      case "hearth":
        g.add(at(H.buildCampfire(), 0, 0.06, 0));
        g.add(at(H.ring(0.36, 0.05, 0x8a8a8a), 0, 0.1, 0));
        break;
      case "toolworks":
        g.add(at(H.box(0.85, 0.3, 0.42, 0x8a6a44), -0.1, 0.21, 0));
        g.add(at(H.box(0.26, 0.16, 0.2, 0x777777), -0.1, 0.44, 0));
        g.add(at(H.buildMound(0x888888), 0.42, 0.06, 0.1));
        break;
      case "foragers":
        g.add(at(H.coneRoof(0.5, 0.75, 0x6f9c5a, 4), 0, 0.44, 0));
        g.add(at(H.cylinder(0.15, 0.12, 0.15, 0xc9a066, 8), 0.5, 0.06, 0.15));
        break;
      case "gatherers": {
        [[-0.16, 0.16], [0.16, 0.16], [0, 0.36]].forEach(function (p) {
          const log = H.cylinder(0.11, 0.11, 0.75, 0x8a5a34, 7);
          log.rotation.z = Math.PI / 2;
          log.position.set(0, p[1] + 0.06, p[0]);
          g.add(log);
        });
        break;
      }
      case "farm": {
        g.add(at(H.flatPlot(1.15, 0.8, 0xd4b95a, 0.08), 0, 0.08, 0.1));
        for (let i = 0; i < 3; i++) g.add(at(H.flatPlot(1.0, 0.07, 0xa88a2f, 0.11), 0, 0.11, -0.12 + i * 0.22));
        g.add(at(H.buildHouse(0xcdb27a, 0x8a5a34, 0.45, 0.4, 0.4), 0, 0.06, -0.55));
        break;
      }
      case "canal":
        g.add(at(H.flatPlot(1.3, 0.34, 0x3d7fae, 0.09), 0, 0.09, 0));
        g.add(at(H.cylinder(0.07, 0.07, 0.6, 0xe8ddb8, 8), -0.6, 0.36, -0.28));
        g.add(at(H.cylinder(0.07, 0.07, 0.6, 0xe8ddb8, 8), 0.6, 0.36, -0.28));
        break;
      case "public_works":
        g.add(at(H.cylinder(0.24, 0.28, 0.72, 0x8a8272, 8), 0, 0.42, 0));
        g.add(at(H.coneRoof(0.3, 0.32, 0x5a4a3a, 8), 0, 1.0, 0));
        break;
      case "guildhall":
        g.add(at(H.buildHouse(0xd8c39a, 0x5a3d24, 0.95, 0.6, 0.7), 0, 0.06, 0));
        g.add(at(H.box(0.3, 0.2, 0.04, 0xe0b374), 0, 0.5, 0.4));
        break;
      case "factory": {
        const built = H.buildChimneyFactory(0x5a5248);
        built.group.position.y = 0.06;
        g.add(built.group);
        break;
      }
      case "sanitation":
        g.add(at(H.buildSanitationWorks(), 0, 0.06, 0));
        break;
      case "planners":
        g.add(at(H.buildGlassTower(0x5f7f9f, 1.0), 0, 0.06, 0));
        break;
      case "transit":
        g.add(at(H.flatPlot(1.3, 0.3, 0xe0c23c, 0.09), 0, 0.09, 0.2));
        g.add(at(H.box(0.5, 0.36, 0.34, 0x5f7f9f), 0.3, 0.24, -0.15));
        break;
      case "rings":
        g.add(at(H.ring(0.58, 0.07, 0x6fd7d0), 0, 0.8, 0));
        g.add(at(H.cylinder(0.07, 0.07, 0.6, 0x8890c8, 6), 0, 0.36, 0));
        break;
      default:
        g.add(at(H.box(0.6, 0.5, 0.6, 0x999999), 0, 0.31, 0));
    }
    return g;
  }

  function rebuildBuildings(chips) {
    const scene = api().scene();
    const H = api().helpers;
    if (group) scene.remove(group);
    group = new THREE.Group();
    // Rim of earth beyond the era's own ground disc, so the outer ring of
    // buildings never floats over empty sky in an era whose ground is small.
    const rim = new THREE.Mesh(new THREE.CircleGeometry(5.0, 32), H.toonMaterial(0x40392c));
    rim.rotation.x = -Math.PI / 2;
    rim.position.y = -0.03;
    group.add(rim);
    chips.forEach(function (chip) {
      const id = chip.getAttribute("data-station");
      const count = parseInt(chip.getAttribute("data-count") || "0", 10) || 0;
      const building = shapeFor(chip.getAttribute("data-shape"), H);
      building.position.set(parseFloat(chip.getAttribute("data-hx")) || 0, 0, parseFloat(chip.getAttribute("data-hz")) || 0);
      building.scale.setScalar(1 + Math.min(count, 8) * 0.04);
      building.traverse(function (o) { o.userData.stationId = id; });
      group.add(building);
    });
    scene.add(group);
    applyHighlight();
  }

  function applyHighlight() {
    if (!group) return;
    group.traverse(function (o) {
      if (o.isMesh && o.material && o.material.emissive) {
        o.material.emissive.setHex(o.userData.stationId && o.userData.stationId === hoverId ? 0x5a4520 : 0x000000);
      }
    });
  }

  function setHover(id) {
    if (id === hoverId) return;
    hoverId = id;
    chipEls().forEach(function (chip) {
      chip.classList.toggle("hamlet-chip--hover", chip.getAttribute("data-station") === id);
    });
    if (in3d() && group) { applyHighlight(); api().redraw(); }
  }

  // --- placing the chips ----------------------------------------------------

  function placeFlat(chip) {
    const x = parseFloat(chip.getAttribute("data-hx")) || 0;
    const z = parseFloat(chip.getAttribute("data-hz")) || 0;
    chip.style.left = (50 + (x / RING_REACH) * 42).toFixed(2) + "%";
    chip.style.top = (54 + (z / RING_REACH) * 34).toFixed(2) + "%";
    chip.style.zIndex = String(Math.round(50 + z * 10));
  }

  function placeProjected(chip) {
    const x = parseFloat(chip.getAttribute("data-hx")) || 0;
    const z = parseFloat(chip.getAttribute("data-hz")) || 0;
    const p = api().project(x, 0.95, z);
    if (!p) { placeFlat(chip); return; }
    chip.style.left = p.left.toFixed(2) + "%";
    chip.style.top = p.top.toFixed(2) + "%";
    // Nearer buildings (smaller depth value) sit in front.
    chip.style.zIndex = String(Math.round(200 - p.depth * 100));
  }

  // --- the one sync pass ------------------------------------------------------

  function sync() {
    scheduled = false;
    const game = gameEl();
    if (!game) return;
    const on = hamletOn();
    const is3d = in3d();
    game.classList.toggle("hamlet-3d", is3d);
    const note = document.getElementById("hamlet-note");
    if (note) {
      note.hidden = !(on && !is3d);
      note.textContent = on && !is3d ? NOTE_FLAT : "";
    }

    if (!on) framed = false;
    if (on && is3d && !framed && window.ContinuumCamera) { framed = true; window.ContinuumCamera.preset("hamlet"); }
    if ((on !== wasOn || is3d !== wasIn3d) && api() && api().ready()) {
      wasOn = on; wasIn3d = is3d;
      api().resize(); // the container changes height with the mode; re-enters sync once, harmlessly
    }
    wasOn = on; wasIn3d = is3d;

    const chips = chipEls();
    if (!on) {
      if (group) group.visible = false;
      return;
    }
    if (is3d) {
      const key = chips.map(function (c) { return c.getAttribute("data-station") + ":" + c.getAttribute("data-count"); }).join("|");
      if (key !== meshKey || !group || !group.parent) {
        meshKey = key;
        rebuildBuildings(chips);
        api().redraw(); // re-enters sync via the change listener; key now matches
        return;
      }
      group.visible = true;
      chips.forEach(placeProjected);
    } else {
      if (group) group.visible = false;
      chips.forEach(placeFlat);
    }
  }

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    // setTimeout, not requestAnimationFrame: rAF is paused in a background tab, which would leave the chips unplaced.
    window.setTimeout(sync, 16);
  }

  // --- pointer picking on the 3D buildings -------------------------------------

  function pickedStation(event) {
    if (!in3d() || !group) return null;
    const hit = api().pick(event.clientX, event.clientY, group.children);
    return hit && hit.userData ? hit.userData.stationId || null : null;
  }

  function setupPointer() {
    const container = document.getElementById("visual3d-container");
    if (!container) return;
    container.addEventListener("pointerdown", function (event) {
      downAt = { x: event.clientX, y: event.clientY };
    });
    container.addEventListener("click", function (event) {
      const start = downAt;
      downAt = null;
      if (start && Math.hypot(event.clientX - start.x, event.clientY - start.y) > 5) return; // a drag, not a click
      const id = pickedStation(event);
      if (!id) return;
      const button = document.getElementById("hamlet-" + id + "-main");
      if (button) { button.click(); button.focus(); }
    });
    container.addEventListener("pointermove", function (event) {
      if (event.buttons) return;
      const id = pickedStation(event);
      container.style.cursor = id ? "pointer" : "";
      setHover(id);
    });
    container.addEventListener("pointerleave", function () { setHover(null); });
  }

  function setupChipHover() {
    const stage = document.getElementById("hamlet-stage");
    if (!stage) return;
    const enter = function (event) {
      const chip = event.target && event.target.closest ? event.target.closest(".hamlet-chip") : null;
      if (chip) setHover(chip.getAttribute("data-station"));
    };
    const leave = function (event) {
      const chip = event.target && event.target.closest ? event.target.closest(".hamlet-chip") : null;
      if (chip) setHover(null);
    };
    stage.addEventListener("mouseover", enter);
    stage.addEventListener("focusin", enter);
    stage.addEventListener("mouseout", leave);
    stage.addEventListener("focusout", leave);
  }

  // --- wiring ------------------------------------------------------------------

  function setupObservers() {
    if (!window.MutationObserver) return;
    const observer = new MutationObserver(schedule);
    const game = gameEl();
    const chips = document.getElementById("hamlet-chips");
    if (game) observer.observe(game, { attributes: true, attributeFilter: ["class"] });
    if (chips) observer.observe(chips, { childList: true, subtree: true, attributes: true, attributeFilter: ["data-count"] });
  }

  function setupMedia() {
    if (!window.matchMedia) return;
    let mq;
    try {
      mq = window.matchMedia("(min-width: 960px) and (hover: hover) and (pointer: fine)");
    } catch (e) { return; }
    const onChange = function () {
      const p = window.pyodide;
      const fn = p && p.globals && p.globals.get("on_hamlet_capability_change");
      if (fn) { try { fn(); } finally { if (fn.destroy) fn.destroy(); } }
    };
    if (mq.addEventListener) mq.addEventListener("change", onChange);
    else if (mq.addListener) mq.addListener(onChange);
    // Belt and braces: some embedded/emulated viewports resize without ever
    // firing the media-query change event, so also compare on window resize.
    let last = mq.matches;
    window.addEventListener("resize", function () {
      if (mq.matches !== last) { last = mq.matches; onChange(); }
    });
  }

  function setupKeys() {
    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape") return;
      const main = document.getElementById("hamlet-town_centre-main");
      if (main && main.getAttribute("aria-expanded") === "true") { main.click(); main.focus(); }
    });
  }

  window.ContinuumHamlet = {
    // Called by render3d.js once a real WebGL scene exists.
    sceneReady: function () {
      if (registered || !api()) return;
      registered = true;
      api().onChange(schedule);
      schedule();
    },
  };

  setupObservers();
  setupPointer();
  setupChipHover();
  setupMedia();
  setupKeys();
  schedule();
})();
