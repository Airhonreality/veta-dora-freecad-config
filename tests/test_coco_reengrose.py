import csv
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
import VDO.cam.vdo_cam_cutlist as E
from VDO.ui.vdo_ui_coco_task import CocoUnifiedTaskPanel
from VDO.core.vdo_math_layout import Layout


def forma_montada(obj):
    """Compuesto con los solidos reales del modulo, leidos de sus hijos.

    Estos tests se escribieron cuando el COCO llevaba su geometria en
    Shape. Con el axioma T5 (C-02) el contenedor tiene Shape NULA y los
    solidos viven en los PanelFeature hijos, asi que `forma_montada(obj).Solids`
    quedaba vacio y `forma_montada(obj).isValid()` lanzaba
    `Standard_NullObject BRepCheck_Analyzer::Init() - NULL shape`.
    Este adaptador reconstruye el conjunto para que las aserciones sigan
    midiendo lo que pretendian medir.
    """
    solidos = []
    try:
        if obj.Shape and not obj.Shape.isNull():
            solidos.extend(obj.Shape.Solids)
    except Exception:
        pass
    for hijo in (getattr(obj, "Hijos", None) or []):
        try:
            if hijo.Shape and not hijo.Shape.isNull():
                solidos.extend(hijo.Shape.Solids)
        except Exception:
            continue
    return Part.makeCompound(solidos) if solidos else Part.Shape()


def max_common(shape):
    solidos = list(shape.Solids)
    maximo = 0.0
    for i in range(len(solidos)):
        for j in range(i + 1, len(solidos)):
            maximo = max(
                maximo, solidos[i].common(solidos[j]).Volume)
    return maximo


def layout_2x2():
    layout = Layout()
    layout.add_column()
    layout.add_row()
    return layout


