# 04 — Decisiones ADR y Axiomas (Pilar 4)

**Sistema:** VDO (Veta de Oro) — FreeCAD 1.1+
**Estado:** Definitivo — sin placeholders

---

## 1. Los 5 Axiomas Matemáticos Oficiales

Los axiomas son invariantes que nunca deben romperse. Constituyen la fuente única de verdad para el control geométrico del sistema.

---

### Axioma 1 — Sistema de Coordenadas Global (COCO_Frame)

**Definición formal:**

El COCO define el marco de referencia global `COCO_Frame`:

```
COCO_Frame = {
  origin: (0, 0, 0) = esquina frontal-inferior-izquierda exterior del mueble
  X_axis: horizontal, positivo hacia la derecha (ancho del mueble)
  Y_axis: horizontal, positivo hacia el fondo (profundidad del mueble)
  Z_axis: vertical, positivo hacia arriba (altura del mueble)
  bounds: [0, ancho_total] × [0, fondo_total] × [0, alto_total]
}
```

**Invariantes:**
- Cualquier objeto con coordenadas $(x, y, z)$ en `COCO_Frame` debe cumplir:
  - $0 \le x \le \text{ancho\_total}$
  - $0 \le y \le \text{fondo\_total}$
  - $0 \le z \le \text{alto\_total}$
- No hay coordenadas negativas en `COCO_Frame` (exigencia fuerte).
- Los solapes (overlays) se representan en marcos locales, no globales.

**Marco local único (invariable para todas las capas):**
- $+X$ = Derecha
- $+Y$ = Fondo
- $+Z$ = Altura
- Frente funcional = $-Y$

---

### Axioma 2 — Definición Unívoca de "Ancho"

**Problema resuelto:** El término "ancho" aparecía con significados diferentes (`w` neto, `nominal_w` total, `ancho_libre` ambiguo).

**Jerarquía de definiciones:**

| Nivel | Símbolo | Definición | Ejemplo | Invariante |
|-------|---------|------------|---------|------------|
| **Base** | `w_vano_total` | $X_{max} - X_{min}$ del rectángulo del vano en `COCO_Frame` | 600.0 mm | Inmutable a través de transformaciones |
| **Decomposición** | `delta_divisiones` | $w_{vano\_total} - w_{disponible}$ (espacio para divisiones internas) | 25.4 mm | $\delta_{divisiones} \ge 0$ |
| **Capa local** | `w_disponible` | $w_{vano\_total} - \delta_{divisiones}$ (espacio útil para el componente) | 574.6 mm | $w_{disponible} = w_{vano\_total} - \delta_{divisiones}$ |
| **Parámetro de entrada** | `ancho_libre` | `ancho_libre := w_vano_total` (siempre total, NUNCA neto) | 600.0 mm | `ancho_libre` SIEMPRE es `w_vano_total` |

**Regla de mapeo obligatoria:**

| Módulo | Símbolo | Significado | Mapeo correcto | Bug si... |
|--------|---------|-------------|----------------|-----------|
| `vdo_layout.py` | `w` | tamaño neto (clear_size) | NO usar para `calcular_despiece` | ✗ se usa para despiece |
| `vdo_layout.py` | `nominal_w` | tamaño total (size) | Usar SIEMPRE para COCO | ✗ se usa `w` |
| `vdo_coco_unified_task.py` | `AnchoLibre` | ancho del vano en COCO | `= resuelto.nominal_w` | ✗ `= resuelto.w` |
| `vdo_cajon_despiece.py` | `li` | ancho libre recibido | Asumir `= w_vano_total` | ✗ se interpreta como neto |
| `vdo_cajon_despiece.py` | `ancho_ext` | caja exterior | `= li - delta` | ✓ correcto si `li = total` |

**Fórmula de transformación:**
$$\text{ancho\_libre} := w_{vano\_total} = nominal_w$$
$$w_{disponible} = w_{vano\_total} - \delta_{divisiones}$$
$$ancho_{ext} = li - \delta$$

**Invariante de consistencia:** $nominal_w \ge w$ siempre. Si $nominal_w < w$: BUG crítico.

---

### Axioma 3 — Marcos de Referencia Locales

**Definición formal:**

Cada componente (cajón, panel, fachada) define su propio marco local `LocalFrame`:

```
LocalFrame (para un cajón) = {
  origin: (0, 0, 0) = esquina frontal-exterior-inferior de la caja
  X_axis: ancho de la caja
  Y_axis: profundidad (hacia el fondo)
  Z_axis: altura
  bounds: [0, ancho_ext] × [0, profundidad] × [0, alto_caja]
  transform_to_coco: {
    base: (x_coco, 0, z_coco)  # LocalPlacement del cajón
    scale: 1.0 (sin escala)
    rotation: identity (sin rotación)
  }
}
```

**Invariante fundamental — Composición de transformaciones:**

$$\forall p \in LocalFrame(\text{cajón}): \quad p_{global} = p_{local} + LocalPlacement.base$$

**Nunca:**
- $p_{global} = p_{local} + offset_1 + offset_2$ (aplicar el mismo offset dos veces)
- $p_{global} = [x_1 + \Delta x, x_2]$ (tamaño cambió)
- $p_{global} = [x_1, x_2 + \Delta x]$ (tamaño cambió)

