"""Star map data and logic for Lexis."""

STAR_MAP = [
    {"id": "s1", "x": 2, "y": 3, "strength": 4, "label": "Faint pulse"},
    {"id": "s2", "x": 5, "y": 7, "strength": 8, "label": "Strong carrier"},
    {"id": "s3", "x": 1, "y": 9, "strength": 2, "label": "Distant beacon"},
    {"id": "s4", "x": 8, "y": 2, "strength": 6, "label": "Narrow band"},
    {"id": "s5", "x": 6, "y": 6, "strength": 9, "label": "Wide signal"},
    {"id": "s6", "x": 3, "y": 1, "strength": 3, "label": "Intermittent"},
    {"id": "s7", "x": 9, "y": 8, "strength": 5, "label": "Steady tone"},
    {"id": "s8", "x": 4, "y": 5, "strength": 7, "label": "Pulsed carrier"},
]


def tune_star(star_id, discovered):
    """Return star info if valid. Updates `discovered` set in place."""
    for star in STAR_MAP:
        if star["id"] == star_id:
            discovered.add(star_id)
            return {"id": star["id"], "x": star["x"], "y": star["y"], "strength": star["strength"], "label": star["label"]}
    return None
