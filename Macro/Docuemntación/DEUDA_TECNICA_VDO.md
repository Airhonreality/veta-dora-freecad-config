# 🧾 Deuda Técnica VDO

> Registro de deuda técnica conocida y **no resuelta** (para no cargar el motor
> con trabajo a medias). Cada ítem indica impacto y resolución propuesta.
> Última actualización: **2026-10-26** (Fases 2 y 3 integradas; D23–D35
> deuda abierta, incluyendo preview y despiece segmentado de carcasa).

---

## ✅ DT-1 — Posición de los divisores verticales — **RESUELTO 2026-10-20**

- **Archivo:** `vdo_coco_spaces.py` → `_generar_shapes_recursivo()`, `_crear_division_vertical_en()`
- **Síntoma:** el divisor se colocaba en `x_pos = esp["inicio"]` (inicio del **vano
  libre**) en lugar de en el **hueco de `espesor`** entre vanos. Con N vanos se
  emitían N cajas (una por vano) en vez de los divisores reales en los huecos → aparecía
  un divisor espurio en `x=0` y otros descolocados.
- **Solución:** 
  - Nuevo `_generar_shapes_recursivo()` itera con índice y crea divisor **solo para i > 0** en `espacios[i-1]["fin"]` (fin del vano anterior = hueco).
  - Nuevas funciones `_crear_division_vertical_en()` y `_crear_division_horizontal_en()` reciben posición absoluta.
  - Los hijos de nodos `IGUALES` (partes iguales) se procesan en **mismo eje** (flatten), no alternan.
  - Solo sub-divisiones explícitas del usuario (FIJO/RESTANTE con children) alternan eje X↔Y.
- **Validación:** Tests standalone confirman posiciones correctas:
  - Módulo 1000mm, fijo 400mm + iguales 2 → divisores en 400 y 700 (3 verticales total).
  - Anidación X→Y (columna con repisas) y Y→X (banda con verticales) funcionan.

## ✅ DT-2 — Recursión de sub-espacios anidados — **RESUELTO 2026-10-20**

- **Archivo:** `vdo_coco_spaces.py` → `_generar_shapes_recursivo()`
- **Síntoma:** la propagación de `z_base`/`ancho_repisa`/`altura_divisor` al alternar X↔Y no estaba validada end-to-end.
- **Solución:** 
  - Lógica de recursión unificada y probada con tests standalone.
  - X→Y: `ancho_repisa = esp["libre"]` (ancho de la columna), `altura_divisor` se mantiene.
  - Y→X: `altura_divisor = esp["libre"]` (alto de la banda), `ancho_repisa` se mantiene.
  - `z_base` se acumula correctamente: `z_base + esp["inicio"]` para Y→X.
- **Validación:** Tests confirman geometría correcta en ambos sentidos de anidación.

---

## ✅ DT-3 — Wrapper de división registrado en la UI — **RESUELTO 2026-10-20**

- **Archivos:** `InitGui.py`, `vdo_install.py`, `vdo_toolbar_inject.py`
- **Síntoma:** `vdo_panel_division.FCMacro` existía pero **no** estaba en la toolbar/menú
  ni en el instalador. Solo se ejecutaba a mano desde `Macro → Ejecutar`.
- **Solución:** 
  - `InitGui.py`: Añadida clase `CmdPanelDivision` + registro `VDO_PanelDivision` + toolbar
  - `vdo_install.py`: Añadida clase `VDO_Cmd_PanelDivision` + registro + workbench cmdList
  - `vdo_toolbar_inject.py`: Ya estaba definido en `VDO_MACROS` (Std_Macro_5) con icono `vdo_panel`, atajo `D,I,V,I`
- **Icono:** Reutiliza `vdo_panel.svg` (existente)
- **Impacto:** Panel División ahora disponible en Workbench VDO y toolbar "CARPINTERIA - VDO"

---

## ✅ DT-6 — Task Panels separados (básico + espacios) — **RESUELTO 2026-10-20**

- **Archivos:** `vdo_coco_4c.FCMacro`, `vdo_coco_core.py`, nuevo `vdo_coco_unified_task.py`
- **Síntoma:** Al crear COCO se abrían **dos Task Panels** separados (medidas + espacios).
  El usuario quería **todo en la pestaña "Datos"** (Property Panel) sin diálogos automáticos.
