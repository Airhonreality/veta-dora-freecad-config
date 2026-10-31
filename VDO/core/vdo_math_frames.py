# -*- coding: utf-8 -*-
"""Marco local unico VDO y vocabulario de lados.

Contrato:
    X+ = derecha
    Y+ = fondo
    Z+ = arriba
    frente funcional = Y-

Este modulo es puro: no importa FreeCAD ni Qt.
"""

import json
import math

import VDO.hub.vdo_hub_defaults as VDO_D


FRENTE = "frente"
FONDO = "fondo"
IZQUIERDA = "izquierda"
DERECHA = "derecha"
SUPERIOR = "superior"
INFERIOR = "inferior"

LADOS = (FRENTE, FONDO, IZQUIERDA, DERECHA, SUPERIOR, INFERIOR)
LADOS_VERTICALES = (FRENTE, FONDO, IZQUIERDA, DERECHA)
LADOS_HORIZONTALES = (SUPERIOR, INFERIOR)

NORMALES = {
    FRENTE: (0.0, -1.0, 0.0),
    FONDO: (0.0, 1.0, 0.0),
    IZQUIERDA: (-1.0, 0.0, 0.0),
    DERECHA: (1.0, 0.0, 0.0),
    SUPERIOR: (0.0, 0.0, 1.0),
    INFERIOR: (0.0, 0.0, -1.0),
}

OPUESTOS = {
    FRENTE: FONDO,
    FONDO: FRENTE,
    IZQUIERDA: DERECHA,
    DERECHA: IZQUIERDA,
    SUPERIOR: INFERIOR,
    INFERIOR: SUPERIOR,
}

MARCO_LOCAL = {
    "X+": DERECHA,
    "Y+": FONDO,
    "Z+": SUPERIOR,
    "frente": FRENTE,
}

ETIQUETA_FRENTE = "FRENTE (Y\u2212)"
EJES_PREVIEW = "X\u2192  Y\u2191"


def normal(lado):
    try:
        return NORMALES[str(lado).lower()]
    except KeyError:
        raise ValueError(
            f"Lado VDO invalido: '{lado}'. Validos: {', '.join(LADOS)}.")


def opuesto(lado):
    try:
        return OPUESTOS[str(lado).lower()]
    except KeyError:
        raise ValueError(
            f"Lado VDO invalido: '{lado}'. Validos: {', '.join(LADOS)}.")


def rotar_z(vector, grados):
    """Rota un vector (x,y,z) alrededor de Z. Angulo en grados."""
    x, y, z = vector
    rad = math.radians(float(grados))
    c = math.cos(rad)
    s = math.sin(rad)
    return (x * c - y * s, x * s + y * c, z)


def normal_global(lado, rotacion_z=0.0):
    return rotar_z(normal(lado), rotacion_z)


def interpretar_lados(valor, por_defecto=None):
    """Devuelve una lista de lados desde JSON, CSV o lista."""
    if valor is None or valor == "":
        return list(por_defecto or [])

    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            return list(por_defecto or [])
        if texto.startswith("["):
            datos = json.loads(texto)
        else:
            datos = texto.split(",")
    elif isinstance(valor, (list, tuple, set)):
        datos = list(valor)
    else:
        raise ValueError(f"Exposicion VDO invalida: {valor!r}")

    resultado = []
    for item in datos:
        lado = str(item).strip().lower()
        if not lado:
            continue
        if lado not in LADOS:
            raise ValueError(
                f"Lado VDO invalido: '{item}'. Validos: {', '.join(LADOS)}.")
        if lado not in resultado:
            resultado.append(lado)
    return resultado


def serializar_lados(lados):
    return json.dumps(interpretar_lados(lados), ensure_ascii=False)


def cargar_exposicion(obj, por_defecto_vistos=(FRENTE,),
                      por_defecto_apoyados=(FONDO,)):
    vistos = interpretar_lados(
        getattr(obj, "VDO_Lados_Vistos", ""), por_defecto_vistos)
    apoyados = interpretar_lados(
        getattr(obj, "VDO_Lados_Apoyados", ""), por_defecto_apoyados)
    apoyados = [lado for lado in apoyados if lado not in vistos]
    return vistos, apoyados


def guardar_exposicion(obj, vistos, apoyados):
    vistos = interpretar_lados(vistos)
    apoyados = [
        lado for lado in interpretar_lados(apoyados) if lado not in vistos]
    obj.VDO_Lados_Vistos = serializar_lados(vistos)
    obj.VDO_Lados_Apoyados = serializar_lados(apoyados)
    return vistos, apoyados


# =====================================================================
# Traduccion caja axial -> cotas de PanelFeature
# =====================================================================
# PanelFeature construye su solido con dos unicas formas:
#     vertical   -> makeBox(espesor, ancho, largo)   espesor sobre X
#     horizontal -> makeBox(largo, ancho, espesor)   espesor sobre Z
# Ninguna cubre una pieza de pie con el espesor sobre Y (contrafrente,
# fachada, fondo del COCO). Para esas se usa vertical girada 90 grados en
# Z, que lleva X->Y; el giro deja la caja en X negativo, de ahi el
# desplazamiento +lx al colocarla.
#
# Capa 0: aritmetica pura sobre dicts, sin FreeCAD ni Part.

