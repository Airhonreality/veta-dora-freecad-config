# -*- coding: utf-8 -*-
# =====================================================================
# vdo_layout.py
# Motor puro de la matriz de vanos del COCO.
#
# No importa FreeCAD ni Qt: sólo datos, medidas y geometría 2D.
#
# MARCO LOCAL 3D (ley única definida en vdo_frames.py):
#   X+ = derecha
#   Y+ = fondo / profundidad
#   Z+ = altura
#   Frente funcional = Y-
#
# CONVENCIÓN DE LA MATRIZ 2D (sólo pantalla / filas):
#   X = ancho interior, crece de izquierda a derecha.
#   Y = filas de la matriz, crece de abajo hacia arriba.
#
# IMPORTANTE: la "Y" de la matriz es SOLO una convención cartesiana 2D
# para nombrar filas. En el espacio 3D se proyecta sobre Z (altura).
# La profundidad física es Y, nunca la altura. Internamente las celdas
# resueltas usan (x, z, w, h), donde z es la elevación física.
#
# Coordenadas de usuario:
#   (x1,y1), (x2,y1), (x2.1,y1), (x2.1,y1.2), ...
# =====================================================================

import copy
import json
import math

import vdo_reengrose as VDO_RE


VERSION = 2
AXIS_X = "X"
AXIS_Y = "Y"
EPS = 1e-7


class LayoutError(ValueError):
    """Error de validación de la matriz de vanos."""


def _to_float(valor):
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _sufijo_id(track_id, prefijo):
    texto = str(track_id or "")
    if texto.startswith(prefijo):
        texto = texto[len(prefijo):]
    return texto or "1"


def _id_unico(prefijo, existentes):
    usados = {str(x) for x in existentes}
    n = 1
    while f"{prefijo}{n}" in usados:
        n += 1
    return f"{prefijo}{n}"


def cavidad_interior(alto, ancho, espesor):
    """Devuelve la cavidad libre interior del COCO.

    Laterales, base y tapa consumen un espesor por cada cara, independiente
    de si la tapa/base son internas o externas.
    """
    t = max(0.0, float(espesor))
    ancho = max(0.0, float(ancho))
    alto = max(0.0, float(alto))
    return {
        "x0": t,
        "z0": t,
        "ancho": max(0.0, ancho - 2.0 * t),
        "alto": max(0.0, alto - 2.0 * t),
    }


class Track:
    """Columna o fila de la matriz raíz."""

    def __init__(self, track_id, fixed=None):
        self.id = str(track_id)
        self.fixed = _to_float(fixed)

    def to_dict(self):
        return {"id": self.id, "fixed": self.fixed}

    @classmethod
    def from_dict(cls, data, prefijo, indice):
        if isinstance(data, str):
            return cls(data)
        return cls(
            data.get("id") or f"{prefijo}{indice + 1}",
            data.get("fixed"),
        )

    def copy(self):
        return Track(self.id, self.fixed)


class Cell:
    """Vano de la matriz y, recursivamente, sus subdivisiones."""

    def __init__(self, px="1", py="1", fixed=None, axis=None,
                 children=None):
        self.px = str(px)
        self.py = str(py)
        self.fixed = _to_float(fixed)
        self.axis = axis if axis in (AXIS_X, AXIS_Y) else None
        self.children = list(children or [])

    @property
    def label(self):
        return f"(x{self.px}, y{self.py})"

    def to_dict(self):
        data = {
            "px": self.px,
            "py": self.py,
            "fixed": self.fixed,
        }
        if self.axis and self.children:
            data["axis"] = self.axis
            data["children"] = [c.to_dict() for c in self.children]
        return data

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            return cls()
        children = [
            cls.from_dict(c) for c in data.get("children", [])
            if isinstance(c, dict)
        ]
        axis = data.get("axis")
        if axis not in (AXIS_X, AXIS_Y):
            axis = None
        if not children:
            axis = None
        return cls(
            px=data.get("px", "1"),
            py=data.get("py", "1"),
            fixed=data.get("fixed"),
            axis=axis,
            children=children,
        )

    def copy(self):
        return Cell.from_dict(self.to_dict())


