#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vdo_detect_config.py
Detecta qué archivos de FreeCAD almacenan toolbar y acciones.
Uso: python3 vdo_detect_config.py
"""
import os
import shutil
from pathlib import Path
from datetime import datetime


def find_freecad_config():
    """Encuentra el directorio de config de FreeCAD."""
    candidates = [
        Path.home() / ".config" / "FreeCAD" / "v1-1",
        Path.home() / ".config" / "FreeCAD",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def create_snapshot():
    """Crea un snapshot de la config actual."""
    config_dir = find_freecad_config()
    if not config_dir:
        print("❌ FreeCAD config no encontrada")
        return False

    snapshot_dir = Path(__file__).parent.parent / "config" / "freecad_snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_name = f"snapshot_{timestamp}"
    snapshot_path = snapshot_dir / snapshot_name
    snapshot_path.mkdir(exist_ok=True)

    # Copiar user.cfg
    user_cfg = config_dir / "user.cfg"
    if user_cfg.exists():
        shutil.copy2(user_cfg, snapshot_path / "user.cfg")
        print(f"✅ Snapshot guardado: {snapshot_path}")
        print(f"   user.cfg ({user_cfg.stat().st_size} bytes)")
        return snapshot_path

    return False


def compare_snapshots():
    """Compara dos snapshots para ver qué cambió."""
    snapshots_dir = Path(__file__).parent.parent / "config" / "freecad_snapshots"
    if not snapshots_dir.exists():
        print("❌ Sin snapshots. Primero ejecuta: vdo_detect_config.py create")
        return

    snapshots = sorted(snapshots_dir.iterdir())
    if len(snapshots) < 2:
        print("⚠️ Se necesitan al menos 2 snapshots para comparar")
        return

    before = snapshots[-2] / "user.cfg"
    after = snapshots[-1] / "user.cfg"

    print(f"\n📊 Comparando snapshots:")
    print(f"   Antes: {snapshots[-2].name}")
    print(f"   Después: {snapshots[-1].name}")
    print(f"\nLos cambios en user.cfg son lo que necesitas copiar al repo.\n")
    print("Usa: diff -u", before, after)


def main():
    print("=" * 70)
    print("🔍 DETECTOR DE CONFIGURACIÓN VDO")
    print("=" * 70)

    print("\n📌 FLUJO DE DETECCIÓN:")
    print("  1. Ejecuta: python3 vdo_detect_config.py  # ANTES de crear toolbar")
    print("  2. En FreeCAD: Crea toolbar + botón manualmente")
    print("  3. Ejecuta: python3 vdo_detect_config.py  # DESPUÉS de crear toolbar")
    print("  4. Compara los snapshots con: diff -u config/freecad_snapshots/snapshot_*/user.cfg")
    print("  5. El archivo QUE CAMBIÓ es ~/.config/FreeCAD/v1-1/user.cfg")
    print("  6. Cópialo a: config/freecad/user.cfg (en el repo)")
    print("  7. Commit y push")

    print("\n" + "=" * 70)

    snapshot_path = create_snapshot()
    if snapshot_path:
        print("\n✅ Snapshot creado. Ahora:")
        print("   → Abre FreeCAD")
        print("   → Crea la toolbar custom con un botón")
        print("   → Guarda y cierra FreeCAD")
        print("   → Vuelve a ejecutar este script para ver los cambios")
    else:
        print("\n⚠️ No se pudo crear snapshot")


if __name__ == "__main__":
    main()
