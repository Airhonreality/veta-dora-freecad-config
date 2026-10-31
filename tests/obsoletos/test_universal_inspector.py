# -*- coding: utf-8 -*-
"""Suite de pruebas del Inspector Universal Reactivo (VDOUniversalInspector).

Ejecución vía CLI:
    freecadcmd -c "import sys; import pytest; sys.exit(pytest.main(['tests/test_universal_inspector.py', '-v']))"

Verifica:
  1. Instanciación correcta del widget sin errores de GUI.
  2. Selección de PanelFeature → QStackedWidget índice PIEZA y Header actualizado.
  3. Selección de CocoFeature → QStackedWidget índice CHASIS.
  4. Desconexión limpia del observer al llamar a detach().

Nota: en entornos headless (freecadcmd sin display) el observer de
Gui.Selection no se puede registrar, por lo que `esta_activo` puede ser
False. Las pruebas verifican el comportamiento funcional
(addSelection / clearSelection / conmutación de páginas) que sí opera.
"""

import importlib.util
import os
import sys
import unittest

# Forzar plataforma offscreen para entornos sin display (freecadcmd / CI).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    _AQUI = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _AQUI = os.getcwd()
_RAIZ = os.path.dirname(_AQUI)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

_HAS_FREECAD = importlib.util.find_spec("FreeCAD") is not None
_HAS_QT = importlib.util.find_spec("PySide6") is not None or importlib.util.find_spec("PySide2") is not None


def _obtener_qapp():
    """Devuelve la QApplication existente (FreeCADGui) o crea una offscreen."""
    from PySide6 import QtWidgets  # type: ignore
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


