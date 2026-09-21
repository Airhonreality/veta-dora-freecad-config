# -*- coding: utf-8 -*-
# =====================================================================
# vdo_install.py
# Instalador Maestro VDO - Veta de Oro
# Aplanado Inteligente + Registro de Comandos + Toolbar Automática
#
# USO: Ejecutar este archivo DENTRO de FreeCAD
#      Macro → Ejecutar → Seleccionar vdo_install.py
# =====================================================================

import os
import sys
import shutil

# Verificar que estamos en FreeCAD
try:
    import FreeCAD as App
    import FreeCADGui as Gui
    FREECAD_AVAILABLE = True
except ImportError:
    FREECAD_AVAILABLE = False
    print("❌ Este script debe ejecutarse DENTRO de FreeCAD")
    print("   Abra FreeCAD → Macro → Ejecutar → Seleccione vdo_install.py")


# =====================================================================
# BLOQUE 1: DETECCIÓN DE RUTAS
# =====================================================================

def obtener_ruta_macros():
    """Obtiene la ruta oficial de macros de FreeCAD."""
    if FREECAD_AVAILABLE:
        return App.getUserMacroDir(True)  # Incluye / al final
    else:
        # Fallback para testing fuera de FreeCAD
        return os.path.expanduser("~/.local/share/FreeCAD/Macro/")


def obtener_ruta_repositorio():
    """Obtiene la ruta del repositorio de desarrollo."""
    # El instalador está en la raíz del repositorio
    return os.path.dirname(os.path.abspath(__file__))


# =====================================================================
# BLOQUE 2: APLANADO DE ARCHIVOS
# =====================================================================

def aplanar_archivos(ruta_origen, ruta_destino):
    """
    Copia archivos de Macro/ a FreeCAD Macro dir.
    
    Estructura origen:
      /Macro/*.py, *.FCMacro  →  raíz de macros
      /Macro/icons/*.svg      →  raíz de macros
    """
    print("\n📦 Copiando archivos...")
    
    # Mapeo de carpetas origen (ahora todo está en Macro/)
    ruta_src = os.path.join(ruta_origen, "Macro")
    
    if not os.path.exists(ruta_src):
        print(f"  ⚠️ Carpeta no encontrada: Macro/")
        return 0
    
    print(f"\n  📂 Macro/ (fuente canónica):")
    
    archivos_copiados = 0
    for archivo in os.listdir(ruta_src):
        src = os.path.join(ruta_src, archivo)
        dst = os.path.join(ruta_destino, archivo)
        
        if os.path.isfile(src):
            try:
                shutil.copy2(src, dst)
                print(f"    ✅ {archivo}")
                archivos_copiados += 1
            except Exception as e:
                print(f"    ❌ Error copiando {archivo}: {e}")
    
    # Copiar subdirectorio icons/ si existe
    icons_src = os.path.join(ruta_src, "icons")
    if os.path.exists(icons_src):
        print(f"\n  📂 icons/:")
        for archivo in os.listdir(icons_src):
            src = os.path.join(icons_src, archivo)
            dst = os.path.join(ruta_destino, archivo)
            if os.path.isfile(src):
                try:
                    shutil.copy2(src, dst)
                    print(f"    ✅ {archivo}")
                    archivos_copiados += 1
                except Exception as e:
                    print(f"    ❌ Error copiando {archivo}: {e}")
    
    print(f"\n📊 Total archivos copiados: {archivos_copiados}")
    return archivos_copiados


# =====================================================================
# BLOQUE 3: DEFINICIÓN DE COMANDOS VDO (solo dentro de FreeCAD)
# =====================================================================

