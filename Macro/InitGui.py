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

# Asegurar que los SVG VDO viven en la raíz de macros y que Qt los ve.
try:
    from vdo_toolbar_inject import preparar_iconos, registrar_ruta_iconos
    preparar_iconos()
    registrar_ruta_iconos(_macro_dir)
except Exception as _icon_exc:
    print("[VDO InitGui] Aviso iconos:", _icon_exc)

# Verificar que los archivos VDO existen
_vdo_files = [
    "vdo_panel_core.py", "vdo_coco_core.py", "vdo_manifest.py",
    "vdo_reengrose.py", "vdo_zocalo_core.py",
]
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

    class CmdPanelDivision:
        def Activated(self):
            exec(open(os.path.join(_macro_dir, "vdo_panel_division.FCMacro")).read())
        def GetResources(self):
            return {"Pixmap": os.path.join(_macro_dir, "vdo_panel.svg"),
                    "MenuText": "Panel División", "ToolTip": "Panel divisor vertical paramétrico"}

    class CmdZocalo:
        def Activated(self):
            exec(open(os.path.join(_macro_dir, "vdo_zocalo.FCMacro")).read())
        def GetResources(self):
            return {"Pixmap": os.path.join(_macro_dir, "vdo_zocalo.svg"),
                    "MenuText": "Zócalo", "ToolTip": "Zócalo paramétrico de base"}

    class CmdEditarVDO:
        def Activated(self):
            exec(open(os.path.join(_macro_dir, "vdo_editar_vdo.FCMacro")).read())
        def GetResources(self):
            return {"Pixmap": os.path.join(_macro_dir, "vdo_workbench.svg"),
                    "MenuText": "Propiedades VDO",
                    "ToolTip": "Abrir el panel del módulo VDO seleccionado"}

    class CmdInspectorVDO:
        def Activated(self):
            from vdo_universal_inspector import obtener_o_crear_dock_inspector
            dock = obtener_o_crear_dock_inspector()
            if dock is not None:
                dock.setVisible(not dock.isVisible())
                if dock.isVisible():
                    dock.raise_()
        def GetResources(self):
            return {"Pixmap": os.path.join(_macro_dir, "vdo_workbench.svg"),
                    "MenuText": "Inspector VDO",
                    "ToolTip": "Mostrar / ocultar el Inspector Universal VDO lateral"}

    # ============================================================
    # 2. Registrar comandos
    # ============================================================

    Gui.addCommand("VDO_CrearHoja", CmdCrearHoja())
    Gui.addCommand("VDO_PanelEstandar", CmdPanelEstandar())
    Gui.addCommand("VDO_PanelFachada", CmdPanelFachada())
    Gui.addCommand("VDO_Coco4C", CmdCoco4C())
    Gui.addCommand("VDO_PanelDivision", CmdPanelDivision())
    Gui.addCommand("VDO_Zocalo", CmdZocalo())
    Gui.addCommand("VDO_Editar", CmdEditarVDO())
    Gui.addCommand("VDO_Inspector", CmdInspectorVDO())

    # ============================================================
    # 3. Workbench con toolbar
    # ============================================================

    class VDO_Workbench(Gui.Workbench):
        MenuText = "VDO - Muebles Paramétricos"
        ToolTip = "Motor paramétrico Veta de Oro"
        Icon = os.path.join(_macro_dir, "vdo_workbench.svg")

        def Initialize(self):
            cmds = ["VDO_CrearHoja", "VDO_PanelEstandar",
                    "VDO_PanelFachada", "VDO_Coco4C", "VDO_PanelDivision",
                    "VDO_Zocalo", "VDO_Editar", "VDO_Inspector"]
            self.appendToolbar("VDO", cmds)
            self.appendMenu("VDO", cmds)

        def Activated(self):
            try:
                from vdo_universal_inspector import obtener_o_crear_dock_inspector
                dock = obtener_o_crear_dock_inspector()
                if dock is not None:
                    dock.show()
                    dock.raise_()
            except Exception as exc:
                print("[VDO Workbench] Aviso al activar dock inspector:", exc)

        def Deactivated(self):
            pass

        def GetClassName(self):
            return "Gui::PythonWorkbench"

    Gui.addWorkbench(VDO_Workbench())

    # Inicializar el DockWidget permanente si FreeCAD arrancó con interfaz gráfica
    try:
        if getattr(App, "GuiUp", False):
            from vdo_universal_inspector import obtener_o_crear_dock_inspector
            _dock = obtener_o_crear_dock_inspector()
            if _dock is not None:
                _dock.show()
    except Exception as _dock_err:
        print("[VDO InitGui] Aviso inicializando dock inspector:", _dock_err)
