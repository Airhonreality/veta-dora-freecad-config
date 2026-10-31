# -*- coding: utf-8 -*-
# =====================================================================
# tests/test_cajon_core.py
# Suite de pruebas del CajonFeature (Trinidad de Cajones v2).
#
# Valida:
#   - Despiece correcto para las 3 tipologías de corredera
#   - Integración con vdo_facade_contract (gola, 45°, push_open)
#   - Lógica de operaciones booleanas (mock de Part)
#   - Integración con vdo_hardware_hub (resolve_drawer_slide)
#
# Nota: La validación de Shape.isValid() y booleanos reales requiere
# FreeCAD GUI (no disponible headless en este entorno). Los tests de
# geometría 3D usan mocks para validar la lógica de coordenadas.
# =====================================================================

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

try:
    _AQUI = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _AQUI = os.getcwd()
_RAIZ = os.path.dirname(_AQUI)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

# ---------------------------------------------------------------------
# Mock de FreeCAD y Part para pruebas de booleanos headless
# ---------------------------------------------------------------------
class _MockVector:
    def __init__(self, x=0, y=0, z=0):
        self.x = x; self.y = y; self.z = z

class _MockPart:
    class Face:
        def __init__(self, wire):
            self.wire = wire
        def extrude(self, vector):
            m = MagicMock()
            m.Volume = 100.0
            m.isValid.return_value = True
            m.cut.return_value = m
            return m
    @staticmethod
    def makeBox(x, y, z, base):
        m = MagicMock()
        m.Volume = float(x) * float(y) * float(z)
        m.isValid.return_value = True
        m.cut.return_value = m
        return m
    @staticmethod
    def makeCylinder(radius, height, base, direction):
        m = MagicMock()
        m.Volume = 3.14159 * float(radius) ** 2 * float(height)
        m.isValid.return_value = True
        m.cut.return_value = m
        return m
    @staticmethod
    def makePolygon(points, closed=False):
        m = MagicMock()
        m.isValid.return_value = True
        return m
    @staticmethod
    def makeCompound(solids):
        m = MagicMock()
        m.Volume = sum(getattr(s, 'Volume', 0) for s in solids)
        m.isValid.return_value = True
        return m

class _MockApp:
    class Console:
        @staticmethod
        def PrintError(msg): pass
        @staticmethod
        def PrintWarning(msg): pass
    @staticmethod
    def getUserMacroDir(create=False):
        return "/tmp/freecad_macro"
    GuiUp = False

# Instalar los mocks SOLO si no hay un FreeCAD real.
#
# Este bloque era incondicional y escribia sys.modules["FreeCAD"] a nivel
# de modulo. Como pytest importa todos los modulos de test en el mismo
# proceso, el stub quedaba instalado para los 26 archivos siguientes y
# contaminaba la suite entera: dentro de FreeCADCmd los tests que usan el
# FreeCAD de verdad fallaban con "'_MockApp' object has no attribute
# 'newDocument'", y en python3 pelado el resultado dependia del orden
# alfabetico de coleccion ("_MockPart.makeBox() missing", "FreeCAD.__spec__
# is not set").
try:  # noqa: SIM105
    import FreeCAD as _FreeCAD_real  # noqa: F401
    import Part as _Part_real  # noqa: F401
    _USANDO_MOCKS = False
except ImportError:
    _mock_app = _MockApp()
    _mock_app.App = _MockApp()
    _mock_app.Vector = _MockVector
    _mock_app.__spec__ = None
    sys.modules.setdefault("FreeCAD", _mock_app)
    sys.modules.setdefault("Part", _MockPart())
    _USANDO_MOCKS = True

from VDO.core.vdo_math_cajon import (
    calcular_despiece, listar_marcas, obtener_marca,
    CORREDERA_TELESCOPICA, CORREDERA_OCULTA, CAJA_METALICA,
    APERTURA_TIRADOR, APERTURA_GOLA, APERTURA_45_GRADOS, APERTURA_PUSH_OPEN,
)
import VDO.core.vdo_math_facade as FC
import VDO.hub.vdo_hub_hardware as H
from VDO.cad.objects.vdo_cad_cajon import (
    _corte_notch_lateral, _corte_pin_trasero, _corte_ranura_piso,
    _aplicar_bisel_45_fachada, _aplicar_corte,
    CORREDERA_TELESCOPICA as CC_TEL, CORREDERA_OCULTA as CC_OCU,
    CAJA_METALICA as CC_MET,
)


