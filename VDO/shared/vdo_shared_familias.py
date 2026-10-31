# -*- coding: utf-8 -*-
# =====================================================================
# VDO/shared/vdo_shared_familias.py
# Clasificador de familias de hijos de VDO_Espacio.
#
# El discriminante autoritativo es VDO_Modulo + resolver_modulo(obj)
# (vdo_hub_registry.py). Nunca se usan literales "COCO"/"Panel"/"Zocalo"
# ni VDO_Tipo crudo, porque los objetos BIM (Arch_Wall, BIM_Door…) no
# tienen VDO_Tipo y los modulos VDO pueden tener vdo_tipo distinto de
# su clave de modulo.
#
# Familias:
#   MOBILIARIO: resolver_modulo(o).tipo in {"coco","cajon","puerta",
#                "zocalo","panel","tambor"}
#   ARQUITECTURA: objetos con IfcType en {"Wall","Door","Window",
#                "Column","Slab"} o isDerivedFrom("Part::Feature")
#                con IfcType (ver B5)
#   ASSETS: marcador VDO_Target/VDO_Familia o IfcType de mobiliario
#   OTROS: todo lo restante (se omite con aviso)
# =====================================================================

from typing import Optional, Sequence

from VDO.hub.vdo_hub_registry import resolver_modulo, CATALOGO

# Claves de modulo VDO que son mobiliario manufacturable.
MOBILIARIO_TIPOS = frozenset(
    s.tipo for s in CATALOGO.values()
    if s.vdo_tipo in ("panel", "contenedor")
)

# IfcTypes que clasifican como arquitectura (objetos BIM/Angen sin VDO_Modulo).
ARQUITECTURA_IFC = frozenset({"Wall", "Door", "Window", "Column", "Slab"})

# Marcadores de assets (objetos no manufactrables, nunca entran en cutlist).
ASSET_MARKERS = frozenset({"Asset", "Electrodomestico", "Sanitario"})


def resolver_tipo_modulo(obj) -> Optional[str]:
    """Devuelve la clave de modulo VDO de `obj`, o None si no es un modulo VDO."""
    s = resolver_modulo(obj)
    return s.tipo if s is not None else None


def es_mobiliario(obj) -> bool:
    """True si `obj` es un modulo VDO de tipo mobiliario (panel/contenedor)."""
    return resolver_tipo_modulo(obj) in MOBILIARIO_TIPOS


def es_arquitectura(obj) -> bool:
    """True si `obj` es arquitectura (BIM con IfcType, o Part::Feature con IfcType)."""
    ifc_type = getattr(obj, "IfcType", None)
    if ifc_type in ARQUITECTURA_IFC:
        return True
    # Part::Feature con IfcType de arquitectura
    try:
        import FreeCAD as App
        if obj.isDerivedFrom("Part::Feature") and ifc_type in ARQUITECTURA_IFC:
            return True
    except Exception:
        pass
    return False


def es_asset(obj) -> bool:
    """True si `obj` es un asset (no manufactrable)."""
    vdo_target = getattr(obj, "VDO_Target", None)
    if vdo_target in ASSET_MARKERS:
        return True
    ifc_type = getattr(obj, "IfcType", None)
    return ifc_type in ASSET_MARKERS


def clasificar_hijo(obj) -> str:
    """Devuelve la familia de `obj`: "mobiliario", "arquitectura", "assets" u "otros"."""
    if es_mobiliario(obj):
        return "mobiliario"
    if es_arquitectura(obj):
        return "arquitectura"
    if es_asset(obj):
        return "assets"
    return "otros"


def hijos_por_familia(espacio, familia: str) -> Sequence:
    """Filtra los Hijos de `espacio` por familia.

    Args:
        espacio: objeto VDO_Espacio con propiedad Hijos.
        familia: "mobiliario", "arquitectura", "assets" u "otros".

    Devuelve lista de objetos hijos que pertenecen a la familia.
    """
    hijos = list(getattr(espacio, "Hijos", None) or [])
    return [h for h in hijos if clasificar_hijo(h) == familia]


__all__ = [
    "MOBILIARIO_TIPOS", "ARQUITECTURA_IFC", "ASSET_MARKERS",
    "resolver_tipo_modulo", "es_mobiliario", "es_arquitectura",
    "es_asset", "clasificar_hijo", "hijos_por_familia",
]
