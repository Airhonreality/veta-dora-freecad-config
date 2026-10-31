import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tests._entorno import HAY_FREECAD

if not HAY_FREECAD:
    pytest.skip("requiere FreeCAD real; ejecutar con FreeCADCmd",
                allow_module_level=True)

import VDO.core.vdo_math_reengrose as R


class ReengrosePureTests(unittest.TestCase):
    def setUp(self):
        self.panel = {
            "nombre": "P", "largo": 600.0, "ancho": 400.0,
            "espesor": 18.0, "cantos": {"norte": "RIG"},
        }

    def test_defaults_and_validation(self):
        mod = R.ReengroseModifier()
        self.assertFalse(mod.activo)
        self.assertEqual(mod.orientacion, "paralela")
        self.assertEqual(mod.ancho, 70.0)
        self.assertIsNone(mod.espesor)
        with self.assertRaises(R.ReengroseError):
            R.ReengroseModifier({"ancho": 0})
        with self.assertRaises(R.ReengroseError):
            R.ReengroseModifier({"orientacion": "diagonal"})

    def test_paralela_cara_a(self):
        mod = R.ReengroseModifier({
            "activo": True, "ancho": 70, "cara": "cara_a",
            "alineacion_profundidad": "frente"})
        geo = R.calcular_geometria_reengrose(self.panel, mod)
        ref = geo["refuerzos"][0]
        self.assertEqual((ref["largo"], ref["ancho"]), (600.0, 70.0))
        self.assertEqual((ref["x"], ref["y"], ref["z"]), (0.0, 0.0, 18.0))

    def test_paralela_fondo_y_cara_b(self):
        mod = R.ReengroseModifier({
            "activo": True, "ancho": 70, "cara": "cara_b",
            "alineacion_profundidad": "fondo"})
        ref = R.calcular_geometria_reengrose(self.panel, mod)["refuerzos"][0]
        self.assertEqual((ref["y"], ref["z"]), (330.0, -18.0))

    def test_transversal(self):
        mod = R.ReengroseModifier({
            "activo": True, "ancho": 70, "orientacion": "transversal"})
        ref = R.calcular_geometria_reengrose(self.panel, mod)["refuerzos"][0]
        self.assertEqual((ref["largo"], ref["ancho"]), (400.0, 70.0))
        self.assertEqual(ref["x"], 265.0)

    def test_pacha_total(self):
        mod = R.ReengroseModifier({
            "activo": True, "modo_fabricacion": "pacha",
            "alcance": "total"})
        ref = R.calcular_geometria_reengrose(self.panel, mod)["refuerzos"][0]
        self.assertEqual((ref["largo"], ref["ancho"]), (600.0, 400.0))

    def test_politica_cantos(self):
        indep = R.ReengroseModifier({
            "activo": True, "modo_fabricacion": "independiente"})
        plan = R.resolver_politica_cantos(self.panel, indep)
        self.assertEqual(plan["base"]["norte"], "RIG")
        self.assertEqual(plan["tira"]["norte"], "RIG")
        pacha = R.ReengroseModifier({
            "activo": True, "modo_fabricacion": "pacha"})
        plan = R.resolver_politica_cantos(self.panel, pacha)
        self.assertEqual(plan["base"]["norte"], "FX")
        self.assertEqual(plan["bloque"]["norte"], "RIG")

    def test_colision_y_mocheo(self):
        repisa = {"x": 0, "y": 0, "z": 0, "w": 500, "h": 400, "d": 18}
        choque = {"x": 480, "y": 0, "z": 0, "w": 18, "h": 70, "d": 18}
        libre = {"x": 100, "y": 0, "z": 40, "w": 18, "h": 70, "d": 18}
        self.assertIsNone(R.generar_mocheo_repisa(repisa, libre))
        retro = R.generar_mocheo_repisa(repisa, choque)
        self.assertEqual(retro["modo"], "retroceder")
        self.assertEqual(retro["recorte_x"], 18.0)
        moche = R.generar_mocheo_repisa(repisa, choque, "mochear")
        self.assertEqual(moche["modo"], "mochear")
        self.assertEqual(moche["moche"]["w"], 18.0)
        self.assertEqual(moche["moche"]["h"], 70.0)

    def test_vano_neto(self):
        resultado = R.calcular_vano_neto_con_reengrose(
            {"ancho": 500, "alto": 700},
            {"lado_afectado": "izquierda", "espesor_extra": 18})
        self.assertEqual(resultado["ancho"], 482.0)
        self.assertEqual(resultado["desplazamiento_x"], 18.0)

    def test_despiece_pacha(self):
        mod = R.ReengroseModifier({
            "activo": True, "modo_fabricacion": "pacha"})
        piezas = R.despiece_panel("P", 600, 400, 18, mod, cantos={})
        self.assertEqual(len(piezas), 2)
        self.assertEqual(piezas[0]["grupo_pacha"], "Pacha_P")
        self.assertEqual(piezas[0]["cantos"]["norte"], "FX")
        self.assertEqual(piezas[0]["cantos_bloque"]["norte"], "RIG")


if __name__ == "__main__":
    unittest.main()
