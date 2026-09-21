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
    print("❌ Este script debe ejecutarse dentro de FreeCAD")
    sys.exit(1)

# Importar loader
_macro_dir = Path(__file__).parent
sys.path.insert(0, str(_macro_dir))
import vdo_loader


def extraer_pieza(obj):
    """Extrae información de una pieza individual"""
    pieza = {
        "nombre": obj.Label,
        "tipo": getattr(obj, "VDO_Tipo", "desconocido"),
        "largo": obj.Length if hasattr(obj, "Length") else 0,
        "ancho": obj.Width if hasattr(obj, "Width") else 0,
        "espesor": obj.Height if hasattr(obj, "Height") else 0,
        "cantidad": 1,
        "material_ref": getattr(obj, "VDO_Material_Ref", "melamina_standar"),
        "herrajes": getattr(obj, "VDO_Hardware", ""),
        "herrajes_qty": getattr(obj, "VDO_HardwareQty", 0),
    }
    return pieza


def extraer_piezas_del_documento(modo="todo"):
    """
    Extrae piezas de melamina del documento

    modo: "todo" | "seleccion" | "grupo"
    Filtro: Solo paneles (VDO_Tipo == "panel")
    Excluye: muros, paneles BIM, otros objetos
    """
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
            # Filtrar: solo paneles de melamina
            if hasattr(obj, "VDO_Tipo") and obj.VDO_Tipo == "panel":
                piezas.append(extraer_pieza(obj))

    elif modo == "grupo":
        # Solo el módulo activo
        modulo = doc.ActiveObject
        if modulo and hasattr(modulo, "VDO_Tipo"):
            piezas.append(extraer_pieza(modulo))

    else:  # "todo"
        # Todas las piezas del documento
        for obj in doc.Objects:
            # Filtrar: solo paneles de melamina
            if hasattr(obj, "VDO_Tipo") and obj.VDO_Tipo == "panel":
                piezas.append(extraer_pieza(obj))

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

    loader = vdo_loader.get_loader()
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
                "Total Cost"
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
                espesor = material["espesores"][0] if material["espesores"] else 18
                material_str = f"{espesor}mm_{material['referencia']}_{material['tipo']}"

                # Calcular costo
                area_m2 = (pieza["largo"] * pieza["ancho"]) / 1000000
                costo_unitario = loader.calcular_costo_material(mat_id, area_m2)
                costo_total = costo_unitario * pieza["cantidad"]
                total_costo += costo_total

                writer.writerow([
                    pieza["largo"],
                    pieza["ancho"],
                    espesor,
                    pieza["cantidad"],
                    material_str,
                    pieza["nombre"],
                    f"{costo_unitario:.2f}",
                    f"{costo_total:.2f}"
                ])

            # Fila de total
            writer.writerow([])
            writer.writerow(["TOTAL COSTO MATERIAL", "", "", "", "", "", "", f"{total_costo:.2f}"])

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
    import vdo_cutting_list_preview
    vdo_cutting_list_preview.main(modo=modo)

    return True


if __name__ == "__main__":
    main(modo="todo")
