"""Minimal fake DOM + Pyodide shims so game.py can run under plain CPython/pytest.

game.py is written for Pyodide (imports `js` and `pyodide.ffi`), which only
exist inside a browser WASM runtime. These fakes stand in for just enough
of that surface (document.getElementById/createElement/appendChild,
setAttribute, addEventListener, create_proxy, js.confirm) to exercise the
game logic headlessly. Modeled on the same shape as every other game's
tests/fakes.py in this hub (see e.g. games/drift/tests/fakes.py), trimmed
to what this simpler, non-ticking tracker actually touches -- notably no
querySelector, since every event handler in game.py closes directly over
the element references render() already has in hand, rather than
re-querying the DOM by attribute selector.
"""


class FakeClassList:
    def __init__(self, element):
        self._element = element
        self._classes = set()

    def add(self, cls):
        self._classes.add(cls)
        self._element.className = " ".join(sorted(self._classes))

    def remove(self, cls):
        self._classes.discard(cls)
        self._element.className = " ".join(sorted(self._classes))

    def contains(self, cls):
        return cls in self._classes

    def __contains__(self, cls):
        return cls in self._classes


class FakeStyle:
    """Arbitrary attribute bag standing in for element.style (e.g. .width)."""


class FakeElement:
    def __init__(self, tag="div", registry=None):
        self.tag = tag
        self._registry = registry
        self._id = None
        self._textContent = ""
        self._innerHTML = ""
        self.value = ""
        self.disabled = False
        self.hidden = False
        self.className = ""
        self.classList = FakeClassList(self)
        self.style = FakeStyle()
        self.children = []
        self.attributes = {}
        self._listeners = {}

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value
        if self._registry is not None:
            self._registry[value] = self

    @property
    def textContent(self):
        return self._textContent

    @textContent.setter
    def textContent(self, value):
        self._textContent = value
        self.children = []

    @property
    def innerHTML(self):
        return self._innerHTML

    @innerHTML.setter
    def innerHTML(self, value):
        self._innerHTML = value
        self.children = []

    def setAttribute(self, name, value):
        self.attributes[name] = value
        if name == "id":
            self.id = value
        elif name == "class":
            self.className = value
        elif name == "value":
            self.value = value
        elif name == "disabled":
            self.disabled = True

    def getAttribute(self, name):
        return self.attributes.get(name)

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
        return FakeElement(tag=tag, registry=self._elements)


class FakeProxy:
    """Stands in for pyodide.ffi.create_proxy()'s JsProxy: callable just
    like the wrapped function, but also exposes `.destroy()` so game code
    that manages a proxy's lifetime (render()'s per-row change/build
    handlers) can be exercised under test the same way it behaves against
    real Pyodide."""

    def __init__(self, func):
        self._func = func
        self.destroyed = False

    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)

    def destroy(self):
        self.destroyed = True


def create_proxy(func):
    return FakeProxy(func)


class FakeConfirm:
    """Stands in for js.confirm() -- a real browser confirm() dialog blocks
    and returns a bool. Tests set `.next_result` before triggering an
    action that calls confirm(), and can inspect `.last_message` to assert
    on the prompt text shown."""

    def __init__(self):
        self.next_result = True
        self.last_message = None

    def __call__(self, message):
        self.last_message = message
        return self.next_result
