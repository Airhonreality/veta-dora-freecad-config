# -*- coding: utf-8 -*-
# =====================================================================
# vdo_puerta_despiece.py
# Capa 0 - Fórmulas de corte, cálculo de Newtons, holguras y posiciones
# de mecanizado para Puertas y Cierres (L2).
# No importa FreeCAD ni Qt. Solo lógica, decimales y catálogo de Capa H.
# =====================================================================

from __future__ import annotations

from VDO.core.vdo_math_facade import (
    MONTAJE_PARCHE, MONTAJE_SEMIPARCHE, MONTAJE_EMBEBIDA,
    HOLGURA_PERIMETRAL_DEFAULT, GOLA_DESCUENTO_ALTURA_DEFAULT,
    APERTURA_TIRADOR, APERTURA_GOLA, APERTURA_45_GRADOS, APERTURA_PUSH_OPEN,
    OPERACION_CANTO_ESTANDAR, OPERACION_CANTO_GOLA, OPERACION_CANTO_45,
    SOLAPE_PARCHE_NOMINAL, BISEL_45_ANGULO_DEFAULT, CALLE_ENTRE_FRENTES_DEFAULT,
    calcular_fachada_base, aplicar_sistema_apertura,
    necesita_descuento_gola, necesita_bisel_45, necesita_expulsor_magnetico,
    cantos_por_sistema_apertura,
    calcular_fachada_desde_deltas, calcular_origen_fachada_local,
    DELTA_PARCHE_TOTAL, DELTA_AGARRE_INFERIOR_AEREO, DELTA_GOLA_SUPERIOR,
    DELTA_GOLA_SUPERIOR_35, DELTA_SEMIPARCHE_DER, DELTA_SEMIPARCHE_IZQ,
    DELTA_RINCON_CIEGO, DELTA_EMBEBIDA,
)
from VDO.hub.vdo_hub_hardware import resolve_hinge, resolve_sliding, calculate_sliding_doors

# ---------------------------------------------------------------------
# Constantes de taller (fuente única: vdo_facade_contract.py)
# ---------------------------------------------------------------------

CAZALETA_DIAMETRO = 35.0      # mm
CAZALETA_PROFUNDIDAD = 11.5   # mm
COTA_K_DEFAULT = 4.0          # mm (distancia de la cara al centro de la cazoleta)
COTA_CAZOLETA_X = COTA_K_DEFAULT + CAZALETA_DIAMETRO / 2.0  # 21.5 mm
COTA_CAZOLETA_Z_EXTREMO = 100.0  # mm desde el borde superior/inferior

HOLGURA_LUZ_DEFAULT = HOLGURA_PERIMETRAL_DEFAULT  # mm (parche / semiparche)
SOLAPE_SEMIPARCHE_NOMINAL = 8.0   # mm sobre montante compartido (legacy default)

DENSIDAD_MELAMINA_KG_M3 = 720.0   # kg/m^3
ESPESOR_PANEL_M = 0.018           # m (18 mm)
GRAVEDAD = 9.81                   # m/s^2
BRAZO_PALANCA_M = 0.12            # m
NUM_PISTONES = 2
FACTOR_SEGURIDAD = 1.2

PISTONES_COMERCIALES_N = [60, 80, 100, 120, 150]

# Umbrales de altura para cantidad de bisagras (mm)
UMBRAL_2_BISAGRAS = 1000.0
UMBRAL_3_BISAGRAS = 1500.0


# =====================================================================
# A. Puertas Batientes Verticales
# =====================================================================

def calcular_dimensiones_batiente(W_neto, H_neto, tipo_montaje,
                                  solape=SOLAPE_SEMIPARCHE_NOMINAL,
                                  holgura=None, deltas=None):
    """Calcula el corte neto de la puerta batiente vertical.

    Consume `calcular_fachada_base` de vdo_facade_contract.py como fuente
    unica de verdad para todos los frentes del sistema.

    Args:
        W_neto: luz libre horizontal del vano (mm).
        H_neto: luz libre vertical del vano (mm).
        tipo_montaje: "parche", "semiparche" o "embebida".
        solape: solape nominal (mm) para semiparche (default 8 mm).
        holgura: holgura perimetral/luz (mm). Default 2.0 mm.
        deltas: si se proporciona, se usa el contrato de deltas netos
            (calcular_fachada_desde_deltas) en lugar de holgura/solape.

    Returns:
        dict con W, H, tipo_montaje, holgura, solape, deltas.
    """
    tipo_montaje = str(tipo_montaje).strip().lower()
    if holgura is None:
        holgura = HOLGURA_PERIMETRAL_DEFAULT

    if deltas is not None:
        # Contrato de deltas netos: ignora holgura/solape
        w, h = calcular_fachada_desde_deltas(W_neto, H_neto, deltas)
    else:
        # Usar el contrato central para el calculo puro (legacy)
        w, h = calcular_fachada_base(W_neto, H_neto, tipo_montaje,
                                      holgura=holgura, solape=solape)

    return {
        "W": w,
        "H": h,
        "tipo_montaje": tipo_montaje,
        "holgura": holgura,
        "solape": solape,
        "deltas": dict(deltas) if deltas is not None else None,
    }


