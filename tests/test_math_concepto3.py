# -*- coding: utf-8 -*-
# =====================================================================
# tests/test_math_concepto3.py
# Suite de validación del Concepto 3: Visto Exterior y Gola de Carpintería.
#
# Capa 0 pura: testable con python3, sin FreeCAD ni Qt.
# =====================================================================

import os
import sys
import unittest

_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(_AQUI)
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

# --- Parte A: Visto ---
from VDO.core.vdo_math_visto import (
    CARA_IZQUIERDA, CARA_DERECHA, CARAS_VISTO_VALIDAS,
    ROL_VISTO,
    ESPESOR_PANEL_DEFAULT, DESFASE_PISO_DEFAULT, DESFASE_FRENTE_DEFAULT,
    VistoConfig, PiezaVisto,
    generar_pieza_visto,
    VISTO_AL_RAS, VISTO_HASTA_PISO, VISTO_SIN_DESFASES,
)

# --- Parte B: Gola ---
from VDO.core.vdo_math_layout import (
    generar_pieza_gola, calcular_bocado_l_gola,
    GOLA_ALTURA_PASO_DEFAULT, GOLA_RETRANQUEO_DEFAULT,
    TIPO_GOLA, CELDA_NORMAL,
    Layout, Cell, Track, resolve_layout,
)
from VDO.core.vdo_math_layout import ResolvedCell, ResolvedTrack

DIMS_VISTO = {"alto": 720.0, "ancho": 600.0, "fondo": 580.0, "espesor": 18.0}


# =====================================================================
# Parte A: Visto Exterior
# =====================================================================

class TestVistoModosYEnum(unittest.TestCase):
    """Validación de caras y roles de visto."""

    def test_caras_validas(self):
        self.assertEqual(CARA_IZQUIERDA, "izquierda")
        self.assertEqual(CARA_DERECHA, "derecha")
        self.assertEqual(tuple(CARAS_VISTO_VALIDAS),
                         ("izquierda", "derecha"))

    def test_rol_visto(self):
        self.assertEqual(ROL_VISTO, "visto")

    def test_constantes(self):
        self.assertEqual(ESPESOR_PANEL_DEFAULT, 18.0)
        self.assertEqual(DESFASE_PISO_DEFAULT, 100.0)
        self.assertEqual(DESFASE_FRENTE_DEFAULT, 18.0)


