# -*- coding: utf-8 -*-
# =====================================================================
# vdo_math_zocalo.py
# Matematica pura del zocalo parametrico VDO.
#
# El zocalo NO es un reengrose: es una entidad fisica independiente que
# reutiliza la primitiva perimetral 2D (distancia_al_canto / largo_tira)
# y la extruye verticalmente en Z.
#
# Vivia dentro de VDO/cad/objects/vdo_cad_zocalo.py, mezclado con el
# FeaturePython. Eso rompia la simetria de capas: coco, cajon y puerta si
# separan su motor en VDO/core/vdo_math_*, y el TaskPanel del zocalo
# acababa importando matematica desde la capa CAD para validar. Aqui no
# se importa ni FreeCAD ni Part: es calculo y nada mas.
# =====================================================================

import VDO.core.vdo_math_reengrose as VDO_RE
from VDO.core.vdo_math_layout import Layout, Track, AXIS_X, resolve_layout


class ZocaloError(ValueError):
    """Error de validación del zócalo."""


NOMBRES_BORDE = {
    "frente": "Zocalo_Frente",
    "izquierda": "Zocalo_Lat_Izq",
    "derecha": "Zocalo_Lat_Der",
    "fondo": "Zocalo_Trasero",
}
ROLES_BORDE = {
    "frente": "frente",
    "izquierda": "lateral_izquierdo",
    "derecha": "lateral_derecho",
    "fondo": "trasero",
}
CANTOS_BORDE = {
    "frente": {"norte": "RIG", "sur": "RIG", "este": "RIG", "oeste": "RIG"},
    "izquierda": {"norte": "RIG", "sur": "RIG", "este": "FX", "oeste": "RIG"},
    "derecha": {"norte": "RIG", "sur": "RIG", "este": "RIG", "oeste": "FX"},
    "fondo": {"norte": "FX", "sur": "FX", "este": "FX", "oeste": "FX"},
    "amarre": {"norte": "FX", "sur": "FX", "este": "FX", "oeste": "FX"},
}


def _float_positivo(valor, nombre):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ZocaloError(f"Valor inválido para '{nombre}': {valor!r}.")
    if numero <= 0:
        raise ZocaloError(f"'{nombre}' debe ser mayor que 0.")
    return numero


def _float_no_negativo(valor, nombre):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ZocaloError(f"Valor inválido para '{nombre}': {valor!r}.")
    if numero < 0:
        raise ZocaloError(f"'{nombre}' no puede ser negativo.")
    return numero


