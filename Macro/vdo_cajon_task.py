# -*- coding: utf-8 -*-
# =====================================================================
# vdo_cajon_task.py
# Task Panel PySide para el cajón con corredera oculta
# =====================================================================

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui

from vdo_qt import VDO_DoubleSpinBox

from vdo_cajon_despiece import listar_marcas
from vdo_task_base import VDOTransactionMixin, cerrar_dialogo
from vdo_module_props import (
    ANCLAJES, ANCLAJE_DEFAULT, ANCLAJE_LABELS,
    add_common_props, aplicar_rotacion
)


class CajonTaskPanel(VDOTransactionMixin):
    """Panel de tareas para editar un cajón con corredera oculta."""

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

    def _crear_widget(self):
        widget = QtGui.QWidget()
        main_layout = QtGui.QVBoxLayout(widget)

        # --- Grupo: Espacio interior del mueble ---
        grupo_espacio = QtGui.QGroupBox("Espacio interior (datos de partida)")
        grid_esp = QtGui.QGridLayout(grupo_espacio)

        grid_esp.addWidget(QtGui.QLabel("Ancho libre LI (mm):"), 0, 0)
        self.spin_li = VDO_DoubleSpinBox()
        self.spin_li.setRange(1, 3000)
        self.spin_li.setSuffix(" mm")
        self.spin_li.setDecimals(1)
        self.spin_li.setToolTip(
            "Luz interior entre laterales del mueble. Es el ancho "
            "disponible para la caja del cajón.")
        grid_esp.addWidget(self.spin_li, 0, 1)

        grid_esp.addWidget(QtGui.QLabel("Profundidad libre (mm):"), 1, 0)
        self.spin_prof = VDO_DoubleSpinBox()
        self.spin_prof.setRange(1, 1500)
        self.spin_prof.setSuffix(" mm")
        self.spin_prof.setDecimals(1)
        self.spin_prof.setToolTip(
            "Profundidad libre interior para la corredera.")
        grid_esp.addWidget(self.spin_prof, 1, 1)

        grid_esp.addWidget(QtGui.QLabel("Ancho módulo (fachada):"), 2, 0)
        self.spin_ancho_mod = VDO_DoubleSpinBox()
        self.spin_ancho_mod.setRange(1, 3000)
        self.spin_ancho_mod.setSuffix(" mm")
        self.spin_ancho_mod.setDecimals(1)
        self.spin_ancho_mod.setToolTip(
            "Ancho exterior del módulo; define el ancho de la fachada.")
        grid_esp.addWidget(self.spin_ancho_mod, 2, 1)

        grid_esp.addWidget(QtGui.QLabel("Alto fachada (mm):"), 3, 0)
        self.spin_alto_frente = VDO_DoubleSpinBox()
        self.spin_alto_frente.setRange(1, 800)
        self.spin_alto_frente.setSuffix(" mm")
        self.spin_alto_frente.setDecimals(1)
        self.spin_alto_frente.setToolTip(
            "Alto de la fachada del cajón.")
        grid_esp.addWidget(self.spin_alto_frente, 3, 1)

        main_layout.addWidget(grupo_espacio)

        # --- Grupo: Caja y fachada ---
        grupo_caja = QtGui.QGroupBox("Caja y fachada")
        grid_caja = QtGui.QGridLayout(grupo_caja)

        grid_caja.addWidget(QtGui.QLabel("Alto caja (mm):"), 0, 0)
        self.spin_alto_caja = VDO_DoubleSpinBox()
        self.spin_alto_caja.setRange(1, 300)
        self.spin_alto_caja.setSuffix(" mm")
        self.spin_alto_caja.setDecimals(1)
        self.spin_alto_caja.setToolTip(
            "Alto de los laterales de la caja del cajón.")
        grid_caja.addWidget(self.spin_alto_caja, 0, 1)

        grid_caja.addWidget(QtGui.QLabel("Grosor caja (mm):"), 1, 0)
        self.spin_g_caja = QtGui.QSpinBox()
        self.spin_g_caja.setRange(1, 25)
        self.spin_g_caja.setSuffix(" mm")
        self.spin_g_caja.setToolTip(
            "Espesor del tablero de la caja del cajón.")
        grid_caja.addWidget(self.spin_g_caja, 1, 1)

        grid_caja.addWidget(QtGui.QLabel("Grosor piso (mm):"), 2, 0)
        self.spin_g_fondo = QtGui.QSpinBox()
        self.spin_g_fondo.setRange(1, 12)
        self.spin_g_fondo.setSuffix(" mm")
        self.spin_g_fondo.setToolTip(
            "Espesor del fondo de la caja del cajón.")
        grid_caja.addWidget(self.spin_g_fondo, 2, 1)

        grid_caja.addWidget(QtGui.QLabel("Grosor fachada (mm):"), 3, 0)
        self.spin_g_fachada = QtGui.QSpinBox()
        self.spin_g_fachada.setRange(1, 30)
        self.spin_g_fachada.setSuffix(" mm")
        self.spin_g_fachada.setToolTip(
            "Espesor de la fachada; suele ser 18 mm.")
        grid_caja.addWidget(self.spin_g_fachada, 3, 1)

        main_layout.addWidget(grupo_caja)

        # --- Grupo: Corredera oculta ---
        grupo_herraje = QtGui.QGroupBox("Corredera oculta")
        grid_h = QtGui.QGridLayout(grupo_herraje)

        grid_h.addWidget(QtGui.QLabel("Marca:"), 0, 0)
        self.combo_marca = QtGui.QComboBox()
        self.combo_marca.addItems(listar_marcas())
        self.combo_marca.setToolTip(
            "Marca y modelo de corredera oculta. Ajusta el descuento de "
            "profundidad y los herrajes.")
        grid_h.addWidget(self.combo_marca, 0, 1)

        grid_h.addWidget(QtGui.QLabel("Longitud guía (mm):"), 1, 0)
        self.spin_guia = VDO_DoubleSpinBox()
        self.spin_guia.setRange(0, 800)
        self.spin_guia.setSuffix(" mm")
        self.spin_guia.setDecimals(0)
        self.spin_guia.setSpecialValueText("Auto (según profundidad)")
        self.spin_guia.setToolTip(
            "Longitud de guía. En Auto se calcula según la profundidad "
            "libre.")
        grid_h.addWidget(self.spin_guia, 1, 1)

        grid_h.addWidget(QtGui.QLabel("Montaje trasera:"), 2, 0)
        self.combo_montaje = QtGui.QComboBox()
        self.combo_montaje.addItems(["entre_laterales", "testa"])
        self.combo_montaje.setToolTip(
            "Entre laterales: la caja entra en la luz interior. "
            "Testa: el frente de la caja queda a tope con el lateral.")
        grid_h.addWidget(self.combo_montaje, 2, 1)

        main_layout.addWidget(grupo_herraje)

        # --- Grupo: Colocación ---
        grupo_coloc = QtGui.QGroupBox("Colocación")
        grid_coloc = QtGui.QGridLayout(grupo_coloc)

        grid_coloc.addWidget(QtGui.QLabel("Rotación Z:"), 0, 0)
        self.spin_rotacion = VDO_DoubleSpinBox()
        self.spin_rotacion.setRange(-360.0, 360.0)
        self.spin_rotacion.setDecimals(1)
        self.spin_rotacion.setSuffix(" °")
        self.spin_rotacion.setWrapping(True)
        self.spin_rotacion.setToolTip(
            "Rotación de colocación alrededor de Z. No cambia la geometría "
            "del cajón.")
        grid_coloc.addWidget(self.spin_rotacion, 0, 1)

        grid_coloc.addWidget(QtGui.QLabel("Anclaje:"), 1, 0)
        self.combo_anclaje = QtGui.QComboBox()
        for anclaje in ANCLAJES:
            self.combo_anclaje.addItem(
                ANCLAJE_LABELS.get(anclaje, anclaje), anclaje)
        self.combo_anclaje.setToolTip(
            "Esquina del cajón que se apoya en el punto de colocación.")
        grid_coloc.addWidget(self.combo_anclaje, 1, 1)

        main_layout.addWidget(grupo_coloc)
        main_layout.addStretch()

        botones = QtGui.QDialogButtonBox()
        btn_ok = botones.addButton(
            "Crear y colocar" if not self.auto_transaction else "Aplicar",
            QtGui.QDialogButtonBox.AcceptRole)
        btn_cancelar = botones.addButton(
            "Cancelar", QtGui.QDialogButtonBox.RejectRole)
        botones.accepted.connect(self._on_ok)
        botones.rejected.connect(self._on_cancel)
        btn_ok.setToolTip(
            "Guarda los cambios del cajón y recalcula la geometría.")
        btn_cancelar.setToolTip("Cierra sin aplicar los cambios.")
        main_layout.addWidget(botones)

        return widget

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
        self.spin_rotacion.setValue(
            float(getattr(obj, "VDO_RotacionZ", 0.0)))
        anclaje = getattr(obj, "VDO_Anclaje", ANCLAJE_DEFAULT)
        for i in range(self.combo_anclaje.count()):
            if self.combo_anclaje.itemData(i) == anclaje:
                self.combo_anclaje.setCurrentIndex(i)
                break

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
        """Cancelar y cerrar el panel."""
        self._vdo_abort()
        self._vdo_call_cancel()
        return True

    def clicked(self, button):
        pass

    def getStandardButtons(self):
        return QtGui.QDialogButtonBox.Ok | QtGui.QDialogButtonBox.Cancel

    def helpRequested(self):
        pass
