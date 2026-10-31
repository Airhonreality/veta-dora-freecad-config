# -*- coding: utf-8 -*-
# =====================================================================
# VDO/cam/vdo_cam_dossier.py
# Motor de dossier: láminas de un VDO_Espacio (docs/07 E-4, docs/08 §9.5).
#
# Uso:  generar_dossier(doc, espacio) -> [paginas]
#
# Reglas (DOS-*):
#   - No lee App.ActiveDocument: recibe el documento (DOS-01).
#   - Orden: página -> plantilla -> recompute -> vistas (DOS-11).
#   - Escala: Automatic -> recompute -> snap hacia abajo a la serie
#     normalizada D-3 (DOS-09). Nunca se calcula desde BoundBox 3D.
#   - Comprobación de cabida en el marco de la vista (DOS-15): se rota
#     una copia de la geometría al marco de la vista y se proyecta en Z.
#   - Un dossier = una transacción (DOS-13).
#   - Las fuentes de cada vista son objetos con Shape real; las piezas
#     que no tienen geometría (Espacio, COCO con Shape nula) se recorren
#     por sus Hijos (DOS-18: sin fuentes, la hoja no se crea).
# =====================================================================

import html
import json
import os
import re

import FreeCAD as App
import Part

from VDO._paths import TEMPLATES_DIR, get_template_area_util, get_template_path
from VDO.hub.vdo_hub_registry import resolver_modulo
from VDO.shared.vdo_shared_familias import clasificar_hijo
from VDO.shared.vdo_shared_fachadas import es_fachada

# Decisión D-3 (docs/04 ADR-006): serie ISO 5455 + 1:25; sin 1:15.
ESCALAS_NORMALIZADAS = (1.0, 0.5, 0.2, 0.1, 0.05, 0.04, 0.02, 0.01)

PLANTILLA_SVG = "vdo_template_a3.svg"
CATALOGO_LAMINAS = TEMPLATES_DIR / "laminas_dossier.json"


# ---------------------------------------------------------------------
# Escala
# ---------------------------------------------------------------------
def snap_abajo(escala):
    """Primera escala normalizada menor o igual que `escala`."""
    for e in ESCALAS_NORMALIZADAS:
        if e <= escala + 1e-12:
            return e
    return ESCALAS_NORMALIZADAS[-1]


def siguiente_abajo(escala):
    """Escala normalizada inmediatamente menor que `escala`."""
    for e in ESCALAS_NORMALIZADAS:
        if e < escala - 1e-12:
            return e
    return ESCALAS_NORMALIZADAS[-1]


def _unitario(v):
    """Vector unitario nuevo (Base.Vector.normalize() es in situ)."""
    vec = App.Vector(*v)
    vec.normalize()
    return vec


def _aristas_visibles_en_vista(shapes, direction, xdir):
    """Aristas visibles proyectadas en el plano de la vista (z = 0).

    Rota una copia de la geometría al marco (x=xdir, z=direction) y proyecta
    a lo largo de Z (DOS-15). No usa BoundBox 3D ni project() crudo.
    """
    import TechDraw
    z = _unitario(direction)
    x = _unitario(xdir)
    y = z.cross(x)
    marco = App.Rotation(x, y, z, "ZXY")
    compuesto = Part.makeCompound(shapes).copy()
    compuesto.Placement = App.Placement(App.Vector(), marco.inverted())
    return TechDraw.project(compuesto, App.Vector(0, 0, 1))[0]


def extent_en_vista(shapes, direction, xdir):
    """Extensión (X, Y) de la proyección dentro del marco de la vista."""
    bb = _aristas_visibles_en_vista(shapes, direction, xdir).BoundBox
    return bb.XLength, bb.YLength


# ---------------------------------------------------------------------
# Selección de fuentes
# ---------------------------------------------------------------------
def _fuentes(obj):
    """Objetos con geometría real que representan `obj`.

    Si `obj` tiene Shape no nula, es una fuente. Si no (Espacio, COCO con
    Shape nula, T5), se recorren sus Hijos.
    """
    shape = getattr(obj, "Shape", None)
    if shape is not None and not shape.isNull() and shape.Solids:
        return [obj]
    salida = []
    for hijo in (getattr(obj, "Hijos", None) or []):
        salida.extend(_fuentes(hijo))
    return salida


def _sin_duplicados(objetos):
    vistos, salida = set(), []
    for o in objetos:
        if o.Name not in vistos:
            vistos.add(o.Name)
            salida.append(o)
    return salida


