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

_vdo_macro_dir = App.getUserMacroDir(True)
if _vdo_macro_dir not in sys.path:
    sys.path.insert(0, _vdo_macro_dir)

import vdo_guardian
import vdo_defaults as VDO_D
import vdo_module_props as VDO_MOD
import vdo_frames as VDO_FR
import vdo_finish as VDO_FINISH
import vdo_reengrose as VDO_RE
from vdo_reengrose_solids import forma_ref


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
    for sub in subpiezas:
        sub["rol"] = pieza.get("rol", "")
        sub["rol_padre"] = pieza.get("rol", "")
        sub["clave_reengrose"] = pieza.get("clave_reengrose", "")
        if pieza.get("mocheos") and sub.get("rol_reengrose") == "base":
            sub["mocheos"] = pieza["mocheos"]
    return subpiezas


class CocoFeature:
    """FeaturePython que genera la geometría de un cofre COCO."""

    def __init__(self, obj):
        obj.addProperty("App::PropertyLength", "Alto", "Dimensiones",
                        "Alto total del módulo (mm)").Alto = VDO_D.ALTO_DEFAULT
        obj.addProperty("App::PropertyLength", "Ancho", "Dimensiones",
                        "Ancho total del módulo (mm)").Ancho = VDO_D.ANCHO_DEFAULT
        obj.addProperty("App::PropertyLength", "FondoModulo", "Dimensiones",
                        "Profundidad total del módulo (mm)").FondoModulo = VDO_D.FONDO_DEFAULT
        obj.addProperty("App::PropertyInteger", "Espesor", "Dimensiones",
                        "Espesor del tablero (mm)").Espesor = VDO_D.ESPESOR_DEFAULT
        obj.addProperty("App::PropertyBool", "TieneFondo", "Estructura",
                        "Habilitar fondo/respaldo").TieneFondo = VDO_D.FONDO_HABILITADO
        obj.addProperty("App::PropertyInteger", "CalibreFondo", "Estructura",
                        "Espesor del fondo (mm)").CalibreFondo = VDO_D.FONDO_CALIBRE
        obj.addProperty("App::PropertyFloat", "ProfundidadRanura", "Estructura",
                        "Profundidad de ranura para fondo (mm)").ProfundidadRanura = VDO_D.FONDO_PROFUNDIDAD_RANURA
        obj.addProperty("App::PropertyFloat", "DistanciaBorde", "Estructura",
                        "Distancia del borde para fondo grueso (mm)").DistanciaBorde = VDO_D.FONDO_DISTANCIA_BORDE
        obj.addProperty("App::PropertyEnumeration", "Tapa", "Estructura",
                        "Configuración de la tapa").Tapa = ["externo", "interno"]
        obj.addProperty("App::PropertyEnumeration", "Base", "Estructura",
                        "Configuración de la base").Base = ["externo", "interno"]
        obj.addProperty("App::PropertyString", "VDO_Divisiones", "Divisiones",
                        "Matriz de vanos v2 (JSON)").VDO_Divisiones = ""
        obj.addProperty("App::PropertyString", "VDO_Reengrose_JSON", "Reengrose",
                        "Modificadores de reengrose por pieza (JSON)").VDO_Reengrose_JSON = "{}"
        obj.addProperty("App::PropertyString", "ResumenEspacios", "Divisiones",
                        "Resumen legible de espacios calculados (solo lectura)")

        # === PROPIEDADES DE EXPORTACIÓN (para cutting list) ===
        obj.addProperty("App::PropertyString", "VDO_Tipo", "VDO",
                        "Tipo de objeto").VDO_Tipo = "contenedor"
        obj.addProperty("App::PropertyString", "VDO_Subtipo", "VDO",
                        "Subtipo (COCO, módulo, etc)").VDO_Subtipo = "COCO_4C"
        obj.addProperty("App::PropertyString", "VDO_Material_Ref", "VDO",
                        "Material de los paneles").VDO_Material_Ref = "melamina_standar"

        # Paneles internos (propiedades de lectura para exportación)
        obj.addProperty("App::PropertyString", "VDO_Paneles_JSON", "VDO",
                        "Descripción JSON de los paneles internos")

        # Lista de insertos contenidos (puertas, cajones) para DAG limpio.
        obj.addProperty("App::PropertyLinkList", "Hijos", "VDO",
                        "Insertos contenidos (puertas, cajones)").Hijos = []

        # Pose común VDO (rotación + anclaje). No altera la geometría.
        VDO_MOD.add_common_props(obj)

        obj.Proxy = self

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
                    f_len = ancho_cavidad + (prof * 2)
                    f_alt = alto_cavidad + (prof * 2)
                    f_x = espesor - prof
                    f_z = espesor - prof
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

            boxes.extend([lat_izq, lat_der, panel_base, panel_techo])
            if fondo_box is not None:
                boxes.append(fondo_box)

            # --- Reengroses de carcasa ---
            reengroses = _cargar_reengroses(fp)
            obstaculos = []
            shell_tiras = []
            shell_info = {}
            shell_refs = []
            shell_cores = {
                "lateral_izquierdo": lat_izq,
                "lateral_derecho": lat_der,
                "base": panel_base,
                "techo": panel_techo,
            }
            if fondo_box is not None:
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

            from vdo_layout import cavidad_interior
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
                from vdo_coco_spaces import generar_divisiones_matriz
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

            # --- Resolucion general tira contra tira y tira contra nucleo ---
            division_tiras = list(getattr(resuelto, "tiras", []) or [])
            from vdo_coco_spaces import resolver_tiras, _shape_tira

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

            # === GUARDAR DATOS DE LOS PANELES PARA EXPORTACIÓN ===
            # Convención: largo/ancho = caras del tablero, espesor = grosor.
            import json
            lados_vistos, lados_apoyados = VDO_FR.cargar_exposicion(fp)
            paneles_data = [
                {
                    "nombre": f"{fp.Label}_Lateral_Izq",
                    "tipo": "panel",
                    "rol": "lateral_izquierdo",
                    "largo": fondo,
                    "ancho": lat_height,
                    "espesor": espesor,
                    "orientacion": "vertical",
                    "cantidad": 1,
                    "material_ref": fp.VDO_Material_Ref
                },
                {
                    "nombre": f"{fp.Label}_Lateral_Der",
                    "tipo": "panel",
                    "rol": "lateral_derecho",
                    "largo": fondo,
                    "ancho": lat_height,
                    "espesor": espesor,
                    "orientacion": "vertical",
                    "cantidad": 1,
                    "material_ref": fp.VDO_Material_Ref
                },
                {
                    "nombre": f"{fp.Label}_Base",
                    "tipo": "panel",
                    "rol": "base",
                    "largo": base_length,
                    "ancho": fondo,
                    "espesor": espesor,
                    "orientacion": "horizontal",
                    "cantidad": 1,
                    "material_ref": fp.VDO_Material_Ref
                },
                {
                    "nombre": f"{fp.Label}_Techo",
                    "tipo": "panel",
                    "rol": "techo",
                    "largo": techo_length,
                    "ancho": fondo,
                    "espesor": espesor,
                    "orientacion": "horizontal",
                    "cantidad": 1,
                    "material_ref": fp.VDO_Material_Ref
                }
            ]

            if tiene_fondo:
                paneles_data.append({
                    "nombre": f"{fp.Label}_Fondo",
                    "tipo": "panel",
                    "rol": "fondo",
                    "largo": f_len,
                    "ancho": f_alt,
                    "espesor": calibre_fondo,
                    "orientacion": "vertical",
                    "cantidad": 1,
                    "material_ref": fp.VDO_Material_Ref,
                    "fondo_delgado": fondo_es_delgado
                })

            for pz in divisiones_piezas:
                pz["nombre"] = f"{fp.Label}_{pz['nombre']}"
                pz["material_ref"] = fp.VDO_Material_Ref
                paneles_data.append(pz)

            for pz in paneles_data:
                info = shell_info.get(pz.get("rol"))
                if info and info.get("reengrose"):
                    pz["reengrose"] = info["reengrose"]
                    pz["caja"] = info["caja"]
                    pz["ejes"] = info["ejes"]
                    pz["clave_reengrose"] = pz.get("rol", "")

            paneles_data = VDO_FINISH.aplicar_cantos(
                paneles_data, lados_vistos, lados_apoyados,
                tapa=tapa, base=base)

            paneles_expandidos = []
            for pz in paneles_data:
                paneles_expandidos.extend(_expandir_reengrose(pz))
            paneles_data = paneles_expandidos

            fp.VDO_Paneles_JSON = json.dumps(paneles_data, ensure_ascii=False)

            solidos = []
            for forma in boxes:
                if forma is None or forma.isNull():
                    continue
                if forma.ShapeType == "Compound":
                    solidos.extend(
                        solido for solido in forma.Solids
                        if solido.Volume > 1e-9)
                elif forma.Volume > 1e-9:
                    solidos.append(forma)
            fp.Shape = Part.makeCompound(solidos)

            # --- Propagación de Placement a insertos (hijos) ---
            # Cuando el COCO se mueve o rota (su Placement cambia),
            # todos sus hijos se mueven rígidamente con él.
            hijos = list(fp.Hijos or [])
            for hijo in hijos:
                try:
                    if hijo is not None and hasattr(hijo, "LocalPlacement"):
                        hijo.Placement = fp.Placement.multiply(
                            hijo.LocalPlacement)
                except Exception:
                    pass

        except Exception as e:
            App.Console.PrintError(f"[VDO] Error en execute(): {e}\n")

    def dumps(self):
        return None

    def loads(self, state):
        return None