def calcular_geometria_zocalo(ancho, fondo, alto_zocalo, espesor_tablero,
                              distancia_frente=50.0,
                              distancia_costados=0.0,
                              distancia_trasera=20.0,
                              tiene_trasera=True,
                              amarres_intermedios=0,
                              material_ref="melamina_standar"):
    """Calcula tiras, amarres y despiece del zócalo (sin FreeCAD).

    Coordenadas del tablero: X = ancho del mueble, Y = fondo del mueble.
    Las tiras se extruyen después de Z=0 a Z=AltoZocalo.
    """
    ancho = _float_positivo(ancho, "ancho")
    fondo = _float_positivo(fondo, "fondo")
    alto_zocalo = _float_positivo(alto_zocalo, "alto_zocalo")
    espesor = _float_positivo(espesor_tablero, "espesor_tablero")
    dist_frente = _float_no_negativo(distancia_frente, "distancia_frente")
    dist_costados = _float_no_negativo(
        distancia_costados, "distancia_costados")
    dist_trasera = _float_no_negativo(
        distancia_trasera, "distancia_trasera")
    tiene_trasera = bool(tiene_trasera)
    try:
        amarres = int(amarres_intermedios)
    except (TypeError, ValueError):
        raise ZocaloError(
            f"Valor inválido para 'amarres_intermedios': "
            f"{amarres_intermedios!r}.")
    if amarres < 0:
        raise ZocaloError("'amarres_intermedios' no puede ser negativo.")

    if dist_frente + espesor > fondo + 1e-9:
        raise ZocaloError(
            "La distancia frontal deja el zócalo fuera del fondo del mueble.")
    if dist_costados + espesor > ancho / 2.0 + 1e-9:
        raise ZocaloError(
            "La distancia a los costados deja el zócalo sin luz interior.")
    if tiene_trasera:
        if dist_trasera + espesor > fondo + 1e-9:
            raise ZocaloError(
                "La distancia trasera deja el zócalo fuera del fondo.")
        if dist_frente + 2.0 * espesor >= fondo - dist_trasera - 1e-9:
            raise ZocaloError(
                "Las tiras frontal y trasera se solapan en el fondo.")

    bordes = {
        "frente": {
            "activo": True,
            "ancho": espesor,
            "distancia_al_canto": dist_frente,
            "largo_tira": "punta_a_punta",
            "espesor": espesor,
        },
        "izquierda": {
            "activo": True,
            "ancho": espesor,
            "distancia_al_canto": dist_costados,
            "largo_tira": "marco_interior",
            "espesor": espesor,
        },
        "derecha": {
            "activo": True,
            "ancho": espesor,
            "distancia_al_canto": dist_costados,
            "largo_tira": "marco_interior",
            "espesor": espesor,
        },
        "fondo": {
            "activo": tiene_trasera,
            "ancho": espesor,
            "distancia_al_canto": dist_trasera,
            "largo_tira": "marco_interior",
            "espesor": espesor,
        },
    }

    tiras = VDO_RE.generar_tiras_perimetrales(
        ancho, fondo, bordes, espesor, "vertical_domina")
    por_borde = {tira["borde"]: tira for tira in tiras}
    for borde in ("frente", "izquierda", "derecha"):
        if borde not in por_borde:
            raise ZocaloError(
                f"No se pudo generar la tira obligatoria '{borde}'.")

    frente = por_borde["frente"]
    izquierda = por_borde["izquierda"]
    derecha = por_borde["derecha"]
    trasera = por_borde.get("fondo")

    rib_y0 = frente["y"] + frente["h"]
    rib_y1 = trasera["y"] if trasera else fondo
    if rib_y1 <= rib_y0 + 1e-9:
        raise ZocaloError(
            "No hay profundidad útil entre la tira frontal y la trasera.")

    interior_izq = izquierda["x"] + izquierda["w"]
    interior_der = derecha["x"]
    luz = interior_der - interior_izq
    if luz <= 0:
        raise ZocaloError("No hay luz interior entre los laterales.")

    amarres = []
    if amarres_intermedios:
        hueco_w = max(0.0, interior_der - interior_izq)
        hueco_h = max(0.0, rib_y1 - rib_y0)
        if hueco_w <= 0 or hueco_h <= 0:
            raise ZocaloError(
                "No hay hueco interior para los amarres intermedios.")
        columnas = [Track(f"col_{i + 1}") for i in range(amarres_intermedios + 1)]
        filas = [Track("fila_1")]
        layout_zocalo = Layout(columns=columnas, rows=filas)
        resuelto = resolve_layout(
            layout_zocalo, hueco_w, hueco_h, espesor, reengroses=None)
        for indice, pieza in enumerate(
                [p for p in resuelto.pieces
                 if getattr(p, "axis", None) == AXIS_X
                 and str(getattr(p, "path", "")).startswith("x")],
                start=1):
            x0 = interior_izq + float(pieza.x)
            amarres.append({
                "nombre": f"Zocalo_Amarre_{indice:02d}",
                "rol": "amarre",
                "borde": "amarre",
                "x": float(x0),
                "y": float(rib_y0),
                "w": float(pieza.w),
                "h": float(hueco_h),
                "d": float(espesor),
                "espesor": float(espesor),
            })

    piezas = []
    for tira in tiras:
        borde = tira["borde"]
        piezas.append({
            "nombre": NOMBRES_BORDE[borde],
            "tipo": "panel",
            "rol": ROLES_BORDE[borde],
            "borde": borde,
            "orientacion": "vertical",
            "largo": float(tira["largo"]),
            "ancho": float(alto_zocalo),
            "espesor": float(espesor),
            "cantidad": 1,
            "material_ref": material_ref,
            "cantos": dict(CANTOS_BORDE[borde]),
            "grupo": "",
            "operacion": "Cantear por separado",
            "largo_tira": tira["largo_tira"],
            "distancia_al_canto": tira["distancia_al_canto"],
        })

    for amarre in amarres:
        piezas.append({
            "nombre": amarre["nombre"],
            "tipo": "panel",
            "rol": "amarre",
            "borde": "amarre",
            "orientacion": "vertical",
            "largo": float(max(amarre["w"], amarre["h"])),
            "ancho": float(alto_zocalo),
            "espesor": float(espesor),
            "cantidad": 1,
            "material_ref": material_ref,
            "cantos": dict(CANTOS_BORDE["amarre"]),
            "grupo": "",
            "operacion": "Cantear por separado",
            "largo_tira": "punta_a_punta",
            "distancia_al_canto": 0.0,
        })

    lineas = [
        f"Zócalo: {ancho:.0f} × {fondo:.0f} × {alto_zocalo:.0f} mm "
        f"(e={espesor:.0f}, trasera={'sí' if tiene_trasera else 'no'})"
    ]
    for pieza in piezas:
        lineas.append(
            f"{pieza['nombre']}: {pieza['largo']:.1f} × "
            f"{pieza['ancho']:.1f} × {pieza['espesor']:.0f} mm "
            f"({pieza['largo_tira']}, "
            f"canto={pieza['distancia_al_canto']:.1f})")

    return {
        "tiras": tiras,
        "amarres": amarres,
        "piezas": piezas,
        "resumen": "\n".join(lineas),
        "bordes": bordes,
    }
