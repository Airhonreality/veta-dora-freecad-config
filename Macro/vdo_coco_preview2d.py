# -*- coding: utf-8 -*-
# =====================================================================
# vdo_coco_preview2d.py
# Vista frontal 2D del COCO: matriz de vanos y paneles internos.
# Sin dependencias de FreeCAD 3D; sólo Qt.
# =====================================================================

from PySide import QtCore, QtGui, QtWidgets

import vdo_frames as VDO_FR


COLOR_FONDO = QtGui.QColor("#f7f7f5")
COLOR_INTERIOR = QtGui.QColor("#ffffff")
COLOR_PANEL = QtGui.QColor("#4a4a4a")
COLOR_CELDA = QtGui.QColor("#b8b8b8")
COLOR_SELECCION = QtGui.QColor("#e67e22")
COLOR_TEXTO = QtGui.QColor("#303030")
COLOR_ERROR = QtGui.QColor("#c0392b")


class CocoPreview2D(QtWidgets.QGraphicsView):
    """Dibuja el frente interior del COCO y permite seleccionar vanos."""

    cellClicked = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QtWidgets.QGraphicsScene(self))
        self.setRenderHints(
            QtGui.QPainter.Antialiasing
            | QtGui.QPainter.TextAntialiasing)
        self.setMinimumHeight(190)
        self.setBackgroundBrush(COLOR_FONDO)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self._cell_items = {}
        self._selected = None
        self._outer_w = 0.0
        self._outer_h = 0.0
        self._resolved = None

    # -----------------------------------------------------------------
    # API
    # -----------------------------------------------------------------
    def set_layout(self, resolved, outer_w=None, outer_h=None,
                   selected=None):
        self._resolved = resolved
        self._outer_w = float(outer_w or resolved.inner_w)
        self._outer_h = float(outer_h or resolved.inner_h)
        self._selected = selected
        self._construir()

    def set_selected(self, label):
        self._selected = label
        for label_item, item in self._cell_items.items():
            self._aplicar_estilo(item, label_item == label)
        self.viewport().update()

    def selected(self):
        return self._selected

    # -----------------------------------------------------------------
    # Geometría
    # -----------------------------------------------------------------
    def _rect(self, x, z, w, h):
        """Convierte coordenadas locales (origen abajo-izquierda) a escena."""
        margen = 14.0
        margen_sup = 34.0
        x0 = (self._outer_w - self._resolved.inner_w) / 2.0
        z0 = (self._outer_h - self._resolved.inner_h) / 2.0
        sx = margen + x0 + float(x)
        sy = margen_sup + self._outer_h - (z0 + float(z) + float(h))
        return QtCore.QRectF(sx, sy, float(w), float(h))

    def _construir(self):
        scene = self.scene()
        scene.clear()
        self._cell_items = {}
        if self._resolved is None:
            return

        margen = 14.0
        margen_sup = 34.0
        total_w = self._outer_w + margen * 2.0
        total_h = self._outer_h + margen + margen_sup
        scene.setSceneRect(0.0, 0.0, total_w, total_h)

        # Etiqueta de frente local y ejes.
        etiqueta = QtWidgets.QGraphicsSimpleTextItem(VDO_FR.ETIQUETA_FRENTE)
        fuente = etiqueta.font()
        fuente.setPointSizeF(7.5)
        fuente.setBold(True)
        etiqueta.setFont(fuente)
        etiqueta.setBrush(COLOR_TEXTO)
        etiqueta.setPos(margen, 7.0)
        scene.addItem(etiqueta)

        ejes = QtWidgets.QGraphicsSimpleTextItem(VDO_FR.EJES_PREVIEW)
        fuente_ejes = ejes.font()
        fuente_ejes.setPointSizeF(7.0)
        ejes.setFont(fuente_ejes)
        ejes.setBrush(COLOR_TEXTO)
        ancho_ejes = ejes.boundingRect().width()
        ejes.setPos(total_w - margen - ancho_ejes, 7.0)
        scene.addItem(ejes)

        # Carcasa exterior e interior.
        exterior = QtCore.QRectF(
            margen, margen_sup, self._outer_w, self._outer_h)
        scene.addRect(
            exterior, QtGui.QPen(QtGui.QColor("#7a7a7a"), 1.0),
            QtGui.QBrush(COLOR_FONDO))

        t = self._resolved.thickness
        interior = QtCore.QRectF(
            margen + t, margen_sup + t,
            self._resolved.inner_w, self._resolved.inner_h)
        scene.addRect(
            interior, QtGui.QPen(QtGui.QColor("#d0d0d0"), 1.0),
            QtGui.QBrush(COLOR_INTERIOR))

        # Paneles internos.
        for piece in self._resolved.pieces:
            rect = self._rect(piece.x, piece.z, piece.w, piece.h)
            scene.addRect(rect, QtGui.QPen(QtCore.Qt.NoPen),
                          QtGui.QBrush(COLOR_PANEL))

        # Celdas (transparentes, encima de los paneles para poder clicar).
        for cell in self._resolved.walk_cells():
            rect = self._rect(cell.x, cell.z, cell.w, cell.h)
            item = QtWidgets.QGraphicsRectItem(rect)
            item.setData(0, cell.label)
            item.setData(1, cell)
            item.setAcceptHoverEvents(True)
            item.setZValue(10 + cell.level)
            item.setToolTip(
                f"{cell.label}\nX libre: {cell.w:.1f} mm\n"
                f"Y libre: {cell.h:.1f} mm")
            scene.addItem(item)
            self._cell_items[cell.label] = item
            self._aplicar_estilo(item, cell.label == self._selected)

            if cell.w >= 50.0 and cell.h >= 18.0:
                texto = QtWidgets.QGraphicsSimpleTextItem(cell.label, item)
                fuente = texto.font()
                fuente.setPointSizeF(6.5)
                texto.setFont(fuente)
                texto.setBrush(COLOR_TEXTO)
                br = texto.boundingRect()
                texto.setPos(
                    rect.center().x() - br.width() / 2.0,
                    rect.center().y() - br.height() / 2.0)

        # Aviso de overflow.
        if self._resolved.overflow:
            scene.addRect(
                interior.adjusted(1, 1, -1, -1),
                QtGui.QPen(COLOR_ERROR, 2.0))

        self.fitInView(
            scene.sceneRect(), QtCore.Qt.KeepAspectRatio)

    def _aplicar_estilo(self, item, seleccionada):
        if seleccionada:
            pen = QtGui.QPen(COLOR_SELECCION, 2.2)
            pen.setStyle(QtCore.Qt.SolidLine)
            item.setBrush(QtGui.QBrush(
                QtGui.QColor(230, 126, 34, 28)))
        else:
            pen = QtGui.QPen(COLOR_CELDA, 1.0)
            pen.setStyle(QtCore.Qt.DashLine)
            item.setBrush(QtCore.Qt.NoBrush)
        item.setPen(pen)

    # -----------------------------------------------------------------
    # Eventos
    # -----------------------------------------------------------------
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() != QtCore.Qt.LeftButton:
            return
        item = self.itemAt(event.pos())
        while item is not None:
            label = item.data(0)
            if label:
                self.set_selected(str(label))
                self.cellClicked.emit(str(label))
                return
            item = item.parentItem()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.scene() is not None:
            self.fitInView(
                self.scene().sceneRect(), QtCore.Qt.KeepAspectRatio)
