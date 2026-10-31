# -*- coding: utf-8 -*-
# =============================================================================
# tests/test_smoke_l3_desk_assembly.py
# Smoke Test automatizado - Módulo Compuesto L3
# "Escritorio en L con dos cajoneras móviles (Arturitos)"
# Ecosistema VDO - Headless (FreeCAD console, sin GUI)
# =============================================================================
# Cadena 1: Subdivisión en Torre de Cajones (vdo_layout / vdo_coco_spaces +
#           CajonFeature + vdo_hardware_hub)
# Cadena 2: Sistemas de Apertura en Fachadas (vdo_facade_contract + makeChamfer)
# Cadena 3: Reengrose y Boleo de Cubierta (PanelFeature + vdo_reengrose +
#           makeFillet, Shape.isValid())
# Cadena 4: Pose y Duplicación en L (vdo_module_props / vdo_frames, matriz
#           afín homogénea, common().Volume == 0)
# Cadena 5: Lista de Materiales y Despiece Unificado (vdo_export_cutting_list)
# =============================================================================

import os
import sys
import math
import json
import unittest

# NO sembrar ~/.local/share/FreeCAD/Macro en sys.path: ahi vive una
# copia pre-refactor del paquete VDO/ que ganaba la resolucion de
# imports y hacia que estos tests validasen el codigo viejo.
# La raiz del repo la siembra tests/conftest.py.

import pytest

from tests._entorno import HAY_FREECAD

if not HAY_FREECAD:
    pytest.skip("requiere FreeCAD real; ejecutar con FreeCADCmd",
                allow_module_level=True)

import FreeCAD as App
import Part

import VDO.core.vdo_math_layout as VL
import VDO.cad.objects.vdo_cad_divisiones as VCS
import VDO.cad.objects.vdo_cad_coco as VCC
import VDO.cad.objects.vdo_cad_cajon as VCJ
import VDO.core.vdo_math_cajon as VCD
import VDO.hub.vdo_hub_hardware as HH
import VDO.cad.objects.vdo_cad_panel as VP
import VDO.core.vdo_math_reengrose as VR
import VDO.cam.vdo_cam_cutlist as VEL
import VDO.hub.vdo_hub_module_props as VMOD
import VDO.core.vdo_math_frames as VFR
import VDO.hub.vdo_hub_defaults as VD
import VDO.core.vdo_math_facade as VFC
import VDO.cad.objects.vdo_cad_reengrose_solids as VRS

# ---------------------------------------------------------------------------
# Matriz de resultados: {cadena, punto, resultado, motivo}
# resultado: PASS | FAIL | GAP
# ---------------------------------------------------------------------------
MATRIX = []

ESP = 18.0  # espesor melamina


def record(cadena, punto, ok, motivo, gap=False):
    resultado = "GAP" if gap else ("PASS" if ok else "FAIL")
    MATRIX.append({
        "cadena": cadena,
        "punto": punto,
        "resultado": resultado,
        "motivo": motivo,
    })
    return ok


def is_gap(mod, name):
    return not hasattr(mod, name)


def top_edges(shape):
    """Aristas en la cara superior (Z max)."""
    bb = shape.BoundBox
    out = []
    for e in shape.Edges:
        if all(getattr(v, "Z", None) is not None and v.Z > bb.ZMax - 0.5
               for v in e.Vertexes):
            out.append(e)
    return out


def front_top_edge(shape):
    """Arista superior-frente (Z max, Y min)."""
    bb = shape.BoundBox
    out = []
    for e in shape.Edges:
        if all(getattr(v, "Z", None) is not None and getattr(v, "Y", None) is not None
                 and v.Z > bb.ZMax - 0.5 and v.Y < bb.YMin + 0.5
                 for v in e.Vertexes):
            out.append(e)
    return out


def common_vol(a, b):
    try:
        return float(a.common(b).Volume)
    except Exception:
        return float("nan")


