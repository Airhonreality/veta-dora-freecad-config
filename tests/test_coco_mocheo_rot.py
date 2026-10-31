# -*- coding: utf-8 -*-
"""Mocheos y pose con rotación (hipótesis rot_z=90 de la auditoría).

Contexto: el COCO convierte los mocheos de cada pieza a su marco local
restando sólo el origen de `caja_geometrica` (vdo_cad_coco.py, bucle de
divisiones_piezas). No aplica la rotación de la pose. Hoy la única pieza
con `rot_z=90` es el fondo, y el fondo no recibe mocheos, así que el
defecto está latente. Estos tests fijan:

  1. Que, en el COCO real, cada mocheo global corta la pieza en el sitio
     correcto del mundo (solape mundial 0).
  2. Que un PanelFeature con pose rot_z=90 aplica un mocheo dado en su
     marco local en el lugar correcto del mundo. Es el contrato que la
     conversión del COCO tendría que cumplir si algún día se asigna un
     mocheo a una pieza rotada.
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
import Part
from PySide import QtWidgets

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

import VDO.cad.objects.vdo_cad_coco as C
import VDO.cad.objects.vdo_cad_panel as P
from VDO.core.vdo_math_layout import Layout


def _layout_2x2():
    layout = Layout()
    layout.add_column()
    layout.add_row()
    return layout


def _caja_mundo(m):
    """Caja {x,y,z,w,h,d} en coordenadas de mundo -> sólido (w→X, h→Y, d→Z)."""
    return Part.makeBox(m["w"], m["h"], m["d"],
                        App.Vector(m["x"], m["y"], m["z"]))


class MocheoEnMundoTests(unittest.TestCase):
    def setUp(self):
        self.doc = App.newDocument("TestMocheoMundo")

    def tearDown(self):
        App.closeDocument(self.doc.Name)

    def test_mocheo_de_division_vertical_corta_en_el_mundo(self):
        """Techo reengrose: la división vertical recibe un mocheo en el
        punto donde la tira de techo la atraviesa. Tras montar el COCO, el
        sólido real no debe ocupar esa caja."""
        mod = {"activo": True, "orientacion": "paralela", "ancho": 50,
               "cara": "cara_b", "alineacion_profundidad": "frente",
               "modo_fabricacion": "independiente",
               "politica_repisa": "retroceder"}
        obj = C.make_coco({
            "nombre": "T", "alto": 720, "ancho": 600, "fondo_modulo": 580,
            "espesor": 18, "divisiones": _layout_2x2().dumps(),
            "reengroses": {"techo": mod}})
        self.doc.recompute()

        data = json.loads(obj.VDO_Paneles_JSON)
        piezas = [p for p in data if p.get("mocheos")]
        self.assertTrue(piezas, "el caso debe producir al menos un mocheo")

        comprobados = 0
        for p in piezas:
            hijos = [h for h in obj.Hijos if h.Label.endswith(p["nombre"])]
            self.assertTrue(hijos, f"sin PanelFeature para {p['nombre']}")
            hijo = hijos[0]
            for m in p["mocheos"]:
                solape = hijo.Shape.common(_caja_mundo(m)).Volume
                self.assertAlmostEqual(
                    solape, 0.0, places=3,
                    msg=f"{hijo.Label} conserva volumen en el mocheo {m}")
                comprobados += 1
        self.assertGreater(comprobados, 0)


class PanelRotado90Tests(unittest.TestCase):
    """Un PanelFeature con pose rot_z=90 recorta su mocheo local."""

    def setUp(self):
        self.doc = App.newDocument("TestMocheoRot90")

    def tearDown(self):
        App.closeDocument(self.doc.Name)

    def _panel(self, largo, ancho, espesor, mocheos):
        obj = self.doc.addObject("Part::FeaturePython", "PanelRot90")
        P.PanelFeature(obj)
        obj.Largo = largo
        obj.Ancho = ancho
        obj.Espesor = espesor
        obj.VDO_Orientacion = "vertical"
        obj.VDO_Mocheos_JSON = json.dumps(mocheos)
        return obj

    def test_mocheo_local_en_pose_rot90_corta_donde_toca(self):
        largo, ancho, espesor = 684.0, 571.0, 18.0
        # Esquina superior del panel en marco local: X=0..18, Y=0..50, Z=666..684
        mocheo = {"x": 0.0, "y": 0.0, "z": 666.0,
                  "w": 18.0, "h": 50.0, "d": 18.0}
        obj = self._panel(largo, ancho, espesor, [mocheo])

        # Pose del fondo del COCO: rotación 90 alrededor de Z.
        obj.Placement = App.Placement(
            App.Vector(582.0, 571.0, 18.0),
            App.Rotation(App.Vector(0, 0, 1), 90.0))
        self.doc.recompute()

        sin_mocheo = Part.makeBox(espesor, ancho, largo)
        volumen_esperado = sin_mocheo.Volume - 18.0 * 50.0 * 18.0
        self.assertFalse(obj.Shape.isNull())
        self.assertAlmostEqual(obj.Shape.Volume, volumen_esperado, places=3)

        # En el mundo, la caja del mocheo (ya transformada por la pose)
        # no debe contener material.
        caja_local = Part.makeBox(mocheo["w"], mocheo["h"], mocheo["d"])
        caja_local.Placement = App.Placement(
            App.Vector(mocheo["x"], mocheo["y"], mocheo["z"]),
            App.Rotation())
        caja_mundo = caja_local.copy()
        caja_mundo.Placement = obj.Placement.multiply(caja_local.Placement)
        self.assertAlmostEqual(
            obj.Shape.common(caja_mundo).Volume, 0.0, places=3)


if __name__ == "__main__":
    unittest.main()