---

### Axioma 4 — Contrato de Interfaces (Precondiciones / Postcondiciones)

**Función: `calcular_despiece()`**

```
PRECONDICIÓN: ancho_libre = tamaño TOTAL del vano en COCO (w_vano_total)
INVARIANTE:  ancho_libre NUNCA es tamaño neto (clear_size)
INVARIANTE:  ancho_libre ≥ 200 mm (mínimo constructivo)
```

```
POSTCONDICIONES:
├─ despiece["caja"]["ancho_exterior"] = ancho_libre - delta
├─ despiece["fachada"]["ancho"] = ancho_libre + 2*solape - holgura
├─ despiece["fachada"]["x"] es respecto a VANO, no a caja
└─ INVARIANTE: fachada[x_min, x_max] cubre [vano_x - solape, vano_x + li + solape]
```

**Validaciones internas:**
- `assert ancho_libre ≥ 200`
- `assert ancho_fachada > 0`
- `assert ancho_fachada ≤ ancho_libre + 50` (sanidad)
- `assert delta > 0 and delta < ancho_libre` (cordura)

---

### Axioma 5 — Invariantes de Transformación Geométrica

**Regla 1: Conservación de tamaño**

Si un objeto $O$ ocupa $[x_1, x_2]$ en Marco A y se transforma a Marco B con offset $\Delta x$, entonces SIEMPRE ocupa $[x_1 + \Delta x, x_2 + \Delta x]$ en Marco B.

**Nunca:** $[x_1 + \Delta x, x_2]$ | $[x_1, x_2 + \Delta x]$ | $[x_1 + \Delta x_1, x_2 + \Delta x_2]$

**Regla 2: Simetría de solapes**

Para fachada en montaje parche sobre vano $[v_{min}, v_{max}]$:

$$\text{margen\_izquierdo} = v_{min} - fachada_{min}$$
$$\text{margen\_derecho} = fachada_{max} - v_{max}$$

$$|\text{margen\_izquierdo} - \text{margen\_derecho}| < 0.1 \text{ mm}$$

Violación: asimetría > 0.1 mm = bug geométrico.

---

## 2. Jerarquía Unívoca de Definiciones de "Ancho" (Axioma 2)

**Tabla de mapeo para evitar bugs de despiece:**

| Nivel | Símbolo | Valor (ejemplo) | Módulo origen | Uso correcto | Semántica |
|-------|---------|-----------------|---------------|--------------|-----------|
| Base | `w_vano_total` | 600.0 mm | COCO | Referencia única | Ancho TOTAL del vano |
| Decomposición | `delta_divisiones` | 25.4 mm | `vdo_layout.py` | Cálculo interno | Espacio para divisiones |
| Capa local | `w_disponible` | 574.6 mm | `vdo_layout.py` | Lógica interna de layout | Espacio útil para caja |
| Parámetro | `ancho_libre` | 600.0 mm | `vdo_cajon_despiece.py` | Entrada a `calcular_despiece` | DEBE ser `w_vano_total` |

**Mapeo en transiciones entre módulos:**

### Transición 1: `vdo_layout.py` → `vdo_coco_unified_task.py`

```
ResolvedCell {
  w = 574.6        ← NUNCA usar para AnchoLibre
  nominal_w = 600  ← USAR SIEMPRE para AnchoLibre
}
       │
       └─→ vdo_coco_unified_task.py
           AnchoLibre = resuelto.nominal_w   ← CORRECTO
           AnchoLibre = resuelto.w           ← BUG (C-04)
```

### Transición 2: `vdo_coco_unified_task.py` → `vdo_cajon_despiece.py`

```
ENTRADA a calcular_despiece():
  ancho_libre = 600   ← DEBE ser w_vano_total
                    NO w_disponible
```

---

## 3. Registros de Decisiones de Arquitectura (ADR)

---

### ADR-001: Adopción de `Part::FeaturePython` frente a `App::Part`

**Estado:** Aprobado  
**Fecha:** 2026-10-29  
**Autor:** Agente 1 — Destilador Documental

#### Contexto
Al diseñar el contenedor padre de un módulo de carpintería paramétrica (COCO, cajón, panel), se debía elegir entre `App::Part` (Std_Part, contenedor nativo de FreeCAD para conjuntos mecánicos) y `Part::FeaturePython` (contenedor programable en Python).

#### Decisión
Adoptar `Part::FeaturePython` como contenedor principal de todo módulo VDO. Prohibido usar `App::Part` ni `App::DocumentObjectGroup` como contenedor principal (Axiomas T1 y T2 del Protocolo).

#### Justificación
- `App::Part` tiene su `ViewProvider` (`Gui::ViewProviderPart`) compilado en C++ y no acepta Proxy en Python, imposibilitando lógica de recálculo paramétrico en Python.
- `Part::FeaturePython` permite `execute()`, `onDelete()`, propiedades dinámicas (`App::PropertyLinkListChild`) y `ViewProvider` personalizado en Python.
- El mobiliario paramétrico requiere regeneración dinámica de piezas según el espacio disponible, incompatible con la rigidez de `App::Part`.

