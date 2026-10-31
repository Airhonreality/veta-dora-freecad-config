# -*- coding: utf-8 -*-
# =====================================================================
# vdo_math_visto.py
# Capa 0 Pura - Visto Exterior (Panel Embellecedor) y Gola de Carpintería
#
# Parte A: El Costado "Visto"
#   Un "Visto" no es un parámetro del COCO, es un PanelFeature hijo
#   adosado (modificador perimetral del motor de reengrose).
#   Cubre un costado del COCO ocultando tornillos/cantos, con desfasos
#   opcionales hacia el piso (tapa zócalo) y hacia el frente (al ras de
#   puertas/fachadas).
#
# Parte B: La Gola de Carpintería (se implementa en vdo_math_layout.py)
#
# No importa FreeCAD ni Qt. Solo lógica, decimales y enums oficiales.
# =====================================================================

from __future__ import annotations
from typing import TypedDict, Literal

# ---------------------------------------------------------------------
# 1. CARAS VÁLIDAS PARA VISTO
# ---------------------------------------------------------------------

CaraVisto = Literal["izquierda", "derecha"]

CARA_IZQUIERDA = "izquierda"
CARA_DERECHA = "derecha"

CARAS_VISTO_VALIDAS = (CARA_IZQUIERDA, CARA_DERECHA)

# Rol de la pieza visto en el BOM / PanelFeature
ROL_VISTO = "visto"

# ---------------------------------------------------------------------
# 2. CONSTANTES DE TALLER
# ---------------------------------------------------------------------

ESPESOR_PANEL_DEFAULT = 18.0   # mm de espesor del tablero del visto
DESFASE_PISO_DEFAULT = 100.0   # mm que baja el visto para tapar el zócalo
DESFASE_FRENTE_DEFAULT = 18.0  # mm que vuela el visto al ras de puertas (18 mm tablero)

# ---------------------------------------------------------------------
# 3. TIPOS DE DATOS
# ---------------------------------------------------------------------


class VistoConfig(TypedDict, total=False):
    """Configuración de un Panel Embellecedor (Visto).

    Parámetros:
        cara: Izquierda o Derecha del COCO.
        espesor: grosor del tablero del visto (default 18 mm).
        desfase_z_piso: mm que baja hacia Z- para tapar el zócalo
            (default 100 mm; 0 = no baja al piso).
        desfase_y_frente: mm que vuela hacia Y- (frente) para quedar al
            ras de las puertas/fachadas (default 18 mm; 0 = al ras del lateral).
    """
    cara: CaraVisto
    espesor: float
    desfase_z_piso: float
    desfase_y_frente: float


class PiezaVisto(TypedDict, total=False):
    """Descriptora de la pieza Visto generada.

    Coordenadas locales del COCO (marco de vdo_math_frames):
        X+ = derecha, Y+ = fondo, Z+ = arriba, frente funcional = Y-
    x, y, z : esquina mínima de la caja en mm
    w, h, d : extensión en cada eje (w=X/ancho, h=Y/profundidad, d=Z/alto)
    """
    nombre: str
    rol: str
    cara: str
    x: float
    y: float
    z: float
    w: float
    h: float
    d: float
    espesor: float
    desfase_z_piso: float
    desfase_y_frente: float


# ---------------------------------------------------------------------
# 4. VALIDACIÓN
# ---------------------------------------------------------------------


def _validar_visto(cfg: VistoConfig) -> VistoConfig:
    """Normaliza y valida una VistoConfig rellenando defaults."""
    cara = str(cfg.get("cara", CARA_IZQUIERDA)).strip().lower()
    if cara not in CARAS_VISTO_VALIDAS:
        raise ValueError(
            f"Cara de visto invalida: {cara!r}. "
            f"Validas: {CARAS_VISTO_VALIDAS}.")
    espesor = float(cfg.get("espesor", ESPESOR_PANEL_DEFAULT))
    if espesor <= 0:
        raise ValueError(f"El espesor del visto debe ser > 0: {espesor}")
    desfase_z = float(cfg.get("desfase_z_piso", DESFASE_PISO_DEFAULT))
    if desfase_z < 0:
        raise ValueError(f"El desfase_z_piso no puede ser negativo: {desfase_z}")
    desfase_y = float(cfg.get("desfase_y_frente", DESFASE_FRENTE_DEFAULT))
    if desfase_y < 0:
        raise ValueError(f"El desfase_y_frente no puede ser negativo: {desfase_y}")
    return {
        "cara": cara,
        "espesor": espesor,
        "desfase_z_piso": desfase_z,
        "desfase_y_frente": desfase_y,
    }


def _validar_dims(dims: dict) -> dict:
    """Valida dimensiones del COCO: alto, ancho, fondo, espesor."""
    alto = float(dims["alto"])
    ancho = float(dims["ancho"])
    fondo = float(dims["fondo"])
    espesor = float(dims.get("espesor", ESPESOR_PANEL_DEFAULT))
    for nombre, valor in (("alto", alto), ("ancho", ancho),
                          ("fondo", fondo), ("espesor", espesor)):
        if valor <= 0:
            raise ValueError(f"Dimensione invalida '{nombre}': {valor}.")
    return {"alto": alto, "ancho": ancho, "fondo": fondo, "espesor": espesor}


