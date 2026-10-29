# -*- coding: utf-8 -*-
# =====================================================================
# vdo_view_base.py
# ViewProvider común para todos los módulos VDO.
#
# Estándar VDO (D13/D17):
#   - Clic derecho → "Propiedades del [Módulo]"
#   - Doble clic → mismo panel
#   - Creación → mismo panel (lo orquesta vdo_creation_flow)
#
# API verificada en FreeCAD 1.1.4:
#   setupContextMenu(self, vobj, menu)   (no getContextMenuItems)
#   doubleClicked(self, vobj)            (no onDoubleClick)
# =====================================================================

import os

import FreeCAD as App

try:
    import FreeCADGui as Gui
except ImportError:  # FreeCADCmd
    Gui = None


class VDOViewProviderBase:
    """Base para ViewProviders de módulos paramétricos VDO."""

    MENU_LABEL = "Propiedades del módulo"
    ICON = None

    def __init__(self, vobj):
        vobj.Proxy = self
        self.Object = vobj.Object
        self.vobj = vobj

    # -----------------------------------------------------------------
    # Ciclo de vida
    # -----------------------------------------------------------------
    def attach(self, vobj):
        self.Object = vobj.Object
        self.vobj = vobj
        return

    def getIcon(self):
        if self.ICON:
            icon_path = os.path.join(App.getUserMacroDir(True), self.ICON)
            if os.path.exists(icon_path):
                return icon_path
        return "Part_Box"

    # -----------------------------------------------------------------
    # Acceso al panel
    # -----------------------------------------------------------------
    def get_panel_class(self):
        raise NotImplementedError(
            "El ViewProvider VDO debe implementar get_panel_class()")

    def _crear_panel(self, obj):
        panel_cls = self.get_panel_class()
        return panel_cls(obj)

    def _abrir_panel(self, obj=None):
        obj = obj or self.Object
        if obj is None or Gui is None:
            return False
        try:
            panel = self._crear_panel(obj)
            Gui.Control.showDialog(panel)
            return True
        except Exception as exc:
            App.Console.PrintError(
                f"[VDO] Error abriendo panel de propiedades: {exc}\n")
            import traceback
            App.Console.PrintError(traceback.format_exc())
            try:
                from PySide import QtGui
                QtGui.QMessageBox.critical(
                    None, "VDO",
                    f"No se pudo abrir el panel de {obj.Name}:\n{exc}")
            except Exception:
                pass
            return False

    # -----------------------------------------------------------------
    # Clic derecho
    # -----------------------------------------------------------------
    def setupContextMenu(self, vobj, menu):
        try:
            action = menu.addAction(self.MENU_LABEL)
            action.triggered.connect(
                lambda checked=False, o=vobj.Object: self._abrir_panel(o))
            return False
        except Exception as exc:
            App.Console.PrintWarning(
                f"[VDO] No se pudo crear el menú contextual: {exc}\n")
            return False

    # -----------------------------------------------------------------
    # Doble clic / edición
    # -----------------------------------------------------------------
    def doubleClicked(self, vobj):
        # Abrir el panel directamente evita que FreeCAD entre/salga del
        # modo edición y cierre el diálogo inmediatamente.
        return self._abrir_panel(vobj.Object)

    def setEdit(self, vobj, mode):
        if mode != 0:
            return False
        if Gui is None:
            return False
        try:
            panel = self._crear_panel(vobj.Object)
            Gui.Control.showDialog(panel)
            return True
        except Exception as exc:
            App.Console.PrintError(
                f"[VDO] Error abriendo editor: {exc}\n")
            import traceback
            App.Console.PrintError(traceback.format_exc())
            return False

    def unsetEdit(self, vobj, mode):
        if Gui is not None:
            try:
                Gui.Control.closeDialog()
            except Exception:
                pass
        return True

    # -----------------------------------------------------------------
    # Compatibilidad
    # -----------------------------------------------------------------
    def claimChildren(self):
        return []

    def dumps(self):
        return None

    def loads(self, state):
        return None