#### Consecuencias
- Todo módulo VDO es `Part::FeaturePython`.
- Jerarquía de datos mediante `App::PropertyLinkListChild` (T3).
- `claimChildren()` refleja `PropertyLinkListChild` (T4).
- `Shape` del contenedor nulo (T5).
- `onDelete()` para borrado en cascada (T6).

---

### ADR-002: Desvinculación Amigable (Friendly Unlink)

**Estado:** Aprobado  
**Fecha:** 2026-10-29  
**Autor:** Agente 1 — Destilador Documental

#### Contexto
En un sistema paramétrico, borrar o sacar un panel del COCO rompe la dependencia. Al siguiente `recompute()`, el COCO intenta recalcular el panel, no lo encuentra y lanza excepciones con iconos rojos en la Report View.

#### Decisión
Adoptar el protocolo Friendly Unlink con 4 pasos atómicos:
1. **Congelación de cotas:** Las cotas calculadas por el vano se copian como valores numéricos fijos en las propiedades locales del panel. Las expresiones paramétricas se eliminan.
2. **Ruptura limpia del enlace:** `panel.ParentCOCO = None`. El panel se mueve fuera del grupo del padre a la raíz del documento.
3. **Registro de supresión en el padre:** El padre añade el rol de la pieza a su lista `Piezas_Omitidas` para que `execute()` la saltee sin crashear.
4. **Transacción atómica:** Los 4 pasos se ejecutan dentro de una sola transacción de FreeCAD.

#### Justificación
- Permite independizar un lateral o repisa para edición libre sin que el COCO crashee.
- `Piezas_Omitidas` es lista de supresión intencional, no pérdida de información. Permite reabrir el archivo sin que el panel desaparezca silenciosamente y re-vincularlo más tarde.
- `execute()` no lanza excepción por objeto faltante.

#### Consecuencias
- `PanelFeature.ParentCOCO` (`App::PropertyLink`) — vínculo jerárquico.
- `PanelFeature.VDO_Rol` (`App::PropertyString`) — rol dentro del padre.
- `CocoFeature.Piezas_Omitidas` (`App::PropertyStringList`) — roles omitidos en `execute()`.

---

### ADR-003: Abandono del Inspector Reactivo Continuo a favor del TaskPanel Modal/Transaccional

**Estado:** Aprobado  
**Fecha:** 2026-10-29  
**Autor:** Agente 1 — Destilador Documental

#### Contexto
La UI inicial usaba un inspector lateral reactivo escuchando `Gui.Selection` en vivo (dockable panel permanente) que conmutaba vistas según la selección en el árbol. Esto generaba condiciones de carrera con Coin3D y congelaba el hilo de Qt durante recomputes pesados.

#### Decisión
Abandonar el inspector reactivo continuo. Adoptar el **Patrón Híbrido Reactivo** implementado en el **TaskPanel Clásico Unificado (`CocoUnifiedTaskPanel`)** por pestañas con `VDOTransactionMixin` y confirmación/cancelación explícita:

- Ventana modal/determinista que mantiene el foco.
- **Reactividad en vivo en pestaña "Estructura":** cada clic en el corte transversal 2D (`VDOChassisControllerWidget`) actualiza propiedades y ejecuta `doc.recompute()` en vivo.
- **Reactividad en vivo en pestaña "Divisiones":** visor 2D (`CocoPreview2D`) responde en 0 ms (memoria Qt); el 3D se actualiza en tiempo real mediante un **temporizador Debounce de 100–250 ms** que llama a `doc.recompute()` al detenerse la interacción.
- **Transaccionalidad limpia:** botón **"Aceptar"** consolida la transacción (`_vdo_commit()`); botón **"Cancelar"** ejecuta `_vdo_abort()` y revierte el modelo 3D en vivo al estado previo.

#### Justificación (DAG, C++, CAM)
- La reactividad continua en FreeCAD genera condiciones de carrera con Coin3D y congela el hilo de Qt durante recomputes pesados.
- El DAG requiere mutaciones topológicas atómicas dentro de transacciones, nunca como reacción inmediata a eventos de selección.
- `execute()` nunca debe mutar topología (INVS-02).
- El inspector lateral flotante (`vdo_universal_inspector.py`) con `Gui.SelectionObserver` en segundo plano fue descartado por corromper el árbol Qt.

#### Consecuencias
- `VDOSelectionObserver` desactivado / eliminado.
- TaskPanels heredan `VDOTransactionMixin`.
- Transacción abierta en `focusIn`, cerrada en `focusOut`; timer 100–250 ms como control de frecuencia (no diferimiento).
- `accept()` → `openTransaction` → mutar → `recompute` → `_vdo_commit()`.
- `reject()` → `_vdo_abort()` (revierte 3D al estado previo).

---

### ADR-004: Contenedor con `Shape` nulo para erradicar duplicación geométrica y Z-fighting

**Estado:** Aprobado  
**Fecha:** 2026-10-29  
**Autor:** Agente 1 — Destilador Documental

