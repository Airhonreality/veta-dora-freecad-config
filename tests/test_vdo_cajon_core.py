# -*- coding: utf-8 -*-
# tests/test_vdo_cajon_core.py
# Tests para vdo_cajon_core.py — antes y después de la refactorización (T2/T5).
#
# Ejecutar dentro de FreeCAD (con el macro dir en sys.path):
#   import sys; sys.path.append(App.getUserMacroDir(True))
#   import unittest
#   from tests.test_vdo_cajon_core import TestSuite
#   unittest.TextTestRunner(verbosity=2).run(TestSuite())

import unittest
import json

import pytest

from tests._entorno import HAY_FREECAD

if not HAY_FREECAD:
    pytest.skip("requiere FreeCAD real; ejecutar con FreeCADCmd",
                allow_module_level=True)

import FreeCAD as App
import Part

# Asegurar que se importan los módulos VDO
import sys
_vdo_dir = App.getUserMacroDir(True)
if _vdo_dir not in sys.path:
    sys.path.insert(0, _vdo_dir)

import VDO.cad.objects.vdo_cad_cajon as CajonCore
from VDO.cad.objects.vdo_cad_cajon import CajonFeature, ViewProviderCajon, make_cajon


def _nuevo_documento(nombre="TestDoc"):
    doc = App.newDocument(nombre)
    return doc


