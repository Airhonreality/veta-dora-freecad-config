# -*- coding: utf-8 -*-
# =====================================================================
# vdo_cad_tambor.py
# FeaturePython del Tambor / Repisa Entamborada Flotante.
#
# Solo la capa CAD: declarar propiedades (desde el esquema), llamar al
# motor y construir los sólidos. La matemática vive en
# VDO.core.vdo_math_tambor.
#
# Antes este archivo se llamaba vdo_tambor_core.py: el único de
# VDO/cad/objects/ que no seguía la convención vdo_cad_*.
# =====================================================================

import json

import FreeCAD as App
import Part

from VDO.hub.vdo_hub_registry import SPEC_TAMBOR
from VDO.hub.vdo_hub_schema import aplicar_esquema, aplicar_config
from VDO.cad.views.vdo_cad_view_base import VDOViewProviderBase

# API pública: la importan los tests y vdo_ui_tambor_task.
from VDO.core.vdo_math_tambor import calcular_geometria_tambor



class TamborFeature:
    """FeaturePython que modela un Tambor / Repisa Entamborada Flotante."""

    def __init__(self, obj):
        # Las 15 propiedades del tambor las declara SPEC_TAMBOR. Ahi se
        # corrigio tambien su VDO_Tipo: era "tambor", valor que el
        # if/elif de vdo_cam_cutlist no contempla, asi que el despiece
        # que este execute() escribe en VDO_Paneles_JSON no lo leia
        # nadie. Ahora es "contenedor".
        aplicar_esquema(obj, SPEC_TAMBOR)
        obj.Proxy = self

    def onDocumentRestored(self, fp):
        """Migracion hacia delante: anade lo que falte, no pisa valores."""
        aplicar_esquema(fp, SPEC_TAMBOR)
        # Reparacion explicita: los tambores guardados con el VDO_Tipo
        # viejo seguirian fuera de la lista de corte. aplicar_esquema()
        # no lo arregla porque la propiedad ya existe.
        if getattr(fp, "VDO_Tipo", "") == "tambor":
            fp.VDO_Tipo = SPEC_TAMBOR.vdo_tipo
            App.Console.PrintLog(
                f"[VDO] {fp.Name}: VDO_Tipo 'tambor' -> "
                f"'{SPEC_TAMBOR.vdo_tipo}' (entra en la lista de corte).\n")


    def execute(self, fp):
        try:
            tipo_key = "repisa_tenedor" if "Tenedor" in fp.TipoTambor else "panel_cerrado"
            modo_key = "taladrado" if "Taladrado" in fp.ModoTenedor else "abierto"

            geo = calcular_geometria_tambor(
                largo=fp.Largo,
                ancho=fp.Ancho,
                espesor_total=fp.EspesorTotal,
                espesor_tapas=fp.EspesorTapas,
                ancho_liston=fp.AnchoListon,
                tipo=tipo_key,
                modo_tenedor=modo_key,
                prof_tenedor=fp.ProfundidadVanoTenedor,
                costillas=fp.CostillasInteriores,
                diam_varilla=fp.DiametroVarillaTenedor,
            )

            solidos = []
            for s in geo["solidos"]:
                box = Part.makeBox(s["w"], s["h"], s["d"], App.Vector(s["x"], s["y"], s["z"]))

                # Si es listón taladrado, sustraer perforaciones para pernos del tenedor
                if s.get("taladros_tenedor"):
                    r = geo["diam_varilla"] / 2.0
                    cz = s["z"] + (s["d"] / 2.0)
                    for px in (s["x"] + s["w"] * 0.25, s["x"] + s["w"] * 0.75):
                        taladro = Part.makeCylinder(r, s["h"] + 2.0, App.Vector(px, s["y"] - 1.0, cz), App.Vector(0, 1, 0))
                        box = box.cut(taladro)

                # Aplicar modificadores embebidos (canal LED, relleno chapa, etc.)
                try:
                    mods = json.loads(getattr(fp, "VDO_Modificadores_JSON", "[]") or "[]")
                except (TypeError, ValueError):
                    mods = []

                for mod in mods:
                    mtype = mod.get("tipo")
                    if mtype == "corte_caja":
                        x = float(mod.get("x", 0.0))
                        y = float(mod.get("y", 0.0))
                        z = float(mod.get("z", 0.0))
                        w = float(mod.get("w", 0.0))
                        h = float(mod.get("h", 0.0))
                        d = float(mod.get("d", 0.0))
                        if w > 0 and h > 0 and d > 0:
                            cutter = Part.makeBox(w, h, d, App.Vector(x, y, z))
                            box = box.cut(cutter)
                    elif mtype == "fuse_caja":
                        x = float(mod.get("x", 0.0))
                        y = float(mod.get("y", 0.0))
                        z = float(mod.get("z", 0.0))
                        w = float(mod.get("w", 0.0))
                        h = float(mod.get("h", 0.0))
                        d = float(mod.get("d", 0.0))
                        if w > 0 and h > 0 and d > 0:
                            adder = Part.makeBox(w, h, d, App.Vector(x, y, z))
                            box = box.fuse(adder)

                solidos.append(box)

            fp.Shape = Part.makeCompound(solidos)
            fp.VDO_Paneles_JSON = json.dumps(geo["piezas"], ensure_ascii=False)

        except Exception as exc:
            App.Console.PrintError(f"[VDO Tambor] Error en execute(): {exc}\n")
            fp.Shape = Part.Shape()

    def dumps(self):
        return None

    def loads(self, state):
        return None


class ViewProviderTambor(VDOViewProviderBase):
    """ViewProvider del Tambor."""
    MENU_LABEL = "Propiedades del Tambor"
    ICON = "vdo_workbench.svg"

    def get_panel_class(self):
        from VDO.ui.vdo_ui_tambor_task import TamborTaskPanel
        return TamborTaskPanel


def make_tambor(configuracion):
    """Factory para crear un Tambor / Repisa flotante en el documento activo."""
    doc = App.ActiveDocument
    if doc is None:
        App.Console.PrintError("[VDO] No hay documento activo.\n")
        return None

    nombre = configuracion.get("nombre", "Repisa_Entamborada")
    obj = doc.addObject("Part::FeaturePython", nombre)
    TamborFeature(obj)

    if App.GuiUp:
        ViewProviderTambor(obj.ViewObject)

    aplicar_config(obj, SPEC_TAMBOR, configuracion)

    doc.recompute()
    return obj
