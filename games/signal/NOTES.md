# Signal: notes

## Design specs (LA-13)

Written 2026-10-22 (LA-13 design pass). Steps: `local-ai/incoming/signal-design.txt`. Standing rules hold for every
item: nothing timed, nothing lost, no luck needed for 100%, no audio files, saves load unchanged.

### R4-PU-4: distress calls (each solve locates a lost probe; clearing a sector opens the next)
- **Rule:** every won puzzle locates one lost probe: a won daily or archive day and every practice win, the same count
  the stats panel already shows as `total_solved`. Archive and practice count here because this is not a streak (the
  "archive and practice never touch streaks" rule is about streaks only); a lost or given-up puzzle locates nothing and
  takes nothing away.
- **Numbers:** 8 sectors of 6 probes (48 in all). Sector 1 is open from the start; sector N+1 opens when sector N has all
  6. After 48 the map is complete and further solves are only counted ("Further solves: N"). Nothing is gated: every
  puzzle stays playable whatever the map shows.
- **Saves: none new.** The map is a pure function of the solve count, which is already derived from `days` and
  `practice_stats`. Old saves show their progress at once and load unchanged; the frozen daily puzzles are untouched.
- **Luck:** none; practice is endless and deterministic, so 48 is always reachable.
- **Engine (signal_records.py, at the end of the file):**

```python
CALL_SECTORS = 8
CALL_PROBES = 6


def solved_count():
    """Every won puzzle: won daily and archive days plus practice wins (the stats panel's total_solved)."""
    days = sum(1 for rec in runstate.S["days"].values() if rec["result"] == "won")
    return days + sum(runstate.S["practice_stats"][m]["won"] for m in PRESET_ORDER)


def distress_calls(total):
    """R4-PU-4: each solved puzzle locates one lost probe; six probes clear a sector and the next one opens.
    A pure function of the solve count, so nothing new is saved."""
    total = max(0, int(total))
    cap = CALL_SECTORS * CALL_PROBES
    found = min(total, cap)
    sectors = []
    for i in range(CALL_SECTORS):
        located = max(0, min(CALL_PROBES, found - i * CALL_PROBES))
        sectors.append({"number": i + 1, "located": located, "of": CALL_PROBES,
                        "cleared": located == CALL_PROBES, "open": i * CALL_PROBES <= found})
    if found >= cap:
        line = "Every distress call answered: all %d probes found. Further solves: %d." % (cap, total - cap)
    else:
        line = "Sector %d: %d of %d probes located." % (found // CALL_PROBES + 1, found % CALL_PROBES, CALL_PROBES)
    return {"sectors": sectors, "found": found, "total": cap, "extra": total - found, "line": line}
```

  `signal_actions._action_stats`: replace its two counting loops with `total_solved = solved_count()` (import it from
  `signal_records`); the answer stays the same (`test_stats_and_achievements.py::test_quiet_streak_counts_all_wins`).
  `signal_session._view`: add `"calls": distress_calls(solved_count()),` directly after the `"ach": {...}` line, and add
  `distress_calls, solved_count` to the `from signal_records import ...` line.
- **Engine tests, NEW file `tests/test_distress_calls.py`:**

```python
"""LA-13 / R4-PU-4: distress calls, a pure function of the solve count."""
import signal_records


def test_a_new_player_has_sector_one_open_and_nothing_found():
    calls = signal_records.distress_calls(0)
    assert calls["line"] == "Sector 1: 0 of 6 probes located."
    assert [s["open"] for s in calls["sectors"]] == [True] + [False] * 7
    assert calls["found"] == 0 and calls["total"] == 48 and calls["extra"] == 0


def test_six_solves_clear_sector_one_and_open_sector_two():
    calls = signal_records.distress_calls(6)
    assert calls["sectors"][0]["cleared"] is True and calls["sectors"][1]["open"] is True
    assert calls["sectors"][2]["open"] is False
    assert calls["line"] == "Sector 2: 0 of 6 probes located."
    assert signal_records.distress_calls(9)["sectors"][1]["located"] == 3


def test_the_map_completes_at_48_and_keeps_counting():
    calls = signal_records.distress_calls(50)
    assert all(s["cleared"] for s in calls["sectors"]) and calls["found"] == 48 and calls["extra"] == 2
    assert calls["line"] == "Every distress call answered: all 48 probes found. Further solves: 2."
    assert signal_records.distress_calls(-3) == signal_records.distress_calls(0)


def test_a_win_locates_a_probe_and_a_loss_does_not(g):
    g.call("boot")
    assert g.call("view")["view"]["calls"]["found"] == 0
    g.call("practice", mode="easy")
    assert g.win_current(pings=1)["view"]["calls"]["found"] == 1
    g.call("practice", mode="easy")
    assert g.lose_current()["view"]["calls"]["found"] == 1
    assert g.call("stats")["total_solved"] == 1
```
- **Page:** a toolbar button `#calls-toggle-button` ("📡 Distress calls", after `#achievements-toggle-button`) opens
  `#calls-panel` (after `#stats-panel`):

