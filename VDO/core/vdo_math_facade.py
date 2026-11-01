# -*- coding: utf-8 -*-
# =====================================================================
# vdo_facade_contract.py
# Capa 0 Pura - Contrato Universal de Cierres Frontales (Fachadas y Puertas)
# Fuente Única de Verdad para Agente 3 (Cajones) y Agente 4 (Puertas).
# No importa FreeCAD ni Qt. Solo lógica, decimales y enums oficiales.
# =====================================================================

from __future__ import annotations
from typing import TypedDict

# ---------------------------------------------------------------------
# 1. SISTEMAS DE APERTURA (Constantes Oficiales)
# ---------------------------------------------------------------------

APERTURA_TIRADOR = "tirador"         # Tirador o manija tradicional postiza
APERTURA_GOLA = "gola_aluminio"      # Perfil Gola de aluminio integrado (C o L)
APERTURA_45_GRADOS = "inglete_45"    # Canto con bisel a 45° (uñero corrido)
APERTURA_PUSH_OPEN = "push_open"     # Apertura por presión (émbolo magnético)

SISTEMAS_APERTURA_VALIDOS = (
    APERTURA_TIRADOR,
    APERTURA_GOLA,
    APERTURA_45_GRADOS,
    APERTURA_PUSH_OPEN,
)

# ---------------------------------------------------------------------
# 2. TIPOLOGÍAS DE MONTAJE FRONTALES
# ---------------------------------------------------------------------

MONTAJE_PARCHE = "parche"          # Solapa sobre los cantos del vano
MONTAJE_SEMIPARCHE = "semiparche"  # Comparte montante central
MONTAJE_EMBEBIDA = "embebida"      # A ras dentro del vano (deja cantos vistos)

# ---------------------------------------------------------------------
# 3. VALORES NOMINALES POR DEFECTO (Tolerancias y Fábrica)
# ---------------------------------------------------------------------

HOLGURA_PERIMETRAL_DEFAULT = 2.0    # mm de luz perimetral entre fachada y armazón
CALLE_ENTRE_FRENTES_DEFAULT = 2.5   # mm de separación horizontal entre frentes adyacentes
GOLA_DESCUENTO_ALTURA_DEFAULT = 35.0   # mm que se restan a la altura de la fachada para el perfil C/L
BISEL_45_ANGULO_DEFAULT = 45.0    # Grados de chaflán en arista de agarre
SOLAPE_PARCHE_NOMINAL = 16.0      # mm de recubrimiento sobre canto de 18 mm

# ---------------------------------------------------------------------
# 4. OPERACIONES DE CANTO (metadata para el despiece y el PanelHeaderWidget)
# ---------------------------------------------------------------------

OPERACION_CANTO_ESTANDAR = "CANTO_ESTANDAR"
OPERACION_CANTO_GOLA = "CORTE_RECTO_GOLA"
OPERACION_CANTO_45 = "BISEL_45"

# ---------------------------------------------------------------------
# 5. DELTA DE BORDE (Contrato de Fachada Universal)
# ---------------------------------------------------------------------

class DeltasBorde(TypedDict):
    """Vector neto de desplazamiento por borde del panel frontal respecto
    al filo interior del vano.

    Convención: Norte = arriba, Sur = abajo, Este = derecha, Oeste = izquierda.
    El valor es NETO: ya incluye holgura, solape, volado o retracción.
    Positivo (+) crece el panel más allá del vano; negativo (-) lo retrae.

    Fórmula de ancho:  W_panel = W_vano + Δ_oeste + Δ_este
    Fórmula de alto:   H_panel = H_vano + Δ_norte + Δ_sur
    (sin restas mágicas globales al final).
    """
    norte: float  # Superior
    sur: float    # Inferior
    este: float   # Derecha
    oeste: float  # Izquierda


