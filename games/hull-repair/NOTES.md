# Hull Repair: notes

## Design specs (LA-13)

Written 2026-10-22 (LA-13 design pass). Steps: `local-ai/incoming/hull-repair-design.txt`. Standing rules hold for every
item: nothing timed, nothing lost, no luck needed for 100%, no audio files, saves load unchanged.

### R4-HRMO-3: pinch zoom and two-finger pan on the board (and a "Whole board" button instead of double-tap)
- **Zoom model:** the shared board zoom (the same `makeBoardZoom` as Dead Reckoning and Logic Gates' NOTES.md; code
  below): only the board SVG's `viewBox` changes, from the whole board (zoom 1) to zoom 4. A new board (`view.board.svg`
  present) fits back to 1; drawing a line (the `#hr-lines` layer) keeps the zoom. Nothing is saved.
- **Gestures:** one finger and the mouse always draw, exactly as today (`blockPan` returns true, so the zoom never pans
  with one pointer). Two fingers pinch and pan together (touch events; the holder already has `touch-action: none`).
  The pinch engages only after the fingers spread, close or move 12 px, so the R4-HRMO-5 two-finger tap (undo) still works.
- **No double-tap fit:** a double tap on the end of a line already takes two cells back ("tap the end of a line to take
  one cell back", `play.Drawing.end`), so stealing it would change a rule. Fit is a button instead: `#board-fit-button`
  ("Whole board"), shown only while zoomed; with `#board-zoom-in-button` (+) and `#board-zoom-out-button` (minus) in
  `#board-zoom-bar` under the board, shown at 700 px wide and below (phones; the desktop board is small enough).
- **Nothing lost: the first finger's touch is cancelled exactly.** On a phone the first finger of a pinch lands first and
  `begin` runs at once (on a line's middle cell `begin` already cuts the line after it). When the second finger lands, the
  page sends a new engine action `cancel_touch`: the layout goes back to exactly what it was before `begin` (the
  `before` copy `begin` already keeps), the took-back flag and the tally's `laid`/`erased` go back too, no undo step is
  recorded and nothing is saved. `cancel_touch` with no touch in progress changes nothing and answers `ok: true`.
- **Engine (play.py, game.py):** `Drawing.begin` adds `"tb": self.took_back` to both `self.drag = {...}` dicts.
  New method `Drawing.cancel()` (below `end`):

```python
    def cancel(self):
        """A second finger came down during a touch (a pinch): put the layout back as it was before begin(). Not an undo step."""
        d = self.drag
        self.drag = None
        if d is None:
            return False
        self.paths = _copy(d["before"])
        self.took_back = d["tb"]
        self.laid = self.erased = 0
        return True
```

  `Game.__init__`: `self.touch_tally = None   # (laid, erased) when the current touch began, for cancel_touch (never saved)`.
  `handle`, `begin` branch: directly before `ok, message = d.begin(cell)` add `g.touch_tally = (g.tally["laid"], g.tally["erased"])`.
  New branch directly before `elif action == "undo":`

```python
    elif action == "cancel_touch":
        if d.cancel() and g.touch_tally is not None:
            g.tally["laid"], g.tally["erased"] = g.touch_tally
        g.touch_tally = None
```

  (it falls through to `g._count()`, which reads zero, and the view). Docstring line under `end`:
  `  cancel_touch                 a second finger came down: the touch in progress is put back exactly (no undo step)`.
- **Page (app.js):** `cellAt` must read the zoomed viewBox, so it converts with `getScreenCTM()` instead of the bounding
  box (this also fixes a latent letterbox error when `max-height: 62vh` makes the SVG box wider than the drawing):

```js
  function cellAt(e) {
    var svg = boardSvg();
    if (!svg || !view) return null;
    var m = svg.getScreenCTM();
    if (!m) return null;
    var p = svg.createSVGPoint();
    p.x = e.clientX;
    p.y = e.clientY;
    var q = p.matrixTransform(m.inverse());   // viewBox units, so the zoom (LA-13) needs nothing else here
    var b = view.board;
    var x = Math.floor(q.x / b.cell);
    var y = Math.floor(q.y / b.cell);
    if (x < 0 || y < 0 || x >= b.w || y >= b.h) return null;
    return [x, y];
  }
  function cancelTouch() {
    if (!drag) return;
    var was = drag;
    drag = null;
    var holder = $("board-holder");
    if (holder.releasePointerCapture) { try { holder.releasePointerCapture(was.id); } catch (err) { /* ignore */ } }
    clearFingerGhost();
    if (was.active) send({ action: "cancel_touch" });
  }
```

  `var boardZoom = null;` and `var mapZoom = null;` go directly after `var drag = null;`. In `wire()`, directly after
  `holder.addEventListener("pointercancel", onPointerUp);`:

```js
    boardZoom = makeBoardZoom(holder, {
      max: 4,
      noDblclick: true,                          // a double tap on a line's end takes two cells back: never steal it
      blockPan: function () { return true; },    // one finger or the mouse always draws; two fingers pan
      onPinchStart: cancelTouch,
      onChange: function (z) { var f = $("board-fit-button"); if (f) f.hidden = z <= 1.001; },
    });
```

  In `renderBoard()`, inside `if (b.svg) {`, directly after `$("board-holder").innerHTML = b.svg;`: `if (boardZoom) boardZoom.fit();`.
- **Zoom bar markup** (index.html, directly after the `#board-holder` div) and CSS (style.css, after the `.board-holder svg` rule):

```html
    <div id="board-zoom-bar" class="board-zoom-bar"><button id="board-zoom-out-button" type="button" aria-label="Zoom out">&minus;</button><button id="board-zoom-in-button" type="button" aria-label="Zoom in">+</button><button id="board-fit-button" type="button" hidden>Whole board</button></div>
```

```css
.board-zoom-bar { display: none; gap: 0.4rem; justify-content: center; margin: 0.3rem 0; }
.board-zoom-bar button { min-height: 44px; min-width: 44px; }
@media (max-width: 700px) { .board-zoom-bar { display: flex; } }
```

  Wiring in `wire()` after the boardZoom block: `$("board-zoom-in-button").addEventListener("click", function () { boardZoom.zoomBy(1.25); });`,
  the same for `board-zoom-out-button` with 0.8, and `board-fit-button` calling `boardZoom.fit()`.
- **Must not break:** drawing by finger, mouse and keyboard (the keyboard cursor `#hr-cursor` is placed in viewBox units
  and is unaffected), the finger ghost, the two-finger tap undo (R4-HRMO-5), `test_pledge.py` (app.js keeps exactly one
  `setTimeout`: the shared zoom uses none; no banned words in the new text), `test_render.py` (Python SVG untouched),
  `test_game_handle.py`, the save (`touch_tally` is never written).
- **Tests:** `tests/test_cancel_touch.py` (NEW, engine) and `tests/test_board_zoom_browser.py` (NEW, page).

### R4-HRPC-1: the station cutaway zooms and pans, hover reads a room
- Most of it exists: `render.station_svg` already gives every room `class="hr-room"`, `data-id` and a `<title>`
  ("name: status"), `onMapClick` opens a room, and R4-HRPC-10 moves across the map by keyboard. What is new:
  a second `makeBoardZoom` on `#map-holder` (wheel: plain on the Desktop page, `<html data-layout="pc">`, Ctrl/Cmd+wheel on
  the Classic page; drag pans when zoomed and the click that ends a pan is swallowed, so a pan never opens a room;
  dblclick fits; zoom 1 to 4), re-applied in `renderMap()` after its `innerHTML`; and a readout line
  `<p id="map-readout" class="note map-readout">` under the map that shows the `<title>` text of the room under the mouse
  (`mouseover`) and goes back to the hint on `mouseleave`. The hint text, constant `MAP_HINT` in app.js:
  "Point at a room to read its state. Ctrl+wheel zooms the map and a drag pans it." The readout is a mouse aid; the
  keyboard path (R4-HRPC-10) and the `<title>` tooltips stay as they are.
- Wiring (in `wire()`, directly after `$("map-holder").addEventListener("click", onMapClick);`):

```js
    mapZoom = makeBoardZoom($("map-holder"), {
      max: 4,
      wheelNeedsCtrl: function () { return document.documentElement.getAttribute("data-layout") !== "pc"; },
    });
    $("map-holder").addEventListener("mouseover", function (e) {
      var room = e.target.closest ? e.target.closest(".hr-room[data-id]") : null;
      var t = room && room.querySelector("title");
      setText($("map-readout"), t ? t.textContent : MAP_HINT);
    });
    $("map-holder").addEventListener("mouseleave", function () { setText($("map-readout"), MAP_HINT); });
```

  `renderMap()`: directly after `holder.innerHTML = view.map;` add `if (mapZoom) mapZoom.apply();`.
  `var MAP_HINT = "Point at a room to read its state. Ctrl+wheel zooms the map and a drag pans it.";` next to `var mapZoom`.
- **Must not break:** `onMapClick` (a plain click still opens the room and closes the panel), R4-HRPC-10's keyboard map
  movement, `test_render.py` (station SVG untouched).

### R4-HRMO-4 (vertical scroll of decks with room thumbnails): not designed in this pass
It needs a small board-thumbnail renderer in `render.py` and a phone layout for the rooms panel; left for a later pass.

### R4-HRMO-6 (drag backward to trim, a soft tick per cell): already built
Checked 2026-10-22: `play.Drawing.move` trims when the finger goes back over its own line (`test_ai_hrpc4.py` and
`test_play.py` drive it), and `onPointerMove` calls `HR_Haptics.tick()` (a 10 ms vibration, off with reduced motion or
effects off) for every accepted move. A fast drag that crosses several cells in one pointer event gives one tick for
that event; a vibration per cell would only cancel the previous one, so this is the intended feel. Nothing to build.

### The shared zoom code (copied verbatim into app.js, directly above the line `// ---- the board ---...`)

```js
  // ---- board zoom and pan (LA-13 shared design). Only the SVG's viewBox changes: the engine's markup, the
  // getScreenCTM tap maths and every test that reads the SVG stay as they are. The zoom survives a redraw
  // because apply() runs again after every innerHTML replacement; nothing is saved. One pointer (mouse, or a
  // finger on a zoomed board) pans after 6 px; two fingers pinch through touch events, whose preventDefault
  // stops the browser's own scroll or zoom for that gesture only.
  function makeBoardZoom(holder, opts) {
    var MAX = opts.max || 6;
    var z = 1, cx = null, cy = null, pointers = 0, pinch = null, drag = null, gestured = false;
    function svg() { return holder.querySelector("svg"); }
    function base(s) {
      if (!s.dataset.baseViewBox) s.dataset.baseViewBox = s.getAttribute("viewBox");
      var b = s.dataset.baseViewBox.split(/[\s,]+/).map(Number);
      return { x: b[0], y: b[1], w: b[2], h: b[3] };
    }
    function apply() {
      var s = svg();
      if (!s || !(s.dataset.baseViewBox || s.getAttribute("viewBox"))) return;
      var b = base(s), w = b.w / z, h = b.h / z;
      if (cx === null) { cx = b.x + b.w / 2; cy = b.y + b.h / 2; }
      cx = Math.min(Math.max(cx, b.x + w / 2), b.x + b.w - w / 2);
      cy = Math.min(Math.max(cy, b.y + h / 2), b.y + b.h - h / 2);
      s.setAttribute("viewBox", [cx - w / 2, cy - h / 2, w, h].map(function (v) { return Math.round(v * 1000) / 1000; }).join(" "));
      holder.classList.toggle("zoomed", z > 1.001);
      if (opts.onChange) opts.onChange(z);
    }
    function toUser(clientX, clientY) {
      var s = svg(), m = s && s.getScreenCTM();
      if (!m) return null;
      var p = s.createSVGPoint();
      p.x = clientX;
      p.y = clientY;
      return p.matrixTransform(m.inverse());
    }
    function zoomTo(nz, clientX, clientY) {
      if (!svg()) return;
      nz = Math.min(Math.max(nz, 1), MAX);
      if (cx === null) apply();
      var p = clientX === undefined ? null : toUser(clientX, clientY);
      if (p) { cx = p.x + (cx - p.x) * z / nz; cy = p.y + (cy - p.y) * z / nz; }
      z = nz;
      apply();
    }
    function panBy(dxPx, dyPx) {
      var s = svg(), m = s && s.getScreenCTM();
      if (!m || z <= 1.001) return;
      cx -= dxPx / m.a;
      cy -= dyPx / m.d;
      apply();
    }
    function fit() { z = 1; cx = null; apply(); }
    var swallowClick = false;   // set when a pan or a pinch ends: the click that follows must not also tap the board
    function swallowNextClick() { gestured = false; swallowClick = true; }
    holder.addEventListener("click", function (ev) {
      if (!swallowClick) return;
      swallowClick = false;
      ev.stopImmediatePropagation();
      ev.preventDefault();
    }, true);
    holder.addEventListener("pointerdown", function (e) {
      swallowClick = false;   // a new press: a gesture that ended without a click leaves nothing behind
      if (e.pointerType === "mouse" && e.button !== 0) return;
      pointers += 1;
      drag = pointers === 1 && !(opts.blockPan && opts.blockPan(e)) ? { id: e.pointerId, x: e.clientX, y: e.clientY, moved: false } : null;
    });
    holder.addEventListener("pointermove", function (e) {
      if (!drag || drag.id !== e.pointerId || pinch || z <= 1.001) return;
      var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (!drag.moved && Math.abs(dx) + Math.abs(dy) < 6) return;
      if (!drag.moved) {
        drag.moved = true;
        gestured = true;
        try { holder.setPointerCapture(e.pointerId); } catch (err) { /* synthetic events have no active pointer */ }
      }
      panBy(dx, dy);
      drag.x = e.clientX;
      drag.y = e.clientY;
    });
    function pointerEnd(e) {
      pointers = Math.max(0, pointers - 1);
      if (drag && drag.id === e.pointerId) drag = null;
      if (!pointers && !pinch && gestured) swallowNextClick();
    }
    holder.addEventListener("pointerup", pointerEnd);
    holder.addEventListener("pointercancel", pointerEnd);
    function two(e) {
      var a = e.touches[0], b = e.touches[1];
      return { d: Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY) || 1, m: { x: (a.clientX + b.clientX) / 2, y: (a.clientY + b.clientY) / 2 } };
    }
    holder.addEventListener("touchstart", function (e) {
      if (e.touches.length !== 2) return;
      var t = two(e);
      pinch = { d: t.d, z: z, m: t.m, m0: t.m, on: false };
      drag = null;
      if (opts.onPinchStart) opts.onPinchStart();   // the game drops whatever the first finger had started
    }, { passive: true });
    holder.addEventListener("touchmove", function (e) {
      if (!pinch || e.touches.length !== 2) return;
      e.preventDefault();   // two fingers: no page scroll or browser zoom while they are down
      var t = two(e);
      if (!pinch.on && Math.abs(t.d - pinch.d) < 12 && Math.hypot(t.m.x - pinch.m0.x, t.m.y - pinch.m0.y) < 12) return;   // still a two-finger tap
      pinch.on = true;
      zoomTo(pinch.z * t.d / pinch.d, t.m.x, t.m.y);
      panBy(t.m.x - pinch.m.x, t.m.y - pinch.m.y);
      pinch.m = t.m;
      gestured = true;
    }, { passive: false });
    function touchEnd(e) {
      if (e.touches.length < 2) pinch = null;
      if (!e.touches.length && gestured) swallowNextClick();
    }
    holder.addEventListener("touchend", touchEnd);
    holder.addEventListener("touchcancel", touchEnd);
    holder.addEventListener("wheel", function (e) {
      if (!svg() || (opts.wheelNeedsCtrl && opts.wheelNeedsCtrl() && !e.ctrlKey && !e.metaKey)) return;
      e.preventDefault();
      zoomTo(z * (e.deltaY < 0 ? 1.25 : 0.8), e.clientX, e.clientY);
    }, { passive: false });
    if (!opts.noDblclick) holder.addEventListener("dblclick", function (e) { if (z > 1.001) { e.preventDefault(); fit(); } });
    window.addEventListener("beforeprint", fit);
    return {
      apply: apply, fit: fit, panBy: panBy,
      zoomBy: function (f) { zoomTo(z * f); },
      level: function () { return z; },
    };
  }
```

### Test code for the R4-HRMO-3 steps (copy verbatim; never change an expected value)
Step 1, NEW file `tests/test_cancel_touch.py`:

```python
"""LA-13 / R4-HRMO-3: cancel_touch puts a touch in progress back exactly (a pinch's first finger)."""
import json

import boards
import game


def call(**req):
    return json.loads(game.handle(json.dumps(req)))


def fresh():
    game.game.__init__()


def test_cancel_touch_puts_the_layout_and_the_tally_back():
    fresh()
    base = call(action="open")
    call(action="begin", x=3, y=0)
    v = call(action="move", cells=[[2, 0]])
    assert v["tally"]["laid"] == 1
    v = call(action="cancel_touch")
    assert v["ok"] is True and v["tally"] == base["tally"] and v["layer"] == base["layer"]
    assert v["can_undo"] is False and game.game.draw.paths == {} and game.game.draw.drag is None


def test_cancel_touch_mends_a_line_that_begin_cut():
    fresh()
    b = boards.ALL_BOARDS[0]
    c = b.lines[0]
    path = b.solution[c]
    call(action="begin", x=path[0][0], y=path[0][1])
    call(action="move", cells=[list(p) for p in path[1:4]])
    call(action="end")
    before = call(action="open")
    call(action="begin", x=path[1][0], y=path[1][1])      # a middle cell: begin cuts the line after it
    v = call(action="cancel_touch")
    assert game.game.draw.paths[c] == [tuple(p) for p in path[:4]]
    assert v["tally"] == before["tally"] and v["can_undo"] == before["can_undo"]
    assert game.game.draw.took_back is False


def test_cancel_touch_without_a_touch_changes_nothing_and_is_never_saved():
    fresh()
    base = call(action="open")
    v = call(action="cancel_touch")
    assert v["ok"] is True and v["tally"] == base["tally"]
    assert "touch_tally" not in json.dumps(game.get_state())
```

Step 2, NEW file `tests/test_board_zoom_browser.py` (step 3 adds one more test to it):

```python
"""LA-13 / R4-HRMO-3: pinch zoom on the board; a second finger cancels the first finger's touch."""
import pytest
from browser_helpers import open_game  # the `base` fixture comes from conftest.py

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

CELL = ("(xy) => { const s = document.querySelector('#board-holder svg'), "
        "T = parseFloat(document.getElementById('hr-cursor').getAttribute('width')), m = s.getScreenCTM(); "
        "return [m.a * (xy[0] + 0.5) * T + m.e, m.d * (xy[1] + 0.5) * T + m.f]; }")
POINTER = ("(a) => document.getElementById('board-holder').dispatchEvent(new PointerEvent(a.type, "
           "{pointerId: 1, pointerType: 'touch', button: 0, clientX: a.x, clientY: a.y, bubbles: true}))")
TWO_FINGERS = ("(a) => { const s = document.querySelector('#board-holder svg'); "
               "const t = (id, x) => new Touch({identifier: id, target: s, clientX: x, clientY: a.y}); "
               "s.dispatchEvent(new TouchEvent('touchstart', {touches: [t(1, a.x), t(2, a.x + 80)], "
               "changedTouches: [t(2, a.x + 80)], bubbles: true, cancelable: true})); }")


def test_a_second_finger_cancels_the_first_fingers_line(base):
    with sync_playwright() as p:
        browser, page = open_game(p, base, 390, 844)
        page.wait_for_selector("#board-holder svg", state="attached")
        a = page.evaluate(CELL, [3, 0])
        b = page.evaluate(CELL, [2, 0])
        page.evaluate(POINTER, {"type": "pointerdown", "x": a[0], "y": a[1]})
        page.evaluate(POINTER, {"type": "pointermove", "x": b[0], "y": b[1]})
        assert page.text_content("#stat-laid") == "1"
        page.evaluate(TWO_FINGERS, {"x": a[0], "y": a[1]})
        assert page.text_content("#stat-laid") == "0"
        assert page.locator("#hr-lines [data-line]").count() == 0
        assert page.page_errors == []
        browser.close()
```
