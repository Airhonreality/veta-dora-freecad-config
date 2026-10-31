# -*- coding: utf-8 -*-
"""Pruebas unitarias del motor de geometría del Tambor VDO."""

import importlib.util
import os
import sys
import unittest

try:
    _AQUI = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _AQUI = os.getcwd()
_RAIZ = os.path.dirname(_AQUI)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import pytest

from tests._entorno import HAY_FREECAD

if not HAY_FREECAD:
    pytest.skip("requiere FreeCAD real; ejecutar con FreeCADCmd",
                allow_module_level=True)

import VDO.cad.objects.vdo_cad_tambor as T


class GeometriaTamborTests(unittest.TestCase):
    """Pruebas de calcular_geometria_tambor."""

    def test_sandwich_valido(self):
        geo = T.calcular_geometria_tambor(
            largo=800, ancho=250, espesor_total=42,
            espesor_tapas=6, ancho_liston=30,
            tipo="panel_cerrado", modo_tenedor="abierto",
            costillas=2, diam_varilla=12)
        self.assertGreater(geo["h_liston"], 0)
        self.assertEqual(geo["h_liston"], 30.0)

    def test_valor_espesor_invalido(self):
        with self.assertRaises(ValueError):
            T.calcular_geometria_tambor(
                largo=800, ancho=250, espesor_total=10,
                espesor_tapas=6, ancho_liston=30)

    def test_panel_cerrado_incluye_trasero(self):
        geo = T.calcular_geometria_tambor(
            largo=800, ancho=250, espesor_total=42,
            espesor_tapas=6, ancho_liston=30,
            tipo="panel_cerrado", modo_tenedor="abierto",
            costillas=2, diam_varilla=12)
        nombres = [p["nombre"] for p in geo["piezas"]]
        self.assertIn("Liston_Trasero", nombres)

    def test_repisa_tenedor_abierto_sin_trasero(self):
        geo = T.calcular_geometria_tambor(
            largo=800, ancho=250, espesor_total=42,
            espesor_tapas=6, ancho_liston=30,
            tipo="repisa_tenedor", modo_tenedor="abierto",
            prof_tenedor=140, costillas=2, diam_varilla=12)
        nombres = [p["nombre"] for p in geo["piezas"]]
        self.assertNotIn("Liston_Trasero", nombres)

    def test_cantidad_costillas(self):
        geo = T.calcular_geometria_tambor(
            largo=800, ancho=250, espesor_total=42,
            espesor_tapas=6, ancho_liston=30,
            tipo="panel_cerrado", modo_tenedor="abierto",
            costillas=3, diam_varilla=12)
        costillas = [s for s in geo["solidos"] if s["nombre"].startswith("Costilla_")]
        self.assertEqual(len(costillas), 3)

    def test_taladrado_incluye_liston_trasero(self):
        geo = T.calcular_geometria_tambor(
            largo=800, ancho=250, espesor_total=42,
            espesor_tapas=6, ancho_liston=30,
            tipo="repisa_tenedor", modo_tenedor="taladrado",
            costillas=2, diam_varilla=12)
        nombres = [s["nombre"] for s in geo["solidos"]]
        self.assertIn("Liston_Trasero_Taladrado", nombres)
        taladrados = [s for s in geo["solidos"] if s.get("taladros_tenedor")]
        self.assertEqual(len(taladrados), 1)


if __name__ == "__main__":
    unittest.main()
