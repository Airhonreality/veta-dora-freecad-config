# -*- coding: utf-8 -*-
# =====================================================================
# vdo_manifest.py
# Cargador de manifesto JSON para VDO
# PRINCIPIO: JSON es la fuente única de verdad
# Carga FRESCA del JSON cada acceso (sin caché de módulo)
# =====================================================================

import json
import os

def _obtener_json():
    """Carga vdo_manifest.json directamente (sin caché)."""
    macro_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(macro_dir, "vdo_manifest.json")

    if not os.path.exists(json_path):
        raise FileNotFoundError(f"vdo_manifest.json no encontrado en: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Cargar JSON al importar (pero es una función, no una constante cacheada)
VDO_MANIFEST = _obtener_json()