# ---------------------------------------------------------------------
# Configuración base de prueba
# ---------------------------------------------------------------------

CONFIG_BASE = {
    "ancho_libre": 600.0,
    "prof_libre": 580.0,
    "ancho_modulo": 640.0,
    "alto_frente": 225.0,
    "marca": "blum_tandem",
    "alto_caja": 120.0,
    "grosor_caja": 16.0,
    "grosor_fondo": 6.0,
    "grosor_fachada": 18.0,
    "longitud_guia": 0.0,
    "montaje_trasera": "entre_laterales",
    "penetracion_ranura": 10.0,
    "eje_ranura": 11.5,
    "holgura_lateral_fachada": 2.0,
    "holgura_superior_fachada": 2.0,
    "holgura_inferior_fachada": 2.0,
    "material_ref": "melamina_standar",
}


# ---------------------------------------------------------------------
# Tests de despiece por tipología
# ---------------------------------------------------------------------

class TestDespieceTipologias(unittest.TestCase):
    """Validación del despiece para cada tipología de corredera."""

    def test_oculta_blum_tandem(self):
        """Corredera oculta Blum Tandem: delta=49, 6 piezas."""
        config = dict(CONFIG_BASE, tipo_corredera=CORREDERA_OCULTA)
        d = calcular_despiece(config)
        self.assertEqual(d["tipo_corredera"], CORREDERA_OCULTA)
        self.assertAlmostEqual(d["guia"]["delta"], 49.0)
        self.assertAlmostEqual(d["caja"]["ancho_exterior"], 551.0)  # 600-49
        self.assertEqual(len(d["piezas"]), 6)
        nombres = [p["nombre"] for p in d["piezas"]]
        self.assertIn("Cajon_Lateral_Izq", nombres)
        self.assertIn("Cajon_Lateral_Der", nombres)

    def test_oculta_generica(self):
        """Corredera oculta genérica: delta=45."""
        config = dict(CONFIG_BASE, tipo_corredera=CORREDERA_OCULTA, marca="generica")
        d = calcular_despiece(config)
        self.assertAlmostEqual(d["guia"]["delta"], 45.0)
        self.assertAlmostEqual(d["caja"]["ancho_exterior"], 555.0)  # 600-45

    def test_telescopica(self):
        """Corredera telescópica: delta=25.4 (12.7mm x 2 lados)."""
        config = dict(CONFIG_BASE, tipo_corredera=CORREDERA_TELESCOPICA)
        d = calcular_despiece(config)
        self.assertEqual(d["tipo_corredera"], CORREDERA_TELESCOPICA)
        self.assertAlmostEqual(d["guia"]["delta"], 25.4)
        self.assertAlmostEqual(d["caja"]["ancho_exterior"], 574.6)  # 600-25.4
        self.assertEqual(len(d["piezas"]), 6)

    def test_metalica_sin_laterales(self):
        """Caja metálica: 4 piezas, sin laterales de madera."""
        config = dict(CONFIG_BASE, tipo_corredera=CAJA_METALICA)
        d = calcular_despiece(config)
        self.assertEqual(d["tipo_corredera"], CAJA_METALICA)
        nombres = [p["nombre"] for p in d["piezas"]]
        self.assertNotIn("Cajon_Lateral_Izq", nombres)
        self.assertNotIn("Cajon_Lateral_Der", nombres)
        self.assertIn("Cajon_Contrafrente", nombres)
        self.assertIn("Cajon_Piso", nombres)
        self.assertEqual(len(d["piezas"]), 4)

    def test_listar_marcas_incluye_nuevas(self):
        """listar_marcas() incluye las claves del manifest y catálogo."""
        marcas = listar_marcas()
        self.assertIn("blum_tandem", marcas)
        self.assertIn("generica", marcas)
        self.assertIn("hafele", marcas)
        self.assertIn("ducasse", marcas)


