# Logic Gates: notes

## Design specs (LA-13)

Written 2026-10-22 (LA-13 design pass). Steps: `local-ai/incoming/logic-gates-design.txt`. Standing rules hold for every
item: nothing timed, nothing lost, no luck needed for 100%, no audio files, saves load unchanged.

### R4-LGPC-2 (wheel zoom, drag pan, minimap) and R4-LGMO-3 (pinch, two-finger pan, double-tap fit)
- **Model: size zoom inside the native scroller.** The board SVG `#lg-board` keeps the natural `width`/`height`
  attributes `render.py` writes; the zoom sets its CSS `style.width`/`style.height` to natural x z. `#board-scroll`
  (already a scroller, keyboard-focusable) does all panning through `scrollLeft`/`scrollTop`, so arrow keys and one-finger
  native scrolling keep working and nothing in `render.py`, the pin maths (`magnetPin` reads `getBoundingClientRect`) or
  the tap-to-wire path changes. (Dead Reckoning uses the viewBox instead because its chart is a fixed-size picture; this
  board is wider than the screen and needs zoom levels below 1, which a viewBox cannot give.)
- **Numbers:** z from min(fit, 1) to 3, where fit = (scroller width - 12) / natural width, clamped 0.2 to 1. Steps x1.25 /
  x0.8. A wheel or pinch zoom keeps the point under the pointer (or between the fingers) in place.
- **Fit:** the existing per-device choice `logic-gates:fit-board` (`FIT_KEY`, R4-LGMO-10) keeps its meaning: while it is
  "1", every redraw zooms to fit. Any wheel, pinch or +/- zoom turns it off (it is a convenience, not a save). The phone
  button `#lg-fit-btn` sets z back to 1 when it turns fit off ("full size", as its message says). Double-click or
  double-tap on the board turns fit on (LGMO-3).
- **Wheel:** Desktop page (`window.NOYVJ_LAYOUT === "pc"`): the plain wheel zooms; Shift+wheel still scrolls sideways.
  Classic page: only Ctrl/Cmd+wheel zooms (a trackpad pinch arrives as Ctrl+wheel, so it works on both).
- **Mouse drag** on the board (not starting on a `[data-pin]`, which stays a pick and is kept free for R4-LGPC-1's wire
  drag) scrolls the scroller after 6 px; the click that ends it is swallowed so nothing is picked or flipped.
- **Touch:** one finger is the browser's own scroll (unchanged). Two fingers: `touchmove` (not passive) calls
  `preventDefault` while two fingers are down, then zooms and pans once the fingers have spread, pinched or moved 12 px.
  Below 12 px it is still the R4-LGMO-9 two-finger tap (undo); the undo handler's touchmove also treats an engaged pinch
  as "moved", so a pinch never undoes.
- **Keys** (`onKey`, any layout, focus not in a field or on a button): `+`/`=` zoom in, `-` zoom out, `0` fit.
- **UI (zoom bar, both layouts):** `<div id="lg-zoom-bar" class="lg-zoom-bar">` directly before `#board-scroll`, holding
  `#zoom-out-button` (minus), `#zoom-level` (text "100%", `aria-live="polite"`), `#zoom-in-button` (plus) and
  `#zoom-fit-button` ("Whole board", hidden at 600 px and below where `#lg-fit-btn` does the same).
- **Minimap (LGPC-2):** `#lg-minimap` after `#board-scroll`, `aria-hidden="true"`, shown only while the board can scroll
  (scrollWidth or scrollHeight larger than the box) and only at 900 px wide and above. It holds a copy of the board's
  markup with every `id="..."` removed (no duplicate ids; `pointer-events: none`) at 200 px wide, plus a rectangle
  `#lg-minimap-view` for the visible part, updated on every zoom and on the scroller's `scroll` event. A press on the
  minimap centres the board there. Keyboard users have the scroller and the zoom keys, so the minimap is a mouse aid only.
- **Saves:** none new. `FIT_KEY` stays as it is.
- **Must not break:** tap-to-wire (`pick`), `magnetPin`, the two-finger-tap undo, `#lg-fit-btn` and its R4-LGMO-10 test
  (`test_ai_r4_wiring.py`), the Desktop board window (`pc.css` gives `.board-scroll` `overflow: auto`), the chip drawer,
  and `test_assets_and_shell.py`'s count of exactly two `setTimeout` in app.js (the click after a gesture is swallowed with a
  flag that the next press clears, not with a timer).
