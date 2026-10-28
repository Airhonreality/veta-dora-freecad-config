# -*- coding: utf-8 -*-
# =====================================================================
# vdo_placement.py
# Colocación interactiva de módulos VDO.
#
# Prioridad:
#   1. Gui.Snapper (Draft): respeta el snap activo del usuario.
#   2. Fallback propio: eventos Coin3D + getPoint/getObjectInfo.
#
# El módulo se crea oculto y aparece al mover el mouse, de modo que
# nunca "salta" al centro del modelo. El clic deposita; Esc cancela.
# =====================================================================

import FreeCAD as App

from vdo_module_props import (
    ANCLAJE_DEFAULT, ancla_local, leer_rotacion, rotacion_z
)

try:
    import FreeCADGui as Gui
except ImportError:  # FreeCADCmd
    Gui = None

try:
    from pivy import coin
except ImportError:
    coin = None


class ColocadorModulo:
    """Herramienta de colocación de un módulo con el mouse."""

    def __init__(self, obj, on_done=None, on_cancel=None, anclaje=None):
        self.obj = obj
        self.on_done = on_done
        self.on_cancel = on_cancel
        self.rot = rotacion_z(leer_rotacion(obj))
        self.ancla = ancla_local(
            obj, anclaje or getattr(obj, "VDO_Anclaje", ANCLAJE_DEFAULT))
        self._medio = None
        self._finalizado = False
        self._visible = False
        self._view = None
        self._callbacks = []
        self._ultimo_punto = None

    # -----------------------------------------------------------------
    # API pública
    # -----------------------------------------------------------------
    def iniciar(self):
        if Gui is None:
            self._cancelar()
            return False
        if not self._hay_vista():
            self._cancelar()
            return False

        try:
            import Draft  # noqa: F401  (inicializa Gui.Snapper)
        except Exception:
            pass

        snapper = getattr(Gui, "Snapper", None)
        if snapper is not None:
            try:
                self._medio = "draft"
                snapper.getPoint(
                    callback=self._on_point,
                    movecallback=self._on_move,
                    title="Colocar módulo",
                )
                self._status(
                    "Mueve el mouse y haz clic para colocar. Esc cancela.")
                return True
            except Exception as exc:
                App.Console.PrintWarning(
                    f"[VDO] Draft Snapper no disponible, usando fallback: "
                    f"{exc}\n")
                self._medio = None

        self._medio = "fallback"
        return self._iniciar_fallback()

    # -----------------------------------------------------------------
    # Draft Snapper
    # -----------------------------------------------------------------
    def _on_move(self, point, snap_info=None):
        if self._finalizado or point is None:
            return
        self._mostrar()
        self._aplicar(point)

    def _on_point(self, point, snap_info=None):
        if self._finalizado:
            return
        if point is None:
            self._cancelar()
            return
        self._mostrar()
        self._aplicar(point)
        self._finalizar()

    # -----------------------------------------------------------------
    # Fallback Coin3D
    # -----------------------------------------------------------------
    def _iniciar_fallback(self):
        try:
            self._view = Gui.ActiveDocument.ActiveView
        except Exception:
            self._view = None
        if self._view is None or coin is None:
            self._cancelar()
            return False
        try:
            self._callbacks = [
                (coin.SoLocation2Event.getClassTypeId(),
                 self._view.addEventCallbackPivy(
                     coin.SoLocation2Event.getClassTypeId(),
                     self._event_move)),
                (coin.SoMouseButtonEvent.getClassTypeId(),
                 self._view.addEventCallbackPivy(
                     coin.SoMouseButtonEvent.getClassTypeId(),
                     self._event_click)),
                (coin.SoKeyboardEvent.getClassTypeId(),
                 self._view.addEventCallbackPivy(
                     coin.SoKeyboardEvent.getClassTypeId(),
                     self._event_key)),
            ]
            self._status(
                "Mueve el mouse y haz clic para colocar. Esc cancela.")
            return True
        except Exception as exc:
            App.Console.PrintError(
                f"[VDO] No se pudo iniciar la colocación: {exc}\n")
            self._cancelar()
            return False

    def _event_move(self, event_cb):
        if self._finalizado or self._view is None:
            return
        try:
            pos = event_cb.getEvent().getPosition()
            punto = self._punto_bajo_cursor(pos)
        except Exception:
            return
        if punto is not None:
            self._ultimo_punto = punto
            self._mostrar()
            self._aplicar(punto)

    def _event_click(self, event_cb):
        if self._finalizado or coin is None:
            return
        try:
            ev = event_cb.getEvent()
            if (ev.getButton() == coin.SoMouseButtonEvent.BUTTON1
                    and ev.getState() == coin.SoMouseButtonEvent.DOWN):
                punto = self._ultimo_punto
                if punto is None:
                    punto = self._punto_bajo_cursor(ev.getPosition())
                if punto is not None:
                    self._aplicar(punto)
                    self._finalizar()
        except Exception:
            pass

    def _event_key(self, event_cb):
        if self._finalizado or coin is None:
            return
        try:
            if event_cb.getEvent().getKey() == coin.SoKeyboardEvent.ESCAPE:
                self._cancelar()
        except Exception:
            pass

    def _punto_bajo_cursor(self, pos):
        pos = (pos[0], pos[1])
        try:
            info = self._view.getObjectInfo(pos)
        except Exception:
            info = None
        if info and all(k in info for k in ("x", "y", "z")):
            return App.Vector(info["x"], info["y"], info["z"])
        try:
            return self._view.getPoint(pos)
        except Exception:
            return None

    # -----------------------------------------------------------------
    # Estado
    # -----------------------------------------------------------------
    def _hay_vista(self):
        try:
            return Gui.ActiveDocument is not None and \
                Gui.ActiveDocument.ActiveView is not None
        except Exception:
            return False

    def _mostrar(self):
        if self._visible:
            return
        try:
            self.obj.ViewObject.Visibility = True
        except Exception:
            pass
        self._visible = True

    def _aplicar(self, punto):
        base = punto - self.rot.multVec(self.ancla)
        self.obj.Placement = App.Placement(base, self.rot)

    def _finalizar(self):
        if self._finalizado:
            return
        self._finalizado = True
        self._quitar_callbacks()
        self._status("")
        if self.on_done:
            self.on_done()

    def _cancelar(self):
        if self._finalizado:
            return
        self._finalizado = True
        self._quitar_callbacks()
        if self._medio == "draft" and Gui is not None:
            try:
                Gui.Snapper.getPoint()
            except Exception:
                pass
        self._status("")
        if self.on_cancel:
            self.on_cancel()

    def _quitar_callbacks(self):
        if self._view is None:
            self._callbacks = []
            return
        for tipo, callback in self._callbacks:
            try:
                self._view.removeEventCallbackPivy(tipo, callback)
            except Exception:
                pass
        self._callbacks = []

    def _status(self, mensaje):
        try:
            mw = Gui.getMainWindow()
            if mw is not None:
                mw.statusBar().showMessage(mensaje)
        except Exception:
            pass


def iniciar_colocacion(obj, on_done=None, on_cancel=None, anclaje=None):
    """Punto de entrada único para colocar un módulo VDO."""
    if obj is None:
        if on_cancel:
            on_cancel()
        return False
    return ColocadorModulo(
        obj, on_done=on_done, on_cancel=on_cancel, anclaje=anclaje
    ).iniciar()
