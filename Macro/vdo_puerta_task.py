# -*- coding: utf-8 -*-
# =====================================================================
# vdo_puerta_task.py
# Capa 4 - Task Panel PySide para Puertas y Cierres (L2).
# Construido con VDOTransactionMixin y el Manifiesto de UI VDO.
# =====================================================================

from PySide import QtGui, QtCore

import FreeCAD as App

from vdo_qt import VDO_DoubleSpinBox
from vdo_task_base import VDOTransactionMixin, cerrar_dialogo
from vdo_module_props import add_common_props, ANCLAJES, ANCLAJE_LABELS

import vdo_hardware_hub as H
from vdo_puerta_despiece import (
    bisagras_para_puerta,
    descripcion_piston,
    calcular_corrediza,
    SISTEMAS_APERTURA,
    necesita_expulsor_magnetico,
    necesita_cantos_45,
    ajuste_altura_apertura,
    APERTURA_TIRADOR, APERTURA_GOLA, APERTURA_45_GRADOS, APERTURA_PUSH_OPEN,
    OPERACION_CANTO_ESTANDAR, OPERACION_CANTO_GOLA, OPERACION_CANTO_45,
    cantos_por_sistema_apertura,
)

FAMILIAS = ["Batiente Vertical", "Basculante Horizontal", "Corrediza"]
SENTIDOS_BATIENTE = ["Izquierda", "Derecha", "Doble"]
SENTIDOS_BASCULANTE = ["Hacia Arriba", "Hacia Abajo"]
SENTIDOS_CORREDIZA = ["2 hojas", "3 hojas"]

# ---------------------------------------------------------------------
# Mapeo de nombres de visualización (UI) a constantes del contrato.
# ---------------------------------------------------------------------
APERTURA_LABELS = {
    APERTURA_TIRADOR: "Tirador Tradicional",
    APERTURA_45_GRADOS: "Inglete 45 Grados",
    APERTURA_GOLA: "Perfil Gola",
    APERTURA_PUSH_OPEN: "Push to Open",
}
APERTURA_VALUES = {v: k for k, v in APERTURA_LABELS.items()}

# Colores del Manifiesto de UI VDO (tema oscuro)
COLOR_FONDO = "#1e1e1e"
COLOR_ACENTO = "#007acc"
COLOR_TEXTO = "#e0e0e0"
COLOR_BORDE = "#4a4a4a"


# ---------------------------------------------------------------------
# PanelHeaderWidget (encabezado universal de pieza física)
# ---------------------------------------------------------------------
class PanelHeaderWidget(QtGui.QGroupBox):
    """Cabecera obligatoria para toda pieza física del sistema VDO.

    Muestra: [ Identificador ] [ Largo × Ancho × Espesor mm ]
             [ Cantos: Norte, Sur, Este, Oeste ]
    """

    def __init__(self, parent=None):
        super().__init__("Cabecera de pieza", parent)
        self.setStyleSheet(
            f"QGroupBox {{ background: {COLOR_FONDO}; color: {COLOR_TEXTO}; "
            f"border: 1px solid {COLOR_BORDE}; border-radius: 4px; "
            f"margin-top: 8px; padding-top: 4px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 8px; }}")
        layout = QtGui.QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        self.lbl_id = QtGui.QLabel("Sin selección")
        self.lbl_id.setStyleSheet("font-weight: bold;")
        self.lbl_id.setWordWrap(True)
        layout.addWidget(self.lbl_id)

        self.lbl_dimensiones = QtGui.QLabel("—")
        self.lbl_dimensiones.setToolTip(
            "Dimensiones brutas de corte: Largo × Ancho × Espesor (mm).")
        layout.addWidget(self.lbl_dimensiones)

        self.lbl_cantos = QtGui.QLabel("")
        self.lbl_cantos.setWordWrap(True)
        self.lbl_cantos.setStyleSheet(
            f"QLabel {{ background: #2b2b2b; color: {COLOR_TEXTO}; "
            f"padding: 3px; border: 1px solid {COLOR_BORDE}; }}")
        layout.addWidget(self.lbl_cantos)

    def set_pieza(self, identificador, largo, ancho, espesor, cantos=None):
        self.lbl_id.setText(str(identificador or "Pieza"))
        self.lbl_dimensiones.setText(
            f"{float(largo):.1f} × {float(ancho):.1f} × "
            f"{float(espesor):.1f} mm")
        cantos = cantos or {}
        partes = []
        for borde in ("norte", "sur", "este", "oeste"):
            partes.append(f"{borde.title()}: {cantos.get(borde, 'FX')}")
        self.lbl_cantos.setText(" · ".join(partes))

    def clear(self):
        self.lbl_id.setText("Sin selección")
        self.lbl_dimensiones.setText("—")
        self.lbl_cantos.setText("")


