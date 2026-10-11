"""shared/lazy-packs.js + lazy-packs.css in headless Chromium (planning/TODO.md LZ-2 and LZ-3): the lazy
content-pack loader. A pack is fetched once however often it is asked for, a failure shows a plain
message with a working "Try again", offline says so, the four kinds (python, json, script, css) do
their job, a save that mentions a pack that is not loaded yet never breaks (requires / missing / soft),
the size cap and length checks refuse bad files, the loading card is an accessible status region, and
the record of fetched packs lands in localStorage["packs:<game>"]. Nothing here touches the network:
pack files are answered by the test itself."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from conftest import ORIGIN, ROOT, page_html  # noqa: E402

STYLE = ('<style>body{margin:0;padding:12px;font-family:system-ui;background:#12162a;color:#eee}'
         'html[data-theme="light"] body{background:#eef2fc;color:#1b2033}</style>')
PAGE = page_html(STYLE + '<link rel="stylesheet" href="/shared/lazy-packs.css">',
                 '<h1>Game</h1><button id="b" type="button">game button</button><div id="probe">probe</div>'
                 '<script src="/shared/lazy-packs.js"></script>')
PAGE_NO_LINK = page_html(STYLE, '<h1>Game</h1><script src="/shared/lazy-packs.js"></script>')
PAGE_MANIFEST = page_html(STYLE, '<h1>Game</h1><div id="probe">probe</div>'
                          '<script src="/shared/lazy-packs.js" data-game-id="harness" data-manifest="/modules.json"></script>')

WET = {"id": "wetland", "label": "Wetland Forest", "kind": "json", "url": "/packs/wetland.json", "bytes": 24300,
       "modes": ["Wetland Forest level"]}


class PackServer:
    """Answers /packs/** and /modules.json from a dict; counts hits; can fail the first N requests of a path,
    hold requests until the test releases them, or send an explicit status."""

    def __init__(self, h):
        self.files = {}          # path -> (status, body, content_type)
        self.hits = {}
        self.fail = {}           # path -> number of requests still to abort
        self.hold = False
        self.held = []
        h.context.route("**/packs/**", self.handle)
        h.context.route("**/modules.json", self.handle)

    def put(self, path, body, status=200, ctype="application/octet-stream"):
        self.files[path] = (status, body, ctype)

    def handle(self, route, request):
        path = request.url[len(ORIGIN):].split("?")[0]
        self.hits[path] = self.hits.get(path, 0) + 1
        if self.fail.get(path, 0) > 0:
            self.fail[path] -= 1
            return route.abort()
        if self.hold:
            self.held.append((route, path))
            return None
        return self.answer(route, path)

    def answer(self, route, path):
        if path not in self.files:
            return route.fulfill(status=404, body="")
        status, body, ctype = self.files[path]
        return route.fulfill(status=status, body=body, content_type=ctype)

    def release(self):
        held, self.held = self.held, []
        for route, path in held:
            self.answer(route, path)


def open_page(harness, page=PAGE, size=(1440, 900), init=(), theme=None, **kw):
    h = harness(size=size, init_scripts=list(init), **kw)
    h.pages["/t.html"] = page
    server = PackServer(h)
    return h, server


def go(h, theme=None):
    h.goto()
    if theme:
        h.page.evaluate("t => document.documentElement.setAttribute('data-theme', t)", theme)
    return h.page


def register(page, packs, **extra):
    page.evaluate("([packs, extra]) => NoyvjPacks.register(Object.assign({game: 'harness', packs}, extra))", [packs, extra])


def console_errors(h):
    return [m for m in h.console if m[0] == "error"]


def card_text(page):
    return page.evaluate("() => { const c = document.getElementById('noyvj-pack-card'); return c && !c.hidden ? c.textContent.replace(/\\s+/g, ' ').trim() : null; }")


# ---------------------------------------------------------------------------------------- one fetch

def test_loading_twice_at_once_and_twice_in_a_row_fetches_once(harness):
    h, srv = open_page(harness)
    srv.put("/packs/wetland.json", json.dumps({"tiles": [1, 2, 3]}), ctype="application/json")
    page = go(h)
    register(page, [WET])
    result = page.evaluate("""async () => {
      const [a, b] = await Promise.all([NoyvjPacks.load('wetland'), NoyvjPacks.load('wetland')]);
      const c = await NoyvjPacks.load('wetland');
      return {same: a === b && b === c, tiles: a.tiles, has: NoyvjPacks.has('wetland')};
    }""")
    assert result == {"same": True, "tiles": [1, 2, 3], "has": True}
    assert srv.hits["/packs/wetland.json"] == 1
    assert h.errors == [] and console_errors(h) == []


def test_requires_of_an_already_loaded_pack_does_not_fetch_again(harness):
    h, srv = open_page(harness)
    srv.put("/packs/wetland.json", "{}", ctype="application/json")
    page = go(h)
    register(page, [WET])
    page.evaluate("async () => { await NoyvjPacks.load('wetland'); await NoyvjPacks.requires(['wetland', 'wetland']); }")
    assert srv.hits["/packs/wetland.json"] == 1


# ---------------------------------------------------------------------------------- failure and retry

