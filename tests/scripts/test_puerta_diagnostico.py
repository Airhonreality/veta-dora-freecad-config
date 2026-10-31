# -*- coding: utf-8 -*-
"""
Test determinista: diagnóstico de puertas VDO.
Verifica que PuertaFeature dibuja geometría para cada tipo de sistema y montaje.

Ejecución: FreeCADCmd test_puerta_diagnostico.py
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

from VDO.cad.objects.vdo_cad_puerta import make_puerta, PuertaFeature
from VDO.core.vdo_math_puerta import (
    APERTURA_TIRADOR, APERTURA_GOLA, APERTURA_45_GRADOS, APERTURA_PUSH_OPEN,
    MONTAJE_PARCHE, MONTAJE_SEMIPARCHE, MONTAJE_EMBEBIDA,
)

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

print("\n=== TEST PUERTA: Geometría directa por tipo de sistema y montaje ===")

doc = App.newDocument("TestPuertaDirecta")
try:
    sistemas = ["Batiente Vertical", "Basculante Horizontal", "Corrediza"]
    montajes = ["Parche", "Semiparche", "Embebida"]
    aperturas = [APERTURA_TIRADOR, APERTURA_GOLA, APERTURA_45_GRADOS, APERTURA_PUSH_OPEN]

    for sistema in sistemas:
        for montaje in montajes:
            # Saltar combinaciones inválidas: Semiparche/Embebida solo para batiente
            if montaje in ("Semiparche", "Embebida") and sistema != "Batiente Vertical":
                continue
            for apertura in aperturas:
                nombre = f"Puerta_{sistema.replace(' ', '_')}_{montaje}_{apertura}"
                cfg = {
                    "nombre": nombre,
                    "tipo_sistema": sistema,
                    "tipo_montaje": montaje,
                    "sentido_apertura": "Izquierda",
                    "sistema_apertura": apertura,
                    "ancho": 400.0,
                    "alto": 700.0,
                    "espesor": 18,
                    "pos_x": 100.0,
                    "pos_y": 0.0,
                    "pos_z": 100.0,
                }
                obj = make_puerta(cfg)
                doc.recompute()

                check(f"{nombre} objeto creado", obj is not None)
                if obj is None:
                    continue

                check(f"{nombre} Shape isValid", obj.Shape.isValid())
                check(f"{nombre} Shape no vacía", not obj.Shape.isNull())
                if not obj.Shape.isNull():
                    vol = obj.Shape.Volume
                    check_almost(f"{nombre} Volumen > 0", vol, 0.0, delta=0.0,
                                 msg=f"volumen={vol:.2f} mm³")
                    check(f"{nombre} tiene sólidos", len(obj.Shape.Solids) > 0)
                    bb = obj.Shape.BoundBox
                    check_almost(f"{nombre} XLength > 0", bb.XLength, 0.0, delta=0.0,
                                 msg=f"XLength={bb.XLength:.2f}")
                    check_almost(f"{nombre} YLength > 0", bb.YLength, 0.0, delta=0.0,
                                 msg=f"YLength={bb.YLength:.2f}")
                    check_almost(f"{nombre} ZLength > 0", bb.ZLength, 0.0, delta=0.0,
                                 msg=f"ZLength={bb.ZLength:.2f}")
finally:
    App.closeDocument(doc.Name)

print("\n=== TEST PUERTA: Vía COCO (puerta como hijo del COCO) ===")

doc = App.newDocument("TestPuertaCOCO")
try:
    from VDO.cad.objects.vdo_cad_coco import make_coco
    from VDO.core.vdo_math_layout import Layout

    layout = Layout()
    layout.add_column()
    layout.add_row()

    coco = make_coco({
        "nombre": "COCO_Puerta_Test",
        "alto": 720,
        "ancho": 600,
        "fondo_modulo": 580,
        "espesor": 18,
        "divisiones": layout.dumps(),
    })
    doc.recompute()

    check("COCO creado", coco is not None)
    check("COCO Shape isValid", coco.Shape.isValid())

    # Ahora añadir una puerta como hijo del COCO directamente
    from VDO.cad.objects.vdo_cad_puerta import make_puerta
    puerta_cfg = {
        "nombre": "Puerta_COCOTEST",
        "tipo_sistema": "Batiente Vertical",
        "tipo_montaje": "Parche",
        "sentido_apertura": "Izquierda",
        "sistema_apertura": APERTURA_TIRADOR,
        "ancho": 580.0,
        "alto": 680.0,
        "espesor": 18,
        "pos_x": 18.0,   # offset de cavidad (espesor)
        "pos_y": 0.0,
        "pos_z": 18.0,   # offset de cavidad (espesor)
        "parent_coco": coco,
    }
    puerta = make_puerta(puerta_cfg)
    doc.recompute()

    check("Puerta vía COCO creada", puerta is not None)
    if puerta is not None:
        check("Puerta COCO Shape isValid", puerta.Shape.isValid())
        check("Puerta COCO Shape no vacía", not puerta.Shape.isNull())
        if not puerta.Shape.isNull():
            check_almost("Puerta COCO Volumen > 0", puerta.Shape.Volume, 0.0, delta=0.0,
                         msg=f"volumen={puerta.Shape.Volume:.2f} mm³")
            check("Puerta COCO tiene sólidos", len(puerta.Shape.Solids) > 0)
            bb = puerta.Shape.BoundBox
            check_almost("Puerta COCO XLength > 0", bb.XLength, 0.0, delta=0.0,
                         msg=f"XLength={bb.XLength:.2f}")
            check_almost("Puerta COCO YLength > 0", bb.YLength, 0.0, delta=0.0,
                         msg=f"YLength={bb.YLength:.2f}")
            check_almost("Puerta COCO ZLength > 0", bb.ZLength, 0.0, delta=0.0,
                         msg=f"ZLength={bb.ZLength:.2f}")

    # Verificar que el COCO tenga la puerta en Hijos
    check("COCO tiene Hijos", len(list(coco.Hijos or [])) > 0)
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

# Escribir a archivo para capturar salida
out_path = os.path.join(os.path.expanduser("~"), "puerta_resultados.txt")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(result_text + "\n")

if failures:
    sys.exit(1)
else:
    print("\n>>> TODOS LOS TESTS DE PUERTA PASARON <<<")
    sys.exit(0)
