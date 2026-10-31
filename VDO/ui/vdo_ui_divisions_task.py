# -*- coding: utf-8 -*-
# =====================================================================
# vdo_coco_divisions_task.py
# Editor de la matriz de vanos del COCO:
#   preview 2D bidireccional + pestañas Vanos/Estructura + inspector.
# =====================================================================

import json

import FreeCAD as App
from PySide import QtCore, QtGui, QtWidgets

import VDO.core.vdo_math_reengrose as VDO_RE
from VDO.shared import vdo_shared_finish as VDO_FIN
import VDO.core.vdo_math_frames as VDO_FR

import VDO.hub.vdo_hub_defaults as VDO_D
from VDO.core.vdo_math_layout import (
    Layout, LayoutError, AXIS_X, AXIS_Y, cavidad_interior, resolve_layout,
)
from VDO.ui.vdo_ui_preview2d_widget import CocoPreview2D
from VDO.cad.objects.vdo_cad_puerta import make_puerta
from VDO.cad.objects.vdo_cad_cajon import make_cajon
from VDO.core.vdo_math_facade import (
    APERTURA_TIRADOR, APERTURA_GOLA, APERTURA_45_GRADOS, APERTURA_PUSH_OPEN,
)


ROLE_DATA = QtCore.Qt.UserRole + 1
ROLE_KIND = QtCore.Qt.UserRole + 2
ROLE_KEY = QtCore.Qt.UserRole + 3

BORDES = ("norte", "sur", "este", "oeste")
BORDE_LABELS = {
    "norte": "Norte", "sur": "Sur", "este": "Este", "oeste": "Oeste"}


