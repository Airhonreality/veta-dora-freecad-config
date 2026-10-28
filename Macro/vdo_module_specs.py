# -*- coding: utf-8 -*-
# =====================================================================
# vdo_module_specs.py
# Registro de módulos VDO y sus paneles de configuración.
# Los imports son perezosos para evitar ciclos.
# =====================================================================

import importlib


MODULE_SPECS = {
    "coco_4c": {
        "label": "COCO 4C",
        "menu": "Propiedades del COCO",
        "icon": "vdo_coco.svg",
        "factory": ("vdo_coco_core", "make_coco"),
        "panel": ("vdo_coco_unified_task", "CocoUnifiedTaskPanel"),
        "config": {
            "nombre": "COCO_4C",
            "alto": 720.0,
            "ancho": 600.0,
            "fondo_modulo": 580.0,
            "espesor": 18,
            "tiene_fondo": True,
            "calibre_fondo": 6,
            "profundidad_ranura": 3.0,
            "distancia_borde": 18.0,
            "tapa": "externo",
            "base": "interno",
            "espacios_x": "",
            "espacios_y": "",
            "rotacion": 0.0,
            "anclaje": "inferior_izquierda_frente",
            "lados_vistos": ["frente"],
            "lados_apoyados": ["fondo"],
        },
    },
    "cajon_oculta": {
        "label": "Cajón oculta",
        "menu": "Propiedades del Cajón",
        "icon": "vdo_cajon.svg",
        "factory": ("vdo_cajon_core", "make_cajon"),
        "panel": ("vdo_cajon_task", "CajonTaskPanel"),
        "config": {
            "nombre": "Cajon_Oculta",
            "ancho_libre": 564.0,
            "prof_libre": 560.0,
            "ancho_modulo": 600.0,
            "alto_frente": 225.0,
            "alto_caja": 120.0,
            "grosor_caja": 16,
            "grosor_fondo": 6,
            "grosor_fachada": 18,
            "marca": "blum_tandem",
            "longitud_guia": 0.0,
            "montaje_trasera": "entre_laterales",
            "rotacion": 0.0,
            "anclaje": "inferior_izquierda_frente",
        },
    },
    "panel_estandar": {
        "label": "Panel Estándar",
        "menu": "Propiedades del Panel",
        "icon": "vdo_panel.svg",
        "factory": ("vdo_panel_core", "crear_pieza"),
        "panel": ("vdo_panel_task", "PanelTaskPanel"),
        "config": {
            "nombre": "Panel_Base",
            "etiqueta": "Panel Estándar",
            "orientacion": "horizontal",
            "cantos": {
                "norte": "FX",
                "sur": "FX",
                "este": "RIG",
                "oeste": "FX",
            },
            "material_ref": "melamina_standar",
            "usar_params": True,
            "rotacion": 0.0,
            "anclaje": "inferior_izquierda_frente",
        },
    },
    "panel_fachada": {
        "label": "Panel Fachada",
        "menu": "Propiedades del Panel",
        "icon": "vdo_panel_fachada.svg",
        "factory": ("vdo_panel_core", "crear_pieza"),
        "panel": ("vdo_panel_task", "PanelTaskPanel"),
        "config": {
            "nombre": "Fachada_Principal",
            "etiqueta": "Fachada",
            "orientacion": "vertical",
            "cantos": {
                "norte": "RIG",
                "sur": "RIG",
                "este": "RIG",
                "oeste": "RIG",
            },
            "material_ref": "melamina_standar",
            "usar_params": True,
            "rotacion": 0.0,
            "anclaje": "inferior_izquierda_frente",
        },
    },
    "panel_division": {
        "label": "Panel División",
        "menu": "Propiedades del Panel",
        "icon": "vdo_panel.svg",
        "factory": ("vdo_panel_core", "crear_pieza"),
        "panel": ("vdo_panel_task", "PanelTaskPanel"),
        "config": {
            "nombre": "Division_1",
            "etiqueta": "División",
            "orientacion": "vertical",
            "cantos": {
                "norte": "FX",
                "sur": "FX",
                "este": "FX",
                "oeste": "FX",
            },
            "material_ref": "melamina_standar",
            "usar_params": True,
            "rotacion": 0.0,
            "anclaje": "inferior_izquierda_frente",
        },
    },
}


def _resolver(referencia):
    modulo, atributo = referencia
    mod = importlib.import_module(modulo)
    return getattr(mod, atributo)


def resolver_panel(spec):
    """Resuelve el panel bajo demanda (evita importar GUI en FreeCADCmd)."""
    return _resolver(spec["panel_ref"])


def get_spec(module_key):
    """Devuelve una copia de la spec con la factory resuelta."""
    base = MODULE_SPECS.get(module_key)
    if base is None:
        raise KeyError(f"Módulo VDO desconocido: {module_key}")
    spec = dict(base)
    spec["config"] = dict(base.get("config", {}))
    spec["factory_fn"] = _resolver(base["factory"])
    spec["panel_ref"] = base["panel"]
    return spec


def listar_modulos():
    return sorted(MODULE_SPECS.keys())
