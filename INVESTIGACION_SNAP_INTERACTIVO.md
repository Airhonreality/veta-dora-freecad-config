# Investigación: Resize Interactivo en FreeCAD (COCO)

**Objetivo inicial:** Permitir redimensionar COCOs arrastrando vértices o haciendo snap entre dos puntos.

---

## Intentos Fallidos

### Intento 1: Visualización de Handles 3D
**Archivo:** `vdo_drag_handles.py` (v1)

**Idea:** Crear 3 esferas azules en las esquinas del COCO que actuaran como "handles" interactivos.

**Problemas:**
- ❌ Las esferas no aparecían en viewport
- ❌ Usaba `self.vobj.addDisplayMode()` (método no existe)
- ❌ Luego corregido a `self.vobj.RootNode.addChild()` pero aún no se visualizaban

**Conclusión:** Abandonado por problemas de visualización Coin3D.

---

### Intento 2: Drag Continuo con Mouse Events
**Archivo:** `vdo_drag_handles.py` (v2)

**Idea:** Sistema 2-click con línea visual guía:
1. Clic 1: selecciona vértice inicial
2. Mouse move: dibuja línea visual
3. Clic 2: calcula distancia y redimensiona

**Problemas:**
- ❌ `SelectionObserver.onSelectionChange()` no se disparaba con clics en vértices
- ❌ No funciona ni con `Gui.Selection.addSelection()` desde código ni con UI clicks
- ❌ Arquitectura fundamental de SelectionObserver no es adecuada para esto

**Investigación encontrada:** GitHub Issue #6204 (abierto desde 2012) confirma que FreeCAD NO tiene API clara para eventos interactivos en 3D desde Python.

**Conclusión:** Imposible sin C++ compilado o PySide2.

---

### Intento 3: Task Panel + SelectionObserver
**Archivo:** `vdo_interactive_task.py`

**Idea:** Crear Task Panel que capturara eventos de selección y los pasara al ViewProvider.

**Problemas:**
- ❌ Requería PySide2 (no disponible en este FreeCAD)
- ❌ Error: `ModuleNotFoundError: No module named 'PySide2'`

**Conclusión:** Abandonado por dependencia no disponible.

---

### Intento 4: Polling con Timer Qt
**Archivo:** `vdo_resize_2click.FCMacro` (v1)

**Idea:** Macro que chequea cada 100ms si cambió la selección en viewport.

**Problemas:**
- ❌ Requería PySide2 para `QtCore.QTimer`
- ❌ Mismo error: `ModuleNotFoundError: No module named 'PySide2'`

**Conclusión:** Eliminado por dependencia no disponible.

---

### Intento 5: Polling con time.sleep()
**Archivo:** `vdo_resize_2click.FCMacro` (v2)

**Idea:** Reescrito sin Qt, usando `time.sleep(0.1)` en un loop para polling.

**Problemas:**
- ❌ `time.sleep()` en loop BLOQUEA el thread principal de FreeCAD
- ❌ UI se congela mientras espera
- ❌ No se detectaban los eventos de selección

**Conclusión:** Abandonado porque bloquea FreeCAD completamente.

---

### Intento 6: Polling No-Bloqueante (15s timeout)
**Archivo:** `vdo_snap_measure.FCMacro` (v3)

**Idea:** Polling con `time.sleep(0.05)` y timeout de 15 segundos para cada punto.

**Problemas:**
- ❌ Seguía bloqueando FreeCAD aunque fuera con delays más cortos
- ❌ No detectaba los vértices seleccionados
- ❌ Error colateral de IFC: `TypeError: bad argument type for built-in operation`

**Conclusión:** Abandonado porque el polling siempre bloquea, sin importar el delay.

---

## Causa Raíz Identificada

**FreeCAD tiene un problema arquitectónico:**

1. **No hay SelectionObserver real en Python** que se dispare con clics
   - `onSelectionChange()` no se comporta como se documenta
   - No se dispara con `Gui.Selection.addSelection()` desde código
   - No se dispara confiablemente con clics en UI

2. **No hay API para UI interactiva en 3D sin blocar**
   - Polling siempre bloquea el thread principal
   - Callbacks/Timers requieren Qt (no disponible)
   - Coin3D events requieren C++ compilado

3. **Esto ha sido un issue conocido desde 2012**
   - GitHub Issue #6204: "Interactive controls in 3D view"
   - Aún sin resolver en 2026
   - Indica problema fundamental, no un bug menor

---

## ¿Qué Sí Funciona?

✅ **Llamadas directas a `handle_vertex_click()` desde código**
```python
vp = coco.ViewObject.Proxy
vp.handle_vertex_click("Vertex0")  # Funciona
vp.handle_vertex_click("Vertex7")  # Funciona
```

Esto demuestra que la **lógica de resize está correcta**. Solo falta la **interfaz de captura de eventos**.

---

## Alternativas Viables

1. **Seleccionar 2 vértices en UI → Ejecutar macro**
   - Usuario: Shift+clic en vértice 1, Shift+clic en vértice 2
   - Macro: detecta los 2 últimos vértices seleccionados
   - Calcula distancia
   - Aplica parámetro
   - ✅ No requiere eventos real-time
   - ✅ No bloquea FreeCAD
   - ✅ Funciona con API estándar

2. **Input en consola Python**
   - Macro pide: "¿Nuevo alto? "
   - Usuario digita valor
   - Se aplica
   - Simple pero menos visual

3. **Draft Dimension (futuro)**
   - Usuario dibuja cota temporal
   - Macro lee longitud de cota
   - Aplica a COCO
   - Requiere que usuario conozca Draft dimension

---

## Conclusión

**El resize interactivo "drag en 3D" es imposible en FreeCAD con Python puro.**

La alternativa pragmática es: **Seleccionar 2 vértices en UI + ejecutar macro.**

Implementar esto próximo: `vdo_snap_measure_simple.FCMacro`