def fuentes_planta(espacio):
    """Hoja A: arquitectura y mobiliario del espacio, en sus sólidos reales."""
    fuentes = []
    for hijo in (getattr(espacio, "Hijos", None) or []):
        if clasificar_hijo(hijo) in ("arquitectura", "mobiliario"):
            fuentes.extend(_fuentes(hijo))
    return _sin_duplicados(fuentes)


def fuentes_sin_fachadas(objetos):
    """Fuentes de un mueble quitando frentes (vista «vanos libres»)."""
    return [f for f in objetos if not es_fachada(f)]


def mobiliario_del_espacio(espacio):
    """Muebles del espacio: un dossier con ficha por cada uno (DOS-05)."""
    return [h for h in (getattr(espacio, "Hijos", None) or [])
            if clasificar_hijo(h) == "mobiliario" and _fuentes(h)]


# ---------------------------------------------------------------------
# Catálogo y membrete
# ---------------------------------------------------------------------
def cargar_catalogo(ruta=CATALOGO_LAMINAS):
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)["laminas"]


def _proyecto_de(doc):
    for o in doc.Objects:
        if getattr(o, "VDO_Tipo", "") == "ProyectoFeature":
            return o
    return None


def _textos_membrete(doc, espacio, lamina, indice):
    proyecto = _proyecto_de(doc)
    nivel = float(getattr(espacio, "NivelPiso", 0.0) or 0.0)
    return {
        "vdo_proyecto": str(getattr(proyecto, "Nombre", "") or ""),
        "vdo_cliente": str(getattr(proyecto, "Cliente", "") or ""),
        "vdo_espacio": str(getattr(espacio, "NombreEspacio", "")
                           or espacio.Label),
        "vdo_lamina": "%s-%s-%02d" % (
            str(getattr(espacio, "CodigoZona", "") or "SIN"),
            lamina["tipo"], indice),
        "vdo_npt": "NPT %+.0f mm" % nivel,
    }


# ---------------------------------------------------------------------
# Construcción de una hoja
# ---------------------------------------------------------------------
def _crear_pagina(doc, nombre):
    """Página + plantilla en el orden obligatorio (DOS-11)."""
    import TechDraw  # noqa: F401  (registra los tipos TechDraw::*)
    page = doc.addObject("TechDraw::DrawPage", nombre)
    tpl = doc.addObject("TechDraw::DrawSVGTemplate", nombre + "_Tpl")
    tpl.Template = get_template_path(PLANTILLA_SVG)
    page.Template = tpl
    doc.recompute()
    page.KeepUpdated = False  # DOS-12: sin N recomputos durante el montaje
    return page, tpl


def _area_dibujable():
    """(x0, y0_svg, x1, y1_svg) del área de dibujo: útil menos cabecera.

    Coordenadas de la plantilla (origen superior izquierdo).
    """
    datos = get_template_area_util()
    area = datos["util"]
    top = max(float(area["y0"]), float(datos.get("cabecera", 0)))
    return (float(area["x0"]), top, float(area["x1"]), float(area["y1"]))


def _util(tpl):
    """Área de dibujo desde la plantilla publicada (DOS-09), no hardcodeada."""
    x0, top, x1, bottom = _area_dibujable()
    return (x1 - x0, bottom - top, float(tpl.Width), float(tpl.Height))


def _montar_hoja(doc, page, tpl, nombre, vistas, anotacion=None):
    """Crea las vistas de una hoja con una escala común que cabe (DOS-06/09).

    `vistas` es una lista de dicts {id, direccion, xdir, fuentes, x, y}.
    Devuelve la escala común aplicada.
    """
    util_w, util_h, _, _ = _util(tpl)
    creadas = []
    for v in vistas:
        obj = doc.addObject("TechDraw::DrawViewPart", "%s_%s" % (nombre, v["id"]))
        page.addView(obj)
        obj.Source = v["fuentes"]
        obj.Direction = App.Vector(*v["direccion"])
        obj.XDirection = App.Vector(*v["xdir"])  # DOS-10
        obj.HardHidden = False
        obj.ScaleType = "Automatic"
        doc.recompute()
        creadas.append((obj, v))

    # Escala común: la más grande que cabe en todas las vistas.
    escala = min(snap_abajo(float(o.Scale)) for o, _ in creadas)
    while True:
        cabe = True
        for o, v in creadas:
            shapes = [f.Shape for f in v["fuentes"]]
            ex, ey = extent_en_vista(shapes, v["direccion"], v["xdir"])
            if ex * escala > util_w or ey * escala > util_h:
                cabe = False
                break
        if cabe or escala <= ESCALAS_NORMALIZADAS[-1] + 1e-12:
            break
        escala = siguiente_abajo(escala)

    for o, v in creadas:
        o.ScaleType = "Custom"
        o.Scale = escala
        o.X = float(v["x"])
        o.Y = float(v["y"])
    doc.recompute()

    if anotacion:
        an = doc.addObject("TechDraw::DrawViewAnnotation", nombre + "_Info")
        page.addView(an)
        an.Text = list(anotacion)
    return escala


