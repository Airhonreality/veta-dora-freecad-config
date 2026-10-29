# -*- coding: utf-8 -*-
# =====================================================================
# vdo_facade_contract.py
# Capa 0 Pura - Contrato Universal de Cierres Frontales (Fachadas y Puertas)
# Fuente Única de Verdad para Agente 3 (Cajones) y Agente 4 (Puertas).
# No importa FreeCAD ni Qt. Solo lógica, decimales y enums oficiales.
# =====================================================================

from __future__ import annotations

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


# =====================================================================
# Funciones de cálculo puro (sin dependencias CAD)
# =====================================================================

def calcular_fachada_base(w_vano: float,
                          h_vano: float,
                          tipo_montaje: str,
                          holgura: float = HOLGURA_PERIMETRAL_DEFAULT,
                          solape: float = SOLAPE_PARCHE_NOMINAL) -> tuple:
    """Cálculo matemático puro y universal de las dimensiones de cualquier
    panel frontal (puerta o fachada de cajón).

    Retorna:
        (w_fachada, h_fachada) en milímetros.
    """
    w_vano = float(w_vano)
    h_vano = float(h_vano)
    tipo_montaje = str(tipo_montaje).strip().lower()

    if tipo_montaje == MONTAJE_PARCHE:
        w = w_vano + (2.0 * solape) - holgura
        h = h_vano + (2.0 * solape) - holgura
    elif tipo_montaje == MONTAJE_SEMIPARCHE:
        w = (w_vano + solape) / 2.0 - holgura
        h = h_vano + (2.0 * solape) - holgura
    elif tipo_montaje == MONTAJE_EMBEBIDA:
        w = w_vano - (2.0 * holgura)
        h = h_vano - (2.0 * holgura)
    else:
        raise ValueError(
            f"Tipo de montaje desconocido: {tipo_montaje!r}. "
            f"Validos: {MONTAJE_PARCHE}, {MONTAJE_SEMIPARCHE}, {MONTAJE_EMBEBIDA}.")

    if w <= 0 or h <= 0:
        raise ValueError(
            f"Dimensiones de fachada invalidas: {w:.1f} x {h:.1f} mm. "
            f"Revise holgura/solape.")

    return (round(w, 6), round(h, 6))


def aplicar_sistema_apertura(h_fachada: float,
                             sistema_apertura: str,
                             descuento_gola: float = GOLA_DESCUENTO_ALTURA_DEFAULT) -> tuple:
    """Ajusta la altura de la fachada segun el sistema de apertura y devuelve
    la operacion de mecanizado superior para el despiece y el PanelHeaderWidget.

    Retorna:
        (h_ajustada, operacion_canto_superior)
    """
    h_fachada = float(h_fachada)
    sistema_apertura = str(sistema_apertura).strip().lower()

    if sistema_apertura not in SISTEMAS_APERTURA_VALIDOS:
        raise ValueError(
            f"Sistema de apertura desconocido: {sistema_apertura!r}. "
            f"Validos: {SISTEMAS_APERTURA_VALIDOS}.")

    if sistema_apertura == APERTURA_GOLA:
        h_ajustada = max(0.0, h_fachada - descuento_gola)
        return (round(h_ajustada, 6), OPERACION_CANTO_GOLA)

    if sistema_apertura == APERTURA_45_GRADOS:
        return (round(h_fachada, 6), OPERACION_CANTO_45)

    # tirador y push_open conservan la altura total
    return (round(h_fachada, 6), OPERACION_CANTO_ESTANDAR)


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
    "calcular_fachada_base",
    "aplicar_sistema_apertura",
    "necesita_descuento_gola",
    "necesita_bisel_45",
    "necesita_expulsor_magnetico",
    "cantos_por_sistema_apertura",
    # Utilidades
    "CANTOS",
    "CANTO_ESTADOS",
]
