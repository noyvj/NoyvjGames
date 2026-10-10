"""Evidence Hunt -- helper the chapter files use to write cases compactly."""


def C(cid, title, layout, truth, pool, restless, kit=3, accounts=(), features=None, keepsake=None, client="", intro="", ending="", names=None):
    """An authored case. `truth` is a kind id (or two). `restless` is a tuple of room-id tuples, one per presence. `accounts`
    is a tuple of (behaviour, room id or None). `features` maps a room id to a feature id. `keepsake` is (room id, keepsake id,
    behaviour it shows)."""
    if isinstance(truth, str):
        truth = (truth,)
    restless = tuple(tuple(slot) for slot in restless)
    return {"id": cid, "title": title, "layout": layout, "truth": tuple(truth), "pool": tuple(pool), "restless": restless, "kit": kit,
            "accounts": tuple(tuple(a) for a in accounts), "features": dict(features or {}), "keepsake": tuple(keepsake) if keepsake else None,
            "client": client, "intro": intro, "ending": ending, "names": dict(names or {})}
