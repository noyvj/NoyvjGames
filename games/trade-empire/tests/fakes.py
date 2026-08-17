"""Minimal fake DOM + Pyodide shims so game.py can run under plain CPython/pytest.

Copied from Canopy's version of this file (same Pyodide-shim needs: document/
getElementById/addEventListener/setTimeout/setInterval, create_proxy) — Trade
Empire's index.html is fully static (no dynamically created elements), so the
createElement/registry machinery isn't needed here, but is kept for parity
and in case a later milestone (e.g. the map) needs it.
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


class FakeCanvasContext:
    """Records every draw call instead of actually rendering anything —
    enough for Milestone 7's map tests to assert on what would have
    been drawn (which nodes, which edges) without a real canvas."""

    def __init__(self):
        self.calls = []
        self.fillStyle = None
        self.strokeStyle = None
        self.lineWidth = None
        self.font = None
        self.textAlign = None
        self.textBaseline = None

    def clearRect(self, *args):
        self.calls.append(("clearRect", args))

    def beginPath(self):
        self.calls.append(("beginPath", ()))

    def moveTo(self, x, y):
        self.calls.append(("moveTo", (x, y)))

    def lineTo(self, x, y):
        self.calls.append(("lineTo", (x, y)))

    def stroke(self):
        self.calls.append(("stroke", ()))

    def arc(self, *args):
        self.calls.append(("arc", args))

    def fill(self):
        self.calls.append(("fill", ()))

    def fillText(self, text, x, y):
        self.calls.append(("fillText", (text, x, y)))


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
        self._innerHTML = value
        self.children = []

    def createElement(self, tag):
        return FakeElement(registry=self._registry)

    def getContext(self, kind):
        if not hasattr(self, "_context"):
            self._context = FakeCanvasContext()
        return self._context

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
    real clock, so tests can step the tick loop deterministically."""

    def __init__(self):
        self.pending = []
        self.intervals = []

    def setTimeout(self, callback, delay):
        self.pending.append((callback, delay))
        return len(self.pending)

    def setInterval(self, callback, delay):
        self.intervals.append((callback, delay))
        return len(self.intervals)

    def flush(self):
        pending, self.pending = self.pending, []
        for callback, _delay in pending:
            callback()

    def tick_intervals(self, times=1):
        for _ in range(times):
            for callback, _delay in self.intervals:
                callback()


def create_proxy(func):
    return func
