#!/usr/bin/env python3
"""
vdo_toolbar_inject.py
Inyecta toolbar VDO en user.cfg de FreeCAD SIN workbench.
Aparece en BIMWorkbench (y opcionalmente en todos los workbenches).

USO: python3 vdo_toolbar_inject.py [ruta/user.cfg]
     (sin argumento: detecta el user.cfg del FreeCAD local)
     o ejecutar dentro de FreeCAD: Macro → Ejecutar → vdo_toolbar_inject.py
"""
import os
import re
import sys
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime

# ============================================================
# CONFIGURACIÓN DE MACROS VDO
# ============================================================
# OJO: Qt (QKeySequence) admite máx. 4 pulsaciones por atajo:
# "P, A, N, E, L" se guarda como "P, A, N, E". Por eso los
# mnemotécnicos son de 4 letras: PANE, COCO, FACH, HOJA, CAJO.
# El orden NO se reordena: los índices 0-2 están ligados a los
# atajos existentes en BaseApp/Preferences/Shortcut.
# ============================================================

VDO_MACROS = [
    {
        "name": "Std_Macro_0",
        "script": "vdo_panel_estandar.FCMacro",
        "menu": "Crear Panel de Melamina",
        "tooltip": "Genera un tablero o entrepaño atómico vinculado al sistema VDO",
        "whatsthis": "Inserta un tablero individual de melamina con control de dimensiones, espesor y posición para complementar el diseño del mobiliario.",
        "statustip": "Crea un panel de melamina independiente con medidas y cantos personalizables",
        "pixmap": "vdo_panel",
        "accel": "P, A, N, E",
    },
    {
        "name": "Std_Macro_1",
        "script": "vdo_coco_4c.FCMacro",
        "menu": "Crear COCO",
        "tooltip": "Genera el contenedor volumétrico básico con Task Panel paramétrico",
        "whatsthis": "Genera una caja estructural de 4 lados y fondo (laterales, tapa y base) con control de espesores, ranura inteligente para fondo y configuración de tapas/bases internas o externas.",
        "statustip": "Crea un nuevo módulo COCO parametrizable en el documento activo",
        "pixmap": "vdo_coco_2",
        "accel": "C, O, C, O",
    },
    {
        "name": "Std_Macro_2",
        "script": "vdo_panel_fachada.FCMacro",
        "menu": "Crear Fachada",
        "tooltip": "Genera un frente o puerta paramétrica para los módulos de mobiliario",
        "whatsthis": "Inserta un panel frontal o puerta dimensionable para cerrar los compartimentos de los módulos COCO con control de luz y holguras perimetrales.",
        "statustip": "Crea una fachada o puerta ajustable con holguras para el sistema VDO",
        "pixmap": "vdo_panel",
        "accel": "F, A, C, H",
    },
    {
        "name": "Std_Macro_3",
        "script": "VDO_Crear_Hoja_Melamina.FCMacro",
        "menu": "Crear Hoja",
        "tooltip": "Crear hoja de melamina con parámetros",
        "whatsthis": "Crear hoja de melamina con parámetros",
        "statustip": "Crear Hoja",
        "pixmap": "vdo_workbench",
        "accel": "H, O, J, A",
    },
    {
        "name": "Std_Macro_4",
        "script": "vdo_cajon_oculta.FCMacro",
        "menu": "Cajón Oculta",
        "tooltip": "Cajón con corredera oculta (Blum Tandem) con despiece milimétrico",
        "whatsthis": "Cajón con corredera oculta (Blum Tandem) con despiece milimétrico",
        "statustip": "Cajón Oculta",
        "pixmap": "vdo_cajon",
        "accel": "C, A, J, O",
    },
    {
        "name": "Std_Macro_5",
        "script": "vdo_panel_division.FCMacro",
        "menu": "Crear División",
        "tooltip": "Panel divisor (orientado verticalmente) vinculado al sistema VDO",
        "whatsthis": "Inserta un panel divisor vertical para separar los compartimentos internos de un módulo.",
        "statustip": "Crea una división vertical independiente",
        "pixmap": "vdo_panel",
        "accel": "D, I, V, I",
    },
]

