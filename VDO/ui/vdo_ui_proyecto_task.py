# -*- coding: utf-8 -*-
# =====================================================================
# VDO/ui/vdo_ui_proyecto_task.py
# Task Panel del VDO_Proyecto sobre VDOPanelGenerico.
# =====================================================================

from VDO.hub.vdo_hub_registry import SPEC_PROYECTO
from VDO.ui.vdo_ui_form_builder import VDOPanelGenerico


class ProyectoTaskPanel(VDOPanelGenerico):
    """Panel de metadatos del proyecto VDO.

    Todos los campos (Nombre, Cliente, Disenador, Fecha) se infieren del
    SPEC_PROYECTO. No hay widgets extra.
    """

    SPEC = SPEC_PROYECTO
    TITULO_TX = "Editar Proyecto VDO"

    def tras_cargar(self, obj):
        """FPR-08: conteos en vivo (no aplica al proyecto; placeholder)."""
        pass