- **Solución:**
  - Nuevo `vdo_coco_unified_task.py`: **Editor Unificado** con 4 pestañas (Medidas, Estructura, Espacios X, Espacios Y)
  - `ViewProviderCoco.setEdit()` → abre editor unificado al **doble-click en objeto**
  - `vdo_coco_4c.FCMacro`: **NO abre Task Panel automáticamente** al crear
  - Propiedades básicas editables directamente en pestaña "Datos" (PropertyLength, PropertyEnumeration, etc.)
  - Espacios X/Y editables via editor unificado (doble-click) o JSON directo en "Datos"
- **Decisiones:**
  - "D10: Un solo editor para todo (básico + espacios), 4 pestañas"
  - "D11: Sin auto-diálogo al crear; doble-click = editar; Data tab = propiedades directas"
  - "D12: Resumen combinado X+Y visible en editor"

---

## ✅ DT-7 — Panel de propiedades COCO via click derecho — **RESUELTO 2026-10-20**

- **Archivos:** `vdo_coco_core.py`, `vdo_coco_unified_task.py`
- **Decisión:** **Click derecho en objeto COCO → "Propiedades del COCO" → Panel unificado modal**.
  Este será el **nuevo estándar para todos los módulos VDO** (paneles, cajones, etc.): un panel de propiedades especializado accesible por click derecho, no por pestaña Datos ni auto-diálogos.
- **Mejoras UX implementadas:**
  - "Dividir en N" → SpinBox libre (2-20) + botón "Dividir" (reemplaza botones fijos 1/2/1/3/1/4)
  - Botones renombrados: "Añadir vano", "Eliminar vano", "Sub-dividir" (antes "Sub-configurar")
  - Pestañas: "Divisiones Verticales (Columnas)", "Divisiones Horizontales (Repisas)"
  - Sub-panel: "Sub-dividir vano seleccionado → Eje: Horizontal/Vertical"
  - Anidación recursiva X→Y→X... ilimitada (soportada por motor)
- **Por qué no pestaña Datos:** FreeCAD Python no permite editores personalizados en Property Panel (solo tipos nativos C++: spinbox, combobox, etc.). JSON en `PropertyString` queda como fallback visible/editable a mano.
- **Por qué modal (Task Panel):** FreeCAD modal es estable y estándar. Tiempo real requeriría diálogo no-modal + recompute en cada cambio + manejo cancelación = frágil.
- **Validación:** Syntax OK, pendiente prueba en FreeCAD GUI.

---

## ✅ DT-4 — Panel migrado a `Part::FeaturePython` (pose y orientación en vivo)

- **Archivo:** `vdo_panel_core.py`, `vdo_panel_task.py`
- **Síntoma original:** el panel era un `Part::Box` plano sin `Proxy`/`execute()`, por lo
  que cambiar `VDO_Orientacion` no re-mapeaba las expresiones y la rotación tampoco
  quedaba como pose desacoplada de la geometría.
- **Solución (2026-10-21):**
  - `PanelFeature` (`Part::FeaturePython`) con `Largo/Ancho/Espesor` (`PropertyLength`),
    `VDO_Orientacion`, `VDO_Etiqueta`, `VDO_Material_Ref`, `VDO_Canto_Norte/Sur/Este/Oeste`
    y las propiedades comunes de pose (`VDO_RotacionZ`, `VDO_Anclaje`).
  - `execute()` genera `Part.makeBox(largo, ancho, espesor)` y **no toca `Placement`**.
  - `aplicar_mapeo_orientacion(obj, orientacion)` re-aplica las expresiones
    `<<Params>>.*` en vivo y `PanelTaskPanel` las controla (checkbox "Usar Params").
  - `crear_pieza()` migra un `Part::Box` previo del mismo nombre a FeaturePython.
  - `ViewProviderPanel(VDOViewProviderBase)` → clic derecho/doble clic abren el panel.
- **Compatibilidad despiece:** `vdo_export_cutting_list.extraer_pieza()` detecta
  `Largo/Ancho/Espesor` y exporta caras del tablero sin re-orientar.

