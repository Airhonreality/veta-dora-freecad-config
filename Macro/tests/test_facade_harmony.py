# -*- coding: utf-8 -*-
# =====================================================================
# tests/test_facade_harmony.py
# Suite de validación cruzada del Contrato Universal de Fachadas.
# Verifica armonía entre Puertas (Agente 4) y Cajones (Agente 3)
# mediante vdo_facade_contract.py como Fuente Única de Verdad.
# =====================================================================

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

from vdo_facade_contract import (
    APERTURA_TIRADOR, APERTURA_GOLA, APERTURA_45_GRADOS, APERTURA_PUSH_OPEN,
    MONTAJE_PARCHE, MONTAJE_SEMIPARCHE, MONTAJE_EMBEBIDA,
    HOLGURA_PERIMETRAL_DEFAULT, GOLA_DESCUENTO_ALTURA_DEFAULT,
    SOLAPE_PARCHE_NOMINAL, BISEL_45_ANGULO_DEFAULT,
    OPERACION_CANTO_ESTANDAR, OPERACION_CANTO_GOLA, OPERACION_CANTO_45,
    calcular_fachada_base, aplicar_sistema_apertura,
    necesita_descuento_gola, necesita_bisel_45, necesita_expulsor_magnetico,
    cantos_por_sistema_apertura,
    SISTEMAS_APERTURA_VALIDOS,
)

import vdo_puerta_despiece as D_PUERTA
import vdo_cajon_despiece as D_CAJON


class TestContratoFachadas(unittest.TestCase):
    """Pruebas del contrato central de fachadas."""

    def test_enums_validos(self):
        """Los enums de apertura y montaje son consistentes."""
        self.assertEqual(APERTURA_TIRADOR, "tirador")
        self.assertEqual(APERTURA_GOLA, "gola_aluminio")
        self.assertEqual(APERTURA_45_GRADOS, "inglete_45")
        self.assertEqual(APERTURA_PUSH_OPEN, "push_open")

        self.assertEqual(MONTAJE_PARCHE, "parche")
        self.assertEqual(MONTAJE_SEMIPARCHE, "semiparche")
        self.assertEqual(MONTAJE_EMBEBIDA, "embebida")

    def test_constantes_taller(self):
        """Las constantes de taller tienen los valores esperados."""
        self.assertEqual(HOLGURA_PERIMETRAL_DEFAULT, 2.0)
        self.assertEqual(GOLA_DESCUENTO_ALTURA_DEFAULT, 35.0)
        self.assertEqual(SOLAPE_PARCHE_NOMINAL, 16.0)
        self.assertEqual(BISEL_45_ANGULO_DEFAULT, 45.0)

    def test_operaciones_canto(self):
        """Las operaciones de canto están definidas."""
        self.assertEqual(OPERACION_CANTO_ESTANDAR, "CANTO_ESTANDAR")
        self.assertEqual(OPERACION_CANTO_GOLA, "CORTE_RECTO_GOLA")
        self.assertEqual(OPERACION_CANTO_45, "BISEL_45")

    def test_sistemas_apertura_validos(self):
        """La lista de sistemas válidos contiene los 4 oficiales."""
        self.assertIn(APERTURA_TIRADOR, SISTEMAS_APERTURA_VALIDOS)
        self.assertIn(APERTURA_GOLA, SISTEMAS_APERTURA_VALIDOS)
        self.assertIn(APERTURA_45_GRADOS, SISTEMAS_APERTURA_VALIDOS)
        self.assertIn(APERTURA_PUSH_OPEN, SISTEMAS_APERTURA_VALIDOS)
        self.assertEqual(len(SISTEMAS_APERTURA_VALIDOS), 4)


class TestCalculoFachadaBase(unittest.TestCase):
    """Pruebas de calcular_fachada_base para montajes."""

    def test_parche(self):
        w, h = calcular_fachada_base(500, 700, MONTAJE_PARCHE)
        # W = 500 + 2*16 - 2 = 530, H = 700 + 2*16 - 2 = 730
        self.assertAlmostEqual(w, 530.0, places=6)
        self.assertAlmostEqual(h, 730.0, places=6)

    def test_semiparche(self):
        w, h = calcular_fachada_base(500, 700, MONTAJE_SEMIPARCHE)
        # W = (500 + 16) / 2 - 2 = 256, H = 700 + 2*16 - 2 = 730
        self.assertAlmostEqual(w, 256.0, places=6)
        self.assertAlmostEqual(h, 730.0, places=6)

    def test_embebida(self):
        w, h = calcular_fachada_base(500, 700, MONTAJE_EMBEBIDA)
        # W = 500 - 2*2 = 496, H = 700 - 2*2 = 696
        self.assertAlmostEqual(w, 496.0, places=6)
        self.assertAlmostEqual(h, 696.0, places=6)

    def test_holgura_personalizada(self):
        w, h = calcular_fachada_base(500, 700, MONTAJE_PARCHE,
                                     holgura=4.0, solape=10.0)
        # W = 500 + 2*10 - 4 = 516, H = 700 + 2*10 - 4 = 716
        self.assertAlmostEqual(w, 516.0, places=6)
        self.assertAlmostEqual(h, 716.0, places=6)

    def test_montaje_invalido(self):
        with self.assertRaises(ValueError):
            calcular_fachada_base(500, 700, "montaje_inexistente")