def _registrar_comandos_freecad():
    """Registra comandos VDO en FreeCAD GUI. Solo se llama desde FreeCAD."""
    if not FREECAD_AVAILABLE or not App.GuiUp:
        return

    class VDO_Cmd_PanelEstandar:
        def GetResources(self):
            return {"Pixmap": "vdo_panel_estandar", "MenuText": "Panel Estándar",
                    "ToolTip": "Crea panel de melamina estándar con cantos selectivos"}
        def Activated(self):
            f = os.path.join(obtener_ruta_macros(), "vdo_panel_estandar.FCMacro")
            if os.path.exists(f): exec(open(f).read())
        def IsActive(self):
            return App.ActiveDocument is not None

    class VDO_Cmd_PanelFachada:
        def GetResources(self):
            return {"Pixmap": "vdo_panel_fachada", "MenuText": "Panel Fachada",
                    "ToolTip": "Crea panel de fachada con 4 cantos gruesos"}
        def Activated(self):
            f = os.path.join(obtener_ruta_macros(), "vdo_panel_fachada.FCMacro")
            if os.path.exists(f): exec(open(f).read())
        def IsActive(self):
            return App.ActiveDocument is not None

    class VDO_Cmd_Coco4C:
        def GetResources(self):
            return {"Pixmap": "vdo_coco", "MenuText": "COCO 4C",
                    "ToolTip": "Genera contenedor de 4 paneles con fondo paramétrico"}
        def Activated(self):
            f = os.path.join(obtener_ruta_macros(), "vdo_coco_4c.FCMacro")
            if os.path.exists(f): exec(open(f).read())
        def IsActive(self):
            return App.ActiveDocument is not None

    class VDO_Cmd_CrearHoja:
        def GetResources(self):
            return {"Pixmap": "vdo_workbench", "MenuText": "Crear Hoja Parámetros",
                    "ToolTip": "Crea las hojas Params_Melamina y Params"}
        def Activated(self):
            f = os.path.join(obtener_ruta_macros(), "VDO_Crear_Hoja_Melamina.FCMacro")
            if os.path.exists(f): exec(open(f).read())
        def IsActive(self):
            return True

    comandos = [
        ("VDO_PanelEstandar", VDO_Cmd_PanelEstandar()),
        ("VDO_PanelFachada", VDO_Cmd_PanelFachada()),
        ("VDO_Coco4C", VDO_Cmd_Coco4C()),
        ("VDO_CrearHoja", VDO_Cmd_CrearHoja()),
    ]
    for nombre, instancia in comandos:
        try:
            Gui.addCommand(nombre, instancia)
        except Exception as e:
            print(f"  ❌ Error registrando {nombre}: {e}")


# =====================================================================
# BLOQUE 5: WORKBENCH VDO (solo si FreeCAD GUI está disponible)
# =====================================================================

if FREECAD_AVAILABLE and App.GuiUp:
    class VDO_Workbench(Gui.Workbench):
        """Workbench VDO - Muebles Paramétricos."""
        
        def __init__(self):
            icon_path = os.path.join(obtener_ruta_macros(), "vdo_workbench.svg")
            if os.path.exists(icon_path):
                self.__class__.Icon = icon_path
            self.__class__.MenuText = "VDO - Muebles Paramétricos"
            self.__class__.ToolTip = "Motor paramétrico Veta de Oro para muebles de melamina"
        
        def Initialize(self):
            """Se ejecuta una vez al cargar el workbench."""
            _registrar_comandos_freecad()
            cmdList = [
                "VDO_CrearHoja",
                "Separator",
                "VDO_PanelEstandar",
                "VDO_PanelFachada",
                "Separator",
                "VDO_Coco4C",
            ]
            self.appendToolbar("VDO - Muebles Paramétricos", cmdList)
            self.appendMenu(["&VDO"], cmdList)
        
        def Activated(self):
            pass
        
        def Deactivated(self):
            pass
        
        def GetClassName(self):
            return "Gui::PythonWorkbench"


# =====================================================================
# BLOQUE 6: INSTALADOR PRINCIPAL
# =====================================================================

