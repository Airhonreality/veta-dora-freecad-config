# -*- coding: utf-8 -*-
"""Motor de dossier (VDO/cam/vdo_cam_dossier.py), headless en FreeCADCmd.

Cubre los criterios de aceptación de docs/07 E-4/E-5 y los requisitos
DOS-01…DOS-18 de docs/08 §9.5 que son verificables sin GUI:

  - Escala: serie normalizada D-3 (sin 1:15, con 1:25) y snap hacia abajo.
  - Marco de vista (DOS-15): la extensión medida depende de XDirection.
  - Cabida: cada vista cabe en el área útil de la plantilla (DOS-09/15).
  - Membrete: vdo_escala coincide con la escala real de la vista (F-20).
  - Transacción: un solo undo() deshace el dossier completo (DOS-13).
  - Sin geometría: el espacio vacío no produce hojas (DOS-18).
"""

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

from VDO._paths import get_template_area_util
from VDO.hub import vdo_hub_registry as REG
from VDO.hub.vdo_hub_schema import resolver
from VDO.cad.objects.vdo_cad_espacio import make_espacio
from VDO.cad.objects.vdo_cad_proyecto import make_proyecto
import VDO.cam.vdo_cam_cutlist as E
import VDO.cam.vdo_cam_dossier as D
from VDO.shared import vdo_shared_fachadas as F


def _util_mm():
    area = get_template_area_util()["util"]
    return (float(area["x1"]) - float(area["x0"]),
            float(area["y1"]) - float(area["y0"]))


def construir_escenario(doc):
    """Espacio con un muro (arquitectura) y un COCO (mobiliario)."""
    espacio = make_espacio({"nombre": "ESPACIO_Cocina", "nivel_piso": -150.0})
    # make_espacio sólo fija Label; el membrete lee NombreEspacio.
    espacio.NombreEspacio = "ESPACIO_Cocina"
    proyecto = make_proyecto({"nombre": "Proyecto Test"})
    proyecto.Nombre = "Proyecto Test"
    proyecto.Cliente = "Cliente Test"

    muro = doc.addObject("Part::Box", "Muro_Norte")
    muro.Length, muro.Width, muro.Height = 3000, 150, 2400
    muro.addProperty("App::PropertyString", "IfcType", "BIM")
    muro.IfcType = "Wall"

    fabrica = resolver(REG.spec("coco").fabrica)
    coco = fabrica({"nombre": "COCO_Demo", "alto": 720, "ancho": 600,
                    "fondo_modulo": 580, "espesor": 18})
    doc.recompute()

    espacio.Hijos = [muro, coco]
    doc.recompute()
    return espacio, coco


class EscalasTests(unittest.TestCase):
    def test_serie_normalizada_sin_1_15_con_1_25(self):
        inversas = sorted(round(1.0 / e) for e in D.ESCALAS_NORMALIZADAS)
        self.assertEqual(inversas, [1, 2, 5, 10, 20, 25, 50, 100])
        self.assertNotIn(15, inversas)

    def test_snap_hacia_abajo(self):
        self.assertEqual(D.snap_abajo(0.37), 0.2)
        self.assertEqual(D.snap_abajo(0.2), 0.2)
        self.assertEqual(D.snap_abajo(0.0005), 0.01)

    def test_siguiente_abajo(self):
        self.assertEqual(D.siguiente_abajo(0.2), 0.1)
        self.assertEqual(D.siguiente_abajo(0.01), 0.01)


class MarcoDeVistaTests(unittest.TestCase):
    """DOS-15: la extensión depende de XDirection, no sólo de la geometría."""

    def setUp(self):
        self.muro = Part.makeBox(3000, 150, 2400)

    def test_extension_sigue_a_xdirection(self):
        ex, ey = D.extent_en_vista([self.muro], (0, 0, 1), (1, 0, 0))
        self.assertAlmostEqual(ex, 3000.0, places=3)
        self.assertAlmostEqual(ey, 150.0, places=3)

    def test_xdirection_girada_intercambia_ejes(self):
        ex, ey = D.extent_en_vista([self.muro], (0, 0, 1), (0, 1, 0))
        self.assertAlmostEqual(ex, 150.0, places=3)
        self.assertAlmostEqual(ey, 3000.0, places=3)