# ---------------------------------------------------------------------
# Task Panel
# ---------------------------------------------------------------------
class PuertaTaskPanel(VDOTransactionMixin):
    """Panel de tareas para configurar una puerta VDO."""

    def __init__(self, obj=None, on_accept=None, on_cancel=None,
                 auto_transaction=True):
        self.obj = obj
        self._vdo_aceptado = False
        self._init_vdo_task(
            on_accept=on_accept,
            on_cancel=on_cancel,
            auto_transaction=auto_transaction,
            transaction_name="Editar puerta VDO",
        )
        self.form = self._crear_widget()
        if obj:
            add_common_props(obj)
            self._cargar_valores(obj)
        self._actualizar_visibilidad()

    # -----------------------------------------------------------------
    # Construcción del formulario
    # -----------------------------------------------------------------
    def _crear_widget(self):
        widget = QtGui.QWidget()
        widget.setStyleSheet(f"QWidget {{ background: {COLOR_FONDO}; "
                             f"color: {COLOR_TEXTO}; }}")
        main = QtGui.QVBoxLayout(widget)
        main.setContentsMargins(8, 8, 8, 8)
        main.setSpacing(8)

        # --- Cabecera universal de pieza (obligatoria por Manifiesto UI) ---
        self.header = PanelHeaderWidget()
        self.header.set_pieza("Puerta", 0, 0, 0)
        main.addWidget(self.header)

        # --- Familia ---
        grp_fam = QtGui.QGroupBox("Familia de puerta")
        grp_fam.setStyleSheet(
            f"QGroupBox {{ color: {COLOR_TEXTO}; border: 1px solid "
            f"{COLOR_BORDE}; border-radius: 4px; margin-top: 8px; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 8px; }}")
        grid_fam = QtGui.QGridLayout(grp_fam)
        grid_fam.addWidget(QtGui.QLabel("Tipo de sistema:"), 0, 0)
        self.combo_sistema = QtGui.QComboBox()
        self.combo_sistema.addItems(FAMILIAS)
        self.combo_sistema.setToolTip(
            "Batiente Vertical, Basculante Horizontal o Corrediza.")
        grid_fam.addWidget(self.combo_sistema, 0, 1)
        main.addWidget(grp_fam)

        # --- Montaje (solo batiente) ---
        self.grp_montaje = QtGui.QGroupBox("Montaje (batiente)")
        self.grp_montaje.setStyleSheet(grp_fam.styleSheet())
        grid_m = QtGui.QGridLayout(self.grp_montaje)
        grid_m.addWidget(QtGui.QLabel("Tipo de montaje:"), 0, 0)
        self.combo_montaje = QtGui.QComboBox()
        self.combo_montaje.addItems(["Parche", "Semiparche", "Embebida"])
        grid_m.addWidget(self.combo_montaje, 0, 1)
        grid_m.addWidget(QtGui.QLabel("Sentido de apertura:"), 1, 0)
        self.combo_sentido = QtGui.QComboBox()
        self.combo_sentido.addItems(SENTIDOS_BATIENTE)
        grid_m.addWidget(self.combo_sentido, 1, 1)
        main.addWidget(self.grp_montaje)

        # --- Dimensiones ---
        grp_dim = QtGui.QGroupBox("Dimensiones de la puerta (mm)")
        grp_dim.setStyleSheet(grp_fam.styleSheet())
        grid_d = QtGui.QGridLayout(grp_dim)

        grid_d.addWidget(QtGui.QLabel("Ancho (W):"), 0, 0)
        self.spin_ancho = VDO_DoubleSpinBox()
        self.spin_ancho.setRange(100, 3000)
        self.spin_ancho.setSuffix(" mm")
        self.spin_ancho.setDecimals(1)
        grid_d.addWidget(self.spin_ancho, 0, 1)

        grid_d.addWidget(QtGui.QLabel("Alto (H):"), 1, 0)
        self.spin_alto = VDO_DoubleSpinBox()
        self.spin_alto.setRange(100, 2600)
        self.spin_alto.setSuffix(" mm")
        self.spin_alto.setDecimals(1)
        grid_d.addWidget(self.spin_alto, 1, 1)

        grid_d.addWidget(QtGui.QLabel("Espesor (mm):"), 2, 0)
        self.spin_espesor = QtGui.QSpinBox()
        self.spin_espesor.setRange(10, 50)
        self.spin_espesor.setSuffix(" mm")
        self.spin_espesor.setValue(18)
        grid_d.addWidget(self.spin_espesor, 2, 1)

        main.addWidget(grp_dim)

        # --- Sistema de apertura ---
        grp_ape = QtGui.QGroupBox("Sistema de apertura / fachada")
        grp_ape.setStyleSheet(grp_fam.styleSheet())
        grid_a = QtGui.QGridLayout(grp_ape)
        grid_a.addWidget(QtGui.QLabel("Tipo:"), 0, 0)
        self.combo_apertura = QtGui.QComboBox()
        self.combo_apertura.addItems(
            [APERTURA_LABELS[k] for k in SISTEMAS_APERTURA])
        grid_a.addWidget(self.combo_apertura, 0, 1)
        main.addWidget(grp_ape)

        # --- Herraje comercial (dropdown poblado desde Capa H) ---
        self.grp_herraje = QtGui.QGroupBox("Herraje comercial")
        self.grp_herraje.setStyleSheet(grp_fam.styleSheet())
        grid_h = QtGui.QGridLayout(self.grp_herraje)
        grid_h.addWidget(QtGui.QLabel("SKU:"), 0, 0)
        self.combo_sku = QtGui.QComboBox()
        grid_h.addWidget(self.combo_sku, 0, 1)
        self.lbl_herraje_info = QtGui.QLabel("")
        self.lbl_herraje_info.setWordWrap(True)
        self.lbl_herraje_info.setStyleSheet(
            f"QLabel {{ background: #2b2b2b; color: {COLOR_TEXTO}; "
            f"padding: 4px; border: 1px solid {COLOR_BORDE}; }}")
        grid_h.addWidget(self.lbl_herraje_info, 1, 0, 1, 2)
        main.addWidget(self.grp_herraje)

        # --- Pistón a gas (solo basculante) ---
        self.grp_piston = QtGui.QGroupBox("Cálculo de pistón a gas")
        self.grp_piston.setStyleSheet(grp_fam.styleSheet())
        grid_p = QtGui.QGridLayout(self.grp_piston)
        self.lbl_piston = QtGui.QLabel("")
        self.lbl_piston.setWordWrap(True)
        self.lbl_piston.setStyleSheet(
            f"QLabel {{ background: #1e4a1e; color: #8fbc8f; padding: 6px; "
            f"border: 1px solid #3a7a3a; font-weight: bold; }}")
        grid_p.addWidget(self.lbl_piston, 0, 0, 1, 2)
        main.addWidget(self.grp_piston)

        # --- Expulsor magnético (solo push) ---
        self.chk_expulsor = QtGui.QCheckBox("Inyectar expulsor magnético al BOM")
        self.chk_expulsor.setStyleSheet(f"color: {COLOR_TEXTO};")
        main.addWidget(self.chk_expulsor)

        # --- Posición ---
        grp_pos = QtGui.QGroupBox("Posición (mm)")
        grp_pos.setStyleSheet(grp_fam.styleSheet())
        grid_p = QtGui.QGridLayout(grp_pos)
        grid_p.addWidget(QtGui.QLabel("Pos X:"), 0, 0)
        self.spin_pos_x = VDO_DoubleSpinBox()
        self.spin_pos_x.setRange(-5000, 5000)
        self.spin_pos_x.setSuffix(" mm")
        self.spin_pos_x.setDecimals(1)
        grid_p.addWidget(self.spin_pos_x, 0, 1)
        grid_p.addWidget(QtGui.QLabel("Pos Y:"), 1, 0)
        self.spin_pos_y = VDO_DoubleSpinBox()
        self.spin_pos_y.setRange(-5000, 5000)
        self.spin_pos_y.setSuffix(" mm")
        self.spin_pos_y.setDecimals(1)
        grid_p.addWidget(self.spin_pos_y, 1, 1)
        grid_p.addWidget(QtGui.QLabel("Pos Z:"), 2, 0)
        self.spin_pos_z = VDO_DoubleSpinBox()
        self.spin_pos_z.setRange(-5000, 5000)
        self.spin_pos_z.setSuffix(" mm")
        self.spin_pos_z.setDecimals(1)
        grid_p.addWidget(self.spin_pos_z, 2, 1)
        main.addWidget(grp_pos)

        # --- Anclaje ---
        grid_p.addWidget(QtGui.QLabel("Anclaje:"), 3, 0)
        self.combo_anclaje = QtGui.QComboBox()
        self.combo_anclaje.setStyleSheet(f"color: {COLOR_TEXTO};")
        for a in ANCLAJES:
            self.combo_anclaje.addItem(ANCLAJE_LABELS.get(a, a), a)
        grid_p.addWidget(self.combo_anclaje, 3, 1)

        main.addStretch()

        # Botones
        botones = QtGui.QDialogButtonBox()
        btn_ok = botones.addButton(
            "Aplicar" if self.auto_transaction else "Crear y colocar",
            QtGui.QDialogButtonBox.AcceptRole)
        btn_cancelar = botones.addButton(
            "Cancelar", QtGui.QDialogButtonBox.RejectRole)
        botones.accepted.connect(self._on_ok)
        botones.rejected.connect(self._on_cancel)
        main.addWidget(botones)

        # Señales de cambio
        self.combo_sistema.currentIndexChanged.connect(self._on_cambio_sistema)
        self.combo_apertura.currentIndexChanged.connect(self._actualizar_todo)
        self.combo_sku.currentIndexChanged.connect(self._actualizar_herraje_info)
        self.combo_montaje.currentIndexChanged.connect(self._actualizar_todo)
        self.combo_sentido.currentIndexChanged.connect(self._actualizar_todo)
        self.spin_ancho.valueChanged.connect(self._actualizar_todo)
        self.spin_alto.valueChanged.connect(self._actualizar_todo)
        self.spin_espesor.valueChanged.connect(self._actualizar_todo)

        return widget

    # -----------------------------------------------------------------
    # Carga / aplicación de valores
    # -----------------------------------------------------------------
    def _cargar_valores(self, obj):
        idx = self.combo_sistema.findText(obj.TipoSistema)
        if idx >= 0:
            self.combo_sistema.setCurrentIndex(idx)
        idx = self.combo_montaje.findText(obj.TipoMontaje)
        if idx >= 0:
            self.combo_montaje.setCurrentIndex(idx)
        idx = self.combo_sentido.findText(obj.SentidoApertura)
        if idx >= 0:
            self.combo_sentido.setCurrentIndex(idx)
        label = APERTURA_LABELS.get(obj.SistemaApertura, obj.SistemaApertura)
        idx = self.combo_apertura.findText(label)
        if idx >= 0:
            self.combo_apertura.setCurrentIndex(idx)
        idx = self.combo_sku.findText(obj.HardwareSKU)
        if idx >= 0:
            self.combo_sku.setCurrentIndex(idx)
        self.spin_ancho.setValue(float(obj.Ancho))
        self.spin_alto.setValue(float(obj.Alto))
        self.spin_espesor.setValue(int(obj.Espesor))
        self.spin_pos_x.setValue(float(obj.PosX))
        self.spin_pos_y.setValue(float(obj.PosY))
        self.spin_pos_z.setValue(float(obj.PosZ))
        anclaje = getattr(obj, "VDO_Anclaje", "inferior_izquierda_frente")
        for i in range(self.combo_anclaje.count()):
            if self.combo_anclaje.itemData(i) == anclaje:
                self.combo_anclaje.setCurrentIndex(i)
                break

    def _poblar_skus(self, familia):
        """Puebla el dropdown de SKUs desde la familia de Capa H."""
        self.combo_sku.blockSignals(True)
        self.combo_sku.clear()
        try:
            skus = sorted(H.query_family(familia).keys())
            if skus:
                self.combo_sku.addItems(skus)
        except KeyError:
            pass
        self.combo_sku.blockSignals(False)

    def _actualizar_visibilidad(self):
        sistema = self.combo_sistema.currentText()
        es_batiente = sistema == "Batiente Vertical"
        es_basculante = sistema == "Basculante Horizontal"
        es_corrediza = sistema == "Corrediza"

        self.grp_montaje.setVisible(es_batiente)
        self.grp_herraje.setVisible(es_batiente or es_corrediza)
        self.grp_piston.setVisible(es_basculante)

        # Sentido según familia
        self.combo_sentido.blockSignals(True)
        self.combo_sentido.clear()
        if es_batiente:
            self.combo_sentido.addItems(SENTIDOS_BATIENTE)
            self._poblar_skus("bisagra_cazoleta")
        elif es_basculante:
            self.combo_sentido.addItems(SENTIDOS_BASCULANTE)
            self.combo_sku.clear()
        else:
            self.combo_sentido.addItems(SENTIDOS_CORREDIZA)
            self._poblar_skus("sistema_corredizo")
        self.combo_sentido.blockSignals(False)

        self._actualizar_herraje_info()
        self._actualizar_piston()
        self._actualizar_header()

    def _on_cambio_sistema(self, idx):
        self._actualizar_visibilidad()
        self._actualizar_todo()

    def _actualizar_todo(self):
        self._actualizar_herraje_info()
        self._actualizar_piston()
        self._actualizar_header()

    def _actualizar_header(self):
        """Actualiza la cabecera universal de pieza con los datos actuales."""
        try:
            W = self.spin_ancho.value()
            H = self.spin_alto.value()
            t = self.spin_espesor.value()
            sistema = self.combo_sistema.currentText()
            apertura_label = self.combo_apertura.currentText()
            apertura = APERTURA_VALUES.get(apertura_label, apertura_label)

            # Usar el sistema de apertura para calcular la altura efectiva
            # y obtener los cantos para el header.
            H_efectiva, _desc = ajuste_altura_apertura(apertura, H)
            cantos = cantos_por_sistema_apertura(apertura)

            identificador = f"Puerta_{sistema.split()[0]}"
            if sistema == "Batiente Vertical":
                identificador += f"_{self.combo_montaje.currentText()}"
            self.header.set_pieza(identificador, W, H_efectiva, t, cantos)
        except Exception:
            self.header.clear()

    def _actualizar_herraje_info(self):
        sku = self.combo_sku.currentText()
        if not sku:
            self.lbl_herraje_info.setText("")
            return
        try:
            hw = H.get_hardware(sku)
            tecnicos = hw["parametros_tecnicos"]
            lineas = [
                f"{hw['nombre']}",
                f"Proveedor: {hw['proveedor']}  ·  Precio: "
                f"{hw['precio_unitario']} {hw['moneda']}",
            ]
            if "tipo_montaje" in tecnicos:
                lineas.append(f"Montaje: {tecnicos['tipo_montaje']}")
            if "diametro_cazoleta" in tecnicos:
                lineas.append(
                    f"Cazoleta: Ø{tecnicos['diametro_cazoleta']} mm × "
                    f"{tecnicos['profundidad_cazoleta']} mm profundo")
            if "descuento_altura_hoja" in tecnicos:
                lineas.append(
                    f"Descuento alto hoja: {tecnicos['descuento_altura_hoja']} mm  ·  "
                    f"Traslape: {tecnicos['traslape_minimo']} mm")
            self.lbl_herraje_info.setText(" · ".join(lineas))
        except KeyError:
            self.lbl_herraje_info.setText(f"SKU {sku} no encontrado en el catálogo.")

    def _actualizar_piston(self):
        if self.combo_sistema.currentText() != "Basculante Horizontal":
            self.lbl_piston.setText("")
            return
        try:
            W = self.spin_ancho.value()
            H = self.spin_alto.value()
            texto, comercial, F = descripcion_piston(W, H)
            self.lbl_piston.setText(
                f"💡 Recomendación: Pistón a Gas de {comercial}N  "
                f"(fuerza teórica: {F:.0f} N)")
        except Exception as e:
            self.lbl_piston.setText(f"Error calculando pistón: {e}")

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
        if not self.obj:
            return True
        try:
            self._vdo_begin()
            for spin in (self.spin_ancho, self.spin_alto,
                         self.spin_pos_x, self.spin_pos_y,
                         self.spin_pos_z):
                spin.interpretText()
            self.obj.TipoSistema = self.combo_sistema.currentText()
            self.obj.TipoMontaje = self.combo_montaje.currentText()
            self.obj.SentidoApertura = self.combo_sentido.currentText()
            label = self.combo_apertura.currentText()
            self.obj.SistemaApertura = APERTURA_VALUES.get(label, label)
            self.obj.HardwareSKU = self.combo_sku.currentText()
            self.obj.Ancho = self.spin_ancho.value()
            self.obj.Alto = self.spin_alto.value()
            self.obj.Espesor = self.spin_espesor.value()
            self.obj.PosX = self.spin_pos_x.value()
            self.obj.PosY = self.spin_pos_y.value()
            self.obj.PosZ = self.spin_pos_z.value()
            anclaje = self.combo_anclaje.currentData()
            if anclaje:
                self.obj.VDO_Anclaje = anclaje

            # Fuerza de pistón (solo lectura)
            if self.obj.TipoSistema == "Basculante Horizontal":
                texto, _, _ = descripcion_piston(self.obj.Ancho, self.obj.Alto)
                self.obj.FuerzaPistonRecomendada = texto
            else:
                self.obj.FuerzaPistonRecomendada = ""

            App.ActiveDocument.recompute()
            self._vdo_commit()
            self._vdo_aceptado = True
            self._vdo_call_accept()
            return True
        except Exception as e:
            self._vdo_abort()
            App.Console.PrintError(f"[VDO Puerta] Error aceptando: {e}\n")
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
