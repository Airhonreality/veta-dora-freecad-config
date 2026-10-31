# -*- coding: utf-8 -*-
# =====================================================================
# vdo_math_caras.py
# Capa 0 Pura - Estado Constructivo de Caras del COCO
#
# Un mueble no siempre es una caja de 4 paredes solidas. Cada cara del
# modulo (Techo, Base, Lateral Izq, Lateral Der, Fondo) adopta uno de
# estos 4 Estados Constructivos:
#
#   Modo_Cara = [ SOLIDO, AMARRES, MARCO_RINCON, NULO ]
#
# No importa FreeCAD ni Qt. Solo logica, decimales y enums oficiales.
# Fuente unica de verdad para el motor de reengrose/mocheo y el despiece.
# =====================================================================

from __future__ import annotations
from typing import TypedDict, Literal

# ---------------------------------------------------------------------
# 1. ESTADOS CONSTRUCTIVOS DE CARA
# ---------------------------------------------------------------------

ModoCara = Literal["SOLIDO", "AMARRES", "MARCO_RINCON", "NULO"]

MODO_SOLIDO = "SOLIDO"        # Tablero completo de 18 mm (default actual)
MODO_AMARRES = "AMARRES"      # Tapas sustituidas por tiras de 70 mm
MODO_MARCO_RINCON = "MARCO_RINCON"  # Lateral suprimido -> travesaños + poste ciego
MODO_NULO = "NULO"            # La cara no existe (sin trasera, campana, etc.)

MODOS_CARA_VALIDOS = (
    MODO_SOLIDO,
    MODO_AMARRES,
    MODO_MARCO_RINCON,
    MODO_NULO,
)

# ---------------------------------------------------------------------
# 2. CARAS Y ROLES DE PIEZA
# ---------------------------------------------------------------------

CARAS_COCO = ("techo", "base", "izquierda", "derecha", "fondo")

# Roles de pieza generados por cada modo
ROL_TECHO = "techo"
ROL_BASE = "base"
ROL_LATERAL_IZQ = "lateral_izquierdo"
ROL_LATERAL_DER = "lateral_derecho"
ROL_FONDO = "fondo"

ROL_AMARRE_FRONTAL = "amarre_frontal"   # Tira frontal contra el frente (Y-)
ROL_AMARRE_TRASERO = "amarre_trasero"   # Tira trasera contra la pared (Y+)
ROL_TRAVESA_SUPERIOR = "travesa_superior"
ROL_TRAVESA_INFERIOR = "travesa_inferior"
ROL_POSTE_CIEGO = "poste_ciego"

# ---------------------------------------------------------------------
# 3. CONSTANTES DE TALLER
# ---------------------------------------------------------------------

ANCHO_AMARRE_DEFAULT = 70.0      # mm de ancho de cada tira de amarre
ESPESOR_PANEL_DEFAULT = 18.0     # mm de espesor del tablero

# ---------------------------------------------------------------------
# 4. TIPO DE PIEZA GENERADA
# ---------------------------------------------------------------------


class PiezaCara(TypedDict, total=False):
    """Descriptora de una pieza generada por el estado constructivo de una cara.

    Coordenadas locales del COCO (marco de vdo_math_frames):
        X+ = derecha, Y+ = fondo, Z+ = arriba, frente funcional = Y-
    x, y, z : esquina minima de la caja en mm
    w, h, d : extension en cada eje (w=X/ancho, h=Y/profundidad, d=Z/alto)
    """
    nombre: str
    rol: str
    x: float
    y: float
    z: float
    w: float
    h: float
    d: float
    espesor: float
    modo_origen: str
    cara_origen: str


# ---------------------------------------------------------------------
# 5. CONFIGURACION DE CARA
# ---------------------------------------------------------------------


class CaraConfig(TypedDict, total=False):
    """Estado constructivo de una cara del COCO."""
    modo: ModoCara
    espesor: float
    # Solo para AMARRES: ancho de tira (default 70 mm)
    ancho_amarre: float
    # Solo para MARCO_RINCON: altura de travesaños (default 70 mm)
    altura_travesa: float


