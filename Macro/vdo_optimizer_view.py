# -*- coding: utf-8 -*-
# =====================================================================
# vdo_optimizer_view.py
# Vista del plano de corte (widget Qt con QPainter).
#
# Axioma 1: separada del cálculo (vdo_optimizer_core) y del launcher.
# Solo dibuja los datos que produce el core. Sin FreeCAD, sin I/O.
# =====================================================================

try:
    from PySide2 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide import QtWidgets, QtCore, QtGui

import vdo_optimizer_core as core

_PAD = 14
_GROUP_H = 26
_SHEET_GAP = 16
_PREVIEW_W = 720.0
_FONT_PX = 8


def _color(material):
    h = (sum(ord(c) for c in str(material)) * 47) % 360
    return QtGui.QColor.fromHsl(h, 150, 205)


class BoardView(QtWidgets.QWidget):
    """Dibuja todos los tableros agrupados por material+espesor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._blocks = []
        self._scale = 1.0
        self._height = 120
        self.setMinimumWidth(int(_PREVIEW_W) + 2 * _PAD)

    # ------------------------------------------------------------------
    def set_groups(self, groups):
        self._groups = groups or []
        self._recompute()
        self.updateGeometry()
        self.update()

    def _recompute(self):
        blocks = []
        y = _PAD
        maxw = 1.0
        for g in self._groups:
            for s in g["sheets"]:
                maxw = max(maxw, s["board_w"])
        scale = _PREVIEW_W / maxw if maxw else 1.0

        for g in self._groups:
            blocks.append({"kind": "group", "y": y, "g": g})
            y += _GROUP_H
            for s in g["sheets"]:
                bw = s["board_w"] * scale
                bh = s["board_h"] * scale
                blocks.append({"kind": "sheet", "y": y, "s": s,
                               "bw": bw, "bh": bh})
                y += bh + _SHEET_GAP

        self._scale = scale
        self._blocks = blocks
        self._height = y + _PAD

    def sizeHint(self):
        return QtCore.QSize(int(_PREVIEW_W) + 2 * _PAD, int(self._height))

    def minimumSizeHint(self):
        return self.sizeHint()

    # ------------------------------------------------------------------
    def paintEvent(self, ev):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QtGui.QColor("#fafafa"))
        p.setFont(QtGui.QFont("Sans", _FONT_PX))

        if not self._blocks:
            p.setPen(QtGui.QColor("#999"))
            p.drawText(self.rect(), QtCore.Qt.AlignCenter,
                       "Configurá el tablero y pulsá «Optimizar».")
            p.end()
            return

        for b in self._blocks:
            if b["kind"] == "group":
                self._draw_group(p, b)
            else:
                self._draw_sheet(p, b)
        p.end()

    # ------------------------------------------------------------------
    def _draw_group(self, p, b):
        g = b["g"]
        placed = g["n_pieces"] - len(g["unplaced"])
        text = (f"{g['label']}   —   {len(g['sheets'])} tablero(s), "
                f"{placed}/{g['n_pieces']} piezas")
        p.setPen(QtGui.QPen(QtGui.QColor("#114488")))
        f = p.font(); f.setBold(True); p.setFont(f)
        p.drawText(_PAD, b["y"] + 16, text)
        f.setBold(False); p.setFont(f)

    def _draw_sheet(self, p, b):
        s = b["s"]
        scale = self._scale
        x0, y0, bw, bh = _PAD, b["y"], b["bw"], b["bh"]

        # Tablero
        p.fillRect(QtCore.QRectF(x0, y0, bw, bh), QtGui.QColor("#f6f2e8"))
        p.setPen(QtGui.QPen(QtGui.QColor("#333"), 1.4))
        p.drawRect(QtCore.QRectF(x0, y0, bw, bh))

        # Retales (sobrante reutilizable)
        hatch = QtGui.QBrush(QtGui.QColor(180, 180, 180),
                             QtCore.Qt.BDiagPattern)
        for o in s.get("offcuts", []):
            if min(o["w"], o["h"]) < core.MIN_OFFCUT:
                continue
            ox = x0 + o["x"] * scale
            oy = y0 + o["y"] * scale
            ow = o["w"] * scale
            oh = o["h"] * scale
            p.setBrush(hatch)
            p.setPen(QtGui.QPen(QtGui.QColor("#999"), 0.8,
                                QtCore.Qt.DashLine))
            p.drawRect(QtCore.QRectF(ox, oy, ow, oh))
            if ow > 44 and oh > 16:
                p.setPen(QtGui.QColor("#666"))
                p.drawText(QtCore.QRectF(ox, oy, ow, oh),
                           QtCore.Qt.AlignCenter,
                           f"retal\n{o['w']:.0f}x{o['h']:.0f}")

        # Piezas
        for pl in s["placements"]:
            px = x0 + pl["x"] * scale
            py = y0 + pl["y"] * scale
            pw = pl["w"] * scale
            ph = pl["h"] * scale
            p.setBrush(QtGui.QBrush(_color(pl["material"])))
            p.setPen(QtGui.QPen(QtGui.QColor("#444"), 0.7))
            p.drawRect(QtCore.QRectF(px, py, pw, ph))
            if pw > 46 and ph > 20:
                p.setPen(QtGui.QColor("#222"))
                name = pl["name"]
                if len(name) > 16:
                    name = name[:15] + "…"
                mark = " ⤾" if pl["rotated"] else ""
                p.drawText(QtCore.QRectF(px, py, pw, ph),
                           QtCore.Qt.AlignCenter,
                           f"{name}{mark}\n{pl['w']:.0f}x{pl['h']:.0f}")

        # Eficiencia por tablero
        p.setPen(QtGui.QColor("#777"))
        p.drawText(QtCore.QRectF(x0, y0 + bh + 2, bw, 14),
                   QtCore.Qt.AlignLeft,
                   f"Tablero {s['index']} · {len(s['placements'])} piezas · "
                   f"{s['efficiency']:.1f}%")
