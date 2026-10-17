/*
 * Continuum — Phase 5 Three.js low-poly rendering layer.
 *
 * ARCHITECTURE (see CLAUDE.md's "Core system 7" and Phase 5 build notes
 * for the full reasoning): Pyodide can't render 3D on its own, so this is
 * a hybrid setup. All game state and logic stay in Python, fully tested
 * by the pytest suite (sim.py / sustainability.py / visual.py); this file
 * is the ONE thing on the JS side that knows Three.js exists, and it only
 * ever READS a plain JSON snapshot — it never calls back into Python to
 * change anything. The seam is exactly two functions:
 *
 *   Python: game.py's get_visual_state() -> visual.py's visual_state()
 *   JS:     ContinuumVisual.init(pyodide) reads it after every render()
 *
 * game.py's render() calls a small JS hook, window.continuumOnRender(),
 * after it finishes its own 2D DOM update (see game.py's
 * _notify_visual_layer()). That hook is only ever installed by this file,
 * and only once a real WebGL renderer exists — so the Python side never
 * has to know or care whether the 3D layer is present.
 *
 * GRACEFUL DEGRADATION (CLAUDE.md Phase 5 scope note #3): the whole point
 * of this file's structure is that every failure mode — the CDN script
 * tag failing to load, `THREE` being undefined, WebGL context creation
 * throwing, or a per-scene build throwing — is caught here and result in
 * ContinuumVisual.init() simply returning `false` having touched nothing.
 * index.html's pre-existing `.settlement-visual` CSS diorama (the Phase 1
 * space-theme stopgap) is never hidden unless a real WebGL scene is ready
 * to replace it, so the 2D game is ALWAYS fully playable regardless of
 * what happens in this file.
 *
 * TESTING REALITY (per CLAUDE.md's own honesty standard): nothing in this
 * file is covered by the pytest suite — it cannot be, the same way no
 * prior milestone has unit-tested actual pixels. This is verified live,
 * under a real browser with Pyodide and WebGL both running — see
 * CLAUDE.md's Phase 5 build notes for exactly what was checked and how.
 */

