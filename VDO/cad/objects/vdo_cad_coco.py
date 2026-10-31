# -*- coding: utf-8 -*-
# =====================================================================
# vdo_coco_core.py
# Motor unificado de cofres VDO (COCO = Contenedor Cohesivo)
# FeaturePython con ViewProvider para Task Panel visual
# =====================================================================

import FreeCAD as App
import Part
import sys
import json

from VDO._paths import ensure_sys_path
ensure_sys_path()

from VDO.shared import vdo_shared_guardian
import VDO.hub.vdo_hub_defaults as VDO_D
import VDO.hub.vdo_hub_module_props as VDO_MOD
import VDO.core.vdo_math_frames as VDO_FR
from VDO.shared import vdo_shared_finish as VDO_FINISH
import VDO.core.vdo_math_reengrose as VDO_RE
from VDO.core.vdo_math_caras import (
    generar_piezas_cara, piezas_por_caras,
    MODO_SOLIDO, MODO_AMARRES, MODO_MARCO_RINCON, MODO_NULO, MODOS_CARA_VALIDOS,
    ROL_TECHO, ROL_BASE, ROL_LATERAL_IZQ, ROL_LATERAL_DER, ROL_FONDO,
    CARAS_COCO,
)
from VDO.core.vdo_math_visto import generar_pieza_visto, VISTO_SIN_DESFASES, CARAS_VISTO_VALIDAS
from VDO.core.vdo_math_layout import (
    generar_pieza_gola, calcular_bocado_l_gola,
    GOLA_ALTURA_PASO_DEFAULT, GOLA_RETRANQUEO_DEFAULT,
    TIPO_GOLA,
)
from VDO.hub.vdo_hub_registry import SPEC_COCO
from VDO.hub.vdo_hub_schema import aplicar_esquema, aplicar_config
from VDO.cad.objects.vdo_cad_reengrose_solids import forma_ref


def _cargar_reengroses(obj):
    texto = getattr(obj, "VDO_Reengrose_JSON", "") or "{}"
    try:
        datos = json.loads(texto) if isinstance(texto, str) else dict(texto)
    except (TypeError, ValueError):
        return {}
    return datos if isinstance(datos, dict) else {}


def _modificador_mapa(mapa, clave):
    datos = (mapa or {}).get(clave)
    if not datos:
        return VDO_RE.ReengroseModifier()
    try:
        return VDO_RE.ReengroseModifier(datos)
    except VDO_RE.ReengroseError:
        return VDO_RE.ReengroseModifier()


def _solido_caja(caja):
    """Caja nominal {x,y,z,w,h,d} como sólido Part."""
    return Part.makeBox(
        float(caja["w"]), float(caja["h"]), float(caja["d"]),
        App.Vector(float(caja["x"]), float(caja["y"]), float(caja["z"])))


_VECTORES_EJE = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0),
                 "z": (0.0, 0.0, 1.0)}


def _prisma_de_solido(solido):
    """Prisma recto exacto {puntos, eje, largo} equivalente a `solido`.

    Un recorte de tira no siempre es una caja: un inglete deja un triangulo.
    Se describe como cara inferior (puntos globales) extruida `largo` mm
    sobre `eje`. Devuelve None si el solido no es un prisma recto simple.
    """
    bb = solido.BoundBox
    rangos = {"x": (bb.XMin, bb.XLength), "y": (bb.YMin, bb.YLength),
              "z": (bb.ZMin, bb.ZLength)}
    for eje in ("z", "x", "y"):
        minimo, largo = rangos[eje]
        if largo <= 1e-9:
            continue
        caras = [
            f for f in solido.Faces
            if abs(getattr(f.BoundBox, eje.upper() + "Min") - minimo) < 1e-6
            and abs(getattr(f.BoundBox, eje.upper() + "Max") - minimo) < 1e-6]
        if len(caras) != 1 or len(caras[0].Wires) != 1:
            continue
        puntos = [[v.X, v.Y, v.Z] for v in caras[0].OuterWire.OrderedVertexes]
        if len(puntos) < 3:
            continue
        vec = App.Vector(*_VECTORES_EJE[eje]) * largo
        candidato = Part.Face(Part.makePolygon(
            [App.Vector(*q) for q in puntos] + [App.Vector(*puntos[0])])
        ).extrude(vec)
        tol = 1e-6 * max(1.0, solido.Volume)
        if (abs(candidato.Volume - solido.Volume) <= tol
                and abs(candidato.common(solido).Volume - solido.Volume) <= tol):
            return {"puntos": puntos, "eje": eje, "largo": largo}
    return None


def _prismas_removidos(nominal, resultante):
    """Prismas (globales) de lo que `resultante` quita de `nominal`."""
    if resultante is None or resultante.isNull():
        prisma = _prisma_de_solido(nominal)
        return [prisma] if prisma else []
    prismas = []
    for solido in nominal.cut(resultante).Solids:
        if solido.isNull() or solido.Volume <= 1e-6:
            continue
        prisma = _prisma_de_solido(solido)
        if prisma is None:
            App.Console.PrintWarning(
                "[VDO] Recorte de tira no prismático: no se puede describir "
                "para el panel hijo.\n")
            continue
        prismas.append(prisma)
    return prismas


def _mocheos_locales(prismas, origen):
    """Pasa prismas globales al marco local de una pieza con origen `origen`."""
    ox, oy, oz = float(origen["x"]), float(origen["y"]), float(origen["z"])
    return [{"puntos": [[q[0] - ox, q[1] - oy, q[2] - oz]
                        for q in pr["puntos"]],
             "eje": pr["eje"], "largo": pr["largo"]}
            for pr in prismas]


def _cortar_shape(forma, recorte):
    """Resta robusta: OCC falla al cortar compounds multi-solido."""
    if forma is None or forma.isNull():
        return None
    if forma.ShapeType != "Compound":
        try:
            resultado = forma.cut(recorte)
        except ValueError:
            return None
        if resultado.isNull() or resultado.Volume <= 1e-9:
            return None
        return resultado
    solidos = []
    for solido in forma.Solids:
        try:
            resultado = solido.cut(recorte)
        except ValueError:
            continue
        if resultado.isNull():
            continue
        solidos.extend(
            s for s in resultado.Solids if not s.isNull() and s.Volume > 1e-9)
    if not solidos:
        return None
    return Part.makeCompound(solidos)