class Layout:
    """Matriz raíz de columnas/filas con contenido anidado por celda."""

    def __init__(self, columns=None, rows=None, cells=None):
        self.columns = list(columns or [Track("x1")])
        self.rows = list(rows or [Track("y1")])
        self.cells = dict(cells or {})
        self._normalizar()

    # -----------------------------------------------------------------
    # Normalización / serialización
    # -----------------------------------------------------------------
    @staticmethod
    def key(col_id, row_id):
        return f"{col_id}|{row_id}"

    def _normalizar(self):
        if not self.columns:
            self.columns = [Track("x1")]
        if not self.rows:
            self.rows = [Track("y1")]

        vistos = set()
        columnas = []
        for i, col in enumerate(self.columns):
            if isinstance(col, str):
                col = Track(col)
            elif isinstance(col, dict):
                col = Track.from_dict(col, "x", i)
            if col.id in vistos:
                col.id = _id_unico("x", vistos)
            vistos.add(col.id)
            columnas.append(col)
        self.columns = columnas

        vistos = set()
        filas = []
        for i, row in enumerate(self.rows):
            if isinstance(row, str):
                row = Track(row)
            elif isinstance(row, dict):
                row = Track.from_dict(row, "y", i)
            if row.id in vistos:
                row.id = _id_unico("y", vistos)
            vistos.add(row.id)
            filas.append(row)
        self.rows = filas

        nuevas = {}
        for col in self.columns:
            for row in self.rows:
                k = self.key(col.id, row.id)
                cell = self.cells.get(k)
                if not isinstance(cell, Cell):
                    cell = Cell.from_dict(cell or {})
                    cell.px = _sufijo_id(col.id, "x")
                    cell.py = _sufijo_id(row.id, "y")
                    cell.fixed = None
                nuevas[k] = cell
        self.cells = nuevas

    def to_dict(self):
        return {
            "version": VERSION,
            "columns": [c.to_dict() for c in self.columns],
            "rows": [r.to_dict() for r in self.rows],
            "cells": {
                k: cell.to_dict()
                for k, cell in self.cells.items()
            },
        }

    def dumps(self):
        return json.dumps(
            self.to_dict(), ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            return cls()
        columns = [
            Track.from_dict(c, "x", i)
            for i, c in enumerate(data.get("columns", []))
        ] or [Track("x1")]
        rows = [
            Track.from_dict(r, "y", i)
            for i, r in enumerate(data.get("rows", []))
        ] or [Track("y1")]

        cells = {}
        raw_cells = data.get("cells", {})
        if isinstance(raw_cells, dict):
            for k, value in raw_cells.items():
                cells[k] = Cell.from_dict(value)
        elif isinstance(raw_cells, list):
            for i, value in enumerate(raw_cells):
                if not isinstance(value, dict):
                    continue
                cell = Cell.from_dict(value)
                if i < len(columns) * len(rows):
                    col = columns[i % len(columns)]
                    row = rows[i // len(columns)]
                    cells[cls.key(col.id, row.id)] = cell
        return cls(columns=columns, rows=rows, cells=cells)

    @classmethod
    def loads(cls, texto):
        if not texto or not str(texto).strip():
            return cls()
        try:
            data = json.loads(texto)
            return cls.from_dict(data)
        except (TypeError, ValueError, KeyError, AttributeError):
            return cls()

    def copy(self):
        return Layout.from_dict(self.to_dict())

    # -----------------------------------------------------------------
    # Matriz raíz
    # -----------------------------------------------------------------
    def add_column(self, fixed=None):
        col = Track(_id_unico("x", [c.id for c in self.columns]), fixed)
        self.columns.append(col)
        for row in self.rows:
            self.cells[self.key(col.id, row.id)] = Cell(
                px=_sufijo_id(col.id, "x"),
                py=_sufijo_id(row.id, "y"),
            )
        return col

    def remove_column(self):
        if len(self.columns) <= 1:
            return False
        col = self.columns.pop()
        for row in self.rows:
            self.cells.pop(self.key(col.id, row.id), None)
        return True

    def add_row(self, fixed=None):
        row = Track(_id_unico("y", [r.id for r in self.rows]), fixed)
        self.rows.append(row)
        for col in self.columns:
            self.cells[self.key(col.id, row.id)] = Cell(
                px=_sufijo_id(col.id, "x"),
                py=_sufijo_id(row.id, "y"),
            )
        return row

    def remove_row(self):
        if len(self.rows) <= 1:
            return False
        row = self.rows.pop()
        for col in self.columns:
            self.cells.pop(self.key(col.id, row.id), None)
        return True

    def set_column_fixed(self, index, fixed):
        if 0 <= index < len(self.columns):
            self.columns[index].fixed = _to_float(fixed)

    def set_row_fixed(self, index, fixed):
        if 0 <= index < len(self.rows):
            self.rows[index].fixed = _to_float(fixed)

    def get_cell(self, col_index, row_index):
        if not (0 <= col_index < len(self.columns)
                and 0 <= row_index < len(self.rows)):
            return None
        col = self.columns[col_index]
        row = self.rows[row_index]
        return self.cells.get(self.key(col.id, row.id))

    def _celdas_arbol(self, cell):
        yield cell
        for child in getattr(cell, "children", []):
            for item in self._celdas_arbol(child):
                yield item

    def column_has_subtree(self, index):
        if not (0 <= index < len(self.columns)):
            return False
        for j in range(len(self.rows)):
            cell = self.get_cell(index, j)
            if cell and (cell.axis or cell.children):
                return True
        return False

    def row_has_subtree(self, index):
        if not (0 <= index < len(self.rows)):
            return False
        for i in range(len(self.columns)):
            cell = self.get_cell(i, index)
            if cell and (cell.axis or cell.children):
                return True
        return False

    # -----------------------------------------------------------------
    # Subdivisiones anidadas
    # -----------------------------------------------------------------
    @staticmethod
    def _etiquetas_hijos(cell, axis, count):
        if axis == AXIS_X:
            return [(f"{cell.px}.{k + 1}", cell.py) for k in range(count)]
        return [(cell.px, f"{cell.py}.{k + 1}") for k in range(count)]

    def set_split(self, cell, axis, count):
        if cell is None:
            return False
        if axis not in (AXIS_X, AXIS_Y):
            raise LayoutError("Eje de subdivisión inválido.")
        count = int(count)
        if count < 2 or count > 100:
            raise LayoutError("N debe estar entre 2 y 100.")
        if not (0 <= count <= 100):
            raise LayoutError("N inválido.")

        etiquetas = self._etiquetas_hijos(cell, axis, count)
        viejos = list(cell.children or [])
        mismo_eje = cell.axis == axis
        nuevos = []
        for k, (px, py) in enumerate(etiquetas):
            if mismo_eje and k < len(viejos):
                child = viejos[k]
                child.px = px
                child.py = py
                nuevos.append(child)
            else:
                nuevos.append(Cell(px=px, py=py))
        cell.axis = axis
        cell.children = nuevos
        return True

    def disable_split(self, cell):
        if cell is None:
            return False
        cell.axis = None
        cell.children = []
        return True

    def set_cell_fixed(self, cell, fixed):
        if cell is not None:
            cell.fixed = _to_float(fixed)

    def iter_all(self):
        for cell in self.cells.values():
            for item in self._celdas_arbol(cell):
                yield item

    def find_label(self, label):
        for cell in self.iter_all():
            if cell.label == label:
                return cell
        return None

    # -----------------------------------------------------------------
    # Migración desde EspaciosX / EspaciosY
    # -----------------------------------------------------------------
    @classmethod
    def from_legacy(cls, espacios_x="", espacios_y=""):
        warnings = []
        cols = _legacy_tracks(espacios_x, "X", warnings)
        rows = _legacy_tracks(espacios_y, "Y", warnings)
        layout = cls(columns=cols, rows=rows)
        if warnings:
            warnings.insert(
                0, "Migración legacy: se conservaron las divisiones raíz; "
                   "las subdivisiones antiguas no se pudieron mapear.")
        return layout, warnings


def _legacy_tracks(texto, eje, warnings):
    nodos = []
    if texto:
        try:
            data = json.loads(texto)
            if isinstance(data, list):
                nodos = data
        except (TypeError, ValueError):
            warnings.append(f"JSON legacy de {eje} inválido.")

    tracks = []
    for nodo in nodos:
        if not isinstance(nodo, dict):
            continue
        tipo = nodo.get("type", "fijo")
        if tipo == "iguales":
            count = max(1, int(nodo.get("count", 1) or 1))
            for _ in range(count):
                tracks.append(Track(f"_{len(tracks) + 1}", None))
            if nodo.get("children"):
                warnings.append(
                    f"{eje}: sub-árbol dentro de 'iguales' no migrado.")
        elif tipo == "fijo":
            tracks.append(Track(f"_{len(tracks) + 1}",
                                nodo.get("value", 0.0)))
        else:
            tracks.append(Track(f"_{len(tracks) + 1}", None))
        if nodo.get("children"):
            warnings.append(
                f"{eje}: sub-árbol de {nodo.get('id', '?')} no migrado.")

    prefijo = "x" if eje == "X" else "y"
    if not tracks:
        tracks = [Track(f"{prefijo}1", None)]
    else:
        for i, track in enumerate(tracks):
            track.id = f"{prefijo}{i + 1}"
    return tracks


# =====================================================================
# Resolución
# =====================================================================
class ResolvedTrack:
    def __init__(self, track, start, size, overflow=0.0,
                 clear_start=None, clear_size=None,
                 extra_izq=0.0, extra_der=0.0):
        self.track = track
        self.id = track.id
        self.fixed = track.fixed
        self.start = float(start)
        self.size = float(max(0.0, size))
        self.clear_start = float(
            start if clear_start is None else clear_start)
        self.clear_size = float(max(0.0, (
            size if clear_size is None else clear_size)))
        self.extra_izq = float(max(0.0, extra_izq))
        self.extra_der = float(max(0.0, extra_der))
        self.overflow = float(max(0.0, overflow))

    @property
    def end(self):
        return self.start + self.size

    @property
    def clear_end(self):
        return self.clear_start + self.clear_size

    @property
    def nominal_start(self):
        return self.start

    @property
    def nominal_size(self):
        return self.size

    def __repr__(self):
        return (f"ResolvedTrack({self.id}, start={self.start:.1f}, "
                f"size={self.size:.1f}, clear={self.clear_size:.1f}, "
                f"overflow={self.overflow:.1f})")


class ResolvedCell:
    def __init__(self, cell, x, z, w, h, level=0,
                 nominal_x=None, nominal_z=None,
                 nominal_w=None, nominal_h=None):
        self.cell = cell
        self.x = float(x)
        self.z = float(z)
        self.w = float(max(0.0, w))
        self.h = float(max(0.0, h))
        self.nominal_x = float(x if nominal_x is None else nominal_x)
        self.nominal_z = float(z if nominal_z is None else nominal_z)
        self.nominal_w = float(max(
            0.0, w if nominal_w is None else nominal_w))
        self.nominal_h = float(max(
            0.0, h if nominal_h is None else nominal_h))
        self.level = int(level)
        self.children = []

    @property
    def label(self):
        return self.cell.label

    @property
    def rect(self):
        return (self.x, self.z, self.w, self.h)

    @property
    def nominal_rect(self):
        return (self.nominal_x, self.nominal_z,
                self.nominal_w, self.nominal_h)

    def walk(self):
        yield self
        for child in self.children:
            for item in child.walk():
                yield item

    def __repr__(self):
        return (f"ResolvedCell({self.label}, x={self.x:.1f}, z={self.z:.1f}, "
                f"w={self.w:.1f}, h={self.h:.1f})")


class PanelPiece:
    """Panel interno resuelto en coordenadas locales del COCO."""

    def __init__(self, axis, role, path, x, z, w, h, thickness,
                 nombre=None):
        self.axis = axis
        self.role = role
        self.path = path
        self.x = float(x)
        self.z = float(z)
        self.w = float(max(0.0, w))
        self.h = float(max(0.0, h))
        self.thickness = float(max(0.0, thickness))
        self.nombre = nombre or f"Division_{axis}_{path}"

    def __repr__(self):
        return (f"PanelPiece({self.nombre}, {self.axis}, "
                f"x={self.x:.1f}, z={self.z:.1f}, "
                f"w={self.w:.1f}, h={self.h:.1f})")


class ResolvedLayout:
    def __init__(self, inner_w, inner_h, thickness, columns, rows,
                 cells, pieces, warnings):
        self.inner_w = float(inner_w)
        self.inner_h = float(inner_h)
        self.thickness = float(thickness)
        self.columns = columns
        self.rows = rows
        self.cells = cells
        self.pieces = pieces
        self.warnings = list(warnings)
        self.overflow = (
            any(c.overflow > EPS for c in columns)
            or any(r.overflow > EPS for r in rows)
            or any("no cabe" in w.lower() or "excede" in w.lower()
                   for w in warnings)
        )

    def walk_cells(self):
        for cell in self.cells:
            for item in cell.walk():
                yield item

    def total_panels(self):
        return len(self.pieces)

    def summary(self):
        lineas = [
            f"Matriz {len(self.columns)} × {len(self.rows)}",
            f"Interior: {self.inner_w:.1f} × {self.inner_h:.1f} mm",
            f"Paneles internos: {len(self.pieces)}",
        ]
        if self.overflow:
            lineas.append("⚠ Hay medidas que no caben.")
        for warning in self.warnings:
            lineas.append("⚠ " + warning)
        return "\n".join(lineas)


def _extras_modificador(reengroses, clave, espesor):
    mod = (reengroses or {}).get(clave)
    if not mod:
        return (0.0, 0.0)
    try:
        return VDO_RE.extras_por_cara(mod, espesor)
    except Exception:
        return (0.0, 0.0)


def _extras_borde(reengroses, clave, espesor):
    positivo, negativo = _extras_modificador(reengroses, clave, espesor)
    return (negativo, positivo)


def _extra_shell(reengroses, clave, espesor, lado):
    positivo, negativo = _extras_modificador(reengroses, clave, espesor)
    if lado in ("izquierda", "inferior"):
        return positivo
    return negativo


def _resolver_track(tracks, total, espesor, etiqueta, warnings,
                    extras_internos=None, extra_borde_izq=0.0,
                    extra_borde_der=0.0):
    n = len(tracks)
    total = max(0.0, float(total))
    espesor = max(0.0, float(espesor))
    extras_internos = list(extras_internos or [])
    separadores = max(0, n - 1) * espesor
    disponible = total - separadores

    if disponible < -EPS:
        warnings.append(
            f"{etiqueta}: el espesor de los separadores "
            f"({separadores:.1f} mm) excede el espacio ({total:.1f} mm).")
        disponible = 0.0

    fijos = []
    for track in tracks:
        if track.fixed is None:
            fijos.append(None)
        else:
            valor = float(track.fixed)
            if valor < 0:
                warnings.append(
                    f"{etiqueta}/{track.id}: medida fija negativa; se usa 0.")
                valor = 0.0
            fijos.append(valor)

    suma_fijos = sum(v for v in fijos if v is not None)
    overflow = 0.0

    if suma_fijos > disponible + EPS:
        overflow = suma_fijos - disponible
        warnings.append(
            f"{etiqueta}: las medidas fijas ({suma_fijos:.1f} mm) "
            f"exceden el espacio útil ({disponible:.1f} mm).")
        factor = disponible / suma_fijos if suma_fijos > 0 else 0.0
        fijos = [None if v is None else v * factor for v in fijos]
        suma_fijos = disponible

    libres = [i for i, v in enumerate(fijos) if v is None]
    if libres:
        resto = max(0.0, disponible - suma_fijos)
        cuota = resto / len(libres)
        tamanos = [cuota if v is None else v for v in fijos]
    elif fijos:
        tamanos = list(fijos)
        tamanos[-1] += max(0.0, disponible - suma_fijos)
    else:
        tamanos = [0.0] * n

    resultado = []
    cursor = 0.0
    for i, track in enumerate(tracks):
        extra_izq = (
            float(extra_borde_izq) if i == 0
            else float(extras_internos[i - 1][1]))
        extra_der = (
            float(extra_borde_der) if i == n - 1
            else float(extras_internos[i][0]))
        neto = {"ancho": tamanos[i], "alto": 0.0}
        if extra_izq > EPS:
            neto = VDO_RE.calcular_vano_neto_con_reengrose(
                neto, {"lado_afectado": "izquierda",
                       "espesor_extra": extra_izq})
        if extra_der > EPS:
            neto = VDO_RE.calcular_vano_neto_con_reengrose(
                neto, {"lado_afectado": "derecha",
                       "espesor_extra": extra_der})
        clear_size = neto["ancho"]
        if tamanos[i] - extra_izq - extra_der < -EPS:
            warnings.append(
                f"{etiqueta}/{track.id}: el reengrose consume todo el vano.")
        resultado.append(ResolvedTrack(
            track, cursor, tamanos[i], overflow,
            clear_start=cursor + extra_izq,
            clear_size=clear_size,
            extra_izq=extra_izq,
            extra_der=extra_der))
        cursor += tamanos[i]
        if i < n - 1:
            cursor += espesor
    return resultado


def _resolver_celda(cell, x, z, w, h, espesor, pieces, warnings,
                    level, seq, nominal_x=None, nominal_z=None,
                    nominal_w=None, nominal_h=None, reengroses=None):
    nominal_x = x if nominal_x is None else nominal_x
    nominal_z = z if nominal_z is None else nominal_z
    nominal_w = w if nominal_w is None else nominal_w
    nominal_h = h if nominal_h is None else nominal_h
    resuelto = ResolvedCell(
        cell, x, z, w, h, level=level,
        nominal_x=nominal_x, nominal_z=nominal_z,
        nominal_w=nominal_w, nominal_h=nominal_h)
    if not cell.axis or not cell.children:
        return resuelto

    axis = cell.axis
    tracks = [
        Track(f"{cell.px}.{i + 1}" if axis == AXIS_X
              else f"{cell.py}.{i + 1}", child.fixed)
        for i, child in enumerate(cell.children)
    ]
    extras = []
    for i in range(1, len(tracks)):
        path = (f"x{cell.px}.{i + 1}" if axis == AXIS_X
                else f"y{cell.py}.{i + 1}")
        clave = f"division_{'x' if axis == AXIS_X else 'y'}:{path}"
        extras.append(_extras_borde(reengroses, clave, espesor))

    etiqueta = f"vano {cell.label} eje {axis}"
    total = nominal_w if axis == AXIS_X else nominal_h
    resueltos = _resolver_track(
        tracks, total, espesor, etiqueta, warnings, extras_internos=extras)

    for i, child in enumerate(cell.children):
        track = resueltos[i]
        if axis == AXIS_X:
            child_res = _resolver_celda(
                child, x + track.clear_start, z, track.clear_size, h,
                espesor, pieces, warnings, level + 1, seq,
                nominal_x=nominal_x + track.start,
                nominal_z=nominal_z,
                nominal_w=track.size,
                nominal_h=nominal_h,
                reengroses=reengroses)
        else:
            child_res = _resolver_celda(
                child, x, z + track.clear_start, w, track.clear_size,
                espesor, pieces, warnings, level + 1, seq,
                nominal_x=nominal_x,
                nominal_z=nominal_z + track.start,
                nominal_w=nominal_w,
                nominal_h=track.size,
                reengroses=reengroses)
        resuelto.children.append(child_res)

    for i in range(1, len(resueltos)):
        prev = resueltos[i - 1]
        path = (f"x{cell.px}.{i + 1}" if axis == AXIS_X
                else f"y{cell.py}.{i + 1}")
        safe = path.replace(".", "_")
        seq[0] += 1
        if axis == AXIS_X:
            pieces.append(PanelPiece(
                AXIS_X, "nested", path,
                nominal_x + prev.end, nominal_z,
                espesor, nominal_h, espesor,
                f"Division_X_{safe}_{seq[0]:03d}"))
        else:
            pieces.append(PanelPiece(
                AXIS_Y, "nested", path,
                nominal_x, nominal_z + prev.end,
                nominal_w, espesor, espesor,
                f"Repisa_Y_{safe}_{seq[0]:03d}"))
    return resuelto


def resolve_layout(layout, inner_w, inner_h, thickness, reengroses=None):
    """Resuelve la matriz completa y devuelve cajas/paneles locales.

    ``reengroses`` es un dict clave_pieza -> modificador. Las divisiones y
    laterales con reengrose reducen la luz clara del vano afectado; la
    geometria nominal queda disponible para el recorte/mocheo de repisas.
    """
    if isinstance(layout, str):
        layout = Layout.loads(layout)
    if not isinstance(layout, Layout):
        layout = Layout()
    if isinstance(layout.to_dict().get("cells"), dict):
        layout._normalizar()

    inner_w = max(0.0, float(inner_w))
    inner_h = max(0.0, float(inner_h))
    thickness = max(0.0, float(thickness))
    reengroses = reengroses or {}
    warnings = []

    extra_izq = _extra_shell(
        reengroses, "lateral_izquierdo", thickness, "izquierda")
    extra_der = _extra_shell(
        reengroses, "lateral_derecho", thickness, "derecha")
    extra_inf = _extra_shell(
        reengroses, "base", thickness, "inferior")
    extra_sup = _extra_shell(
        reengroses, "techo", thickness, "superior")

    extras_columnas = [
        _extras_borde(
            reengroses, f"division_x:x{i + 1}", thickness)
        for i in range(1, len(layout.columns))
    ]
    extras_filas = [
        _extras_borde(
            reengroses, f"division_y:y{j + 1}", thickness)
        for j in range(1, len(layout.rows))
    ]

    columns = _resolver_track(
        layout.columns, inner_w, thickness, "columnas", warnings,
        extras_internos=extras_columnas,
        extra_borde_izq=extra_izq,
        extra_borde_der=extra_der)
    rows = _resolver_track(
        layout.rows, inner_h, thickness, "filas", warnings,
        extras_internos=extras_filas,
        extra_borde_izq=extra_inf,
        extra_borde_der=extra_sup)

    pieces = []
    seq = [0]

    for i in range(1, len(columns)):
        prev = columns[i - 1]
        seq[0] += 1
        pieces.append(PanelPiece(
            AXIS_X, "root", f"x{i + 1}",
            prev.end, 0.0, thickness, inner_h, thickness,
            f"Division_X_col_{i + 1:03d}"))

    for j in range(1, len(rows)):
        prev = rows[j - 1]
        for i, col in enumerate(columns):
            seq[0] += 1
            pieces.append(PanelPiece(
                AXIS_Y, "root", f"y{j + 1}_x{i + 1}",
                col.start, prev.end, col.size, thickness, thickness,
                f"Repisa_Y_row_{j + 1:03d}_col_{i + 1:03d}"))

    cells = []
    for row in rows:
        for col in columns:
            cell = layout.cells.get(Layout.key(col.id, row.id))
            if cell is None:
                continue
            cells.append(_resolver_celda(
                cell, col.clear_start, row.clear_start,
                col.clear_size, row.clear_size,
                thickness, pieces, warnings, 0, seq,
                nominal_x=col.start, nominal_z=row.start,
                nominal_w=col.size, nominal_h=row.size,
                reengroses=reengroses))

    return ResolvedLayout(
        inner_w, inner_h, thickness, columns, rows, cells, pieces, warnings)
