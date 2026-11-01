# -*- coding: utf-8 -*-
"""Herencia de Δ_S: luz_suelo vive en el COCO y cada fachada inferior lo hereda.

Regla (decisión de arquitectura):
    Δ_S = H_zocalo − COCO.LuzSueloDefault
    Un vector de deltas propio en la fachada (VDO_Deltas_JSON) manda.
"""

import json
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

import VDO.cad.objects.vdo_cad_coco as C
import VDO.core.vdo_math_facade as F
from VDO.cad.objects.vdo_cad_puerta import make_puerta


def _zmin(p):
    """Cota Z de la base de la fachada en el marco del COCO (padre en origen).

    La forma va en origen local; la posición está en LocalPlacement.
    """
    return p.LocalPlacement.Base.z + p.Shape.BoundBox.ZMin


class ReglaPuraTests(unittest.TestCase):
    def test_delta_s_es_zocalo_menos_luz(self):
        self.assertAlmostEqual(F.delta_s_fachada_inferior(100.0, 15.0), 85.0)
        self.assertAlmostEqual(F.delta_s_fachada_inferior(0.0, 15.0), -15.0)

    def test_deltas_heredados_conservan_laterales_del_montaje(self):
        d = F.deltas_heredados_inferior("parche", 100.0, 15.0)
        self.assertEqual(d["sur"], 85.0)
        self.assertEqual(d["este"], F.DELTA_PARCHE_TOTAL["este"])
        self.assertEqual(d["oeste"], F.DELTA_PARCHE_TOTAL["oeste"])
        self.assertEqual(d["norte"], 0.0)

    def test_gola_conserva_descuento_en_norte(self):
        d = F.deltas_heredados_inferior("parche", 0.0, 15.0, norte=-35.0)
        self.assertEqual(d["norte"], -35.0)


class HerenciaEnPuertaTests(unittest.TestCase):
    def setUp(self):
        self.doc = App.newDocument("TestLuzSuelo")

    def tearDown(self):
        App.closeDocument(self.doc.Name)

    def _modulo(self, luz=None, zocalo=None):
        cfg = {"nombre": "COCO_LS", "alto": 720, "ancho": 600,
               "fondo_modulo": 580, "espesor": 18}
        coco = C.make_coco(cfg)
        if luz is not None:
            coco.LuzSueloDefault = luz
        if zocalo is not None:
            coco.touch()
            coco.VDO_Chassis_JSON = json.dumps(
                {"base": {"estrategia": "zocalo", "altura": zocalo}})
        self.doc.recompute()
        return coco

    def _puerta(self, coco, pos_z=0.0):
        p = make_puerta({"nombre": "P_LS", "parent_coco": coco})
        p.Ancho = 500.0
        p.Alto = 700.0
        p.PosX = 0.0
        p.PosZ = pos_z
        p.TipoSistema = "Batiente Vertical"
        p.TipoMontaje = "Parche"
        p.SistemaApertura = "tirador"
        self.doc.recompute()
        return p

    def test_puerta_inferior_hereda_luz_del_coco(self):
        coco = self._modulo(luz=15.0)
        p = self._puerta(coco, pos_z=0.0)
        # Sin zócalo: la base de la fachada queda 15 mm sobre el piso.
        self.assertAlmostEqual(_zmin(p), 15.0, places=3)

    def test_cambiar_luz_del_coco_se_propaga(self):
        coco = self._modulo(luz=15.0)
        p = self._puerta(coco, pos_z=0.0)
        coco.LuzSueloDefault = 20.0
        self.doc.recompute()
        self.assertAlmostEqual(_zmin(p), 20.0, places=3)

    def test_vector_local_manda_sobre_la_herencia(self):
        coco = self._modulo(luz=15.0)
        p = self._puerta(coco, pos_z=0.0)
        p.VDO_Deltas_JSON = json.dumps(
            {"norte": 0.0, "sur": 16.0, "este": 16.0, "oeste": 16.0})
        self.doc.recompute()
        self.assertAlmostEqual(_zmin(p), -16.0, places=3)

    def test_puerta_superior_no_hereda(self):
        coco = self._modulo(luz=15.0, zocalo=100.0)
        p = self._puerta(coco, pos_z=500.0)
        # Vano por encima del zócalo: no es inferior, no toca Δ_S.
        self.assertGreater(_zmin(p), 100.0)

    def test_sin_padre_no_hereda(self):
        p = make_puerta({"nombre": "P_Solo"})
        p.Ancho, p.Alto, p.PosZ = 500.0, 700.0, 0.0
        p.TipoMontaje = "Parche"
        self.doc.recompute()
        # Legacy: centrado simétrico de 16 mm; la base baja 16 mm bajo PosZ.
        self.assertAlmostEqual(_zmin(p), -16.0, places=3)


if __name__ == "__main__":
    unittest.main()