def _expandir_reengrose(pieza):
    mod = pieza.get("reengrose")
    caja = pieza.get("caja")
    ejes = pieza.get("ejes")
    if not mod or not caja or not ejes:
        return [pieza]
    caja = dict(caja)
    caja["nombre"] = pieza.get("nombre", "Pieza")
    cantos_bloque = (
        pieza.get("cantos")
        if mod.get("modo_fabricacion") == "pacha" else None)
    try:
        subpiezas = VDO_RE.despiece_caja(
            caja, mod, ejes, cantos=pieza.get("cantos"),
            material_ref=pieza.get(
                "material_ref", "melamina_standar"),
            orientacion=pieza.get("orientacion", "vertical"),
            cantos_bloque=cantos_bloque)
    except VDO_RE.ReengroseError as exc:
        App.Console.PrintWarning(
            f"[VDO] Reengrose inválido en '{pieza.get('nombre')}': {exc}\n")
        return [pieza]
    # Cada tira de borde conserva su caja nominal (despiece_caja la deja en
    # caja_geometrica, unica por tira). Lo que los choques le quitaron viaja
    # como prismas en su marco local; no se usa un BoundBox comun, que daba
    # la misma caja a todas las tiras y perdia las muescas.
    cortes_tiras = pieza.get("tiras_cortes") or {}
    for sub in subpiezas:
        if sub.get("rol_reengrose") != "refuerzo":
            continue
        cortes = cortes_tiras.get(sub.get("nombre"))
        if cortes and sub.get("caja_geometrica"):
            sub["mocheos_json"] = json.dumps(
                _mocheos_locales(cortes, sub["caja_geometrica"]))
    for sub in subpiezas:
        if sub.get("rol_reengrose") == "refuerzo":
            # Los refuerzos de reengrose son piezas adicionales del panel
            # padre: no comparten su rol para que _propagar_dimensiones_hijos
            # y posiciones() no les asignen las cotas del panel principal.
            sub["rol"] = pieza.get("rol", "") + "_refuerzo"
        else:
            sub["rol"] = pieza.get("rol", "")
        sub["rol_padre"] = pieza.get("rol", "")
        sub["clave_reengrose"] = pieza.get("clave_reengrose", "")
        if pieza.get("mocheos") and sub.get("rol_reengrose") == "base":
            sub["mocheos"] = pieza["mocheos"]
    return subpiezas


