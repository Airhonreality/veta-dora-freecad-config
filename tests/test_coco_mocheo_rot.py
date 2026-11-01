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


class ConversionConPoseTests(unittest.TestCase):
    """La conversión global -> marco de pieza deshace la pose completa.

    Contrato: si una pieza se coloca con Placement = pos + rot_z, un mocheo
    global convertido con `_mocheos_locales(..., pos, rot_z)` debe recortar
    exactamente el volumen que ocupa en el mundo.
    """

    def setUp(self):
        self.doc = App.newDocument("TestConversionPose")

    def tearDown(self):
        App.closeDocument(self.doc.Name)

    def test_caja_rot90_se_invierte_exacta(self):
        pos, rot = [582.0, 571.0, 18.0], 90.0
        local = {"x": 0.0, "y": 0.0, "z": 666.0, "w": 18.0, "h": 50.0,
                 "d": 18.0}
        # Caja del mundo = caja local colocada con la pose.
        s = Part.makeBox(local["w"], local["h"], local["d"],
                         App.Vector(local["x"], local["y"], local["z"]))
        s.Placement = App.Placement(App.Vector(*pos),
                                    App.Rotation(App.Vector(0, 0, 1), rot))
        bb = s.BoundBox
        mundo = {"x": bb.XMin, "y": bb.YMin, "z": bb.ZMin,
                 "w": bb.XLength, "h": bb.YLength, "d": bb.ZLength}

        (salida,) = C._mocheos_locales([mundo], pos, rot)
        for clave, valor in local.items():
            self.assertAlmostEqual(salida[clave], valor, places=6,
                                   msg=f"componente {clave}")

    def test_prisma_rot270_normaliza_sentido_negativo(self):
        pos, rot = [0.0, 571.0, 18.0], 270.0
        # Prisma global: polígono en la cara de mínimo Y del mundo, eje y.
        y_ini = pos[1] - 18.0
        prisma = {"puntos": [[0.0, y_ini, 684.0], [50.0, y_ini, 684.0],
                             [50.0, y_ini, 702.0], [0.0, y_ini, 702.0]],
                  "eje": "y", "largo": 18.0}
        (salida,) = C._mocheos_locales([prisma], pos, rot)
        self.assertEqual(salida["eje"], "x")
        self.assertAlmostEqual(salida["largo"], 18.0, places=6)
        xs = sorted({round(p[0], 6) for p in salida["puntos"]})
        self.assertEqual(xs, [0.0])  # polígono en la cara local x=0

    def test_pieza_rot270_recibe_mocheo_y_queda_limpia_en_mundo(self):
        largo, ancho, espesor = 684.0, 571.0, 18.0
        pos, rot = [0.0, 571.0, 18.0], 270.0
        y_ini = pos[1] - espesor
        prisma_mundo = {"puntos": [[0.0, y_ini, 684.0], [50.0, y_ini, 684.0],
                                   [50.0, y_ini, 702.0], [0.0, y_ini, 702.0]],
                        "eje": "y", "largo": espesor}
        (local,) = C._mocheos_locales([prisma_mundo], pos, rot)

        obj = self.doc.addObject("Part::FeaturePython", "PanelRot270")
        P.PanelFeature(obj)
        obj.Largo, obj.Ancho, obj.Espesor = largo, ancho, espesor
        obj.VDO_Orientacion = "vertical"
        obj.VDO_Mocheos_JSON = json.dumps([local])
        obj.Placement = App.Placement(App.Vector(*pos),
                                      App.Rotation(App.Vector(0, 0, 1), rot))
        self.doc.recompute()

        # Volumen del mocheo en el mundo, recortado por la pieza original.
        mundo = Part.Face(Part.makePolygon(
            [App.Vector(*p) for p in prisma_mundo["puntos"]]
            + [App.Vector(*prisma_mundo["puntos"][0])])).extrude(
            App.Vector(0, espesor, 0))
        sin_mocheo = Part.makeBox(espesor, ancho, largo)
        sin_mocheo.Placement = obj.Placement
        volumen_quitado = sin_mocheo.common(mundo).Volume
        self.assertGreater(volumen_quitado, 0.0)
        self.assertAlmostEqual(obj.Shape.common(mundo).Volume, 0.0, places=3)
        self.assertAlmostEqual(obj.Shape.Volume,
                               sin_mocheo.Volume - volumen_quitado, places=3)


if __name__ == "__main__":
    unittest.main()
