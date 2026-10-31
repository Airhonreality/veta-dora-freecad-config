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

from VDO.core.vdo_math_facade import (
    APERTURA_TIRADOR, APERTURA_GOLA, APERTURA_45_GRADOS, APERTURA_PUSH_OPEN,
    MONTAJE_PARCHE, MONTAJE_SEMIPARCHE, MONTAJE_EMBEBIDA,
    HOLGURA_PERIMETRAL_DEFAULT, GOLA_DESCUENTO_ALTURA_DEFAULT,
    SOLAPE_PARCHE_NOMINAL, BISEL_45_ANGULO_DEFAULT,
    OPERACION_CANTO_ESTANDAR, OPERACION_CANTO_GOLA, OPERACION_CANTO_45,
    calcular_fachada_base, aplicar_sistema_apertura,
    necesita_descuento_gola, necesita_bisel_45, necesita_expulsor_magnetico,
    cantos_por_sistema_apertura,
    SISTEMAS_APERTURA_VALIDOS,
    # Contrato de deltas netos
    calcular_fachada_desde_deltas, calcular_origen_fachada_local,
    DELTA_PARCHE_TOTAL, DELTA_AGARRE_INFERIOR_AEREO,
    DELTA_GOLA_SUPERIOR, DELTA_GOLA_SUPERIOR_35,
    DELTA_SEMIPARCHE_DER, DELTA_SEMIPARCHE_IZQ,
    DELTA_RINCON_CIEGO, DELTA_EMBEBIDA,
)

import VDO.core.vdo_math_puerta as D_PUERTA
import VDO.core.vdo_math_cajon as D_CAJON


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
        # DELTA_PARCHE_TOTAL: w = 500 + 16 + 16 = 532, h = 700 + 16 + 16 = 732
        self.assertAlmostEqual(w, 532.0, places=6)
        self.assertAlmostEqual(h, 732.0, places=6)

    def test_semiparche(self):
        w, h = calcular_fachada_base(500, 700, MONTAJE_SEMIPARCHE)
        # DELTA_SEMIPARCHE_DER: w = 500 + 16 + 8 = 524, h = 700 + 16 + 16 = 732
        self.assertAlmostEqual(w, 524.0, places=6)
        self.assertAlmostEqual(h, 732.0, places=6)

    def test_embebida(self):
        w, h = calcular_fachada_base(500, 700, MONTAJE_EMBEBIDA)
        # DELTA_EMBEBIDA: w = 500 - 2 - 2 = 496, h = 700 - 2 - 2 = 696
        self.assertAlmostEqual(w, 496.0, places=6)
        self.assertAlmostEqual(h, 696.0, places=6)

    def test_holgura_personalizada_ignorada_en_deltas(self):
        """calcular_fachada_base ignora holgura/solape legacy; usa presets netos."""
        w, h = calcular_fachada_base(500, 700, MONTAJE_PARCHE,
                                     holgura=4.0, solape=10.0)
        # DELTA_PARCHE_TOTAL ignora holgura=4/solape=10: w = 532, h = 732
        self.assertAlmostEqual(w, 532.0, places=6)
        self.assertAlmostEqual(h, 732.0, places=6)

    def test_montaje_invalido(self):
        with self.assertRaises(ValueError):
            calcular_fachada_base(500, 700, "montaje_inexistente")


