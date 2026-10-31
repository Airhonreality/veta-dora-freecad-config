# -*- coding: utf-8 -*-
# =====================================================================
# vdo_ui_tambor_task.py
# Task Panel del Tambor / Repisa Entamborada VDO.
#
# Formulario íntegramente inferido de SPEC_TAMBOR: cuatro grupos
# (Dimensiones, Estructura, Configuración, Anclaje) más Colocación, con
# sus diez etiquetas, rangos, sufijos y tooltips tomados del esquema.
#
# Lo único que queda aquí es una regla de interfaz que el esquema no
# expresa: el vano del tenedor solo tiene sentido en la repisa flotante.
#
# Antes: 251 líneas, de las cuales ~190 eran formulario, volcado y
# escritura a mano.
# =====================================================================

from VDO.ui.vdo_ui_form_builder import VDOPanelGenerico
from VDO.hub.vdo_hub_registry import SPEC_TAMBOR


class TamborTaskPanel(VDOPanelGenerico):
    """Configuración de un Tambor / Repisa Entamborada VDO."""

    SPEC = SPEC_TAMBOR
    VARIANTE = "tambor"
    TITULO_TX = "Editar tambor VDO"

    def al_cambiar(self):
        """El anclaje a pared solo aplica a la repisa flotante.

        En el "Panel Cerrado 4 Lados" no hay vano posterior, así que la
        profundidad del vano y el diámetro de varilla no pintan nada.
        """
        combo = self.controles.get("TipoTambor")
        if combo is None:
            return
        es_repisa = "Tenedor" in (combo.currentData() or combo.currentText())
        for nombre in ("ModoTenedor", "ProfundidadVanoTenedor",
                       "DiametroVarillaTenedor"):
            control = self.controles.get(nombre)
            if control is not None:
                control.setEnabled(es_repisa)