```html
    <div id="calls-panel" class="section" hidden>
      <h2 class="panel-heading">Distress calls</h2>
      <p class="panel-note">Every puzzle you solve (daily, archive or practice) locates one lost probe. Six probes clear a sector and open the next.</p>
      <p id="calls-line" class="panel-note" aria-live="polite">The receiver is warming up.</p>
      <ol id="calls-list" class="calls-list"></ol>
    </div>
```

  Each sector is one `<li class="call-sector">`: `<strong>Sector N</strong>`, six probe marks `◉` (found) or `○`
  (silent) in an `aria-hidden` span, and a visible count text "4/6", or "opens after sector N-1" for a closed sector
  (state by shape and words, never colour alone). In the result panel, after `#result-detail`, a line
  `<p id="result-calls" class="panel-note" hidden></p>` shows "Each solve locates a lost probe. " + `calls.line` after a win.
  The page code (app-2-render.js, directly above `function render()`):

```js
  // ---- distress calls (R4-PU-4): every solve locates one lost probe; the engine sends view.calls --------------
  function renderCalls() {
    var calls = A.view && A.view.calls;
    if (!calls) return;
    $("calls-line").textContent = calls.line;
    var list = $("calls-list");
    list.textContent = "";
    calls.sectors.forEach(function (s) {
      var li = el("li", "call-sector" + (s.cleared ? " cleared" : "") + (s.open ? "" : " closed"));
      li.appendChild(el("strong", "", "Sector " + s.number));
      var marks = el("span", "call-probes", "");
      marks.setAttribute("aria-hidden", "true");
      for (var i = 0; i < s.of; i++) marks.appendChild(el("span", i < s.located ? "probe found" : "probe", i < s.located ? "◉" : "○"));
      li.appendChild(marks);
      li.appendChild(el("span", "call-count", s.open ? s.located + "/" + s.of : "opens after sector " + (s.number - 1)));
      list.appendChild(li);
    });
  }
```

  In `renderResult()`, directly after `$("result-detail").textContent = detail;`:
  `var callsLine = $("result-calls"); callsLine.hidden = !(res.won && A.view.calls); callsLine.textContent = res.won && A.view.calls ? "Each solve locates a lost probe. " + A.view.calls.line : "";`
  (and `$("result-calls").hidden = true;` is not needed when the panel is hidden). In `render()` add `renderCalls();` after
  `renderResult();`. Export: `A.renderCalls = renderCalls;` on the line that sets `A.render = render;`.
  app.js `wire()`, directly after the achievements toggle listener:

```js
    $("calls-toggle-button").addEventListener("click", function () {
      var panel = $("calls-panel");
      panel.hidden = !panel.hidden;
      if (!panel.hidden) { startEngine(); A.renderCalls(); }
    });
```

  index.html KeyboardShortcuts `panels`: `{ toggle: "calls-toggle-button", panel: "calls-panel" },` after the achievements
  entry. Desktop (later step): `["calls-panel", "calls-toggle-button", "Distress calls"]` in `pc-config.json` `windows`
  after the achievements window, and `["calls-toggle-button", "📡"]` in `toolbar.icons`; then regenerate `pc.html`.
  CSS (style.css, end): `.calls-list { list-style: none; padding: 0; margin: 0.4rem 0; display: grid; gap: 0.3rem; }`,
  `.call-sector { display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap; }`,
  `.call-sector.closed { opacity: 0.65; }`, `.call-probes { letter-spacing: 0.2em; }`, `.call-probes .found { font-weight: 700; }`.
- **Authored content:** none beyond the plain sector numbers. Sector names (for example after real probes) would be
  owner content and are left out; the numbers work without them.
- **Must not break:** the frozen daily puzzles and `SEED_VERSION`, streaks (unchanged), `total_solved` in the stats
  answer, the share text (no change), `test_file_sizes.py` (index.html grows by about 10 lines), `test_module_list.py`
  (no new module), the queued-tap boot (the panel shows "warming up" until the engine view arrives).
- **Tests:** engine as above; browser `tests/test_distress_calls_browser.py` (NEW): open the panel, wait for
  `window.SignalPage.engineReady`, 8 sectors listed, the line reads "Sector 1: 0 of 6 probes located.", sector 2's count
  reads "opens after sector 1", `#result-calls` hidden, no page errors.
