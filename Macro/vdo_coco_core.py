# -*- coding: utf-8 -*-
# =====================================================================
# vdo_coco_core.py
# Motor unificado de cofres VDO (COCO = Contenedor Cohesivo)
# FeaturePython con ViewProvider para Task Panel visual
# =====================================================================

import FreeCAD as App
import Part
import sys

_vdo_macro_dir = App.getUserMacroDir(True)
if _vdo_macro_dir not in sys.path:
    sys.path.insert(0, _vdo_macro_dir)

import vdo_guardian


class CocoFeature:
    """FeaturePython que genera la geometría de un cofre COCO."""

    def __init__(self, obj):
        obj.addProperty("App::PropertyLength", "Alto", "Dimensiones",
                        "Alto total del módulo (mm)").Alto = 720.0
        obj.addProperty("App::PropertyLength", "Ancho", "Dimensiones",
                        "Ancho total del módulo (mm)").Ancho = 600.0
        obj.addProperty("App::PropertyLength", "FondoModulo", "Dimensiones",
                        "Profundidad total del módulo (mm)").FondoModulo = 580.0
        obj.addProperty("App::PropertyInteger", "Espesor", "Dimensiones",
                        "Espesor del tablero (mm)").Espesor = 18
        obj.addProperty("App::PropertyBool", "TieneFondo", "Estructura",
                        "Habilitar fondo/respaldo").TieneFondo = True
        obj.addProperty("App::PropertyInteger", "CalibreFondo", "Estructura",
                        "Espesor del fondo (mm)").CalibreFondo = 6
        obj.addProperty("App::PropertyFloat", "ProfundidadRanura", "Estructura",
                        "Profundidad de ranura para fondo (mm)").ProfundidadRanura = 3.0
        obj.addProperty("App::PropertyFloat", "DistanciaBorde", "Estructura",
                        "Distancia del borde para fondo grueso (mm)").DistanciaBorde = 18.0
        obj.addProperty("App::PropertyEnumeration", "Tapa", "Estructura",
                        "Configuración de la tapa").Tapa = ["externo", "interno"]
        obj.addProperty("App::PropertyEnumeration", "Base", "Estructura",
                        "Configuración de la base").Base = ["externo", "interno"]
        obj.addProperty("App::PropertyString", "EspaciosX", "Divisiones",
                        "Definición de espacios libres en eje X (JSON)").EspaciosX = ""
        obj.addProperty("App::PropertyString", "EspaciosY", "Divisiones",
                        "Definición de espacios libres en eje Y/Z (JSON)").EspaciosY = ""
        obj.addProperty("App::PropertyString", "ResumenEspacios", "Divisiones",
                        "Resumen legible de espacios calculados (solo lectura)")
        obj.Proxy = self

    def execute(self, fp):
        """Reconstruir la geometría del cofre."""
        import Part

        try:
            alto = float(fp.Alto)
            ancho = float(fp.Ancho)
            fondo = float(fp.FondoModulo)
            espesor = float(fp.Espesor)
            tapa = fp.Tapa
            base = fp.Base
            tiene_fondo = fp.TieneFondo
            calibre_fondo = float(fp.CalibreFondo)
            prof_ranura = float(fp.ProfundidadRanura)
            dist_borde = float(fp.DistanciaBorde)

            boxes = []

            # --- Calcular dimensiones de laterales ---
            lat_height = alto
            lat_pos_z = 0.0

            if tapa == "externo":
                lat_height -= espesor
            if base == "externo":
                lat_height -= espesor
                lat_pos_z = espesor

            # --- Calcular dimensiones de base ---
            if base == "externo":
                base_length = ancho
                base_pos_x = 0.0
            else:
                base_length = ancho - (espesor * 2)
                base_pos_x = espesor

            base_pos_z = 0.0

            # --- Calcular dimensiones de tapa ---
            if tapa == "externo":
                techo_length = ancho
                techo_pos_x = 0.0
            else:
                techo_length = ancho - (espesor * 2)
                techo_pos_x = espesor

            techo_pos_z = alto - espesor

            # Panel lateral izquierdo
            lat_izq = Part.makeBox(espesor, fondo, lat_height,
                                   App.Vector(0, 0, lat_pos_z))
            boxes.append(lat_izq)

            # Panel lateral derecho
            lat_der = Part.makeBox(espesor, fondo, lat_height,
                                   App.Vector(ancho - espesor, 0, lat_pos_z))
            boxes.append(lat_der)

            # Panel base
            panel_base = Part.makeBox(base_length, fondo, espesor,
                                      App.Vector(base_pos_x, 0, base_pos_z))
            boxes.append(panel_base)

            # Panel techo
            panel_techo = Part.makeBox(techo_length, fondo, espesor,
                                       App.Vector(techo_pos_x, 0, techo_pos_z))
            boxes.append(panel_techo)

            # --- Fondo ---
            if tiene_fondo:
                es_delgado = calibre_fondo <= 8.0
                if es_delgado:
                    f_len = ancho - (espesor * 2) + (prof_ranura * 2)
                    f_alt = alto - (espesor * 2) + (prof_ranura * 2)
                    f_x = espesor - prof_ranura
                    f_z = espesor - prof_ranura
                    f_y = 0.0
                else:
                    f_len = ancho - (espesor * 2)
                    f_alt = alto - (espesor * 2)
                    f_x = espesor
                    f_z = espesor
                    f_y = fondo - calibre_fondo - dist_borde

                fondo_box = Part.makeBox(f_len, calibre_fondo, f_alt,
                                         App.Vector(f_x, f_y, f_z))
                boxes.append(fondo_box)

            # --- Divisiones internas (Sistema de Espacios Libres) ---
            espacios_x = getattr(fp, "EspaciosX", "")
            espacios_y = getattr(fp, "EspaciosY", "")
            resumen_parts = []

            if espacios_x or espacios_y:
                from vdo_coco_spaces import (
                    generar_divisiones_x, generar_divisiones_y)

                ancho_util = ancho - (espesor * 2)
                altura_util = lat_height

                if espacios_x:
                    divs_x, resumen_x = generar_divisiones_x(
                        espacios_x, ancho_util, fondo, espesor,
                        lat_pos_z, altura_util)
                    boxes.extend(divs_x)
                    if resumen_x:
                        resumen_parts.append(resumen_x)

                if espacios_y:
                    divs_y, resumen_y = generar_divisiones_y(
                        espacios_y, ancho_util, fondo, espesor,
                        lat_pos_z, altura_util)
                    boxes.extend(divs_y)
                    if resumen_y:
                        resumen_parts.append(resumen_y)

                fp.ResumenEspacios = "\n".join(resumen_parts)

            fp.Shape = Part.makeCompound(boxes)
            
        except Exception as e:
            App.Console.PrintError(f"[VDO] Error en execute(): {e}\n")

    def dumps(self):
        return None

    def loads(self, state):
        return None


