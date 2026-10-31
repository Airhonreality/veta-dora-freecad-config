# -*- coding: utf-8 -*-
"""
Suite de pruebas: Validación de BoundingBox del reengrose L1.

Verifica que las tiras de reengrose en modo 'marco_interior' con 'vertical_domina'
queden estrictamente contenidas dentro del BoundingBox del panel base.

Caso de prueba: Panel L1 horizontal 600x580 mm, reengrose 70 mm en 4 bordes.
"""

import sys
import unittest

import pytest

from tests._entorno import HAY_FREECAD

if not HAY_FREECAD:
    pytest.skip("requiere FreeCAD real; ejecutar con FreeCADCmd",
                allow_module_level=True)

import FreeCAD as App
import Part

# NO sembrar ~/.local/share/FreeCAD/Macro en sys.path: ahi vive una
# copia pre-refactor del paquete VDO/ que ganaba la resolucion de
# imports y hacia que estos tests validasen el codigo viejo.
# La raiz del repo la siembra tests/conftest.py.

import VDO.core.vdo_math_reengrose as VDO_RE
from VDO.cad.objects.vdo_cad_reengrose_solids import forma_ref


class TestReengroseL1BoundingBox(unittest.TestCase):
    """Validación estricta de contenedor geométrico para tiras de reengrose."""

    def setUp(self):
        """Prepara panel 600x580 con reengrose perimetral."""
        self.largo_panel = 600.0
        self.ancho_panel = 580.0
        self.espesor_panel = 18.0

        # Crear panel base (caja 600x580x18)
        self.panel_base = Part.makeBox(
            self.largo_panel, self.ancho_panel, self.espesor_panel)

        # Configurar reengrose: 70 mm ancho, marco_interior, 4 bordes, vertical_domina
        self.config_reengrose = {
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

    def test_tiras_contenidas_en_bbox_panel(self):
        """Las tiras deben estar 100% contenidas dentro del BoundingBox del panel."""
        panel_bb = self.panel_base.BoundBox

        geo = VDO_RE.calcular_geometria_reengrose(
            {
                "nombre": "Panel_L1_Test",
                "largo": self.largo_panel,
                "ancho": self.ancho_panel,
                "espesor": self.espesor_panel,
            },
            self.config_reengrose
        )

        # calcular_geometria_reengrose devuelve
        # {base, refuerzos, grupo_pacha, modificador}: no hay clave
        # "activo" (estaba en el contrato antiguo) y esto lanzaba
        # KeyError. El flag vive en el modificador.
        mod = geo["modificador"]
        activo = (mod.get("activo") if isinstance(mod, dict)
                  else getattr(mod, "activo", False))
        self.assertTrue(
            activo or geo["refuerzos"], "Debe haber refuerzos calculados")

        tolerancia = 0.1  # ±0.1 mm

        for ref in geo["refuerzos"]:
            forma = forma_ref(ref)
            if forma is None:
                continue

            tira_bb = forma.BoundBox

            # Validación X: tira debe estar dentro de panel [0, 600]
            self.assertGreaterEqual(
                tira_bb.XMin, panel_bb.XMin - tolerancia,
                f"Tira {ref.get('nombre', '?')} sobresale en -X: {tira_bb.XMin} < {panel_bb.XMin}"
            )
            self.assertLessEqual(
                tira_bb.XMax, panel_bb.XMax + tolerancia,
                f"Tira {ref.get('nombre', '?')} sobresale en +X: {tira_bb.XMax} > {panel_bb.XMax} "
                f"(DESBORDAMIENTO CRÍTICO)"
            )

            # Validación Y: tira debe estar dentro de panel [0, 580]
            self.assertGreaterEqual(
                tira_bb.YMin, panel_bb.YMin - tolerancia,
                f"Tira {ref.get('nombre', '?')} sobresale en -Y: {tira_bb.YMin} < {panel_bb.YMin}"
            )
            self.assertLessEqual(
                tira_bb.YMax, panel_bb.YMax + tolerancia,
                f"Tira {ref.get('nombre', '?')} sobresale en +Y: {tira_bb.YMax} > {panel_bb.YMax}"
            )

            # Validación Z: la tira se ADOSA a una cara, no se mete en el
            # tablero. "Reengrose" es engrosar: una tira de cara_a ocupa
            # z=[espesor, espesor+e] y una de cara_b z=[-e, 0]. La version
            # anterior exigia ZMax <= espesor, o sea que la tira cupiese
            # DENTRO del panel: lo contrario de lo que hace la funcion.
            cara = ref.get("cara", "cara_a")
            if cara == "cara_a":
                self.assertAlmostEqual(
                    tira_bb.ZMin, self.espesor_panel, delta=tolerancia,
                    msg=f"Tira {ref.get('nombre', '?')} no arranca en la cara "
                        f"A (z={tira_bb.ZMin}, esperado {self.espesor_panel})"
                )
            else:
                self.assertAlmostEqual(
                    tira_bb.ZMax, 0.0, delta=tolerancia,
                    msg=f"Tira {ref.get('nombre', '?')} no termina en la cara "
                        f"B (z={tira_bb.ZMax}, esperado 0)"
                )
            self.assertGreater(
                tira_bb.ZLength, 0.0,
                f"Tira {ref.get('nombre', '?')} sin espesor"
            )

    def test_dimensiones_tiras_verticales(self):
        """Tiras verticales (izq/der) deben tener dimensión X ≤ 70 mm (ancho reengrose)."""
        geo = VDO_RE.calcular_geometria_reengrose(
            {
                "nombre": "Panel_L1_Test",
                "largo": self.largo_panel,
                "ancho": self.ancho_panel,
                "espesor": self.espesor_panel,
            },
            self.config_reengrose
        )

        for ref in geo["refuerzos"]:
            borde = ref.get("borde", "")
            if borde not in ("izquierda", "derecha"):
                continue

            forma = forma_ref(ref)
            if forma is None:
                continue

            tira_bb = forma.BoundBox
            ancho_x = tira_bb.XMax - tira_bb.XMin

            self.assertLessEqual(
                ancho_x, 75.0,  # 70 + 5 mm tolerancia
                f"Tira {borde} tiene dimension X demasiado grande: {ancho_x:.1f} mm "
                f"(esperado ≤ 70 mm). BUG: w y h están intercambiados"
            )

    def test_dimensiones_tiras_horizontales(self):
        """Tiras horizontales (frente/fondo) deben tener dimensión Y ≤ 70 mm (ancho reengrose)."""
        geo = VDO_RE.calcular_geometria_reengrose(
            {
                "nombre": "Panel_L1_Test",
                "largo": self.largo_panel,
                "ancho": self.ancho_panel,
                "espesor": self.espesor_panel,
            },
            self.config_reengrose
        )

        for ref in geo["refuerzos"]:
            borde = ref.get("borde", "")
            if borde not in ("frente", "fondo"):
                continue

            forma = forma_ref(ref)
            if forma is None:
                continue

            tira_bb = forma.BoundBox
            ancho_y = tira_bb.YMax - tira_bb.YMin

            self.assertLessEqual(
                ancho_y, 75.0,  # 70 + 5 mm tolerancia
                f"Tira {borde} tiene dimension Y demasiado grande: {ancho_y:.1f} mm "
                f"(esperado ≤ 70 mm). BUG: w y h están intercambiados"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
