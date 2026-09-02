"""Minimal fake DOM + Pyodide shims so game.py can run under plain CPython/pytest.

Same pattern as every other game in the hub (Grid/Tide/Canopy): game.py is
written for Pyodide (it imports `js` and `pyodide.ffi`), which only exist
inside a browser WASM runtime, so these fakes stand in for just enough of
that surface — getElementById, createElement/appendChild, addEventListener,
create_proxy — to exercise the game logic headlessly.

Continuum leans on the dynamic half of that surface more than Grid did:
the research tree renders its node rows at runtime (a node list that grows
across seven eras can't be static HTML), so created elements register
themselves under whatever id they're later given, which is how tests reach
a research button by id and dispatch a click on it.
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


def create_proxy(func):
    """Stands in for `pyodide.ffi.create_proxy`.

    The real one wraps a Python callable in a JsProxy that JS can hold and
    call, and which must be explicitly `.destroy()`-ed once it's no longer
    needed — Pyodide doesn't garbage-collect it on its own. This fake keeps
    the exact same "returns something callable" contract every other test
    already relies on, but attaches `.destroy()`/`.destroyed` directly onto
    the function object so a test can assert that game.py actually destroys
    a proxy it's replacing, rather than leaking it.
    """
    func.destroyed = False

    def _destroy():
        func.destroyed = True

    func.destroy = _destroy
    return func