def _es_coco(obj):
    return (hasattr(obj, "VDO_Divisiones")
            or hasattr(obj, "EspaciosX")
            or hasattr(obj, "EspaciosY"))


def _es_cajon(obj):
    return hasattr(obj, "AnchoLibre") and hasattr(obj, "MarcaCorredera")


def _es_zocalo(obj):
    return hasattr(obj, "AltoZocalo") and hasattr(obj, "DistanciaFrente")


def _es_panel(obj):
    return hasattr(obj, "VDO_Orientacion") and hasattr(obj, "Largo")


def diagnostico_viewprovider(obj):
    """Texto de diagnóstico para depurar el proxy de un módulo VDO."""
    if obj is None:
        return "Sin objeto."
    try:
        vp = obj.ViewObject
    except Exception as exc:
        return f"{obj.Name}: sin ViewObject ({exc})"
    proxy = getattr(vp, "Proxy", None)
    metodos = [m for m in ("_abrir_panel", "setupContextMenu",
                           "doubleClicked", "setEdit", "get_panel_class")
               if hasattr(proxy, m)]
    return (f"{obj.Name}: TypeId={obj.TypeId} "
            f"Proxy={type(proxy).__name__} metodos={metodos}")


def reparar_viewprovider(obj):
    """Reinstala el ViewProvider VDO si el objeto perdió su proxy."""
    if obj is None or Gui is None:
        return None
    try:
        vp = obj.ViewObject
    except Exception:
        return None
    if vp is None:
        return None
    proxy = getattr(vp, "Proxy", None)
    if hasattr(proxy, "_abrir_panel") and hasattr(proxy, "get_panel_class"):
        return proxy

    try:
        if _es_coco(obj):
            try:
                from vdo_drag_handles import DragableViewProvider
                return DragableViewProvider(vp)
            except Exception:
                from vdo_coco_core import ViewProviderCoco
                return ViewProviderCoco(vp)
        if _es_cajon(obj):
            from vdo_cajon_core import ViewProviderCajon
            return ViewProviderCajon(vp)
        if _es_zocalo(obj):
            from vdo_zocalo_core import ViewProviderZocalo
            return ViewProviderZocalo(vp)
        if _es_panel(obj):
            from vdo_panel_core import ViewProviderPanel
            return ViewProviderPanel(vp)
    except Exception as exc:
        App.Console.PrintError(
            f"[VDO] No se pudo reparar ViewProvider de {obj.Name}: {exc}\n")
    return None


def abrir_panel_objeto(obj):
    """Abre el panel de cualquier módulo VDO, reparando el proxy si hace falta."""
    if obj is None:
        return False
    proxy = getattr(getattr(obj, "ViewObject", None), "Proxy", None)
    if not hasattr(proxy, "_abrir_panel"):
        proxy = reparar_viewprovider(obj)
    if proxy is not None and hasattr(proxy, "_abrir_panel"):
        return proxy._abrir_panel(obj)

    # Último recurso: panel directo según las propiedades del objeto.
    try:
        if _es_coco(obj):
            from vdo_coco_unified_task import CocoUnifiedTaskPanel
            panel = CocoUnifiedTaskPanel(obj)
        elif _es_cajon(obj):
            from vdo_cajon_task import CajonTaskPanel
            panel = CajonTaskPanel(obj)
        elif _es_zocalo(obj):
            from vdo_zocalo_task import ZocaloTaskPanel
            panel = ZocaloTaskPanel(obj)
        elif _es_panel(obj):
            from vdo_panel_task import PanelTaskPanel
            panel = PanelTaskPanel(obj)
        else:
            App.Console.PrintWarning(
                f"[VDO] {obj.Name} no parece un módulo VDO.\n")
            return False
        Gui.Control.showDialog(panel)
        return True
    except Exception as exc:
        App.Console.PrintError(
            f"[VDO] No se pudo abrir el panel de {obj.Name}: {exc}\n")
        import traceback
        App.Console.PrintError(traceback.format_exc())
        return False
