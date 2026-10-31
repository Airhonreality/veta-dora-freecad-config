# -*- coding: utf-8 -*-
"""Verificacion empirica del motor TechDraw del Plan Fase 0/1.

Respalda los hallazgos F-8, F-9, F-10, F-17, F-20 y F-22 de
docs/06_AUDITORIA_PLAN_FASE0_FASE1.md, y valida el algoritmo de escala
normalizada que propone docs/07_CONTRAPLAN_FASE0_FASE1.md (E-4).

Uso:   FreeCADCmd tools/vdo_verify_fase1_techdraw.py
Salida: /tmp/vdo_verify_techdraw.log
"""

import os
import traceback

import FreeCAD as App

LOG = "/tmp/vdo_verify_techdraw.log"
_lineas = []

_TPL_CANDIDATAS = [
    "/usr/share/freecad/Mod/TechDraw/Templates/ISO/A3_Landscape_ISO5457_advanced.svg",
    "/usr/lib/freecad/Mod/TechDraw/Templates/ISO/A3_Landscape_ISO5457_advanced.svg",
]

# Escalas normalizadas. Decision D-3 de docs/07: serie ISO 5455 mas 1:25
# (no ISO, pero presente en escalimetros de arquitectura; cubre el salto
# 1:20 -> 1:50, grande para muebles altos). 1:15 queda fuera: ver F-18.
#        1:1  1:2  1:5  1:10 1:20  1:25  1:50  1:100
ESCALAS = [1.0, 0.5, 0.2, 0.1, 0.05, 0.04, 0.02, 0.01]

# Area util A3 = hoja menos margenes (20) menos membrete (180 de ancho).
UTIL_W, UTIL_H = 420 - 20 - 180, 297 - 20


def p(msg):
    _lineas.append(str(msg))
    with open(LOG, "a") as fh:
        fh.write(str(msg) + "\n")
        fh.flush()


def snap_abajo(escala):
    """Primera escala normalizada <= la calculada por TechDraw."""
    for e in ESCALAS:
        if e <= escala + 1e-12:
            return e
    return ESCALAS[-1]


def extent_exacta(shape, direction):
    """Extension real de la proyeccion. DrawViewPart.getBoundingBox() NO esta
    expuesto a Python (AttributeError), asi que se usa TechDraw.project."""
    import TechDraw
    visibles = TechDraw.project(shape, App.Vector(*direction))[0]
    bb = visibles.BoundBox
    return bb.XLength, bb.YLength


