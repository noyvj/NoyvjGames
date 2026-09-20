import importlib.util
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeConfirm, FakeDocument, FakeElement, create_proxy

GAME_PY = Path(__file__).resolve().parent.parent / "game.py"

ELEMENT_IDS = [
    "components-body",
    "resources-body",
    "component-progress",
    "progress-bar",
    "summary",
    "status-message",
    "reset-button",
]


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM."""

    def __init__(self, module, elements, confirm_fn):
        self.module = module
        self.elements = elements
        self.confirm = confirm_fn

    def reset(self):
        self.elements["reset-button"].dispatch("click", None)


def _install_pyodide_fakes(elements, confirm_fn):
    fake_js = types.ModuleType("js")
    fake_js.document = FakeDocument(elements)
    fake_js.confirm = confirm_fn

    fake_pyodide = types.ModuleType("pyodide")
    fake_pyodide_ffi = types.ModuleType("pyodide.ffi")
    fake_pyodide_ffi.create_proxy = create_proxy
    fake_pyodide.ffi = fake_pyodide_ffi

    sys.modules["js"] = fake_js
    sys.modules["pyodide"] = fake_pyodide
    sys.modules["pyodide.ffi"] = fake_pyodide_ffi


def _remove_pyodide_fakes():
    for name in ("js", "pyodide", "pyodide.ffi", "game"):
        sys.modules.pop(name, None)


@pytest.fixture
def game_env():
    """Loads a brand-new game.py module against a fresh fake DOM.

    game.py runs setup() as a module-level side effect on import, so every
    test gets its own module object (and its own `state` dict) rather than
    sharing state via Python's normal import cache.
    """
    elements = {}
    for id_ in ELEMENT_IDS:
        el = FakeElement(registry=elements)
        el.id = id_

    confirm_fn = FakeConfirm()
    _install_pyodide_fakes(elements, confirm_fn)

    spec = importlib.util.spec_from_file_location("game", GAME_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules["game"] = module
    spec.loader.exec_module(module)  # runs setup() at the bottom of game.py

    yield GameEnv(module, elements, confirm_fn)

    _remove_pyodide_fakes()
