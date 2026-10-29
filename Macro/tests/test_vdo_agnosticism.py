# -*- coding: utf-8 -*-
"""Auditoria de agnosticidad de los motores VDO.

Comprueba que ``vdo_layout``, ``vdo_reengrose`` y la resolucion de vanos
funcionan exclusivamente con datos y geometria 2D/3D, sin GUI.
"""

import os
import re
import sys
import unittest

try:
    _AQUI = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _AQUI = os.getcwd()
_RAIZ = os.path.dirname(_AQUI)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

import vdo_layout as VDO_LAYOUT
import vdo_reengrose as VDO_RE
from vdo_layout import AXIS_X, AXIS_Y, Layout, Track, resolve_layout


TOL = 1e-6
_MODULOS_GUI = (
    "FreeCADGui", "PySide", "PySide2", "PySide6", "shiboken2", "shiboken6",
)


def _aabb_intersection_volume(a, b, tol=TOL):
    """Volumen de interseccion de dos cajas (x, y, z, w, h, d)."""
    ax, ay, az, aw, ah, ad = (float(v) for v in a)
    bx, by, bz, bw, bh, bd = (float(v) for v in b)
    ix = min(ax + aw, bx + bw) - max(ax, bx)
    iy = min(ay + ah, by + bh) - max(ay, by)
    iz = min(az + ad, bz + bd) - max(az, bz)
    if ix <= tol or iy <= tol or iz <= tol:
        return 0.0
    return ix * iy * iz


def _buscar_celda(resuelto, etiqueta):
    for celda in resuelto.walk_cells():
        if celda.label == etiqueta:
            return celda
    raise AssertionError(f"No se encontro la celda resuelta {etiqueta!r}.")


def _contrato_vano(celda):
    """Adaptador de nombres: contrato publico del Vano para otros modulos."""
    return {
        "w_nominal": celda.nominal_w,
        "h_nominal": celda.nominal_h,
        "w_neto": celda.w,
        "h_neto": celda.h,
        "X0": celda.x,
        "Z0": celda.z,
    }


class _DummyDoorMock:
    """Inserto funcional de prueba que consume un Vano, no un mueble."""

    def __init__(self, vano_w, vano_h, espesor,
                 holgura_total=3.0, holgura_inset=2.0):
        self.w = float(vano_w)
        self.h = float(vano_h)
        self.e = float(espesor)
        self.holgura_total = float(holgura_total)
        self.holgura_inset = float(holgura_inset)

    def parche_total(self):
        return (
            self.w + 2.0 * self.e - self.holgura_total,
            self.h + 2.0 * self.e - self.holgura_total,
        )

    def semiparche(self):
        return (
            self.w + self.e / 2.0 - self.holgura_total,
            self.h + self.e / 2.0 - self.holgura_total,
        )

    def embebida(self):
        return (
            self.w - 2.0 * self.holgura_inset,
            self.h - 2.0 * self.holgura_inset,
        )


