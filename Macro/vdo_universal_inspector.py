# -*- coding: utf-8 -*-
# =====================================================================
# vdo_universal_inspector.py
# Inspector Universal Reactivo — Sistema VDO (FreeCAD).
#
# Un único panel permanente lateral con Zoom Semántico que reacciona en
# tiempo real a clics en el Viewport 3D y al árbol de FreeCAD, conectado
# al puente de selección nativa (VDOSelectionBridge).
#
# Acoplamiento Qt: permitido SOLO aquí (capa de UI). El puente de selección
# se mantiene puro y sin widgets Qt.
# =====================================================================

import os
import json

# Forzar plataforma offscreen si no hay display (freecadcmd / CI).
if os.environ.get("QT_QPA_PLATFORM") is None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:  # pragma: no cover - fallback para PySide2 / PySide
    try:
        from PySide2 import QtCore, QtGui, QtWidgets
    except ImportError:
        from PySide import QtCore, QtGui, QtWidgets

import FreeCAD as App

try:
    import FreeCADGui as Gui
except ImportError:  # pragma: no cover
    Gui = None

from vdo_selection_bridge import VDOSelectionBridge

try:
    from vdo_box_controller import VDOBoxControllerWidget
except ImportError:  # pragma: no cover
    VDOBoxControllerWidget = None

try:
    from vdo_chassis_widget import VDOChassisControllerWidget
except ImportError:  # pragma: no cover
    VDOChassisControllerWidget = None

import vdo_hardware_hub as HH
from vdo_qt import VDO_DoubleSpinBox


# ----------------------------------------------------------------------
# Constantes de navegación del QStackedWidget
# ----------------------------------------------------------------------
PAGE_CHASIS = 0   # COCO / Chasis L2 (VDOChassisControllerWidget)
PAGE_VANO = 1     # Vano libre L0 (Luz neta + Dock de Habitantes)
PAGE_PIEZA = 2    # PANEL L1 (Header + Cuadrado Figma)
PAGE_CIERRE = 3   # CAJON / PUERTA / ZOCALO (Herrajes y Capa H)

_TARGET_TO_PAGE = {
    VDOSelectionBridge.TARGET_COCO: PAGE_CHASIS,
    getattr(VDOSelectionBridge, "TARGET_VANO", "VANO"): PAGE_VANO,
    VDOSelectionBridge.TARGET_PANEL: PAGE_PIEZA,
    VDOSelectionBridge.TARGET_CAJON: PAGE_CIERRE,
    VDOSelectionBridge.TARGET_PUERTA: PAGE_CIERRE,
    VDOSelectionBridge.TARGET_ZOCALO: PAGE_CIERRE,
}


def _float_seguro(valor, default=0.0):
    try:
        if valor is None:
            return default
        return float(valor)
    except (TypeError, ValueError, AttributeError):
        return default


def _str_seguro(valor, default=""):
    try:
        if valor is None:
            return default
        return str(valor)
    except Exception:
        return default


# ----------------------------------------------------------------------
# Barra de Migas de Pan (Breadcrumbs)
# ----------------------------------------------------------------------
class _BreadcrumbBar(QtWidgets.QWidget):
    """Barra superior con eslabones interactivos para regresar a un nivel."""

    sigNivelClickeado = QtCore.Signal(str)  # emite el nombre del nivel

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("VDOBreadcrumbBar")
        self.setFixedHeight(34)
        self._niveles = []  # lista de (label, clave)
        self._nivel_activo = None

        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(8, 2, 8, 2)
        self.layout.setSpacing(4)

        self.lbl_inicio = QtWidgets.QLabel("🏠 Mueble")
        self.lbl_inicio.setObjectName("lblBreadcrumbRoot")
        self.lbl_inicio.setCursor(QtCore.Qt.PointingHandCursor)
        self.lbl_inicio.setStyleSheet(
            "QLabel#lblBreadcrumbRoot { color: #0098ff; font-weight: bold; }")
        self.lbl_inicio.mousePressEvent = lambda _e: self.sigNivelClickeado.emit("mueble")
        self.layout.addWidget(self.lbl_inicio)

        self.layout.addStretch()

    def set_ruta(self, niveles, activo=None):
        """niveles: lista de (label, clave). Activo: clave del nivel actual."""
        while self.layout.count() > 2:
            item = self.layout.takeAt(1)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self._niveles = list(niveles)
        self._nivel_activo = activo

        for label, clave in niveles:
            sep = QtWidgets.QLabel(" › ")
            sep.setStyleSheet("color: #666666; font-size: 11px;")
            self.layout.insertWidget(self.layout.count() - 1, sep)

            lbl = QtWidgets.QLabel(label)
            lbl.setObjectName(f"lblBreadcrumb_{clave}")
            lbl.setCursor(QtCore.Qt.PointingHandCursor)
            activo_es = (clave == activo)
            lbl.setStyleSheet(
                f"QLabel#lblBreadcrumb_{clave} {{ "
                f"color: {'#ffffff' if activo_es else '#aaaaaa'}; "
                f"font-weight: {'bold' if activo_es else 'normal'}; "
                f"font-size: 11px; }}"
            )
            lbl.mousePressEvent = (
                lambda _e, c=clave: self.sigNivelClickeado.emit(c))
            self.layout.insertWidget(self.layout.count() - 1, lbl)

    def limpiar(self):
        self.set_ruta([], activo=None)