def calcular_origen_batiente_local(x_vano, z_vano, deltas=None,
                                   holgura=None):
    """Calcula el punto de anclaje (X, Z) de la puerta respecto al marco
    del vano, usando deltas netos (anti-basura espacial).

    Si no se pasan deltas, se deriva un delta parche total desde holgura
    (anula el centrado simetrico del legacy).

    Retorna:
        (x_local, z_local) en milímetros.
    """
    if deltas is not None:
        return calcular_origen_fachada_local(x_vano, z_vano, deltas)
    # Fallback legacy: parche total con holgura por borde
    h = float(holgura if holgura is not None else HOLGURA_PERIMETRAL_DEFAULT)
    deltas_legacy = {
        "norte": h, "sur": h, "este": h, "oeste": h,
    }
    return calcular_origen_fachada_local(x_vano, z_vano, deltas_legacy)


def cantidad_bisagras(H):
    """Devuelve la cantidad de bisagras segun la regla de altura de taller.

    H < 1000 -> 2
    1000 <= H < 1500 -> 3
    H >= 1500 -> 4
    """
    H = float(H)
    if H < UMBRAL_2_BISAGRAS:
        return 2
    if H < UMBRAL_3_BISAGRAS:
        return 3
    return 4


def posiciones_cazoleta(H, n_bisagras=None, cota_extremo=COTA_CAZOLETA_Z_EXTREMO):
    """Calcula las cotas Z de los centros de las cazoletas.

    Los extremos superior e inferior se colocan a cota_extremo del borde.
    Las intermedias se distribuyen equitativamente en Z.

    Args:
        H: altura de la puerta (mm).
        n_bisagras: cantidad (se calcula si no se pasa).
        cota_extremo: distancia desde el borde superior/inferior (mm).

    Returns:
        lista de cotas Z (mm) desde el borde superior de la puerta.
    """
    H = float(H)
    if n_bisagras is None:
        n_bisagras = cantidad_bisagras(H)
    n_bisagras = int(n_bisagras)

    if n_bisagras <= 0:
        return []

    if n_bisagras == 1:
        return [round(H / 2.0, 6)]

    # Extremos fijos, intermedias equidistantes.
    if n_bisagras == 2:
        zs = [cota_extremo, H - cota_extremo]
    else:
        paso = (H - 2.0 * cota_extremo) / (n_bisagras - 1)
        zs = [round(cota_extremo + i * paso, 6) for i in range(n_bisagras)]

    return zs


def cazoleta_tecnica():
    """Devuelve los parámetros técnicos de la cazoleta de 35 mm."""
    return {
        "diametro": CAZALETA_DIAMETRO,
        "radio": CAZALETA_DIAMETRO / 2.0,
        "profundidad": CAZALETA_PROFUNDIDAD,
        "cota_k": COTA_K_DEFAULT,
        "cota_x": COTA_CAZOLETA_X,
        "cota_z_extremo": COTA_CAZOLETA_Z_EXTREMO,
    }


def bisagras_para_puerta(H, tipo_montaje="parche", prefer_sku=None):
    """Resuelve las bisagras y sus posiciones para una puerta batiente.

    Consulta Capa H (resolve_hinge) y aplica la regla de altura de taller.

    Returns:
        dict con sku, nombre, proveedor, precio_unitario, n_bisagras,
        posiciones_z, cota_x, profundidad_cazoleta, diametro_cazoleta.
    """
    herraje = resolve_hinge(tipo_montaje, prefer_sku=prefer_sku)
    tecnicos = herraje["parametros_tecnicos"]
    n = cantidad_bisagras(H)
    zs = posiciones_cazoleta(H, n)
    return {
        "sku": herraje.get("sku", tipo_montaje.upper()),
        "nombre": herraje["nombre"],
        "proveedor": herraje["proveedor"],
        "precio_unitario": herraje["precio_unitario"],
        "moneda": herraje["moneda"],
        "tipo_montaje": tipo_montaje,
        "n_bisagras": n,
        "posiciones_z": zs,
        "cota_x": COTA_CAZOLETA_X,
        "profundidad_cazoleta": float(tecnicos.get("profundidad_cazoleta",
                                                   CAZALETA_PROFUNDIDAD)),
        "diametro_cazoleta": float(tecnicos.get("diametro_cazoleta",
                                                CAZALETA_DIAMETRO)),
        "cota_k": float(tecnicos.get("cota_k_default", COTA_K_DEFAULT)),
        "total": round(herraje["precio_unitario"] * n, 2),
    }