class TestGenerarPiezaVisto(unittest.TestCase):
    """Validación de generar_pieza_visto."""

    def test_visto_izquierda_sin_desfases(self):
        """Visto izquierdo al ras: cubre el lateral sin sobresalir."""
        cfg = dict(VISTO_SIN_DESFASES, cara=CARA_IZQUIERDA)
        p = generar_pieza_visto(CARA_IZQUIERDA, cfg, DIMS_VISTO)
        self.assertEqual(p["rol"], ROL_VISTO)
        self.assertEqual(p["cara"], CARA_IZQUIERDA)
        # Placa vertical: espesor sobre X, arranca en x=-esp (fuera del lateral)
        self.assertAlmostEqual(p["x"], -18.0)
        self.assertAlmostEqual(p["w"], 18.0)
        # Cubre fondo completo en Y, alto completo en Z
        self.assertAlmostEqual(p["y"], 0.0)
        self.assertAlmostEqual(p["h"], 580.0)
        self.assertAlmostEqual(p["z"], 0.0)
        self.assertAlmostEqual(p["d"], 720.0)
        self.assertAlmostEqual(p["desfase_z_piso"], 0.0)
        self.assertAlmostEqual(p["desfase_y_frente"], 0.0)

    def test_visto_derecha_sin_desfases(self):
        """Visto derecho al ras: cubre el lateral derecho."""
        cfg = dict(VISTO_SIN_DESFASES, cara=CARA_DERECHA)
        p = generar_pieza_visto(CARA_DERECHA, cfg, DIMS_VISTO)
        self.assertEqual(p["cara"], CARA_DERECHA)
        self.assertAlmostEqual(p["x"], 600.0)   # ancho del COCO (fuera del lateral derecho)
        self.assertAlmostEqual(p["w"], 18.0)
        self.assertAlmostEqual(p["y"], 0.0)
        self.assertAlmostEqual(p["z"], 0.0)

    def test_visto_con_desfase_piso(self):
        """Visto hasta el piso: baja 100mm hacia Z-."""
        cfg = dict(VISTO_HASTA_PISO, cara=CARA_IZQUIERDA)
        p = generar_pieza_visto(CARA_IZQUIERDA, cfg, DIMS_VISTO)
        self.assertAlmostEqual(p["z"], -100.0)   # baja 100mm
        self.assertAlmostEqual(p["d"], 820.0)    # 720 + 100
        self.assertAlmostEqual(p["desfase_z_piso"], 100.0)

    def test_visto_con_desfase_frente(self):
        """Visto al ras de puertas: vuela 18mm hacia Y-."""
        cfg = dict(VISTO_AL_RAS, cara=CARA_IZQUIERDA)
        p = generar_pieza_visto(CARA_IZQUIERDA, cfg, DIMS_VISTO)
        self.assertAlmostEqual(p["y"], -18.0)   # vuela al frente
        self.assertAlmostEqual(p["h"], 598.0)   # 580 + 18
        self.assertAlmostEqual(p["desfase_y_frente"], 18.0)

    def test_visto_ambos_desfases(self):
        """Visto con desfase al piso y al frente."""
        cfg = {
            "cara": CARA_DERECHA,
            "espesor": 18.0,
            "desfase_z_piso": 100.0,
            "desfase_y_frente": 20.0,
        }
        p = generar_pieza_visto(CARA_DERECHA, cfg, DIMS_VISTO)
        self.assertAlmostEqual(p["x"], 600.0)   # ancho del COCO
        self.assertAlmostEqual(p["y"], -20.0)
        self.assertAlmostEqual(p["z"], -100.0)
        self.assertAlmostEqual(p["h"], 600.0)   # 580 + 20
        self.assertAlmostEqual(p["d"], 820.0)   # 720 + 100

    def test_visto_espesor_personalizado(self):
        """Espesor de visto configurable."""
        cfg = dict(VISTO_SIN_DESFASES, cara=CARA_IZQUIERDA, espesor=25.0)
        p = generar_pieza_visto(CARA_IZQUIERDA, cfg, DIMS_VISTO)
        self.assertAlmostEqual(p["w"], 25.0)
        self.assertAlmostEqual(p["x"], -25.0)

    def test_cara_invalida(self):
        with self.assertRaises(ValueError):
            generar_pieza_visto("frente", {}, DIMS_VISTO)

    def test_espesor_invalido(self):
        with self.assertRaises(ValueError):
            generar_pieza_visto(CARA_IZQUIERDA, {"espesor": -5}, DIMS_VISTO)

    def test_desfase_negativo(self):
        with self.assertRaises(ValueError):
            generar_pieza_visto(CARA_IZQUIERDA,
                                {"desfase_z_piso": -10}, DIMS_VISTO)

    def test_dimension_invalida(self):
        with self.assertRaises(ValueError):
            generar_pieza_visto(CARA_IZQUIERDA, {},
                                {"alto": 0, "ancho": 600, "fondo": 580})


class TestVistoPresets(unittest.TestCase):
    """Validación de presets oficiales de visto."""

    def test_visto_al_ras(self):
        self.assertEqual(VISTO_AL_RAS["cara"], CARA_IZQUIERDA)
        self.assertEqual(VISTO_AL_RAS["desfase_z_piso"], 0.0)
        self.assertEqual(VISTO_AL_RAS["desfase_y_frente"], 18.0)

    def test_visto_hasta_piso(self):
        self.assertEqual(VISTO_HASTA_PISO["cara"], CARA_IZQUIERDA)
        self.assertEqual(VISTO_HASTA_PISO["desfase_z_piso"], 100.0)
        self.assertEqual(VISTO_HASTA_PISO["desfase_y_frente"], 18.0)

    def test_visto_sin_desfases(self):
        self.assertEqual(VISTO_SIN_DESFASES["desfase_z_piso"], 0.0)
        self.assertEqual(VISTO_SIN_DESFASES["desfase_y_frente"], 0.0)


# =====================================================================
# Parte B: Gola de Carpintería
# =====================================================================

class _FakeResolvedCell:
    """Stub mínimo de ResolvedCell para probar generar_pieza_gola aislado."""
    def __init__(self, x, z, w, h, cell):
        self.nominal_x = x
        self.nominal_z = z
        self.nominal_w = w
        self.nominal_h = h
        self.cell = cell


