# -*- coding: utf-8 -*-
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import FreeCAD as App
from PySide import QtWidgets

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

import vdo_coco_core as C
import vdo_coco_spaces as S
from vdo_coco_unified_task import CocoUnifiedTaskPanel
from vdo_layout import Layout


def max_common(shape):
    solidos = list(shape.Solids)
    maximo = 0.0
    for i in range(len(solidos)):
        for j in range(i + 1, len(solidos)):
            maximo = max(maximo, solidos[i].common(solidos[j]).Volume)
    return maximo


def layout_2x2():
    layout = Layout()
    layout.add_column()
    layout.add_row()
    return layout


def mod(**cambios):
    base = {
        "activo": True,
        "orientacion": "paralela",
        "ancho": 50,
        "cara": "cara_b",
        "alineacion_profundidad": "frente",
        "modo_fabricacion": "independiente",
    }
    base.update(cambios)
    return base


class CocoReengroseAvanzadoTests(unittest.TestCase):
    def setUp(self):
        self.doc = App.newDocument("TestCocoAvanzado")

    def tearDown(self):
        App.closeDocument(self.doc.Name)

    def _coco(self, reengroses, nombre="C"):
        obj = C.make_coco({
            "nombre": nombre,
            "alto": 720,
            "ancho": 600,
            "fondo_modulo": 580,
            "espesor": 18,
            "divisiones": layout_2x2().dumps(),
            "reengroses": reengroses,
        })
        self.doc.recompute()
        return obj

    @staticmethod
    def _tiras_en_banda(shape, zmin, zmax, ymax=60.0):
        encontradas = []
        for solido in shape.Solids:
            caja = solido.BoundBox
            if (abs(caja.ZMin - zmin) < 1.0
                    and abs(caja.ZMax - zmax) < 1.0
                    and caja.YMin < 1.0 and caja.YMax <= ymax):
                encontradas.append(solido)
        return encontradas

    def test_repisa_retranqueada_ancla_cara_real(self):
        obstaculo = {
            "clave": "lateral_izquierdo_tira01",
            "host": "lateral_izquierdo",
            "x": 18.0, "y": 0.0, "z": 18.0,
            "w": 18.0, "h": 50.0, "d": 684.0,
            "modo_choque": "retroceso",
        }
        reengroses = {"division_y:y2_x1": mod()}
        shapes, _resumen, piezas, resuelto = S.generar_divisiones_matriz(
            layout_2x2().dumps(), 600, 720, 580, 18,
            reengroses=reengroses, obstaculos=[obstaculo])
        self.assertTrue(shapes)
        tiras = [
            t for t in resuelto.tiras
            if t.get("host") == "division_y:y2_x1"]
        self.assertTrue(tiras)
        tira = tiras[0]
        self.assertAlmostEqual(tira["y"], 50.0)
        self.assertAlmostEqual(tira["h"], 50.0)
        self.assertAlmostEqual(tira["anclaje_y"]["frente"], 50.0)
        repisa = [
            p for p in piezas
            if p.get("rol") == "division_y"
            and p.get("clave_reengrose") == "division_y:y2_x1"]
        self.assertTrue(repisa)
        self.assertAlmostEqual(repisa[0]["caja_geometrica"]["y"], 50.0)

    def test_techo_reengrose_division_vertical(self):
        obj = self._coco({"techo": mod()}, "C_TechoDiv")
        self.assertTrue(obj.Shape.isValid())
        self.assertAlmostEqual(max_common(obj.Shape), 0.0)
        data = json.loads(obj.VDO_Paneles_JSON)
        divisiones = [
            p for p in data
            if p.get("rol") == "division_x" and p.get("mocheos")]
        self.assertTrue(divisiones)
        moche = divisiones[0]["mocheos"][0]
        self.assertAlmostEqual(moche["w"], 19.0)
        self.assertAlmostEqual(moche["d"], 18.0)
        tiras = self._tiras_en_banda(obj.Shape, 684.0, 702.0)
        self.assertEqual(len(tiras), 1)
        self.assertGreater(tiras[0].BoundBox.XLength, 500.0)

    def test_esquina_techo_lateral_vertical_domina(self):
        obj = self._coco({
            "techo": mod(),
            "lateral_izquierdo": mod(cara="cara_a"),
        }, "C_EsquinaV")
        self.assertTrue(obj.Shape.isValid())
        self.assertAlmostEqual(max_common(obj.Shape), 0.0)
        laterales = [
            s for s in obj.Shape.Solids
            if abs(s.BoundBox.XMin - 18.0) < 1.0
            and abs(s.BoundBox.XMax - 36.0) < 1.0
            and s.BoundBox.ZMax > 690.0]
        self.assertEqual(len(laterales), 1)
        self.assertAlmostEqual(laterales[0].BoundBox.ZMin, 18.0)
        self.assertAlmostEqual(laterales[0].BoundBox.ZMax, 702.0)
        techo = self._tiras_en_banda(obj.Shape, 684.0, 702.0)
        self.assertEqual(len(techo), 1)
        self.assertGreaterEqual(techo[0].BoundBox.XMin, 35.0)

    def test_esquina_techo_lateral_horizontal_domina(self):
        obj = self._coco({
            "techo": mod(),
            "lateral_izquierdo": mod(
                cara="cara_a", prioridad_encuentro_tiras="horizontal_domina"),
        }, "C_EsquinaH")
        self.assertTrue(obj.Shape.isValid())
        self.assertAlmostEqual(max_common(obj.Shape), 0.0)
        laterales = [
            s for s in obj.Shape.Solids
            if abs(s.BoundBox.XMin - 18.0) < 1.0
            and abs(s.BoundBox.XMax - 36.0) < 1.0
            and s.BoundBox.ZMin < 20.0]
        self.assertEqual(len(laterales), 1)
        self.assertAlmostEqual(laterales[0].BoundBox.ZMax, 684.0)
        techo = self._tiras_en_banda(obj.Shape, 684.0, 702.0)
        self.assertEqual(len(techo), 1)
        self.assertLessEqual(techo[0].BoundBox.XMin, 19.0)

    def test_interrumpir_tira_en_division(self):
        obj = self._coco({
            "techo": mod(comportamiento_choque_nucleo="interrumpir_tira"),
        }, "C_Interrumpir")
        self.assertTrue(obj.Shape.isValid())
        self.assertAlmostEqual(max_common(obj.Shape), 0.0)
        data = json.loads(obj.VDO_Paneles_JSON)
        divisiones = [
            p for p in data
            if p.get("rol") == "division_x" and p.get("mocheos")]
        self.assertFalse(divisiones)
        tiras = self._tiras_en_banda(obj.Shape, 684.0, 702.0)
        self.assertEqual(len(tiras), 2)
        rangos = sorted(
            (round(t.BoundBox.XMin, 3), round(t.BoundBox.XMax, 3))
            for t in tiras)
        self.assertAlmostEqual(rangos[0][0], 18.0)
        self.assertAlmostEqual(rangos[0][1], 291.0)
        self.assertAlmostEqual(rangos[1][0], 309.0)
        self.assertAlmostEqual(rangos[1][1], 582.0)

    def test_ui_contextual_modos_nuevos(self):
        obj = self._coco({}, "C_UINuevo")
        panel = CocoUnifiedTaskPanel(obj=obj, auto_transaction=False)
        editor = panel.editor_divisiones
        item = editor._items_by_key.get(("elemento", "division_x:x2"))
        self.assertIsNotNone(item)
        editor.tree.setCurrentItem(item)
        idx = editor.combo_elemento_reengrose.findData("division_x:x2")
        self.assertGreaterEqual(idx, 0)
        editor.combo_elemento_reengrose.setCurrentIndex(idx)
        editor.chk_reengrose.setChecked(True)
        editor._set_combo_data(editor.combo_re_politica, "mocheo")
        editor._set_combo_data(
            editor.combo_re_prioridad, "inglete_45")
        editor._on_reengrose_changed()
        self.assertTrue(panel.accept())
        self.doc.recompute()
        data = json.loads(obj.VDO_Reengrose_JSON)
        self.assertEqual(
            data["division_x:x2"]["comportamiento_choque_nucleo"],
            "mocheo")
        self.assertEqual(
            data["division_x:x2"]["prioridad_encuentro_tiras"],
            "inglete_45")
        self.assertAlmostEqual(max_common(obj.Shape), 0.0)

    def test_inglete_45_sin_solapes(self):
        obj = self._coco({
            "techo": mod(),
            "lateral_izquierdo": mod(
                cara="cara_a", prioridad_encuentro_tiras="inglete_45"),
        }, "C_Inglete")
        self.assertTrue(obj.Shape.isValid())
        self.assertAlmostEqual(max_common(obj.Shape), 0.0)


suite = unittest.defaultTestLoader.loadTestsFromTestCase(
    CocoReengroseAvanzadoTests)
resultado = unittest.TextTestRunner(verbosity=2).run(suite)
if not resultado.wasSuccessful():
    raise SystemExit(1)
