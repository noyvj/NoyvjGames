"""Minimal fake DOM + Pyodide shims so game.py can run under plain CPython/pytest.

game.py is written for Pyodide (imports `js` and `pyodide.ffi`), which only
exist inside a browser WASM runtime. These fakes stand in for just enough of
that surface (document/getElementById/createElement/appendChild/classList/
addEventListener/setTimeout, create_proxy) to exercise the game logic
headlessly.

Extended from SOL's version of this file: Canopy renders its plot grid by
creating DOM elements from Python at runtime (`document.createElement`)
rather than reading a fully static index.html, so this fake also tracks a
document-wide id registry that dynamically-created elements register into
as soon as `.id` is assigned — mirroring how a real re-render makes a
freshly created element reachable via getElementById.
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
        self.className = ""
        self.classList = FakeClassList()
        self.style = FakeStyle()
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
        # Real assignment to innerHTML discards existing child nodes —
        # mirror that so a render-loop's `grid_el.innerHTML = ""` actually
        # clears out the previous render's tiles.
        self._innerHTML = value
        self.children = []

    def createElement(self, tag):
        # Convenience so a FakeElement can stand in for `document` too, if
        # ever needed; unused by the current game.py (which calls
        # document.createElement), kept for parity/flexibility.
        return FakeElement(registry=self._registry)

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
        return self._elements[id_]

    def createElement(self, tag):
        return FakeElement(registry=self._elements)


class FakeTimers:
    """Collects setTimeout/setInterval callbacks instead of running them on a
    real clock, so tests can assert on pre/post-flush state, on the
    requested delay, and step the passive-production loop deterministically."""

    def __init__(self):
        self.pending = []  # one-shot setTimeout calls
        self.intervals = []  # (callback, delay) repeating setInterval calls

    def setTimeout(self, callback, delay):
        self.pending.append((callback, delay))
        return len(self.pending)

    def setInterval(self, callback, delay):
        self.intervals.append((callback, delay))
        return len(self.intervals)

    def flush(self):
        """Runs and clears all pending one-shot setTimeout callbacks."""
        pending, self.pending = self.pending, []
        for callback, _delay in pending:
            callback()

    def tick_intervals(self, times=1):
        """Manually fires every registered setInterval callback `times` times."""
        for _ in range(times):
            for callback, _delay in self.intervals:
                callback()


def create_proxy(func):
    return func
