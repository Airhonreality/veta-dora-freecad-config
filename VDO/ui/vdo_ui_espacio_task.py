# -*- coding: utf-8 -*-
# =====================================================================
# VDO/ui/vdo_ui_espacio_task.py
# Task Panel del VDO_Espacio sobre VDOPanelGenerico.
# =====================================================================

from PySide import QtWidgets

from VDO.hub.vdo_hub_registry import SPEC_ESPACIO
from VDO.shared.vdo_shared_familias import hijos_por_familia
from VDO.ui.vdo_ui_form_builder import VDOPanelGenerico


class EspacioTaskPanel(VDOPanelGenerico):
    """Panel de propiedades del VDO_Espacio.

    NombreEspacio, NivelPiso y AlturaCielorraso se infieren del SPEC_ESPACIO.
    NotasInstalacion y RequisitosCliente (multilinea) se inyectan como
    widgets extra porque el esquema las declara con ui=False.
    """

    SPEC = SPEC_ESPACIO
    TITULO_TX = "Editar Espacio VDO"

    def widgets_extra(self):
        """QTextEdit para NotasInstalacion y RequisitosCliente (multilinea)."""
        extras = []

        lbl_notas = QtWidgets.QLabel("Notas de instalación:")
        lbl_notas.setToolTip(
            "Notas de instalación, advertencias de pared, desniveles...")
        self.edit_notas = QtWidgets.QTextEdit()
        self.edit_notas.setPlaceholderText(
            "Notas de instalación, advertencias de pared, desniveles...")
        self.edit_notas.setMaximumHeight(100)
        self.edit_notas.setToolTip(
            "Notas de instalación, advertencias de pared, desniveles...")
        extras.extend([lbl_notas, self.edit_notas])

        lbl_req = QtWidgets.QLabel("Requisitos del cliente:")
        lbl_req.setToolTip(
            "Requerimientos estéticos y funcionales del cliente para este recinto.")
        self.edit_requisitos = QtWidgets.QLineEdit()
        self.edit_requisitos.setPlaceholderText(
            "Requerimientos del cliente para este recinto...")
        self.edit_requisitos.setToolTip(
            "Requerimientos estéticos y funcionales del cliente para este recinto.")
        extras.extend([lbl_req, self.edit_requisitos])

        return extras

    def tras_cargar(self, obj):
        """Vuelca NotasInstalacion y RequisitosCliente a los controles extra."""
        self.edit_notas.setPlainText(getattr(obj, "NotasInstalacion", "") or "")
        self.edit_requisitos.setText(
            getattr(obj, "RequisitosCliente", "") or "")

    def tras_aplicar(self, obj):
        """Escribe NotasInstalacion y RequisitosCliente desde los controles."""
        obj.NotasInstalacion = self.edit_notas.toPlainText()
        obj.RequisitosCliente = self.edit_requisitos.text()

    def al_cambiar(self):
        """FPR-08: conteos en vivo de arquitectura/mobiliario/assets."""
        if self.obj is None:
            return
        try:
            n_arq = len(hijos_por_familia(self.obj, "arquitectura"))
            n_mob = len(hijos_por_familia(self.obj, "mobiliario"))
            n_assets = len(hijos_por_familia(self.obj, "assets"))
            self.form.setWindowTitle(
                f"Espacio VDO — Arquitectura: {n_arq}, "
                f"Mobiliario: {n_mob}, Assets: {n_assets}")
        except Exception:
            pass
