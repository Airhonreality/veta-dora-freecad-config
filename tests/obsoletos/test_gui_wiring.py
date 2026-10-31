# -*- coding: utf-8 -*-
"""
tests/test_gui_wiring.py
Verificación de cableado definitivo de entrada y cierre de cadena en FreeCAD GUI.
"""

import os
import sys
import json
import unittest

import FreeCAD as App
try:
    import FreeCADGui as Gui
except ImportError:
    Gui = None

from PySide import QtCore, QtWidgets

from vdo_universal_inspector import VDOUniversalInspectorWidget, obtener_o_crear_dock_inspector
from VDO.ui.vdo_ui_chassis_widget import VDOChassisControllerWidget
from VDO.ui.vdo_ui_coco_task import CocoUnifiedTaskPanel
from VDO.cad.objects.vdo_cad_coco import make_coco, ViewProviderCoco
from VDO.cad.views.vdo_cad_view_base import enfocar_inspector_universal, abrir_panel_objeto


class TestGuiWiring(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Asegurar QApplication
        cls.app = QtWidgets.QApplication.instance()
        if cls.app is None:
            cls.app = QtWidgets.QApplication(sys.argv)

    def setUp(self):
        self.doc_name = "DocWiringVDO"
        try:
            App.closeDocument(self.doc_name)
        except Exception:
            pass
        self.doc = App.newDocument(self.doc_name)

    def tearDown(self):
        try:
            App.closeDocument(self.doc_name)
        except Exception:
            pass

    def test_extirpacion_combos_planos_en_coco_task(self):
        """Verifica que CocoUnifiedTaskPanel no tenga combos viejos y use VDOChassisControllerWidget."""
        coco = make_coco({"nombre": "CocoTestWiring", "alto": 720, "ancho": 600, "fondo": 500})
        self.doc.recompute()

        panel = CocoUnifiedTaskPanel(obj=coco, auto_transaction=False)

        # 1. Combos viejos extirpados
        self.assertFalse(hasattr(panel, "combo_tapa"), "combo_tapa debe ser extirpado")
        self.assertFalse(hasattr(panel, "combo_base"), "combo_base debe ser extirpado")
        self.assertFalse(hasattr(panel, "chk_fondo"), "chk_fondo debe ser extirpado")
        self.assertFalse(hasattr(panel, "spin_calibre"), "spin_calibre debe ser extirpado")

        # 2. VDOChassisControllerWidget presente
        self.assertTrue(hasattr(panel, "box_chassis"), "Debe tener box_chassis")
        self.assertIsInstance(panel.box_chassis, VDOChassisControllerWidget)

        # 3. Interacción reactiva de chasis
        cfg_nueva = {
            "caras": {
                "superior": {"activa": True, "tipo": "estructural"},
                "inferior": {"activa": True, "tipo": "estructural"},
                "izquierda": {"activa": True, "tipo": "estructural"},
                "derecha": {"activa": True, "tipo": "estructural"},
                "fondo": {"activa": False, "tipo": "ranurado_5mm"},
            },
            "encuentros": {
                "superior_izq": "lateral_domina",
                "superior_der": "lateral_domina",
                "inferior_izq": "base_domina",
                "inferior_der": "base_domina",
            },
            "base": {
                "estrategia": "zocalo",
                "altura": 120.0,
                "separacion_frente": 60.0,
            }
        }
        panel.box_chassis.setChassisConfig(cfg_nueva)
        panel._on_chassis_changed(cfg_nueva)

        self.assertEqual(coco.Tapa, "interno")
        self.assertEqual(coco.Base, "externo")
        self.assertFalse(coco.TieneFondo)
        self.assertIn("lateral_domina", getattr(coco, "VDO_Chassis_JSON", ""))

        # 4. Accept persiste
        self.assertTrue(panel.accept())
        self.assertEqual(coco.Tapa, "interno")
        self.assertEqual(coco.Base, "externo")

    def test_dock_inspector_en_mainwindow(self):
        """Verifica que el DockWidget lateral se cree y contenga VDOUniversalInspectorWidget."""
        dock = obtener_o_crear_dock_inspector()
        if Gui is not None and getattr(App, "GuiUp", False):
            self.assertIsNotNone(dock)
            self.assertEqual(dock.objectName(), "VDOUniversalInspectorDock")
            self.assertIsInstance(dock.widget(), VDOUniversalInspectorWidget)

    def test_enfocar_inspector_universal(self):
        """Verifica que enfocar_inspector_universal sincronice el objeto sin lanzar excepciones."""
        coco = make_coco({"nombre": "CocoFocusTest"})
        self.doc.recompute()
        # Debe ejecutarse sin error
        resultado = enfocar_inspector_universal(coco)
        self.assertIn(resultado, (True, False))

    def test_viewprovider_coco_redireccion(self):
        """Verifica que ViewProviderCoco implemente setEdit y doubleClicked con integración de inspector."""
        coco = make_coco({"nombre": "CocoVPTest"})
        self.doc.recompute()
        vp = getattr(coco, "ViewObject", None)
        if vp is not None:
            proxy = getattr(vp, "Proxy", None)
            if proxy is not None:
                self.assertTrue(hasattr(proxy, "setEdit"))
                self.assertTrue(hasattr(proxy, "doubleClicked"))


    @classmethod
    def tearDownClass(cls):
        try:
            for doc in list(App.listDocuments().keys()):
                App.closeDocument(doc)
        except Exception:
            pass


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestGuiWiring)
    resultado = unittest.TextTestRunner(verbosity=2).run(suite)
    os._exit(0 if resultado.wasSuccessful() else 1)
