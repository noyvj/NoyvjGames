"""Shared skill-tree rules (planning/TODO.md W-3): the Python mirror of the pure
functions in `shared/skill-tree.js`.

A skill tree is plain data, a dict (or the parsed JSON a game ships):

    {"id": "seed_vault", "title": "Seed Vault", "currency": "seed points",
     "branches": [{"id": "growth", "title": "Growth"}],        # optional
     "nodes": [{"id": "deep_roots", "branch": "growth", "cost": 2,
                "label": "Deep Roots", "description": "Plots recover faster.",
                "effect": "plot_recovery_plus",                  # optional, default = id
                "requires": ["quick_start"],                     # ALL must be owned
                "tier": 2}]}                                     # optional, default = depth

The player's state is only a list of owned node ids (save-friendly, order is
the order they were bought). `earned` is the total points the player has ever
been given for this tree (not the unspent balance); the balance is always
`earned - spent(tree, owned)`, so nothing can drift. `earned=None` means the
points are unlimited (a sandbox or test).

Every function is deterministic and never mutates its arguments: the ones that
change ownership (`buy`, `refund`, `refund_all`) return a result dict holding
the new owned list. The JavaScript mirror uses the same names in camelCase and
the same rules; `shared/tests/test_skill_tree_parity.py` pins them together.
"""

STATUS_OWNED = "owned"
STATUS_AVAILABLE = "available"
STATUS_UNAFFORDABLE = "unaffordable"  # prerequisites met, not enough points yet
STATUS_LOCKED = "locked"              # a prerequisite is missing


def nodes_of(tree):
    nodes = tree.get("nodes") if isinstance(tree, dict) else None
    return [n for n in nodes if isinstance(n, dict) and isinstance(n.get("id"), str)] if isinstance(nodes, list) else []


def node_map(tree):
    return {n["id"]: n for n in nodes_of(tree)}


def requires_of(node):
    req = node.get("requires")
    return [r for r in req if isinstance(r, str)] if isinstance(req, (list, tuple)) else []


def cost_of(node):
    cost = node.get("cost")
    return cost if isinstance(cost, int) and not isinstance(cost, bool) and cost >= 0 else 0


def effect_of(node):
    effect = node.get("effect")
    return effect if isinstance(effect, str) and effect else node["id"]


def validate(tree):
    """A list of human-readable problems with the tree data (empty when fine):
    duplicate ids, non-integer or non-positive costs, unknown or self
    prerequisites, cycles."""
    errors = []
    raw = tree.get("nodes") if isinstance(tree, dict) else None
    if not isinstance(raw, list) or not raw:
        return ["tree has no nodes"]
    seen = set()
    for n in raw:
        if not isinstance(n, dict) or not isinstance(n.get("id"), str) or not n["id"]:
            errors.append("a node has no string id")
            continue
        if n["id"] in seen:
            errors.append(f"duplicate node id {n['id']}")
        seen.add(n["id"])
        cost = n.get("cost")
        if not isinstance(cost, int) or isinstance(cost, bool) or cost < 1:
            errors.append(f"node {n['id']} needs an integer cost of at least 1")
        if not isinstance(n.get("label"), str) or not n["label"]:
            errors.append(f"node {n['id']} needs a label")
        req = n.get("requires", [])
        if not isinstance(req, (list, tuple)) or any(not isinstance(r, str) for r in req):
            errors.append(f"node {n['id']} requires must be a list of ids")
    ids = {n["id"] for n in raw if isinstance(n, dict) and isinstance(n.get("id"), str)}
    for n in raw:
        if not isinstance(n, dict) or not isinstance(n.get("id"), str):
            continue
        for r in requires_of(n):
            if r == n["id"]:
                errors.append(f"node {n['id']} requires itself")
            elif r not in ids:
                errors.append(f"node {n['id']} requires unknown node {r}")
    if not errors:
        # Cycle check: repeatedly peel nodes whose prerequisites are all peeled.
        remaining = {n["id"]: set(requires_of(n)) for n in raw}
        while remaining:
            ready = [i for i, req in remaining.items() if not (req & remaining.keys())]
            if not ready:
                errors.append("prerequisites form a cycle: " + ", ".join(sorted(remaining)))
                break
            for i in ready:
                del remaining[i]
    return errors


def tier_of(tree, node_id):
    """The node's declared `tier`, else its depth (1 + the deepest prerequisite)."""
    nodes = node_map(tree)

    def depth(i, trail):
        node = nodes.get(i)
        if node is None or i in trail:
            return 0
        tier = node.get("tier")
        if isinstance(tier, int) and not isinstance(tier, bool) and tier >= 1:
            return tier
        reqs = requires_of(node)
        return 1 + max((depth(r, trail | {i}) for r in reqs), default=0)

    return max(depth(node_id, frozenset()), 1) if node_id in nodes else 0


def spent(tree, owned):
    """Points spent: the cost of every distinct, known owned node."""
    nodes = node_map(tree)
    return sum(cost_of(nodes[i]) for i in dict.fromkeys(owned or []) if isinstance(i, str) and i in nodes)


def points_left(tree, owned, earned):
    """The unspent balance, or None for an unlimited tree."""
    return None if earned is None else earned - spent(tree, owned)


