# -*- coding: utf-8 -*-
# =====================================================================
# vdo_cajon_task.py
# Task Panel PySide para el cajón con corredera oculta (Trinidad v2).
# =====================================================================

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui

from vdo_qt import VDO_DoubleSpinBox

from vdo_cajon_despiece import (
    listar_marcas,
    CORREDERA_TELESCOPICA, CORREDERA_OCULTA, CAJA_METALICA,
    APERTURA_TIRADOR, APERTURA_GOLA, APERTURA_45_GRADOS, APERTURA_PUSH_OPEN,
)
from vdo_facade_contract import (
    APERTURA_TIRADOR as FA_TIRADOR,
    APERTURA_GOLA as FA_GOLA,
    APERTURA_45_GRADOS as FA_45,
    APERTURA_PUSH_OPEN as FA_PUSH,
    OPERACION_CANTO_ESTANDAR, OPERACION_CANTO_GOLA, OPERACION_CANTO_45,
    MONTAJE_PARCHE, MONTAJE_SEMIPARCHE, MONTAJE_EMBEBIDA,
    cantos_por_sistema_apertura,
)
from vdo_hardware_hub import (
    resolve_drawer_slide, get_family,
    _FAMILIAS as _HW_FAMILIAS,  # para verificar disponibilidad
)
from vdo_task_base import VDOTransactionMixin, cerrar_dialogo
from vdo_module_props import (
    ANCLAJES, ANCLAJE_DEFAULT, ANCLAJE_LABELS,
    add_common_props, aplicar_rotacion,
)


# ---------------------------------------------------------------------
# PanelHeaderWidget: cabecera con cotas y cantos de la fachada
# ---------------------------------------------------------------------
class PanelHeaderWidget(QtWidgets.QGroupBox):
    """Cabecera informativa que muestra cotas y cantos de la fachada
    y las piezas del cajón seleccionado. Tema oscuro."""

    def __init__(self, parent=None):
        super().__init__("Fachada — Cotas y Cantos", parent)
        self.setStyleSheet(
            "QGroupBox { font-weight: bold; color: #e0e0e0; "
            "border: 1px solid #555555; border-radius: 6px; "
            "margin-top: 10px; padding-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; "
            "padding: 0 4px; }")

        self._layout = QtWidgets.QGridLayout(self)
        self._layout.setHorizontalSpacing(12)
        self._layout.setVerticalSpacing(4)

        self._labels = {}
        filas = [
            ("ancho_fachada", "Ancho fachada (mm):"),
            ("alto_fachada", "Alto fachada (mm):"),
            ("espesor_fachada", "Espesor (mm):"),
            ("sistema_apertura", "Sistema apertura:"),
            ("operacion_canto", "Operación canto sup.:"),
            ("canto_norte", "Canto Norte:"),
            ("canto_sur", "Canto Sur:"),
            ("canto_este", "Canto Este:"),
            ("canto_oeste", "Canto Oeste:"),
        ]
        for i, (clave, texto) in enumerate(filas):
            lbl_key = QtWidgets.QLabel(texto)
            lbl_key.setStyleSheet("color: #b0b0b0; font-size: 11px;")
            lbl_val = QtWidgets.QLabel("-")
            lbl_val.setStyleSheet("color: #e0e0e0; font-size: 11px;")
            lbl_val.setMinimumWidth(120)
            self._layout.addWidget(lbl_key, i, 0)
            self._layout.addWidget(lbl_val, i, 1)
            self._labels[clave] = lbl_val

    def actualizar(self, datos_fachada):
        """Actualiza los valores mostrados con los datos de la fachada."""
        if not datos_fachada:
            return
        self._labels["ancho_fachada"].setText(
            f"{float(datos_fachada.get('ancho', 0)):.1f}")
        self._labels["alto_fachada"].setText(
            f"{float(datos_fachada.get('alto', 0)):.1f}")
        self._labels["espesor_fachada"].setText(
            f"{float(datos_fachada.get('espesor', 0)):.1f}")
        self._labels["sistema_apertura"].setText(
            str(datos_fachada.get("sistema_apertura", "-")))
        self._labels["operacion_canto"].setText(
            str(datos_fachada.get("operacion_canto", "-")))
        cantos = datos_fachada.get("cantos", {})
        for lado in ("norte", "sur", "este", "oeste"):
            self._labels[f"canto_{lado}"].setText(
                str(cantos.get(lado, "-")))


