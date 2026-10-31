#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ejecuta la suite de tests DENTRO de FreeCAD.

    FreeCADCmd tools/run_tests_freecad.py

Por qué hace falta: buena parte de la suite crea documentos y sólidos
reales. Con `python3 -m pytest` esos tests se omiten (ver
`tests/_entorno.HAY_FREECAD`); aquí se ejecutan de verdad.

Dos detalles del entorno que este script resuelve:

1. **El resumen se escribe a un archivo.** FreeCADCmd segfaltea en
   `PySide::destroyQCoreApplication()` al cerrar una sesión de consola que
   importó QtWidgets. Es un crash de *teardown*, posterior a los tests,
   pero se lleva por delante la salida y el código de retorno.
2. **Se sale con `os._exit()`** para saltarse ese `finalize()`.
"""

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RESUMEN = RAIZ / ".verif" / "pytest_resumen.txt"


class _Resumen:
    """Vuelca el recuento a disco antes de que FreeCAD cierre."""

    def pytest_terminal_summary(self, terminalreporter):
        stats = terminalreporter.stats
        lineas = []
        for estado in ("passed", "failed", "error", "skipped", "xfailed"):
            n = len(stats.get(estado, []))
            if n:
                lineas.append(f"{estado}={n}")
        for estado in ("failed", "error"):
            for rep in stats.get(estado, []):
                lineas.append(f"  {estado.upper()}: {rep.nodeid}")
        RESUMEN.parent.mkdir(parents=True, exist_ok=True)
        RESUMEN.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def main():
    if str(RAIZ) not in sys.path:
        sys.path.insert(0, str(RAIZ))
    try:
        import pytest
    except ImportError:
        sys.stderr.write(
            "pytest no esta disponible para el Python de FreeCAD.\n")
        return 2

    codigo = pytest.main(
        ["-q", "--no-header", "-p", "no:cacheprovider", "--tb=line",
         str(RAIZ / "tests")] + sys.argv[1:],
        plugins=[_Resumen()])

    print(f"\nResumen en {RESUMEN}")
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(codigo)


# Sin guarda de __main__ a proposito: FreeCADCmd ejecuta el script con
# exec() y __name__ NO vale "__main__", asi que con la guarda no se
# ejecutaba nada (el mismo motivo por el que Init.py no puede usar
# __file__; ver README, "Tres trampas de FreeCAD").
main()
