/*
 * Continuum -- the Three.js scene building blocks and the era scene recipes (part 1 of 2 of the old render3d.js).
 *
 * This file only DEFINES things: the low-poly building blocks (box, hut, house, spire ...), the sky and lighting set-up, one builder per
 * era (ERA_BUILDERS) and the time-of-day table. It touches no renderer, camera or page element, and reaches THREE only inside
 * functions, so it is safe to load when Three.js failed to load. It exports everything through window.ContinuumScenes;
 * render3d.js (loaded right after this file) destructures that object and owns the renderer, camera, drag controls, snapshot,
 * screensaver and the view-mode toggle. Ask for this file to change how an era's scene looks.
 */

(function () {
  "use strict";

  let toonGradientMap = null;
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

  // R2-K26 (the Relay Age): a Relay Station -- a slim pylon with a tilted
  // dish and a glowing beacon on top, the one shape every relay in the scene
  // and in the Hamlet view is built from.
  function buildRelayPylon(hex) {
    const group = new THREE.Group();
    const mast = cylinder(0.05, 0.09, 1.0, hex, 6);
    const dish = coneRoof(0.24, 0.16, 0xd8e4ff, 8);
    dish.rotation.x = Math.PI; // open side up, like a receiving dish
    dish.position.y = 1.0;
    const beacon = new THREE.Mesh(new THREE.SphereGeometry(0.07, 8, 6), toonMaterial(0xffd27a));
    beacon.position.y = 1.2;
    group.add(mast, dish, beacon);
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

  // Y11b (light theme): the renderer is transparent (alpha: true) and the
  // "sky" is the container's CSS background, so the light theme swaps that
  // gradient in style.css; here only the lights change. Dark mode's numbers
  // are untouched. A little extra hemisphere light lifts the shadowed
  // sides of the low-poly buildings, and the sky tint is pulled toward a
  // pale daylight blue so the ground-side colours read as bright, not murky.
  const LIGHT_THEME_HEMI_BOOST = 1.18;
  const LIGHT_THEME_SUN_BOOST = 1.1;
  const LIGHT_THEME_SKY_TINT = 0xdbe8ff;
  const LIGHT_THEME_SKY_PULL = 0.35;

  function isLightTheme() {
    const attr = document.documentElement && document.documentElement.getAttribute("data-theme");
    if (attr) return attr === "light";
    return !!(window.NoyvjTheme && window.NoyvjTheme.get() === "light");
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
    let tintedSky = lerpColor(skyHex, seasonalTint, SEASONAL_TINT_PULL);
    let hemiBoost = 1.0;
    let sunBoost = 1.0;
    if (isLightTheme()) {
      tintedSky = lerpColor(tintedSky, LIGHT_THEME_SKY_TINT, LIGHT_THEME_SKY_PULL);
      hemiBoost = LIGHT_THEME_HEMI_BOOST;
      sunBoost = LIGHT_THEME_SUN_BOOST;
    }

    const hemi = new THREE.HemisphereLight(tintedSky, groundHex, 0.9 * brightnessFactor * hemiBoost);
    const sun = new THREE.DirectionalLight(0xffffff, 0.75 * brightnessFactor * sunBoost);
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

  // K-5 (planning/TODO.md): later eras switch from a circle to a grid so more buildings fit.
  // A centred block of `count` cells in rows of `columns`, `spacing` apart.
  function gridLayout(count, columns, spacing) {
    const positions = [];
    const rows = Math.ceil(count / columns);
    for (let i = 0; i < count; i++) {
      const col = i % columns;
      const row = Math.floor(i / columns);
      const inRow = Math.min(columns, count - row * columns);
      positions.push([(col - (inRow - 1) / 2) * spacing, (row - (rows - 1) / 2) * spacing]);
    }
    return positions;
  }

  // K-5: heritage sites, one per era the settlement has left behind, on a ring at the edge of
  // the ground. A kept site is a weathered ruin whose SHAPE is its era's (stone circle, wall,
  // colonnade, tower stump, chimney, slab, ring segment); a cleared one is only a flat
  // footprint, so the state reads by shape and not by colour.
  const RUIN_STONE = 0x9a9486;
  const RUIN_ORDER = ["tribal", "agrarian", "classical", "medieval", "industrial", "digital", "space"];

  function buildRuin(era, kept) {
    const group = new THREE.Group();
    if (!kept) {
      const footprint = flatPlot(0.5, 0.5, 0x6d6658, 0.02);
      group.add(footprint);
      return group;
    }
    if (era === "tribal") {
      for (let i = 0; i < 5; i++) {
        const stone = cylinder(0.05, 0.07, 0.22 + (i % 2) * 0.1, RUIN_STONE, 5);
        const a = (i / 5) * Math.PI * 2;
        stone.position.set(Math.cos(a) * 0.22, stone.position.y, Math.sin(a) * 0.22);
        group.add(stone);
      }
    } else if (era === "agrarian") {
      for (let i = 0; i < 3; i++) {
        const wall = box(0.5, 0.08 + (i % 2) * 0.05, 0.06, RUIN_STONE);
        wall.position.set(0, wall.position.y, (i - 1) * 0.16);
        group.add(wall);
      }
    } else if (era === "classical") {
      for (let i = 0; i < 3; i++) {
        const column = cylinder(0.06, 0.07, i === 1 ? 0.2 : 0.4, RUIN_STONE, 8);
        column.position.set((i - 1) * 0.2, column.position.y, 0);
        group.add(column);
      }
    } else if (era === "medieval") {
      group.add(cylinder(0.22, 0.26, 0.38, RUIN_STONE, 8));
      const gap = box(0.12, 0.2, 0.12, 0x6d6658);
      gap.position.set(0.18, gap.position.y + 0.28, 0);
      group.add(gap);
    } else if (era === "industrial") {
      group.add(cylinder(0.07, 0.11, 0.6, 0x8a5a44, 8));
      group.add(box(0.34, 0.1, 0.3, RUIN_STONE));
    } else if (era === "digital") {
      const slab = box(0.46, 0.06, 0.32, 0x7d8892);
      slab.rotation.z = 0.25;
      slab.position.y = 0.12;
      group.add(slab);
      group.add(box(0.1, 0.22, 0.1, 0x59636c));
    } else {
      const segment = new THREE.Mesh(
        new THREE.TorusGeometry(0.3, 0.05, 6, 12, Math.PI * 1.3),
        toonMaterial(0x8e98a8)
      );
      segment.rotation.x = Math.PI / 2;
      segment.position.y = 0.06;
      group.add(segment);
    }
    return group;
  }

  // K-12: the generated map's non-plains cells as flat tiles on the ground (and a small peak on each
  // mountain cell away from the middle), so the geography reads by shape and sits under the buildings.
  const TERRAIN_COLOR = { river: 0x6fb0d8, coast: 0x4f7fc0, mountains: 0x8d8d92, desert: 0xd8c27a };

  function addTerrain(group, cells) {
    if (!Array.isArray(cells)) return;
    cells.forEach(function (cell) {
      const color = TERRAIN_COLOR[cell.biome];
      if (color === undefined) return;
      const x = cell.x * 3.6;
      const z = cell.z * 2.6;
      const tile = flatPlot(1.2, 1.2, color, 0.012);
      tile.position.set(x, 0.012, z);
      group.add(tile);
      if (cell.biome === "mountains" && Math.hypot(x, z) >= 2.2) {
        const peak = coneRoof(0.4, 0.55, 0x77777c, 5);
        peak.position.set(x, 0.28, z);
        group.add(peak);
      }
      if (cell.biome === "coast") {
        const foam = flatPlot(1.2, 0.06, 0xdfeaf6, 0.02);
        foam.position.set(x, 0.02, z + (cell.z > 0 ? -0.55 : 0.55));
        group.add(foam);
      }
    });
  }

  function addHeritage(group, sites) {
    if (!Array.isArray(sites)) return;
    sites.forEach(function (site) {
      const index = RUIN_ORDER.indexOf(site.era);
      if (index < 0) return;
      const angle = -Math.PI / 2 + (index / RUIN_ORDER.length) * Math.PI * 2 + 0.2;
      const ruin = buildRuin(site.era, site.kept !== false);
      ruin.position.set(Math.cos(angle) * 4.2, 0, Math.sin(angle) * 4.2);
      ruin.rotation.y = -angle;
      ruin.scale.set(1.5, 1.5, 1.5);
      group.add(ruin);
    });
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

    const towerCount = settlementScale(vs, 3, 8, 16);
    gridLayout(towerCount, 4, 0.7).forEach(function (pos, i) {
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

    const spireCount = settlementScale(vs, 3, 8, 16);
    gridLayout(spireCount, 4, 0.7).forEach(function (pos, i) {
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

  // R2-K26: the Relay Age. The core keeps the Space Age silhouette (spires and
  // habitat rings) and grows a ring of outlying holdings around it, each with
  // a relay pylon, a low dome for its residents, and a link back to the core
  // drawn as a row of flat plates. A holding that was NOT fully supplied
  // last season has a BROKEN link -- plates missing from the outer end in
  // proportion to the shortfall -- so the state is legible by shape, not by
  // colour alone (same rule the rest of the game's status cues follow).
  function buildRelayScene(vs) {
    const group = new THREE.Group();
    group.add(buildGround(0x5d6d76, 4.6));

    const spireCount = settlementScale(vs, 2, 12, 6);
    ringLayout(spireCount, 0.9, 0.35).forEach(function (pos, i) {
      const spire = buildSpire(0x8890c8, 0.8 + (i % 3) * 0.3);
      spire.position.set(pos[0], 0, pos[1]);
      group.add(spire);
    });
    const habitatCount = Math.min(2, vs.buildings.habitat_rings || 0);
    for (let i = 0; i < habitatCount; i++) {
      const habitatRing = ring(0.8 + i * 0.4, 0.05, 0x6fd7d0);
      habitatRing.position.y = 0.95 + i * 0.3;
      group.add(habitatRing);
    }

    const relayCount = Math.min(6, vs.buildings.relay_stations || 0);
    const served = vs.holdings_served_ratio == null ? 1.0 : vs.holdings_served_ratio;
    const PLATES = 6;
    const litPlates = Math.ceil(Math.max(0, Math.min(1, served)) * PLATES - 1e-9);
    for (let i = 0; i < relayCount; i++) {
      const angle = (i / 6) * Math.PI * 2 + 0.5;
      const dx = Math.cos(angle);
      const dz = Math.sin(angle);
      const pylon = buildRelayPylon(0x9fb0bd);
      pylon.position.set(dx * 3.1, 0, dz * 3.1);
      group.add(pylon);
      const dome = buildMound(0x6fd7d0);
      dome.scale.set(1.6, 1.3, 1.6);
      dome.position.set(dx * 3.6, 0, dz * 3.6);
      group.add(dome);
      for (let k = 0; k < litPlates; k++) {
        const t = 1.7 + (k / PLATES) * 1.3;
        const plate = flatPlot(0.14, 0.09, 0xe6d9a8, 0.03);
        plate.position.set(dx * t, 0, dz * t);
        plate.rotation.y = -angle;
        group.add(plate);
      }
    }
    if (relayCount >= 3) {
      // First off-world foothold: an orbital platform hanging over the site.
      const platform = new THREE.Group();
      platform.add(ring(0.55, 0.05, 0xd8e4ff));
      const hub = box(0.3, 0.16, 0.3, 0x8890c8);
      hub.position.y = -0.08;
      platform.add(hub);
      platform.position.set(-1.6, 2.2, -1.2);
      group.add(platform);
    }
    setupLighting(group, 0xa8c0d8, 0x26303a, vs.season);
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
    relay: buildRelayScene,
  };

  function lerpColor(fromHex, toHex, t) {
    const from = new THREE.Color(fromHex);
    const to = new THREE.Color(toHex);
    return from.lerp(to, Math.max(0, Math.min(1, t))).getHex();
  }

  // What render3d.js (and through it hamlet.js) uses. toonGradientMap and timeOfDay are private to this file;
  // the two small functions below are the only way render3d.js changes them.
  window.ContinuumScenes = {
    toonMaterial: toonMaterial,
    box: box,
    coneRoof: coneRoof,
    cylinder: cylinder,
    ring: ring,
    flatPlot: flatPlot,
    buildHut: buildHut,
    buildHouse: buildHouse,
    buildCampfire: buildCampfire,
    buildMound: buildMound,
    buildChimneyFactory: buildChimneyFactory,
    buildSanitationWorks: buildSanitationWorks,
    buildGlassTower: buildGlassTower,
    buildSpire: buildSpire,
    buildRelayPylon: buildRelayPylon,
    isLightTheme: isLightTheme,
    addTerrain: addTerrain,
    addHeritage: addHeritage,
    ERA_BUILDERS: ERA_BUILDERS,
    lerpColor: lerpColor,
    initToonGradientMap: function () { toonGradientMap = makeToonGradientMap(); },
    setTimeOfDay: function (value) { timeOfDay = value; },
  };
})();
