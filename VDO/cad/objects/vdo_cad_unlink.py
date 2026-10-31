# -*- coding: utf-8 -*-
# =====================================================================
# vdo_desvincular_pieza.py
# Comando de "Desvinculación Amigable" (Friendly Unlink) — Sistema VDO.
#
# Protocolo seguro para desvincular un panel de su COCO padre:
#   1. Congela cotas (expresiones → valores numéricos fijos)
#   2. Rompe el vínculo ParentCOCO
#   3. Mueve el panel fuera del grupo nativo (raíz del documento)
#   4. Registra el rol en Piezas_Omitidas del COCO para que execute()
#      saltee ese panel sin crashear
# =====================================================================

import FreeCAD as App

try:
    import FreeCADGui as Gui
except ImportError:
    Gui = None

from VDO.cad.objects.vdo_cad_panel import congelar_cotas, romper_vinculo_padre


def _encontrar_coco_padre(doc, panel_obj):
    """Busca el COCO padre a través de ParentCOCO o del grupo contenedor."""
    coco = getattr(panel_obj, "ParentCOCO", None)
    if coco is not None:
        return coco

    # Fallback: buscar el grupo padre que contenga al panel y cuyo
    # padre sea un COCO.
    for grupo in doc.Objects:
        if grupo.TypeId == "App::DocumentObjectGroup":
            try:
                if panel_obj in grupo.Group:
                    padre_grupo = grupo.getParentObject()
                    if padre_grupo is not None:
                        proxy = getattr(padre_grupo, "Proxy", None)
                        if proxy is not None and type(proxy).__name__ == "CocoFeature":
                            return padre_grupo
            except Exception:
                pass
    return None


def _sacar_de_grupo(panel_obj):
    """Saca el panel de cualquier grupo nativo al que pertenezca."""
    doc = App.ActiveDocument
    if doc is None:
        return
    for grupo in doc.Objects:
        if grupo.TypeId == "App::DocumentObjectGroup":
            try:
                if panel_obj in grupo.Group:
                    grupo.removeObject(panel_obj)
            except Exception:
                pass


def vdo_desvincular_pieza(panel_obj):
    """Desvincula un panel de su COCO padre de forma segura y no destructiva.

    Args:
        panel_obj: DocumentObject de tipo PanelFeature.

    Returns:
        dict con el resultado de la operación.
    """
    doc = App.ActiveDocument
    if doc is None:
        return {"ok": False, "error": "No hay documento activo"}

    if panel_obj is None:
        return {"ok": False, "error": "Objeto panel no válido"}

    # Verificar que es un panel
    proxy = getattr(panel_obj, "Proxy", None)
    if proxy is None or type(proxy).__name__ != "PanelFeature":
        return {"ok": False, "error": "El objeto no es un PanelFeature"}

    rol = getattr(panel_obj, "VDO_Rol", "") or ""
    nombre = panel_obj.Name

    # Encontrar el COCO padre
    coco = _encontrar_coco_padre(doc, panel_obj)
    if coco is None:
        return {
            "ok": False,
            "error": f"No se encontró COCO padre para '{nombre}'",
        }

    doc.openTransaction("Desvincular pieza VDO")
    try:
        # 1. CONGELACIÓN DE COTAS
        congelar_cotas(panel_obj)

        # 2. RUPTURA LIMPIA DEL ENLACE
        padre_previo = romper_vinculo_padre(panel_obj)

        # 3. SACAR DEL GRUPO NATIVO (mover a raíz del documento)
        _sacar_de_grupo(panel_obj)

        # 4. REGISTRO DE SUPRESIÓN EN EL PADRE
        omitidas = list(getattr(coco, "Piezas_Omitidas", []) or [])
        if rol and rol not in omitidas:
            omitidas.append(rol)
        coco.Piezas_Omitidas = omitidas

        doc.commitTransaction()
        doc.recompute()

        App.Console.PrintMessage(
            f"[VDO] Panel '{nombre}' (rol='{rol}') desvinculado del "
            f"COCO '{coco.Name}'.\n")

        return {
            "ok": True,
            "panel": nombre,
            "rol": rol,
            "coco": coco.Name,
        }
    except Exception as exc:
        try:
            doc.abortTransaction()
        except Exception:
            pass
        App.Console.PrintError(
            f"[VDO] Error desvinculando '{nombre}': {exc}\n")
        return {"ok": False, "error": str(exc)}


def registrar_menu_desvincular(view_provider_panel):
    """Registra la acción 'Desvincular del COCO' en el menú contextual
    de un ViewProviderPanel.

    Uso en ViewProviderPanel.setupContextMenu:
        from VDO.cad.objects.vdo_cad_unlink import registrar_menu_desvincular
        registrar_menu_desvincular(self)
    """
    def _setup_context_menu_original(vobj, menu):
        obj = vobj.Object
        coco = _encontrar_coco_padre(App.ActiveDocument, obj) if App.ActiveDocument else None
        if coco is not None and getattr(obj, "VDO_Rol", ""):
            action = menu.addAction("Desvincular del COCO")
            action.setToolTip(
                "Congela cotas, rompe el vínculo con el COCO y registra "
                "el rol en Piezas_Omitidas para evitar crasheos al recompute.")
            action.triggered.connect(
                lambda checked=False, o=obj: _desvincular(o))
    return _setup_context_menu_original


__all__ = ["vdo_desvincular_pieza", "registrar_menu_desvincular"]