def test_failure_then_retry_succeeds_without_the_card(harness):
    h, srv = open_page(harness)
    srv.put("/packs/wetland.json", '{"ok": true}', ctype="application/json")
    srv.fail["/packs/wetland.json"] = 1
    page = go(h)
    register(page, [WET])
    first = page.evaluate("async () => { try { await NoyvjPacks.load('wetland', {ui: false}); return 'loaded'; } catch (e) { return [e.code, e.packId, NoyvjPacks.has('wetland')]; } }")
    assert first == ["network", "wetland", False]
    second = page.evaluate("async () => (await NoyvjPacks.load('wetland', {ui: false})).ok")
    assert second is True
    assert srv.hits["/packs/wetland.json"] == 2
    assert h.errors == []


def test_card_failure_message_and_try_again_button_resumes_the_same_promise(harness):
    h, srv = open_page(harness)
    srv.put("/packs/wetland.json", '{"ok": true}', ctype="application/json")
    srv.fail["/packs/wetland.json"] = 1
    page = go(h)
    register(page, [WET])
    page.evaluate("() => { window.__p = NoyvjPacks.load('wetland'); window.__p.then(v => { window.__done = v.ok; }, e => { window.__err = e.code; }); }")
    page.wait_for_selector(".noyvj-pack-retry")
    text = card_text(page)
    assert "Wetland Forest could not be loaded" in text and "Try again" in text and "Not now" in text
    assert page.evaluate("() => document.activeElement.className") == "noyvj-pack-retry"       # keyboard users land on it
    page.click(".noyvj-pack-retry")
    page.wait_for_function("window.__done === true")
    assert srv.hits["/packs/wetland.json"] == 2
    assert card_text(page) is None                                                           # the card went away
    assert page.evaluate("() => document.getElementById('noyvj-pack-card').hidden") is True


def test_not_now_rejects_and_a_later_load_starts_fresh(harness):
    h, srv = open_page(harness)
    srv.put("/packs/wetland.json", '{"ok": true}', ctype="application/json")
    srv.fail["/packs/wetland.json"] = 1
    page = go(h)
    register(page, [WET])
    page.evaluate("() => { window.__p = NoyvjPacks.load('wetland'); window.__p.catch(e => { window.__err = [e.code, e.dismissed]; }); }")
    page.wait_for_selector(".noyvj-pack-close")
    page.click(".noyvj-pack-close")
    page.wait_for_function("window.__err")
    assert page.evaluate("window.__err") == ["network", True]
    assert card_text(page) is None
    assert page.evaluate("async () => (await NoyvjPacks.load('wetland', {ui: false})).ok") is True


def test_http_errors_say_what_happened(harness):
    h, srv = open_page(harness)
    srv.put("/packs/missing.json", "", status=404)
    srv.put("/packs/broken.json", "", status=503)
    page = go(h)
    register(page, [dict(WET, id="missing", url="/packs/missing.json", label="Missing"), dict(WET, id="broken", url="/packs/broken.json", label="Broken")])
    out = page.evaluate("""async () => {
      const r = {};
      for (const id of ['missing', 'broken']) {
        try { await NoyvjPacks.load(id, {ui: false}); } catch (e) { r[id] = [e.code, e.status, e.message]; }
      }
      return r;
    }""")
    assert out["missing"][:2] == ["http", 404] and "not found" in out["missing"][2]
    assert out["broken"][:2] == ["http", 503] and "503" in out["broken"][2]


# ------------------------------------------------------------------------------------------ offline

def test_offline_says_so_plainly_and_a_retry_works_when_back_online(harness):
    h, srv = open_page(harness)
    srv.put("/packs/wetland.json", '{"ok": true}', ctype="application/json")
    page = go(h)
    register(page, [WET])
    h.context.set_offline(True)                       # navigator.onLine turns false ...
    srv.fail["/packs/wetland.json"] = 99              # ... and the (fulfilled) request has to fail like a dead network
    page.evaluate("() => { window.__p = NoyvjPacks.load('wetland'); window.__p.then(v => { window.__done = v.ok; }, e => { window.__err = e.code; }); }")
    page.wait_for_selector(".noyvj-pack-retry")
    text = card_text(page)
    assert "offline" in text and "Wetland Forest has not been downloaded" in text
    h.context.set_offline(False)
    srv.fail["/packs/wetland.json"] = 0
    page.click(".noyvj-pack-retry")
    page.wait_for_function("window.__done === true")


def test_offline_error_code_without_the_card(harness):
    h, srv = open_page(harness)
    page = go(h)
    register(page, [WET])
    h.context.set_offline(True)
    srv.fail["/packs/wetland.json"] = 99
    out = page.evaluate("async () => { try { await NoyvjPacks.load('wetland', {ui: false}); } catch (e) { return [e.code, e.message]; } }")
    assert out[0] == "offline" and "offline" in out[1]


CACHES_STUB = """(() => {
  const body = JSON.stringify({fromCache: true});
  window.__puts = [];
  window.caches = {
    keys: async () => ['site-cache-v5', 'runtime-cdn-cache-v1', 'site-cache-v12'],
    match: async (url) => (String(url).includes('cached.json') ? new Response(body, {status: 200}) : undefined),
    open: async (name) => ({ put: async (url, res) => { window.__puts.push([name, String(url), (await res.text()).length]); } }),
  };
})();"""


def test_a_pack_already_in_cache_storage_loads_when_the_network_is_gone(harness):
    h, srv = open_page(harness, init=[CACHES_STUB])
    page = go(h)
    register(page, [dict(WET, id="cached", url="/packs/cached.json")])
    srv.fail["/packs/cached.json"] = 5
    value = page.evaluate("async () => await NoyvjPacks.load('cached', {ui: false})")
    assert value == {"fromCache": True}
    assert page.evaluate("NoyvjPacks.has('cached')") is True


