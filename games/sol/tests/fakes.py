"""Minimal fake DOM + Pyodide shims so game.py can run under plain CPython/pytest.

game.py is written for Pyodide (imports `js` and `pyodide.ffi`), which only
exist inside a browser WASM runtime. These fakes stand in for just enough of
that surface (document/getElementById/classList/addEventListener/setTimeout,
create_proxy) to exercise the game logic headlessly.

`className`/`children`/`innerHTML`/`appendChild`/`document.createElement`
were added for the achievements panel (ACHIEVEMENTS-SYSTEM-DESIGN.md), the
first thing in this game to build DOM nodes dynamically from Python rather
than only writing text/attributes onto elements index.html already declares.
Same shape as Le Champ de Mots' own `tests/fakes.py`, which needed the same
capability first for its farm grid and achievements panel.
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
    def __init__(self, id_=None):
        self.id = id_
        self.innerText = ""
        self._innerHTML = ""
        self.disabled = False
        self.hidden = False
        self.className = ""
        self.classList = FakeClassList()
        self.style = FakeStyle()
        self.children = []
        self._listeners = {}
        self._attrs = {}
        self.value = ""
        self.title = ""
        self.type = ""

    @property
    def innerHTML(self):
        return self._innerHTML

    @innerHTML.setter
    def innerHTML(self, value):
        # Only ever set to "" by game.py (clear-before-rebuild, same as a
        # real panel.innerHTML = "" before repainting) — dropping the
        # previously-appended children is the only behaviour that matters
        # here, not actually parsing markup.
        self._innerHTML = value
        self.children = []

    def appendChild(self, child):
        self.children.append(child)
        return child

    def setAttribute(self, name, value):
        self._attrs[name] = value

    def getAttribute(self, name):
        return self._attrs.get(name)

    def removeChild(self, child):
        if child in self.children:
            self.children.remove(child)
        return child

    def addEventListener(self, event_name, handler):
        self._listeners.setdefault(event_name, []).append(handler)

    def dispatch(self, event_name, event=None):
        for handler in list(self._listeners.get(event_name, [])):
            handler(event)

    def descendants(self):
        """Depth-first walk of everything appended under this element."""
        for child in self.children:
            yield child
            yield from child.descendants()


class FakeDocument:
    def __init__(self, elements):
        self._elements = elements

    def getElementById(self, id_):
        return self._elements[id_]

    def createElement(self, tag):
        element = FakeElement()
        element.tagName = tag.upper()
        return element


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


class FakeLocalStorage:
    """Stands in for the real browser `window.localStorage` (V-CD-4's
    welcome-back-toast delta reads/writes it via Pyodide's `js` module, the
    same per-browser-record-outside-the-save pattern as Canopy's
    personal_best/Tide's best_coastline_saved). Plain in-memory dict --
    persistence across real browser sessions is exactly the one thing this
    fake deliberately does NOT need to emulate; each test gets a fresh
    instance via a fresh game_env fixture, same as every other piece of
    fake browser state."""

    def __init__(self):
        self._store = {}

    def getItem(self, key):
        return self._store.get(key)

    def setItem(self, key, value):
        self._store[key] = str(value)

    def removeItem(self, key):
        self._store.pop(key, None)
