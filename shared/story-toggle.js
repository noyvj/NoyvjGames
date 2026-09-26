/*
 * Shared "story text" toggle (Z-extra, from Z11: "let players pick to do a
 * story mode in each game or turn off the story elements"). One include per
 * game that carries narrative/flavor framing:
 *   <script src="../../shared/story-toggle.js" data-game-id="<slug>"
 *           data-story-selectors="#vignette, .region-flavor"></script>
 * data-story-selectors lists ONLY narrative elements (vignettes, flavor
 * lines, story logs, epilogues). Mechanics explanations, tooltips and the
 * real-world info framing are deliberately never listed: turning the story
 * off must never hide anything the player needs to play.
 *
 * Adds a small fixed "Story: on/off" pill (bottom-left) and, when off, hides
 * the listed elements with one injected CSS rule keyed on
 * <html data-story-text="off">. The choice persists per game in
 * localStorage["story-text:<slug>"] ("off" or absent = on) and is a per-device
 * display preference, never part of a save.
 */
(function () {
  const SCRIPT = document.currentScript;
  const GAME_ID = SCRIPT && SCRIPT.dataset.gameId;
  const SELECTORS = ((SCRIPT && SCRIPT.dataset.storySelectors) || "")
    .split(",").map((s) => s.trim()).filter(Boolean);
  if (!GAME_ID || !SELECTORS.length) {
    console.error("story-toggle.js: needs data-game-id and data-story-selectors");
    return;
  }
  const KEY = `story-text:${GAME_ID}`;

  function lsGet(key) { try { return localStorage.getItem(key); } catch (err) { return null; } }
  function lsSet(key, value) { try { localStorage.setItem(key, value); } catch (err) { /* convenience only */ } }

  const style = document.createElement("style");
  style.textContent =
    SELECTORS.map((s) => `html[data-story-text="off"] ${s}`).join(",\n") +
    " { display: none !important; }\n" +
    `#story-toggle { position: fixed; left: 0.6rem; bottom: 4.4rem; z-index: 800;
       font: inherit; font-size: 0.75rem; padding: 0.3rem 0.7rem; cursor: pointer;
       color: inherit; background: rgba(20, 22, 36, 0.85);
       border: 1px solid rgba(140, 160, 255, 0.3); border-radius: 999px; }
     #story-toggle:hover, #story-toggle:focus-visible { background: rgba(60, 68, 110, 0.9); outline: none; }`;
  document.head.appendChild(style);

  let on = lsGet(KEY) !== "off";
  const button = document.createElement("button");
  button.type = "button";
  button.id = "story-toggle";
  button.title = "Show or hide this game's story and flavor text. Nothing needed to play is ever hidden.";

  function apply() {
    document.documentElement.setAttribute("data-story-text", on ? "on" : "off");
    button.textContent = on ? "📖 Story: on" : "📖 Story: off";
    button.setAttribute("aria-pressed", String(on));
  }
  button.addEventListener("click", () => {
    on = !on;
    lsSet(KEY, on ? "on" : "off");
    apply();
  });
  apply();
  const mount = () => document.body.appendChild(button);
  if (document.body) mount();
  else document.addEventListener("DOMContentLoaded", mount);
})();
