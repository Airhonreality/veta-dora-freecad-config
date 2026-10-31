#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vdo_export_cutting_list.py
Exporta lista de corte desde modelo VDO a CSV para OpenCutList

Sin hardcode: Lee especificaciones desde vdo_manifest.json
Filtro: Solo exporta paneles de melamina (excluye muros, paneles BIM, etc)
"""

import sys
import csv
from pathlib import Path

try:
    import FreeCAD as App
    import FreeCADGui as Gui
except ImportError:
    # Un modulo de libreria no puede llamar a sys.exit() al importarse:
    # aborta el interprete que lo importe (pytest incluido).
    raise ImportError("VDO: este modulo requiere ejecutarse dentro de FreeCAD")

# Importar loader
_macro_dir = Path(__file__).parent
sys.path.insert(0, str(_macro_dir))
from VDO.shared import vdo_shared_loader
import VDO.core.vdo_math_reengrose as VDO_RE


def _datos_panel(obj):
    orientacion = getattr(obj, "VDO_Orientacion", "horizontal")
    if hasattr(obj, "Largo"):
        largo = float(obj.Largo)
        ancho = float(obj.Ancho)
        espesor = float(obj.Espesor)
    else:
        length = obj.Length if hasattr(obj, "Length") else 0
        width = obj.Width if hasattr(obj, "Width") else 0
        height = obj.Height if hasattr(obj, "Height") else 0
        if orientacion == "vertical":
            largo, ancho, espesor = height, width, length
        else:
            largo, ancho, espesor = length, width, height

    cantos = {}
    for direccion in ("Norte", "Sur", "Este", "Oeste"):
        cantos[direccion.lower()] = getattr(
            obj, f"VDO_Canto_{direccion}", "FX")
    return largo, ancho, espesor, cantos, orientacion


def extraer_piezas_panel(obj):
    """Extrae las subpiezas fisicas del panel (base + reengrose/pacha)."""
    largo, ancho, espesor, cantos, orientacion = _datos_panel(obj)
    try:
        mod = VDO_RE.desde_objeto(obj)
    except Exception:
        mod = VDO_RE.ReengroseModifier()
    try:
        piezas = VDO_RE.despiece_panel(
            obj.Label, largo, ancho, espesor, mod, cantos=cantos,
            material_ref=getattr(obj, "VDO_Material_Ref", "melamina_standar"),
            orientacion=orientacion)
    except VDO_RE.ReengroseError as exc:
        print(f"⚠️  Reengrose inválido en '{obj.Label}': {exc}")
        piezas = VDO_RE.despiece_panel(
            obj.Label, largo, ancho, espesor, VDO_RE.ReengroseModifier(),
            cantos=cantos,
            material_ref=getattr(obj, "VDO_Material_Ref", "melamina_standar"),
            orientacion=orientacion)
    info_grupo = _grupo_desde_padre(obj)
    for pieza in piezas:
        pieza.setdefault("herrajes", getattr(obj, "VDO_Hardware", ""))
        pieza.setdefault("herrajes_qty", getattr(obj, "VDO_HardwareQty", 0))
        if info_grupo and not pieza.get("grupo"):
            pieza["grupo"] = info_grupo["grupo"]
            pieza["operacion"] = info_grupo["operacion"]
    return piezas


def _grupo_desde_padre(obj):
    """Grupo de fabricacion (p.ej. pacha) que el COCO asigna a este hijo.

    Un PanelFeature hijo no conserva el grupo de encolado: ese dato vive en
    la entrada de VDO_Paneles_JSON de su COCO padre (ParentCOCO), con la
    misma clave de nombre. Sin esta lectura, el CSV de corte pierde el
    grupo de las piezas materializadas.
    """
    import json
    padre = getattr(obj, "ParentCOCO", None)
    if padre is None or not getattr(padre, "VDO_Paneles_JSON", None):
        return None
    try:
        entradas = json.loads(padre.VDO_Paneles_JSON)
    except (ValueError, TypeError):
        return None
    for entrada in entradas:
        if entrada.get("nombre") in (obj.Name, obj.Label) and entrada.get("grupo"):
            return {"grupo": entrada["grupo"],
                    "operacion": entrada.get("operacion", "")}
    return None


def extraer_pieza(obj):
    """Compatibilidad: devuelve la pieza base del panel."""
    piezas = extraer_piezas_panel(obj)
    return piezas[0] if piezas else {}


def _piezas_ya_materializadas(obj):
    """True si el contenedor tiene sus piezas como PanelFeature hijos.

    Un contenedor VDO publica su despiece DOS veces: en VDO_Paneles_JSON y
    como PanelFeature hijos con su propio B-Rep. En el modo "todo" el
    recorrido visita esos hijos uno a uno, asi que leer ademas el JSON del
    padre contaba cada pieza dos veces (un COCO de 5 tableros salia con 10
    lineas en la lista de corte). Se queda el objeto real, que es el que
    lleva cantos, material y reengroses al dia; el JSON solo se usa para
    contenedores que todavia no han materializado sus piezas.
    """
    for hijo in (getattr(obj, "Hijos", None) or []):
        if hijo is not None and getattr(hijo, "VDO_Tipo", "") == "panel":
            return True
    return False


def extraer_piezas_del_documento(modo="todo"):
    """
    Extrae piezas de melamina del documento

    modo: "todo" | "seleccion" | "grupo"
    Filtro: Paneles (VDO_Tipo == "panel") y Contenedores (VDO_Tipo == "contenedor")
    Excluye: muros, paneles BIM, otros objetos
    """
    import json

    doc = App.ActiveDocument
    if not doc:
        print("❌ No hay documento activo")
        return []

    piezas = []

    if modo == "seleccion":
        # Solo objetos seleccionados
        selected = Gui.Selection.getSelectionEx()
        for sel in selected:
            obj = sel.Object
            if hasattr(obj, "VDO_Tipo"):
                if obj.VDO_Tipo == "panel":
                    piezas.extend(extraer_piezas_panel(obj))
                elif obj.VDO_Tipo == "contenedor":
                    # Extraer paneles del contenedor (ej: COCO_4C)
                    if hasattr(obj, "VDO_Paneles_JSON") and obj.VDO_Paneles_JSON:
                        try:
                            paneles_json = json.loads(obj.VDO_Paneles_JSON)
                            piezas.extend(paneles_json)
                        except:
                            pass

    elif modo == "grupo":
        # Solo el módulo activo
        modulo = doc.ActiveObject
        if modulo and hasattr(modulo, "VDO_Tipo"):
            if modulo.VDO_Tipo == "panel":
                piezas.extend(extraer_piezas_panel(modulo))
            elif modulo.VDO_Tipo == "contenedor":
                if hasattr(modulo, "VDO_Paneles_JSON") and modulo.VDO_Paneles_JSON:
                    try:
                        paneles_json = json.loads(modulo.VDO_Paneles_JSON)
                        piezas.extend(paneles_json)
                    except:
                        pass

    else:  # "todo"
        # Todas las piezas del documento
        for obj in doc.Objects:
            if hasattr(obj, "VDO_Tipo"):
                if obj.VDO_Tipo == "panel":
                    piezas.extend(extraer_piezas_panel(obj))
                elif (obj.VDO_Tipo == "contenedor"
                        and not _piezas_ya_materializadas(obj)):
                    # Extraer paneles del contenedor (ej: COCO_4C)
                    if hasattr(obj, "VDO_Paneles_JSON") and obj.VDO_Paneles_JSON:
                        try:
                            paneles_json = json.loads(obj.VDO_Paneles_JSON)
                            piezas.extend(paneles_json)
                        except:
                            pass

    return piezas


def agrupar_piezas_por_material(piezas):
    """Agrupa piezas por material para optimización"""
    agrupadas = {}
    for pieza in piezas:
        mat = pieza["material_ref"]
        if mat not in agrupadas:
            agrupadas[mat] = []
        agrupadas[mat].append(pieza)
    return agrupadas


def generar_csv_opencutlist(piezas, output_path):
    """Genera CSV compatible con OpenCutList"""

    loader = vdo_shared_loader.get_loader()
    if not loader:
        print("❌ No se pudo cargar configuración VDO")
        return False

    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            # Header para OpenCutList
            writer.writerow([
                "Length",
                "Width",
                "Thickness",
                "Quantity",
                "Material",
                "Name",
                "Unit Cost",
                "Total Cost",
                "Edge N",
                "Edge S",
                "Edge E",
                "Edge W",
                "Group",
                "Operation"
            ])

            # Escribir piezas
            total_costo = 0
            for pieza in piezas:
                mat_id = pieza["material_ref"]
                material = loader.get_material(mat_id)

                if not material:
                    print(f"⚠️  Material no encontrado: {mat_id}")
                    continue

                # Construir string de material (sin hardcode)
                # Prioriza el espesor real de la pieza (multi-espesor:
                # cajón caja=16, fondo=6, fachada=18); fallback al
                # primer espesor del material.
                espesor_pieza = pieza.get("espesor") or 0
                if espesor_pieza:
                    espesor = espesor_pieza
                else:
                    espesor = material["espesores"][0] if material["espesores"] else 18
                material_str = f"{espesor}mm_{material['referencia']}_{material['tipo']}"

                # Calcular costo
                area_m2 = (pieza["largo"] * pieza["ancho"]) / 1000000
                costo_unitario = loader.calcular_costo_material(mat_id, area_m2)
                costo_total = costo_unitario * pieza["cantidad"]
                total_costo += costo_total

                cantos = pieza.get("cantos", {})
                writer.writerow([
                    pieza["largo"],
                    pieza["ancho"],
                    espesor,
                    pieza["cantidad"],
                    material_str,
                    pieza["nombre"],
                    f"{costo_unitario:.2f}",
                    f"{costo_total:.2f}",
                    cantos.get("norte", "FX"),
                    cantos.get("sur", "FX"),
                    cantos.get("este", "FX"),
                    cantos.get("oeste", "FX"),
                    pieza.get("grupo", ""),
                    pieza.get("operacion", "")
                ])

            # Fila de total
            writer.writerow([])
            writer.writerow([
                "TOTAL COSTO MATERIAL", "", "", "", "", "", "",
                f"{total_costo:.2f}", "", "", "", "", "", ""])

        print(f"✅ Exportado: {output_path}")
        print(f"💰 Costo total de material: ${total_costo:.2f}")
        return True

    except Exception as e:
        print(f"❌ Error escribiendo CSV: {e}")
        return False


def main(modo="todo"):
    """Main: Extrae, previsualia, exporta"""
    print("=" * 70)
    print(f"📊 VDO EXPORT CUTTING LIST - {modo.upper()}")
    print("=" * 70)

    # Extraer piezas
    print(f"\n🔍 Extrayendo piezas ({modo})...")
    piezas = extraer_piezas_del_documento(modo)

    if not piezas:
        print("⚠️  No se encontraron piezas de melamina para exportar")
        return False

    print(f"✅ {len(piezas)} piezas encontradas")

    # Mostrar preview (colorear y confirmar)
    print("\n🎨 Mostrando preview...")
    import VDO.cam.vdo_cam_cutlist_preview
    vdo_cutting_list_preview.main(modo=modo)

    return True


if __name__ == "__main__":
    main(modo="todo")