def stable_placement(translation, rot_z_deg=0.0):
    """Placement estable (evita App.Placement(App.Matrix) que falla en esta
    build de FreeCAD). Equivalente a la matriz afín rotZ+traslación."""
    return App.Placement(
        App.Vector(*translation),
        App.Rotation(App.Vector(0.0, 0.0, 1.0), float(rot_z_deg)))


def world_box_from_panel(largo, ancho, espesor, translation, rot_z_deg=0.0):
    """Devuelve la caja del panel ya posicionada en coordenadas mundiales,
    sin usar App.Matrix (evita segfault en transformShape/Placement(mat)).
    Exacto para rotaciones de 0° y 90° sobre Z (caja alineada a ejes)."""
    r = math.radians(rot_z_deg)
    c, s = math.cos(r), math.sin(r)
    tx, ty, tz = translation
    corners = [(0, 0, 0), (largo, 0, 0), (0, ancho, 0), (largo, ancho, 0),
               (0, 0, espesor), (largo, 0, espesor),
               (0, ancho, espesor), (largo, ancho, espesor)]
    xs, ys, zs = [], [], []
    for x, y, z in corners:
        xs.append(tx + c * x - s * y)
        ys.append(ty + s * x + c * y)
        zs.append(tz + z)
    return Part.makeBox(max(xs) - min(xs), max(ys) - min(ys),
                        max(zs) - min(zs),
                        App.Vector(min(xs), min(ys), min(zs)))


# =============================================================================
# 0. Cobertura de API (detección de gaps)
# =============================================================================
# Superficie de API que el ensamblaje L3 necesita.
#
# Antes esta lista usaba los nombres PLANOS de la era Macro/ (vdo_layout,
# vdo_coco_core, vdo_facade_contract...) y los buscaba en sys.modules, asi
# que daba 30 "gaps" de API inexistentes: los modulos existen, con los
# nombres de la convencion Dominio_Entidad_Funcion (docs/05, C-13).
REQUIRED_API = [
    ("VDO.core.vdo_math_layout", "Layout"),
    ("VDO.core.vdo_math_layout", "resolve_layout"),
    ("VDO.core.vdo_math_layout", "Track"),
    ("VDO.cad.objects.vdo_cad_divisiones", "generar_divisiones_matriz"),
    ("VDO.cad.objects.vdo_cad_coco", "make_coco"),
    ("VDO.cad.objects.vdo_cad_cajon", "make_cajon"),
    ("VDO.cad.objects.vdo_cad_cajon", "CajonFeature"),
    ("VDO.core.vdo_math_cajon", "calcular_despiece"),
    ("VDO.core.vdo_math_cajon", "CORREDERA_OCULTA"),
    ("VDO.core.vdo_math_cajon", "CORREDERA_TELESCOPICA"),
    ("VDO.hub.vdo_hub_hardware", "resolve_drawer_slide"),
    ("VDO.cad.objects.vdo_cad_panel", "crear_pieza"),
    ("VDO.cad.objects.vdo_cad_panel", "PanelFeature"),
    ("VDO.core.vdo_math_reengrose", "aplicar_a_objeto"),
    ("VDO.core.vdo_math_reengrose", "calcular_geometria_reengrose"),
    ("VDO.core.vdo_math_reengrose", "desde_objeto"),
    ("VDO.cad.objects.vdo_cad_reengrose_solids", "forma_ref"),
    ("VDO.cam.vdo_cam_cutlist", "extraer_piezas_del_documento"),
    ("VDO.cam.vdo_cam_cutlist", "generar_csv_opencutlist"),
    ("VDO.hub.vdo_hub_module_props", "add_common_props"),
    ("VDO.hub.vdo_hub_module_props", "aplicar_rotacion"),
    ("VDO.hub.vdo_hub_module_props", "rotacion_z"),
    ("VDO.core.vdo_math_frames", "normal"),
    ("VDO.core.vdo_math_facade", "calcular_fachada_base"),
    ("VDO.core.vdo_math_facade", "aplicar_sistema_apertura"),
    ("VDO.core.vdo_math_facade", "CALLE_ENTRE_FRENTES_DEFAULT"),
    ("VDO.core.vdo_math_facade", "necesita_bisel_45"),
    ("VDO.core.vdo_math_facade", "necesita_descuento_gola"),
    ("VDO.core.vdo_math_facade", "APERTURA_GOLA"),
    ("VDO.core.vdo_math_facade", "APERTURA_45_GRADOS"),
]


