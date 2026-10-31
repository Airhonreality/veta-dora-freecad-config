# -*- coding: utf-8 -*-
# =====================================================================
# VDO/shared/vdo_shared_fachadas.py
# Fachadas: frentes visibles de un mueble (hojas de puerta y frentes de
# cajón). Acción de primera clase: la usan el botón de la vista 3D y las
# vistas «vanos libres» / «cerrado» del dossier (docs/08 §6, cuadrantes 2-3).
#
# Definición (sin literales de nombre):
#   - VDO_Rol == "fachada"  -> frente de cajón (PanelFeature hijo del cajón)
#   - módulo resuelto == "puerta" -> hoja de puerta
# =====================================================================


def es_fachada(obj):
    """True si `obj` es un frente: frente de cajón o hoja de puerta."""
    if getattr(obj, "VDO_Rol", "") == "fachada":
        return True
    from VDO.hub.vdo_hub_registry import resolver_modulo
    try:
        spec = resolver_modulo(obj)
    except Exception:
        return False
    return spec is not None and spec.tipo == "puerta"


def fachadas_de(raiz):
    """Fachadas de `raiz` y de todo su subárbol (Hijos), sin duplicados."""
    vistas, salida = set(), []

    def recorrer(o):
        if o is None or o.Name in vistas:
            return
        vistas.add(o.Name)
        if es_fachada(o):
            salida.append(o)
        for h in (getattr(o, "Hijos", None) or []):
            recorrer(h)

    recorrer(raiz)
    return salida


def fachadas_del_documento(doc):
    """Todas las fachadas visibles del documento (para el botón 3D)."""
    salida = []
    for o in doc.Objects:
        if es_fachada(o):
            salida.append(o)
    return salida


def alternar_fachadas(doc):
    """Muestra u oculta todas las fachadas del documento.

    Si alguna está visible, las oculta todas; si ninguna lo está, las muestra.
    Devuelve (n_fachadas, visibles_tras_la_accion).
    """
    frentes = fachadas_del_documento(doc)
    if not frentes:
        return 0, None
    mostrar = not any(bool(f.Visibility) for f in frentes)
    for f in frentes:
        f.Visibility = mostrar
    return len(frentes), mostrar