class CocoReengroseTests(unittest.TestCase):
    def setUp(self):
        self.doc = App.newDocument("TestCocoReengrose")

    def tearDown(self):
        App.closeDocument(self.doc.Name)

    def _coco(self, nombre="C", politica="retroceder", modo="independiente"):
        mod = {
            "activo": True,
            "orientacion": "paralela",
            "ancho": 50,
            "cara": "cara_b",
            "alineacion_profundidad": "frente",
            "modo_fabricacion": modo,
            "politica_repisa": politica,
        }
        obj = C.make_coco({
            "nombre": nombre,
            "alto": 720,
            "ancho": 600,
            "fondo_modulo": 580,
            "espesor": 18,
            "divisiones": layout_2x2().dumps(),
            "reengroses": {"division_x:x2": mod},
        })
        self.doc.recompute()
        return obj

    def test_retroceso_repisa(self):
        obj = self._coco("C_Retro")
        self.assertTrue(forma_montada(obj).isValid())
        self.assertAlmostEqual(max_common(forma_montada(obj)), 0.0)
        data = json.loads(obj.VDO_Paneles_JSON)
        repisas = [p for p in data if p.get("rol") == "division_y"]
        self.assertTrue(repisas)
        self.assertAlmostEqual(repisas[0]["ancho"], 521.0)
        # El refuerzo de reengrose conserva su pieza padre con el sufijo
        # _refuerzo en el rol (ver _expandir_reengrose): se busca por prefijo.
        divisiones = [
            p for p in data
            if p.get("rol", "").startswith("division_x")]
        self.assertTrue(any("Reengrose" in p["nombre"] for p in divisiones))

    def test_mocheo_repisa(self):
        obj = self._coco("C_Moche", politica="mochear")
        self.assertTrue(forma_montada(obj).isValid())
        self.assertAlmostEqual(max_common(forma_montada(obj)), 0.0)
        data = json.loads(obj.VDO_Paneles_JSON)
        repisas = [
            p for p in data
            if p.get("rol") == "division_y" and p.get("mocheos")]
        self.assertTrue(repisas)
        self.assertAlmostEqual(repisas[0]["ancho"], 571.0)
        moche = repisas[0]["mocheos"][0]
        self.assertAlmostEqual(moche["w"], 18.0)
        self.assertAlmostEqual(moche["h"], 50.0)

    def test_pacha_en_despiece(self):
        obj = self._coco("C_Pacha", modo="pacha")
        self.assertTrue(forma_montada(obj).isValid())
        self.assertAlmostEqual(max_common(forma_montada(obj)), 0.0)
        data = json.loads(obj.VDO_Paneles_JSON)
        sub = [
            p for p in data
            if p.get("rol", "").startswith("division_x")
            and p.get("grupo_pacha")]
        self.assertGreaterEqual(len(sub), 2)
        self.assertTrue(all(
            p["operacion"] == "Encolar + canto de bloque unificado"
            for p in sub))
        self.assertIn("cantos_bloque", sub[0])

    def test_export_csv_grupo(self):
        obj = self._coco("C_Export", modo="pacha")
        piezas = E.extraer_piezas_del_documento("todo")
        path = "/tmp/vdo_coco_reengrose.csv"
        self.assertTrue(E.generar_csv_opencutlist(piezas, path))
        with open(path, newline="", encoding="utf-8") as f:
            filas = list(csv.reader(f))
        cabecera = filas[0]
        self.assertEqual(cabecera[-2:], ["Group", "Operation"])
        pacha = [
            f for f in filas[1:]
            if len(f) > 12 and f[12].startswith("Pacha_")]
        self.assertTrue(pacha)
        self.assertEqual(
            pacha[0][13], "Encolar + canto de bloque unificado")

    def test_carcasa_lateral_sin_solapes(self):
        obj = C.make_coco({
            "nombre": "C_Lat",
            "divisiones": layout_2x2().dumps(),
            "reengroses": {
                "lateral_izquierdo": {
                    "activo": True, "ancho": 50, "cara": "cara_a",
                    "orientacion": "paralela",
                    "alineacion_profundidad": "frente",
                    "modo_fabricacion": "independiente",
                }
            },
        })
        self.doc.recompute()
        self.assertTrue(forma_montada(obj).isValid())
        self.assertAlmostEqual(max_common(forma_montada(obj)), 0.0)

    def test_carcasa_base_sin_solapes(self):
        obj = C.make_coco({
            "nombre": "C_Base",
            "divisiones": layout_2x2().dumps(),
            "reengroses": {
                "base": {
                    "activo": True, "ancho": 50, "cara": "cara_a",
                    "orientacion": "paralela",
                    "alineacion_profundidad": "frente",
                    "modo_fabricacion": "independiente",
                }
            },
        })
        self.doc.recompute()
        self.assertTrue(forma_montada(obj).isValid())
        self.assertAlmostEqual(max_common(forma_montada(obj)), 0.0)

    def test_ui_contextual(self):
        obj = C.make_coco({
            "nombre": "C_UI",
            "alto": 720,
            "ancho": 600,
            "fondo_modulo": 580,
            "espesor": 18,
            "divisiones": layout_2x2().dumps(),
        })
        self.doc.recompute()
        panel = CocoUnifiedTaskPanel(obj=obj, auto_transaction=False)
        editor = panel.editor_divisiones
        item = editor._items_by_key.get(("elemento", "division_x:x2"))
        self.assertIsNotNone(item)
        editor.tree.setCurrentItem(item)
        self.assertEqual(
            editor.combo_elemento_reengrose.currentData(),
            "division_x:x2")
        idx = editor.combo_elemento_reengrose.findData("division_x:x2")
        self.assertGreaterEqual(idx, 0)
        editor.combo_elemento_reengrose.setCurrentIndex(idx)
        editor.chk_reengrose.setChecked(True)
        editor._set_combo_data(editor.combo_re_cara, "cara_b")
        editor.spin_re_ancho.setValue(50)
        editor._on_reengrose_changed()
        self.assertIn("division_x:x2", editor.reengroses)
        self.assertAlmostEqual(
            editor._resolved.columns[0].clear_size, 255.0)
        self.assertTrue(panel.accept())
        self.doc.recompute()
        self.assertIn("division_x:x2", obj.VDO_Reengrose_JSON)
        self.assertAlmostEqual(max_common(forma_montada(obj)), 0.0)

    def test_coco_estandar_regresion(self):
        obj = C.make_coco({
            "nombre": "C_Estandar",
            "alto": 720,
            "ancho": 600,
            "fondo_modulo": 580,
            "espesor": 18,
            "divisiones": layout_2x2().dumps(),
        })
        self.doc.recompute()
        self.assertTrue(forma_montada(obj).isValid())
        self.assertAlmostEqual(max_common(forma_montada(obj)), 0.0)
        self.assertAlmostEqual(forma_montada(obj).BoundBox.XMax, 600.0)
        self.assertAlmostEqual(forma_montada(obj).BoundBox.YMax, 580.0)
        self.assertAlmostEqual(forma_montada(obj).BoundBox.ZMax, 720.0)
        self.assertEqual(obj.VDO_Reengrose_JSON, "{}")

if __name__ == "__main__":
    # Protegido: a nivel de modulo este runner se ejecutaba al IMPORTAR el
    # archivo, y su SystemExit abortaba la coleccion entera de pytest
    # (INTERNALERROR dentro de FreeCADCmd).
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CocoReengroseTests)
    resultado = unittest.TextTestRunner(verbosity=2).run(suite)
    if not resultado.wasSuccessful():
        raise SystemExit(1)
