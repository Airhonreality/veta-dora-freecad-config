#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vdo_verify.py - Arnes de verificacion de carga del workbench VDO.

Comprueba en niveles crecientes que el workbench REALMENTE carga y hace su
trabajo, no solo que los archivos existen:

  N1 ESTATICO  - invariantes del codigo y del paquete (sin arrancar FreeCAD)
  N2 CONSOLA   - freecadcmd ejecuta Init.py sin abortar
  N3 GUI       - freecad real registra, activa y expone los comandos
  N4 E2E       - crea un mueble por la toolbar, lo guarda y lo reabre
  N5 INSERTOS  - contenido de vano: piezas, pose, despiece y retirada

Del N3 en adelante se trabaja con sondas: macros autogeneradas que corren
en el FreeCAD real, escriben un JSON en .verif/ y cierran la ventana. El
metodo y como escribir una sonda nueva estan en docs/05 §5.

Uso:
    python3 vdo_verify.py              # N1 + N2
    python3 vdo_verify.py --gui        # N1 + N2 + N3 (abre FreeCAD ~20s)
    python3 vdo_verify.py --e2e        # + N4 y N5 (verificacion completa)
    python3 vdo_verify.py --insertos   # N1 + N2 + N3 + solo N5
    python3 vdo_verify.py --deploy     # sincroniza Macro/ -> Mod/ y verifica

Codigo de salida: 0 todo correcto, 1 algun fallo. Apto para gatillar CI.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

WB_NAME = "VDO_CarpinteriaParametrica"
CLASE_WB = "VDO_Workbench"
FUENTE = Path(__file__).resolve().parent.parent  # raiz del repo (tools/..)
def _comandos_declarados() -> list[str]:
    """Comandos que el workbench debe registrar, segun el catalogo.

    Antes esta lista estaba escrita a mano aqui y se habia quedado en 7
    de los 10 comandos reales: VDO_NuevoProyecto, VDO_Cajon y VDO_Puerta
    podian desaparecer del workbench sin que el arnes lo notara
    ("faltantes": []). Luego se leyo por AST de vdo_initgui.COMANDOS, que
    era una lista literal.
    
    Ahora COMANDOS se DERIVA de VDO.hub.vdo_hub_registry, asi que el
    arnes pregunta a la misma fuente. El registro es dato puro: se puede
    importar sin FreeCADGui, que es justo lo que este arnes necesita
    (comprueba el registro real arrancando FreeCAD en otro proceso).
    """
    if str(FUENTE) not in sys.path:
        sys.path.insert(0, str(FUENTE))
    try:
        from VDO.hub.vdo_hub_registry import nombres_comandos
    except Exception as exc:
        raise SystemExit(
            f"No se pudo leer el catalogo de modulos VDO ({exc}); "
            f"el arnes no puede saber que comandos verificar.")
    return list(nombres_comandos())


COMANDOS_ESPERADOS = _comandos_declarados()

fallos: list[str] = []
avisos: list[str] = []


def ok(msg):
    print(f"  \033[32mOK\033[0m   {msg}")


def fail(msg):
    print(f"  \033[31mFALLO\033[0m {msg}")
    fallos.append(msg)


def warn(msg):
    print(f"  \033[33mAVISO\033[0m {msg}")
    avisos.append(msg)


def titulo(t):
    print(f"\n\033[1m{t}\033[0m\n" + "-" * len(t))


# =====================================================================
# Localizacion de rutas (preguntando a FreeCAD, no adivinando)
# =====================================================================

def rutas_freecad() -> dict:
    """Obtiene UserAppDataDir y ResourceDir del propio FreeCAD."""
    script = "import FreeCAD,json;print('@@'+json.dumps({'user':FreeCAD.getUserAppDataDir(),'res':FreeCAD.getResourceDir()}))"
    tmp = Path("/tmp/_vdo_rutas.py")
    tmp.write_text(script)
    try:
        out = subprocess.run(["freecadcmd", str(tmp)], capture_output=True,
                             text=True, timeout=120).stdout
        for linea in out.splitlines():
            if linea.startswith("@@"):
                return json.loads(linea[2:])
    except Exception as e:
        fail(f"No se pudo consultar las rutas a FreeCAD: {e}")
    return {}


# =====================================================================
# N1 - ESTATICO
# =====================================================================

def nombres_en_codigo(archivo: Path) -> set[str]:
    """Nombres referenciados en el AST (los comentarios no cuentan)."""
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    return {n.id for n in ast.walk(arbol) if isinstance(n, ast.Name)}


