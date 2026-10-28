# 🏗️ Contexto Técnico VDO - Arquitectura del Sistema

## 📖 Visión General

El sistema VDO (Veta de Oro) es un motor paramétrico para FreeCAD que genera muebles modulares de melamina. La arquitectura sigue el patrón **Code-as-UI** donde la configuración se define en código Python en lugar de interfaces gráficas manuales.

---

## 🧱 Axiomas de la Arquitectura

### Axioma 1: Datos Puros (Sin lógica)
**Archivo**: `vdo_manifest.py`

- Contrato de dependencias globales del taller
- Contiene: hojas, alias, valores, dependencias
- **No contiene lógica**: solo datos (exportable a JSON/ERP)
- Es la "fuente única de la verdad"

### Axioma 2: Motor Geométrico (Sin UI)
**Archivos**: `vdo_panel_core.py`, `vdo_coco_core.py`

- Lógica geométrica pura
- Expresiones enlazadas al Guardián
- Gestión de propiedades dinámicas
- **No tiene dependencias de UI**

### Axioma 3: Comandos (Capa UI)
**Archivos**: `vdo_*.FCMacro`

- Envoltorios ultraligeros (~25 líneas)
- Contienen solo parámetros de configuración
- Llaman al motor central con sus respectivos parámetros
- **Uno por cada variante de mueble**

### Axioma 4: Inicialización (Orquestador)
**Archivo**: `InitGui.py` (futuro)

- Registra workbench en FreeCAD
- Inyecta comandos e iconos
- **Opcional**: se puede usar sin él

### Axioma 5: Separación Semántica / Física

- El **motor geométrico** (`vdo_panel_core.py`) es **agnóstico**: modela únicamente una
  pieza física (tablero) con atributos físicos: `orientacion`, `cantos` por lado,
  `material_ref`, `espesor`. Nada más.
- La **semántica de mobiliario** ("fachada", "base", "división", "lateral"...) **no** vive
  en el motor ni en reglas geométricas. Vivirá en un **diccionario semántico** (datos puros)
  que hoy **no existe** → por tanto hoy **no se acopla nada**.
- La `orientacion` es un **atributo físico libre e independiente** de la semántica: una
  fachada puede ser horizontal (abatible) y un panel base vertical, sin romper el sistema.
