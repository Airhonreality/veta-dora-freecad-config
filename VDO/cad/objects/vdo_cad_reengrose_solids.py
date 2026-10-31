# -*- coding: utf-8 -*-
"""Construccion de solidos de tiras de reengrose (Capa 3).

Las tiras normales son cajas. Las tiras con ``poligono`` (inglete 45)
se extruyen como prisma poligonal para no solapar en la esquina.
"""

import FreeCAD as App
import Part


_DIM = {"x": "w", "y": "h", "z": "d"}
_EJE = {"w": "x", "h": "y", "d": "z"}


def forma_ref(ref):
    """Devuelve un Part.Shape para una tira/refuerzo."""
    try:
        poly = ref.get("poligono")
        if poly and len(poly) >= 3:
            puntos = [App.Vector(float(p[0]), float(p[1]), float(p[2]))
                      for p in poly]
            eje = str(ref.get("eje_extrusion", "z")).lower()
            if eje not in _DIM:
                eje = "z"
            dim = _DIM[eje]
            largo = float(ref.get(dim, ref.get("espesor", 0.0)))
            if largo > 1e-9:
                try:
                    wire = Part.makePolygon(puntos + [puntos[0]])
                    cara = Part.Face(wire)
                    vector = {"x": 0.0, "y": 0.0, "z": 0.0}
                    vector[eje] = largo
                    solido = cara.extrude(
                        App.Vector(vector["x"], vector["y"], vector["z"]))
                    if not solido.isNull() and solido.Volume > 1e-9:
                        return solido
                except Exception:
                    pass
        w = float(ref.get("w", 0.0))
        h = float(ref.get("h", 0.0))
        d = float(ref.get("d", ref.get("espesor", 0.0)))

        # Fallback solo si w y h no existen
        if w <= 1e-9 and h <= 1e-9:
            largo = float(ref.get("largo", 0.0))
            ancho = float(ref.get("ancho", 0.0))
            borde = ref.get("borde", "")
            if borde in ("frente", "fondo"):
                w, h = largo, ancho
            else:
                w, h = ancho, largo

        if w <= 1e-9 or h <= 1e-9:
            nombre = ref.get("nombre", "?")
            borde = ref.get("borde", "?")
            App.Console.PrintWarning(
                f"[VDO] forma_ref: tira '{nombre}' (borde={borde}) sin w/h "
                f"proyectadas (w={w}, h={h}). Se omite el sólido para evitar "
                f"heurísticas de orientación.\n")
            return None
        if d <= 1e-9:
            nombre = ref.get("nombre", "?")
            borde = ref.get("borde", "?")
            App.Console.PrintWarning(
                f"[VDO] forma_ref: tira '{nombre}' (borde={borde}) sin espesor "
                f"proyectado (d={d}). Se omite el sólido.\n")
            return None
        return Part.makeBox(
            w, h, d,
            App.Vector(
                float(ref.get("x", 0.0)),
                float(ref.get("y", 0.0)),
                float(ref.get("z", 0.0))))
    except Exception:
        return None