def test_without_a_service_worker_a_fresh_pack_is_stored_in_the_newest_live_cache(harness):
    h, srv = open_page(harness, init=[CACHES_STUB])
    srv.put("/packs/fresh.json", '{"n": 1}', ctype="application/json")
    page = go(h)
    register(page, [dict(WET, id="fresh", url="/packs/fresh.json")])
    page.evaluate("async () => { await NoyvjPacks.load('fresh', {ui: false}); }")
    page.wait_for_function("window.__puts.length === 1")
    name, url, size = page.evaluate("window.__puts[0]")
    assert name == "site-cache-v12" and url == ORIGIN + "/packs/fresh.json" and size == 8


# ------------------------------------------------------------------------------------------- kinds

def test_json_script_and_css_kinds(harness):
    h, srv = open_page(harness)
    srv.put("/packs/data.json", json.dumps({"levels": ["a", "b"]}), ctype="application/json")
    srv.put("/packs/mode.js", "window.__modeRuns = (window.__modeRuns || 0) + 1; window.__modeFn = () => 'hello';", ctype="text/javascript")
    srv.put("/packs/theme.css", "#probe { color: rgb(1, 2, 3); }", ctype="text/css")
    page = go(h)
    register(page, [
        {"id": "data", "label": "Data", "kind": "json", "url": "/packs/data.json", "bytes": 40},
        {"id": "mode", "label": "Mode", "kind": "script", "url": "/packs/mode.js", "bytes": 90},
        {"id": "theme", "label": "Theme", "kind": "css", "url": "/packs/theme.css", "bytes": 30},
    ])
    out = page.evaluate("""async () => {
      const data = await NoyvjPacks.load('data');
      const s1 = await NoyvjPacks.load('mode'); const s2 = await NoyvjPacks.load('mode');
      const c1 = await NoyvjPacks.load('theme'); const c2 = await NoyvjPacks.load('theme');
      return {levels: data.levels, runs: window.__modeRuns, fn: window.__modeFn(), sameScript: s1 === s2,
              scripts: document.querySelectorAll('script[data-noyvj-pack="mode"]').length,
              styles: document.querySelectorAll('style[data-noyvj-pack="theme"]').length, sameStyle: c1 === c2,
              color: getComputedStyle(document.getElementById('probe')).color};
    }""")
    assert out == {"levels": ["a", "b"], "runs": 1, "fn": "hello", "sameScript": True, "scripts": 1, "styles": 1,
                   "sameStyle": True, "color": "rgb(1, 2, 3)"}
    assert srv.hits == {"/packs/data.json": 1, "/packs/mode.js": 1, "/packs/theme.css": 1}
    assert h.errors == [] and console_errors(h) == []


FAKE_PYODIDE = """(() => {
  window.__fs = {};
  window.__ran = [];
  window.__mkdirs = [];
  window.pyodide = {
    FS: { writeFile: (name, text, opts) => { window.__fs[name] = [text, opts && opts.encoding]; }, mkdirTree: (p) => window.__mkdirs.push(p) },
    runPython: (code) => { window.__ran.push(['sync', code]); },
    runPythonAsync: async (code) => { window.__ran.push(['async', code]); },
  };
})();"""


def test_python_kind_writes_into_pyodides_file_system_and_can_exec(harness):
    h, srv = open_page(harness, init=[FAKE_PYODIDE])
    srv.put("/packs/wetland.py", "WET = 1\n", ctype="text/x-python")
    srv.put("/packs/cut.py", "def extra():\n    return 2\n", ctype="text/x-python")
    srv.put("/packs/sub.py", "X = 3\n", ctype="text/x-python")
    page = go(h)
    page.evaluate("window.__loaded = []")
    register(page, [
        {"id": "wetland", "label": "Wetland", "kind": "python", "url": "/packs/wetland.py", "bytes": 8},
        {"id": "cut", "label": "Cut piece", "kind": "python", "url": "/packs/cut.py", "bytes": 26, "exec": True},
        {"id": "sub", "label": "Nested", "kind": "python", "url": "/packs/sub.py", "bytes": 6, "path": "packs_dir/sub_mod.py"},
    ], onLoaded=None)
    out = page.evaluate("""async () => {
      const text = await NoyvjPacks.load('wetland', {onLoaded: (id, t, info) => window.__loaded.push([id, t, info.kind])});
      await NoyvjPacks.load('wetland');
      await NoyvjPacks.load('cut');
      await NoyvjPacks.load('sub');
      return {text, fs: window.__fs, ran: window.__ran.filter(r => r[0] === 'async'), loaded: window.__loaded, mkdirs: window.__mkdirs,
              invalidated: window.__ran.filter(r => r[0] === 'sync').length};
    }""")
    assert out["text"] == "WET = 1\n"
    assert out["fs"]["wetland.py"] == ["WET = 1\n", "utf8"]
    assert out["fs"]["cut.py"][0].startswith("def extra")
    assert out["fs"]["packs_dir/sub_mod.py"][0] == "X = 3\n"
    assert out["mkdirs"] == ["packs_dir"]
    assert out["ran"] == [["async", "def extra():\n    return 2\n"]]                       # only the exec pack was run
    assert out["loaded"] == [["wetland", "WET = 1\n", "python"]]
    assert out["invalidated"] == 3                                                         # importlib caches cleared per write
    assert srv.hits["/packs/wetland.py"] == 1