def nivel1(instalado: Path) -> None:
    titulo("N1 ESTATICO - invariantes de codigo y paquete")

    if not instalado.is_dir():
        fail(f"No existe la instalacion: {instalado}")
        return
    ok(f"Instalacion presente: {instalado}")

    # -- Invariante 1: ni Init.py ni InitGui.py pueden USAR __file__ --
    for nombre in ("Init.py", "InitGui.py"):
        f = instalado / nombre
        if not f.is_file():
            fail(f"Falta {nombre}")
            continue
        try:
            if "__file__" in nombres_en_codigo(f):
                fail(f"{nombre} USA __file__ (FreeCAD no lo define -> NameError)")
            else:
                ok(f"{nombre} no usa __file__")
        except SyntaxError as e:
            fail(f"{nombre} no compila: {e}")

    # -- Invariante 2: InitGui.py no debe definir clases --
    # FreeCAD hace exec(code, globals, locals) con dicts distintos: los
    # metodos de una clase definida ahi no ven los helpers del modulo.
    ig = instalado / "InitGui.py"
    if ig.is_file():
        try:
            arbol = ast.parse(ig.read_text(encoding="utf-8"))
            clases = [n.name for n in arbol.body if isinstance(n, ast.ClassDef)]
            if clases:
                fail(f"InitGui.py define clases {clases}: deben vivir en un "
                     f"modulo importado real (trampa de namespace de exec)")
            else:
                ok("InitGui.py no define clases (patron cascaron correcto)")
        except SyntaxError:
            pass

    # -- Modulo de implementacion real --
    impl = instalado / "VDO" / "vdo_initgui.py"
    if impl.is_file():
        clases = [n.name for n in ast.parse(impl.read_text(encoding="utf-8")).body
                  if isinstance(n, ast.ClassDef)]
        if CLASE_WB in clases:
            ok(f"VDO/vdo_initgui.py define {CLASE_WB}")
        else:
            fail(f"VDO/vdo_initgui.py no define {CLASE_WB} (tiene {clases})")
    else:
        fail("Falta VDO/vdo_initgui.py (implementacion del workbench)")

    # -- Paquete VDO --
    if (instalado / "VDO" / "__init__.py").is_file():
        ok("Paquete VDO/ con __init__.py")
    else:
        fail("VDO/__init__.py ausente: no es un paquete Python importable")

    # -- package.xml --
    px = instalado / "package.xml"
    if px.is_file():
        try:
            raiz = ET.parse(px).getroot()
            ns = "{https://wiki.freecad.org/Package_Metadata}"
            cn = raiz.find(f".//{ns}classname")
            cn = cn.text.strip() if cn is not None and cn.text else None
            if cn == CLASE_WB:
                ok(f"package.xml classname = {cn}")
            else:
                fail(f"package.xml classname = {cn}, se esperaba {CLASE_WB}")
            ic = raiz.find(f".//{ns}icon")
            if ic is not None and ic.text:
                ruta_ic = instalado / ic.text.strip()
                (ok if ruta_ic.is_file() else fail)(
                    f"icono de package.xml: {ic.text.strip()}"
                    + ("" if ruta_ic.is_file() else " NO EXISTE"))
        except ET.ParseError as e:
            fail(f"package.xml mal formado: {e}")
    else:
        fail("Falta package.xml")

    # -- _paths.py debe resolver a la raiz, no a VDO/ --
    pth = instalado / "VDO" / "_paths.py"
    if pth.is_file():
        r = subprocess.run(
            [sys.executable, "-c",
             f"import sys;sys.path.insert(0,{str(instalado)!r});"
             "from VDO import _paths as P;"
             "print(P.WB_DIR);print(P.VDO_DIR.is_dir());"
             "import os;print(os.path.isfile(P.get_icon_path('vdo_workbench.svg')))"],
            capture_output=True, text=True)
        lineas = r.stdout.strip().splitlines()
        if len(lineas) == 3 and lineas[1] == "True" and lineas[2] == "True":
            ok(f"_paths.py resuelve bien (WB_DIR={lineas[0]})")
        else:
            fail(f"_paths.py no resuelve: {r.stdout.strip()} {r.stderr.strip()[:200]}")

    # -- Invariante 3: paquete autocontenido (sin imports absolutos vdo_*) --
    fugas = imports_absolutos_vdo(instalado / "VDO")
    if fugas:
        for arch, mods in list(fugas.items())[:6]:
            fail(f"import absoluto no encapsulado en {arch}: {mods} "
                 f"(usar VDO.shared.*)")
    else:
        ok("paquete autocontenido: ningun import absoluto vdo_* en VDO/")

    # -- VDO/shared/ con los modulos compartidos --
    shared = instalado / "VDO" / "shared"
    if (shared / "__init__.py").is_file():
        ok(f"VDO/shared/ presente ({len(list(shared.glob('*.py'))) - 1} modulos)")
    else:
        fail("falta VDO/shared/__init__.py")

    # -- El manifiesto JSON debe existir donde _paths lo busca --
    if (instalado / "VDO" / "vdo_manifest.json").is_file():
        ok("VDO/vdo_manifest.json presente")
    else:
        fail("falta VDO/vdo_manifest.json")

    # -- Instalaciones duplicadas --
    dup = []
    for base in (Path("/usr/share/freecad/Mod"), Path("/usr/lib/freecad/Mod"),
                 Path.home() / ".FreeCAD" / "Mod"):
        if base.is_dir():
            dup += [d for d in base.glob("VDO*")]
    if dup:
        for d in dup:
            vacio = d.is_dir() and not any(d.iterdir())
            warn(f"Copia conflictiva en {d}" + (" (vacia, basura)" if vacio else ""))
    else:
        ok("Sin instalaciones duplicadas fuera de Mod/ del usuario")


# =====================================================================
# N2 - CONSOLA
# =====================================================================

def nivel2() -> None:
    titulo("N2 CONSOLA - freecadcmd ejecuta Init.py sin abortar")
    tmp = Path("/tmp/_vdo_noop.py")
    tmp.write_text("import FreeCAD\n")
    try:
        r = subprocess.run(["freecadcmd", str(tmp)], capture_output=True,
                           text=True, timeout=180)
    except FileNotFoundError:
        fail("freecadcmd no esta en el PATH")
        return
    except subprocess.TimeoutExpired:
        fail("freecadcmd excedio el tiempo limite")
        return

    salida = r.stdout + r.stderr
    malas = [l for l in salida.splitlines()
             if "During initialization the error" in l or
             (WB_NAME in l and ("Error" in l or "Traceback" in l))]
    if malas:
        for l in malas[:6]:
            fail(f"arranque: {l.strip()[:160]}")
    else:
        ok("Init.py se ejecuta sin errores de inicializacion")


# =====================================================================
# N3 - GUI
# =====================================================================

