# -*- coding: utf-8 -*-
"""
tests/test_workbench_convergence.py

Suite de Pruebas de Integración y Convergencia Final del VDO Workbench.
Verifica:
  1. Simulación de selección en 3D / árbol con VDOSelectionBridge:
     - Selección de COCO (Chasis) -> Página 0 (PAGE_CHASIS) con VDOChassisControllerWidget.
     - Selección de VANO -> Página 1 (PAGE_VANO) con Luz Neta y Dock de Habitantes.
     - Selección de PANEL (Tablero L1) -> Página 2 (PAGE_PIEZA) con PanelHeader y VDOBoxControllerWidget.
     - Selección de PUERTA / CAJON -> Página 3 (PAGE_CIERRE) con datos comerciales de Capa H (vdo_hardware_hub).
  2. Comportamiento interactivo sin excepciones:
     - Cambio de esquinas en VDOChassisControllerWidget emite diccionarios canónicos.
     - Cambio de bordes en VDOBoxControllerWidget emite configuración válida.
     - Dock táctil de vano conmuta entre Subdividir, Cajón, Puerta y Vacío emitiendo sigHabitanteCambiado.
  3. Desconexión y ciclo de vida de observadores FreeCAD limpios e idempotentes.
"""

import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    _AQUI = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _AQUI = os.getcwd()
_RAIZ = os.path.dirname(_AQUI)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import FreeCAD as App

try:
    from PySide6 import QtWidgets
except ImportError:
    try:
        from PySide2 import QtWidgets
    except ImportError:
        from PySide import QtWidgets

from VDO.cad.objects.vdo_cad_coco import CocoFeature
from VDO.cad.objects.vdo_cad_panel import PanelFeature
from VDO.cad.objects.vdo_cad_puerta import PuertaFeature
from VDO.cad.objects.vdo_cad_cajon import CajonFeature
import VDO.hub.vdo_hub_hardware as HH

from vdo_universal_inspector import (
    VDOUniversalInspectorWidget,
    PAGE_CHASIS,
    PAGE_VANO,
    PAGE_PIEZA,
    PAGE_CIERRE,
)
from vdo_selection_bridge import VDOSelectionBridge


def _get_qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


