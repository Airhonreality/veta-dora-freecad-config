# -*- coding: utf-8 -*-
# =====================================================================
# tests/test_math_caras.py
# Suite de validacion del Estado Constructivo de Caras del COCO (Concepto 2).
#
# Modos: SOLIDO, AMARRES, MARCO_RINCON, NULO.
# Capa 0 pura: testable con python3, sin FreeCAD ni Qt.
# =====================================================================

import os
import sys
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(_AQUI)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from VDO.core.vdo_math_caras import (
    MODO_SOLIDO, MODO_AMARRES, MODO_MARCO_RINCON, MODO_NULO,
    MODOS_CARA_VALIDOS,
    CARAS_COCO,
    ROL_TECHO, ROL_BASE, ROL_LATERAL_IZQ, ROL_LATERAL_DER, ROL_FONDO,
    ROL_AMARRE_FRONTAL, ROL_AMARRE_TRASERO,
    ROL_TRAVESA_SUPERIOR, ROL_TRAVESA_INFERIOR, ROL_POSTE_CIEGO,
    ANCHO_AMARRE_DEFAULT, ESPESOR_PANEL_DEFAULT,
    CaraConfig, PiezaCara,
    generar_piezas_cara, piezas_por_caras, modo_por_cara, resumir_caras,
)

DIMS = {"alto": 720.0, "ancho": 600.0, "fondo": 580.0, "espesor": 18.0}


class TestModosYEnum(unittest.TestCase):
    """Validacion de modos y enums de cara."""

    def test_modos_validos(self):
        self.assertEqual(MODO_SOLIDO, "SOLIDO")
        self.assertEqual(MODO_AMARRES, "AMARRES")
        self.assertEqual(MODO_MARCO_RINCON, "MARCO_RINCON")
        self.assertEqual(MODO_NULO, "NULO")
        self.assertEqual(len(MODOS_CARA_VALIDOS), 4)
        for m in MODOS_CARA_VALIDOS:
            self.assertIn(m, ("SOLIDO", "AMARRES", "MARCO_RINCON", "NULO"))

    def test_carasa_coco(self):
        self.assertEqual(tuple(CARAS_COCO),
                         ("techo", "base", "izquierda", "derecha", "fondo"))

    def test_constantes_taller(self):
        self.assertEqual(ANCHO_AMARRE_DEFAULT, 70.0)
        self.assertEqual(ESPESOR_PANEL_DEFAULT, 18.0)

    def test_roles_pieza(self):
        self.assertEqual(ROL_TECHO, "techo")
        self.assertEqual(ROL_BASE, "base")
        self.assertEqual(ROL_LATERAL_IZQ, "lateral_izquierdo")
        self.assertEqual(ROL_LATERAL_DER, "lateral_derecho")
        self.assertEqual(ROL_FONDO, "fondo")
        self.assertEqual(ROL_AMARRE_FRONTAL, "amarre_frontal")
        self.assertEqual(ROL_AMARRE_TRASERO, "amarre_trasero")
        self.assertEqual(ROL_TRAVESA_SUPERIOR, "travesa_superior")
        self.assertEqual(ROL_TRAVESA_INFERIOR, "travesa_inferior")
        self.assertEqual(ROL_POSTE_CIEGO, "poste_ciego")