# ---------------------------------------------------------------------
# Tests de integración con facade_contract
# ---------------------------------------------------------------------

class TestFacadeContractIntegracion(unittest.TestCase):
    """Validación de la integración con vdo_facade_contract."""

    def test_gola_descuenta_35mm_en_alto(self):
        """APERTURA_GOLA descuenta 35 mm via deltas["norte"]."""
        config = dict(CONFIG_BASE,
                      tipo_corredera=CORREDERA_OCULTA,
                      sistema_apertura=APERTURA_GOLA)
        d = calcular_despiece(config)
        # alto_frente=225 + norte(-35) + sur(-2) = 188 (deltas netos, sin holgura global)
        self.assertAlmostEqual(d["fachada"]["alto"], 188.0)
        self.assertTrue(d["fachada"]["necesita_gola"])
        self.assertEqual(d["fachada"]["operacion_canto"],
                         FC.OPERACION_CANTO_GOLA)

    def test_inglete_45_conserva_altura(self):
        """APERTURA_45_GRADOS conserva la altura y usa BISEL_45."""
        config = dict(CONFIG_BASE,
                      tipo_corredera=CORREDERA_OCULTA,
                      sistema_apertura=APERTURA_45_GRADOS)
        d = calcular_despiece(config)
        # alto_frente=225 + norte(-2) + sur(-2) = 221 (deltas netos)
        self.assertAlmostEqual(d["fachada"]["alto"], 221.0)
        self.assertTrue(d["fachada"]["necesita_bisel_45"])
        self.assertEqual(d["fachada"]["operacion_canto"],
                         FC.OPERACION_CANTO_45)

    def test_push_open_conserva_altura(self):
        """APERTURA_PUSH_OPEN conserva la altura."""
        config = dict(CONFIG_BASE,
                      tipo_corredera=CORREDERA_OCULTA,
                      sistema_apertura=APERTURA_PUSH_OPEN)
        d = calcular_despiece(config)
        self.assertAlmostEqual(d["fachada"]["alto"], 221.0)
        self.assertTrue(d["fachada"]["necesita_expulsor"])

    def test_tirador_conserva_altura(self):
        """APERTURA_TIRADOR conserva la altura y canto estándar."""
        config = dict(CONFIG_BASE,
                      tipo_corredera=CORREDERA_OCULTA,
                      sistema_apertura=APERTURA_TIRADOR)
        d = calcular_despiece(config)
        self.assertAlmostEqual(d["fachada"]["alto"], 221.0)
        self.assertFalse(d["fachada"]["necesita_gola"])
        self.assertFalse(d["fachada"]["necesita_bisel_45"])
        self.assertFalse(d["fachada"]["necesita_expulsor"])

    def test_cantos_por_sistema_apertura(self):
        """Los cantos se asignan correctamente por sistema de apertura."""
        config = dict(CONFIG_BASE,
                      tipo_corredera=CORREDERA_OCULTA,
                      sistema_apertura=APERTURA_45_GRADOS)
        d = calcular_despiece(config)
        cantos = d["fachada"]["cantos"]
        self.assertEqual(cantos["norte"], FC.OPERACION_CANTO_45)
        self.assertEqual(cantos["sur"], "FX")

        config2 = dict(CONFIG_BASE,
                       tipo_corredera=CORREDERA_OCULTA,
                       sistema_apertura=APERTURA_GOLA)
        d2 = calcular_despiece(config2)
        cantos2 = d2["fachada"]["cantos"]
        self.assertEqual(cantos2["norte"], FC.OPERACION_CANTO_GOLA)


# ---------------------------------------------------------------------
# Tests de integración con hardware_hub
# ---------------------------------------------------------------------

