# -*- coding: utf-8 -*-
# =====================================================================
# vdo_spaces.py
# Motor de resolución de espacios libres para COCO VDO
# Axioma 2: Lógica pura, sin dependencias de UI ni FreeCAD
# =====================================================================

import json
import math


# --- Constantes de tipos de espacio ---
ESPACIO_FIJO = "fijo"
ESPACIO_RESTANTE = "restante"
ESPACIO_IGUALES = "iguales"


class SpaceNode:
    """Nodo de un árbol de espacios libres.

    Cada nodo representa un espacio que puede contener sub-espacios
    en el eje opuesto (recursividad bidimensional).
    """

    def __init__(self, space_type=ESPACIO_FIJO, value=0.0, children=None,
                 space_id=None, parent_id=None, axis=None):
        self.space_type = space_type
        self.value = value
        self.children = children or []
        self.space_id = space_id or "auto"
        self.parent_id = parent_id or ""
        self.axis = axis

    def to_dict(self):
        d = {
            "type": self.space_type,
            "id": self.space_id,
            "parent": self.parent_id,
        }
        if self.space_type == ESPACIO_FIJO:
            d["value"] = self.value
        elif self.space_type == ESPACIO_IGUALES:
            d["count"] = int(self.value)
        if self.children:
            d["axis"] = self.axis or "X"
            d["children"] = [c.to_dict() for c in self.children]
        return d

    @classmethod
    def from_dict(cls, d):
        node = cls(
            space_type=d.get("type", ESPACIO_FIJO),
            value=d.get("value", 0.0),
            space_id=d.get("id", "auto"),
            parent_id=d.get("parent", ""),
            axis=d.get("axis"),
        )
        if d.get("count") is not None:
            node.value = float(d["count"])
        for child_data in d.get("children", []):
            node.children.append(cls.from_dict(child_data))
        return node

    def __repr__(self):
        return (f"SpaceNode(type={self.space_type}, value={self.value}, "
                f"id={self.space_id}, children={len(self.children)})")


def serializar_espacios(nodes):
    """Serializa una lista de SpaceNode a JSON para PropertyStringList."""
    return json.dumps([n.to_dict() for n in nodes], ensure_ascii=False)


def deserializar_espacios(json_str):
    """Deserializa JSON a lista de SpaceNode."""
    if not json_str or not json_str.strip():
        return []
    try:
        data = json.loads(json_str)
        return [SpaceNode.from_dict(d) for d in data]
    except (json.JSONDecodeError, TypeError):
        return []


def resolver_espacios_eje(nodes, espacio_total, espesor):
    """Resuelve una lista de nodos en posiciones físicas a lo largo de un eje.

    Args:
        nodes: Lista de SpaceNode (definition-level, no nested).
        espacio_total: Espacio libre total disponible en mm.
        espesor: Espesor de las piezas divisorias en mm.

    Returns:
        Lista de dicts con la información de cada espacio resuelto:
        [
            {
                "id": str,
                "inicio": float,    # posición inicial del espacio libre
                "fin": float,       # posición final del espacio libre
                "libre": float,     # espacio libre en mm
                "tipo": str,        # "fijo", "restante", "iguales"
                "children": list,   # sub-espacios resueltos (si existen)
            },
            ...
        ]
    """
    if not nodes:
        return [{"id": "_full", "inicio": 0.0, "fin": espacio_total,
                 "libre": espacio_total, "tipo": "fijo", "children": []}]

    espacio_disponible = espacio_total

    if espacio_disponible < 0:
        espacio_disponible = 0.0

    fijos = [n for n in nodes if n.space_type == ESPACIO_FIJO]
    restantes = [n for n in nodes if n.space_type == ESPACIO_RESTANTE]
    iguales = [n for n in nodes if n.space_type == ESPACIO_IGUALES]

    espacio_consumido_fijos = sum(n.value for n in fijos)
    espacio_para_iguales = espacio_disponible - espacio_consumido_fijos

    if restantes:
        espacio_para_iguales = max(0, espacio_para_iguales)

    if iguales and espacio_para_iguales > 0:
        n_iguales = len(iguales)
        n_div_iguales = sum(int(n.value) for n in iguales)
        espacio_para_dividir = espacio_para_iguales - (n_iguales - 1) * espesor
        espacio_para_dividir = max(0, espacio_para_dividir)
        espacio_cada_div = (espacio_para_dividir / n_div_iguales
                            if n_div_iguales > 0 else 0)
    else:
        espacio_cada_div = 0

    resultado = []
    cursor = 0.0

    for i, node in enumerate(nodes):
        if node.space_type == ESPACIO_FIJO:
            libre = min(node.value, max(0, espacio_disponible - cursor))
            resuelto = {
                "id": node.space_id,
                "inicio": cursor,
                "fin": cursor + libre,
                "libre": libre,
                "tipo": ESPACIO_FIJO,
                "children": [],
            }
            if node.children:
                resuelto["children"] = _resolver_subespacios(
                    node.children, libre, espesor)
            resultado.append(resuelto)
            cursor += libre

        elif node.space_type == ESPACIO_IGUALES:
            n_sub = max(1, int(node.value))
            espacio_total_este = espacio_cada_div * n_sub
            sub_cursor = cursor
            sub_spaces = []
            for j in range(n_sub):
                sub_spaces.append({
                    "id": f"{node.space_id}_{j+1}",
                    "inicio": sub_cursor,
                    "fin": sub_cursor + espacio_cada_div,
                    "libre": espacio_cada_div,
                    "tipo": ESPACIO_FIJO,
                    "children": [],
                })
                sub_cursor += espacio_cada_div
                if j < n_sub - 1:
                    sub_cursor += espesor

            resuelto = {
                "id": node.space_id,
                "inicio": cursor,
                "fin": sub_cursor,
                "libre": espacio_total_este,
                "tipo": ESPACIO_IGUALES,
                "children": sub_spaces,
            }
            resultado.append(resuelto)
            cursor = sub_cursor

        elif node.space_type == ESPACIO_RESTANTE:
            libre = max(0, espacio_disponible - cursor)
            resuelto = {
                "id": node.space_id,
                "inicio": cursor,
                "fin": cursor + libre,
                "libre": libre,
                "tipo": ESPACIO_RESTANTE,
                "children": [],
            }
            if node.children:
                resuelto["children"] = _resolver_subespacios(
                    node.children, libre, espesor)
            resultado.append(resuelto)
            cursor += libre

        if i < len(nodes) - 1:
            cursor += espesor

    return resultado