def pose_panel_desde_caja(x, y, z, lx, ly, lz):
    """Devuelve orientacion, cotas de panel y pose local para una caja axial.

    Args:
        x, y, z: esquina minima de la caja en el marco local del modulo.
        lx, ly, lz: extension de la caja en cada eje.

    Returns:
        dict con orientacion, panel_largo, panel_ancho, panel_espesor,
        pos (lista de 3) y rot_z (grados).
    """
    lx, ly, lz = float(lx), float(ly), float(lz)
    x, y, z = float(x), float(y), float(z)
    menor = min(lx, ly, lz)

    if menor == lz:                 # espesor sobre Z: tablero tumbado
        return {"orientacion": "horizontal", "panel_largo": lx,
                "panel_ancho": ly, "panel_espesor": lz,
                "pos": [x, y, z], "rot_z": 0.0}
    if menor == lx:                 # espesor sobre X: de pie, canto al frente
        return {"orientacion": "vertical", "panel_largo": lz,
                "panel_ancho": ly, "panel_espesor": lx,
                "pos": [x, y, z], "rot_z": 0.0}
    # espesor sobre Y: de pie con la cara al frente
    return {"orientacion": "vertical", "panel_largo": lz,
            "panel_ancho": lx, "panel_espesor": ly,
            "pos": [x + lx, y, z], "rot_z": 90.0}


def pose_panel_desde_dict(caja, claves=("w", "h", "d")):
    """Igual que pose_panel_desde_caja, leyendo un dict {x,y,z,w,h,d}."""
    kx, ky, kz = claves
    return pose_panel_desde_caja(
        caja.get("x", 0.0), caja.get("y", 0.0), caja.get("z", 0.0),
        caja.get(kx, 0.0), caja.get(ky, 0.0), caja.get(kz, 0.0))


# =====================================================================
# Cotas teoricas de carcasa (compartidas por execute() y onChanged())
# =====================================================================
# Devuelve {rol: (largo, ancho, espesor, pos, rot_z)} en el marco de
# PanelFeature: largo/ancho son los que PanelFeature espera en sus
# propiedades Largo/Ancho/Espesor para su VDO_Orientacion, y pos/rot_z son
# la LocalPlacement relativa al COCO. No construye solidos Part: solo
# aritmetica pura sobre las propiedades numericas del COCO.


def _calcular_cotas_teoricas(fp):
    """Cotas teoricas de carcasa en el marco de PanelFeature.

    Args:
        fp: Objeto COCO (FeaturePython) con las propiedades Alto, Ancho,
            FondoModulo, Espesor, Tapa, Base, TieneFondo, CalibreFondo,
            ProfundidadRanura y DistanciaBorde.

    Returns:
        dict {rol: (largo, ancho, espesor, pos, rot_z)} para los roles de
        carcasa presentes (lateral_izquierdo, lateral_derecho, base, techo
        y, si TieneFondo, fondo).
    """
    alto = float(getattr(fp, "Alto", 0) or 0)
    ancho = float(getattr(fp, "Ancho", 0) or 0)
    fondo = float(getattr(fp, "FondoModulo", 0) or 0)
    espesor = float(getattr(fp, "Espesor", 0) or 0)
    tapa = str(getattr(fp, "Tapa", "interno") or "interno")
    base = str(getattr(fp, "Base", "interno") or "interno")
    tiene_fondo = bool(getattr(fp, "TieneFondo", False))
    calibre_fondo = float(getattr(fp, "CalibreFondo", 0) or 0)
    prof_ranura = float(getattr(fp, "ProfundidadRanura", 0) or 0)
    dist_borde = float(getattr(fp, "DistanciaBorde", 0) or 0)

    # --- Laterales ---
    lat_height = alto
    lat_pos_z = 0.0
    if tapa == "externo":
        lat_height -= espesor
    if base == "externo":
        lat_height -= espesor
        lat_pos_z = espesor

    # --- Base ---
    if base == "externo":
        base_length = ancho
        base_pos_x = 0.0
    else:
        base_length = ancho - (espesor * 2)
        base_pos_x = espesor
    base_pos_z = 0.0

    # --- Techo ---
    if tapa == "externo":
        techo_length = ancho
        techo_pos_x = 0.0
    else:
        techo_length = ancho - (espesor * 2)
        techo_pos_x = espesor
    techo_pos_z = alto - espesor

    piezas = {
        "lateral_izquierdo": (
            lat_height, fondo, espesor,
            [0.0, 0.0, lat_pos_z], 0.0),
        "lateral_derecho": (
            lat_height, fondo, espesor,
            [ancho - espesor, 0.0, lat_pos_z], 0.0),
        "base": (
            base_length, fondo, espesor,
            [base_pos_x, 0.0, base_pos_z], 0.0),
        "techo": (
            techo_length, fondo, espesor,
            [techo_pos_x, 0.0, techo_pos_z], 0.0),
    }

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
        else:
            f_len = ancho_cavidad
            f_alt = alto_cavidad
            f_x = espesor
            f_z = espesor
            f_y = fondo - calibre_fondo - dist_borde
            f_y = max(espesor, min(f_y, max(0.0, fondo - calibre_fondo)))
        # Marco de PanelFeature (vertical): Largo=ancho_val(f_alt),
        # Ancho=largo_val(f_len). Consistencia con _crear_actualizar_panel.
        piezas["fondo"] = (
            f_alt, f_len, calibre_fondo,
            [f_x + f_len, f_y, f_z], 90.0)

    return piezas