def test_python_pack_without_a_runtime_fails_plainly(harness):
    h, srv = open_page(harness)
    srv.put("/packs/wetland.py", "A = 1\n")
    page = go(h)
    register(page, [{"id": "wetland", "label": "Wetland", "kind": "python", "url": "/packs/wetland.py"}])
    out = page.evaluate("async () => { try { await NoyvjPacks.load('wetland', {ui: false}); } catch (e) { return [e.code, e.message]; } }")
    assert out[0] == "no-runtime" and "not ready" in out[1]
    assert page.evaluate("NoyvjPacks.has('wetland')") is False


def test_a_failing_import_callback_leaves_the_pack_unloaded_and_retryable(harness):
    h, srv = open_page(harness, init=[FAKE_PYODIDE])
    srv.put("/packs/wetland.py", "A = 1\n")
    page = go(h)
    register(page, [{"id": "wetland", "label": "Wetland", "kind": "python", "url": "/packs/wetland.py"}])
    out = page.evaluate("""async () => {
      let n = 0;
      const cb = () => { n += 1; if (n === 1) throw new Error('boom'); };
      let first = null;
      try { await NoyvjPacks.load('wetland', {ui: false, onLoaded: cb}); } catch (e) { first = e.code; }
      const state1 = NoyvjPacks.has('wetland');
      await NoyvjPacks.load('wetland', {ui: false, onLoaded: cb});
      return [first, state1, NoyvjPacks.has('wetland')];
    }""")
    assert out == ["import", False, True]


# ------------------------------------------------------------------------------ saves and requires

def test_requires_missing_unknown_and_used(harness):
    h, srv = open_page(harness)
    srv.put("/packs/a.json", '{"a": 1}')
    srv.put("/packs/b.json", '{"b": 1}')
    page = go(h)
    register(page, [dict(WET, id="a", label="A", url="/packs/a.json"), dict(WET, id="b", label="B", url="/packs/b.json")])
    out = page.evaluate("""async () => {
      const before = {missing: NoyvjPacks.missing(['a', 'b', 'ghost']), unknown: NoyvjPacks.unknown(['a', 'ghost']), used: NoyvjPacks.used()};
      const loaded = await NoyvjPacks.requires(['b', 'a', 'b'], {ui: false});
      return {before, loaded, after: {missing: NoyvjPacks.missing(['a', 'b', 'ghost']), used: NoyvjPacks.used()},
              empty: await NoyvjPacks.requires([]), none: await NoyvjPacks.requires(null)};
    }""")
    assert out["before"] == {"missing": ["a", "b", "ghost"], "unknown": ["ghost"], "used": []}
    assert out["loaded"] == ["b", "a"]
    assert out["after"] == {"missing": ["ghost"], "used": ["b", "a"]}
    assert out["empty"] == [] and out["none"] == []


def test_a_save_that_mentions_a_pack_that_cannot_load_never_breaks_soft_mode(harness):
    """The load_state flow: ask for the packs a save used; whatever cannot load is reported, nothing throws,
    nothing is removed, and the game can still restore everything else."""
    h, srv = open_page(harness)
    srv.put("/packs/a.json", '{"a": 1}')
    srv.put("/packs/gone.json", "", status=404)
    page = go(h)
    register(page, [dict(WET, id="a", label="A", url="/packs/a.json"), dict(WET, id="gone", label="Gone", url="/packs/gone.json")])
    out = page.evaluate("""async () => {
      const save = {version: 3, packs_used: ['a', 'gone', 'from-a-newer-version'], plots: [1, 2, 3]};
      const report = await NoyvjPacks.requires(save.packs_used, {soft: true, ui: false});
      return {report, save, a: NoyvjPacks.has('a')};
    }""")
    assert out["report"]["loaded"] == ["a"]
    assert [(f["id"], f["code"]) for f in out["report"]["failed"]] == [("gone", "http"), ("from-a-newer-version", "unknown")]
    assert all(f["message"] for f in out["report"]["failed"])
    assert out["save"]["plots"] == [1, 2, 3] and out["a"] is True


def test_requires_rejects_in_strict_mode_with_the_failing_id(harness):
    h, srv = open_page(harness)
    srv.put("/packs/a.json", '{"a": 1}')
    page = go(h)
    register(page, [dict(WET, id="a", label="A", url="/packs/a.json")])
    out = page.evaluate("async () => { try { await NoyvjPacks.requires(['a', 'ghost'], {ui: false}); } catch (e) { return [e.code, e.packId, NoyvjPacks.has('a')]; } }")
    assert out == ["unknown", "ghost", True]


def test_unknown_ids_are_refused(harness):
    h, srv = open_page(harness)
    page = go(h)
    register(page, [WET])
    out = page.evaluate("async () => { try { await NoyvjPacks.load('nope'); } catch (e) { return [e.code, e.message, document.getElementById('noyvj-pack-card') === null]; } }")
    assert out[0] == "unknown" and "nope" in out[1] and out[2] is True                          # no card for a typo
    assert page.evaluate("[NoyvjPacks.known('nope'), NoyvjPacks.known('wetland'), NoyvjPacks.has('nope'), NoyvjPacks.info('nope')]") == [False, True, False, None]