---

## ✅ D17–D21 — Marco común de módulos y flujo de creación (2026-10-21)

- **Archivos nuevos:** `vdo_task_base.py`, `vdo_module_props.py`,
  `vdo_view_base.py`, `vdo_module_specs.py`, `vdo_creation_flow.py`,
  `vdo_placement.py`, `vdo_panel_task.py`.
- **D17 — Triple acceso:** clic derecho (`setupContextMenu` + `menu.addAction`),
  doble clic (`doubleClicked`) y flujo de creación comparten el **mismo** Task Panel
  del módulo. API verificada en FreeCAD 1.1.4 (`getContextMenuItems`/`onDoubleClick`
  no existen).
- **D18 — Flujo de creación:** toolbar → crear objeto **oculto** dentro de una única
  transacción → panel de configuración → colocación con el mouse → `commit`. Cancelar
  el panel o la colocación **borra** el objeto y aborta la transacción
  (`crear_modulo_interactivo`, `vdo_creation_flow.py`).
- **D19 — Colocación libre:** prioridad `Gui.Snapper.getPoint` (respeta snap de Draft)
  con fallback Coin3D (`SoLocation2Event`/`SoMouseButtonEvent`/`SoKeyboardEvent` +
  `getObjectInfo`/`getPoint`). El objeto permanece oculto hasta el primer movimiento;
  Esc cancela (`vdo_placement.py`).
- **D20 — Pose, no geometría:** `VDO_RotacionZ` (`PropertyAngle`) y `VDO_Anclaje`
  (`PropertyEnumeration`) viven en el objeto; `execute()` nunca modifica `Placement`.
  La rotación se pasa en grados (`App.Rotation` usa grados; `Rotation.Angle` devuelve radianes).
- **D21 — Marco común:** `vdo_module_specs.MODULE_SPECS` registra fábrica, panel,
  icono, menú y configuración por defecto de `coco_4c`, `cajon_oculta` y los paneles.
  Los `ViewProvider` heredan `VDOViewProviderBase`; los paneles de tarea heredan
  `VDOTransactionMixin` (`auto_transaction=False` durante la creación).

- **Validación:** `python3 -m py_compile` OK en todos los archivos; tests headless con
  `FreeCADCmd` (creación, panel FeaturePython, expresiones, pose, COCO anidado,
  exportación de piezas). Pendiente prueba visual en GUI (sin display en este entorno).

- **Deuda remanente (UX):** `aplicar_rotacion()` ya rota alrededor del anclaje con
  bbox local real (`transformShape`). Los handles 3D del COCO siguen siendo solo
  visuales (Fases 2/3 pendientes).

## ✅ Ajustes de GUI y entrada de datos (2026-10-22)

- **Botones explícitos** en los paneles COCO/Cajón/Panel (`QDialogButtonBox`):
  “Crear y colocar” durante la creación y “Aplicar” en edición, más “Cancelar”.
- **Enter/valores viejos:** `accept()` llama `interpretText()` en todos los spins
  antes de leerlos; evita que el panel cree con los valores por defecto (600 mm).
- **Decimales:** nuevo `vdo_qt.VDO_DoubleSpinBox` acepta punto y coma
  (`850.5` y `850,5`) y varios decimales, independiente del locale.
- **Rangos mínimos:** los mínimos de medida bajan a `1` para que escribir
  “8” camino de “800” no sea rechazado/reseteado por el spinbox.
- **Apertura robusta:** `abrir_panel_objeto()` + `reparar_viewprovider()` reabren
  el panel aunque el objeto haya perdido el proxy. Comando de toolbar
  “Propiedades VDO” (`vdo_editar_vdo.FCMacro`) para árbol o vista 3D.
- **Diagnóstico:** `diagnostico_viewprovider()` imprime `TypeId`, proxy y métodos
  disponibles; se ejecuta al crear un módulo para detectar proxys perdidos.
- **Nota FreeCAD:** `setupContextMenu`/`doubleClicked` son hooks del **árbol**
  (Model), no de la vista 3D.

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

*Deuda técnica VDO — generado 2026-10-20.*

