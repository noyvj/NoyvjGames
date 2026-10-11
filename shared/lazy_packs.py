"""Python side of the lazy content-pack loader (planning/TODO.md LZ-2). The loader itself is shared/lazy-packs.js
(window.NoyvjPacks); this module is the few lines a game's Python needs to use it, because a Python event
handler cannot simply wait for a JavaScript promise. Written into Pyodide's file system like info_page.py:

    import lazy_packs

    async def open_wetland(event=None):
        result = await lazy_packs.require("wetland")      # shows the loading card, fetches once, writes the file
        if not result["ok"]:
            show_notice(result["message"])                 # plain words; the save and the screen are untouched
            return
        wetland = lazy_packs.import_pack("wetland")        # importlib after the file is in place
        wetland.start()

    def on_open_wetland_click(event):                      # the DOM handler stays a normal function
        lazy_packs.spawn(open_wetland(event))

Saving: put `lazy_packs.used()` in the game's state as "packs_used"; when loading a save, `await
lazy_packs.require(*state.get("packs_used", []))` BEFORE restoring and carry on with whatever failed listed in
result["failed"]. Nothing here ever deletes or rewrites a save.

Everything imports js / pyodide lazily, so the module can be imported (and tested) outside Pyodide.
"""


def _window():
    from js import window  # noqa: PLC0415 -- Pyodide only

    return window


def _loader():
    return getattr(_window(), "NoyvjPacks", None)


def _to_py(value):
    return value.to_py() if hasattr(value, "to_py") else value


def _to_js_list(ids):
    from pyodide.ffi import to_js  # noqa: PLC0415 -- Pyodide only

    return to_js([str(i) for i in ids])


def available():
    """True when the page loaded shared/lazy-packs.js."""
    return _loader() is not None


def has(pack_id):
    """True once the pack has finished loading on this page."""
    loader = _loader()
    return bool(loader is not None and loader.has(pack_id))


def missing(ids):
    """Those of the ids that are not loaded yet (unknown ids included)."""
    ids = [str(i) for i in ids]
    loader = _loader()
    if loader is None:
        return ids
    return list(_to_py(loader.missing(_to_js_list(ids))))


def used():
    """Ids loaded on this page, in load order: store as the state's "packs_used"."""
    loader = _loader()
    return [] if loader is None else list(_to_py(loader.used()))


async def require(*ids):
    """Load every pack in ids that is not loaded yet, behind the loader's card. Never raises: returns
    {"ok": bool, "loaded": [ids], "failed": [{"id", "code", "message"}], "message": str}. `message` joins the
    plain failure messages (empty when ok)."""
    wanted = [str(i) for i in ids if i]
    loader = _loader()
    if not wanted:
        return {"ok": True, "loaded": [], "failed": [], "message": ""}
    if loader is None:
        failed = [{"id": i, "code": "no-loader", "message": "The content loader is not on this page."} for i in wanted]
        return {"ok": False, "loaded": [], "failed": failed, "message": failed[0]["message"]}
    try:
        report = _to_py(await loader.requiresSoft(_to_js_list(wanted)))
    except Exception as exc:  # a JsException from the loader itself; the contract is "never raises"
        failed = [{"id": i, "code": "error", "message": str(exc)} for i in wanted]
        return {"ok": False, "loaded": [], "failed": failed, "message": failed[0]["message"]}
    failed = [dict(f) for f in report.get("failed", [])]
    return {
        "ok": not failed,
        "loaded": list(report.get("loaded", [])),
        "failed": failed,
        "message": " ".join(f.get("message", "") for f in failed).strip(),
    }


def import_pack(module_name):
    """Import a module that a python pack wrote into the file system (call after require() said ok)."""
    import importlib  # noqa: PLC0415

    importlib.invalidate_caches()
    return importlib.import_module(module_name)


def spawn(coroutine):
    """Run a coroutine from a normal (synchronous) event handler. Pyodide's event loop schedules it."""
    import asyncio  # noqa: PLC0415

    return asyncio.ensure_future(coroutine)