# Toolbars VDO antiguas a limpiar (evita restos de 3 botones)
NOMBRES_VDO_OBSOLETOS = {
    "CARPINTERIA VDO",
    "CARPINTERIA - VDO",
    "CARPINTERIA TEST",
    "VDO",
    "VDO - Muebles Paramétricos",
}


def _ruta_macro_abs(nombre):
    """Devuelve la ruta ABSOLUTA de una macro (evita ambigüedad de rutas relativas)."""
    try:
        import FreeCAD as _App
        base = _App.getUserMacroDir(True)
    except Exception:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, nombre)


def _limpiar_toolbars_obsoletas(baseapp):
    """Elimina toolbars VDO antiguas de TODOS los workbenches."""
    wb_base = baseapp.find("FCParamGroup[@Name='Workbench']")
    if wb_base is None:
        return
    for wb in list(wb_base):
        if wb.tag != "FCParamGroup":
            continue
        tb = wb.find("FCParamGroup[@Name='Toolbar']")
        if tb is None:
            continue
        for grp in list(tb):
            if grp.tag != "FCParamGroup":
                continue
            name_el = grp.find("FCText[@Name='Name']")
            disp = (name_el.text or "") if name_el is not None else ""
            if disp in NOMBRES_VDO_OBSOLETOS:
                tb.remove(grp)
                print(f"[VDO] Toolbar obsoleta eliminada: '{disp}' "
                      f"(workbench: {wb.get('Name')})")

TOOLBAR_NAME = "CARPINTERIA - VDO"
TOOLBAR_GROUP = "Custom_1"
# Para que aparezca en TODOS los workbenches, usar "Global"
# Para que aparezca solo en BIM, usar "BIMWorkbench"
WORKBENCH_TARGET = "Global"


