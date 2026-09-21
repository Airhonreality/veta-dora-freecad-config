#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vdo_clone.py
Clona VDO (macros + configuración) desde repo → FreeCAD local

Uso:
  Terminal:  python3 Macro/vdo_clone.py
  FreeCAD:   Macro → Ejecutar → vdo_clone.py
"""
import os
import sys
import shutil
from pathlib import Path


# =====================================================================
# DETECTAR CONTEXTO
# =====================================================================

FREECAD_AVAILABLE = False
try:
    import FreeCAD as App
    FREECAD_AVAILABLE = True
except ImportError:
    pass


# =====================================================================
# RUTAS - Detectar dónde está todo
# =====================================================================

def get_freecad_macro_dir():
    """Obtiene la carpeta de macros de FreeCAD (con prioridad a FreeCAD si está disponible)."""
    if FREECAD_AVAILABLE:
        return App.getUserMacroDir(True)

    # Fallback: rutas estándar
    candidates = [
        Path.home() / ".local" / "share" / "FreeCAD" / "Macro",
        Path.home() / ".config" / "FreeCAD" / "Macro",
        Path.home() / "AppData" / "Roaming" / "FreeCAD" / "Macro",  # Windows
    ]
    for p in candidates:
        if p.exists():
            return str(p)

    # Crear por defecto
    default = Path.home() / ".local" / "share" / "FreeCAD" / "Macro"
    default.mkdir(parents=True, exist_ok=True)
    return str(default)


def get_freecad_config_dir():
    """Obtiene la carpeta de configuración de FreeCAD."""
    candidates = [
        Path.home() / ".config" / "FreeCAD" / "v1-1",
        Path.home() / ".config" / "FreeCAD",
        Path.home() / "AppData" / "Roaming" / "FreeCAD" / "v1-1",  # Windows
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def find_repo_root():
    """Busca la raíz del repositorio VDO."""
    # Si se ejecuta desde Macro/, subir un nivel
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    # Verificar que tiene estructura VDO
    if (repo_root / "Macro").exists() and (repo_root / "config").exists():
        return repo_root

    # Búsqueda alternativa: buscar .git
    for parent in script_dir.parents:
        if (parent / ".git").exists() and (parent / "Macro").exists():
            return parent

    # Fallback: usar directorio del script
    return repo_root


# =====================================================================
# CLONACIÓN
# =====================================================================

def clone_macros(repo_root, freecad_macro_dir):
    """Copia macros desde repo → FreeCAD."""
    print("\n📦 Clonando macros...")

    src_macros = repo_root / "Macro"
    if not src_macros.exists():
        print(f"  ❌ Carpeta no encontrada: {src_macros}")
        return 0

    dst_dir = Path(freecad_macro_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for file in src_macros.glob("*"):
        if file.is_file():
            dst = dst_dir / file.name
            try:
                shutil.copy2(file, dst)
                print(f"  ✅ {file.name}")
                count += 1
            except Exception as e:
                print(f"  ❌ {file.name}: {e}")

    return count


def clone_config(repo_root, freecad_config_dir):
    """Restaura user.cfg desde repo → FreeCAD."""
    if not freecad_config_dir:
        print("\n⚠️  Config dir no encontrado")
        return False

    print("\n⚙️  Restaurando configuración...")

    src_config = repo_root / "config" / "freecad" / "user.cfg"
    if not src_config.exists():
        print(f"  ℹ️  Sin configuración guardada (primera instalación)")
        return True

    dst_config = freecad_config_dir / "user.cfg"

    # Backup del actual
    if dst_config.exists():
        backup = dst_config.with_suffix(".cfg.bak")
        shutil.copy2(dst_config, backup)
        print(f"  💾 Backup anterior: user.cfg.bak")

    # Restaurar
    try:
        shutil.copy2(src_config, dst_config)
        print(f"  ✅ Configuración restaurada")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def register_workbench(freecad_macro_dir):
    """Registra workbench VDO (solo si FreeCAD está disponible)."""
    if not FREECAD_AVAILABLE or not App.GuiUp:
        return True

    print("\n🔧 Registrando workbench VDO...")

    try:
        # Importar InitGui para que se registre el workbench
        macro_path = Path(freecad_macro_dir)
        sys.path.insert(0, str(macro_path))

        import InitGui as vdo_gui
        print(f"  ✅ Workbench VDO registrado")
        return True
    except Exception as e:
        print(f"  ℹ️  Workbench no auto-registrado: {e}")
        print(f"     (Puede registrarse manualmente desde FreeCAD)")
        return True


# =====================================================================
# MAIN
# =====================================================================

def main():
    print("=" * 70)
    print("🚀 VDO CLONE - Sistema de Clonación Minimalista")
    print("=" * 70)

    # 1. Detectar rutas
    print("\n🔍 Detectando rutas...")

    repo_root = find_repo_root()
    print(f"  📁 Repo: {repo_root}")

    freecad_macro_dir = get_freecad_macro_dir()
    print(f"  📁 Macros FreeCAD: {freecad_macro_dir}")

    freecad_config_dir = get_freecad_config_dir()
    if freecad_config_dir:
        print(f"  📁 Config FreeCAD: {freecad_config_dir}")
    else:
        print(f"  ⚠️  Config dir no encontrado (primera vez)")

    # 2. Clonar
    print("\n" + "=" * 70)

    macros_count = clone_macros(repo_root, freecad_macro_dir)
    config_ok = clone_config(repo_root, freecad_config_dir) if freecad_config_dir else True

    # 3. Registrar (solo si está disponible FreeCAD)
    if FREECAD_AVAILABLE and App.GuiUp:
        register_workbench(freecad_macro_dir)

    # 4. Resumen
    print("\n" + "=" * 70)
    if macros_count > 0 and config_ok:
        print("✅ CLONACIÓN COMPLETADA")
        print("=" * 70)
        print(f"\n  ✓ {macros_count} macros copiadas")
        print(f"  ✓ Configuración restaurada")

        if FREECAD_AVAILABLE:
            print(f"\n  📌 Próximo paso:")
            print(f"     1. Si está dentro de FreeCAD: Reinicia FreeCAD")
            print(f"     2. Verifica que la toolbar 'CARPINTERIA' aparece")
            print(f"     3. Selecciona workbench 'VDO - Muebles Paramétricos'")
        else:
            print(f"\n  📌 Próximo paso:")
            print(f"     Abre FreeCAD y verifica que las macros aparecen")

        return 0
    else:
        print("⚠️  CLONACIÓN INCOMPLETA")
        print("=" * 70)
        return 1


# =====================================================================
# EJECUCIÓN
# =====================================================================

if __name__ == "__main__":
    sys.exit(main())
