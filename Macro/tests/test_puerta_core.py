# -*- coding: utf-8 -*-
"""Pruebas unitarias del submódulo de Puertas y Cierres (L2).

Capa 0 (despiece): fórmulas de corte, Newtons, holguras, cazoletas.
Capa 2 (core): PuertaFeature (Part::FeaturePython) sin depender de GUI.
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

import vdo_puerta_despiece as D


class DespieceBatienteTests(unittest.TestCase):
    """Pruebas de fórmulas de corte para puertas batientes."""

    def test_dimensiones_parche(self):
        res = D.calcular_dimensiones_batiente(600, 800, "parche")
        # W = 600 + 2*8 - 2 = 614, H = 800 + 2*8 - 2 = 814
        self.assertAlmostEqual(res["W"], 614.0, places=6)
        self.assertAlmostEqual(res["H"], 814.0, places=6)

    def test_dimensiones_semiparche(self):
        res = D.calcular_dimensiones_batiente(600, 800, "semiparche")
        # W = (600 + 8) / 2 - 2 = 302, H = 800 + 2*8 - 2 = 814 (contrato)
        self.assertAlmostEqual(res["W"], 302.0, places=6)
        self.assertAlmostEqual(res["H"], 814.0, places=6)

    def test_dimensiones_embebida(self):
        res = D.calcular_dimensiones_batiente(600, 800, "embebida")
        # W = 600 - 2*2 = 596, H = 800 - 2*2 = 796
        self.assertAlmostEqual(res["W"], 596.0, places=6)
        self.assertAlmostEqual(res["H"], 796.0, places=6)

    def test_cantidad_bisagras(self):
        self.assertEqual(D.cantidad_bisagras(900), 2)
        self.assertEqual(D.cantidad_bisagras(1000), 3)
        self.assertEqual(D.cantidad_bisagras(1499), 3)
        self.assertEqual(D.cantidad_bisagras(1500), 4)
        self.assertEqual(D.cantidad_bisagras(2000), 4)

    def test_posiciones_cazoleta_2_bisagras(self):
        zs = D.posiciones_cazoleta(800, n_bisagras=2)
        self.assertEqual(len(zs), 2)
        self.assertAlmostEqual(zs[0], 100.0, places=6)
        self.assertAlmostEqual(zs[1], 700.0, places=6)

    def test_posiciones_cazoleta_3_bisagras(self):
        zs = D.posiciones_cazoleta(1200, n_bisagras=3)
        self.assertEqual(len(zs), 3)
        self.assertAlmostEqual(zs[0], 100.0, places=6)
        self.assertAlmostEqual(zs[1], 600.0, places=6)
        self.assertAlmostEqual(zs[2], 1100.0, places=6)

    def test_posiciones_cazoleta_4_bisagras(self):
        zs = D.posiciones_cazoleta(1800, n_bisagras=4)
        self.assertEqual(len(zs), 4)
        self.assertAlmostEqual(zs[0], 100.0, places=6)
        self.assertAlmostEqual(zs[3], 1700.0, places=6)
        paso = (1800 - 200) / 3
        self.assertAlmostEqual(zs[1], 100 + paso, places=6)
        self.assertAlmostEqual(zs[2], 100 + 2 * paso, places=6)

    def test_cota_cazoleta(self):
        self.assertAlmostEqual(D.COTA_CAZOLETA_X, 21.5, places=6)

    def test_bisagras_para_puerta(self):
        bis = D.bisagras_para_puerta(800, "parche")
        self.assertEqual(bis["n_bisagras"], 2)
        self.assertEqual(bis["tipo_montaje"], "parche")
        self.assertAlmostEqual(bis["cota_x"], 21.5, places=6)
        self.assertAlmostEqual(bis["diametro_cazoleta"], 35.0, places=6)
        self.assertAlmostEqual(bis["profundidad_cazoleta"], 11.5, places=6)
        self.assertEqual(len(bis["posiciones_z"]), 2)


class DespieceBasculanteTests(unittest.TestCase):
    """Pruebas de cálculo de Newtons para puertas basculantes."""

    def test_masa_puerta(self):
        M = D.masa_puerta(600, 800)
        # M = 0.6 * 0.8 * 0.018 * 720 = 6.2208 kg
        self.assertAlmostEqual(M, 6.2208, places=4)

    def test_fuerza_piston(self):
        F = D.fuerza_piston_teorica(600, 800)
        self.assertGreater(F, 0)

    def test_piston_recomendado(self):
        comercial, F = D.piston_recomendado(600, 800)
        self.assertIn(comercial, [60, 80, 100, 120, 150])
        self.assertGreaterEqual(comercial, F - 1e-9)

    def test_descripcion_piston(self):
        texto, comercial, F = D.descripcion_piston(600, 800)
        self.assertIn("N", texto)
        self.assertIn("unidades", texto)
        self.assertEqual(comercial, D.piston_recomendado(600, 800)[0])


class DespieceCorredizaTests(unittest.TestCase):
    """Pruebas de cálculo de puertas corredizas."""

    def test_corrediza_d52(self):
        res = D.calcular_corrediza(1500, 2000, "closet", n_hojas=2)
        self.assertEqual(res["sku"], "DUC-KIT-D52")
        self.assertAlmostEqual(res["alto_hoja"], 1967.0, places=6)
        self.assertAlmostEqual(res["ancho_hoja"], 767.5, places=6)
        self.assertEqual(len(res["hojas"]), 2)

    def test_corrediza_al1535(self):
        res = D.calcular_corrediza(800, 600, "alacena", n_hojas=2)
        self.assertEqual(res["sku"], "DUC-AL-1535-MAD")
        self.assertAlmostEqual(res["alto_hoja"], 590.0, places=6)
        self.assertAlmostEqual(res["ancho_hoja"], 412.5, places=6)


class SistemasAperturaTests(unittest.TestCase):
    """Pruebas de sistemas de apertura."""

    def test_ajuste_altura_tirador(self):
        H, desc = D.ajuste_altura_apertura("tirador", 800)
        self.assertEqual(H, 800)
        self.assertEqual(desc, 0.0)

    def test_ajuste_altura_gola(self):
        H, desc = D.ajuste_altura_apertura("perfil_gola_aluminio", 800)
        self.assertEqual(H, 765)
        self.assertEqual(desc, 35.0)

    def test_ajuste_altura_push(self):
        H, desc = D.ajuste_altura_apertura("push_open_mecanico", 800)
        self.assertEqual(H, 800)
        self.assertEqual(desc, 0.0)

    def test_necesita_expulsor(self):
        self.assertTrue(D.necesita_expulsor_magnetico("push_open_mecanico"))
        self.assertFalse(D.necesita_expulsor_magnetico("tirador"))

    def test_necesita_cantos_45(self):
        self.assertTrue(D.necesita_cantos_45("fachada_a_45_grados"))
        self.assertFalse(D.necesita_cantos_45("tirador"))


class CoreImportTests(unittest.TestCase):
    """Pruebas de importación del núcleo (sin GUI)."""

    @unittest.skipUnless(
        importlib.util.find_spec("FreeCAD") is not None,
        "FreeCAD no disponible en este entorno")
    def test_import_core(self):
        import vdo_puerta_core  # noqa: F401

    @unittest.skipUnless(
        importlib.util.find_spec("FreeCAD") is not None,
        "FreeCAD no disponible en este entorno")
    def test_make_puerta_existe(self):
        from vdo_puerta_core import make_puerta
        self.assertTrue(callable(make_puerta))


if __name__ == "__main__":
    resultado = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if resultado.wasSuccessful():
        print("Tests de Puertas y Cierres (L2) OK - 100% validado")
        sys.exit(0)
    sys.exit(1)
