#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vdo_export_cutting_list.py
Exporta lista de corte desde modelo VDO a CSV para OpenCutList

Sin hardcode: Lee especificaciones desde vdo_manifest.json
"""

import sys
import csv
from pathlib import Path

try:
    import FreeCAD as App
except ImportError:
    print("❌ Este script debe ejecutarse dentro de FreeCAD")
    sys.exit(1)

# Importar loader
_macro_dir = Path(__file__).parent
sys.path.insert(0, str(_macro_dir))
import vdo_loader


def extraer_piezas_del_documento():
    """Extrae todas las piezas de melamina del documento activo"""
    doc = App.ActiveDocument
    if not doc:
        print("❌ No hay documento activo")
        return []

    piezas = []
    for obj in doc.Objects:
        # Buscar objetos con propiedades VDO
        if hasattr(obj, "VDO_Tipo"):
            pieza = {
                "nombre": obj.Label,
                "tipo": obj.VDO_Tipo,
                "largo": obj.Length if hasattr(obj, "Length") else 0,
                "ancho": obj.Width if hasattr(obj, "Width") else 0,
                "espesor": obj.Height if hasattr(obj, "Height") else 0,
                "cantidad": 1,
                "material_ref": getattr(obj, "VDO_Material_Ref", "melamina_standar"),
                "herrajes": getattr(obj, "VDO_Hardware", ""),
                "herrajes_qty": getattr(obj, "VDO_HardwareQty", 0),
            }
            piezas.append(pieza)

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


def main():
    print("=" * 70)
    print("📊 VDO EXPORT CUTTING LIST")
    print("=" * 70)

    # Extraer piezas
    print("\n🔍 Extrayendo piezas del documento...")
    piezas = extraer_piezas_del_documento()

    if not piezas:
        print("⚠️  No se encontraron piezas con propiedades VDO")
        return False

    print(f"✅ {len(piezas)} piezas encontradas")

    # Agrupar por material
    print("\n📦 Agrupando por material...")
    agrupadas = agrupar_piezas_por_material(piezas)
    for mat, lista in agrupadas.items():
        print(f"  - {mat}: {len(lista)} piezas")

    # Exportar
    print("\n💾 Generando CSV para OpenCutList...")
    output_file = Path.home() / "Desktop" / "vdo_cutting_list.csv"

    if generar_csv_opencutlist(piezas, output_file):
        print("\n" + "=" * 70)
        print("✅ EXPORTACIÓN COMPLETADA")
        print("=" * 70)
        print(f"\n📁 Archivo: {output_file}")
        print("\n📌 Próximos pasos:")
        print("   1. Abre OpenCutList web: https://www.opencutlist.org/")
        print("   2. Importa el CSV generado")
        print("   3. Optimiza disposición de tableros")
        print("   4. Genera plano de corte")
        return True
    else:
        print("\n❌ Error durante exportación")
        return False


if __name__ == "__main__":
    import sys
    sys.exit(0 if main() else 1)