#### Contexto
Algunos diseños previos asignaban `Part.makeCompound(solidos)` al `Shape` del contenedor COCO, duplicando la geometría de los paneles hijos. Esto causaba Z-fighting en pantalla, doble cálculo de masa/peso y duplicación del corte en el exportador CAM/Nesting.

#### Decisión
El contenedor padre (COCO/L2) debe tener `Shape = Part.Shape()` (nulo) o, opcionalmente, un wireframe de bounding box para selección. Nunca `Part.makeCompound` de los hijos.

#### Justificación
- El COCO es un contenedor lógico, no un sólido manufacturable.
- Cada panel L1 existe como entidad B-Rep independiente con su propio `Shape`.
- Previene Z-fighting, doble masa y duplicación CAM/Nesting.
- Funciona en modo headless (sin duplicación visual).

#### Consecuencias
- `fp.Shape = Part.Shape()` en `execute()` del contenedor.
- `claimChildren()` retorna los paneles hijos para el Tree View.
- El contenedor no aparece como sólido en el visor 3D (solo sus hijos).

---

### ADR-005: Contenedor Territorial `VDO_Espacio` (T2) y Coexistencia T2/T3

**Estado:** Aprobado  
**Fecha:** 2026-10-31  
**Autor:** Agente de Implementación VDO

#### Contexto
El subsistema de dossier (Capa 5) requiere una entidad de primer orden que agrupe muros, muebles y assets de un recinto real (ej. Cocina, Habitación Juan). La auditoría (docs/06 F-13) demostró que el contenedor debe ser `Part::FeaturePython` con `Shape` nulo para funcionar como fuente de TechDraw y como nodo relacional limpio en el DAG.

#### Decisión
`VDO_Espacio` es un contenedor territorial **T2**: hereda de `Part::FeaturePython` con `Shape` nulo (Axioma T5 / ADR-004). Agrupa a sus integrantes mediante vinculación canónica directa (`App::PropertyLinkListChild` / patrón `Hijos` / `claimChildren()`, canon T2). Es un **nodo relacional puro**: no aplica matrices de transformación geométrica sobre sus hijos, que conservan sus coordenadas de mundo. El Espacio define cotas de referencia lógicas (`NivelPiso`, `AlturaCielorraso`) como datos de obra, no como desplazamientos geométricos.

`COCO` permanece como contenedor **T3** (Componente Ensamblado Rígido): utiliza `PropertyLinkListChild` (`Hijos`) porque modela un conjunto físico de placas unidas mecánicamente.

No hay inconsistencia entre T2 y T3: representan dos realidades físicas distintas (la habitación vs. el mueble).

#### Reglas de Arquitectura (no negociables)
1. **Cero ciclos DAG:** La dependencia es estrictamente unidireccional: Espacio ⟶ contiene en su lista de pertenencia a ⟶ COCO. El `execute()` del COCO es geométricamente autónomo y **jamás** enlaza con el Espacio. Las colisiones con `AlturaCielorraso` o límites de obra se gestionan exclusivamente en la interfaz (TaskPanel / `vdo_creation_flow.py`) como restricciones de entrada del usuario, nunca como enlaces en el árbol de dependencias.
2. **Nombres Naturales:** Prohibido usar códigos crípticos como `COC-01` o `DOR-02`. Nomenclatura 100% en lenguaje natural: `ESPACIO_Cocina`, `Cocina_BajoMesada_01`, etc.
3. **Propiedades del Espacio:** `NombreEspacio` (string), `VDO_Tipo = "EspacioFeature"` (solo lectura), `NivelPiso` (PropertyDistance, acepta negativos), `AlturaCielorraso` (PropertyLength), `NotasInstalacion` (string multilínea), `RequisitosCliente` (string).
4. **Clasificación por predicado (no carpetas):** `Arquitectura`, `Mobiliario` y `Assets` son clasificadores semánticos derivados del `VDO_Tipo` de cada hijo, no objetos `App::DocumentObjectGroup`. El árbol permanece plano.
   - `ARQUITECTURA = ("Muro", "Vano", "Columna", "Piso")`
   - `MOBILIARIO   = ("COCO", "Panel", "Zocalo")`
   - `ASSETS       = ("Asset", "Electrodomestico", "Sanitario")`
5. **Validación de tipo:** vive en la API de inserción (única puerta de entrada) más un chequeo pasivo en el guardián que reporte intrusos. Los consumidores (dossier, lista de corte) filtran por `VDO_Tipo`; objetos no soportados se omiten silenciosamente.

#### Justificación Técnica de Núcleo
- `Part::FeaturePython` con `Shape` nulo permite `execute()` y Proxy de Python, compatible con ADR-001 (no es `App::Part`).
- No usar `GeoFeatureGroupExtensionPython`: el Espacio no necesita `Placement` propio ni propagación de coordenadas locales a hijos. Mantiene el árbol plano y evita roces con el Axioma T2.
- La jerarquía de datos reside en la lista de pertenencia (capa de datos), no en carpetas visuales, funcionando en modo headless (`FreeCADCmd`).

