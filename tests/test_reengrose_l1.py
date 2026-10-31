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

import VDO.core.vdo_math_reengrose as R
import VDO.cad.objects.vdo_cad_panel as P
import VDO.cam.vdo_cam_cutlist as E

from PySide import QtWidgets
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
from VDO.ui.vdo_ui_panel_task import PanelTaskPanel


def _sin_solapes(shape):
    solidos = list(shape.Solids)
    for i in range(len(solidos)):
        for j in range(i + 1, len(solidos)):
            if solidos[i].common(solidos[j]).Volume > 1e-6:
                return False
    return True


class ReengroseL1Tests(unittest.TestCase):
    def setUp(self):
        self.doc = App.newDocument("TestReengroseL1")

    def tearDown(self):
        App.closeDocument(self.doc.Name)

    def crear(self, nombre, **reengrose):
        obj = P.crear_pieza({
            "nombre": nombre,
            "orientacion": "vertical",
            "largo": 600,
            "ancho": 400,
            "espesor": 18,
            "usar_params": False,
            "cantos": {"norte": "RIG"},
            "reengrose": dict({"activo": True}, **reengrose),
        })
        self.doc.recompute()
        return obj

    def test_independiente(self):
        obj = self.crear(
            "P_Ind", modo_fabricacion="independiente", ancho=70)
        self.assertTrue(obj.Shape.isValid())
        self.assertEqual(len(obj.Shape.Solids), 2)
        self.assertTrue(_sin_solapes(obj.Shape))
        piezas = E.extraer_piezas_panel(obj)
        self.assertEqual(len(piezas), 2)
        self.assertEqual(piezas[0]["operacion"], "Cantear por separado")

    def test_pacha_parcial(self):
        obj = self.crear(
            "P_Pacha", modo_fabricacion="pacha", ancho=70)
        self.assertTrue(obj.Shape.isValid())
        self.assertEqual(len(obj.Shape.Solids), 2)
        self.assertTrue(_sin_solapes(obj.Shape))
        piezas = E.extraer_piezas_panel(obj)
        self.assertEqual(piezas[0]["grupo_pacha"], "Pacha_P_Pacha")
        self.assertEqual(piezas[0]["cantos"]["norte"], "FX")
        self.assertEqual(piezas[0]["cantos_bloque"]["norte"], "RIG")

    def test_pacha_total(self):
        obj = self.crear(
            "P_Total", modo_fabricacion="pacha", alcance="total")
        self.assertTrue(obj.Shape.isValid())
        self.assertEqual(len(obj.Shape.Solids), 2)
        piezas = E.extraer_piezas_panel(obj)
        self.assertEqual(piezas[1]["largo"], 600.0)
        self.assertEqual(piezas[1]["ancho"], 400.0)

    def test_panel_viejo_sin_propiedades(self):
        obj = self.doc.addObject("Part::FeaturePython", "P_Viejo")
        P.PanelFeature(obj)
        obj.Largo = 300
        obj.Ancho = 200
        obj.Espesor = 18
        self.doc.recompute()
        self.assertTrue(obj.Shape.isValid())
        P.add_reengrose_props(obj)
        self.assertIn("VDO_Reengrose_Activo", obj.PropertiesList)

    def test_desde_objeto(self):
        obj = self.crear(
            "P_Json", modo_fabricacion="independiente",
            orientacion="transversal", ancho=55)
        mod = R.desde_objeto(obj)
        self.assertTrue(mod.activo)
        self.assertEqual(mod.orientacion, "transversal")
        self.assertEqual(mod.ancho, 55.0)

    def test_ui_tooltips_y_accept(self):
        obj = self.crear(
            "P_UI", modo_fabricacion="independiente", ancho=70)
        panel = PanelTaskPanel(obj=obj, auto_transaction=False)
        self.assertTrue(panel.chk_reengrose.isChecked())
        self.assertTrue(panel.chk_reengrose.toolTip())
        self.assertTrue(panel.spin_re_ancho.toolTip())
        panel.chk_reengrose.setChecked(False)
        self.assertFalse(panel.spin_re_ancho.isEnabled())
        panel.chk_reengrose.setChecked(True)
        self.assertTrue(panel.spin_re_ancho.isEnabled())
        panel.spin_re_ancho.setValue(55)
        self.assertTrue(panel.accept())
        self.doc.recompute()
        self.assertAlmostEqual(float(obj.VDO_Reengrose_Ancho), 55.0)

if __name__ == "__main__":
    # Protegido: a nivel de modulo este runner se ejecutaba al IMPORTAR el
    # archivo, y su SystemExit abortaba la coleccion entera de pytest
    # (INTERNALERROR dentro de FreeCADCmd).
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReengroseL1Tests)
    resultado = unittest.TextTestRunner(verbosity=2).run(suite)
    if not resultado.wasSuccessful():
        raise SystemExit(1)
