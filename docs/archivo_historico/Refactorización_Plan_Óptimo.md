# Refactorización: Plan Óptimo de Transacciones
**ARCHIVO HISTÓRICO** — Referencia operativa, no ley de diseño. Origen: `documentacion/Progreso/Refactorización_Plan_Óptimo.md`

**Fecha:** 2026-10-29  
**Estado:** ✅ IMPLEMENTADO  
**Validación:** Sintaxis OK

## Cambio de Paradigma

**Antes (Plan Anterior):**
```
Usuario cambia parámetro
  ↓ [0ms]
UI actualiza
  ↓ [Espera 250ms]
Timer expira → openTransaction() → recompute() → commitTransaction()
```
❌ 250ms de latencia en 3D  
❌ Inconsistencia temporal (UI adelante del documento)  
❌ Viola especificación de FreeCAD  

**Después (Plan Óptimo - Implementado Ahora):**
```
Usuario entra al control
  ↓ [focusIn]
openTransaction()
  ↓
Usuario cambia parámetro
  ↓ [0ms]
UI actualiza
  ↓ [recompute cada 100ms, dentro de transacción]
Timer expira → recompute()
  ↓
Usuario suelta el control
  ↓ [focusOut / editingFinished]
commitTransaction()
```
✅ 0ms de latencia perceptible (100ms es imperceptible)  
✅ Consistencia total (todo dentro de transacción)  
✅ Conforme a especificación de FreeCAD  
✅ Mejor manejo de errores  

## Cambios Implementados

### 1. Control Central de Transacciones
**Archivo:** `vdo_universal_inspector.py`, Clase: `VDOUniversalInspectorWidget`
- `self._transaction_abierta = False` (flag global de transacción)
- Timer cambió de 250ms a 100ms: `self.timer_recompute.setInterval(100)`

### 2. Conexiones de Controles del Vano (focusIn/focusOut)
**Archivo:** `vdo_universal_inspector.py`, Método: `_conectar_controles_vano_reactivos()`
- `valueChanged` / `currentIndexChanged` → cambios en UI
- `focusInEvent` → abre transacción
- `focusOutEvent` → cierra transacción

### 3. Handlers de Transacción
- `_crear_handler_focus_in()` - Abre transacción al entrar
- `_crear_handler_focus_out()` - Cierra transacción al salir

### 4. Micro-Header (W, H, D, E)
**Archivo:** `vdo_universal_inspector.py`, Clase: `_MicroHeaderWidget`
- Conecta `focusInEvent` / `focusOutEvent` de spinboxes
- Accede al padre (`VDOUniversalInspectorWidget`) para abrir/cerrar transacción

### 5. Timer Recompute (100ms)
**Método:** `_on_timer_recompute_expired()`
```python
def _on_timer_recompute_expired(self):
    """Ejecutado cada 100ms mientras hay cambios en UI."""
    if not self._transaction_abierta:
        return
    doc.recompute()  # ← Sin abrir/cerrar transacción
```

### 6. Actualización de Páginas Internas
- `PaginaChasis._on_chassis_changed()` - Usa `timer_recompute` del padre
- `PaginaPieza._on_box_changed()` - Usa `timer_recompute` del padre

## Comparación: Antes vs Después

| Métrica | Antes | Después |
|---------|-------|---------|
| Timer | 250ms | 100ms ✓ |
| Transacción abierta | En debounce (tardío) | En focusIn ✓ |
| Transacción cerrada | En debounce | En focusOut ✓ |
| Latencia perceptible | 250ms ⚠️ | ~100ms ✓ |
| Recomputes/evento | 1 (diferido) | Controlado c/100ms ✓ |
| Consistencia | Temporal (gap 250ms) | Total ✓ |
| Conforme a doc | NO ❌ | SÍ ✓ |
| Sintaxis | OK | OK ✓ |

## Beneficios Técnicos
1. **Coherencia Temporal:** Transacción abierta ANTES de cualquier cambio. Sin brechas donde los datos estén inconsistentes.
2. **Responsividad Percibida:** 100ms es imperceptible para el usuario.
3. **Mejor Manejo de Errores:** Si hay excepción durante la transacción, abortTransaction() revierte TODO.
4. **Conforme a Estándares FreeCAD:** Sigue el patrón de BIM, Draft, PartDesign.
5. **Mejor Control de Carga:** Debounce cada 100ms previene saturación del bucle de eventos.

## Lecciones Aprendidas
1. **Paradigma de Transacciones en FreeCAD:** Abrir transacción al inicio de la interacción, mantener abierta durante toda la edición, cerrar al final del gesto (focusOut, editingFinished). Usar debounce para CONTROLAR FRECUENCIA, no para DIFERIR.
2. **Debounce vs Transacción:** Debounce ≠ Diferimiento (250ms espera). Debounce = Control de frecuencia (máx. cada 100ms). Son complementarios, no excluyentes.
3. **Comunicación entre Páginas:** Las páginas internas usan `parent()` para acceder a recursos del padre. Búsqueda de parent por atributo es segura (hasattr check).
4. **Optimización de UI:** 100ms de latencia es imperceptible (límite humano ~150ms). Control de frecuencia > diferimiento en latencia.

## Estado de Implementación
| Componente | Estado |
|-----------|--------|
| Timer reducido a 100ms | ✅ DONE |
| focusIn/focusOut para vano | ✅ DONE |
| focusIn/focusOut para micro-header | ✅ DONE |
| _on_timer_recompute_expired() | ✅ DONE |
| Actualización páginas internas | ✅ DONE |
| Sintaxis validada | ✅ DONE |
| Próximo: FASE 6 pruebas | ⏳ PENDIENTE |

*Este archivo es referencia histórica; la ley de diseño vigente está en `documentacion_v2/`.*