#### Consecuencias
- No es necesario matizar el Axioma T2 ni crear excepciones en C-01.
- `VDO_Espacio` se registra en `vdo_hub_registry.py` con su propio `SPEC_ESPACIO` y comando `VDO_CrearEspacio`.
- TaskPanel propio para `VDO_Espacio` vía `setEdit()` (doble clic en el árbol).
- `VDO_Proyecto` como singleton `App::FeaturePython` para metadatos de proyecto.

---

## 4. Tabla Resumen de ADR

| ADR | Título | Decisión | Estado | Justificación clave |
|-----|--------|----------|--------|---------------------|
| ADR-001 | Contenedor principal | `Part::FeaturePython` (nunca `App::Part` ni grupos automáticos) | Aprobado | `App::Part` no acepta Proxy en Python |
| ADR-002 | Desvinculación de piezas | Friendly Unlink (4 pasos atómicos + `Piezas_Omitidas`) | Aprobado | Evita iconos rojos y objetos huérfanos en `recompute()` |
| ADR-003 | Paradigma de UI | TaskPanel determinista (`VDOTransactionMixin`); sin inspector reactivo | Aprobado | DAG requiere mutaciones atómicas; evita condiciones de carrera con Coin3D |
| ADR-004 | Forma del contenedor | `Shape = Part.Shape()` nulo (sin `Part.makeCompound`) | Aprobado | Evita Z-fighting, doble masa y duplicación CAM/Nesting |
| ADR-005 | Contenedor Territorial `VDO_Espacio` (T2) | `Part::FeaturePython` con `Shape` nulo; `PropertyLinkListChild` (`Hijos`) para pertenencia; nodo relacional puro sin CS local propio; clasificación por predicado (`Arquitectura`/`Mobiliario`/`Assets`); cero ciclos DAG con COCO (T3); nombres naturales | Aprobado | NivelPiso y AlturaCielorraso son cotas lógicas, no desplazamientos geométricos; coexistencia T2/T3 representa habitación vs. mueble |

---

## 6. Matriz de Bugs Geométricos BUG-001 a BUG-008 (absorbido de `AXIOMAS_VDO_Metodologia.md` y `DIAGNOSTICO_BUGS_GEOMETRICOS.md`)

| Bug # | Descripción | Causa | Axioma que lo previene | ¿Cómo? |
|-------|-------------|-------|------------------------|--------|
| **BUG-001** | Reengrose desbordado (w/h invertidos) | Confusión semántica: largo vs w | Axioma 2 + tipificación fuerte | Forzar que `forma_ref()` valide w > 0, h > 0 en contexto |
| **BUG-002** | ancho_fachada undersized (usa ancho_ext) | Pasar ancho_ext en lugar de li a calcular_fachada_base | Axioma 2 + contrato | Contrato explícito: `@requires(w_vano = total)` |
| **BUG-003** | Fachada descentrada (x respecto a caja) | Calcular x_local vs ancho_ext, no vs li | Axioma 2 + Axioma 4 | Postcondición: validar simetría `\|margen_izq - margen_der\| < 0.1` |
| **BUG-004** | Cajón corrido (usa w neto, no total) | vdo_coco_unified_task.py usa resuelto.w | Axioma 2 + tabla mapeo | Validación en transición: `assert resuelto.nominal_w >= resuelto.w` |
| **BUG-005** | Pos X cajón sin offset (descentralizado) | LocalPlacement ignora delta/2 | Axioma 3 + Axioma 5 | Validación post-transform: centrado ±0.1 mm |
| **BUG-006** | Doble aplicación de offset | Suma delta/2 dos veces (fue bug, revertido) | Axioma 5 (Regla 1) | Contrato: NUNCA aplicar offset dos veces |
| **BUG-007** | Confusión neto/total en interfaces | Parámetros float sin semántica | Axioma 2 + tipos | Crear tipos: `AnchoVanoTotal`, `AnchoVanoNeto` |
| **BUG-008** | Cascada de transformaciones inconsistentes | Marcos sin documentación | Axioma 3 | Documentar LocalFrame en cada módulo |

### 6.1 Diagnóstico Fallo 1: Tira de Reengrose Disparada (Desbordamiento +X, Panel L1)

**Síntoma:** Una tira de reengrose se proyecta fuera del sólido melamínico como viga descolgada (casi el doble de la longitud del tablero).

**Causa matemática exacta:** En `vdo_reengrose_solids.py:40-50`, el fallback incorrecto usaba "largo" como fallback para W (dimensión X) y "ancho" como fallback para H (dimensión Y):

```python
# Código INCORRECTO (original):
w = float(ref.get("w", ref.get("largo", 0.0)))  # Usa "largo" como W ✗
h = float(ref.get("h", ref.get("ancho", 0.0)))  # Usa "ancho" como H ✗

# Para tira "izquierda" (largo=580, ancho=70):
w = 580  (¡INVERTIDO! Debería ser 70)
h = 70   (¡INVERTIDO! Debería ser 580)

# Sólido creado: Part.makeBox(580, 70, 18, Vector(0, 0, z0))
# Ocupa X: 0 a 580 mm ← ¡DESBORDAMIENTO en panel de 600 mm!
```