class TestWorkbenchConvergence(unittest.TestCase):
    """Pruebas de integración del flujo de convergencia del Workbench VDO."""

    @classmethod
    def setUpClass(cls):
        cls.qapp = _get_qapp()
        cls.doc = App.newDocument("DocConvergenciaVDO")

        # 1. Objeto COCO (Chasis)
        cls.obj_coco = cls.doc.addObject("Part::FeaturePython", "COCO_Principal")
        CocoFeature(cls.obj_coco)
        cls.obj_coco.Alto = 720.0
        cls.obj_coco.Ancho = 600.0
        cls.obj_coco.FondoModulo = 580.0

        # 2. Objeto PANEL (Pieza L1)
        cls.obj_panel = cls.doc.addObject("Part::FeaturePython", "Lateral_Izquierdo")
        PanelFeature(cls.obj_panel)
        cls.obj_panel.Largo = 720.0
        cls.obj_panel.Ancho = 580.0
        cls.obj_panel.Espesor = 18.0
        cls.obj_panel.VDO_Canto_Norte = "RIG"
        cls.obj_panel.VDO_Canto_Sur = "FX"

        # 3. Objeto PUERTA (Cierre)
        cls.obj_puerta = cls.doc.addObject("Part::FeaturePython", "Puerta_Cocina")
        PuertaFeature(cls.obj_puerta)
        cls.obj_puerta.Ancho = 596.0
        cls.obj_puerta.Alto = 716.0
        cls.obj_puerta.TipoMontaje = "Parche"
        cls.obj_puerta.HardwareSKU = "GEN-CAZ-35-PARCHE"

        # 4. Objeto CAJON (Cierre)
        cls.obj_cajon = cls.doc.addObject("Part::FeaturePython", "Cajon_Cubiertos")
        CajonFeature(cls.obj_cajon)
        cls.obj_cajon.AnchoLibre = 564.0
        cls.obj_cajon.AltoFrente = 200.0
        cls.obj_cajon.MarcaCorredera = "blum_tandem"
        cls.obj_cajon.TipoCorredera = "oculta"

        # 5. Objeto VANO simulado
        cls.obj_vano = cls.doc.addObject("Part::FeaturePython", "Vano_Superior")
        cls.obj_vano.addProperty("App::PropertyString", "VDO_Tipo", "VDO", "Tipo")
        cls.obj_vano.VDO_Tipo = "vano"
        cls.obj_vano.addProperty("App::PropertyFloat", "LuzLibreX", "VDO", "Luz X")
        cls.obj_vano.addProperty("App::PropertyFloat", "LuzLibreY", "VDO", "Luz Y")
        cls.obj_vano.addProperty("App::PropertyFloat", "LuzLibreZ", "VDO", "Luz Z")
        cls.obj_vano.LuzLibreX = 564.0
        cls.obj_vano.LuzLibreY = 320.0
        cls.obj_vano.LuzLibreZ = 550.0

        cls.doc.recompute()

    @classmethod
    def tearDownClass(cls):
        try:
            App.closeDocument(cls.doc.Name)
        except Exception:
            pass

    def setUp(self):
        self.inspector = VDOUniversalInspectorWidget()
        self.qapp.processEvents()

    def tearDown(self):
        if self.inspector:
            self.inspector.cerrar_inspector()
            self.inspector = None
        self.qapp.processEvents()

    # ------------------------------------------------------------------
    # 1. Convergencia de Selección y Zoom Semántico
    # ------------------------------------------------------------------
    def test_zoom_semantico_chasis(self):
        """Al seleccionar un COCO, el inspector abre Página 0 con el Chasis 2D."""
        puente = self.inspector.puente()
        puente.addSelection(self.doc.Name, self.obj_coco.Name, "", App.Vector())
        self.qapp.processEvents()

        self.assertEqual(self.inspector.pagina_actual(), PAGE_CHASIS)
        self.assertEqual(self.inspector.tipo_actual(), VDOSelectionBridge.TARGET_COCO)

        # Widget de Chasis 2D incrustado y activo
        box_chassis = self.inspector.pagina_chasis.box_chassis
        self.assertIsNotNone(box_chassis)
        cfg = box_chassis.getChassisConfig()
        self.assertIn("caras", cfg)
        self.assertIn("encuentros", cfg)
        self.assertIn("base", cfg)

    def test_zoom_semantico_vano(self):
        """Al seleccionar un Vano, el inspector abre Página 1 con Luz Neta y Dock."""
        puente = self.inspector.puente()
        puente.addSelection(self.doc.Name, self.obj_vano.Name, "", App.Vector())
        self.qapp.processEvents()

        self.assertEqual(self.inspector.pagina_actual(), PAGE_VANO)
        p_vano = self.inspector.pagina_vano
        self.assertEqual(p_vano.lbl_luz_w.text(), "564.0 mm")
        self.assertEqual(p_vano.lbl_luz_h.text(), "320.0 mm")
        self.assertIn("564.0", p_vano.lbl_luz_banner.text())

    def test_zoom_semantico_pieza_l1(self):
        """Al seleccionar un Panel, abre Página 2 con Header y Cuadrado 3x3."""
        puente = self.inspector.puente()
        puente.addSelection(self.doc.Name, self.obj_panel.Name, "", App.Vector())
        self.qapp.processEvents()

        self.assertEqual(self.inspector.pagina_actual(), PAGE_PIEZA)
        p_pieza = self.inspector.pagina_pieza
        self.assertEqual(p_pieza.lbl_largo.text(), "720.0")
        self.assertEqual(p_pieza.lbl_ancho.text(), "580.0")
        self.assertEqual(p_pieza.lbl_canto_norte.text(), "RIG")

        # Cuadrado 3x3 Figma embebido
        self.assertIsNotNone(p_pieza.box_controller)
        cfg_box = p_pieza.box_controller.getConfig()
        self.assertIn("bordes", cfg_box)
        self.assertIn("esquinas", cfg_box)

    def test_zoom_semantico_cierre_puerta(self):
        """Al seleccionar una Puerta, abre Página 3 con fachada y Capa H (bisagra)."""
        puente = self.inspector.puente()
        puente.addSelection(self.doc.Name, self.obj_puerta.Name, "", App.Vector())
        self.qapp.processEvents()

        self.assertEqual(self.inspector.pagina_actual(), PAGE_CIERRE)
        p_cierre = self.inspector.pagina_cierre
        self.assertEqual(p_cierre.lbl_tipo.text(), "PUERTA")
        self.assertIn("GEN-CAZ-35-PARCHE", p_cierre.lbl_sku.text())
        self.assertIn("Cazoleta 35mm", p_cierre.lbl_fresado.text())

    def test_zoom_semantico_cierre_cajon(self):
        """Al seleccionar un Cajón, abre Página 3 con fachada y Capa H (corredera Tandem)."""
        puente = self.inspector.puente()
        puente.addSelection(self.doc.Name, self.obj_cajon.Name, "", App.Vector())
        self.qapp.processEvents()

        self.assertEqual(self.inspector.pagina_actual(), PAGE_CIERRE)
        p_cierre = self.inspector.pagina_cierre
        self.assertEqual(p_cierre.lbl_tipo.text(), "CAJON")
        self.assertEqual(p_cierre.lbl_proveedor.text(), "Blum")
        self.assertIn("BLUM-TANDEM", p_cierre.lbl_sku.text())
        self.assertIn("Delta:", p_cierre.lbl_fresado.text())

    # ------------------------------------------------------------------
    # 2. Interacciones Reactivas sin Excepciones
    # ------------------------------------------------------------------
    def test_interaccion_chasis_emite_capa1(self):
        """Ciclar esquinas y conmutar caras en Chasis Widget no produce fallas."""
        puente = self.inspector.puente()
        puente.addSelection(self.doc.Name, self.obj_coco.Name, "", App.Vector())
        self.qapp.processEvents()

        box_chassis = self.inspector.pagina_chasis.box_chassis
        cambios = []
        box_chassis.sigChassisChanged.connect(lambda d: cambios.append(d))

        # Ciclar esquina superior izquierda
        box_chassis.btn_esquina["superior_izq"].click()
        self.assertGreater(len(cambios), 0)
        self.assertEqual(cambios[-1]["encuentros"]["superior_izq"], "lateral_domina")

        # Conmutar cara superior
        box_chassis.btn_cara_sup.click()
        self.assertFalse(cambios[-1]["caras"]["superior"]["activa"])

    def test_interaccion_vano_dock(self):
        """El dock táctil del vano conmuta limpiamente entre sus 4 habitantes."""
        puente = self.inspector.puente()
        puente.addSelection(self.doc.Name, self.obj_vano.Name, "", App.Vector())
        self.qapp.processEvents()

        p_vano = self.inspector.pagina_vano
        eventos = []
        p_vano.sigHabitanteCambiado.connect(lambda t, c: eventos.append((t, c)))

        # 1. Clic en Subdividir
        p_vano.btn_dock["subdividir"].click()
        self.assertEqual(p_vano.stack_dock.currentIndex(), 0)
        self.assertEqual(eventos[-1][0], "subdividir")

        # 2. Clic en Cajón
        p_vano.btn_dock["cajon"].click()
        self.assertEqual(p_vano.stack_dock.currentIndex(), 1)
        self.assertEqual(eventos[-1][0], "cajon")

        # 3. Clic en Puerta
        p_vano.btn_dock["puerta"].click()
        self.assertEqual(p_vano.stack_dock.currentIndex(), 2)
        self.assertEqual(eventos[-1][0], "puerta")

        # 4. Clic en Vacío
        p_vano.btn_dock["vacio"].click()
        self.assertEqual(p_vano.stack_dock.currentIndex(), 3)
        self.assertEqual(eventos[-1][0], "vacio")

    def test_interaccion_box_controller_pieza(self):
        """Ciclar esquinas y bordes en Cuadrado Figma no produce fallas."""
        puente = self.inspector.puente()
        puente.addSelection(self.doc.Name, self.obj_panel.Name, "", App.Vector())
        self.qapp.processEvents()

        box_ctrl = self.inspector.pagina_pieza.box_controller
        # Activar reengrose en el widget
        box_ctrl.chk_activo.setChecked(True)
        self.assertTrue(box_ctrl.chk_activo.isChecked())

        cambios = []
        box_ctrl.sigConfigChanged.connect(lambda d: cambios.append(d))

        # Ciclar esquina NO
        box_ctrl.btn_esquina["fondo_izquierda"].click()
        self.assertGreater(len(cambios), 0)

        # Modificar offset de borde
        box_ctrl.seleccionar_margen("fondo")
        box_ctrl.spin_offset.setValue(18.0)
        self.assertEqual(box_ctrl.getConfig()["bordes"]["fondo"]["offset_borde"], 18.0)

    # ------------------------------------------------------------------
    # 3. Ciclo de Vida y Limpieza
    # ------------------------------------------------------------------
    def test_lifecycle_context_manager(self):
        """Verifica que el context manager desconecta el observador al salir."""
        with VDOUniversalInspectorWidget() as insp:
            self.assertIsNotNone(insp.puente())
        # Al salir del bloque with, cerrar_inspector debió ejecutarse
        self.assertIsNone(insp.puente())


if __name__ == "__main__":
    unittest.main()