from vdo_view_base import VDOViewProviderBase


class ViewProviderCoco(VDOViewProviderBase):
    """ViewProvider de respaldo para el COCO FeaturePython."""

    MENU_LABEL = "Propiedades del COCO"
    ICON = "vdo_coco.svg"

    def get_panel_class(self):
        from vdo_coco_unified_task import CocoUnifiedTaskPanel
        return CocoUnifiedTaskPanel

    def setEdit(self, vobj, mode):
        from vdo_view_base import enfocar_inspector_universal
        enfocar_inspector_universal(getattr(vobj, "Object", None))
        return super().setEdit(vobj, mode)

    def doubleClicked(self, vobj):
        from vdo_view_base import enfocar_inspector_universal
        enfocar_inspector_universal(getattr(vobj, "Object", None))
        return super().doubleClicked(vobj)


def make_coco(configuracion):
    """
    Crea un COCO FeaturePython con propiedades configurables.

    Args:
        configuracion (dict): Parámetros del cofre.

    Returns:
        App.DocumentObject: El objeto FeaturePython creado.
    """
    doc = vdo_guardian.vdo_guard()
    if not doc:
        App.Console.PrintError("[VDO] No hay documento activo.\n")
        return None

    nombre = configuracion.get("nombre", "COCO_4C")

    obj = doc.addObject("Part::FeaturePython", nombre)
    CocoFeature(obj)

    if App.GuiUp:
        try:
            from vdo_drag_handles import DragableViewProvider
            DragableViewProvider(obj.ViewObject)
        except ImportError:
            App.Console.PrintWarning(
                "[VDO] vdo_drag_handles no disponible, usando ViewProvider básico.\n")
            ViewProviderCoco(obj.ViewObject)

    # Aplicar configuración (valores por defecto desde vdo_manifest.json)
    obj.Alto = configuracion.get("alto", VDO_D.ALTO_DEFAULT)
    obj.Ancho = configuracion.get("ancho", VDO_D.ANCHO_DEFAULT)
    obj.FondoModulo = configuracion.get("fondo_modulo", VDO_D.FONDO_DEFAULT)
    obj.Espesor = configuracion.get("espesor", VDO_D.ESPESOR_DEFAULT)
    obj.TieneFondo = configuracion.get("tiene_fondo", VDO_D.FONDO_HABILITADO)
    obj.CalibreFondo = configuracion.get("calibre_fondo", VDO_D.FONDO_CALIBRE)
    obj.ProfundidadRanura = configuracion.get("profundidad_ranura", VDO_D.FONDO_PROFUNDIDAD_RANURA)
    obj.DistanciaBorde = configuracion.get("distancia_borde", VDO_D.FONDO_DISTANCIA_BORDE)
    obj.Tapa = configuracion.get("tapa", VDO_D.TAPA_POSICION)
    obj.Base = configuracion.get("base", VDO_D.BASE_POSICION)
    obj.VDO_Divisiones = configuracion.get("divisiones", "")
    reengroses = configuracion.get("reengroses", {})
    if not isinstance(reengroses, str):
        reengroses = json.dumps(reengroses or {}, ensure_ascii=False)
    obj.VDO_Reengrose_JSON = reengroses or "{}"
    rotacion = float(configuracion.get("rotacion", 0.0))
    obj.VDO_RotacionZ = rotacion
    obj.VDO_Anclaje = configuracion.get(
        "anclaje", VDO_MOD.ANCLAJE_DEFAULT)
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
    return obj