# Presets oficiales de taller (valores NETOS en mm)
DELTA_PARCHE_TOTAL: DeltasBorde = {
    "norte": 16.0, "sur": 16.0, "este": 16.0, "oeste": 16.0,
}
DELTA_AGARRE_INFERIOR_AEREO: DeltasBorde = {
    "norte": 16.0, "sur": 35.0, "este": 16.0, "oeste": 16.0,
}
DELTA_GOLA_SUPERIOR: DeltasBorde = {
    "norte": -25.0, "sur": 16.0, "este": 16.0, "oeste": 16.0,
}
DELTA_GOLA_SUPERIOR_35: DeltasBorde = {
    "norte": -35.0, "sur": 16.0, "este": 16.0, "oeste": 16.0,
}
DELTA_SEMIPARCHE_DER: DeltasBorde = {
    "norte": 16.0, "sur": 16.0, "este": 8.0, "oeste": 16.0,
}
DELTA_SEMIPARCHE_IZQ: DeltasBorde = {
    "norte": 16.0, "sur": 16.0, "este": 16.0, "oeste": 8.0,
}
DELTA_RINCON_CIEGO: DeltasBorde = {
    "norte": 16.0, "sur": 16.0, "este": 0.0, "oeste": 16.0,
}
DELTA_EMBEBIDA: DeltasBorde = {
    "norte": -2.0, "sur": -2.0, "este": -2.0, "oeste": -2.0,
}

# Mapa de montaje legacy -> deltas por defecto (para calcular_fachada_base)
_DELTAS_POR_MONTAJE = {
    MONTAJE_PARCHE: DELTA_PARCHE_TOTAL,
    MONTAJE_SEMIPARCHE: DELTA_SEMIPARCHE_DER,
    MONTAJE_EMBEBIDA: DELTA_EMBEBIDA,
}

# =====================================================================
# Herencia de Δ_S (fachada inferior)
# =====================================================================
# luz_suelo vive en el módulo (COCO.LuzSueloDefault): holgura uniforme para
# toda la tirada. Cada fachada inferior hereda Δ_S = H_zocalo − luz_suelo.
# Si la fachada tiene un vector de deltas propio, ese vector manda.

LUZ_SUELO_DEFAULT = 15.0  # mm: punta del pie / desniveles de suelo


def delta_s_fachada_inferior(h_zocalo: float, luz_suelo: float) -> float:
    """Δ_S heredado: cuánto baja la fachada inferior bajo el vano."""
    return float(h_zocalo) - float(luz_suelo)


def deltas_heredados_inferior(montaje: str, h_zocalo: float,
                              luz_suelo: float,
                              norte: float = 0.0) -> DeltasBorde:
    """Vector completo de una fachada inferior con Δ_S heredado.

    Parte del preset del montaje (lados y solapes) y sustituye sólo `sur`.
    `norte` admite el descuento de altura por apertura (gola).
    """
    base = _DELTAS_POR_MONTAJE.get(str(montaje).strip().lower(),
                                   DELTA_PARCHE_TOTAL)
    return {
        "norte": float(norte),
        "sur": delta_s_fachada_inferior(h_zocalo, luz_suelo),
        "este": float(base["este"]),
        "oeste": float(base["oeste"]),
    }


# =====================================================================
# Funciones de cálculo puro (sin dependencias CAD)
# =====================================================================


def validar_deltas(deltas: DeltasBorde) -> DeltasBorde:
    """Valida y normaliza un diccionario de deltas, asegurando las 4 claves
    con valores float."""
    requeridas = ("norte", "sur", "este", "oeste")
    for clave in requeridas:
        if clave not in deltas:
            raise ValueError(
                f"DeltasBorde incompleto: falta la clave '{clave}'. "
                f"Claves requeridas: {requeridas}.")
    return {clave: float(deltas[clave]) for clave in requeridas}


def calcular_fachada_desde_deltas(
    w_vano: float,
    h_vano: float,
    deltas: DeltasBorde,
) -> tuple[float, float]:
    """Cálculo matemático puro del panel frontal por deltas netos
    independientes por borde.

    Fórmula:
        W_panel = W_vano + Δ_oeste + Δ_este
        H_panel = H_vano + Δ_norte + Δ_sur

    No se aplica holgura global adicional: cada delta es neto.

    Retorna:
        (ancho_panel, alto_panel) en milímetros, redondeados a 6 decimales.
    """
    deltas = validar_deltas(deltas)
    w_vano = float(w_vano)
    h_vano = float(h_vano)

    w = w_vano + deltas["oeste"] + deltas["este"]
    h = h_vano + deltas["norte"] + deltas["sur"]

    if w <= 0.0 or h <= 0.0:
        raise ValueError(
            f"Dimensiones de fachada invalidas ({w:.1f} x {h:.1f} mm). "
            f"Vano: ({w_vano}x{h_vano}), Deltas: {deltas}"
        )

    return (round(w, 6), round(h, 6))