- **Tests:** `tests/test_board_zoom_browser.py` (NEW): keys, Ctrl+wheel, a redraw (flip switch A) keeps the zoom, mouse
  drag scrolls without flipping, the zoom bar, the minimap appears at 300% and its press scrolls, a synthetic two-finger
  pinch zooms, and a two-finger tap still undoes.

The code (step 1 copies it verbatim into app.js, directly above `function wire()`; tested on a stand-alone page on
2026-10-22: Ctrl+wheel 1.25 about the pointer, plain wheel left alone on Classic, mouse drag scrolls and the click is
swallowed, synthetic TouchEvent pinch prevented and zoomed to 2.5, double-click fits, a redraw keeps the zoom):

```js
  // ---- board zoom (LA-13: R4-LGPC-2, R4-LGMO-3). The SVG keeps its natural width and height attributes; the zoom sets its CSS size
  // and #board-scroll (a native scroller) does the panning, so arrow keys and one-finger scrolling keep working. Nothing new is
  // saved: the zoom lasts for the page visit, and the existing per-device "fit" choice (FIT_KEY) still means "fit to the width".
  var ZOOM_MAX = 3;
  var zoom = { z: 1, drag: null, pinch: null, gestured: false, swallow: false };
  function naturalSize() {
    var s = $("lg-board");
    return s ? { w: parseFloat(s.getAttribute("width")) || 1, h: parseFloat(s.getAttribute("height")) || 1 } : null;
  }
  function fitLevel() {
    var n = naturalSize(), sc = $("board-scroll");
    if (!n || !sc || !sc.clientWidth) return 1;
    return Math.max(0.2, Math.min(1, (sc.clientWidth - 12) / n.w));
  }
  function applyZoom() {
    var s = $("lg-board"), n = naturalSize();
    if (!s) return;
    if (fitOn()) zoom.z = fitLevel();
    zoom.z = Math.max(Math.min(fitLevel(), 1), Math.min(ZOOM_MAX, zoom.z));
    s.style.width = Math.round(n.w * zoom.z) + "px";
    s.style.height = Math.round(n.h * zoom.z) + "px";
    var label = $("zoom-level");
    if (label) setText(label, Math.round(zoom.z * 100) + "%");
    if (typeof updateMinimap === "function") updateMinimap();
  }
  function zoomAt(nz, clientX, clientY) {
    var sc = $("board-scroll");
    if (!sc || !$("lg-board")) return;
    if (fitOn()) { lsSet(FIT_KEY, "0"); applyFit(); }
    nz = Math.max(Math.min(fitLevel(), 1), Math.min(ZOOM_MAX, nz));
    var r = sc.getBoundingClientRect();
    var ox = clientX === undefined ? sc.clientWidth / 2 : clientX - r.left;
    var oy = clientY === undefined ? sc.clientHeight / 2 : clientY - r.top;
    var px = (sc.scrollLeft + ox) / zoom.z, py = (sc.scrollTop + oy) / zoom.z;
    zoom.z = nz;
    applyZoom();
    sc.scrollLeft = px * nz - ox;
    sc.scrollTop = py * nz - oy;
  }
  function swallowBoardClick() { zoom.gestured = false; zoom.swallow = true; }   // the click after a pan or a pinch must not pick a pin
  function initZoom() {
    var sc = $("board-scroll");
    sc.addEventListener("wheel", function (e) {
      if (e.shiftKey || (window.NOYVJ_LAYOUT !== "pc" && !e.ctrlKey && !e.metaKey)) return;
      e.preventDefault();
      zoomAt(zoom.z * (e.deltaY < 0 ? 1.25 : 0.8), e.clientX, e.clientY);
    }, { passive: false });
    sc.addEventListener("click", function (e) {
      if (!zoom.swallow) return;
      zoom.swallow = false;
      e.stopImmediatePropagation();
      e.preventDefault();
    }, true);
    sc.addEventListener("pointerdown", function (e) {
      zoom.swallow = false;   // a new press: a gesture that ended without a click leaves nothing behind
      var onPin = e.target.closest && e.target.closest("[data-pin]");   // a press on a pin stays a pick (kept free for wire dragging)
      zoom.drag = e.pointerType === "mouse" && e.button === 0 && !onPin ? { id: e.pointerId, x: e.clientX, y: e.clientY, moved: false } : null;
    });
    sc.addEventListener("pointermove", function (e) {
      var d = zoom.drag;
      if (!d || d.id !== e.pointerId) return;
      var dx = e.clientX - d.x, dy = e.clientY - d.y;
      if (!d.moved && Math.abs(dx) + Math.abs(dy) < 6) return;
      if (!d.moved) {
        d.moved = true;
        zoom.gestured = true;
        try { sc.setPointerCapture(e.pointerId); } catch (err) { /* synthetic events have no active pointer */ }
      }
      sc.scrollLeft -= dx;
      sc.scrollTop -= dy;
      d.x = e.clientX;
      d.y = e.clientY;
    });
    function pointerEnd() { zoom.drag = null; if (zoom.gestured && !zoom.pinch) swallowBoardClick(); }
    sc.addEventListener("pointerup", pointerEnd);
    sc.addEventListener("pointercancel", pointerEnd);
    function two(e) {
      var a = e.touches[0], b = e.touches[1];
      return { d: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY) || 1, m: { x: (a.clientX + b.clientX) / 2, y: (a.clientY + b.clientY) / 2 } };
    }
    sc.addEventListener("touchstart", function (e) {
      if (e.touches.length !== 2) return;
      var t = two(e);
      zoom.pinch = { d: t.d, z: zoom.z, m: t.m, m0: t.m, on: false };
    }, { passive: true });
    sc.addEventListener("touchmove", function (e) {
      var p = zoom.pinch;
      if (!p || e.touches.length !== 2) return;
      e.preventDefault();   // two fingers: no page scroll or browser zoom while they are down
      var t = two(e);
      if (!p.on && Math.abs(t.d - p.d) < 12 && Math.hypot(t.m.x - p.m0.x, t.m.y - p.m0.y) < 12) return;   // still a two-finger tap (undo)
      p.on = true;
      zoom.gestured = true;
      zoomAt(p.z * t.d / p.d, t.m.x, t.m.y);
      sc.scrollLeft -= t.m.x - p.m.x;
      sc.scrollTop -= t.m.y - p.m.y;
      p.m = t.m;
    }, { passive: false });
    function touchEnd(e) {
      if (e.touches.length < 2) zoom.pinch = null;
      if (!e.touches.length && zoom.gestured) swallowBoardClick();
    }
    sc.addEventListener("touchend", touchEnd);
    sc.addEventListener("touchcancel", touchEnd);
    $("board-holder").addEventListener("dblclick", function (e) { e.preventDefault(); lsSet(FIT_KEY, "1"); applyFit(); });
    window.addEventListener("resize", applyZoom);
  }
```

