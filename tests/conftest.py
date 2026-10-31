import sys
from pathlib import Path

# Raíz del repo (tests/..), para que "import VDO.*" resuelva
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# tests/obsoletos/ valida la arquitectura retirada por C-03 / ADR-003
# (inspector reactivo). Importa módulos que ya no existen, así que su
# simple colección rompía la suite completa con ModuleNotFoundError.
# Ver tests/obsoletos/LEEME.md.
# tests/scripts/ son guiones de diagnostico, no tests: se ejecutaban
# al importarlos y su sys.exit() abortaba la coleccion entera.
# Ver tests/scripts/LEEME.md.
collect_ignore_glob = ["obsoletos/*", "scripts/*"]


def pytest_report_header(config):
    """Deja constancia de si la suite corre con FreeCAD real o sin él."""
    try:
        import FreeCAD  # noqa: F401
        return "FreeCAD: real (los tests que crean documentos se ejecutan)"
    except ImportError:
        return ("FreeCAD: ausente (los tests que necesitan documentos se "
                "omiten; ejecútalos con FreeCADCmd)")