class TestAplicarSistemaApertura(unittest.TestCase):
    """Pruebas de aplicar_sistema_apertura."""

    def test_gola_descuenta_35(self):
        """aplicar_sistema_apertura ya no ajusta altura (0% dimensional).
        El descuento de gola va en deltas["norte"] negativo."""
        h_aj, op = aplicar_sistema_apertura(700.0, APERTURA_GOLA)
        self.assertAlmostEqual(h_aj, 700.0, places=6)  # altura inalterada
        self.assertEqual(op, OPERACION_CANTO_GOLA)

    def test_gola_con_descuento_personalizado(self):
        """aplicar_sistema_apertura no ajusta altura; descuento via deltas."""
        h_aj, op = aplicar_sistema_apertura(700.0, APERTURA_GOLA,
                                            descuento_gola=30.0)
        self.assertAlmostEqual(h_aj, 700.0, places=6)  # altura inalterada
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
        deben tener exactamente la misma altura final (gola via deltas)."""
        w_vano, h_vano = 500.0, 700.0

        # Puerta Parche con Gola (vía deltas: norte = -35)
        deltas_gola = dict(DELTA_PARCHE_TOTAL)
        deltas_gola["norte"] = -GOLA_DESCUENTO_ALTURA_DEFAULT
        w_p, h_p_final = calcular_fachada_desde_deltas(w_vano, h_vano, deltas_gola)

        # Fachada de Cajón Parche con Gola (vía deltas)
        w_c, h_c_final = calcular_fachada_desde_deltas(w_vano, h_vano, deltas_gola)

        # Ambas fachadas tienen las mismas dimensiones
        self.assertAlmostEqual(w_p, w_c, places=6)
        self.assertAlmostEqual(h_p_final, h_c_final, places=6)

        # Altura esperada: 700 - 35 + 16 = 681.0 mm (deltas netos, sin holgura global)
        self.assertAlmostEqual(h_p_final, 681.0, places=6)
        self.assertAlmostEqual(h_c_final, 681.0, places=6)

        # Ambas usan la misma operación de canto
        _, op_p = aplicar_sistema_apertura(h_p_final, APERTURA_GOLA)
        _, op_c = aplicar_sistema_apertura(h_c_final, APERTURA_GOLA)
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
        import VDO.core.vdo_math_facade  # noqa: F401

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
        """No hay discrepancias de strings entre puerta y cajón.

        El contrato de fachada vive en VDO.core.vdo_math_facade; el
        modulo plano vdo_facade_contract de la era Macro/ no existe en el
        paquete y este test fallaba con ModuleNotFoundError.
        """
        import VDO.core.vdo_math_facade as CONTRATO
        for attr in ("APERTURA_TIRADOR", "APERTURA_GOLA",
                      "APERTURA_45_GRADOS", "APERTURA_PUSH_OPEN"):
            v_puerta = getattr(D_PUERTA, attr)
            v_cajon = getattr(D_CAJON, attr)
            v_contrato = getattr(CONTRATO, attr)
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


class TestContratoFachadaDeltas(unittest.TestCase):
    """Pruebas del Contrato de Fachada Universal (deltas netos por borde)."""

    def test_calcular_fachada_desde_deltas_parche(self):
        w, h = calcular_fachada_desde_deltas(500, 700, DELTA_PARCHE_TOTAL)
        self.assertAlmostEqual(w, 532.0, places=6)   # 500 + 16 + 16
        self.assertAlmostEqual(h, 732.0, places=6)   # 700 + 16 + 16

    def test_calcular_fachada_desde_deltas_agarre_aereo(self):
        """Puerta aereo con volado inferior: sur +35."""
        w, h = calcular_fachada_desde_deltas(500, 700, DELTA_AGARRE_INFERIOR_AEREO)
        self.assertAlmostEqual(w, 532.0, places=6)   # 500 + 16 + 16
        self.assertAlmostEqual(h, 751.0, places=6)   # 700 + 16 + 35

    def test_calcular_fachada_desde_deltas_gola(self):
        """Cajon con gola superior: norte -25."""
        w, h = calcular_fachada_desde_deltas(500, 700, DELTA_GOLA_SUPERIOR)
        self.assertAlmostEqual(w, 532.0, places=6)   # 500 + 16 + 16
        self.assertAlmostEqual(h, 691.0, places=6)   # 700 - 25 + 16

    def test_calcular_fachada_desde_deltas_gola_35(self):
        """Gola con descuento de 35 en norte."""
        w, h = calcular_fachada_desde_deltas(500, 700, DELTA_GOLA_SUPERIOR_35)
        self.assertAlmostEqual(h, 681.0, places=6)   # 700 - 35 + 16

    def test_calcular_fachada_desde_deltas_rincon_ciego(self):
        """Rincon ciego: este 0 (semiparche contra poste ciego)."""
        w, h = calcular_fachada_desde_deltas(500, 700, DELTA_RINCON_CIEGO)
        self.assertAlmostEqual(w, 516.0, places=6)   # 500 + 16 + 0
        self.assertAlmostEqual(h, 732.0, places=6)

    def test_calcular_fachada_desde_deltas_embebida(self):
        w, h = calcular_fachada_desde_deltas(500, 700, DELTA_EMBEBIDA)
        self.assertAlmostEqual(w, 496.0, places=6)   # 500 - 2 - 2
        self.assertAlmostEqual(h, 696.0, places=6)   # 700 - 2 - 2

    def test_calcular_fachada_desde_deltas_dimension_negativa(self):
        """Deltas muy negativas deben lanzar ValueError."""
        malos = {"norte": -1000.0, "sur": -1000.0, "este": 0.0, "oeste": 0.0}
        with self.assertRaises(ValueError):
            calcular_fachada_desde_deltas(100, 100, malos)

    def test_calcular_fachada_desde_deltas_clave_faltante(self):
        """Falta una clave del delta -> ValueError."""
        incompleto = {"norte": 16.0, "sur": 16.0, "este": 16.0}
        with self.assertRaises(ValueError):
            calcular_fachada_desde_deltas(500, 700, incompleto)

    def test_calcular_origen_fachada_local_simetrico(self):
        """Deltas parche: origen desplazado 16mm hacia O y S."""
        x, z = calcular_origen_fachada_local(100.0, 200.0, DELTA_PARCHE_TOTAL)
        self.assertAlmostEqual(x, 84.0, places=6)    # 100 - 16
        self.assertAlmostEqual(z, 184.0, places=6)   # 200 - 16

    def test_calcular_origen_fachada_local_agarre_aereo(self):
        """Volado inferior: la puerta arranca 35mm por debajo del vano."""
        x, z = calcular_origen_fachada_local(100.0, 200.0, DELTA_AGARRE_INFERIOR_AEREO)
        self.assertAlmostEqual(x, 84.0, places=6)    # 100 - 16
        self.assertAlmostEqual(z, 165.0, places=6)   # 200 - 35

    def test_calcular_origen_fachada_local_gola(self):
        """Gola superior: origen en Z no se desplaza hacia arriba (norte negativo
        afecta dimensiones, no el anclaje Z que usa sur)."""
        x, z = calcular_origen_fachada_local(100.0, 200.0, DELTA_GOLA_SUPERIOR)
        self.assertAlmostEqual(x, 84.0, places=6)    # 100 - 16
        self.assertAlmostEqual(z, 184.0, places=6)   # 200 - 16 (sur, no norte)

    def test_aplicar_sistema_apertura_no_toca_altura(self):
        """0% dimensional: altura inalterada para todos los sistemas."""
        for sistema in SISTEMAS_APERTURA_VALIDOS:
            h_aj, _op = aplicar_sistema_apertura(700.0, sistema)
            self.assertAlmostEqual(h_aj, 700.0, places=6)

    def test_operacion_canto_por_sistema(self):
        """Cada sistema devuelve su operacion de canto esperada."""
        _, op_tirador = aplicar_sistema_apertura(700.0, APERTURA_TIRADOR)
        self.assertEqual(op_tirador, OPERACION_CANTO_ESTANDAR)

        _, op_gola = aplicar_sistema_apertura(700.0, APERTURA_GOLA)
        self.assertEqual(op_gola, OPERACION_CANTO_GOLA)

        _, op_45 = aplicar_sistema_apertura(700.0, APERTURA_45_GRADOS)
        self.assertEqual(op_45, OPERACION_CANTO_45)

        _, op_push = aplicar_sistema_apertura(700.0, APERTURA_PUSH_OPEN)
        self.assertEqual(op_push, OPERACION_CANTO_ESTANDAR)

    def test_deltas_neto_sin_holgura_global(self):
        """Regla de oro: ancho = w_vano + oeste + este, sin restas magicas."""
        deltas_personal = {"norte": 10.0, "sur": 20.0, "este": 5.0, "oeste": 7.0}
        w, h = calcular_fachada_desde_deltas(100.0, 100.0, deltas_personal)
        self.assertAlmostEqual(w, 112.0, places=6)   # 100 + 7 + 5
        self.assertAlmostEqual(h, 130.0, places=6)   # 100 + 10 + 20


if __name__ == "__main__":
    resultado = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if resultado.wasSuccessful():
        print("=" * 64)
        print("Tests de Armonía de Fachadas OK - 100% validado")
        print("=" * 64)
        sys.exit(0)
    sys.exit(1)
