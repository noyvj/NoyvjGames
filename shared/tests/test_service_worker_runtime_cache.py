"""sw.js caches the versioned Pyodide/Three.js CDN files (TODO Z-12): cache-first in a cache of its own,
bounded, never the backend, and it survives a SW_VERSION bump.

sw.js is run inside a headless Chromium page against fake `self`, `caches` and `fetch` objects (an
in-memory cache that behaves like the Cache API for the calls sw.js makes), so nothing touches the network."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SW = (ROOT / "sw.js").read_text(encoding="utf-8")
PYO = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/"
LIVE = "site-cache-v" + re.search(r"SW_VERSION = (\d+)", SW).group(1)

HARNESS = """
async (src) => {
  const log = { fetches: [] };
  const stores = new Map();
  const key = (r) => (typeof r === "string" ? r : r.url);
  const makeCache = (name) => {
    if (!stores.has(name)) stores.set(name, new Map());
    const m = stores.get(name);
    return {
      match: async (r) => { const v = m.get(key(r)); return v ? v.clone() : undefined; },
      put: async (r, v) => { m.delete(key(r)); m.set(key(r), v); },
      delete: async (r) => m.delete(key(r)),
      keys: async () => [...m.keys()].map((u) => ({ url: u })),
      addAll: async () => {},
    };
  };
  const fakeCaches = {
    open: async (n) => makeCache(n),
    keys: async () => [...stores.keys()],
    delete: async (n) => stores.delete(n),
  };
  const handlers = {};
  const fakeSelf = {
    location: new URL("https://site.test/sw.js"),
    addEventListener: (t, f) => { handlers[t] = f; },
    skipWaiting: () => {},
    clients: { claim: async () => {} },
  };
  let offline = false;
  const responder = { size: null };
  const fakeFetch = async (req, opts) => {
    const url = typeof req === "string" ? req : req.url;
    log.fetches.push({ url, mode: opts && opts.mode });
    if (offline) throw new TypeError("offline");
    const headers = responder.size ? { "content-length": String(responder.size) } : {};
    return new Response("body of " + url, { status: 200, headers });
  };
  new Function("self", "caches", "fetch", "setTimeout", src)(fakeSelf, fakeCaches, fakeFetch, setTimeout);
  const send = async (url, init) => {
    const request = new Request(url, init);
    let responded = null; let waits = [];
    handlers.fetch({
      request,
      respondWith: (p) => { responded = Promise.resolve(p); },
      waitUntil: (p) => waits.push(p),
    });
    if (!responded) return { handled: false };
    let text = null; let failed = false;
    try { text = await (await responded).text(); } catch (e) { failed = true; }
    await Promise.all(waits);
    return { handled: true, text, failed };
  };
  const lifecycle = async (type) => { const w = []; handlers[type]({ waitUntil: (p) => w.push(p) }); await Promise.all(w); };
  const out = await (new Function("send", "lifecycle", "log", "stores", "setOffline", "responder", "return (" + window.__scenario + ")(send, lifecycle, log, stores, setOffline, responder)"))(
    send, lifecycle, log, stores, (v) => { offline = v; }, responder);
  return out;
}
"""


@pytest.fixture(scope="module")
def page(chromium):
    pg = chromium.new_page()
    yield pg
    pg.close()


def run(page, scenario):
    page.evaluate("(s) => { window.__scenario = s; }", scenario)
    return page.evaluate(HARNESS, SW)


def test_second_request_for_a_pyodide_file_never_touches_the_network(page):
    out = run(page, """async (send, lifecycle, log, stores) => {
      const url = '%spyodide.asm.wasm';
      const first = await send(url); const n = log.fetches.length;
      const second = await send(url, { mode: 'no-cors' });
      return { first, second, fetchesAfterFirst: n, fetchesAfterSecond: log.fetches.length,
               mode: log.fetches[0].mode, cacheNames: [...stores.keys()], size: stores.get('runtime-cdn-cache-v1').size };
    }""" % PYO)
    assert out["first"]["text"] == out["second"]["text"] == "body of " + PYO + "pyodide.asm.wasm"
    assert out["fetchesAfterFirst"] == 1 and out["fetchesAfterSecond"] == 1
    assert out["mode"] == "cors"          # readable response, not an opaque one
    assert "runtime-cdn-cache-v1" in out["cacheNames"] and out["size"] == 1


def test_offline_repeat_visit_is_served_from_the_cache_and_unseen_files_fail_like_the_browser(page):
    out = run(page, """async (send, lifecycle, log, stores, setOffline) => {
      await send('%spython_stdlib.zip'); setOffline(true);
      return { cached: await send('%spython_stdlib.zip'), missing: await send('%spyodide-lock.json') };
    }""" % (PYO, PYO, PYO))
    assert out["cached"]["text"] == "body of " + PYO + "python_stdlib.zip"
    assert out["missing"]["failed"] is True


def test_files_from_download_for_offline_in_the_live_cache_are_found(page):
    out = run(page, """async (send, lifecycle, log, stores, setOffline) => {
      const c = await caches_open(stores, '%s');
      c.set('%spyodide.asm.js', new Response('offline copy'));
      setOffline(true);
      return await send('%spyodide.asm.js');
      function caches_open(s, n) { if (!s.has(n)) s.set(n, new Map()); return s.get(n); }
    }""" % (LIVE, PYO, PYO))
    assert out["text"] == "offline copy"


@pytest.mark.parametrize("url", [
    "https://noyvjgames.fastapicloud.dev/saves/abc",
    "https://cdn.jsdelivr.net/pyodide/latest/full/pyodide.js",
    "https://cdn.jsdelivr.net/npm/three@latest/build/three.min.js",
    "https://cdn.jsdelivr.net/npm/three@0/build/three.min.js".replace("@0/", "@0.x/"),
    "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js?cachebust=1",
    "https://cdn.jsdelivr.net/gh/someone/repo@1.0.0/file.js",
    "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js",
    "http://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js",
])
def test_only_exact_versioned_jsdelivr_files_use_the_runtime_cache(page, url):
    out = run(page, """async (send, lifecycle, log, stores) => {
      await send('%s'); return { names: [...stores.keys()], runtime: stores.has('runtime-cdn-cache-v1') ? stores.get('runtime-cdn-cache-v1').size : 0 };
    }""" % url)
    assert out["runtime"] == 0


def test_versioned_three_js_is_cached_and_the_backend_is_left_alone(page):
    out = run(page, """async (send, lifecycle, log, stores) => {
      await send('https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js');
      const api = await send('https://noyvjgames.fastapicloud.dev/saves/abc');
      return { three: [...stores.get('runtime-cdn-cache-v1').keys()], api, fetched: log.fetches.map(f => f.url) };
    }""")
    assert out["three"] == ["https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"]
    assert out["api"] == {"handled": False}
    assert not any("fastapicloud" in u for u in out["fetched"])


def test_cache_is_bounded_oldest_first_and_huge_files_are_not_stored(page):
    out = run(page, """async (send, lifecycle, log, stores, setOffline, responder) => {
      for (let i = 0; i < 30; i++) await send('https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pkg' + i + '.whl');
      const keys = [...stores.get('runtime-cdn-cache-v1').keys()];
      responder.size = 25 * 1024 * 1024;
      await send('https://cdn.jsdelivr.net/pyodide/v0.26.4/full/huge.whl');
      return { count: keys.length, first: keys[0], last: keys[keys.length - 1],
               huge: stores.get('runtime-cdn-cache-v1').has('https://cdn.jsdelivr.net/pyodide/v0.26.4/full/huge.whl') };
    }""")
    assert out["count"] == 24
    assert out["first"].endswith("pkg6.whl") and out["last"].endswith("pkg29.whl")
    assert out["huge"] is False


def test_a_version_bump_keeps_the_runtime_cache_and_drops_other_old_caches(page):
    out = run(page, """async (send, lifecycle, log, stores) => {
      await send('%spyodide.js');
      stores.set('site-cache-v1', new Map()); stores.set('%s', new Map()); stores.set('stray', new Map());
      await lifecycle('activate');
      return [...stores.keys()].sort();
    }""" % (PYO, LIVE))
    assert "runtime-cdn-cache-v1" in out and LIVE in out
    assert "site-cache-v1" not in out and "stray" not in out


def test_same_origin_pages_still_go_to_the_network_first_path(page):
    out = run(page, """async (send, lifecycle, log) => {
      const r = await send('https://site.test/games/sol/index.html');
      return { r, fetched: log.fetches.map(f => f.url) };
    }""")
    assert out["r"]["handled"] is True and out["r"]["text"].startswith("body of https://site.test/games/sol")


def test_source_has_a_versioned_runtime_cache_and_no_api_caching():
    assert re.search(r'const RUNTIME_CACHE = "runtime-cdn-cache-v\d+";', SW)
    assert "url.origin === API_ORIGIN" in SW and SW.index("url.origin === API_ORIGIN") < SW.index("respondWith(runtimeResponse(event))")
