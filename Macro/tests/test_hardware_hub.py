# -*- coding: utf-8 -*-
"""Pruebas de la Capa H - Catalogo de herrajes VDO."""

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

import vdo_hardware_hub as H


class HardwareHubTests(unittest.TestCase):
    def test_get_hardware_ducasse_d52(self):
        hw = H.get_hardware("DUC-KIT-D52")
        self.assertEqual(hw["proveedor"], "Ducasse Industrial")
        self.assertEqual(hw["parametros_tecnicos"]["descuento_altura_hoja"], 33.0)
        self.assertEqual(hw["parametros_tecnicos"]["traslape_minimo"], 35.0)
        self.assertEqual(hw["precio_unitario"], 18.50)
        self.assertEqual(hw["moneda"], "USD")

    def test_get_hardware_al1535(self):
        hw_mad = H.get_hardware("DUC-AL-1535-MAD")
        self.assertEqual(hw_mad["parametros_tecnicos"]["descuento_altura_hoja"], 10.0)
        self.assertEqual(hw_mad["parametros_tecnicos"]["traslape_minimo"], 25.0)

        hw_vid = H.get_hardware("DUC-AL-1535-VID")
        self.assertEqual(hw_vid["parametros_tecnicos"]["descuento_altura_hoja"], 10.0)
        self.assertEqual(hw_vid["parametros_tecnicos"]["traslape_minimo"], 25.0)
        self.assertEqual(hw_vid["parametros_tecnicos"]["espesor_vidrio_max"], 6.0)

    def test_get_hardware_sku_no_existente(self):
        with self.assertRaises(KeyError):
            H.get_hardware("SKU-INEXISTENTE")

    def test_get_family(self):
        bisagras = H.get_family("bisagra_cazoleta")
        self.assertIn("GEN-CAZ-35-PARCHE", bisagras)
        self.assertIn("GEN-CAZ-35-SEMIPARCHE", bisagras)
        self.assertIn("GEN-CAZ-35-EMBEBIDA", bisagras)

        corredizos = H.get_family("sistema_corredizo")
        self.assertIn("DUC-KIT-D52", corredizos)
        self.assertIn("DUC-AL-1535-MAD", corredizos)
        self.assertIn("DUC-AL-1535-VID", corredizos)

        with self.assertRaises(KeyError):
            H.get_family("familia_inexistente")

    def test_calculate_sliding_doors_placard_d52(self):
        res = H.calculate_sliding_doors(1500.0, 2000.0, "DUC-KIT-D52", n_hojas=2)
        self.assertEqual(res["sku"], "DUC-KIT-D52")
        self.assertAlmostEqual(res["alto_hoja"], 1967.0, places=6)
        self.assertAlmostEqual(res["ancho_hoja"], 767.5, places=6)
        self.assertEqual(len(res["hojas"]), 2)
        for hoja in res["hojas"]:
            self.assertAlmostEqual(hoja["alto_corte"], 1967.0, places=6)
            self.assertAlmostEqual(hoja["ancho_corte"], 767.5, places=6)

    def test_calculate_sliding_doors_alacena_al1535(self):
        res = H.calculate_sliding_doors(800.0, 600.0, "DUC-AL-1535-MAD", n_hojas=2)
        self.assertEqual(res["sku"], "DUC-AL-1535-MAD")
        self.assertAlmostEqual(res["alto_hoja"], 590.0, places=6)
        self.assertAlmostEqual(res["ancho_hoja"], 412.5, places=6)

    def test_resolve_hinge_generic_parche(self):
        hw = H.resolve_hinge("parche")
        self.assertEqual(hw["nombre"], "Bisagra Cazoleta 35mm Cierre Suave - Recta (Parche)")
        self.assertEqual(hw["parametros_tecnicos"]["tipo_montaje"], "parche")
        self.assertAlmostEqual(hw["parametros_tecnicos"]["diametro_cazoleta"], 35.0)

    def test_resolve_hinge_prefer_sku(self):
        hw = H.resolve_hinge("embebida", prefer_sku="GEN-CAZ-35-PARCHE")
        self.assertEqual(hw["parametros_tecnicos"]["tipo_montaje"], "parche")

    def test_resolve_sliding(self):
        self.assertEqual(H.resolve_sliding("closet")["nombre"], "Kit Corredizo Ducasse D-52 (Closet / Placard al Piso)")
        self.assertEqual(H.resolve_sliding("placard")["nombre"], "Kit Corredizo Ducasse D-52 (Closet / Placard al Piso)")
        self.assertEqual(H.resolve_sliding("mueble")["nombre"], "Sistema Corredizo Ducasse AL 1535 Madera (Muebles / Alacenas)")
        self.assertEqual(H.resolve_sliding("alacena")["nombre"], "Sistema Corredizo Ducasse AL 1535 Madera (Muebles / Alacenas)")

    def test_resolve_drawer_slide_blum_tandem(self):
        hw = H.resolve_drawer_slide(tipo="oculta", marca="blum_tandem")
        self.assertEqual(hw["sku"], "BLUM-TANDEM")
        self.assertAlmostEqual(hw["parametros_tecnicos"]["delta_ancho"], 49.0)
        self.assertEqual(
            hw["parametros_tecnicos"]["longitudes_comerciales"],
            [300.0, 350.0, 400.0, 450.0, 500.0, 550.0])

    def test_resolve_drawer_slide_sku_directo(self):
        hw = H.resolve_drawer_slide(tipo="oculta", marca="GEN-OCULTA")
        self.assertEqual(hw["sku"], "GEN-OCULTA")
        self.assertAlmostEqual(hw["parametros_tecnicos"]["delta_ancho"], 45.0)

    def test_resolve_drawer_slide_telescopica(self):
        hw = H.resolve_drawer_slide(
            tipo="telescopica", marca="GEN-TELESCOPICA-45KG")
        self.assertEqual(hw["sku"], "GEN-TELESCOPICA-45KG")
        self.assertAlmostEqual(
            hw["parametros_tecnicos"]["holgura_lateral_por_lado"], 12.7)
        self.assertAlmostEqual(
            hw["parametros_tecnicos"]["fondo_ranurado"], 5.5)

    def test_resolve_drawer_slide_sku_inexistente(self):
        with self.assertRaises(KeyError):
            H.resolve_drawer_slide(tipo="oculta", marca="INEXISTENTE")

    def test_get_family_corredera_oculta(self):
        familia = H.get_family("corredera_oculta")
        self.assertIn("BLUM-TANDEM", familia)
        self.assertIn("GEN-OCULTA", familia)
        self.assertIn("HAFELE-OCULTA", familia)
        self.assertIn("DUCASSE-OCULTA", familia)

    def test_get_family_corredera_telescopica(self):
        familia = H.get_family("corredera_telescopica")
        self.assertIn("GEN-TELESCOPICA-45KG", familia)

    def test_no_gui_imports(self):
        for nombre in ("FreeCADGui", "PySide", "PySide2", "PySide6"):
            self.assertNotIn(nombre, sys.modules, f"{nombre} importado en Capa H")


if __name__ == "__main__":
    resultado = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(HardwareHubTests))
    if resultado.wasSuccessful():
        print("Tests de Capa H OK - Catalogo de herrajes validado al 100%")
        sys.exit(0)
    sys.exit(1)
