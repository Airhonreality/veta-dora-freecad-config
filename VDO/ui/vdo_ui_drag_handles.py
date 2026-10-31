# -*- coding: utf-8 -*-
# =====================================================================
# vdo_drag_handles.py
# Sistema de handles interactivos 3D para redimensionamiento COCO
# Fase 1: Visualización de handles
# Fase 2: Detección de mouse
# Fase 3: Mapping drag 3D → parámetros
# =====================================================================

import FreeCAD as App
import FreeCADGui as Gui
from pivy import coin
import math

from VDO.cad.views.vdo_cad_view_base import VDOViewProviderBase


class DragableViewProvider(VDOViewProviderBase):
    """ViewProvider del COCO con handles 3D + panel unificado."""

    MENU_LABEL = "Propiedades del COCO"
    ICON = "vdo_coco.svg"

    def __init__(self, vobj):
        super().__init__(vobj)

        # Estado del sistema de handles
        self._handles_enabled = False
        self._handle_nodes = {}  # {nombre → SoNode}
        self._drag_state = None  # {handle_id, inicio_pos, inicio_valor}
        self._hover_handle = None  # Handle actual hovereado
        self._root = None  # Grupo raíz Coin3D para handles

        # Colores
        self.COLOR_INACTIVE = coin.SoMaterial()
        self.COLOR_INACTIVE.diffuseColor.setValue(0.2, 0.6, 1.0)  # Azul

        self.COLOR_HOVER = coin.SoMaterial()
        self.COLOR_HOVER.diffuseColor.setValue(1.0, 0.8, 0.0)  # Amarillo

        self.COLOR_ACTIVE = coin.SoMaterial()
        self.COLOR_ACTIVE.diffuseColor.setValue(1.0, 0.2, 0.2)  # Rojo

    # =====================================================================
    # FASE 1: VISUALIZACIÓN DE HANDLES
    # =====================================================================

    def _crear_handles_visuales(self):
        """Crea las esferas visuales de los 3 handles principales."""
        if self._root is not None:
            return  # Ya existen

        fp = self.Object
        try:
            alto = float(fp.Alto)
            ancho = float(fp.Ancho)
            fondo = float(fp.FondoModulo)
        except (AttributeError, TypeError):
            App.Console.PrintWarning(
                "[VDO] No se pudo obtener dimensiones para crear handles.\n")
            return

        # Crear nodo raíz para handles
        self._root = coin.SoSeparator()

        # Definir los 3 handles principales en esquinas
        # Handle X: esquina superior-derecha (controla Ancho)
        handle_x = {
            "nombre": "Handle_X",
            "pos": App.Vector(ancho, 0, alto),
            "eje": "X",
            "propiedad": "Ancho"
        }

        # Handle Y: esquina superior-frente (controla FondoModulo)
        handle_y = {
            "nombre": "Handle_Y",
            "pos": App.Vector(0, fondo, alto),
            "eje": "Y",
            "propiedad": "FondoModulo"
        }

        # Handle Z: esquina superior-izquierda (controla Alto)
        handle_z = {
            "nombre": "Handle_Z",
            "pos": App.Vector(0, 0, alto),
            "eje": "Z",
            "propiedad": "Alto"
        }

        handles_def = [handle_x, handle_y, handle_z]

        # Crear esferas para cada handle
        for h_def in handles_def:
            sphere_sep = coin.SoSeparator()

            # Material inicial (azul)
            material = coin.SoMaterial()
            material.diffuseColor.setValue(0.2, 0.6, 1.0)
            sphere_sep.addChild(material)

            # Transformación de posición
            transform = coin.SoTransform()
            transform.translation.setValue(h_def["pos"].x,
                                          h_def["pos"].y,
                                          h_def["pos"].z)
            sphere_sep.addChild(transform)

            # Esfera visualización (radio ~40mm - más visible)
            sphere = coin.SoSphere()
            sphere.radius.setValue(40.0)
            sphere_sep.addChild(sphere)

            # Guardar referencias
            self._handle_nodes[h_def["nombre"]] = {
                "separator": sphere_sep,
                "transform": transform,
                "material": material,
                "def": h_def
            }

            self._root.addChild(sphere_sep)

        # Agregar el grupo de handles al RootNode del ViewProvider
        try:
            self.vobj.RootNode.addChild(self._root)
            App.Console.PrintMessage("[VDO] Handles visuales creados.\n")
        except Exception as e:
            App.Console.PrintError(
                f"[VDO] Error agregando handles a RootNode: {e}\n")

    def _destruir_handles_visuales(self):
        """Destruye las esferas visuales de los handles."""
        if self._root is None:
            return

        try:
            self.vobj.RootNode.removeChild(self._root)
        except Exception as e:
            App.Console.PrintWarning(
                f"[VDO] Error removiendo handles: {e}\n")

        self._root.removeAllChildren()
        self._root = None
        self._handle_nodes.clear()
        self._hover_handle = None

    def _actualizar_posicion_handles(self):
        """Actualiza la posición de los handles según propiedades actuales."""
        if self._root is None or not self._handle_nodes:
            return

        fp = self.Object
        try:
            alto = float(fp.Alto)
            ancho = float(fp.Ancho)
            fondo = float(fp.FondoModulo)
        except (AttributeError, TypeError):
            return

        # Actualizar posiciones
        nuevas_pos = {
            "Handle_X": App.Vector(ancho, 0, alto),
            "Handle_Y": App.Vector(0, fondo, alto),
            "Handle_Z": App.Vector(0, 0, alto)
        }

        for nombre, nueva_pos in nuevas_pos.items():
            if nombre in self._handle_nodes:
                transform = self._handle_nodes[nombre]["transform"]
                transform.translation.setValue(nueva_pos.x,
                                              nueva_pos.y,
                                              nueva_pos.z)

    # =====================================================================
    # FASE 2: DETECCIÓN DE MOUSE (stub por ahora)
    # =====================================================================

    def _on_mouse_press(self, event_data):
        """Intercepta click de mouse en viewport."""
        # TODO: Implementar raycast para detectar handle clickeado
        pass

    def _on_mouse_move(self, event_data):
        """Intercepta movimiento de mouse en viewport."""
        # TODO: Implementar hover detection
        pass

    def _on_mouse_release(self, event_data):
        """Finaliza drag."""
        # TODO: Finalizar operación
        pass

    # =====================================================================
    # INTEGRACIONES CON VIEWPROVIDER ESTÁNDAR
    # =====================================================================

    def get_panel_class(self):
        from VDO.ui.vdo_ui_coco_task import CocoUnifiedTaskPanel
        return CocoUnifiedTaskPanel

    def setEdit(self, vobj, mode):
        """Activar edición: handles visuales + panel unificado."""
        if mode != 0:
            return False
        try:
            self._crear_handles_visuales()
            self._handles_enabled = True
        except Exception as exc:
            App.Console.PrintWarning(
                f"[VDO] No se pudieron crear los handles: {exc}\n")
        return super().setEdit(vobj, mode)

    def unsetEdit(self, vobj, mode):
        """Desactivar edición: ocultar handles + cerrar panel."""
        try:
            self._destruir_handles_visuales()
            self._handles_enabled = False
        except Exception as exc:
            App.Console.PrintWarning(
                f"[VDO] No se pudieron destruir los handles: {exc}\n")
        return super().unsetEdit(vobj, mode)

    def onChanged(self, vobj, prop):
        """Reaccionar a cambios de propiedades."""
        if prop in ["Alto", "Ancho", "FondoModulo"] and self._handles_enabled:
            self._actualizar_posicion_handles()

    def getDisplayModes(self, obj):
        """Modos de visualización disponibles."""
        return ["Flat Lines", "Shading", "Wireframe", "Handles"]

    def getDefaultDisplayMode(self):
        """Modo por defecto."""
        return "Flat Lines"