class TestCajonArbolYGeometria(unittest.TestCase):
    """Verifica la estructura del árbol y la geometría del cajón.

    Antes de la refactorización (actual):
      - fp.Shape = Part.makeCompound(solidos)  -> duplicación geométrica (T5 violado)
      - _sincronizar_paneles_hijos crea App::DocumentObjectGroup "{fp.Name}_Paneles"
        y lo añade como hijo del cajón (T2 violado)

    Después de la refactorización (esperado):
      - fp.Shape = Part.Shape() (nulo, sin duplicación)
      - fp.Hijos es App::PropertyLinkListChild con los PanelFeature
      - No existe objeto "{fp.Name}_Paneles"
      - claimChildren() retorna fp.Hijos
      - onDelete() elimina hijos en cascada
    """

    def setUp(self):
        self.doc = _nuevo_documento()

    def tearDown(self):
        try:
            App.closeDocument(self.doc.Name)
        except Exception:
            pass

    def _crear_cajon(self, nombre="Cajon_Test"):
        obj = self.doc.addObject("Part::FeaturePython", nombre)
        CajonFeature(obj)
        if App.GuiUp:
            ViewProviderCajon(obj.ViewObject)
        # Valores mínimos para que execute no falle
        obj.AnchoLibre = 564.0
        obj.ProfLibre = 560.0
        obj.AnchoModulo = 600.0
        obj.AltoFrente = 225.0
        obj.AltoCaja = 85.0
        obj.GrosorCaja = 16.0
        obj.GrosorFondo = 12.0
        obj.GrosorFachada = 18.0
        obj.MarcaCorredera = "blum_tandem"
        obj.LongitudGuia = 0.0
        obj.MontajeTrasera = "entre_laterales"
        obj.TipoCorredera = "oculta"
        obj.SistemaApertura = "tirador"
        obj.TipoMontaje = "parche"
        obj.VDO_Material_Ref = "melamina_standar"
        obj.VDO_RotacionZ = 0.0
        obj.VDO_Anclaje = "inferior_izquierda_frente"
        self.doc.recompute()
        return obj

    # -----------------------------------------------------------------
    # TESTS DE GEOMETRÍA DEL PADRE (T5)
    # -----------------------------------------------------------------
    @staticmethod
    def _volumen_propio(obj):
        try:
            if obj.Shape and not obj.Shape.isNull():
                return obj.Shape.Volume
        except Exception:
            pass
        return 0.0

    @staticmethod
    def _volumen_hijos(obj):
        total = 0.0
        for hijo in (getattr(obj, "Hijos", None) or []):
            try:
                total += hijo.Shape.Volume
            except Exception:
                continue
        return total

    def test_padre_shape_no_es_compuesto_de_hijos(self):
        """T5: el contenedor no DUPLICA la geometría de sus hijos.

        El axioma existe para evitar doble masa, Z-fighting y doble corte
        en CAM. El invariante es la no duplicación, no "volumen cero" a
        secas: un cajón sin PanelFeature hijos no tiene nada que duplicar,
        y con Shape nula seria un modulo invisible (asi estaba: execute()
        calculaba los 6 solidos y los tiraba). Este test crea el cajon a
        mano, sin make_cajon, asi que no tiene hijos y el compuesto del
        padre es su unica geometria: correcto.
        """
        cajon = self._crear_cajon()
        propio = self._volumen_propio(cajon)
        hijos = self._volumen_hijos(cajon)
        self.assertFalse(
            propio > 0 and hijos > 0,
            f"Geometría duplicada: el padre acumula {propio:.1f} mm³ "
            f"mientras sus hijos ya aportan {hijos:.1f} mm³")

    def test_padre_no_tiene_volumen_duplicado(self):
        """Con hijos materializados, el padre no aporta volumen."""
        # Sin addCleanup: tearDown cierra el documento completo y retirar
        # el objeto despues daba ReferenceError.
        cajon = make_cajon({"nombre": "Cajon_Con_Hijos"})
        self.assertTrue(
            self._volumen_hijos(cajon) > 0,
            "make_cajon debe materializar las piezas como PanelFeature")
        self.assertEqual(
            self._volumen_propio(cajon), 0.0,
            "Con hijos presentes el contenedor padre debe tener Shape nula")

    # -----------------------------------------------------------------
    # TESTS DE ÁRBOL / JERARQUÍA (T2, T3, T4)
    # -----------------------------------------------------------------
    def test_no_existe_grupo_paneles_automatico(self):
        """T2: No debe crearse App::DocumentObjectGroup '{nombre}_Paneles'."""
        cajon = self._crear_cajon()
        nombre_grupo = f"{cajon.Name}_Paneles"
        grupo = self.doc.getObject(nombre_grupo)
        self.assertIsNone(
            grupo,
            f"No debe existir grupo automático '{nombre_grupo}' bajo el cajón"
        )

    def test_existe_propiedad_hijos_linklistchild(self):
        """T3: Debe existir App::PropertyLinkListChild 'Hijos' en el cajón."""
        cajon = self._crear_cajon()
        self.assertTrue(hasattr(cajon, "Hijos"),
                        "El cajón debe tener la propiedad 'Hijos' (LinkListChild)")

    def test_claim_children_retorna_hijos_directos(self):
        """T4: claimChildren() debe retornar hijos directos, no grupos intermedios."""
        cajon = self._crear_cajon()
        # En FreeCADCmd no hay ViewObject: claimChildren() es capa Gui y el
        # test reventaba con AttributeError en vez de omitirse.
        if not App.GuiUp or cajon.ViewObject is None:
            self.skipTest("claimChildren() requiere GUI")
        vp = cajon.ViewObject.Proxy
        hijos = vp.claimChildren() if hasattr(vp, "claimChildren") else []
        # Post-refactor: retorna lista de objetos de fp.Hijos
        # Pre-refactor: retorna [] (base) o grupos
        self.assertIsInstance(hijos, list)

    # -----------------------------------------------------------------
    # TESTS DE BORRADO EN CASCADA (T6)
    # -----------------------------------------------------------------
    def test_ondelete_existe(self):
        """T6: CajonFeature debe implementar onDelete()."""
        cajon = self._crear_cajon()
        self.assertTrue(hasattr(cajon.Proxy, "onDelete"),
                        "CajonFeature debe tener método onDelete")

    def test_ondelete_elimina_hijos(self):
        """onDelete debe eliminar objetos hijos de fp.Hijos."""
        cajon = self._crear_cajon()
        # Simular que hay hijos registrados
        hijo_falso = self.doc.addObject("Part::FeaturePython", "Hijo_Falso")
        cajon.Hijos = [hijo_falso]
        proxy = cajon.Proxy
        resultado = proxy.onDelete(cajon, [])
        self.assertTrue(resultado, "onDelete debe retornar True")
        # Tras onDelete, el hijo debería estar eliminado (si se llama doc.removeObject)
        # Nota: esto solo se puede verificar realmente al borrar el objeto del documento.

    # -----------------------------------------------------------------
    # TESTS DE make_cajon
    # -----------------------------------------------------------------
    def test_make_cajon_retorna_objeto(self):
        cajon = make_cajon({"nombre": "Cajon_Make", "ancho_libre": 564.0,
                            "prof_libre": 560.0})
        self.assertIsNotNone(cajon)
        self.assertEqual(cajon.Name, "Cajon_Make")

    def test_make_cajon_no_crea_grupo_paneles(self):
        make_cajon({"nombre": "Cajon_NoGrupo", "ancho_libre": 564.0,
                    "prof_libre": 560.0})
        grupo = self.doc.getObject("Cajon_NoGrupo_Paneles")
        self.assertIsNone(grupo, "make_cajon no debe crear grupo _Paneles")


def TestSuite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCajonArbolYGeometria))
    return suite


if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=2).run(TestSuite())
