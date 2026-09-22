"""Minimal fake DOM + Pyodide shims so game.py can run under plain CPython/pytest.

game.py is written for Pyodide (imports `js` and `pyodide.ffi`), which only
exist inside a browser WASM runtime. These fakes stand in for just enough
of that surface (document.getElementById, createElement/appendChild,
addEventListener, create_proxy) to exercise the game logic headlessly.
"""


class FakeClassList:
    def __init__(self):
        self._classes = set()

    def add(self, cls):
        self._classes.add(cls)

    def remove(self, cls):
        self._classes.discard(cls)

    def contains(self, cls):
        return cls in self._classes

    def __contains__(self, cls):
        return cls in self._classes


class FakeStyle:
    """Arbitrary attribute bag standing in for element.style (e.g. .width)."""


class FakeElement:
    def __init__(self, id_=None, registry=None):
        self._id = id_
        self._registry = registry
        self.innerText = ""
        self._innerHTML = ""
        self.disabled = False
        self.hidden = False
        self.title = ""
        self.value = ""
        self.className = ""
        self.classList = FakeClassList()
        self.style = FakeStyle()
        # Z27b: element.dataset.achievementId support, plain attribute bag
        # (same shape as .style -- real dataset lowercases/hyphenates keys,
        # but game.py only ever sets one plain attribute, so that's not
        # needed here).
        self.dataset = FakeStyle()
        self.children = []
        self._listeners = {}
        if id_ is not None and registry is not None:
            registry[id_] = self

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value
        if self._registry is not None:
            self._registry[value] = self

    @property
    def innerHTML(self):
        return self._innerHTML

    @innerHTML.setter
    def innerHTML(self, value):
        self._innerHTML = value
        self.children = []

    def appendChild(self, child):
        self.children.append(child)
        return child

    def addEventListener(self, event_name, handler):
        self._listeners.setdefault(event_name, []).append(handler)

    def dispatch(self, event_name, event=None):
        for handler in list(self._listeners.get(event_name, [])):
            handler(event)


class FakeDocument:
    def __init__(self, elements):
        self._elements = elements

    def getElementById(self, id_):
        return self._elements.get(id_)

    def createElement(self, tag):
        return FakeElement(registry=self._elements)


class FakeTimers:
    """Collects setTimeout callbacks instead of running them on a real
    clock, so tests can assert on pre/post-flush state (e.g. the
    achievement toast hiding itself after ACHIEVEMENT_TOAST_DURATION_MS)
    without an actual wall-clock delay."""

    def __init__(self):
        self.pending = []  # one-shot setTimeout calls

    def setTimeout(self, callback, delay):
        self.pending.append((callback, delay))
        return len(self.pending)

    def flush(self):
        """Runs and clears all pending one-shot setTimeout callbacks."""
        pending, self.pending = self.pending, []
        for callback, _delay in pending:
            callback()


class FakeJsProxy:
    """Stands in for the real pyodide.ffi.create_proxy() return value: a
    callable wrapper with a `.destroy()` a caller can invoke once the
    proxy is no longer needed (show_achievement_toast() destroys its own
    previous setTimeout proxy before creating a new one). Tracks
    `destroyed` so tests can assert cleanup actually happened rather than
    just not crashing."""

    def __init__(self, func):
        self._func = func
        self.destroyed = False

    def __call__(self, *args, **kwargs):
        # Real Pyodide throws when a destroyed proxy is invoked (a pending
        # setTimeout firing after its proxy was destroyed).
        if self.destroyed:
            raise RuntimeError("Object has already been destroyed")
        return self._func(*args, **kwargs)

    def destroy(self):
        self.destroyed = True


def create_proxy(func):
    return FakeJsProxy(func)
