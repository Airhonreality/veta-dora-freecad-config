# -*- coding: utf-8 -*-
# =====================================================================
# vdo_coco_spaces.py
# Motor de geometría para divisiones internas del COCO
# Convierte la resolución de espacios en shapes de FreeCAD
# Axioma 2: Lógica geométrica pura, sin dependencias de UI
# =====================================================================

import FreeCAD as App
import Part

from vdo_spaces import (
    deserializar_espacios, resolver_espacios_eje,
    generar_texto_resumen, ESPACIO_RESTANTE
)


def generar_divisiones_x(espacios_x_json, ancho_util, fondo, espesor,
                         z_base, altura_disponible):
    """Genera shapes y piezas VDO de divisiones verticales (eje X).

    Args:
        espacios_x_json: JSON string con la definición de espacios en X.
        ancho_util: Ancho interior disponible (entre laterales) en mm.
        fondo: Profundidad del módulo en mm.
        espesor: Espesor del tablero en mm.
        z_base: Posición Z donde inicia el espacio util.
        altura_disponible: Altura disponible para las divisiones.

    Returns:
        (list, str, list): (shapes, texto resumen, piezas VDO)
    """
    nodes = deserializar_espacios(espacios_x_json)
    if not nodes:
        return [], "", []

    resueltos = resolver_espacios_eje(nodes, ancho_util, espesor)
    resumen = generar_texto_resumen(resueltos, "X")

    shapes, piezas = [], []
    _generar_shapes_recursivo(
        resueltos, shapes, piezas, fondo, espesor,
        z_base, ancho_util, altura_disponible, "X", [1])

    return shapes, resumen, piezas


def generar_divisiones_y(espacios_y_json, ancho_util, fondo, espesor,
                         z_base, altura_disponible):
    """Genera shapes y piezas VDO de divisiones horizontales (eje Y / repisas).

    Returns:
        (list, str, list): (shapes, texto resumen, piezas VDO)
    """
    nodes = deserializar_espacios(espacios_y_json)
    if not nodes:
        return [], "", []

    resueltos = resolver_espacios_eje(nodes, altura_disponible, espesor)
    resumen = generar_texto_resumen(resueltos, "Y/Z")

    shapes, piezas = [], []
    _generar_shapes_recursivo(
        resueltos, shapes, piezas, fondo, espesor,
        z_base, ancho_util, altura_disponible, "Y", [1])

    return shapes, resumen, piezas


def _generar_shapes_recursivo(espacios, shapes, piezas, fondo, espesor,
                              z_base, ancho_repisa, altura_divisor, eje,
                              contador):
    """Genera divisiones de forma recursiva.

    ancho_repisa:   ancho (X) de la región actual (ancho de repisas horizontales).
    altura_divisor: alto (Z) de la región actual (alto de divisiones verticales).
    """
    for esp in espacios:
        if eje == "X":
            pieza = _crear_division_vertical(
                esp, shapes, fondo, espesor, z_base, altura_divisor,
                contador[0])
        else:
            pieza = _crear_division_horizontal(
                esp, shapes, fondo, espesor, z_base, ancho_repisa,
                contador[0])

        if pieza is not None:
            piezas.append(pieza)
            contador[0] += 1

        if esp.get("children"):
            if eje == "X":
                # columna de ancho libre -> subdividir en altura (repisas)
                _generar_shapes_recursivo(
                    esp["children"], shapes, piezas, fondo, espesor,
                    z_base, esp["libre"], altura_divisor, "Y", contador)
            else:
                # banda de alto libre -> subdividir en ancho (verticales)
                _generar_shapes_recursivo(
                    esp["children"], shapes, piezas, fondo, espesor,
                    z_base + esp["inicio"], ancho_repisa, esp["libre"],
                    "X", contador)


def _crear_division_vertical(esp, shapes, fondo, espesor,
                             z_base, altura_divisor, idx):
    """Crea un panel divisor vertical (paralelo al eje Y-Z)."""
    x_pos = esp["inicio"]
    libre = esp["libre"]

    if libre <= 0:
        return None

    box = Part.makeBox(
        espesor, fondo, altura_divisor,
        App.Vector(x_pos, 0, z_base))
    shapes.append(box)

    return {
        "nombre": f"Division_X_{idx}",
        "tipo": "panel",
        "largo": fondo,
        "ancho": altura_divisor,
        "espesor": espesor,
        "orientacion": "vertical",
        "cantidad": 1,
    }


def _crear_division_horizontal(esp, shapes, fondo, espesor,
                               z_base, ancho_repisa, idx):
    """Crea un panel divisor horizontal (repisa, paralelo al eje X-Y)."""
    z_pos = z_base + esp["inicio"]
    libre = esp["libre"]

    if libre <= 0:
        return None

    box = Part.makeBox(
        ancho_repisa, fondo, espesor,
        App.Vector(0, 0, z_pos))
    shapes.append(box)

    return {
        "nombre": f"Division_Y_{idx}",
        "tipo": "panel",
        "largo": ancho_repisa,
        "ancho": fondo,
        "espesor": espesor,
        "orientacion": "horizontal",
        "cantidad": 1,
    }
