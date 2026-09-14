"""Minimal fake DOM + Pyodide shims so game.py can run under plain CPython/pytest.

game.py is written for Pyodide (imports `js` and `pyodide.ffi`), which only
exist inside a browser WASM runtime. These fakes stand in for just enough
of that surface (document.getElementById/createElement/appendChild,
addEventListener, localStorage, create_proxy) to exercise the game logic
headlessly.
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
        # Stand-ins for <input>/<textarea> DOM properties (used by E12's
        # progress-code import textarea and E18's extended-run checkbox).
        self.value = ""
        self.checked = False
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


class FakeLocalStorage:
    """In-memory stand-in for window.localStorage — a plain string->string
    dict, same interface (getItem/setItem/removeItem)."""

    def __init__(self):
        self._data = {}

    def getItem(self, key):
        return self._data.get(key)

    def setItem(self, key, value):
        self._data[key] = value

    def removeItem(self, key):
        self._data.pop(key, None)


class FakeProxy:
    """Stands in for pyodide.ffi.create_proxy()'s JsProxy: callable just
    like the wrapped function, but also exposes `.destroy()` so game code
    that manages a one-shot proxy's lifetime (e.g. the achievement toast's
    setTimeout callback) can be exercised under test the same way it
    behaves against real Pyodide. Existing callers that just invoke a
    dispatched handler directly (FakeElement.dispatch) keep working
    unchanged, since a FakeProxy is still plainly callable. Same shape as
    Grid/Canopy's own tests/fakes.py FakeProxy."""

    def __init__(self, func):
        self._func = func
        self.destroyed = False

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)

    def destroy(self):
        self.destroyed = True


def create_proxy(func):
    return FakeProxy(func)


class FakeTimers:
    """Collects setTimeout calls instead of running them on a real clock, so
    tests can assert on pre/post-flush state (used by the achievement-unlock
    toast's auto-hide timer). Same shape as Grid's tests/fakes.py FakeTimers."""

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
