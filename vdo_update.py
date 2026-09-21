#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vdo_update.py
Actualiza VDO desde GitHub directamente

USO:
  python3 vdo_update.py

AUTOMATIZA:
  1. git pull (trae cambios de GitHub)
  2. vdo_clone.py (instala en FreeCAD local)
  3. Listo

GARANTIZA: Siempre usa la versión NUEVA del repo, no la copia vieja
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Ejecuta comando y reporta resultado"""
    print(f"\n▶️  {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ {description}")
            return True
        else:
            print(f"❌ Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("=" * 70)
    print("🚀 VDO UPDATE - Actualizar desde GitHub")
    print("=" * 70)

    # Determinar ruta del repo
    script_path = Path(__file__).resolve()
    repo_root = script_path.parent

    print(f"\n📁 Repo: {repo_root}")

    # 1. Verificar que es un repo git
    if not (repo_root / ".git").exists():
        print(f"❌ No es un repositorio git: {repo_root}")
        return 1

    # 2. Git pull
    if not run_command(f"cd {repo_root} && git pull origin master", "Trayendo cambios de GitHub"):
        return 1

    # 3. Ejecutar vdo_clone.py desde REPO (no desde FreeCAD)
    clone_script = repo_root / "Macro" / "vdo_clone.py"
    if not clone_script.exists():
        print(f"❌ No encontrado: {clone_script}")
        return 1

    if not run_command(f"cd {repo_root} && python3 Macro/vdo_clone.py", "Instalando en FreeCAD local"):
        return 1

    # 4. Success
    print("\n" + "=" * 70)
    print("✅ ACTUALIZACIÓN COMPLETADA")
    print("=" * 70)
    print(f"\n📌 Cambios instalados en FreeCAD")
    print(f"   Reinicia FreeCAD para ver los cambios")

    return 0


if __name__ == "__main__":
    sys.exit(main())
