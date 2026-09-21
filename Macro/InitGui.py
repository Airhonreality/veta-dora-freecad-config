# -*- coding: utf-8 -*-
# =====================================================================
# InitGui.py - VDO: toolbar con comandos paramétricos
# Se ejecuta automáticamente al iniciar FreeCAD con GUI
# =====================================================================

import os
import sys
import FreeCAD as App
import FreeCADGui as Gui

_macro_dir = App.getUserMacroDir(True)
if _macro_dir not in sys.path:
    sys.path.insert(0, _macro_dir)

# Verificar que los archivos VDO existen
_vdo_files = ["vdo_panel_core.py", "vdo_coco_core.py", "vdo_manifest.py"]
_vdo_installed = all(os.path.exists(os.path.join(_macro_dir, f)) for f in _vdo_files)

print("[VDO InitGui] macro_dir:", _macro_dir, "installed:", _vdo_installed)

if _vdo_installed:

    # ============================================================
    # 1. Definir comandos
    # ============================================================

    class CmdCrearHoja:
        def Activated(self):
            exec(open(os.path.join(_macro_dir, "VDO_Crear_Hoja_Melamina.FCMacro")).read())
        def GetResources(self):
            return {"Pixmap": os.path.join(_macro_dir, "vdo_workbench.svg"),
                    "MenuText": "Crear Hoja", "ToolTip": "Crear hoja de melamina"}

    class CmdPanelEstandar:
        def Activated(self):
            exec(open(os.path.join(_macro_dir, "vdo_panel_estandar.FCMacro")).read())
        def GetResources(self):
            return {"Pixmap": os.path.join(_macro_dir, "vdo_panel_estandar.svg"),
                    "MenuText": "Panel Estándar", "ToolTip": "Panel estándar paramétrico"}

    class CmdPanelFachada:
        def Activated(self):
            exec(open(os.path.join(_macro_dir, "vdo_panel_fachada.FCMacro")).read())
        def GetResources(self):
            return {"Pixmap": os.path.join(_macro_dir, "vdo_panel_fachada.svg"),
                    "MenuText": "Panel Fachada", "ToolTip": "Panel fachada paramétrico"}

    class CmdCoco4C:
        def Activated(self):
            exec(open(os.path.join(_macro_dir, "vdo_coco_4c.FCMacro")).read())
        def GetResources(self):
            return {"Pixmap": os.path.join(_macro_dir, "vdo_coco.svg"),
                    "MenuText": "COCO 4C", "ToolTip": "Cajón 4 caras paramétrico"}

    # ============================================================
    # 2. Registrar comandos
    # ============================================================

    Gui.addCommand("VDO_CrearHoja", CmdCrearHoja())
    Gui.addCommand("VDO_PanelEstandar", CmdPanelEstandar())
    Gui.addCommand("VDO_PanelFachada", CmdPanelFachada())
    Gui.addCommand("VDO_Coco4C", CmdCoco4C())

    # ============================================================
    # 3. Workbench con toolbar
    # ============================================================

    class VDO_Workbench(Gui.Workbench):
        MenuText = "VDO - Muebles Paramétricos"
        ToolTip = "Motor paramétrico Veta de Oro"
        Icon = os.path.join(_macro_dir, "vdo_workbench.svg")

        def Initialize(self):
            cmds = ["VDO_CrearHoja", "VDO_PanelEstandar",
                    "VDO_PanelFachada", "VDO_Coco4C"]
            self.appendToolbar("VDO", cmds)

        def Activated(self):
            pass

        def Deactivated(self):
            pass

        def GetClassName(self):
            return "Gui::PythonWorkbench"

    Gui.addWorkbench(VDO_Workbench())