def _resolver_subespacios(children, espacio_libre, espesor):
    """Resuelve sub-espacios recursivamente en el eje opuesto."""
    if not children or espacio_libre <= 0:
        return []

    espacio_disponible = espacio_libre

    fijos = [c for c in children if c.space_type == ESPACIO_FIJO]
    restantes = [c for c in children if c.space_type == ESPACIO_RESTANTE]
    iguales = [c for c in children if c.space_type == ESPACIO_IGUALES]

    espacio_consumido = sum(c.value for c in fijos)
    espacio_para_iguales = espacio_disponible - espacio_consumido

    if iguales and espacio_para_iguales > 0:
        n_div = sum(int(c.value) for c in iguales)
        espacio_para_dividir = max(0, espacio_para_iguales)
        espacio_cada = (espacio_para_dividir / n_div if n_div > 0 else 0)
    else:
        espacio_cada = 0

    resultado = []
    cursor = 0.0

    for i, child in enumerate(children):
        if child.space_type == ESPACIO_FIJO:
            libre = min(child.value, max(0, espacio_disponible - cursor))
            resultado.append({
                "id": child.space_id,
                "inicio": cursor,
                "fin": cursor + libre,
                "libre": libre,
                "tipo": ESPACIO_FIJO,
                "children": _resolver_subespacios(
                    child.children, libre, espesor) if child.children else [],
            })
            cursor += libre

        elif child.space_type == ESPACIO_IGUALES:
            n_sub = max(1, int(child.value))
            sub_cursor = cursor
            sub_spaces = []
            for j in range(n_sub):
                sub_spaces.append({
                    "id": f"{child.space_id}_{j+1}",
                    "inicio": sub_cursor,
                    "fin": sub_cursor + espacio_cada,
                    "libre": espacio_cada,
                    "tipo": ESPACIO_FIJO,
                    "children": [],
                })
                sub_cursor += espacio_cada
                if j < n_sub - 1:
                    sub_cursor += espesor
            resultado.append({
                "id": child.space_id,
                "inicio": cursor,
                "fin": sub_cursor,
                "libre": espacio_cada * n_sub,
                "tipo": ESPACIO_IGUALES,
                "children": sub_spaces,
            })
            cursor = sub_cursor

        elif child.space_type == ESPACIO_RESTANTE:
            libre = max(0, espacio_disponible - cursor)
            resultado.append({
                "id": child.space_id,
                "inicio": cursor,
                "fin": cursor + libre,
                "libre": libre,
                "tipo": ESPACIO_RESTANTE,
                "children": _resolver_subespacios(
                    child.children, libre, espesor) if child.children else [],
            })
            cursor += libre

        if i < len(children) - 1:
            cursor += espesor

    return resultado


def generar_texto_resumen(espacios_resueltos, eje_label="X"):
    """Genera un texto legible del resultado de la resolución de espacios."""
    lineas = []
    for esp in espacios_resueltos:
        libre = esp["libre"]
        tipo = esp["tipo"]
        if tipo == ESPACIO_RESTANTE:
            tipo_label = "Restante"
        elif tipo == ESPACIO_IGUALES:
            tipo_label = f"Iguales ({len(esp.get('children', []))} partes)"
        else:
            tipo_label = "Fijo"
        lineas.append(
            f"  {esp['id']}: {libre:.1f}mm libres [{tipo_label}]")
        for sub in esp.get("children", []):
            lineas.append(
                f"    {sub['id']}: {sub['libre']:.1f}mm libres")
    return f"Eje {eje_label}:\n" + "\n".join(lineas) if lineas else ""


def crear_config_por_defecto():
    """Crea una configuración de espacios por defecto (sin divisiones)."""
    return [SpaceNode(space_type=ESPACIO_RESTANTE, space_id="V1")]


def calcular_espacio_libre(espacios_json, espacio_total, espesor):
    """Calcula el espacio libre total y el último vano remanente.

    Returns:
        dict: {
            "total_libre": float,
            "ultimo_vano": float,
            "n_espacios": int,
            "texto": str
        }
    """
    nodes = deserializar_espacios(espacios_json)
    if not nodes:
        return {
            "total_libre": espacio_total,
            "ultimo_vano": espacio_total,
            "n_espacios": 0,
            "texto": f"Sin divisiones. Espacio libre: {espacio_total:.1f}mm",
        }

    resueltos = resolver_espacios_eje(nodes, espacio_total, espesor)
    total = sum(e["libre"] for e in resueltos)
    ultimo = resueltos[-1]["libre"] if resueltos else espacio_total

    return {
        "total_libre": total,
        "ultimo_vano": ultimo,
        "n_espacios": len(resueltos),
        "texto": generar_texto_resumen(resueltos),
    }