def calcular_origen_fachada_local(
    x_vano: float,
    z_vano: float,
    deltas: DeltasBorde,
) -> tuple[float, float]:
    """Calcula el punto de anclaje (X, Z) del panel frontal respecto al
    marco inferior-izquierdo del vano.

    Previene derivas y desalineaciones por deltas asimétricos: no se promedia,
    se ancla al borde oeste y sur.

        X_local = X_vano - Δ_oeste
        Z_local = Z_vano - Δ_sur

    Retorna:
        (x_local, z_local) en milímetros, redondeados a 6 decimales.
    """
    deltas = validar_deltas(deltas)
    x_vano = float(x_vano)
    z_vano = float(z_vano)

    x_local = x_vano - deltas["oeste"]
    z_local = z_vano - deltas["sur"]

    return (round(x_local, 6), round(z_local, 6))


def calcular_fachada_base(w_vano: float,
                          h_vano: float,
                          tipo_montaje: str,
                          holgura: float = HOLGURA_PERIMETRAL_DEFAULT,
                          solape: float = SOLAPE_PARCHE_NOMINAL) -> tuple:
    """Cálculo matemático puro y universal de las dimensiones de cualquier
    panel frontal (puerta o fachada de cajón).

    Esta función es un wrapper de compatibilidad que resuelve los deltas
    internamente a partir de los parámetros legacy (holgura / solape) y
    delega en ``calcular_fachada_desde_deltas``.

    Retorna:
        (w_fachada, h_fachada) en milímetros.
    """
    w_vano = float(w_vano)
    h_vano = float(h_vano)
    tipo_montaje = str(tipo_montaje).strip().lower()

    if tipo_montaje not in _DELTAS_POR_MONTAJE:
        raise ValueError(
            f"Tipo de montaje desconocido: {tipo_montaje!r}. "
            f"Validos: {MONTAJE_PARCHE}, {MONTAJE_SEMIPARCHE}, {MONTAJE_EMBEBIDA}.")

    deltas = _DELTAS_POR_MONTAJE[tipo_montaje]
    return calcular_fachada_desde_deltas(w_vano, h_vano, deltas)


def _operacion_por_sistema_apertura(sistema_apertura: str) -> str:
    """Devuelve solo la operacion de canto para un sistema de apertura,
    sin modificar la altura dimensional.

    La altura ahora se controla mediante deltas["norte"] (ej. gola = -25).
    Esta función solo resuelve la semantica de mecanizado / herraje.
    """
    sistema_apertura = str(sistema_apertura).strip().lower()
    if sistema_apertura not in SISTEMAS_APERTURA_VALIDOS:
        raise ValueError(
            f"Sistema de apertura desconocido: {sistema_apertura!r}. "
            f"Validos: {SISTEMAS_APERTURA_VALIDOS}.")

    if sistema_apertura == APERTURA_GOLA:
        return OPERACION_CANTO_GOLA
    if sistema_apertura == APERTURA_45_GRADOS:
        return OPERACION_CANTO_45
    return OPERACION_CANTO_ESTANDAR


def aplicar_sistema_apertura(h_fachada: float,
                             sistema_apertura: str,
                             descuento_gola: float = GOLA_DESCUENTO_ALTURA_DEFAULT) -> tuple:
    """Ajuste semantico de la fachada segun el sistema de apertura.

    Rol actual: 100% semantica y mecanizado, 0% dimensional. La altura se
    deja intacta; el descuento de gola se expresa ahora como delta neto en
    ``calcular_fachada_desde_deltas`` (deltas["norte"] negativo).

    Retorna:
        (h_fachada_inalterada, operacion_canto_superior)
    """
    h_fachada = float(h_fachada)
    sistema_apertura = str(sistema_apertura).strip().lower()

    if sistema_apertura not in SISTEMAS_APERTURA_VALIDOS:
        raise ValueError(
            f"Sistema de apertura desconocido: {sistema_apertura!r}. "
            f"Validos: {SISTEMAS_APERTURA_VALIDOS}.")

    operacion = _operacion_por_sistema_apertura(sistema_apertura)
    return (round(h_fachada, 6), operacion)


