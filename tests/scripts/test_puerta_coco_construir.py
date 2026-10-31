# -*- coding: utf-8 -*-
"""
Test determinista: diagnóstico de puertas vía COCO (_construir_puerta).

Reproduce el bug real: el config de puerta guarda ancho=0.0, alto=0.0,
pos_x=0.0, pos_z=0.0 como placeholders, y cfg.get("ancho", w) devuelve 0.0
(no usa el fallback w porque la clave existe). Esto deja el Shape vacío.

Ejecución: FreeCADCmd test_puerta_coco_construir.py
"""

import sys
import os

# NO sembrar ~/.local/share/FreeCAD/Macro en sys.path: ahi vive una
# copia pre-refactor del paquete VDO/ que ganaba la resolucion de
# imports y hacia que estos tests validasen el codigo viejo.
# La raiz del repo la siembra tests/conftest.py.

import pytest

from tests._entorno import HAY_FREECAD

if not HAY_FREECAD:
    pytest.skip("requiere FreeCAD real; ejecutar con FreeCADCmd",
                allow_module_level=True)

import FreeCAD as App
import Part

from VDO.cad.objects.vdo_cad_coco import make_coco
from VDO.core.vdo_math_layout import Layout
from VDO.ui.vdo_ui_coco_task import CocoUnifiedTaskPanel

failures = []
passes = []

def check(name, condition, msg=""):
    if condition:
        passes.append(f"  PASS: {name}")
    else:
        failures.append(f"  FAIL: {name} - {msg}")

def check_almost(name, actual, expected, delta=0.1, msg=""):
    ok = abs(actual - expected) <= delta
    if ok:
        passes.append(f"  PASS: {name} (actual={actual:.4f}, expected={expected:.4f})")
    else:
        failures.append(f"  FAIL: {name} (actual={actual:.4f}, expected={expected:.4f}) - {msg}")

print("\n=== TEST PUERTA COCO: _construir_puerta con config placeholder (ancho=0) ===")

