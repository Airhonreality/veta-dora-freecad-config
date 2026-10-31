# 📋 Documento de Progreso VDO - Motor Multiestado
**ARCHIVO HISTÓRICO** — Referencia operativa, no ley de diseño. Origen: `documentacion/Progreso/PROGRESO_VDO.md`

## 🎯 Objetivo del Proyecto
Consolidar un motor unificado de paneles/fachadas y cofres para FreeCAD, eliminando configuración manual en la interfaz. Arquitectura **Code-as-UI** con patrón de envoltorio delgado (Thin Wrapper/Facade).

## 📁 Estructura Actual del Proyecto
```
Macro/
├── vdo_manifest.py              ← Contrato de datos (v1.4.0)
├── vdo_guardian.py              ← Guardián de dependencias
├── vdo_panel_core.py            ← Motor central de paneles
├── vdo_coco_core.py             ← Motor central de cofres
├── vdo_panel_estandar.FCMacro   ← Envoltorio: Panel Estándar
├── vdo_panel_fachada.FCMacro    ← Envoltorio: Panel Fachada
├── vdo_coco_4c.FCMacro          ← Envoltorio: COCO 4C
├── VDO_Crear_Hoja_Melamina.FCMacro ← Legacy (compatibilidad)
├── PROGRESO_VDO.md              ← Este documento
└── icons/
    ├── vdo_panel.svg, vdo_panel_v2.svg, vdo_coco.svg, vdo_coco_v2.svg, vdo_workbench.svg, vdo_workbench_v2.svg
```

## ✅ Funcionalidades Implementadas (resumen por versión)

### v1.2.0 — Arquitectura Base
| Componente | Estado | Descripción |
|------------|--------|-------------|
| `vdo_panel_core.py` | ✅ COMPLETADO | Motor central de paneles con parámetro `tipo` |
| `vdo_coco_core.py` | ✅ COMPLETADO | Motor central de cofres |
| Envoltorios (.FCMacro) | ✅ COMPLETADOS | 3 envoltorios ultraligeros |
| `vdo_manifest.py` | ✅ ACTUALIZADO | Contrato de datos unificado |

### v1.3.0 — Lógica del Fondo
| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `habilitado` | True | Interruptor de existencia |
| `calibre` | 6mm | Espesor del fondo |
| `profundidad_ranura` | 3mm | Para fondos delgados |
| `distancia_borde` | 18mm | Retranqueo del borde trasero |

### v1.4.0 — Configuración Estructural
| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `tapa` | "externo" | Tapa por encima de laterales |
| `base` | "interno" | Base entre laterales |

### v1.5.0 — Task Panel PySide + FeaturePython + ViewProvider
- FeaturePython, ViewProvider, Task Panel PySide en `vdo_coco_core.py` / `vdo_coco_task.py`
- Transacciones Undo/Redo, Icono dinámico

### v1.6.0 — Marco local, fondo en Y+, exposición y cantos
- Marco local único: X+ derecha, Y+ fondo, Z+ arriba, frente Y−
- Fondo delgado en Y+ con ranuras reales
- VDO_Lados_Vistos / VDO_Lados_Apoyados, política vdo_finish

### v1.7.0 — Fase 1: motor de reengroses/pachas y panel L1
- `vdo_reengrose.py` puro, propiedades VDO_Reengrose_*, compound base+tira/pacha

### v1.8.0 — Fases 2 y 3: COCO, vanos, repisas y UI contextual
- `vdo_layout.py`, `vdo_coco_divisions_task.py`, `vdo_coco_preview2d.py`
- `VDO_Reengrose_JSON`, UI contextual, despiece con subpiezas

## 📐 Sesión 22/10/2026 — Divisiones COCO v2
Implementado: `vdo_layout.py` (matriz de vanos v2), `vdo_coco_preview2d.py` (preview frontal), `vdo_coco_divisions_task.py` (pestaña Divisiones), `vdo_coco_core.py` (VDO_Divisiones + cavidad interior), `vdo_coco_spaces.py` (generar_divisiones_matriz), `vdo_coco_unified_task.py` (pestaña única Divisiones).
Validación: py_compile OK, tests headless 1×1, 3 columnas, 3×2, anidación X→Y→X, overflow, common().Volume == 0.

## 🧩 Sesión 26/10/2026 — Marco local, fondo en Y+ y exposición/cantos
Marco local único implementado. Fondo delgado en Y+ con ranuras. Preview con FRENTE (Y−). VDO_Lados_Vistos/Apoyados. Política vdo_finish. Despiece con Edge N/S/E/W.

## 🧩 Fase 1 — Motor de Reengroses/Pachas + Panel L1 (26/10/2026)
`vdo_reengrose.py` puro: DTO, geometría local, política de cantos, colisión, vano neto, mocheo. Panel L1 con propiedades VDO_Reengrose_*, compound base+tira/pacha, UI de Reengrose/Pacha, despiece con subpiezas. Tests: 9 puros OK, 6 FreeCAD OK.

## 🧩 Fases 2 y 3 — Reengroses en COCO, layout y UI contextual (26/10/2026)
`VDO_Reengrose_JSON` en COCO, `resolve_layout` con luz clara y geometría nominal, colisión repisa/reengrose con retroceso/mocheo, subpiezas de pacha en despiece, inspector contextual. Tests: 15 puros + 14 FreeCAD OK.

## 📋 Tareas Pendientes (históricas)
- Probar visualmente en FreeCAD GUI
- Fase 1: transacción al abrir + debounce de recompute para edición en vivo
- Revisar migración de subdivisiones legacy anidadas
- Generador de despiece (lista de cortes)
- Integración con ERP/reportes
- Más variantes de cofres

## 📊 Historial de Versiones
| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.1.0 | - | Estructura inicial |
| 1.2.0 | - | Motor unificado paneles + envoltorios |
| 1.3.0 | - | Lógica del fondo |
| 1.4.0 | - | Parámetros tapa/base externo/interno |
| 1.5.0 | 20/09/2026 | Task Panel PySide + FeaturePython + ViewProvider |
| 1.6.0 | 26/10/2026 | Marco local, fondo en Y+, exposición y cantos |
| 1.7.0 | 26/10/2026 | Fase 1: motor de reengroses/pachas |
| 1.8.0 | 26/10/2026 | Fases 2 y 3: COCO, vanos, repisas, UI contextual |

*Documento generado automáticamente - Última actualización: v1.8.0 (26/10/2026). Este archivo es referencia histórica; la ley de diseño vigente está en `documentacion_v2/`.*
