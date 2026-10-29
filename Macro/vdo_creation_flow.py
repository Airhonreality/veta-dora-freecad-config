# -*- coding: utf-8 -*-
# =====================================================================
# vdo_creation_flow.py
# Flujo común de creación de módulos VDO (D18):
#   toolbar → crear oculto → panel → colocar con mouse → commit
# =====================================================================

import re

import FreeCAD as App

import vdo_guardian
from vdo_module_props import add_common_props
from vdo_module_specs import get_spec, resolver_panel


def _sanitizar_nombre(nombre):
    nombre = re.sub(r"[^A-Za-z0-9_]", "_", str(nombre or "Modulo"))
    if not nombre or nombre[0].isdigit():
        nombre = "Modulo_" + nombre
    return nombre


def _nombre_unico(doc, base):
    base = _sanitizar_nombre(base)
    if doc.getObject(base) is None:
        return base
    i = 1
    while doc.getObject(f"{base}_{i:03d}") is not None:
        i += 1
    return f"{base}_{i:03d}"


def crear_modulo_interactivo(module_key, config=None):
    """Crea un módulo VDO y lo coloca con el mouse.

    En FreeCADCmd (sin GUI) crea el módulo y lo deja en el origen,
    sin panel ni colocación interactiva.
    """
    try:
        spec = get_spec(module_key)
    except Exception as exc:
        App.Console.PrintError(f"[VDO] {exc}\n")
        return None

    doc = vdo_guardian.vdo_guard()
    if doc is None:
        App.Console.PrintError(
            "[VDO] No hay documento activo para crear el módulo.\n")
        return None

    cfg = dict(spec.get("config", {}))
    if config:
        cfg.update(config)
    cfg["nombre"] = _nombre_unico(
        doc, cfg.get("nombre") or spec.get("label", module_key))

    obj = None
    tx_propia = False
    if not doc.HasPendingTransaction:
        try:
            doc.openTransaction(
                f"Crear y colocar {spec.get('label', module_key)}")
            tx_propia = True
        except Exception as exc:
            App.Console.PrintWarning(
                f"[VDO] No se pudo abrir transacción: {exc}\n")

    def cancelar():
        if tx_propia:
            try:
                doc.abortTransaction()
            except Exception:
                pass
        if obj is not None:
            try:
                if doc.getObject(obj.Name) is not None:
                    doc.removeObject(obj.Name)
            except Exception:
                pass
        try:
            doc.recompute()
        except Exception:
            pass

    def confirmar():
        try:
            doc.recompute()
        except Exception:
            pass
        if tx_propia:
            try:
                doc.commitTransaction()
            except Exception:
                pass

    try:
        obj = spec["factory_fn"](cfg)
        if obj is None:
            raise RuntimeError("La factory no devolvió un objeto")

        add_common_props(obj)
        if not App.GuiUp:
            confirmar()
            return obj

        import FreeCADGui as Gui
        from vdo_view_base import diagnostico_viewprovider
        App.Console.PrintMessage(
            "[VDO] " + diagnostico_viewprovider(obj) + "\n")

        try:
            obj.ViewObject.Visibility = False
        except Exception:
            pass

        panel_cls = resolver_panel(spec)
        estado = {"finalizado": False}

        def on_accept():
            if estado["finalizado"]:
                return
            estado["finalizado"] = True
            from vdo_placement import iniciar_colocacion
            iniciar_colocacion(
                obj,
                on_done=confirmar,
                on_cancel=cancelar,
            )

        def on_cancel():
            if estado["finalizado"]:
                return
            estado["finalizado"] = True
            cancelar()

        panel = panel_cls(
            obj,
            on_accept=on_accept,
            on_cancel=on_cancel,
            auto_transaction=False,
        )
        try:
            if hasattr(Gui.Control, "activeDialog") \
                    and Gui.Control.activeDialog():
                Gui.Control.closeDialog()
        except Exception:
            pass
        Gui.Control.showDialog(panel)
        return obj

    except Exception as exc:
        cancelar()
        App.Console.PrintError(
            f"[VDO] Error creando módulo '{module_key}': {exc}\n")
        import traceback
        App.Console.PrintError(traceback.format_exc())
        return None
