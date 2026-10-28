# -*- coding: utf-8 -*-
# =====================================================================
# vdo_coco_divisions_task.py
# Editor de la matriz de vanos del COCO:
#   preview 2D + botonera X/Y + árbol de vanos + inspector.
# =====================================================================

import json

from PySide import QtCore, QtGui, QtWidgets

import vdo_reengrose as VDO_RE

import vdo_defaults as VDO_D
from vdo_layout import (
    Layout, LayoutError, AXIS_X, AXIS_Y, cavidad_interior, resolve_layout,
)
from vdo_coco_preview2d import CocoPreview2D


ROLE_DATA = QtCore.Qt.UserRole + 1


class DivisionesEditor(QtWidgets.QWidget):
    """Editor único de divisiones, sin tablas de filas."""

    changed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = Layout()
        self.inner_w = 0.0
        self.inner_h = 0.0
        self.outer_w = 0.0
        self.outer_h = 0.0
        self.thickness = float(VDO_D.ESPESOR_DEFAULT)
        self._resolved = None
        self._resolved_map = {}
        self._items_by_label = {}
        self._items_by_key = {}
        self._selected_key = ("cell", "x1", "y1")
        self._selected_data = None
        self._building = False
        self._legacy_warnings = []
        self.reengroses = {}
        self._selected_reengrose_key = None

        self._crear_widget()
        self._rebuild()

    # -----------------------------------------------------------------
    # Construcción
    # -----------------------------------------------------------------
    def _crear_widget(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.preview = CocoPreview2D()
        self.preview.setMinimumHeight(190)
        self.preview.cellClicked.connect(self._seleccionar_por_label)
        layout.addWidget(self.preview, 1)

        grupo_matriz = QtWidgets.QGroupBox("Matriz de vanos")
        fila = QtWidgets.QHBoxLayout(grupo_matriz)
        self.lbl_columnas = QtWidgets.QLabel("Columnas raíz: 1")
        self.lbl_filas = QtWidgets.QLabel("Filas raíz: 1")
        self.btn_x_add = QtWidgets.QPushButton("+X")
        self.btn_x_del = QtWidgets.QPushButton("−X")
        self.btn_y_add = QtWidgets.QPushButton("+Y")
        self.btn_y_del = QtWidgets.QPushButton("−Y")
        self.btn_x_add.setToolTip("Añadir columna a la derecha")
        self.btn_x_del.setToolTip("Quitar la última columna (derecha)")
        self.btn_y_add.setToolTip("Añadir fila arriba")
        self.btn_y_del.setToolTip("Quitar la última fila (arriba)")
        for btn in (self.btn_x_add, self.btn_x_del,
                    self.btn_y_add, self.btn_y_del):
            btn.setMaximumWidth(46)
        fila.addWidget(self.lbl_columnas)
        fila.addWidget(self.btn_x_del)
        fila.addWidget(self.btn_x_add)
        fila.addSpacing(14)
        fila.addWidget(self.lbl_filas)
        fila.addWidget(self.btn_y_del)
        fila.addWidget(self.btn_y_add)
        fila.addStretch()
        layout.addWidget(grupo_matriz)

        cuerpo = QtWidgets.QHBoxLayout()
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(
            ["Vano", "X libre", "Y libre", "Subdivisión"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(
            QtWidgets.QAbstractItemView.SingleSelection)
        self.tree.setUniformRowHeights(True)
        self.tree.setToolTip(
            "Árbol de vanos: selecciona una celda para editar sus medidas "
            "o una fila para fijar su alto.")
        cabecera = self.tree.header()
        cabecera.setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeToContents)
        cabecera.setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeToContents)
        cabecera.setSectionResizeMode(
            2, QtWidgets.QHeaderView.ResizeToContents)
        cabecera.setSectionResizeMode(
            3, QtWidgets.QHeaderView.Stretch)
        cuerpo.addWidget(self.tree, 2)

        self.inspector = QtWidgets.QGroupBox("Inspector del vano")
        self.form = QtWidgets.QFormLayout(self.inspector)
        self.lbl_sel = QtWidgets.QLabel("Sin selección.")
        self.lbl_sel.setWordWrap(True)
        self.form.addRow(self.lbl_sel)

        self.chk_col_fixed = QtWidgets.QCheckBox("Fijar ancho de columna")
        self.chk_col_fixed.setToolTip(
            "Fija el ancho de esta columna. El resto de columnas libres se "
            "reparten el espacio sobrante.")
        self.spin_col_fixed = self._spin_medida()
        self.spin_col_fixed.setToolTip(
            "Ancho fijo de la columna en milímetros, sin contar divisiones.")
        self.widget_col_fixed = self._fila_check_spin(
            self.chk_col_fixed, self.spin_col_fixed)
        self.form.addRow(self.widget_col_fixed)

        self.chk_row_fixed = QtWidgets.QCheckBox("Fijar alto de fila")
        self.chk_row_fixed.setToolTip(
            "Fija el alto de esta fila. El resto de filas libres se reparten "
            "el espacio sobrante.")
        self.spin_row_fixed = self._spin_medida()
        self.spin_row_fixed.setToolTip(
            "Alto fijo de la fila en milímetros, sin contar repisas.")
        self.widget_row_fixed = self._fila_check_spin(
            self.chk_row_fixed, self.spin_row_fixed)
        self.form.addRow(self.widget_row_fixed)

        self.chk_cell_fixed = QtWidgets.QCheckBox("Medida fija")
        self.chk_cell_fixed.setToolTip(
            "Fija la medida de este sub-vano. Si el sub-vano está "
            "subdividido, primero hay que editar el padre.")
        self.spin_cell_fixed = self._spin_medida()
        self.spin_cell_fixed.setToolTip(
            "Medida fija del sub-vano en milímetros.")
        self.widget_cell_fixed = self._fila_check_spin(
            self.chk_cell_fixed, self.spin_cell_fixed)
        self.form.addRow(self.widget_cell_fixed)

        self.chk_split = QtWidgets.QCheckBox("Subdividir este vano")
        self.chk_split.setToolTip(
            "Activa la subdivisión del vano seleccionado en el eje X o Y.")
        self.form.addRow(self.chk_split)

        self.widget_split = QtWidgets.QWidget()
        split_layout = QtWidgets.QFormLayout(self.widget_split)
        split_layout.setContentsMargins(16, 0, 0, 0)
        self.combo_axis = QtWidgets.QComboBox()
        self.combo_axis.addItem("X (columnas)", AXIS_X)
        self.combo_axis.addItem("Y (repisas)", AXIS_Y)
        self.combo_axis.setToolTip(
            "X divide en columnas verticales. Y divide en repisas "
            "horizontales.")
        self.spin_n = QtWidgets.QSpinBox()
        self.spin_n.setRange(2, 100)
        self.spin_n.setValue(2)
        self.spin_n.setToolTip(
            "Cantidad de partes iguales en que se subdivide el vano.")
        split_layout.addRow("Eje:", self.combo_axis)
        split_layout.addRow("N partes:", self.spin_n)
        self.form.addRow(self.widget_split)

        self.lbl_aviso = QtWidgets.QLabel("")
        self.lbl_aviso.setWordWrap(True)
        self.lbl_aviso.setStyleSheet("QLabel { color: #b03a2e; }")
        self.form.addRow(self.lbl_aviso)
        self.grupo_reengrose = self._crear_grupo_reengrose()
        self.form.addRow(self.grupo_reengrose)

        cuerpo.addWidget(self.inspector, 1)
        layout.addLayout(cuerpo, 2)

        self.lbl_resumen = QtWidgets.QLabel("")
        self.lbl_resumen.setWordWrap(True)
        self.lbl_resumen.setStyleSheet(
            "QLabel { background: #f0f0f0; padding: 6px; "
            "border: 1px solid #ccc; font-family: monospace; }")
        layout.addWidget(self.lbl_resumen)

        self.btn_x_add.clicked.connect(self._agregar_columna)
        self.btn_x_del.clicked.connect(self._quitar_columna)
        self.btn_y_add.clicked.connect(self._agregar_fila)
        self.btn_y_del.clicked.connect(self._quitar_fila)
        self.tree.itemSelectionChanged.connect(self._on_tree_selection)
        self.chk_col_fixed.toggled.connect(self._on_col_fixed)
        self.chk_row_fixed.toggled.connect(self._on_row_fixed)
        self.chk_cell_fixed.toggled.connect(self._on_cell_fixed)
        self.spin_col_fixed.valueChanged.connect(self._on_col_fixed)
        self.spin_row_fixed.valueChanged.connect(self._on_row_fixed)
        self.spin_cell_fixed.valueChanged.connect(self._on_cell_fixed)
        self.chk_split.toggled.connect(self._on_split_toggled)
        self.combo_axis.currentIndexChanged.connect(self._on_axis_changed)
        self.spin_n.valueChanged.connect(self._on_n_changed)
        self.combo_elemento_reengrose.currentIndexChanged.connect(
            self._on_reengrose_element_changed)
        self.chk_reengrose.toggled.connect(self._on_reengrose_changed)
        self.combo_re_orientacion.currentIndexChanged.connect(
            self._on_reengrose_changed)
        self.combo_re_cara.currentIndexChanged.connect(
            self._on_reengrose_changed)
        self.combo_re_alineacion.currentIndexChanged.connect(
            self._on_reengrose_changed)
        self.combo_re_modo.currentIndexChanged.connect(
            self._on_reengrose_changed)
        self.combo_re_alcance.currentIndexChanged.connect(
            self._on_reengrose_changed)
        self.combo_re_politica.currentIndexChanged.connect(
            self._on_reengrose_changed)
        self.combo_re_prioridad.currentIndexChanged.connect(
            self._on_reengrose_changed)
        self.spin_re_ancho.editingFinished.connect(self._on_reengrose_changed)
        self.spin_re_espesor.editingFinished.connect(
            self._on_reengrose_changed)

    def _crear_grupo_reengrose(self):
        grupo = QtWidgets.QGroupBox("Reengrose / Refuerzo")
        grid = QtWidgets.QGridLayout(grupo)

        grid.addWidget(QtWidgets.QLabel("Elemento:"), 0, 0)
        self.combo_elemento_reengrose = QtWidgets.QComboBox()
        self.combo_elemento_reengrose.setToolTip(
            "Elegí el lateral, la base, el techo o una división para "
            "configurar su refuerzo. Los vanos muestran la luz neta; el "
            "refuerzo pertenece a la pieza que lo lleva.")
        grid.addWidget(self.combo_elemento_reengrose, 0, 1, 1, 3)

        self.chk_reengrose = QtWidgets.QCheckBox("Activar reengrose")
        self.chk_reengrose.setToolTip(
            "<b>Reengrose / Pacha</b><br>"
            "Agrega una tira o duplicado sobre una cara de la pieza. "
            "Ejemplo: 50–70 mm en el nudo de bisagras de una división.")
        grid.addWidget(self.chk_reengrose, 1, 0, 1, 4)

        grid.addWidget(QtWidgets.QLabel("Orientación:"), 2, 0)
        self.combo_re_orientacion = QtWidgets.QComboBox()
        self.combo_re_orientacion.addItem("Paralela", "paralela")
        self.combo_re_orientacion.addItem("Transversal", "transversal")
        self.combo_re_orientacion.setToolTip(
            "Paralela: la tira corre a lo largo de la pieza. Transversal: "
            "cruza el ancho, por ejemplo un tope horizontal.")
        grid.addWidget(self.combo_re_orientacion, 2, 1)

        grid.addWidget(QtWidgets.QLabel("Ancho:"), 2, 2)
        self.spin_re_ancho = QtWidgets.QDoubleSpinBox()
        self.spin_re_ancho.setRange(1.0, 5000.0)
        self.spin_re_ancho.setDecimals(1)
        self.spin_re_ancho.setSuffix(" mm")
        self.spin_re_ancho.setValue(70.0)
        self.spin_re_ancho.setToolTip(
            "Ancho de la tira. 50–70 mm para bisagras; 100 mm para zócalos.")
        grid.addWidget(self.spin_re_ancho, 2, 3)

        grid.addWidget(QtWidgets.QLabel("Espesor:"), 3, 0)
        self.spin_re_espesor = QtWidgets.QDoubleSpinBox()
        self.spin_re_espesor.setRange(0.0, 100.0)
        self.spin_re_espesor.setDecimals(1)
        self.spin_re_espesor.setSuffix(" mm")
        self.spin_re_espesor.setSpecialValueText("Auto")
        self.spin_re_espesor.setValue(0.0)
        self.spin_re_espesor.setToolTip(
            "Espesor de la tira. En <b>Auto</b> usa el mismo espesor que la "
            "pieza base. Editable para proyectos especiales.")
        grid.addWidget(self.spin_re_espesor, 3, 1)

        grid.addWidget(QtWidgets.QLabel("Cara:"), 3, 2)
        self.combo_re_cara = QtWidgets.QComboBox()
        self.combo_re_cara.addItem("Cara A (+)", "cara_a")
        self.combo_re_cara.addItem("Cara B (−)", "cara_b")
        self.combo_re_cara.addItem("Ambos lados", "ambos")
        self.combo_re_cara.setToolTip(
            "Cara de la pieza donde se pega el refuerzo. En una división, "
            "A y B son los dos lados que miran a los vanos vecinos.")
        grid.addWidget(self.combo_re_cara, 3, 3)

        grid.addWidget(QtWidgets.QLabel("Alineación:"), 4, 0)
        self.combo_re_alineacion = QtWidgets.QComboBox()
        self.combo_re_alineacion.addItem("Frente", "frente")
        self.combo_re_alineacion.addItem("Centrado", "centrado")
        self.combo_re_alineacion.addItem("Fondo", "fondo")
        self.combo_re_alineacion.setToolTip(
            "Posición de la tira sobre la cara: junto al frente de la "
            "puerta, centrada o contra el fondo del mueble.")
        grid.addWidget(self.combo_re_alineacion, 4, 1)

        grid.addWidget(QtWidgets.QLabel("Fabricación:"), 4, 2)
        self.combo_re_modo = QtWidgets.QComboBox()
        self.combo_re_modo.addItem("Independiente", "independiente")
        self.combo_re_modo.addItem("Pacha", "pacha")
        self.combo_re_modo.setToolTip(
            "Independiente: tira cortada y canteada aparte. Pacha: se pega "
            "en bruto y se cantea como un bloque macizo.")
        grid.addWidget(self.combo_re_modo, 4, 3)

        grid.addWidget(QtWidgets.QLabel("Alcance:"), 5, 0)
        self.combo_re_alcance = QtWidgets.QComboBox()
        self.combo_re_alcance.addItem("Parcial (tira)", "parcial")
        self.combo_re_alcance.addItem("Total (área completa)", "total")
        self.combo_re_alcance.setToolTip(
            "Parcial: refuerzo en una franja. Total: duplica toda la cara "
            "de la pieza.")
        grid.addWidget(self.combo_re_alcance, 5, 1)

        grid.addWidget(QtWidgets.QLabel("Choque núcleo:"), 5, 2)
        self.combo_re_politica = QtWidgets.QComboBox()
        self.combo_re_politica.addItem(
            "Retroceso (corte recto)", "retroceso")
        self.combo_re_politica.addItem(
            "Mocheo (cajeado)", "mocheo")
        self.combo_re_politica.addItem(
            "Interrumpir tira", "interrumpir_tira")
        self.combo_re_politica.setToolTip(
            "<b>Choque contra panel núcleo</b><br>"
            "Retroceso: el panel perpendicular termina a 90° en la cara "
            "trasera de la tira. Mocheo: conserva su profundidad y se "
            "cajea en escuadra. Interrumpir tira: el panel pasa continuo "
            "hasta el frente y la tira se corta en tramos.")
        grid.addWidget(self.combo_re_politica, 5, 3)

        grid.addWidget(QtWidgets.QLabel("Encuentro de tiras:"), 6, 0)
        self.combo_re_prioridad = QtWidgets.QComboBox()
        self.combo_re_prioridad.addItem(
            "Vertical domina (montantes continuos)", "vertical_domina")
        self.combo_re_prioridad.addItem(
            "Horizontal domina (techo/base continuos)", "horizontal_domina")
        self.combo_re_prioridad.addItem(
            "Inglete a 45° (marco continuo)", "inglete_45")
        self.combo_re_prioridad.setToolTip(
            "<b>Matriz de prioridad de encuentro</b><br>"
            "Vertical domina: las tiras verticales pasan continuas y las "
            "horizontales hacen tope a 90° contra ellas. Horizontal domina: "
            "al revés. Inglete 45°: ambas tiras se biselan en la esquina.")
        grid.addWidget(self.combo_re_prioridad, 6, 1, 1, 3)

        self.lbl_reengrose = QtWidgets.QLabel("Sin reengrose.")
        self.lbl_reengrose.setWordWrap(True)
        self.lbl_reengrose.setStyleSheet(
            "QLabel { background: #f4f4f2; padding: 5px; "
            "border: 1px solid #d0d0d0; }")
        grid.addWidget(self.lbl_reengrose, 7, 0, 1, 4)
        return grupo

    @staticmethod
    def _spin_medida():
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(0.0, 100000.0)
        spin.setDecimals(1)
        spin.setSuffix(" mm")
        return spin

    @staticmethod
    def _fila_check_spin(check, spin):
        widget = QtWidgets.QWidget()
        fila = QtWidgets.QHBoxLayout(widget)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.addWidget(check)
        fila.addWidget(spin, 1)
        return widget

    # -----------------------------------------------------------------
    # API para el panel COCO
    # -----------------------------------------------------------------
    def set_dimensions(self, alto, ancho, espesor):
        self.outer_w = float(ancho)
        self.outer_h = float(alto)
        self.thickness = float(espesor)
        cavidad = cavidad_interior(alto, ancho, espesor)
        self.inner_w = cavidad["ancho"]
        self.inner_h = cavidad["alto"]
        self._rebuild()

    def cargar_desde_objeto(self, obj):
        texto = getattr(obj, "VDO_Divisiones", "") or ""
        self._legacy_warnings = []
        self.layout = Layout.loads(texto)
        self.reengroses = self._leer_reengroses(obj)
        self._selected_reengrose_key = None
        self._selected_key = ("cell",
                              self.layout.columns[0].id,
                              self.layout.rows[0].id)
        self._rebuild()

    def dumps(self):
        return self.layout.dumps()

    def dumps_reengroses(self):
        return json.dumps(self.reengroses, ensure_ascii=False)

    @staticmethod
    def _leer_reengroses(obj):
        texto = getattr(obj, "VDO_Reengrose_JSON", "") or "{}"
        try:
            datos = json.loads(texto) if isinstance(texto, str) else dict(texto)
        except (TypeError, ValueError):
            return {}
        return datos if isinstance(datos, dict) else {}

    def resumen(self):
        if self._resolved is None:
            return "Sin dimensiones."
        lineas = [self._resolved.summary()]
        if self._legacy_warnings:
            lineas.extend("⚠ " + w for w in self._legacy_warnings)
        return "\n".join(lineas)

    def tiene_overflow(self):
        return bool(self._resolved and self._resolved.overflow)

    # -----------------------------------------------------------------
    # Resolución y árbol
    # -----------------------------------------------------------------
    def _rebuild(self):
        if self.inner_w <= 0 or self.inner_h <= 0:
            self._resolved = resolve_layout(
                self.layout, max(0.0, self.inner_w),
                max(0.0, self.inner_h), self.thickness,
                reengroses=self.reengroses)
        else:
            self._resolved = resolve_layout(
                self.layout, self.inner_w, self.inner_h, self.thickness,
                reengroses=self.reengroses)
        self._resolved_map = {
            cell.label: cell for cell in self._resolved.walk_cells()
        }
        self._items_by_label = {}
        self._items_by_key = {}
        self._pintar_arbol()
        self.preview.set_layout(
            self._resolved, self.outer_w, self.outer_h,
            selected=self._label_seleccionado())
        self.lbl_columnas.setText(
            f"Columnas raíz: {len(self.layout.columns)}")
        self.lbl_filas.setText(f"Filas raíz: {len(self.layout.rows)}")
        self.lbl_resumen.setText(self.resumen())
        self._poblar_elementos_reengrose()
        self._restaurar_seleccion()

    def _pintar_arbol(self):
        self.tree.blockSignals(True)
        self.tree.clear()
        root = QtWidgets.QTreeWidgetItem([
            f"COCO — Matriz {len(self.layout.columns)} × "
            f"{len(self.layout.rows)}", "", "", ""])
        root.setFlags(root.flags() & ~QtCore.Qt.ItemIsSelectable)
        self.tree.addTopLevelItem(root)

        elementos = QtWidgets.QTreeWidgetItem([
            "Elementos / refuerzos", "", "", "Reengrose"])
        elementos.setFlags(elementos.flags() & ~QtCore.Qt.ItemIsSelectable)
        for clave, etiqueta in self._elementos_reengrose():
            item = QtWidgets.QTreeWidgetItem([
                etiqueta, "", "", "reengrose"])
            item.setData(0, ROLE_DATA, {
                "kind": "elemento_reengrose", "clave": clave})
            item.setToolTip(
                0, f"{etiqueta}\nConfigurar reengrose de esta pieza.")
            elementos.addChild(item)
            self._items_by_key[("elemento", clave)] = item
        root.addChild(elementos)

        for j, row in enumerate(self._resolved.rows):
            row_item = QtWidgets.QTreeWidgetItem([
                f"Y{j + 1}",
                "",
                f"{row.size:.1f}",
                "fijo" if row.fixed is not None else "libre",
            ])
            row_item.setData(0, ROLE_DATA, {
                "kind": "row", "row_index": j, "row": row,
            })
            row_item.setToolTip(
                0, f"Fila Y{j + 1}: alto libre {row.size:.1f} mm")
            root.addChild(row_item)
            self._items_by_key[("row", j)] = row_item

            for i, col in enumerate(self._resolved.columns):
                cell = self.layout.get_cell(i, j)
                resuelto = self._resolved_map.get(cell.label) if cell else None
                if resuelto is None:
                    continue
                item = self._crear_item_celda(
                    resuelto, row_item, kind="cell",
                    col_index=i, row_index=j, parent_axis=None)
                self._items_by_key[
                    ("cell", self.layout.columns[i].id,
                     self.layout.rows[j].id)] = item

        self.tree.expandAll()
        self.tree.blockSignals(False)

    def _crear_item_celda(self, resuelto, parent_item, kind,
                          col_index=None, row_index=None,
                          parent_axis=None):
        cell = resuelto.cell
        if cell.axis and cell.children:
            division = f"{len(cell.children)} {cell.axis}"
        else:
            division = "vacío"
        item = QtWidgets.QTreeWidgetItem([
            cell.label,
            f"{resuelto.w:.1f}",
            f"{resuelto.h:.1f}",
            division,
        ])
        data = {
            "kind": kind,
            "cell": cell,
            "col_index": col_index,
            "row_index": row_index,
            "parent_axis": parent_axis,
            "level": resuelto.level,
        }
        item.setData(0, ROLE_DATA, data)
        item.setToolTip(
            0, f"{cell.label}\nX libre: {resuelto.w:.1f} mm\n"
               f"Y libre: {resuelto.h:.1f} mm")
        parent_item.addChild(item)
        self._items_by_label[cell.label] = item
        key = ("nested", cell.px, cell.py)
        self._items_by_key[key] = item

        for child in resuelto.children:
            self._crear_item_celda(
                child, item, kind="nested",
                parent_axis=cell.axis)
        return item

    def _label_seleccionado(self):
        data = self._selected_data
        if not data:
            return None
        if data["kind"] == "row":
            return None
        cell = data.get("cell")
        return cell.label if cell is not None else None

    def _restaurar_seleccion(self):
        item = self._items_by_key.get(self._selected_key)
        if item is None:
            # Fallback: primera celda raíz.
            key = ("cell", self.layout.columns[0].id,
                   self.layout.rows[0].id)
            item = self._items_by_key.get(key)
            self._selected_key = key
        if item is not None:
            self.tree.blockSignals(True)
            self.tree.setCurrentItem(item)
            self.tree.blockSignals(False)
            self._seleccionar_item(item)

    # -----------------------------------------------------------------
    # Selección
    # -----------------------------------------------------------------
    def _on_tree_selection(self):
        items = self.tree.selectedItems()
        if not items:
            return
        self._seleccionar_item(items[0])

    def _seleccionar_item(self, item):
        data = item.data(0, ROLE_DATA)
        if not data:
            return
        if data.get("kind") == "elemento_reengrose":
            self._selected_data = data
            clave = data["clave"]
            self._selected_key = ("elemento", clave)
            self._selected_reengrose_key = clave
            idx = self.combo_elemento_reengrose.findData(clave)
            if idx >= 0:
                self._building = True
                self.combo_elemento_reengrose.setCurrentIndex(idx)
                self._building = False
            self._cargar_reengrose_controls(clave)
            self.preview.set_selected(None)
            return
        self._selected_data = data
        cell = data.get("cell")
        if data["kind"] == "row":
            self._selected_key = ("row", data["row_index"])
        elif data["kind"] == "cell":
            self._selected_key = (
                "cell", self.layout.columns[data["col_index"]].id,
                self.layout.rows[data["row_index"]].id)
        else:
            self._selected_key = ("nested", cell.px, cell.py)
        self.preview.set_selected(
            cell.label if cell is not None else None)
        self._actualizar_inspector()

    def _seleccionar_por_label(self, label):
        item = self._items_by_label.get(label)
        if item is None:
            return
        self.tree.blockSignals(True)
        self.tree.setCurrentItem(item)
        self.tree.blockSignals(False)
        self._seleccionar_item(item)

    # -----------------------------------------------------------------
    # Inspector
    # -----------------------------------------------------------------
    def _actualizar_inspector(self):
        data = self._selected_data
        if not data:
            self.lbl_sel.setText("Sin selección.")
            return
        self._building = True
        kind = data["kind"]
        cell = data.get("cell")
        self.widget_col_fixed.setVisible(kind == "cell")
        self.widget_row_fixed.setVisible(kind in ("cell", "row"))
        self.widget_cell_fixed.setVisible(kind == "nested")
        self.lbl_aviso.setText("")

        if kind == "row":
            row = data["row"]
            self.lbl_sel.setText(f"Fila Y{data['row_index'] + 1}")
            self.chk_row_fixed.setChecked(row.fixed is not None)
            self.spin_row_fixed.setValue(
                row.fixed if row.fixed is not None else row.size)
            self.chk_split.setChecked(False)
            self.chk_split.setEnabled(False)
            self.widget_split.setVisible(False)
            self.spin_row_fixed.setEnabled(row.fixed is not None)
        else:
            resuelto = self._resolved_map.get(cell.label)
            self.lbl_sel.setText(
                f"Vano {cell.label}\nX libre: {resuelto.w:.1f} mm · "
                f"Y libre: {resuelto.h:.1f} mm")
            self.chk_split.setEnabled(True)
            self.chk_split.setChecked(bool(cell.axis and cell.children))
            self.widget_split.setVisible(bool(cell.axis and cell.children))
            if cell.axis and cell.children:
                idx = 0 if cell.axis == AXIS_X else 1
                self.combo_axis.setCurrentIndex(idx)
                self.spin_n.setValue(len(cell.children))
            else:
                self.combo_axis.setCurrentIndex(
                    0 if self.combo_axis.currentData() != AXIS_Y else 1)
                self.spin_n.setValue(2)

            if kind == "cell":
                col = self.layout.columns[data["col_index"]]
                row = self.layout.rows[data["row_index"]]
                self.lbl_sel.setText(
                    f"Vano {cell.label} · columna X{data['col_index'] + 1} · "
                    f"fila Y{data['row_index'] + 1}\n"
                    f"X libre: {resuelto.w:.1f} mm · "
                    f"Y libre: {resuelto.h:.1f} mm")
                self.chk_col_fixed.setChecked(col.fixed is not None)
                self.spin_col_fixed.setValue(
                    col.fixed if col.fixed is not None else resuelto.w)
                self.spin_col_fixed.setEnabled(col.fixed is not None)
                self.chk_row_fixed.setChecked(row.fixed is not None)
                self.spin_row_fixed.setValue(
                    row.fixed if row.fixed is not None else resuelto.h)
                self.spin_row_fixed.setEnabled(row.fixed is not None)
                self.widget_cell_fixed.setVisible(False)
            else:
                axis = data.get("parent_axis")
                self.lbl_sel.setText(
                    f"Vano {cell.label} · subdivisión local\n"
                    f"X libre: {resuelto.w:.1f} mm · "
                    f"Y libre: {resuelto.h:.1f} mm")
                self.chk_cell_fixed.setText(
                    "Medida fija en X" if axis == AXIS_X
                    else "Medida fija en Y")
                base = resuelto.w if axis == AXIS_X else resuelto.h
                self.chk_cell_fixed.setChecked(cell.fixed is not None)
                self.spin_cell_fixed.setValue(
                    cell.fixed if cell.fixed is not None else base)
                self.spin_cell_fixed.setEnabled(
                    cell.fixed is not None and not cell.axis)
                self.chk_cell_fixed.setEnabled(not cell.axis)
                if cell.axis:
                    self.lbl_aviso.setText(
                        "Vano subdividido: su medida exterior está "
                        "congelada. Para cambiarla, edita el padre.")

        self._building = False
        self._actualizar_aviso_overflow()

    def _actualizar_aviso_overflow(self):
        if self._resolved and self._resolved.overflow:
            self.lbl_aviso.setText(
                "⚠ Medidas fijas fuera de presupuesto. "
                "Reduce alguna medida o el número de vanos.")
        elif self._legacy_warnings:
            self.lbl_aviso.setText(self._legacy_warnings[0])

    # -----------------------------------------------------------------
    # Acciones de matriz
    def _agregar_columna(self):
        self.layout.add_column()
        self._selected_key = ("cell",
                              self.layout.columns[-1].id,
                              self.layout.rows[0].id)
        self._rebuild_y_avisar()

    def _quitar_columna(self):
        if len(self.layout.columns) <= 1:
            return
        if (self.layout.column_has_subtree(len(self.layout.columns) - 1)
                and not self._confirmar(
                    "La última columna contiene subdivisiones.\n"
                    "¿Eliminarla con todo su contenido?")):
            return
        self.layout.remove_column()
        self._selected_key = ("cell",
                              self.layout.columns[-1].id,
                              self.layout.rows[0].id)
        self._rebuild_y_avisar()

    def _agregar_fila(self):
        self.layout.add_row()
        self._selected_key = ("cell",
                              self.layout.columns[0].id,
                              self.layout.rows[-1].id)
        self._rebuild_y_avisar()

    def _quitar_fila(self):
        if len(self.layout.rows) <= 1:
            return
        if (self.layout.row_has_subtree(len(self.layout.rows) - 1)
                and not self._confirmar(
                    "La última fila contiene subdivisiones.\n"
                    "¿Eliminarla con todo su contenido?")):
            return
        self.layout.remove_row()
        self._selected_key = ("cell",
                              self.layout.columns[0].id,
                              self.layout.rows[-1].id)
        self._rebuild_y_avisar()

    # -----------------------------------------------------------------
    # Acciones del inspector
    # -----------------------------------------------------------------
    def _on_col_fixed(self, *args):
        if self._building or not self._selected_data:
            return
        data = self._selected_data
        if data["kind"] != "cell":
            return
        valor = (self.spin_col_fixed.value()
                 if self.chk_col_fixed.isChecked() else None)
        self.layout.set_column_fixed(data["col_index"], valor)
        self._rebuild_y_avisar()

    def _on_row_fixed(self, *args):
        if self._building or not self._selected_data:
            return
        data = self._selected_data
        if data["kind"] not in ("cell", "row"):
            return
        valor = (self.spin_row_fixed.value()
                 if self.chk_row_fixed.isChecked() else None)
        self.layout.set_row_fixed(data["row_index"], valor)
        self._rebuild_y_avisar()

    def _on_cell_fixed(self, *args):
        if self._building or not self._selected_data:
            return
        data = self._selected_data
        if data["kind"] != "nested":
            return
        cell = data["cell"]
        if cell.axis:
            return
        valor = (self.spin_cell_fixed.value()
                 if self.chk_cell_fixed.isChecked() else None)
        self.layout.set_cell_fixed(cell, valor)
        self._rebuild_y_avisar()

    def _on_split_toggled(self, activo):
        if self._building or not self._selected_data:
            return
        data = self._selected_data
        cell = data.get("cell")
        if cell is None:
            return
        if not activo:
            if cell.children and not self._confirmar(
                    "Se eliminarán las subdivisiones de este vano.\n"
                    "¿Continuar?"):
                self._building = True
                self.chk_split.setChecked(True)
                self._building = False
                return
            self.layout.disable_split(cell)
        else:
            try:
                self.layout.set_split(
                    cell, self.combo_axis.currentData(),
                    self.spin_n.value())
            except LayoutError as exc:
                self._mostrar_error(str(exc))
                return
        self._rebuild_y_avisar()

    def _on_axis_changed(self, *args):
        if self._building or not self._selected_data:
            return
        data = self._selected_data
        cell = data.get("cell")
        if cell is None or not cell.axis:
            return
        axis = self.combo_axis.currentData()
        if axis == cell.axis:
            return
        if cell.children and not self._confirmar(
                "Cambiar el eje borrará las subdivisiones actuales.\n"
                "¿Continuar?"):
            self._building = True
            self.combo_axis.setCurrentIndex(
                0 if cell.axis == AXIS_X else 1)
            self._building = False
            return
        self.layout.set_split(cell, axis, self.spin_n.value())
        self._rebuild_y_avisar()

    def _on_n_changed(self, valor):
        if self._building or not self._selected_data:
            return
        data = self._selected_data
        cell = data.get("cell")
        if cell is None or not cell.axis:
            return
        if (valor < len(cell.children)
                and any(c.axis or c.children
                        for c in cell.children[valor:])
                and not self._confirmar(
                    "Reducir N eliminará subdivisiones internas.\n"
                    "¿Continuar?")):
            self._building = True
            self.spin_n.setValue(len(cell.children))
            self._building = False
            return
        self.layout.set_split(cell, cell.axis, valor)
        self._rebuild_y_avisar()

    def _rebuild_y_avisar(self):
        self._rebuild()
        self.changed.emit()

    # -----------------------------------------------------------------
    # Auxiliares
    # -----------------------------------------------------------------
    # -----------------------------------------------------------------
    # Reengrose contextual
    # -----------------------------------------------------------------
    def _elementos_reengrose(self):
        items = [
            ("lateral_izquierdo", "Lateral izquierdo"),
            ("lateral_derecho", "Lateral derecho"),
            ("base", "Base"),
            ("techo", "Techo"),
            ("fondo", "Fondo"),
        ]
        for pieza in (self._resolved.pieces if self._resolved else []):
            clave = (
                f"division_x:{pieza.path}" if pieza.axis == "X"
                else f"division_y:{pieza.path}")
            items.append((clave, pieza.nombre))
        return items

    def _poblar_elementos_reengrose(self):
        if self._resolved is None:
            return
        items = self._elementos_reengrose()
        claves = [clave for clave, _ in items]
        seleccion = self._selected_reengrose_key
        if seleccion not in claves:
            preferida = "division_x:x2"
            seleccion = (
                preferida if preferida in claves else claves[0])

        previo = self._building
        self._building = True
        self.combo_elemento_reengrose.blockSignals(True)
        self.combo_elemento_reengrose.clear()
        for clave, etiqueta in items:
            self.combo_elemento_reengrose.addItem(etiqueta, clave)
        idx = self.combo_elemento_reengrose.findData(seleccion)
        if idx >= 0:
            self.combo_elemento_reengrose.setCurrentIndex(idx)
        self.combo_elemento_reengrose.blockSignals(False)
        self._selected_reengrose_key = seleccion
        self._cargar_reengrose_controls(seleccion)
        self._building = previo

    def _cargar_reengrose_controls(self, clave):
        datos = self.reengroses.get(clave)
        try:
            mod = VDO_RE.ReengroseModifier(datos) if datos else VDO_RE.ReengroseModifier()
        except VDO_RE.ReengroseError:
            mod = VDO_RE.ReengroseModifier()
        etiquetas = self._etiquetas_caras(clave)
        self.combo_re_cara.setItemText(0, etiquetas[0])
        self.combo_re_cara.setItemText(1, etiquetas[1])
        self.combo_re_cara.setItemText(2, "Ambos lados")
        previo = self._building
        self._building = True
        self.chk_reengrose.setChecked(mod.activo)
        self._set_combo_data(self.combo_re_orientacion, mod.orientacion)
        self._set_combo_data(self.combo_re_cara, mod.cara)
        self._set_combo_data(
            self.combo_re_alineacion, mod.alineacion_profundidad)
        self._set_combo_data(self.combo_re_modo, mod.modo_fabricacion)
        self._set_combo_data(self.combo_re_alcance, mod.alcance)
        self._set_combo_data(
            self.combo_re_politica, mod.comportamiento_choque_nucleo)
        self._set_combo_data(
            self.combo_re_prioridad, mod.prioridad_encuentro_tiras)
        self.spin_re_ancho.setValue(mod.ancho)
        self.spin_re_espesor.setValue(mod.espesor or 0.0)
        self._actualizar_estado_reengrose()
        self._building = previo

    @staticmethod
    def _etiquetas_caras(clave):
        if clave == "lateral_izquierdo":
            return ("Interna (+)", "Externa (−)")
        if clave == "lateral_derecho":
            return ("Externa (+)", "Interna (−)")
        if clave == "base":
            return ("Superior / interna (+)", "Inferior / externa (−)")
        if clave == "techo":
            return ("Superior / externa (+)", "Inferior / interna (−)")
        if clave == "fondo":
            return ("Trasera (+)", "Delantera (−)")
        if str(clave).startswith("division_x:"):
            return ("Lado derecho (+)", "Lado izquierdo (−)")
        return ("Superior (+)", "Inferior (−)")

    @staticmethod
    def _set_combo_data(combo, valor):
        idx = combo.findData(valor)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _leer_reengrose_ui(self):
        modo = self.combo_re_modo.currentData()
        espesor = self.spin_re_espesor.value()
        choque = self.combo_re_politica.currentData()
        politica = {
            "retroceso": "retroceder",
            "mocheo": "mochear",
            "interrumpir_tira": "interrumpir_tira",
        }.get(choque, "retroceder")
        return {
            "activo": True,
            "orientacion": self.combo_re_orientacion.currentData(),
            "ancho": self.spin_re_ancho.value(),
            "espesor": espesor if espesor > 0 else None,
            "cara": self.combo_re_cara.currentData(),
            "alineacion_profundidad": self.combo_re_alineacion.currentData(),
            "modo_fabricacion": modo,
            "alcance": (
                self.combo_re_alcance.currentData()
                if modo == "pacha" else "parcial"),
            "politica_repisa": politica,
            "comportamiento_choque_nucleo": choque,
            "prioridad_encuentro_tiras": (
                self.combo_re_prioridad.currentData()),
        }

    def _actualizar_estado_reengrose(self):
        activo = self.chk_reengrose.isChecked()
        es_pacha = self.combo_re_modo.currentData() == "pacha"
        es_total = (
            es_pacha and self.combo_re_alcance.currentData() == "total")
        self.combo_re_alcance.setEnabled(activo and es_pacha)
        self.spin_re_ancho.setEnabled(activo and not es_total)
        self.combo_re_orientacion.setEnabled(activo and not es_total)
        self.combo_re_alineacion.setEnabled(activo and not es_total)
        self.spin_re_espesor.setEnabled(activo)
        self.combo_re_cara.setEnabled(activo)
        self.combo_re_modo.setEnabled(activo)
        self.combo_re_politica.setEnabled(activo)
        self.combo_re_prioridad.setEnabled(activo)
        if not activo:
            self.lbl_reengrose.setText("Sin reengrose.")
            return
        datos = self._leer_reengrose_ui()
        self.lbl_reengrose.setText(
            f"{datos['modo_fabricacion'].capitalize()} "
            f"{datos['alcance']}: tira {datos['ancho']:.1f} mm · "
            f"cara {datos['cara']} · {datos['orientacion']} · "
            f"choque {datos['comportamiento_choque_nucleo']} · "
            f"encuentro {datos['prioridad_encuentro_tiras']}.")

    def _on_reengrose_element_changed(self, *args):
        if self._building:
            return
        clave = self.combo_elemento_reengrose.currentData()
        if not clave:
            return
        self._selected_reengrose_key = clave
        self._cargar_reengrose_controls(clave)

    def _on_reengrose_changed(self, *args):
        if self._building:
            return
        clave = self.combo_elemento_reengrose.currentData()
        if not clave:
            return
        if not self.chk_reengrose.isChecked():
            self.reengroses.pop(clave, None)
        else:
            self.reengroses[clave] = self._leer_reengrose_ui()
        self._selected_reengrose_key = clave
        self._rebuild_y_avisar()

    def _confirmar(self, texto):
        respuesta = QtWidgets.QMessageBox.question(
            self, "Divisiones VDO", texto,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No)
        return respuesta == QtWidgets.QMessageBox.Yes

    def _mostrar_error(self, texto):
        self.lbl_aviso.setText("⚠ " + texto)