def instalar_vdo():
    """Función principal del instalador."""
    print("=" * 60)
    print("🚀 INSTALADOR VDO - Veta de Oro")
    print("   Motor Paramétrico de Muebles de Melamina")
    print("=" * 60)
    
    # 1. Detectar rutas
    ruta_macros = obtener_ruta_macros()
    ruta_origen = obtener_ruta_repositorio()
    
    print(f"\n📁 Repositorio origen: {ruta_origen}")
    print(f"📁 FreeCAD Macro dir: {ruta_macros}")
    
    # Verificar que la carpeta de macros existe
    if not os.path.exists(ruta_macros):
        try:
            os.makedirs(ruta_macros)
            print(f"✅ Carpeta de macros creada: {ruta_macros}")
        except Exception as e:
            print(f"❌ No se pudo crear la carpeta de macros: {e}")
            return False
    
    # 2. Aplanar archivos
    archivos_copiados = aplanar_archivos(ruta_origen, ruta_macros)
    
    if archivos_copiados == 0:
        print("\n⚠️ No se copiaron archivos. Verifique la estructura del repositorio.")
        return False
    
    # 3. Registrar workbench (si hay GUI)
    if FREECAD_AVAILABLE and App.GuiUp:
        print("\n🔧 Registrando workbench VDO...")
        
        try:
            # Verificar si el workbench ya está registrado
            workbenches = Gui.listWorkbenches()
            
            if "VDO_Workbench" not in workbenches:
                Gui.addWorkbench(VDO_Workbench())
                print("✅ Workbench 'VDO - Muebles Paramétricos' registrado")
            else:
                print("ℹ️ Workbench ya registrado, actualizando...")
            
            # Activar workbench
            try:
                Gui.activateWorkbench("VDO_Workbench")
                print("✅ Workbench activado")
            except Exception as e:
                print(f"⚠️ No se pudo activar workbench automáticamente: {e}")
                print("   Puede activarlo manualmente desde el menú Workbench")
        
        except Exception as e:
            print(f"❌ Error registrando workbench: {e}")
            return False
    
    elif not FREECAD_AVAILABLE:
        print("\n⚠️ FreeCAD no detectado. Solo se copiaron archivos.")
        print("   Para completar la instalación, ejecute este script dentro de FreeCAD.")

    # 4. Restaurar configuración personalizada
    restaurar_configuracion(ruta_origen)

    # 5. Resumen final
    print("\n" + "=" * 60)
    print("✅ INSTALACIÓN COMPLETADA")
    print("=" * 60)
    print("\n📌 Próximos pasos:")
    print("   1. Reiniciar FreeCAD (recomendado)")
    print("   2. Seleccionar workbench 'VDO - Muebles Paramétricos'")
    print("   3. Usar botones de la toolbar:")
    print("      - Crear Hoja Parámetros (primera vez)")
    print("      - Panel Estándar")
    print("      - Panel Fachada")
    print("      - COCO 4C")
    
    return True


# =====================================================================
# BLOQUE 7: RESTAURACIÓN DE CONFIGURACIÓN
# =====================================================================

def restaurar_configuracion(ruta_repo):
    """Restaura configuración de usuario (user.cfg) desde el repo."""
    config_source = os.path.join(ruta_repo, "config", "freecad", "user.cfg")

    if not os.path.exists(config_source):
        print("\n⚠️ Configuración personalizada no encontrada (config/freecad/user.cfg)")
        print("   Esto es normal si es la primera instalación.")
        return True

    freecad_config_dir = None
    candidates = [
        os.path.expanduser("~/.config/FreeCAD/v1-1"),
        os.path.expanduser("~/.config/FreeCAD"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            freecad_config_dir = candidate
            break

    if not freecad_config_dir:
        print("\n⚠️ No se encontró directorio de configuración de FreeCAD")
        print("   Se ignorará la restauración de toolbar")
        return True

    config_dest = os.path.join(freecad_config_dir, "user.cfg")

    # Hacer backup del actual
    if os.path.exists(config_dest):
        backup = config_dest + ".bak_before_vdo"
        try:
            shutil.copy2(config_dest, backup)
            print(f"\n🔒 Backup local guardado: user.cfg.bak_before_vdo")
        except Exception as e:
            print(f"\n⚠️ No se pudo hacer backup: {e}")

    # Restaurar
    try:
        shutil.copy2(config_source, config_dest)
        print(f"\n✅ Configuración restaurada (toolbar, botones)")
        print(f"   ⚠️ IMPORTANTE: Reinicia FreeCAD para ver los cambios")
        return True
    except Exception as e:
        print(f"\n❌ Error restaurando configuración: {e}")
        return False


# =====================================================================
# EJECUCIÓN PRINCIPAL
# =====================================================================

if __name__ == "__main__":
    instalar_vdo()
else:
    # Si se importa como módulo, ejecutar automáticamente
    instalar_vdo()
