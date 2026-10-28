# -*- coding: utf-8 -*-
"""Politica de acabados VDO: lados vistos -> cantos por borde.

No escribe geometria. Recibe piezas descritas por ``rol`` y devuelve el
mismo listado con un diccionario ``cantos`` por borde de tablero.
"""

import vdo_frames as FR


CANTO_VISTO = "RIG"
CANTO_OCULTO = "FX"
CANTOS_VALIDOS = ("RIG", "FX", "SMRG")

BORDES = ("norte", "sur", "este", "oeste")

ROLES = (
    "lateral_izquierdo",
    "lateral_derecho",
    "base",
    "techo",
    "fondo",
    "division_x",
    "division_y",
)


def _mapa(rol, tapa, base):
    if rol in ("lateral_izquierdo", "lateral_derecho"):
        return {
            "oeste": FR.FRENTE,
            "este": FR.FONDO,
            "sur": FR.INFERIOR if base == "interno" else None,
            "norte": FR.SUPERIOR if tapa == "interno" else None,
        }
    if rol in ("base", "techo"):
        externo = (
            (rol == "base" and base == "externo")
            or (rol == "techo" and tapa == "externo")
        )
        return {
            "oeste": FR.IZQUIERDA if externo else None,
            "este": FR.DERECHA if externo else None,
            "sur": FR.FRENTE,
            "norte": FR.FONDO,
        }
    if rol == "fondo":
        return {}
    if rol == "division_x":
        return {
            "oeste": FR.FRENTE,
            "este": FR.FONDO,
            "sur": None,
            "norte": None,
        }
    if rol == "division_y":
        return {
            "oeste": None,
            "este": None,
            "sur": FR.FRENTE,
            "norte": FR.FONDO,
        }
    return {}


def cantos_para_rol(rol, lados_vistos, tapa="externo", base="interno"):
    vistos = set(FR.interpretar_lados(lados_vistos))
    mapa = _mapa(rol, tapa, base)
    return {
        borde: (CANTO_VISTO if mapa.get(borde) in vistos else CANTO_OCULTO)
        for borde in BORDES
    }


def aplicar_cantos(piezas, lados_vistos, lados_apoyados=(),
                   tapa="externo", base="interno"):
    vistos = FR.interpretar_lados(lados_vistos)
    apoyados = [
        lado for lado in FR.interpretar_lados(lados_apoyados)
        if lado not in vistos
    ]
    resultado = []
    for original in piezas:
        pieza = dict(original)
        pieza["cantos"] = cantos_para_rol(
            pieza.get("rol", ""), vistos, tapa=tapa, base=base)
        pieza["lados_vistos"] = list(vistos)
        pieza["lados_apoyados"] = list(apoyados)
        resultado.append(pieza)
    return resultado
