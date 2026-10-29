# -*- coding: utf-8 -*-
# =====================================================================
# vdo_inspector_dock.py
# Dock lateral permanente del Inspector Universal — Sistema VDO (FreeCAD).
#
# Proporciona el contenedor QDockWidget permanente para alojar el
# Inspector Universal Consolidado en el panel lateral de FreeCAD.
# =====================================================================

import os
import FreeCAD as App

try:
    import FreeCADGui as Gui
except ImportError:  # pragma: no cover
    Gui = None

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:  # pragma: no cover
    try:
        from PySide2 import QtCore, QtGui, QtWidgets
    except ImportError:
        from PySide import QtCore, QtGui, QtWidgets

from vdo_universal_inspector import (
    VDOUniversalInspectorWidget,
    PAGE_CHASIS,
    PAGE_VANO,
    PAGE_PIEZA,
    PAGE_CIERRE,
)


class VDOInspectorDockWidget(QtWidgets.QDockWidget):
    """QDockWidget lateral permanente de FreeCAD para el Inspector VDO."""

    def __init__(self, parent=None):
        super().__init__("VDO Inspector Universal", parent)
        self.setObjectName("VDOUniversalInspectorDock")
        self.setAllowedAreas(
            QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)

        self.inspector = VDOUniversalInspectorWidget(self)
        self.setWidget(self.inspector)

    def closeEvent(self, event):
        if self.inspector is not None:
            try:
                self.inspector.cerrar_inspector()
            except Exception:
                pass
        super().closeEvent(event)


def obtener_o_crear_dock_inspector(mw=None):
    """
    Crea o recupera el QDockWidget lateral derecho permanente en FreeCAD GUI
    con VDOUniversalInspectorWidget consolidado.
    """
    if Gui is None or not getattr(App, "GuiUp", False):
        return None

    if mw is None:
        try:
            mw = Gui.getMainWindow()
        except Exception:
            mw = None
    if mw is None:
        return None

    dock = mw.findChild(QtWidgets.QDockWidget, "VDOUniversalInspectorDock")
    if dock is None:
        try:
            dock = VDOInspectorDockWidget(mw)
            mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
        except Exception as exc:
            App.Console.PrintError(
                f"[VDO] Error creando DockWidget Inspector: {exc}\n")
            return None
    return dock


__all__ = [
    "VDOInspectorDockWidget",
    "obtener_o_crear_dock_inspector",
    "VDOUniversalInspectorWidget",
    "PAGE_CHASIS",
    "PAGE_VANO",
    "PAGE_PIEZA",
    "PAGE_CIERRE",
]
