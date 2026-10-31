# -*- coding: utf-8 -*-
"""
Suite de pruebas: Validación de simetría bilateral en torres de cajones COCO.

Verifica que la distancia entre el borde izquierdo de la fachada y el borde izquierdo
del vano sea IDÉNTICA (±0.1 mm) a la distancia entre el borde derecho de la fachada
y el borde derecho del vano (simetría perfecta en MONTAJE_PARCHE).

Caso de prueba: Torre de 3 cajones en vano de 600 mm, correspondencia asimétrica -X.
"""

import sys
import unittest
from unittest.mock import Mock, patch

# NO sembrar ~/.local/share/FreeCAD/Macro en sys.path: ahi vive una
# copia pre-refactor del paquete VDO/ que ganaba la resolucion de
# imports y hacia que estos tests validasen el codigo viejo.
# La raiz del repo la siembra tests/conftest.py.

import pytest

from tests._entorno import HAY_FREECAD

if not HAY_FREECAD:
    pytest.skip("requiere FreeCAD real; ejecutar con FreeCADCmd",
                allow_module_level=True)

from VDO.core.vdo_math_cajon import (
    calcular_despiece, obtener_marca, CORREDERA_OCULTA, APERTURA_TIRADOR,
)


class TestCajonSymmetry(unittest.TestCase):
    """Validación de simetría bilateral en posicionamiento de fachadas de cajón."""

    def setUp(self):
        """Configura despiece de cajón para vano de 600 mm."""
        self.config_cajon = {
            "ancho_libre": 600.0,  # Ancho neto del vano en COCO
            "prof_libre": 580.0,   # Profundidad interior del mueble
            "ancho_modulo": 600.0,
            "alto_frente": 200.0,
            "marca": "blum_tandem",
            "tipo_corredera": CORREDERA_OCULTA,
            "sistema_apertura": APERTURA_TIRADOR,
            "tipo_montaje_fachada": "parche",
            "holgura_lateral_fachada": 2.0,
        }

    def test_fachada_simetrica_en_vano(self):
        """La fachada debe estar centrada simétricamente en el vano."""
        despiece = calcular_despiece(self.config_cajon)

        li = self.config_cajon["ancho_libre"]  # 600 mm
        ancho_fachada = despiece["fachada"]["ancho"]

        # Posición de la fachada en coordenadas locales del cajón
        fachada_pos = despiece["posiciones"]["fachada"]
        x_fachada_local = fachada_pos["x"]

        # OJO CON EL MARCO. Las posiciones de calcular_despiece() son
        # LOCALES AL CAJON, cuyo origen es la esquina exterior de la caja,
        # y la caja va metida delta/2 dentro del vano (el centrado lo pone
        # _construir_cajones con x_caja = x_vano + delta/2). Para medir
        # margenes respecto al VANO hay que deshacer ese desplazamiento.
        #
        # Sin esta correccion el test medía x local contra cotas de vano y
        # acusaba de descentrada a una fachada que si esta centrada: daba
        # margen_izq=24.50 y margen_der=-5.50, exactamente delta/2=24.5 de
        # discrepancia.
        delta = float(obtener_marca(self.config_cajon["marca"])["delta_ancho"])
        x_fachada_vano = x_fachada_local + delta / 2.0

        margen_izq = x_fachada_vano
        margen_der = li - (x_fachada_vano + ancho_fachada)

        self.assertAlmostEqual(
            margen_izq, margen_der, delta=0.1,
            msg=f"Fachada no centrada: margen_izq={margen_izq:.2f} mm, "
            f"margen_der={margen_der:.2f} mm (esperado: iguales ±0.1 mm)"
        )

    def test_ancho_fachada_correcto_para_parche(self):
        """En MONTAJE_PARCHE, ancho_fachada = li + 2*solape - holgura."""
        despiece = calcular_despiece(self.config_cajon)

        li = self.config_cajon["ancho_libre"]
        ancho_fachada = despiece["fachada"]["ancho"]

        # Deltas netos: Δ_oeste=16, Δ_este=16 → ancho = li + 32
        ancho_esperado = li + 16.0 + 16.0

        self.assertAlmostEqual(
            ancho_fachada, ancho_esperado, delta=0.1,
            msg=f"Ancho de fachada incorrecto: {ancho_fachada:.2f} mm "
            f"(esperado: {ancho_esperado:.2f} mm, li={li} + 32)")

    def test_fachada_no_desbordada_lateralmente(self):
        """La fachada no debe estar desplazada asimétricamente hacia -X o +X."""
        despiece = calcular_despiece(self.config_cajon)

        li = self.config_cajon["ancho_libre"]
        fachada_pos = despiece["posiciones"]["fachada"]

        ancho_fachada = despiece["fachada"]["ancho"]

        # Igual que arriba: pasar del marco local del cajon al del vano.
        delta = float(obtener_marca(self.config_cajon["marca"])["delta_ancho"])
        x_fachada = fachada_pos["x"] + delta / 2.0

        # En MONTAJE_PARCHE la fachada solapa el canto del vano, asi que su
        # borde queda en -(solape - holgura/2) = -15 mm respecto al vano.
        x_esperado = -(ancho_fachada - li) / 2.0

        self.assertAlmostEqual(
            x_fachada, x_esperado, delta=0.1,
            msg=f"Fachada descentrada sobre el vano: x={x_fachada:.2f} mm "
            f"(esperado {x_esperado:.2f} mm)"
        )

    def test_despiece_completo_sin_errores(self):
        """El cálculo de despiece completo debe ejecutarse sin excepciones."""
        try:
            despiece = calcular_despiece(self.config_cajon)
            self.assertIn("caja", despiece)
            self.assertIn("fachada", despiece)
            self.assertIn("posiciones", despiece)
        except Exception as e:
            self.fail(f"calcular_despiece lanzó excepción: {e}")

    def test_delta_aplicado_correctamente(self):
        """Delta debe reducir ancho_ext = li - delta, no afectar directamente a fachada."""
        despiece = calcular_despiece(self.config_cajon)

        li = self.config_cajon["ancho_libre"]
        delta = despiece["guia"]["delta"]
        ancho_ext = despiece["caja"]["ancho_exterior"]

        # Validar que ancho_ext = li - delta
        self.assertAlmostEqual(
            ancho_ext, li - delta, delta=0.1,
            msg=f"ancho_ext incorrecto: {ancho_ext:.2f} mm "
            f"(esperado: li - delta = {li} - {delta} = {li - delta:.2f} mm)"
        )

        # ancho_fachada debe basarse en li con deltas netos
        ancho_fachada = despiece["fachada"]["ancho"]
        ancho_fachada_esperado = li + 16.0 + 16.0  # li + 32 (deltas netos)

        self.assertAlmostEqual(
            ancho_fachada, ancho_fachada_esperado, delta=0.1,
            msg=f"ancho_fachada debe basarse en li con deltas netos. "
            f"Actual: {ancho_fachada:.2f} mm, "
            f"Esperado (li + 32): {ancho_fachada_esperado:.2f} mm"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