class TestGenerarPiezasCara(unittest.TestCase):
    """Validacion de generar_piezas_cara por modo."""

    def test_solido_techo(self):
        piezas = generar_piezas_cara("techo", {"modo": MODO_SOLIDO}, DIMS)
        self.assertEqual(len(piezas), 1)
        p = piezas[0]
        self.assertEqual(p["rol"], ROL_TECHO)
        self.assertEqual(p["cara_origen"], "techo")
        self.assertEqual(p["modo_origen"], MODO_SOLIDO)
        # Placa horizontal: w=ancho, h=fondo, d=espesor, z = alto - espesor
        self.assertAlmostEqual(p["w"], 600.0)
        self.assertAlmostEqual(p["h"], 580.0)
        self.assertAlmostEqual(p["d"], 18.0)
        self.assertAlmostEqual(p["z"], 702.0)   # 720 - 18
        self.assertAlmostEqual(p["x"], 0.0)
        self.assertAlmostEqual(p["y"], 0.0)

    def test_solido_base(self):
        piezas = generar_piezas_cara("base", {"modo": MODO_SOLIDO}, DIMS)
        self.assertEqual(len(piezas), 1)
        p = piezas[0]
        self.assertEqual(p["rol"], ROL_BASE)
        # Placa horizontal en el piso: z = 0
        self.assertAlmostEqual(p["z"], 0.0)
        self.assertAlmostEqual(p["w"], 600.0)
        self.assertAlmostEqual(p["h"], 580.0)
        self.assertAlmostEqual(p["d"], 18.0)

    def test_solido_lateral_izquierda(self):
        piezas = generar_piezas_cara("izquierda", {"modo": MODO_SOLIDO}, DIMS)
        self.assertEqual(len(piezas), 1)
        p = piezas[0]
        self.assertEqual(p["rol"], ROL_LATERAL_IZQ)
        # Placa vertical: espesor sobre X, altura completa
        self.assertAlmostEqual(p["x"], 0.0)
        self.assertAlmostEqual(p["w"], 18.0)
        self.assertAlmostEqual(p["h"], 580.0)   # fondo
        self.assertAlmostEqual(p["d"], 720.0)   # alto

    def test_solido_lateral_derecha(self):
        piezas = generar_piezas_cara("derecha", {"modo": MODO_SOLIDO}, DIMS)
        self.assertEqual(len(piezas), 1)
        p = piezas[0]
        self.assertEqual(p["rol"], ROL_LATERAL_DER)
        self.assertAlmostEqual(p["x"], 582.0)   # 600 - 18
        self.assertAlmostEqual(p["w"], 18.0)

    def test_solido_fondo(self):
        piezas = generar_piezas_cara("fondo", {"modo": MODO_SOLIDO}, DIMS)
        self.assertEqual(len(piezas), 1)
        p = piezas[0]
        self.assertEqual(p["rol"], ROL_FONDO)
        # Placa vertical trasera: espesor sobre Y
        self.assertAlmostEqual(p["y"], 562.0)   # 580 - 18
        self.assertAlmostEqual(p["h"], 18.0)
        self.assertAlmostEqual(p["w"], 564.0)   # 600 - 2*18
        self.assertAlmostEqual(p["d"], 684.0)   # 720 - 2*18

    def test_amarres_techo(self):
        """Techo con AMARRES genera 2 tiras de 70 mm."""
        piezas = generar_piezas_cara(
            "techo", {"modo": MODO_AMARRES, "ancho_amarre": 70.0}, DIMS)
        self.assertEqual(len(piezas), 2)
        roles = {p["rol"] for p in piezas}
        self.assertEqual(roles, {ROL_AMARRE_FRONTAL, ROL_AMARRE_TRASERO})
        for p in piezas:
            self.assertEqual(p["modo_origen"], MODO_AMARRES)
            self.assertAlmostEqual(p["d"], 18.0)   # espesor sobre Z
            self.assertAlmostEqual(p["w"], 600.0)   # recorre ancho completo
            self.assertAlmostEqual(p["h"], 70.0)    # ancho_amarre en Y
            self.assertAlmostEqual(p["z"], 702.0)   # alto - espesor
        # Frontal en Y=0, trasero en Y=510 (580-70)
        frontal = [p for p in piezas if p["rol"] == ROL_AMARRE_FRONTAL][0]
        trasero = [p for p in piezas if p["rol"] == ROL_AMARRE_TRASERO][0]
        self.assertAlmostEqual(frontal["y"], 0.0)
        self.assertAlmostEqual(trasero["y"], 510.0)

    def test_amarres_base(self):
        """Base con AMARRES genera 2 tiras en el piso."""
        piezas = generar_piezas_cara(
            "base", {"modo": MODO_AMARRES, "ancho_amarre": 70.0}, DIMS)
        self.assertEqual(len(piezas), 2)
        for p in piezas:
            self.assertAlmostEqual(p["z"], 0.0)   # en el piso
            self.assertAlmostEqual(p["d"], 18.0)

    def test_amarres_ancho_personalizado(self):
        """Ancho de amarre configurable."""
        piezas = generar_piezas_cara(
            "techo", {"modo": MODO_AMARRES, "ancho_amarre": 100.0}, DIMS)
        for p in piezas:
            self.assertAlmostEqual(p["h"], 100.0)
        trasero = [p for p in piezas if p["rol"] == ROL_AMARRE_TRASERO][0]
        self.assertAlmostEqual(trasero["y"], 480.0)  # 580 - 100

    def test_amarres_en_lateral_degrada_a_solido(self):
        """AMARRES en un lateral (no techo/base) degrada a SOLIDO."""
        piezas = generar_piezas_cara(
            "izquierda", {"modo": MODO_AMARRES}, DIMS)
        self.assertEqual(len(piezas), 1)
        self.assertEqual(piezas[0]["modo_origen"], MODO_SOLIDO)
        self.assertEqual(piezas[0]["rol"], ROL_LATERAL_IZQ)

    def test_marco_rincon_izquierda(self):
        """Lateral izquierdo MARCO_RINCON: 2 travesaños + poste ciego."""
        piezas = generar_piezas_cara(
            "izquierda", {"modo": MODO_MARCO_RINCON, "altura_travesa": 70.0}, DIMS)
        self.assertEqual(len(piezas), 3)
        roles = {p["rol"] for p in piezas}
        self.assertEqual(roles, {ROL_TRAVESA_SUPERIOR, ROL_TRAVESA_INFERIOR,
                                 ROL_POSTE_CIEGO})
        for p in piezas:
            self.assertEqual(p["modo_origen"], MODO_MARCO_RINCON)
            self.assertAlmostEqual(p["x"], 0.0)   # poste en el borde izquierdo
            self.assertAlmostEqual(p["w"], 18.0)   # espesor en X
            if p["rol"] == ROL_POSTE_CIEGO:
                self.assertAlmostEqual(p["h"], 70.0)   # listón frontal, no fondo completo
            else:
                self.assertAlmostEqual(p["h"], 580.0)   # travesaños a fondo completo
        # Travesaño superior en z = 650 (720-70), inferior en z = 0
        sup = [p for p in piezas if p["rol"] == ROL_TRAVESA_SUPERIOR][0]
        inf = [p for p in piezas if p["rol"] == ROL_TRAVESA_INFERIOR][0]
        poste = [p for p in piezas if p["rol"] == ROL_POSTE_CIEGO][0]
        self.assertAlmostEqual(sup["z"], 650.0)   # 720 - 70
        self.assertAlmostEqual(sup["d"], 70.0)
        self.assertAlmostEqual(inf["z"], 0.0)
        self.assertAlmostEqual(inf["d"], 70.0)
        # Poste entre travesaños: z=70, d=580 (720-2*70)
        self.assertAlmostEqual(poste["z"], 70.0)
        self.assertAlmostEqual(poste["d"], 580.0)

    def test_marco_rincon_derecha(self):
        """Lateral derecho MARCO_RINCON: poste en el borde derecho."""
        piezas = generar_piezas_cara(
            "derecha", {"modo": MODO_MARCO_RINCON}, DIMS)
        self.assertEqual(len(piezas), 3)
        for p in piezas:
            self.assertAlmostEqual(p["x"], 582.0)   # 600 - 18

    def test_marco_rincon_altura_travesa_personalizada(self):
        """Altura de travesaño configurable."""
        piezas = generar_piezas_cara(
            "izquierda", {"modo": MODO_MARCO_RINCON, "altura_travesa": 100.0}, DIMS)
        sup = [p for p in piezas if p["rol"] == ROL_TRAVESA_SUPERIOR][0]
        inf = [p for p in piezas if p["rol"] == ROL_TRAVESA_INFERIOR][0]
        poste = [p for p in piezas if p["rol"] == ROL_POSTE_CIEGO][0]
        self.assertAlmostEqual(sup["z"], 620.0)   # 720 - 100
        self.assertAlmostEqual(sup["d"], 100.0)
        self.assertAlmostEqual(poste["z"], 100.0)
        self.assertAlmostEqual(poste["d"], 520.0)  # 720 - 2*100

    def test_marco_rincon_en_techo_degrada_a_solido(self):
        """MARCO_RINCON en techo (no lateral) degrada a SOLIDO."""
        piezas = generar_piezas_cara(
            "techo", {"modo": MODO_MARCO_RINCON}, DIMS)
        self.assertEqual(len(piezas), 1)
        self.assertEqual(piezas[0]["modo_origen"], MODO_SOLIDO)

    def test_nulo_no_genera_piezas(self):
        """NULO: la cara no existe, lista vacia."""
        for cara in CARAS_COCO:
            piezas = generar_piezas_cara(cara, {"modo": MODO_NULO}, DIMS)
            self.assertEqual(len(piezas), 0, f"{cara} no deberia generar piezas")

    def test_cara_invalida(self):
        with self.assertRaises(ValueError):
            generar_piezas_cara("caras_inexistente", {"modo": MODO_SOLIDO}, DIMS)

    def test_modo_invalido(self):
        with self.assertRaises(ValueError):
            generar_piezas_cara("techo", {"modo": "MODO_FANTASMA"}, DIMS)

    def test_dimension_invalida(self):
        with self.assertRaises(ValueError):
            generar_piezas_cara("techo", {"modo": MODO_SOLIDO},
                                {"alto": 0, "ancho": 600, "fondo": 580})

    def test_espesor_invalido(self):
        with self.assertRaises(ValueError):
            generar_piezas_cara("techo", {"modo": MODO_SOLIDO, "espesor": -5}, DIMS)


