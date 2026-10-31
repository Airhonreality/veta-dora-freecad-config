# -*- coding: utf-8 -*-
"""
Tests deterministas Rama 1 - Versión con output explícito para FreeCADCmd.
"""

import sys
import os
import traceback

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

import VDO.core.vdo_math_reengrose as VDO_RE
from VDO.cad.objects.vdo_cad_reengrose_solids import forma_ref
from VDO.core.vdo_math_cajon import calcular_despiece, CORREDERA_OCULTA, APERTURA_TIRADOR

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

# ============================================================
# TEST 1: Reengrose L1 BBox contención
# ============================================================
print("\n=== TEST 1: Reengrose L1 BBox contención ===")

largo_panel = 600.0
ancho_panel = 580.0
espesor_panel = 18.0

config_reengrose = {
    "activo": True,
    "bordes": {
        "frente": {"activo": True, "ancho": 70.0, "distancia_al_canto": 0.0},
        "fondo": {"activo": True, "ancho": 70.0, "distancia_al_canto": 0.0},
        "izquierda": {"activo": True, "ancho": 70.0, "distancia_al_canto": 0.0},
        "derecha": {"activo": True, "ancho": 70.0, "distancia_al_canto": 0.0},
    },
    "esquinas": "vertical_domina",
    "fabricacion": "pacha",
    "choque_nucleo": "retroceso",
}

panel_bb = Part.makeBox(largo_panel, ancho_panel, espesor_panel).BoundBox
geo = VDO_RE.calcular_geometria_reengrose(
    {"nombre": "Panel_L1_Test", "largo": largo_panel, "ancho": ancho_panel, "espesor": espesor_panel},
    config_reengrose,
)

check("Hay refuerzos calculados", len(geo["refuerzos"]) > 0,
      f"refuerzos={len(geo['refuerzos'])}")

tol = 0.1
for ref in geo["refuerzos"]:
    nombre = ref.get("nombre", "?")
    borde = ref.get("borde", "?")
    forma = forma_ref(ref)
    check(f"forma_ref no None para {borde}", forma is not None,
          f"forma_ref retornó None")
    if forma is None:
        continue
    bb = forma.BoundBox
    check(f"{borde} XMin >= 0", bb.XMin >= panel_bb.XMin - tol,
          f"XMin={bb.XMin:.3f}")
    check(f"{borde} XMax <= 600", bb.XMax <= panel_bb.XMax + tol,
          f"XMax={bb.XMax:.3f} (DESBORDA en +X)")
    check(f"{borde} YMin >= 0", bb.YMin >= panel_bb.YMin - tol,
          f"YMin={bb.YMin:.3f}")
    check(f"{borde} YMax <= 580", bb.YMax <= panel_bb.YMax + tol,
          f"YMax={bb.YMax:.3f} (DESBORDA en +Y)")

# Tiras verticales: X <= 70mm
for ref in geo["refuerzos"]:
    if ref.get("borde") not in ("izquierda", "derecha"):
        continue
    forma = forma_ref(ref)
    if forma is None:
        continue
    ancho_x = forma.BoundBox.XMax - forma.BoundBox.XMin
    check_almost(f"{ref.get('borde')} dim X <= 70", ancho_x, 70.0, delta=5.0,
                 msg=f"X={ancho_x:.1f} mm")

# Tiras horizontales: Y <= 70mm
for ref in geo["refuerzos"]:
    if ref.get("borde") not in ("frente", "fondo"):
        continue
    forma = forma_ref(ref)
    if forma is None:
        continue
    ancho_y = forma.BoundBox.YMax - forma.BoundBox.YMin
    check_almost(f"{ref.get('borde')} dim Y <= 70", ancho_y, 70.0, delta=5.0,
                 msg=f"Y={ancho_y:.1f} mm")

# ============================================================
# TEST 2: Cajón despiece simetría
# ============================================================
print("\n=== TEST 2: Cajón despiece simetría (Bug C) ===")

config_cajon = {
    "ancho_libre": 600.0,
    "prof_libre": 580.0,
    "ancho_modulo": 600.0,
    "alto_frente": 200.0,
    "marca": "blum_tandem",
    "tipo_corredera": CORREDERA_OCULTA,
    "sistema_apertura": APERTURA_TIRADOR,
    "tipo_montaje_fachada": "parche",
    "holgura_lateral_fachada": 2.0,
}

d = calcular_despiece(config_cajon)
li = config_cajon["ancho_libre"]

check_almost("ancho_fachada = li + 30 = 630.0", d["fachada"]["ancho"], 630.0, delta=0.1,
             msg=f"actual={d['fachada']['ancho']:.2f}")

x_fachada_local = d["posiciones"]["fachada"]["x"]
ancho_fachada = d["fachada"]["ancho"]
solape = 16.0
holgura = 2.0
delta = d["guia"]["delta"]  # 49.0 para Blum Tandem oculta
# La fachada_x_local es relativa al origen de la caja del cajón.
# La caja del cajón está desplazada delta/2 respecto al vano.
# Posición de la fachada relativa al vano:
x_fachada_vano = delta / 2.0 + x_fachada_local
# Márgenes netos (después de solape y holgura):
margen_izq = x_fachada_vano + solape - holgura / 2.0
margen_der = li - (x_fachada_vano + ancho_fachada) + solape - holgura / 2.0
check_almost("margen_izq == margen_der (simetría bilateral)", margen_izq, margen_der, delta=0.1,
             msg=f"izq={margen_izq:.2f}, der={margen_der:.2f}")

# ============================================================
# TEST 3: COCO cavidad offset
# ============================================================
print("\n=== TEST 3: COCO cavidad offset (Bug B) ===")

doc = App.newDocument("TestCocoOffset")
try:
    from VDO.cad.objects.vdo_cad_coco import make_coco
    from VDO.core.vdo_math_layout import Layout

    layout = Layout()
    layout.add_column()
    layout.add_row()

    coco = make_coco({
        "nombre": "COCO_Offset_Test",
        "alto": 720,
        "ancho": 600,
        "fondo_modulo": 580,
        "espesor": 18,
        "divisiones": layout.dumps(),
    })
    doc.recompute()

    espesor = float(coco.Espesor)
    check_almost("Espesor COCO = 18.0", espesor, 18.0, delta=0.1)
    check("COCO Shape isValid", coco.Shape.isValid())
    check_almost("COCO XMax = 600", coco.Shape.BoundBox.XMax, 600.0, delta=0.1)
    check_almost("COCO YMax = 580", coco.Shape.BoundBox.YMax, 580.0, delta=0.1)
    check_almost("COCO ZMax = 720", coco.Shape.BoundBox.ZMax, 720.0, delta=0.1)
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
out_path = os.path.join(os.path.expanduser("~"), "rama1_resultados.txt")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(result_text + "\n")

if failures:
    sys.exit(1)
else:
    print("\n>>> TODOS LOS TESTS PASARON <<<")
    sys.exit(0)