class CocoFeature:
    """FeaturePython que genera la geometría de un cofre COCO."""

    def __init__(self, obj):
        # Las 23 propiedades del COCO las declara SPEC_COCO en
        # vdo_hub_registry. Antes eran 63 lineas de obj.addProperty()
        # aqui, con el tipo, el grupo, la ayuda y el default repetidos
        # tambien en el TaskPanel y en make_coco().
        aplicar_esquema(obj, SPEC_COCO)
        obj.Proxy = self
        self._bloqueo_sync = False

    def onDocumentRestored(self, fp):
        """Migracion de documentos guardados antes del arreglo del DAG."""
        aplicar_esquema(fp, SPEC_COCO)
        for hijo in list(getattr(fp, "Hijos", None) or []):
            if hijo is not None:
                VDO_MOD.migrar_parent_link(hijo)

    def execute(self, fp):
        """Reconstruir la geometría del cofre."""
        import Part

        try:
            alto = float(fp.Alto)
            ancho = float(fp.Ancho)
            fondo = float(fp.FondoModulo)
            espesor = float(fp.Espesor)
            tapa = fp.Tapa
            base = fp.Base
            tiene_fondo = fp.TieneFondo
            calibre_fondo = float(fp.CalibreFondo)
            prof_ranura = float(fp.ProfundidadRanura)
            dist_borde = float(fp.DistanciaBorde)

            # --- Concepto 2: Estados Constructivos de Caras ---
            # Lee VDO_Chassis_JSON (establecido por el TaskPanel) para saber
            # el modo constructivo de cada cara. Si no hay config, se deriva
            # del estado legacy (tapa/base/Piezas_Omitidas).
            caras_cfg = {}
            try:
                _chassis_raw = getattr(fp, "VDO_Chassis_JSON", "") or "{}"
                _chassis = json.loads(_chassis_raw) if isinstance(_chassis_raw, str) else {}
                _caras_raw = _chassis.get("caras", {}) if isinstance(_chassis, dict) else {}
                for cara in CARAS_COCO:
                    c = _caras_raw.get(cara, {}) if isinstance(_caras_raw, dict) else {}
                    modo = str(c.get("modo", "")).strip().upper()
                    if modo not in MODOS_CARA_VALIDOS:
                        # Deriva desde legacy: activa=True -> SOLIDO, activa=False -> NULO
                        modo = MODO_SOLIDO if c.get("activa", True) else MODO_NULO
                    caras_cfg[cara] = {"modo": modo}
            except (ValueError, TypeError, AttributeError):
                caras_cfg = {cara: {"modo": MODO_SOLIDO} for cara in CARAS_COCO}

            # Modos resueltos por cara (para decisiones rápidas)
            caras_modos = {cara: cfg.get("modo", MODO_SOLIDO) for cara, cfg in caras_cfg.items()}

            boxes = []

            # --- Calcular dimensiones de laterales ---
            lat_height = alto
            lat_pos_z = 0.0

            if tapa == "externo":
                lat_height -= espesor
            if base == "externo":
                lat_height -= espesor
                lat_pos_z = espesor

            # --- Calcular dimensiones de base ---
            if base == "externo":
                base_length = ancho
                base_pos_x = 0.0
            else:
                base_length = ancho - (espesor * 2)
                base_pos_x = espesor

            base_pos_z = 0.0

            # --- Calcular dimensiones de tapa ---
            if tapa == "externo":
                techo_length = ancho
                techo_pos_x = 0.0
            else:
                techo_length = ancho - (espesor * 2)
                techo_pos_x = espesor

            techo_pos_z = alto - espesor

            # Panel lateral izquierdo
            lat_izq = Part.makeBox(espesor, fondo, lat_height,
                                   App.Vector(0, 0, lat_pos_z))

            # Panel lateral derecho
            lat_der = Part.makeBox(espesor, fondo, lat_height,
                                   App.Vector(ancho - espesor, 0, lat_pos_z))

            # Panel base
            panel_base = Part.makeBox(base_length, fondo, espesor,
                                      App.Vector(base_pos_x, 0, base_pos_z))

            # Panel techo
            panel_techo = Part.makeBox(techo_length, fondo, espesor,
                                       App.Vector(techo_pos_x, 0, techo_pos_z))

            # --- Fondo en Y+ (nunca en el frente) ---
            fondo_box = None
            fondo_es_delgado = False
            f_len = f_alt = f_x = f_y = f_z = 0.0
            if tiene_fondo:
                fondo_es_delgado = calibre_fondo <= VDO_D.FONDO_UMBRAL_DELGADO
                alto_cavidad = max(0.0, alto - (espesor * 2))
                ancho_cavidad = max(0.0, ancho - (espesor * 2))

                if fondo_es_delgado:
                    prof = min(float(prof_ranura), max(0.0, espesor - 0.1))
                    # El fondo delgado se coloca ENTRE los laterales y entre
                    # techo/base, no dentro de las ranuras. Usar prof para
                    # expandir f_x/f_z/f_len/f_alt meteria el fondo en las
                    # ranuras de los paneles de carcasa, cuyos PanelFeature
                    # hijos son boxes simples sin ranura, provocando solapes
                    # de volumen (Problema B del diagnostico).
                    f_len = ancho_cavidad
                    f_alt = alto_cavidad
                    f_x = espesor
                    f_z = espesor
                    f_y = max(0.0, fondo - calibre_fondo - prof)
                    f_y = min(f_y, max(0.0, fondo - calibre_fondo))

                    g_y = f_y
                    if prof > 0 and alto_cavidad > 0 and ancho_cavidad > 0:
                        lat_izq = lat_izq.cut(Part.makeBox(
                            prof, calibre_fondo, alto_cavidad + (prof * 2),
                            App.Vector(espesor - prof, g_y, espesor - prof)))
                        lat_der = lat_der.cut(Part.makeBox(
                            prof, calibre_fondo, alto_cavidad + (prof * 2),
                            App.Vector(ancho - espesor, g_y, espesor - prof)))
                        panel_base = panel_base.cut(Part.makeBox(
                            ancho_cavidad + (prof * 2), calibre_fondo, prof,
                            App.Vector(espesor - prof, g_y, espesor - prof)))
                        panel_techo = panel_techo.cut(Part.makeBox(
                            ancho_cavidad + (prof * 2), calibre_fondo, prof,
                            App.Vector(espesor - prof, g_y, alto - espesor)))
                else:
                    f_len = ancho_cavidad
                    f_alt = alto_cavidad
                    f_x = espesor
                    f_z = espesor
                    f_y = fondo - calibre_fondo - dist_borde
                    f_y = max(espesor, min(f_y, max(0.0, fondo - calibre_fondo)))

                fondo_box = Part.makeBox(f_len, calibre_fondo, f_alt,
                                         App.Vector(f_x, f_y, f_z))

            # --- Concepto 2: Piezas para caras con modo no-SOLIDO ---
            # AMARRES genera tiras de 70 mm; MARCO_RINCON genera travesaños +
            # poste ciego. Se crean como boxes independientes y se añaden al
            # despiece, sin pasar por el motor de reengrose de carcasa.
            dims_coco = {"alto": alto, "ancho": ancho, "fondo": fondo,
                         "espesor": espesor, "tapa": tapa}
            _prefix = f"{fp.Label}_"
            for cara in CARAS_COCO:
                modo = caras_modos[cara]
                if modo == MODO_SOLIDO or modo == MODO_NULO:
                    continue
                for pz in generar_piezas_cara(cara, caras_cfg[cara], dims_coco):
                    _b = Part.makeBox(
                        pz["w"], pz["h"], pz["d"],
                        App.Vector(pz["x"], pz["y"], pz["z"]))
                    boxes.append(_b)

            omitidas = set(fp.Piezas_Omitidas or [])
            # Caras NULO o con modo no-SOLIDO no usan la caja legacy
            for cara, modo in caras_modos.items():
                if modo != MODO_SOLIDO:
                    omitidas.add(cara)

            if fondo_box is not None and "fondo" not in omitidas:
                boxes.append(fondo_box)

            # --- Reengroses de carcasa ---
            reengroses = _cargar_reengroses(fp)
            obstaculos = []
            shell_tiras = []
            shell_info = {}
            shell_refs = []
            omitidas = set(fp.Piezas_Omitidas or [])
            shell_cores = {}
            if "lateral_izquierdo" not in omitidas:
                shell_cores["lateral_izquierdo"] = lat_izq
            if "lateral_derecho" not in omitidas:
                shell_cores["lateral_derecho"] = lat_der
            if "base" not in omitidas:
                shell_cores["base"] = panel_base
            if "techo" not in omitidas:
                shell_cores["techo"] = panel_techo
            if fondo_box is not None and "fondo" not in omitidas:
                shell_cores["fondo"] = fondo_box

            def _aplicar_shell(clave, caja, ejes):
                mod = _modificador_mapa(reengroses, clave)
                shell_info[clave] = {
                    "caja": caja,
                    "ejes": ejes,
                    "reengrose": mod.to_dict() if mod.activo else None,
                }
                if not mod.activo:
                    return
                try:
                    geo = VDO_RE.calcular_geometria_caja(caja, mod, ejes)
                except VDO_RE.ReengroseError as exc:
                    App.Console.PrintWarning(
                        f"[VDO] Reengrose {clave} ignorado: {exc}\n")
                    return
                for i, ref in enumerate(geo["refuerzos"]):
                    forma = forma_ref(ref)
                    if forma is None:
                        continue
                    indice = len(boxes)
                    boxes.append(forma)
                    tira = dict(ref)
                    tira["clave"] = f"{clave}_tira{i + 1:02d}"
                    tira["host"] = clave
                    tira["orientacion_tira"] = (
                        "vertical" if ejes.get("largo") == "z"
                        else "horizontal")
                    tira["modo_choque"] = (
                        mod.comportamiento_choque_nucleo)
                    crudo = reengroses.get(clave) or {}
                    tira["modo_explicito"] = (
                        "comportamiento_choque_nucleo" in crudo)
                    prioridad = getattr(
                        mod, "prioridad_encuentro_tiras", None)
                    tira["prioridad"] = (
                        None if prioridad
                        == VDO_RE.DEFAULTS["prioridad_encuentro_tiras"]
                        else prioridad)
                    segmento = {
                        "x": float(ref["x"]), "y": float(ref["y"]),
                        "z": float(ref["z"]), "w": float(ref["w"]),
                        "h": float(ref["h"]), "d": float(ref["d"]),
                    }
                    if ref.get("poligono"):
                        segmento["poligono"] = list(ref["poligono"])
                        segmento["eje_extrusion"] = ref.get(
                            "eje_extrusion", "z")
                    tira["segmentos"] = [segmento]
                    tira["shape"] = forma
                    shell_refs.append({
                        "indice": indice,
                        "clave": clave,
                        "shape": forma,
                        "tira": tira,
                    })
                    shell_tiras.append(tira)
                    obstaculos.append(tira)

            _aplicar_shell(
                "lateral_izquierdo",
                {"nombre": f"{fp.Label}_Lateral_Izq",
                 "x": 0.0, "y": 0.0, "z": espesor,
                 "w": espesor, "h": fondo,
                 "d": max(0.0, alto - (espesor * 2))},
                {"largo": "z", "ancho": "y", "espesor": "x"})
            _aplicar_shell(
                "lateral_derecho",
                {"nombre": f"{fp.Label}_Lateral_Der",
                 "x": ancho - espesor, "y": 0.0, "z": espesor,
                 "w": espesor, "h": fondo,
                 "d": max(0.0, alto - (espesor * 2))},
                {"largo": "z", "ancho": "y", "espesor": "x"})
            _aplicar_shell(
                "base",
                {"nombre": f"{fp.Label}_Base",
                 "x": base_pos_x, "y": 0.0, "z": base_pos_z,
                 "w": base_length, "h": fondo, "d": espesor},
                {"largo": "x", "ancho": "y", "espesor": "z"})
            _aplicar_shell(
                "techo",
                {"nombre": f"{fp.Label}_Techo",
                 "x": techo_pos_x, "y": 0.0, "z": techo_pos_z,
                 "w": techo_length, "h": fondo, "d": espesor},
                {"largo": "x", "ancho": "y", "espesor": "z"})
            if tiene_fondo:
                _aplicar_shell(
                    "fondo",
                    {"nombre": f"{fp.Label}_Fondo",
                     "x": f_x, "y": f_y, "z": f_z,
                     "w": f_len, "h": calibre_fondo, "d": f_alt},
                    {"largo": "x", "ancho": "z", "espesor": "y"})

            # --- Divisiones internas (matriz de vanos v2) ---
            divisiones_json = getattr(fp, "VDO_Divisiones", "")
            divisiones_piezas = []

            from VDO.core.vdo_math_layout import cavidad_interior
            cavidad = cavidad_interior(alto, ancho, espesor)
            ancho_util = cavidad["ancho"]
            altura_util = cavidad["alto"]
            x_util = cavidad["x0"]
            z_util = cavidad["z0"]

            resuelto = None
            divs = []
            indice_divs = None
            fondo_divisiones = max(0.0, f_y) if tiene_fondo else fondo
            if divisiones_json:
                from VDO.cad.objects.vdo_cad_divisiones import generar_divisiones_matriz
                divs, resumen, piezas, resuelto = generar_divisiones_matriz(
                    divisiones_json, ancho_util, altura_util,
                    fondo_divisiones, espesor, x_util, z_util,
                    reengroses=reengroses, obstaculos=obstaculos)
                indice_divs = len(boxes)
                boxes.extend(divs)
                divisiones_piezas.extend(piezas)
                fp.ResumenEspacios = resumen
            else:
                fp.ResumenEspacios = ""

            # --- Concepto 3B: Bocado en "L" de gola sobre laterales ---
            # Debe ejecutarse ANTES de meter los laterales a boxes_para_extender
            # para que el compound del mueble lleve los laterales ya cortados.
            # Se coloca DESPUÉS de la resolución de divisiones porque necesita
            # resuelto.cells, que solo existe cuando hay VDO_Divisiones.
            if resuelto is not None:
                for cell_res in resuelto.cells:
                    bocado = calcular_bocado_l_gola(
                        cell_res, fondo_coco=fondo,
                        altura_paso=getattr(cell_res.cell, "gola_altura_paso",
                                            GOLA_ALTURA_PASO_DEFAULT),
                        retranqueo=getattr(cell_res.cell, "gola_retranqueo",
                                           GOLA_RETRANQUEO_DEFAULT))
                    if bocado is None:
                        continue

                    # Bocado para lateral izquierdo (X: 0 a espesor)
                    _bocado_izq = Part.makeBox(
                        espesor, bocado["h"], bocado["d"],
                        App.Vector(0.0, bocado["y"], bocado["z"]))
                    lat_izq = lat_izq.cut(_bocado_izq)

                    # Bocado para lateral derecho (X: ancho - espesor a ancho)
                    _bocado_der = Part.makeBox(
                        espesor, bocado["h"], bocado["d"],
                        App.Vector(ancho - espesor, bocado["y"], bocado["z"]))
                    lat_der = lat_der.cut(_bocado_der)

            boxes_para_extender = []
            if "lateral_izquierdo" not in omitidas:
                boxes_para_extender.append(lat_izq)
            if "lateral_derecho" not in omitidas:
                boxes_para_extender.append(lat_der)
            if "base" not in omitidas:
                boxes_para_extender.append(panel_base)
            if "techo" not in omitidas:
                boxes_para_extender.append(panel_techo)
            boxes.extend(boxes_para_extender)

            # --- Resolucion general tira contra tira y tira contra nucleo ---
            division_tiras = list(getattr(resuelto, "tiras", []) or [])
            from VDO.cad.objects.vdo_cad_divisiones import resolver_tiras, _shape_tira

            # Las tiras de carcasa con "interrumpir_tira" se segmentan
            # de forma controlada alrededor de las divisiones.
            for tira in shell_tiras:
                if tira.get("modo_choque") != "interrumpir_tira":
                    continue
                for pz in divisiones_piezas:
                    caja = pz.get("caja_geometrica")
                    if not caja:
                        continue
                    nuevos = []
                    for segmento in tira.get("segmentos") or []:
                        if VDO_RE.detectar_colision(segmento, caja):
                            nuevos.extend(
                                VDO_RE.recortar_tira_contra_tira(
                                    segmento, caja))
                        else:
                            nuevos.append(segmento)
                    tira["segmentos"] = nuevos

            resolver_tiras(shell_tiras + division_tiras)

            mapa_divs = {id(shape): i for i, shape in enumerate(divs)}
            for tira in division_tiras:
                viejo = tira.get("shape")
                nuevo = _shape_tira(tira)
                tira["shape"] = nuevo
                idx = mapa_divs.get(id(viejo))
                if idx is not None:
                    divs[idx] = nuevo if nuevo is not None else Part.Shape()
                    boxes[indice_divs + idx] = divs[idx]

            strip_shape_ids = {
                id(tira.get("shape")) for tira in division_tiras
                if tira.get("shape") is not None}

            for entry in shell_refs:
                tira = entry["tira"]
                forma = _shape_tira(tira)
                if forma is None:
                    boxes[entry["indice"]] = Part.Shape()
                    continue
                for clave, nucleo in shell_cores.items():
                    if clave == entry["clave"]:
                        continue
                    if (forma.BoundBox.intersect(nucleo.BoundBox)
                            and forma.common(nucleo).Volume > 1e-6):
                        forma = _cortar_shape(forma, nucleo)
                        if forma is None:
                            break
                if forma is not None:
                    for division in divs:
                        if (division.isNull()
                                or id(division) in strip_shape_ids):
                            continue
                        if (forma.BoundBox.intersect(division.BoundBox)
                                and forma.common(division).Volume > 1e-6):
                            forma = _cortar_shape(forma, division)
                            if forma is None:
                                break
                boxes[entry["indice"]] = (
                    forma if forma is not None else Part.Shape())
                tira["shape"] = forma
                # Lo que se quito de la caja nominal de cada tira, como
                # prismas: PanelFeature los resta de su caja.
                shell_info[entry["clave"]].setdefault(
                    "tiras_cortes", {})[tira.get("nombre")] = (
                    _prismas_removidos(_solido_caja(tira), forma))

            # === GUARDAR DATOS DE LOS PANELES PARA EXPORTACIÓN ===
            # Convención: largo/ancho = caras del tablero, espesor = grosor.
            lados_vistos, lados_apoyados = VDO_FR.cargar_exposicion(fp)

            # --- Concepto 3A: Paneles Visto (embellecedor de costado) ---
            # Lee VDO_Chassis_JSON["vistos"] y genera una pieza visto por cara activa.
            _vistos_cfg = {}
            try:
                _chassis_vistos = _chassis.get("vistos", {}) if isinstance(_chassis, dict) else {}
                if isinstance(_chassis_vistos, dict):
                    for cara_v in CARAS_VISTO_VALIDAS:
                        cv = _chassis_vistos.get(cara_v, {})
                        if cv.get("activo", False):
                            _vistos_cfg[cara_v] = cv
            except (ValueError, TypeError, AttributeError):
                _vistos_cfg = {}

            piezas_visto = []
            for cara_v, cfg_v in _vistos_cfg.items():
                try:
                    pz_v = generar_pieza_visto(cara_v, cfg_v, dims_coco)
                    _b_v = Part.makeBox(
                        pz_v["w"], pz_v["h"], pz_v["d"],
                        App.Vector(pz_v["x"], pz_v["y"], pz_v["z"]))
                    boxes.append(_b_v)
                    piezas_visto.append(pz_v)
                except Exception as exc:
                    App.Console.PrintWarning(
                        f"[VDO COCO] No se pudo generar visto '{cara_v}': {exc}\n")

            # Construye paneles_data según los modos de cara (Concepto 2).
            # Caras SOLIDO usan las entradas legacy; caras AMARRES/MARCO_RINCON
            # usan las piezas de generar_piezas_cara(); caras NULO se omiten.
            paneles_data = []

            def _panel_entry(nombre, rol, largo, ancho, espesor_val,
                             orientacion, caja_geo=None, material=None,
                             extra=None):
                entry = {
                    "nombre": nombre,
                    "tipo": "panel",
                    "rol": rol,
                    "largo": float(largo),
                    "ancho": float(ancho),
                    "espesor": float(espesor_val),
                    "orientacion": orientacion,
                    "cantidad": 1,
                    "material_ref": material or fp.VDO_Material_Ref,
                }
                if caja_geo is not None:
                    entry["caja_geometrica"] = caja_geo
                if extra:
                    entry.update(extra)
                return entry

            for cara in CARAS_COCO:
                modo = caras_modos[cara]
                if modo == MODO_NULO:
                    continue

                if modo != MODO_SOLIDO:
                    # Concepto 2: piezas desde el contrato puro de caras
                    for pz in generar_piezas_cara(cara, caras_cfg[cara], dims_coco):
                        caja_geo = {
                            "x": pz["x"], "y": pz["y"], "z": pz["z"],
                            "w": pz["w"], "h": pz["h"], "d": pz["d"],
                        }
                        # Orientacion: si el espesor (d) es la menor dim, es
                        # horizontal; si es X, vertical de pie; si es Y, vertical girada.
                        dims_pz = [pz["w"], pz["h"], pz["d"]]
                        menor = min(dims_pz)
                        if menor == pz["d"]:
                            orientacion = "horizontal"
                        elif menor == pz["w"]:
                            orientacion = "vertical"
                        else:
                            orientacion = "vertical"
                        paneles_data.append(_panel_entry(
                            f"{fp.Label}_{pz['nombre']}", pz["rol"],
                            pz["w"], pz["h"], pz["espesor"],
                            orientacion, caja_geo=caja_geo))
                else:
                    # Modo SOLIDO: entradas legacy (posicionamiento tapa/base)
                    if cara == "izquierda":
                        paneles_data.append(_panel_entry(
                            f"{fp.Label}_Lateral_Izq", ROL_LATERAL_IZQ,
                            fondo, lat_height, espesor, "vertical"))
                    elif cara == "derecha":
                        paneles_data.append(_panel_entry(
                            f"{fp.Label}_Lateral_Der", ROL_LATERAL_DER,
                            fondo, lat_height, espesor, "vertical"))
                    elif cara == "base":
                        paneles_data.append(_panel_entry(
                            f"{fp.Label}_Base", ROL_BASE,
                            base_length, fondo, espesor, "horizontal"))
                    elif cara == "techo":
                        paneles_data.append(_panel_entry(
                            f"{fp.Label}_Techo", ROL_TECHO,
                            techo_length, fondo, espesor, "horizontal"))
                    elif cara == "fondo" and tiene_fondo:
                        paneles_data.append(_panel_entry(
                            f"{fp.Label}_Fondo", ROL_FONDO,
                            f_len, f_alt, calibre_fondo, "vertical",
                            extra={"fondo_delgado": fondo_es_delgado}))

            for pz in divisiones_piezas:
                pz["nombre"] = f"{fp.Label}_{pz['nombre']}"
                pz["material_ref"] = fp.VDO_Material_Ref
                # Convertir mocheos (coordenadas globales COCO) al marco local
                # del panel, para que PanelFeature pueda aplicar los cortes
                # sobre su propio box base.
                _caja = pz.get("caja_geometrica") or {}
                _mocheos = pz.get("mocheos")
                if _caja and _mocheos:
                    _m_loc = []
                    for _m in _mocheos:
                        _m_l = dict(_m)
                        _m_l["x"] = float(_m.get("x", 0.0)) - float(
                            _caja.get("x", 0.0))
                        _m_l["y"] = float(_m.get("y", 0.0)) - float(
                            _caja.get("y", 0.0))
                        _m_l["z"] = float(_m.get("z", 0.0)) - float(
                            _caja.get("z", 0.0))
                        _m_loc.append(_m_l)
                    pz["mocheos_json"] = json.dumps(_m_loc)
                paneles_data.append(pz)

            # Añadir piezas visto al despiece (Concepto 3A)
            for pz_v in piezas_visto:
                caja_geo = {
                    "x": pz_v["x"], "y": pz_v["y"], "z": pz_v["z"],
                    "w": pz_v["w"], "h": pz_v["h"], "d": pz_v["d"],
                }
                dims_pz = [pz_v["w"], pz_v["h"], pz_v["d"]]
                menor = min(dims_pz)
                if menor == pz_v["d"]:
                    orientacion = "horizontal"
                    largo = pz_v["w"]
                    ancho = pz_v["h"]
                elif menor == pz_v["w"]:
                    orientacion = "vertical"
                    largo = pz_v["d"]
                    ancho = pz_v["h"]
                else:
                    orientacion = "vertical"
                    largo = pz_v["h"]
                    ancho = pz_v["d"]
                paneles_data.append(_panel_entry(
                    f"{fp.Label}__{pz_v['cara']}__visto", ROL_VISTO,
                    largo, ancho, pz_v["espesor"],
                    orientacion, caja_geo=caja_geo))

            # === POSICION LOCAL DE CADA PANEL DENTRO DEL MODULO ===
            # execute() ya calculo donde va cada caja para el compound; sin
            # volcarlo a paneles_data los PanelFeature hijos nacen todos en el
            # origen y el modulo no se ensambla (contradice el axioma
            # p_global = p_local + LocalPlacement.base de los ADR).
            # "rot_z" existe porque PanelFeature construye el fondo con el
            # espesor sobre X, mientras aqui la caja lo lleva sobre Y.
            posiciones = {
                "lateral_izquierdo": {"pos": [0.0, 0.0, lat_pos_z]},
                "lateral_derecho": {"pos": [ancho - espesor, 0.0, lat_pos_z]},
                "base": {"pos": [base_pos_x, 0.0, base_pos_z]},
                "techo": {"pos": [techo_pos_x, 0.0, techo_pos_z]},
            }
            if tiene_fondo:
                posiciones["fondo"] = {"pos": [f_x + f_len, f_y, f_z],
                                       "rot_z": 90.0}

            for pz in paneles_data:
                ubic = posiciones.get(pz.get("rol"))
                if ubic:
                    pz["pos"] = ubic["pos"]
                    if "rot_z" in ubic:
                        pz["rot_z"] = ubic["rot_z"]


            for pz in paneles_data:
                info = shell_info.get(pz.get("rol"))
                if info and info.get("reengrose"):
                    pz["reengrose"] = info["reengrose"]
                    pz["caja"] = info["caja"]
                    pz["tiras_cortes"] = info.get("tiras_cortes") or {}
                    pz["ejes"] = info["ejes"]
                    pz["clave_reengrose"] = pz.get("rol", "")

            paneles_data = VDO_FINISH.aplicar_cantos(
                paneles_data, lados_vistos, lados_apoyados,
                tapa=tapa, base=base)

            paneles_expandidos = []
            for pz in paneles_data:
                paneles_expandidos.extend(_expandir_reengrose(pz))
            paneles_data = paneles_expandidos

            # Pose de todo lo que no es carcasa: divisiones, repisas y las
            # subpiezas que salen de expandir un reengrose. Su posicion no
            # esta en `posiciones` (que solo cubre los 5 roles de carcasa)
            # sino en la caja geometrica que arrastra cada pieza.
            #
            # TIENE QUE IR DESPUES de _expandir_reengrose: la expansion
            # sustituye la pieza original por sus subpiezas y descartaba la
            # pose ya calculada. Sin esto, cada division con reengrose y
            # cada tira nacian en el origen, apiladas unas sobre otras
            # (solapes de millones de mm3 en el arbol del COCO).
            for pz in paneles_data:
                if pz.get("pos") is not None:
                    continue
                caja = pz.get("caja_geometrica")
                if not caja:
                    continue
                pz.update(VDO_FR.pose_panel_desde_dict(caja))

            fp.VDO_Paneles_JSON = json.dumps(paneles_data, ensure_ascii=False)

            # Contenedor lógico: Shape vacío para evitar duplicación geométrica.
            # Cada panel tiene su propio B-Rep independiente (para CNC/nesting).
            fp.Shape = Part.Shape()

            # La pose de los hijos NO se propaga aquí: ver onChanged().
            # El COCO depende de sus hijos (Hijos es LinkListChild), asi que
            # su execute() corre DESPUES del de ellos; escribirles el
            # Placement aqui los dejaba "still touched after recompute" en
            # cada ciclo, sin converger nunca.

        except Exception as e:
            App.Console.PrintError(f"[VDO] Error en execute(): {e}\n")
            import traceback
            App.Console.PrintError(traceback.format_exc())
            # Re-lanzar para que FreeCAD marque el objeto en error en vez de
            # dejarlo con la Shape anterior y aparentando estar bien.
            raise

    PROPS_GEOM_COCO = frozenset({"Alto", "Ancho", "FondoModulo", "Espesor", "Tapa", "Base"})

    def onChanged(self, fp, prop):
        """Propaga la pose y las cotas del COCO a sus hijos (fuera de execute()).

        R-03/R-04: nunca mutar dentro del ciclo de recompute. Mover o rotar
        el COCO reposiciona a los hijos al instante; editar Alto/Ancho/
        Espesor/Tapa/Base re-dimensiona los PanelFeature hijos sin abrir
        TaskPanel y sin disparar "still touched after recompute".
        """
        if prop != "Placement" and prop not in self.PROPS_GEOM_COCO:
            return
        if getattr(fp, "_bloqueo_sync", False):
            return
        try:
            self._bloqueo_sync = True
            if prop == "Placement":
                self._propagar_placement(fp)
            elif prop in self.PROPS_GEOM_COCO:
                self._propagar_dimensiones_hijos(fp)
        finally:
            self._bloqueo_sync = False

    def _propagar_dimensiones_hijos(self, fp):
        """Empuja las cotas teoricas del COCO a los PanelFeature hijos existentes.

        Solo actualiza numericos en objetos ya creados: no crea ni destruye.
        Tolerancia 1e-4 para no disparar eventos fantasmas.
        """
        nuevas_piezas = VDO_FR._calcular_cotas_teoricas(fp)
        for hijo in list(getattr(fp, "Hijos", None) or []):
            if hijo is None:
                continue
            rol = getattr(hijo, "VDO_Rol", None)
            if not rol or rol not in nuevas_piezas:
                continue
            nl, na, ne, npos, nrot = nuevas_piezas[rol]
            try:
                if abs(float(getattr(hijo, "Largo", 0) or 0) - nl) > 1e-4:
                    hijo.Largo = nl
                if abs(float(getattr(hijo, "Ancho", 0) or 0) - na) > 1e-4:
                    hijo.Ancho = na
                if abs(float(getattr(hijo, "Espesor", 0) or 0) - ne) > 1e-4:
                    hijo.Espesor = ne
                if npos:
                    local_actual = getattr(hijo, "LocalPlacement", None)
                    base = local_actual.Base if local_actual is not None else None
                    if base is None or (App.Vector(*npos) - base).Length > 1e-4:
                        hijo.LocalPlacement = App.Placement(
                            App.Vector(*npos),
                            App.Rotation(App.Vector(0, 0, 1), nrot))
                        hijo.Placement = fp.Placement.multiply(hijo.LocalPlacement)
            except Exception as exc:
                App.Console.PrintWarning(
                    f"[VDO] No se pudo sincronizar dimensiones del hijo "
                    f"{getattr(hijo, 'Name', '?')}: {exc}\n")

    def _propagar_placement(self, fp):
        """hijo.Placement = fp.Placement * hijo.LocalPlacement."""
        try:
            base = fp.Placement
        except Exception:
            return
        for hijo in list(getattr(fp, "Hijos", None) or []):
            if hijo is None:
                continue
            local = getattr(hijo, "LocalPlacement", None)
            if local is None:
                continue
            try:
                hijo.Placement = base.multiply(local)
            except Exception as exc:
                App.Console.PrintWarning(
                    f"[VDO] No se pudo reposicionar "
                    f"{getattr(hijo, 'Name', '?')}: {exc}\n")

    def onDelete(self, obj, subelements):
        """Eliminación en cascada: borra todos los paneles hijos cuando se elimina el COCO.

        Previene objetos huérfanos en el documento al eliminar un COCO padre.
        """
        try:
            hijos = list(obj.Hijos or [])
            doc = obj.Document
            for hijo in hijos:
                if hijo is not None and doc.getObject(hijo.Name):
                    doc.removeObject(hijo.Name)
        except Exception:
            pass
        return True

    @staticmethod
    def _es_rol_omitido(fp, rol):
        return rol in (fp.Piezas_Omitidas or [])

    def sincronizar_paneles_hijos(self, fp, doc=None):
        """Crea, actualiza y retira los PanelFeature hijos del COCO.

        Cada panel es un Part::FeaturePython independiente con su propio
        B-Rep, agregado a fp.Hijos (LinkListChild) para jerarquía en capa
        de datos. No hay grupos intermedios (Axioma T2).

        SE LLAMA SIEMPRE FUERA DE execute() (Axioma R-04: no mutar
        topología dentro del ciclo de recompute): desde make_coco() al
        crear y desde CocoUnifiedTaskPanel.accept() al editar. Antes solo
        se llamaba al crear, asi que cambiar Alto/Ancho/Espesor actualizaba
        VDO_Paneles_JSON pero dejaba los paneles del arbol con las medidas
        originales, y activar el fondo despues no creaba nada.
        """
        doc = doc or fp.Document
        try:
            paneles_data = json.loads(fp.VDO_Paneles_JSON or "[]")
        except (TypeError, ValueError):
            paneles_data = []

        vigentes = set()
        for pz in paneles_data:
            panel = self._crear_actualizar_panel(doc, pz, None, fp)
            if panel is not None:
                vigentes.add(panel.Name)

        self._retirar_paneles_obsoletos(fp, doc, vigentes)

    # Nombre anterior, conservado para no romper llamadas externas.
    _crear_paneles_hijos = sincronizar_paneles_hijos

    def _retirar_paneles_obsoletos(self, fp, doc, vigentes):
        """Borra los paneles de carcasa que ya no aparecen en el despiece.

        Ejemplo: desactivar TieneFondo debe hacer desaparecer el fondo del
        arbol, no dejarlo huerfano colgando del COCO. Solo se tocan los
        paneles de carcasa (los que tienen VDO_Rol); puertas, cajones y
        piezas desvinculadas a mano se respetan.
        """
        conservados = []
        for hijo in list(getattr(fp, "Hijos", None) or []):
            if hijo is None:
                continue
            if hijo.Name in vigentes:
                conservados.append(hijo)
                continue
            rol = getattr(hijo, "VDO_Rol", None)
            if not rol:
                # No es un panel de carcasa: no es asunto de esta funcion.
                conservados.append(hijo)
                continue
            try:
                # Evitar que PanelFeature.onDelete lo marque como omitido:
                # no lo quita el usuario, lo quita el despiece.
                hijo.ParentCOCO = None
                doc.removeObject(hijo.Name)
                App.Console.PrintLog(
                    f"[VDO] Panel '{rol}' retirado (ya no esta en el "
                    f"despiece de {fp.Name}).\n")
            except Exception as exc:
                App.Console.PrintWarning(
                    f"[VDO] No se pudo retirar {hijo.Name}: {exc}\n")
                conservados.append(hijo)
        fp.Hijos = conservados

    def _crear_actualizar_panel(self, doc, panel_data, grupo, fp):
        """Crea o actualiza un PanelFeature para un panel de carcasa.

        Seca las dimensiones (sin expresiones) para que cada panel sea
        independiente en el árbol. Asigna ParentCOCO = fp.
        """
        rol = panel_data.get("rol", "")
        nombre = panel_data.get("nombre", rol)

        if self._es_rol_omitido(fp, rol):
            return None

        panel = doc.getObject(nombre)
        es_nuevo = panel is None
        if es_nuevo:
            panel = doc.addObject("Part::FeaturePython", nombre)
            from VDO.cad.objects.vdo_cad_panel import PanelFeature, ViewProviderPanel
            PanelFeature(panel)
            if App.GuiUp:
                ViewProviderPanel(panel.ViewObject)

        # Dimensiones como valores fijos (sin expresiones del COCO)
        # Mapeo según orientación (PanelFeature.execute() respeta VDO_Orientacion):
        #   vertical:   Largo=alto del panel,  Ancho=fondo del panel
        #   horizontal: Largo=ancho del panel, Ancho=fondo del panel
        orientacion = panel_data.get("orientacion", "vertical")
        largo_val = float(panel_data.get("largo", 0))
        ancho_val = float(panel_data.get("ancho", 0))
        if "panel_largo" in panel_data:
            # Cotas ya resueltas en el marco de PanelFeature por
            # vdo_math_frames.pose_panel_desde_*: unica fuente de verdad
            # cuando existe, porque va emparejada con pos/rot_z.
            panel.Largo = float(panel_data["panel_largo"])
            panel.Ancho = float(panel_data["panel_ancho"])
            panel.Espesor = float(panel_data["panel_espesor"])
        elif orientacion == "vertical":
            # En paneles_data, "largo" tiene el fondo y "ancho" tiene el alto
            panel.Largo = ancho_val   # alto del panel (ej. 702)
            panel.Ancho = largo_val   # fondo del panel (ej. 580)
            panel.Espesor = float(
                panel_data.get("espesor", VDO_D.ESPESOR_DEFAULT))
        else:
            panel.Largo = largo_val   # ancho del panel
            panel.Ancho = ancho_val   # fondo del panel
            panel.Espesor = float(
                panel_data.get("espesor", VDO_D.ESPESOR_DEFAULT))
        panel.VDO_Orientacion = orientacion
        panel.VDO_Etiqueta = panel_data.get("nombre", nombre)
        panel.VDO_Material_Ref = panel_data.get(
            "material_ref", fp.VDO_Material_Ref)
        panel.VDO_Rol = rol
        mocheos_json = panel_data.get("mocheos_json", "[]")
        try:
            panel.VDO_Mocheos_JSON = mocheos_json
        except Exception:
            pass
        panel.ParentCOCO = fp

        cantos = panel_data.get("cantos", {})
        for direccion in ["Norte", "Sur", "Este", "Oeste"]:
            prop_name = f"VDO_Canto_{direccion}"
            valor = cantos.get(direccion.lower(), "FX")
            try:
                setattr(panel, prop_name, valor)
            except Exception:
                pass

        # Posicion dentro del modulo. LocalPlacement es la pose relativa
        # (capa de datos, la que persiste); Placement es su composicion con
        # la del COCO y la recalcula execute() en cada recompute.
        pos = panel_data.get("pos")
        if pos:
            local = App.Placement(
                App.Vector(*pos),
                App.Rotation(App.Vector(0, 0, 1),
                             float(panel_data.get("rot_z", 0.0))))
            panel.LocalPlacement = local
            panel.Placement = fp.Placement.multiply(local)

        # Agregar a la lista de hijos del COCO (jerarquía en capa de datos)
        if es_nuevo:
            hijos_actuales = list(fp.Hijos or [])
            if panel not in hijos_actuales:
                hijos_actuales.append(panel)
                fp.Hijos = hijos_actuales

        return panel

    def dumps(self):
        return None

    def loads(self, state):
        return None