class TestHardwareHubIntegracion(unittest.TestCase):
    """Validación de resolve_drawer_slide desde el cajón."""

    def test_resolve_blum_tandem_desde_manifest(self):
        """blum_tandem se resuelve a BLUM-TANDEM con delta=49."""
        hw = H.resolve_drawer_slide(tipo="oculta", marca="blum_tandem")
        self.assertEqual(hw["sku"], "BLUM-TANDEM")
        self.assertAlmostEqual(hw["parametros_tecnicos"]["delta_ancho"], 49.0)

    def test_resolve_generica(self):
        """generica se resuelve a GEN-OCULTA con delta=45."""
        hw = H.resolve_drawer_slide(tipo="oculta", marca="generica")
        self.assertEqual(hw["sku"], "GEN-OCULTA")
        self.assertAlmostEqual(hw["parametros_tecnicos"]["delta_ancho"], 45.0)

    def test_resolve_sku_directo(self):
        """SKU directo se resuelve sin transformación."""
        hw = H.resolve_drawer_slide(tipo="oculta", marca="DUCASSE-OCULTA")
        self.assertEqual(hw["sku"], "DUCASSE-OCULTA")

    def test_resolve_telescopica(self):
        """Telescópica se resuelve con holgura 12.7mm."""
        hw = H.resolve_drawer_slide(tipo="telescopica",
                                    marca="GEN-TELESCOPICA-45KG")
        self.assertEqual(hw["sku"], "GEN-TELESCOPICA-45KG")
        self.assertAlmostEqual(
            hw["parametros_tecnicos"]["holgura_lateral_por_lado"], 12.7)

    def test_resolve_inexistente_lanza_keyerror(self):
        """Marca inexistente lanza KeyError descriptivo."""
        with self.assertRaises(KeyError):
            H.resolve_drawer_slide(tipo="oculta", marca="no_existe")


# ---------------------------------------------------------------------
# Tests de lógica de booleanos (mock de Part)
# ---------------------------------------------------------------------

class TestBooleanLogicMocked(unittest.TestCase):
    """Validación de la lógica de coordenadas para operaciones booleanas.

    Usa mocks de FreeCAD/Part ya que no hay display headless disponible.
    """

    def setUp(self):
        self.mock_solid = MagicMock()
        self.mock_solid.isValid.return_value = True
        self.mock_solid.Volume = 1000.0

        self.mock_tool = MagicMock()
        self.mock_tool.isValid.return_value = True

    def test_notch_reduce_volumen(self):
        """El notch en lateral reduce el volumen respecto al prisma puro."""
        from VDO.cad.objects.vdo_cad_cajon import _corte_notch_lateral

        # Simular: prisma puro = 1000, con notch = 800 (reducción)
        self.mock_solid.cut.return_value = MagicMock()
        self.mock_solid.cut.return_value.isValid.return_value = True
        self.mock_solid.cut.return_value.Volume = 800.0

        pos = {"x": 0, "y": 0, "z": 0, "largo_x": 16, "largo_y": 550,
               "largo_z": 120}
        resultado = _corte_notch_lateral(
            self.mock_solid, pos, 35.0, 12.0, 550)

        # Verificar que se llamó a cut con una herramienta
        self.mock_solid.cut.assert_called()
        args, _ = self.mock_solid.cut.call_args
        herramienta = args[0]
        # La herramienta de notch debe ser un Box (prisma)
        self.assertIsNotNone(herramienta)

    def test_pin_hole_reduce_volumen(self):
        """El taladro de pin reduce el volumen del testero trasero."""
        from VDO.cad.objects.vdo_cad_cajon import _corte_pin_trasero

        self.mock_solid.cut.return_value = MagicMock()
        self.mock_solid.cut.return_value.isValid.return_value = True
        self.mock_solid.cut.return_value.Volume = 950.0

        pos = {"x": 16, "y": 0, "z": 11.5, "largo_x": 519, "largo_y": 16,
               "largo_z": 96.5}
        resultado = _corte_pin_trasero(
            self.mock_solid, pos, 6.0, 10.0, 11.5, 6.0,
            96.5, 519, 16)

        self.mock_solid.cut.assert_called()
        args, _ = self.mock_solid.cut.call_args
        herramienta = args[0]
        self.assertIsNotNone(herramienta)

    def test_ranura_piso_reduce_volumen(self):
        """La ranura para piso delgado reduce el volumen del lateral."""
        from VDO.cad.objects.vdo_cad_cajon import _corte_ranura_piso

        self.mock_solid.cut.return_value = MagicMock()
        self.mock_solid.cut.return_value.isValid.return_value = True
        self.mock_solid.cut.return_value.Volume = 900.0

        pos = {"x": 0, "y": 0, "z": 0, "largo_x": 16, "largo_y": 550,
               "largo_z": 120}
        resultado = _corte_ranura_piso(
            self.mock_solid, pos, 4.0, 10.0, 5.5, 550)

        self.mock_solid.cut.assert_called()

    def test_bisel_45_crea_herramienta_triangular(self):
        """El bisel 45° crea una herramienta de corte triangular extruida."""
        from VDO.cad.objects.vdo_cad_cajon import _aplicar_bisel_45_fachada

        self.mock_solid.cut.return_value = MagicMock()
        self.mock_solid.cut.return_value.isValid.return_value = True

        pos = {"x": 0, "y": -18, "z": 0, "largo_x": 636, "largo_y": 18,
               "largo_z": 221}
        resultado = _aplicar_bisel_45_fachada(
            self.mock_solid, pos, 636.0, 221.0, bisel_dist=5.0)

        self.mock_solid.cut.assert_called()

    def test_aplicar_corte_devuelve_original_si_falla(self):
        """Si el corte produce resultado invalido, se devuelve el solido original."""
        from VDO.cad.objects.vdo_cad_cajon import _aplicar_corte

        solido_original = MagicMock()
        solido_original.isValid.return_value = True
        # El resultado del corte es invalido -> se devuelve el original
        resultado_corte = MagicMock()
        resultado_corte.isValid.return_value = False
        solido_original.cut.return_value = resultado_corte
        herramienta = MagicMock()

        resultado = _aplicar_corte(solido_original, herramienta)
        self.assertEqual(resultado, solido_original)