SONDA = '''# Sonda GUI autogenerada por vdo_verify.py
import json, os, traceback
R = %(reporte)r
r = {"ok": False, "errores": []}
try:
    import FreeCAD as App, FreeCADGui as Gui
    wbs = Gui.listWorkbenches()
    r["vdo_presente"] = "%(clase)s" in wbs
    r["total_wb"] = len(wbs)
    if r["vdo_presente"]:
        Gui.activateWorkbench("%(clase)s")
        wb = Gui.getWorkbench("%(clase)s")
        r["activado"] = Gui.activeWorkbench().name() == "%(clase)s"
        todos = Gui.listCommands()
        esp = %(cmds)s
        r["registrados"] = [c for c in esp if c in todos]
        r["faltantes"] = [c for c in esp if c not in todos]
        r["icono_existe"] = os.path.isfile(getattr(wb, "Icon", "") or "")
        r["ok"] = r["activado"] and not r["faltantes"] and r["icono_existe"]
    else:
        r["errores"].append("%(clase)s ausente de listWorkbenches()")
except Exception:
    r["errores"].append(traceback.format_exc())
open(R, "w").write(json.dumps(r, indent=2, ensure_ascii=False))
try:
    from PySide import QtCore
    import FreeCADGui as Gui
    QtCore.QTimer.singleShot(300, Gui.getMainWindow().close)
except Exception:
    pass
'''


def nivel3() -> None:
    titulo("N3 GUI - freecad real registra y activa el workbench")
    sonda = Path("/tmp/_vdo_sonda.FCMacro")
    ARTEF.mkdir(parents=True, exist_ok=True)
    sonda.write_text(SONDA % {"clase": CLASE_WB,
                              "cmds": repr(COMANDOS_ESPERADOS),
                              "reporte": str(ARTEF / "gui_report.json")})
    rep = ARTEF / "gui_report.json"
    rep.unlink(missing_ok=True)

    entorno = dict(os.environ, QT_STYLE_OVERRIDE="Fusion")
    try:
        salida = subprocess.run(["freecad", str(sonda)], capture_output=True,
                                text=True, timeout=180, env=entorno)
    except FileNotFoundError:
        fail("freecad no esta en el PATH")
        return
    except subprocess.TimeoutExpired:
        fail("la GUI de FreeCAD excedio el tiempo limite")
        return

    if not rep.is_file():
        fail("la sonda GUI no genero reporte (FreeCAD no llego a ejecutarla)")
        print((salida.stdout + salida.stderr)[-800:])
        return

    r = json.loads(rep.read_text())
    if r.get("vdo_presente"):
        ok(f"{CLASE_WB} registrado ({r.get('total_wb')} workbenches en total)")
    else:
        fail(f"{CLASE_WB} NO registrado")
    if r.get("activado"):
        ok("se activa correctamente")
    if r.get("faltantes"):
        fail(f"comandos sin registrar: {r['faltantes']}")
    elif r.get("registrados"):
        ok(f"los {len(r['registrados'])} comandos estan registrados")
    if r.get("icono_existe"):
        ok("el icono del workbench se resuelve")
    elif r.get("vdo_presente"):
        fail("el icono del workbench no existe en disco")
    for e in r.get("errores", []):
        fail(f"sonda: {e.strip()[:300]}")

    huerfanos = [l for l in (salida.stdout + salida.stderr).splitlines()
                 if "Cannot find icon" in l]
    if huerfanos:
        warn(f"{len(huerfanos)} iconos no encontrados (toolbars heredadas de "
             f"user.cfg, ajenas al workbench)")


# =====================================================================
# Despliegue
# =====================================================================

def imports_absolutos_vdo(raiz_paquete: Path) -> dict[str, list[str]]:
    """Imports absolutos de modulos vdo_* de nivel superior dentro de VDO/.

    En un paquete autocontenido deben ser CERO: FreeCAD anade cada Mod/<dir>
    al sys.path global, asi que un modulo llamado 'vdo_shared_guardian' en la raiz
    del workbench queda visible para todo Python y puede colisionar con otro
    addon. Todo debe ir por VDO.shared.*
    """
    import re
    patron = re.compile(r"^\s*(?:import|from)\s+(vdo_[a-z_0-9]+)", re.MULTILINE)
    hallazgos: dict[str, list[str]] = {}
    for py in raiz_paquete.rglob("*.py"):
        mods = set(patron.findall(py.read_text(encoding="utf-8", errors="ignore")))
        if mods:
            hallazgos[str(py.relative_to(raiz_paquete.parent))] = sorted(mods)
    return hallazgos


