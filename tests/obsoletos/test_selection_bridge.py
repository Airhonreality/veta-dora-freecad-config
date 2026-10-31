# -*- coding: utf-8 -*-
"""Suite de pruebas del puente de selección nativa VDO.

Crea un documento FreeCAD de prueba con una instancia de cada tipo de
entidad VDO (COCO, Panel L1, CajonFeature, PuertaFeature, ZocaloFeature)
más un Part::Box nativo, y valida:
  1. classify_object() identifica con 100% de precisión cada entidad.
  2. addSelection / clearSelection disparan on_target_changed correctamente.
  3. Seleccionar/deseleccionar repetidamente no produce bloqueos.
"""

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

_HAS_FREECAD = importlib.util.find_spec("FreeCAD") is not None


def _requiere_freecad(msg="FreeCAD no disponible en este entorno"):
    return unittest.skipUnless(_HAS_FREECAD, msg)


@_requiere_freecad()
class SelectionBridgeTests(unittest.TestCase):
    """Pruebas del puente de selección con contexto FreeCAD."""

    @classmethod
    def setUpClass(cls):
        import FreeCAD as App
        import Part

        cls.App = App
        cls.Part = Part

        # Importar los proxies FeaturePython de cada módulo VDO.
        from VDO.cad.objects.vdo_cad_coco import CocoFeature
        from VDO.cad.objects.vdo_cad_panel import PanelFeature
        from VDO.cad.objects.vdo_cad_cajon import CajonFeature
        from VDO.cad.objects.vdo_cad_puerta import PuertaFeature
        from VDO.cad.objects.vdo_cad_zocalo import ZocaloFeature

        cls.CocoFeature = CocoFeature
        cls.PanelFeature = PanelFeature
        cls.CajonFeature = CajonFeature
        cls.PuertaFeature = PuertaFeature
        cls.ZocaloFeature = ZocaloFeature

        from vdo_selection_bridge import VDOSelectionBridge
        cls.VDOSelectionBridge = VDOSelectionBridge

        # Crear documento de prueba.
        cls.doc = App.newDocument("TestSelectionBridge")

        # 1 COCO
        cls.obj_coco = cls.doc.addObject("Part::FeaturePython", "TestCOCO")
        cls.CocoFeature(cls.obj_coco)

        # 1 Panel L1
        cls.obj_panel = cls.doc.addObject("Part::FeaturePython", "TestPanel")
        cls.PanelFeature(cls.obj_panel)

        # 1 CajonFeature
        cls.obj_cajon = cls.doc.addObject("Part::FeaturePython", "TestCajon")
        cls.CajonFeature(cls.obj_cajon)

        # 1 PuertaFeature
        cls.obj_puerta = cls.doc.addObject("Part::FeaturePython", "TestPuerta")
        cls.PuertaFeature(cls.obj_puerta)

        # 1 ZocaloFeature
        cls.obj_zocalo = cls.doc.addObject("Part::FeaturePython", "TestZocalo")
        cls.ZocaloFeature(cls.obj_zocalo)

        # 1 Part::Box nativo de FreeCAD
        cls.obj_box = cls.doc.addObject("Part::Box", "TestBox")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.App.closeDocument(cls.doc.Name)
        except Exception:
            pass

    def setUp(self):
        self.eventos = []
        self.bridge = self.VDOSelectionBridge(
            on_target_changed=lambda obj, tipo: self.eventos.append((obj, tipo)))

    def _seleccionar(self, obj):
        self.bridge.addSelection(self.doc.Name, obj.Name, "", self.App.Vector())

    # ------------------------------------------------------------------
    # Clasificación
    # ------------------------------------------------------------------
    def test_classify_coco(self):
        self.assertEqual(self.bridge.classify_object(self.obj_coco), "COCO")

    def test_classify_panel(self):
        self.assertEqual(self.bridge.classify_object(self.obj_panel), "PANEL")

    def test_classify_cajon(self):
        self.assertEqual(self.bridge.classify_object(self.obj_cajon), "CAJON")

    def test_classify_puerta(self):
        self.assertEqual(self.bridge.classify_object(self.obj_puerta), "PUERTA")

    def test_classify_zocalo(self):
        self.assertEqual(self.bridge.classify_object(self.obj_zocalo), "ZOCALO")

    def test_classify_box_nativo_desconocido(self):
        self.assertEqual(self.bridge.classify_object(self.obj_box), "UNKNOWN")

    def test_classify_none(self):
        self.assertEqual(self.bridge.classify_object(None), "UNKNOWN")

    def test_classify_precision_100(self):
        casos = [
            (self.obj_coco, "COCO"),
            (self.obj_panel, "PANEL"),
            (self.obj_cajon, "CAJON"),
            (self.obj_puerta, "PUERTA"),
            (self.obj_zocalo, "ZOCALO"),
            (self.obj_box, "UNKNOWN"),
        ]
        fallos = 0
        for obj, esperado in casos:
            obtenido = self.bridge.classify_object(obj)
            if obtenido != esperado:
                fallos += 1
        self.assertEqual(fallos, 0, f"{fallos} clasificación(es) incorrecta(s)")

    # ------------------------------------------------------------------
    # Eventos de selección
    # ------------------------------------------------------------------
    def test_add_selection_dispara_callback(self):
        self.eventos.clear()
        self._seleccionar(self.obj_coco)
        self.assertEqual(len(self.eventos), 1)
        obj, tipo = self.eventos[0]
        self.assertIs(obj, self.obj_coco)
        self.assertEqual(tipo, "COCO")

    def test_add_selection_todos_los_tipos(self):
        self.eventos.clear()
        secuencias = [
            (self.obj_coco, "COCO"),
            (self.obj_panel, "PANEL"),
            (self.obj_cajon, "CAJON"),
            (self.obj_puerta, "PUERTA"),
            (self.obj_zocalo, "ZOCALO"),
            (self.obj_box, "UNKNOWN"),
        ]
        for obj, esperado in secuencias:
            self._seleccionar(obj)
        self.assertEqual(len(self.eventos), len(secuencias))
        for (obj, tipo), (_obj, esperado) in zip(self.eventos, secuencias):
            self.assertIs(obj, _obj)
            self.assertEqual(tipo, esperado)

    def test_clear_selection_resetear_estado(self):
        self.eventos.clear()
        self._seleccionar(self.obj_panel)
        self.assertEqual(self.bridge.ultimo_tipo, "PANEL")
        self.bridge.clearSelection(self.doc.Name)
        self.assertIsNone(self.bridge.ultimo_objeto)
        self.assertEqual(self.bridge.ultimo_tipo, "UNKNOWN")
        # El callback debe haber recibido (None, UNKNOWN) al limpiar.
        self.assertTrue(any(o is None and t == "UNKNOWN" for o, t in self.eventos))

    # ------------------------------------------------------------------
    # Anti-bloqueo / sin fugas
    # ------------------------------------------------------------------
    def test_repeticion_seleccion_deseleccion_sin_excepciones(self):
        """Seleccionar/deseleccionar repetidamente nunca debe lanzar."""
        objetos = [
            self.obj_coco, self.obj_panel, self.obj_cajon,
            self.obj_puerta, self.obj_zocalo, self.obj_box,
        ]
        for _ in range(50):
            for obj in objetos:
                self._seleccionar(obj)
            self.bridge.clearSelection(self.doc.Name)
        # Si llegamos aquí sin excepción, el test pasa.
        self.assertTrue(True)

    def test_desregistrar_observer_idempotente(self):
        self.bridge.detach()
        self.bridge.detach()  # segundo desregistro no debe fallar
        self.assertFalse(self.bridge.esta_activo)


if __name__ == "__main__":
    resultado = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    sys.exit(0 if resultado.wasSuccessful() else 1)