(function () {
  "use strict";

  // Defined by render3d-scenes.js, which index.html loads just before this file.
  const {
    toonMaterial,
    box,
    coneRoof,
    cylinder,
    ring,
    flatPlot,
    buildHut,
    buildHouse,
    buildCampfire,
    buildMound,
    buildChimneyFactory,
    buildSanitationWorks,
    buildGlassTower,
    buildSpire,
    buildRelayPylon,
    isLightTheme,
    addTerrain,
    addHeritage,
    ERA_BUILDERS,
    lerpColor,
    initToonGradientMap,
    setTimeOfDay,
  } = window.ContinuumScenes;

  const CONTAINER_ID = "visual3d-container";
  const TOGGLE_BUTTON_ID = "visual-mode-toggle-button";
  const CAMERA_PRESET_ROW_ID = "camera-preset-buttons";
  const SNAPSHOT_BUTTON_ID = "visual-snapshot-button"; // K13
  const SCREENSAVER_BUTTON_ID = "screensaver-button"; // K-21
  const SETTLEMENT_2D_SELECTOR = ".settlement-visual";
  const VIEW_MODE_STORAGE_KEY = "continuum-visual-mode"; // "3d" | "2d"

  let renderer = null;
  let scene = null;
  let camera = null;
  let pyodideRef = null;
  let sceneGroup = null; // everything era-specific; replaced wholesale on era change
  let builtEra = null;
  let ready = false;
  // K13 — the most recent visual_state() snapshot, kept purely so the
  // snapshot-export filename can name the era/season it was taken in;
  // never read for anything that affects rendering itself.
  let lastVisualState = null;

  // Orbit state for the built-in drag-to-look control (no OrbitControls
  // import needed — this hub's whole convention is no build step and no
  // dependency beyond what a single pinned <script> tag brings in, and a
  // few lines of pointer-event math is much less risk than a second
  // Three.js module).
  let yaw = 0.7;
  let pitch = 0.55;
  const MIN_PITCH = 0.15;
  const MAX_PITCH = 1.3;
  let dragging = false;
  let lastPointer = null;
  let cameraDistance = 9.5;

  // K6 (planning/TODO.md): named camera presets, so a player who has never
  // touched the drag-to-look control still has a reliable way to see the
  // settlement from a useful angle, rather than orbit being the only route
  // to any view but the default one. Each preset is just a fixed
  // yaw/pitch/distance triple -- reusing the exact same
  // updateCameraPosition() math the drag control already drives, so a
  // preset and a manual drag are indistinguishable to the camera itself.
  const CAMERA_PRESETS = {
    overview: { yaw: 0.7, pitch: 0.55, distance: 9.5 },
    closeup: { yaw: 0.7, pitch: 0.4, distance: 5.5 },
    aerial: { yaw: 0.7, pitch: 1.2, distance: 9.5 },
    // K4: the classic isometric city-builder angle (45 degrees around,
    // about 35 degrees down), pulled back a little so the whole map fits.
    isometric: { yaw: 0.785, pitch: 0.615, distance: 11.5 },
    // U2: the Hamlet view's default angle -- a little higher and further
    // back so the whole ring of buildings sits inside the taller stage.
    hamlet: { yaw: 0.785, pitch: 0.98, distance: 12.5 },
  };


  // --- feature detection ---------------------------------------------

  function threeAvailable() {
    return typeof window.THREE !== "undefined";
  }

  function webglAvailable() {
    try {
      const canvas = document.createElement("canvas");
      return !!(
        window.WebGLRenderingContext &&
        (canvas.getContext("webgl") || canvas.getContext("experimental-webgl"))
      );
    } catch (e) {
      return false;
    }
  }

  // --- renderer / camera setup ------------------------------------------

  function updateCameraPosition() {
    const clampedPitch = Math.max(MIN_PITCH, Math.min(MAX_PITCH, pitch));
    camera.position.set(
      cameraDistance * Math.cos(clampedPitch) * Math.sin(yaw),
      cameraDistance * Math.sin(clampedPitch),
      cameraDistance * Math.cos(clampedPitch) * Math.cos(yaw)
    );
    camera.lookAt(0, 0.4, 0);
  }

  function applyCameraPreset(name) {
    const preset = CAMERA_PRESETS[name];
    if (!preset || !camera) return;
    yaw = preset.yaw;
    pitch = preset.pitch;
    cameraDistance = preset.distance;
    updateCameraPosition();
    if (renderer && scene) renderer.render(scene, camera);
    notifyChange();
  }

  // U2 (the Hamlet view): a small, read-mostly surface for hamlet.js so the
  // overlay can sit on the same scene without this file knowing it exists.
  // notifyChange() fires after anything that moves the picture (a redraw,
  // the camera, a resize, the 2D/3D toggle); hamlet.js re-projects its
  // buttons then. Nothing here is ever called unless hamlet.js registered.
  const changeListeners = [];
  function notifyChange() {
    changeListeners.forEach(function (fn) {
      try { fn(); } catch (err) { console.warn("Continuum 3D: change listener failed.", err); }
    });
  }

  function viewHeight() {
    const container = document.getElementById(CONTAINER_ID);
    return (container && container.clientHeight) || 220;
  }

  function resizeToContainer() {
    const container = document.getElementById(CONTAINER_ID);
    if (!renderer || !container) return;
    const w = container.clientWidth || 320;
    const h = viewHeight();
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    if (scene) renderer.render(scene, camera);
    notifyChange();
  }

  // A ground-plane/world point -> percentages of the canvas box (or null if
  // it is behind the camera). Only valid after a render (three updates the
  // camera's inverse matrix during renderer.render).
  function projectPoint(x, y, z) {
    if (!renderer || !camera) return null;
    const v = new THREE.Vector3(x, y, z).project(camera);
    if (v.z > 1) return null;
    return { left: (v.x * 0.5 + 0.5) * 100, top: (-v.y * 0.5 + 0.5) * 100, depth: v.z };
  }

  // First object hit under a client-space pointer, among `objects` (and
  // their descendants), or null.
  function pickAt(clientX, clientY, objects) {
    if (!renderer || !camera || !objects || !objects.length) return null;
    const rect = renderer.domElement.getBoundingClientRect();
    if (!rect.width || !rect.height) return null;
    const ndc = new THREE.Vector2(
      ((clientX - rect.left) / rect.width) * 2 - 1,
      -((clientY - rect.top) / rect.height) * 2 + 1
    );
    const caster = new THREE.Raycaster();
    caster.setFromCamera(ndc, camera);
    const hits = caster.intersectObjects(objects, true);
    return hits.length ? hits[0].object : null;
  }

  // K27: keyboard access to the presets (see the shortcuts panel).
  window.ContinuumCamera = {
    preset: applyCameraPreset,
    // K-21: the screensaver, for the keyboard shortcut (index.html).
    screensaver: function () {
      if (screensaverOn) exitScreensaver(); else enterScreensaver();
    },
  };

  function setupCameraPresetButtons() {
    const row = document.getElementById(CAMERA_PRESET_ROW_ID);
    if (!row) return;
    const timeSelect = document.getElementById("time-of-day-select");
    if (timeSelect) {
      timeSelect.addEventListener("change", function () {
        setTimeOfDay(timeSelect.value);
        pullStateAndRender();
      });
    }
    Object.keys(CAMERA_PRESETS).forEach(function (name) {
      const button = document.getElementById("camera-preset-" + name + "-button");
      if (!button) return;
      button.addEventListener("click", function () {
        applyCameraPreset(name);
      });
    });
  }

  // K13 (planning/TODO.md): a shareable "my settlement" snapshot, exported
  // straight off the live WebGL canvas. `renderer.domElement` IS the
  // canvas Three.js draws into, so `toDataURL()` on it captures exactly
  // what the player is looking at -- no second offscreen render, no
  // server round-trip, nothing beyond what the browser already gives a
  // <canvas> for free.
  function downloadSnapshot() {
    if (!renderer || !scene || !camera) return;
    try {
      // Render one more frame immediately before capturing. The renderer
      // was constructed with `preserveDrawingBuffer: true` specifically so
      // this isn't strictly required for correctness, but forcing a fresh
      // render right before the read guarantees the captured pixels match
      // the camera's current position even if a drag or preset just
      // moved it on this exact tick, rather than depending on whichever
      // frame the browser happened to have buffered last.
      renderer.render(scene, camera);
      const dataUrl = renderer.domElement.toDataURL("image/png");
      const link = document.createElement("a");
      const era = (lastVisualState && lastVisualState.era) || "settlement";
      const season = lastVisualState && lastVisualState.season;
      link.download = "continuum-" + era + (season ? "-season-" + season : "") + ".png";
      link.href = dataUrl;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      // Same "never let the render layer break the game" posture as
      // pullStateAndRender()'s own try/catch -- a failed export (a
      // tainted-canvas security error, an unsupported browser) should
      // never surface as a broken game, just a snapshot that silently
      // didn't download.
      console.warn("Continuum 3D: snapshot export failed.", err);
    }
  }

  // K18/K20: a downscaled JPEG data URL of the current 3D view, used for the
  // settlement archive thumbnail and the shareable card. Returns "" when no
  // scene exists or the capture fails. The scene has a transparent
  // background, so it is composited on a dark backdrop before encoding.
  function capture(width, quality) {
    if (!renderer || !scene || !camera) return "";
    try {
      const w = Math.min(Math.max(Math.floor(Number(width)) || 240, 64), 1200);
      const q = Math.min(Math.max(Number(quality) || 0.7, 0.3), 0.95);
      renderer.render(scene, camera);
      const src = renderer.domElement;
      if (!src.width || !src.height) return "";
      const out = document.createElement("canvas");
      out.width = w;
      out.height = Math.max(1, Math.round((w * src.height) / src.width));
      const ctx = out.getContext("2d");
      ctx.fillStyle = "#1a1410";
      ctx.fillRect(0, 0, out.width, out.height);
      ctx.drawImage(src, 0, 0, out.width, out.height);
      return out.toDataURL("image/jpeg", q);
    } catch (err) {
      console.warn("Continuum 3D: capture failed.", err);
      return "";
    }
  }

  function setupSnapshotButton() {
    const button = document.getElementById(SNAPSHOT_BUTTON_ID);
    if (!button) return;
    button.addEventListener("click", downloadSnapshot);
  }

  // --- K-21: screensaver mode ---------------------------------------------
  // The 3D city on its own: all other UI hidden, a slow orbit, for a second
  // monitor. It asks the browser to make the scene stage fullscreen (Escape
  // leaves natively); where that is refused or unsupported it falls back to a
  // fixed full-window stage that a click or Escape leaves. Visual only: it
  // changes no game state and does not touch the season clock (P still
  // pauses). The orbit is the one place this file runs an animation loop, and
  // only while the screensaver is on; with reduce motion on (the Settings
  // toggle or the OS preference) the camera holds still instead.
  const SCREENSAVER_SPEED = 0.07; // radians per second: one turn in about 90 seconds
  const SCREENSAVER_FRAME_MS = 33; // about 30 frames per second
  const SCREENSAVER_GRACE_MS = 500; // ignore the click that started it
  let screensaverOn = false;
  let screensaverFallback = false;
  let screensaverRaf = 0;
  let screensaverLast = 0;
  let screensaverStarted = 0;
  let screensaverSaved = null;
  let screensaverHintTimer = 0;
  let screensaverWired = false;

  // Z-31: lite mode (shared/lite-mode.js, the hub-wide "slow computer" switch) lowers this
  // scene's costs: no antialiasing and a device pixel ratio of 1 for the canvas, and a still
  // screensaver camera (reduced motion) instead of an animated orbit.
  function liteMode() {
    return !!(window.NoyvjLite && typeof window.NoyvjLite.on === "function" && window.NoyvjLite.on());
  }

  function canvasPixelRatio() {
    return liteMode() ? 1 : Math.min(window.devicePixelRatio || 1, 2);
  }

  function reducedMotion() {
    if (liteMode()) return true;
    if (document.documentElement.classList.contains("reduce-motion")) return true;
    try {
      return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    } catch (err) {
      return false;
    }
  }

  function screensaverHint(text) {
    const stage = document.getElementById("visual-stage");
    if (!stage) return;
    let hint = document.getElementById("screensaver-hint");
    if (!hint) {
      hint = document.createElement("p");
      hint.id = "screensaver-hint";
      hint.className = "screensaver-hint";
      hint.setAttribute("role", "status");
      stage.appendChild(hint);
    }
    hint.textContent = text;
    hint.classList.add("visible");
    window.clearTimeout(screensaverHintTimer);
    screensaverHintTimer = window.setTimeout(function () { hint.classList.remove("visible"); }, 6000);
  }

  function screensaverFrame(now) {
    if (!screensaverOn) return;
    screensaverRaf = window.requestAnimationFrame(screensaverFrame);
    if (document.visibilityState !== "visible") { screensaverLast = now; return; }
    if (now - screensaverLast < SCREENSAVER_FRAME_MS) return;
    const dt = Math.min((now - screensaverLast) / 1000, 0.25);
    screensaverLast = now;
    if (reducedMotion() || !renderer || !scene) return;
    yaw += SCREENSAVER_SPEED * dt;
    updateCameraPosition();
    renderer.render(scene, camera);
  }

  function useScreensaverFallback() {
    const stage = document.getElementById("visual-stage");
    if (!stage || !screensaverOn) return;
    screensaverFallback = true;
    stage.classList.add("screensaver-fallback");
    resizeToContainer();
  }

  function enterScreensaver() {
    const container = document.getElementById(CONTAINER_ID);
    const stage = document.getElementById("visual-stage");
    if (!ready || screensaverOn || !container || container.hidden || !stage) return false;
    screensaverOn = true;
    screensaverFallback = false;
    screensaverStarted = Date.now();
    screensaverSaved = { yaw: yaw, pitch: pitch, distance: cameraDistance };
    pitch = 0.5;
    cameraDistance = 11;
    document.body.classList.add("screensaver-on");
    stage.classList.add("screensaver-stage");
    updateCameraPosition();
    const request = stage.requestFullscreen || stage.webkitRequestFullscreen;
    if (request) {
      try {
        const result = request.call(stage);
        if (result && typeof result.catch === "function") result.catch(useScreensaverFallback);
      } catch (err) {
        useScreensaverFallback();
      }
    } else {
      useScreensaverFallback();
    }
    // Some embedded browsers neither grant nor refuse: do not wait forever.
    window.setTimeout(function () {
      if (screensaverOn && !screensaverFallback && !(document.fullscreenElement || document.webkitFullscreenElement)) {
        useScreensaverFallback();
      }
    }, 700);
    window.setTimeout(resizeToContainer, 60);
    screensaverLast = performance.now();
    screensaverRaf = window.requestAnimationFrame(screensaverFrame);
    screensaverHint(
      reducedMotion()
        ? "Screensaver. The camera holds still because reduce motion is on. Click or press Esc to leave."
        : "Screensaver. Click or press Esc to leave. P pauses time."
    );
    return true;
  }

  function exitScreensaver() {
    if (!screensaverOn) return;
    screensaverOn = false;
    window.cancelAnimationFrame(screensaverRaf);
    window.clearTimeout(screensaverHintTimer);
    const stage = document.getElementById("visual-stage");
    document.body.classList.remove("screensaver-on");
    if (stage) stage.classList.remove("screensaver-stage", "screensaver-fallback");
    const hint = document.getElementById("screensaver-hint");
    if (hint) hint.classList.remove("visible");
    const fsElement = document.fullscreenElement || document.webkitFullscreenElement;
    if (fsElement) {
      try { (document.exitFullscreen || document.webkitExitFullscreen).call(document); } catch (err) { /* already out */ }
    }
    if (screensaverSaved) {
      yaw = screensaverSaved.yaw;
      pitch = screensaverSaved.pitch;
      cameraDistance = screensaverSaved.distance;
      screensaverSaved = null;
    }
    updateCameraPosition();
    window.setTimeout(resizeToContainer, 60);
  }

  function setupScreensaver() {
    const button = document.getElementById(SCREENSAVER_BUTTON_ID);
    if (!button || screensaverWired) return;
    screensaverWired = true;
    button.addEventListener("click", function () {
      if (screensaverOn) exitScreensaver(); else enterScreensaver();
    });
    // Escape leaves the in-window fallback. Captured first and stopped so the
    // Desktop layout's own Escape (open the Menu) does not also fire.
    window.addEventListener("keydown", function (event) {
      if (!screensaverOn || event.key !== "Escape") return;
      event.preventDefault();
      event.stopImmediatePropagation();
      exitScreensaver();
    }, true);
    // A click or tap on the scene leaves it, after a short grace period.
    document.addEventListener("pointerdown", function (event) {
      if (!screensaverOn || Date.now() - screensaverStarted < SCREENSAVER_GRACE_MS) return;
      const stage = document.getElementById("visual-stage");
      if (stage && stage.contains(event.target)) exitScreensaver();
    }, true);
    // The browser's own fullscreen exit (Escape, or the user's gesture).
    function onFullscreenChange() {
      const inFullscreen = !!(document.fullscreenElement || document.webkitFullscreenElement);
      if (screensaverOn && !screensaverFallback && !inFullscreen && Date.now() - screensaverStarted > 200) {
        exitScreensaver();
      }
    }
    document.addEventListener("fullscreenchange", onFullscreenChange);
    document.addEventListener("webkitfullscreenchange", onFullscreenChange);
  }

  function attachDragControls(container) {
    container.style.touchAction = "none";
    container.addEventListener("pointerdown", function (event) {
      dragging = true;
      lastPointer = { x: event.clientX, y: event.clientY };
    });
    window.addEventListener("pointerup", function () {
      dragging = false;
      lastPointer = null;
    });
    window.addEventListener("pointermove", function (event) {
      if (!dragging || !lastPointer) return;
      const dx = event.clientX - lastPointer.x;
      const dy = event.clientY - lastPointer.y;
      lastPointer = { x: event.clientX, y: event.clientY };
      yaw -= dx * 0.008;
      pitch += dy * 0.006;
      updateCameraPosition();
      renderer.render(scene, camera);
      notifyChange();
    });
  }

  function renderScene(vs) {
    const builder = ERA_BUILDERS[vs.era];
    if (!builder) return; // an era this build's JS layer doesn't know yet — degrade quietly

    if (vs.era !== builtEra || sceneGroup === null) {
      if (sceneGroup) {
        scene.remove(sceneGroup);
      }
      sceneGroup = builder(vs);
      addTerrain(sceneGroup, vs.terrain);
      addHeritage(sceneGroup, vs.heritage);
      scene.add(sceneGroup);
      builtEra = vs.era;
    } else {
      // Same era, state moved (population grew, a building went up, a
      // season advanced) — cheapest correct option is rebuilding the
      // group each time rather than diffing individual meshes; scenes are
      // small (well under 100 meshes even at the largest settlement caps
      // above), so this stays comfortably fast.
      scene.remove(sceneGroup);
      sceneGroup = builder(vs);
      addTerrain(sceneGroup, vs.terrain);
      addHeritage(sceneGroup, vs.heritage);
      scene.add(sceneGroup);
    }
    renderer.render(scene, camera);
    notifyChange();
  }

  function pullStateAndRender() {
    if (!ready || !pyodideRef) return;
    // Same try/finally-destroy idiom shared/save-widget.js's own
    // readGameState() uses for the equivalent get_state() call — a PyProxy
    // returned across the Python/JS boundary has to be destroyed
    // explicitly or it leaks, the same real-not-hypothetical class of bug
    // CLAUDE.md's Milestone 4 audit already found and fixed for
    // create_proxy()-wrapped click handlers.
    const getVisualState = pyodideRef.globals.get("get_visual_state");
    if (!getVisualState) return; // game.py hasn't finished booting yet
    let raw;
    try {
      raw = getVisualState();
      const vs = raw && raw.toJs ? raw.toJs({ dict_converter: Object.fromEntries }) : raw;
      lastVisualState = vs;
      renderScene(vs);
    } catch (err) {
      // A render-layer failure must never surface as a broken game — log
      // for diagnosis and leave the last good frame on screen.
      console.warn("Continuum 3D: render failed, leaving last frame.", err);
    } finally {
      if (raw && typeof raw.destroy === "function") raw.destroy();
    }
  }

  // --- view-mode toggle (3D <-> 2D) ---------------------------------------

  function applyViewMode(mode) {
    const container = document.getElementById(CONTAINER_ID);
    const fallback = document.querySelector(SETTLEMENT_2D_SELECTOR);
    const button = document.getElementById(TOGGLE_BUTTON_ID);
    const presetRow = document.getElementById(CAMERA_PRESET_ROW_ID);
    const snapshotButton = document.getElementById(SNAPSHOT_BUTTON_ID);
    const screensaverButton = document.getElementById(SCREENSAVER_BUTTON_ID);
    if (!container || !fallback) return;
    if (mode === "3d") {
      container.hidden = false;
      fallback.hidden = true;
      if (button) button.innerText = "🖼 2D view";
      if (presetRow) presetRow.hidden = false;
      // K13 — a snapshot of the 2D CSS diorama isn't this feature's point,
      // so the button only ever shows alongside a live 3D scene, the same
      // gating the camera-preset row above already uses.
      if (snapshotButton) snapshotButton.hidden = false;
      if (screensaverButton) screensaverButton.hidden = false;
    } else {
      container.hidden = true;
      fallback.hidden = false;
      if (button) button.innerText = "🧊 3D view";
      // Camera presets only mean anything with a live 3D scene on screen.
      if (presetRow) presetRow.hidden = true;
      if (snapshotButton) snapshotButton.hidden = true;
      if (screensaverButton) screensaverButton.hidden = true;
      if (screensaverOn) exitScreensaver();
    }
    try {
      window.localStorage.setItem(VIEW_MODE_STORAGE_KEY, mode);
    } catch (e) {
      // Storage can throw in a locked-down/private-browsing context —
      // the toggle still works for this page load, it just won't be
      // remembered next time. Not worth failing the toggle over.
    }
    notifyChange();
  }

  function currentViewMode() {
    try {
      const stored = window.localStorage.getItem(VIEW_MODE_STORAGE_KEY);
      if (stored === "2d" || stored === "3d") return stored;
    } catch (e) {
      // ignore — default below
    }
    return "3d";
  }

  function setupToggleButton() {
    const button = document.getElementById(TOGGLE_BUTTON_ID);
    if (!button) return;
    button.hidden = false;
    button.addEventListener("click", function () {
      const container = document.getElementById(CONTAINER_ID);
      const showing3d = container && !container.hidden;
      applyViewMode(showing3d ? "2d" : "3d");
    });
    applyViewMode(currentViewMode());
  }

  // --- public entry point -------------------------------------------------

  function init(pyodide) {
    if (!threeAvailable()) {
      console.warn("Continuum 3D: THREE failed to load (CDN unreachable/blocked) — staying on the 2D view.");
      return false;
    }
    if (!webglAvailable()) {
      console.warn("Continuum 3D: WebGL is not available in this browser — staying on the 2D view.");
      return false;
    }

    const container = document.getElementById(CONTAINER_ID);
    if (!container) return false;

    try {
      const width = container.clientWidth || 320;
      const height = viewHeight();

      // K13 — preserveDrawingBuffer keeps the drawing buffer intact after
      // a render instead of letting the browser clear/swap it away before
      // the next paint, which is what makes toDataURL() a reliable
      // capture of the last-rendered frame across browsers rather than
      // occasionally returning a blank PNG.
      renderer = new THREE.WebGLRenderer({ antialias: !liteMode(), alpha: true, preserveDrawingBuffer: true });
      renderer.setSize(width, height);
      renderer.setPixelRatio(canvasPixelRatio());
      // Antialiasing is fixed when the renderer is made (it applies from the next load), but the
      // pixel ratio follows the lite-mode switch live.
      document.addEventListener("noyvj-lite-change", function () {
        if (!renderer) return;
        renderer.setPixelRatio(canvasPixelRatio());
        const el = document.getElementById(CONTAINER_ID);
        renderer.setSize((el && el.clientWidth) || width, viewHeight());
        if (scene && camera) renderer.render(scene, camera);
      });
      container.innerHTML = "";
      container.appendChild(renderer.domElement);

      scene = new THREE.Scene();
      camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 100);
      updateCameraPosition();

      initToonGradientMap();

      attachDragControls(container);
      window.addEventListener("resize", function () {
        const w = container.clientWidth || width;
        const h = viewHeight();
        renderer.setSize(w, h);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        if (scene) renderer.render(scene, camera);
        notifyChange();
      });

      pyodideRef = pyodide;
      ready = true;

      // Y11b: re-light the scene when the player flips the theme in
      // Settings (shared/theme.js fires this event). The sky itself is a CSS
      // background, so only the lights need rebuilding.
      document.addEventListener("noyvj-theme-change", function () {
        if (ready && lastVisualState) {
          try { renderScene(lastVisualState); } catch (err) { console.warn("Continuum 3D: theme re-light failed.", err); }
        }
      });

      // First paint, then wire the hook game.py calls after every render().
      pullStateAndRender();
      window.continuumOnRender = pullStateAndRender;

      setupToggleButton();
      setupCameraPresetButtons();
      setupSnapshotButton();
      setupScreensaver();
      if (window.ContinuumHamlet && window.ContinuumHamlet.sceneReady) {
        window.ContinuumHamlet.sceneReady();
      }
      return true;
    } catch (err) {
      console.warn("Continuum 3D: failed to initialise, staying on the 2D view.", err);
      ready = false;
      return false;
    }
  }

  window.ContinuumVisual = { init: init, capture: capture };

  // U2: what hamlet.js may use. The building blocks are the same low-poly
  // helpers every era scene above is made of, so hamlet buildings match.
  window.ContinuumScene = {
    ready: function () { return ready; },
    isLight: isLightTheme,
    is3dVisible: function () {
      const container = document.getElementById(CONTAINER_ID);
      return !!(ready && container && !container.hidden);
    },
    scene: function () { return scene; },
    project: projectPoint,
    pick: pickAt,
    redraw: function () { if (renderer && scene) { renderer.render(scene, camera); notifyChange(); } },
    resize: resizeToContainer,
    onChange: function (fn) { changeListeners.push(fn); },
    helpers: {
      box: box, cylinder: cylinder, coneRoof: coneRoof, ring: ring, flatPlot: flatPlot,
      buildHut: buildHut, buildHouse: buildHouse, buildCampfire: buildCampfire,
      buildMound: buildMound, buildChimneyFactory: buildChimneyFactory,
      buildSanitationWorks: buildSanitationWorks, buildGlassTower: buildGlassTower,
      buildSpire: buildSpire, buildRelayPylon: buildRelayPylon, toonMaterial: toonMaterial, lerpColor: lerpColor,
    },
  };
})();
