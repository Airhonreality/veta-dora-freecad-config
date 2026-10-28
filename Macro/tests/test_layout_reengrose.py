import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import vdo_reengrose as R
from vdo_layout import Layout, resolve_layout


class LayoutReengroseTests(unittest.TestCase):
    def setUp(self):
        self.layout = Layout()
        self.layout.add_column()
        self.layout.add_row()

    def test_sin_reengrose(self):
        res = resolve_layout(self.layout, 564, 684, 18)
        self.assertAlmostEqual(res.columns[0].size, 273.0)
        self.assertAlmostEqual(res.columns[0].clear_size, 273.0)
        self.assertAlmostEqual(res.columns[1].start, 291.0)
        resinas = [p for p in res.pieces if p.axis == "Y"]
        self.assertAlmostEqual(resinas[0].w, 273.0)

    def test_division_izquierda_reduce_vano(self):
        mod = R.ReengroseModifier({
            "activo": True, "ancho": 50, "cara": "cara_b",
            "orientacion": "paralela"})
        res = resolve_layout(
            self.layout, 564, 684, 18,
            reengroses={"division_x:x2": mod})
        self.assertAlmostEqual(res.columns[0].size, 273.0)
        self.assertAlmostEqual(res.columns[0].clear_size, 255.0)
        self.assertAlmostEqual(res.columns[1].clear_size, 273.0)
        self.assertAlmostEqual(res.columns[0].extra_der, 18.0)
        vertical = [p for p in res.pieces if p.axis == "X"][0]
        self.assertAlmostEqual(vertical.x, 273.0)

    def test_division_derecha_reduce_vano(self):
        mod = R.ReengroseModifier({
            "activo": True, "ancho": 50, "cara": "cara_a",
            "orientacion": "paralela"})
        res = resolve_layout(
            self.layout, 564, 684, 18,
            reengroses={"division_x:x2": mod})
        self.assertAlmostEqual(res.columns[0].clear_size, 273.0)
        self.assertAlmostEqual(res.columns[1].clear_size, 255.0)

    def test_ambos_lados(self):
        mod = R.ReengroseModifier({
            "activo": True, "ancho": 50, "cara": "ambos",
            "orientacion": "paralela"})
        res = resolve_layout(
            self.layout, 564, 684, 18,
            reengroses={"division_x:x2": mod})
        self.assertAlmostEqual(res.columns[0].clear_size, 255.0)
        self.assertAlmostEqual(res.columns[1].clear_size, 255.0)

    def test_lateral_izquierdo(self):
        mod = R.ReengroseModifier({
            "activo": True, "ancho": 50, "cara": "cara_a",
            "orientacion": "paralela"})
        res = resolve_layout(
            self.layout, 564, 684, 18,
            reengroses={"lateral_izquierdo": mod})
        self.assertAlmostEqual(res.columns[0].clear_start, 18.0)
        self.assertAlmostEqual(res.columns[0].clear_size, 255.0)

    def test_repisa_nominal_para_mocheo(self):
        mod = R.ReengroseModifier({
            "activo": True, "ancho": 50, "cara": "cara_b",
            "orientacion": "paralela"})
        res = resolve_layout(
            self.layout, 564, 684, 18,
            reengroses={"division_x:x2": mod})
        repisas = [p for p in res.pieces if p.axis == "Y"]
        self.assertAlmostEqual(repisas[0].w, 273.0)
        self.assertAlmostEqual(repisas[1].w, 273.0)


if __name__ == "__main__":
    unittest.main()
