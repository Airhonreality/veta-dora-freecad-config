# Plan de Acciones: Resolución de Incompatibilidad Reactiva en VDO
**ARCHIVO HISTÓRICO** — Referencia operativa, no ley de diseño. Origen: `documentacion/Progreso/Plan_de_Acciones_VDO.md`

## 1. Diagnóstico Ejecutivo

### Problema Central
La UI del Sistema VDO entra en estado inerte y desincronizado porque:
- Visor 2D no responde a cambios en selectores (señales Qt no conectadas)
- Cajones/Puertas nunca se instancian (botón Aceptar eliminado sin reemplazo)
- Rendimiento 3D sin mecanismo debounce ni transacciones

### Incompatibilidad de Paradigmas
- TaskPanel Clásico (obsoleto): Botón Aceptar → openTransaction → sincronizar_insertos_vdo → recompute → commitTransaction
- Inspector Dock Reactivo (actual): Cambio en UI → ¿? → nada → escena 3D congelada

## 2. Plan de Acciones en Fases

### FASE 1: Diagnóstico Verificado (1-2 horas)
Tarea 1.1: Auditoría de señales en UI (confirmado: no conectadas reactivamente)
Tarea 1.2: Búsqueda de función huérfana (confirmado: sincronizar_insertos_vdo no existe)
Tarea 1.3: Inspección del temporizador debounce (confirmado: sin QTimer debounce)

### FASE 2: Conectar Visor 2D (2-3 horas)
Tarea 2.1: Validar clase CocoPreview2D (set_layout() funcional)
Tarea 2.2: Conectar señales en panel dock (actualizar_vista_2d)
Tarea 2.3: Prueba manual (pendiente: requiere sesión FreeCAD GUI)

### FASE 3: Implementar Temporizador Debounce (2-3 horas)
Tarea 3.1: Crear controlador debounce (QTimer, 250 ms)
Tarea 3.2: Conectar actualizar_vista_2d() en lugar de botón
Tarea 3.3: Prueba debounce (pendiente: requiere sesión FreeCAD GUI)

### FASE 4: Recuperar Función de Sincronización Topológica (1-2 horas)
Tarea 4.1: Verificar función existente
Tarea 4.2: Implementar si falta (crea/borra Cajon_X en Hijos)
Tarea 4.3: Verificación (pendiente: requiere sesión FreeCAD GUI)

### FASE 5: Validación de Integridad DAG (1 hora)
Tarea 5.1: Auditar execute() (sin addObject/removeObject → DAG limpio)
Tarea 5.2: Prueba de consistencia (checkDependencies, pendiente GUI)

### FASE 6: Pruebas Integradas (1-2 horas)
Test 6.1-6.4: Flujos integrados (diseñados, verificación manual pendiente)

## 3. Matriz de Dependencias y Ruta Crítica
FASE 1 → FASE 2 → FASE 3 → FASE 4 → FASE 6 (FASE 5 paralelizable durante 6)
Duración total: ~14 horas

## 4. Checklist de Implementación (estado al cierre de este archivo histórico)
- FASE 1: ✅ Completado
- FASE 2: ✅ Completado (verificación manual pendiente)
- FASE 3: ✅ Completado (verificación manual pendiente)
- FASE 4: ✅ Completado (verificación manual pendiente)
- FASE 5: ✅ Completado (verificación manual pendiente)
- FASE 6: ⏳ Pendiente (tests diseñados, verificación en GUI pendiente)

## 5. Criterios de Éxito
| Criterio | Indicador | Estado |
|----------|-----------|--------|
| Visor 2D Reactivo | Actualiza en <100ms al cambiar parámetros | ☐ (pendiente GUI) |
| Transacciones Atómicas | Undo muestra 1 bloque por ráfaga, no N | ☐ (pendiente GUI) |
| Cajones Instanciados | Árbol contiene "Cajon_X" | ☐ (pendiente GUI) |
| DAG Íntegro | checkDependencies() sin ciclos | ☐ (pendiente GUI) |
| Rendimiento UI | Cambios rápidos no congelan FreeCAD | ☐ (pendiente GUI) |
| Undo/Redo Funcional | Ctrl+Z y Ctrl+Y restauran estado correcto | ☐ (pendiente GUI) |
| Sin Errores | Console limpia, sin PrintError() | ☐ (pendiente GUI) |

## 6. Próxima Acción
Implementado (FASE 1-5): señales reactivas, temporizador debounce, transacción atómica, sincronizar_insertos_vdo, suite de tests unitarios PASS.
Pendiente (verificación manual en sesión FreeCAD GUI): cambiar Nº Cajones de 2 a 3, verificar visor 2D, undo/redo, creación de cajones en árbol.

*Este archivo es referencia histórica; la ley de diseño vigente está en `documentacion_v2/`.*