def _lineas_despiece(fuentes):
    lineas = []
    for f in fuentes:
        lineas.append("%s  %.0f x %.0f x %.0f" % (
            f.Label,
            float(getattr(f, "Largo", 0.0) or 0.0),
            float(getattr(f, "Ancho", 0.0) or 0.0),
            float(getattr(f, "Espesor", 0.0) or 0.0)))
    return lineas or ["(sin piezas)"]


# ---------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------
def generar_dossier(doc, espacio, destino=None):
    """Genera todas las láminas del catálogo para `espacio`.

    Devuelve la lista de páginas creadas. Todo el montaje es una sola
    transacción: un `undo()` deshace el dossier completo (DOS-13).

    Si `destino` es una carpeta, cada lámina se exporta como SVG
    (`exportar_pagina_svg`) una vez terminado el montaje.
    """
    if doc is None or espacio is None:
        raise ValueError("generar_dossier requiere documento y espacio")
    catalogo = cargar_catalogo()
    paginas = []

    doc.openTransaction("Generar dossier VDO")
    try:
        for lamina in catalogo:
            if lamina["alcance"] == "espacio":
                fuentes = fuentes_planta(espacio)
                if not fuentes:
                    continue  # DOS-18: sin geometría, hoja omitida
                page, tpl = _crear_pagina(doc, "Dossier_%s" % lamina["tipo"])
                x_c, y_c = _centro_util(tpl)
                vistas = [{
                    "id": v["id"], "direccion": v["direccion"],
                    "xdir": v["xdir"], "fuentes": fuentes,
                    "x": x_c, "y": y_c,
                } for v in lamina["vistas"]]
                escala = _montar_hoja(doc, page, tpl,
                                      "Dossier_%s" % lamina["tipo"], vistas)
                _estampar(doc, tpl, espacio, lamina, 1, escala)
                paginas.append(page)
            elif lamina["alcance"] == "modulo":
                for indice, mueble in enumerate(
                        mobiliario_del_espacio(espacio), start=1):
                    todas = _fuentes(mueble)
                    nombre = "Dossier_%s_%02d" % (lamina["tipo"], indice)
                    page, tpl = _crear_pagina(doc, nombre)
                    x_c, y_c = _centro_util(tpl)
                    vistas = []
                    especificadas = [v for v in lamina["vistas"]
                                     if _fuentes_de_vista(v, todas)]
                    n = len(especificadas)
                    paso = _separacion(tpl, n)
                    for k, v in enumerate(especificadas):
                        dx = (k - (n - 1) / 2.0) * paso
                        vistas.append({
                            "id": v["id"], "direccion": v["direccion"],
                            "xdir": v["xdir"],
                            "fuentes": _fuentes_de_vista(v, todas),
                            "x": x_c + dx, "y": y_c,
                        })
                    if not vistas:
                        continue  # DOS-18
                    escala = _montar_hoja(
                        doc, page, tpl, nombre, vistas,
                        anotacion=["Mueble: %s" % mueble.Label]
                        + _lineas_despiece(fuentes))
                    _estampar(doc, tpl, espacio, lamina, indice, escala,
                              mueble=mueble)
                    paginas.append(page)
        for page in paginas:
            page.KeepUpdated = True  # DOS-12: al final del montaje
        doc.recompute()
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    if destino is not None:
        os.makedirs(destino, exist_ok=True)
        for page in paginas:
            exportar_pagina_svg(page, os.path.join(destino, page.Name + ".svg"))
    return paginas


def _rellenar_membrete(svg_plantilla, textos):
    """Sustituye el contenido de cada campo freecad:editable por su valor."""
    for clave, valor in textos.items():
        patron = re.compile(
            r'(freecad:editable="%s"[^>]*>)\s*<tspan>.*?</tspan>' % re.escape(clave),
            re.S)
        svg_plantilla = patron.sub(
            lambda m: m.group(1) + "<tspan>%s</tspan>" % html.escape(valor),
            svg_plantilla, count=1)
    return svg_plantilla


