# -*- coding: utf-8 -*-
"""Detección del entorno de ejecución de la suite.

`HAY_FREECAD` distingue el FreeCAD de verdad (FreeCADCmd / freecad) de un
stub de pruebas. No vale con `import FreeCAD`: tests/test_cajon_core.py
instala un mock en sys.modules cuando no hay FreeCAD, y ese mock satisface
el import pero no sabe crear documentos. El discriminante es newDocument().
"""

try:
    import FreeCAD as _fc
except ImportError:
    HAY_FREECAD = False
else:
    HAY_FREECAD = hasattr(_fc, "newDocument")
