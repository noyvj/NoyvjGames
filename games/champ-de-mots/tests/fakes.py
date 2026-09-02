"""Minimal fake DOM + Pyodide shims so game.py can run under plain CPython/pytest.

Same harness pattern as the rest of the hub's games (see games/grid/tests/fakes.py):
game.py is written for Pyodide (imports `js` and `pyodide.ffi`), which only exist
inside a browser WASM runtime, so these fakes stand in for just enough of that
surface to exercise the game logic headlessly.

Two small additions over Grid's copy, both driven by what this game's UI actually
needs: `value` (the typed-answer input box) and `setAttribute`/`getAttribute`
(plot cells carry an `aria-label` mirroring their tooltip, so the sprite's
meaning reaches a screen reader as well as the eye).
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
        self.value = ""
        self.disabled = False
        self.hidden = False
        self.title = ""
        self.className = ""
        self.classList = FakeClassList()
        self.style = FakeStyle()
        self.children = []
        self.attributes = {}
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

    def setAttribute(self, name, value):
        self.attributes[name] = value

    def getAttribute(self, name):
        return self.attributes.get(name)

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
        element = FakeElement(registry=self._elements)
        element.tagName = tag.upper()
        return element


class FakeProxy:
    """Stands in for a Pyodide `JsProxy` returned by `create_proxy`.

    Real proxies leak (they pin the wrapped Python callable in memory) until
    `.destroy()` is called, and calling a destroyed one raises. Both of those
    are the behaviours the game's own leak-prevention code needs to be able
    to exercise from a plain-CPython test.
    """

    def __init__(self, func):
        self._func = func
        self.destroyed = False

    def __call__(self, *args, **kwargs):
        if self.destroyed:
            raise RuntimeError("Object has already been destroyed")
        return self._func(*args, **kwargs)

    def destroy(self):
        self.destroyed = True


def create_proxy(func):
    return FakeProxy(func)
