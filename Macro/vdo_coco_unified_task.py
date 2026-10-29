# -*- coding: utf-8 -*-
# =====================================================================
# vdo_coco_unified_task.py
# Task Panel UNIFICADO para COCO: edita TODO (básico + espacios + pose).
# Se abre por clic derecho, doble clic o flujo de creación.
# =====================================================================

import json
from PySide import QtGui, QtCore

from vdo_qt import VDO_DoubleSpinBox
import FreeCAD as App
import FreeCADGui as Gui

from vdo_spaces import (
    SpaceNode, ESPACIO_FIJO, ESPACIO_RESTANTE, ESPACIO_IGUALES,
    serializar_espacios, deserializar_espacios,
    calcular_espacio_libre
)
from vdo_task_base import VDOTransactionMixin, cerrar_dialogo
from vdo_coco_divisions_task import DivisionesEditor
from vdo_module_props import (
    ANCLAJES, ANCLAJE_DEFAULT, ANCLAJE_LABELS,
    add_common_props, aplicar_rotacion
)
from vdo_puerta_core import make_puerta
from vdo_cajon_core import make_cajon
from vdo_facade_contract import (
    APERTURA_TIRADOR, APERTURA_GOLA, APERTURA_45_GRADOS, APERTURA_PUSH_OPEN,
    CALLE_ENTRE_FRENTES_DEFAULT,
)
import vdo_frames as VDO_FR


COL_TIPO = 0
COL_VALOR = 1
COL_RESUMEN = 2
COL_ACCIONES = 3

ROLE_NODE_ID = QtCore.Qt.UserRole + 1

TIPOS_LABELS = {
    ESPACIO_FIJO: "Fijo (mm)",
    ESPACIO_RESTANTE: "Restante",
    ESPACIO_IGUALES: "Iguales (N partes)",
}

LADOS_EXPOSICION = (
    (VDO_FR.FRENTE, "Frente"),
    (VDO_FR.FONDO, "Fondo"),
    (VDO_FR.IZQUIERDA, "Izquierda"),
    (VDO_FR.DERECHA, "Derecha"),
    (VDO_FR.SUPERIOR, "Superior"),
    (VDO_FR.INFERIOR, "Inferior"),
)

ESTADOS_EXPOSICION = (
    ("oculto", "Oculto"),
    ("visto", "Visto"),
    ("apoyado", "Apoyado"),
)


class EspacioRow:
    """Representa una fila visual en la tabla de espacios."""

    def __init__(self, node=None, depth=0):
        self.node = node or SpaceNode(space_type=ESPACIO_RESTANTE)
        self.depth = depth
        self.children_rows = []


class SpacesTableWidget(QtGui.QTableWidget):
    """QTableWidget con reordenamiento basado en modelo.

    No mueve filas por sí mismo: calcula el nuevo orden de nodos y delega
    en el panel, que reconstruye la tabla desde el modelo.
    """

    def __init__(self, parent=None, reorder_callback=None):
        super().__init__(parent)
        self.reorder_callback = reorder_callback
        self.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(
            ["Tipo", "Valor", "Resultado", "Acciones"])
        header = self.horizontalHeader()
        header.setResizeMode(COL_TIPO, QtGui.QHeaderView.ResizeToContents)
        header.setResizeMode(COL_VALOR, QtGui.QHeaderView.Stretch)
        header.setResizeMode(COL_RESUMEN, QtGui.QHeaderView.Stretch)
        header.setResizeMode(COL_ACCIONES, QtGui.QHeaderView.ResizeToContents)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)

    def _ids_actuales(self):
        ids = []
        for row in range(self.rowCount()):
            item = self.item(row, COL_TIPO)
            node_id = item.data(ROLE_NODE_ID) if item else None
            ids.append(node_id)
        return ids

    def dropEvent(self, event):
        if event.source() is not self or self.reorder_callback is None:
            super().dropEvent(event)
            return

        ids = self._ids_actuales()
        selected_rows = sorted(
            set(idx.row() for idx in self.selectedIndexes()))
        if not selected_rows:
            event.ignore()
            return

        drop_index = self.indexAt(event.pos())
        drop_row = None
        if drop_index.isValid():
            pos = self.dropIndicatorPosition()
            if pos == QtGui.QAbstractItemView.AboveItem:
                drop_row = drop_index.row()
            elif pos in (QtGui.QAbstractItemView.BelowItem,
                         QtGui.QAbstractItemView.OnItem):
                drop_row = drop_index.row() + 1
        if drop_row is None:
            drop_row = self.rowCount()

        moving = [ids[r] for r in selected_rows]
        rest = [node_id for i, node_id in enumerate(ids)
                if i not in selected_rows]
        insert_at = drop_row - sum(1 for r in selected_rows if r < drop_row)
        insert_at = max(0, min(insert_at, len(rest)))
        new_ids = rest[:insert_at] + moving + rest[insert_at:]

        event.setDropAction(QtCore.Qt.MoveAction)
        event.accept()
        self.reorder_callback(new_ids)


