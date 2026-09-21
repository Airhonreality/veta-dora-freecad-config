# -*- coding: utf-8 -*-
# =====================================================================
# Init.py
# Inicializador automático VDO para FreeCAD
# Se ejecuta AUTOMÁTICAMENTE cuando FreeCAD arranca
# =====================================================================

import os
import sys
import FreeCAD as App

# Obtener ruta de macros
_macro_dir = App.getUserMacroDir(True)

# Agregar ruta al sys.path si no existe
if _macro_dir not in sys.path:
    sys.path.insert(0, _macro_dir)

# Verificar si VDO ya está instalado
_vdo_files = ["vdo_panel_core.py", "vdo_coco_core.py", "vdo_manifest.py"]
_vdo_installed = all(os.path.exists(os.path.join(_macro_dir, f)) for f in _vdo_files)

if _vdo_installed:
    print("[VDO] Sistema VDO detectado en:", _macro_dir)
else:
    print("[VDO] Sistema VDO no encontrado. Ejecute vdo_install.py para instalar.")