# ---------------------------------------------------------------------
# 5. GENERADOR DE PIEZA VISTO
# ---------------------------------------------------------------------


def _pieza_visto(nombre: str, cara: str, cfg: VistoConfig,
                 x: float, y: float, z: float,
                 w: float, h: float, d: float) -> PiezaVisto:
    """Constructor de despacho de PiezaVisto."""
    return PiezaVisto(
        nombre=nombre,
        rol=ROL_VISTO,
        cara=cara,
        x=round(float(x), 6),
        y=round(float(y), 6),
        z=round(float(z), 6),
        w=round(float(w), 6),
        h=round(float(h), 6),
        d=round(float(d), 6),
        espesor=round(float(cfg["espesor"]), 6),
        desfase_z_piso=round(float(cfg["desfase_z_piso"]), 6),
        desfase_y_frente=round(float(cfg["desfase_y_frente"]), 6),
    )


def generar_pieza_visto(cara: str,
                        cfg: VistoConfig | dict,
                        dims: dict) -> PiezaVisto:
    """Genera la pieza física del Panel Embellecedor (Visto) para una cara
    del COCO.

    El visto es una placa vertical que cubre el costado lateral. Se coloca
    como overlay sobre el lateral existente, con desfasos opcionales:

        - desfase_z_piso: baja hacia Z- para tapar el zócalo
          (la pieza arranca por debajo de z=0).
        - desfase_y_frente: vuela hacia Y- (frente) para quedar al ras de
          las puertas/fachadas (la pieza arranca por delante de y=0).

    La placa siempre tiene el espesor del tablero sobre el eje X
    (placa de pie, cara al frente).

    Args:
        cara: "izquierda" o "derecha".
        cfg: VistoConfig con cara, espesor, desfase_z_piso, desfase_y_frente.
        dims: Dimensiones del COCO {alto, ancho, fondo, espesor}.

    Returns:
        PiezaVisto lista para materializar como PanelFeature hijo del COCO.

    Raises:
        ValueError: si cara, config o dimensiones son invalidas.
    """
    cara = str(cara).strip().lower()
    if cara not in CARAS_VISTO_VALIDAS:
        raise ValueError(
            f"Cara de visto invalida: {cara!r}. "
            f"Validas: {CARAS_VISTO_VALIDAS}.")
    cfg_val = _validar_visto(cfg or {})
    dims_val = _validar_dims(dims)

    esp = cfg_val["espesor"]
    dz = cfg_val["desfase_z_piso"]
    dy = cfg_val["desfase_y_frente"]
    alto = dims_val["alto"]
    ancho = dims_val["ancho"]
    fondo = dims_val["fondo"]

    if cara == CARA_IZQUIERDA:
        # Visto izquierdo: placa vertical que cubre x in [-esp, 0]
        # (superpuesto hacia afuera del lateral existente: cero colisión)
        # Desfase al frente: arranca en y = -dy (hacia Y-), crece dy en h
        # Desfase al piso: arranca en z = -dz (hacia Z-), crece dz en d
        x = -esp
        y = -dy
        z = -dz
        w = esp
        h = fondo + dy
        d = alto + dz
    else:  # CARA_DERECHA
        # Visto derecho: placa vertical que cubre x in [ancho, ancho+esp]
        x = ancho
        y = -dy
        z = -dz
        w = esp
        h = fondo + dy
        d = alto + dz

    return _pieza_visto(
        f"{cara}_visto", cara, cfg_val,
        x, y, z, w, h, d)


# ---------------------------------------------------------------------
# 6. PRESETS OFICIALES
# ---------------------------------------------------------------------

VISTO_AL_RAS: VistoConfig = {
    "cara": CARA_IZQUIERDA,
    "espesor": ESPESOR_PANEL_DEFAULT,
    "desfase_z_piso": 0.0,
    "desfase_y_frente": DESFASE_FRENTE_DEFAULT,
}

VISTO_HASTA_PISO: VistoConfig = {
    "cara": CARA_IZQUIERDA,
    "espesor": ESPESOR_PANEL_DEFAULT,
    "desfase_z_piso": DESFASE_PISO_DEFAULT,
    "desfase_y_frente": DESFASE_FRENTE_DEFAULT,
}

VISTO_SIN_DESFASES: VistoConfig = {
    "cara": CARA_IZQUIERDA,
    "espesor": ESPESOR_PANEL_DEFAULT,
    "desfase_z_piso": 0.0,
    "desfase_y_frente": 0.0,
}


__all__ = [
    # Caras
    "CARA_IZQUIERDA", "CARA_DERECHA", "CARAS_VISTO_VALIDAS",
    "CaraVisto",
    # Rol
    "ROL_VISTO",
    # Constantes
    "ESPESOR_PANEL_DEFAULT", "DESFASE_PISO_DEFAULT", "DESFASE_FRENTE_DEFAULT",
    # Tipos
    "VistoConfig", "PiezaVisto",
    # API
    "generar_pieza_visto",
    # Presets
    "VISTO_AL_RAS", "VISTO_HASTA_PISO", "VISTO_SIN_DESFASES",
]