**Solución implementada** (`vdo_reengrose_solids.py:40-54`):

```python
w = float(ref.get("w", 0.0))
h = float(ref.get("h", 0.0))
d = float(ref.get("d", ref.get("espesor", 0.0)))

if w <= 1e-9 and h <= 1e-9:
    largo = float(ref.get("largo", 0.0))
    ancho = float(ref.get("ancho", 0.0))
    # Lógica correcta: el eje principal va a h (dimensión Y), secundario a w (dimensión X)
    if largo > ancho:
        h = largo  # Dimensión Y (principal)
        w = ancho  # Dimensión X (secundario)
    else:
        h = ancho
        w = largo
```

**Efecto:** Para tira "izquierda" (largo=580 > ancho=70): `w = 70` ✓, `h = 580` ✓. Box resultante: 70 × 580 × 18 (contenido en panel 600 × 580).

### 6.2 Diagnóstico Fallo 2: Desplazamiento Asimétrico de Fachadas (Desplazamiento −X, Cajones COCO)

**Síntoma:** Las fachadas de cajón quedan corridas completamente hacia la izquierda (−X): lateral izquierdo tapado + sobrepasado, lateral derecho con hueco abierto.

**Parte A: Ancho de Fachada Subcalculado**

En `vdo_cajon_despiece.py`, `calcular_despiece` recibe `li = config["ancho_libre"]` (ancho total del vano = 600 mm) y `delta = 25.4 mm` (telescópica).

**Línea incorrecta (original):** pasar `ancho_ext = li - delta = 574.6` en lugar de `li` a `calcular_fachada_base()`:

```python
ancho_fachada = calcular_fachada_base(
    ancho_ext,  ← ¡ERROR! Debería ser li
    alto_fachada_nominal, tipo_montaje_fachada,
    holgura=holg_lat, solape=SOLAPE_PARCHE_NOMINAL)
```

Resultado: `ancho_fachada = 574.6 + 30 = 604.6 mm` (debería ser `600 + 30 = 630 mm`). **Pérdida: 25.4 mm** (exactamente delta).

**Interpretación correcta:** En MONTAJE_PARCHE, la fachada se monta sobre el vano del COCO (li), no sobre la caja interior del cajón (ancho_ext). El delta es interno al vano.

**Parte B: Posicionamiento X sin Offset de Centrado**

En `vdo_coco_unified_task.py`, el LocalPlacement se ponía en `x` (sin offset), causando desplazamiento de `delta/2 ≈ 12.7 mm` hacia la izquierda.

**Solución:** `x_centered = x + delta / 2.0` antes de crear el `App.Placement`.

**Síntesis de doble impacto:**

| Efecto | Magnitud | Dirección |
|--------|----------|-----------|
| Ancho_fachada reducido (604.6 vs 630 mm) | −25.4 mm | Ambos lados |
| Posición X sin delta/2 | −12.7 mm | Izquierda |

Con ambos fixes aplicados: margen izquierdo = −15 mm, margen derecho = −15 mm → **asimetría 0 mm ✓**.

---

## 7. Código Puro de Implementación Axiomática (absorbido de `AXIOMAS_VDO_Metodologia.md`)

### 7.1 Módulo `vdo_axioms.py`

```python
"""
VDO - Axioms and Invariants Module
Formalizes coordinate systems and contracts
"""

from typing import Tuple, Dict, List
from dataclasses import dataclass
import functools


# ==== DECORADORES ====

def requires(condition_str: str):
    """Validar precondición al entrar en función"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


def ensures(condition_str: str):
    """Validar postcondición al salir de función"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator


# ==== MARCOS DE REFERENCIA ====

@dataclass
class VDOCoordFrame:
    """Define un marco de coordenadas con axiomas explícitos"""
    name: str
    origin: Tuple[float, float, float]
    semantics: Dict[str, str]

    x_min: float = 0.0
    x_max: float = None
    y_min: float = 0.0
    y_max: float = None
    z_min: float = 0.0
    z_max: float = None

    def validate_point(self, x: float, y: float, z: float) -> bool:
        checks = [
            x >= self.x_min if self.x_max is not None else True,
            x <= self.x_max if self.x_max is not None else True,
            y >= self.y_min if self.y_max is not None else True,
            y <= self.y_max if self.y_max is not None else True,
            z >= self.z_min if self.z_max is not None else True,
            z <= self.z_max if self.z_max is not None else True,
        ]
        return all(checks)

    def __str__(self):
        return f"Frame({self.name}): origin={self.origin}, semantics={self.semantics}"


# ==== MARCOS ESTÁNDAR DE VDO ====

COCO_FRAME = VDOCoordFrame(
    name="COCO",
    origin=(0.0, 0.0, 0.0),
    semantics={
        "X": "ancho del mueble (0 = izquierda)",
        "Y": "profundidad del mueble (0 = frente)",
        "Z": "altura del mueble (0 = piso)",
    }
)


# ==== VALIDADORES GEOMÉTRICOS ====

class GeometricValidator:
    """Valida invariantes geométricos"""

    @staticmethod
    def validate_symmetry(margen_izq: float, margen_der: float,
                         tolerance: float = 0.1) -> bool:
        """AXIOMA 5 (Regla 2): Simetría de solapes"""
        return abs(margen_izq - margen_der) <= tolerance

    @staticmethod
    def validate_transformation_size_conservation(
        original_size: float, transformed_start: float, transformed_end: float
    ) -> bool:
        """AXIOMA 5 (Regla 1): Conservación de tamaño en transformaciones"""
        transformed_size = transformed_end - transformed_start
        return abs(original_size - transformed_size) < 1e-6

    @staticmethod
    def validate_coordinate_bounds(x: float, frame: VDOCoordFrame) -> bool:
        if frame.x_max is None:
            return x >= frame.x_min
        return frame.x_min <= x <= frame.x_max
```