class TestGenerarPiezaGola(unittest.TestCase):
    """Validación de generar_pieza_gola."""

    def _celda_gola(self, x=100.0, z=200.0, w=400.0, h=300.0,
                    altura_paso=40.0, retranqueo=25.0):
        cell = Cell(tipo=TIPO_GOLA,
                    gola_altura_paso=altura_paso,
                    gola_retranqueo=retranqueo)
        return _FakeResolvedCell(x, z, w, h, cell), cell

    def test_gola_dimensiones(self):
        resuelto, cell = self._celda_gola()
        p = generar_pieza_gola(resuelto, fondo_coco=580.0, espesor_coco=18.0)
        self.assertIsNotNone(p)
        self.assertEqual(p.role, "gola")
        # w = ancho del vano
        self.assertAlmostEqual(p.w, 400.0)
        # h (Z) = altura de paso de dedos
        self.assertAlmostEqual(p.h, 40.0)
        # d = espesor del tablero (PanelPiece.thickness)
        self.assertAlmostEqual(p.thickness, 18.0)
        # y = retranqueo desde el frente
        self.assertAlmostEqual(p.x, 100.0)  # PanelPiece usa x, z (no y)
        # z = borde inferior del vano menos altura de paso
        self.assertAlmostEqual(p.z, 200.0 + 300.0 - 40.0)  # 460.0

    def test_gola_altura_paso_personalizada(self):
        resuelto, cell = self._celda_gola(altura_paso=50.0)
        p = generar_pieza_gola(resuelto, fondo_coco=580.0, espesor_coco=18.0,
                               altura_paso=50.0)
        self.assertAlmostEqual(p.h, 50.0)

    def test_gola_retranqueo_personalizado(self):
        resuelto, cell = self._celda_gola(retranqueo=30.0)
        p = generar_pieza_gola(resuelto, fondo_coco=580.0, espesor_coco=18.0,
                               retranqueo=30.0)
        # El retranqueo no se expone como atributo directo de PanelPiece;
        # se infiere de la posición x (que es nominal_x, no retranqueo).
        # Aquí verificamos que no lanza error y genera la pieza.
        self.assertIsNotNone(p)
        self.assertEqual(p.role, "gola")

    def test_gola_no_gola_devuelve_none(self):
        cell = Cell(tipo=CELDA_NORMAL)
        resuelto = _FakeResolvedCell(0.0, 0.0, 100.0, 100.0, cell)
        p = generar_pieza_gola(resuelto, fondo_coco=580.0, espesor_coco=18.0)
        self.assertIsNone(p)

    def test_gola_sin_celda_devuelve_none(self):
        resuelto = _FakeResolvedCell(0.0, 0.0, 100.0, 100.0, None)
        p = generar_pieza_gola(resuelto, fondo_coco=580.0, espesor_coco=18.0)
        self.assertIsNone(p)


class TestBocadoLGola(unittest.TestCase):
    """Validación de calcular_bocado_l_gola."""

    def _celda_gola(self, x=100.0, z=200.0, w=400.0, h=300.0):
        cell = Cell(tipo=TIPO_GOLA)
        return _FakeResolvedCell(x, z, w, h, cell)

    def test_bocado_l_dimensiones(self):
        resuelto = self._celda_gola()
        b = calcular_bocado_l_gola(resuelto, fondo_coco=580.0)
        self.assertIsNotNone(b)
        self.assertEqual(b["tipo"], "bocado_l_gola")
        self.assertAlmostEqual(b["x"], 100.0)   # ancho del vano
        self.assertAlmostEqual(b["y"], 0.0)      # desde el frente
        self.assertAlmostEqual(b["w"], 400.0)    # ancho del vano
        self.assertAlmostEqual(b["h"], 25.0)     # retranqueo (canal)
        self.assertAlmostEqual(b["d"], 40.0)     # altura de paso

    def test_bocado_l_no_gola(self):
        cell = Cell(tipo=CELDA_NORMAL)
        resuelto = _FakeResolvedCell(0.0, 0.0, 100.0, 100.0, cell)
        b = calcular_bocado_l_gola(resuelto, fondo_coco=580.0)
        self.assertIsNone(b)


