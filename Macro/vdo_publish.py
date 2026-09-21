#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vdo_publish.py
Publica cambios del SDK completo (macros + configuración) a GitHub

Uso: FreeCAD → Macro → Ejecutar → vdo_publish.py

Sincroniza TODO:
  1. Macros nuevas/modificadas (*.py, *.FCMacro, *.svg)
  2. Configuración (toolbar, settings)
  3. git add/commit/push automático
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime


FREECAD_AVAILABLE = False
try:
    import FreeCAD as App
    FREECAD_AVAILABLE = True
except ImportError:
    pass


def find_repo_root():
    """Encuentra la raíz del repositorio VDO."""
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    if (repo_root / "Macro").exists() and (repo_root / "config").exists():
        return repo_root

    for parent in script_dir.parents:
        if (parent / ".git").exists() and (parent / "Macro").exists():
            return parent

    return repo_root


def get_freecad_macro_dir():
    """Obtiene la carpeta de macros de FreeCAD."""
    if FREECAD_AVAILABLE:
        return App.getUserMacroDir(True)

    candidates = [
        Path.home() / ".local" / "share" / "FreeCAD" / "Macro",
        Path.home() / ".config" / "FreeCAD" / "Macro",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return None


def get_freecad_config_dir():
    """Obtiene la carpeta de configuración de FreeCAD."""
    candidates = [
        Path.home() / ".config" / "FreeCAD" / "v1-1",
        Path.home() / ".config" / "FreeCAD",
    ]
    for p in candidates:
        if (p / "user.cfg").exists():
            return p
    return None


def sync_macros(freecad_macro_dir, repo_root):
    """Sincroniza macros de FreeCAD al repo."""
    print("📤 Sincronizando macros...")

    if not freecad_macro_dir or not Path(freecad_macro_dir).exists():
        print("  ⚠️  Macro dir no encontrado")
        return 0

    src_dir = Path(freecad_macro_dir)
    dst_dir = repo_root / "Macro"
    dst_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for file in src_dir.glob("*"):
        if file.is_file() and file.suffix in [".py", ".FCMacro", ".svg"]:
            dst = dst_dir / file.name

            # Verificar si cambió
            if dst.exists():
                if file.read_bytes() == dst.read_bytes():
                    continue

            try:
                shutil.copy2(file, dst)
                print(f"  ✅ {file.name}")
                count += 1
            except Exception as e:
                print(f"  ⚠️  {file.name}: {e}")

    return count


def sync_config(freecad_config_dir, repo_root):
    """Sincroniza configuración (user.cfg) al repo."""
    print("⚙️  Sincronizando configuración...")

    if not freecad_config_dir:
        print("  ⚠️  Config dir no encontrado")
        return 0

    src = freecad_config_dir / "user.cfg"
    if not src.exists():
        print("  ⚠️  user.cfg no encontrado")
        return 0

    dst = repo_root / "config" / "freecad" / "user.cfg"
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Verificar si cambió
    if dst.exists():
        if src.read_bytes() == dst.read_bytes():
            print("  ℹ️  Sin cambios")
            return 0

    shutil.copy2(src, dst)
    print(f"  ✅ user.cfg actualizado")
    return 1


def git_add_all(repo_root):
    """Ejecuta git add ."""
    print(f"\n📝 git add .")
    try:
        result = subprocess.run(
            ["git", "add", "."],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"  ✅ Archivos staged")
            return True
        else:
            # git add . retorna 0 incluso si no hay cambios
            return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def git_commit(repo_root, message):
    """Ejecuta git commit."""
    print(f"\n💾 git commit...")
    try:
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"  ✅ {message}")
            return True
        elif "nothing to commit" in result.stderr:
            print(f"  ℹ️  Sin cambios para commit")
            return None  # Retorna None = sin cambios
        else:
            print(f"  ❌ {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def git_push(repo_root):
    """Ejecuta git push."""
    print(f"\n🚀 git push...")
    try:
        result = subprocess.run(
            ["git", "push", "origin", "master"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"  ✅ Push completado")
            return True
        else:
            print(f"  ❌ {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    print("=" * 70)
    print("🚀 VDO PUBLISH - SDK Completo a GitHub")
    print("=" * 70)

    if not FREECAD_AVAILABLE:
        print("\n❌ Este script debe ejecutarse DENTRO de FreeCAD")
        print("   FreeCAD → Macro → Ejecutar → vdo_publish.py")
        return 1

    # 1. Detectar rutas
    print("\n🔍 Detectando rutas...")
    repo_root = find_repo_root()
    freecad_macro_dir = get_freecad_macro_dir()
    freecad_config_dir = get_freecad_config_dir()

    print(f"  📁 Repo: {repo_root}")
    print(f"  📁 Macros FreeCAD: {freecad_macro_dir}")
    print(f"  📁 Config FreeCAD: {freecad_config_dir}")

    if not (repo_root / ".git").exists():
        print(f"\n❌ No es un repositorio git: {repo_root}")
        return 1

    # 2. Sincronizar
    print("\n" + "=" * 70)
    print("📦 SINCRONIZANDO SDK")
    print("=" * 70)

    macros_count = sync_macros(freecad_macro_dir, repo_root)
    config_count = sync_config(freecad_config_dir, repo_root)

    total_changes = macros_count + config_count

    if total_changes == 0:
        print("\n" + "=" * 70)
        print("ℹ️  Sin cambios para publicar")
        print("=" * 70)
        return 0

    print(f"\n  Cambios detectados: {total_changes}")

    # 3. Git workflow
    print("\n" + "=" * 70)
    print("🔧 GIT WORKFLOW")
    print("=" * 70)

    if not git_add_all(repo_root):
        print("\n❌ Error en git add")
        return 1

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    message = f"Update SDK: {macros_count} macros, {config_count} config ({timestamp})"

    commit_result = git_commit(repo_root, message)
    if commit_result is False:
        print("\n❌ Error en git commit")
        return 1

    if commit_result is None:
        print("\n" + "=" * 70)
        print("ℹ️  Sin cambios en git")
        print("=" * 70)
        return 0

    if not git_push(repo_root):
        print("\n❌ Error en git push")
        print("   Verifica que tienes acceso a GitHub")
        return 1

    # 4. Éxito
    print("\n" + "=" * 70)
    print("✅ SDK PUBLICADO EN GITHUB")
    print("=" * 70)
    print(f"\n  Cambios:")
    print(f"    ✓ {macros_count} macros sincronizadas")
    print(f"    ✓ {config_count} configuraciones actualizadas")
    print(f"    ✓ Commit: {message}")
    print(f"    ✓ Push completado")
    print(f"\n  Otros usuarios pueden traer estos cambios con:")
    print(f"    git pull origin master")
    print(f"    python3 Macro/vdo_clone.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