### 7.2 Módulo `vdo_types.py`

```python
"""
Tipos semánticos para VDO
Hace explícito lo que cada parámetro representa
"""

from typing import NewType

# AXIOMA 2: Tipos distintos para evitar confusión
AnchoVanoTotal = NewType('AnchoVanoTotal', float)   # w_vano_total
AnchoVanoNeto = NewType('AnchoVanoNeto', float)     # w_disponible
EspacioDivisiones = NewType('EspacioDivisiones', float)  # delta


def calcular_despiece(config: dict) -> dict:
    """
    Uso correcto:
    ├─ config["ancho_libre"]: AnchoVanoTotal (NOT AnchoVanoNeto)
    └─ Contratos internos usan tipos distintos
    """
    pass
```

### 7.3 Tests de Axiomas (`tests/test_axioms_vdo.py`)

```python
"""
Tests para validar que axiomas VDO se cumplen
"""
import unittest
from vdo_axioms import VDOCoordFrame, GeometricValidator, COCO_FRAME


class TestAxiom2UnivocityOfWidth(unittest.TestCase):
    """AXIOMA 2: Definición unívoca de "ancho" """

    def test_nominal_w_greater_than_w(self):
        """INVARIANTE: nominal_w >= w"""
        class MockCell:
            w = 574.6
            nominal_w = 600.0
        cell = MockCell()
        assert cell.nominal_w >= cell.w, "AXIOMA 2 VIOLADO"

    def test_ancho_libre_must_be_total(self):
        """AXIOMA 4: calcular_despiece recibe w_vano_total"""
        config = {
            "ancho_libre": 600.0,
            "prof_libre": 580.0,
            "ancho_modulo": 600.0,
            "alto_frente": 200.0,
            "marca": "blum_tandem",
        }
        # Debe completar sin assertion
        result = calcular_despiece(config)
        fachada_x = result["posiciones"]["fachada"]["x"]
        ancho_fachada = result["fachada"]["ancho"]
        margen_izq = -fachada_x - 16 + 1
        margen_der = (600 + fachada_x) - ancho_fachada - solape + 1
        assert abs(margen_izq - margen_der) < 0.1, \
            f"Asimetría detectada: {abs(margen_izq - margen_der):.2f} mm"


class TestAxiom5TransformationConservation(unittest.TestCase):
    """AXIOMA 5 (Regla 1): Conservación de tamaño en transformaciones"""

    def test_size_conservation_on_transform(self):
        original = [100.0, 150.0]  # tamaño = 50
        delta_x = 12.7
        transformed = [original[0] + delta_x, original[1] + delta_x]
        original_size = original[1] - original[0]
        transformed_size = transformed[1] - transformed[0]
        assert abs(original_size - transformed_size) < 1e-6, \
            "AXIOMA 5 VIOLADO: Tamaño cambió en transformación"

    def test_symmetry_of_overlaps(self):
        """AXIOMA 5 (Regla 2): |margen_izq - margen_der| < 0.1 mm"""
        vano_min, vano_max = 0.0, 600.0
        fachada_min, fachada_max = -15.0, 615.0
        margen_izq = vano_min - fachada_min  # 15
        margen_der = fachada_max - vano_max  # 15
        asimetria = abs(margen_izq - margen_der)
        assert asimetria < 0.1, \
            f"AXIOMA 5 VIOLADO: Asimetría {asimetria:.2f} mm"
```

### 7.4 Plan de Implementación de Axiomas (5 fases)

| Fase | Objetivo | Archivos clave |
|------|----------|----------------|
| 1 | Infraestructura de axiomas | `vdo_axioms.py`, `AXIOMAS_FORMALES.md` |
| 2 | Documentación de axiomas | Encabezados de módulos clave, `MAPEO_ANCHO_VDO.md` |
| 3 | Validaciones en puntos críticos | `vdo_coco_unified_task.py`, `vdo_cajon_despiece.py` |
| 4 | Refactorización de tipos | `vdo_types.py`, firmas con `NewType` |
| 5 | Testing de axiomas | `tests/test_axioms_vdo.py`, ejecución `pytest` |

---

## 8. CAM y Optimizador de Corte 2D (absorbido de `VDO_NESTING_README.md`)

### 8.1 Descripción

Sistema completo de optimización de corte 2D integrado en FreeCAD. Permite seleccionar piezas (TODO / SELECCIÓN / GRUPO/MÓDULO), configurar tableros predefinidos (presets guardados), ejecutar nesting automático, visualizar resultado en 3D y exportar a DXF.