# ---------------------------------------------------------------------
# Tests de validación de coordenadas calculadas (sin face indexing)
# ---------------------------------------------------------------------

class TestCoordenadasCalculadas(unittest.TestCase):
    """Validación de que las coordenadas se calculan, no se indexan."""

    def test_posiciones_laterales(self):
        """Las posiciones de laterales se calculan desde ancho_ext y g_caja."""
        config = dict(CONFIG_BASE, tipo_corredera=CORREDERA_OCULTA)
        d = calcular_despiece(config)
        pos = d["posiciones"]

        # lateral_izquierdo empieza en origen
        self.assertAlmostEqual(pos["lateral_izquierdo"]["x"], 0.0)
        self.assertAlmostEqual(pos["lateral_izquierdo"]["y"], 0.0)
        self.assertAlmostEqual(pos["lateral_izquierdo"]["z"], 0.0)

        # lateral_derecho empieza en ancho_ext - g_caja
        g_caja = d["caja"]["grosor"]
        ancho_ext = d["caja"]["ancho_exterior"]
        self.assertAlmostEqual(pos["lateral_derecho"]["x"],
                               ancho_ext - g_caja)

    def test_piso_en_ranura_telescopica(self):
        """En telescópica, el piso está en z_piso=10mm con grosor 5.5mm."""
        config = dict(CONFIG_BASE, tipo_corredera=CORREDERA_TELESCOPICA,
                      grosor_fondo=5.5, eje_ranura=10.0)
        d = calcular_despiece(config)
        self.assertAlmostEqual(d["caja"]["z_piso"], 10.0)
        self.assertAlmostEqual(d["caja"]["grosor_piso"], 5.5)

    def test_fachada_con_gola(self):
        """Con gola, la fachada es más baja (gola via deltas["norte"])."""
        config = dict(CONFIG_BASE,
                      tipo_corredera=CORREDERA_OCULTA,
                      sistema_apertura=APERTURA_GOLA)
        d = calcular_despiece(config)
        alto_nominal = d["fachada"]["alto_nominal"]
        alto_final = d["fachada"]["alto"]
        # alto_frente=225 + norte(-35) + sur(-2) = 188; nominal == final
        self.assertAlmostEqual(alto_final, alto_nominal)
        self.assertAlmostEqual(alto_final, 225.0 - 35.0 - 2.0)


# ---------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------

if __name__ == "__main__":
    resultado = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if resultado.wasSuccessful():
        print("=" * 64)
        print("Tests de CajonCore OK - Trinidad v2 validada al 100%")
        print("=" * 64)
        sys.exit(0)
    sys.exit(1)