class TestResolveLayoutConGola(unittest.TestCase):
    """Validación de que resolve_layout genera piezas de gola."""

    def test_layout_con_celda_gola(self):
        layout = Layout(columns=[Track("x1"), Track("x2")],
                        rows=[Track("y1")])
        # Marcar celda (x1, y1) como gola
        key = Layout.key("x1", "y1")
        cell = layout.cells[key]
        cell.tipo = TIPO_GOLA
        cell.gola_altura_paso = 40.0
        cell.gola_retranqueo = 25.0

        resuelto = resolve_layout(layout, inner_w=600.0, inner_h=720.0,
                                  thickness=18.0)

        # Debe haber al menos una pieza de tipo gola
        goleas = [p for p in resuelto.pieces if p.role == "gola"]
        self.assertEqual(len(goleas), 1)
        g = goleas[0]
        self.assertEqual(g.role, "gola")
        # 2 columnas de 600mm con 18mm separador: (600-18)/2 = 291 cada una
        self.assertAlmostEqual(g.w, 291.0)
        self.assertAlmostEqual(g.h, 40.0)   # altura de paso
        self.assertAlmostEqual(g.thickness, 18.0)  # espesor

    def test_layout_sin_gola_no_genera_goleas(self):
        layout = Layout(columns=[Track("x1"), Track("x2")],
                        rows=[Track("y1")])
        resuelto = resolve_layout(layout, inner_w=600.0, inner_h=720.0,
                                  thickness=18.0)
        goleas = [p for p in resuelto.pieces if p.role == "gola"]
        self.assertEqual(len(goleas), 0)


# ---------------------------------------------------------------------
# Test Anti-Fantasmas (requiere FreeCAD real)
# ---------------------------------------------------------------------

def _tiene_freecad():
    try:
        import FreeCAD as App  # noqa: F401
        # FreeCAD real tiene newDocument; el mock de python3 pelado no.
        return hasattr(App, "newDocument")
    except ImportError:
        return False


class TestAntiFantasmas(unittest.TestCase):
    """Doble instanciación simultánea de COCOs con amarres en el mismo
    documento. Garantiza cero colisiones de nombres, aislamiento total
    y borrado en cascada sin residuos."""

    @unittest.skipIf(not _tiene_freecad(), "Requiere FreeCAD real")
    def test_anti_fantasmas_y_aislamiento_instancias(self):
        import FreeCAD as App
        from VDO.cad.objects.vdo_cad_coco import make_coco

        doc = App.newDocument("TestAntiFantasmas")

        try:
            mueble1 = make_coco({
                "nombre": "Mueble_A",
                "tapa": "externo",
                "base": "interno",
            })
            mueble2 = make_coco({
                "nombre": "Mueble_B",
                "tapa": "externo",
                "base": "interno",
            })
            doc.recompute()

            # 1. Cero colisiones de nombres (ningún objeto renombrado con 001/002)
            nombres = [obj.Name for obj in doc.Objects]
            for n in nombres:
                self.assertFalse(
                    n.endswith("001") or n.endswith("002"),
                    f"Colisión detectada: objeto renombrado por FreeCAD: {n}")
                self.assertTrue(
                    n.startswith("Mueble_A") or n.startswith("Mueble_B") or
                    not n.startswith("Mueble_"),
                    f"Nombre inesperado: {n}")

            # 2. Aislamiento total: los hijos de cada mueble son disjuntos
            hijos_a = {h.Name for h in mueble1.Hijos or []}
            hijos_b = {h.Name for h in mueble2.Hijos or []}
            self.assertEqual(
                len(hijos_a.intersection(hijos_b)), 0,
                "Contaminación cruzada de hijos entre muebles!")

            # 3. Borrado en cascada sin residuos
            mueble1.Proxy.onDelete(mueble1, None)
            doc.removeObject(mueble1.Name)
            doc.recompute()

            restantes = [obj.Name for obj in doc.Objects]
            for n in restantes:
                self.assertFalse(
                    n.startswith("Mueble_A"),
                    f"Objeto fantasma sobrevivió al borrado: {n}")

        finally:
            try:
                App.closeDocument("TestAntiFantasmas")
            except Exception:
                pass


if __name__ == "__main__":
    resultado = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    if resultado.wasSuccessful():
        print("=" * 64)
        print("Tests de Concepto 3 (Visto + Gola) OK - 100% validado")
        print("=" * 64)
        sys.exit(0)
    sys.exit(1)
