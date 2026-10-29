import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import FreeCAD as App
    import vdo_zocalo_core as Z
except Exception:
    App = None
    Z = None


@unittest.skipIf(Z is None, "requiere FreeCAD")
class ZocaloGeometryTests(unittest.TestCase):
    def test_geometria_con_trasera(self):
        g = Z.calcular_geometria_zocalo(
            600, 580, 100, 18, 50, 0, 20, True, 2)
        tiras = {t["borde"]: t for t in g["tiras"]}
        self.assertEqual(tiras["frente"]["x"], 18.0)
        self.assertEqual(tiras["frente"]["y"], 50.0)
        self.assertEqual(tiras["frente"]["w"], 564.0)
        self.assertEqual(tiras["frente"]["h"], 18.0)
        self.assertEqual(tiras["izquierda"]["y"], 50.0)
        self.assertEqual(tiras["izquierda"]["h"], 510.0)
        self.assertEqual(tiras["fondo"]["x"], 18.0)
        self.assertEqual(tiras["fondo"]["w"], 564.0)
        self.assertEqual(tiras["fondo"]["y"], 542.0)

    def test_sin_trasera_y_amarres(self):
        g = Z.calcular_geometria_zocalo(
            600, 580, 100, 18, 50, 15, 20, False, 2)
        self.assertEqual(len(g["tiras"]), 3)
        self.assertNotIn("fondo", {t["borde"] for t in g["tiras"]})
        self.assertEqual(len(g["amarres"]), 2)
        for amarre in g["amarres"]:
            self.assertEqual(amarre["y"], 68.0)
            self.assertEqual(amarre["h"], 512.0)
            self.assertGreaterEqual(amarre["x"], 33.0)
            self.assertLessEqual(amarre["x"] + amarre["w"], 567.0)

    def test_despiece_longitudes(self):
        g = Z.calcular_geometria_zocalo(
            600, 580, 100, 18, 50, 0, 20, True, 0)
        piezas = {p["nombre"]: p for p in g["piezas"]}
        self.assertEqual(piezas["Zocalo_Frente"]["largo"], 564.0)
        self.assertEqual(piezas["Zocalo_Trasero"]["largo"], 564.0)
        self.assertEqual(piezas["Zocalo_Lat_Izq"]["largo"], 510.0)
        self.assertEqual(piezas["Zocalo_Frente"]["largo_tira"],
                         "punta_a_punta")
        self.assertEqual(piezas["Zocalo_Trasero"]["largo_tira"],
                         "marco_interior")

    def test_errores_de_configuracion(self):
        with self.assertRaises(Z.ZocaloError):
            Z.calcular_geometria_zocalo(600, 580, 100, 18, 570, 0, 20)
        with self.assertRaises(Z.ZocaloError):
            Z.calcular_geometria_zocalo(600, 580, 100, 18, 50, 0, 20,
                                        True, -1)

    def test_make_zocalo_sin_solapes(self):
        doc = App.newDocument("TestZocalo")
        try:
            obj = Z.make_zocalo({
                "nombre": "ZocaloTest",
                "ancho": 600,
                "fondo": 580,
                "alto_zocalo": 100,
                "espesor_tablero": 18,
                "distancia_frente": 50,
                "distancia_costados": 0,
                "distancia_trasera": 20,
                "tiene_trasera": True,
                "amarres_intermedios": 2,
            })
            doc.recompute()
            self.assertTrue(obj.Shape.isValid())
            solidos = list(obj.Shape.Solids)
            self.assertEqual(len(solidos), 6)
            for i in range(len(solidos)):
                for j in range(i + 1, len(solidos)):
                    self.assertAlmostEqual(
                        solidos[i].common(solidos[j]).Volume, 0.0, places=6)
            piezas = json.loads(obj.VDO_Paneles_JSON)
            self.assertEqual(len(piezas), 6)
            self.assertIn("Zocalo_Frente", obj.VDO_ResumenDespiece)
        finally:
            App.closeDocument(doc.Name)


if __name__ == "__main__":
    unittest.main()