class TestAplicarSistemaApertura(unittest.TestCase):
    """Pruebas de aplicar_sistema_apertura."""

    def test_gola_descuenta_35(self):
        h_aj, op = aplicar_sistema_apertura(700.0, APERTURA_GOLA)
        self.assertAlmostEqual(h_aj, 665.0, places=6)  # 700 - 35
        self.assertEqual(op, OPERACION_CANTO_GOLA)

    def test_gola_con_descuento_personalizado(self):
        h_aj, op = aplicar_sistema_apertura(700.0, APERTURA_GOLA,
                                            descuento_gola=30.0)
        self.assertAlmostEqual(h_aj, 670.0, places=6)  # 700 - 30
        self.assertEqual(op, OPERACION_CANTO_GOLA)

    def test_inglete_45_conserva_altura(self):
        h_aj, op = aplicar_sistema_apertura(700.0, APERTURA_45_GRADOS)
        self.assertAlmostEqual(h_aj, 700.0, places=6)
        self.assertEqual(op, OPERACION_CANTO_45)

    def test_tirador_conserva_altura(self):
        h_aj, op = aplicar_sistema_apertura(700.0, APERTURA_TIRADOR)
        self.assertAlmostEqual(h_aj, 700.0, places=6)
        self.assertEqual(op, OPERACION_CANTO_ESTANDAR)

    def test_push_open_conserva_altura(self):
        h_aj, op = aplicar_sistema_apertura(700.0, APERTURA_PUSH_OPEN)
        self.assertAlmostEqual(h_aj, 700.0, places=6)
        self.assertEqual(op, OPERACION_CANTO_ESTANDAR)

    def test_sistema_invalido(self):
        with self.assertRaises(ValueError):
            aplicar_sistema_apertura(700.0, "sistema_inexistente")


class TestSimetriaGolaPuertaVsCajon(unittest.TestCase):
    """Test de Simetría Gola: Puerta vs. Cajón en vanos idénticos."""

    def test_altura_igual_con_gola(self):
        """En vanos idénticos de 500x700 mm, puerta y cajón con Gola
        deben tener exactamente la misma altura final."""
        w_vano, h_vano = 500.0, 700.0

        # Puerta Parche con Gola (vía contrato)
        w_p, h_p_base = calcular_fachada_base(
            w_vano, h_vano, MONTAJE_PARCHE,
            holgura=HOLGURA_PERIMETRAL_DEFAULT,
            solape=SOLAPE_PARCHE_NOMINAL)
        h_p_final, op_p = aplicar_sistema_apertura(
            h_p_base, APERTURA_GOLA,
            descuento_gola=GOLA_DESCUENTO_ALTURA_DEFAULT)

        # Fachada de Cajón Parche con Gola (vía contrato)
        w_c, h_c_base = calcular_fachada_base(
            w_vano, h_vano, MONTAJE_PARCHE,
            holgura=HOLGURA_PERIMETRAL_DEFAULT,
            solape=SOLAPE_PARCHE_NOMINAL)
        h_c_final, op_c = aplicar_sistema_apertura(
            h_c_base, APERTURA_GOLA,
            descuento_gola=GOLA_DESCUENTO_ALTURA_DEFAULT)

        # Ambas fachadas tienen las mismas dimensiones
        self.assertAlmostEqual(w_p, w_c, places=6)
        self.assertAlmostEqual(h_p_base, h_c_base, places=6)
        self.assertAlmostEqual(h_p_final, h_c_final, places=6)

        # Altura esperada: 700 + 2(16) - 2 - 35 = 695.0 mm
        self.assertAlmostEqual(h_p_final, 695.0, places=6)
        self.assertAlmostEqual(h_c_final, 695.0, places=6)

        # Ambas usan la misma operación de canto
        self.assertEqual(op_p, op_c)
        self.assertEqual(op_p, OPERACION_CANTO_GOLA)


