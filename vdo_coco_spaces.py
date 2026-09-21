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
    """Genera shapes de divisiones verticales (eje X) como lista de boxes.

    Args:
        espacios_x_json: JSON string con la definición de espacios en X.
        ancho_util: Ancho interior disponible (entre laterales) en mm.
        fondo: Profundidad del módulo en mm.
        espesor: Espesor del tablero en mm.
        z_base: Posición Z donde inicia el espacio util.
        altura_disponible: Altura disponible para las divisiones.

    Returns:
        (list, str): (lista de TopoShape boxes, texto resumen)
    """
    nodes = deserializar_espacios(espacios_x_json)
    if not nodes:
        return [], ""

    resueltos = resolver_espacios_eje(nodes, ancho_util, espesor)
    resumen = generar_texto_resumen(resueltos, "X")

    shapes = []
    _generar_shapes_recursivo(
        resueltos, shapes, fondo, espesor, z_base, altura_disponible, "X")

    return shapes, resumen


def generar_divisiones_y(espacios_y_json, ancho_util, fondo, espesor,
                         z_base, altura_disponible):
    """Genera shapes de divisiones horizontales (eje Y / repisas) como lista de boxes.

    Args:
        espacios_y_json: JSON string con la definición de espacios en Y.
        ancho_util: Ancho interior disponible (entre laterales) en mm.
        fondo: Profundidad del módulo en mm.
        espesor: Espesor del tablero en mm.
        z_base: Posición Z donde inicia el espacio util.
        altura_disponible: Altura disponible para las divisiones.

    Returns:
        (list, str): (lista de TopoShape boxes, texto resumen)
    """
    nodes = deserializar_espacios(espacios_y_json)
    if not nodes:
        return [], ""

    resueltos = resolver_espacios_eje(nodes, altura_disponible, espesor)
    resumen = generar_texto_resumen(resueltos, "Y/Z")

    shapes = []
    _generar_shapes_recursivo(
        resueltos, shapes, fondo, espesor, z_base, altura_disponible, "Y")

    return shapes, resumen


def _generar_shapes_recursivo(espacios, shapes, fondo, espesor,
                              z_base, altura_disponible, eje):
    """Genera shapes de divisiones de forma recursiva para espacios anidados.

    Args:
        espacios: Lista de espacios resueltos (output de resolver_espacios_eje).
        shapes: Lista acumuladora de shapes (mutated in-place).
        fondo: Profundidad del módulo.
        espesor: Espesor del tablero.
        z_base: Z base del espacio util.
        altura_disponible: Altura disponible.
        eje: "X" para divisiones verticales, "Y" para horizontales.
    """
    for esp in espacios:
        if eje == "X":
            _crear_division_vertical(esp, shapes, fondo, espesor,
                                     z_base, altura_disponible)
        else:
            _crear_division_horizontal(esp, shapes, fondo, espesor,
                                       z_base, altura_disponible)

        if esp.get("children"):
            _generar_shapes_recursivo(
                esp["children"], shapes, fondo, espesor,
                z_base + esp["inicio"], esp["libre"],
                "Y" if eje == "X" else "X")


def _crear_division_vertical(esp, shapes, fondo, espesor,
                             z_base, altura_disponible):
    """Crea un panel divisor vertical (paralelo al eje Y-Z)."""
    x_pos = esp["inicio"]
    libre = esp["libre"]

    if libre <= 0:
        return

    box = Part.makeBox(
        espesor, fondo, altura_disponible,
        App.Vector(x_pos, 0, z_base))
    shapes.append(box)


def _crear_division_horizontal(esp, shapes, fondo, espesor,
                               z_base, altura_disponible):
    """Crea un panel divisor horizontal (repisa, paralelo al eje X-Y)."""
    x_pos = esp["inicio"]
    libre = esp["libre"]

    if libre <= 0:
        return

    box = Part.makeBox(
        altura_disponible, fondo, espesor,
        App.Vector(0, 0, x_pos + z_base))
    shapes.append(box)