def test_dependencies_load_first_and_a_cycle_is_refused(harness):
    h, srv = open_page(harness)
    for name in "abc":
        srv.put(f"/packs/{name}.json", json.dumps({"n": name}))
    page = go(h)
    register(page, [
        dict(WET, id="a", label="A", url="/packs/a.json", needs=["b"]),
        dict(WET, id="b", label="B", url="/packs/b.json", needs=["c"]),
        dict(WET, id="c", label="C", url="/packs/c.json"),
        dict(WET, id="x", label="X", url="/packs/a.json", needs=["y"]),
        dict(WET, id="y", label="Y", url="/packs/b.json", needs=["x"]),
    ])
    out = page.evaluate("""async () => {
      await NoyvjPacks.load('a', {ui: false});
      const order = NoyvjPacks.used();
      let cycle = null;
      try { await NoyvjPacks.load('x', {ui: false}); } catch (e) { cycle = e.code; }
      return {order, cycle};
    }""")
    assert out == {"order": ["c", "b", "a"], "cycle": "dependency"}


def test_a_failing_dependency_stops_the_pack_that_needs_it(harness):
    h, srv = open_page(harness)
    srv.put("/packs/a.json", "{}")
    page = go(h)
    register(page, [dict(WET, id="a", label="A", url="/packs/a.json", needs=["dep"]),
                    dict(WET, id="dep", label="Dep", url="/packs/dep.json")])
    out = page.evaluate("async () => { try { await NoyvjPacks.load('a', {ui: false}); } catch (e) { return [e.code, e.cause && e.cause.code]; } }")
    assert out == ["dependency", "http"]
    assert srv.hits.get("/packs/a.json") is None                                             # never fetched before its need


# ----------------------------------------------------------------------------- size and integrity

def test_a_pack_listed_as_bigger_than_the_cap_is_refused_without_a_fetch(harness):
    h, srv = open_page(harness)
    srv.put("/packs/big.json", "{}")
    page = go(h)
    register(page, [dict(WET, id="big", label="Big", url="/packs/big.json", bytes=5 * 1024 * 1024)], maxBytes=1024 * 1024)
    out = page.evaluate("async () => { try { await NoyvjPacks.load('big', {ui: false}); } catch (e) { return [e.code, e.message]; } }")
    assert out[0] == "too-big" and "5.0 MB" in out[1]
    assert "/packs/big.json" not in srv.hits


def test_content_length_over_the_cap_is_refused(harness):
    h, srv = open_page(harness)
    srv.put("/packs/huge.json", json.dumps({"pad": "x" * 6000}))
    page = go(h)
    register(page, [dict(WET, id="huge", label="Huge", url="/packs/huge.json", bytes=0)], maxBytes=2000)
    out = page.evaluate("async () => { try { await NoyvjPacks.load('huge', {ui: false}); } catch (e) { return e.code; } }")
    assert out == "too-big"
    assert page.evaluate("NoyvjPacks.has('huge')") is False


def test_a_file_far_bigger_than_its_listed_size_is_refused(harness):
    h, srv = open_page(harness)
    srv.put("/packs/grown.json", json.dumps({"pad": "x" * 200000}))
    page = go(h)
    register(page, [dict(WET, id="grown", label="Grown", url="/packs/grown.json", bytes=1000)])
    out = page.evaluate("async () => { try { await NoyvjPacks.load('grown', {ui: false}); } catch (e) { return e.code; } }")
    assert out == "too-big"


def test_exact_length_empty_body_and_bad_json_are_refused(harness):
    h, srv = open_page(harness)
    srv.put("/packs/len.json", '{"a": 1}')
    srv.put("/packs/empty.json", "")
    srv.put("/packs/bad.json", "{not json")
    page = go(h)
    register(page, [dict(WET, id="len", label="Len", url="/packs/len.json", length=999),
                    dict(WET, id="exact", label="Exact", url="/packs/len.json", length=8),
                    dict(WET, id="empty", label="Empty", url="/packs/empty.json", bytes=0),
                    dict(WET, id="bad", label="Bad", url="/packs/bad.json", bytes=0)])
    out = page.evaluate("""async () => {
      const r = {};
      for (const id of ['len', 'exact', 'empty', 'bad']) {
        try { await NoyvjPacks.load(id, {ui: false}); r[id] = 'ok'; } catch (e) { r[id] = e.code; }
      }
      return r;
    }""")
    assert out == {"len": "length", "exact": "ok", "empty": "empty", "bad": "parse"}


def test_cross_origin_and_odd_urls_are_refused(harness):
    h, srv = open_page(harness)
    page = go(h)
    register(page, [dict(WET, id="evil", label="Evil", url="https://example.com/x.json"),
                    dict(WET, id="js", label="Js", url="javascript:alert(1)")])
    out = page.evaluate("""async () => {
      const r = {};
      for (const id of ['evil', 'js']) { try { await NoyvjPacks.load(id, {ui: false}); } catch (e) { r[id] = e.code; } }
      return r;
    }""")
    assert out == {"evil": "bad-url", "js": "bad-url"}


