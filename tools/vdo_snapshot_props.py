#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Instantanea del inventario de propiedades de cada modulo VDO.

    FreeCADCmd tools/vdo_snapshot_props.py

Escribe .verif/props_snapshot.json con, para cada tipo creable:
nombre de propiedad -> {typeid, grupo, doc, valor, enum}.

PARA QUE SIRVE: la fase 2 del refactor sustituye las cadenas de
obj.addProperty() de cada Feature por aplicar_esquema(obj, spec). Esa
sustitucion solo es correcta si el objeto resultante es
INDISTINGUIBLE del anterior. Se captura el antes, se refactoriza y se
compara (tests/test_contrato_modulos.py::test_inventario_sin_deriva).
"""

import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "tests" / "datos" / "props_snapshot.json"

if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import FreeCAD as App


def _valor_serializable(obj, prop):
    try:
        v = getattr(obj, prop)
    except Exception as exc:
        return f"<error:{exc}>"
    if isinstance(v, (int, float, bool, str)) or v is None:
        return v
    if hasattr(v, "Value"):          # Quantity
        return float(v.Value)
    if hasattr(v, "Base") and hasattr(v, "Rotation"):   # Placement
        p, r = v.Base, v.Rotation
        return {"base": [p.x, p.y, p.z],
                "axis": [r.Axis.x, r.Axis.y, r.Axis.z],
                "angle": round(r.Angle, 9)}
    if isinstance(v, (list, tuple)):
        return [getattr(i, "Name", str(i)) for i in v]
    return str(v)


def inventario(obj):
    datos = {}
    for prop in obj.PropertiesList:
        entrada = {
            "typeid": obj.getTypeIdOfProperty(prop),
            "grupo": obj.getGroupOfProperty(prop),
            "doc": obj.getDocumentationOfProperty(prop),
            "valor": _valor_serializable(obj, prop),
        }
        try:
            if entrada["typeid"] == "App::PropertyEnumeration":
                entrada["enum"] = list(obj.getEnumerationsOfProperty(prop))
        except Exception:
            pass
        datos[prop] = entrada
    return datos


def main():
    from VDO.ui.vdo_ui_creation_flow import ESPECIFICACIONES, crear_modulo_directo

    App.newDocument("SNAP")
    resultado = {}
    for tipo in sorted(ESPECIFICACIONES):
        obj = crear_modulo_directo(tipo)
        if obj is None:
            resultado[tipo] = {"__error__": "la fabrica devolvio None"}
            continue
        resultado[tipo] = inventario(obj)

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(
        json.dumps(resultado, indent=1, ensure_ascii=False, sort_keys=True),
        encoding="utf-8")
    total = sum(len(v) for v in resultado.values())
    print(f"[snapshot] {len(resultado)} tipos, {total} propiedades -> {SALIDA}")
    sys.stdout.flush()
    os._exit(0)


main()
