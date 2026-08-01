import importlib.util
import sys
import types
from pathlib import Path

import pytest

from .fakes import FakeDocument, FakeElement, FakeLocalStorage, create_proxy

GAME_PY = Path(__file__).resolve().parent.parent / "game.py"

SKILL_IDS = ["reinforced_infrastructure", "community_reserves", "early_warning"]

ELEMENT_IDS = [
    "progress-display",
    "next-event-display",
    "resources-display",
    "resilience-display",
    "growth-display",
    "run-summary-display",
    "knowledge-points-display",
    "resilience-invest-button",
    "growth-invest-button",
    "resolve-event-button",
    "new-run-button",
    "progress-comparison-display",
]
for _skill in SKILL_IDS:
    ELEMENT_IDS += [f"skill-{_skill}-status", f"skill-{_skill}-unlock-button"]

INITIALLY_DISABLED_IDS = [
    "resilience-invest-button",
    "growth-invest-button",
] + [f"skill-{s}-unlock-button" for s in SKILL_IDS]


class GameEnv:
    """Bundles a freshly-loaded game module with its fake DOM."""

    def __init__(self, module, elements, local_storage):
        self.module = module
        self.elements = elements
        self.local_storage = local_storage

    @property
    def run(self):
        return self.module.run

    @property
    def skill_tree(self):
        return self.module.skill_tree

    @property
    def run_history(self):
        return self.module.run_history

    def invest_resilience(self):
        self.elements["resilience-invest-button"].dispatch("click", None)

    def invest_growth(self):
        self.elements["growth-invest-button"].dispatch("click", None)

    def resolve_event(self):
        self.elements["resolve-event-button"].dispatch("click", None)

    def unlock_skill(self, skill_id):
        self.elements[f"skill-{skill_id}-unlock-button"].dispatch("click", None)

    def start_new_run(self):
        self.elements["new-run-button"].dispatch("click", None)


def _install_pyodide_fakes(elements, local_storage):
    fake_js = types.ModuleType("js")
    fake_js.document = FakeDocument(elements)
    fake_js.localStorage = local_storage

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
    test gets its own module object (and its own RunState) rather than
    sharing state via Python's normal import cache.
    """
    elements = {}
    for id_ in ELEMENT_IDS:
        FakeElement(id_, registry=elements)
    for id_ in INITIALLY_DISABLED_IDS:
        elements[id_].disabled = True
    local_storage = FakeLocalStorage()
    _install_pyodide_fakes(elements, local_storage)

    spec = importlib.util.spec_from_file_location("game", GAME_PY)
    module = importlib.util.module_from_spec(spec)
    sys.modules["game"] = module
    spec.loader.exec_module(module)  # runs setup() at the bottom of game.py

    yield GameEnv(module, elements, local_storage)

    _remove_pyodide_fakes()
