"""The Forest Lab panel (B-5): sliders, saved variants and renders."""

import json

from js import document

from canopy_helpers import _el, _read_local_storage_item, _write_local_storage_item
from canopy_rules import LAB_KEYS, LAB_MAX, LAB_MIN, LAB_STEP, lab, lab_active


# B-5 continued: staged values, applying them, saved variants and the panel. ---------------------------------
LAB_VARIANTS_KEY = "canopy_lab_variants_v1"
LAB_VARIANTS_MAX = 6
LAB_LABELS = {"soil": "Soil damage per clear", "maturity": "Growth over time", "requests": "Request frequency", "season": "Season strength"}
lab_pending = {key: 1.0 for key in LAB_KEYS}


def clean_lab_value(value):
    """A value snapped onto the slider's steps and range; anything unusable becomes 1.0."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return 1.0
    snapped = round(float(value) / LAB_STEP) * LAB_STEP
    return min(LAB_MAX, max(LAB_MIN, snapped))


def set_lab_values(raw):
    """Applies saved values (missing or invalid ones are the normal 1.0)."""
    source = raw if isinstance(raw, dict) else {}
    for key in LAB_KEYS:
        lab[key] = clean_lab_value(source.get(key, 1.0))
        lab_pending[key] = lab[key]


def lab_summary_text(values):
    return ", ".join(f"{LAB_LABELS[k].lower()} x{values[k]:g}" for k in LAB_KEYS)


def load_lab_variants():
    raw = _read_local_storage_item(LAB_VARIANTS_KEY)
    try:
        data = json.loads(raw) if raw else []
    except (ValueError, TypeError):
        return []
    out = []
    for item in data if isinstance(data, list) else []:
        if isinstance(item, dict) and isinstance(item.get("values"), dict):
            out.append({"name": str(item.get("name", "Variant"))[:20] or "Variant",
                        "values": {k: clean_lab_value(item["values"].get(k, 1.0)) for k in LAB_KEYS}})
    return out[:LAB_VARIANTS_MAX]


def save_lab_variant(name=""):
    """Stores the staged values as a named variant; the newest replaces the oldest once six are held."""
    variants = load_lab_variants()
    name = " ".join(str(name or "").split())[:20] or f"Variant {len(variants) + 1}"
    variants = [v for v in variants if v["name"] != name]
    variants.append({"name": name, "values": dict(lab_pending)})
    _write_local_storage_item(LAB_VARIANTS_KEY, json.dumps(variants[-LAB_VARIANTS_MAX:]))
    return name


def load_lab_variant(name):
    for variant in load_lab_variants():
        if variant["name"] == name:
            lab_pending.update(variant["values"])
            return True
    return False


def reset_lab_to_normal(event=None):
    for key in LAB_KEYS:
        lab_pending[key] = 1.0
    render_lab()


def on_lab_slider(key):
    element = _el(f"lab-{key}")
    if element is None:
        return
    try:
        lab_pending[key] = clean_lab_value(float(element.value))
    except (TypeError, ValueError):
        return
    render_lab()


def on_lab_save_variant(event=None):
    name_box = _el("lab-variant-name")
    save_lab_variant(getattr(name_box, "value", ""))
    if name_box is not None:
        name_box.value = ""
    render_lab()


def on_lab_load_variant(event=None):
    select = _el("lab-variant-select")
    if select is not None and load_lab_variant(getattr(select, "value", "")):
        render_lab()


def render_lab_banner():
    banner = _el("lab-banner")
    if banner is not None:
        banner.hidden = not lab_active()
        banner.innerText = "Sandbox forest: not counted toward personal bests, lifetime statistics, legacy bonus or rank." if lab_active() else ""


def render_lab():
    render_lab_banner()
    for key in LAB_KEYS:
        slider, readout = _el(f"lab-{key}"), _el(f"lab-{key}-value")
        if slider is not None:
            slider.min, slider.max, slider.step = str(LAB_MIN), str(LAB_MAX), str(LAB_STEP)
            slider.value = f"{lab_pending[key]:g}"
        if readout is not None:
            readout.innerText = f"x{lab_pending[key]:g}"
    status = _el("lab-status")
    if status is not None:
        changed = any(abs(lab_pending[k] - lab[k]) > 1e-9 for k in LAB_KEYS)
        status.innerText = (f"Live: {lab_summary_text(lab)}." if lab_active() else "Live: the normal game.") + (
            " Staged changes start a new forest when you press Apply." if changed else "")
    select = _el("lab-variant-select")
    if select is not None:
        previous = getattr(select, "value", "")
        select.innerHTML = ""
        names = []
        for variant in load_lab_variants():
            option = document.createElement("option")
            option.value = variant["name"]
            option.innerText = f"{variant['name']} ({lab_summary_text(variant['values'])})"
            select.appendChild(option)
            names.append(variant["name"])
        if previous in names:
            select.value = previous