## ✅ Divisiones COCO v2 — matriz de vanos (2026-10-22)

- **Archivos nuevos:** `vdo_layout.py`, `vdo_coco_divisions_task.py`,
  `vdo_coco_preview2d.py`.
- **Archivos modificados:** `vdo_coco_core.py` (`VDO_Divisiones` + cavidad
  interior), `vdo_coco_spaces.py` (`generar_divisiones_matriz`),
  `vdo_coco_unified_task.py` (pestaña única “Divisiones”).
- **Resuelto:** cruces vertical/repisa (repisas segmentadas por columna),
  reparto fijo/libre, último absorbe, overflow bloqueado en UI, preview 2D
  bidireccional con el árbol, árbol agrupado por filas Y, anidación X/Y.
- **Migración:** `EspaciosX/Y` se conservan como legado; `Layout.from_legacy()`
  solo migra divisiones raíz. Las subdivisiones anidadas antiguas requieren
  rehacerlas en el editor nuevo.
- **Pendiente Fase 1:** transacción al abrir panel + debounce de recompute para
  edición en vivo. Hoy los cambios se aplican en bloque al pulsar “Aplicar”,
  por lo que Cancelar no requiere abort y el Undo sigue siendo único.
- **Pendiente Fase 3/4:** prueba visual en GUI real (árbol/preview), más tests
  automáticos permanentes y documentación de usuario final.

---

## ✅ D22 — Fondo delgado en el frente + preview ambiguo — **RESUELTO 2026-10-26**

- **Archivos:** `vdo_coco_core.py`, `vdo_frames.py`, `vdo_finish.py`,
  `vdo_coco_preview2d.py`, `vdo_coco_unified_task.py`.
- **Síntoma:** con `calibre_fondo <= 8`, el fondo se creaba en `f_y=0` (frente
  funcional), con `+2×ranura` de sobremedida y sin ranuras reales; además el
  preview no declaraba qué eje era el frente y se interpretaba como espejado.
- **Solución:**
  - Marco local único: `Y+ = fondo`, `frente = Y−`.
  - Fondo delgado en `f_y = fondo − calibre − ranura`, con ranuras en laterales,
    base y techo; el panel entra en ellas sin solape.
  - Divisiones limitadas a `f_y` para no atravesar el fondo.
  - Preview con `FRENTE (Y−)` y `X→  Y↑`; sin espejo.
- **Validación:** `common().Volume == 0` entre todas las piezas para fondos de
  6/18 mm, fondos de 300/580 mm y ranuras de 3/6 mm; tests v2 de divisiones OK.

## 🧾 D23 — Acabado de caras (no sólo cantos)

- **Síntoma:** la política actual trabaja por **borde de tablero**. Un divisor
  con el fondo visto y sin fachada tiene la **cara** del fondo expuesta, pero
  sus cuatro bordes van en ranura; hoy no se emite ningún acabado de cara.
- **Impacto:** el despiece marca cantos correctamente, pero no describe
  revestimiento/chapa de una cara vista.
- **Propuesta:** añadir un `plan_caras` en C2 (cara vista → acabado/material),
  separado de `plan_cantos`; no mezclarlo con la geometría L1/L2.

## 🧾 D24 — Exposición/cantos sólo en COCO

- **Síntoma:** `VDO_Lados_Vistos`/`VDO_Lados_Apoyados` se añaden a todos los
  módulos, pero sólo el COCO tiene UI y política de cantos. Cajones y paneles
  sueltos conservan sus cantos manuales sin cruzar exposición.
- **Propuesta:** extender `vdo_finish.aplicar_cantos()` a `vdo_cajon_core` y a
  los paneles sueltos cuando tengan `rol` contextual.

## 🧾 D25 — Tipo de canto fijo (`RIG`)

- **Síntoma:** los bordes vistos se marcan siempre `RIG`; `SMRG` existe en el
  vocabulario pero la política no elige por material/espesor/uso.
- **Propuesta:** mover la selección `RIG/SMRG/FX` a una tabla de datos pura
  (material × espesor × tipo de borde), no a `vdo_finish.py`.

## 🧾 D26 — Tests A+B temporales

