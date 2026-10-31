# -*- coding: utf-8 -*-
# =====================================================================
# Init.py - VDO Workbench
# Ejecutado por FreeCAD (consola y GUI) al arrancar, para cada Mod/.
#
# PROHIBIDO usar __file__ en este archivo: FreeCAD lo ejecuta via exec()
# con __name__ == "__main__" y SIN __file__ definido. Usarlo lanza
# NameError y aborta la carga del workbench antes de registrarlo.
# El patron canonico (usado por BIM, Draft, CAM) es derivar la ruta de
# FreeCAD.getUserAppDataDir() / FreeCAD.getResourceDir().
# =====================================================================

import os
import sys

import FreeCAD

WB_NAME = "VDO_CarpinteriaParametrica"

_candidatos = [
    os.path.join(FreeCAD.getUserAppDataDir(), "Mod", WB_NAME),
    os.path.join(FreeCAD.getResourceDir(), "Mod", WB_NAME),
]
VDO_WB_DIR = next((p for p in _candidatos if os.path.isdir(p)), "")

if not VDO_WB_DIR:
    FreeCAD.Console.PrintError(
        "[VDO] No se encontro Mod/%s en %s\n" % (WB_NAME, _candidatos)
    )
else:
    if VDO_WB_DIR not in sys.path:
        sys.path.insert(0, VDO_WB_DIR)

    if os.path.isdir(os.path.join(VDO_WB_DIR, "VDO")):
        FreeCAD.Console.PrintLog("[VDO] Workbench localizado en %s\n" % VDO_WB_DIR)
    else:
        FreeCAD.Console.PrintError(
            "[VDO] Falta el paquete VDO/ dentro de %s\n" % VDO_WB_DIR
        )