# =====================================================================
# B. Puertas Horizontales (Basculantes / Abatibles) - Newtons
# =====================================================================

def masa_puerta(W, H, t=ESPESOR_PANEL_M, rho=DENSIDAD_MELAMINA_KG_M3):
    """Masa estimada de la puerta en kg.

    M = (W/1000) * (H/1000) * t * rho
    """
    W_m = float(W) / 1000.0
    H_m = float(H) / 1000.0
    return W_m * H_m * t * rho


def fuerza_piston_teorica(W, H, n_pistones=NUM_PISTONES,
                          brazo_palanca=BRAZO_PALANCA_M,
                          factor_seguridad=FACTOR_SEGURIDAD,
                          t=ESPESOR_PANEL_M, rho=DENSIDAD_MELAMINA_KG_M3):
    """Fuerza teorica requerida por pistón (Newtons).

    F ≈ (M * g * (H / 2000)) / (2 * brazo_palanca) * factor_seguridad
    """
    M = masa_puerta(W, H, t, rho)
    H_m = float(H) / 1000.0
    F = (M * GRAVEDAD * (H_m / 2.0)) / (n_pistones * brazo_palanca) * factor_seguridad
    return F


def piston_recomendado(W, H, n_pistones=NUM_PISTONES):
    """Devuelve el pistón comercial más cercano >= fuerza teorica.

    Catálogo: [60, 80, 100, 120, 150] N.
    """
    F = fuerza_piston_teorica(W, H, n_pistones)
    for comercial in PISTONES_COMERCIALES_N:
        if comercial >= F - 1e-9:
            return comercial, F
    return PISTONES_COMERCIALES_N[-1], F


def descripcion_piston(W, H):
    """Texto legible para la interfaz: '80N (2 unidades)'."""
    comercial, F = piston_recomendado(W, H)
    return f"{comercial}N ({NUM_PISTONES} unidades)", comercial, F


# =====================================================================
# C. Puertas Corredizas (Ducasse D-52 / AL-1535)
# =====================================================================

def calcular_corrediza(inner_w, inner_h, tipo_mueble="closet", n_hojas=2,
                       prefer_sku=None):
    """Calcula el despiece de hojas corredizas consumiendo Capa H.

    Args:
        inner_w: luz libre interior (mm).
        inner_h: luz libre interior (mm).
        tipo_mueble: "closet"/"placard" -> DUC-KIT-D52;
                     "mueble"/"alacena" -> DUC-AL-1535-MAD.
        n_hojas: cantidad de hojas (2 o 3).
        prefer_sku: SKU comercial a forzar.

    Returns:
        dict con el resultado de calculate_sliding_doors + sku_resuelto.
    """
    sku = prefer_sku
    if not sku:
        # resolve_sliding valida el tipo_mueble y devuelve el hardware dict;
        # necesitamos el SKU string para calculate_sliding_doors.
        resolve_sliding(tipo_mueble)  # valida que exista
        tipo_lower = str(tipo_mueble).strip().lower()
        _default_map = {
            "closet": "DUC-KIT-D52", "placard": "DUC-KIT-D52",
            "mueble": "DUC-AL-1535-MAD", "alacena": "DUC-AL-1535-MAD",
        }
        sku = _default_map.get(tipo_lower)
        if sku is None:
            raise KeyError(
                f"Tipo de mueble corredizo {tipo_mueble!r} no soportado.")
    res = calculate_sliding_doors(inner_w, inner_h, sku, n_hojas=n_hojas)
    res["sku_resuelto"] = sku
    res["tipo_mueble"] = tipo_mueble
    res["n_hojas"] = n_hojas
    return res


# =====================================================================
# D. Sistemas de Apertura (consumen vdo_facade_contract.py)
# =====================================================================

# Nombres legados mantenidos para compatibilidad con el resto del ecosistema.
SISTEMAS_APERTURA = (
    APERTURA_TIRADOR,
    APERTURA_45_GRADOS,
    APERTURA_GOLA,
    APERTURA_PUSH_OPEN,
)