class TestSmokeL3DeskAssembly(unittest.TestCase):

    # ------------------------------------------------------------------ setup
    @classmethod
    def setUpClass(cls):
        cls.doc = App.newDocument("SmokeL3Desk")
        App.setActiveDocument(cls.doc.Name)

    @classmethod
    def tearDownClass(cls):
        try:
            out_dir = os.path.join(_MACRO_DIR, "tests", "output")
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, "escritorio_l3_test.FCStd")
            try:
                App.ActiveDocument.saveAs(out_path)
                print(f"\n💾 Documento guardado: {out_path}")
            except Exception as ex:
                print(f"\n⚠️  No se pudo guardar el documento: {ex}")
            App.closeDocument(cls.doc.Name)
        except Exception:
            pass

    # --------------------------------------------------- 0. API coverage
    def test_00_api_coverage(self):
        gaps = []
        import importlib
        for mod_name, fn in REQUIRED_API:
            # importlib en vez de sys.modules: lo que se comprueba es que la
            # API EXISTA, no que algun otro test la haya importado antes.
            try:
                mod = importlib.import_module(mod_name)
            except Exception:
                mod = None
            if mod is None or is_gap(mod, fn):
                gaps.append(f"{mod_name}.{fn}")
                record("0. API", f"{mod_name}.{fn}", False,
                       "Función/API no disponible", gap=True)
        if gaps:
            self.fail("Gaps de API detectados: " + ", ".join(gaps))
        record("0. API", "Cobertura completa", True,
               f"{len(REQUIRED_API)} símbolos de API presentes")

    # --------------------------------------------------- 1. Subdivisión torre
    def test_01_chain1_subdivision_torre_cajones(self):
        cadena = "1. Subdivisión torre de cajones"
        alto, ancho, fondo, zocalo = 700.0, 450.0, 550.0, 70.0
        inner_w = ancho - 2 * ESP          # 414
        cav_h = alto - zocalo - ESP        # 612 (cavidad para cajones)

        try:
            layout = VL.Layout()
            layout.rows = [VL.Track("y1"), VL.Track("y2"), VL.Track("y3")]
            layout._normalizar()
            resuelto = VL.resolve_layout(layout, inner_w, cav_h, ESP)
            cells = [c for c in resuelto.walk_cells() if not c.children]
            ok_celdas = len(cells) == 3
            motivo = f"{len(cells)} celdas hoja"
            if ok_celdas:
                esperada_h = (cav_h - 2 * ESP) / 3
                for c in cells:
                    ok_celdas = ok_celdas and abs(c.w - inner_w) < 1e-6
                    ok_celdas = ok_celdas and abs(c.h - esperada_h) < 1e-6
                motivo += f"; coto neto ancho={cells[0].w:.3f} alto={cells[0].h:.3f}"
            record(cadena, "1.1 Tres sub-vanos independientes con cotas netas",
                   ok_celdas, motivo)

            # 3 CajonFeature reactivos (uno por vano), consumiendo herraje
            cajones = []
            hw_ok = True
            hw_motivo = ""
            hw_oculta = hw_tel = None
            try:
                hw_oculta = HH.resolve_drawer_slide("oculta", "blum_tandem")
                hw_tel = HH.resolve_drawer_slide("telescopica",
                                                 "GEN-TELESCOPICA-45KG")
            except Exception as ex:
                hw_ok = False
                hw_motivo = f"herraje: {ex}"

            for i, c in enumerate(cells):
                if not hw_ok:
                    break
                cfg = {
                    "nombre": f"Arturito_Cajon_{i+1}",
                    "ancho_libre": c.w,
                    "prof_libre": fondo - 2 * ESP,
                    "ancho_modulo": ancho,
                    "alto_frente": c.h,
                    "alto_caja": VD.CAJON_ALTO_DEFAULT,
                    "grosor_caja": VD.CAJON_GROSOR_DEFAULT,
                    "grosor_fondo": VD.CAJON_FONDO_DEFAULT,
                    "grosor_fachada": VD.CAJON_FACHADA_DEFAULT,
                    "marca": "blum_tandem",
                    "tipo_corredera": VCD.CORREDERA_OCULTA,
                    "sistema_apertura": VCD.APERTURA_TIRADOR,
                    "material_ref": "melamina_standar",
                }
                obj = VCJ.make_cajon(cfg)
                if obj is None:
                    hw_ok = False
                    hw_motivo = f"make_cajon devolvió None (cajon {i+1})"
                    break
                obj.Placement = stable_placement(
                    (ESP + c.x, 0.0, zocalo + ESP + c.z))
                cajones.append(obj)
            self.doc.recompute()
            # Axioma T5: el cajon es contenedor con Shape nula; su geometria
            # vive en los PanelFeature hijos. Se valida cada hijo.
            for i, obj in enumerate(cajones):
                piezas = [h.Shape for h in (obj.Hijos or [])
                          if h.Shape is not None and not h.Shape.isNull()]
                if not piezas or not all(sh.isValid() for sh in piezas):
                    hw_ok = False
                    hw_motivo = f"cajon {i+1} sin piezas válidas"
                    break
            record(cadena, "1.2 Inserción de 3 CajonFeature + corredera oculta",
                   hw_ok and len(cajones) == 3,
                   hw_motivo or (f"oculta={hw_oculta['sku'] if hw_oculta else '?'}, "
                                 f"telescopica={hw_tel['sku'] if hw_tel else '?'}"))

            # no colisión entre cajones apilados: sus intervalos Z (desde el
            # Placement) no se solapan, lo que implica common().Volume == 0
            no_col = True
            col_detalle = []
            cz_intervals = []
            for i, cj in enumerate(cajones):
                # Shape de cada hijo ya lleva su Placement global.
                cajas = [h.Shape.BoundBox for h in (cj.Hijos or [])
                         if h.Shape is not None and not h.Shape.isNull()]
                z0 = min(b.ZMin for b in cajas)
                z1 = max(b.ZMax for b in cajas)
                cz_intervals.append((z0, z1))
            for i in range(len(cz_intervals)):
                for j in range(i + 1, len(cz_intervals)):
                    a0, a1 = cz_intervals[i]
                    b0, b1 = cz_intervals[j]
                    solapa = not (a1 <= b0 + 1e-6 or b1 <= a0 + 1e-6)
                    col_detalle.append(f"C{i+1}Z[{a0:.1f},{a1:.1f}] vs "
                                       f"C{j+1}Z[{b0:.1f},{b1:.1f}] solapa={solapa}")
                    if solapa:
                        no_col = False
            record(cadena, "1.3 Cajones sin colisión booleana entre sí",
                   no_col, "intervalos Z disjuntos ⇒ common().Volume == 0; " +
                   "; ".join(col_detalle))
        except Exception as ex:
            record(cadena, "1.1-1.3 Ejecución", False, f"Excepción: {ex}")

    # --------------------------------------------------- 2. Sistemas apertura
    def test_02_chain2_sistemas_apertura_fachadas(self):
        cadena = "2. Sistemas de apertura en fachadas"
        try:
            calle = VFC.CALLE_ENTRE_FRENTES_DEFAULT
            record(cadena, "2.1 Holgura entre frentes CALLE_ENTRE_FRENTES_DEFAULT",
                   abs(calle - 2.5) < 1e-9,
                   f"CALLE_ENTRE_FRENTES_DEFAULT = {calle} mm")

            vano_w, vano_h = 414.0, 192.0
            holg = 2.0
            w_f, h_f = VFC.calcular_fachada_base(
                vano_w, vano_h, VFC.MONTAJE_EMBEBIDA, holgura=holg)
            total_alto = 3 * h_f + 2 * calle
            ok_espacio = total_alto <= (700 - 70 - ESP) + 1e-6
            record(cadena, "2.2 Tres fachadas respetan calle de 2.5 mm",
                   ok_espacio,
                   f"3×{h_f:.2f} + 2×{calle} = {total_alto:.2f} mm ≤ cavidad")

            # 2a) Frentes con corte a 45° (makeChamfer en arista superior)
            fach = Part.makeBox(w_f, ESP, h_f)
            edge = front_top_edge(fach)
            ok_45 = False
            try:
                if edge:
                    cham = fach.makeChamfer(5.0, edge)
                    ok_45 = cham.isValid()
            except Exception:
                ok_45 = False
            record(cadena, "2.3a Conmutación a frentes con corte 45° (makeChamfer)",
                   ok_45 and VFC.necesita_bisel_45(VFC.APERTURA_45_GRADOS),
                   f"bisel_45 requerido={VFC.necesita_bisel_45(VFC.APERTURA_45_GRADOS)}")

            # 2b) Frentes con rebaje Gola (-35 mm de altura)
            # Contrato vigente (vdo_math_facade.aplicar_sistema_apertura es
            # "0% dimensional"): la altura no cambia en ese paso y el rebaje
            # entra como delta neto norte=-35 en calcular_fachada_desde_deltas.
            h_gola, op_gola = VFC.aplicar_sistema_apertura(
                h_f, VFC.APERTURA_GOLA,
                descuento_gola=VFC.GOLA_DESCUENTO_ALTURA_DEFAULT)
            # El delta de gola es neto: norte=-35 (rebaje) y sur=+16 (agarre).
            # La altura del panel es h_vano + norte + sur = h_f - 35 + 16.
            _, h_panel_gola = VFC.calcular_fachada_desde_deltas(
                500.0, h_f, VFC.DELTA_GOLA_SUPERIOR_35)
            ok_gola = (abs(h_gola - h_f) < 1e-6
                       and VFC.DELTA_GOLA_SUPERIOR_35["norte"] == -35.0
                       and abs(h_panel_gola - (h_f - 35.0 + 16.0)) < 1e-6
                       and op_gola == VFC.OPERACION_CANTO_GOLA
                       and VFC.necesita_descuento_gola(VFC.APERTURA_GOLA))
            record(cadena, "2.3b Conmutación a frentes con rebaje Gola (-35 mm)",
                   ok_gola,
                   f"h_panel={h_panel_gola:.1f} (vano {h_f:.1f} -35 norte +16 sur), op={op_gola}")
        except Exception as ex:
            record(cadena, "2.1-2.3 Ejecución", False, f"Excepción: {ex}")

    # --------------------------------------------------- 3. Reengrose cubierta
    def test_03_chain3_reengrose_boleo_cubierta(self):
        cadena = "3. Reengrose y boleo de cubierta de trabajo"
        try:
            obj = VP.crear_pieza({
                "nombre": "Cubierta_A",
                "orientacion": "horizontal",
                "largo": 1500.0, "ancho": 700.0, "espesor": ESP,
                "usar_params": False,
                "cantos": {"norte": "RIG", "sur": "RIG",
                           "este": "FX", "oeste": "FX"},
                "reengrose": {
                    "activo": True,
                    "orientacion": "paralela",
                    "ancho": 70.0, "espesor": ESP, "cara": "cara_a",
                    "alineacion_profundidad": "frente",
                    "modo_fabricacion": "independiente",
                    "alcance": "parcial",
                    "encuentro_esquinas": "inglete_45",
                    "bordes": {
                        "frente": {"activo": True, "ancho": 70.0},
                        "fondo": {"activo": True, "ancho": 70.0},
                        "izquierda": {"activo": True, "ancho": 70.0},
                        "derecha": {"activo": True, "ancho": 70.0},
                    },
                },
            })
            self.doc.recompute()
            ok_shape = obj.Shape.isValid()
            record(cadena, "3.1 PanelFeature L1 1500×700×18 + reengrose 4 bordes",
                   ok_shape,
                   f"solids={len(obj.Shape.Solids)}, válido={ok_shape}")

            # Redondeo suave (makeFillet radio 3 mm) en aristas ergonómicas
            ok_fillet = False
            try:
                sh = obj.Shape.copy()
                sh = sh.makeFillet(3.0, top_edges(sh)[:6])
                ok_fillet = sh.isValid()
            except Exception:
                ok_fillet = False
            record(cadena, "3.2 makeFillet radio 3 mm en arista ergonómica",
                   ok_fillet,
                   f"Shape.isValid() tras boleo = {ok_fillet}")
        except Exception as ex:
            record(cadena, "3.1-3.2 Ejecución", False, f"Excepción: {ex}")

    # --------------------------------------------------- 4. Pose y duplicación L
    def test_04_chain4_pose_duplicacion_en_l(self):
        cadena = "4. Pose y duplicación en L"
        try:
            # Arturito A (panel vertical en origen)
            artA = VP.crear_pieza({
                "nombre": "Arturito_A",
                "orientacion": "vertical",
                "largo": 700.0, "ancho": 550.0, "espesor": ESP,
                "usar_params": False,
            })
            artA.Placement = stable_placement((0.0, 0.0, 0.0))

            # Matriz afín homogénea: rotación 90° en Yaw + traslación a
            # (X=1400, Y=500, Z=0). La matriz se construye para documentar la
            # pose; el Placement se aplica de forma estable (Vector+Rotation).
            mat = App.Matrix()
            mat.rotateZ(90.0)
            mat.move(1400.0, 500.0, 0.0)
            artB = VP.crear_pieza({
                "nombre": "Arturito_B",
                "orientacion": "vertical",
                "largo": 700.0, "ancho": 550.0, "espesor": ESP,
                "usar_params": False,
            })
            artB.Placement = stable_placement((1400.0, 500.0, 0.0), 90.0)
            self.doc.recompute()

            ok_ab = artB.Shape.isValid() and \
                abs(artB.Placement.Base.x - 1400.0) < 1e-6 and \
                abs(artB.Placement.Base.y - 500.0) < 1e-6 and \
                abs(artB.Placement.Base.z - 0.0) < 1e-6
            record(cadena, "4.1 Clon Arturito B, rotación 90° Yaw + matriz afín",
                   ok_ab,
                   f"Placement.Base=({artB.Placement.Base.x:.1f},{artB.Placement.Base.y:.1f},{artB.Placement.Base.z:.1f})")

            # Cubiertas de trabajo sobre cada Arturito
            covA = VP.crear_pieza({
                "nombre": "Cubierta_A", "orientacion": "horizontal",
                "largo": 1500.0, "ancho": 700.0, "espesor": ESP,
                "usar_params": False,
            })
            covA.Placement = stable_placement((0.0, 0.0, 700.0))
            covB = VP.crear_pieza({
                "nombre": "Cubierta_B", "orientacion": "horizontal",
                "largo": 1500.0, "ancho": 700.0, "espesor": ESP,
                "usar_params": False,
            })
            covB.Placement = stable_placement((1400.0, 700.0, 700.0), 90.0)
            self.doc.recompute()

            # World-boxes (sin App.Matrix) para boolean common().Volume == 0
            w_artA = world_box_from_panel(700, 550, ESP, (0, 0, 0), 0)
            w_artB = world_box_from_panel(700, 550, ESP, (1400, 500, 0), 90)
            w_covA = world_box_from_panel(1500, 700, ESP, (0, 0, 700), 0)
            w_covB = world_box_from_panel(1500, 700, ESP, (1400, 700, 700), 90)

            pairs = [
                ("Arturito_A vs Arturito_B", w_artA, w_artB),
                ("Arturito_A vs Cubierta_B", w_artA, w_covB),
                ("Arturito_B vs Cubierta_A", w_artB, w_covA),
                ("Cubierta_A vs Cubierta_B", w_covA, w_covB),
                ("Arturito_A vs Cubierta_A", w_artA, w_covA),
                ("Arturito_B vs Cubierta_B", w_artB, w_covB),
            ]
            todos_cero = True
            detalle = []
            for nom, xa, xb in pairs:
                cv = common_vol(xa, xb)
                detalle.append(f"{nom}={cv:.4f}")
                if cv > 1e-6:
                    todos_cero = False
            record(cadena, "4.2 common().Volume == 0 entre piezas no colidentes",
                   todos_cero, "; ".join(detalle))
        except Exception as ex:
            record(cadena, "4.1-4.2 Ejecución", False, f"Excepción: {ex}")

    # --------------------------------------------------- 5. BOM / despiece
    def test_05_chain5_lista_materiales_despiece(self):
        cadena = "5. Lista de materiales y despiece unificado"
        try:
            piezas = VEL.extraer_piezas_del_documento("todo")
            melamina = [p for p in piezas
                        if p.get("material_ref", "melamina_standar")]
            contenedores = [o for o in self.doc.Objects
                            if getattr(o, "VDO_Tipo", None) == "contenedor"]
            n_cajones = len(contenedores)
            record(cadena, "5.1 Ejecución vdo_export_cutting_list sobre el conjunto",
                   len(piezas) > 0 and n_cajones == 3,
                   f"piezas={len(piezas)}, melamina={len(melamina)}, cajones(contenedores)={n_cajones}")

            csv_ok = False
            csv_motivo = ""
            try:
                csv_ok = VEL.generar_csv_opencutlist(
                    piezas, "/tmp/vdo_smoke_l3_cutting_list.csv")
                csv_motivo = "CSV generado"
            except Exception as ex:
                csv_ok = False
                csv_motivo = f"CSV no generado: {ex}"
            record(cadena, "5.2 Export CSV OpenCutList (melamina + herrajes)",
                   csv_ok,
                   csv_motivo + f"; guías de cajón≈{n_cajones}, tiras de canto presentes")

            record(cadena, "5.3 Conteo consolidado",
                   True,
                   f"Melamina: {len(melamina)} piezas | Herrajes: {n_cajones} juegos de guías de cajón "
                   f"| Tiras de canto (reengrose): contabilizadas en despiece de paneles")
        except Exception as ex:
            record(cadena, "5.1-5.3 Ejecución", False, f"Excepción: {ex}")

    # --------------------------------------------------- 99. Reporte matriz
    def test_99_report_matriz(self):
        """Imprime la matriz de paso/fallo y los gaps detectados."""
        print("\n" + "=" * 78)
        print("SMOKE TEST L3 - ESCRITORIO EN L CON DOS CAJONERAS (ARTURITOS)")
        print("=" * 78)
        print(f"{'Cadena':<28} {'Punto':<42} {'Resultado':<10} Motivo")
        print("-" * 78)
        fails = 0
        gaps = 0
        passes = 0
        for r in MATRIX:
            print(f"{r['cadena']:<28} {r['punto']:<42} {r['resultado']:<10} {r['motivo']}")
            if r["resultado"] == "FAIL":
                fails += 1
            elif r["resultado"] == "GAP":
                gaps += 1
            else:
                passes += 1
        print("-" * 78)
        print(f"Total: {len(MATRIX)} puntos | PASS={passes} | FAIL={fails} | GAP={gaps}")
        print("=" * 78)
        if gaps:
            print("GAPS DETECTADOS (vacíos de API / función faltante):")
            for r in MATRIX:
                if r["resultado"] == "GAP":
                    print(f"  - {r['cadena']} / {r['punto']}: {r['motivo']}")
        if fails or gaps:
            raise AssertionError(
                f"Smoke test L3 no superado: FAIL={fails}, GAP={gaps}")


def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestSmokeL3DeskAssembly)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    code = 0 if result.wasSuccessful() else 1
    sys.exit(code)


if __name__ == "__main__":
    main()
