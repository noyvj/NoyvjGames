"""Minimal fake DOM + Pyodide shims so game.py can run under plain CPython/pytest.

game.py is written for Pyodide (imports `js` and `pyodide.ffi`), which only
exist inside a browser WASM runtime. These fakes stand in for just enough of
that surface (document/getElementById/classList/addEventListener/setTimeout,
create_proxy) to exercise the game logic headlessly.
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
    def __init__(self, id_):
        self.id = id_
        self.innerText = ""
        self.disabled = False
        self.hidden = False
        self.classList = FakeClassList()
        self.style = FakeStyle()
        self._listeners = {}

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


class FakeProxy:
    """Stands in for pyodide.ffi.create_proxy()'s JsProxy: callable just like
    the wrapped function, but also exposes `.destroy()` so game code that
    manages a one-shot proxy's lifetime (e.g. a setTimeout callback) can be
    exercised under test the same way it behaves against real Pyodide."""

    def __init__(self, func):
        self._func = func
        self.destroyed = False

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)

    def destroy(self):
        self.destroyed = True


def create_proxy(func):
    return FakeProxy(func)
