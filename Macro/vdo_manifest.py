# -*- coding: utf-8 -*-
# =====================================================================
# vdo_manifest.py
# Contrato de dependencias globales del taller Veta de Oro (VDO).
# Fuente única de la verdad: hojas, alias, valores y dependencias.
# No contiene lógica: solo datos (exportable posteriormente a JSON/ERP).
# =====================================================================

VDO_MANIFEST = {
    "version": "1.6.0",
    "taller": "Veta de Oro",
    "unidades": "mm",

    # --- Interfaz UI (Workbench VDO - Muebles Paramétricos) ------------
    # El InitGui.py lee esta lista para construir la barra de herramientas.
    "modulos_ui": [
        {
            "id": "VDO_PanelEstandar",
            "label": "Panel Estándar",
            "macro": "vdo_panel_estandar",
            "icono": "vdo_panel_estandar.svg",
        },
        {
            "id": "VDO_PanelFachada",
            "label": "Panel Fachada",
            "macro": "vdo_panel_fachada",
            "icono": "vdo_panel_fachada.svg",
        },
        {
            "id": "VDO_COCO_4C",
            "label": "COCO 4C",
            "macro": "vdo_coco_4c",
            "icono": "vdo_coco.svg",
        },
    ],

    # --- Capa Global (Reglas de Taller) --------------------------------
    "capa_global": {
        "hoja": "Params_Melamina",
        "parametros": {
            "espesor": {
                "valor": 18,
                "descripcion": "Espesor nominal del tablero melamínico",
            },
            "canto_grueso": {
                "valor": 2,
                "descripcion": "Espesor de cinta de canto para despiece",
            },
            "ranura_fondo": {
                "valor": 3,
                "descripcion": "Profundidad de ranura para trasera",
            },
        },
    },

    # --- Capa Local (Contenedores y Módulos) ---------------------------
    "capa_local": {
        "hoja": "Params",
        "parametros": {
            "alto": {
                "valor": 720,
                "descripcion": "Alto total del módulo (mm)",
            },
            "ancho": {
                "valor": 600,
                "descripcion": "Ancho total del módulo (mm)",
            },
            "fondo_modulo": {
                "valor": 580,
                "descripcion": "Profundidad total del módulo (mm)",
            },
            "espesor": {
                "valor": 18,
                "descripcion": "Espesor estándar del tablero (mm)",
            },
        },
    },

    # --- Configuración del Fondo (Respaldo) -----------------------------
    "fondo": {
        "habilitado": True,
        "calibre": 6,
        "profundidad_ranura": 3,
        "distancia_borde": 18,
    },

    # --- Configuración Estructural (Tapa y Base) ------------------------
    # "externo": tapa/base van POR ENCIMA/DEBAJO de los laterales
    # "interno": tapa/base van ENTRE los laterales
    "estructura": {
        "tapa": "externo",
        "base": "interno",
    },

    # --- Materiales (extensible) ----------------------------------------
    "materiales": {
        "melamina": {
            "espesores": [18, 25],
            "presentaciones": "2440 x 1830",
        },
    },

    # --- Dependencias del sistema --------------------------------------
    "dependencias": {
        "hojas_obligatorias": ["Params_Melamina", "Params"],
        "macros": [
            "vdo_manifest.py",
            "vdo_guardian.py",
            "vdo_panel_core.py",
            "vdo_spaces.py",
            "vdo_coco_spaces.py",
            "vdo_coco_core.py",
            "vdo_coco_task.py",
            "vdo_coco_spaces_task.py",
            "vdo_panel_estandar.FCMacro",
            "vdo_panel_fachada.FCMacro",
            "vdo_coco_4c.FCMacro",
            "VDO_Crear_Hoja_Melamina.FCMacro",
        ],
        "documentacion": [
            "PROGRESO_VDO.md",
            "CONTEXTO_TECNICO_VDO.md",
        ],
        "workbench": [
            "Mod/VDO_Workbench/InitGui.py",
            "Mod/VDO_Workbench/Init.py",
            "Mod/VDO_Workbench/package.xml",
        ],
    },
}