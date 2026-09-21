# -*- coding: utf-8 -*-
# =====================================================================
# vdo_coco_spaces_task.py
# Task Panel dinámico para configuración de espacios libres del COCO
# Filas dinámicas, anidamiento recursivo, funciones helper
# =====================================================================

import json
from PySide import QtGui, QtCore
import FreeCAD as App
import FreeCADGui as Gui

from vdo_spaces import (
    SpaceNode, ESPACIO_FIJO, ESPACIO_RESTANTE, ESPACIO_IGUALES,
    serializar_espacios, deserializar_espacios,
    calcular_espacio_libre
)


COL_TIPO = 0
COL_VALOR = 1
COL_RESUMEN = 2
COL_ACCIONES = 3

TIPOS_LABELS = {
    ESPACIO_FIJO: "Fijo (mm)",
    ESPACIO_RESTANTE: "Restante",
    ESPACIO_IGUALES: "Iguales (N partes)",
}


class EspacioRow:
    """Representa una fila visual en la tabla de espacios."""

    def __init__(self, node=None, depth=0):
        self.node = node or SpaceNode(space_type=ESPACIO_RESTANTE)
        self.depth = depth
        self.children_rows = []


class SpacesTableWidget(QtGui.QTableWidget):
    """QTableWidget personalizado con soporte para drag-drop reorder."""

    rowsReordered = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Tipo", "Valor", "Resultado", "Acciones"])
        header = self.horizontalHeader()
        header.setResizeMode(COL_TIPO, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(COL_VALOR, QtGui.QHeaderView.Stretch)
        header.setResizeMode(COL_RESUMEN, QtGui.QHeaderView.Stretch)
        header.setResizeMode(COL_ACCIONES, QtGui.QHeaderView.ResizeToContents)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)

    def dropEvent(self, event):
        selected_rows = sorted(set(idx.row() for idx in self.selectedIndexes()))
        drop_index = self.indexAt(event.pos())
        if not drop_index.isValid() or self.rowCount() - 1 == drop_index.row():
            drop_row = self.rowCount()
        else:
            drop_row = drop_index.row()
        rows_data = []
        for row in selected_rows:
            row_items = []
            for col in range(self.columnCount()):
                item = self.item(row, col)
                row_items.append(item.clone() if item else None)
            widget = self.cellWidget(row, COL_ACCIONES)
            rows_data.append({"items": row_items, "widget": widget})
        for row in reversed(selected_rows):
            self.removeRow(row)
            if row < drop_row:
                drop_row -= 1
        for i, rd in enumerate(rows_data):
            self.insertRow(drop_row + i)
            for col, item in enumerate(rd["items"]):
                if item:
                    self.setItem(drop_row + i, col, item)
        self.rowsReordered.emit()


