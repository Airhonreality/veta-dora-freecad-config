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
import vdo_defaults as VDO_D


class CocoFeature:
    """FeaturePython que genera la geometría de un cofre COCO."""

    def __init__(self, obj):
        obj.addProperty("App::PropertyLength", "Alto", "Dimensiones",
                        "Alto total del módulo (mm)").Alto = VDO_D.ALTO_DEFAULT
        obj.addProperty("App::PropertyLength", "Ancho", "Dimensiones",
                        "Ancho total del módulo (mm)").Ancho = VDO_D.ANCHO_DEFAULT
        obj.addProperty("App::PropertyLength", "FondoModulo", "Dimensiones",
                        "Profundidad total del módulo (mm)").FondoModulo = VDO_D.FONDO_DEFAULT
        obj.addProperty("App::PropertyInteger", "Espesor", "Dimensiones",
                        "Espesor del tablero (mm)").Espesor = VDO_D.ESPESOR_DEFAULT
        obj.addProperty("App::PropertyBool", "TieneFondo", "Estructura",
                        "Habilitar fondo/respaldo").TieneFondo = VDO_D.FONDO_HABILITADO
        obj.addProperty("App::PropertyInteger", "CalibreFondo", "Estructura",
                        "Espesor del fondo (mm)").CalibreFondo = VDO_D.FONDO_CALIBRE
        obj.addProperty("App::PropertyFloat", "ProfundidadRanura", "Estructura",
                        "Profundidad de ranura para fondo (mm)").ProfundidadRanura = VDO_D.FONDO_PROFUNDIDAD_RANURA
        obj.addProperty("App::PropertyFloat", "DistanciaBorde", "Estructura",
                        "Distancia del borde para fondo grueso (mm)").DistanciaBorde = VDO_D.FONDO_DISTANCIA_BORDE
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

        # === PROPIEDADES DE EXPORTACIÓN (para cutting list) ===
        obj.addProperty("App::PropertyString", "VDO_Tipo", "VDO",
                        "Tipo de objeto").VDO_Tipo = "contenedor"
        obj.addProperty("App::PropertyString", "VDO_Subtipo", "VDO",
                        "Subtipo (COCO, módulo, etc)").VDO_Subtipo = "COCO_4C"
        obj.addProperty("App::PropertyString", "VDO_Material_Ref", "VDO",
                        "Material de los paneles").VDO_Material_Ref = "melamina_standar"

        # Paneles internos (propiedades de lectura para exportación)
        obj.addProperty("App::PropertyString", "VDO_Paneles_JSON", "VDO",
                        "Descripción JSON de los 5 paneles internos")

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

            # === GUARDAR DATOS DE LOS 5 PANELES PARA EXPORTACIÓN ===
            import json
            paneles_data = [
                {
                    "nombre": f"{fp.Label}_Lateral_Izq",
                    "tipo": "panel",
                    "largo": espesor,
                    "ancho": fondo,
                    "espesor": lat_height,
                    "cantidad": 1,
                    "material_ref": fp.VDO_Material_Ref
                },
                {
                    "nombre": f"{fp.Label}_Lateral_Der",
                    "tipo": "panel",
                    "largo": espesor,
                    "ancho": fondo,
                    "espesor": lat_height,
                    "cantidad": 1,
                    "material_ref": fp.VDO_Material_Ref
                },
                {
                    "nombre": f"{fp.Label}_Base",
                    "tipo": "panel",
                    "largo": base_length,
                    "ancho": fondo,
                    "espesor": espesor,
                    "cantidad": 1,
                    "material_ref": fp.VDO_Material_Ref
                },
                {
                    "nombre": f"{fp.Label}_Techo",
                    "tipo": "panel",
                    "largo": techo_length,
                    "ancho": fondo,
                    "espesor": espesor,
                    "cantidad": 1,
                    "material_ref": fp.VDO_Material_Ref
                }
            ]

            # Agregar fondo si está habilitado
            if tiene_fondo:
                f_len = ancho - (espesor * 2) + (prof_ranura * 2) if (calibre_fondo <= 8.0) else (ancho - (espesor * 2))
                f_alt = alto - (espesor * 2) + (prof_ranura * 2) if (calibre_fondo <= 8.0) else (alto - (espesor * 2))
                paneles_data.append({
                    "nombre": f"{fp.Label}_Fondo",
                    "tipo": "panel",
                    "largo": f_len,
                    "ancho": calibre_fondo,
                    "espesor": f_alt,
                    "cantidad": 1,
                    "material_ref": fp.VDO_Material_Ref
                })

            fp.VDO_Paneles_JSON = json.dumps(paneles_data, ensure_ascii=False)

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

    # Aplicar configuración (valores por defecto desde vdo_manifest.json)
    obj.Alto = configuracion.get("alto", VDO_D.ALTO_DEFAULT)
    obj.Ancho = configuracion.get("ancho", VDO_D.ANCHO_DEFAULT)
    obj.FondoModulo = configuracion.get("fondo_modulo", VDO_D.FONDO_DEFAULT)
    obj.Espesor = configuracion.get("espesor", VDO_D.ESPESOR_DEFAULT)
    obj.TieneFondo = configuracion.get("tiene_fondo", VDO_D.FONDO_HABILITADO)
    obj.CalibreFondo = configuracion.get("calibre_fondo", VDO_D.FONDO_CALIBRE)
    obj.ProfundidadRanura = configuracion.get("profundidad_ranura", VDO_D.FONDO_PROFUNDIDAD_RANURA)
    obj.DistanciaBorde = configuracion.get("distancia_borde", VDO_D.FONDO_DISTANCIA_BORDE)
    obj.Tapa = configuracion.get("tapa", VDO_D.TAPA_POSICION)
    obj.Base = configuracion.get("base", VDO_D.BASE_POSICION)
    obj.EspaciosX = configuracion.get("espacios_x", "")
    obj.EspaciosY = configuracion.get("espacios_y", "")

    doc.recompute()
    App.Console.PrintMessage(
        f"[VDO] COCO '{nombre}' creado con FeaturePython.\n")
    return obj