def _trazos_svg(v):
    """Aristas visibles de una vista como trazos SVG a su escala.

    Se proyecta la geometría con TechDraw.project en el marco de la vista
    (igual que la comprobación de cabida) y se discretiza cada arista. La
    escala de la vista se aplica aquí; el SVG se coloca con `translate`.
    """
    visibles = _aristas_visibles_en_vista(
        [f.Shape for f in v.Source], tuple(v.Direction), tuple(v.XDirection))
    esc = float(v.Scale)
    # X,Y de la vista = centro de su geometria: se centra aqui el bbox.
    bb = visibles.BoundBox
    cx, cy = (bb.XMin + bb.XMax) / 2.0, (bb.YMin + bb.YMax) / 2.0
    trazos = []
    for arista in visibles.Edges:
        puntos = arista.discretize(Distance=0.5)
        if len(puntos) < 2:
            continue
        orden = " ".join(
            "%s%.3f,%.3f" % ("M" if i == 0 else "L",
                             (p.x - cx) * esc, -(p.y - cy) * esc)
            for i, p in enumerate(puntos))
        trazos.append('<path d="%s" fill="none" stroke="#000000" '
                      'stroke-width="0.35"/>' % orden)
    return "\n".join(trazos)


def exportar_pagina_svg(page, ruta):
    """Escribe la lámina completa (membrete + vistas) como un SVG.

    FreeCADCmd no expone la exportación de página (vive en TechDrawGui), así
    que se compone aquí: la plantilla con sus campos rellenos y, encima, el
    grupo de geometría de cada vista (`TechDraw.viewPartAsSvg`) en su
    posición. Las coordenadas de página tienen origen inferior; el SVG, superior.
    """
    # Las vistas deben estar calculadas antes de leer su geometria.
    page.Document.recompute()
    tpl = page.Template
    with open(tpl.Template, encoding="utf-8") as fh:
        plantilla = fh.read()
    cuerpo = re.search(r"<svg[^>]*>(.*)</svg>", plantilla, re.S)
    cabecera = re.search(r"<svg[^>]*>", plantilla)
    textos = {k: str(v) for k, v in dict(tpl.EditableTexts).items()}
    cuerpo_svg = _rellenar_membrete(cuerpo.group(1), textos)
    alto = float(tpl.Height)

    partes = []
    for v in page.Views:
        if not v.isDerivedFrom("TechDraw::DrawViewPart"):
            continue
        geometria = _trazos_svg(v)
        if not geometria:
            raise RuntimeError("La vista %s no tiene geometria exportable"
                               % v.Name)
        x, y = float(v.X), float(v.Y)
        partes.append('<g transform="translate(%.3f,%.3f)">%s</g>'
                      % (x, alto - y, geometria))

    for an in page.Views:
        if not an.isDerivedFrom("TechDraw::DrawViewAnnotation"):
            continue
        x, y = float(an.X), float(an.Y)
        for i, linea in enumerate(an.Text or []):
            partes.append(
                '<text x="%.3f" y="%.3f" font-family="sans-serif" '
                'font-size="3.5" fill="#000000">%s</text>'
                % (x, alto - y - i * 4.5, html.escape(str(linea))))

    svg = ('<?xml version="1.0" encoding="UTF-8"?>\n%s\n%s\n%s\n</svg>\n'
           % (cabecera.group(0), cuerpo_svg, "\n".join(partes)))
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(svg)
    return ruta


def _centro_util(tpl):
    """Centro del área de dibujo en coordenadas de página (origen inferior)."""
    x0, top, x1, bottom = _area_dibujable()
    cx = (x0 + x1) / 2.0
    cy_svg = (top + bottom) / 2.0
    # La plantilla SVG tiene origen superior izquierdo; la página, inferior.
    return cx, float(tpl.Height) - cy_svg


def _fuentes_de_vista(vista, todas):
    """Fuentes de una vista según su política de fachadas (catálogo)."""
    if vista.get("fachadas", "visibles") == "ocultas":
        return fuentes_sin_fachadas(todas)
    return list(todas)


def _separacion(tpl, n):
    """Paso horizontal entre `n` vistas alineadas en una fila."""
    util_w, _, _, _ = _util(tpl)
    return util_w / float(max(n, 1))


def _estampar(doc, tpl, espacio, lamina, indice, escala, mueble=None):
    """Membrete: reasignación completa del diccionario (F-8) y escala leída."""
    textos = _textos_membrete(doc, espacio, lamina, indice)
    textos["vdo_escala"] = "1:%g" % round(1.0 / escala)
    datos = dict(tpl.EditableTexts)
    datos.update(textos)
    tpl.EditableTexts = datos
