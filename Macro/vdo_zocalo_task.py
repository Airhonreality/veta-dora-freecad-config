# -*- coding: utf-8 -*-
# =====================================================================
# vdo_zocalo_task.py
# Task Panel PySide del zócalo paramétrico VDO.
# =====================================================================

import FreeCAD as App
from PySide import QtGui, QtWidgets

from vdo_qt import VDO_DoubleSpinBox

from vdo_coco_divisions_task import PanelHeaderWidget
from vdo_task_base import VDOTransactionMixin, cerrar_dialogo
from vdo_module_props import (
    ANCLAJES, ANCLAJE_DEFAULT, ANCLAJE_LABELS,
    add_common_props, aplicar_rotacion
)
from vdo_zocalo_core import calcular_geometria_zocalo, ZocaloError


CANTOS_FRENTE = {
    "norte": "RIG", "sur": "RIG", "este": "RIG", "oeste": "RIG"}


class ZocaloTaskPanel(VDOTransactionMixin):
    """Panel de tareas para editar un zócalo."""

    def __init__(self, obj=None, on_accept=None, on_cancel=None,
                 auto_transaction=True):
        self.obj = obj
        self._vdo_aceptado = False
        self._init_vdo_task(
            on_accept=on_accept,
            on_cancel=on_cancel,
            auto_transaction=auto_transaction,
            transaction_name="Editar zócalo",
        )
        self.form = self._crear_widget()
        if obj:
            add_common_props(obj)
            self._cargar_valores(obj)
        self._actualizar_header()

    # -----------------------------------------------------------------
    def _crear_widget(self):
        widget = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(widget)

        self.header = PanelHeaderWidget()
        main_layout.addWidget(self.header)

        grupo_dim = QtWidgets.QGroupBox("Dimensiones del mueble")
        grid_dim = QtWidgets.QGridLayout(grupo_dim)

        grid_dim.addWidget(QtWidgets.QLabel("Ancho (mm):"), 0, 0)
        self.spin_ancho = VDO_DoubleSpinBox()
        self.spin_ancho.setRange(1, 4000)
        self.spin_ancho.setSuffix(" mm")
        self.spin_ancho.setDecimals(1)
        self.spin_ancho.setToolTip(
            "Ancho total del mueble; define el largo de la tira frontal.")
        grid_dim.addWidget(self.spin_ancho, 0, 1)

        grid_dim.addWidget(QtWidgets.QLabel("Fondo (mm):"), 1, 0)
        self.spin_fondo = VDO_DoubleSpinBox()
        self.spin_fondo.setRange(1, 2000)
        self.spin_fondo.setSuffix(" mm")
        self.spin_fondo.setDecimals(1)
        self.spin_fondo.setToolTip(
            "Fondo total del mueble; limita el largo de los laterales.")
        grid_dim.addWidget(self.spin_fondo, 1, 1)

        grid_dim.addWidget(QtWidgets.QLabel("Alto zócalo (mm):"), 2, 0)
        self.spin_alto = VDO_DoubleSpinBox()
        self.spin_alto.setRange(1, 400)
        self.spin_alto.setSuffix(" mm")
        self.spin_alto.setDecimals(1)
        self.spin_alto.setToolTip(
            "Altura física del zócalo (por ejemplo 100 o 120 mm).")
        grid_dim.addWidget(self.spin_alto, 2, 1)

        grid_dim.addWidget(QtWidgets.QLabel("Espesor tablero (mm):"), 3, 0)
        self.spin_espesor = QtWidgets.QSpinBox()
        self.spin_espesor.setRange(1, 40)
        self.spin_espesor.setSuffix(" mm")
        self.spin_espesor.setToolTip(
            "Espesor de las tiras de melamina del zócalo.")
        grid_dim.addWidget(self.spin_espesor, 3, 1)

        main_layout.addWidget(grupo_dim)

        grupo_sep = QtWidgets.QGroupBox("Separación y encuentros")
        grid_sep = QtWidgets.QGridLayout(grupo_sep)

        grid_sep.addWidget(QtWidgets.QLabel("Separación frontal:"), 0, 0)
        self.spin_frente = VDO_DoubleSpinBox()
        self.spin_frente.setRange(0, 500)
        self.spin_frente.setSuffix(" mm")
        self.spin_frente.setDecimals(1)
        self.spin_frente.setToolTip(
            "Distancia desde el frente del mueble hacia adentro. "
            "Deja espacio libre para no golpear los pies.")
        grid_sep.addWidget(self.spin_frente, 0, 1)

        grid_sep.addWidget(QtWidgets.QLabel("Distancia costados:"), 1, 0)
        self.spin_costados = VDO_DoubleSpinBox()
        self.spin_costados.setRange(0, 500)
        self.spin_costados.setSuffix(" mm")
        self.spin_costados.setDecimals(1)
        self.spin_costados.setToolTip(
            "Separación desde cada costado del mueble (0 = al ras).")
        grid_sep.addWidget(self.spin_costados, 1, 1)

        grid_sep.addWidget(QtWidgets.QLabel("Distancia trasera:"), 2, 0)
        self.spin_trasera = VDO_DoubleSpinBox()
        self.spin_trasera.setRange(0, 500)
        self.spin_trasera.setSuffix(" mm")
        self.spin_trasera.setDecimals(1)
        self.spin_trasera.setToolTip(
            "Separación desde el fondo del mueble para librar el rodapié "
            "de la pared.")
        grid_sep.addWidget(self.spin_trasera, 2, 1)

        self.chk_trasera = QtWidgets.QCheckBox("Tiene trasera")
        self.chk_trasera.setToolTip(
            "Cierra el cajón del zócalo por detrás.")
        grid_sep.addWidget(self.chk_trasera, 3, 0, 1, 2)

        main_layout.addWidget(grupo_sep)

        grupo_est = QtWidgets.QGroupBox("Estructura")
        grid_est = QtWidgets.QGridLayout(grupo_est)

        grid_est.addWidget(QtWidgets.QLabel("Divisiones interiores:"), 0, 0)
        self.spin_amarres = QtWidgets.QSpinBox()
        self.spin_amarres.setRange(0, 20)
        self.spin_amarres.setToolTip(
            "Partes iguales del hueco interior entre frente y trasera. "
            "Se resuelven con el motor de división de vanos (vdo_layout).")
        grid_est.addWidget(self.spin_amarres, 0, 1)

        main_layout.addWidget(grupo_est)

        grupo_coloc = QtWidgets.QGroupBox("Colocación")
        grid_coloc = QtWidgets.QGridLayout(grupo_coloc)

        grid_coloc.addWidget(QtWidgets.QLabel("Rotación Z:"), 0, 0)
        self.spin_rotacion = VDO_DoubleSpinBox()
        self.spin_rotacion.setRange(-360.0, 360.0)
        self.spin_rotacion.setDecimals(1)
        self.spin_rotacion.setSuffix(" °")
        self.spin_rotacion.setWrapping(True)
        self.spin_rotacion.setToolTip(
            "Rotación de colocación alrededor de Z. No cambia la geometría.")
        grid_coloc.addWidget(self.spin_rotacion, 0, 1)

        grid_coloc.addWidget(QtWidgets.QLabel("Anclaje:"), 1, 0)
        self.combo_anclaje = QtWidgets.QComboBox()
        for anclaje in ANCLAJES:
            self.combo_anclaje.addItem(
                ANCLAJE_LABELS.get(anclaje, anclaje), anclaje)
        self.combo_anclaje.setToolTip(
            "Esquina del zócalo que se apoya en el punto de colocación.")
        grid_coloc.addWidget(self.combo_anclaje, 1, 1)

        main_layout.addWidget(grupo_coloc)
        main_layout.addStretch()

        botones = QtWidgets.QDialogButtonBox()
        btn_ok = botones.addButton(
            "Crear y colocar" if not self.auto_transaction else "Aplicar",
            QtWidgets.QDialogButtonBox.AcceptRole)
        btn_cancelar = botones.addButton(
            "Cancelar", QtWidgets.QDialogButtonBox.RejectRole)
        botones.accepted.connect(self._on_ok)
        botones.rejected.connect(self._on_cancel)
        btn_ok.setToolTip(
            "Guarda los cambios del zócalo y recalcula la geometría.")
        btn_cancelar.setToolTip("Cierra sin aplicar los cambios.")
        main_layout.addWidget(botones)

        for senal in (
                self.spin_ancho.valueChanged,
                self.spin_fondo.valueChanged,
                self.spin_alto.valueChanged,
                self.spin_espesor.valueChanged,
                self.spin_frente.valueChanged,
                self.spin_costados.valueChanged,
                self.spin_trasera.valueChanged):
            senal.connect(self._actualizar_header)
        self.chk_trasera.toggled.connect(self._on_trasera)
        self.chk_trasera.toggled.connect(self._actualizar_header)
        self.chk_trasera.setChecked(True)

        return widget

    # -----------------------------------------------------------------
    def _on_trasera(self, activo):
        self.spin_trasera.setEnabled(bool(activo))

    def _actualizar_header(self, *_args):
        ancho = self.spin_ancho.value()
        alto = self.spin_alto.value()
        espesor = float(self.spin_espesor.value())
        self.header.set_panel(
            "Zocalo_Frente", ancho, alto, espesor, CANTOS_FRENTE)

    def _cargar_valores(self, obj):
        if hasattr(obj, "Ancho"):
            self.spin_ancho.setValue(float(obj.Ancho))
        if hasattr(obj, "Fondo"):
            self.spin_fondo.setValue(float(obj.Fondo))
        if hasattr(obj, "AltoZocalo"):
            self.spin_alto.setValue(float(obj.AltoZocalo))
        if hasattr(obj, "EspesorTablero"):
            self.spin_espesor.setValue(
                int(round(float(obj.EspesorTablero))))
        if hasattr(obj, "DistanciaFrente"):
            self.spin_frente.setValue(float(obj.DistanciaFrente))
        if hasattr(obj, "DistanciaCostados"):
            self.spin_costados.setValue(float(obj.DistanciaCostados))
        if hasattr(obj, "DistanciaTrasera"):
            self.spin_trasera.setValue(float(obj.DistanciaTrasera))
        if hasattr(obj, "TieneTrasera"):
            self.chk_trasera.setChecked(bool(obj.TieneTrasera))
        if hasattr(obj, "AmarresIntermedios"):
            self.spin_amarres.setValue(int(obj.AmarresIntermedios))
        self.spin_rotacion.setValue(
            float(getattr(obj, "VDO_RotacionZ", 0.0)))
        anclaje = getattr(obj, "VDO_Anclaje", ANCLAJE_DEFAULT)
        for i in range(self.combo_anclaje.count()):
            if self.combo_anclaje.itemData(i) == anclaje:
                self.combo_anclaje.setCurrentIndex(i)
                break

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
            for spin in (
                    self.spin_ancho, self.spin_fondo, self.spin_alto,
                    self.spin_frente, self.spin_costados,
                    self.spin_trasera, self.spin_rotacion):
                spin.interpretText()
            self.spin_espesor.interpretText()
            self.spin_amarres.interpretText()

            calcular_geometria_zocalo(
                self.spin_ancho.value(),
                self.spin_fondo.value(),
                self.spin_alto.value(),
                self.spin_espesor.value(),
                self.spin_frente.value(),
                self.spin_costados.value(),
                self.spin_trasera.value(),
                self.chk_trasera.isChecked(),
                self.spin_amarres.value(),
            )

            self.obj.Ancho = self.spin_ancho.value()
            self.obj.Fondo = self.spin_fondo.value()
            self.obj.AltoZocalo = self.spin_alto.value()
            self.obj.EspesorTablero = self.spin_espesor.value()
            self.obj.DistanciaFrente = self.spin_frente.value()
            self.obj.DistanciaCostados = self.spin_costados.value()
            self.obj.DistanciaTrasera = self.spin_trasera.value()
            self.obj.TieneTrasera = self.chk_trasera.isChecked()
            self.obj.AmarresIntermedios = self.spin_amarres.value()
            anclaje = self.combo_anclaje.currentData()
            if anclaje:
                self.obj.VDO_Anclaje = anclaje
            aplicar_rotacion(self.obj, self.spin_rotacion.value())
            App.ActiveDocument.recompute()
            self._vdo_commit()
            self._vdo_aceptado = True
            self._vdo_call_accept()
            return True
        except ZocaloError as exc:
            self._vdo_abort()
            QtWidgets.QMessageBox.warning(
                self.form, "Zócalo", str(exc))
            return False
        except Exception as exc:
            self._vdo_abort()
            App.Console.PrintError(
                f"[VDO] Error aceptando el zócalo: {exc}\n")
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