class DossierTests(unittest.TestCase):
    def setUp(self):
        self.doc = App.newDocument("VDO_Test_Dossier")
        # FreeCADCmd deja el undo apagado; sin esto no hay transacciones.
        self.doc.UndoMode = 1

    def tearDown(self):
        try:
            App.closeDocument(self.doc.Name)
        except Exception:
            pass

    def _escenario(self):
        return construir_escenario(self.doc)

    def _paginas(self, paginas):
        return [p for p in paginas if p.Views]

    def test_genera_planta_y_ficha(self):
        espacio, coco = self._escenario()
        paginas = D.generar_dossier(self.doc, espacio)
        self.assertEqual(len(paginas), 2,
                         "esperadas 1 planta (1B) + 1 ficha por mueble (4)")
        vistas = [v for p in paginas for v in p.Views
                  if v.isDerivedFrom("TechDraw::DrawViewPart")]
        self.assertEqual(len(vistas), 4, "planta + casco + vanos + cerrado")

    def test_escala_normalizada_y_cabe_en_util(self):
        espacio, _ = self._escenario()
        util_w, util_h = _util_mm()
        for pagina in D.generar_dossier(self.doc, espacio):
            for v in pagina.Views:
                if not v.isDerivedFrom("TechDraw::DrawViewPart"):
                    continue
                esc = float(v.Scale)
                self.assertIn(round(1.0 / esc, 6),
                              [round(1.0 / e, 6) for e in D.ESCALAS_NORMALIZADAS])
                shapes = [f.Shape for f in v.Source]
                ex, ey = D.extent_en_vista(
                    shapes, tuple(v.Direction), tuple(v.XDirection))
                self.assertLessEqual(ex * esc, util_w + 1e-6,
                                     f"{v.Name} desborda en X")
                self.assertLessEqual(ey * esc, util_h + 1e-6,
                                     f"{v.Name} desborda en Y")

    def test_membrete_coincide_con_escala_de_la_vista(self):
        espacio, _ = self._escenario()
        paginas = D.generar_dossier(self.doc, espacio)
        for pagina in paginas:
            tpl = pagina.Template
            vistas = [v for v in pagina.Views
                      if v.isDerivedFrom("TechDraw::DrawViewPart")]
            esperado = "1:%g" % round(1.0 / float(vistas[0].Scale))
            self.assertEqual(tpl.EditableTexts["vdo_escala"], esperado)
            self.assertEqual(tpl.EditableTexts["vdo_espacio"], "ESPACIO_Cocina")
            self.assertEqual(tpl.EditableTexts["vdo_npt"], "NPT -150 mm")
            self.assertEqual(tpl.EditableTexts["vdo_proyecto"], "Proyecto Test")
            self.assertEqual(tpl.EditableTexts["vdo_cliente"], "Cliente Test")

    def test_exporta_svg_con_membrete_y_geometria(self):
        import shutil
        import tempfile
        espacio, _ = self._escenario()
        carpeta = tempfile.mkdtemp(prefix="vdo_dossier_")
        try:
            paginas = D.generar_dossier(self.doc, espacio, destino=carpeta)
            self.assertTrue(paginas)
            for pagina in paginas:
                ruta = os.path.join(carpeta, pagina.Name + ".svg")
                self.assertTrue(os.path.isfile(ruta), ruta)
                with open(ruta, encoding="utf-8") as fh:
                    svg = fh.read()
                self.assertIn("NPT -150 mm", svg)
                self.assertIn("ESPACIO_Cocina", svg)
                self.assertIn("translate(", svg)
                self.assertIn("<path", svg)
        finally:
            shutil.rmtree(carpeta, ignore_errors=True)

    def test_un_solo_undo_deshace_el_dossier(self):
        espacio, _ = self._escenario()
        antes = len(self.doc.Objects)
        undo_antes = self.doc.UndoCount
        D.generar_dossier(self.doc, espacio)
        self.assertEqual(self.doc.UndoCount, undo_antes + 1,
                         "el dossier debe ser una sola transaccion")
        self.doc.undo()
        self.doc.recompute()
        self.assertEqual(len(self.doc.Objects), antes)

    def test_espacio_vacio_no_genera_hojas(self):
        espacio = make_espacio({"nombre": "ESPACIO_Vacio"})
        self.doc.recompute()
        self.assertEqual(D.generar_dossier(self.doc, espacio), [])


