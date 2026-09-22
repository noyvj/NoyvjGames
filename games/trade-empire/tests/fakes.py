"""Minimal fake DOM + Pyodide shims so game.py can run under plain CPython/pytest.

Copied from Canopy's version of this file (same Pyodide-shim needs: document/
getElementById/addEventListener/setTimeout/setInterval, create_proxy) — Trade
Empire's index.html is otherwise fully static; the createElement/registry/
remove() machinery below exists for J22's dynamically-created sale-spark
burst (game.py's _spark_burst_high_value_sale()), the one place this game
creates and later removes its own transient elements.
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

    def closePath(self):
        self.calls.append(("closePath", ()))

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
        self._innerText = ""
        self._innerHTML = ""
        self.disabled = False
        self.hidden = False
        self.title = ""
        self.value = ""  # J10: stands in for a text <input>'s .value
        self.className = ""
        self.classList = FakeClassList()
        self.style = FakeStyle()
        # Z27b: element.dataset.achievementId support, plain attribute bag
        # (same shape as .style -- real dataset lowercases/hyphenates keys,
        # but game.py only ever sets one plain attribute, so that's not
        # needed here).
        self.dataset = FakeStyle()
        self.children = []
        self._parent = None
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

    @property
    def innerText(self):
        return self._innerText

    @innerText.setter
    def innerText(self, value):
        """Real DOM: assigning .innerText replaces all of an element's
        child nodes with a single text node, same as .innerHTML. J22's
        live-browser verification found a real bug this fake previously
        couldn't catch -- a plain innerText attribute here let a test
        believe elements appended as children survived a subsequent
        innerText assignment on the same element, when in a real browser
        they don't. Clearing .children here keeps this fake honest about
        that."""
        self._innerText = value
        self.children = []

    def createElement(self, tag):
        return FakeElement(registry=self._registry)

    def getContext(self, kind):
        if not hasattr(self, "_context"):
            self._context = FakeCanvasContext()
        return self._context

    def appendChild(self, child):
        self.children.append(child)
        child._parent = self
        return child

    def remove(self):
        """Stands in for real DOM Element.remove() -- detaches self from
        whichever parent's .children list it was appended to. Added for
        J22's spark burst, which creates and later removes its own
        transient elements."""
        if self._parent is not None:
            try:
                self._parent.children.remove(self)
            except ValueError:
                pass
            self._parent = None

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


class FakeProxy:
    """Stands in for pyodide.ffi.create_proxy()'s JsProxy: callable just like
    the wrapped function, but also exposes `.destroy()` so game code that
    manages a one-shot proxy's lifetime (e.g. the achievement toast's
    setTimeout hide callback) can be exercised under test the same way it
    behaves against real Pyodide. Copied from SOL's own fakes.py, which
    established this pattern first."""

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
    return FakeProxy(func)