# Mapeo de nombres de visualización (UI) y nombres legados a claves del contrato.
# Cubre tanto los valores del enum de vdo_puerta_core.py como los usados
# históricamente en vdo_puerta_task.py.
APERTURA_LEGADO_A_CONTRATO = {
    # Nombres de visualización del enum SistemaApertura (vdo_puerta_core.py)
    "tirador tradicional": APERTURA_TIRADOR,
    "inglete 45 grados": APERTURA_45_GRADOS,
    "perfil gola": APERTURA_GOLA,
    "push to open": APERTURA_PUSH_OPEN,
    # Nombres legacy de vdo_puerta_task.py (antes del contrato)
    "tirador": APERTURA_TIRADOR,
    "fachada_a_45_grados": APERTURA_45_GRADOS,
    "perfil_gola_aluminio": APERTURA_GOLA,
    "push_open_mecanico": APERTURA_PUSH_OPEN,
    # Alias del contrato (nombres canónicos)
    "tirador": APERTURA_TIRADOR,
    "inglete_45": APERTURA_45_GRADOS,
    "gola_aluminio": APERTURA_GOLA,
    "push_open": APERTURA_PUSH_OPEN,
}

# Descuento de altura por sistema (según el contrato central)
APERTURA_DESCUENTO_ALTO = {
    APERTURA_TIRADOR: 0.0,
    APERTURA_45_GRADOS: 0.0,
    APERTURA_GOLA: GOLA_DESCUENTO_ALTURA_DEFAULT,
    APERTURA_PUSH_OPEN: 0.0,
}


def _normalizar_apertura(tipo_apertura: str) -> str:
    """Normaliza un nombre de apertura (legado o canonico) a la clave del contrato."""
    tipo_apertura = str(tipo_apertura).strip().lower()
    return APERTURA_LEGADO_A_CONTRATO.get(tipo_apertura, tipo_apertura)


def ajuste_altura_apertura(tipo_apertura, H):
    """Devuelve la altura ajustada segun el sistema de apertura.

    Consume `aplicar_sistema_apertura` de vdo_facade_contract.py.
    Retorna (h_ajustada, descuento).
    """
    contrato = _normalizar_apertura(tipo_apertura)
    h_ajustada, operacion = aplicar_sistema_apertura(
        float(H), contrato,
        descuento_gola=GOLA_DESCUENTO_ALTURA_DEFAULT)
    descuento = max(0.0, float(H) - h_ajustada)
    return (round(h_ajustada, 6), round(descuento, 6))


def necesita_expulsor_magnetico(tipo_apertura):
    """True si inyecta expulsor magnetico al BOM (push_open)."""
    return necesita_expulsor_magnetico_contrato(tipo_apertura)


def necesita_expulsor_magnetico_contrato(tipo_apertura):
    """Wrapper interno para evitar colisión de nombres."""
    contrato = _normalizar_apertura(tipo_apertura)
    return contrato == APERTURA_PUSH_OPEN


def necesita_cantos_45(tipo_apertura):
    """True si aplica bisel a 45° en el canto de agarre."""
    contrato = _normalizar_apertura(tipo_apertura)
    return contrato == APERTURA_45_GRADOS


__all__ = [
    "CAZALETA_DIAMETRO", "CAZALETA_PROFUNDIDAD", "COTA_K_DEFAULT",
    "COTA_CAZOLETA_X", "COTA_CAZOLETA_Z_EXTREMO",
    "HOLGURA_PERIMETRAL_DEFAULT", "HOLGURA_LUZ_DEFAULT",
    "SOLAPE_SEMIPARCHE_NOMINAL",
    "DENSIDAD_MELAMINA_KG_M3", "ESPESOR_PANEL_M", "GRAVEDAD",
    "BRAZO_PALANCA_M", "NUM_PISTONES", "FACTOR_SEGURIDAD",
    "PISTONES_COMERCIALES_N",
    "calcular_dimensiones_batiente", "cantidad_bisagras",
    "posiciones_cazoleta", "cazoleta_tecnica", "bisagras_para_puerta",
    "calcular_origen_batiente_local",
    "masa_puerta", "fuerza_piston_teorica", "piston_recomendado",
    "descripcion_piston", "calcular_corrediza",
    # Contrato de fachadas (reexportados)
    "APERTURA_TIRADOR", "APERTURA_GOLA", "APERTURA_45_GRADOS", "APERTURA_PUSH_OPEN",
    "MONTAJE_PARCHE", "MONTAJE_SEMIPARCHE", "MONTAJE_EMBEBIDA",
    "SISTEMAS_APERTURA", "APERTURA_DESCUENTO_ALTO",
    "GOLA_DESCUENTO_ALTURA_DEFAULT", "HOLGURA_PERIMETRAL_DEFAULT",
    "SOLAPE_PARCHE_NOMINAL", "BISEL_45_ANGULO_DEFAULT",
    "calcular_fachada_base", "aplicar_sistema_apertura",
    "necesita_descuento_gola", "necesita_bisel_45",
    "necesita_expulsor_magnetico", "necesita_cantos_45",
    "cantos_por_sistema_apertura",
]