class PanelHeaderWidget(QtWidgets.QGroupBox):
    """Encabezado universal para una pieza física o una tira de reengrose."""

    def __init__(self, parent=None):
        super().__init__("Encabezado de pieza", parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        self.lbl_nombre = QtWidgets.QLabel("Sin selección")
        self.lbl_nombre.setStyleSheet("font-weight: bold;")
        self.lbl_nombre.setWordWrap(True)
        layout.addWidget(self.lbl_nombre)

        self.lbl_dimensiones = QtWidgets.QLabel("—")
        self.lbl_dimensiones.setToolTip(
            "Dimensiones brutas de corte: Largo × Ancho × Espesor.")
        layout.addWidget(self.lbl_dimensiones)

        self.lbl_cantos = QtWidgets.QLabel("")
        self.lbl_cantos.setWordWrap(True)
        self.lbl_cantos.setStyleSheet(
            "QLabel { background: #2b2b2b; color: #e0e0e0; padding: 3px; "
            "border: 1px solid #4a4a4a; }")
        layout.addWidget(self.lbl_cantos)

        self._cantos_labels = {}
        self.set_panel("Sin selección", 0.0, 0.0, 0.0)

    def _normalizar_cantos(self, cantos):
        datos = {}
        for borde in BORDES:
            valor = str((cantos or {}).get(borde, "FX") or "FX").upper()
            datos[borde] = valor
        return datos

    def set_panel(self, nombre, largo, ancho, espesor, cantos=None,
                  sufijo=""):
        nombre = str(nombre or "Pieza")
        if sufijo:
            nombre = f"{nombre} {sufijo}"
        self.lbl_nombre.setText(nombre)
        self.lbl_dimensiones.setText(
            f"{float(largo):.1f} × {float(ancho):.1f} × "
            f"{float(espesor):.1f} mm")
        datos = self._normalizar_cantos(cantos)
        self.lbl_cantos.setText(" · ".join(
            f"{BORDE_LABELS[borde]}: {datos[borde]}" for borde in BORDES))

    def set_strip(self, nombre, largo, ancho, espesor, cantos=None):
        self.set_panel(nombre, largo, ancho, espesor, cantos,
                       sufijo="(tira de reengrose)")

    def clear(self):
        self.lbl_nombre.setText("Sin selección")
        self.lbl_dimensiones.setText("—")
        self.lbl_cantos.setText("")

    def cantos_texto(self):
        return self.lbl_cantos.text()


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
        self._en_reengrose = False
        self._skip_cargar_reengrose = False
        self._legacy_warnings = []
        self.reengroses = {}
        self._selected_reengrose_key = None
        self._contenido_por_celda = {}
        self.mode = "vanos"
        self._obj = None
        self._fondo = 580.0
        self._tapa = "externo"
        self._base = "interno"
        self._tiene_fondo = True

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
        self.preview.panelClicked.connect(self._seleccionar_panel_preview)
        self.preview.reengroseClicked.connect(
            self._seleccionar_reengrose_preview)
        layout.addWidget(self.preview, 1)

        self.tabs_modo = QtWidgets.QTabBar()
        self.tabs_modo.addTab("🔲 Vanos")
        self.tabs_modo.addTab("🪵 Estructura")
        self.tabs_modo.setToolTip(
            "Vanos: espacios libres y subdivisiones. "
            "Estructura: paneles físicos y sus reengroses.")
        self.tabs_modo.currentChanged.connect(self._on_modo_changed)
        layout.addWidget(self.tabs_modo)

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

        self.inspector = QtWidgets.QGroupBox("Inspector")
        self.form = QtWidgets.QFormLayout(self.inspector)
        self.header = PanelHeaderWidget()
        self.header.setVisible(False)
        self.form.addRow(self.header)

        self.lbl_sel = QtWidgets.QLabel("Sin selección.")
        self.lbl_sel.setWordWrap(True)
        self.form.addRow(self.lbl_sel)

        self.lbl_nominal_neto = QtWidgets.QLabel("")
        self.lbl_nominal_neto.setWordWrap(True)
        self.lbl_nominal_neto.setStyleSheet(
            "QLabel { background: #2b2b2b; color: #e0e0e0; padding: 4px; "
            "border: 1px solid #4a4a4a; }")
        self.form.addRow(self.lbl_nominal_neto)

        self.lbl_invasores = QtWidgets.QLabel("")
        self.lbl_invasores.setWordWrap(True)
        self.form.addRow(self.lbl_invasores)

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

        # ---- Selector unificado de contenido de vano ----
        self.lbl_contenido = QtWidgets.QLabel("Contenido del vano:")
        self.lbl_contenido.setStyleSheet("font-weight: bold; color: #e0e0e0;")
        self.form.addRow(self.lbl_contenido)

        self.combo_contenido = QtWidgets.QComboBox()
        self.combo_contenido.addItem("🔲  Vacío", "vacio")
        self.combo_contenido.addItem("➗  Subdivisión", "subdivision")
        self.combo_contenido.addItem("🚪  Puerta", "puerta")
        self.combo_contenido.addItem("🗄️  Cajón", "cajon")
        self.combo_contenido.setToolTip(
            "Tipo de contenido para este vano. Los insertos (puerta, cajón) "
            "requieren un vano padre y se anidan bajo él en el árbol.")
        self.form.addRow(self.combo_contenido)

        # ---- Panel reactivo: Subdivisión ----
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
        self.widget_split.setVisible(False)

        # ---- Panel reactivo: Puerta ----
        self.widget_puerta = QtWidgets.QWidget()
        puerta_layout = QtWidgets.QFormLayout(self.widget_puerta)
        puerta_layout.setContentsMargins(16, 0, 0, 0)

        self.combo_puerta_familia = QtWidgets.QComboBox()
        self.combo_puerta_familia.addItems(["Batiente", "Corrediza", "Basculante"])
        self.combo_puerta_familia.setToolTip("Tipo de sistema de la puerta.")
        puerta_layout.addRow("Familia:", self.combo_puerta_familia)

        self.combo_puerta_montaje = QtWidgets.QComboBox()
        self.combo_puerta_montaje.addItems(["Parche", "Semiparche", "Embebida"])
        self.combo_puerta_montaje.setToolTip("Tipo de montaje frontal.")
        puerta_layout.addRow("Montaje:", self.combo_puerta_montaje)

        self.combo_puerta_apertura = QtWidgets.QComboBox()
        self.combo_puerta_apertura.addItems(
            ["Tirador", "Gola", "45°", "Push Open"])
        self.combo_puerta_apertura.setToolTip("Sistema de apertura/fachada.")
        puerta_layout.addRow("Apertura:", self.combo_puerta_apertura)

        self.combo_puerta_herraje = QtWidgets.QComboBox()
        self.combo_puerta_herraje.setToolTip("SKU de herraje comercial.")
        puerta_layout.addRow("Herraje:", self.combo_puerta_herraje)

        self.lbl_puerta_info = QtWidgets.QLabel(
            "Se creará al aceptar el Task Panel del COCO.")
        self.lbl_puerta_info.setStyleSheet("color: #8a8a8a; font-style: italic;")
        puerta_layout.addRow(self.lbl_puerta_info)
        self.form.addRow(self.widget_puerta)
        self.widget_puerta.setVisible(False)

        # ---- Panel reactivo: Cajón ----
        self.widget_cajon = QtWidgets.QWidget()
        cajon_layout = QtWidgets.QFormLayout(self.widget_cajon)
        cajon_layout.setContentsMargins(16, 0, 0, 0)

        self.spin_cajon_cantidad = QtWidgets.QSpinBox()
        self.spin_cajon_cantidad.setRange(1, 6)
        self.spin_cajon_cantidad.setValue(1)
        self.spin_cajon_cantidad.setToolTip("Cantidad de frentes (1 a 6).")
        cajon_layout.addRow("Cantidad:", self.spin_cajon_cantidad)

        self.combo_cajon_corredera = QtWidgets.QComboBox()
        self.combo_cajon_corredera.addItems(["Telescópica", "Oculta"])
        self.combo_cajon_corredera.setToolTip("Tipo de corredera del cajón.")
        cajon_layout.addRow("Corredera:", self.combo_cajon_corredera)

        self.combo_cajon_apertura = QtWidgets.QComboBox()
        self.combo_cajon_apertura.addItems(["Tirador", "Gola", "45°", "Push"])
        self.combo_cajon_apertura.setToolTip("Sistema de apertura del frente.")
        cajon_layout.addRow("Apertura:", self.combo_cajon_apertura)

        self.lbl_cajon_info = QtWidgets.QLabel(
            "Se creará al aceptar el Task Panel del COCO.")
        self.lbl_cajon_info.setStyleSheet("color: #8a8a8a; font-style: italic;")
        cajon_layout.addRow(self.lbl_cajon_info)
        self.form.addRow(self.widget_cajon)
        self.widget_cajon.setVisible(False)

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
            "QLabel { background: #2b2b2b; color: #e0e0e0; padding: 6px; "
            "border: 1px solid #4a4a4a; font-family: monospace; }")
        layout.addWidget(self.lbl_resumen)

        self.tree.itemSelectionChanged.connect(self._on_tree_selection)
        self.chk_col_fixed.toggled.connect(self._on_col_fixed)
        self.chk_row_fixed.toggled.connect(self._on_row_fixed)
        self.chk_cell_fixed.toggled.connect(self._on_cell_fixed)
        self.spin_col_fixed.valueChanged.connect(self._on_col_fixed)
        self.spin_row_fixed.valueChanged.connect(self._on_row_fixed)
        self.spin_cell_fixed.valueChanged.connect(self._on_cell_fixed)
        self.combo_contenido.currentIndexChanged.connect(
            self._on_contenido_changed)
        self.combo_axis.currentIndexChanged.connect(self._on_axis_changed)
        self.spin_n.valueChanged.connect(self._on_n_changed)
        self.combo_elemento_reengrose.currentIndexChanged.connect(
            self._on_reengrose_element_changed)
        self.re_editor.changed.connect(self._on_reengrose_changed)
        self.re_editor.sigConfigChanged.connect(self._on_reengrose_changed)
        self.combo_fabricacion.currentIndexChanged.connect(
            self._on_reengrose_changed)
        self.combo_choque.currentIndexChanged.connect(
            self._on_reengrose_changed)
        self.combo_cara.currentIndexChanged.connect(
            self._on_reengrose_changed)
        # Guardar config de insertos al cambiar cualquier widget reactivo
        self.combo_puerta_familia.currentIndexChanged.connect(
            self._guardar_config_desde_ui)
        self.combo_puerta_montaje.currentIndexChanged.connect(
            self._guardar_config_desde_ui)
        self.combo_puerta_apertura.currentIndexChanged.connect(
            self._guardar_config_desde_ui)
        self.combo_puerta_herraje.currentIndexChanged.connect(
            self._guardar_config_desde_ui)
        self.spin_cajon_cantidad.valueChanged.connect(
            self._guardar_config_desde_ui)
        self.combo_cajon_corredera.currentIndexChanged.connect(
            self._guardar_config_desde_ui)
        self.combo_cajon_apertura.currentIndexChanged.connect(
            self._guardar_config_desde_ui)

    def _guardar_config_desde_ui(self, *args):
        """Guarda la configuración actual de los paneles reactivos en
        _contenido_por_celda para la celda o hijo seleccionado."""
        if self._building or not self._selected_data:
            return
        data = self._selected_data
        kind = data.get("kind")
        if kind in ("cell", "nested"):
            col = data.get("col_index")
            row = data.get("row_index")
            if col is None or row is None:
                return
            self._guardar_config_actual(col, row)
        elif kind == "contenido_hijo":
            celda = data.get("celda")
            if not celda:
                return
            try:
                col, row = celda
            except (ValueError, TypeError):
                return
            self._guardar_config_actual(col, row)
            # Refrescar preview 2D al instante
            self._rebuild_y_avisar()

    def _crear_grupo_reengrose(self):
        from VDO.ui.vdo_ui_box_widget import VDOBoxControllerWidget
        grupo = QtWidgets.QGroupBox("Reengrose / Refuerzo")
        grid = QtWidgets.QGridLayout(grupo)
        grid.setContentsMargins(6, 6, 6, 6)
        grid.setVerticalSpacing(4)
        grid.setHorizontalSpacing(8)

        grid.addWidget(QtWidgets.QLabel("Elemento:"), 0, 0)
        self.combo_elemento_reengrose = QtWidgets.QComboBox()
        self.combo_elemento_reengrose.setToolTip(
            "Elegí el lateral, la base, el techo o una división para "
            "configurar su refuerzo. Los vanos muestran la luz neta; el "
            "refuerzo pertenece a la pieza que lo lleva.")
        grid.addWidget(self.combo_elemento_reengrose, 0, 1, 1, 3)

        # Controlador Espacial Figma Box Model (Cuadrado Paramétrico)
        self.box_controller = VDOBoxControllerWidget()
        self.re_editor = self.box_controller
        grid.addWidget(self.box_controller, 1, 0, 1, 4)

        # Parámetros globales de fabricación debajo del widget
        grid.addWidget(QtWidgets.QLabel("Fabricación:"), 2, 0)
        self.combo_fabricacion = QtWidgets.QComboBox()
        self.combo_fabricacion.addItem("Pacha (bloque unificado)", "pacha")
        self.combo_fabricacion.addItem("Independiente", "independiente")
        self.combo_fabricacion.setToolTip("Fabricación de las tiras y su canteado.")
        grid.addWidget(self.combo_fabricacion, 2, 1, 1, 3)

        grid.addWidget(QtWidgets.QLabel("Choque núcleo:"), 3, 0)
        self.combo_choque = QtWidgets.QComboBox()
        self.combo_choque.addItem("Retroceso (corte recto)", "retroceso")
        self.combo_choque.addItem("Mocheo / rebaje", "mocheo")
        self.combo_choque.addItem("Interrumpir tira", "interrumpir_tira")
        self.combo_choque.setToolTip("Comportamiento de la tira al chocar con el núcleo.")
        grid.addWidget(self.combo_choque, 3, 1, 1, 3)

        grid.addWidget(QtWidgets.QLabel("Cara de pegado:"), 4, 0)
        self.combo_cara = QtWidgets.QComboBox()
        self.combo_cara.addItem("Cara A (+)", "cara_a")
        self.combo_cara.addItem("Cara B (−)", "cara_b")
        self.combo_cara.addItem("Ambas caras", "ambos")
        self.combo_cara.setToolTip("Cara del tablero donde se pegan las tiras.")
        grid.addWidget(self.combo_cara, 4, 1, 1, 3)

        # Aliases y compatibilidad backward
        self.chk_reengrose = self.re_editor.chk_activo
        self.spin_re_ancho = self.re_editor.spin_ancho
        self.spin_re_espesor = self.re_editor.spin_espesor
        self.combo_re_cara = self.combo_cara
        self.combo_re_modo = self.combo_fabricacion
        self.combo_re_politica = self.combo_choque
        self.combo_re_prioridad = self.re_editor.combo_esquinas
        self.combo_re_esquinas = self.re_editor.combo_esquinas
        self.combo_re_choque = self.combo_choque
        self.spin_re_offset = self.re_editor.spin_offset
        self.chk_re_uniforme = self.re_editor.chk_uniforme
        self.btn_all = self.re_editor.btn_all
        self.btn_borde = self.re_editor.btn_borde
        self.btn_borde_frente = self.re_editor.btn_borde["frente"]
        self.btn_borde_fondo = self.re_editor.btn_borde["fondo"]
        self.btn_borde_izquierda = self.re_editor.btn_borde["izquierda"]
        self.btn_borde_derecha = self.re_editor.btn_borde["derecha"]
        self.spin_re_ancho_borde = self.re_editor.spin_ancho_borde
        self.spin_re_offset_borde = self.re_editor.spin_offset_borde
        self.lbl_reengrose = self.re_editor.lbl_resumen
        self.chk_sync_esquinas = self.re_editor.chk_sync_esquinas
        self.combo_esquina = self.re_editor.combo_esquina
        self.preview_reengrose = None

        self.re_editor.combo_choque = self.combo_choque
        self.re_editor.combo_cara = self.combo_cara
        self.re_editor.combo_fabricacion = self.combo_fabricacion
        self.re_editor._set_combo_data = self._set_combo_data

        # Controles legacy ocultos para compatibilidad de API
        self.combo_re_orientacion = QtWidgets.QComboBox()
        self.combo_re_orientacion.addItem("Paralela", "paralela")
        self.combo_re_orientacion.addItem("Transversal", "transversal")
        self.combo_re_alineacion = QtWidgets.QComboBox()
        self.combo_re_alineacion.addItem("Frente", "frente")
        self.combo_re_alineacion.addItem("Centrado", "centrado")
        self.combo_re_alineacion.addItem("Fondo", "fondo")
        self.combo_re_alcance = QtWidgets.QComboBox()
        self.combo_re_alcance.addItem("Parcial", "parcial")
        self.combo_re_alcance.addItem("Total", "total")
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
    def set_dimensions(self, alto, ancho, espesor, fondo=None, tapa=None,
                       base=None, tiene_fondo=None):
        self.outer_w = float(ancho)
        self.outer_h = float(alto)
        self.thickness = float(espesor)
        if fondo is not None:
            self._fondo = float(fondo)
        if tapa is not None:
            self._tapa = str(tapa)
        if base is not None:
            self._base = str(base)
        if tiene_fondo is not None:
            self._tiene_fondo = bool(tiene_fondo)
        cavidad = cavidad_interior(alto, ancho, espesor)
        self.inner_w = cavidad["ancho"]
        self.inner_h = cavidad["alto"]
        self._rebuild()
    def cargar_desde_objeto(self, obj):
        texto = getattr(obj, "VDO_Divisiones", "") or ""
        self._legacy_warnings = []
        self.layout = Layout.loads(texto)
        self.reengroses = self._leer_reengroses(obj)
        self._obj = obj
        self._fondo = float(getattr(obj, "FondoModulo", self._fondo))
        self._tapa = str(getattr(obj, "Tapa", self._tapa))
        self._base = str(getattr(obj, "Base", self._base))
        self._tiene_fondo = bool(
            getattr(obj, "TieneFondo", self._tiene_fondo))
        self._selected_reengrose_key = None
        self._selected_key = ("cell",
                              self.layout.columns[0].id,
                              self.layout.rows[0].id)
        # Cargar contenido de vanos persistido
        texto_contenido = getattr(obj, "VDO_Contenido_JSON", "") or "{}"
        try:
            self._contenido_por_celda = json.loads(texto_contenido)
            # Convertir claves de string "i,j" a tuplas
            self._contenido_por_celda = {
                tuple(map(int, k.split(","))): v
                for k, v in self._contenido_por_celda.items()
            }
        except (ValueError, TypeError, AttributeError):
            self._contenido_por_celda = {}
        self._rebuild()
    def dumps(self):
        return self.layout.dumps()
    def dumps_reengroses(self):
        return json.dumps(self.reengroses, ensure_ascii=False)
    def dumps_contenido(self):
        serializable = {
            f"{i},{j}": v for (i, j), v in self._contenido_por_celda.items()
        }
        return json.dumps(serializable, ensure_ascii=False)
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
        # Mapeo label de celda -> (col, row) para el preview 2D
        self._label_to_colrow = {}
        for j, row in enumerate(self._resolved.rows):
            for i, col in enumerate(self._resolved.columns):
                cell = self.layout.get_cell(i, j)
                if cell is not None:
                    resuelto = self._resolved_map.get(cell.label)
                    if resuelto is not None:
                        self._label_to_colrow[resuelto.label] = (i, j)
        self._pintar_arbol()
        self.preview.set_layout(
            self._resolved, self.outer_w, self.outer_h,
            selected=self._label_seleccionado(),
            reengroses=self.reengroses,
            entities=self._piezas_fisicas(),
            fondo=self._fondo,
            contenido_por_celda=self._contenido_por_celda,
            label_to_colrow=self._label_to_colrow)
        self.lbl_resumen.setText(self.resumen())
        self._poblar_elementos_reengrose()
        self._restaurar_seleccion()

    def _on_modo_changed(self, index):
        if self._building:
            return
        modo = "vanos" if index == 0 else "estructura"
        if modo == self.mode:
            return
        self.mode = modo
        if modo == "vanos":
            self._selected_key = (
                "cell", self.layout.columns[0].id,
                self.layout.rows[0].id)
        else:
            piezas = self._piezas_fisicas()
            self._selected_key = (
                ("piece", piezas[0]["key"]) if piezas
                else ("cell", self.layout.columns[0].id,
                      self.layout.rows[0].id))
        self._selected_data = None
        self._rebuild()

    def _pintar_arbol(self):
        self.tree.blockSignals(True)
        self.tree.clear()
        if self.mode == "estructura":
            self.tree.setHeaderLabels(
                ["Pieza", "Largo", "Ancho", "Espesor"])
            self._pintar_estructura()
        else:
            self.tree.setHeaderLabels(
                ["Vano", "X libre", "Y libre", "Subdivisión"])
            self._pintar_vanos()
        self.tree.expandAll()
        self.tree.blockSignals(False)

    def _pintar_vanos(self):
        root = QtWidgets.QTreeWidgetItem([
            f"COCO — Matriz {len(self.layout.columns)} × "
            f"{len(self.layout.rows)}", "", "", ""])
        root.setFlags(root.flags() & ~QtCore.Qt.ItemIsSelectable)
        self.tree.addTopLevelItem(root)

        for j, row in enumerate(self._resolved.rows):
            row_item = QtWidgets.QTreeWidgetItem([
                f"Y{j + 1}", "", f"{row.size:.1f}",
                "fijo" if row.fixed is not None else "libre"])
            row_item.setData(0, ROLE_DATA, {
                "kind": "row", "row_index": j, "row": row})
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

                # Hijos del vano: puertas, cajones, torres
                contenido = self._contenido_por_celda.get((i, j))
                if contenido:
                    tipo = contenido.get("tipo", "vacio")
                    if tipo == "puerta":
                        cfg = contenido.get("config", {})
                        nombre = cfg.get("nombre", f"Puerta_{cell.label}")
                        montaje = cfg.get("tipo_montaje", "Parche")
                        apertura = cfg.get("sistema_apertura", "tirador")
                        child = QtWidgets.QTreeWidgetItem([
                            f"🚪 Puerta ({montaje} · {apertura})", "", "", ""])
                        child.setData(0, ROLE_DATA, {
                            "kind": "contenido_hijo",
                            "tipo": "puerta",
                            "celda": (i, j),
                            "config": cfg,
                        })
                        item.addChild(child)
                    elif tipo == "cajon":
                        cfg = contenido.get("config", {})
                        cantidad = cfg.get("cantidad", 1)
                        corredera = cfg.get("corredera", "Oculta")
                        apertura = cfg.get("apertura", "Tirador")
                        child = QtWidgets.QTreeWidgetItem([
                            f"🗄️ Cajón ×{cantidad} ({corredera} · {apertura})",
                            "", "", ""])
                        child.setData(0, ROLE_DATA, {
                            "kind": "contenido_hijo",
                            "tipo": "cajon",
                            "celda": (i, j),
                            "config": cfg,
                        })
                        item.addChild(child)

        for pieza in self._piezas_fisicas():
            item = QtWidgets.QTreeWidgetItem([
                pieza["nombre"], "", "", ""])
            item.setData(0, ROLE_DATA, {
                "kind": "elemento_reengrose",
                "clave": pieza["key"],
                "pieza": pieza,
            })
            item.setHidden(True)
            root.addChild(item)
            self._items_by_key[("elemento", pieza["key"])] = item

    def _pintar_estructura(self):
        root = QtWidgets.QTreeWidgetItem([
            "COCO — Estructura física", "", "", ""])
        root.setFlags(root.flags() & ~QtCore.Qt.ItemIsSelectable)
        self.tree.addTopLevelItem(root)

        grupos = (
            ("Horizontales", "horizontal"),
            ("Verticales", "vertical"),
        )
        piezas = self._piezas_fisicas()
        for titulo, grupo in grupos:
            grupo_item = QtWidgets.QTreeWidgetItem([
                f"▾ {titulo}", "", "", ""])
            grupo_item.setFlags(
                grupo_item.flags() & ~QtCore.Qt.ItemIsSelectable)
            root.addChild(grupo_item)
            for pieza in piezas:
                if pieza["grupo"] != grupo:
                    continue
                item = self._crear_item_pieza(pieza, grupo_item)
                self._items_by_key[("piece", pieza["key"])] = item
                self._items_by_key[("elemento", pieza["key"])] = item
                if pieza["key"] in self.reengroses:
                    self._crear_item_reengrose(pieza, item)

    def _crear_item_pieza(self, pieza, parent):
        item = QtWidgets.QTreeWidgetItem([
            pieza["nombre"],
            f"{pieza['largo']:.1f}",
            f"{pieza['ancho']:.1f}",
            f"{pieza['espesor']:.1f}",
        ])
        item.setData(0, ROLE_DATA, {
            "kind": "piece",
            "clave": pieza["key"],
            "pieza": pieza,
        })
        item.setToolTip(
            0, f"{pieza['nombre']}\n"
               f"{pieza['largo']:.1f} × {pieza['ancho']:.1f} × "
               f"{pieza['espesor']:.1f} mm")
        parent.addChild(item)
        return item

    def _crear_item_reengrose(self, pieza, parent):
        item = QtWidgets.QTreeWidgetItem([
            "🪵 Reengrose · tira", "", "", ""])
        item.setData(0, ROLE_DATA, {
            "kind": "reengrose_piece",
            "clave": pieza["key"],
            "pieza": pieza,
        })
        item.setToolTip(
            0, f"Tira de reengrose de {pieza['nombre']}")
        parent.addChild(item)
        self._items_by_key[("reengrose", pieza["key"])] = item
        return item
    def _vistos(self):
        if self._obj is not None:
            try:
                vistos, _apoyados = VDO_FR.cargar_exposicion(self._obj)
                if vistos:
                    return list(vistos)
            except Exception:
                pass
        return [VDO_FR.FRENTE]

    def _cantos_pieza(self, rol, clave=None, es_reengrose=False):
        try:
            cantos = VDO_FIN.cantos_para_rol(
                rol, self._vistos(), tapa=self._tapa, base=self._base)
        except Exception:
            cantos = {borde: "FX" for borde in BORDES}
        if es_reengrose and clave:
            datos = self.reengroses.get(clave)
            if datos:
                try:
                    mod = VDO_RE.ReengroseModifier(datos)
                    plan = VDO_RE.resolver_politica_cantos(
                        {"cantos": cantos}, mod)
                    cantos = (
                        plan.get("tira") or plan.get("bloque") or cantos)
                except Exception:
                    pass
        return cantos

    def _piezas_fisicas(self):
        """Registro 2D de piezas físicas para árbol, header y preview."""
        t = float(self.thickness)
        outer_w = float(self.outer_w)
        outer_h = float(self.outer_h)
        fondo = float(self._fondo)
        inner_w = float(self.inner_w)
        inner_h = float(self.inner_h)
        lat_h = outer_h
        if self._tapa == "externo":
            lat_h -= t
        if self._base == "externo":
            lat_h -= t
        base_len = outer_w if self._base == "externo" else max(
            0.0, outer_w - 2.0 * t)
        techo_len = outer_w if self._tapa == "externo" else max(
            0.0, outer_w - 2.0 * t)

        piezas = []

        def agregar(clave, nombre, grupo, rol, largo, ancho, espesor,
                    caja, ejes):
            piezas.append({
                "key": clave,
                "nombre": nombre,
                "grupo": grupo,
                "rol": rol,
                "largo": float(largo),
                "ancho": float(ancho),
                "espesor": float(espesor),
                "caja": caja,
                "ejes": ejes,
                "cantos": self._cantos_pieza(rol, clave, False),
            })

        agregar(
            "base", "Base", "horizontal", "base",
            base_len, fondo, t,
            {"nombre": "Base", "x": 0.0, "y": 0.0, "z": 0.0,
             "w": inner_w, "h": fondo, "d": t},
            {"largo": "x", "ancho": "y", "espesor": "z"})
        agregar(
            "techo", "Techo", "horizontal", "techo",
            techo_len, fondo, t,
            {"nombre": "Techo", "x": 0.0, "y": 0.0, "z": inner_h,
             "w": inner_w, "h": fondo, "d": t},
            {"largo": "x", "ancho": "y", "espesor": "z"})

        agregar(
            "lateral_izquierdo", "Lateral Izq", "vertical",
            "lateral_izquierdo", fondo, lat_h, t,
            {"nombre": "Lateral Izq", "x": 0.0, "y": 0.0, "z": 0.0,
             "w": t, "h": fondo, "d": inner_h},
            {"largo": "z", "ancho": "y", "espesor": "x"})
        agregar(
            "lateral_derecho", "Lateral Der", "vertical",
            "lateral_derecho", fondo, lat_h, t,
            {"nombre": "Lateral Der", "x": max(0.0, inner_w - t),
             "y": 0.0, "z": 0.0, "w": t, "h": fondo, "d": inner_h},
            {"largo": "z", "ancho": "y", "espesor": "x"})
        if self._tiene_fondo:
            agregar(
                "fondo", "Fondo", "vertical", "fondo",
                inner_w, inner_h, t,
                {"nombre": "Fondo", "x": 0.0, "y": max(0.0, fondo - t),
                 "z": 0.0, "w": inner_w, "h": t, "d": inner_h},
                {"largo": "x", "ancho": "z", "espesor": "y"})

        h_seq = 0
        v_seq = 0
        for pieza in (self._resolved.pieces if self._resolved else []):
            clave = (
                f"division_x:{pieza.path}" if pieza.axis == AXIS_X
                else f"division_y:{pieza.path}")
            if pieza.axis == AXIS_Y:
                h_seq += 1
                nombre = f"H{h_seq} · {pieza.nombre}"
                agregar(
                    clave, nombre, "horizontal", "division_y",
                    pieza.w, fondo, t,
                    {"nombre": pieza.nombre, "x": pieza.x, "y": 0.0,
                     "z": pieza.z, "w": pieza.w, "h": fondo, "d": t},
                    {"largo": "x", "ancho": "y", "espesor": "z"})
            else:
                v_seq += 1
                nombre = f"V{v_seq} · {pieza.nombre}"
                agregar(
                    clave, nombre, "vertical", "division_x",
                    fondo, pieza.h, t,
                    {"nombre": pieza.nombre, "x": pieza.x, "y": 0.0,
                     "z": pieza.z, "w": t, "h": fondo, "d": pieza.h},
                    {"largo": "z", "ancho": "y", "espesor": "x"})
        return piezas

    def _pieza_por_clave(self, clave):
        for pieza in self._piezas_fisicas():
            if pieza["key"] == clave:
                return pieza
        return None

    def _reengroses_invasores(self, resuelto):
        if resuelto is None:
            return []
        x0, z0 = resuelto.nominal_x, resuelto.nominal_z
        x1 = x0 + resuelto.nominal_w
        z1 = z0 + resuelto.nominal_h
        invasores = []
        for clave, datos in self.reengroses.items():
            if not datos:
                continue
            pieza = self._pieza_por_clave(clave)
            if pieza is None:
                continue
            try:
                mod = VDO_RE.ReengroseModifier(datos)
                geo = VDO_RE.calcular_geometria_caja(
                    pieza["caja"], mod, pieza["ejes"])
            except Exception:
                continue
            for ref in geo.get("refuerzos") or []:
                rx0, rz0 = float(ref["x"]), float(ref["z"])
                rx1 = rx0 + float(ref["w"])
                rz1 = rz0 + float(ref["d"])
                if (min(x1, rx1) - max(x0, rx0) > 1e-6
                        and min(z1, rz1) - max(z0, rz0) > 1e-6):
                    invasores.append(pieza["nombre"])
                    break
        return invasores
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
        if data.get("kind") not in ("cell", "nested"):
            return None
        cell = data.get("cell")
        return cell.label if cell is not None else None

    def _restaurar_seleccion(self):
        item = self._items_by_key.get(self._selected_key)
        if item is None:
            if self.mode == "estructura":
                piezas = self._piezas_fisicas()
                if piezas:
                    key = ("piece", piezas[0]["key"])
                    item = self._items_by_key.get(key)
                    self._selected_key = key
            else:
                key = ("cell", self.layout.columns[0].id,
                       self.layout.rows[0].id)
                item = self._items_by_key.get(key)
                self._selected_key = key
        if item is not None:
            self.tree.blockSignals(True)
            self.tree.setCurrentItem(item)
            self.tree.blockSignals(False)
            self._seleccionar_item(item)
    def _on_tree_selection(self):
        items = self.tree.selectedItems()
        if not items:
            return
        self._seleccionar_item(items[0])
    def _seleccionar_item(self, item):
        data = item.data(0, ROLE_DATA)
        if not data:
            return
        kind = data.get("kind")
        if kind in ("elemento_reengrose", "piece", "reengrose_piece"):
            self._selected_data = data
            clave = data["clave"]
            if kind == "piece":
                self._selected_key = ("piece", clave)
            elif kind == "reengrose_piece":
                self._selected_key = ("reengrose", clave)
            else:
                self._selected_key = ("elemento", clave)
            self._selected_reengrose_key = clave
            idx = self.combo_elemento_reengrose.findData(clave)
            if idx >= 0:
                self._building = True
                self.combo_elemento_reengrose.setCurrentIndex(idx)
                self._building = False
            if not self._skip_cargar_reengrose:
                self._cargar_reengrose_controls(clave)
            if hasattr(self.preview, "set_selected_entity"):
                tipo_preview = (
                    "reengrose" if kind == "reengrose_piece"
                    else "panel")
                self.preview.set_selected_entity(tipo_preview, clave)
            else:
                self.preview.set_selected(None)
            self._actualizar_inspector()
            return

        self._selected_data = data
        cell = data.get("cell")
        if kind == "row":
            self._selected_key = ("row", data["row_index"])
        elif kind == "cell":
            self._selected_key = (
                "cell", self.layout.columns[data["col_index"]].id,
                self.layout.rows[data["row_index"]].id)
        else:
            self._selected_key = ("nested", cell.px, cell.py)
        self.preview.set_selected(
            cell.label if cell is not None else None)
        self._actualizar_inspector()

    def _seleccionar_por_label(self, label):
        if self.mode != "vanos":
            self._ir_a_modo("vanos", None)
        item = self._items_by_label.get(label)
        if item is None:
            return
        self.tree.blockSignals(True)
        self.tree.setCurrentItem(item)
        self.tree.blockSignals(False)
        self._seleccionar_item(item)

    def _seleccionar_panel_preview(self, clave):
        self._seleccionar_clave_en_modo("estructura", ("piece", clave))

    def _seleccionar_reengrose_preview(self, clave):
        self._seleccionar_clave_en_modo(
            "estructura", ("reengrose", clave))

    def _seleccionar_clave_en_modo(self, modo, key):
        if self.mode != modo:
            self._ir_a_modo(modo, key)
            return
        item = self._items_by_key.get(key)
        if item is None and key and key[0] == "reengrose":
            item = self._items_by_key.get(("piece", key[1]))
        if item is None:
            return
        self.tree.blockSignals(True)
        self.tree.setCurrentItem(item)
        self.tree.blockSignals(False)
        self._seleccionar_item(item)

    def _ir_a_modo(self, modo, key):
        self.mode = modo
        self._selected_key = key
        self._selected_data = None
        self._building = True
        self.tabs_modo.setCurrentIndex(0 if modo == "vanos" else 1)
        self._building = False
        self._rebuild()
    def _actualizar_inspector(self):
        data = self._selected_data
        if not data:
            self.header.setVisible(False)
            self.lbl_nominal_neto.setVisible(False)
            self.lbl_invasores.setVisible(False)
            self.lbl_sel.setText("Sin selección.")
            return
        self._building = True
        kind = data["kind"]
        es_pieza = kind in (
            "piece", "reengrose_piece", "elemento_reengrose")
        self.header.setVisible(es_pieza)
        self.grupo_reengrose.setVisible(es_pieza)
        self.lbl_nominal_neto.setVisible(
            kind in ("cell", "nested"))
        self.lbl_invasores.setVisible(kind in ("cell", "nested"))
        self.widget_col_fixed.setVisible(kind == "cell")
        self.widget_row_fixed.setVisible(kind in ("cell", "row"))
        self.widget_cell_fixed.setVisible(kind == "nested")
        self.lbl_contenido.setVisible(kind in ("cell", "nested"))
        self.combo_contenido.setVisible(kind in ("cell", "nested"))
        self.widget_split.setVisible(False)
        self.widget_puerta.setVisible(False)
        self.widget_cajon.setVisible(False)
        self.lbl_aviso.setText("")

        if kind in ("cell", "nested"):
            cell = data.get("cell")
            contenido = self._contenido_por_celda.get(
                (data.get("col_index"), data.get("row_index")), {"tipo": "vacio"})
            idx = self.combo_contenido.findData(contenido["tipo"])
            if idx >= 0:
                self.combo_contenido.blockSignals(True)
                self.combo_contenido.setCurrentIndex(idx)
                self.combo_contenido.blockSignals(False)
            self._mostrar_panel_contenido(contenido["tipo"])

        elif kind == "contenido_hijo":
            tipo = data.get("tipo")
            cfg = data.get("config", {})
            celda = data.get("celda")
            celda_label = ""
            if celda:
                try:
                    col, row = celda
                    resuelto = self._resolved_map.get(
                        self.layout.get_cell(col, row).label
                    )
                    if resuelto is not None:
                        celda_label = resuelto.label
                except (ValueError, TypeError, AttributeError):
                    celda_label = f"{celda}"
            # Ocultar panel de pieza física
            self.header.setVisible(False)
            self.grupo_reengrose.setVisible(False)
            self.lbl_nominal_neto.setVisible(False)
            self.lbl_invasores.setVisible(False)
            self.widget_col_fixed.setVisible(False)
            self.widget_row_fixed.setVisible(False)
            self.widget_cell_fixed.setVisible(False)
            self.lbl_contenido.setVisible(False)
            self.combo_contenido.setVisible(False)
            self.widget_split.setVisible(False)
            self.lbl_aviso.setText("")

            if tipo == "cajon":
                self.inspector.setTitle("Inspector de cajón")
                self.lbl_sel.setText(
                    f"<b>Cajón en vano {celda_label}</b>")
                self.widget_cajon.setVisible(True)
                self.widget_puerta.setVisible(False)
                # Cargar valores actuales en los spinners/combos
                self._building = True
                self.spin_cajon_cantidad.setValue(
                    int(cfg.get("cantidad", 1)))
                self._set_combo_data(
                    self.combo_cajon_corredera,
                    cfg.get("corredera", "Oculta"))
                self._set_combo_data(
                    self.combo_cajon_apertura,
                    cfg.get("apertura", "Tirador"))
                self._building = False
            elif tipo == "puerta":
                self.inspector.setTitle("Inspector de puerta")
                self.lbl_sel.setText(
                    f"<b>Puerta en vano {celda_label}</b>")
                self.widget_puerta.setVisible(True)
                self.widget_cajon.setVisible(False)
                # Cargar valores actuales en los combos
                self._building = True
                self._set_combo_data(
                    self.combo_puerta_familia,
                    cfg.get("tipo_sistema", "Batiente Vertical"))
                self._set_combo_data(
                    self.combo_puerta_montaje,
                    cfg.get("tipo_montaje", "Parche"))
                apertura_val = cfg.get("sistema_apertura", APERTURA_TIRADOR)
                apertura_label = {
                    APERTURA_TIRADOR: "Tirador",
                    APERTURA_GOLA: "Gola",
                    APERTURA_45_GRADOS: "45°",
                    APERTURA_PUSH_OPEN: "Push Open",
                }.get(apertura_val, "Tirador")
                self._set_combo_data(
                    self.combo_puerta_apertura, apertura_label)
                self._set_combo_data(
                    self.combo_puerta_herraje,
                    cfg.get("hardware_sku", ""))
                self._building = False

        if es_pieza:
            pieza = data.get("pieza")
            if pieza is None:
                pieza = self._pieza_por_clave(data["clave"])
            self.inspector.setTitle("Inspector de pieza")
            if pieza is not None:
                es_reengrose = kind != "piece"
                self._actualizar_header_pieza(pieza, es_reengrose)
                if es_reengrose:
                    self.lbl_sel.setText(
                        f"🪵 Reengrose de {pieza['nombre']}")
                else:
                    self.lbl_sel.setText(f"Pieza {pieza['nombre']}")
            else:
                self.header.clear()
                self.lbl_sel.setText("Pieza no disponible.")
            self.widget_split.setVisible(False)
            self.widget_puerta.setVisible(False)
            self.widget_cajon.setVisible(False)
            self.lbl_nominal_neto.setText("")
            self.lbl_invasores.setText("")
            self._building = False
            self._actualizar_aviso_overflow()
            return

        self.inspector.setTitle("Inspector del vano")
        cell = data.get("cell")

        if kind == "row":
            row = data["row"]
            self.lbl_sel.setText(f"Fila Y{data['row_index'] + 1}")
            self.chk_row_fixed.setChecked(row.fixed is not None)
            self.spin_row_fixed.setValue(
                row.fixed if row.fixed is not None else row.size)
            self.widget_split.setVisible(False)
            self.widget_puerta.setVisible(False)
            self.widget_cajon.setVisible(False)
            self.spin_row_fixed.setEnabled(row.fixed is not None)
            self.lbl_nominal_neto.setText("")
            self.lbl_invasores.setText("")
        else:
            resuelto = self._resolved_map.get(cell.label)
            self.lbl_sel.setText(
                f"Vano {cell.label}\nX libre: {resuelto.w:.1f} mm · "
                f"Y libre: {resuelto.h:.1f} mm")
            self.chk_col_fixed.setEnabled(True)
            if cell.axis and cell.children:
                idx = 0 if cell.axis == AXIS_X else 1
                self.combo_axis.setCurrentIndex(idx)
                self.spin_n.setValue(len(cell.children))
                self.combo_contenido.blockSignals(True)
                self.combo_contenido.setCurrentIndex(
                    self.combo_contenido.findData("subdivision"))
                self.combo_contenido.blockSignals(False)
                self.widget_split.setVisible(True)
                self.widget_puerta.setVisible(False)
                self.widget_cajon.setVisible(False)
            else:
                self.combo_axis.setCurrentIndex(
                    0 if self.combo_axis.currentData() != AXIS_Y else 1)
                self.spin_n.setValue(2)

            self.lbl_nominal_neto.setText(
                f"Nominal: {resuelto.nominal_w:.1f} × "
                f"{resuelto.nominal_h:.1f} mm\n"
                f"Neto: {resuelto.w:.1f} × {resuelto.h:.1f} mm")
            invasores = self._reengroses_invasores(resuelto)
            self.lbl_invasores.setText(
                ("Reengroses invasores: " + ", ".join(invasores))
                if invasores else "Sin reengroses invasores.")

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

    def _actualizar_header_pieza(self, pieza, es_reengrose):
        if pieza is None:
            self.header.clear()
            return
        if not es_reengrose:
            self.header.set_panel(
                pieza["nombre"], pieza["largo"], pieza["ancho"],
                pieza["espesor"], pieza["cantos"])
            return
        datos = self.reengroses.get(pieza["key"])
        cantos = self._cantos_pieza(
            pieza["rol"], pieza["key"], True)
        if not datos:
            self.header.set_panel(
                pieza["nombre"], pieza["largo"], pieza["ancho"],
                pieza["espesor"], cantos)
            return
        try:
            mod = VDO_RE.ReengroseModifier(datos)
            geo = VDO_RE.calcular_geometria_caja(
                pieza["caja"], mod, pieza["ejes"])
            refs = geo.get("refuerzos") or []
        except Exception:
            refs = []
        if not refs:
            self.header.set_panel(
                pieza["nombre"], pieza["largo"], pieza["ancho"],
                pieza["espesor"], cantos)
            return
        ref = refs[0]
        dim_key = {"x": "w", "y": "h", "z": "d"}
        largo = ref[dim_key[pieza["ejes"]["largo"]]]
        ancho = ref[dim_key[pieza["ejes"]["ancho"]]]
        espesor = ref[dim_key[pieza["ejes"]["espesor"]]]
        self.header.set_strip(
            pieza["nombre"], largo, ancho, espesor, cantos)
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

    def _on_contenido_changed(self, index):
        if self._building or not self._selected_data:
            return
        data = self._selected_data
        if data.get("kind") not in ("cell", "nested"):
            return
        tipo = self.combo_contenido.currentData()
        col = data.get("col_index")
        row = data.get("row_index")
        if col is None or row is None:
            return
        prev = self._contenido_por_celda.get((col, row), {"tipo": "vacio"})
        if prev["tipo"] == tipo:
            self._mostrar_panel_contenido(tipo)
            return
        # Solo actualizar el estado interno. NO crear objetos en el documento
        # aquí: la creación ocurre exclusivamente al presionar "Aceptar"
        # en CocoUnifiedTaskPanel.accept() -> _construir_insertos().
        self._contenido_por_celda[(col, row)] = {"tipo": tipo}
        self._guardar_config_actual(col, row)
        self._mostrar_panel_contenido(tipo)
        cell = data.get("cell")
        if cell is None:
            return
        resuelto = self._resolved_map.get(cell.label)
        if resuelto is None:
            return
        if tipo == "subdivision":
            if not (cell.axis and cell.children):
                try:
                    self.layout.set_split(cell, AXIS_X, 2)
                except LayoutError:
                    pass
                self._rebuild_y_avisar()
        else:
            # vacio / puerta / cajon: limpiar subdivisiones si las hay
            if cell.axis and cell.children:
                self.layout.disable_split(cell)
                self._rebuild_y_avisar()

    def _guardar_config_actual(self, col, row):
        """Lee los valores de los paneles reactivos y los guarda en
        _contenido_por_celda[(col, row)] para persistencia posterior."""
        datos = self._contenido_por_celda.get((col, row), {"tipo": "vacio"})
        tipo = datos.get("tipo", "vacio")
        cfg = dict(datos.get("config", {}))

        if tipo == "puerta":
            cfg.update({
                "nombre": f"Puerta_{(col, row)}",
                "tipo_sistema": self.combo_puerta_familia.currentText(),
                "tipo_montaje": self.combo_puerta_montaje.currentText(),
                "sentido_apertura": "Izquierda",
                "sistema_apertura": {
                    "Tirador": APERTURA_TIRADOR,
                    "Gola": APERTURA_GOLA,
                    "45°": APERTURA_45_GRADOS,
                    "Push Open": APERTURA_PUSH_OPEN,
                }.get(self.combo_puerta_apertura.currentText(), APERTURA_TIRADOR),
                "hardware_sku": self.combo_puerta_herraje.currentText(),
                "vdo_vano_id": f"({col},{row})",
                "ancho": 0.0,  # Se rellena en construir_insertos desde el resolved
                "alto": 0.0,
                "espesor": 18,
                "pos_x": 0.0,
                "pos_y": 0.0,
                "pos_z": 0.0,
                "anclaje": "inferior_izquierda_frente",
            })
        elif tipo == "cajon":
            cfg.update({
                "nombre": f"Cajon_{(col, row)}",
                "tipo": "cajon",
                "cantidad": self.spin_cajon_cantidad.value(),
                "corredera": self.combo_cajon_corredera.currentText(),
                "apertura": self.combo_cajon_apertura.currentText(),
                "vdo_vano_id": f"({col},{row})",
                "ancho": 0.0,
                "alto": 0.0,
                "espesor": 18,
                "pos_x": 0.0,
                "pos_y": 0.0,
                "pos_z": 0.0,
            })

        self._contenido_por_celda[(col, row)] = {"tipo": tipo, "config": cfg}

    def _mostrar_panel_contenido(self, tipo):
        self.widget_split.setVisible(tipo == "subdivision")
        self.widget_puerta.setVisible(tipo == "puerta")
        self.widget_cajon.setVisible(tipo == "cajon")
        if tipo == "subdivision":
            data = self._selected_data
            cell = data.get("cell") if data else None
            if cell and cell.axis and cell.children:
                idx = 0 if cell.axis == AXIS_X else 1
                self.combo_axis.setCurrentIndex(idx)
                self.spin_n.setValue(len(cell.children))
            self.widget_split.setVisible(True)

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
        return [
            (pieza["key"], pieza["nombre"])
            for pieza in self._piezas_fisicas()
        ]
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
        if not self._skip_cargar_reengrose:
            self._cargar_reengrose_controls(seleccion)
        self._building = previo
    def _cargar_reengrose_controls(self, clave):
        datos = self.reengroses.get(clave)
        try:
            mod = (
                VDO_RE.ReengroseModifier(datos) if datos
                else VDO_RE.ReengroseModifier())
        except VDO_RE.ReengroseError:
            mod = VDO_RE.ReengroseModifier()
        self.re_editor.cargar(mod)
        self._set_combo_data(
            self.combo_fabricacion, getattr(mod, "fabricacion", "pacha"))
        choque = getattr(mod, "choque_nucleo", "retroceso")
        if not datos and str(clave) in ("techo", "base"):
            choque = "mocheo"
        self._set_combo_data(self.combo_choque, choque)
        self._set_combo_data(
            self.combo_cara, getattr(mod, "cara", "cara_a"))
        self.re_editor._actualizar_resumen()
        self._actualizar_estado_reengrose()

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
        datos = self.re_editor.getConfig()
        datos["fabricacion"] = self.combo_fabricacion.currentData()
        datos["choque_nucleo"] = self.combo_choque.currentData()
        datos["cara"] = self.combo_cara.currentData()
        datos["activo"] = True
        return VDO_RE.normalizar_modificador(datos)

    def _actualizar_estado_reengrose(self):
        activo = self.chk_reengrose.isChecked()
        self.re_editor._actualizar_estado_habilitacion()
        self.combo_fabricacion.setEnabled(activo)
        self.combo_choque.setEnabled(activo)
        self.combo_cara.setEnabled(activo)
    def _on_reengrose_element_changed(self, *args):
        if self._building:
            return
        clave = self.combo_elemento_reengrose.currentData()
        if not clave:
            return
        self._selected_reengrose_key = clave
        self._cargar_reengrose_controls(clave)
    def _on_reengrose_changed(self, *args):
        if self._building or self._en_reengrose:
            return
        clave = self.combo_elemento_reengrose.currentData()
        if not clave:
            return
        self._en_reengrose = True
        self._skip_cargar_reengrose = True
        try:
            if not self.chk_reengrose.isChecked():
                self.reengroses.pop(clave, None)
            else:
                self.reengroses[clave] = self._leer_reengrose_ui()
            self._selected_reengrose_key = clave
            self._rebuild_y_avisar()
        finally:
            self._skip_cargar_reengrose = False
            self._en_reengrose = False
    def _confirmar(self, texto):
        respuesta = QtWidgets.QMessageBox.question(
            self, "Divisiones VDO", texto,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No)
        return respuesta == QtWidgets.QMessageBox.Yes
    def _mostrar_error(self, texto):
        self.lbl_aviso.setText("⚠ " + texto)
