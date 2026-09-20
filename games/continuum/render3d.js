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

  const CONTAINER_ID = "visual3d-container";
  const TOGGLE_BUTTON_ID = "visual-mode-toggle-button";
  const CAMERA_PRESET_ROW_ID = "camera-preset-buttons";
  const SNAPSHOT_BUTTON_ID = "visual-snapshot-button"; // K13
  const SETTLEMENT_2D_SELECTOR = ".settlement-visual";
  const VIEW_MODE_STORAGE_KEY = "continuum-visual-mode"; // "3d" | "2d"

  let renderer = null;
  let scene = null;
  let camera = null;
  let pyodideRef = null;
  let toonGradientMap = null;
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
  };

  // K14: an optional time-of-day override for screenshots. "auto" keeps the
  // seasonal cycle below; the others pin the light to a fixed look until
  // changed again (session-only, not saved). Still no animation loop.
  const TIME_OF_DAY = {
    dawn: { wave: 0.6, brightness: 0.95 },
    noon: { wave: 1.0, brightness: 1.08 },
    dusk: { wave: 0.3, brightness: 0.85 },
    night: { wave: 0.0, brightness: 0.62 },
  };
  let timeOfDay = "auto";

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

  // --- shared low-poly building blocks ---------------------------------
  // Every shape below is a small, flat-shaded/toon-shaded primitive group.
  // Per CLAUDE.md's Core system 7 brief ("flat-shaded geometry, simple
  // toon-style shading, and simplified geometric forms... without needing
  // realistic textures or complex asset pipelines"), MeshToonMaterial with
  // a tiny programmatically-generated gradient map gives real cel/toon
  // shading with zero external texture assets.

  function makeToonGradientMap() {
    const canvas = document.createElement("canvas");
    canvas.width = 4;
    canvas.height = 1;
    const ctx = canvas.getContext("2d");
    const shades = [70, 140, 200, 255];
    for (let i = 0; i < shades.length; i++) {
      ctx.fillStyle = "rgb(" + shades[i] + "," + shades[i] + "," + shades[i] + ")";
      ctx.fillRect(i, 0, 1, 1);
    }
    const texture = new THREE.CanvasTexture(canvas);
    texture.magFilter = THREE.NearestFilter;
    texture.minFilter = THREE.NearestFilter;
    return texture;
  }

  function toonMaterial(hex) {
    return new THREE.MeshToonMaterial({ color: hex, gradientMap: toonGradientMap });
  }

  function box(width, height, depth, hex) {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(width, height, depth), toonMaterial(hex));
    mesh.position.y = height / 2;
    return mesh;
  }

  function coneRoof(radius, height, hex, sides) {
    const mesh = new THREE.Mesh(
      new THREE.ConeGeometry(radius, height, sides || 6),
      toonMaterial(hex)
    );
    return mesh;
  }

  function cylinder(radiusTop, radiusBottom, height, hex, sides) {
    const mesh = new THREE.Mesh(
      new THREE.CylinderGeometry(radiusTop, radiusBottom, height, sides || 8),
      toonMaterial(hex)
    );
    mesh.position.y = height / 2;
    return mesh;
  }

  function ring(radius, tube, hex) {
    const mesh = new THREE.Mesh(new THREE.TorusGeometry(radius, tube, 8, 16), toonMaterial(hex));
    mesh.rotation.x = Math.PI / 2;
    return mesh;
  }

  function flatPlot(width, depth, hex, y) {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(width, 0.05, depth), toonMaterial(hex));
    mesh.position.y = y || 0.03;
    return mesh;
  }

  /** A round hut: cylinder base + cone roof — Tribal's own flagship shape,
   * and reused (recoloured) as the generic "housing cluster" shape a
   * scene falls back to when it has nothing more specific to show. */
  function buildHut(wallHex, roofHex) {
    const group = new THREE.Group();
    const base = cylinder(0.5, 0.56, 0.55, wallHex, 8);
    const roof = coneRoof(0.62, 0.55, roofHex, 8);
    roof.position.y = 0.85;
    group.add(base, roof);
    return group;
  }

  /** A boxy house with a pitched (prism) roof — used from Agrarian on,
   * where "settlement" starts meaning built structures, not round huts. */
  function buildHouse(wallHex, roofHex, w, h, d) {
    const group = new THREE.Group();
    const wallW = w || 0.7;
    const wallH = h || 0.6;
    const wallD = d || 0.6;
    const walls = box(wallW, wallH, wallD, wallHex);
    // A roof built from a single flattened box, rotated 45 degrees, reads
    // as a simple pitched roof without needing a bespoke prism geometry —
    // in keeping with "simplified geometric forms", not a literal asset.
    const roof = new THREE.Mesh(
      new THREE.BoxGeometry(wallW * 0.95, wallH * 0.5, wallD * 1.05),
      toonMaterial(roofHex)
    );
    roof.rotation.z = Math.PI / 4;
    roof.position.y = wallH + wallH * 0.2;
    group.add(walls, roof);
    return group;
  }

  function buildCampfire() {
    const group = new THREE.Group();
    const logHex = 0x5a3d24;
    for (let i = 0; i < 4; i++) {
      const log = cylinder(0.045, 0.045, 0.5, logHex, 5);
      log.rotation.z = Math.PI / 2;
      log.rotation.y = (Math.PI / 4) * i;
      log.position.y = 0.08;
      group.add(log);
    }
    const flame = coneRoof(0.13, 0.32, 0xff8a3d, 5);
    flame.position.y = 0.32;
    group.add(flame);
    return group;
  }

  function buildMound(hex) {
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(0.32, 8, 6), toonMaterial(hex));
    mesh.scale.y = 0.55;
    mesh.position.y = 0.16;
    return mesh;
  }

  function buildChimneyFactory(wallHex) {
    const group = new THREE.Group();
    const body = box(0.9, 0.55, 0.7, wallHex);
    const chimney = cylinder(0.09, 0.11, 0.75, 0x4a4a4a, 8);
    chimney.position.set(0.28, 0.55, 0);
    group.add(body, chimney);
    return { group, smokeOrigin: new THREE.Vector3(0.28, 1.0, 0) };
  }

  // K19 (planning/TODO.md): Sanitation Works (Industrial) previously had NO
  // mesh of its own -- worksCount only ever fed the smoke-puff-reduction
  // math in buildIndustrialScene(), so a settlement could build several and
  // see nothing distinct for it in the scene at all, unlike every other
  // building in the game. A squat teal treatment tank (clearly distinct
  // from the grey chimney factory it sits beside) closes that gap.
  function buildSanitationWorks() {
    const group = new THREE.Group();
    const tank = cylinder(0.32, 0.36, 0.5, 0x3a8a82, 10);
    const cap = cylinder(0.2, 0.2, 0.12, 0x2a6a64, 10);
    cap.position.y = 0.31;
    group.add(tank, cap);
    return group;
  }

  function buildSmokePuff(hex, scale) {
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(0.14, 6, 5), toonMaterial(hex));
    mesh.scale.setScalar(scale);
    return mesh;
  }

  function buildGlassTower(hex, height) {
    const group = new THREE.Group();
    const body = box(0.55, height, 0.55, hex);
    const cap = box(0.6, 0.06, 0.6, 0x2a3a4a);
    cap.position.y = height + 0.03;
    group.add(body, cap);
    return group;
  }

  function buildSpire(hex, height) {
    const group = new THREE.Group();
    const body = cylinder(0.18, 0.3, height, hex, 6);
    const tip = coneRoof(0.18, 0.4, 0xd8e4ff, 6);
    tip.position.y = height + 0.2;
    group.add(body, tip);
    return group;
  }

  // --- ground plane, sky/lighting -------------------------------------

  function buildGround(hex, radius) {
    const mesh = new THREE.Mesh(new THREE.CircleGeometry(radius || 4.4, 28), toonMaterial(hex));
    mesh.rotation.x = -Math.PI / 2;
    return mesh;
  }

  // K17 (planning/TODO.md): a subtle seasonal lighting cycle, tied to
  // `visual_state().season` -- the same field the 2D UI's own "Season N"
  // line already reads, so this needs no new state and no new save field.
  // Deliberately NOT a real-time day/night loop: this hub's Phase 5 build
  // notes are explicit that "no continuous requestAnimationFrame loop
  // runs" is a deliberate posture (battery/performance cost for a scene
  // that isn't otherwise changing), and the scene already only redraws
  // when continuumOnRender() fires -- i.e. on a real state change. A
  // four-step cycle mapped onto the season counter steps forward exactly
  // once per season advance, the same cadence every other scene detail
  // (building counts, pollution tint) already updates on.
  const SEASONAL_CYCLE_LENGTH = 4; // spring/summer/autumn/winter, loosely
  const SEASONAL_BRIGHTNESS_RANGE = 0.08; // +/-8% -- ambience, not a new mechanic
  const SEASONAL_TINT_PULL = 0.12; // how far skyHex is nudged toward the seasonal tint
  const SEASONAL_COOL_TINT = 0xaebbe0; // winter/dusk
  const SEASONAL_WARM_TINT = 0xffdca8; // summer/noon

  function seasonalPhase(season) {
    const step = ((Math.round(season || 1) - 1) % SEASONAL_CYCLE_LENGTH + SEASONAL_CYCLE_LENGTH) % SEASONAL_CYCLE_LENGTH;
    return step / SEASONAL_CYCLE_LENGTH; // 0..1
  }

  function setupLighting(target, skyHex, groundHex, season) {
    const phase = seasonalPhase(season);
    // A single sine wave drives both the warm/cool tint pull and the
    // brightness nudge together, so "brighter" and "warmer" move in
    // lockstep (a summery peak, a dim, cool trough) instead of two
    // independent, potentially-clashing cycles.
    let wave = Math.sin(phase * Math.PI * 2) * 0.5 + 0.5; // 0..1
    let brightnessFactor = 1.0 + (wave - 0.5) * 2 * SEASONAL_BRIGHTNESS_RANGE;
    if (TIME_OF_DAY[timeOfDay]) {
      wave = TIME_OF_DAY[timeOfDay].wave;
      brightnessFactor = TIME_OF_DAY[timeOfDay].brightness;
    }
    const seasonalTint = lerpColor(SEASONAL_COOL_TINT, SEASONAL_WARM_TINT, wave);
    const tintedSky = lerpColor(skyHex, seasonalTint, SEASONAL_TINT_PULL);

    const hemi = new THREE.HemisphereLight(tintedSky, groundHex, 0.9 * brightnessFactor);
    const sun = new THREE.DirectionalLight(0xffffff, 0.75 * brightnessFactor);
    sun.position.set(4, 6, 3);
    target.add(hemi, sun);
  }

  // --- era scene recipes -------------------------------------------------
  // One builder per era. Every builder reads ONLY the plain visual_state()
  // dict (never a live Python object) and returns a THREE.Group. Deriving
  // prop counts from population/buildings is deliberately simple and
  // capped (never more than a handful of extra props per state field) —
  // per CLAUDE.md's own scope-reality-check instruction not to over-build
  // any single era's art at the expense of the others.

  function settlementScale(vs, minCount, populationDivisor, maxCount) {
    const byBuildings = (vs.buildings && vs.buildings.shelter) || 0;
    const byPopulation = Math.ceil(vs.population / populationDivisor);
    return Math.max(minCount, Math.min(maxCount, Math.max(byBuildings, byPopulation)));
  }

  function ringLayout(count, radiusBase, radiusStep) {
    const positions = [];
    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2;
      const radius = radiusBase + (i % 3) * radiusStep;
      positions.push([Math.cos(angle) * radius, Math.sin(angle) * radius]);
    }
    return positions;
  }

  function buildTribalScene(vs) {
    const group = new THREE.Group();
    group.add(buildGround(0x5c8a3e));

    const hutCount = settlementScale(vs, 2, 4, 10);
    ringLayout(hutCount, 1.5, 0.5).forEach(function (pos) {
      const hut = buildHut(0xc9a066, 0x8a5a34);
      hut.position.set(pos[0], 0, pos[1]);
      group.add(hut);
    });

    if ((vs.buildings.hearth || 0) > 0) {
      group.add(buildCampfire());
    }
    const granaryCount = Math.min(4, vs.buildings.granary || 0);
    for (let i = 0; i < granaryCount; i++) {
      const mound = buildMound(0x8a6d3b);
      mound.position.set(0.6 + i * 0.4, 0, -1.2);
      group.add(mound);
    }
    if ((vs.buildings.toolworks || 0) > 0) {
      const bench = box(0.5, 0.22, 0.3, 0x777777);
      bench.position.set(-0.9, 0, -1.1);
      group.add(bench);
    }
    setupLighting(group, 0xfff2d0, 0x3a2c1a, vs.season);
    return group;
  }

  function buildAgrarianScene(vs) {
    const group = new THREE.Group();
    group.add(buildGround(0x8a7a3e));

    const houseCount = settlementScale(vs, 2, 5, 10);
    ringLayout(houseCount, 1.4, 0.45).forEach(function (pos) {
      const house = buildHouse(0xcdb27a, 0x8a5a34);
      house.position.set(pos[0], 0, pos[1]);
      group.add(house);
    });

    const fieldCount = Math.min(6, vs.buildings.farmland || 0);
    for (let i = 0; i < fieldCount; i++) {
      const plot = flatPlot(0.8, 0.55, i % 2 === 0 ? 0xd4b95a : 0xb89a3f);
      plot.position.set(-2.6 + (i % 3) * 0.95, 0, 2.4 + Math.floor(i / 3) * 0.7);
      group.add(plot);
    }
    setupLighting(group, 0xfff2d0, 0x4a3a1a, vs.season);
    return group;
  }

  function buildClassicalScene(vs) {
    const group = new THREE.Group();
    group.add(buildGround(0xc2b280));

    const houseCount = settlementScale(vs, 2, 6, 9);
    ringLayout(houseCount, 1.6, 0.4).forEach(function (pos) {
      const house = buildHouse(0xe4d9b8, 0xb08850, 0.6, 0.5, 0.6);
      house.position.set(pos[0], 0, pos[1]);
      group.add(house);
    });

    // A small civic marker (columns) always present once Classical is
    // reached — Administrators produce no resource of their own (see
    // sim.py), so there is no per-administrator prop to scale; the
    // building it stands for (Canals) is drawn as a flat blue channel
    // instead, scaled by the real canal count.
    for (let i = 0; i < 4; i++) {
      const column = cylinder(0.07, 0.07, 0.7, 0xe8ddb8, 8);
      column.position.set(-1.0 + i * 0.35, 0, -2.0);
      group.add(column);
    }
    const canalCount = Math.min(4, vs.buildings.canals || 0);
    for (let i = 0; i < canalCount; i++) {
      const canal = flatPlot(1.6, 0.22, 0x3d7fae, 0.03);
      canal.position.set(0, 0, 1.4 + i * 0.35);
      group.add(canal);
    }
    setupLighting(group, 0xfff6e0, 0x5a4a2a, vs.season);
    return group;
  }

  function buildMedievalScene(vs) {
    const group = new THREE.Group();
    group.add(buildGround(0x6f8a52));

    const houseCount = settlementScale(vs, 3, 6, 10);
    ringLayout(houseCount, 1.6, 0.4).forEach(function (pos) {
      const house = buildHouse(0xd8c39a, 0x5a3d24, 0.55, 0.55, 0.55);
      house.position.set(pos[0], 0, pos[1]);
      group.add(house);
    });

    const worksCount = Math.min(4, vs.buildings.public_works || 0);
    for (let i = 0; i < worksCount; i++) {
      const tower = cylinder(0.22, 0.26, 0.9, 0x8a8272, 8);
      const roof = coneRoof(0.28, 0.3, 0x5a4a3a, 8);
      roof.position.y = 1.05;
      const well = new THREE.Group();
      well.add(tower, roof);
      well.position.set(-1.6 + i * 0.9, 0, -1.8);
      group.add(well);
    }
    setupLighting(group, 0xf0ead0, 0x3a4a2a, vs.season);
    return group;
  }

  function buildIndustrialScene(vs) {
    const group = new THREE.Group();
    const pollution = vs.pollution || 0.0;
    // Pollution tints the ground and sky rather than only the smoke
    // puffs, so a heavily-polluted settlement reads as visibly worse off
    // at a glance, not just "has more smoke" — a direct visual echo of
    // sustainability._industrial_pollution_penalty() (sustainability.py).
    const groundHex = lerpColor(0x6f8a52, 0x4a4238, pollution);
    group.add(buildGround(groundHex));

    const houseCount = settlementScale(vs, 3, 7, 10);
    ringLayout(houseCount, 1.7, 0.4).forEach(function (pos) {
      const house = buildHouse(0xa89880, 0x3a3028, 0.5, 0.5, 0.5);
      house.position.set(pos[0], 0, pos[1]);
      group.add(house);
    });

    const worksCount = Math.min(4, vs.buildings.sanitation_works || 0);
    const factoryCount = Math.max(1, Math.min(4, Math.ceil(vs.population / 12)));
    for (let i = 0; i < factoryCount; i++) {
      const built = buildChimneyFactory(0x5a5248);
      built.group.position.set(-1.6 + i * 1.1, 0, 2.0);
      group.add(built.group);
      const smokeIntensity = Math.max(0, pollution - worksCount * 0.15);
      const puffs = Math.round(smokeIntensity * 4);
      for (let p = 0; p < puffs; p++) {
        const puff = buildSmokePuff(0x777777, 0.5 + p * 0.15);
        puff.position.copy(built.smokeOrigin).add(built.group.position);
        puff.position.y += p * 0.22;
        group.add(puff);
      }
    }
    // Real, distinct meshes for Sanitation Works itself (see
    // buildSanitationWorks() above) -- previously this building had no
    // visual footprint at all beyond reducing the factories' smoke.
    for (let i = 0; i < worksCount; i++) {
      const works = buildSanitationWorks();
      works.position.set(1.5, 0, 1.4 + i * 0.7);
      group.add(works);
    }
    setupLighting(group, lerpColor(0xdfe6ee, 0x8a8a86, pollution), 0x3a3a3a, vs.season);
    return group;
  }

  function buildDigitalScene(vs) {
    const group = new THREE.Group();
    group.add(buildGround(0x808a94));

    const towerCount = settlementScale(vs, 3, 8, 10);
    ringLayout(towerCount, 1.6, 0.5).forEach(function (pos, i) {
      const height = 0.7 + (i % 4) * 0.3;
      const tower = buildGlassTower(0x5f7f9f, height);
      tower.position.set(pos[0], 0, pos[1]);
      group.add(tower);
    });

    const hubCount = Math.min(4, vs.buildings.transit_hubs || 0);
    for (let i = 0; i < hubCount; i++) {
      const line = flatPlot(1.8, 0.14, 0xe0c23c, 0.03);
      line.position.set(0, 0, -1.2 - i * 0.3);
      group.add(line);
    }
    setupLighting(group, 0xdbe8f5, 0x40484f, vs.season);
    return group;
  }

  function buildSpaceScene(vs) {
    const group = new THREE.Group();
    group.add(buildGround(0x746a7c));

    const spireCount = settlementScale(vs, 3, 8, 10);
    ringLayout(spireCount, 1.7, 0.5).forEach(function (pos, i) {
      const height = 0.9 + (i % 3) * 0.35;
      const spire = buildSpire(0x8890c8, height);
      spire.position.set(pos[0], 0, pos[1]);
      group.add(spire);
    });

    const ringCount = Math.min(3, vs.buildings.habitat_rings || 0);
    for (let i = 0; i < ringCount; i++) {
      const habitatRing = ring(1.1 + i * 0.5, 0.06, 0x6fd7d0);
      habitatRing.position.y = 0.9 + i * 0.35;
      group.add(habitatRing);
    }
    setupLighting(group, 0x9fa8e8, 0x2a2440, vs.season);
    return group;
  }

  const ERA_BUILDERS = {
    tribal: buildTribalScene,
    agrarian: buildAgrarianScene,
    classical: buildClassicalScene,
    medieval: buildMedievalScene,
    industrial: buildIndustrialScene,
    digital: buildDigitalScene,
    space: buildSpaceScene,
  };

  function lerpColor(fromHex, toHex, t) {
    const from = new THREE.Color(fromHex);
    const to = new THREE.Color(toHex);
    return from.lerp(to, Math.max(0, Math.min(1, t))).getHex();
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
  }

  // K27: keyboard access to the presets (see the shortcuts panel).
  window.ContinuumCamera = { preset: applyCameraPreset };

  function setupCameraPresetButtons() {
    const row = document.getElementById(CAMERA_PRESET_ROW_ID);
    if (!row) return;
    const timeSelect = document.getElementById("time-of-day-select");
    if (timeSelect) {
      timeSelect.addEventListener("change", function () {
        timeOfDay = timeSelect.value;
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
      scene.add(sceneGroup);
    }
    renderer.render(scene, camera);
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
    } else {
      container.hidden = true;
      fallback.hidden = false;
      if (button) button.innerText = "🧊 3D view";
      // Camera presets only mean anything with a live 3D scene on screen.
      if (presetRow) presetRow.hidden = true;
      if (snapshotButton) snapshotButton.hidden = true;
    }
    try {
      window.localStorage.setItem(VIEW_MODE_STORAGE_KEY, mode);
    } catch (e) {
      // Storage can throw in a locked-down/private-browsing context —
      // the toggle still works for this page load, it just won't be
      // remembered next time. Not worth failing the toggle over.
    }
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
      const height = 220;

      // K13 — preserveDrawingBuffer keeps the drawing buffer intact after
      // a render instead of letting the browser clear/swap it away before
      // the next paint, which is what makes toDataURL() a reliable
      // capture of the last-rendered frame across browsers rather than
      // occasionally returning a blank PNG.
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      container.innerHTML = "";
      container.appendChild(renderer.domElement);

      scene = new THREE.Scene();
      camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 100);
      updateCameraPosition();

      toonGradientMap = makeToonGradientMap();

      attachDragControls(container);
      window.addEventListener("resize", function () {
        const w = container.clientWidth || width;
        renderer.setSize(w, height);
        camera.aspect = w / height;
        camera.updateProjectionMatrix();
        if (scene) renderer.render(scene, camera);
      });

      pyodideRef = pyodide;
      ready = true;

      // First paint, then wire the hook game.py calls after every render().
      pullStateAndRender();
      window.continuumOnRender = pullStateAndRender;

      setupToggleButton();
      setupCameraPresetButtons();
      setupSnapshotButton();
      return true;
    } catch (err) {
      console.warn("Continuum 3D: failed to initialise, staying on the 2D view.", err);
      ready = false;
      return false;
    }
  }

  window.ContinuumVisual = { init: init, capture: capture };
})();