def test_malformed_manifest_entries_are_skipped_not_fatal(harness):
    h, srv = open_page(harness)
    page = go(h)
    page.evaluate("""() => NoyvjPacks.register({game: 'harness', packs: [
      null, {id: 'Bad Id', kind: 'json', url: 'x.json'}, {id: 'okid', kind: 'wasm', url: 'x'}, {id: 'nourl', kind: 'json'},
      {id: 'good', kind: 'json', url: '/packs/g.json', label: 'Good', modes: ['A', 'B'], needs: 'some text note'}]})""")
    assert page.evaluate("NoyvjPacks.list().map(p => p.id)") == ["good"]
    info = page.evaluate("NoyvjPacks.info('good')")
    assert info["modes"] == "A, B" and info["needs"] == [] and info["state"] == "idle"
    assert len(page.evaluate("NoyvjPacks.problems")) == 4


# ------------------------------------------------------------------------------------ manifest file

def test_data_manifest_attribute_reads_modules_json(harness):
    h, srv = open_page(harness, page=PAGE_MANIFEST)
    srv.put("/modules.json", json.dumps({"version": 1, "game": "harness", "packs": [
        {"id": "wetland", "label": "Wetland Forest", "kind": "json", "url": "/packs/wetland.json", "bytes": 24300, "modes": "Wetland Forest level"}]}))
    srv.put("/packs/wetland.json", '{"tiles": 4}')
    page = go(h)
    # load() right at boot, before the manifest has been read, waits for it instead of saying "unknown"
    out = page.evaluate("async () => { const v = await NoyvjPacks.load('wetland', {ui: false}); return [v.tiles, (await NoyvjPacks.ready()).ids]; }")
    assert out == [4, ["wetland"]]
    assert page.evaluate("NoyvjPacks.info('wetland').modes") == "Wetland Forest level"
    assert h.errors == []


def test_a_missing_manifest_leaves_no_packs_and_no_exceptions(harness):
    h, srv = open_page(harness, page=PAGE_MANIFEST)
    page = go(h)
    ids = page.evaluate("async () => (await NoyvjPacks.ready()).ids")
    assert ids == [] and page.evaluate("NoyvjPacks.list()") == []
    assert h.errors == []


# ----------------------------------------------------------------------------------- the record

def test_fetched_packs_are_recorded_in_local_storage_for_the_hub(harness):
    h, srv = open_page(harness)
    srv.put("/packs/wetland.json", json.dumps({"k": "v" * 100}))
    srv.put("/packs/a.json", "{}")
    page = go(h)
    register(page, [WET, dict(WET, id="a", label="A", url="/packs/a.json")])
    page.evaluate("async () => { await NoyvjPacks.load('wetland'); await NoyvjPacks.load('a'); await NoyvjPacks.load('a'); }")
    raw = json.loads(page.evaluate("localStorage.getItem('packs:harness')"))
    assert set(raw) == {"wetland", "a"}
    assert raw["wetland"]["bytes"] == len(json.dumps({"k": "v" * 100})) and raw["a"]["bytes"] == 2
    assert len(raw["a"]["at"]) == 10                                                            # a date, no time
    listed = page.evaluate("NoyvjPacks.downloaded()")
    assert [d["id"] for d in listed] == ["a", "wetland"]
    assert page.evaluate("NoyvjPacks.downloaded('other-game')") == []
    page.evaluate("localStorage.setItem('packs:tide', JSON.stringify({coast: {bytes: 5, at: '2026-10-11'}, 'BAD ID': {bytes: 1}, junk: 7}))")
    everything = page.evaluate("NoyvjPacks.downloadedAll()")
    assert set(everything) == {"harness", "tide"} and everything["tide"] == [{"id": "coast", "bytes": 5, "at": "2026-10-11"}]
    page.evaluate("NoyvjPacks.clearRecord('harness', 'a')")
    assert [d["id"] for d in page.evaluate("NoyvjPacks.downloaded()")] == ["wetland"]
    page.evaluate("NoyvjPacks.clearRecord('harness')")
    assert page.evaluate("localStorage.getItem('packs:harness')") is None


def test_a_failed_load_records_nothing_and_blocked_storage_does_not_break_loading(harness):
    h, srv = open_page(harness, init=["Storage.prototype.setItem = function () { throw new Error('blocked'); };"])
    srv.put("/packs/wetland.json", '{"ok": true}')
    srv.put("/packs/bad.json", "", status=404)
    page = go(h)
    register(page, [WET, dict(WET, id="bad", label="Bad", url="/packs/bad.json")])
    assert page.evaluate("async () => (await NoyvjPacks.load('wetland', {ui: false})).ok") is True
    page.evaluate("async () => { try { await NoyvjPacks.load('bad', {ui: false}); } catch (e) {} }")
    assert page.evaluate("NoyvjPacks.downloaded()") == []
    assert h.errors == []


# ---------------------------------------------------------------------------- the card (accessible)

def test_the_card_is_an_accessible_status_with_words_a_bar_and_progress_events(harness):
    h, srv = open_page(harness)
    srv.put("/packs/wetland.json", json.dumps({"tiles": list(range(50))}))
    srv.hold = True
    page = go(h)
    register(page, [WET])
    page.evaluate("""() => { window.__events = []; window.__p = NoyvjPacks.load('wetland', {onProgress: (e) => window.__events.push(e)});
                     window.__p.then(() => { window.__done = true; }); }""")
    page.wait_for_function("document.querySelector('.noyvj-pack-row')")
    card = page.query_selector("#noyvj-pack-card")
    assert card.get_attribute("role") == "status" and card.get_attribute("aria-live") == "polite"
    assert card_text(page).startswith("Loading Wetland Forest (about 24 KB)…")
    bar = page.query_selector(".noyvj-pack-bar")
    assert bar.evaluate("e => e.tagName") == "PROGRESS" and bar.get_attribute("aria-label") == "Wetland Forest download progress"
    assert page.query_selector(".noyvj-pack-pct").get_attribute("aria-hidden") == "true"
    # the card sits inside the window and is not a spinner-only cue
    box = card.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= 1440 and box["y"] + box["height"] <= 900
    srv.release()
    page.wait_for_function("window.__done === true")
    events = page.evaluate("window.__events")
    assert events[0]["phase"] == "fetch" and events[-1]["phase"] == "done" and events[-1]["fraction"] == 1
    assert {e["id"] for e in events} == {"wetland"}
    assert card_text(page) is None
    assert h.errors == [] and console_errors(h) == []


