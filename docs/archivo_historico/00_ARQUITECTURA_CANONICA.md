# 00_ARQUITECTURA_CANONICA

Muro de contención de entropia y reglas básicas del ecosistema FreeCAD para el workbench VDO Carpintería Paramétrica.

Este archivo es la única fuente de verdad estructural. No contiene lógica de negocio. Solo define forma, capas, dependencias y reglas de empaquetado.

---

## 1. Estándar de empaquetado (Addon Manager FreeCAD)

- `package.xml` en la raíz del repositorio (manifiesto REP 149, formato 1.0).
- `metadata.txt` para dependencias de Python (`pylibs=`, `optionalpylibs=`).
- `package.xml` debe declarar: `<name>`, `<version>`, `<license>`, `<icon>`, `<content><workbench><classname>`, `<subdirectory>`, `<depend>`.
- Iconos en `resources/icons/` (SVG vectoriales).

---

## 2. Estructura de capas (paquete Python `VDO/`)

```
VDO/
├── __init__.py
├── Init.py            # Punto de entrada sin GUI (headless / consola)
├── InitGui.py         # Registro de Workbench, toolbars, menús (GUI exclusivo)
├── vdo_manifest.json  # Configuración y tolerancias de taller
├── vdo_hardware_catalog.json
│
├── math/              # CAPA 0: Matemáticas y algoritmos puros (cero CAD, cero UI)
├── hub/               # CAPA 1: Catálogos, defaults, resolución de datos
├── cad/               # CAPAS 2 y 3: Motor geométrico y enlace FreeCAD
│   ├── objects/       # Proxies FeaturePython (agnósticos a GUI)
│   └── views/         # ViewProviders Coin3D (exclusivos GUI)
├── ui/                # CAPA 4: Task Panels, widgets, comandos GUI (PySide)
└── cam/               # CAPA 5: CAM, documentación, fabricación
```

### Reglas de dependencias entre capas

- CAPA 0 (`math/`) no importa de ninguna otra capa del paquete.
- CAPA 1 (`hub/`) importa solo de CAPA 0.
- CAPA 2/3 (`cad/objects/`) importa de CAPA 0 y CAPA 1.
- CAPA views (`cad/views/`) importa de `cad/objects/` y de FreeCADGui/pivy. Nunca se importa desde `math/` ni desde `cad/objects/`.
- CAPA 4 (`ui/`) importa de todas las capas inferiores y de PySide/FreeCADGui.
- CAPA 5 (`cam/`) importa de CAPA 0 y CAPA 1.

---

## 3. Patrón de Comandos GUI

Cada acción de toolbar o menú debe ser una clase Python con:
- `GetResources()` → `Pixmap`, `MenuText`, `ToolTip`.
- `IsActive()` → condición de habilitación (ej. `FreeCAD.ActiveDocument is not None`).
- `Activated()` → lógica de ejecución.

Registro: `FreeCADGui.addCommand('NombreComando', ClaseComando())`.

Inyección en `InitGui.py` mediante `appendToolbar` y `appendMenu`.

---

## 4. Separación Datos vs Visual

- `cad/objects/*`: clases Proxy de `Part::FeaturePython`. Geometría B-Rep, propiedades paramétricas, `execute()`. Agnósticos a GUI.
- `cad/views/*`: clases ViewProvider. Sombreado, iconos del árbol, modos de display Coin3D. Exclusivos de GUI.

---

## 5. Prerrequisitos antes de ejecutar cualquier ola de refactor

1. Rama git creada: `git checkout -b refactor/arquitectura-v2`.
2. Baseline de pruebas en verde: `pytest tests/` (81 tests).
3. Diagnóstico de documentación resuelto: este archivo coherente con `01_` a `05_`.
4. Diagnóstico de archivos `.py` completado: matriz de renombrados y dependencias.
5. Script de re-enrutamiento de imports listo (`tools/refactor_imports.py`).

