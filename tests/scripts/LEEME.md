# Scripts de diagnóstico (no son tests de pytest)

Estos archivos se llaman `test_*.py` pero **no son tests**: son guiones
procedimentales de sesiones de depuración. Ejecutan sus comprobaciones a
nivel de módulo, imprimen un informe, escriben un `.txt` en `$HOME` y
terminan con `sys.exit()`.

Dentro de pytest eso no es un fallo de test: es un `SystemExit` durante la
importación que **abortaba la colección completa** de la suite
(`INTERNALERROR`). Por eso viven aquí, fuera de la colección
(`collect_ignore_glob` en `tests/conftest.py`).

Se ejecutan a mano, con FreeCAD real:

```bash
FreeCADCmd tests/scripts/test_puerta_diagnostico.py
```

| Script | Qué diagnostica |
|---|---|
| `test_puerta_bug_d_fix.py` | Bug D de puertas: geometría tras el fix |
| `test_puerta_bug_simple.py` | Caso mínimo de reproducción del bug D |
| `test_puerta_coco_construir.py` | Puerta construida como inserto de un COCO |
| `test_puerta_diagnostico.py` | Volcado de cotas y placement de `make_puerta` |
| `test_rama1_deterministico.py` | Determinismo del reengrose L1 y del despiece |

Si alguna de estas comprobaciones debe proteger el código a futuro,
hay que reescribirla como `unittest.TestCase` y devolverla a `tests/`.