def find_user_cfg():
    """Encuentra user.cfg de FreeCAD (agnóstico: native/flatpak/snap/win/mac)."""
    try:
        import vdo_paths as vp
        cfg = vp.get_user_cfg()
        if cfg:
            return str(cfg)
    except Exception:
        pass
    # Fallback mínimo si vdo_paths no está disponible
    candidates = [
        os.path.expanduser("~/.config/FreeCAD/v1-1/user.cfg"),
        os.path.expanduser("~/.config/FreeCAD/user.cfg"),
        os.path.expanduser(
            "~/.var/app/org.freecad.FreeCAD/config/FreeCAD/v1-1/user.cfg"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def inject_toolbar(cfg_path):
    """Inyecta macros VDO y toolbar en user.cfg."""

    # Backup
    backup = cfg_path + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(cfg_path, backup)
    print(f"[VDO] Backup: {backup}")

    tree = ET.parse(cfg_path)
    root = tree.getroot()

    # Navegar la estructura: Root → BaseApp
    baseapp = root.find(".//FCParamGroup[@Name='BaseApp']")
    if baseapp is None:
        print("[VDO] ERROR: No se encontró BaseApp en user.cfg")
        return False

    # Limpiar toolbars VDO antiguas (restos de 3 botones, etc.)
    _limpiar_toolbars_obsoletas(baseapp)

    # ============================================================
    # 1. Definir macros en BaseApp/Macro/Macros
    # ============================================================
    macro_base = baseapp.find("FCParamGroup[@Name='Macro']")
    if macro_base is None:
        macro_base = ET.SubElement(baseapp, "FCParamGroup", Name="Macro")

    macros_group = macro_base.find("FCParamGroup[@Name='Macros']")
    if macros_group is None:
        macros_group = ET.SubElement(macro_base, "FCParamGroup", Name="Macros")

    # Eliminar macros VDO existentes (todas las de VDO_MACROS)
    for macro in VDO_MACROS:
        existing = macros_group.find(f"FCParamGroup[@Name='{macro['name']}']")
        if existing is not None:
            macros_group.remove(existing)
            print(f"[VDO] Eliminada definición existente: {macro['name']}")

    # Crear macros VDO
    for macro in VDO_MACROS:
        grp = ET.SubElement(macros_group, "FCParamGroup", Name=macro["name"])
        ET.SubElement(grp, "FCText", Name="Script").text = _ruta_macro_abs(macro["script"])
        ET.SubElement(grp, "FCText", Name="Menu").text = macro["menu"]
        ET.SubElement(grp, "FCText", Name="Tooltip").text = macro["tooltip"]
        ET.SubElement(grp, "FCText", Name="WhatsThis").text = macro.get("whatsthis", macro["tooltip"])
        ET.SubElement(grp, "FCText", Name="Statustip").text = macro.get("statustip", macro["menu"])
        ET.SubElement(grp, "FCText", Name="Pixmap").text = macro["pixmap"]
        ET.SubElement(grp, "FCText", Name="Accel").text = macro.get("accel", "")
        ET.SubElement(grp, "FCBool", Name="System", Value="0")
        print(f"[VDO] Macro definida: {macro['name']} → {macro['script']}"
              + (f"  (atajo: {macro['accel']})" if macro.get("accel") else ""))

    # ============================================================
    # 1b. Sincronizar atajos en BaseApp/Preferences/Shortcut
    # ============================================================
    prefs = baseapp.find("FCParamGroup[@Name='Preferences']")
    if prefs is not None:
        shortcut_grp = prefs.find("FCParamGroup[@Name='Shortcut']")
        if shortcut_grp is None:
            shortcut_grp = ET.SubElement(prefs, "FCParamGroup", Name="Shortcut")
        for macro in VDO_MACROS:
            if not macro.get("accel"):
                continue
            entry = shortcut_grp.find(f"FCText[@Name='{macro['name']}']")
            if entry is None:
                entry = ET.SubElement(shortcut_grp, "FCText", Name=macro["name"])
            if (entry.text or "") != macro["accel"]:
                entry.text = macro["accel"]
                print(f"[VDO] Atajo sincronizado: {macro['name']} = {macro['accel']}")

    # ============================================================
    # 2. Crear toolbar en BaseApp/Workbench/<target>/Toolbar
    # ============================================================
    wb_base = baseapp.find("FCParamGroup[@Name='Workbench']")
    if wb_base is None:
        wb_base = ET.SubElement(baseapp, "FCParamGroup", Name="Workbench")

    wb_target = wb_base.find(f"FCParamGroup[@Name='{WORKBENCH_TARGET}']")
    if wb_target is None:
        wb_target = ET.SubElement(wb_base, "FCParamGroup", Name=WORKBENCH_TARGET)

    toolbar_base = wb_target.find("FCParamGroup[@Name='Toolbar']")
    if toolbar_base is None:
        toolbar_base = ET.SubElement(wb_target, "FCParamGroup", Name="Toolbar")

    # Eliminar toolbar existente
    existing_toolbar = toolbar_base.find(f"FCParamGroup[@Name='{TOOLBAR_GROUP}']")
    if existing_toolbar is not None:
        toolbar_base.remove(existing_toolbar)
        print(f"[VDO] Eliminada toolbar existente: {TOOLBAR_GROUP}")

    # Crear toolbar con botones
    toolbar_grp = ET.SubElement(toolbar_base, "FCParamGroup", Name=TOOLBAR_GROUP)
    ET.SubElement(toolbar_grp, "FCText", Name="Name").text = TOOLBAR_NAME
    ET.SubElement(toolbar_grp, "FCBool", Name="Active", Value="1")

    for macro in VDO_MACROS:
        ET.SubElement(toolbar_grp, "FCText", Name=macro["name"]).text = "FreeCAD"

    print(f"[VDO] Toolbar creada: {TOOLBAR_NAME} con {len(VDO_MACROS)} botones")

    # ============================================================
    # 3. Asegurar visibilidad en Toolbars
    # ============================================================
    main_window = baseapp.find(".//FCParamGroup[@Name='MainWindow']")
    if main_window is not None:
        toolbars_vis = main_window.find("FCParamGroup[@Name='Toolbars']")
        if toolbars_vis is not None:
            # Desactivar flags de toolbars VDO obsoletas
            for flag_name in NOMBRES_VDO_OBSOLETOS:
                if flag_name == TOOLBAR_NAME:
                    continue
                old = toolbars_vis.find(f"FCBool[@Name='{flag_name}']")
                if old is not None:
                    old.set("Value", "0")
            # Asegurar la canónica visible
            existing = toolbars_vis.find(f"FCBool[@Name='{TOOLBAR_NAME}']")
            if existing is None:
                existing = ET.SubElement(toolbars_vis, "FCBool",
                                         Name=TOOLBAR_NAME, Value="1")
            else:
                existing.set("Value", "1")
            print(f"[VDO] Toolbar '{TOOLBAR_NAME}' marcada como visible")

    # ============================================================
    # 4. Guardar (normalizando al formato que escribe FreeCAD,
    #    para que el diff solo muestre los cambios reales)
    # ============================================================
    ET.indent(tree, space="  ")
    tree.write(cfg_path, encoding="UTF-8", xml_declaration=True)

    with open(cfg_path, "r", encoding="utf-8") as f:
        texto = f.read()

    # Declaración XML como la escribe FreeCAD
    texto = texto.replace("<?xml version='1.0' encoding='UTF-8'?>",
                          '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>')
    # Self-closing sin espacio: <FCInt ... /> → <FCInt .../>
    texto = texto.replace(" />", "/>")
    # FCText vacío como par, como FreeCAD: <FCText ...></FCText>
    texto = re.sub(r"<FCText([^>]*?)/>", r"<FCText\1></FCText>", texto)
    # Final de archivo: línea en blanco antes de </FCParameters> + \n final
    cuerpo = texto.rstrip("\n")
    if cuerpo.endswith("</FCParameters>"):
        cuerpo = cuerpo[:-len("</FCParameters>")].rstrip("\n")
    texto = cuerpo + "\n\n</FCParameters>\n"

    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(texto)

    print(f"[VDO] user.cfg actualizado: {cfg_path}")
    return True


def main():
    print("=" * 60)
    print("[VDO] Inyección de toolbar en user.cfg")
    print("=" * 60)

    if len(sys.argv) > 1:
        cfg = os.path.abspath(os.path.expanduser(sys.argv[1]))
        if not os.path.isfile(cfg):
            print(f"[VDO] ERROR: No existe el archivo: {cfg}")
            return False
    else:
        cfg = find_user_cfg()
        if not cfg:
            print("[VDO] ERROR: No se encontró user.cfg de FreeCAD")
            print("       Buscando en: ~/.config/FreeCAD/v1-1/user.cfg")
            print("       (o pasa la ruta: python3 vdo_toolbar_inject.py <user.cfg>)")
            return False

    print(f"[VDO] user.cfg: {cfg}")
    ok = inject_toolbar(cfg)

    if ok:
        print("")
        print("=" * 60)
        print("[VDO] LISTO. Reinicia FreeCAD para ver la toolbar.")
        print(f"[VDO] Toolbar '{TOOLBAR_NAME}' aparecerá en:")
        print(f"       - {WORKBENCH_TARGET}" if WORKBENCH_TARGET != "Global" else "       - TODOS los workbenches")
        print(f"       - {len(VDO_MACROS)} botones: Panel, COCO, Fachada, Hoja, Cajón, División")
        print(f"       - Atajos (máx. 4 teclas Qt): PANE, COCO, FACH, HOJA, CAJO, DIVI")
        print("=" * 60)

    return ok


if __name__ == "__main__":
    main()
