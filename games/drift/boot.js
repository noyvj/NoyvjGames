// Boot: load Pyodide, write the shared Python helper and every drift_*.py module into Pyodide's file system, then
// run game.py (the entry point), which imports them. Add a new Python module to DRIFT_PY_MODULES below (and to
// sw.js and offline-manifest.json) or the page cannot import it. Keep the list in dependency order; it must match
// _PART_NAMES in game.py (a test checks both against the .py files on disk).
const DRIFT_PY_MODULES = [
  "drift_runstate.py",
  "drift_rules.py",
  "drift_model_region.py",
  "drift_regional.py",
  "drift_trendgraph.py",
  "drift_visuals.py",
  "drift_messages.py",
  "drift_achievements.py",
  "drift_pages.py",
  "drift_ledger.py",
  "drift_calendar.py",
  "drift_collection.py",
  "drift_undo.py",
  "drift_tiers.py",
  "drift_plans.py",
  "drift_assist.py",
  "drift_settings.py",
  "drift_loading.py",
  "drift_report.py",
  "drift_newsview.py",
  "drift_renderer.py",
  "drift_handlers.py",
  "drift_savestate.py",
];

async function main() {
  const pyodide = await loadPyodide();
  window.pyodide = pyodide; // exposed for the save/load bridge below
  // Shared info-page widget (see shared/info_page.py) -- written into
  // Pyodide's virtual filesystem before game.py runs so `import
  // info_page` resolves normally, same pattern as Continuum's
  // ENGINE_MODULES loop.
  const infoPageSource = await (await fetch("../../shared/info_page.py")).text();
  pyodide.FS.writeFile("info_page.py", infoPageSource, { encoding: "utf8" });
  // game.py imports these (see the list at the top of this file); same fetch-then-writeFile pattern as Continuum's ENGINE_MODULES.
  await Promise.all(DRIFT_PY_MODULES.map(async (name) => {
    const moduleSource = await (await fetch(name)).text();
    pyodide.FS.writeFile(name, moduleSource, { encoding: "utf8" });
  }));
  const [achievementsJson, changelogJson, code] = await Promise.all([
    fetch("achievements.json").then((response) => response.text()),
    fetch("changelog.json").then((response) => response.text()),
    fetch("game.py").then((response) => response.text()),
  ]);
  window.ACHIEVEMENTS_JSON = achievementsJson;
  window.CHANGELOG_JSON = changelogJson;
  await pyodide.runPythonAsync(code);

  if (window.GameTutorial) {
    GameTutorial.init(window.DRIFT_PC_TUTORIAL_STEPS || DRIFT_TUTORIAL_STEPS, { gameId: "drift" });
  }

  // I-2: Scenario Builder wiring
  window.addEventListener("load", () => {
    const housingSlider = document.getElementById("scenario-housing-slider");
    const servicesSlider = document.getElementById("scenario-services-slider");
    const infraSlider = document.getElementById("scenario-infra-slider");
    const fundsSlider = document.getElementById("scenario-funds-slider");
    const severitySlider = document.getElementById("scenario-severity-slider");
    const horizonSelect = document.getElementById("scenario-horizon-select");
    const housingVal = document.getElementById("scenario-housing-val");
    const servicesVal = document.getElementById("scenario-services-val");
    const infraVal = document.getElementById("scenario-infra-val");
    const fundsVal = document.getElementById("scenario-funds-val");
    const severityVal = document.getElementById("scenario-severity-val");
    const horizonVal = document.getElementById("scenario-horizon-val");
    const generateBtn = document.getElementById("scenario-generate-button");
    const codeDisplay = document.getElementById("scenario-code-display");
    const loadBtn = document.getElementById("scenario-load-button");

    function updateLabels() {
      housingVal.textContent = housingSlider.value;
      servicesVal.textContent = servicesSlider.value;
      infraVal.textContent = infraSlider.value;
      fundsVal.textContent = fundsSlider.value;
      severityVal.textContent = parseFloat(severitySlider.value).toFixed(1);
      horizonVal.textContent = horizonSelect.value;
    }

    [housingSlider, servicesSlider, infraSlider, fundsSlider, severitySlider].forEach(el => {
      el.addEventListener("input", updateLabels);
    });
    horizonSelect.addEventListener("change", updateLabels);

    function getParams() {
      return {
        housing: parseInt(housingSlider.value),
        services: parseInt(servicesSlider.value),
        infrastructure: parseInt(infraSlider.value),
        funds: parseInt(fundsSlider.value),
        severity_rate: parseFloat(severitySlider.value),
        horizon: parseInt(horizonSelect.value)
      };
    }

    function generateCode() {
      const params = getParams();
      const json = JSON.stringify(params);
      const encoded = btoa(unescape(encodeURIComponent(json)));
      codeDisplay.textContent = encoded;
      codeDisplay.hidden = false;
      loadBtn.hidden = true;
    }

    function loadCode() {
      const code = prompt("Paste scenario code:");
      if (!code) return;
      try {
        const json = decodeURIComponent(escape(atob(code)));
        const params = JSON.parse(json);
        housingSlider.value = params.housing || 0;
        servicesSlider.value = params.services || 0;
        infraSlider.value = params.infrastructure || 0;
        fundsSlider.value = params.funds || 300;
        severitySlider.value = params.severity_rate || 0.5;
        horizonSelect.value = params.horizon || 50;
        updateLabels();
        codeDisplay.hidden = true;
        loadBtn.hidden = false;
      } catch (e) {
        alert("Invalid scenario code.");
      }
    }

    generateBtn.addEventListener("click", generateCode);
    loadBtn.addEventListener("click", loadCode);

    // Apply loaded scenario to the game region
    window.DRIFT_APPLY_SCENARIO = function() {
      const params = getParams();
      const pyodide = window.pyodide;
      if (!pyodide) return;
      const start_scenario = pyodide.globals.get("start_scenario");
      if (typeof start_scenario === "function") {
        start_scenario(
          { housing: params.housing, services: params.services, infrastructure: params.infrastructure },
          params.funds,
          params.severity_rate,
          params.horizon
        );
        render();
      }
    };

    // Auto-load if URL has scenario param
    const urlParams = new URLSearchParams(window.location.search);
    const scenarioParam = urlParams.get("scenario");
    if (scenarioParam) {
      try {
        const json = decodeURIComponent(escape(atob(scenarioParam)));
        const params = JSON.parse(json);
        housingSlider.value = params.housing || 0;
        servicesSlider.value = params.services || 0;
        infraSlider.value = params.infrastructure || 0;
        fundsSlider.value = params.funds || 300;
        severitySlider.value = params.severity_rate || 0.5;
        horizonSelect.value = params.horizon || 50;
        updateLabels();
        window.DRIFT_APPLY_SCENARIO();
      } catch (e) { /* ignore invalid URL param */ }
    }
  });
  if (window.MobileHud) {
    MobileHud.init([
      { selector: "#hud-round-display", label: "" },
      { selector: "#hud-strain-display", label: "Strain" },
      { selector: "#hud-wellbeing-display", label: "Wellbeing" },
    ]);
  }
}
main();
