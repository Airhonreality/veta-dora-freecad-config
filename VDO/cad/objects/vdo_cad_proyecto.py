# -*- coding: utf-8 -*-
# =====================================================================
# VDO/cad/objects/vdo_cad_proyecto.py
# Singleton VDO_Proyecto: metadatos de proyecto (Nombre, Cliente,
# Disenador, Fecha). Fuente de verdad para el membrete del dossier.
#
# App::FeaturePython visible y editable en el árbol (no Part::FeaturePython:
# el proyecto no necesita Shape, Placement ni visibilidad). Participa del
# DAG: cambiar Nombre/Cliente propaga recompute a las hojas que lo lean.
# =====================================================================

import FreeCAD as App

from VDO._paths import ensure_sys_path
ensure_sys_path()

from VDO.hub.vdo_hub_registry import SPEC_PROYECTO
from VDO.hub.vdo_hub_schema import (
    PROP_MODULO, aplicar_esquema, aplicar_config)
from VDO.cad.views.vdo_cad_view_base import VDOViewProviderBase


class ProyectoFeature:
    """FeaturePython del proyecto VDO (singleton de metadatos)."""

    def __init__(self, obj):
        aplicar_esquema(obj, SPEC_PROYECTO)
        obj.Proxy = self
        obj.VDO_Tipo = "ProyectoFeature"

    def onDocumentRestored(self, fp):
        """Migración hacia adelante: añade propiedades que falten."""
        aplicar_esquema(fp, SPEC_PROYECTO)
        fp.VDO_Tipo = "ProyectoFeature"

    def execute(self, fp):
        """El proyecto no tiene geometría propia (App::FeaturePython)."""
        pass

    def onDelete(self, obj, subelements):
        """El proyecto es singleton: no hay cascada de borrado."""
        return True

    def dumps(self):
        return None

    def loads(self, state):
        return None


class ViewProviderProyecto(VDOViewProviderBase):
    """ViewProvider del proyecto: panel de metadatos."""

    MENU_LABEL = "Propiedades del Proyecto"
    ICON = "vdo_proyecto.svg"

    def get_panel_class(self):
        from VDO.ui.vdo_ui_proyecto_task import ProyectoTaskPanel
        return ProyectoTaskPanel

    def claimChildren(self):
        """El proyecto no tiene hijos directos."""
        return []


def make_proyecto(configuracion):
    """Crea (o devuelve el existente) VDO_Proyecto como singleton.

    Solo debe existir un objeto de tipo "proyecto" por documento.
    Si ya existe, se actualizan sus valores y se devuelve el existente.
    Toda la creación/actualización ocurre en una transacción para que
    sea un solo Ctrl+Z (criterio E-2 de docs/07).
    """
    from VDO.shared import vdo_shared_guardian

    doc = vdo_shared_guardian.vdo_guard()
    if not doc:
        App.Console.PrintError("[VDO] No hay documento activo.\n")
        return None

    nombre = configuracion.get("nombre", "VDO_Proyecto")

    # Buscar proyecto existente (singleton por documento)
    existente = None
    for o in doc.Objects:
        if getattr(o, PROP_MODULO, None) == "proyecto":
            existente = o
            break

    doc.openTransaction("Crear/actualizar Proyecto VDO")
    try:
        if existente is not None:
            obj = existente
            obj.Label = nombre
        else:
            obj = doc.addObject("App::FeaturePython", nombre)
            ProyectoFeature(obj)
            if App.GuiUp:
                ViewProviderProyecto(obj.ViewObject)

        aplicar_config(obj, SPEC_PROYECTO, configuracion)

        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise

    doc.recompute()
    App.Console.PrintMessage(
        f"[VDO] Proyecto '{nombre}' listo (singleton de metadatos).\n")

    return obj
