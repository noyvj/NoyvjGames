"""Small fake-DOM tree helpers shared by the batch A feature tests."""


def walk(node):
    yield node
    for child in node.children:
        yield from walk(child)


def find_all(node, tag=None, class_name=None, text=None):
    """Every descendant matching the given tag, class and/or text substring."""
    found = []
    for el in walk(node):
        if tag and el.tag != tag:
            continue
        if class_name and class_name not in str(el.className).split():
            continue
        if text is not None and text not in (el.textContent or ""):
            continue
        found.append(el)
    return found


def all_text(node):
    return " ".join(str(el.textContent or "") for el in walk(node))


def click(element):
    element.dispatch("click", None)


def known_state(m, parts=None, inventory=None):
    """Every part fully owned except the ones named in `parts`; empty inventory."""
    m.state["parts"] = {name: {"target": qty, "owned": qty} for name, qty in m.DEFAULT_PARTS}
    m.state["inventory"] = {}
    for name, info in (parts or {}).items():
        m.state["parts"][name].update(info)
    for name, info in (inventory or {}).items():
        m.state["inventory"][name] = dict(info)
    m.render()