# ----------------------------------------------------------------------
# Páginas del QStackedWidget (Con Contenedores Scrollables)
# ----------------------------------------------------------------------
class _PaginaBase(QtWidgets.QWidget):
    """Página base con contenedor scrollable de datos."""

    def __init__(self, titulo, parent=None):
        super().__init__(parent)
        self._titulo = titulo

        layout_externo = QtWidgets.QVBoxLayout(self)
        layout_externo.setContentsMargins(0, 0, 0, 0)
        layout_externo.setSpacing(0)

        # ScrollArea para evitar overflow en TaskPanels estrechos
        self.scroll = QtWidgets.QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background-color: transparent; }")

        self.contenido = QtWidgets.QWidget()
        self._layout = QtWidgets.QVBoxLayout(self.contenido)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(6)

        self.lbl_titulo = QtWidgets.QLabel(titulo)
        self.lbl_titulo.setObjectName("lblPaginaTitulo")
        self.lbl_titulo.setStyleSheet(
            "QLabel#lblPaginaTitulo { color: #0098ff; font-size: 13px; "
            "font-weight: bold; padding-bottom: 2px; }")
        self._layout.addWidget(self.lbl_titulo)

        self.contenedor_datos = QtWidgets.QVBoxLayout()
        self.contenedor_datos.setSpacing(4)
        self._layout.addLayout(self.contenedor_datos)
        self._layout.addStretch()

        self.scroll.setWidget(self.contenido)
        layout_externo.addWidget(self.scroll)

    def _add_dato(self, etiqueta, valor):
        fila = QtWidgets.QHBoxLayout()
        lbl_key = QtWidgets.QLabel(etiqueta)
        lbl_key.setFixedWidth(130)
        lbl_key.setStyleSheet("color: #aaaaaa; font-size: 10px;")
        lbl_val = QtWidgets.QLabel(str(valor))
        lbl_val.setStyleSheet("color: #e0e0e0; font-size: 11px; font-weight: bold;")
        fila.addWidget(lbl_key)
        fila.addWidget(lbl_val)
        fila.addStretch()
        self.contenedor_datos.addLayout(fila)
        return lbl_val


# ----------------------------------------------------------------------
# PÁGINA 0: CHASIS L2 (VDOChassisControllerWidget)
# ----------------------------------------------------------------------
class PaginaChasis(_PaginaBase):
    """Nivel Chasis / Envolvente (L2): Corte Transversal 2D interactivo."""

    def __init__(self, parent=None):
        super().__init__("Chasis / Envolvente del Mueble (L2)", parent)
        self._obj_actual = None

        # Fila de métricas rápidas superiores
        self.lbl_alto = self._add_dato("Alto", "—")
        self.lbl_ancho = self._add_dato("Ancho", "—")
        self.lbl_fondo = self._add_dato("Fondo", "—")
        self.lbl_anclaje = self._add_dato("Sistema de anclaje", "—")
        self.lbl_subtipo = self._add_dato("Subtipo", "—")

        # Separador
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setStyleSheet("color: #333333; margin: 4px 0;")
        self.contenedor_datos.addWidget(sep)

        # Widget de corte transversal interactivo 2D
        self.box_chassis = None
        if VDOChassisControllerWidget is not None:
            self.box_chassis = VDOChassisControllerWidget()
            self.box_chassis.sigChassisChanged.connect(self._on_chassis_changed)
            self.contenedor_datos.addWidget(self.box_chassis)

    def cargar_coco(self, obj):
        """Carga los parámetros del chasis desde un objeto FreeCAD."""
        self._obj_actual = obj
        alto = _float_seguro(getattr(obj, "Alto", None))
        ancho = _float_seguro(getattr(obj, "Ancho", None))
        fondo = _float_seguro(getattr(obj, "FondoModulo", None))
        anclaje = _str_seguro(getattr(obj, "VDO_Anclaje", None))
        subtipo = _str_seguro(getattr(obj, "VDO_Subtipo", None))

        self.lbl_alto.setText(f"{alto:.1f} mm" if alto else "—")
        self.lbl_ancho.setText(f"{ancho:.1f} mm" if ancho else "—")
        self.lbl_fondo.setText(f"{fondo:.1f} mm" if fondo else "—")
        self.lbl_anclaje.setText(anclaje if anclaje else "—")
        self.lbl_subtipo.setText(subtipo if subtipo else "—")

        if self.box_chassis is not None:
            # Leer configuración persistida en el objeto si existe
            raw_cfg = getattr(obj, "VDO_Chassis_JSON", None)
            if raw_cfg:
                try:
                    cfg = json.loads(raw_cfg) if isinstance(raw_cfg, str) else raw_cfg
                    self.box_chassis.setChassisConfig(cfg)
                    return
                except Exception:
                    pass

            # Configuración derivada por defecto según propiedades del objeto
            cfg_default = {
                "caras": {
                    "superior": {"activa": True, "tipo": "estructural"},
                    "inferior": {"activa": True, "tipo": "estructural"},
                    "izquierda": {"activa": True, "tipo": "estructural"},
                    "derecha": {"activa": True, "tipo": "estructural"},
                    "fondo": {"activa": True, "tipo": "ranurado_5mm"},
                },
                "encuentros": {
                    "superior_izq": "tapa_domina",
                    "superior_der": "tapa_domina",
                    "inferior_izq": "lateral_domina",
                    "inferior_der": "lateral_domina",
                },
                "base": {
                    "estrategia": "zocalo" if getattr(obj, "AltoZocalo", None) else "zocalo",
                    "altura": _float_seguro(getattr(obj, "AltoZocalo", None), 100.0),
                    "separacion_frente": _float_seguro(getattr(obj, "DistanciaFrente", None), 50.0),
                }
            }
            self.box_chassis.setChassisConfig(cfg_default)

    def _on_chassis_changed(self, cfg):
        """Persiste la configuración modificada en el objeto FreeCAD."""
        obj = self._obj_actual
        if obj is None:
            return
        try:
            if hasattr(obj, "VDO_Chassis_JSON"):
                obj.VDO_Chassis_JSON = json.dumps(cfg)
            elif hasattr(obj, "addProperty"):
                try:
                    obj.addProperty("App::PropertyString", "VDO_Chassis_JSON", "VDO",
                                    "Configuración semiótica de Capa 1")
                    obj.VDO_Chassis_JSON = json.dumps(cfg)
                except Exception:
                    pass

            doc = getattr(obj, "Document", None)
            if doc is not None:
                doc.recompute()
        except Exception:
            pass