# ---------------------------------------------------------------------
# CajonTaskPanel
# ---------------------------------------------------------------------
class CajonTaskPanel(VDOTransactionMixin):
    """Panel de tareas para editar un cajón con corredera (Trinidad v2)."""

    def __init__(self, obj=None, on_accept=None, on_cancel=None,
                 auto_transaction=True):
        self.obj = obj
        self._vdo_aceptado = False
        self._init_vdo_task(
            on_accept=on_accept,
            on_cancel=on_cancel,
            auto_transaction=auto_transaction,
            transaction_name="Editar cajón oculta",
        )
        self.form = self._crear_widget()
        if obj:
            add_common_props(obj)
            self._cargar_valores(obj)
        self._actualizar_header()

    # -----------------------------------------------------------------
    # Construcción del widget
    # -----------------------------------------------------------------
    def _crear_widget(self):
        widget = QtGui.QWidget()
        widget.setStyleSheet(
            "QWidget { background-color: #2b2b2b; color: #e0e0e0; }"
            "QGroupBox { font-weight: bold; color: #e0e0e0; "
            "border: 1px solid #555555; border-radius: 6px; "
            "margin-top: 10px; padding-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; "
            "padding: 0 4px; }"
            "QLabel { color: #e0e0e0; }"
            "QComboBox, QDoubleSpinBox, QSpinBox {"
            "  background-color: #3a3a3a; color: #e0e0e0;"
            "  border: 1px solid #555555; border-radius: 3px; padding: 3px;"
            "}"
            "QPushButton {"
            "  background-color: #3a3a3a; color: #e0e0e0;"
            "  border: 1px solid #555555; border-radius: 4px;"
            "  padding: 6px 14px; font-weight: bold;"
            "}"
            "QPushButton:hover { background-color: #444444; }")

        main_layout = QtGui.QVBoxLayout(widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # --- PanelHeaderWidget (cabecera) ---
        self.header = PanelHeaderWidget()
        main_layout.addWidget(self.header)

        # --- Grupo: Espacio interior del mueble ---
        grupo_espacio = QtGui.QGroupBox("Espacio interior (datos de partida)")
        grid_esp = QtGui.QGridLayout(grupo_espacio)

        grid_esp.addWidget(QtGui.QLabel("Ancho libre LI (mm):"), 0, 0)
        self.spin_li = VDO_DoubleSpinBox()
        self.spin_li.setRange(1, 3000)
        self.spin_li.setSuffix(" mm")
        self.spin_li.setDecimals(1)
        grid_esp.addWidget(self.spin_li, 0, 1)

        grid_esp.addWidget(QtGui.QLabel("Profundidad libre (mm):"), 1, 0)
        self.spin_prof = VDO_DoubleSpinBox()
        self.spin_prof.setRange(1, 1500)
        self.spin_prof.setSuffix(" mm")
        self.spin_prof.setDecimals(1)
        grid_esp.addWidget(self.spin_prof, 1, 1)

        grid_esp.addWidget(QtGui.QLabel("Ancho módulo (fachada):"), 2, 0)
        self.spin_ancho_mod = VDO_DoubleSpinBox()
        self.spin_ancho_mod.setRange(1, 3000)
        self.spin_ancho_mod.setSuffix(" mm")
        self.spin_ancho_mod.setDecimals(1)
        grid_esp.addWidget(self.spin_ancho_mod, 2, 1)

        grid_esp.addWidget(QtGui.QLabel("Alto frente (mm):"), 3, 0)
        self.spin_alto_frente = VDO_DoubleSpinBox()
        self.spin_alto_frente.setRange(1, 800)
        self.spin_alto_frente.setSuffix(" mm")
        self.spin_alto_frente.setDecimals(1)
        grid_esp.addWidget(self.spin_alto_frente, 3, 1)

        main_layout.addWidget(grupo_espacio)

        # --- Grupo: Corredera y herraje ---
        grupo_herraje = QtGui.QGroupBox("Corredera y herraje")
        grid_h = QtGui.QGridLayout(grupo_herraje)

        grid_h.addWidget(QtGui.QLabel("Tipo de corredera:"), 0, 0)
        self.combo_tipo = QtGui.QComboBox()
        self.combo_tipo.addItems([
            "Oculta (Blum Tandem / Genérica)",
            "Telescópica",
            "Metálica (Slim Box / Tandembox)",
        ])
        self.combo_tipo.setToolTip(
            "Oculta: corredera bajo cajón con notch y pin.\n"
            "Telescópica: guía lateral con piso delgado en ranura.\n"
            "Metálica: sin laterales de madera, solo piso y trasera.")
        grid_h.addWidget(self.combo_tipo, 0, 1)

        grid_h.addWidget(QtGui.QLabel("SKU comercial:"), 1, 0)
        self.combo_sku = QtGui.QComboBox()
        self.combo_sku.setEditable(True)
        self.combo_sku.setToolTip(
            "SKU de la corredera (vía vdo_hardware_hub.py).")
        grid_h.addWidget(self.combo_sku, 1, 1)

        grid_h.addWidget(QtGui.QLabel("Marca:"), 2, 0)
        self.combo_marca = QtGui.QComboBox()
        self.combo_marca.addItems(listar_marcas())
        self.combo_marca.setToolTip(
            "Marca de corredera oculta (delta y cotas).")
        grid_h.addWidget(self.combo_marca, 2, 1)

        grid_h.addWidget(QtGui.QLabel("Longitud guía (mm):"), 3, 0)
        self.spin_guia = VDO_DoubleSpinBox()
        self.spin_guia.setRange(0, 800)
        self.spin_guia.setSuffix(" mm")
        self.spin_guia.setDecimals(0)
        self.spin_guia.setSpecialValueText("Auto (según profundidad)")
        grid_h.addWidget(self.spin_guia, 3, 1)

        grid_h.addWidget(QtGui.QLabel("Montaje trasera:"), 4, 0)
        self.combo_montaje = QtGui.QComboBox()
        self.combo_montaje.addItems(["entre_laterales", "testa"])
        grid_h.addWidget(self.combo_montaje, 4, 1)

        self.combo_tipo.currentIndexChanged.connect(self._on_tipo_cambiado)
        self._on_tipo_cambiado(0)

        main_layout.addWidget(grupo_herraje)

        # --- Grupo: Sistema de apertura (fachada) ---
        grupo_apertura = QtGui.QGroupBox("Sistema de apertura (fachada)")
        grid_a = QtGui.QGridLayout(grupo_apertura)

        grid_a.addWidget(QtGui.QLabel("Sistema:"), 0, 0)
        self.combo_apertura = QtGui.QComboBox()
        self.combo_apertura.addItems([
            "Tirador",
            "Gola aluminio (−35 mm altura)",
            "45° (bisel en arista superior)",
            "Push open (expulsor magnético)",
        ])
        self.combo_apertura.setToolTip(
            "Tirador: manija postiza, altura completa.\n"
            "Gola: perfil C/L integrado, descuenta 35 mm en altura.\n"
            "45°: bisel paramétrico en arista superior frontal.\n"
            "Push open: émbolo magnético, holgura perimetral ajustada.")
        self.combo_apertura.currentIndexChanged.connect(
            self._on_apertura_cambiado)
        grid_a.addWidget(self.combo_apertura, 0, 1)

        grid_a.addWidget(QtGui.QLabel("Montaje fachada:"), 1, 0)
        self.combo_montaje_fachada = QtGui.QComboBox()
        self.combo_montaje_fachada.addItems(["Parche", "Semiparche", "Embebida"])
        self.combo_montaje_fachada.setToolTip(
            "Parche: solapa sobre los cantos del vano.\n"
            "Semiparche: comparte montante central.\n"
            "Embebida: a ras dentro del vano (deja cantos vistos).")
        grid_a.addWidget(self.combo_montaje_fachada, 1, 1)

        main_layout.addWidget(grupo_apertura)

        # --- Grupo: Caja y fachada ---
        grupo_caja = QtGui.QGroupBox("Caja y fachada")
        grid_caja = QtGui.QGridLayout(grupo_caja)

        grid_caja.addWidget(QtGui.QLabel("Alto caja (mm):"), 0, 0)
        self.spin_alto_caja = VDO_DoubleSpinBox()
        self.spin_alto_caja.setRange(1, 300)
        self.spin_alto_caja.setSuffix(" mm")
        self.spin_alto_caja.setDecimals(1)
        grid_caja.addWidget(self.spin_alto_caja, 0, 1)

        grid_caja.addWidget(QtGui.QLabel("Grosor caja (mm):"), 1, 0)
        self.spin_g_caja = QtGui.QSpinBox()
        self.spin_g_caja.setRange(1, 25)
        self.spin_g_caja.setSuffix(" mm")
        grid_caja.addWidget(self.spin_g_caja, 1, 1)

        grid_caja.addWidget(QtGui.QLabel("Grosor piso (mm):"), 2, 0)
        self.spin_g_fondo = QtGui.QSpinBox()
        self.spin_g_fondo.setRange(1, 12)
        self.spin_g_fondo.setSuffix(" mm")
        grid_caja.addWidget(self.spin_g_fondo, 2, 1)

        grid_caja.addWidget(QtGui.QLabel("Grosor fachada (mm):"), 3, 0)
        self.spin_g_fachada = QtGui.QSpinBox()
        self.spin_g_fachada.setRange(1, 30)
        self.spin_g_fachada.setSuffix(" mm")
        grid_caja.addWidget(self.spin_g_fachada, 3, 1)

        main_layout.addWidget(grupo_caja)

        # --- Grupo: Colocación ---
        grupo_coloc = QtGui.QGroupBox("Colocación")
        grid_coloc = QtGui.QGridLayout(grupo_coloc)

        grid_coloc.addWidget(QtGui.QLabel("Rotación Z:"), 0, 0)
        self.spin_rotacion = VDO_DoubleSpinBox()
        self.spin_rotacion.setRange(-360.0, 360.0)
        self.spin_rotacion.setDecimals(1)
        self.spin_rotacion.setSuffix(" °")
        self.spin_rotacion.setWrapping(True)
        grid_coloc.addWidget(self.spin_rotacion, 0, 1)

        grid_coloc.addWidget(QtGui.QLabel("Anclaje:"), 1, 0)
        self.combo_anclaje = QtGui.QComboBox()
        for anclaje in ANCLAJES:
            self.combo_anclaje.addItem(
                ANCLAJE_LABELS.get(anclaje, anclaje), anclaje)
        grid_coloc.addWidget(self.combo_anclaje, 1, 1)

        main_layout.addWidget(grupo_coloc)
        main_layout.addStretch()

        # --- Botones ---
        botones = QtGui.QDialogButtonBox()
        btn_ok = botones.addButton(
            "Crear y colocar" if not self.auto_transaction else "Aplicar",
            QtGui.QDialogButtonBox.AcceptRole)
        btn_cancelar = botones.addButton(
            "Cancelar", QtGui.QDialogButtonBox.RejectRole)
        botones.accepted.connect(self._on_ok)
        botones.rejected.connect(self._on_cancel)
        main_layout.addWidget(botones)

        return widget

    # -----------------------------------------------------------------
    # Selectores contextuales
    # -----------------------------------------------------------------
    def _on_tipo_cambiado(self, idx):
        """Actualiza el combo SKU según el tipo de corredera."""
        self.combo_sku.clear()
        tipo_map = {
            0: CORREDERA_OCULTA,
            1: CORREDERA_TELESCOPICA,
            2: CAJA_METALICA,
        }
        tipo = tipo_map.get(idx, CORREDERA_OCULTA)
        familia = "corredera_oculta" if tipo == CORREDERA_OCULTA else (
            "corredera_telescopica" if tipo == CORREDERA_TELESCOPICA else None)

        try:
            skus = get_family(familia) if familia else {}
        except Exception:
            skus = {}

        for sku in sorted(skus.keys()):
            datos = skus[sku]
            label = f"{sku} — {datos.get('nombre', '')}"
            self.combo_sku.addItem(label, sku)

        # Si no hay SKUs en el catálogo, añadir opciones manuales
        if self.combo_sku.count() == 0:
            if tipo == CORREDERA_OCULTA:
                self.combo_sku.addItem("BLUM-TANDEM — Blum Tandem", "blum_tandem")
                self.combo_sku.addItem("GEN-OCULTA — Genérica", "generica")
                self.combo_sku.addItem("HAFELE-OCULTA — Hafele", "hafele")
                self.combo_sku.addItem("DUCASSE-OCULTA — Ducasse", "ducasse")
            elif tipo == CORREDERA_TELESCOPICA:
                self.combo_sku.addItem(
                    "GEN-TELESCOPICA-45KG — Telescópica 45kg",
                    "GEN-TELESCOPICA-45KG")

    def _on_apertura_cambiado(self, idx):
        """Actualiza el header cuando cambia el sistema de apertura."""
        self._actualizar_header()

    # -----------------------------------------------------------------
    # Carga de valores
    # -----------------------------------------------------------------
    def _cargar_valores(self, obj):
        """Carga las propiedades del objeto en los controles."""
        if hasattr(obj, "AnchoLibre"):
            self.spin_li.setValue(float(obj.AnchoLibre))
        if hasattr(obj, "ProfLibre"):
            self.spin_prof.setValue(float(obj.ProfLibre))
        if hasattr(obj, "AnchoModulo"):
            self.spin_ancho_mod.setValue(float(obj.AnchoModulo))
        if hasattr(obj, "AltoFrente"):
            self.spin_alto_frente.setValue(float(obj.AltoFrente))
        if hasattr(obj, "AltoCaja"):
            self.spin_alto_caja.setValue(float(obj.AltoCaja))
        if hasattr(obj, "GrosorCaja"):
            self.spin_g_caja.setValue(int(round(float(obj.GrosorCaja))))
        if hasattr(obj, "GrosorFondo"):
            self.spin_g_fondo.setValue(int(round(float(obj.GrosorFondo))))
        if hasattr(obj, "GrosorFachada"):
            self.spin_g_fachada.setValue(int(round(float(obj.GrosorFachada))))
        if hasattr(obj, "MarcaCorredera"):
            idx = self.combo_marca.findText(obj.MarcaCorredera)
            if idx >= 0:
                self.combo_marca.setCurrentIndex(idx)
        if hasattr(obj, "LongitudGuia"):
            self.spin_guia.setValue(float(obj.LongitudGuia))
        if hasattr(obj, "MontajeTrasera"):
            idx = self.combo_montaje.findText(obj.MontajeTrasera)
            if idx >= 0:
                self.combo_montaje.setCurrentIndex(idx)
        if hasattr(obj, "TipoCorredera"):
            tipo_map_rev = {
                CORREDERA_OCULTA: 0,
                CORREDERA_TELESCOPICA: 1,
                CAJA_METALICA: 2,
            }
            idx = tipo_map_rev.get(obj.TipoCorredera, 0)
            self.combo_tipo.setCurrentIndex(idx)
        if hasattr(obj, "SistemaApertura"):
            apertura_map_rev = {
                APERTURA_TIRADOR: 0,
                APERTURA_GOLA: 1,
                APERTURA_45_GRADOS: 2,
                APERTURA_PUSH_OPEN: 3,
            }
            idx = apertura_map_rev.get(obj.SistemaApertura, 0)
            self.combo_apertura.setCurrentIndex(idx)
        if hasattr(obj, "TipoMontaje"):
            idx = self.combo_montaje_fachada.findText(obj.TipoMontaje)
            if idx >= 0:
                self.combo_montaje_fachada.setCurrentIndex(idx)
        if hasattr(obj, "VDO_Herraje_Ref"):
            sku = obj.VDO_Herraje_Ref
            sku_idx = self.combo_sku.findData(sku)
            if sku_idx >= 0:
                self.combo_sku.setCurrentIndex(sku_idx)

        self.spin_rotacion.setValue(
            float(getattr(obj, "VDO_RotacionZ", 0.0)))
        anclaje = getattr(obj, "VDO_Anclaje", ANCLAJE_DEFAULT)
        for i in range(self.combo_anclaje.count()):
            if self.combo_anclaje.itemData(i) == anclaje:
                self.combo_anclaje.setCurrentIndex(i)
                break

    def _actualizar_header(self):
        """Actualiza el PanelHeaderWidget con las cotas calculadas."""
        try:
            from vdo_cajon_despiece import calcular_despiece
            config = {
                "ancho_libre": self.spin_li.value(),
                "prof_libre": self.spin_prof.value(),
                "ancho_modulo": self.spin_ancho_mod.value(),
                "alto_frente": self.spin_alto_frente.value(),
                "marca": self.combo_marca.currentText(),
                "alto_caja": self.spin_alto_caja.value(),
                "grosor_caja": self.spin_g_caja.value(),
                "grosor_fondo": self.spin_g_fondo.value(),
                "grosor_fachada": self.spin_g_fachada.value(),
                "longitud_guia": self.spin_guia.value(),
                "montaje_trasera": self.combo_montaje.currentText(),
                "tipo_corredera": (
                    CORREDERA_OCULTA if self.combo_tipo.currentIndex() == 0
                    else CORREDERA_TELESCOPICA if self.combo_tipo.currentIndex() == 1
                    else CAJA_METALICA),
                "sistema_apertura": (
                    APERTURA_TIRADOR if self.combo_apertura.currentIndex() == 0
                    else APERTURA_GOLA if self.combo_apertura.currentIndex() == 1
                    else APERTURA_45_GRADOS if self.combo_apertura.currentIndex() == 2
                    else APERTURA_PUSH_OPEN),
                "tipo_montaje_fachada": self.combo_montaje_fachada.currentText(),
                "penetracion_ranura": 10.0,
                "eje_ranura": 11.5,
                "holgura_lateral_fachada": 2.0,
                "holgura_superior_fachada": 2.0,
                "holgura_inferior_fachada": 2.0,
                "material_ref": "melamina_standar",
            }
            d = calcular_despiece(config)
            self.header.actualizar(d.get("fachada", {}))
        except Exception:
            pass

    # -----------------------------------------------------------------
    # Aceptar / Cancelar
    # -----------------------------------------------------------------
    def _on_ok(self):
        if self.accept():
            cerrar_dialogo()

    def _on_cancel(self):
        self.reject()
        cerrar_dialogo()

    def accept(self):
        """Aplicar cambios y cerrar el panel."""
        if not self.obj:
            return True
        try:
            self._vdo_begin()
            for spin in (self.spin_li, self.spin_prof,
                         self.spin_ancho_mod, self.spin_alto_frente,
                         self.spin_alto_caja, self.spin_g_caja,
                         self.spin_g_fondo, self.spin_g_fachada,
                         self.spin_guia, self.spin_rotacion):
                spin.interpretText()
            self.obj.AnchoLibre = self.spin_li.value()
            self.obj.ProfLibre = self.spin_prof.value()
            self.obj.AnchoModulo = self.spin_ancho_mod.value()
            self.obj.AltoFrente = self.spin_alto_frente.value()
            self.obj.AltoCaja = self.spin_alto_caja.value()
            self.obj.GrosorCaja = self.spin_g_caja.value()
            self.obj.GrosorFondo = self.spin_g_fondo.value()
            self.obj.GrosorFachada = self.spin_g_fachada.value()
            self.obj.MarcaCorredera = self.combo_marca.currentText()
            self.obj.LongitudGuia = self.spin_guia.value()
            self.obj.MontajeTrasera = self.combo_montaje.currentText()
            self.obj.TipoCorredera = (
                CORREDERA_OCULTA if self.combo_tipo.currentIndex() == 0
                else CORREDERA_TELESCOPICA if self.combo_tipo.currentIndex() == 1
                else CAJA_METALICA)
            self.obj.SistemaApertura = (
                APERTURA_TIRADOR if self.combo_apertura.currentIndex() == 0
                else APERTURA_GOLA if self.combo_apertura.currentIndex() == 1
                else APERTURA_45_GRADOS if self.combo_apertura.currentIndex() == 2
                else APERTURA_PUSH_OPEN)
            self.obj.TipoMontaje = self.combo_montaje_fachada.currentText()
            sku_data = self.combo_sku.currentData()
            if sku_data:
                self.obj.VDO_Herraje_Ref = str(sku_data)
            else:
                self.obj.VDO_Herraje_Ref = self.combo_marca.currentText()
            anclaje = self.combo_anclaje.currentData()
            if anclaje:
                self.obj.VDO_Anclaje = anclaje
            aplicar_rotacion(self.obj, self.spin_rotacion.value())
            App.ActiveDocument.recompute()
            self._vdo_commit()
            self._vdo_aceptado = True
            self._vdo_call_accept()
            return True
        except Exception as e:
            self._vdo_abort()
            App.Console.PrintError(f"[VDO] Error aceptando cambios: {e}\n")
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
