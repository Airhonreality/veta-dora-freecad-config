#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install.py - Instala este repo como workbench de FreeCAD.

Pregunta a FreeCAD donde esta su directorio de usuario (no lo adivina: en
FreeCAD 1.x es ~/.local/share/FreeCAD/v1-1/, con subcarpeta de version) y
coloca el workbench en Mod/VDO_CarpinteriaParametrica.

  python3 tools/install.py            # enlace simbolico (desarrollo)
  python3 tools/install.py --copy     # copia real (otro equipo / produccion)
  python3 tools/install.py --uninstall

El enlace simbolico hace que el repo sea la unica fuente de verdad: editas
aqui y FreeCAD lo ve al reiniciar, sin pasos de sincronizacion.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WB_NAME = "VDO_CarpinteriaParametrica"
REPO = Path(__file__).resolve().parent.parent
CONTENIDO = ("Init.py", "InitGui.py", "package.xml", "metadata.txt", "VDO")


def destino_mod() -> Path:
    """Pregunta a FreeCAD su directorio de usuario real."""
    script = ("import FreeCAD, json;"
              "print('@@' + json.dumps(FreeCAD.getUserAppDataDir()))")
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(script)
        tmp = f.name
    for binario in ("freecadcmd", "FreeCADCmd"):
        try:
            out = subprocess.run([binario, tmp], capture_output=True,
                                 text=True, timeout=180).stdout
        except FileNotFoundError:
            continue
        for linea in out.splitlines():
            if linea.startswith("@@"):
                return Path(json.loads(linea[2:])) / "Mod" / WB_NAME
    sys.exit("No se encontro freecadcmd en el PATH; no puedo localizar FreeCAD.")


def desinstalar(dst: Path) -> None:
    if dst.is_symlink():
        dst.unlink()
        print(f"enlace eliminado: {dst}")
    elif dst.is_dir():
        shutil.rmtree(dst)
        print(f"directorio eliminado: {dst}")
    else:
        print(f"nada que desinstalar en {dst}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--copy", action="store_true",
                    help="copia los archivos en vez de enlazar el repo")
    ap.add_argument("--uninstall", action="store_true")
    args = ap.parse_args()

    dst = destino_mod()
    print(f"repo    : {REPO}")
    print(f"destino : {dst}")

    if args.uninstall:
        desinstalar(dst)
        return 0

    faltan = [c for c in CONTENIDO if not (REPO / c).exists()]
    if faltan:
        sys.exit(f"El repo esta incompleto, falta: {faltan}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    desinstalar(dst)

    if args.copy:
        dst.mkdir(parents=True)
        for nombre in CONTENIDO:
            origen = REPO / nombre
            if origen.is_dir():
                shutil.copytree(origen, dst / nombre,
                                ignore=shutil.ignore_patterns(
                                    "__pycache__", "*.pyc", "*.bak"))
            else:
                shutil.copy2(origen, dst / nombre)
        print(f"instalado por copia ({len(CONTENIDO)} entradas)")
    else:
        dst.symlink_to(REPO, target_is_directory=True)
        print("instalado por enlace simbolico (el repo es la fuente de verdad)")

    print("\nReinicia FreeCAD y elige 'VDO - Muebles Parametricos' en el "
          "selector de workbenches.")
    print("Verifica con: python3 tools/vdo_verify.py --gui")
    return 0


if __name__ == "__main__":
    sys.exit(main())