# ----------------------------------------------------------------------
# PÁGINA 1: VANO L0 (Luz Neta y Dock Táctil de Habitantes)
# ----------------------------------------------------------------------
class PaginaVano(_PaginaBase):
    """Nivel Vano Libre (L0): Luz neta y Dock táctil de habitantes."""

    sigHabitanteCambiado = QtCore.Signal(str, dict)  # (tipo_habitante, configuracion)

    def __init__(self, parent=None):
        super().__init__("Vano Libre / Cavidad Útil (L0)", parent)
        self._obj_actual = None
        self._luz = {"w": 564.0, "h": 280.0, "d": 550.0}

        # Etiquetas retrocompatibles de datos
        self.lbl_luz_w = self._add_dato("Luz neta W", "—")
        self.lbl_luz_h = self._add_dato("Luz neta H", "—")
        self.lbl_luz_d = self._add_dato("Luz neta D", "—")
        self.lbl_subdiv = self._add_dato("Subdivisión", "—")

        # -------------------------------------------------------------
        # Banner de Luz Libre Real
        # -------------------------------------------------------------
        self.banner_luz = QtWidgets.QFrame()
        self.banner_luz.setStyleSheet(
            "QFrame { background-color: #22252a; border: 1px solid #007acc; "
            "border-radius: 5px; padding: 4px; }")
        lay_b = QtWidgets.QHBoxLayout(self.banner_luz)
        lay_b.setContentsMargins(6, 4, 6, 4)

        self.lbl_luz_banner = QtWidgets.QLabel("📐 <b>LUZ LIBRE NETA:</b> 564 × 280 × 550 mm")
        self.lbl_luz_banner.setStyleSheet("color: #00d4ff; font-size: 11px;")
        lay_b.addWidget(self.lbl_luz_banner)
        self.contenedor_datos.addWidget(self.banner_luz)

        # -------------------------------------------------------------
        # Dock Táctil de Habitantes (4 Acciones)
        # -------------------------------------------------------------
        lbl_dock = QtWidgets.QLabel("HABITANTE DEL VANO:")
        lbl_dock.setStyleSheet("color: #888888; font-size: 9px; font-weight: bold; margin-top: 6px;")
        self.contenedor_datos.addWidget(lbl_dock)

        fila_dock = QtWidgets.QHBoxLayout()
        fila_dock.setSpacing(4)

        self.btn_dock = {}
        habitantes_spec = [
            ("subdividir", "➗ Subdividir", "Subdividir el vano con vdo_layout"),
            ("cajon", "🗄 Cajón", "Insertar torre de cajones y rieles"),
            ("puerta", "🚪 Puerta", "Insertar puerta batiente, basculante o corrediza"),
            ("vacio", "🔲 Vacío", "Restaurar vano libre sin insertos"),
        ]
        for key, text, tip in habitantes_spec:
            btn = QtWidgets.QPushButton(text)
            btn.setCheckable(True)
            btn.setToolTip(tip)
            btn.setFixedHeight(28)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #282828;
                    border: 1px solid #3d3d3d;
                    border-radius: 4px;
                    font-size: 10px;
                    color: #cccccc;
                }
                QPushButton:checked {
                    background-color: #007acc;
                    border-color: #0098ff;
                    color: #ffffff;
                    font-weight: bold;
                }
                QPushButton:hover:!checked {
                    background-color: #333333;
                    color: #ffffff;
                }
            """)
            btn.clicked.connect(lambda _, k=key: self._on_dock_clicked(k))
            fila_dock.addWidget(btn)
            self.btn_dock[key] = btn

        self.btn_dock["vacio"].setChecked(True)
        self.contenedor_datos.addLayout(fila_dock)

        # -------------------------------------------------------------
        # Sub-paneles Contextuales del Dock
        # -------------------------------------------------------------
        self.stack_dock = QtWidgets.QStackedWidget()
        self.stack_dock.setStyleSheet("background-color: #1a1a1a; border-radius: 4px;")

        # 0. Subdividir
        panel_subdiv = QtWidgets.QWidget()
        lay_sub = QtWidgets.QVBoxLayout(panel_subdiv)
        lay_sub.setContentsMargins(6, 6, 6, 6)
        lay_sub.setSpacing(4)

        f_eje = QtWidgets.QHBoxLayout()
        f_eje.addWidget(QtWidgets.QLabel("Eje:"))
        self.combo_eje = QtWidgets.QComboBox()
        self.combo_eje.addItems(["Horizontal (Repisas en Y)", "Vertical (Montantes en X)"])
        f_eje.addWidget(self.combo_eje, 1)
        lay_sub.addLayout(f_eje)

        f_n = QtWidgets.QHBoxLayout()
        f_n.addWidget(QtWidgets.QLabel("Número de vanos:"))
        self.spin_n_partes = QtWidgets.QSpinBox()
        self.spin_n_partes.setRange(2, 8)
        self.spin_n_partes.setValue(2)
        f_n.addWidget(self.spin_n_partes, 1)
        lay_sub.addLayout(f_n)

        f_modo = QtWidgets.QHBoxLayout()
        f_modo.addWidget(QtWidgets.QLabel("Modo:"))
        self.combo_dist = QtWidgets.QComboBox()
        self.combo_dist.addItems(["Equitativo (1/N partes iguales)", "Medida fija personalizada"])
        f_modo.addWidget(self.combo_dist, 1)
        lay_sub.addLayout(f_modo)

        btn_ap_sub = QtWidgets.QPushButton("➗ Aplicar Subdivisión")
        btn_ap_sub.setStyleSheet("background-color: #007acc; color: white; font-weight: bold; padding: 4px;")
        btn_ap_sub.clicked.connect(self._aplicar_subdivision)
        lay_sub.addWidget(btn_ap_sub)
        self.stack_dock.addWidget(panel_subdiv)

        # 1. Cajón
        panel_cajon = QtWidgets.QWidget()
        lay_caj = QtWidgets.QVBoxLayout(panel_cajon)
        lay_caj.setContentsMargins(6, 6, 6, 6)
        lay_caj.setSpacing(4)

        f_nc = QtWidgets.QHBoxLayout()
        f_nc.addWidget(QtWidgets.QLabel("Cantidad cajones:"))
        self.spin_cajones = QtWidgets.QSpinBox()
        self.spin_cajones.setRange(1, 4)
        self.spin_cajones.setValue(1)
        f_nc.addWidget(self.spin_cajones, 1)
        lay_caj.addLayout(f_nc)

        f_cor = QtWidgets.QHBoxLayout()
        f_cor.addWidget(QtWidgets.QLabel("Corredera:"))
        self.combo_corredera = QtWidgets.QComboBox()
        self.combo_corredera.addItems(["Oculta Blum Tandem (Cierre Suave)", "Telescópica Pesada 45mm"])
        f_cor.addWidget(self.combo_corredera, 1)
        lay_caj.addLayout(f_cor)

        f_ag_caj = QtWidgets.QHBoxLayout()
        f_ag_caj.addWidget(QtWidgets.QLabel("Frente / Agarre:"))
        self.combo_agarre_caj = QtWidgets.QComboBox()
        self.combo_agarre_caj.addItems(["Tirador aplicado", "Perfil Gola", "Chaflán 45°"])
        f_ag_caj.addWidget(self.combo_agarre_caj, 1)
        lay_caj.addLayout(f_ag_caj)

        self.lbl_cajon_hub = QtWidgets.QLabel("SKU: BLUM-TANDEM | Blum | $12.50 USD")
        self.lbl_cajon_hub.setStyleSheet("color: #28a745; font-size: 10px;")
        lay_caj.addWidget(self.lbl_cajon_hub)

        btn_ap_caj = QtWidgets.QPushButton("🗄 Insertar Cajón")
        btn_ap_caj.setStyleSheet("background-color: #007acc; color: white; font-weight: bold; padding: 4px;")
        btn_ap_caj.clicked.connect(self._aplicar_cajon)
        lay_caj.addWidget(btn_ap_caj)
        self.stack_dock.addWidget(panel_cajon)

        # 2. Puerta
        panel_puerta = QtWidgets.QWidget()
        lay_pue = QtWidgets.QVBoxLayout(panel_puerta)
        lay_pue.setContentsMargins(6, 6, 6, 6)
        lay_pue.setSpacing(4)

        f_sis = QtWidgets.QHBoxLayout()
        f_sis.addWidget(QtWidgets.QLabel("Sistema:"))
        self.combo_sistema_pue = QtWidgets.QComboBox()
        self.combo_sistema_pue.addItems(["Batiente Vertical (Cazoleta 35mm)", "Basculante / Flap (Pistón)", "Corrediza (Ducasse)"])
        f_sis.addWidget(self.combo_sistema_pue, 1)
        lay_pue.addLayout(f_sis)

        f_sen = QtWidgets.QHBoxLayout()
        f_sen.addWidget(QtWidgets.QLabel("Sentido:"))
        self.combo_sentido_pue = QtWidgets.QComboBox()
        self.combo_sentido_pue.addItems(["Izquierda", "Derecha", "Doble Hoja"])
        f_sen.addWidget(self.combo_sentido_pue, 1)
        lay_pue.addLayout(f_sen)

        f_ag_pue = QtWidgets.QHBoxLayout()
        f_ag_pue.addWidget(QtWidgets.QLabel("Agarre:"))
        self.combo_agarre_pue = QtWidgets.QComboBox()
        self.combo_agarre_pue.addItems(["Tirador", "Perfil Gola", "Bisel 45°", "Push-to-open"])
        f_ag_pue.addWidget(self.combo_agarre_pue, 1)
        lay_pue.addLayout(f_ag_pue)

        self.lbl_puerta_hub = QtWidgets.QLabel("Bisagras Cazoleta 35mm Cierre Suave (Parche)")
        self.lbl_puerta_hub.setStyleSheet("color: #28a745; font-size: 10px;")
        lay_pue.addWidget(self.lbl_puerta_hub)

        btn_ap_pue = QtWidgets.QPushButton("🚪 Insertar Puerta")
        btn_ap_pue.setStyleSheet("background-color: #007acc; color: white; font-weight: bold; padding: 4px;")
        btn_ap_pue.clicked.connect(self._aplicar_puerta)
        lay_pue.addWidget(btn_ap_pue)
        self.stack_dock.addWidget(panel_puerta)

        # 3. Vacío
        panel_vacio = QtWidgets.QWidget()
        lay_vac = QtWidgets.QVBoxLayout(panel_vacio)
        lay_vac.setContentsMargins(6, 6, 6, 6)
        lbl_v = QtWidgets.QLabel("🔲 Vano libre de almacenamiento útil (sin insertos)")
        lbl_v.setStyleSheet("color: #888888; font-size: 10px;")
        lay_vac.addWidget(lbl_v)
        btn_ap_vac = QtWidgets.QPushButton("Restaurar Vacío")
        btn_ap_vac.setStyleSheet("background-color: #333333; color: #cccccc; padding: 4px;")
        btn_ap_vac.clicked.connect(self._aplicar_vacio)
        lay_vac.addWidget(btn_ap_vac)
        self.stack_dock.addWidget(panel_vacio)

        self.stack_dock.setCurrentIndex(3)  # Inicia en vacío
        self.contenedor_datos.addWidget(self.stack_dock)

    def _on_dock_clicked(self, habitante):
        for k, btn in self.btn_dock.items():
            btn.blockSignals(True)
            btn.setChecked(k == habitante)
            btn.blockSignals(False)

        idx = {"subdividir": 0, "cajon": 1, "puerta": 2, "vacio": 3}.get(habitante, 3)
        self.stack_dock.setCurrentIndex(idx)

        # Actualizar consulta de herraje reactiva
        if habitante == "puerta":
            h = HH.resolve_hinge("parche")
            if h:
                self.lbl_puerta_hub.setText(f"{h.get('nombre')} · ${h.get('precio_unitario', 0.0):.2f} {h.get('moneda', 'USD')}")
        elif habitante == "cajon":
            s = HH.resolve_drawer_slide("oculta", "blum_tandem")
            if s:
                self.lbl_cajon_hub.setText(f"{s.get('nombre')} · ${s.get('precio_unitario', 0.0):.2f} {s.get('moneda', 'USD')}")

        self.sigHabitanteCambiado.emit(habitante, self.get_habitante_config())

    def _aplicar_subdivision(self):
        cfg = self.get_habitante_config()
        self.lbl_subdiv.setText(f"{cfg['eje']} × {cfg['n_partes']}")
        self.sigHabitanteCambiado.emit("subdividir", cfg)

    def _aplicar_cajon(self):
        cfg = self.get_habitante_config()
        self.lbl_subdiv.setText(f"Cajón ({cfg['n_cajones']}x)")
        self.sigHabitanteCambiado.emit("cajon", cfg)

    def _aplicar_puerta(self):
        cfg = self.get_habitante_config()
        self.lbl_subdiv.setText(f"Puerta ({cfg['sistema']})")
        self.sigHabitanteCambiado.emit("puerta", cfg)

    def _aplicar_vacio(self):
        self.lbl_subdiv.setText("Libre")
        self.sigHabitanteCambiado.emit("vacio", {"tipo": "vacio"})

    def get_habitante_config(self):
        act = "vacio"
        for k, b in self.btn_dock.items():
            if b.isChecked():
                act = k
                break
        if act == "subdividir":
            return {
                "tipo": "subdividir",
                "eje": "X" if "Horizontal" in self.combo_eje.currentText() else "Y",
                "n_partes": self.spin_n_partes.value(),
                "modo": "equitativo" if "Equitativo" in self.combo_dist.currentText() else "fijo"
            }
        elif act == "cajon":
            return {
                "tipo": "cajon",
                "n_cajones": self.spin_cajones.value(),
                "corredera": self.combo_corredera.currentText(),
                "agarre": self.combo_agarre_caj.currentText()
            }
        elif act == "puerta":
            return {
                "tipo": "puerta",
                "sistema": self.combo_sistema_pue.currentText(),
                "sentido": self.combo_sentido_pue.currentText(),
                "agarre": self.combo_agarre_pue.currentText()
            }
        return {"tipo": "vacio"}

    def cargar_vano(self, obj):
        """Carga medidas de vano desde un objeto o diccionario."""
        self._obj_actual = obj
        w = _float_seguro(getattr(obj, "LuzLibreX", getattr(obj, "w", 564.0)), 564.0)
        h = _float_seguro(getattr(obj, "LuzLibreY", getattr(obj, "h", 280.0)), 280.0)
        d = _float_seguro(getattr(obj, "LuzLibreZ", getattr(obj, "d", 550.0)), 550.0)

        self._luz = {"w": w, "h": h, "d": d}
        self.lbl_luz_w.setText(f"{w:.1f} mm")
        self.lbl_luz_h.setText(f"{h:.1f} mm")
        self.lbl_luz_d.setText(f"{d:.1f} mm")
        self.lbl_luz_banner.setText(f"📐 <b>LUZ LIBRE NETA:</b> {w:.1f} × {h:.1f} × {d:.1f} mm")


# ----------------------------------------------------------------------
# PÁGINA 2: PIEZA L1 (PanelHeader + Cuadrado Figma)
# ----------------------------------------------------------------------
class PaginaPieza(_PaginaBase):
    """Nivel Pieza Física (PANEL): Header + Cuadrado Figma (VDOBoxController)."""

    def __init__(self, parent=None):
        super().__init__("Pieza / Tablero (Panel L1)", parent)
        self._obj_actual = None

        # --- PanelHeaderWidget incorporado ---
        self.header = QtWidgets.QGroupBox("PanelHeader")
        self.header.setObjectName("grpPanelHeader")
        self.header.setStyleSheet(
            "QGroupBox#grpPanelHeader { color: #e0e0e0; font-weight: bold; "
            "border: 1px solid #444444; border-radius: 6px; margin-top: 10px; }"
            "QGroupBox#grpPanelHeader::title { subcontrol-origin: margin; "
            "left: 10px; padding: 0 4px; color: #0098ff; }")
        h_layout = QtWidgets.QGridLayout(self.header)
        h_layout.setContentsMargins(10, 18, 10, 10)
        h_layout.setHorizontalSpacing(12)
        h_layout.setVerticalSpacing(4)

        self.lbl_largo = QtWidgets.QLabel("—")
        self.lbl_ancho = QtWidgets.QLabel("—")
        self.lbl_espesor = QtWidgets.QLabel("—")
        self.lbl_canto_norte = QtWidgets.QLabel("—")
        self.lbl_canto_sur = QtWidgets.QLabel("—")
        self.lbl_canto_este = QtWidgets.QLabel("—")
        self.lbl_canto_oeste = QtWidgets.QLabel("—")

        def _fila(r, clave, lbl_widget, label_txt):
            k = QtWidgets.QLabel(label_txt)
            k.setStyleSheet("color: #aaaaaa; font-size: 10px;")
            v = lbl_widget
            v.setStyleSheet("color: #e0e0e0; font-size: 11px; font-weight: bold;")
            h_layout.addWidget(k, r, 0)
            h_layout.addWidget(v, r, 1)

        _fila(0, "Largo", self.lbl_largo, "Largo (mm):")
        _fila(0, "Ancho", self.lbl_ancho, "Ancho (mm):")
        _fila(0, "Espesor", self.lbl_espesor, "Espesor (mm):")
        _fila(1, "CantoNorte", self.lbl_canto_norte, "Canto N:")
        _fila(1, "CantoSur", self.lbl_canto_sur, "Canto S:")
        _fila(2, "CantoEste", self.lbl_canto_este, "Canto E:")
        _fila(2, "CantoOeste", self.lbl_canto_oeste, "Canto O:")

        self.contenedor_datos.addWidget(self.header)

        # --- Cuadrado Figma (VDOBoxControllerWidget) ---
        self.box_controller = None
        if VDOBoxControllerWidget is not None:
            self.box_controller = VDOBoxControllerWidget()
            self.box_controller.sigConfigChanged.connect(self._on_box_changed)
            self.contenedor_datos.addWidget(self.box_controller)

    def cargar_panel(self, obj):
        self._obj_actual = obj
        largo = _float_seguro(getattr(obj, "Largo", None))
        ancho = _float_seguro(getattr(obj, "Ancho", None))
        espesor = _float_seguro(getattr(obj, "Espesor", None))

        self.lbl_largo.setText(f"{largo:.1f}" if largo else "—")
        self.lbl_ancho.setText(f"{ancho:.1f}" if ancho else "—")
        self.lbl_espesor.setText(f"{espesor:.1f}" if espesor else "—")

        canto_norte = _str_seguro(getattr(obj, "VDO_Canto_Norte", None), "FX")
        canto_sur = _str_seguro(getattr(obj, "VDO_Canto_Sur", None), "FX")
        canto_este = _str_seguro(getattr(obj, "VDO_Canto_Este", None), "FX")
        canto_oeste = _str_seguro(getattr(obj, "VDO_Canto_Oeste", None), "FX")
        self.lbl_canto_norte.setText(canto_norte)
        self.lbl_canto_sur.setText(canto_sur)
        self.lbl_canto_este.setText(canto_este)
        self.lbl_canto_oeste.setText(canto_oeste)

        if self.box_controller is not None:
            raw_cfg = getattr(obj, "VDO_Reengrose_JSON", None)
            if raw_cfg:
                try:
                    cfg = json.loads(raw_cfg) if isinstance(raw_cfg, str) else raw_cfg
                    self.box_controller.setConfig(cfg)
                    return
                except Exception:
                    pass

            self.box_controller.setConfig({
                "activo": True,
                "uniforme": True,
                "ancho_uniforme": 70.0,
                "distancia_uniforme": 0.0,
                "espesor": espesor if espesor else None,
                "bordes": {
                    b: {"activo": True, "ancho": 70.0, "offset_borde": 0.0}
                    for b in ("frente", "fondo", "izquierda", "derecha")
                },
            })

    def _on_box_changed(self, cfg):
        obj = self._obj_actual
        if obj is None:
            return
        try:
            if hasattr(obj, "VDO_Reengrose_JSON"):
                obj.VDO_Reengrose_JSON = json.dumps(cfg)
            elif hasattr(obj, "addProperty"):
                try:
                    obj.addProperty("App::PropertyString", "VDO_Reengrose_JSON", "VDO", "Regrueso JSON")
                    obj.VDO_Reengrose_JSON = json.dumps(cfg)
                except Exception:
                    pass
        except Exception:
            pass


# ----------------------------------------------------------------------
# PÁGINA 3: CIERRES Y HERRAJES (CAJON / PUERTA / ZOCALO / CAPA H)
# ----------------------------------------------------------------------
class PaginaCierre(_PaginaBase):
    """Nivel Cierre / Herraje (CAJON / PUERTA / ZOCALO): Capa H y Fresado CNC."""

    def __init__(self, parent=None):
        super().__init__("Cierre / Herraje (Capa H)", parent)
        self._obj_actual = None

        # Datos de fachada / caja
        self.lbl_tipo = self._add_dato("Tipo de cierre", "—")
        self.lbl_subtipo = self._add_dato("Subtipo", "—")
        self.lbl_sistema = self._add_dato("Sistema de apertura", "—")
        self.lbl_ancho_libre = self._add_dato("Ancho libre", "—")
        self.lbl_alto_frente = self._add_dato("Alto frente", "—")

        # -------------------------------------------------------------
        # Grupo de Herrajes y Fresado CNC (Capa H)
        # -------------------------------------------------------------
        self.grp_herraje = QtWidgets.QGroupBox("Herrajes y Fresado CNC (Capa H)")
        self.grp_herraje.setStyleSheet(
            "QGroupBox { color: #28a745; font-weight: bold; border: 1px solid #334d38; "
            "border-radius: 6px; margin-top: 8px; padding-top: 14px; }")
        lay_h = QtWidgets.QVBoxLayout(self.grp_herraje)
        lay_h.setContentsMargins(8, 8, 8, 8)
        lay_h.setSpacing(4)

        def _fila_h(etiqueta):
            f = QtWidgets.QHBoxLayout()
            k = QtWidgets.QLabel(etiqueta)
            k.setFixedWidth(110)
            k.setStyleSheet("color: #aaaaaa; font-size: 10px;")
            v = QtWidgets.QLabel("—")
            v.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: bold;")
            f.addWidget(k)
            f.addWidget(v, 1)
            lay_h.addLayout(f)
            return v

        self.lbl_sku = _fila_h("SKU Comercial:")
        self.lbl_proveedor = _fila_h("Proveedor:")
        self.lbl_precio = _fila_h("Precio Unitario:")
        self.lbl_fresado = _fila_h("Fresado CNC:")

        self.contenedor_datos.addWidget(self.grp_herraje)

    def cargar_cierre(self, obj, target_type):
        self._obj_actual = obj
        subtipo = _str_seguro(getattr(obj, "VDO_Subtipo", None))
        sistema = _str_seguro(getattr(obj, "SistemaApertura", None))
        ancho_libre = _float_seguro(getattr(obj, "AnchoLibre", None))
        alto_frente = _float_seguro(getattr(obj, "AltoFrente", None))

        self.lbl_tipo.setText(target_type)
        self.lbl_subtipo.setText(subtipo if subtipo else "—")
        self.lbl_sistema.setText(sistema if sistema else "—")
        self.lbl_ancho_libre.setText(f"{ancho_libre:.1f} mm" if ancho_libre else "—")
        self.lbl_alto_frente.setText(f"{alto_frente:.1f} mm" if alto_frente else "—")

        # Consulta a Capa H
        sku = _str_seguro(getattr(obj, "HardwareSKU", getattr(obj, "VDO_Herraje_Ref", None)))

        if target_type == "PUERTA":
            montaje = _str_seguro(getattr(obj, "TipoMontaje", "parche")).lower()
            h = HH.resolve_hinge(montaje, prefer_sku=sku if sku else None)
            if h:
                sku_txt = sku if sku else h.get("sku", "GEN-CAZ-35-PARCHE")
                self.lbl_sku.setText(sku_txt)
                self.lbl_proveedor.setText(h.get("proveedor", "Genérico"))
                self.lbl_precio.setText(f"${h.get('precio_unitario', 0.0):.2f} {h.get('moneda', 'USD')}")
                params = h.get("parametros_tecnicos", {})
                self.lbl_fresado.setText(
                    f"Cazoleta {params.get('diametro_cazoleta', 35):.0f}mm × {params.get('profundidad_cazoleta', 11.5):.1f}mm | K={params.get('cota_k_default', 4):.0f}mm")
                return

        elif target_type == "CAJON":
            marca = _str_seguro(getattr(obj, "MarcaCorredera", "blum_tandem")).lower()
            tipo_cor = _str_seguro(getattr(obj, "TipoCorredera", "oculta")).lower()
            s = HH.resolve_drawer_slide(tipo_cor, marca)
            if s:
                self.lbl_sku.setText(s.get("sku", "BLUM-TANDEM"))
                self.lbl_proveedor.setText(s.get("proveedor", "Blum"))
                self.lbl_precio.setText(f"${s.get('precio_unitario', 0.0):.2f} {s.get('moneda', 'USD')}")
                params = s.get("parametros_tecnicos", {})
                self.lbl_fresado.setText(
                    f"Delta: {params.get('delta_ancho', 49):.0f}mm | Pin: {params.get('diametro_pin_trasero', 6):.0f}mm | Ranura Z: {params.get('cota_ranura_z', 10):.0f}mm")
                return

        # Fallback genérico si no hay coincidencia
        self.lbl_sku.setText(sku if sku else "STD-VDO")
        self.lbl_proveedor.setText("Taller Estándar")
        self.lbl_precio.setText("—")
        self.lbl_fresado.setText("Perforaciones de ensamble estándar")


# ----------------------------------------------------------------------
# Widget Inspector Universal
# ----------------------------------------------------------------------
class VDOUniversalInspectorWidget(QtWidgets.QWidget):
    """
    Inspector universal lateral reactivo para el Sistema VDO.

    Conecta VDOSelectionBridge con un QStackedWidget que muestra la vista
    apropiada según el tipo de entidad seleccionada (COCO, VANO, PANEL,
    CAJON, PUERTA, ZOCALO o desconocido).
    """

    sigNivelCambiado = QtCore.Signal(int, str)  # (page_index, target_type)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("VDOUniversalInspector")
        self.setMinimumWidth(320)

        self._puente = None
        self._obj_actual = None
        self._tipo_actual = VDOSelectionBridge.TARGET_UNKNOWN

        self._construir_ui()
        self._inicializar_puente()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _construir_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 1. Breadcrumbs
        self.breadcrumbs = _BreadcrumbBar(self)
        root.addWidget(self.breadcrumbs)

        # Separador sutil
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setStyleSheet("color: #333333;")
        root.addWidget(sep)

        # 2. QStackedWidget con las 4 páginas
        self.stack = QtWidgets.QStackedWidget(self)

        self.pagina_chasis = PaginaChasis()
        self.pagina_vano = PaginaVano()
        self.pagina_pieza = PaginaPieza()
        self.pagina_cierre = PaginaCierre()

        self.stack.addWidget(self.pagina_chasis)   # 0
        self.stack.addWidget(self.pagina_vano)     # 1
        self.stack.addWidget(self.pagina_pieza)    # 2
        self.stack.addWidget(self.pagina_cierre)   # 3

        root.addWidget(self.stack)

        # Nivel por defecto: mueble general (chasis)
        self._ir_a_nivel(PAGE_CHASIS, VDOSelectionBridge.TARGET_UNKNOWN)

    def _ir_a_nivel(self, page_index, target_type):
        if self.stack is None:
            return
        self.stack.setCurrentIndex(page_index)
        self._tipo_actual = target_type

        # Actualizar breadcrumbs
        if target_type == VDOSelectionBridge.TARGET_COCO:
            self.breadcrumbs.set_ruta(
                [("Mueble", "mueble"), ("Chasis L2", "chasis")], activo="chasis")
        elif target_type in (getattr(VDOSelectionBridge, "TARGET_VANO", "VANO"), "VANO"):
            self.breadcrumbs.set_ruta(
                [("Mueble", "mueble"), ("Vano L0", "vano")], activo="vano")
        elif target_type == VDOSelectionBridge.TARGET_PANEL:
            self.breadcrumbs.set_ruta(
                [("Mueble", "mueble"), ("Pieza L1", "pieza")], activo="pieza")
        elif target_type in (
                VDOSelectionBridge.TARGET_CAJON,
                VDOSelectionBridge.TARGET_PUERTA,
                VDOSelectionBridge.TARGET_ZOCALO):
            self.breadcrumbs.set_ruta(
                [("Mueble", "mueble"), ("Cierre / Herraje", "cierre")], activo="cierre")
        else:
            self.breadcrumbs.set_ruta(
                [("Mueble", "mueble")], activo="mueble")

        self.sigNivelCambiado.emit(page_index, target_type)

    # ------------------------------------------------------------------
    # Puente de selección
    # ------------------------------------------------------------------
    def _inicializar_puente(self):
        self._puente = VDOSelectionBridge(
            on_target_changed=self._on_selection_changed)
        self._puente.attach()

    def _on_selection_changed(self, obj, target_type):
        """Reacción reactiva a un cambio de selección en FreeCAD."""
        try:
            self._obj_actual = obj
            self._tipo_actual = target_type

            if obj is None or target_type == VDOSelectionBridge.TARGET_UNKNOWN:
                self._ir_a_nivel(PAGE_CHASIS, VDOSelectionBridge.TARGET_UNKNOWN)
                return

            page = _TARGET_TO_PAGE.get(target_type, PAGE_CHASIS)

            if page == PAGE_CHASIS and target_type == VDOSelectionBridge.TARGET_COCO:
                self.pagina_chasis.cargar_coco(obj)
            elif page == PAGE_PIEZA and target_type == VDOSelectionBridge.TARGET_PANEL:
                self.pagina_pieza.cargar_panel(obj)
            elif page == PAGE_CIERRE:
                self.pagina_cierre.cargar_cierre(obj, target_type)
            elif page == PAGE_VANO:
                self.pagina_vano.cargar_vano(obj)
            else:
                self._ir_a_nivel(PAGE_CHASIS, VDOSelectionBridge.TARGET_UNKNOWN)
                return

            self._ir_a_nivel(page, target_type)

        except Exception:
            # Anti-crash: el inspector nunca debe romper la UI de FreeCAD.
            try:
                self._ir_a_nivel(PAGE_CHASIS, VDOSelectionBridge.TARGET_UNKNOWN)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # API pública y Ciclo de Vida
    # ------------------------------------------------------------------
    def pagina_actual(self):
        return self.stack.currentIndex() if self.stack is not None else -1

    def tipo_actual(self):
        return self._tipo_actual

    def objeto_actual(self):
        return self._obj_actual

    def puente(self):
        return self._puente

    def cerrar_inspector(self):
        """Limpieza: desregistra el observer de FreeCAD sin fugas."""
        try:
            if self._puente is not None:
                self._puente.detach()
                self._puente = None
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cerrar_inspector()

    def closeEvent(self, event):
        self.cerrar_inspector()
        super().closeEvent(event)

    @classmethod
    def mostrar_en_freecad(cls, parent=None):
        """Abre el inspector en FreeCAD GUI dentro de un TaskPanel o diálogo dockeable."""
        instancia = cls(parent=parent)
        if Gui is not None and hasattr(Gui, "Control"):
            try:
                Gui.Control.showDialog(instancia)
            except Exception:
                instancia.show()
        else:
            instancia.show()
        return instancia


__all__ = [
    "VDOUniversalInspectorWidget",
    "PAGE_CHASIS",
    "PAGE_VANO",
    "PAGE_PIEZA",
    "PAGE_CIERRE",
]