class WorkflowCompletoTests(unittest.TestCase):
    """Espacio -> lista de corte -> dossier -> guardar -> reabrir -> dossier."""

    def test_flujo_completo_sobrevive_a_guardar_y_reabrir(self):
        import tempfile
        doc = App.newDocument("VDO_Workflow")
        doc.UndoMode = 1
        csv_path = tempfile.mktemp(suffix=".csv", dir="/tmp")
        ruta = tempfile.mktemp(suffix=".FCStd", dir="/tmp")
        try:
            espacio, _coco = construir_escenario(doc)
            piezas_antes = E.extraer_piezas_del_documento("todo")
            self.assertTrue(piezas_antes, "la lista de corte debe tener piezas")
            E.generar_csv_opencutlist(piezas_antes, csv_path)
            with open(csv_path, encoding="utf-8") as fh:
                self.assertGreater(len(fh.read().splitlines()), 1)

            self.assertEqual(len(D.generar_dossier(doc, espacio)), 2)

            doc.saveAs(ruta)
            App.closeDocument(doc.Name)

            doc2 = App.openDocument(ruta)
            try:
                espacios = [o for o in doc2.Objects
                            if getattr(o, "VDO_Tipo", "") == "EspacioFeature"]
                self.assertEqual(len(espacios), 1)
                self.assertEqual(float(espacios[0].NivelPiso), -150.0)
                piezas_despues = E.extraer_piezas_del_documento("todo")
                self.assertEqual(len(piezas_despues), len(piezas_antes))
                self.assertEqual(len(D.generar_dossier(doc2, espacios[0])), 2)
            finally:
                App.closeDocument(doc2.Name)
        finally:
            for f in (csv_path, ruta):
                if os.path.exists(f):
                    os.remove(f)


class FachadasTests(unittest.TestCase):
    """Acción mostrar/ocultar fachadas (3D) y su uso en el dossier."""

    def setUp(self):
        self.doc = App.newDocument("VDO_Test_Fachadas")
        self.doc.UndoMode = 1

    def tearDown(self):
        try:
            App.closeDocument(self.doc.Name)
        except Exception:
            pass

    def _frente(self, coco):
        frente = self.doc.addObject("Part::Box", "Frente_Cajon")
        frente.Length, frente.Width, frente.Height = 500, 18, 150
        frente.addProperty("App::PropertyString", "VDO_Rol", "VDO")
        frente.VDO_Rol = "fachada"
        coco.Hijos = list(coco.Hijos) + [frente]
        self.doc.recompute()
        return frente

    def test_detecta_frente_por_rol(self):
        espacio, coco = construir_escenario(self.doc)
        frente = self._frente(coco)
        self.assertTrue(F.es_fachada(frente))
        self.assertFalse(F.es_fachada(coco))
        self.assertIn(frente.Name, [f.Name for f in F.fachadas_de(coco)])

    def test_alternar_oculta_y_vuelve_a_mostrar(self):
        espacio, coco = construir_escenario(self.doc)
        frente = self._frente(coco)
        n, visibles = F.alternar_fachadas(self.doc)
        self.assertEqual((n, visibles), (1, False))
        self.assertFalse(frente.Visibility)
        n, visibles = F.alternar_fachadas(self.doc)
        self.assertEqual((n, visibles), (1, True))
        self.assertTrue(frente.Visibility)

    def test_ficha_vanos_sin_frente_y_cerrado_con_frente(self):
        espacio, coco = construir_escenario(self.doc)
        frente = self._frente(coco)
        paginas = D.generar_dossier(self.doc, espacio)
        ficha = [p for p in paginas if p.Name.startswith("Dossier_4")][0]
        por_vista = {v.Name.split("_")[-1]: v for v in ficha.Views
                     if v.isDerivedFrom("TechDraw::DrawViewPart")}
        self.assertNotIn(frente.Name, [o.Name for o in por_vista["casco"].Source])
        self.assertNotIn(frente.Name, [o.Name for o in por_vista["vanos"].Source])
        self.assertIn(frente.Name, [o.Name for o in por_vista["cerrado"].Source])


if __name__ == "__main__":
    unittest.main()