- **Síntoma:** la validación de orientación, ranuras y cantos se hizo con
  scripts en `/tmp`, no con una suite permanente.
- **Propuesta:** crear `tests/` con casos mínimos: fondo Y+, sin solapes,
  preview local, exposición contra muro/divisor/lateral expuesto y CSV.

## 🧾 D27 — C0/C1/C2 pendientes

- **Síntoma:** la exposición es manual en el módulo; no existe `VDO_Espacio`
  ni cálculo de pose global/contexto.
- **Propuesta:** implementar C0 (muros/piso/vistas), C1 (instancia+pose) y C2
  (exposición calculada) sin escribir geometría; la UI manual queda como
  override.

---

## 🧾 D28 — Reengrose Fase 1 sólo en L1

- **Síntoma:** `vdo_reengrose.py`, el panel L1 y la UI ya funcionan, pero
  `vdo_layout`, `vdo_coco_core`, `vdo_coco_spaces` y `vdo_finish` todavía no
  aplican modificadores a divisiones, laterales, base o techo.
- **Impacto:** el nudo de bisagras se puede modelar en un panel suelto, pero
  aún no dentro de un COCO.
- **Propuesta:** Fase 2: modifiers por pieza/división en `VDO_Reengrose_JSON`,
  separadores variables en `resolve_layout()` y consumo en COCO/finish.

## 🧾 D29 — Un reengrose por panel

- **Síntoma:** el DTO y las propiedades representan una sola tira o pacha.
- **Impacto:** no se puede modelar todavía una tapa con cuatro tiras
  perimetrales en una sola operación.
- **Propuesta:** añadir `borde` (`izquierda/derecha/frente/fondo`) y lista de
  modificadores, o un modo `perimetral` con cuatro tiras.

## 🧾 D30 — Mocheo automático sin integración

- **Síntoma:** `generar_mocheo_repisa()` y
  `calcular_vano_neto_con_reengrose()` son puros y están testeados, pero no se
  llaman desde el resolvedor de vanos.
- **Impacto:** las repisas de un COCO aún no se recortan ni se mochean
  automáticamente al chocar con un reengrose.
- **Propuesta:** integrar en `vdo_layout._resolver_track()` y en la generación
  de repisas de `vdo_coco_spaces`; probar colisión real por AABB.

## 🧾 D31 — Previsualización de pacha

- **Síntoma:** el CSV ya agrupa las subpiezas con `Group`/`Operation`, pero el
  preview de lista de corte no muestra el grupo ni el canto de bloque.
- **Propuesta:** añadir columnas/indicadores de grupo y operación en
  `vdo_cutting_list_preview`, sin alterar el optimizador.

---

## 🧾 D32 — Preview 2D sin tiras de reengrose

- **Síntoma:** el preview y el árbol muestran la luz clara, pero no dibujan la
  tira ni el mocheo. El usuario debe mirar el inspector o el 3D.
- **Propósito:** añadir overlay de refuerzos y marcar repisas retrocedidas o
  mocheadas, sin convertirlo en una tabla.

## 🧾 D33 — Metadatos de tiras de carcasa segmentadas

- **Síntoma:** cuando una tira de base/techo/lateral choca con un núcleo, la
  geometría se recorta para no solaparse, pero `VDO_Paneles_JSON` conserva la
  medida nominal de la tira.
- **Propósito:** generar subpiezas segmentadas o `mocheos` equivalentes para
  que el despiece refleje exactamente lo que se corta.

## 🧾 D34 — Reengrose horizontal por fila/columna

- **Síntoma:** las divisiones verticales y las carcasas ya reducen vanos; las
  repisas horizontales con reengrose no ajustan la altura neta global de la
  misma forma.
- **Propósito:** modelar extras por segmento de repisa y resolver la altura
  neta cuando un reengrose horizontal invade un vano.

## 🧾 D35 — Perímetro y selección directa en preview

- **Síntoma:** falta el modo perimetral de cuatro tiras y el clic directo
  sobre una pieza en el preview 2D; hoy la selección directa es por árbol o
  combo del inspector.
- **Propósito:** añadir `borde`/lista de modificadores y hotspots de piezas
  en el preview.
