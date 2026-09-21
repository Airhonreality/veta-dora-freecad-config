#!/usr/bin/env python3
"""
vdo_toolbar_inject.py
Inyecta toolbar VDO en user.cfg de FreeCAD SIN workbench.
Aparece en BIMWorkbench (y opcionalmente en todos los workbenches).

USO: python3 vdo_toolbar_inject.py
     o ejecutar dentro de FreeCAD: Macro → Ejecutar → vdo_toolbar_inject.py
"""
import os
import sys
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime

# ============================================================
# CONFIGURACIÓN DE MACROS VDO
# ============================================================

VDO_MACROS = [
    {
        "name": "Std_Macro_0",
        "script": "VDO_Crear_Hoja_Melamina.FCMacro",
        "menu": "Crear Hoja",
        "tooltip": "Crear hoja de melamina con parámetros",
        "pixmap": "vdo_workbench",
    },
    {
        "name": "Std_Macro_1",
        "script": "vdo_panel_estandar.FCMacro",
        "menu": "Panel Estándar",
        "tooltip": "Panel estándar paramétrico con cantos selectivos",
        "pixmap": "vdo_panel_estandar",
    },
    {
        "name": "Std_Macro_2",
        "script": "vdo_panel_fachada.FCMacro",
        "menu": "Panel Fachada",
        "tooltip": "Panel fachada con 4 cantos gruesos",
        "pixmap": "vdo_panel_fachada",
    },
    {
        "name": "Std_Macro_3",
        "script": "vdo_coco_4c.FCMacro",
        "menu": "COCO 4C",
        "tooltip": "Cajón 4 caras paramétrico",
        "pixmap": "vdo_coco",
    },
]

TOOLBAR_NAME = "CARPINTERIA - VDO"
TOOLBAR_GROUP = "Custom_1"
# Para que aparezca en TODOS los workbenches, usar "Global"
# Para que aparezca solo en BIM, usar "BIMWorkbench"
WORKBENCH_TARGET = "Global"


def find_user_cfg():
    """Encuentra user.cfg de FreeCAD."""
    candidates = [
        os.path.expanduser("~/.config/FreeCAD/v1-1/user.cfg"),
        os.path.expanduser("~/.config/FreeCAD/user.cfg"),
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

    # ============================================================
    # 1. Definir macros en BaseApp/Macro/Macros
    # ============================================================
    macro_base = baseapp.find("FCParamGroup[@Name='Macro']")
    if macro_base is None:
        macro_base = ET.SubElement(baseapp, "FCParamGroup", Name="Macro")

    macros_group = macro_base.find("FCParamGroup[@Name='Macros']")
    if macros_group is None:
        macros_group = ET.SubElement(macro_base, "FCParamGroup", Name="Macros")

    # Eliminar macros VDO existentes (Std_Macro_0 a Std_Macro_3)
    for macro in VDO_MACROS:
        existing = macros_group.find(f"FCParamGroup[@Name='{macro['name']}']")
        if existing is not None:
            macros_group.remove(existing)
            print(f"[VDO] Eliminada definición existente: {macro['name']}")

    # Crear macros VDO
    for macro in VDO_MACROS:
        grp = ET.SubElement(macros_group, "FCParamGroup", Name=macro["name"])
        ET.SubElement(grp, "FCText", Name="Script").text = macro["script"]
        ET.SubElement(grp, "FCText", Name="Menu").text = macro["menu"]
        ET.SubElement(grp, "FCText", Name="Tooltip").text = macro["tooltip"]
        ET.SubElement(grp, "FCText", Name="WhatsThis").text = macro["tooltip"]
        ET.SubElement(grp, "FCText", Name="Statustip").text = macro["menu"]
        ET.SubElement(grp, "FCText", Name="Pixmap").text = macro["pixmap"]
        ET.SubElement(grp, "FCText", Name="Accel").text = ""
        ET.SubElement(grp, "FCBool", Name="System", Value="0")
        print(f"[VDO] Macro definida: {macro['name']} → {macro['script']}")

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
            # Verificar si ya existe
            existing = toolbars_vis.find(f"FCBool[@Name='{TOOLBAR_NAME}']")
            if existing is None:
                ET.SubElement(toolbars_vis, "FCBool", Name=TOOLBAR_NAME, Value="1")
                print(f"[VDO] Toolbar marcada como visible")

    # ============================================================
    # 4. Guardar
    # ============================================================
    ET.indent(tree, space="  ")
    tree.write(cfg_path, encoding="UTF-8", xml_declaration=True)
    print(f"[VDO] user.cfg actualizado: {cfg_path}")

    return True


def main():
    print("=" * 60)
    print("[VDO] Inyección de toolbar en user.cfg")
    print("=" * 60)

    cfg = find_user_cfg()
    if not cfg:
        print("[VDO] ERROR: No se encontró user.cfg de FreeCAD")
        print("       Buscando en: ~/.config/FreeCAD/v1-1/user.cfg")
        return False

    print(f"[VDO] user.cfg: {cfg}")
    ok = inject_toolbar(cfg)

    if ok:
        print("")
        print("=" * 60)
        print("[VDO] LISTO. Reinicia FreeCAD para ver la toolbar.")
        print(f"[VDO] Toolbar '{TOOLBAR_NAME}' aparecerá en:")
        print(f"       - {WORKBENCH_TARGET}" if WORKBENCH_TARGET != "Global" else "       - TODOS los workbenches")
        print(f"       - {len(VDO_MACROS)} botones: Crear Hoja, Panel Estándar, Panel Fachada, COCO 4C")
        print("=" * 60)

    return ok


if __name__ == "__main__":
    main()
