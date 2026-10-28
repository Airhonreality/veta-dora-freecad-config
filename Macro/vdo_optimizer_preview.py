#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vdo_optimizer_preview.py
Render de preview (SVG) del resultado del optimizador de corte VDO.

Python puro, sin dependencias. Recibe las 'sheets' y 'unplaced' que
devuelve vdo_optimizer_core.optimize() y escribe un SVG con el acomodo
de cada tablero listo para abrir en el navegador.

No toca FreeCAD ni el canvas: es solo un archivo SVG.
"""

import html

_PAD = 40
_TITLE_H = 34
_GAP = 40
_FONT = "font-family='Segoe UI, Arial, sans-serif'"


def _color(material):
    """Color determinista por material (HSL)."""
    if not material:
        return "hsl(0, 0%, 88%)"
    hue = abs(hash(material)) % 360
    return f"hsl({hue}, 60%, 80%)"


def _esc(text):
    return html.escape(str(text), quote=True)


def _short(name, maxlen=18):
    name = str(name)
    return name if len(name) <= maxlen else name[:maxlen - 1] + "…"


def render_svg(sheets, unplaced, path,
               board_w=2440.0, board_h=1830.0,
               kerf=0.0, margin=0.0):
    """Escribe un SVG con todos los tableros y devuelve la ruta."""

    max_board_w = max([s["board_w"] for s in sheets], default=board_w)
    scale = min(1.0, 1000.0 / max_board_w) if max_board_w else 1.0

    # Altura total
    total_h = _PAD
    sheet_geom = []
    for s in sheets:
        bw = s["board_w"] * scale
        bh = s["board_h"] * scale
        sheet_geom.append((bw, bh))
        total_h += _TITLE_H + bh + _GAP
    total_h += _PAD + 30

    parts = []
    parts.append(
        f"<svg xmlns='http://www.w3.org/2000/svg' "
        f"width='{int(_PAD * 2 + max(1000, 1000))}' height='{int(total_h)}' "
        f"viewBox='0 0 {int(_PAD * 2 + max(1000, 1000))} {int(total_h)}'>")
    parts.append(f"<rect width='100%' height='100%' fill='#ffffff'/>")
    parts.append(
        f"<text x='{_PAD}' y='{_PAD - 10}' font-size='20' font-weight='bold' "
        f"{_FONT} fill='#222'>VDO · Plan de corte</text>")

    y = _PAD + 6
    for s, (bw, bh) in zip(sheets, sheet_geom):
        parts.append(
            f"<text x='{_PAD}' y='{y + 18}' font-size='15' font-weight='bold' "
            f"{_FONT} fill='#0a5'>Tablero {s['index']} — "
            f"{len(s['placements'])} piezas — "
            f"aprovechamiento {s['efficiency']:.1f}%</text>")
        board_y = y + _TITLE_H

        # Tablero
        parts.append(
            f"<rect x='{_PAD}' y='{board_y}' width='{bw:.2f}' height='{bh:.2f}' "
            f"fill='#f6f2e8' stroke='#333' stroke-width='1.5'/>")

        # Margen perimetral (referencia)
        if margin > 0:
            m = margin * scale
            parts.append(
                f"<rect x='{_PAD + m:.2f}' y='{board_y + m:.2f}' "
                f"width='{bw - 2 * m:.2f}' height='{bh - 2 * m:.2f}' "
                f"fill='none' stroke='#c9c2b0' stroke-width='0.8' "
                f"stroke-dasharray='4 4'/>")

        # Piezas
        for pl in s["placements"]:
            px = _PAD + pl["x"] * scale
            py = board_y + pl["y"] * scale
            pw = pl["w"] * scale
            ph = pl["h"] * scale
            fill = _color(pl["material"])
            parts.append(
                f"<rect x='{px:.2f}' y='{py:.2f}' width='{pw:.2f}' "
                f"height='{ph:.2f}' fill='{fill}' stroke='#444' "
                f"stroke-width='0.7'/>")

            if pw > 46 and ph > 22:
                cx = px + pw / 2
                parts.append(
                    f"<text x='{cx:.1f}' y='{py + ph / 2 - 2:.1f}' "
                    f"font-size='9' text-anchor='middle' {_FONT} "
                    f"fill='#222'>{_esc(_short(pl['name']))}</text>")
                dims = f"{pl['w']:.0f}x{pl['h']:.0f}"
                parts.append(
                    f"<text x='{cx:.1f}' y='{py + ph / 2 + 9:.1f}' "
                    f"font-size='8' text-anchor='middle' {_FONT} "
                    f"fill='#555'>{dims}</text>")

        y = board_y + bh + _GAP

    # Piezas no colocadas
    if unplaced:
        parts.append(
            f"<text x='{_PAD}' y='{y}' font-size='14' font-weight='bold' "
            f"{_FONT} fill='#c00'>No colocadas: {len(unplaced)}</text>")
        for i, p in enumerate(unplaced[:15]):
            parts.append(
                f"<text x='{_PAD + 16}' y='{y + 18 + i * 15}' font-size='11' "
                f"{_FONT} fill='#c00'>- {_esc(p['name'])} "
                f"({p['w']:.0f}x{p['h']:.0f})</text>")

    parts.append("</svg>")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    return path
