# -*- coding: utf-8 -*-
"""Verificacion empirica de los fundamentos del Plan Fase 0/1 (nucleo).

Respalda los hallazgos F-3, F-13, F-14, F-15, F-16 y F-24 de
docs/06_AUDITORIA_PLAN_FASE0_FASE1.md.

Uso:   FreeCADCmd tools/vdo_verify_fase1_nucleo.py
Salida: /tmp/vdo_verify_nucleo.log  (y stdout al salir limpiamente)

NOTA DE METODO: en FreeCADCmd, print() no llega a stdout y
App.Console.PrintMessage solo se vacia al salir limpiamente. Si el proceso
se cuelga se pierde todo. Por eso se escribe a fichero con flush por linea.
"""

import traceback

import FreeCAD as App

LOG = "/tmp/vdo_verify_nucleo.log"
_lineas = []


def p(msg):
    _lineas.append(str(msg))
    with open(LOG, "a") as fh:
        fh.write(str(msg) + "\n")
        fh.flush()


def ok(titulo, valor):
    p("[%s] %s -> %r" % ("OK " if valor else "NO ", titulo, valor))


class Proxy:
    pass


def main():
    doc = App.newDocument("verify_nucleo")

    # ---- F-13: App::DocumentObjectGroupPython no tiene Placement ----
    p("\n=== F-13 ¿App::DocumentObjectGroupPython sirve como ESPACIO? ===")
    g = doc.addObject("App::DocumentObjectGroupPython", "GrpPy")
    g.Proxy = Proxy()
    p("    TypeId = %s" % g.TypeId)
    p("    props  = %s" % list(g.PropertiesList))
    ok("tiene Placement (CS local)", hasattr(g, "Placement"))
    ok("tiene Shape (Source de TechDraw)", hasattr(g, "Shape"))
    ok("es App::GeoFeature", g.isDerivedFrom("App::GeoFeature"))

    # ---- F-14: PropertyLength clampa los negativos ----
    p("\n=== F-14 NPT negativo: PropertyLength vs PropertyDistance ===")
    f = doc.addObject("App::FeaturePython", "Props")
    f.addProperty("App::PropertyLength", "Largo")
    f.addProperty("App::PropertyDistance", "Cota")
    f.Largo = -150.0
    f.Cota = -150.0
    p("    PropertyLength   = -150 -> %s" % f.Largo)
    p("    PropertyDistance = -150 -> %s" % f.Cota)
    ok("PropertyLength conserva el negativo", float(f.Largo) == -150.0)
    ok("PropertyDistance conserva el negativo", float(f.Cota) == -150.0)

    # ---- F-24: texto multilinea ----
    p("\n=== F-24 NotasInstalacion: texto multilinea ===")
    f.addProperty("App::PropertyString", "Notas")
    f.addProperty("App::PropertyStringList", "NotasLista")
    f.Notas = "linea 1\nlinea 2"
    f.NotasLista = ["linea 1", "linea 2"]
    p("    PropertyString con \\n     -> %r" % f.Notas)
    p("    PropertyStringList        -> %r" % f.NotasLista)
    ok("PropertyString conserva el salto de linea", "\n" in f.Notas)

    # ---- F-15: metadatos a nivel de documento ----
    p("\n=== F-15 ¿Donde viven los metadatos de proyecto? ===")
    try:
        m = doc.Meta
        m["VDO_Proyecto"] = "Residencia Alfa"
        doc.Meta = m
        ok("doc.Meta persiste (reasignando el dict)",
           doc.Meta.get("VDO_Proyecto") == "Residencia Alfa")
    except Exception as exc:
        p("[NO ] doc.Meta -> %s: %s" % (type(exc).__name__, exc))
    try:
        doc.VDO_Proyecto = "X"
        ok("doc.VDO_Proyecto (propiedad dinamica de documento)", True)
    except Exception as exc:
        p("[NO ] doc.VDO_Proyecto -> %s: %s" % (type(exc).__name__, exc))

    # ---- F-16: allowObject no se respeta por script ----
    p("\n=== F-16 ¿Se pueden 'proteger' los sub-contenedores por tipo? ===")

    class SoloMuros:
        def allowObject(self, grp, obj):
            return "Muro" in obj.Name

    g2 = doc.addObject("App::DocumentObjectGroupPython", "SoloMuros")
    g2.Proxy = SoloMuros()
    intruso = doc.addObject("Part::Box", "Intruso")
    g2.addObject(intruso)
    p("    contenido tras addObject(Intruso): %s" % [o.Name for o in g2.Group])
    ok("addObject por script respeta allowObject", len(g2.Group) == 0)

    # ---- F-3: propagacion de Placement ----
    p("\n=== F-3 ¿Hay sistema de coordenadas local? ===")
    esp = doc.addObject("Part::FeaturePython", "Espacio")
    esp.Proxy = Proxy()
    esp.addProperty("App::PropertyLinkListChild", "Mobiliario", "Espacio", "hijos")
    ok("addProperty App::PropertyLinkListChild", hasattr(esp, "Mobiliario"))
    hijo = doc.addObject("Part::Box", "Hijo")
    esp.Mobiliario = [hijo]
    esp.Placement.Base = App.Vector(1000, 0, 0)
    doc.recompute()
    p("    Espacio a x=1000 -> Hijo.Placement.Base = %s" % hijo.Placement.Base)
    ok("Placement NO se propaga con enlaces (esperado)", hijo.Placement.Base.x == 0)

    esp2 = doc.addObject("Part::FeaturePython", "EspacioGeo")
    esp2.Proxy = Proxy()
    esp2.addExtension("App::GeoFeatureGroupExtensionPython")
    ok("addExtension GeoFeatureGroupExtensionPython",
       esp2.hasExtension("App::GeoFeatureGroupExtension"))
    p("    props tras la extension: %s" % list(esp2.PropertiesList))
    hijo2 = doc.addObject("Part::Box", "HijoGeo")
    esp2.Group = [hijo2]
    esp2.Placement.Base = App.Vector(2000, 0, 0)
    doc.recompute()
    glob = hijo2.getGlobalPlacement()
    p("    HijoGeo.Placement.Base       = %s  (local)" % hijo2.Placement.Base)
    p("    HijoGeo.getGlobalPlacement() = %s  (global)" % glob.Base)
    ok("GeoFeatureGroup da CS local real", abs(glob.Base.x - 2000) < 1e-6)

    App.closeDocument(doc.Name)
    p("\n--- fin verificacion nucleo ---")


with open(LOG, "w") as _fh:
    _fh.write("")
try:
    main()
except Exception:
    p("EXC:\n" + traceback.format_exc())
App.Console.PrintMessage("\n".join(_lineas) + "\n")
