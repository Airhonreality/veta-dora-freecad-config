# Tests obsoletos (no se coleccionan)

Estos tests validan una arquitectura **retirada a propósito** por
`docs/00` C-03 y ADR-003: el Inspector Lateral Flotante reactivo con
`Gui.SelectionObserver`, descartado por condiciones de carrera con Coin3D.

Los módulos que importan no existen en el paquete `VDO/`:

| Test | Módulo que importa | Estado |
|---|---|---|
| `test_gui_wiring.py` | `vdo_universal_inspector` | retirado (C-03) |
| `test_universal_inspector.py` | `vdo_universal_inspector` | retirado (C-03) |
| `test_selection_bridge.py` | `vdo_selection_bridge` | retirado (C-03) |
| `test_single_dock_convergence.py` | `vdo_inspector_dock` | retirado (C-03) |
| `test_workbench_convergence.py` | ambos | retirado (C-03) |

Se conservan sólo por trazabilidad. `tests/conftest.py` excluye esta
carpeta de la colección: antes estos 5 archivos rompían la colección de
pytest con `ModuleNotFoundError` y arrastraban a toda la suite.

Si algún día se reintroduce un canal de edición reactivo, estos tests son
el punto de partida, pero habrá que reescribirlos contra `VDO.ui.*`.