from VDO.cad.views.vdo_cad_view_base import VDOViewProviderBase


class ViewProviderCoco(VDOViewProviderBase):
    """ViewProvider de respaldo para el COCO (Part::FeaturePython).

    Implementa claimChildren() para que FreeCAD dibuje los paneles hijos
    directamente bajo el COCO en el árbol nativo (sin grupos intermedios
    como Estructura_Carcasa o Cajones).
    """

    MENU_LABEL = "Propiedades del COCO"
    ICON = "vdo_coco.svg"

    def get_panel_class(self):
        from VDO.ui.vdo_ui_coco_task import CocoUnifiedTaskPanel
        return CocoUnifiedTaskPanel

    def claimChildren(self):
        """Retorna los paneles hijos directos para mostrar en el árbol nativo bajo el COCO.

        Lee de la propiedad LinkListChild Hijos (capa de datos), no de grupos
        intermedios. Funciona tanto en GUI como en el modelo de datos subyacente.
        """
        try:
            obj = self.Object
            hijos = list(obj.Hijos or [])
            return [h for h in hijos if h is not None]
        except Exception:
            return []

    def setEdit(self, vobj, mode):
        return super().setEdit(vobj, mode)

    def doubleClicked(self, vobj):
        return super().doubleClicked(vobj)


