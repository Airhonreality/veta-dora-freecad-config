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
            from VDO._paths import get_icon_path
            icon_path = get_icon_path(self.ICON)
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
        # Abre directamente el diálogo de parámetros del objeto
        return self._abrir_panel(vobj.Object)

    def setEdit(self, vobj, mode):
        if mode != 0 or Gui is None:
            return False
        return self._abrir_panel(vobj.Object)

    def unsetEdit(self, vobj, mode):
        if Gui is not None:
            try:
                Gui.Control.closeDialog()
            except Exception:
                pass
        return True

    # -----------------------------------------------------------------
    # Borrado (Axioma T6)
    # -----------------------------------------------------------------
    def onDelete(self, vobj, subelements):
        """Delega el borrado en cascada al proxy de datos del módulo.

        FreeCAD invoca onDelete() en el proxy del VIEWPROVIDER, no en el
        del objeto de datos. Los módulos VDO implementan su cascada en
        CocoFeature.onDelete() / PanelFeature.onDelete() siguiendo el
        ejemplo de docs/02 §2.2, que los coloca en la clase de datos; sin
        este puente nunca se ejecutaban y borrar un COCO dejaba todos sus
        paneles huérfanos en el documento.
        """
        try:
            obj = getattr(vobj, "Object", None) or self.Object
            proxy = getattr(obj, "Proxy", None)
            if proxy is not None and hasattr(proxy, "onDelete"):
                return bool(proxy.onDelete(obj, subelements))
        except Exception as exc:
            App.Console.PrintWarning(
                f"[VDO] Borrado en cascada incompleto: {exc}\n")
        return True

    # -----------------------------------------------------------------
    # Árbol (Axioma T4)
    # -----------------------------------------------------------------
    def claimChildren(self):
        """Reflejo visual de la jerarquía de datos (fp.Hijos).

        Implementado en la BASE a proposito. ViewProviderCoco lo define,
        pero make_coco() instala preferentemente DragableViewProvider, que
        no lo hacia: el COCO salia sin hijos en el arbol y sus 5 paneles de
        carcasa aparecian sueltos en la raiz del documento.

        No se sobrescribe claimChildren3D() (C-12): la seleccion y el
        resaltado 3D los sigue gestionando Coin3D de forma nativa.
        """
        if not App.GuiUp:
            return []
        obj = getattr(self, "Object", None)
        if obj is None:
            return []
        hijos = getattr(obj, "Hijos", None) or []
        return [h for h in hijos if h is not None]

    def dumps(self):
        return None

    def loads(self, state):
        return None


# =====================================================================
# Identificacion de modulos
# =====================================================================
# Aqui vivian cuatro predicados por duck-typing:
#
#   def _es_coco(obj):   return hasattr(obj, "VDO_Divisiones") or ...
#   def _es_cajon(obj):  return hasattr(obj, "AnchoLibre") and \
#                               hasattr(obj, "MarcaCorredera")
#   def _es_zocalo(obj): ...
#   def _es_panel(obj):  ...
#
# Tres problemas:
#   1. El tipo del objeto se ADIVINABA mirando si tenia tal o cual
#      dimension. Dos modulos futuros con medidas parecidas colisionan.
#   2. Solo habia cuatro para seis modulos: PUERTA y TAMBOR no tenian
#      predicado, asi que no se podian reparar ni abrir.
#   3. Cada uno alimentaba una cadena de `if` que habia que ampliar a
#      mano en reparar_viewprovider() y en abrir_panel_objeto().
#
# Ahora el tipo lo dice la propiedad testigo VDO_Modulo y la clase del
# ViewProvider y del panel salen del catalogo. Dar de alta un modulo ya
# no obliga a tocar este archivo.

def modulo_de(obj):
    """ModuloSpec al que pertenece `obj`, o None."""
    from VDO.hub.vdo_hub_registry import resolver_modulo
    return resolver_modulo(obj)


def es_modulo_vdo(obj):
    return modulo_de(obj) is not None



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

    spec = modulo_de(obj)
    if spec is None:
        App.Console.PrintWarning(
            f"[VDO] {obj.Name} no parece un modulo VDO: no se repara.\n")
        return None

    try:
        # El COCO prefiere DragableViewProvider (manejadores de arrastre);
        # si no esta disponible cae al del catalogo.
        if spec.tipo == "coco":
            try:
                from VDO.ui.vdo_ui_drag_handles import DragableViewProvider
                return DragableViewProvider(vp)
            except Exception:
                pass
        from VDO.hub.vdo_hub_schema import resolver
        return resolver(spec.viewprovider)(vp)
    except Exception as exc:
        App.Console.PrintError(
            f"[VDO] No se pudo reparar ViewProvider de {obj.Name}: {exc}\n")
    return None


def enfocar_inspector_universal(obj):
    """Archivado: no busca docks reactivos."""
    return False


def abrir_panel_objeto(obj):
    """Abre el panel de cualquier módulo VDO, reparando el proxy si hace falta."""
    if obj is None:
        return False
    # Si el Inspector Universal está disponible, enfocarlo y no abrir diálogos secundarios flotantes
    if enfocar_inspector_universal(obj):
        return True
    proxy = getattr(getattr(obj, "ViewObject", None), "Proxy", None)
    if not hasattr(proxy, "_abrir_panel"):
        proxy = reparar_viewprovider(obj)
    if proxy is not None and hasattr(proxy, "_abrir_panel"):
        return proxy._abrir_panel(obj)

    # Ultimo recurso: el panel que declare el catalogo. Antes era una
    # cadena de cuatro `elif` que no incluia puerta ni tambor, asi que
    # esos dos modulos simplemente no se podian abrir por esta via.
    spec = modulo_de(obj)
    if spec is None:
        App.Console.PrintWarning(
            f"[VDO] {obj.Name} no parece un módulo VDO.\n")
        return False
    try:
        from VDO.hub.vdo_hub_schema import resolver
        Gui.Control.showDialog(resolver(spec.panel)(obj))
        return True
    except Exception as exc:
        App.Console.PrintError(
            f"[VDO] No se pudo abrir el panel de {obj.Name}: {exc}\n")
        import traceback
        App.Console.PrintError(traceback.format_exc())
        return False