def test_labels_are_written_as_text_never_as_markup(harness):
    h, srv = open_page(harness)
    srv.put("/packs/wetland.json", "{}")
    srv.hold = True
    page = go(h)
    register(page, [dict(WET, label="<img src=x onerror=window.__pwned=1>Evil <b>bold</b>")])
    page.evaluate("() => { window.__p = NoyvjPacks.load('wetland') }")
    page.wait_for_selector(".noyvj-pack-row")
    assert "<img" in card_text(page)
    assert page.evaluate("document.querySelectorAll('#noyvj-pack-card img, #noyvj-pack-card b').length") == 0
    assert page.evaluate("window.__pwned") is None
    srv.release()


def test_two_packs_at_once_get_two_rows_and_both_disappear(harness):
    h, srv = open_page(harness)
    srv.put("/packs/a.json", "{}")
    srv.put("/packs/b.json", "{}")
    srv.hold = True
    page = go(h)
    register(page, [dict(WET, id="a", label="Alpha", url="/packs/a.json"), dict(WET, id="b", label="Beta", url="/packs/b.json")])
    page.evaluate("() => { Promise.all([NoyvjPacks.load('a'), NoyvjPacks.load('b')]).then(() => { window.__done = true; }); }")
    page.wait_for_function("document.querySelectorAll('.noyvj-pack-row').length === 2")
    text = card_text(page)
    assert "Alpha" in text and "Beta" in text
    srv.release()
    page.wait_for_function("window.__done === true")
    assert card_text(page) is None


def test_buttons_are_44px_and_focus_returns_to_the_game(harness):
    h, srv = open_page(harness)
    srv.put("/packs/wetland.json", '{"ok": true}')
    srv.fail["/packs/wetland.json"] = 1
    page = go(h)
    register(page, [WET])
    page.focus("#b")
    page.evaluate("() => { window.__p = NoyvjPacks.load('wetland'); window.__p.then(() => { window.__done = true; }); }")
    page.wait_for_selector(".noyvj-pack-retry")
    for sel in (".noyvj-pack-retry", ".noyvj-pack-close"):
        box = page.query_selector(sel).bounding_box()
        assert box["height"] >= 44 and box["width"] >= 44
    page.keyboard.press("Enter")                                                               # the focused Try again button
    page.wait_for_function("window.__done === true")
    assert page.evaluate("document.activeElement.id") == "b"


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_card_fits_a_360px_phone_in_both_themes(harness, theme):
    h, srv = open_page(harness, size=(360, 740))
    srv.put("/packs/wetland.json", '{"ok": true}')
    srv.fail["/packs/wetland.json"] = 1
    page = go(h, theme=theme)
    register(page, [dict(WET, label="A rather long content pack label that has to wrap onto several lines on a phone")])
    page.evaluate("() => { window.__p = NoyvjPacks.load('wetland'); window.__p.catch(() => {}); }")
    page.wait_for_selector(".noyvj-pack-retry")
    box = page.query_selector("#noyvj-pack-card").bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= 360
    assert page.evaluate("document.documentElement.scrollWidth <= 360")
    colors = page.evaluate("(() => { const s = getComputedStyle(document.getElementById('noyvj-pack-card')); return [s.backgroundColor, s.color]; })()")
    assert colors[0] != colors[1]
    if theme == "light":
        assert colors[0].startswith("rgba(255, 255, 255") or colors[0] == "rgb(255, 255, 255)"


def test_stylesheet_is_linked_by_the_script_when_the_page_forgot_it(harness):
    h, srv = open_page(harness, page=PAGE_NO_LINK)
    srv.put("/packs/wetland.json", "{}")
    page = go(h)
    register(page, [WET])
    page.wait_for_function("document.querySelectorAll('link[href*=\"lazy-packs.css\"]').length === 1")
    assert page.evaluate("document.querySelector('link[href*=\"lazy-packs.css\"]').getAttribute('href')").endswith("/shared/lazy-packs.css")
    page.evaluate("NoyvjPacks.register({game: 'harness', packs: []})")                          # registering again does not link twice
    assert page.evaluate("document.querySelectorAll('link[href*=\"lazy-packs.css\"]').length") == 1


def test_reduced_motion_page_has_no_animation_on_the_card(harness):
    h, srv = open_page(harness, media={"reduced_motion": "reduce"})
    srv.put("/packs/wetland.json", "{}")
    srv.hold = True
    page = go(h)
    register(page, [WET])
    page.evaluate("() => { window.__p = NoyvjPacks.load('wetland') }")
    page.wait_for_selector(".noyvj-pack-row")
    anim = page.evaluate("""(() => { const out = []; document.querySelectorAll('#noyvj-pack-card, #noyvj-pack-card *').forEach((e) => {
      const s = getComputedStyle(e); if (s.animationName !== 'none' || parseFloat(s.transitionDuration) > 0) out.push(e.className); }); return out; })()""")
    assert anim == []
    srv.release()