class TestPiezasPorCaras(unittest.TestCase):
    """Validacion de piezas_por_caras (todas las caras de un golpe)."""

    def test_todas_solido(self):
        caras_cfg = {c: {"modo": MODO_SOLIDO} for c in CARAS_COCO}
        res = piezas_por_caras(caras_cfg, DIMS)
        self.assertEqual(set(res.keys()), set(CARAS_COCO))
        total = sum(len(v) for v in res.values())
        self.assertEqual(total, 5)  # 5 caras solido = 5 piezas

    def test_mezcla_modos(self):
        caras_cfg = {
            "techo": {"modo": MODO_AMARRES},
            "base": {"modo": MODO_SOLIDO},
            "izquierda": {"modo": MODO_MARCO_RINCON},
            "derecha": {"modo": MODO_SOLIDO},
            "fondo": {"modo": MODO_NULO},
        }
        res = piezas_por_caras(caras_cfg, DIMS)
        self.assertEqual(len(res["techo"]), 2)     # 2 tiras amarre
        self.assertEqual(len(res["base"]), 1)      # 1 solido
        self.assertEqual(len(res["izquierda"]), 3) # 2 trav + 1 poste
        self.assertEqual(len(res["derecha"]), 1)   # 1 solido
        self.assertEqual(len(res["fondo"]), 0)     # nulo
        total = sum(len(v) for v in res.values())
        self.assertEqual(total, 7)

    def test_default_es_solido(self):
        """Sin configuracion, todas las caras son SOLIDO."""
        res = piezas_por_caras({}, DIMS)
        for cara in CARAS_COCO:
            self.assertEqual(len(res[cara]), 1)
            self.assertEqual(res[cara][0]["modo_origen"], MODO_SOLIDO)


