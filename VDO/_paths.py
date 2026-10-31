# -*- coding: utf-8 -*-
# =====================================================================
# VDO/_paths.py — Sistema único de rutas del workbench
# Todas las rutas se derivan de __file__, nunca de getUserMacroDir()
# =====================================================================

from __future__ import annotations

import json
import os
from pathlib import Path

# Este archivo vive en  <raiz_wb>/VDO/_paths.py
# Por tanto: parent  -> .../VDO      (paquete Python)
#            parent.parent -> .../VDO_CarpinteriaParametrica (raiz del workbench)
VDO_DIR = Path(__file__).resolve().parent
WB_DIR = VDO_DIR.parent

# Subdirectorios canónicos
MATH_DIR = VDO_DIR / "core"      # antes math/, renombrado para no colisionar con math de Python
HUB_DIR = VDO_DIR / "hub"
CAD_OBJECTS_DIR = VDO_DIR / "cad" / "objects"
CAD_VIEWS_DIR = VDO_DIR / "cad" / "views"
UI_DIR = VDO_DIR / "ui"
CAM_DIR = VDO_DIR / "cam"
RESOURCES_DIR = VDO_DIR / "resources"
ICONS_DIR = RESOURCES_DIR / "icons"
TEMPLATES_DIR = RESOURCES_DIR / "templates"

# Archivos de manifiesto en la raíz del workbench
PACKAGE_XML = WB_DIR / "package.xml"
METADATA_TXT = WB_DIR / "metadata.txt"
INIT_PY = WB_DIR / "Init.py"
INIT_GUI_PY = WB_DIR / "InitGui.py"


def get_wb_dir() -> Path:
    """Devuelve la ruta raíz del workbench (donde está Init.py / package.xml)."""
    return WB_DIR


def get_vdo_dir() -> Path:
    """Devuelve la ruta del paquete VDO/."""
    return VDO_DIR


def get_icon_path(nombre: str) -> str:
    """Devuelve la ruta absoluta a un icono en VDO/resources/icons/."""
    return str(ICONS_DIR / nombre)


def get_template_path(nombre: str) -> str:
    """Devuelve la ruta absoluta a una plantilla SVG en VDO/resources/templates/."""
    return str(TEMPLATES_DIR / nombre)


def get_template_area_util() -> dict:
    """Devuelve el diccionario de área útil de la plantilla VDO (vdo_template_a3.json).

    El motor de dossier lee esto para saber cuánto espacio tienen las vistas
    sin solapar el cajetín ni salirse del margen. Prohibido hardcodear
    220×277 (eso es del cajetín ISO, no del VDO).
    """
    json_path = TEMPLATES_DIR / "vdo_template_a3.json"
    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ensure_sys_path() -> None:
    """Añade el directorio raíz del workbench a sys.path si no está."""
    wb_str = str(WB_DIR)
    import sys
    if wb_str not in sys.path:
        sys.path.insert(0, wb_str)
