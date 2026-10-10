"""Stranded -- story builders. The story is data: every scene is a Python table built with S() and C(), so the engine never
contains a line of story. Plain Python with no DOM, no clock and no random source.

Text shorthands (kept small so a whole scene fits on a few lines):
  fx    "t1 h-2 s1"   Trust, Hope, Supplies deltas (clamped 0..10 by the walker)
  set / get   space-separated names: flags set, collectables found
  need  "bit", "!bit", "t4", "h<4", joined with "&": every part must hold (flag, no-flag, stat at least, stat below)
  to    a scene id, or a list of "cond>scene" routes tried in order with a plain scene id last as the default
  lines "?bit|text" shows only when the flag is set, "?!bit|text" only when it is not; "*text*" is a stage direction
"""

import re

STATS = ("trust", "supplies", "hope")
LETTER = {"t": "trust", "s": "supplies", "h": "hope"}
START_STATS = (3, 6, 5)
LOW, HIGH = 0, 10

_FX = re.compile(r"^([tsh])([+-]?\d+)$")
_MIN = re.compile(r"^([tsh])(\d+)$")
_MAX = re.compile(r"^([tsh])<(\d+)$")


def parse_fx(text):
    out = [0, 0, 0]
    for token in text.split():
        m = _FX.match(token)
        if not m:
            raise ValueError("bad fx %r" % token)
        out[("t", "s", "h").index(m.group(1))] += int(m.group(2))
    return tuple(out)


def parse_cond(text):
    """'bit&!battery&t4&h<5' -> {'all': [...], 'none': [...], 'min': {stat: n}, 'max': {stat: n}} or None when empty."""
    text = (text or "").strip()
    if not text:
        return None
    cond = {"all": [], "none": [], "min": {}, "max": {}}
    for token in text.split("&"):
        token = token.strip()
        m = _MAX.match(token)
        if m:
            cond["max"][LETTER[m.group(1)]] = int(m.group(2))
            continue
        m = _MIN.match(token)
        if m:
            cond["min"][LETTER[m.group(1)]] = int(m.group(2))
            continue
        if token.startswith("!"):
            cond["none"].append(token[1:])
        elif re.match(r"^[a-z_]{3,}$", token):
            cond["all"].append(token)
        else:
            raise ValueError("bad condition %r" % token)
    return cond


def parse_line(text):
    """-> (cond or None, text). '?bit|hello' is shown only when the flag bit is set."""
    if text.startswith("?"):
        head, _sep, body = text[1:].partition("|")
        return parse_cond(head), body
    return None, text


def _words(text):
    return tuple(text.split())


def parse_route(to):
    """-> tuple of (cond or None, scene id); the last one is the default."""
    items = [to] if isinstance(to, str) else list(to)
    out = []
    for item in items:
        head, sep, target = item.rpartition(">")
        out.append((parse_cond(head) if sep else None, target))
    if out[-1][0] is not None:
        raise ValueError("the last route needs no condition: %r" % (to,))
    return tuple(out)


def C(text, reply, to, fx="", need="", set="", get=""):
    """One choice: what you send, what she answers, where it goes."""
    return {"text": text, "reply": [parse_line(r) for r in ([reply] if isinstance(reply, str) else reply)],
            "to": parse_route(to), "fx": parse_fx(fx), "need": parse_cond(need), "set": _words(set), "get": _words(get)}


def S(sid, day, title, lines, choices=(), fx="", set="", get="", end=""):
    """One scene. A scene with no choices must be an ending (end='its id')."""
    return {"id": sid, "day": day, "title": title, "lines": [parse_line(x) for x in lines], "choices": list(choices),
            "fx": parse_fx(fx), "set": _words(set), "get": _words(get), "end": end}