---

## 6. Matriz de diagnóstico de archivos `.py` actuales (estructura, no lógica)

| Archivo actual | Capa destino | Nombre propuesto | Observación |
|---|---|---|---|
| `vdo_layout.py` | math | `vdo_math_layout.py` | Motor matricial BSP |
| `vdo_reengrose.py` | math | `vdo_math_reengrose.py` | Geometría de tiras |
| `vdo_facade_contract.py` | math | `vdo_math_facade.py` | Frentes y solapes |
| `vdo_cajon_despiece.py` | math | `vdo_math_cajon.py` | Despiece cajones |
| `vdo_puerta_despiece.py` | math | `vdo_math_puerta.py` | Despiece puertas |
| `vdo_frames.py` | math | `vdo_math_frames.py` | Marco local |
| `vdo_defaults.py` | hub | `vdo_hub_defaults.py` | Acceso tipado al manifest |
| `vdo_manifest.py` | hub | `vdo_hub_manifest.py` | Configuración de taller |
| `vdo_hardware_hub.py` | hub | `vdo_hub_hardware.py` | API herrajes SKU |
| `vdo_module_props.py` | hub | `vdo_hub_module_props.py` | Propiedades de módulo |
| `vdo_module_specs.py` | hub | `vdo_hub_module_specs.py` | Especificaciones |
| `vdo_module_boilerplate.py` | hub | `vdo_hub_module_boilerplate.py` | Boilerplate |
| `vdo_sync_config.py` | hub | `vdo_hub_sync_config.py` | Sincronización config |
| `vdo_coco_core.py` | cad/objects | `vdo_cad_coco.py` | Chasis estructural |
| `vdo_panel_core.py` | cad/objects | `vdo_cad_panel.py` | Panel melamínico |
| `vdo_cajon_core.py` | cad/objects | `vdo_cad_cajon.py` | Sub-ensamblaje cajón |
| `vdo_puerta_core.py` | cad/objects | `vdo_cad_puerta.py` | Mecanizado puerta |
| `vdo_zocalo_core.py` | cad/objects | `vdo_cad_zocalo.py` | Perímetro base |
| `vdo_reengrose_solids.py` | cad/objects | `vdo_cad_reengrose_solids.py` | Sólidos refuerzo |
| `vdo_coco_spaces.py` | cad/objects | `vdo_cad_space.py` | Contenedor espacio |
| `vdo_tambor_core.py` | cad/objects | `vdo_cad_tambor.py` | Tambor (si aplica) |
| `vdo_placement.py` | cad/objects | `vdo_cad_placement.py` | Snapping/colocación |
| `vdo_desvincular_pieza.py` | cad/objects | `vdo_cad_unlink.py` | Friendly unlink |
| `vdo_view_base.py` | cad/views | `vdo_cad_view_base.py` | ViewProvider base |
| `vdo_panel_task.py` | ui | `vdo_ui_panel_task.py` | TaskPanel panel L1 |
| `vdo_coco_unified_task.py` | ui | `vdo_ui_coco_task.py` | TaskPanel maestro COCO |
| `vdo_coco_divisions_task.py` | ui | `vdo_ui_divisions_task.py` | TaskPanel divisiones |
| `vdo_zocalo_task.py` | ui | `vdo_ui_zocalo_task.py` | TaskPanel zócalo |
| `vdo_puerta_task.py` | ui | `vdo_ui_puerta_task.py` | TaskPanel puerta |
| `vdo_cajon_task.py` | ui | `vdo_ui_cajon_task.py` | TaskPanel cajón |
| `vdo_tambor_task.py` | ui | `vdo_ui_tambor_task.py` | TaskPanel tambor |
| `vdo_chassis_widget.py` | ui | `vdo_ui_chassis_widget.py` | Widget 2D chasis |
| `vdo_box_controller.py` | ui | `vdo_ui_box_widget.py` | Widget 3x3 regruesos |
| `vdo_coco_preview2d.py` | ui | `vdo_ui_preview2d_widget.py` | Visor 2D vanos |
| `vdo_reengrose_ui.py` | ui | `vdo_ui_reengrose.py` | UI refuerzo |
| `vdo_drag_handles.py` | ui | `vdo_ui_drag_handles.py` | Handles interacción |
| `vdo_qt.py` | ui | `vdo_ui_qt_compat.py` | Compat PySide |
| `vdo_task_base.py` | ui | `vdo_ui_task_base.py` | Mixin transaccional |
| `vdo_export_cutting_list.py` | cam | `vdo_cam_cutlist.py` | CSV OpenCutList |
| `vdo_optimizer_core.py` | cam | `vdo_cam_optimizer_engine.py` | MaxRects nesting |
| `vdo_optimizer_view.py` | cam | `vdo_cam_optimizer_view.py` | Visor plano corte |
| `vdo_cutting_list_preview.py` | cam | `vdo_cam_cutlist_preview.py` | Vista previa lista |
| `vdo_nesting_workflow.py` | cam | `vdo_cam_nesting_workflow.py` | Flujo nesting |
| `vdo_nesting_presets.py` | cam | `vdo_cam_nesting_presets.py` | Presets nesting |
| `vdo_universal_inspector.py` | archivo | — | Muerto, mover a archivo/ |
| `vdo_inspector_dock.py` | archivo | — | Muerto, mover a archivo/ |
| `vdo_selection_bridge.py` | archivo | — | Muerto, mover a archivo/ |
| `vdo_inspector_arbol.py` | archivo | — | Muerto, mover a archivo/ |
| `vdo_spaces.py` | archivo | — | Candidato a archivo/ |
| `vdo_coco_spaces_task.py` | archivo | — | Muerto, mover a archivo/ |
| `vdo_coco_task.py` | archivo | — | Muerto, mover a archivo/ |
| `Init.py` | raíz | `Init.py` | Proteger, no renombrar |
| `InitGui.py` | raíz | `InitGui.py` | Proteger, no renombrar |
| `vdo_loader.py` | raíz | `vdo_loader.py` | Infraestructura |
| `vdo_install.py` | raíz | `vdo_install.py` | Instalación |
| `vdo_sync.py` | raíz | `vdo_sync.py` | Herramienta dev |
| `vdo_publish.py` | raíz | `vdo_publish.py` | Publicación |
| `vdo_detect_config.py` | raíz | `vdo_detect_config.py` | Detección config |
| `vdo_guardian.py` | raíz | `vdo_guardian.py` | Guardia |
| `vdo_paths.py` | raíz | `vdo_paths.py` | Rutas |
| `vdo_creation_flow.py` | raíz | `vdo_creation_flow.py` | Flujo creación |
| `vdo_clone.py` | raíz | `vdo_clone.py` | Clonado |
| `vdo_finish.py` | raíz | `vdo_finish.py` | Finalizado |
| `vdo_toolbar_test.py` | raíz | `vdo_toolbar_test.py` | Test toolbar |
| `vdo_toolbar_inject.py` | raíz | `vdo_toolbar_inject.py` | Inyección toolbar |

**Total: ~79 archivos. Reducción esperada Ola 1: ~45 archivos activos.**

---

## 7. Reglas básicas del ecosistema FreeCAD

- Un workbench se instala en `Mod/` y es reconocido vía `package.xml` + `metadata.txt`.
- `Init.py` carga sin GUI; `InitGui.py` registra la interfaz gráfica.
- Los ViewProviders requieren `pivy.coin` y solo existen en sesiones con GUI.
- Los tests de regresión se ejecutan headless (`pytest`) y deben quedar en verde al final de cada ola.
- Nunca mezclar proxies de datos (`cad/objects/`) con ViewProviders (`cad/views/`) en el mismo módulo.