Edits around it (step 1): in `applyFit()` add `applyZoom();` as its last line; in `initMobileTools()`'s click handler add
`zoom.z = 1;` directly before its `applyFit();`; in `renderBoard()` add `applyZoom();` directly after the
`if (holder.dataset.signature !== view.svg) { ... }` block; in `wire()` add `initZoom();` directly before
`initMobileTools();`; in `onKey`, directly after the `key === "escape"` branch, add
`else if (key === "+" || key === "=") { e.preventDefault(); zoomAt(zoom.z * 1.25); }`,
`else if (key === "-") { e.preventDefault(); zoomAt(zoom.z * 0.8); }` and
`else if (key === "0") { e.preventDefault(); lsSet(FIT_KEY, "1"); applyFit(); }`.

The two-finger-tap undo (step 4, R4-LGMO-3): in `wire()`, the document `touchmove` listener's condition
`if (tap2 && Math.hypot(e.touches[0].clientX - tap2.x, e.touches[0].clientY - tap2.y) > 12)` becomes
`if (tap2 && (Math.hypot(e.touches[0].clientX - tap2.x, e.touches[0].clientY - tap2.y) > 12 || (zoom.pinch && zoom.pinch.on)))`.
CSS for touch (style.css, after the `.board-scroll` rule): `.board-scroll { touch-action: pan-x pan-y; }`.

