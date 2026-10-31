# -*- coding: utf-8 -*-
# =====================================================================
# vdo_defaults.py
# Proveedor único de valores por defecto desde vdo_manifest.json.
# OJO: las constantes de este módulo se evalúan UNA VEZ al importar.
# No evita el caché de Python: lo que evita es un segundo intérprete
# del JSON.
# =====================================================================

import json
import os
import importlib

def _cargar_json_fresco():
    """Lee vdo_manifest.json del disco. La ruta sale de VDO._paths."""
    # Antes derivaba la ruta de __file__ por su cuenta, duplicando en
    # silencio lo que _paths.py declara como fuente única de verdad
    # (README, "Estructura"). Si el módulo se mueve de carpeta, con
    # __file__ la ruta se rompe sin aviso.
    from VDO._paths import VDO_DIR
    json_path = str(VDO_DIR / "vdo_manifest.json")

    if not os.path.exists(json_path):
        raise FileNotFoundError(f"vdo_manifest.json no encontrado en: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Instantánea al importar (constante de módulo, por tanto cacheada).
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
CANTO_MEDIO_DEFAULT = get_param("parametros_globales.canto_medio.valor", 1)
CANTO_FINO_DEFAULT = get_param("parametros_globales.canto_fino.valor", 0.4)
RANURA_FONDO_DEFAULT = get_param("parametros_globales.ranura_fondo.valor", 3)

# === CONFIGURACIÓN DEL FONDO (valores por defecto sensatos) ===
FONDO_HABILITADO = True
FONDO_CALIBRE = 6
FONDO_PROFUNDIDAD_RANURA = 3.0
FONDO_DISTANCIA_BORDE = 18.0
FONDO_UMBRAL_DELGADO = get_param(
    "parametros_globales.fondo_umbral_delgado.valor", 8.0)

# === ESTRUCTURA (Tapa y Base) ===
TAPA_POSICION = "externo"
BASE_POSICION = "interno"

# === MECANIZADOS / CNC ===
# Cuando False, el visor no genera solidos de taladros (shape.cut) y se
# muestra una representacion ligera; los datos CNC (vectores X/Y/Z, diametro,
# profundidad, cara) siguen viviendo al 100% en VDO_Paneles_JSON para el
# despiece/CAM independientemente de este ajuste.
VerMecanizados = False

# === ORIENTACIÓN (vocabulario del manifiesto) ===
ORIENTACIONES = get_param("orientaciones", {})
ORIENTACIONES_VALIDAS = list(ORIENTACIONES.keys())
ORIENTACION_DEFAULT = (
    "horizontal" if "horizontal" in ORIENTACIONES_VALIDAS
    else (ORIENTACIONES_VALIDAS[0] if ORIENTACIONES_VALIDAS else "horizontal")
)


def listar_orientaciones():
    """Lista las claves de orientaciones válidas desde el manifest."""
    return ORIENTACIONES_VALIDAS


def obtener_mapeo_orientacion(orientacion):
    """Devuelve el mapeo de ejes de una orientación desde el manifest.

    Args:
        orientacion (str): clave en manifest["orientaciones"].

    Returns:
        dict: {"X": parametro, "Y": parametro, "Z": parametro}

    Raises:
        ValueError: si la orientación no existe en el vocabulario.
    """
    info = ORIENTACIONES.get(orientacion)
    if info is None:
        raise ValueError(
            f"Orientación desconocida: '{orientacion}'. "
            f"Disponibles: {', '.join(ORIENTACIONES_VALIDAS)}")
    return info["ejes"]

# === CAJÓN CON CORREDERA OCULTA (params de parametros_cajon) ===
CAJON_ALTO_DEFAULT = get_param("parametros_cajon.alto_caja.valor", 120)
CAJON_GROSOR_DEFAULT = get_param("parametros_cajon.grosor_caja.valor", 16)
CAJON_FONDO_DEFAULT = get_param("parametros_cajon.grosor_fondo.valor", 6)
CAJON_FACHADA_DEFAULT = get_param("parametros_cajon.grosor_fachada.valor", 18)
CAJON_HOLGURA_LAT_FACHADA = get_param("parametros_cajon.holgura_lateral_fachada.valor", 2)
CAJON_HOLGURA_SUP_FACHADA = get_param("parametros_cajon.holgura_superior_fachada.valor", 2)
CAJON_HOLGURA_INF_FACHADA = get_param("parametros_cajon.holgura_inferior_fachada.valor", 2)
CAJON_PENETRACION_RANURA = get_param("parametros_cajon.penetracion_ranura_piso.valor", 10)
CAJON_EJE_RANURA = get_param("parametros_cajon.eje_ranura_piso.valor", 11.5)
