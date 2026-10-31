# -*- coding: utf-8 -*-
"""
Test determinista: diagnóstico del bug de puertas vía _construir_puerta.

El bug: vdo_coco_divisions_task.py guarda ancho=0.0, alto=0.0, pos_x=0.0,
pos_z=0.0 como placeholders. En _construir_puerta:
    cfg.get("ancho", w)  -> devuelve 0.0 (clave existe, no usa fallback w)
Esto deja W=0, H=0, y PuertaFeature.execute() deja Shape vacío.

Ejecución: FreeCADCmd test_puerta_bug_simple.py
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

from VDO.cad.objects.vdo_cad_puerta import PuertaFeature

result_lines = []

def log(msg):
    result_lines.append(msg)
    print(msg)

def check(name, condition, msg=""):
    if condition:
        result_lines.append(f"  PASS: {name}")
    else:
        result_lines.append(f"  FAIL: {name} - {msg}")

def check_almost(name, actual, expected, delta=0.1, msg=""):
    ok = abs(actual - expected) <= delta
    if ok:
        result_lines.append(f"  PASS: {name} (actual={actual:.4f}, expected={expected:.4f})")
    else:
        result_lines.append(f"  FAIL: {name} (actual={actual:.4f}, expected={expected:.4f}) - {msg}")

log("\n=== TEST 1: cfg.get('ancho', w) con ancho=0.0 (placeholder) ===")

cfg = {"ancho": 0.0, "alto": 0.0, "pos_x": 0.0, "pos_z": 0.0}
w = 580.0
h = 680.0
x = 18.0
z = 18.0

ancho_obtenido = float(cfg.get("ancho", w))
alto_obtenido = float(cfg.get("alto", h))
pos_x_obtenido = float(cfg.get("pos_x", x))
pos_z_obtenido = float(cfg.get("pos_z", z))

check("BUG: ancho_obtenido == 0.0 (clave existe, fallback w ignorado)", ancho_obtenido == 0.0,
      f"ancho_obtenido={ancho_obtenido}, esperado 0.0 (BUG)")
check("BUG: alto_obtenido == 0.0 (clave existe, fallback h ignorado)", alto_obtenido == 0.0,
      f"alto_obtenido={alto_obtenido}, esperado 0.0 (BUG)")
check("BUG: pos_x_obtenido == 0.0 (clave existe, fallback x ignorado)", pos_x_obtenido == 0.0,
      f"pos_x_obtenido={pos_x_obtenido}, esperado 0.0 (BUG)")
check("BUG: pos_z_obtenido == 0.0 (clave existe, fallback z ignorado)", pos_z_obtenido == 0.0,
      f"pos_z_obtenido={pos_z_obtenido}, esperado 0.0 (BUG)")

# Verificar que el fallback funcionaría si la clave NO existiera
cfg_sin_ancho = {"alto": 0.0}
ancho_fallback = float(cfg_sin_ancho.get("ancho", w))
check("Fallback funciona si clave ausente: ancho = w", ancho_fallback == w,
      f"ancho_fallback={ancho_fallback}, esperado {w}")

log("\n=== TEST 2: PuertaFeature con W=0, H=0 -> Shape vacío ===")

doc = App.newDocument("TestPuertaVacia")
obj = doc.addObject("Part::FeaturePython", "Puerta_Vacia")
PuertaFeature(obj)
obj.TipoSistema = "Batiente Vertical"
obj.TipoMontaje = "Parche"
obj.SentidoApertura = "Izquierda"
obj.SistemaApertura = "tirador"
obj.Ancho = 0.0   # ancho placeholder
obj.Alto = 0.0    # alto placeholder
obj.Espesor = 18
obj.PosX = 0.0
obj.PosY = 0.0
obj.PosZ = 0.0
doc.recompute()

check("Puerta vacía: Shape isNull (W=0,H=0 -> Shape vacío)", obj.Shape.isNull(),
      f"Shape no es nulo (volumen={obj.Shape.Volume:.2f})")
check("Puerta vacía: Volumen == 0", abs(obj.Shape.Volume) < 1e-9,
      f"volumen={obj.Shape.Volume:.2f}")
App.closeDocument(doc.Name)

log("\n=== TEST 3: PuertaFeature con W=580, H=680 -> Shape válido ===")

doc = App.newDocument("TestPuertaValida")
obj = doc.addObject("Part::FeaturePython", "Puerta_Valida")
PuertaFeature(obj)
obj.TipoSistema = "Batiente Vertical"
obj.TipoMontaje = "Parche"
obj.SentidoApertura = "Izquierda"
obj.SistemaApertura = "tirador"
obj.Ancho = w   # ancho real del vano
obj.Alto = h    # alto real del vano
obj.Espesor = 18
obj.PosX = x    # con offset de espesor
obj.PosY = 0.0
obj.PosZ = z    # con offset de espesor
doc.recompute()

check("Puerta válida: Shape isValid", obj.Shape.isValid())
check("Puerta válida: Shape no nula", not obj.Shape.isNull())
check("Puerta válida: tiene sólidos", len(obj.Shape.Solids) > 0)
if not obj.Shape.isNull():
    check_almost("Puerta válida: Volumen > 0", obj.Shape.Volume, 0.0, delta=0.0,
                 msg=f"volumen={obj.Shape.Volume:.2f} mm³")
    bb = obj.Shape.BoundBox
    check_almost("Puerta válida: XLength = 580", bb.XLength, w, delta=0.1)
    check_almost("Puerta válida: YLength = 18", bb.YLength, 18.0, delta=0.1)
    check_almost("Puerta válida: ZLength = 680", bb.ZLength, h, delta=0.1)
App.closeDocument(doc.Name)

# Contar pases y fallos
passes = [l for l in result_lines if l.startswith("  PASS:")]
failures = [l for l in result_lines if l.startswith("  FAIL:")]

# ============================================================
# RESUMEN
# ============================================================
result_lines.append("\n" + "=" * 60)
result_lines.append(f"RESULTADO: {len(passes)} pasados, {len(failures)} fallidos")
result_lines.append("=" * 60)

result_text = "\n".join(result_lines)
print(result_text)

out_path = os.path.join(os.path.expanduser("~"), "puerta_bug_resultados.txt")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(result_text + "\n")

if failures:
    sys.exit(1)
else:
    print("\n>>> DIAGNÓSTICO CONFIRMADO: Bug de puertas identificado <<<")
    sys.exit(0)