@unittest.skipUnless(_HAS_FREECAD and _HAS_QT, "FreeCAD y PySide requeridos")
class UniversalInspectorTests(unittest.TestCase):
    """Pruebas del inspector universal con contexto FreeCAD + Qt."""

    @classmethod
    def setUpClass(cls):
        import FreeCAD as App
        import Part

        cls.App = App
        cls.Part = Part

        from VDO.cad.objects.vdo_cad_coco import CocoFeature
        from VDO.cad.objects.vdo_cad_panel import PanelFeature

        cls.CocoFeature = CocoFeature
        cls.PanelFeature = PanelFeature

        from vdo_universal_inspector import (
            VDOUniversalInspectorWidget,
            PAGE_CHASIS,
            PAGE_PIEZA,
        )
        cls.VDOUniversalInspectorWidget = VDOUniversalInspectorWidget
        cls.PAGE_CHASIS = PAGE_CHASIS
        cls.PAGE_PIEZA = PAGE_PIEZA

        # QApplication (reusa la de FreeCADGui si existe)
        cls.qapp = _obtener_qapp()

        # Documento de prueba
        cls.doc = App.newDocument("TestUniversalInspector")

        # 1 CocoFeature
        cls.obj_coco = cls.doc.addObject("Part::FeaturePython", "TestCOCO")
        cls.CocoFeature(cls.obj_coco)

        # 1 PanelFeature
        cls.obj_panel = cls.doc.addObject("Part::FeaturePython", "TestPanel")
        cls.PanelFeature(cls.obj_panel)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.App.closeDocument(cls.doc.Name)
        except Exception:
            pass

    def setUp(self):
        self.inspector = self.VDOUniversalInspectorWidget()

    def tearDown(self):
        try:
            self.inspector.cerrar_inspector()
        except Exception:
            pass
        self.inspector = None
        try:
            self.qapp.processEvents()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 1. Instanciación
    # ------------------------------------------------------------------
    def test_instanciacion_sin_errores(self):
        self.assertIsNotNone(self.inspector)
        self.assertIsNotNone(self.inspector.stack)
        self.assertIsNotNone(self.inspector.breadcrumbs)
        self.assertEqual(self.inspector.stack.count(), 4)

    def test_pagina_inicial_es_chasis(self):
        self.assertEqual(self.inspector.pagina_actual(), self.PAGE_CHASIS)

    def test_puente_creado(self):
        puente = self.inspector.puente()
        self.assertIsNotNone(puente)
        # addSelection debe funcionar incluso si el observer no está
        # registrado en entornos headless.
        puente.addSelection(
            self.doc.Name, self.obj_panel.Name, "", self.App.Vector())
        self.qapp.processEvents()
        self.assertEqual(self.inspector.pagina_actual(), self.PAGE_PIEZA)

    # ------------------------------------------------------------------
    # 2. Selección simulada: Panel → Página Pieza
    # ------------------------------------------------------------------
    def test_seleccion_panel_cambia_a_pieza(self):
        puente = self.inspector.puente()
        puente.addSelection(
            self.doc.Name, self.obj_panel.Name, "", self.App.Vector())
        self.qapp.processEvents()

        self.assertEqual(
            self.inspector.pagina_actual(), self.PAGE_PIEZA,
            "Al seleccionar un PanelFeature debe ir a la página PIEZA")
        self.assertEqual(self.inspector.tipo_actual(), "PANEL")

        # Verificar que el Header del panel se actualizó con los datos
        lbl_largo = self.inspector.pagina_pieza.lbl_largo
        self.assertNotEqual(lbl_largo.text(), "—")

    def test_seleccion_panel_actualiza_header_cantos(self):
        puente = self.inspector.puente()
        puente.addSelection(
            self.doc.Name, self.obj_panel.Name, "", self.App.Vector())
        self.qapp.processEvents()

        lbl_canto_norte = self.inspector.pagina_pieza.lbl_canto_norte
        lbl_canto_sur = self.inspector.pagina_pieza.lbl_canto_sur
        lbl_canto_este = self.inspector.pagina_pieza.lbl_canto_este
        lbl_canto_oeste = self.inspector.pagina_pieza.lbl_canto_oeste

        # Al menos uno de los cantos debe mostrar un valor (FX por defecto)
        valores = [
            lbl_canto_norte.text(), lbl_canto_sur.text(),
            lbl_canto_este.text(), lbl_canto_oeste.text(),
        ]
        self.assertTrue(any(v != "—" for v in valores),
                        "Los cantos N/S/E/O del PanelHeader deben mostrarse")

    # ------------------------------------------------------------------
    # 3. Selección simulada: Coco → Página Chasis
    # ------------------------------------------------------------------
    def test_seleccion_coco_cambia_a_chasis(self):
        puente = self.inspector.puente()
        puente.addSelection(
            self.doc.Name, self.obj_coco.Name, "", self.App.Vector())
        self.qapp.processEvents()

        self.assertEqual(
            self.inspector.pagina_actual(), self.PAGE_CHASIS,
            "Al seleccionar un CocoFeature debe ir a la página CHASIS")
        self.assertEqual(self.inspector.tipo_actual(), "COCO")

    # ------------------------------------------------------------------
    # 4. Desconexión limpia (idempotente, sin excepciones)
    # ------------------------------------------------------------------
    def test_desconexion_observer_limpia(self):
        puente = self.inspector.puente()
        # detach debe ser idempotente y nunca lanzar
        puente.detach()
        puente.detach()
        puente.detach()

    def test_cerrar_inspector_no_lanza(self):
        self.inspector.cerrar_inspector()
        # Segunda llamada idempotente
        self.inspector.cerrar_inspector()

    # ------------------------------------------------------------------
    # 5. Selección vacía / desconocido → vuelve a chasis general
    # ------------------------------------------------------------------
    def test_seleccion_vacio_regresa_chasis(self):
        puente = self.inspector.puente()
        # Primero seleccionar un panel para alejarse del chasis
        puente.addSelection(
            self.doc.Name, self.obj_panel.Name, "", self.App.Vector())
        self.qapp.processEvents()
        self.assertEqual(self.inspector.pagina_actual(), self.PAGE_PIEZA)

        # Luego limpiar selección
        puente.clearSelection(self.doc.Name)
        self.qapp.processEvents()

        self.assertEqual(self.inspector.pagina_actual(), self.PAGE_CHASIS)
        self.assertEqual(self.inspector.tipo_actual(), "UNKNOWN")


if __name__ == "__main__":
    resultado = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    sys.exit(0 if resultado.wasSuccessful() else 1)