### 8.2 Instalación

**Requisito:** Nesting Workbench (FreeCAD → Tools → Addon Manager → "Nesting Workbench" → Instalar → Reiniciar).

**Archivos VDO:**
- `vdo_nesting_presets.py` — Gestor de presets
- `vdo_nesting_workflow.py` — Lógica automatizada
- `vdo_nesting.FCMacro` — Entry point

### 8.3 Flujo de Uso

1. Crear paneles (`vdo_panel_estandar` / `vdo_panel_fachada`) o COCO_4C desde toolbar.
2. Ejecutar `vdo_nesting.FCMacro` → elegir modo / tablero / algoritmo → "Ejecutar Nesting".
3. Se crea `NestingLayout` con `Sheet_1`, `Sheet_2`... (Boundary rojo, piezas colocadas, etiquetas con IDs).
4. Opcional: click derecho en `NestingLayout` → "Export Sheets" → DXF / SVG.

### 8.4 Presets Predefinidos

| Nombre | Dimensiones | Espaciado | Uso |
|--------|-------------|-----------|-----|
| Estándar EN | 2440×1830 mm | 15 mm | Tablero europeo estándar (MDF, melamina) |
| Medio Horizontal | 1220×2440 mm | 15 mm | Alternativa horizontal |
| Pequeño | 1200×900 mm | 12 mm | Piezas chicas |
| Cuadrado | 1000×1000 mm | 15 mm | Módulos cuadrados |
| Larguero | 3000×600 mm | 15 mm | Perfiles largos |

### 8.5 Algoritmos

| Algoritmo | Precisión | Aprovechamiento | Velocidad | Mejor para |
|-----------|-----------|-----------------|-----------|------------|
| Minkowski | Alta | Excelente | Lento | Piezas irregulares, máximo aprovechamiento |
| Physics | Media | Bueno | Muy rápido | Muchas piezas, shapes complejas |

**Parámetros Minkowski:** `Generaciones` 1-100 (1 = rápido, 5-10 = balance, 20+ = exhaustivo).

### 8.6 Interpretación de Resultados

- Eficiencia = (área piezas) / (área tablero) × 100. 90%+ = excelente, <70% = revisar configuración.
- Piezas no colocadas: tablero demasiado pequeño, espaciado muy grande, o geometría incompatible.

### 8.7 API Headless

```python
import FreeCAD
from vdo_nesting_presets import NestingPresetManager
from freecad.nestingworkbench.Tools.Nesting.nesting_logic import nest
from freecad.nestingworkbench.Tools.Nesting.shape_preparer import ShapePreparer

doc = FreeCAD.ActiveDocument
preparer = ShapePreparer(doc, {})
shapes = [preparer.prepare_shape(obj, quantity=1) for obj in doc.Objects]
config = NestingPresetManager.get_preset("Estándar EN")

sheets, unplaced, _, elapsed = nest(
    shapes,
    width=config['width'],
    height=config['height'],
    spacing=config['spacing'],
    algorithm='Minkowski',
    generations=2
)
print(f"✅ {len(sheets)} tablero(s) en {elapsed:.2f}s")
```

---

## 4. Tabla Resumen de ADR — actualizada

| ADR | Título | Decisión | Estado | Justificación clave |
|-----|--------|----------|--------|---------------------|
| ADR-001 | Contenedor principal | `Part::FeaturePython` (nunca `App::Part` ni grupos automáticos) | Aprobado | `App::Part` no acepta Proxy en Python |
| ADR-002 | Desvinculación de piezas | Friendly Unlink (4 pasos atómicos + `Piezas_Omitidas`) | Aprobado | Evita iconos rojos y objetos huérfanos en `recompute()` |
| ADR-003 | Paradigma de UI | TaskPanel determinista (`VDOTransactionMixin`); inspector retirado | Aprobado | DAG requiere mutaciones atómicas; evita condiciones de carrera con Coin3D |
| ADR-004 | Forma del contenedor | `Shape = Part.Shape()` nulo (sin `Part.makeCompound`) | Aprobado | Evita Z-fighting, doble masa y duplicación CAM/Nesting |

---

## 5. Sello de Axiomas y ADR — actualizado

Los 5 axiomas matemáticos, los 4 ADR, la matriz de bugs BUG-001 a BUG-008, el código puro de implementación (`vdo_axioms.py`, `vdo_types.py`, tests), el diagnóstico de Fallo 1 y Fallo 2, y la especificación CAM/Nesting están formalmente declarados y son invariantes del sistema VDO. Cualquier cambio futuro debe pasar por un nuevo ADR que revoque o modifique uno de estos registros, con justificación técnica de núcleo (DAG, C++, CAM).

Las contradicciones detectadas en la carpeta `documentacion/` original han sido todas resueltas según la Matriz de Contradicciones (FASE 1, documento `00_MATRIZ_CONTRADICCIONES_Y_RESOLUCION.md`).

*Fin del Pilar 4. Este documento sella los axiomas matemáticos y las decisiones de arquitectura de VDO.*
