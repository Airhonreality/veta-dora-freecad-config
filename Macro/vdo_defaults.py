# -*- coding: utf-8 -*-
# =====================================================================
# vdo_defaults.py
# Proveedor único de valores por defecto desde vdo_manifest.json
# Carga directamente el JSON (evita caché de módulos Python)
# =====================================================================

import json
import os
import importlib

def _cargar_json_fresco():
    """Carga vdo_manifest.json directamente, sin caché."""
    macro_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(macro_dir, "vdo_manifest.json")

    if not os.path.exists(json_path):
        raise FileNotFoundError(f"vdo_manifest.json no encontrado en: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Cargar JSON fresco (NO cacheado)
_MANIFEST = _cargar_json_fresco()

def get_param(ruta, default=None):
    """
    Obtiene un parámetro del manifest por ruta de acceso.

    Ejemplo:
        get_param("parametros_locales.alto.valor")  → 720
        get_param("parametros_globales.canto_grueso.valor")  → 2

    Args:
        ruta (str): Ruta separada por puntos
        default: Valor si no encuentra

    Returns:
        El valor encontrado o default
    """
    partes = ruta.split(".")
    valor = _MANIFEST

    try:
        for parte in partes:
            valor = valor[parte]
        return valor
    except (KeyError, TypeError):
        if default is not None:
            return default
        raise ValueError(f"Parámetro no encontrado en manifest: {ruta}")


# === DIMENSIONES LOCALES (Params) ===
ALTO_DEFAULT = get_param("parametros_locales.alto.valor", 720)
ANCHO_DEFAULT = get_param("parametros_locales.ancho.valor", 600)
FONDO_DEFAULT = get_param("parametros_locales.fondo.valor", 580)
ESPESOR_DEFAULT = get_param("parametros_locales.espesor.valor", 18)

# === DIMENSIONES GLOBALES (Params_Melamina) ===
ESPESOR_MELAMINA_DEFAULT = get_param("parametros_globales.espesor_default.valor", 18)
CANTO_GRUESO_DEFAULT = get_param("parametros_globales.canto_grueso.valor", 2)
RANURA_FONDO_DEFAULT = get_param("parametros_globales.ranura_fondo.valor", 3)

# === CONFIGURACIÓN DEL FONDO (valores por defecto sensatos) ===
FONDO_HABILITADO = True
FONDO_CALIBRE = 6
FONDO_PROFUNDIDAD_RANURA = 3.0
FONDO_DISTANCIA_BORDE = 18.0

# === ESTRUCTURA (Tapa y Base) ===
TAPA_POSICION = "externo"
BASE_POSICION = "interno"