class VDOAgnosticismTests(unittest.TestCase):
    def setUp(self):
        for modulo in (VDO_LAYOUT, VDO_RE):
            ruta = getattr(modulo, "__file__", "")
            with open(ruta, encoding="utf-8") as manejador:
                fuente = manejador.read()
            for nombre in _MODULOS_GUI:
                patron = re.compile(
                    rf"^\s*(?:import|from)\s+{re.escape(nombre)}\b",
                    re.MULTILINE)
                self.assertIsNone(
                    patron.search(fuente),
                    f"{modulo.__name__} importa {nombre}; dejo de ser puro.")
        for nombre in _MODULOS_GUI:
            self.assertNotIn(
                nombre, sys.modules,
                f"{nombre} ya estaba cargado: la prueba no es headless.")

    def test_01_contrato_espacial_del_vano(self):
        layout = Layout(
            columns=[Track("x1"), Track("x2")],
            rows=[Track("y1"), Track("y2")],
        )
        layout.set_split(layout.get_cell(0, 0), AXIS_X, 2)
        hijo_x12 = layout.find_label("(x1.2, y1)")
        self.assertIsNotNone(hijo_x12)
        layout.set_split(hijo_x12, AXIS_Y, 2)

        resuelto = resolve_layout(layout, 1000.0, 800.0, 18.0)
        self.assertAlmostEqual(resuelto.columns[0].size, 491.0, places=6)
        self.assertAlmostEqual(resuelto.columns[1].start, 509.0, places=6)
        self.assertAlmostEqual(resuelto.rows[0].size, 391.0, places=6)
        self.assertAlmostEqual(resuelto.rows[1].start, 409.0, places=6)

        vano = _buscar_celda(resuelto, "(x1.2, y1.1)")
        contrato = _contrato_vano(vano)
        self.assertAlmostEqual(contrato["w_nominal"], 236.5, places=6)
        self.assertAlmostEqual(contrato["h_nominal"], 186.5, places=6)
        self.assertAlmostEqual(contrato["w_neto"], 236.5, places=6)
        self.assertAlmostEqual(contrato["h_neto"], 186.5, places=6)
        self.assertAlmostEqual(contrato["X0"], 254.5, places=6)
        self.assertAlmostEqual(contrato["Z0"], 0.0, places=6)

        mod_izq = VDO_RE.ReengroseModifier({
            "activo": True, "ancho": 50.0, "cara": "cara_a",
            "orientacion": "paralela",
        })
        mod_sup = VDO_RE.ReengroseModifier({
            "activo": True, "ancho": 50.0, "cara": "cara_b",
            "orientacion": "paralela",
        })
        con_reengrose = resolve_layout(
            layout.copy(), 1000.0, 800.0, 18.0,
            reengroses={
                "division_x:x1.2": mod_izq,
                "division_y:y1.2": mod_sup,
            },
        )
        vano_neto = _buscar_celda(con_reengrose, "(x1.2, y1.1)")
        contrato_neto = _contrato_vano(vano_neto)
        self.assertAlmostEqual(
            contrato_neto["w_nominal"], 236.5, places=6)
        self.assertAlmostEqual(
            contrato_neto["h_nominal"], 186.5, places=6)
        self.assertAlmostEqual(contrato_neto["w_neto"], 218.5, places=6)
        self.assertAlmostEqual(contrato_neto["h_neto"], 168.5, places=6)
        self.assertAlmostEqual(contrato_neto["X0"], 272.5, places=6)
        self.assertAlmostEqual(contrato_neto["Z0"], 0.0, places=6)

    def test_02_agnosticidad_dilatacion_muro(self):
        largo_tablero = 800.0
        ancho_tablero = 600.0
        espesor = 18.0
        bordes = {borde: {"activo": False} for borde in VDO_RE.BORDES_2D}
        bordes["fondo"] = {
            "activo": True,
            "ancho": 50.0,
            "distancia_al_canto": 0.0,
            "largo_tira": "punta_a_punta",
            "espesor": espesor,
        }

        tiras = VDO_RE.generar_tiras_perimetrales(
            largo_tablero, ancho_tablero, bordes, espesor)
        self.assertEqual(len(tiras), 1)
        tira = tiras[0]
        self.assertEqual(tira["borde"], "fondo")
        self.assertAlmostEqual(tira["largo"], 800.0, places=6)
        self.assertAlmostEqual(tira["ancho"], 50.0, places=6)
        self.assertAlmostEqual(tira["w"], 800.0, places=6)
        self.assertAlmostEqual(tira["h"], 50.0, places=6)
        self.assertAlmostEqual(tira["x"], 0.0, places=6)
        self.assertAlmostEqual(tira["y"], 550.0, places=6)
        self.assertAlmostEqual(tira["distancia_al_canto"], 0.0, places=6)
        self.assertEqual(tira["largo_tira"], "punta_a_punta")
        self.assertAlmostEqual(
            tira["y"] + tira["h"], ancho_tablero, places=6)
        self.assertAlmostEqual(
            tira["x"] + tira["w"], largo_tablero, places=6)

        panel = {
            "nombre": "Lateral",
            "largo": largo_tablero,
            "ancho": ancho_tablero,
            "espesor": espesor,
        }
        modificador = VDO_RE.ReengroseModifier({
            "activo": True,
            "usa_bordes": True,
            "bordes": bordes,
            "cara": "cara_a",
            "fabricacion": "pacha",
            "esquinas": "vertical_domina",
        })
        geometria = VDO_RE.calcular_geometria_reengrose(panel, modificador)
        self.assertEqual(len(geometria["refuerzos"]), 1)
        refuerzo = geometria["refuerzos"][0]
        self.assertAlmostEqual(refuerzo["z"], espesor, places=6)
        caja_base = (0.0, 0.0, 0.0, largo_tablero, ancho_tablero, espesor)
        caja_tira = (
            refuerzo["x"], refuerzo["y"], refuerzo["z"],
            refuerzo["largo"], refuerzo["ancho"], refuerzo["espesor"],
        )
        self.assertAlmostEqual(
            _aabb_intersection_volume(caja_base, caja_tira), 0.0,
            places=6)

    def test_03_agnosticidad_zocalo_con_amarres(self):
        largo_marco = 1000.0
        ancho_marco = 600.0
        ancho_tira = 70.0
        espesor = 18.0
        bordes = {
            borde: {
                "activo": True,
                "ancho": ancho_tira,
                "distancia_al_canto": 0.0,
                "largo_tira": "marco_interior",
                "espesor": espesor,
            }
            for borde in VDO_RE.BORDES_2D
        }
        tiras = VDO_RE.generar_tiras_perimetrales(
            largo_marco, ancho_marco, bordes, espesor)
        self.assertEqual(len(tiras), 4)
        por_borde = {tira["borde"]: tira for tira in tiras}
        self.assertAlmostEqual(
            por_borde["izquierda"]["x"] + por_borde["izquierda"]["w"],
            70.0, places=6)
        self.assertAlmostEqual(
            por_borde["derecha"]["x"], 930.0, places=6)
        self.assertAlmostEqual(
            por_borde["frente"]["y"] + por_borde["frente"]["h"],
            70.0, places=6)
        self.assertAlmostEqual(
            por_borde["fondo"]["y"], 530.0, places=6)

        hueco_w = largo_marco - 2.0 * ancho_tira
        hueco_h = ancho_marco - 2.0 * ancho_tira
        self.assertAlmostEqual(hueco_w, 860.0, places=6)
        self.assertAlmostEqual(hueco_h, 460.0, places=6)

        layout = Layout()
        layout.set_split(layout.get_cell(0, 0), AXIS_X, 3)
        resuelto = resolve_layout(layout, hueco_w, hueco_h, espesor)
        amarres = [
            pieza for pieza in resuelto.pieces if pieza.axis == AXIS_X
        ]
        self.assertEqual(len(amarres), 2)

        cajas_marco = [
            (tira["x"], tira["y"], 0.0, tira["w"], tira["h"], tira["d"])
            for tira in tiras
        ]
        for amarre in amarres:
            self.assertAlmostEqual(amarre.h, 460.0, places=6)
            self.assertAlmostEqual(amarre.w, espesor, places=6)
            caja = (
                ancho_tira + amarre.x,
                ancho_tira + amarre.z,
                0.0,
                amarre.w,
                amarre.h,
                espesor,
            )
            for caja_marco in cajas_marco:
                self.assertAlmostEqual(
                    _aabb_intersection_volume(caja, caja_marco), 0.0,
                    places=6)

    def test_04_simulacion_inserto_universal(self):
        layout = Layout()
        resuelto = resolve_layout(layout, 500.0, 700.0, 18.0)
        self.assertEqual(len(resuelto.cells), 1)
        vano = resuelto.cells[0]
        self.assertAlmostEqual(vano.w, 500.0, places=6)
        self.assertAlmostEqual(vano.h, 700.0, places=6)
        self.assertAlmostEqual(resuelto.thickness, 18.0, places=6)

        inserto = _DummyDoorMock(vano.w, vano.h, resuelto.thickness)

        parche_w, parche_h = inserto.parche_total()
        self.assertAlmostEqual(parche_w, 533.0, places=6)
        self.assertAlmostEqual(parche_h, 733.0, places=6)

        semiparche_w, _ = inserto.semiparche()
        self.assertAlmostEqual(semiparche_w, 506.0, places=6)

        embebida_w, embebida_h = inserto.embebida()
        self.assertAlmostEqual(embebida_w, 496.0, places=6)
        self.assertAlmostEqual(embebida_h, 696.0, places=6)


def _run():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        VDOAgnosticismTests)
    resultado = unittest.TextTestRunner(verbosity=2).run(suite)
    if resultado.wasSuccessful():
        print("4 tests OK - Agnosticidad de Motores Validada al 100%")
        sys.stdout.flush()
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(_run())
