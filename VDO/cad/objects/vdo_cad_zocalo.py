# -*- coding: utf-8 -*-
# =====================================================================
# vdo_cad_zocalo.py
# FeaturePython del zócalo paramétrico VDO.
#
# Solo la capa CAD: declarar propiedades (desde el esquema), llamar al
# motor y construir los sólidos. La matemática vive en
# VDO.core.vdo_math_zocalo.
# =====================================================================

import json

import FreeCAD as App
import Part

from VDO._paths import ensure_sys_path
ensure_sys_path()

from VDO.shared import vdo_shared_guardian
import VDO.hub.vdo_hub_module_props as VDO_MOD
from VDO.hub.vdo_hub_registry import SPEC_ZOCALO
from VDO.hub.vdo_hub_schema import (
    aplicar_esquema, aplicar_config, config_desde_objeto)
from VDO.cad.views.vdo_cad_view_base import VDOViewProviderBase

# La matemática del zócalo vive en VDO.core.vdo_math_zocalo (simetría de
# capas con coco/cajon/puerta). Se reexporta aquí porque es API pública:
# la importan vdo_ui_zocalo_task y tests/test_vdo_zocalo.py.
from VDO.core.vdo_math_zocalo import (  # noqa: F401  (reexportación)
    ZocaloError, NOMBRES_BORDE, ROLES_BORDE, CANTOS_BORDE,
    calcular_geometria_zocalo)



class ZocaloFeature:
    """FeaturePython que genera la geometría de un zócalo."""

    def __init__(self, obj):
        # Las 14 propiedades del zocalo las declara el esquema
        # (SPEC_ZOCALO en vdo_hub_registry). Antes eran 44 lineas de
        # obj.addProperty() con el tipo, el grupo, la ayuda y el default
        # escritos a mano aqui, y repetidos en el TaskPanel y en la
        # fabrica.
        aplicar_esquema(obj, SPEC_ZOCALO)
        obj.Proxy = self

    def onDocumentRestored(self, fp):
        """Migracion hacia delante de documentos guardados.

        aplicar_esquema() es idempotente: anade solo lo que falte. Un
        zocalo guardado antes de que el esquema existiera recibe aqui el
        testigo VDO_Modulo y cualquier propiedad nueva, sin perder
        valores.
        """
        aplicar_esquema(fp, SPEC_ZOCALO)

    def _config(self, fp):
        """Entrada del motor, derivada de las clave_motor del esquema."""
        return config_desde_objeto(fp, SPEC_ZOCALO)


    def execute(self, fp):
        try:
            geo = calcular_geometria_zocalo(**self._config(fp))
        except ValueError as exc:
            App.Console.PrintError(f"[VDO] Zócalo inválido: {exc}\n")
            fp.Shape = Part.Shape()
            fp.VDO_Paneles_JSON = "[]"
            fp.VDO_ResumenDespiece = f"Zócalo inválido: {exc}"
            return

        alto = float(fp.AltoZocalo)
        solidos = []
        for tira in geo["tiras"]:
            solidos.append(Part.makeBox(
                tira["w"], tira["h"], alto,
                App.Vector(tira["x"], tira["y"], 0.0)))
        for amarre in geo["amarres"]:
            solidos.append(Part.makeBox(
                amarre["w"], amarre["h"], alto,
                App.Vector(amarre["x"], amarre["y"], 0.0)))

        fp.Shape = Part.makeCompound(solidos)

        piezas = []
        for pieza in geo["piezas"]:
            dato = dict(pieza)
            dato["grupo"] = fp.Label
            dato["material_ref"] = fp.VDO_Material_Ref
            piezas.append(dato)
        fp.VDO_Paneles_JSON = json.dumps(piezas, ensure_ascii=False)
        fp.VDO_ResumenDespiece = geo["resumen"]

    def dumps(self):
        return None

    def loads(self, state):
        return None


class ViewProviderZocalo(VDOViewProviderBase):
    """ViewProvider del zócalo FeaturePython."""

    MENU_LABEL = "Propiedades del Zócalo"
    ICON = "vdo_zocalo.svg"

    def get_panel_class(self):
        from VDO.ui.vdo_ui_zocalo_task import ZocaloTaskPanel
        return ZocaloTaskPanel


def make_zocalo(configuracion):
    """Crea un zócalo paramétrico (FeaturePython).

    Args:
        configuracion (dict): claves ancho, fondo, alto_zocalo,
            espesor_tablero, distancia_frente, distancia_costados,
            distancia_trasera, tiene_trasera, amarres_intermedios,
            material_ref, rotacion/anclaje/nombre.

    Returns:
        App.DocumentObject: el objeto creado o None.
    """
    doc = vdo_shared_guardian.vdo_guard()
    if not doc:
        App.Console.PrintError("[VDO] No hay documento activo.\n")
        return None

    nombre = configuracion.get("nombre", "Zocalo")
    obj = doc.addObject("Part::FeaturePython", nombre)
    ZocaloFeature(obj)

    if App.GuiUp:
        ViewProviderZocalo(obj.ViewObject)

    # Un solo paso: aplicar_config() escribe lo que el llamador pasa y
    # deja intacto lo que no. Los valores por defecto ya los puso
    # aplicar_esquema() en __init__; aqui no se repiten.
    aplicar_config(obj, SPEC_ZOCALO, configuracion)

    rotacion = float(getattr(obj, "VDO_RotacionZ", 0.0))
    if rotacion:
        obj.Placement = App.Placement(
            obj.Placement.Base, VDO_MOD.rotacion_z(rotacion))

    doc.recompute()
    App.Console.PrintMessage(
        f"[VDO] Zócalo '{nombre}' creado "
        f"({float(obj.Ancho):.0f} × {float(obj.Fondo):.0f} × "
        f"{float(obj.AltoZocalo):.0f} mm).\n")
    return obj
