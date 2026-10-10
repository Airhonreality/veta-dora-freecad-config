# 🧾 Deuda Técnica VDO

> Registro de deuda técnica conocida y **no resuelta** (para no cargar el motor
> con trabajo a medias). Cada ítem indica impacto y resolución propuesta.
> Última actualización: **2026-10-10** (Task 6 — Refactor axiomático).

---

## DT-1 — Posición de los divisores verticales

- **Archivo:** `vdo_coco_spaces.py` → `_crear_division_vertical()`
- **Síntoma:** el divisor se coloca en `x_pos = esp["inicio"]` (inicio del **vano
  libre**) en lugar de en el **hueco de `espesor`** entre vanos. Con N vanos se
  emiten N cajas (una por vano) en vez de los divisores reales en los huecos → aparece
  un divisor espurio en `x=0` y otros descolocados.
- **Impacto:** **solo visual (3D)**. Las **cotas de despiece no se ven afectadas**
  (se calculan por caras/espesor, no por posición).
- **Propuesta:** emitir un divisor por **hueco** (entre vanos consecutivos), centrado en
  el `espesor`, en lugar de uno por vano.

## DT-2 — Recursión de sub-espacios anidados sin validar

- **Archivo:** `vdo_coco_spaces.py` → `_generar_shapes_recursivo()`
- **Síntoma:** el tracking de región (`ancho_repisa`, `altura_divisor`) se corrigió, pero
  los casos **anidados** (sub-división dentro de un vano) no están validados
  end-to-end en FreeCAD; la propagación de `z_base`/ejes al alternar X↔Y debe probarse.
- **Impacto:** geometría de divisiones anidadas.
- **Propuesta:** test de caso anidado (vano dividido en repisas, y repisa dividida en
  verticales) en FreeCAD GUI.

## DT-3 — Wrapper de división no registrado en la UI

- **Archivos:** `InitGui.py`, `vdo_install.py`, `vdo_toolbar_inject.py`
- **Síntoma:** `vdo_panel_division.FCMacro` existe pero **no** está en la toolbar/menú
  ni en el instalador. Hoy solo se ejecuta a mano desde `Macro → Ejecutar`.
- **Impacto:** descubribilidad / usabilidad.
- **Propuesta:** añadir el comando `Panel División` a los tres puntos de registro
  (mismo patrón que `Panel Estándar` / `Panel Fachada`), con icono y (opcional) atajo.

## DT-4 — El panel es `Part::Box` plano: `VDO_Orientacion` no re-mapea en vivo

- **Archivo:** `vdo_panel_core.py`
- **Síntoma:** el panel es un `Part::Box` primitivo (sin `Proxy`/`execute()`). El mapeo de
  ejes según `orientacion` se aplica **solo al crear** (`crear_pieza`). Cambiar el enum
  `VDO_Orientacion` desde el panel de propiedades **no** re-ajusta las expresiones.
- **Nota:** rotar físicamente la pieza con `Placement.Rotation` **sí** es libre y **no**
  rompe el despiece (las cotas salen de ejes + `VDO_Orientacion`, no de la pose).
- **Impacto:** cambiar la orientación semántica requiere re-ejecutar la macro.
- **Propuesta:** convertir el panel a `Part::FeaturePython` con `Proxy` (patrón
  `CocoFeature`) y `execute()` que re-mapee las expresiones cuando cambie el enum.

## DT-5 — Diccionario semántico vacío + taxonomía de materiales pendiente

- **Archivos:** `vdo_diccionario_semantico.md`, `vdo_manifest.json`
- **Síntoma:** el diccionario es un esqueleto; la semántica (p.ej. `fachada` = RIG×4 +
  material `fachadas`) **no** está acoplada a propósito. El material `fachadas` aún no
  existe en `vdo_manifest.json → materiales`.
- **Impacto:** ninguno en el motor (por diseño, Axioma 5). Pendiente para cuando se
  defina la semántica.
- **Propuesta:** llenar el diccionario y promoverlo a datos puros
  (`vdo_manifest.json → semantica`).

---

## ✅ Resuelto en Task 6 (para referencia)

- Se eliminó el acoplamiento `tipo == "fachada"` → reglas físicas del motor.
- Se corrigió el ancho de repisa horizontal (`altura_disponible` → `ancho_util`).
- Se corrigieron las cotas **naive** del despiece del COCO (p.ej. lateral `espesor=720`
  → `espesor=18`).
- Las divisiones del COCO ahora **entran al despiece** (`VDO_Paneles_JSON`).

---

*Deuda técnica VDO — generado 2026-10-10.*