def main():
    tpl_path = next((c for c in _TPL_CANDIDATAS if os.path.isfile(c)), "")
    if not tpl_path:
        p("No se encontro plantilla ISO A3 de stock; abortando.")
        return
    doc = App.newDocument("verify_td")

    # ---- F-17: el BBox 3D es la magnitud equivocada ----
    p("\n=== F-17 BBox 3D vs proyeccion real (isometrica 1,-1,1) ===")
    p("    area util A3 = %.0f x %.0f mm" % (UTIL_W, UTIL_H))

    def escala_desde(ex, ey):
        for e in ESCALAS:
            if ex * e <= UTIL_W and ey * e <= UTIL_H:
                return e
        return ESCALAS[-1]

    for nombre, dims in [("COCO 600x580x720", (600, 580, 720)),
                         ("Armario 900x600x2400", (900, 600, 2400))]:
        bx = doc.addObject("Part::Box", "Tmp")
        bx.Length, bx.Width, bx.Height = dims
        doc.recompute()
        b3 = bx.Shape.BoundBox
        ex, ey = extent_exacta(bx.Shape, (1, -1, 1))
        s_plan = escala_desde(b3.XLength, b3.YLength)
        desborda = ex * s_plan > UTIL_W or ey * s_plan > UTIL_H
        p("    %s" % nombre)
        p("      bbox 3D (lo que usa el plan): %.1f x %.1f" % (b3.XLength, b3.YLength))
        p("      proyeccion real            : %.1f x %.1f" % (ex, ey))
        p("      escala del plan = 1:%-4g -> ocupa %.1f x %.1f mm => %s"
          % (1 / s_plan, ex * s_plan, ey * s_plan,
             "DESBORDA LA HOJA" if desborda else "cabe"))
        doc.removeObject(bx.Name)

    # ---- F-9: orden obligatorio de construccion ----
    p("\n=== F-9 Orden de construccion ===")
    page = doc.addObject("TechDraw::DrawPage", "Hoja")
    tpl = doc.addObject("TechDraw::DrawSVGTemplate", "Tpl")
    v0 = doc.addObject("TechDraw::DrawViewPart", "V0")
    try:
        page.addView(v0)
        p("    addView sin template -> no lanzo (inesperado)")
    except Exception as exc:
        p("    addView sin template -> %s: %s" % (type(exc).__name__, exc))
    p("    tpl.Width/Height antes del SVG: %s / %s" % (tpl.Width, tpl.Height))
    tpl.Template = tpl_path
    page.Template = tpl
    doc.recompute()
    p("    tpl.Width/Height tras el SVG  : %s / %s" % (tpl.Width, tpl.Height))
    campos = sorted(tpl.EditableTexts.keys())
    p("    campos freecad:editable (%d): %s" % (len(campos), campos))
    p("    page.KeepUpdated por defecto = %s" % page.KeepUpdated)

    # ---- E-4: Automatic + normalizacion ----
    p("\n=== E-4 ScaleType='Automatic' + snap a escala normalizada ===")
    for nombre, dims, direction, xdir in [
        ("COCO cenital", (600, 580, 720), (0, 0, 1), (1, 0, 0)),
        ("COCO iso", (600, 580, 720), (1, -1, 1), (1, 1, 0)),
        ("Armario iso", (900, 600, 2400), (1, -1, 1), (1, 1, 0)),
        ("Muro cenital", (3000, 150, 2400), (0, 0, 1), (1, 0, 0)),
    ]:
        bx = doc.addObject("Part::Box", "Tmp")
        bx.Length, bx.Width, bx.Height = dims
        doc.recompute()
        v = doc.addObject("TechDraw::DrawViewPart", "V")
        page.addView(v)
        v.Source = [bx]
        v.Direction = App.Vector(*direction)
        v.XDirection = App.Vector(*xdir)
        v.HardHidden = False
        v.ScaleType = "Automatic"
        doc.recompute()
        s_auto = float(v.Scale)
        v.ScaleType = "Custom"
        v.Scale = snap_abajo(s_auto)
        doc.recompute()
        p("    %-14s Automatic=1:%-6.2f -> normalizada 1:%-4g  X=%s Y=%s"
          % (nombre, 1 / s_auto, 1 / float(v.Scale), v.X, v.Y))
        doc.removeObject(v.Name)
        doc.removeObject(bx.Name)
    p("    (X=210 Y=148.5 es el centro exacto del A3: TechDraw ya centra)")

    # ---- F-8: EditableTexts hay que reasignarlo completo ----
    p("\n=== F-8 EditableTexts: mutacion en sitio vs reasignacion ===")
    clave = campos[0]
    original = tpl.EditableTexts.get(clave)
    tpl.EditableTexts[clave] = "MUTADO_EN_SITIO"
    p("    mutacion en sitio   -> %r (original %r)" % (tpl.EditableTexts.get(clave), original))
    d = tpl.EditableTexts
    d[clave] = "REASIGNADO"
    tpl.EditableTexts = d
    p("    reasignacion total  -> %r" % tpl.EditableTexts.get(clave))

    # ---- F-20 + F-22 ----
    p("\n=== F-20 escala leida de vuelta al membrete / F-22 DrawViewAnnotation ===")
    bx = doc.addObject("Part::Box", "Coco")
    bx.Length, bx.Width, bx.Height = 900, 600, 2400
    doc.recompute()
    v = doc.addObject("TechDraw::DrawViewPart", "Vfinal")
    page.addView(v)
    v.Source = [bx]
    v.Direction = App.Vector(1, -1, 1)
    v.XDirection = App.Vector(1, 1, 0)
    v.ScaleType = "Automatic"
    doc.recompute()
    v.ScaleType = "Custom"
    v.Scale = snap_abajo(float(v.Scale))
    doc.recompute()
    if "scale" in campos:
        d = tpl.EditableTexts
        d["scale"] = "1:%g" % (1 / float(v.Scale))
        tpl.EditableTexts = d
        p("    membrete 'scale' = %r (leido de v.Scale=%s tras el recompute final)"
          % (tpl.EditableTexts.get("scale"), v.Scale))
    an = doc.addObject("TechDraw::DrawViewAnnotation", "Despiece")
    page.addView(an)
    an.Text = ["Lateral Izq  720 x 580 x 18", "Base  600 x 580 x 18"]
    doc.recompute()
    p("    DrawViewAnnotation.Text = %r" % an.Text)
    p("    page.Views = %s" % [o.Name for o in page.Views])

    App.closeDocument(doc.Name)
    p("\n--- fin verificacion TechDraw (headless: TechDraw funciona sin GUI) ---")


with open(LOG, "w") as _fh:
    _fh.write("")
try:
    main()
except Exception:
    p("EXC:\n" + traceback.format_exc())
App.Console.PrintMessage("\n".join(_lineas) + "\n")
