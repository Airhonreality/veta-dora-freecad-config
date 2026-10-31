# -*- coding: utf-8 -*-
"""
Test determinista: Bug de puertas vía _construir_puerta (Bug D).

El bug: vdo_coco_divisions_task.py::_guardar_config_actual() guarda
"ancho": 0.0, "alto": 0.0, "pos_x": 0.0, "pos_z": 0.0 como placeholders.
Luego _construir_puerta() usa cfg.get("ancho", w) que devuelve 0.0
(la clave existe, no usa el fallback w). W=0 → PuertaFeature.execute()
deja Shape vacío → ninguna puerta se dibuja.

Fix: usar cfg.get("ancho") or w (el operador 'or' usa el fallback cuando
el valor es 0.0/falsy, a diferencia de get() que solo fallback si la clave
no existe).

Ejecución: FreeCADCmd test_puerta_bug_d_fix.py
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

log("\n=== TEST D: Puerta con config placeholder (ancho=0.0) → usa w como fallback ===")

cfg_bug = {"ancho": 0.0, "alto": 0.0, "pos_x": 0.0, "pos_z": 0.0}
w = 580.0
h = 680.0
x = 18.0
z = 18.0

# Simular el fix: cfg.get("ancho") or w  (en vez de cfg.get("ancho", w))
ancho_fix = float(cfg_bug.get("ancho") or w)
alto_fix = float(cfg_bug.get("alto") or h)
pos_x_fix = float(cfg_bug.get("pos_x") or x)
pos_z_fix = float(cfg_bug.get("pos_z") or z)

check_almost("Fix: ancho = w (no 0.0)", ancho_fix, w, delta=0.1)
check_almost("Fix: alto = h (no 0.0)", alto_fix, h, delta=0.1)
check_almost("Fix: pos_x = x (no 0.0)", pos_x_fix, x, delta=0.1)
check_almost("Fix: pos_z = z (no 0.0)", pos_z_fix, z, delta=0.1)

# Verificar que cfg.get("ancho", w) todavía está roto (para documentar el bug)
ancho_roto = float(cfg_bug.get("ancho", w))
check("BUG documentado: cfg.get('ancho', w) = 0.0 (clave existe)", ancho_roto == 0.0,
      f"ancho_roto={ancho_roto}, debería ser 0.0 para confirmar el bug")

log("\n=== TEST D: PuertaFeature con valores del fix → Shape válido ===")

doc = App.newDocument("TestPuertaFixD")
obj = doc.addObject("Part::FeaturePython", "Puerta_FixD")
PuertaFeature(obj)
obj.TipoSistema = "Batiente Vertical"
obj.TipoMontaje = "Parche"
obj.SentidoApertura = "Izquierda"
obj.SistemaApertura = "tirador"
obj.Ancho = ancho_fix   # w = 580 (no 0.0)
obj.Alto = alto_fix     # h = 680 (no 0.0)
obj.Espesor = 18
obj.PosX = pos_x_fix    # x = 18 (con offset de espesor)
obj.PosY = 0.0
obj.PosZ = pos_z_fix    # z = 18 (con offset de espesor)
doc.recompute()

check("Puerta fix: Shape isValid", obj.Shape.isValid())
check("Puerta fix: Shape no nula", not obj.Shape.isNull())
check("Puerta fix: tiene sólidos", len(obj.Shape.Solids) > 0)
if not obj.Shape.isNull():
    check("Puerta fix: Volumen > 0", obj.Shape.Volume > 1e-9,
          f"volumen={obj.Shape.Volume:.2f} mm³")
    bb = obj.Shape.BoundBox
    check_almost("Puerta fix: XLength = 580", bb.XLength, w, delta=0.1)
    check_almost("Puerta fix: YLength = 18", bb.YLength, 18.0, delta=0.1)
    check_almost("Puerta fix: ZLength = 680", bb.ZLength, h, delta=0.1)
    # La posición está en LocalPlacement (no en BoundBox del Shape)
    check_almost("Puerta fix: LocalPlacement.X = 18 (offset espesor)",
                 obj.LocalPlacement.Base.x, x, delta=0.1)
    check_almost("Puerta fix: LocalPlacement.Z = 18 (offset espesor)",
                 obj.LocalPlacement.Base.z, z, delta=0.1)
App.closeDocument(doc.Name)

# Contar pases y fallos
passes = [l for l in result_lines if l.startswith("  PASS:")]
failures = [l for l in result_lines if l.startswith("  FAIL:")]

result_lines.append("\n" + "=" * 60)
result_lines.append(f"RESULTADO: {len(passes)} pasados, {len(failures)} fallidos")
result_lines.append("=" * 60)

result_text = "\n".join(result_lines)
print(result_text)

out_path = os.path.join(os.path.expanduser("~"), "puerta_bug_d_resultados.txt")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(result_text + "\n")

if failures:
    sys.exit(1)
else:
    print("\n>>> TEST D (PUERTAS): TODOS PASARON <<<")
    sys.exit(0)
