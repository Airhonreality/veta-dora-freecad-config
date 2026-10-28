# -*- coding: utf-8 -*-
# =====================================================================
# vdo_module_props.py
# Propiedades comunes de colocación para todos los módulos VDO.
# - VDO_RotacionZ: rotación alrededor de Z (pose, no geometría).
# - VDO_Anclaje: esquina del módulo que se alinea con el cursor/snap.
# =====================================================================

import FreeCAD as App

import vdo_frames as VDO_FR


ANCLAJES = [
    "inferior_izquierda_frente",
    "inferior_derecha_frente",
    "inferior_izquierda_fondo",
    "inferior_derecha_fondo",
    "superior_izquierda_frente",
    "superior_derecha_frente",
    "superior_izquierda_fondo",
    "superior_derecha_fondo",
    "centro_inferior",
]

ANCLAJE_DEFAULT = "inferior_izquierda_frente"

ANCLAJE_LABELS = {
    "inferior_izquierda_frente": "Inferior izquierda (frente)",
    "inferior_derecha_frente": "Inferior derecha (frente)",
    "inferior_izquierda_fondo": "Inferior izquierda (fondo)",
    "inferior_derecha_fondo": "Inferior derecha (fondo)",
    "superior_izquierda_frente": "Superior izquierda (frente)",
    "superior_derecha_frente": "Superior derecha (frente)",
    "superior_izquierda_fondo": "Superior izquierda (fondo)",
    "superior_derecha_fondo": "Superior derecha (fondo)",
    "centro_inferior": "Centro inferior",
}

ANCLAJE_IDS = {label: idx for idx, label in ANCLAJE_LABELS.items()}


def add_common_props(obj):
    """Añade las propiedades de colocación si no existen (idempotente)."""
    if not hasattr(obj, "VDO_RotacionZ"):
        obj.addProperty(
            "App::PropertyAngle", "VDO_RotacionZ", "Colocación",
            "Rotación del módulo alrededor del eje Z (pose, no geometría)"
        ).VDO_RotacionZ = 0.0

    if not hasattr(obj, "VDO_Anclaje"):
        prop = obj.addProperty(
            "App::PropertyEnumeration", "VDO_Anclaje", "Colocación",
            "Esquina del módulo que se alinea con el punto de colocación"
        )
        prop.VDO_Anclaje = ANCLAJES
        obj.VDO_Anclaje = ANCLAJE_DEFAULT

    if not hasattr(obj, "VDO_Lados_Vistos"):
        obj.addProperty(
            "App::PropertyString", "VDO_Lados_Vistos", "Exposici\u00f3n",
            "Lados del m\u00f3dulo visibles desde el espacio (JSON)"
        ).VDO_Lados_Vistos = VDO_FR.serializar_lados([VDO_FR.FRENTE])

    if not hasattr(obj, "VDO_Lados_Apoyados"):
        obj.addProperty(
            "App::PropertyString", "VDO_Lados_Apoyados", "Exposici\u00f3n",
            "Lados del m\u00f3dulo apoyados contra muro/piso (JSON)"
        ).VDO_Lados_Apoyados = VDO_FR.serializar_lados([VDO_FR.FONDO])


def leer_rotacion(obj):
    """Devuelve la rotación en grados."""
    try:
        return float(getattr(obj, "VDO_RotacionZ", 0.0))
    except (TypeError, ValueError):
        return 0.0


def rotacion_z(grados):
    """Crea una rotación Z a partir de grados.

    En FreeCAD 1.1.4 el constructor `App.Rotation(axis, angle)` recibe el
    ángulo en GRADOS; `Rotation.Angle` sí devuelve radianes.
    """
    return App.Rotation(App.Vector(0.0, 0.0, 1.0), float(grados))


def aplicar_rotacion(obj, grados):
    """Aplica rotación Z alrededor del anclaje, manteniéndolo fijo."""
    ancla = ancla_local(obj)
    p = obj.Placement
    ancla_global = p.multVec(ancla)
    rot = rotacion_z(grados)
    base = ancla_global - rot.multVec(ancla)
    obj.Placement = App.Placement(base, rot)
    if hasattr(obj, "VDO_RotacionZ"):
        obj.VDO_RotacionZ = float(grados)


def _boundbox_local(obj):
    """BoundBox en coordenadas locales (FreeCAD 1.1 aplica Placement a Shape)."""
    try:
        shape = obj.Shape.copy()
        if shape.isNull():
            return None
        shape.transformShape(obj.Placement.inverse().toMatrix(), True)
        bb = shape.BoundBox
        return bb if bb.isValid() else None
    except Exception:
        return None


def ancla_local(obj, anclaje=None):
    """Devuelve el punto local (Vector) de la esquina de anclaje.

    Convención de ejes:
      X: izquierda (min) / derecha (max)
      Y: frente (min) / fondo (max)
      Z: inferior (min) / superior (max)
    """
    anclaje = anclaje or getattr(obj, "VDO_Anclaje", ANCLAJE_DEFAULT)
    bb = _boundbox_local(obj)
    if bb is None:
        xmin = xmax = ymin = ymax = zmin = zmax = 0.0
    else:
        xmin, xmax = bb.XMin, bb.XMax
        ymin, ymax = bb.YMin, bb.YMax
        zmin, zmax = bb.ZMin, bb.ZMax

    izquierda = anclaje.startswith("inferior_izquierda") or anclaje.startswith(
        "superior_izquierda")
    derecha = anclaje.startswith("inferior_derecha") or anclaje.startswith(
        "superior_derecha")
    frente = anclaje.endswith("_frente")
    fondo = anclaje.endswith("_fondo")
    superior = anclaje.startswith("superior_")
    centro_inferior = anclaje == "centro_inferior"

    if centro_inferior:
        return App.Vector((xmin + xmax) / 2.0, (ymin + ymax) / 2.0, zmin)
    return App.Vector(
        xmin if izquierda else (xmax if derecha else (xmin + xmax) / 2.0),
        ymin if frente else (ymax if fondo else (ymin + ymax) / 2.0),
        zmax if superior else zmin,
    )
