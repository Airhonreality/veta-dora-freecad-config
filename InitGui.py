# -*- coding: utf-8 -*-
# =====================================================================
# InitGui.py - VDO Workbench (cascaron de arranque)
#
# DOS RESTRICCIONES DE FREECAD QUE OBLIGAN ESTA FORMA:
#  1. FreeCAD ejecuta este archivo via exec() SIN definir __file__.
#     -> la ruta se deriva de getUserAppDataDir()/getResourceDir().
#  2. FreeCAD usa exec(code, globals, locals) con dicts DISTINTOS, asi que
#     nada definido aqui es visible desde los metodos de una clase definida
#     aqui (NameError diferido al construir la toolbar).
#     -> las clases viven en VDO/vdo_initgui.py, un modulo importado real.
#
# Por tanto este archivo solo hace: localizar la raiz, sembrar sys.path,
# importar la implementacion y registrarla.
# =====================================================================

import os
import sys

import FreeCAD as App

WB_NAME = "VDO_CarpinteriaParametrica"

_candidatos = [
    os.path.join(App.getUserAppDataDir(), "Mod", WB_NAME),
    os.path.join(App.getResourceDir(), "Mod", WB_NAME),
]
_wb_dir = next((p for p in _candidatos if os.path.isdir(p)), "")

if not _wb_dir:
    App.Console.PrintError(
        "[VDO] No se encontro Mod/%s; el workbench no se registrara.\n" % WB_NAME
    )
else:
    if _wb_dir not in sys.path:
        sys.path.insert(0, _wb_dir)
    try:
        from VDO.vdo_initgui import register
        register()
        App.Console.PrintLog("[VDO] Workbench registrado desde %s\n" % _wb_dir)
    except Exception:
        import traceback
        App.Console.PrintError(
            "[VDO] Fallo al registrar el workbench:\n%s\n" % traceback.format_exc()
        )