def make_coco(configuracion):
    """
    Crea un COCO como Part::FeaturePython con propiedades configurables.
    El COCO es un contenedor lógico con Shape NULA (axioma T5 / C-02):
    la geometría fabricable vive en los PanelFeature hijos, cada uno con
    su propio B-Rep, enlazados por Hijos (PropertyLinkListChild, T3) y
    sin grupos intermedios (T2). Los hijos se materializan aquí, fuera
    de execute() (R-04), y se resincronizan al editar.

    Args:
        configuracion (dict): Parámetros del cofre.

    Returns:
        App.DocumentObject: El objeto Part::FeaturePython creado.
    """
    doc = vdo_shared_guardian.vdo_guard()
    if not doc:
        App.Console.PrintError("[VDO] No hay documento activo.\n")
        return None

    nombre = configuracion.get("nombre", "COCO_4C")

    obj = doc.addObject("Part::FeaturePython", nombre)
    CocoFeature(obj)

    if App.GuiUp:
        try:
            from VDO.ui.vdo_ui_drag_handles import DragableViewProvider
            DragableViewProvider(obj.ViewObject)
        except ImportError:
            App.Console.PrintWarning(
                "[VDO] vdo_drag_handles no disponible, usando ViewProvider básico.\n")
            ViewProviderCoco(obj.ViewObject)

    # Aplicar configuración (valores por defecto desde vdo_manifest.json)
    # Tapa y Base no son simetricas: el COCO nace con tapa externa y base
    # interna, y eso lo dicen las constantes del manifiesto. El resto de
    # defaults ya los puso aplicar_esquema() en __init__.
    efectiva = {"tapa": VDO_D.TAPA_POSICION, "base": VDO_D.BASE_POSICION}
    efectiva.update(configuracion)
    aplicar_config(obj, SPEC_COCO, efectiva)

    # Los reengroses llegan como dict o como JSON ya serializado.
    reengroses = configuracion.get("reengroses", {})
    if not isinstance(reengroses, str):
        reengroses = json.dumps(reengroses or {}, ensure_ascii=False)
    obj.VDO_Reengrose_JSON = reengroses or "{}"
    rotacion = float(getattr(obj, "VDO_RotacionZ", 0.0))
    VDO_FR.guardar_exposicion(
        obj,
        configuracion.get("lados_vistos", [VDO_FR.FRENTE]),
        configuracion.get("lados_apoyados", [VDO_FR.FONDO]))
    if rotacion:
        obj.Placement = App.Placement(
            obj.Placement.Base, VDO_MOD.rotacion_z(rotacion))

    doc.recompute()
    App.Console.PrintMessage(
        f"[VDO] COCO '{nombre}' creado con FeaturePython.\n")

    # --- Crear PanelFeature hijos directos bajo el COCO (T2) ---
    # Cada entrada en VDO_Paneles_JSON se convierte en un PanelFeature
    # independiente con su propio B-Rep, agregado a fp.Hijos (LinkListChild)
    # para jerarquía en capa de datos. No hay grupos intermedios.
    try:
        proxy = getattr(obj, "Proxy", None)
        if proxy is not None and hasattr(proxy, "_crear_paneles_hijos"):
            proxy._crear_paneles_hijos(obj, doc)
    except Exception as exc:
        App.Console.PrintWarning(
            f"[VDO] Aviso al crear paneles hijos del COCO: {exc}\n")

    # Segundo recompute para que los PanelFeature hijos ejecuten su execute()
    # y generen su B-Rep independiente (se crearon después del primer recompute).
    doc.recompute()

    return obj
