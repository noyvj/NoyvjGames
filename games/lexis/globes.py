"""Lexis -- low-poly globes for each planet."""

import math


def globe_svg(lamp_count: int, width: int = 200, height: int = 200) -> str:
    """Return an SVG string for a dark low-poly globe with `lamp_count` lamps lit (0-7)."""
    lat_bands = 6
    lon_bands = 12
    radius = width / 3.5

    # Generate sphere points deterministically
    points = []
    for i in range(lat_bands + 1):
        phi = math.pi * i / lat_bands
        sin_phi = math.sin(phi)
        cos_phi = math.cos(phi)
        for j in range(lon_bands + 1):
            theta = 2 * math.pi * j / lon_bands
            x = radius * sin_phi * math.cos(theta)
            y = radius * cos_phi
            z = radius * sin_phi * math.sin(theta)
            points.append((x, y, z))

    def proj(p):
        scale = width / 2
        return f"{width / 2 + p[0] * scale:.1f},{height / 2 - p[1] * scale:.1f}"

    faces = []
    for i in range(lat_bands):
        for j in range(lon_bands):
            p0 = points[i * (lon_bands + 1) + j]
            p1 = points[i * (lon_bands + 1) + j + 1]
            p2 = points[(i + 1) * (lon_bands + 1) + j]
            p3 = points[(i + 1) * (lon_bands + 1) + j + 1]
            faces.append(f"M{proj(p0)} L{proj(p1)} L{proj(p3)} Z")
            faces.append(f"M{proj(p0)} L{proj(p3)} L{proj(p2)} Z")

    svg_parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Low-poly globe">']

    for i, face in enumerate(faces):
        # Subtle variation for low-poly look
        lightness = 12 + (i % 6) * 3
        svg_parts.append(f'<path d="{face}" fill="hsl(220, 18%, {lightness}%)" stroke="#1b2744" stroke-width="0.5"/>')

    # Lit lamps around the equator
    for i in range(lamp_count):
        angle = 2 * math.pi * i / 7 - math.pi / 2
        x = width / 2 + (width / 3.5) * math.cos(angle)
        y = height / 2 + (height / 3.5) * math.sin(angle)
        svg_parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#ffd866" stroke="#fff3c4" stroke-width="1"/>')

    svg_parts.append('</svg>')
    return "".join(svg_parts)
