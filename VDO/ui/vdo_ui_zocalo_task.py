# -*- coding: utf-8 -*-
# =====================================================================
# vdo_ui_zocalo_task.py
# Task Panel del zócalo paramétrico VDO.
#
# El formulario entero se infiere de SPEC_ZOCALO: los cuatro grupos
# (Dimensiones, Separación, Estructura, Colocación), las once etiquetas,
# los once rangos, los sufijos y los tooltips salen del esquema.
#
# Aquí solo queda lo que el esquema no puede saber:
#   - la cabecera de pieza, que previsualiza la tira frontal;
#   - que la distancia trasera se deshabilita si no hay trasera;
#   - la validación geométrica del motor (tiras que se solapan, etc.),
#     que es matemática y no un rango por parámetro.
#
# Antes este archivo tenía 321 líneas, de las cuales ~200 eran el
# formulario, el volcado objeto->widget y el widget->objeto escritos a
# mano, con los rangos válidos viviendo solo dentro de los setRange().
# =====================================================================

from VDO.ui.vdo_ui_divisions_task import PanelHeaderWidget
from VDO.ui.vdo_ui_form_builder import VDOPanelGenerico
from VDO.hub.vdo_hub_registry import SPEC_ZOCALO
from VDO.core.vdo_math_zocalo import calcular_geometria_zocalo, ZocaloError


# Una tira de zócalo queda vista por sus cuatro bordes.
CANTOS_FRENTE = {
    "norte": "RIG", "sur": "RIG", "este": "RIG", "oeste": "RIG"}


class ZocaloTaskPanel(VDOPanelGenerico):
    """Panel de tareas para editar un zócalo."""

    SPEC = SPEC_ZOCALO
    VARIANTE = "zocalo"
    TITULO_TX = "Editar zócalo"

    # -----------------------------------------------------------------
    def widgets_extra(self):
        self.header = PanelHeaderWidget()
        return [self.header]

    def tras_cargar(self, obj):
        self._sincronizar_trasera()

    def al_cambiar(self):
        """Refresca la cabecera y el estado de la distancia trasera."""
        self._sincronizar_trasera()
        self._actualizar_header()

    # -----------------------------------------------------------------
    def _sincronizar_trasera(self):
        """Sin trasera no hay distancia trasera que ajustar."""
        chk = self.controles.get("TieneTrasera")
        spin = self.controles.get("DistanciaTrasera")
        if chk is not None and spin is not None:
            spin.setEnabled(bool(chk.isChecked()))

    def _actualizar_header(self):
        if not hasattr(self, "header"):
            return
        ancho = self.controles["Ancho"].value()
        alto = self.controles["AltoZocalo"].value()
        espesor = float(self.controles["EspesorTablero"].value())
        self.header.set_panel(
            "Zocalo_Frente", ancho, alto, espesor, CANTOS_FRENTE)

    # -----------------------------------------------------------------
    def validar_extra(self, obj):
        """Validación geométrica: la que el rango por parámetro no cubre.

        Los rangos del esquema (1..4000 mm de ancho, 0..500 de separación)
        no detectan que la tira frontal y la trasera se solapen, ni que la
        separación a los costados deje el zócalo sin luz interior. Eso lo
        sabe el motor, así que se le pregunta antes de confirmar.
        """
        try:
            calcular_geometria_zocalo(**obj.Proxy._config(obj))
        except ZocaloError as exc:
            return (str(exc),)
        except Exception:
            # Un fallo que no sea de validación lo reporta execute().
            return ()
        return ()