class CocoSpacesTaskPanel:
    """Task Panel para configurar la distribución de espacios internos."""

    def __init__(self, obj=None):
        self.obj = obj
        self._current_axis = "X"
        self._rows = []
        self._child_rows = {}
        self._building = False
        self.form = self._crear_widget()
        if obj:
            self._cargar_valores(obj)

    def _crear_widget(self):
        widget = QtGui.QWidget()
        main_layout = QtGui.QVBoxLayout(widget)

        # --- Selector de eje ---
        grupo_eje = QtGui.QGroupBox("Eje de Distribución")
        layout_eje = QtGui.QHBoxLayout(grupo_eje)
        layout_eje.addWidget(QtGui.QLabel("Dividir en:"))
        self.combo_eje = QtGui.QComboBox()
        self.combo_eje.addItems(["X (Vertical / Columnas)", "Y (Horizontal / Repisas)"])
        self.combo_eje.currentIndexChanged.connect(self._on_eje_cambiado)
        layout_eje.addWidget(self.combo_eje)
        main_layout.addWidget(grupo_eje)

        # --- Tabla de espacios ---
        grupo_tabla = QtGui.QGroupBox("Espacios Libres")
        layout_tabla = QtGui.QVBoxLayout(grupo_tabla)

        self.table = SpacesTableWidget()
        self.table.cellChanged.connect(self._on_cell_changed)
        layout_tabla.addWidget(self.table)

        # Botones de acción
        layout_botones = QtGui.QHBoxLayout()
        btn_add = QtGui.QPushButton("+ Añadir Espacio")
        btn_add.clicked.connect(self._agregar_espacio)
        btn_remove = QtGui.QPushButton("- Eliminar")
        btn_remove.clicked.connect(self._eliminar_espacio)
        btn_half = QtGui.QPushButton("1/2")
        btn_half.setToolTip("Dividir el espacio seleccionado en 2 partes iguales")
        btn_half.clicked.connect(lambda: self._dividir_seleccion(2))
        btn_third = QtGui.QPushButton("1/3")
        btn_third.setToolTip("Dividir el espacio seleccionado en 3 partes iguales")
        btn_third.clicked.connect(lambda: self._dividir_seleccion(3))
        btn_fourth = QtGui.QPushButton("1/4")
        btn_fourth.setToolTip("Dividir el espacio seleccionado en 4 partes iguales")
        btn_fourth.clicked.connect(lambda: self._dividir_seleccion(4))
        btn_nest = QtGui.QPushButton("Sub-configurar")
        btn_nest.setToolTip("Abrir sub-panel para anidar hijos en este espacio")
        btn_nest.clicked.connect(self._subconfigurar)

        layout_botones.addWidget(btn_add)
        layout_botones.addWidget(btn_remove)
        layout_botones.addWidget(QtGui.QSeparate(QtGui.QSeparator(QtCore.Qt.Vertical)))
        layout_botones.addWidget(btn_half)
        layout_botones.addWidget(btn_third)
        layout_botones.addWidget(btn_fourth)
        layout_botones.addWidget(QtGui.QSeparate(QtGui.QSeparator(QtCore.Qt.Vertical)))
        layout_botones.addWidget(btn_nest)
        layout_tabla.addLayout(layout_botones)

        main_layout.addWidget(grupo_tabla)

        # --- Resumen ---
        grupo_resumen = QtGui.QGroupBox("Resumen de Espacios Calculados")
        layout_resumen = QtGui.QVBoxLayout(grupo_resumen)
        self.lbl_resumen = QtGui.QLabel("Sin divisiones configuradas.")
        self.lbl_resumen.setWordWrap(True)
        self.lbl_resumen.setStyleSheet(
            "QLabel { background-color: #f0f0f0; padding: 8px; "
            "border: 1px solid #ccc; font-family: monospace; }")
        layout_resumen.addWidget(self.lbl_resumen)
        main_layout.addWidget(grupo_resumen)

        # --- Sub-panel de hijos (oculto por defecto) ---
        self.group_hijos = QtGui.QGroupBox("Sub-división del Espacio Seleccionado")
        self.group_hijos.setVisible(False)
        layout_hijos = QtGui.QVBoxLayout(self.group_hijos)

        self.lbl_hijo_info = QtGui.QLabel("")
        self.lbl_hijo_info.setWordWrap(True)
        layout_hijos.addWidget(self.lbl_hijo_info)

        self.combo_hijo_eje = QtGui.QComboBox()
        self.combo_hijo_eje.addItems(["Y (Horizontal)", "X (Vertical)"])
        layout_hijos.addWidget(QtGui.QLabel("Eje de sub-división:"))
        layout_hijos.addWidget(self.combo_hijo_eje)

        self.table_hijos = SpacesTableWidget()
        self.table_hijos.setMaximumHeight(200)
        layout_hijos.addWidget(self.table_hijos)

        layout_hijos_botones = QtGui.QHBoxLayout()
        btn_hijo_add = QtGui.QPushButton("+ Añadir")
        btn_hijo_add.clicked.connect(self._agregar_hijo)
        btn_hijo_remove = QtGui.QPushButton("- Eliminar")
        btn_hijo_remove.clicked.connect(self._eliminar_hijo)
        btn_hijo_half = QtGui.QPushButton("1/2")
        btn_hijo_half.clicked.connect(lambda: self._dividir_hijo(2))
        btn_hijo_third = QtGui.QPushButton("1/3")
        btn_hijo_third.clicked.connect(lambda: self._dividir_hijo(3))
        btn_close_hijos = QtGui.QPushButton("Cerrar")
        btn_close_hijos.clicked.connect(self._cerrar_hijos)
        layout_hijos_botones.addWidget(btn_hijo_add)
        layout_hijos_botones.addWidget(btn_hijo_remove)
        layout_hijos_botones.addWidget(btn_hijo_half)
        layout_hijos_botones.addWidget(btn_hijo_third)
        layout_hijos_botones.addWidget(btn_close_hijos)
        layout_hijos.addLayout(layout_hijos_botones)

        main_layout.addWidget(self.group_hijos)
        main_layout.addStretch()

        return widget

    def _cargar_valores(self, obj):
        """Carga las propiedades del FeaturePython en los controles."""
        self._building = True
        prop = "EspaciosX" if self._current_axis == "X" else "EspaciosY"
        json_str = getattr(obj, prop, "") or ""
        self._rows = []
        nodes = deserializar_espacios(json_str)
        for node in nodes:
            self._rows.append(EspacioRow(node, depth=0))
        self._refrescar_tabla()
        self._actualizar_resumen()
        self._building = False

    def _on_eje_cambiado(self, index):
        """Cambia entre eje X e Y."""
        if self._building:
            return
        self._building = True
        self._current_axis = "X" if index == 0 else "Y"
        if self.obj:
            prop = "EspaciosX" if self._current_axis == "X" else "EspaciosY"
            json_str = getattr(self.obj, prop, "") or ""
            nodes = deserializar_espacios(json_str)
            self._rows = []
            for node in nodes:
                self._rows.append(EspacioRow(node, depth=0))
        self._refrescar_tabla()
        self._actualizar_resumen()
        self._building = False

    def _refrescar_tabla(self):
        """Reconstruye la tabla desde self._rows."""
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for i, row in enumerate(self._rows):
            self.table.insertRow(i)
            self._pintar_fila(self.table, i, row)
        self.table.blockSignals(False)

    def _pintar_fila(self, table, row_idx, esp_row):
        """Pinta una fila en la tabla con los datos de EspacioRow."""
        node = esp_row.node
        indent = "  " * esp_row.depth

        # Columna Tipo
        tipo_item = QtGui.QTableWidgetItem(
            indent + TIPOS_LABELS.get(node.space_type, node.space_type))
        tipo_item.setFlags(tipo_item.flags() & ~QtCore.Qt.ItemIsEditable)
        tipo_item.setData(QtCore.Qt.UserRole, row_idx)
        table.setItem(row_idx, COL_TIPO, tipo_item)

        # Columna Valor (editable o no)
        if node.space_type == ESPACIO_FIJO:
            valor_item = QtGui.QTableWidgetItem(f"{node.value:.1f}")
        elif node.space_type == ESPACIO_IGUALES:
            valor_item = QtGui.QTableWidgetItem(str(int(node.value)))
        else:
            valor_item = QtGui.QTableWidgetItem("—")
            valor_item.setFlags(valor_item.flags() & ~QtCore.Qt.ItemIsEditable)
        table.setItem(row_idx, COL_VALOR, valor_item)

        # Columna Resumen (calculada)
        resumen = node.space_id
        if node.space_type == ESPACIO_IGUALES and node.children:
            resumen = f"{len(node.children)} partes"
        elif node.space_type == ESPACIO_FIJO:
            resumen = f"{node.value:.0f}mm fijos"
        res_item = QtGui.QTableWidgetItem(resumen)
        res_item.setFlags(res_item.flags() & ~QtCore.Qt.ItemIsEditable)
        table.setItem(row_idx, COL_RESUMEN, res_item)

        # Columna Acciones (botones)
        widget_acciones = QtGui.QWidget()
        layout_acciones = QtGui.QHBoxLayout(widget_acciones)
        layout_acciones.setContentsMargins(2, 2, 2, 2)
        layout_acciones.setSpacing(2)

        btn_nid = QtGui.QPushButton("...")
        btn_nid.setMaximumWidth(30)
        btn_nid.setToolTip("Sub-configurar hijos")
        btn_nid.clicked.connect(
            lambda checked, r=row_idx: self._abrir_hijos(r))
        layout_acciones.addWidget(btn_nid)

        table.setCellWidget(row_idx, COL_ACCIONES, widget_acciones)

    def _on_cell_changed(self, row, col):
        """Cuando el usuario edita una celda, actualiza el nodo."""
        if self._building:
            return
        if col == COL_VALOR and row < len(self._rows):
            item = self.table.item(row, col)
            if item:
                texto = item.text().strip()
                try:
                    valor = float(texto)
                    self._rows[row].node.value = valor
                except ValueError:
                    pass
            self._actualizar_resumen()

    def _agregar_espacio(self):
        """Añade una nueva fila de espacio."""
        n = len(self._rows)
        node = SpaceNode(
            space_type=ESPACIO_RESTANTE,
            space_id=f"V{n+1}")
        self._rows.append(EspacioRow(node, depth=0))
        self.table.insertRow(n)
        self._pintar_fila(self.table, n, self._rows[n])
        self._actualizar_resumen()

    def _eliminar_espacio(self):
        """Elimina la fila seleccionada."""
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        if 0 <= row < len(self._rows):
            self._rows.pop(row)
            self._refrescar_tabla()
            self._actualizar_resumen()

    def _dividir_seleccion(self, n_partes):
        """Divide el espacio seleccionado en N partes iguales."""
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        if 0 <= row < len(self._rows):
            old = self._rows[row]
            node = SpaceNode(
                space_type=ESPACIO_IGUALES,
                value=float(n_partes),
                space_id=old.node.space_id)
            self._rows[row] = EspacioRow(node, depth=old.depth)
            self._refrescar_tabla()
            self._actualizar_resumen()

    def _abrir_hijos(self, row_idx):
        """Abre el sub-panel de hijos para un espacio."""
        if row_idx >= len(self._rows):
            return
        self._selected_parent_row = row_idx
        parent = self._rows[row_idx]
        self.group_hijos.setVisible(True)
        self.lbl_hijo_info.setText(
            f"Sub-dividiendo: <b>{parent.node.space_id}</b> "
            f"({TIPOS_LABELS.get(parent.node.space_type, '')})")

        self.table_hijos.blockSignals(True)
        self.table_hijos.setRowCount(0)
        for i, child in enumerate(parent.children_rows):
            self.table_hijos.insertRow(i)
            self._pintar_fila(self.table_hijos, i, child)
        self.table_hijos.blockSignals(False)

    def _subconfigurar(self):
        """Abre sub-panel para la fila seleccionada."""
        selected = self.table.selectedItems()
        if not selected:
            return
        self._abrir_hijos(selected[0].row())

    def _agregar_hijo(self):
        """Añade un hijo al espacio padre seleccionado."""
        if not hasattr(self, '_selected_parent_row'):
            return
        parent_row = self._selected_parent_row
        if parent_row >= len(self._rows):
            return
        parent = self._rows[parent_row]
        n = len(parent.children_rows)
        child = SpaceNode(
            space_type=ESPACIO_RESTANTE,
            space_id=f"{parent.node.space_id}.{n+1}")
        parent.children_rows.append(
            EspacioRow(child, depth=parent.depth + 1))
        parent.node.children = [c.node for c in parent.children_rows]
        self._abrir_hijos(parent_row)
        self._actualizar_resumen()

    def _eliminar_hijo(self):
        """Elimina un hijo del espacio padre."""
        if not hasattr(self, '_selected_parent_row'):
            return
        selected = self.table_hijos.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        parent_row = self._selected_parent_row
        parent = self._rows[parent_row]
        if 0 <= row < len(parent.children_rows):
            parent.children_rows.pop(row)
            parent.node.children = [c.node for c in parent.children_rows]
            self._abrir_hijos(parent_row)
            self._actualizar_resumen()

    def _dividir_hijo(self, n_partes):
        """Divide un espacio hijo en N partes iguales."""
        if not hasattr(self, '_selected_parent_row'):
            return
        selected = self.table_hijos.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        parent_row = self._selected_parent_row
        parent = self._rows[parent_row]
        if 0 <= row < len(parent.children_rows):
            old = parent.children_rows[row]
            child = SpaceNode(
                space_type=ESPACIO_IGUALES,
                value=float(n_partes),
                space_id=old.node.space_id)
            parent.children_rows[row] = EspacioRow(
                child, depth=old.depth)
            parent.node.children = [c.node for c in parent.children_rows]
            self._abrir_hijos(parent_row)
            self._actualizar_resumen()

    def _cerrar_hijos(self):
        """Cierra el sub-panel de hijos."""
        self.group_hijos.setVisible(False)
        if hasattr(self, '_selected_parent_row'):
            parent_row = self._selected_parent_row
            if parent_row < len(self._rows):
                parent = self._rows[parent_row]
                self.table.item(parent_row, COL_RESUMEN).setText(
                    f"{len(parent.children_rows)} hijos")

    def _actualizar_resumen(self):
        """Calcula y muestra el resumen de espacios."""
        if not self.obj:
            self.lbl_resumen.setText("Sin objeto seleccionado.")
            return

        espesor = float(self.obj.Espesor)
        if self._current_axis == "X":
            espacio_total = float(self.obj.Ancho) - (espesor * 2)
        else:
            lat_height = float(self.obj.Alto)
            if self.obj.Tapa == "externo":
                lat_height -= espesor
            if self.obj.Base == "externo":
                lat_height -= espesor
            espacio_total = lat_height

        nodes = [r.node for r in self._rows]
        json_str = serializar_espacios(nodes)
        info = calcular_espacio_libre(json_str, espacio_total, espesor)

        texto = f"Espacio total: {espacio_total:.1f}mm\n"
        texto += f"Espacios definidos: {info['n_espacios']}\n"
        texto += f"Total libre: {info['total_libre']:.1f}mm\n"
        texto += f"Último vano: {info['ultimo_vano']:.1f}mm\n\n"
        texto += info['texto']
        self.lbl_resumen.setText(texto)

    def accept(self):
        """Aplicar cambios y cerrar el panel."""
        if not self.obj:
            return True
        try:
            App.ActiveDocument.openTransaction("Editar Espacios COCO")
            nodes = [r.node for r in self._rows]
            json_str = serializar_espacios(nodes)
            if self._current_axis == "X":
                self.obj.EspaciosX = json_str
            else:
                self.obj.EspaciosY = json_str
            App.ActiveDocument.commitTransaction()
            App.ActiveDocument.recompute()
            Gui.ActiveDocument.resetEdit()
        except Exception as e:
            App.Console.PrintError(
                f"[VDO] Error aceptando espacios: {e}\n")
            App.ActiveDocument.abortTransaction()
        return True

    def reject(self):
        """Cancelar y cerrar el panel."""
        try:
            App.ActiveDocument.abortTransaction()
        except Exception:
            pass
        Gui.ActiveDocument.resetEdit()
        return True

    def clicked(self, button):
        pass

    def getStandardButtons(self):
        return QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel

    def helpRequested(self):
        pass
