# -*- coding: utf-8 -*-
"""Zócalo dentro de alto (D59) y ranura de encastre (D2) en el COCO.

Decisiones de docs/05 §17 (arquitectura):
  - El zócalo va DENTRO de alto: la carcasa se calcula con alto - H_zocalo
    y se desplaza en Z; la altura total del mueble no cambia.
  - Ranura de encastre: operación de mecanizado en la base, profundidad
    espesor_base / 3, anchura espesor_division + 0.2. No altera el B-Rep.
  - La división suma la profundidad a su largo de corte (lista de corte).
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tests._entorno import HAY_FREECAD

if not HAY_FREECAD:
    pytest.skip("requiere FreeCAD real; ejecutar con FreeCADCmd",
                allow_module_level=True)

import FreeCAD as App
from PySide import QtWidgets

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

import VDO.cad.objects.vdo_cad_coco as C
import VDO.cam.vdo_cam_cutlist as E
from VDO.core.vdo_math_layout import Layout


def _layout_2x2():
    layout = Layout()
    layout.add_column()
    layout.add_row()
    return layout


def _hijos_con_forma(obj):
    return [h for h in obj.Hijos if h.Shape and not h.Shape.isNull()]


def _max_solape(piezas):
    maximo = 0.0
    for i in range(len(piezas)):
        for j in range(i + 1, len(piezas)):
            v = piezas[i].Shape.common(piezas[j].Shape).Volume
            maximo = max(maximo, v)
    return maximo


class ZocaloEncastreTests(unittest.TestCase):
    def setUp(self):
        self.doc = App.newDocument("TestZocaloEncastre")
        self.doc.UndoMode = 1

    def tearDown(self):
        try:
            App.closeDocument(self.doc.Name)
        except Exception:
            pass

    def _coco(self, chassis_base=None):
        obj = C.make_coco({
            "nombre": "Z", "alto": 720, "ancho": 600, "fondo_modulo": 580,
            "espesor": 18, "divisiones": _layout_2x2().dumps()})
        if chassis_base is not None:
            obj.touch()
            obj.VDO_Chassis_JSON = json.dumps({"base": chassis_base})
        self.doc.recompute()
        obj.Proxy.sincronizar_paneles_hijos(obj)
        self.doc.recompute()
        return obj

    def test_sin_configuracion_no_hay_zocalo(self):
        obj = self._coco()
        self.assertFalse([h for h in obj.Hijos if h.VDO_Rol == "zocalo"])
        base = [h for h in obj.Hijos if h.VDO_Rol == "base"][0]
        self.assertAlmostEqual(base.Shape.BoundBox.ZMin, 0.0, places=3)

    def test_zocalo_dentro_de_alto_sin_solapes(self):
        obj = self._coco({"estrategia": "zocalo", "altura": 100.0,
                          "separacion_frente": 50.0})
        zocalos = [h for h in obj.Hijos if h.VDO_Rol == "zocalo"]
        self.assertEqual(len(zocalos), 1)
        bb = zocalos[0].Shape.BoundBox
        self.assertAlmostEqual(bb.ZMin, 0.0, places=3)
        self.assertAlmostEqual(bb.ZMax, 100.0, places=3)
        self.assertAlmostEqual(bb.YMin, 50.0, places=3)   # retranqueo
        self.assertAlmostEqual(bb.XMin, 18.0, places=3)   # entre laterales
        self.assertAlmostEqual(bb.XMax, 582.0, places=3)
        self.assertAlmostEqual(_max_solape(_hijos_con_forma(obj)), 0.0,
                               places=3)

    def test_carcasa_se_eleva_y_altura_total_no_cambia(self):
        obj = self._coco({"estrategia": "zocalo", "altura": 100.0,
                          "separacion_frente": 50.0})
        base = [h for h in obj.Hijos if h.VDO_Rol == "base"][0]
        techo = [h for h in obj.Hijos if h.VDO_Rol == "techo"][0]
        self.assertAlmostEqual(base.Shape.BoundBox.ZMin, 100.0, places=3)
        self.assertAlmostEqual(techo.Shape.BoundBox.ZMax, 720.0, places=3)
        zmax = max(h.Shape.BoundBox.ZMax for h in _hijos_con_forma(obj))
        self.assertAlmostEqual(zmax, 720.0, places=3)

    def test_ranura_en_base_bajo_la_division(self):
        obj = self._coco({"estrategia": "zocalo", "altura": 100.0,
                          "separacion_frente": 50.0})
        base = [h for h in obj.Hijos if h.VDO_Rol == "base"][0]
        ranuras = json.loads(base.VDO_Mecanizados_JSON)
        self.assertEqual(len(ranuras), 1)
        r = ranuras[0]
        self.assertEqual(r["tipo"], "ranura")
        self.assertEqual(r["cara"], "superior")
        self.assertEqual(r["eje"], "y")
        self.assertAlmostEqual(r["profundidad"], 6.0, places=3)  # 18 / 3
        self.assertAlmostEqual(r["ancho"], 18.2, places=3)       # 18 + 0.2

    def test_division_suma_encastre_en_lista_de_corte(self):
        obj = self._coco({"estrategia": "zocalo", "altura": 100.0,
                          "separacion_frente": 50.0})
        division = [h for h in obj.Hijos
                    if h.VDO_Rol == "division_x"][0]
        self.assertAlmostEqual(division.VDO_Encastre_mm, 6.0, places=3)
        # La geometria sigue siendo la nominal (sin solape con la base).
        self.assertAlmostEqual(division.Shape.BoundBox.ZMin, 118.0, places=3)
        self.assertIn("Ranura", E._texto_mecanizados(
            [h for h in obj.Hijos if h.VDO_Rol == "base"][0]))
        largo_corte = E._datos_panel(division)[0]
        self.assertAlmostEqual(largo_corte, float(division.Largo) + 6.0, places=3)

if __name__ == "__main__":
    unittest.main()