def _validar_cara(cfg: CaraConfig) -> CaraConfig:
    """Normaliza y valida una CaraConfig, rellenando defaults."""
    modo = str(cfg.get("modo", MODO_SOLIDO)).strip().upper()
    if modo not in MODOS_CARA_VALIDOS:
        raise ValueError(
            f"Modo de cara invalido: {modo!r}. "
            f"Validos: {MODOS_CARA_VALIDOS}.")
    espesor = float(cfg.get("espesor", ESPESOR_PANEL_DEFAULT))
    if espesor <= 0:
        raise ValueError(f"El espesor de la cara debe ser > 0: {espesor}")
    ancho_amarre = float(cfg.get("ancho_amarre", ANCHO_AMARRE_DEFAULT))
    if ancho_amarre <= 0:
        raise ValueError(f"El ancho de amarre debe ser > 0: {ancho_amarre}")
    altura_travesa = float(cfg.get("altura_travesa", ANCHO_AMARRE_DEFAULT))
    if altura_travesa <= 0:
        raise ValueError(f"La altura de travesa debe ser > 0: {altura_travesa}")
    return {
        "modo": modo,
        "espesor": espesor,
        "ancho_amarre": ancho_amarre,
        "altura_travesa": altura_travesa,
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
# 6. GENERADORES DE PIEZAS POR MODO
# ---------------------------------------------------------------------


def _pieza(nombre: str, rol: str, cara: str, modo: str,
           x: float, y: float, z: float,
           w: float, h: float, d: float, espesor: float) -> PiezaCara:
    """Constructor de despacha de PiezaCara."""
    return PiezaCara(
        nombre=nombre,
        rol=rol,
        x=round(float(x), 6),
        y=round(float(y), 6),
        z=round(float(z), 6),
        w=round(float(w), 6),
        h=round(float(h), 6),
        d=round(float(d), 6),
        espesor=round(float(espesor), 6),
        modo_origen=modo,
        cara_origen=cara,
    )


def _generar_solido(cara: str, cfg: CaraConfig, dims: dict) -> list[PiezaCara]:
    """SOLIDO: el tablero completo de espesor."""
    esp = cfg["espesor"]
    alto = dims["alto"]
    ancho = dims["ancho"]
    fondo = dims["fondo"]

    if cara == "techo":
        # Techo: placa horizontal (espesor sobre Z)
        return [_pieza(
            f"{cara}_solido", ROL_TECHO, cara, MODO_SOLIDO,
            0.0, 0.0, alto - esp,
            ancho, fondo, esp, esp)]
    if cara == "base":
        return [_pieza(
            f"{cara}_solido", ROL_BASE, cara, MODO_SOLIDO,
            0.0, 0.0, 0.0,
            ancho, fondo, esp, esp)]
    if cara in ("izquierda", "derecha"):
        # Lateral: placa vertical (espesor sobre X), altura completa
        z0 = 0.0
        x0 = 0.0 if cara == "izquierda" else ancho - esp
        return [_pieza(
            f"{cara}_solido",
            ROL_LATERAL_IZQ if cara == "izquierda" else ROL_LATERAL_DER,
            cara, MODO_SOLIDO,
            x0, 0.0, z0,
            esp, fondo, alto, esp)]
    if cara == "fondo":
        # Fondo: placa vertical trasera (espesor sobre Y)
        return [_pieza(
            f"{cara}_solido", ROL_FONDO, cara, MODO_SOLIDO,
            esp, fondo - esp, esp,
            ancho - 2 * esp, esp, alto - 2 * esp, esp)]
    return []


def _generar_amarres(cara: str, cfg: CaraConfig, dims: dict) -> list[PiezaCara]:
    """AMARRES: tapa sustituida por 2 tiras de 70 mm.

    Solo aplica a techo (y base, analogamente). Cada tira tiene ancho_amarre
    de profundidad (eje Y), recorre el ancho completo (eje X) y tiene el
    espesor del tablero (eje Z).

    Cuando tapa == "interno" (mesón de piedra sobre laterales), los amarres
    deben empezar en X = espesor para no colisionar 18 mm dentro de cada
    lateral.
    """
    esp = cfg["espesor"]
    ancho_am = cfg["ancho_amarre"]
    alto = dims["alto"]
    ancho = dims["ancho"]
    fondo = dims["fondo"]
    tapa = dims.get("tapa", "externo")

    if cara not in ("techo", "base"):
        # AMARRES no tiene sentido en laterales/fondo; degrada a SOLIDO
        return _generar_solido(cara, cfg, dims)

    z0 = 0.0 if cara == "base" else alto - esp
    y_frente = 0.0                      # contra el frente (Y-)
    y_trasero = fondo - ancho_am        # contra la pared (Y+)

    # Cuando tapa es interna, los laterales suben hasta el techo y ocupan
    # X in [0, esp] y X in [ancho-esp, ancho]. Los amarres deben quedar
    # entre ellos: X = esp, W = ancho - 2*esp.
    if tapa == "interno":
        x_start = esp
        x_width = max(0.0, ancho - 2.0 * esp)
    else:
        x_start = 0.0
        x_width = ancho

    piezas = []
    piezas.append(_pieza(
        f"{cara}_amarre_frontal", ROL_AMARRE_FRONTAL, cara, MODO_AMARRES,
        x_start, y_frente, z0,
        x_width, ancho_am, esp, esp))
    piezas.append(_pieza(
        f"{cara}_amarre_trasero", ROL_AMARRE_TRASERO, cara, MODO_AMARRES,
        x_start, y_trasero, z0,
        x_width, ancho_am, esp, esp))
    return piezas


def _generar_marco_rincon(cara: str, cfg: CaraConfig, dims: dict) -> list[PiezaCara]:
    """MARCO_RINCON: lateral suprimido, se inyectan:
        - travesaño horizontal superior e inferior de amarre
        - poste vertical ciego donde descansara la puerta

    Solo aplica a laterales (izquierda/derecha). Para otras caras degrada a SOLIDO.
    """
    esp = cfg["espesor"]
    alto_trav = cfg["altura_travesa"]
    alto = dims["alto"]
    ancho = dims["ancho"]
    fondo = dims["fondo"]

    if cara not in ("izquierda", "derecha"):
        return _generar_solido(cara, cfg, dims)

    # El lateral queda reducido a un poste ciego en el extremo interior
    # (donde la puerta bisagra y sella contra el modulo perpendicular).
    # El poste ocupa el ancho del espesor del tablero en X.
    x_poste = 0.0 if cara == "izquierda" else ancho - esp

    piezas = []
    # Travesaño superior: recorre el fondo (Y), espesor en X, altura_travesa en Z
    piezas.append(_pieza(
        f"{cara}_travesa_superior", ROL_TRAVESA_SUPERIOR, cara, MODO_MARCO_RINCON,
        x_poste, 0.0, alto - alto_trav,
        esp, fondo, alto_trav, esp))
    # Travesaño inferior: recorre el fondo (Y), espesor en X, altura_travesa en Z
    piezas.append(_pieza(
        f"{cara}_travesa_inferior", ROL_TRAVESA_INFERIOR, cara, MODO_MARCO_RINCON,
        x_poste, 0.0, 0.0,
        esp, fondo, alto_trav, esp))
    # Poste vertical ciego: listón frontal de 70 mm en Y (no todo el fondo),
    # deja el centro vacío para acceso al módulo en L.
    h_poste_frontal = max(0.0, alto - 2.0 * alto_trav)
    POSTE_ANCHO_FRONTAL = 70.0
    if h_poste_frontal > 0:
        piezas.append(_pieza(
            f"{cara}_poste_ciego", ROL_POSTE_CIEGO, cara, MODO_MARCO_RINCON,
            x_poste, 0.0, alto_trav,
            esp, POSTE_ANCHO_FRONTAL, h_poste_frontal, esp))
    return piezas


def _generar_nulo(cara: str, cfg: CaraConfig, dims: dict) -> list[PiezaCara]:
    """NULO: la cara no existe. No genera piezas."""
    return []


_GENERADORES = {
    MODO_SOLIDO: _generar_solido,
    MODO_AMARRES: _generar_amarres,
    MODO_MARCO_RINCON: _generar_marco_rincon,
    MODO_NULO: _generar_nulo,
}


# ---------------------------------------------------------------------
# 7. API PUBLICA
# ---------------------------------------------------------------------


def generar_piezas_cara(cara: str,
                        cfg: CaraConfig | dict,
                        dims: dict) -> list[PiezaCara]:
    """Genera la lista de piezas físicas para una cara del COCO segun su
    estado constructivo.

    Args:
        cara: Una de CARAS_COCO ("techo", "base", "izquierda", "derecha", "fondo").
        cfg: CaraConfig con modo, espesor, ancho_amarre, altura_travesa.
        dims: Dimensiones del COCO {alto, ancho, fondo, espesor}.

    Returns:
        Lista de PiezaCara (listas vacias si modo == NULO o cara invalida).

    Raises:
        ValueError: si modo o dimensiones son invalidos.
    """
    cara = str(cara).strip().lower()
    if cara not in CARAS_COCO:
        raise ValueError(
            f"Cara invalida: {cara!r}. Validas: {CARAS_COCO}.")
    cfg_val = _validar_cara(cfg or {})
    dims_val = _validar_dims(dims)
    generador = _GENERADORES[cfg_val["modo"]]
    return generador(cara, cfg_val, dims_val)


def piezas_por_caras(caras_cfg: dict, dims: dict) -> dict[str, list[PiezaCara]]:
    """Genera piezas para todas las caras del COCO de una sola pasada.

    Args:
        caras_cfg: dict {cara: CaraConfig} para cada cara de CARAS_COCO.
        dims: Dimensiones del COCO {alto, ancho, fondo, espesor}.

    Returns:
        dict {cara: [PiezaCara, ...]}.
    """
    dims_val = _validar_dims(dims)
    resultado = {}
    for cara in CARAS_COCO:
        cfg = caras_cfg.get(cara, {"modo": MODO_SOLIDO})
        resultado[cara] = generar_piezas_cara(cara, cfg, dims_val)
    return resultado


def modo_por_cara(caras_cfg: dict, cara: str) -> ModoCara:
    """Devuelve el modo constructivo de una cara (default SOLIDO)."""
    cfg = caras_cfg.get(cara, {}) or {}
    return str(cfg.get("modo", MODO_SOLIDO)).strip().upper()


def resumir_caras(caras_cfg: dict, dims: dict) -> dict:
    """Resumen textual de lo que genera cada cara (para UI / logs)."""
    dims_val = _validar_dims(dims)
    lineas = []
    total_piezas = 0
    for cara in CARAS_COCO:
        cfg = _validar_cara(caras_cfg.get(cara, {}) or {})
        piezas = generar_piezas_cara(cara, cfg, dims_val)
        total_piezas += len(piezas)
        if cfg["modo"] == MODO_NULO:
            desc = "ausente"
        elif cfg["modo"] == MODO_SOLIDO:
            desc = f"tablero {cfg['espesor']:.0f} mm"
        elif cfg["modo"] == MODO_AMARRES:
            desc = f"2 tiras de {cfg['ancho_amarre']:.0f} mm"
        elif cfg["modo"] == MODO_MARCO_RINCON:
            desc = f"2 travesaños + poste ciego (trav {cfg['altura_travesa']:.0f} mm)"
        else:
            desc = cfg["modo"]
        lineas.append(f"  {cara:10s}: {cfg['modo']:14s} -> {desc} ({len(piezas)} pieza(s))")
    return {
        "total_piezas": total_piezas,
        "lineas": lineas,
        "resumen": "\n".join(lineas),
    }


__all__ = [
    # Modos
    "MODO_SOLIDO",
    "MODO_AMARRES",
    "MODO_MARCO_RINCON",
    "MODO_NULO",
    "MODOS_CARA_VALIDOS",
    "ModoCara",
    # Caras y roles
    "CARAS_COCO",
    "ROL_TECHO", "ROL_BASE", "ROL_LATERAL_IZQ", "ROL_LATERAL_DER", "ROL_FONDO",
    "ROL_AMARRE_FRONTAL", "ROL_AMARRE_TRASERO",
    "ROL_TRAVESA_SUPERIOR", "ROL_TRAVESA_INFERIOR", "ROL_POSTE_CIEGO",
    # Constantes
    "ANCHO_AMARRE_DEFAULT", "ESPESOR_PANEL_DEFAULT",
    # Tipos
    "CaraConfig", "PiezaCara",
    # API
    "generar_piezas_cara",
    "piezas_por_caras",
    "modo_por_cara",
    "resumir_caras",
]