class CocoUnifiedTaskPanel(VDOTransactionMixin):
    """Task Panel UNIFICADO: Medidas + Estructura + Divisiones + Colocación."""

    def __init__(self, obj=None, on_accept=None, on_cancel=None,
                 auto_transaction=True):
        self.obj = obj
        self._vdo_aceptado = False
        self._current_axis = "X"
        self._rows_x = []
        self._rows_y = []
        self._selected_paths = {"X": [], "Y": []}
        self._building = False
        self.spin_dividir = {}
        self.spin_dividir_hijo = {}
        self._init_vdo_task(
            on_accept=on_accept,
            on_cancel=on_cancel,
            auto_transaction=auto_transaction,
            transaction_name="Editar COCO Completo",
        )
        self.form = self._crear_widget()
        if obj:
            add_common_props(obj)
            if not hasattr(obj, "VDO_Reengrose_JSON"):
                obj.addProperty(
                    "App::PropertyString", "VDO_Reengrose_JSON",
                    "Reengrose",
                    "Modificadores de reengrose por pieza (JSON)"
                ).VDO_Reengrose_JSON = "{}"
            if not hasattr(obj, "VDO_Contenido_JSON"):
                obj.addProperty(
                    "App::PropertyString", "VDO_Contenido_JSON",
                    "Contenido",
                    "Contenido de vanos (puertas, cajones) (JSON)"
                ).VDO_Contenido_JSON = "{}"
            self._cargar_valores(obj)

    # =================================================================
    # Construcción de UI
    # =================================================================
    def _crear_widget(self):
        widget = QtGui.QWidget()
        main_layout = QtGui.QVBoxLayout(widget)

        self.tabs = QtGui.QTabWidget()
        main_layout.addWidget(self.tabs)

        # --- Tab 1: Medidas Generales ---
        tab_medidas = QtGui.QWidget()
        layout_medidas = QtGui.QVBoxLayout(tab_medidas)

        grupo_medidas = QtGui.QGroupBox("Medidas Generales")
        grid_medidas = QtGui.QGridLayout(grupo_medidas)

        grid_medidas.addWidget(QtGui.QLabel("Alto (mm):"), 0, 0)
        self.spin_alto = VDO_DoubleSpinBox()
        self.spin_alto.setRange(1, 3000)
        self.spin_alto.setSuffix(" mm")
        self.spin_alto.setDecimals(1)
        self.spin_alto.setToolTip(
            "Alto exterior total del mueble, de piso a techo, incluyendo "
            "tapa y base.")
        grid_medidas.addWidget(self.spin_alto, 0, 1)

        grid_medidas.addWidget(QtGui.QLabel("Ancho (mm):"), 1, 0)
        self.spin_ancho = VDO_DoubleSpinBox()
        self.spin_ancho.setRange(1, 3000)
        self.spin_ancho.setSuffix(" mm")
        self.spin_ancho.setDecimals(1)
        self.spin_ancho.setToolTip(
            "Ancho exterior total del mueble, de lateral a lateral.")
        grid_medidas.addWidget(self.spin_ancho, 1, 1)

        grid_medidas.addWidget(QtGui.QLabel("Fondo módulo (mm):"), 2, 0)
        self.spin_fondo = VDO_DoubleSpinBox()
        self.spin_fondo.setRange(1, 1500)
        self.spin_fondo.setSuffix(" mm")
        self.spin_fondo.setDecimals(1)
        self.spin_fondo.setToolTip(
            "Profundidad exterior del mueble, desde el frente hasta el fondo.")
        grid_medidas.addWidget(self.spin_fondo, 2, 1)

        grid_medidas.addWidget(QtGui.QLabel("Espesor (mm):"), 3, 0)
        self.spin_espesor = QtGui.QSpinBox()
        self.spin_espesor.setRange(1, 50)
        self.spin_espesor.setSuffix(" mm")
        self.spin_espesor.setToolTip(
            "Espesor del tablero de laterales, base, techo y divisiones.")
        grid_medidas.addWidget(self.spin_espesor, 3, 1)

        layout_medidas.addWidget(grupo_medidas)

        # --- Colocación (pose, no geometría) ---
        grupo_coloc = QtGui.QGroupBox("Colocación")
        grid_coloc = QtGui.QGridLayout(grupo_coloc)

        grid_coloc.addWidget(QtGui.QLabel("Rotación Z:"), 0, 0)
        layout_rot = QtGui.QHBoxLayout()
        self.spin_rotacion = VDO_DoubleSpinBox()
        self.spin_rotacion.setRange(-360.0, 360.0)
        self.spin_rotacion.setDecimals(1)
        self.spin_rotacion.setSuffix(" °")
        self.spin_rotacion.setWrapping(True)
        self.spin_rotacion.setToolTip(
            "Rotación de colocación alrededor de Z. No cambia las medidas "
            "del mueble.")
        layout_rot.addWidget(self.spin_rotacion)
        btn_rot_menos = QtGui.QPushButton("-90°")
        btn_rot_menos.setMaximumWidth(50)
        btn_rot_menos.setToolTip(
            "Gira el mueble 90° en sentido horario.")
        btn_rot_menos.clicked.connect(
            lambda: self.spin_rotacion.setValue(
                self.spin_rotacion.value() - 90.0))
        layout_rot.addWidget(btn_rot_menos)
        btn_rot_mas = QtGui.QPushButton("+90°")
        btn_rot_mas.setMaximumWidth(50)
        btn_rot_mas.setToolTip(
            "Gira el mueble 90° en sentido antihorario.")
        btn_rot_mas.clicked.connect(
            lambda: self.spin_rotacion.setValue(
                self.spin_rotacion.value() + 90.0))
        layout_rot.addWidget(btn_rot_mas)
        grid_coloc.addLayout(layout_rot, 0, 1)

        grid_coloc.addWidget(QtGui.QLabel("Anclaje:"), 1, 0)
        self.combo_anclaje = QtGui.QComboBox()
        for anclaje in ANCLAJES:
            self.combo_anclaje.addItem(
                ANCLAJE_LABELS.get(anclaje, anclaje), anclaje)
        self.combo_anclaje.setToolTip(
            "Esquina del mueble que se apoya en el punto de colocación.")
        grid_coloc.addWidget(self.combo_anclaje, 1, 1)

        layout_medidas.addWidget(grupo_coloc)

        grupo_exp = QtGui.QGroupBox("Exposición")
        grid_exp = QtGui.QGridLayout(grupo_exp)
        self.combos_exposicion = {}
        for i, (lado, label) in enumerate(LADOS_EXPOSICION):
            fila = i // 2
            col = (i % 2) * 2
            grid_exp.addWidget(QtGui.QLabel(f"{label}:"), fila, col)
            combo = QtGui.QComboBox()
            for codigo, texto in ESTADOS_EXPOSICION:
                combo.addItem(texto, codigo)
            combo.setToolTip(
                "Visto: cara exterior visible. Apoyado: contra muro/piso. "
                "Oculto: sin exposición.")
            self.combos_exposicion[lado] = combo
            grid_exp.addWidget(combo, fila, col + 1)
        layout_medidas.addWidget(grupo_exp)

        # --- Tab 2: Estructura y Fondo ---
        tab_estructura = QtGui.QWidget()
        layout_estructura = QtGui.QVBoxLayout(tab_estructura)

        grupo_est = QtGui.QGroupBox("Estructura y Fondo")
        grid_est = QtGui.QGridLayout(grupo_est)

        grid_est.addWidget(QtGui.QLabel("Tapa:"), 0, 0)
        self.combo_tapa = QtGui.QComboBox()
        self.combo_tapa.addItems(["externo", "interno"])
        self.combo_tapa.setToolTip(
            "Externo: la tapa cubre los laterales. Interno: la tapa entra "
            "entre los laterales.")
        grid_est.addWidget(self.combo_tapa, 0, 1)

        grid_est.addWidget(QtGui.QLabel("Base:"), 1, 0)
        self.combo_base = QtGui.QComboBox()
        self.combo_base.addItems(["externo", "interno"])
        self.combo_base.setToolTip(
            "Externo: la base cubre los laterales. Interno: la base entra "
            "entre los laterales.")
        grid_est.addWidget(self.combo_base, 1, 1)

        self.chk_fondo = QtGui.QCheckBox("Tiene fondo")
        self.chk_fondo.setToolTip(
            "Activa el respaldo. El fondo delgado va en Y+ con ranuras; "
            "el grueso va retranqueado del borde trasero.")
        grid_est.addWidget(self.chk_fondo, 2, 0, 1, 2)

        grid_est.addWidget(QtGui.QLabel("Calibre fondo (mm):"), 3, 0)
        self.spin_calibre = QtGui.QSpinBox()
        self.spin_calibre.setRange(1, 25)
        self.spin_calibre.setSuffix(" mm")
        self.spin_calibre.setToolTip(
            "Espesor del fondo. Hasta 8 mm se considera fondo delgado.")
        grid_est.addWidget(self.spin_calibre, 3, 1)

        grid_est.addWidget(QtGui.QLabel("Profundidad ranura (mm):"), 4, 0)
        self.spin_ranura = VDO_DoubleSpinBox()
        self.spin_ranura.setRange(0.5, 20.0)
        self.spin_ranura.setSuffix(" mm")
        self.spin_ranura.setDecimals(1)
        self.spin_ranura.setToolTip(
            "Profundidad de la ranura donde entra el fondo delgado.")
        grid_est.addWidget(self.spin_ranura, 4, 1)

        grid_est.addWidget(QtGui.QLabel("Distancia borde (mm):"), 5, 0)
        self.spin_borde = VDO_DoubleSpinBox()
        self.spin_borde.setRange(0, 100.0)
        self.spin_borde.setSuffix(" mm")
        self.spin_borde.setDecimals(1)
        self.spin_borde.setToolTip(
            "Retranqueo del fondo grueso respecto al borde trasero.")
        grid_est.addWidget(self.spin_borde, 5, 1)

        layout_estructura.addWidget(grupo_est)

        # --- Tab 3: Divisiones (matriz de vanos + preview 2D) ---
        tab_divisiones = QtGui.QWidget()
        layout_divisiones = QtGui.QVBoxLayout(tab_divisiones)
        self.editor_divisiones = DivisionesEditor()
        self.editor_divisiones.changed.connect(self._on_divisiones_changed)
        layout_divisiones.addWidget(self.editor_divisiones)

        self.tabs.addTab(tab_medidas, "Medidas")
        self.tabs.addTab(tab_estructura, "Estructura")
        self.tabs.addTab(tab_divisiones, "Divisiones")

        # Resumen global
        grupo_resumen = QtGui.QGroupBox("Resumen Completo")
        layout_resumen = QtGui.QVBoxLayout(grupo_resumen)
        self.lbl_resumen = QtGui.QLabel("Sin configurar.")
        self.lbl_resumen.setWordWrap(True)
        self.lbl_resumen.setStyleSheet(
            "QLabel { background-color: #f0f0f0; padding: 8px; "
            "border: 1px solid #ccc; font-family: monospace; }")
        layout_resumen.addWidget(self.lbl_resumen)
        main_layout.addWidget(grupo_resumen)

        main_layout.addStretch()

        botones = QtGui.QDialogButtonBox()
        texto_ok = ("Crear y colocar" if not self.auto_transaction
                    else "Aplicar")
        btn_ok = botones.addButton(
            texto_ok, QtGui.QDialogButtonBox.AcceptRole)
        btn_cancelar = botones.addButton(
            "Cancelar", QtGui.QDialogButtonBox.RejectRole)
        botones.accepted.connect(self._on_ok)
        botones.rejected.connect(self._on_cancel)
        btn_ok.setToolTip(
            "Aplica medidas, estructura, divisiones y colocación del COCO.")
        btn_cancelar.setToolTip("Cierra sin aplicar los cambios.")
        main_layout.addWidget(botones)

        # El resumen sigue los valores de la UI, no las propiedades viejas.
        for spin in [self.spin_alto, self.spin_ancho,
                     self.spin_fondo, self.spin_espesor]:
            spin.valueChanged.connect(self._on_medida_changed)
        self.combo_tapa.currentIndexChanged.connect(self._on_medida_changed)
        self.combo_base.currentIndexChanged.connect(self._on_medida_changed)

        return widget

    def _crear_tab_espacios(self, layout, axis):
        """Crea la UI para un eje (X o Y)."""
        table = SpacesTableWidget(
            reorder_callback=lambda ids, a=axis: self._reordenar_raiz(a, ids))
        table.cellChanged.connect(
            lambda r, c, a=axis: self._on_cell_changed(r, c, a))
        if axis == "X":
            self.table_x = table
        else:
            self.table_y = table
        layout.addWidget(table)
        self._crear_botones_espacios(layout, axis)
        self._crear_grupo_hijos(layout, axis)

    def _crear_botones_espacios(self, layout, axis):
        """Botones de acción para la tabla principal de espacios."""
        layout_botones = QtGui.QHBoxLayout()

        btn_add = QtGui.QPushButton("+ Añadir vano")
        btn_add.clicked.connect(lambda: self._agregar_espacio(axis))
        layout_botones.addWidget(btn_add)

        btn_remove = QtGui.QPushButton("- Eliminar vano")
        btn_remove.clicked.connect(lambda: self._eliminar_espacio(axis))
        layout_botones.addWidget(btn_remove)

        layout_botones.addWidget(QtGui.QLabel("  |  "))

        layout_botones.addWidget(QtGui.QLabel("Dividir en:"))
        spin = QtGui.QSpinBox()
        spin.setRange(2, 20)
        spin.setValue(2)
        spin.setToolTip("Número de partes iguales")
        spin.setMaximumWidth(60)
        self.spin_dividir[axis] = spin
        layout_botones.addWidget(spin)

        btn_dividir = QtGui.QPushButton("Dividir")
        btn_dividir.setToolTip(
            "Divide el vano seleccionado en N partes iguales")
        btn_dividir.clicked.connect(
            lambda: self._dividir_seleccion(
                axis, self.spin_dividir[axis].value()))
        layout_botones.addWidget(btn_dividir)

        btn_nest = QtGui.QPushButton("Sub-dividir")
        btn_nest.setToolTip(
            "Sub-divide el vano seleccionado en el eje opuesto")
        btn_nest.clicked.connect(lambda: self._subconfigurar(axis))
        layout_botones.addWidget(btn_nest)

        layout.addLayout(layout_botones)

    def _crear_grupo_hijos(self, layout, axis):
        """Grupo para sub-configuración recursiva de hijos."""
        group = QtGui.QGroupBox("Sub-dividir vano seleccionado")
        group.setVisible(False)
        group_layout = QtGui.QVBoxLayout(group)

        lbl = QtGui.QLabel("")
        lbl.setWordWrap(True)
        group_layout.addWidget(lbl)

        lbl_eje = QtGui.QLabel("Eje de sub-división:")
        group_layout.addWidget(lbl_eje)

        table = SpacesTableWidget(
            reorder_callback=lambda ids, a=axis: self._reordenar_hijos(a, ids))
        table.setMaximumHeight(200)
        table.cellChanged.connect(
            lambda r, c, a=axis: self._on_child_cell_changed(r, c, a))
        group_layout.addWidget(table)

        btn_layout = QtGui.QHBoxLayout()

        btn_add = QtGui.QPushButton("+ Añadir vano")
        btn_add.clicked.connect(lambda: self._agregar_hijo(axis))
        btn_layout.addWidget(btn_add)

        btn_remove = QtGui.QPushButton("- Eliminar vano")
        btn_remove.clicked.connect(lambda: self._eliminar_hijo(axis))
        btn_layout.addWidget(btn_remove)

        btn_layout.addWidget(QtGui.QLabel("Dividir en:"))
        spin = QtGui.QSpinBox()
        spin.setRange(2, 20)
        spin.setValue(2)
        spin.setToolTip("Número de partes iguales")
        spin.setMaximumWidth(60)
        self.spin_dividir_hijo[axis] = spin
        btn_layout.addWidget(spin)

        btn_dividir = QtGui.QPushButton("Dividir")
        btn_dividir.setToolTip(
            "Divide el sub-vano seleccionado en N partes iguales")
        btn_dividir.clicked.connect(
            lambda: self._dividir_hijo(
                axis, self.spin_dividir_hijo[axis].value()))
        btn_layout.addWidget(btn_dividir)

        btn_back = QtGui.QPushButton("Atrás")
        btn_back.setToolTip("Subir un nivel en la jerarquía")
        btn_back.clicked.connect(lambda: self._subir_nivel(axis))
        btn_layout.addWidget(btn_back)

        btn_close = QtGui.QPushButton("Cerrar")
        btn_close.clicked.connect(lambda: self._cerrar_hijos(axis))
        btn_layout.addWidget(btn_close)

        group_layout.addLayout(btn_layout)
        layout.addWidget(group)

        if axis == "X":
            self.group_hijos_x = group
            self.lbl_hijo_info_x = lbl
            self.lbl_hijo_eje_x = lbl_eje
            self.table_hijos_x = table
            self.btn_hijo_atras_x = btn_back
        else:
            self.group_hijos_y = group
            self.lbl_hijo_info_y = lbl
            self.lbl_hijo_eje_y = lbl_eje
            self.table_hijos_y = table
            self.btn_hijo_atras_y = btn_back

        return group

    # =================================================================
    # Carga de datos
    # =================================================================
    def _cargar_valores(self, obj):
        """Carga todas las propiedades del objeto en el panel."""
        self._building = True

        self.spin_alto.setValue(float(obj.Alto))
        self.spin_ancho.setValue(float(obj.Ancho))
        self.spin_fondo.setValue(float(obj.FondoModulo))
        self.spin_espesor.setValue(int(obj.Espesor))

        idx = self.combo_tapa.findText(obj.Tapa)
        if idx >= 0:
            self.combo_tapa.setCurrentIndex(idx)
        idx = self.combo_base.findText(obj.Base)
        if idx >= 0:
            self.combo_base.setCurrentIndex(idx)
        self.chk_fondo.setChecked(obj.TieneFondo)
        self.spin_calibre.setValue(int(obj.CalibreFondo))
        self.spin_ranura.setValue(float(obj.ProfundidadRanura))
        self.spin_borde.setValue(float(obj.DistanciaBorde))

        self.spin_rotacion.setValue(
            float(getattr(obj, "VDO_RotacionZ", 0.0)))
        anclaje = getattr(obj, "VDO_Anclaje", ANCLAJE_DEFAULT)
        for i in range(self.combo_anclaje.count()):
            if self.combo_anclaje.itemData(i) == anclaje:
                self.combo_anclaje.setCurrentIndex(i)
                break

        vistos, apoyados = VDO_FR.cargar_exposicion(obj)
        for lado, combo in self.combos_exposicion.items():
            estado = "oculto"
            if lado in vistos:
                estado = "visto"
            elif lado in apoyados:
                estado = "apoyado"
            idx = combo.findData(estado)
            if idx >= 0:
                combo.setCurrentIndex(idx)

        self._rows_x = []
        self._rows_y = []
        self._selected_paths = {"X": [], "Y": []}

        self.editor_divisiones.set_dimensions(
            self.spin_alto.value(), self.spin_ancho.value(),
            self.spin_espesor.value())
        self.editor_divisiones.cargar_desde_objeto(obj)

        self._actualizar_resumen()
        self._building = False

    def _row_from_node(self, node, depth=0):
        """Hidrata recursivamente el árbol visual desde el modelo."""
        row = EspacioRow(node, depth=depth)
        row.children_rows = [
            self._row_from_node(child, depth=depth + 1)
            for child in getattr(node, "children", [])
        ]
        return row

    # =================================================================
    # Acceso al modelo visual
    # =================================================================
    def _get_rows(self, axis):
        return self._rows_x if axis == "X" else self._rows_y

    def _get_table(self, axis):
        return self.table_x if axis == "X" else self.table_y

    def _get_hijo_widgets(self, axis):
        if axis == "X":
            return (self.group_hijos_x, self.lbl_hijo_info_x,
                    self.lbl_hijo_eje_x, self.table_hijos_x,
                    self.btn_hijo_atras_x)
        return (self.group_hijos_y, self.lbl_hijo_info_y,
                self.lbl_hijo_eje_y, self.table_hijos_y,
                self.btn_hijo_atras_y)

    def _get_row_by_path(self, axis, path):
        if not path:
            return None
        rows = self._get_rows(axis)
        try:
            row = rows[path[0]]
            for idx in path[1:]:
                row = row.children_rows[idx]
            return row
        except (IndexError, TypeError):
            return None

    def _path_text(self, axis, path):
        partes = []
        for i in range(len(path)):
            row = self._get_row_by_path(axis, path[:i + 1])
            if row is not None:
                partes.append(str(row.node.space_id))
        return " → ".join(partes)

    # =================================================================
    # Pintado
    # =================================================================
    def _refrescar_tabla(self, axis):
        table = self._get_table(axis)
        rows = self._get_rows(axis)
        table.blockSignals(True)
        table.setRowCount(0)
        for i, row in enumerate(rows):
            table.insertRow(i)
            self._pintar_fila(table, i, row, axis, [i])
        table.blockSignals(False)

    def _pintar_fila(self, table, row_idx, esp_row, axis, path):
        node = esp_row.node
        indent = "  " * esp_row.depth

        tipo_item = QtGui.QTableWidgetItem(
            indent + TIPOS_LABELS.get(node.space_type, node.space_type))
        tipo_item.setFlags(tipo_item.flags() & ~QtCore.Qt.ItemIsEditable)
        tipo_item.setData(ROLE_NODE_ID, id(node))
        table.setItem(row_idx, COL_TIPO, tipo_item)

        if node.space_type == ESPACIO_FIJO:
            valor_item = QtGui.QTableWidgetItem(f"{node.value:.1f}")
        elif node.space_type == ESPACIO_IGUALES:
            valor_item = QtGui.QTableWidgetItem(str(int(node.value)))
        else:
            valor_item = QtGui.QTableWidgetItem("—")
            valor_item.setFlags(
                valor_item.flags() & ~QtCore.Qt.ItemIsEditable)
        table.setItem(row_idx, COL_VALOR, valor_item)

        if node.children:
            resumen = f"{len(node.children)} sub-vanos"
        elif node.space_type == ESPACIO_IGUALES:
            resumen = f"{int(node.value)} partes"
        elif node.space_type == ESPACIO_FIJO:
            resumen = f"{node.value:.0f}mm fijos"
        else:
            resumen = node.space_id
        res_item = QtGui.QTableWidgetItem(resumen)
        res_item.setFlags(res_item.flags() & ~QtCore.Qt.ItemIsEditable)
        table.setItem(row_idx, COL_RESUMEN, res_item)

        widget_acciones = QtGui.QWidget()
        layout_acciones = QtGui.QHBoxLayout(widget_acciones)
        layout_acciones.setContentsMargins(2, 2, 2, 2)
        layout_acciones.setSpacing(2)

        btn_nid = QtGui.QPushButton("...")
        btn_nid.setMaximumWidth(30)
        btn_nid.setToolTip("Sub-dividir este vano")
        btn_nid.setEnabled(node.space_type != ESPACIO_IGUALES)
        btn_nid.clicked.connect(
            lambda checked, a=axis, p=list(path):
                self._abrir_hijos(a, p))
        layout_acciones.addWidget(btn_nid)

        table.setCellWidget(row_idx, COL_ACCIONES, widget_acciones)

    # =================================================================
    # Edición de celdas
    # =================================================================
    def _on_medida_changed(self, *args):
        if self._building:
            return
        self.editor_divisiones.set_dimensions(
            self.spin_alto.value(), self.spin_ancho.value(),
            self.spin_espesor.value())
        self._actualizar_resumen()

    def _on_divisiones_changed(self):
        self._actualizar_resumen()

    def _aplicar_valor(self, table, row, col, axis, path):
        if col != COL_VALOR:
            return
        row_obj = self._get_row_by_path(axis, path)
        if row_obj is None:
            return
        item = table.item(row, col)
        if item is None:
            return
        texto = item.text().strip()
        try:
            valor = float(texto)
        except ValueError:
            return
        if row_obj.node.space_type == ESPACIO_IGUALES:
            valor = max(1.0, float(int(round(valor))))
            table.blockSignals(True)
            item.setText(str(int(valor)))
            table.blockSignals(False)
        row_obj.node.value = valor
        self._actualizar_resumen()

    def _on_cell_changed(self, row, col, axis):
        if self._building:
            return
        self._aplicar_valor(
            self._get_table(axis), row, col, axis, [row])

    def _on_child_cell_changed(self, row, col, axis):
        if self._building:
            return
        path = list(self._selected_paths[axis]) + [row]
        self._aplicar_valor(
            self._get_hijo_widgets(axis)[3], row, col, axis, path)

    # =================================================================
    # Operaciones sobre la tabla principal
    # =================================================================
    def _agregar_espacio(self, axis):
        rows = self._get_rows(axis)
        n = len(rows)
        node = SpaceNode(
            space_type=ESPACIO_RESTANTE,
            space_id=f"V{n+1}" if axis == "X" else f"H{n+1}")
        rows.append(EspacioRow(node, depth=0))
        table = self._get_table(axis)
        table.blockSignals(True)
        table.insertRow(n)
        self._pintar_fila(table, n, rows[n], axis, [n])
        table.blockSignals(False)
        self._actualizar_resumen()

    def _eliminar_espacio(self, axis):
        table = self._get_table(axis)
        selected = table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        rows = self._get_rows(axis)
        if 0 <= row < len(rows):
            rows.pop(row)
            self._refrescar_tabla(axis)
            self._actualizar_resumen()

    def _confirmar_borrado_hijos(self, node):
        if not getattr(node, "children", None):
            return True
        respuesta = QtGui.QMessageBox.question(
            self.form,
            "Sub-divisiones existentes",
            "Este vano tiene sub-divisiones.\n"
            "Si continúas se eliminarán.\n\n¿Continuar?",
            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No,
            QtGui.QMessageBox.No)
        return respuesta == QtGui.QMessageBox.Yes

    def _dividir_seleccion(self, axis, n_partes):
        table = self._get_table(axis)
        selected = table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        rows = self._get_rows(axis)
        if not (0 <= row < len(rows)):
            return
        old = rows[row]
        if not self._confirmar_borrado_hijos(old.node):
            return
        node = SpaceNode(
            space_type=ESPACIO_IGUALES,
            value=float(n_partes),
            space_id=old.node.space_id)
        rows[row] = EspacioRow(node, depth=old.depth)
        self._refrescar_tabla(axis)
        self._actualizar_resumen()

    def _subconfigurar(self, axis):
        table = self._get_table(axis)
        selected = table.selectedItems()
        if not selected:
            return
        self._abrir_hijos(axis, [selected[0].row()])

    # =================================================================
    # Sub-panel recursivo
    # =================================================================
    def _eje_hijos_label(self, axis, depth):
        """Etiqueta física del eje de los hijos según alternancia."""
        if axis == "X":
            return ("Horizontal (Repisas)" if depth % 2 == 1
                    else "Vertical (Columnas)")
        return ("Vertical (Columnas)" if depth % 2 == 1
                else "Horizontal (Repisas)")

    def _abrir_hijos(self, axis, path):
        row = self._get_row_by_path(axis, path)
        if row is None:
            return

        self._selected_paths[axis] = list(path)

        group, lbl, lbl_eje, table_hijos, btn_back = \
            self._get_hijo_widgets(axis)
        group.setVisible(True)
        btn_back.setEnabled(len(path) > 1)

        breadcrumb = self._path_text(axis, path)
        lbl.setText(
            f"Sub-dividiendo vano: <b>{breadcrumb}</b>")
        lbl_eje.setText(
            "Eje de sub-división: "
            + self._eje_hijos_label(axis, len(path)))

        table_hijos.blockSignals(True)
        table_hijos.setRowCount(0)
        for i, child in enumerate(row.children_rows):
            table_hijos.insertRow(i)
            self._pintar_fila(
                table_hijos, i, child, axis, list(path) + [i])
        table_hijos.blockSignals(False)

    def _agregar_hijo(self, axis):
        path = self._selected_paths[axis]
        parent = self._get_row_by_path(axis, path)
        if parent is None:
            return
        n = len(parent.children_rows)
        child = SpaceNode(
            space_type=ESPACIO_RESTANTE,
            space_id=f"{parent.node.space_id}.{n + 1}",
            parent_id=parent.node.space_id)
        parent.children_rows.append(
            EspacioRow(child, depth=parent.depth + 1))
        parent.node.children = [c.node for c in parent.children_rows]
        self._abrir_hijos(axis, path)
        self._actualizar_resumen()

    def _eliminar_hijo(self, axis):
        table_hijos = self._get_hijo_widgets(axis)[3]
        selected = table_hijos.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        path = self._selected_paths[axis]
        parent = self._get_row_by_path(axis, path)
        if parent is None or not (0 <= row < len(parent.children_rows)):
            return
        parent.children_rows.pop(row)
        parent.node.children = [c.node for c in parent.children_rows]
        self._abrir_hijos(axis, path)
        self._actualizar_resumen()

    def _dividir_hijo(self, axis, n_partes):
        table_hijos = self._get_hijo_widgets(axis)[3]
        selected = table_hijos.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        path = self._selected_paths[axis]
        parent = self._get_row_by_path(axis, path)
        if parent is None or not (0 <= row < len(parent.children_rows)):
            return
        old = parent.children_rows[row]
        if not self._confirmar_borrado_hijos(old.node):
            return
        child = SpaceNode(
            space_type=ESPACIO_IGUALES,
            value=float(n_partes),
            space_id=old.node.space_id,
            parent_id=parent.node.space_id)
        parent.children_rows[row] = EspacioRow(
            child, depth=old.depth)
        parent.node.children = [c.node for c in parent.children_rows]
        self._abrir_hijos(axis, path)
        self._actualizar_resumen()

    def _subir_nivel(self, axis):
        path = self._selected_paths[axis]
        if len(path) <= 1:
            return
        self._abrir_hijos(axis, path[:-1])

    def _cerrar_hijos(self, axis):
        group = self._get_hijo_widgets(axis)[0]
        group.setVisible(False)
        self._selected_paths[axis] = []
        self._refrescar_tabla(axis)
        self._actualizar_resumen()

    # =================================================================
    # Reordenamiento
    # =================================================================
    def _reordenar_por_ids(self, rows, ordered_ids):
        por_id = {id(row.node): row for row in rows}
        nuevas = [por_id[nid] for nid in ordered_ids if nid in por_id]
        usadas = {id(row.node) for row in nuevas}
        nuevas.extend(row for row in rows if id(row.node) not in usadas)
        return nuevas

    def _reordenar_raiz(self, axis, ordered_ids):
        rows = self._get_rows(axis)
        rows[:] = self._reordenar_por_ids(rows, ordered_ids)
        self._refrescar_tabla(axis)
        self._actualizar_resumen()

    def _reordenar_hijos(self, axis, ordered_ids):
        path = self._selected_paths[axis]
        parent = self._get_row_by_path(axis, path)
        if parent is None:
            return
        parent.children_rows[:] = self._reordenar_por_ids(
            parent.children_rows, ordered_ids)
        parent.node.children = [c.node for c in parent.children_rows]
        self._abrir_hijos(axis, path)
        self._actualizar_resumen()

    # =================================================================
    # Resumen
    # =================================================================
    def _leer_valores_ui(self):
        return {
            "alto": self.spin_alto.value(),
            "ancho": self.spin_ancho.value(),
            "fondo": self.spin_fondo.value(),
            "espesor": self.spin_espesor.value(),
            "tapa": self.combo_tapa.currentText(),
            "base": self.combo_base.currentText(),
        }

    def _actualizar_resumen(self):
        valores = self._leer_valores_ui()
        espesor = float(valores["espesor"])
        ancho_util = valores["ancho"] - (espesor * 2)
        alto_util = valores["alto"] - (espesor * 2)
        texto = (
            f"COCO {valores['ancho']:.0f} × {valores['alto']:.0f} × "
            f"{valores['fondo']:.0f} mm\n"
            f"Cavidad interior: {ancho_util:.1f} × {alto_util:.1f} mm\n"
            f"Tapa: {valores['tapa']} · Base: {valores['base']} · "
            f"Espesor: {espesor:.0f} mm\n\n")
        texto += self.editor_divisiones.resumen()
        if self.editor_divisiones.tiene_overflow():
            texto += ("\n\n⚠ OVERFLOW: corrige las medidas fijas "
                      "antes de aplicar.")
        self.lbl_resumen.setText(texto)

    # =================================================================
    # Aceptar / cancelar
    # =================================================================
    def _on_ok(self):
        if self.accept():
            cerrar_dialogo()

    def _on_cancel(self):
        self.reject()
        cerrar_dialogo()

    # =================================================================
    # Construcción de insertos (solo al aceptar - ciclo transaccional)
    # =================================================================
    def _construir_insertos(self, coco_obj):
        """Crea o actualiza los objetos hijos (puertas, cajones) del COCO.

        Se llama solo al presionar "Aceptar". No muta el documento antes.
        Gestiona huérfanos: elimina hijos cuyo vano ya no tenga contenido.
        """
        doc = App.ActiveDocument
        if doc is None:
            return

        # Leer contenido persistido
        texto = getattr(coco_obj, "VDO_Contenido_JSON", "") or "{}"
        try:
            contenido = json.loads(texto) if isinstance(texto, str) else {}
        except (ValueError, TypeError):
            contenido = {}
        # Convertir claves "i,j" a tuplas (col, row)
        contenido_tuplas = {}
        for k, v in contenido.items():
            try:
                col, row = map(int, str(k).split(","))
                contenido_tuplas[(col, row)] = v
            except (ValueError, TypeError):
                continue

        # Resolved map para obtener cotas de celdas
        editor = self.editor_divisiones
        resolved_map = getattr(editor, "_resolved_map", {})
        layout = getattr(editor, "layout", None)

        hijos_nuevos = []
        celdas_procesadas = set()

        for (col, row), datos in contenido_tuplas.items():
            celdas_procesadas.add((col, row))
            tipo = datos.get("tipo", "vacio")
            cfg = datos.get("config", {})

            if layout is None:
                continue
            cell = layout.get_cell(col, row)
            if cell is None:
                continue
            resuelto = resolved_map.get(cell.label)
            if resuelto is None:
                continue

            x = float(getattr(resuelto, "nominal_x", 0.0))
            z = float(getattr(resuelto, "nominal_z", 0.0))
            w = float(resuelto.w)
            h = float(resuelto.h)

            if tipo == "puerta":
                self._construir_puerta(
                    doc, coco_obj, cfg, x, z, w, h, hijos_nuevos)
            elif tipo == "cajon" or tipo == "cajon_torre":
                self._construir_cajones(
                    doc, coco_obj, cfg, x, z, w, h, hijos_nuevos)

        # --- Gestión de huérfanos ---
        hijos_actuales = list(coco_obj.Hijos or [])
        claves_activas = set()
        for hijo in hijos_nuevos:
            claves_activas.add(hijo.Name)
        for hijo in hijos_actuales:
            if hijo.Name not in claves_activas:
                try:
                    doc.removeObject(hijo.Name)
                except Exception:
                    pass

        coco_obj.Hijos = hijos_nuevos

    def _construir_puerta(self, doc, coco_obj, cfg, x, z, w, h, hijos_nuevos):
        """Crea o actualiza una puerta como hijo del COCO."""
        nombre = cfg.get("nombre", f"Puerta_{coco_obj.Name}")
        # Buscar si ya existe
        existente = None
        for hijo in list(coco_obj.Hijos or []):
            if hijo.Name == nombre:
                existente = hijo
                break

        if existente is None:
            existente = doc.addObject("Part::FeaturePython", nombre)
            from vdo_puerta_core import PuertaFeature
            PuertaFeature(existente)
            if App.GuiUp:
                from vdo_puerta_core import ViewProviderPuerta
                ViewProviderPuerta(existente.ViewObject)

        # Propiedades de la puerta
        existente.TipoSistema = cfg.get("tipo_sistema", "Batiente Vertical")
        existente.TipoMontaje = cfg.get("tipo_montaje", "Parche")
        existente.SentidoApertura = cfg.get("sentido_apertura", "Izquierda")
        existente.SistemaApertura = cfg.get(
            "sistema_apertura", APERTURA_TIRADOR)
        existente.HardwareSKU = cfg.get("hardware_sku", "")
        existente.VDO_Vano_ID = cfg.get("vdo_vano_id", "")
        existente.Ancho = float(cfg.get("ancho", w))
        existente.Alto = float(cfg.get("alto", h))
        existente.Espesor = int(cfg.get("espesor", 18))
        existente.PosX = float(cfg.get("pos_x", x))
        existente.PosY = float(cfg.get("pos_y", 0.0))
        existente.PosZ = float(cfg.get("pos_z", z))
        existente.VDO_Anclaje = cfg.get("anclaje", "inferior_izquierda_frente")

        # Vínculo padre-hijo
        existente.ParentCOCO = coco_obj
        existente.LocalPlacement = App.Placement(
            App.Vector(
                float(cfg.get("pos_x", x)),
                float(cfg.get("pos_y", 0.0)),
                float(cfg.get("pos_z", z)),
            ), App.Rotation())

        hijos_nuevos.append(existente)

    def _construir_cajones(self, doc, coco_obj, cfg, x, z, w, h, hijos_nuevos):
        """Crea o actualiza cajones (1 o más, torre apilada) como hijos del COCO."""
        cantidad = int(cfg.get("cantidad", 1))
        corredera = cfg.get("corredera", "Oculta")
        apertura = cfg.get("apertura", "Tirador")
        nombre_base = cfg.get("nombre", f"Cajon_{coco_obj.Name}")

        # Calcular altura individual de frente para torre N cajones
        h_frente = (h - (cantidad - 1) * CALLE_ENTRE_FRENTES_DEFAULT) / cantidad
        if h_frente <= 0:
            h_frente = max(10.0, h / max(cantidad, 1))

        from vdo_cajon_despiece import CORREDERA_OCULTA, CORREDERA_TELESCOPICA
        tipo_corredera = CORREDERA_OCULTA if corredera == "Oculta" else CORREDERA_TELESCOPICA

        apertura_map = {
            "Tirador": APERTURA_TIRADOR,
            "Gola": APERTURA_GOLA,
            "45°": APERTURA_45_GRADOS,
            "Push": APERTURA_PUSH_OPEN,
        }
        sistema_apertura = apertura_map.get(apertura, APERTURA_TIRADOR)

        for i in range(cantidad):
            nombre = f"{nombre_base}_{i + 1:02d}"
            # Buscar si ya existe
            existente = None
            for hijo in list(coco_obj.Hijos or []):
                if hijo.Name == nombre:
                    existente = hijo
                    break

            if existente is None:
                existente = doc.addObject("Part::FeaturePython", nombre)
                from vdo_cajon_core import CajonFeature
                CajonFeature(existente)
                if App.GuiUp:
                    from vdo_cajon_core import ViewProviderCajon
                    ViewProviderCajon(existente.ViewObject)

            # Propiedades del cajón
            existente.AnchoLibre = w
            existente.ProfLibre = float(getattr(coco_obj, "FondoModulo", 580.0))
            existente.AnchoModulo = w
            existente.AltoFrente = h_frente
            existente.AltoCaja = float(getattr(coco_obj, "Espesor", 18)) * 5  # default 90mm
            existente.GrosorCaja = 16.0
            existente.GrosorFondo = 6.0
            existente.GrosorFachada = 18.0
            existente.MarcaCorredera = "blum_tandem"
            existente.LongitudGuia = 0.0
            existente.MontajeTrasera = "entre_laterales"
            existente.TipoCorredera = tipo_corredera
            existente.SistemaApertura = sistema_apertura

            # Vínculo padre-hijo con z escalonado
            z_local = z + i * (h_frente + CALLE_ENTRE_FRENTES_DEFAULT)
            existente.ParentCOCO = coco_obj
            existente.LocalPlacement = App.Placement(
                App.Vector(x, 0.0, z_local), App.Rotation())

            hijos_nuevos.append(existente)

    def accept(self):
        if not self.obj:
            return True
        try:
            self._vdo_begin()

            for spin in (self.spin_alto, self.spin_ancho,
                         self.spin_fondo, self.spin_espesor,
                         self.spin_calibre, self.spin_ranura,
                         self.spin_borde, self.spin_rotacion):
                spin.interpretText()

            self.obj.Alto = self.spin_alto.value()
            self.obj.Ancho = self.spin_ancho.value()
            self.obj.FondoModulo = self.spin_fondo.value()
            self.obj.Espesor = self.spin_espesor.value()

            self.obj.Tapa = self.combo_tapa.currentText()
            self.obj.Base = self.combo_base.currentText()
            self.obj.TieneFondo = self.chk_fondo.isChecked()
            self.obj.CalibreFondo = self.spin_calibre.value()
            self.obj.ProfundidadRanura = self.spin_ranura.value()
            self.obj.DistanciaBorde = self.spin_borde.value()

            anclaje = self.combo_anclaje.currentData()
            if anclaje:
                self.obj.VDO_Anclaje = anclaje
            aplicar_rotacion(self.obj, self.spin_rotacion.value())

            if self.editor_divisiones.tiene_overflow():
                QtGui.QMessageBox.warning(
                    self.form, "Divisiones VDO",
                    "Las medidas fijas no caben en la cavidad interior.\n"
                    "Reduce alguna medida antes de aplicar.")
                self._vdo_abort()
                return False

            vistos = []
            apoyados = []
            for lado, combo in self.combos_exposicion.items():
                estado = combo.currentData()
                if estado == "visto":
                    vistos.append(lado)
                elif estado == "apoyado":
                    apoyados.append(lado)
            VDO_FR.guardar_exposicion(self.obj, vistos, apoyados)

            if not hasattr(self.obj, "VDO_Divisiones"):
                self.obj.addProperty(
                    "App::PropertyString", "VDO_Divisiones", "Divisiones",
                    "Matriz de vanos v2 (JSON)")
            self.obj.VDO_Divisiones = self.editor_divisiones.dumps()
            self.obj.VDO_Reengrose_JSON = (
                self.editor_divisiones.dumps_reengroses())
            self.obj.VDO_Contenido_JSON = (
                self.editor_divisiones.dumps_contenido())

            # --- Construir insertos solo al aceptar (ciclo transaccional) ---
            self._construir_insertos(self.obj)

            App.ActiveDocument.recompute()
            self._vdo_commit()
            self._vdo_aceptado = True
            self._vdo_call_accept()
            return True
        except Exception as exc:
            self._vdo_abort()
            App.Console.PrintError(
                f"[VDO] Error aceptando COCO: {exc}\n")
            import traceback
            App.Console.PrintError(traceback.format_exc())
            return False

    def reject(self):
        if getattr(self, "_vdo_aceptado", False):
            return True
        self._vdo_abort()
        self._vdo_call_cancel()
        return True

    def clicked(self, button):
        pass

    def getStandardButtons(self):
        return QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel

    def helpRequested(self):
        pass


def abrir_editor_unificado(obj=None):
    """Abre el editor unificado para un COCO."""
    panel = CocoUnifiedTaskPanel(obj)
    Gui.Control.showDialog(panel)
    return panel