def necesita_descuento_gola(sistema_apertura: str) -> bool:
    """True si el sistema requiere descuento de 35 mm en altura (gola)."""
    return str(sistema_apertura).strip().lower() == APERTURA_GOLA


def necesita_bisel_45(sistema_apertura: str) -> bool:
    """True si el sistema requiere bisel a 45° en la arista de agarre."""
    return str(sistema_apertura).strip().lower() == APERTURA_45_GRADOS


def necesita_expulsor_magnetico(sistema_apertura: str) -> bool:
    """True si el sistema inyecta expulsor magnetico al BOM (push_open)."""
    return str(sistema_apertura).strip().lower() == APERTURA_PUSH_OPEN


# ---------------------------------------------------------------------
# Metadatos para PanelHeaderWidget (cantos y mecanizados)
# ---------------------------------------------------------------------

CANTOS = ("norte", "sur", "este", "oeste")

CANTO_ESTADOS = ("FX", "RIG", "SMRG", "NONE")


def cantos_por_sistema_apertura(sistema_apertura: str,
                                canto_superior: str = "FX",
                                cantos_laterales: str = "FX",
                                canto_inferior: str = "FX") -> dict:
    """Devuelve el estado de los 4 cantos segun el sistema de apertura.

    Convenio: Norte = arriba, Sur = abajo, Oeste = izquierda, Este = derecha.
    """
    sistema_apertura = str(sistema_apertura).strip().lower()
    cantos = {
        "norte": canto_superior,
        "sur": canto_inferior,
        "este": cantos_laterales,
        "oeste": cantos_laterales,
    }

    if sistema_apertura == APERTURA_45_GRADOS:
        cantos["norte"] = "BISEL_45"
    if sistema_apertura == APERTURA_GOLA:
        cantos["norte"] = OPERACION_CANTO_GOLA

    return cantos


__all__ = [
    # Sistemas de apertura
    "APERTURA_TIRADOR",
    "APERTURA_GOLA",
    "APERTURA_45_GRADOS",
    "APERTURA_PUSH_OPEN",
    "SISTEMAS_APERTURA_VALIDOS",
    # Montajes
    "MONTAJE_PARCHE",
    "MONTAJE_SEMIPARCHE",
    "MONTAJE_EMBEBIDA",
    # Tipos y presets de deltas (Contrato de Fachada Universal)
    "DeltasBorde",
    "DELTA_PARCHE_TOTAL",
    "DELTA_AGARRE_INFERIOR_AEREO",
    "DELTA_GOLA_SUPERIOR",
    "DELTA_GOLA_SUPERIOR_35",
    "DELTA_SEMIPARCHE_DER",
    "DELTA_SEMIPARCHE_IZQ",
    "DELTA_RINCON_CIEGO",
    "DELTA_EMBEBIDA",
    # Constantes de taller
    "HOLGURA_PERIMETRAL_DEFAULT",
    "CALLE_ENTRE_FRENTES_DEFAULT",
    "GOLA_DESCUENTO_ALTURA_DEFAULT",
    "BISEL_45_ANGULO_DEFAULT",
    "SOLAPE_PARCHE_NOMINAL",
    # Operaciones de canto
    "OPERACION_CANTO_ESTANDAR",
    "OPERACION_CANTO_GOLA",
    "OPERACION_CANTO_45",
    # Funciones
    "validar_deltas",
    "calcular_fachada_desde_deltas",
    "LUZ_SUELO_DEFAULT",
    "delta_s_fachada_inferior",
    "deltas_heredados_inferior",
    "calcular_origen_fachada_local",
    "calcular_fachada_base",
    "aplicar_sistema_apertura",
    "necesita_descuento_gola",
    "necesita_bisel_45",
    "necesita_expulsor_magnetico",
    "cantos_por_sistema_apertura",
    "_operacion_por_sistema_apertura",
    # Utilidades
    "CANTOS",
    "CANTO_ESTADOS",
]
