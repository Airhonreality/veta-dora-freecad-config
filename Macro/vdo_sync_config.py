#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vdo_sync_config.py
Sincroniza configuración FreeCAD (user.cfg) entre repo y local.

Uso:
  python3 vdo_sync_config.py export   # Copia ~/user.cfg → repo/config/freecad/
  python3 vdo_sync_config.py import   # Copia repo/config/freecad/ → ~/user.cfg
"""
import os
import sys
import shutil
import argparse
from pathlib import Path


def find_freecad_config():
    """Encuentra el directorio de config de FreeCAD."""
    candidates = [
        Path.home() / ".config" / "FreeCAD" / "v1-1",
        Path.home() / ".config" / "FreeCAD",
    ]
    for p in candidates:
        if (p / "user.cfg").exists():
            return p
    return None


def export_config():
    """Exporta user.cfg de FreeCAD al repo."""
    print("=" * 70)
    print("📤 EXPORTAR CONFIGURACIÓN")
    print("=" * 70)

    freecad_config_dir = find_freecad_config()
    if not freecad_config_dir:
        print("❌ FreeCAD config no encontrada")
        print("   Buscando en: ~/.config/FreeCAD/v1-1/")
        return False

    source = freecad_config_dir / "user.cfg"
    if not source.exists():
        print(f"❌ No existe: {source}")
        return False

    # Ruta destino en el repo
    repo_dir = Path(__file__).parent.parent
    dest = repo_dir / "config" / "freecad" / "user.cfg"
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Hacer backup del anterior en el repo
    if dest.exists():
        backup = dest.with_suffix('.cfg.bak')
        shutil.copy2(dest, backup)
        print(f"💾 Backup anterior: {backup.name}")

    # Copiar
    shutil.copy2(source, dest)

    print(f"\n✅ Exportado:")
    print(f"   Desde: {source}")
    print(f"   Hacia: {dest}")
    print(f"\n📌 Próximos pasos:")
    print(f"   1. Revisar cambios: git diff config/freecad/user.cfg")
    print(f"   2. git add config/freecad/user.cfg")
    print(f"   3. git commit -m 'Add toolbar configuration'")
    print(f"   4. git push")

    return True


def import_config():
    """Importa user.cfg desde el repo a FreeCAD."""
    print("=" * 70)
    print("📥 IMPORTAR CONFIGURACIÓN")
    print("=" * 70)

    repo_dir = Path(__file__).parent.parent
    source = repo_dir / "config" / "freecad" / "user.cfg"

    if not source.exists():
        print(f"❌ No existe: {source}")
        print("   El repositorio no tiene configuración guardada aún")
        return False

    freecad_config_dir = find_freecad_config()
    if not freecad_config_dir:
        print("❌ FreeCAD config no encontrada")
        return False

    dest = freecad_config_dir / "user.cfg"

    # Hacer backup del actual
    if dest.exists():
        backup = dest.with_suffix('.cfg.bak')
        shutil.copy2(dest, backup)
        print(f"💾 Backup local: {backup.name}")

    # Importar
    shutil.copy2(source, dest)

    print(f"\n✅ Importado:")
    print(f"   Desde: {source}")
    print(f"   Hacia: {dest}")
    print(f"\n📌 Próximos pasos:")
    print(f"   1. Reinicia FreeCAD")
    print(f"   2. Verifica que la toolbar y botones aparezcan")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Sincroniza configuración VDO entre repo y FreeCAD"
    )
    parser.add_argument(
        'action',
        choices=['export', 'import'],
        help="export: Copia user.cfg de FreeCAD al repo. import: Restaura desde repo"
    )

    args = parser.parse_args()

    if args.action == 'export':
        success = export_config()
    else:
        success = import_config()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