The zoom bar (step 2), index.html directly before `<div id="board-scroll"`:

```html
      <div id="lg-zoom-bar" class="lg-zoom-bar"><button id="zoom-out-button" type="button" aria-label="Zoom out">&minus;</button><span id="zoom-level" class="lg-zoom-level" aria-live="polite">100%</span><button id="zoom-in-button" type="button" aria-label="Zoom in">+</button><button id="zoom-fit-button" type="button">Whole board</button></div>
```

```css
.lg-zoom-bar { display: flex; gap: 0.4rem; align-items: center; margin: 0 0 0.4rem; }
.lg-zoom-level { min-width: 3.5em; text-align: center; font-variant-numeric: tabular-nums; }
@media (max-width: 600px) { #zoom-fit-button { display: none; } }
```

Its wiring (app.js `wire()`, directly after `initZoom();`): `guard("zoom-in-button", function () { zoomAt(zoom.z * 1.25); });`,
`guard("zoom-out-button", function () { zoomAt(zoom.z * 0.8); });`,
`guard("zoom-fit-button", function () { lsSet(FIT_KEY, "1"); applyFit(); });`.

The minimap (step 3), index.html directly after the `#board-scroll` div closes:

```html
      <div id="lg-minimap" class="lg-minimap" aria-hidden="true" hidden><div id="lg-minimap-board"></div><div id="lg-minimap-view" class="lg-minimap-view"></div></div>
```

```js
  function updateMinimap() {
    var mm = $("lg-minimap"), sc = $("board-scroll");
    if (!mm || !sc || !$("lg-board") || !view) return;
    var big = sc.scrollWidth > sc.clientWidth + 4 || sc.scrollHeight > sc.clientHeight + 4;
    mm.hidden = !big;
    if (!big) return;
    var copy = $("lg-minimap-board");
    if (copy.dataset.signature !== view.svg) {
      copy.innerHTML = view.svg.replace(/ id="[^"]*"/g, "");
      copy.dataset.signature = view.svg;
    }
    var k = 200 / sc.scrollWidth, box = $("lg-minimap-view").style;
    box.left = Math.round(sc.scrollLeft * k) + "px";
    box.top = Math.round(sc.scrollTop * k) + "px";
    box.width = Math.round(sc.clientWidth * k) + "px";
    box.height = Math.round(Math.min(sc.clientHeight, sc.scrollHeight) * k) + "px";
  }
  function initMinimap() {
    $("board-scroll").addEventListener("scroll", updateMinimap);
    $("lg-minimap").addEventListener("pointerdown", function (e) {
      var r = $("lg-minimap").getBoundingClientRect(), sc = $("board-scroll"), k = sc.scrollWidth / r.width;
      sc.scrollLeft = (e.clientX - r.left) * k - sc.clientWidth / 2;
      sc.scrollTop = (e.clientY - r.top) * k - sc.clientHeight / 2;
    });
  }
```

```css
.lg-minimap { position: relative; width: 200px; margin: 0.4rem 0 0 auto; border: 1px solid var(--line); border-radius: 6px; background: var(--surface); line-height: 0; cursor: pointer; }
.lg-minimap svg { width: 200px; height: auto; pointer-events: none; }
.lg-minimap-view { position: absolute; border: 2px solid var(--focus); box-sizing: border-box; pointer-events: none; }
@media (max-width: 899px) { .lg-minimap { display: none !important; } }
```

### R4-LGPC-1 (drag a wire pin to pin) and R4-LGPC-4 (chip right-click menu with Open inside): not designed in this pass
LGPC-1 can follow the zoom: the zoom leaves presses on `[data-pin]` alone on purpose. It needs only the existing `pick`
action (pick the source on pointerdown, the destination found with `magnetPin` on pointerup), plus a preview line drawn
in a separate overlay SVG (not inside `#lg-board`, which the engine replaces). LGPC-4 needs an engine view of a chip's
inside circuit and Duplicate/Delete rules for wired chips; left for a later pass.