- El mapeo de semántica a propiedades físicas inmutables (p.ej. "fachada = canto rígido ×4
  + material `fachadas`") pertenece al diccionario, **no** al motor.

> ⚠️ **Fallo axiomático corregido (2026-10-10):** la versión previa del motor acoplaba
> `tipo == "fachada"` a reglas físicas (cantos, holguras, tipo de fachada) y arrastraba
> cantos por subtipo. Eso violaba este axioma. Ver `PROGRESO_VDO.yaml` (Task 6).

**Diccionario semántico**: `vdo_diccionario_semantico.md` (esqueleto de la tabla de piezas;
cuando madure, se promoverá a datos puros en `vdo_manifest.json` → sección `semantica`).

**Deuda técnica**: `DEUDA_TECNICA_VDO.md` (DT-1..DT-5: posición de divisores, recursión
anidada, registro de la división en UI, panel `Part::Box` plano, diccionario vacío).

### Marco local único (2026-10-26)

Contrato geométrico obligatorio para todas las capas:

```
X+ = derecha
Y+ = fondo
Z+ = arriba
frente funcional = Y−
```

- `vdo_frames.py` es la fuente pura de lados, normales y serialización.
- El preview 2D dibuja el frente local, con etiqueta `FRENTE (Y−)` y ejes
  `X→  Y↑`; **no se espeja** aunque el módulo esté rotado 180° en el espacio.
- La rotación global vive en `VDO_RotacionZ` (pose), no en la geometría local.
- Los seis lados de módulo son: `frente`, `fondo`, `izquierda`, `derecha`,
  `superior`, `inferior`.

---

## 🧩 Reengrose / Pacha — Fase 1 (L1)

El reengrose es una **capa modificadora** de la pieza L1. No conoce el mueble,
el vano ni la exposición; solo recibe una pieza base y devuelve piezas locales,
cantos y datos de colisión.

### Coordenadas locales del tablero

```
X = largo
Y = ancho / profundidad de la pieza
Z = espesor
Cara A = +Z
Cara B = -Z
```

- `orientacion = paralela`: la tira corre a lo largo del `Largo`.
- `orientacion = transversal`: la tira cruza el `Ancho`.
- `ancho`: ancho de la tira sobre la cara.
- `espesor`: espesor de la tira; `0` o `None` significa “usar el espesor del panel”.
- `cara`: cara A o B donde se adhiere.
- `alineacion_profundidad`: `frente`, `centrado` o `fondo` para la tira paralela.
- `modo_fabricacion`:
  - `independiente`: tira separada, se cantea aparte.
  - `pacha`: se pega en bruto y se cantea como bloque.
- `alcance`:
  - `parcial`: una tira.
  - `total`: duplica toda la cara del panel.
- `politica_repisa`: `retroceder` (por defecto) o `mochear`.

### Propiedades nativas del panel L1

| Propiedad | Tipo | Descripción |
|-----------|------|-------------|
| `VDO_Reengrose_Activo` | Bool | Activa el modificador |
| `VDO_Reengrose_Orientacion` | Enum | `paralela` / `transversal` |
| `VDO_Reengrose_Ancho` | Length | Ancho de la tira (70 mm típico) |
| `VDO_Reengrose_Espesor` | Length | 0 = usar espesor del panel |
| `VDO_Reengrose_Cara` | Enum | `cara_a` / `cara_b` |
| `VDO_Reengrose_Alineacion` | Enum | `frente` / `centrado` / `fondo` |
| `VDO_Reengrose_Modo` | Enum | `independiente` / `pacha` |
| `VDO_Reengrose_Alcance` | Enum | `parcial` / `total` |
| `VDO_Reengrose_PoliticaRepisa` | Enum | `retroceder` / `mochear` |
| `VDO_Reengrose_JSON` | String | Instantánea JSON para despiece |

### Tooltips

- Los controles Qt usan `setToolTip()` con lenguaje de taller, no con jerga
  técnica. Los tooltips de propiedades usan el tercer argumento de
  `addProperty()` para que FreeCAD los muestre en el panel de propiedades.
- En Fase 1 se cubrieron Panel L1, COCO, Divisiones y Cajón. Los controles
  nuevos de reengrose tienen ayuda específica por parámetro.

### Despiece

- `independiente`: panel base + tira, cada uno con sus cantos.
- `pacha parcial`: dos subpiezas de 18 mm con `grupo_pacha` y
  `operacion = "Encolar + canto de bloque unificado"`.
- `pacha total`: base + duplicado completo, mismo grupo y canto de bloque.
- El CSV incorpora `Group` y `Operation`; los cantos individuales de una pacha
  quedan en `FX` y el bloque lleva `cantos_bloque` en `RIG`.

### Ayudas puras para Fase 2

- `detectar_colision(aabb_a, aabb_b)`: colisión 3D por caja envolvente.
- `calcular_vano_neto_con_reengrose(vano, division)`: reduce el vano neto.
- `generar_mocheo_repisa(repisa, reengrose, politica)`: devuelve `None`,
  retroceso o rebaje en escuadra. La integración con el motor de vanos queda
  para Fase 2.

### Limitación de Fase 1

- Un reengrose por panel.
- El perímetro de cuatro tiras (tapa de escritorio) requiere un selector de
  borde que se añadirá en Fase 2.
- COCO, vanos y repisas todavía no consumen el modificador.

### Integración COCO — Fases 2 y 3

`VDO_Reengrose_JSON` vive en el COCO como un diccionario:

```
{
  "lateral_izquierdo": {...},
  "lateral_derecho": {...},
  "base": {...},
  "techo": {...},
  "fondo": {...},
  "division_x:x2": {...},
  "division_y:y2_x1": {...}
}
```

Las claves de división usan el `path` estable de `PanelPiece` (`x2`, `x1.2`,
`y2_x1`, `y2.2_x1`). El editor 2D guarda y recupera ese JSON al aplicar.

#### Vanos claros vs. geometría nominal

`resolve_layout(..., reengroses=...)` calcula:

- **luz clara** (`clear_start`, `clear_size`): lo que ve la puerta/cajón,
  descontando la tira que invade el vano;
- **geometría nominal** (`start`, `size`): hasta la cara del núcleo de la
  división, usada por la repisa que puede pasar detrás de la tira.

La división conserva su posición de núcleo; la tira se descuenta del vano
afectado. Si la tira está en la cara A/B, sólo se reduce ese lado; con
`ambos` se reducen los dos.

#### Repisas: retroceso y mocheo

- Si no hay colisión, la repisa queda igual.
- `retroceder`: corta la profundidad de la repisa a 90° detrás de la tira.
  Si el reengrose cubre todo el fondo, reduce el ancho.
- `mochear`: descuenta el prisma de intersección en la esquina; la repisa
  llega al frente con un cajeado.

El resultado queda en `VDO_Paneles_JSON[].mocheos` y en el ancho/profundidad
ajustados de la pieza.

#### Subpiezas y CSV

Para cada pieza con reengrose activo:

- `independiente`: base + tira, cada una con sus cantos.
- `pacha`: base + refuerzo con `grupo_pacha`,
  `operacion = "Encolar + canto de bloque unificado"` y `cantos_bloque`
  tomados de la exposición de la pieza base.
- El CSV incluye `Group` y `Operation`.

#### UI contextual

En `DivisionesEditor`:

- El árbol incorpora el grupo **“Elementos / refuerzos”**.
- El inspector muestra **“Reengrose / Refuerzo”** para el elemento
  seleccionado.
- Controles: activo, elemento, orientación, ancho, espesor Auto/editable,
  cara A/B/ambos, alineación, fabricación, alcance y política de repisa.
- Todos los controles tienen tooltips de taller.

Limitaciones actuales: el preview 2D no dibuja la tira, y las tiras de
carcasa que chocan con divisiones se recortan geométricamente pero el JSON
de despiece conserva la medida nominal de la tira.

---

## 🔄 Patrón de Diseño: Thin Wrapper (Facade)

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA UI (Envoltorios)                    │
│  vdo_panel_estandar.FCMacro  vdo_panel_fachada.FCMacro     │
│  vdo_coco_4c.FCMacro         (más variantes futuras)       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 CAPA MOTOR (Lógica Central)                 │
│  vdo_panel_core.py  →  crear_pieza(configuracion)          │
│  vdo_coco_core.py   →  crear_coco(configuracion)           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                CAPA DATOS (Manifiesto)                      │
│  vdo_manifest.py  →  VDO_MANIFEST (parámetros globales)    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│               CAPA VALIDACIÓN (Guardián)                    │
│  vdo_guardian.py  →  vdo_guard() (asegura entorno)         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  FreeCAD (Geometría 3D)                     │
│  Part::Box + Propiedades VDO + Expresiones Paramétricas    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📐 Modelos de Datos

### Panel (vdo_panel_core.py) — contrato agnóstico

```python
# Entrada (sin semántica de mobiliario; Axioma 5)
configuracion = {
    "nombre": str,
    "etiqueta": str,                          # tag libre, NO dirige geometría
    "orientacion": "horizontal" | "vertical", # OBLIGATORIO (vocabulario del manifiesto)
    "cantos": {
        "norte": "RIG" | "FX" | "SMRG",
        "sur":   "RIG" | "FX" | "SMRG",
        "este":  "RIG" | "FX" | "SMRG",
        "oeste": "RIG" | "FX" | "SMRG"
    },
    "material_ref": str                       # opcional (default "melamina_standar")
}

# Salida (FreeCAD Object)
panel = {
    "Type": "Part::FeaturePython",             # PanelFeature
    # Dimensiones del tablero (caras + grosor):
    # horizontal: Largo=<<Params>>.ancho, Ancho=<<Params>>.fondo, Espesor=<<Params>>.espesor
    # vertical:   Largo=<<Params>>.alto,  Ancho=<<Params>>.fondo, Espesor=<<Params>>.espesor
    "Shape": Part.makeBox(Largo, Ancho, Espesor),   # generate by execute()
    "Placement": pose libre (rotación Z + traslación),  # NUNCA la toca execute()
    "VDO_Tipo": "panel",
    "VDO_Orientacion": "horizontal" | "vertical",
    "VDO_Canto_Norte/Sur/Este/Oeste": "RIG" | "FX" | "SMRG",
    "VDO_Material_Ref": str,
    "VDO_Etiqueta": str,
    "VDO_RotacionZ": float,                    # pose (PropertyAngle, grados)
    "VDO_Anclaje": enum,                       # esquina que se ancla al cursor
}
```

> La orientación NO se modela con rotación de `Placement` (esa pose pertenece al
> mueble/espacio). Se modela por **mapeo de ejes** de las expresiones paramétricas, de modo
> que el despiece y el modelo de espacio la lean sin ambigüedad.

---

## 🧩 Marco común de módulos (D17–D21)

Todo módulo VDO (COCO, cajón, paneles y futuros) declara su contrato en
`vdo_module_specs.MODULE_SPECS`:

```python
"panel_estandar": {
    "label": "Panel Estándar",
    "menu": "Propiedades del Panel",       # texto del clic derecho
    "icon": "vdo_panel.svg",
    "factory": ("vdo_panel_core", "crear_pieza"),
    "panel":   ("vdo_panel_task", "PanelTaskPanel"),
    "config":  { ... defaults ... },
}
```

### Flujo único de creación y edición

```python
from vdo_creation_flow import crear_modulo_interactivo
crear_modulo_interactivo("panel_estandar", {"nombre": "Panel_Base"})
```

1. **Crear oculto**: la fábrica se ejecuta dentro de una sola transacción y el
   objeto queda oculto (`ViewObject.Visibility = False`).
2. **Configurar**: se abre el Task Panel del módulo (`auto_transaction=False`).
3. **Colocar**: `vdo_placement.iniciar_colocacion()` usa `Gui.Snapper.getPoint`
   (respeta el snap de Draft) o un fallback Coin3D. El módulo aparece al primer
   movimiento del mouse; el clic deposita; Esc cancela.
4. **Commit**: al soltar se recomputa y se confirma la transacción. Si se cancela
   el panel o la colocación se **aborta la transacción y se borra el objeto**.

### Triple acceso al mismo panel

| Vía | API FreeCAD 1.1.4 | Implementado en |
|-----|-------------------|-----------------|
| Clic derecho | `setupContextMenu(self, vobj, menu)` | `vdo_view_base.VDOViewProviderBase` |
| Doble clic | `doubleClicked(self, vobj)` | `vdo_view_base.VDOViewProviderBase` |
| Creación | `Gui.Control.showDialog(panel)` | `vdo_creation_flow.py` |

> `getContextMenuItems()` y `onDoubleClick()` **no existen** en FreeCAD 1.1.4.

### Pose vs. geometría (D20)

- `VDO_RotacionZ` y `VDO_Anclaje` son **pose**; se guardan en el objeto y se
  aplican sobre `Placement`.
- `execute()` reconstruye solo el `Shape` y **nunca** toca `Placement`.
- `App.Rotation` recibe **grados** en su constructor (`App.Rotation(axis, angle)`);
  `Rotation.Angle` devuelve radianes. `vdo_module_props.rotacion_z()` trabaja en grados.

### Cofre (vdo_coco_core.py)

```python
# Entrada
configuracion = {
    "nombre": str,
    "etiqueta": str,
    "fondo": bool,
    "calibre_fondo": int,
    "profundidad_ranura": int,
    "distancia_borde": int,
    "tapa": "externo" | "interno",
    "base": "externo" | "interno",
    "lados_vistos": ["frente"],          # contextual, JSON en el objeto
    "lados_apoyados": ["fondo"]
}

# Salida (FreeCAD Group)
coco = {
    "Type": "App::DocumentObjectGroup",
    "Children": [
        "PANEL_LAT_IZQ",
        "PANEL_LAT_DER",
        "PANEL_BASE",
        "PANEL_TECHO",
        "PANEL_FONDO"  # condicional
    ]
}
```

---

## � Reglas de Negocio

### 1. CANTOS

| Tipo / contexto | Cantos por Defecto |
|-----------------|-------------------|
| `estandar` | Selectivos (ej: solo este) |
| `fachada` | 4 cantos gruesos |
| COCO con exposición | `vdo_finish`: `RIG` sólo en bordes exteriores vistos; `FX` en uniones |
| Reengrose independiente | Pieza base con sus cantos + tira con canto perimetral |
| Reengrose pacha | Piezas individuales en `FX`; `cantos_bloque` en `RIG` |

### 2. FONDO (RESPALDO)

| Condición | Comportamiento |
|-----------|----------------|
| `fondo = False` | No existe en el modelo |
| `calibre ≤ 8mm` | Ranurado en laterales/base/techo, en `Y+`; panel `= cavidad + 2×ranura` |
| `calibre > 8mm` | Sin ranura, retranqueado desde el fondo con `DistanciaBorde` |

El fondo **nunca** se coloca en `Y=0`. Para el fondo delgado:

```
f_y = fondo − calibre_fondo − profundidad_ranura
```

Las divisiones terminan en la cara frontal del fondo (`f_y`), no en `fondo`,
para no atravesarlo.

### 3. ESTRUCTURA (TAPA/BASE)

| Tapa | Base | Resultado |
|------|------|-----------|
| `externo` | `interno` | Tapa cubre laterales, base cabe entre ellos |
| `externo` | `externo` | Ambos cubren laterales |
| `interno` | `interno` | Ambos caben entre laterales |
| `interno` | `externo` | Tapa cabe, base cubre |

---

## 🔧 Sistema de Propiedades VDO

Todas las propiedades personalizadas se agrupan bajo la categoría **"VDO"** en FreeCAD:

| Propiedad | Tipo | Descripción |
|-----------|------|-------------|
| `VDO_Tipo` | String | Identifica el tipo de pieza (`panel` / `contenedor`) |
| `VDO_Orientacion` | Enum | `horizontal` / `vertical` (atributo físico libre) |
| `VDO_Etiqueta` | String | Tag libre descriptivo (NO dirige geometría) |
| `VDO_Canto Norte/Sur/Este/Oeste` | Enum | Tipo de canto por lado: `RIG` / `FX` / `SMRG` |
| `VDO_Material_Ref` | String | Referencia de material (manifiesto) |
| `VDO_Calibre` | Float | Espesor del fondo (contenedores) |
| `VDO_RotacionZ` | Angle (grados) | Rotación de pose alrededor de Z (todos los módulos) |
| `VDO_Anclaje` | Enum | Esquina del módulo que se ancla al cursor (todos los módulos) |
| `VDO_Lados_Vistos` | String JSON | Lados visibles desde el espacio, p.ej. `["frente","derecha"]` |
| `VDO_Lados_Apoyados` | String JSON | Lados contra muro/piso, p.ej. `["fondo"]` |
| `VDO_Paneles_JSON[].rol` | String | `lateral_izquierdo`, `base`, `techo`, `fondo`, `division_x`, `division_y` |
| `VDO_Paneles_JSON[].cantos` | Dict | `norte/sur/este/oeste` → `RIG`, `FX`, `SMRG` |

**Uso en reportes/despiece:**
```python
# Filtrar piezas por tipo
for obj in doc.Objects:
    if hasattr(obj, "VDO_Tipo"):
        if obj.VDO_Tipo == "Fachada":
            print(f"Pieza de fachada: {obj.Name}")
```

---

## 📊 Dependencias del Sistema

### Hojas Obligatorias (FreeCAD Spreadsheet)

| Hoja | Propósito |
|------|-----------|
| `Params_Melamina` | Parámetros globales del taller |
| `Params` | Parámetros locales del módulo |

### Archivos Core

| Archivo | Propósito |
|---------|-----------|
| `vdo_manifest.py` | Contrato de datos |
| `vdo_guardian.py` | Validación de entorno |
| `vdo_panel_core.py` | Motor de paneles (FeaturePython, agnóstico) |
| `vdo_coco_core.py` | Motor de cofres |
| `vdo_cajon_core.py` | Motor de cajón con corredera oculta |
| `vdo_module_specs.py` | Registro de módulos (fábrica + panel + defaults) |
| `vdo_module_props.py` | Pose común (`VDO_RotacionZ`, `VDO_Anclaje`) y exposición |
| `vdo_frames.py` | Marco local puro: lados, normales, rotación y JSON de exposición |
| `vdo_finish.py` | Política de acabados: lados vistos → cantos por borde |
| `vdo_reengrose.py` | Motor puro de reengroses/pachas, colisiones y despiece L1 |
| `vdo_creation_flow.py` | Flujo crear → configurar → colocar |
| `vdo_placement.py` | Colocación con snap (Draft) + fallback Coin3D |
| `vdo_diccionario_semantico.md` | Diccionario semántico (pieza → propiedades inmutables) |

### Archivos UI

| Archivo | Propósito |
|---------|-----------|
| `vdo_view_base.py` | ViewProvider base (clic derecho + doble clic) |
| `vdo_task_base.py` | Mixin de transacciones para Task Panels |
| `vdo_panel_task.py` | Panel de propiedades de cualquier tablero |
| `vdo_coco_unified_task.py` | Editor unificado COCO (Medidas, Estructura, Divisiones) |
| `vdo_coco_divisions_task.py` | Editor de matriz de vanos (preview 2D + árbol + inspector) |
| `vdo_coco_preview2d.py` | Preview frontal 2D con selección de vanos |
| `vdo_layout.py` | Modelo/resolvedor puro de la matriz de vanos v2 |
| `vdo_cajon_task.py` | Panel de propiedades del cajón |
| `vdo_panel_estandar.FCMacro` | Panel estándar |
| `vdo_panel_fachada.FCMacro` | Panel fachada |
| `vdo_coco_4c.FCMacro` | COCO 4 paneles |

---

## 🚀 Flujo de Instalación

```
1. Copiar carpeta Macro/ a FreeCAD Macro Path
2. FreeCAD → Macro → Macros → Ejecutar vdo_guardian.py
3. Verificar: hojas Params_Melamina y Params creadas
4. Ejecutar vdo_coco_4c.FCMacro
5. Verificar: COCO_4C con 5 paneles
```

---

## 🧱 Matriz de vanos v2 (COCO)

- **Modelo puro:** `vdo_layout.py` (sin FreeCAD/Qt). Serializa en
  `VDO_Divisiones` como JSON `version: 2`.
- **Convención:** origen en la cavidad inferior izquierda; X izquierda→derecha;
  Y abajo→arriba. Etiquetas `(x2,y1)` y anidadas `(x2.1,y1)`, `(x2,y1.2)`.
- **Reparto:** medidas fijas primero; el espacio neto restante se reparte igual
  entre los vanos libres. Si todos son fijos, el último absorbe el sobrante.
  Si los fijos no caben, `resolve_layout()` marca overflow y el panel bloquea
  “Aplicar” con aviso rojo.
- **Geometría:** verticales raíz continuas de piso a techo interior; repisas
  raíz segmentadas por columna, apoyadas en caras internas de verticales.
  Subdivisiones anidadas alternan X/Y sin cruzar piezas.
- **Cavidad interior:** `cavidad_interior(alto, ancho, espesor)` devuelve
  `x0=t`, `z0=t`, `ancho-2t`, `alto-2t`, independiente de tapa/base interna o
  externa. El COCO usa esta cavidad para las divisiones.
- **Fondo y profundidad de divisiones:** el fondo delgado va en `Y+` con ranuras
  reales; las divisiones usan `fondo_divisiones = f_y` (cara frontal del fondo)
  para no solaparse con él.
- **Exposición y cantos:** `VDO_Lados_Vistos`/`VDO_Lados_Apoyados` se editan en
  la pestaña Medidas → Colocación. `vdo_finish.aplicar_cantos()` cruza esos
  lados con el rol de cada pieza y con `tapa`/`base` para marcar `RIG` sólo en
  bordes exteriores vistos; el resto queda en `FX`.
- **UI:** una sola pestaña “Divisiones” con preview 2D arriba, botonera
  `+X/−X/+Y/−Y`, árbol agrupado por filas `Y` y inspector por vano. `−X/−Y`
  piden confirmación si la última columna/fila contiene subdivisiones.
- **Compatibilidad:** `Layout.from_legacy()` migra `EspaciosX/Y` sólo a nivel
  raíz; las subdivisiones antiguas anidadas no se mapean y se avisa.
- **Validación headless:** `resolve_layout`, distribución fija/libre, overflow,
  anidación X→Y→X, preview/editor Qt offscreen y `common().Volume == 0` entre
  piezas.

## 🎯 Próximos Pasos

### Fase 1: Validación
- [x] Tests headless (`FreeCADCmd`): creación, expresiones, pose, COCO anidado
- [ ] Probar triple acceso (clic derecho / doble clic / creación) en GUI
- [ ] Probar colocación con snap de Draft y fallback Coin3D
- [ ] Confirmar propiedades VDO en panel de propiedades

### Fase 2: UI
- [x] Marco común (`VDOViewProviderBase`, `VDOTransactionMixin`)
- [x] Panel FeaturePython con re-mapeo vivo de orientación (DT-4)
- [ ] Rotación de pose alrededor del anclaje (hoy rota alrededor del origen local)
- [ ] Handles 3D del COCO operativos (detección de mouse / drag)

### Fase 3: Funcionalidad
- [ ] Generador de despiece (lista de cortes)
- [ ] Integración con ERP/reportes
- [ ] Más variantes de cofres

---

## 📝 Notas para Desarrolladores

### Para agregar un nuevo módulo VDO:

1. Implementar la fábrica (FeaturePython) y su panel en módulos Python.
2. Heredar el ViewProvider de `vdo_view_base.VDOViewProviderBase`.
3. Heredar el panel de `vdo_task_base.VDOTransactionMixin`.
4. Registrar el módulo en `vdo_module_specs.MODULE_SPECS` (fábrica, panel,
   icono, menú y `config` por defecto).
5. Crear un envoltorio `vdo_<modulo>.FCMacro` que llame a
   `crear_modulo_interactivo("<clave>", configuracion)`.
6. Agregar icono y registrar en `vdo_manifest.py` → `modulos_ui`.

### Para agregar un nuevo parámetro:

1. Agregar en `vdo_manifest.py` → sección correspondiente
2. Actualizar función del motor para usar el parámetro
3. Actualizar envoltorios con valor por defecto
4. Documentar en `PROGRESO_VDO.md`

---

## 🔍 Debugging

### Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| `No hay documento activo` | FreeCAD sin archivo abierto | Crear nuevo documento |
| `Hoja no encontrada` | Guardian no ejecutado | Ejecutar `vdo_guardian.vdo_guard()` |
| `Import failed` | Path incorrecto | Verificar Bootstrap en envoltorio |

### Logs Útiles

```python
# El motor imprime:
"📦 Panel creado: Nombre"
"✅ Panel 'Nombre' configurado como 'fachada'"
"📐 Estructura: Tapa=externo, Base=interno"
"📦 Fondo delgado (6mm) con ranuras de 3mm"
```

---

*Contexto técnico generado automáticamente - Motor VDO v1.4.0*