class ViewProviderCoco:
    """ViewProvider para el COCO FeaturePython."""

    def __init__(self, vobj):
        vobj.Proxy = self
        self.Object = vobj.Object

    def getIcon(self):
        # Buscar icono en la carpeta de macros
        import os
        icon_path = os.path.join(App.getUserMacroDir(True), "vdo_coco.svg")
        if os.path.exists(icon_path):
            return icon_path
        # Fallback: icono por defecto de FreeCAD
        return "Part_Box"

    def setEdit(self, vobj, mode):
        if mode == 0:
            try:
                from vdo_coco_spaces_task import CocoSpacesTaskPanel
                import FreeCADGui as Gui
                Gui.Control.showDialog(CocoSpacesTaskPanel(vobj.Object))
            except Exception as e:
                App.Console.PrintError(
                    f"[VDO] Error abriendo Task Panel: {e}\n")
            return True
        return False

    def unsetEdit(self, vobj, mode):
        import FreeCADGui as Gui
        Gui.Control.closeDialog()
        return True

    def claimChildren(self):
        return []

    def dumps(self):
        return None

    def loads(self, state):
        return None


def make_coco(configuracion):
    """
    Crea un COCO FeaturePython con propiedades configurables.

    Args:
        configuracion (dict): Parámetros del cofre.

    Returns:
        App.DocumentObject: El objeto FeaturePython creado.
    """
    doc = vdo_guardian.vdo_guard()
    if not doc:
        App.Console.PrintError("[VDO] No hay documento activo.\n")
        return None

    nombre = configuracion.get("nombre", "COCO_4C")

    obj = doc.addObject("Part::FeaturePython", nombre)
    CocoFeature(obj)

    if App.GuiUp:
        ViewProviderCoco(obj.ViewObject)

    # Aplicar configuración
    obj.Alto = configuracion.get("alto", 720.0)
    obj.Ancho = configuracion.get("ancho", 600.0)
    obj.FondoModulo = configuracion.get("fondo_modulo", 580.0)
    obj.Espesor = configuracion.get("espesor", 18)
    obj.TieneFondo = configuracion.get("tiene_fondo", True)
    obj.CalibreFondo = configuracion.get("calibre_fondo", 6)
    obj.ProfundidadRanura = configuracion.get("profundidad_ranura", 3.0)
    obj.DistanciaBorde = configuracion.get("distancia_borde", 18.0)
    obj.Tapa = configuracion.get("tapa", "externo")
    obj.Base = configuracion.get("base", "interno")
    obj.EspaciosX = configuracion.get("espacios_x", "")
    obj.EspaciosY = configuracion.get("espacios_y", "")

    doc.recompute()
    App.Console.PrintMessage(
        f"[VDO] COCO '{nombre}' creado con FeaturePython.\n")
    return obj