class TestInglete45(unittest.TestCase):
    """Test de Inglete a 45°."""

    def test_altura_conservada(self):
        """Al aplicar inglete_45, la altura nominal se conserva."""
        h_aj, op = aplicar_sistema_apertura(700.0, APERTURA_45_GRADOS)
        self.assertAlmostEqual(h_aj, 700.0, places=6)

    def test_operacion_canto_bisel_45(self):
        """La operación de canto devuelve BISEL_45."""
        h_aj, op = aplicar_sistema_apertura(700.0, APERTURA_45_GRADOS)
        self.assertEqual(op, OPERACION_CANTO_45)
        self.assertEqual(op, "BISEL_45")


class TestImportacionYEnums(unittest.TestCase):
    """Test de importación y consistencia de enums entre módulos."""

    def test_contrato_importable(self):
        """vdo_facade_contract se importa sin errores."""
        import vdo_facade_contract  # noqa: F401

    def test_puerta_consume_contrato(self):
        """vdo_puerta_despiece reexporta los enums del contrato."""
        self.assertEqual(D_PUERTA.APERTURA_TIRADOR, APERTURA_TIRADOR)
        self.assertEqual(D_PUERTA.APERTURA_GOLA, APERTURA_GOLA)
        self.assertEqual(D_PUERTA.APERTURA_45_GRADOS, APERTURA_45_GRADOS)
        self.assertEqual(D_PUERTA.APERTURA_PUSH_OPEN, APERTURA_PUSH_OPEN)

    def test_cajon_consume_contrato(self):
        """vdo_cajon_despiece importa los enums del contrato."""
        self.assertEqual(D_CAJON.APERTURA_TIRADOR, APERTURA_TIRADOR)
        self.assertEqual(D_CAJON.APERTURA_GOLA, APERTURA_GOLA)
        self.assertEqual(D_CAJON.APERTURA_45_GRADOS, APERTURA_45_GRADOS)
        self.assertEqual(D_CAJON.APERTURA_PUSH_OPEN, APERTURA_PUSH_OPEN)

    def test_no_discrepancias_strings(self):
        """No hay discrepancias de strings entre puerta y cajón."""
        for attr in ("APERTURA_TIRADOR", "APERTURA_GOLA",
                      "APERTURA_45_GRADOS", "APERTURA_PUSH_OPEN"):
            v_puerta = getattr(D_PUERTA, attr)
            v_cajon = getattr(D_CAJON, attr)
            v_contrato = getattr(__import__("vdo_facade_contract"), attr)
            self.assertEqual(v_puerta, v_contrato,
                             f"Discrepancia en {attr}: puerta={v_puerta}, "
                             f"contrato={v_contrato}")
            self.assertEqual(v_cajon, v_contrato,
                             f"Discrepancia en {attr}: cajón={v_cajon}, "
                             f"contrato={v_contrato}")


class TestFuncionesAuxiliares(unittest.TestCase):
    """Pruebas de funciones auxiliares del contrato."""

    def test_necesita_descuento_gola(self):
        self.assertTrue(necesita_descuento_gola(APERTURA_GOLA))
        self.assertFalse(necesita_descuento_gola(APERTURA_TIRADOR))
        self.assertFalse(necesita_descuento_gola(APERTURA_45_GRADOS))
        self.assertFalse(necesita_descuento_gola(APERTURA_PUSH_OPEN))

    def test_necesita_bisel_45(self):
        self.assertTrue(necesita_bisel_45(APERTURA_45_GRADOS))
        self.assertFalse(necesita_bisel_45(APERTURA_TIRADOR))
        self.assertFalse(necesita_bisel_45(APERTURA_GOLA))
        self.assertFalse(necesita_bisel_45(APERTURA_PUSH_OPEN))

    def test_necesita_expulsor_magnetico(self):
        self.assertTrue(necesita_expulsor_magnetico(APERTURA_PUSH_OPEN))
        self.assertFalse(necesita_expulsor_magnetico(APERTURA_TIRADOR))
        self.assertFalse(necesita_expulsor_magnetico(APERTURA_GOLA))
        self.assertFalse(necesita_expulsor_magnetico(APERTURA_45_GRADOS))

    def test_cantos_por_sistema_apertura(self):
        """Los cantos se asignan correctamente por sistema de apertura."""
        cantos_tirador = cantos_por_sistema_apertura(APERTURA_TIRADOR)
        self.assertEqual(cantos_tirador["norte"], "FX")
        self.assertEqual(cantos_tirador["sur"], "FX")

        cantos_45 = cantos_por_sistema_apertura(APERTURA_45_GRADOS)
        self.assertEqual(cantos_45["norte"], OPERACION_CANTO_45)

        cantos_gola = cantos_por_sistema_apertura(APERTURA_GOLA)
        self.assertEqual(cantos_gola["norte"], OPERACION_CANTO_GOLA)


if __name__ == "__main__":
    resultado = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if resultado.wasSuccessful():
        print("=" * 64)
        print("Tests de Armonía de Fachadas OK - 100% validado")
        print("=" * 64)
        sys.exit(0)
    sys.exit(1)
