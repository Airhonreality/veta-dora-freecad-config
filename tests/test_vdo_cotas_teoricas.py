# -*- coding: utf-8 -*-
"""
Tests unitarios puros para VDO.core.vdo_math_frames._calcular_cotas_teoricas.

No requiere FreeCAD: solo aritmetica sobre un objeto simulado.
Cubre el criterio de exito de A1 (execute() y onChanged() comparten la
misma fuente de cotas) y A5 (delta bajo/sobre tolerancia 1e-4).
"""

import sys
import unittest

# Repo root en path para importar VDO.*
sys.path.insert(0, __file__.rsplit("tests", 1)[0])

import VDO.core.vdo_math_frames as VDO_FR  # noqa: E402


class FakeFP:
    """Objeto simulado con las propiedades numericas del COCO."""

    def __init__(self, **kwargs):
        self.Alto = kwargs.get("alto", 720.0)
        self.Ancho = kwargs.get("ancho", 600.0)
        self.FondoModulo = kwargs.get("fondo_modulo", 580.0)
        self.Espesor = kwargs.get("espesor", 18.0)
        self.Tapa = kwargs.get("tapa", "interno")
        self.Base = kwargs.get("base", "interno")
        self.TieneFondo = kwargs.get("tiene_fondo", True)
        self.CalibreFondo = kwargs.get("calibre_fondo", 6.0)
        self.ProfundidadRanura = kwargs.get("profundidad_ranura", 3.0)
        self.DistanciaBorde = kwargs.get("distancia_borde", 18.0)
        for clave, valor in kwargs.get("extra", {}).items():
            setattr(self, clave, valor)


class TestCalcularCotasTeoricas(unittest.TestCase):
    """_calcular_cotas_teoricas devuelve cotas teoricas en el marco de PanelFeature."""

    def setUp(self):
        self.fp = FakeFP()

    def _cotas(self, **kwargs):
        fp = FakeFP(**kwargs) if kwargs else self.fp
        return VDO_FR._calcular_cotas_teoricas(fp)

    def test_roles_esperados(self):
        cotas = self._cotas()
        self.assertEqual(
            set(cotas.keys()),
            {"lateral_izquierdo", "lateral_derecho", "base", "techo", "fondo"},
        )

    def test_cotas_estandar_interno_interno(self):
        """Alto=720 Ancho=600 Fondo=580 Espesor=18 tapa/base interno."""
        cotas = self._cotas()
        # Laterales: entero, z=0
        self.assertEqual(cotas["lateral_izquierdo"][:3], (720.0, 580.0, 18.0))
        self.assertEqual(cotas["lateral_izquierdo"][3], [0.0, 0.0, 0.0])
        self.assertEqual(cotas["lateral_izquierdo"][4], 0.0)
        self.assertEqual(cotas["lateral_derecho"][:3], (720.0, 580.0, 18.0))
        self.assertEqual(cotas["lateral_derecho"][3], [600.0 - 18.0, 0.0, 0.0])
        # Base / techo: ancho - 2*espesor
        self.assertEqual(cotas["base"][:3], (564.0, 580.0, 18.0))
        self.assertEqual(cotas["base"][3], [18.0, 0.0, 0.0])
        self.assertEqual(cotas["techo"][:3], (564.0, 580.0, 18.0))
        self.assertEqual(cotas["techo"][3], [18.0, 0.0, 702.0])
        # Fondo delgado (calibre 6 <= umbral 8)
        self.assertEqual(cotas["fondo"][:3], (690.0, 570.0, 6.0))
        self.assertEqual(cotas["fondo"][3], [585.0, 571.0, 15.0])
        self.assertEqual(cotas["fondo"][4], 90.0)

    def test_tapa_base_externo(self):
        cotas = self._cotas(tapa="externo", base="externo")
        self.assertEqual(cotas["lateral_izquierdo"][:3], (684.0, 580.0, 18.0))
        self.assertEqual(cotas["lateral_izquierdo"][3], [0.0, 0.0, 18.0])
        self.assertEqual(cotas["base"][:3], (600.0, 580.0, 18.0))
        self.assertEqual(cotas["base"][3], [0.0, 0.0, 0.0])
        self.assertEqual(cotas["techo"][:3], (600.0, 580.0, 18.0))
        self.assertEqual(cotas["techo"][3], [0.0, 0.0, 702.0])

    def test_sin_fondo(self):
        cotas = self._cotas(tiene_fondo=False)
        self.assertNotIn("fondo", cotas)
        self.assertEqual(cotas["lateral_izquierdo"][:3], (720.0, 580.0, 18.0))

    def test_espesor_cero_no_resta_lateral(self):
        cotas = self._cotas(espesor=0.0)
        self.assertEqual(cotas["lateral_izquierdo"][0], 720.0)
        self.assertEqual(cotas["base"][0], 600.0)

    def test_tolerancia_1e4_bajo_ya_igual(self):
        """Un delta de 1e-5 se considera dentro de la tolerancia (no se propaga)."""
        cotas = self._cotas()
        nl, na, ne, npos, nrot = cotas["lateral_izquierdo"]
        delta_bajo = 1e-5
        self.assertTrue(abs(nl - (nl + delta_bajo)) <= 1e-4)
        self.assertTrue(abs(na - (na + delta_bajo)) <= 1e-4)
        self.assertTrue(abs(ne - (ne + delta_bajo)) <= 1e-4)

    def test_tolerancia_1e4_sobre_se_propaga(self):
        """Un delta de 1e-3 supera la tolerancia (se propaga al hijo)."""
        cotas = self._cotas()
        nl, na, ne, npos, nrot = cotas["lateral_izquierdo"]
        delta_sobre = 1e-3
        self.assertTrue(abs(nl - (nl + delta_sobre)) > 1e-4)
        self.assertTrue(abs(na - (na + delta_sobre)) > 1e-4)
        self.assertTrue(abs(ne - (ne + delta_sobre)) > 1e-4)

    def test_mismo_valor_al_recaller(self):
        """execute() y onChanged() comparten la misma fuente: llamadas repetidas son deterministas."""
        a = self._cotas()
        b = self._cotas()
        self.assertEqual(a, b)

    def test_calcule_coincide_con_execute(self):
        """Las cotas devueltas coinciden con la aritmetica embebida en execute()."""
        cotas = self._cotas()
        # base_length = ancho - 2*espesor (base interno)
        self.assertAlmostEqual(cotas["base"][0], 600.0 - 2 * 18.0)
        # techo_pos_z = alto - espesor
        self.assertAlmostEqual(cotas["techo"][3][2], 720.0 - 18.0)
        # lateral derecho x = ancho - espesor
        self.assertAlmostEqual(cotas["lateral_derecho"][3][0], 600.0 - 18.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