def test_the_source_has_no_timers_and_uses_text_content_only():
    src = (ROOT / "shared" / "lazy-packs.js").read_text(encoding="utf-8")
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith(("*", "/*", "//")))
    assert "setTimeout" not in code and "setInterval" not in code and "requestAnimationFrame" not in code
    assert "innerHTML" not in code and "insertAdjacentHTML" not in code and "outerHTML" not in code and "document.write" not in code
    assert "eval(" not in code and "new Function" not in code


def test_requires_soft_is_requires_with_soft_true(harness):
    h, srv = open_page(harness)
    srv.put("/packs/a.json", "{}")
    page = go(h)
    register(page, [dict(WET, id="a", label="A", url="/packs/a.json")])
    out = page.evaluate("async () => await NoyvjPacks.requiresSoft(['a', 'ghost'], {ui: false})")
    assert out["loaded"] == ["a"] and [f["id"] for f in out["failed"]] == ["ghost"]


# ------------------------------------------------------------------------ shared/lazy_packs.py (no browser)

import asyncio  # noqa: E402
import importlib.util  # noqa: E402
import types  # noqa: E402


import threading  # noqa: E402


def run_async(coroutine):
    """Run a coroutine on its own loop in a worker thread (the Playwright sync API keeps a loop running in this thread)."""
    box = {}

    def target():
        try:
            box["value"] = asyncio.run(coroutine)
        except BaseException as exc:  # noqa: BLE001
            box["error"] = exc

    thread = threading.Thread(target=target)
    thread.start()
    thread.join()
    if "error" in box:
        raise box["error"]
    return box["value"]




class FakeJsResult:
    def __init__(self, data):
        self.data = data

    def to_py(self):
        return self.data


class FakeLoader:
    def __init__(self, report=None, boom=None):
        self.report, self.boom, self.asked = report or {"loaded": [], "failed": []}, boom, []
        self.loaded = {"have"}

    def has(self, pack_id):
        return pack_id in self.loaded

    def missing(self, ids):
        return FakeJsResult([i for i in ids if i not in self.loaded])

    def used(self):
        return FakeJsResult(["have"])

    async def requiresSoft(self, ids):  # noqa: N802 -- the JS name
        self.asked.append(list(ids))
        if self.boom:
            raise RuntimeError(self.boom)
        return FakeJsResult(self.report)


@pytest.fixture
def lazy_py(monkeypatch):
    spec = importlib.util.spec_from_file_location("lazy_packs_under_test", ROOT / "shared" / "lazy_packs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    window = types.SimpleNamespace()
    monkeypatch.setitem(sys.modules, "js", types.SimpleNamespace(window=window))
    monkeypatch.setitem(sys.modules, "pyodide", types.ModuleType("pyodide"))
    monkeypatch.setitem(sys.modules, "pyodide.ffi", types.SimpleNamespace(to_js=lambda value: value))
    return mod, window


def test_python_helper_without_the_loader_never_raises(lazy_py):
    mod, window = lazy_py
    assert mod.available() is False and mod.has("x") is False and mod.used() == []
    assert mod.missing(["a", "b"]) == ["a", "b"]
    assert run_async(mod.require()) == {"ok": True, "loaded": [], "failed": [], "message": ""}
    out = run_async(mod.require("wetland"))
    assert out["ok"] is False and out["failed"][0]["code"] == "no-loader" and out["message"]


def test_python_helper_reports_loaded_and_failed_packs_in_plain_words(lazy_py):
    mod, window = lazy_py
    window.NoyvjPacks = FakeLoader({"loaded": ["a"], "failed": [{"id": "b", "code": "offline", "message": "You are offline."},
                                                                 {"id": "c", "code": "unknown", "message": "No pack c."}]})
    assert mod.available() and mod.has("have") and not mod.has("a")
    assert mod.missing(["have", "a"]) == ["a"] and mod.used() == ["have"]
    out = run_async(mod.require("a", "b", "c", ""))
    assert window.NoyvjPacks.asked == [["a", "b", "c"]]                                          # blanks dropped
    assert out["ok"] is False and out["loaded"] == ["a"] and [f["id"] for f in out["failed"]] == ["b", "c"]
    assert out["message"] == "You are offline. No pack c."
    window.NoyvjPacks = FakeLoader({"loaded": ["a"], "failed": []})
    assert run_async(mod.require("a"))["ok"] is True


def test_python_helper_turns_a_loader_exception_into_a_result(lazy_py):
    mod, window = lazy_py
    window.NoyvjPacks = FakeLoader(boom="kaput")
    out = run_async(mod.require("a", "b"))
    assert out["ok"] is False and [f["code"] for f in out["failed"]] == ["error", "error"] and "kaput" in out["message"]


def test_python_helper_spawn_and_import_pack(lazy_py, tmp_path, monkeypatch):
    mod, _window = lazy_py
    (tmp_path / "pack_written_later.py").write_text("VALUE = 42\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    assert mod.import_pack("pack_written_later").VALUE == 42
    ran = []

    async def work():
        ran.append(1)
        return "done"

    async def main():
        return await mod.spawn(work())

    assert run_async(main()) == "done" and ran == [1]