def sanitize_owned(tree, owned, earned=None, overspend="clear"):
    """Clean an owned list read from a save: known string ids only, no
    duplicates (first occurrence wins, order kept), and any node whose
    prerequisites are not also owned is dropped (repeating until stable). If the
    result costs more than `earned`: `overspend="clear"` (default, what Trade
    Empire does) returns []; `"trim"` drops the most recently listed nodes (and
    anything that needed them) until it fits."""
    nodes = node_map(tree)
    out = []
    for i in owned if isinstance(owned, (list, tuple)) else []:
        if isinstance(i, str) and i in nodes and i not in out:
            out.append(i)
    out = _prune(nodes, out)
    if earned is not None and spent(tree, out) > earned:
        if overspend != "trim":
            return []
        while out and spent(tree, out) > earned:
            out.pop()
            out = _prune(nodes, out)
    return out


def _prune(nodes, owned):
    """Drop owned nodes whose prerequisites are not owned, until stable."""
    out = list(owned)
    changed = True
    while changed:
        changed = False
        for i in list(out):
            if any(r not in out for r in requires_of(nodes[i])):
                out.remove(i)
                changed = True
    return out


def missing_requirements(tree, owned, node_id):
    """Prerequisite ids the player does not own yet, in the node's own order."""
    nodes = node_map(tree)
    node = nodes.get(node_id)
    if node is None:
        return []
    have = set(owned or [])
    return [r for r in requires_of(node) if r not in have]


def status(tree, owned, node_id, earned=None):
    """owned / available / unaffordable / locked (unknown ids read as locked)."""
    nodes = node_map(tree)
    node = nodes.get(node_id)
    if node is None:
        return STATUS_LOCKED
    if node_id in (owned or []):
        return STATUS_OWNED
    if missing_requirements(tree, owned, node_id):
        return STATUS_LOCKED
    if earned is not None and points_left(tree, owned, earned) < cost_of(node):
        return STATUS_UNAFFORDABLE
    return STATUS_AVAILABLE


def can_buy(tree, owned, node_id, earned=None):
    return isinstance(node_id, str) and status(tree, owned, node_id, earned) == STATUS_AVAILABLE


def buy(tree, owned, node_id, earned=None):
    """Try to buy a node. Returns {"ok", "owned" (a new list), "spent",
    "points_left", "reason" ("" when ok)}; on failure `owned` is unchanged."""
    current = list(owned or [])
    state = status(tree, current, node_id, earned) if isinstance(node_id, str) else STATUS_LOCKED
    if state == STATUS_AVAILABLE:
        current.append(node_id)
        reason = ""
    elif not isinstance(node_id, str) or node_id not in node_map(tree):
        reason = "unknown"
    elif state == STATUS_OWNED:
        reason = "owned"
    elif state == STATUS_LOCKED:
        reason = "locked"
    else:
        reason = "points"
    return {"ok": state == STATUS_AVAILABLE, "owned": current, "spent": spent(tree, current),
            "points_left": points_left(tree, current, earned), "reason": reason}


def can_refund(tree, owned, node_id):
    """A node can be refunded alone only if nothing else owned depends on it."""
    nodes = node_map(tree)
    if node_id not in nodes or node_id not in (owned or []):
        return False
    return not any(node_id in requires_of(nodes[i]) for i in owned if i in nodes and i != node_id)


def refund(tree, owned, node_id):
    current = list(owned or [])
    if node_id not in node_map(tree):
        return {"ok": False, "owned": current, "refunded": 0, "reason": "unknown"}
    if node_id not in current:
        return {"ok": False, "owned": current, "refunded": 0, "reason": "not-owned"}
    if not can_refund(tree, current, node_id):
        return {"ok": False, "owned": current, "refunded": 0, "reason": "needed"}
    nodes = node_map(tree)
    current = [i for i in current if i != node_id]
    return {"ok": True, "owned": current, "refunded": cost_of(nodes[node_id]), "reason": ""}


def refund_all(tree, owned):
    """Refund every owned node: the new owned list is empty and `refunded` is
    the whole spend (the balance then equals `earned` again)."""
    return {"ok": True, "owned": [], "refunded": spent(tree, owned), "reason": ""}


def effects(tree, owned):
    """Effect ids of the owned nodes, in tree order (what a game switches on)."""
    have = set(owned or [])
    return [effect_of(n) for n in nodes_of(tree) if n["id"] in have]


def has_effect(tree, owned, effect):
    return effect in effects(tree, owned)


def totals(tree, owned, earned=None):
    """Counts for a header or a completion badge."""
    nodes = nodes_of(tree)
    have = set(owned or [])
    owned_nodes = [n for n in nodes if n["id"] in have]
    by_branch = {}
    for n in nodes:
        slot = by_branch.setdefault(n.get("branch") or "", {"owned": 0, "nodes": 0, "spent": 0, "cost": 0})
        slot["nodes"] += 1
        slot["cost"] += cost_of(n)
        if n["id"] in have:
            slot["owned"] += 1
            slot["spent"] += cost_of(n)
    total_cost = sum(cost_of(n) for n in nodes)
    spent_now = sum(cost_of(n) for n in owned_nodes)
    return {
        "owned_count": len(owned_nodes), "node_count": len(nodes),
        "spent": spent_now, "total_cost": total_cost, "remaining_cost": total_cost - spent_now,
        "points_left": None if earned is None else earned - spent_now,
        "complete": bool(nodes) and len(owned_nodes) == len(nodes),
        "by_branch": by_branch,
    }