class TestModoPorCara(unittest.TestCase):
    """Validacion de modo_por_cara."""

    def test_default_solido(self):
        self.assertEqual(modo_por_cara({}, "techo"), MODO_SOLIDO)

    def test_modo_explicito(self):
        self.assertEqual(
            modo_por_cara({"techo": {"modo": MODO_AMARRES}}, "techo"),
            MODO_AMARRES)

    def test_cara_inexistente_devuelve_solido(self):
        self.assertEqual(modo_por_cara({}, "fondo"), MODO_SOLIDO)


class TestResumirCaras(unittest.TestCase):
    """Validacion de resumir_caras (resumen textual)."""

    def test_resumen_contiene_lineas(self):
        caras_cfg = {c: {"modo": MODO_SOLIDO} for c in CARAS_COCO}
        res = resumir_caras(caras_cfg, DIMS)
        self.assertEqual(res["total_piezas"], 5)
        self.assertEqual(len(res["lineas"]), 5)
        self.assertIn("techo", res["resumen"])
        self.assertIn("tablero 18 mm", res["resumen"])

    def test_resumen_amarres(self):
        caras_cfg = {"techo": {"modo": MODO_AMARRES}}
        res = resumir_caras(caras_cfg, DIMS)
        self.assertIn("2 tiras de 70 mm", res["resumen"])

    def test_resumen_nulo(self):
        caras_cfg = {"fondo": {"modo": MODO_NULO}}
        res = resumir_caras(caras_cfg, DIMS)
        self.assertEqual(res["total_piezas"], 4)  # 4 solido + 0 nulo
        self.assertIn("ausente", res["resumen"])


if __name__ == "__main__":
    resultado = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if resultado.wasSuccessful():
        print("=" * 64)
        print("Tests de Estado Constructivo de Caras OK - 100% validado")
        print("=" * 64)
        sys.exit(0)
    sys.exit(1)
