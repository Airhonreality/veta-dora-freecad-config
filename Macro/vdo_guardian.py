# -*- coding: utf-8 -*-
# =====================================================================
# vdo_guardian.py
# Guardián de Dependencias VDO
# Valida e inyecta el entorno mínimo antes de ejecutar cualquier macro.
# Cualquier macro puede llamar a vdo_guard() y quedará autoconfigurada.
# =====================================================================

import FreeCAD as App

import vdo_manifest as VM

HOJA_GLOBAL = "Params_Melamina"
HOJA_LOCAL = "Params"


def _obtener_hoja(doc, nombre):
    hoja = doc.getObject(nombre)
    if hoja is None:
        hoja = doc.addObject("Spreadsheet::Sheet", nombre)
        hoja.Label = nombre
        print(f"[VDO Guardian] Creada hoja: {nombre}")
    return hoja


def _tiene_alias(hoja, celda):
    return hoja.getAlias(celda) is not None


def _asegurar_parametros(hoja, fila_inicio, fila_valor, fila_descripcion,
                         parametros):
    """Inyecta etiqueta/valor+alias/descripcion en cada fila de parametros.

    Solo escribe celdas sin alias: respeta cualquier valor ya editado.
    """
    for fila, (nombre, info) in enumerate(parametros.items(), start=fila_inicio):
        celda_valor = f"{fila_valor}{fila}"
        if _tiene_alias(hoja, celda_valor):
            continue
        if fila_valor == "A":
            hoja.set(f"A{fila}", str(info["valor"]))
            hoja.setAlias(f"A{fila}", nombre)
        else:
            hoja.set(f"A{fila}", f"'{nombre}")
            hoja.set(f"{fila_valor}{fila}", str(info["valor"]))
            hoja.setAlias(f"{fila_valor}{fila}", nombre)
        if "descripcion" in info and info["descripcion"]:
            hoja.set(f"{fila_descripcion}{fila}", f"'{info['descripcion']}")
        print(f"[VDO Guardian] Parametro '{nombre}' = {info['valor']} mm")


def asegurar_hoja_global(doc):
    """Capa Global (Reglas de Taller): hoja Params_Melamina."""
    nombre = VM.VDO_MANIFEST.get("capa_global", {}).get("hoja", HOJA_GLOBAL)
    hoja = _obtener_hoja(doc, nombre)

    if not hoja.getContents("A1"):
        hoja.set("A1", "'Parametro")
        hoja.set("B1", "'Valor")
        hoja.set("C1", "'Descripcion")

    _asegurar_parametros(
        hoja,
        fila_inicio=2,
        fila_valor="B",
        fila_descripcion="C",
        parametros=VM.VDO_MANIFEST["parametros_globales"],
    )
    return hoja


def asegurar_params_local(doc):
    """Capa Local (Contenedores y Módulos): hoja Params del módulo."""
    nombre = VM.VDO_MANIFEST.get("capa_local", {}).get("hoja", HOJA_LOCAL)
    hoja = _obtener_hoja(doc, nombre)

    _asegurar_parametros(
        hoja,
        fila_inicio=1,
        fila_valor="A",
        fila_descripcion="B",
        parametros=VM.VDO_MANIFEST["parametros_locales"],
    )
    return hoja


def asegurar_documento():
    doc = App.ActiveDocument
    if doc is None:
        doc = App.newDocument("VDO")
        print("[VDO Guardian] No había documento activo; se creó VDO.")
    return doc


def vdo_guard(doc=None):
    """Punto de entrada: valida el documento y inyecta el entorno completo."""
    if doc is None:
        doc = asegurar_documento()

    hoja_global = asegurar_hoja_global(doc)
    hoja_local = asegurar_params_local(doc)

    doc.recompute()
    version = VM.VDO_MANIFEST["version"]
    print(f"[VDO Guardian] Entorno asegurado v{version}: "
          f"{hoja_global.Name} + {hoja_local.Name}")
    return doc