doc = App.newDocument("TestPuertaCocoConstruir")
try:
    layout = Layout()
    layout.add_column()
    layout.add_row()

    coco = make_coco({
        "nombre": "COCO_PuertaBug",
        "alto": 720,
        "ancho": 600,
        "fondo_modulo": 580,
        "espesor": 18,
        "divisiones": layout.dumps(),
    })
    doc.recompute()

    espesor = float(coco.Espesor)

    # Simular lo que hace _construir_insertos: leer contenido con ancho=0.0, alto=0.0
    # (como lo guarda _guardar_config_actual en vdo_coco_divisions_task.py)
    config_puerta_bug = {
        "tipo": "puerta",
        "config": {
            "nombre": "Puerta_Bug_Test",
            "tipo_sistema": "Batiente Vertical",
            "tipo_montaje": "Parche",
            "sentido_apertura": "Izquierda",
            "sistema_apertura": "tirador",
            "hardware_sku": "",
            "vdo_vano_id": "(0,0)",
            "ancho": 0.0,       # <-- BUG: placeholder, debería usarse w del resolved
            "alto": 0.0,        # <-- BUG: placeholder, debería usarse h del resolved
            "espesor": 18,
            "pos_x": 0.0,       # <-- BUG: placeholder, debería usarse x del resolved
            "pos_y": 0.0,
            "pos_z": 0.0,       # <-- BUG: placeholder, debería usarse z del resolved
            "anclaje": "inferior_izquierda_frente",
        },
    }

    # Llamar directamente a _construir_puerta con el config bug
    panel = CocoUnifiedTaskPanel(obj=coco, auto_transaction=False)

    # Obtener el resolved para la celda (0,0)
    editor = panel.editor_divisiones
    resolved_map = getattr(editor, "_resolved_map", {})
    layout_obj = getattr(editor, "layout", None)
    cell = layout_obj.get_cell(0, 0)
    resuelto = resolved_map.get(cell.label) if cell else None

    w = float(getattr(resuelto, "nominal_w", resuelto.w))
    h = float(getattr(resuelto, "nominal_h", resuelto.h))
    x = espesor + float(getattr(resuelto, "nominal_x", 0.0))
    z = espesor + float(getattr(resuelto, "nominal_z", 0.0))

    hijos_nuevos = []
    panel._construir_puerta(
        doc, coco, config_puerta_bug["config"], x, z, w, h, hijos_nuevos)
    doc.recompute()

    puerta = hijos_nuevos[0] if hijos_nuevos else None
    check("Puerta creada en hijos_nuevos", puerta is not None)

    if puerta is not None:
        check("Puerta Shape isValid", puerta.Shape.isValid())
        check("Puerta Shape no vacía", not puerta.Shape.isNull())
        if not puerta.Shape.isNull():
            check_almost("Puerta Ancho > 0 (no 0.0)", puerta.Ancho, w, delta=0.1,
                         msg=f"Ancho={puerta.Ancho}, esperado {w}")
            check_almost("Puerta Alto > 0 (no 0.0)", puerta.Alto, h, delta=0.1,
                         msg=f"Alto={puerta.Alto}, esperado {h}")
            check_almost("Puerta Volumen > 0", puerta.Shape.Volume, 0.0, delta=0.0,
                         msg=f"volumen={puerta.Shape.Volume:.2f} mm³ (BUG: Shape vacío)")
            check("Puerta tiene sólidos", len(puerta.Shape.Solids) > 0)
            bb = puerta.Shape.BoundBox
            check_almost("Puerta XLength > 0", bb.XLength, 0.0, delta=0.0,
                         msg=f"XLength={bb.XLength:.2f}")
            check_almost("Puerta ZLength > 0", bb.ZLength, 0.0, delta=0.0,
                         msg=f"ZLength={bb.ZLength:.2f}")

    # Ahora probar con config CORRECTO (ancho=w, alto=h, pos_x=x, pos_z=z)
    print("\n--- Probando con config correcto ---")
    config_puerta_ok = {
        "nombre": "Puerta_OK_Test",
        "tipo_sistema": "Batiente Vertical",
        "tipo_montaje": "Parche",
        "sentido_apertura": "Izquierda",
        "sistema_apertura": "tirador",
        "ancho": w,      # CORRECTO
        "alto": h,       # CORRECTO
        "espesor": 18,
        "pos_x": x,      # CORRECTO (incluye espesor)
        "pos_y": 0.0,
        "pos_z": z,      # CORRECTO (incluye espesor)
        "anclaje": "inferior_izquierda_frente",
    }

    hijos_nuevos2 = []
    panel._construir_puerta(
        doc, coco, config_puerta_ok, x, z, w, h, hijos_nuevos2)
    doc.recompute()

    puerta_ok = hijos_nuevos2[0] if hijos_nuevos2 else None
    check("Puerta OK creada", puerta_ok is not None)
    if puerta_ok is not None:
        check("Puerta OK Shape isValid", puerta_ok.Shape.isValid())
        check("Puerta OK Shape no vacía", not puerta_ok.Shape.isNull())
        if not puerta_ok.Shape.isNull():
            check_almost("Puerta OK Volumen > 0", puerta_ok.Shape.Volume, 0.0, delta=0.0,
                         msg=f"volumen={puerta_ok.Shape.Volume:.2f} mm³")
            check_almost("Puerta OK Ancho = w", puerta_ok.Ancho, w, delta=0.1)
            check_almost("Puerta OK Alto = h", puerta_ok.Alto, h, delta=0.1)

finally:
    App.closeDocument(doc.Name)

# ============================================================
# RESUMEN
# ============================================================
result_lines = []
result_lines.append("\n" + "=" * 60)
result_lines.append(f"RESULTADO: {len(passes)} pasados, {len(failures)} fallidos")
result_lines.append("=" * 60)
for p in passes:
    result_lines.append(p)
for f in failures:
    result_lines.append(f)

result_text = "\n".join(result_lines)
print(result_text)

out_path = os.path.join(os.path.expanduser("~"), "puerta_coco_resultados.txt")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(result_text + "\n")

if failures:
    sys.exit(1)
else:
    print("\n>>> TODOS LOS TESTS DE PUERTA COCO PASARON <<<")
    sys.exit(0)
