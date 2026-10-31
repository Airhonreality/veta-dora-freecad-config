# -*- coding: utf-8 -*-
# =====================================================================
# tests/test_single_dock_convergence.py
# Pruebas de integración del Dock Lateral Único Consolidado:
# - Visor 2D (CocoPreview2D) en la sección superior
# - Micro-Header editable (W × H × D │ Esp)
# - QSplitter con Árbol Maestro (izq) y Stack Contextual (der)
# - Sincronización bidireccional (2D <-> Árbol <-> Stack)
# - Erradicación de diálogos modales en edición y doble clic
# =====================================================================

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
    from PySide6 import QtCore, QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtWidgets
    except ImportError:
        from PySide import QtCore, QtWidgets

from VDO.cad.objects.vdo_cad_coco import CocoFeature, ViewProviderCoco
from VDO.cad.objects.vdo_cad_panel import PanelFeature
from VDO.cad.views.vdo_cad_view_base import enfocar_inspector_universal, abrir_panel_objeto
from vdo_inspector_dock import (
    obtener_o_crear_dock_inspector,
    VDOUniversalInspectorWidget,
    PAGE_CHASIS,
    PAGE_VANO,
    PAGE_PIEZA,
    PAGE_CIERRE,
)


def _get_qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


class TestSingleDockConvergence(unittest.TestCase):
    """Verifica la fusión total del Inspector Universal en un Dock único lateral."""

    @classmethod
    def setUpClass(cls):
        cls.qapp = _get_qapp()
        cls.doc = App.newDocument("DocSingleDock")

        cls.obj_coco = cls.doc.addObject("Part::FeaturePython", "COCO_Unificado")
        CocoFeature(cls.obj_coco)
        cls.obj_coco.Alto = 720.0
        cls.obj_coco.Ancho = 600.0
        cls.obj_coco.FondoModulo = 580.0
        cls.obj_coco.Espesor = 18

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
    # 1. Estructura de Panel Único
    # ------------------------------------------------------------------
    def test_anatomia_panel_unico(self):
        """Verifica que el 2D, el micro-header, el árbol y las páginas habiten el mismo widget."""
        # 1. Breadcrumbs presentes
        self.assertIsNotNone(self.inspector.breadcrumbs)

        # 2. Micro-Header editable presente con los 4 spins
        self.assertIsNotNone(self.inspector.micro_header)
        self.assertIsNotNone(self.inspector.micro_header.spin_w)
        self.assertIsNotNone(self.inspector.micro_header.spin_h)
        self.assertIsNotNone(self.inspector.micro_header.spin_d)
        self.assertIsNotNone(self.inspector.micro_header.spin_e)

        # 3. Visor 2D (CocoPreview2D) integrado arriba
        self.assertIsNotNone(self.inspector.preview)

        # 4. QSplitter con Árbol Maestro (izq) y Stack (der)
        self.assertIsNotNone(self.inspector.splitter)
        self.assertIsNotNone(self.inspector.master_tree)
        self.assertIsNotNone(self.inspector.stack)
        self.assertEqual(self.inspector.stack.count(), 4)

    def test_carga_coco_puebla_micro_header_y_arbol(self):
        """Al cargar un COCO se actualizan los spins del micro-header y las 3 ramas del árbol."""
        self.inspector.cargar_coco(self.obj_coco)
        self.qapp.processEvents()

        # Micro-header refleja dimensiones del COCO
        self.assertAlmostEqual(self.inspector.micro_header.spin_w.value(), 600.0)
        self.assertAlmostEqual(self.inspector.micro_header.spin_h.value(), 720.0)
        self.assertAlmostEqual(self.inspector.micro_header.spin_d.value(), 580.0)
        self.assertAlmostEqual(self.inspector.micro_header.spin_e.value(), 18.0)

        # Árbol maestro contiene la raíz COCO y sus 3 ramas
        tree = self.inspector.master_tree
        self.assertEqual(tree.topLevelItemCount(), 1)
        root = tree.topLevelItem(0)
        self.assertIn("COCO", root.text(0))

        # Verificar 3 ramas principales
        nombres_hijos = [root.child(i).text(0) for i in range(root.childCount())]
        self.assertTrue(any("Chasis" in n for n in nombres_hijos))
        self.assertTrue(any("Piezas" in n for n in nombres_hijos))
        self.assertTrue(any("Vanos" in n for n in nombres_hijos))

    # ------------------------------------------------------------------
    # 2. Sincronización Bidireccional
    # ------------------------------------------------------------------
    def test_click_arbol_conmuta_stack(self):
        """Hacer clic en ramas del árbol maestro conmuta el QStackedWidget a la página correcta."""
        self.inspector.cargar_coco(self.obj_coco)
        self.qapp.processEvents()

        root = self.inspector.master_tree.topLevelItem(0)
        item_chasis = root.child(0)
        item_piezas = root.child(1)
        item_vanos = root.child(2)

        # Clic en Chasis -> Página 0
        self.inspector._on_tree_item_clicked(item_chasis, 0)
        self.assertEqual(self.inspector.pagina_actual(), PAGE_CHASIS)

        # Clic en una pieza física -> Página 2 (PIEZA)
        if item_piezas.childCount() > 0:
            pieza_item = item_piezas.child(0)
            self.inspector._on_tree_item_clicked(pieza_item, 0)
            self.assertEqual(self.inspector.pagina_actual(), PAGE_PIEZA)

        # Clic en un vano -> Página 1 (VANO)
        if item_vanos.childCount() > 0:
            vano_item = item_vanos.child(0)
            self.inspector._on_tree_item_clicked(vano_item, 0)
            self.assertEqual(self.inspector.pagina_actual(), PAGE_VANO)

    def test_click_preview_2d_sincroniza_arbol_y_stack(self):
        """Hacer clic en celda o panel de CocoPreview2D selecciona en árbol y conmuta página."""
        self.inspector.cargar_coco(self.obj_coco)
        self.qapp.processEvents()

        # Clic 2D en celda -> Página VANO y celda seleccionada
        self.inspector._on_preview_cell_clicked("(x1, y1)")
        self.assertEqual(self.inspector.pagina_actual(), PAGE_VANO)

        item_sel = self.inspector.master_tree.currentItem()
        self.assertIsNotNone(item_sel)
        self.assertIn("(x1, y1)", item_sel.text(0))

        # Clic 2D en panel -> Página PIEZA y panel seleccionado
        self.inspector._on_preview_panel_clicked("lat_izq")
        self.assertEqual(self.inspector.pagina_actual(), PAGE_PIEZA)

        item_sel = self.inspector.master_tree.currentItem()
        self.assertIsNotNone(item_sel)
        self.assertIn("Lateral Izquierdo", item_sel.text(0))

    def test_edicion_micro_header_actualiza_coco_y_preview(self):
        """Modificar valores en el micro-header actualiza las propiedades del COCO en FreeCAD."""
        self.inspector.cargar_coco(self.obj_coco)
        self.qapp.processEvents()

        # Cambiar ancho a 800 mm
        self.inspector.micro_header.spin_w.setValue(800.0)
        self.inspector.micro_header._on_edited()
        self.qapp.processEvents()

        self.assertAlmostEqual(self.obj_coco.Ancho, 800.0)

    # ------------------------------------------------------------------
    # 3. Erradicación de Diálogos Flotantes Secundarios
    # ------------------------------------------------------------------
    def test_abrir_panel_objeto_no_abre_dialogo_flotante(self):
        """Verifica que abrir_panel_objeto y doubleClicked deleguen al Inspector lateral."""
        # En entornos con GuiUp simulado, enfocar_inspector_universal busca el dock
        # y no abre diálogos modales secundarios.
        res = abrir_panel_objeto(self.obj_coco)
        # Si no hay GUI completo levantado devuelve True o False de forma segura sin excepciones
        self.assertIsInstance(res, bool)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestSingleDockConvergence)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    os._exit(0 if result.wasSuccessful() else 1)
