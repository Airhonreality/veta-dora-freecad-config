# -*- coding: utf-8 -*-
# =====================================================================
# vdo_shared_manifest.py
# Cargador de manifesto JSON para VDO
# PRINCIPIO: JSON es la fuente única de verdad.
# OJO: VDO_MANIFEST se construye UNA VEZ al importar el módulo; el
# import system de Python lo cachea como cualquier constante. Para
# releer el JSON en caliente hay que llamar a _obtener_json().
# =====================================================================

import json
import os

def _obtener_json():
    """Lee vdo_manifest.json del disco en cada llamada.

    La ruta se toma de VDO._paths, unica fuente de verdad, en vez de
    componerla desde __file__: este modulo se movio a VDO/shared/ y el
    JSON sigue viviendo en la raiz del paquete VDO/.
    """
    from VDO._paths import VDO_DIR
    json_path = str(VDO_DIR / "vdo_manifest.json")

    if not os.path.exists(json_path):
        raise FileNotFoundError(f"vdo_manifest.json no encontrado en: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Instantánea al importar. Es una constante cacheada: relee con
# _obtener_json() si necesitas el estado actual del archivo.
VDO_MANIFEST = _obtener_json()
