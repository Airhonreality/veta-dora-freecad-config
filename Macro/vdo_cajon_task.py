# -*- coding: utf-8 -*-
# =====================================================================
# vdo_cajon_task.py
# Task Panel PySide para el cajón con corredera oculta
# =====================================================================

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui

from vdo_cajon_despiece import listar_marcas


class CajonTaskPanel:
    """Panel de tareas para editar un cajón con corredera oculta."""

    def __init__(self, obj=None):
        self.obj = obj
        self.form = self._crear_widget()
        if obj:
            self._cargar_valores(obj)

    def _crear_widget(self):
        widget = QtGui.QWidget()
        main_layout = QtGui.QVBoxLayout(widget)

        # --- Grupo: Espacio interior del mueble ---
        grupo_espacio = QtGui.QGroupBox("Espacio interior (datos de partida)")
        grid_esp = QtGui.QGridLayout(grupo_espacio)

        grid_esp.addWidget(QtGui.QLabel("Ancho libre LI (mm):"), 0, 0)
        self.spin_li = QtGui.QDoubleSpinBox()
        self.spin_li.setRange(100, 3000)
        self.spin_li.setSuffix(" mm")
        self.spin_li.setDecimals(1)
        grid_esp.addWidget(self.spin_li, 0, 1)

        grid_esp.addWidget(QtGui.QLabel("Profundidad libre (mm):"), 1, 0)
        self.spin_prof = QtGui.QDoubleSpinBox()
        self.spin_prof.setRange(100, 1500)
        self.spin_prof.setSuffix(" mm")
        self.spin_prof.setDecimals(1)
        grid_esp.addWidget(self.spin_prof, 1, 1)

        grid_esp.addWidget(QtGui.QLabel("Ancho módulo (fachada):"), 2, 0)
        self.spin_ancho_mod = QtGui.QDoubleSpinBox()
        self.spin_ancho_mod.setRange(100, 3000)
        self.spin_ancho_mod.setSuffix(" mm")
        self.spin_ancho_mod.setDecimals(1)
        grid_esp.addWidget(self.spin_ancho_mod, 2, 1)

        grid_esp.addWidget(QtGui.QLabel("Alto fachada (mm):"), 3, 0)
        self.spin_alto_frente = QtGui.QDoubleSpinBox()
        self.spin_alto_frente.setRange(40, 800)
        self.spin_alto_frente.setSuffix(" mm")
        self.spin_alto_frente.setDecimals(1)
        grid_esp.addWidget(self.spin_alto_frente, 3, 1)

        main_layout.addWidget(grupo_espacio)

        # --- Grupo: Caja y fachada ---
        grupo_caja = QtGui.QGroupBox("Caja y fachada")
        grid_caja = QtGui.QGridLayout(grupo_caja)

        grid_caja.addWidget(QtGui.QLabel("Alto caja (mm):"), 0, 0)
        self.spin_alto_caja = QtGui.QDoubleSpinBox()
        self.spin_alto_caja.setRange(60, 300)
        self.spin_alto_caja.setSuffix(" mm")
        self.spin_alto_caja.setDecimals(1)
        grid_caja.addWidget(self.spin_alto_caja, 0, 1)

        grid_caja.addWidget(QtGui.QLabel("Grosor caja (mm):"), 1, 0)
        self.spin_g_caja = QtGui.QSpinBox()
        self.spin_g_caja.setRange(12, 25)
        self.spin_g_caja.setSuffix(" mm")
        grid_caja.addWidget(self.spin_g_caja, 1, 1)

        grid_caja.addWidget(QtGui.QLabel("Grosor piso (mm):"), 2, 0)
        self.spin_g_fondo = QtGui.QSpinBox()
        self.spin_g_fondo.setRange(4, 12)
        self.spin_g_fondo.setSuffix(" mm")
        grid_caja.addWidget(self.spin_g_fondo, 2, 1)

        grid_caja.addWidget(QtGui.QLabel("Grosor fachada (mm):"), 3, 0)
        self.spin_g_fachada = QtGui.QSpinBox()
        self.spin_g_fachada.setRange(10, 30)
        self.spin_g_fachada.setSuffix(" mm")
        grid_caja.addWidget(self.spin_g_fachada, 3, 1)

        main_layout.addWidget(grupo_caja)

        # --- Grupo: Corredera oculta ---
        grupo_herraje = QtGui.QGroupBox("Corredera oculta")
        grid_h = QtGui.QGridLayout(grupo_herraje)

        grid_h.addWidget(QtGui.QLabel("Marca:"), 0, 0)
        self.combo_marca = QtGui.QComboBox()
        self.combo_marca.addItems(listar_marcas())
        grid_h.addWidget(self.combo_marca, 0, 1)

        grid_h.addWidget(QtGui.QLabel("Longitud guía (mm):"), 1, 0)
        self.spin_guia = QtGui.QDoubleSpinBox()
        self.spin_guia.setRange(0, 800)
        self.spin_guia.setSuffix(" mm")
        self.spin_guia.setDecimals(0)
        self.spin_guia.setSpecialValueText("Auto (según profundidad)")
        grid_h.addWidget(self.spin_guia, 1, 1)

        grid_h.addWidget(QtGui.QLabel("Montaje trasera:"), 2, 0)
        self.combo_montaje = QtGui.QComboBox()
        self.combo_montaje.addItems(["entre_laterales", "testa"])
        grid_h.addWidget(self.combo_montaje, 2, 1)

        main_layout.addWidget(grupo_herraje)
        main_layout.addStretch()

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

    def accept(self):
        """Aplicar cambios y cerrar el panel."""
        if not self.obj:
            return True
        try:
            App.ActiveDocument.openTransaction("Editar cajón oculta")
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
            App.ActiveDocument.commitTransaction()
            App.ActiveDocument.recompute()
            Gui.ActiveDocument.resetEdit()
        except Exception as e:
            App.Console.PrintError(f"[VDO] Error aceptando cambios: {e}\n")
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
