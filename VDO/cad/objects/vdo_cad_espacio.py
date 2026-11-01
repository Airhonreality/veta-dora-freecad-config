# -*- coding: utf-8 -*-
# =====================================================================
# vdo_cad_espacio.py
# Contenedor territorial VDO_Espacio (T2, ADR-005).
#
# Part::FeaturePython con Shape NULA: nodo relacional puro que agrupa
# muros, muebles y assets de un recinto real (ej. Cocina, Habitación Juan)
# mediante PropertyLinkListChild (Hijos). No aplica matrices de
# transformacion sobre sus hijos; cada hijo conserva sus coordenadas de
# mundo. NivelPiso y AlturaCielorraso son cotas logicas de obra, no
# desplazamientos geometricos.
#
# Dependencia estrictamente unidireccional: Espacio -> contiene -> COCO.
# El execute() del COCO es geometricamente autonomo y NUNCA enlaza con el
# Espacio (cero ciclos DAG, coexistencia T2/T3).
# =====================================================================

import FreeCAD as App
import Part

from VDO._paths import ensure_sys_path
ensure_sys_path()

from VDO.hub.vdo_hub_registry import SPEC_ESPACIO
from VDO.hub.vdo_hub_schema import aplicar_esquema, aplicar_config
from VDO.cad.views.vdo_cad_view_base import VDOViewProviderBase


class EspacioFeature:
    """FeaturePython del contenedor territorial VDO_Espacio."""

    def __init__(self, obj):
        aplicar_esquema(obj, SPEC_ESPACIO)
        obj.Proxy = self
        # VDO_Tipo es metadato del sistema: se impone siempre, incluso en
        # documentos restaurados donde la propiedad acaba de añadirse.
        obj.VDO_Tipo = "EspacioFeature"

    def onDocumentRestored(self, fp):
        """Migracion hacia adelante: anade propiedades faltantes del esquema."""
        aplicar_esquema(fp, SPEC_ESPACIO)
        fp.VDO_Tipo = "EspacioFeature"

    def execute(self, fp):
        """El Espacio no tiene geometria propia: Shape NULA (ADR-004 / T5).

        No toca a sus hijos ni propaga Placement: es un nodo relacional
        puro. La validacion de tipo vive en la API de insercion y el
        guardiano informa pasivamente de intrusos.
        """
        fp.Shape = Part.Shape()

    def onDelete(self, obj, subelements):
        """Borrado en cascada: elimina los hijos del Espacio sin huorfanos.

        Solo los objetos que el Espacio posee directamente (Hijos). Los
        hijos no referencian al Espacio, asi que no hay ciclo DAG.
        """
        try:
            hijos = list(getattr(obj, "Hijos", None) or [])
            doc = obj.Document
            for hijo in hijos:
                if hijo is not None and doc.getObject(hijo.Name):
                    doc.removeObject(hijo.Name)
        except Exception:
            pass
        return True

    def dumps(self):
        return None

    def loads(self, state):
        return None


class ViewProviderEspacio(VDOViewProviderBase):
    """ViewProvider del Espacio: arbol plano, claimChildren refleja Hijos."""

    MENU_LABEL = "Propiedades del Espacio"
    ICON = "vdo_espacio.svg"

    def get_panel_class(self):
        from VDO.ui.vdo_ui_espacio_task import EspacioTaskPanel
        return EspacioTaskPanel

    def claimChildren(self):
        """Retorna los hijos directos (arquitectura/mobiliario/assets) para
        mostrarlos bajo el Espacio en el arbol nativo, sin subcarpetas."""
        try:
            obj = self.Object
            hijos = list(getattr(obj, "Hijos", None) or [])
            return [h for h in hijos if h is not None]
        except Exception:
            return []


def make_espacio(configuracion):
    """Crea un VDO_Espacio como Part::FeaturePython con Shape NULA.

    Args:
        configuracion (dict): parametros del espacio (NombreEspacio,
            NivelPiso, AlturaCielorraso, ...).

    Returns:
        App.DocumentObject: el Part::FeaturePython creado, o None.
    """
    from VDO.shared import vdo_shared_guardian

    doc = vdo_shared_guardian.vdo_guard()
    if not doc:
        App.Console.PrintError("[VDO] No hay documento activo.\n")
        return None

    nombre = configuracion.get("nombre", "ESPACIO_SinNombre")
    # "nombre" es el identificador del objeto; NombreEspacio (que alimenta
    # el membrete del dossier) toma el mismo valor salvo que el llamador
    # pase explicitamente "nombre_espacio".
    config = dict(configuracion)
    config.setdefault("nombre_espacio", nombre)

    # Toda la creacion en una transaccion para que un solo Ctrl+Z
    # deshaga el espacio completo (criterio E-2 de docs/07).
    doc.openTransaction("Crear Espacio VDO")
    try:
        obj = doc.addObject("Part::FeaturePython", nombre)
        EspacioFeature(obj)

        if App.GuiUp:
            ViewProviderEspacio(obj.ViewObject)

        aplicar_config(obj, SPEC_ESPACIO, config)

        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise

    doc.recompute()
    App.Console.PrintMessage(
        f"[VDO] Espacio '{nombre}' creado (Part::FeaturePython, Shape nula).\n")

    return obj
