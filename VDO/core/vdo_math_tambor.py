# -*- coding: utf-8 -*-
# =====================================================================
# vdo_math_tambor.py
# Matematica pura del Tambor / Panel Entamborado y Repisa Flotante.
#
# Resuelve la estructura sandwich:
#   - Tapa superior e inferior (pieles de 4/6 mm)
#   - Bastidor perimetral en listones
#   - Costillas interiores de arriostramiento
#   - Vano posterior para anclaje con tenedor / pernos invisibles
#
# Vivia dentro de VDO/cad/objects/vdo_tambor_core.py, mezclado con el
# FeaturePython y en un archivo que ademas rompia la convencion de
# nombres vdo_cad_* de sus nueve hermanos. No importa FreeCAD: es
# calculo y nada mas.
# =====================================================================


def calcular_geometria_tambor(largo, ancho, espesor_total, espesor_tapas=6.0,
                              ancho_liston=30.0, tipo="repisa_tenedor",
                              modo_tenedor="abierto", prof_tenedor=150.0,
                              costillas=2, diam_varilla=12.0):
    """
    Cálculo matemático puro y desacoplado del entamborado.
    X: Largo de repisa | Y: Profundidad (Y+ hacia muro) | Z: Altura
    """
    largo = float(largo)
    ancho = float(ancho)
    espesor_total = float(espesor_total)
    e_tapa = float(espesor_tapas)
    w_liston = float(ancho_liston)
    prof_tenedor = float(prof_tenedor)
    costillas = int(costillas)

    h_liston = espesor_total - (2.0 * e_tapa)
    if h_liston <= 0:
        raise ValueError("El espesor total debe ser mayor que el doble de las tapas.")

    solidos_info = []
    piezas_bom = []

    # 1. Tapa Inferior (Z = 0 a e_tapa)
    solidos_info.append({
        "nombre": "Tapa_Inferior",
        "x": 0.0, "y": 0.0, "z": 0.0,
        "w": largo, "h": ancho, "d": e_tapa,
    })
    piezas_bom.append({"nombre": "Tambor_Tapa_Inf", "largo": largo, "ancho": ancho, "espesor": e_tapa})

    # 2. Tapa Superior (Z = espesor_total - e_tapa a espesor_total)
    solidos_info.append({
        "nombre": "Tapa_Superior",
        "x": 0.0, "y": 0.0, "z": espesor_total - e_tapa,
        "w": largo, "h": ancho, "d": e_tapa,
    })
    piezas_bom.append({"nombre": "Tambor_Tapa_Sup", "largo": largo, "ancho": ancho, "espesor": e_tapa})

    z_nucleo = e_tapa

    # 3. Listón Frontal (Y = 0 a w_liston en el frente Y-)
    solidos_info.append({
        "nombre": "Liston_Frente",
        "x": 0.0, "y": 0.0, "z": z_nucleo,
        "w": largo, "h": w_liston, "d": h_liston,
    })
    piezas_bom.append({"nombre": "Liston_Frente", "largo": largo, "ancho": w_liston, "espesor": h_liston})

    # 4. Listones Laterales (Izquierdo y Derecho)
    # Longitud según si el fondo está abierto o cerrado
    long_lat = ancho - w_liston if tipo == "repisa_tenedor" and modo_tenedor == "abierto" else ancho - (2.0 * w_liston)

    solidos_info.append({
        "nombre": "Liston_Lat_Izq",
        "x": 0.0, "y": w_liston, "z": z_nucleo,
        "w": w_liston, "h": long_lat, "d": h_liston,
    })
    solidos_info.append({
        "nombre": "Liston_Lat_Der",
        "x": largo - w_liston, "y": w_liston, "z": z_nucleo,
        "w": w_liston, "h": long_lat, "d": h_liston,
    })
    piezas_bom.append({"nombre": "Liston_Lateral", "largo": long_lat, "ancho": w_liston, "espesor": h_liston, "cantidad": 2})

    # 5. Cierre Trasero o Preparación de Tenedor
    y_limite_costillas = ancho
    if tipo == "panel_cerrado":
        solidos_info.append({
            "nombre": "Liston_Trasero",
            "x": 0.0, "y": ancho - w_liston, "z": z_nucleo,
            "w": largo, "h": w_liston, "d": h_liston,
        })
        piezas_bom.append({"nombre": "Liston_Trasero", "largo": largo, "ancho": w_liston, "espesor": h_liston})
        y_limite_costillas = ancho - w_liston
    elif tipo == "repisa_tenedor":
        if modo_tenedor == "taladrado":
            # Listón macizo en pared taladrado para varillas
            solidos_info.append({
                "nombre": "Liston_Trasero_Taladrado",
                "x": w_liston, "y": ancho - w_liston, "z": z_nucleo,
                "w": largo - (2.0 * w_liston), "h": w_liston, "d": h_liston,
                "taladros_tenedor": True,
            })
            y_limite_costillas = ancho - w_liston
        else:
            # Hueco abierto: las costillas frenan antes de la profundidad del tenedor
            y_limite_costillas = max(w_liston, ancho - prof_tenedor)

    # 6. Costillas Interiores (Peinazos transversales de apoyo)
    ancho_hueco_x = largo - (2.0 * w_liston)
    prof_hueco_y = y_limite_costillas - w_liston

    if costillas > 0 and ancho_hueco_x > 0 and prof_hueco_y > 0:
        paso_x = ancho_hueco_x / (costillas + 1)
        for i in range(1, costillas + 1):
            cx = w_liston + (i * paso_x) - (w_liston / 2.0)
            solidos_info.append({
                "nombre": f"Costilla_{i}",
                "x": cx, "y": w_liston, "z": z_nucleo,
                "w": w_liston, "h": prof_hueco_y, "d": h_liston,
            })
            piezas_bom.append({"nombre": f"Costilla_Refuerzo_{i}", "largo": prof_hueco_y, "ancho": w_liston, "espesor": h_liston})

    return {
        "solidos": solidos_info,
        "piezas": piezas_bom,
        "h_liston": h_liston,
        "diam_varilla": diam_varilla,
    }
