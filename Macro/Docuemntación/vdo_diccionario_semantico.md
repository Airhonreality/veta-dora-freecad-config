# 📖 Diccionario Semántico VDO — Piezas de Mobiliario

> **Estado:** ESQUELETO (v0.1.0) — tabla vacía, lista para llenar.
> **Propósito:** definir, para cada pieza de mobiliario, **qué es** (semántica) y
> **qué propiedades físicas le son inamovibles**. Es la única fuente de verdad que
> mapea *semántica → física*.

---

## 🎯 Por qué existe este diccionario

El motor geométrico (`vdo_panel_core.py`) es **agnóstico** (Axioma 5 — Separación
Semántica/Física): modela piezas físicas (tablero) con atributos físicos libres:

- `orientacion` (horizontal / vertical)
- `cantos` por lado (RIG / FX / SMRG)
- `material_ref`
- `espesor` y dimensiones

La **semántica** de mobiliario ("fachada", "base", "división", "lateral"...) **no vive
en el motor**. Vive aquí, en este diccionario, como **datos puros**.

> Cuando este diccionario esté definido y maduro, se promoverá a `vdo_manifest.json`
> (sección `semantica`) para que el motor lo lea como datos, **sin acoplar reglas en código**.

## 📋 Reglas de llenado

1. Una fila por **pieza semántica** (no por objeto FreeCAD).
2. En **"Propiedades físicas inmutables"** se anota SOLO lo que *no puede variar* para
   que la pieza siga siendo "esa pieza". Ej.: `fachada` → canto RIG ×4 + material `fachadas`.
3. Lo que quede libre (orientación, cantos, material) se deja en "libre".
4. **No** acoplar nada al motor hasta que una fila esté cerrada y validada.

## 🗂️ Tabla de piezas (a llenar)

| Pieza (semántica) | Origen hoy | Canto inmutable | Material inamovible | Orientación | Estado |
|---|---|---|---|---|---|
| Panel Estándar | `vdo_panel_estandar.FCMacro` | libre | libre | libre | existente |
| Panel Fachada | `vdo_panel_fachada.FCMacro` | **RIG ×4** (a validar) | **`fachadas`** (a validar) | libre | existente |
| Panel División | `vdo_panel_division.FCMacro` | libre | libre | **vertical** (por naturaleza) | existente (nuevo) |
| Lateral (COCO) | `vdo_coco_core.py` | libre | libre | vertical | existente |
| Base (COCO) | `vdo_coco_core.py` | libre | libre | horizontal | existente |
| Techo (COCO) | `vdo_coco_core.py` | libre | libre | horizontal | existente |
| Fondo / Respaldo (COCO) | `vdo_coco_core.py` | libre | libre | horizontal | existente |
| División interna (COCO) | `vdo_coco_spaces.py` | libre | libre | vertical / horizontal | existente |
| Cajón — Lateral Izq/Der | `vdo_cajon_despiece.py` | libre | libre | vertical | existente |
| Cajón — Contrafrente | `vdo_cajon_despiece.py` | libre | libre | vertical | existente |
| Cajón — Frente interior | `vdo_cajon_despiece.py` | libre | libre | vertical | existente |
| Cajón — Piso | `vdo_cajon_despiece.py` | libre | libre | horizontal | existente |
| Cajón — Fachada | `vdo_cajon_despiece.py` | **RIG ×4** (a validar) | **`fachadas`** (a validar) | vertical | existente |
| _(nueva pieza)_ | — | — | — | — | a definir |

## 🧭 Notas / decisiones pendientes

- La única semilla semántica conocida hoy es **fachada** = canto rígido ×4 + material
  `fachadas`. Está anotada pero **aún NO acoplada en el motor** (correcto según Axioma 5).
- La "división" y el "lateral" comparten física (panel vertical); su diferencia es
  únicamente semántica/posición, no de reglas del motor.
- Cuando exista una taxonomía de materiales ("fachadas", "cajas", "estructura"...) se
  referenciará aquí desde `vdo_manifest.json → materiales`.

---

*Diccionario semántico VDO — generado 2026-10-10 (Task 6, Refactor axiomático).*