def desplegar(instalado: Path) -> None:
    titulo("DESPLIEGUE - Macro/ (fuente) -> Mod/ (instalacion)")
    instalado.mkdir(parents=True, exist_ok=True)

    for nombre in ("Init.py", "InitGui.py", "package.xml", "metadata.txt"):
        src = FUENTE / nombre
        if src.is_file():
            shutil.copy2(src, instalado / nombre)
            ok(f"copiado {nombre}")
        else:
            fail(f"falta en la fuente: {nombre}")

    src_vdo, dst_vdo = FUENTE / "VDO", instalado / "VDO"
    if not src_vdo.is_dir():
        fail("falta el paquete VDO/ en la fuente")
        return
    if dst_vdo.exists():
        shutil.rmtree(dst_vdo)
    shutil.copytree(src_vdo, dst_vdo,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.bak"))
    ok(f"paquete VDO/ sincronizado ({sum(1 for _ in dst_vdo.rglob('*.py'))} modulos .py)")


# =====================================================================

# =====================================================================
# N4 - END TO END funcional
# =====================================================================

ARCHIVO_DEMO = Path.home() / "Documentos" / "VDO_demo_mueble.FCStd"
# Artefactos de verificacion dentro del repo (gitignorados), no en /tmp:
# asi quedan junto al codigo que los produjo y son inspeccionables.
ARTEF = FUENTE / ".verif"

E2E_CREAR = '''# Sonda E2E autogenerada: crea muro + COCO + panel y guarda.
import json, os, traceback
R = %(rep_crear)r
r = {"ok": False, "pasos": {}, "errores": [], "consola": []}

def paso(nombre, fn):
    try:
        v = fn()
        r["pasos"][nombre] = True
        return v
    except Exception:
        r["pasos"][nombre] = False
        r["errores"].append(nombre + ": " + traceback.format_exc())
        return None

try:
    import FreeCAD as App, FreeCADGui as Gui

    paso("activar_workbench", lambda: Gui.activateWorkbench("%(clase)s"))

    doc = paso("crear_documento", lambda: App.newDocument("VDO_Demo"))

    # Vista 3D: es lo que el usuario llama "modo canvas".
    def _vista():
        v = Gui.activeDocument().activeView()
        assert v is not None, "no hay vista 3D activa"
        v.viewAxonometric()
        return True
    r["vista_3d"] = paso("vista_3d", _vista)

    # --- 1. Muro BIM clasico, via la API real de Arch ---
    def _muro():
        import Arch, Draft
        base = Draft.make_wire([App.Vector(0, 0, 0), App.Vector(3000, 0, 0)])
        m = Arch.makeWall(base, width=150, height=2400)
        m.Label = "Muro_Demo"
        doc.recompute()
        return m.Name
    r["muro"] = paso("muro_arch", _muro)

    # --- 2. Modulo de mueble COCO, POR EL COMANDO DE LA TOOLBAR ---
    # Esta prueba llamaba a make_coco() directamente y por eso daba
    # "ok": true mientras el camino real del usuario (clic en el icono ->
    # panel -> Crear) no creaba nada: el comando abria el TaskPanel sin
    # objeto y accept() devolvia True sin tocar el documento.
    # Lo que hay que ejercitar es el comando, no la fabrica.
    def _coco():
        antes = {o.Name for o in doc.Objects}
        Gui.runCommand("VDO_Coco4C")
        Gui.updateGui()
        nuevos = sorted({o.Name for o in doc.Objects} - antes)
        assert nuevos, (
            "VDO_Coco4C no creo ningun objeto (regresion del flujo de "
            "creacion: comando -> fabrica -> panel)")
        r["coco_objetos_creados"] = nuevos
        r["coco_dialogo_abierto"] = bool(Gui.Control.activeDialog())
        assert r["coco_dialogo_abierto"], (
            "el comando no abrio el panel de configuracion")

        # El panel debe tener el objeto: si llega con obj=None, Aceptar
        # vuelve a ser un no-op silencioso.
        from VDO.ui.vdo_ui_creation_flow import FlujoCreacion
        Gui.Control.closeDialog()
        Gui.updateGui()
        flujo = FlujoCreacion("coco_4c", {"nombre": "COCO_Demo"},
                              colocar=False)
        c = flujo.iniciar()
        assert c is not None, "el flujo de creacion devolvio None"
        assert flujo.panel is not None and flujo.panel.obj is not None, (
            "el panel se abrio sin objeto")

        carcasa_antes = sorted(h.Name for h in (c.Hijos or []))
        assert len(carcasa_antes) >= 5, (
            "el COCO nacio sin carcasa: %%s" %% carcasa_antes)

        assert flujo.panel.accept(), "accept() del panel devolvio False"
        Gui.updateGui()
        carcasa_despues = sorted(h.Name for h in (c.Hijos or []))
        # Regresion historica: _construir_insertos borraba como huerfano
        # todo hijo que no fuese puerta/cajon, es decir la carcasa entera,
        # y como el Shape del COCO es nulo (T5) el modulo quedaba invisible.
        assert carcasa_despues == carcasa_antes, (
            "Aceptar altero la carcasa del COCO: antes=%%s despues=%%s"
            %% (carcasa_antes, carcasa_despues))

        # El arbol debe anidar la carcasa bajo el modulo (Axioma T4).
        hijos_arbol = [h.Name for h in c.ViewObject.Proxy.claimChildren()]
        assert sorted(hijos_arbol) == carcasa_antes, (
            "claimChildren() no refleja la capa de datos: %%s vs %%s"
            %% (sorted(hijos_arbol), carcasa_antes))
        r["coco_hijos"] = hijos_arbol

        # Mover el padre debe arrastrar la carcasa (LocalPlacement).
        x_antes = {h.Name: h.Placement.Base.x for h in c.Hijos}
        c.Placement = App.Placement(App.Vector(400, 120, 0), App.Rotation())
        doc.recompute()
        movidos = [n for n, x in x_antes.items()
                   if abs(doc.getObject(n).Placement.Base.x - x - 400) < 1e-6]
        assert len(movidos) == len(x_antes), (
            "la carcasa no sigue al COCO al moverlo: %%s/%%s"
            %% (len(movidos), len(x_antes)))
        doc.recompute()
        return c.Name
    r["coco"] = paso("coco", _coco)

    # --- 2b. Cada modulo creable debe producir geometria ---
    # Un modulo que se crea pero no se ve es indistinguible de uno que no
    # se crea. El cajon calculaba todos sus solidos en execute() y los
    # tiraba (Shape nula por T5 sin tener hijos con volumen).
    def _todos_los_modulos():
        from VDO.ui.vdo_ui_creation_flow import (
            crear_modulo_directo, tipos_disponibles)
        sin_volumen = []
        detalle = {}
        for tipo in tipos_disponibles():
            obj = crear_modulo_directo(tipo, {"nombre": "Chk_" + tipo})
            assert obj is not None, "crear_modulo_directo('%%s') -> None" %% tipo
            propio = 0.0
            try:
                if obj.Shape and not obj.Shape.isNull():
                    propio = obj.Shape.Volume
            except Exception:
                propio = 0.0
            hijos = 0.0
            for h in (getattr(obj, "Hijos", None) or []):
                try:
                    hijos += h.Shape.Volume
                except Exception:
                    pass
            detalle[tipo] = round(propio + hijos, 1)
            if propio + hijos <= 0:
                sin_volumen.append(tipo)
        r["volumen_por_modulo"] = detalle
        assert not sin_volumen, (
            "modulos creados sin geometria visible: %%s" %% sin_volumen)
        return detalle
    paso("todos_los_modulos_con_geometria", _todos_los_modulos)

    # --- 2c. Borrar el modulo arrastra su carcasa (Axioma T6) ---
    def _cascada():
        from VDO.ui.vdo_ui_creation_flow import crear_modulo_directo
        c = crear_modulo_directo("coco_4c", {"nombre": "COCO_Borrar"})
        hijos = [h.Name for h in (c.Hijos or [])]
        assert hijos, "el COCO de prueba nacio sin carcasa"
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(doc.Name, c.Name)
        Gui.runCommand("Std_Delete")
        Gui.updateGui()
        huerfanos = [n for n in hijos if doc.getObject(n) is not None]
        assert not huerfanos, (
            "borrar el COCO dejo paneles huerfanos: %%s" %% huerfanos)
        return True
    paso("borrado_en_cascada", _cascada)

    # --- 3. Panel de mueble ---
    def _panel():
        from VDO.cad.objects.vdo_cad_panel import crear_pieza
        pz = crear_pieza({"nombre": "Panel_Demo", "orientacion": "horizontal",
                          "largo": 600, "ancho": 580, "espesor": 18,
                          "cantos": {"norte": "FX", "sur": "FX",
                                     "este": "FX", "oeste": "FX"}})
        assert pz is not None, "crear_pieza devolvio None"
        pz.Placement.Base = App.Vector(400, 120, 760)
        doc.recompute()
        return pz.Name
    r["panel"] = paso("panel", _panel)

    # --- Validar solidos reales, no solo objetos en el arbol ---
    # El COCO padre es un contenedor logico: dibuja un compound y delega la
    # geometria fabricable a sus PanelFeature hijos, asi que su Shape puede
    # ser nulo sin que eso sea un defecto. Lo que debe tener volumen son las
    # piezas: el muro, los paneles del COCO y el panel suelto.
    def _solidos():
        vol, invalidos = {}, []
        for o in doc.Objects:
            if not hasattr(o, "Shape"):
                continue
            try:
                if o.Shape and not o.Shape.isNull():
                    vol[o.Name] = round(o.Shape.Volume, 1)
            except Exception:
                invalidos.append(o.Name)
        r["shapes_sin_geometria"] = invalidos
        solidos = {k: v for k, v in vol.items() if v > 0}
        assert len(solidos) >= 7, (
            "se esperaban al menos 7 solidos (muro + 5 paneles COCO + panel), "
            "hay %%s: %%s" %% (len(solidos), solidos))
        return solidos
    r["volumenes"] = paso("solidos_con_volumen", _solidos)

    # --- Captura del canvas: prueba visual de que el mueble se renderiza ---
    def _captura():
        v = Gui.activeDocument().activeView()
        v.viewIsometric()
        v.fitAll()
        Gui.updateGui()
        v.saveImage(%(png_crear)r, 1400, 900, "White")
        assert os.path.isfile(%(png_crear)r), "no se escribio el PNG"
        return True
    paso("captura_canvas", _captura)

    paso("guardar", lambda: doc.saveAs(%(archivo)r))
    r["archivo"] = %(archivo)r
    r["objetos"] = [o.Name for o in doc.Objects]
    r["n_objetos"] = len(doc.Objects)
    r["ok"] = all(r["pasos"].values())
except Exception:
    r["errores"].append(traceback.format_exc())

open(R, "w").write(json.dumps(r, indent=2, ensure_ascii=False))
try:
    from PySide import QtCore
    import FreeCADGui as Gui
    QtCore.QTimer.singleShot(400, Gui.getMainWindow().close)
except Exception:
    pass
'''

E2E_ABRIR = '''# Sonda E2E autogenerada: reabre el archivo y valida su contenido.
import json, traceback
R = %(rep_abrir)r
r = {"ok": False, "errores": []}
try:
    import FreeCAD as App, FreeCADGui as Gui
    Gui.activateWorkbench("%(clase)s")
    doc = App.openDocument(%(archivo)r)
    doc.recompute()
    r["objetos"] = [o.Name for o in doc.Objects]
    etiquetas = [o.Label for o in doc.Objects]
    r["etiquetas"] = etiquetas
    tipos = {o.Name: o.TypeId for o in doc.Objects}

    def buscar(frag):
        return [n for n in r["objetos"] if frag.lower() in n.lower()]

    r["muro_presente"] = bool(buscar("wall")) or "Muro_Demo" in etiquetas
    r["coco_presente"] = bool(buscar("COCO_Demo"))
    r["panel_presente"] = bool(buscar("Panel_Demo"))

    vol = {}
    for n in r["objetos"]:
        o = doc.getObject(n)
        if hasattr(o, "Shape") and o.Shape and not o.Shape.isNull():
            try:
                vol[n] = round(o.Shape.Volume, 1)
            except Exception:
                pass
    r["volumenes"] = vol
    r["wb_activo"] = Gui.activeWorkbench().name()
    r["vista_3d"] = Gui.activeDocument().activeView() is not None
    try:
        Gui.activeDocument().activeView().viewIsometric()
        Gui.activeDocument().activeView().fitAll()
        Gui.updateGui()
        Gui.activeDocument().activeView().saveImage(
            %(png_abrir)r, 1400, 900, "White")
        r["captura"] = %(png_abrir)r
    except Exception as exc:
        r["errores"].append("captura: %%s" %% exc)
    r["ok"] = (r["muro_presente"] and r["coco_presente"]
               and r["panel_presente"] and r["vista_3d"]
               and r["wb_activo"] == "%(clase)s")
except Exception:
    r["errores"].append(traceback.format_exc())

open(R, "w").write(json.dumps(r, indent=2, ensure_ascii=False))
try:
    from PySide import QtCore
    import FreeCADGui as Gui
    QtCore.QTimer.singleShot(400, Gui.getMainWindow().close)
except Exception:
    pass
'''


def _lanzar(macro_txt: str, nombre: str, reporte: Path) -> dict | None:
    """Ejecuta una sonda en la GUI real y devuelve su reporte JSON."""
    ruta = Path(f"/tmp/_vdo_{nombre}.FCMacro")
    ruta.write_text(macro_txt)
    reporte.unlink(missing_ok=True)
    entorno = dict(os.environ, QT_STYLE_OVERRIDE="Fusion")
    try:
        res = subprocess.run(["freecad", str(ruta)], capture_output=True,
                             text=True, timeout=300, env=entorno)
    except subprocess.TimeoutExpired:
        # La sonda escribe su JSON antes de cerrar la ventana, asi que un
        # cuelgue al salir (un modal de "¿guardar cambios?", por ejemplo)
        # no debe tirar a la basura lo que ya habia medido: se reporta el
        # cuelgue como fallo aparte y se sigue leyendo el informe.
        fail(f"{nombre}: la GUI no cerro la ventana (timeout)")
        if reporte.is_file():
            return json.loads(reporte.read_text())
        return None
    if not reporte.is_file():
        fail(f"{nombre}: la sonda no genero reporte")
        print((res.stdout + res.stderr)[-1200:])
        return None
    salida = res.stdout + res.stderr
    graves = [l for l in salida.splitlines()
              if "Traceback" in l or "During initialization the error" in l]
    for l in graves[:4]:
        fail(f"{nombre}: {l.strip()[:160]}")
    return json.loads(reporte.read_text())


def nivel4() -> None:
    titulo("N4 END-TO-END - crear mueble, guardar y reabrir")
    ARCHIVO_DEMO.parent.mkdir(parents=True, exist_ok=True)

    ARTEF.mkdir(parents=True, exist_ok=True)
    sub = {"clase": CLASE_WB, "archivo": str(ARCHIVO_DEMO),
           "rep_crear": str(ARTEF / "e2e_crear.json"),
           "rep_abrir": str(ARTEF / "e2e_abrir.json"),
           "png_crear": str(ARTEF / "canvas_creado.png"),
           "png_abrir": str(ARTEF / "canvas_reabierto.png")}
    r = _lanzar(E2E_CREAR % sub, "e2e_crear", Path(str(ARTEF / "e2e_crear.json")))
    if r is None:
        return

    for nombre, bien in r.get("pasos", {}).items():
        (ok if bien else fail)(f"paso {nombre}")
    if r.get("vista_3d"):
        ok(f"canvas 3D activo ({r['vista_3d']})")
    if r.get("volumenes"):
        ok(f"solidos con volumen: {r['volumenes']}")
    for e in r.get("errores", []):
        fail(f"crear: {e.strip()[:400]}")

    if not ARCHIVO_DEMO.is_file():
        fail(f"no se guardo el archivo {ARCHIVO_DEMO}")
        return
    ok(f"archivo guardado: {ARCHIVO_DEMO} "
       f"({ARCHIVO_DEMO.stat().st_size // 1024} KB, {r.get('n_objetos')} objetos)")

    # --- Segunda sesion: reabrir en limpio ---
    r2 = _lanzar(E2E_ABRIR % sub, "e2e_abrir", Path(str(ARTEF / "e2e_abrir.json")))
    if r2 is None:
        return
    for clave, etiqueta in (("muro_presente", "muro BIM"),
                            ("coco_presente", "modulo COCO"),
                            ("panel_presente", "panel de mueble")):
        (ok if r2.get(clave) else fail)(f"al reabrir: {etiqueta}")
    if r2.get("wb_activo") == CLASE_WB:
        ok("el archivo abre con el workbench VDO activo")
    else:
        fail(f"workbench activo al reabrir: {r2.get('wb_activo')}")
    (ok if r2.get("vista_3d") else fail)("al reabrir: canvas 3D presente")
    for e in r2.get("errores", []):
        fail(f"reabrir: {e.strip()[:400]}")


# =====================================================================
# N5 - INSERTOS DE VANO (contenido del COCO)
# =====================================================================
#
# El N4 cubre la carcasa del COCO; el contenido de los vanos (cajones,
# puertas) no lo cubria nadie, y ahi vivian cuatro defectos a la vez:
# cajones sin piezas en el arbol, insertos apilados en el origen, piezas
# huerfanas al retirar un inserto y despiece duplicado en la lista de
# corte. Los cuatro son invisibles para la suite de pytest porque solo se
# manifiestan con FreeCAD y Qt reales. Ver docs/05 §5.
#
# La sonda entra por donde entra el usuario: escribe el contenido del vano
# en VDO_Contenido_JSON y pulsa Aceptar en el panel del COCO.

INSERTOS = '''# Sonda N5 autogenerada: insertos de vano del COCO.
import json, traceback
R = %(reporte)r
r = {"ok": False, "pasos": {}, "errores": []}

def paso(nombre, fn):
    try:
        v = fn()
        r["pasos"][nombre] = True
        return v
    except Exception:
        r["pasos"][nombre] = False
        r["errores"].append(nombre + ": " + traceback.format_exc())
        return None

try:
    import FreeCAD as App, FreeCADGui as Gui
    Gui.activateWorkbench("%(clase)s")
    doc = App.newDocument("VDO_Insertos")

    from VDO.cad.objects.vdo_cad_coco import make_coco
    from VDO.ui.vdo_ui_coco_task import CocoUnifiedTaskPanel

    ALTO, ANCHO, FONDO, N = 720.0, 600.0, 580.0, 3
    TOL = 1.0

    def aplicar(coco, contenido):
        """Pulsa Aceptar con ese contenido de vano, como haria el usuario.

        El panel se construye ANTES de escribir el contenido porque es el
        propio panel quien declara VDO_Contenido_JSON en el COCO (el
        CocoFeature no la trae de fabrica); luego se le pide que relea el
        objeto para que el editor de divisiones resuelva los vanos.
        """
        panel = CocoUnifiedTaskPanel(coco)
        coco.VDO_Contenido_JSON = json.dumps(contenido, ensure_ascii=False)
        panel.editor_divisiones.cargar_desde_objeto(coco)
        assert panel.accept(), "accept() del panel del COCO devolvio False"
        Gui.updateGui()
        doc.recompute()

    def cajones():
        return [o for o in doc.Objects
                if o.Name.startswith("Cj") and not getattr(o, "VDO_Rol", "")]

    def bbox(objetos):
        caja = None
        for o in objetos:
            try:
                if o.Shape is None or o.Shape.isNull():
                    continue
                caja = o.Shape.BoundBox if caja is None else caja.united(
                    o.Shape.BoundBox)
            except Exception:
                continue
        return caja

    coco = make_coco({"nombre": "COCO_Ins", "alto": ALTO, "ancho": ANCHO,
                      "fondo_modulo": FONDO})
    aplicar(coco, {"0,0": {"tipo": "cajon",
                           "config": {"cantidad": N, "nombre": "Cj"}}})

    # --- 1. Cada cajon materializa sus 6 piezas y las reclama en el arbol
    #
    # El panel del COCO calculaba el despiece del cajon y se paraba ahi:
    # quien crea los PanelFeature es sincronizar_paneles_hijos(), que por
    # R-04 vive fuera de execute() y nadie llamaba. Sintoma visible: el
    # cajon no tenia desplegable en el arbol.
    def _piezas():
        hallados = cajones()
        assert len(hallados) == N, (
            "se esperaban %%s cajones, hay %%s" %% (N, len(hallados)))
        detalle = {}
        for c in hallados:
            hijos = sorted(h.Name for h in (getattr(c, "Hijos", None) or []))
            assert len(hijos) == 6, (
                "%%s tiene %%s piezas y deberia tener 6: el panel del COCO no "
                "materializo el despiece" %% (c.Name, len(hijos)))
            claim = sorted(h.Name for h in c.ViewObject.Proxy.claimChildren())
            assert claim == hijos, (
                "%%s no reclama sus piezas en el arbol (T4): %%s vs %%s"
                %% (c.Name, claim, hijos))
            detalle[c.Name] = hijos
        r["piezas_por_cajon"] = {k: len(v) for k, v in detalle.items()}
        return detalle
    paso("cajon_materializa_piezas", _piezas)

    # --- 2. Los insertos se colocan en su vano, no en el origen
    #
    # CocoFeature solo propaga Placement desde onChanged("Placement"), aviso
    # que un inserto recien vinculado nunca recibe: los N cajones de una
    # torre se quedaban con Placement nulo, superpuestos en el origen.
    def _pose():
        zs = []
        for c in cajones():
            base = c.Placement.Base
            assert base.Length > 1e-6, (
                "%%s esta en el origen del documento: no se le propago la "
                "pose del COCO" %% c.Name)
            zs.append(round(base.z, 3))
            caja = bbox(getattr(c, "Hijos", None) or [])
            assert caja is not None, "%%s no tiene piezas con geometria" %% c.Name
            # En X y Z el inserto vive dentro del mueble. En Y no se acota
            # por arriba: la fachada de parche sobresale por delante (y<0).
            assert -TOL <= caja.XMin and caja.XMax <= ANCHO + TOL, (
                "%%s se sale del mueble en X: %%.1f..%%.1f"
                %% (c.Name, caja.XMin, caja.XMax))
            assert -TOL <= caja.ZMin and caja.ZMax <= ALTO + TOL, (
                "%%s se sale del mueble en Z: %%.1f..%%.1f"
                %% (c.Name, caja.ZMin, caja.ZMax))
            assert caja.YMax <= FONDO + TOL, (
                "%%s se sale del mueble por el fondo: %%.1f" %% (c.Name, caja.YMax))
        assert len(set(zs)) == N, (
            "la torre no esta escalonada, los cajones comparten altura: %%s" %% zs)
        r["z_cajones"] = sorted(zs)
        return zs
    paso("insertos_colocados_en_su_vano", _pose)

    # --- 3. La lista de corte no cuenta ninguna pieza dos veces
    #
    # Un contenedor publica su despiece en VDO_Paneles_JSON Y como hijos
    # reales; el modo "todo" sumaba ambos y devolvia cada tablero duplicado.
    def _despiece():
        from VDO.cam.vdo_cam_cutlist import extraer_piezas_del_documento
        piezas = extraer_piezas_del_documento("todo")
        nombres = [p.get("nombre", "?") for p in piezas]
        repetidos = sorted({n for n in nombres if nombres.count(n) > 1})
        assert not repetidos, (
            "la lista de corte duplica piezas: %%s" %% repetidos[:6])
        esperadas = 5 + 6 * N          # carcasa del COCO + 6 por cajon
        assert len(piezas) >= esperadas, (
            "la lista de corte tiene %%s piezas y se esperaban al menos %%s"
            %% (len(piezas), esperadas))
        r["piezas_lista_corte"] = len(piezas)
        return len(piezas)
    paso("lista_corte_sin_duplicados", _despiece)

    # --- 4. Vaciar el vano se lleva los insertos y TODAS sus piezas
    #
    # doc.removeObject() no dispara el onDelete del proxy (solo lo hace el
    # borrado desde la GUI), asi que retirar un cajon dejaba sus 6 paneles
    # sueltos en la raiz del documento.
    def _retirada():
        nombres_antes = {o.Name for o in doc.Objects}
        aplicar(coco, {})
        vivos = [n for n in nombres_antes
                 if n.startswith("Cj") and doc.getObject(n) is not None]
        assert not vivos, (
            "vaciar el vano dejo huerfanos: %%s" %% vivos)
        carcasa = sorted(h.Name for h in (coco.Hijos or []))
        assert len(carcasa) == 5, (
            "la carcasa del COCO quedo en %%s piezas: %%s"
            %% (len(carcasa), carcasa))
        r["objetos_tras_retirar"] = len(doc.Objects)
        assert len(doc.Objects) == 6, (
            "quedan %%s objetos y deberian quedar 6 (COCO + 5 tableros): %%s"
            %% (len(doc.Objects), [o.Name for o in doc.Objects]))
        return True
    paso("retirar_inserto_sin_huerfanos", _retirada)

    r["ok"] = all(r["pasos"].values())
except Exception:
    r["errores"].append(traceback.format_exc())

open(R, "w").write(json.dumps(r, indent=2, ensure_ascii=False))
try:
    # Cerrar los documentos ANTES que la ventana: con un documento sin
    # guardar, close() abre el modal "¿guardar cambios?" y la sonda se
    # queda colgada hasta que salta el timeout del arnes.
    import FreeCAD as App
    for nombre in list(App.listDocuments()):
        try:
            App.closeDocument(nombre)
        except Exception:
            pass
except Exception:
    pass
try:
    from PySide import QtCore
    import FreeCADGui as Gui
    QtCore.QTimer.singleShot(400, Gui.getMainWindow().close)
except Exception:
    pass
'''


def nivel5() -> None:
    titulo("N5 INSERTOS - contenido de vano: piezas, pose, despiece y retirada")
    ARTEF.mkdir(parents=True, exist_ok=True)
    rep = ARTEF / "insertos.json"
    r = _lanzar(INSERTOS % {"clase": CLASE_WB, "reporte": str(rep)},
                "insertos", rep)
    if r is None:
        return

    for nombre, bien in r.get("pasos", {}).items():
        (ok if bien else fail)(f"paso {nombre}")

    piezas = r.get("piezas_por_cajon") or {}
    if piezas:
        ok(f"{len(piezas)} cajones con {sum(piezas.values())} piezas en el arbol")
    if r.get("z_cajones"):
        ok(f"torre escalonada en z: {r['z_cajones']}")
    if r.get("piezas_lista_corte") is not None:
        ok(f"lista de corte: {r['piezas_lista_corte']} piezas, sin duplicados")
    if r.get("objetos_tras_retirar") is not None:
        ok(f"al vaciar el vano quedan {r['objetos_tras_retirar']} objetos "
           f"(COCO + carcasa)")
    for e in r.get("errores", []):
        fail(f"insertos: {e.strip()[:400]}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Verifica que el workbench VDO carga")
    ap.add_argument("--gui", action="store_true", help="incluye el nivel 3 (abre FreeCAD)")
    ap.add_argument("--deploy", action="store_true", help="sincroniza Macro/ -> Mod/ antes")
    ap.add_argument("--e2e", action="store_true",
                    help="incluye los niveles 4 (end-to-end) y 5 (insertos)")
    ap.add_argument("--insertos", action="store_true",
                    help="solo el nivel 5: contenido de vano del COCO")
    args = ap.parse_args()

    print("\033[1m" + "=" * 62)
    print(f" VERIFICACION DE CARGA - {WB_NAME}")
    print("=" * 62 + "\033[0m")

    rutas = rutas_freecad()
    if not rutas:
        return 1
    instalado = Path(rutas["user"]) / "Mod" / WB_NAME
    print(f"\nUserAppDataDir : {rutas['user']}")
    print(f"ResourceDir    : {rutas['res']}")
    print(f"Destino Mod/   : {instalado}")

    if args.deploy:
        desplegar(instalado)

    nivel1(instalado)
    nivel2()
    if args.gui or args.e2e or args.insertos:
        nivel3()
    if args.e2e:
        nivel4()
    if args.e2e or args.insertos:
        nivel5()
    if not (args.gui or args.e2e or args.insertos):
        print("\n(nivel 3 GUI omitido; use --gui para la verificacion completa)")

    titulo("RESULTADO")
    if avisos:
        print(f"  {len(avisos)} aviso(s) no bloqueante(s)")
    if fallos:
        print(f"  \033[31m{len(fallos)} FALLO(S)\033[0m")
        for f in fallos:
            print(f"    - {f}")
        return 1
    print("  \033[32mTODO CORRECTO: el workbench carga.\033[0m")
    return 0


if __name__ == "__main__":
    sys.exit(main())
