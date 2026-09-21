# -*- coding: utf-8 -*-
# =====================================================================
# vdo_coco_task.py
# Task Panel visual PySide para el generador de COCO
# =====================================================================

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui, QtCore


class CocoTaskPanel:
    """Panel de tareas para editar propiedades de un COCO FeaturePython."""

    def __init__(self, obj=None):
        self.obj = obj
        self.form = self._crear_widget()
        if obj:
            self._cargar_valores(obj)

    def _crear_widget(self):
        widget = QtGui.QWidget()
        main_layout = QtGui.QVBoxLayout(widget)

        # --- Grupo: Medidas Generales ---
        grupo_medidas = QtGui.QGroupBox("Medidas Generales")
        grid_medidas = QtGui.QGridLayout(grupo_medidas)

        grid_medidas.addWidget(QtGui.QLabel("Alto (mm):"), 0, 0)
        self.spin_alto = QtGui.QDoubleSpinBox()
        self.spin_alto.setRange(100, 3000)
        self.spin_alto.setSuffix(" mm")
        self.spin_alto.setDecimals(1)
        grid_medidas.addWidget(self.spin_alto, 0, 1)

        grid_medidas.addWidget(QtGui.QLabel("Ancho (mm):"), 1, 0)
        self.spin_ancho = QtGui.QDoubleSpinBox()
        self.spin_ancho.setRange(100, 3000)
        self.spin_ancho.setSuffix(" mm")
        self.spin_ancho.setDecimals(1)
        grid_medidas.addWidget(self.spin_ancho, 1, 1)

        grid_medidas.addWidget(QtGui.QLabel("Fondo módulo (mm):"), 2, 0)
        self.spin_fondo = QtGui.QDoubleSpinBox()
        self.spin_fondo.setRange(100, 1500)
        self.spin_fondo.setSuffix(" mm")
        self.spin_fondo.setDecimals(1)
        grid_medidas.addWidget(self.spin_fondo, 2, 1)

        grid_medidas.addWidget(QtGui.QLabel("Espesor (mm):"), 3, 0)
        self.spin_espesor = QtGui.QSpinBox()
        self.spin_espesor.setRange(6, 50)
        self.spin_espesor.setSuffix(" mm")
        grid_medidas.addWidget(self.spin_espesor, 3, 1)

        main_layout.addWidget(grupo_medidas)

        # --- Grupo: Estructura y Fondo ---
        grupo_estructura = QtGui.QGroupBox("Estructura y Fondo")
        grid_est = QtGui.QGridLayout(grupo_estructura)

        grid_est.addWidget(QtGui.QLabel("Tapa:"), 0, 0)
        self.combo_tapa = QtGui.QComboBox()
        self.combo_tapa.addItems(["externo", "interno"])
        grid_est.addWidget(self.combo_tapa, 0, 1)

        grid_est.addWidget(QtGui.QLabel("Base:"), 1, 0)
        self.combo_base = QtGui.QComboBox()
        self.combo_base.addItems(["externo", "interno"])
        grid_est.addWidget(self.combo_base, 1, 1)

        self.chk_fondo = QtGui.QCheckBox("Tiene fondo")
        grid_est.addWidget(self.chk_fondo, 2, 0, 1, 2)

        grid_est.addWidget(QtGui.QLabel("Calibre fondo (mm):"), 3, 0)
        self.spin_calibre = QtGui.QSpinBox()
        self.spin_calibre.setRange(3, 25)
        self.spin_calibre.setSuffix(" mm")
        grid_est.addWidget(self.spin_calibre, 3, 1)

        grid_est.addWidget(QtGui.QLabel("Profundidad ranura (mm):"), 4, 0)
        self.spin_ranura = QtGui.QDoubleSpinBox()
        self.spin_ranura.setRange(0.5, 20.0)
        self.spin_ranura.setSuffix(" mm")
        self.spin_ranura.setDecimals(1)
        grid_est.addWidget(self.spin_ranura, 4, 1)

        grid_est.addWidget(QtGui.QLabel("Distancia borde (mm):"), 5, 0)
        self.spin_borde = QtGui.QDoubleSpinBox()
        self.spin_borde.setRange(0, 100.0)
        self.spin_borde.setSuffix(" mm")
        self.spin_borde.setDecimals(1)
        grid_est.addWidget(self.spin_borde, 5, 1)

        main_layout.addWidget(grupo_estructura)
        main_layout.addStretch()

        return widget

    def _cargar_valores(self, obj):
        """Carga las propiedades del FeaturePython en los controles."""
        if hasattr(obj, "Alto"):
            self.spin_alto.setValue(float(obj.Alto))
        if hasattr(obj, "Ancho"):
            self.spin_ancho.setValue(float(obj.Ancho))
        if hasattr(obj, "FondoModulo"):
            self.spin_fondo.setValue(float(obj.FondoModulo))
        if hasattr(obj, "Espesor"):
            self.spin_espesor.setValue(int(obj.Espesor))
        if hasattr(obj, "Tapa"):
            idx = self.combo_tapa.findText(obj.Tapa)
            if idx >= 0:
                self.combo_tapa.setCurrentIndex(idx)
        if hasattr(obj, "Base"):
            idx = self.combo_base.findText(obj.Base)
            if idx >= 0:
                self.combo_base.setCurrentIndex(idx)
        if hasattr(obj, "TieneFondo"):
            self.chk_fondo.setChecked(obj.TieneFondo)
        if hasattr(obj, "CalibreFondo"):
            self.spin_calibre.setValue(int(obj.CalibreFondo))
        if hasattr(obj, "ProfundidadRanura"):
            self.spin_ranura.setValue(float(obj.ProfundidadRanura))
        if hasattr(obj, "DistanciaBorde"):
            self.spin_borde.setValue(float(obj.DistanciaBorde))

    def accept(self):
        """Aplicar cambios y cerrar el panel."""
        if not self.obj:
            return True
        try:
            App.ActiveDocument.openTransaction("Editar COCO")
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


def abrir_task_panel(obj=None):
    """Abre el Task Panel para un COCO existente o crea uno nuevo."""
    panel = CocoTaskPanel(obj)
    Gui.Control.showDialog(panel)
    return panel
