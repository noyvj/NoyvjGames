"""Small validation helpers shared by the batch B modules (wf_*.py).

Pure Python: no browser imports, so every module built on it can be imported
and tested under plain CPython. index.html writes these files into Pyodide's
virtual file system before game.py runs (see MODULES in its boot script).
"""

import re

LOG_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def clean(value, limit):
    """A stripped string of at most `limit` characters ("" for None)."""
    return str(value if value is not None else "").strip()[:limit]


def str_in(value, container):
    """`value in container`, but False (never a TypeError) for unhashable junk from a bad save."""
    return isinstance(value, str) and value in container


def norm(name):
    """Lower-case letters and digits only, so "Tear Azurite" and "TearAzurite" compare equal."""
    return "".join(ch for ch in str(name) if ch.isalnum()).lower()


def dict_entries(value):
    return [e for e in value if isinstance(e, dict)] if isinstance(value, list) else []


def find_ci(items, text):
    """The item of `items` equal to `text` ignoring case and surrounding space, or None."""
    wanted = str(text or "").strip().lower()
    if not wanted:
        return None
    for item in items:
        if item.lower() == wanted:
            return item
    return None


def pooled(inv):
    """Built plus raw stock of one inventory entry, the pooling the tracker uses."""
    inv = inv or {}
    return int(inv.get("built", 0)) + int(inv.get("raw", 0))
