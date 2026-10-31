# 01 — Lógica de Negocio y Carpintería (Pilar 1)

**Sistema:** VDO (Veta de Oro) — FreeCAD 1.1+
**Capa:** 0 (BIM Muros) y lógica de taller pura (agnóstica a CAD)
**Estado:** Definitivo — sin placeholders

---

## 1. Jerarquía Física de Fabricación

El mueble se descompone en una jerarquía estricta de seis niveles, del espacio al tablero físico. Cada nivel tiene un rol inequívoco y no se solapa con el siguiente.

### C0 — Espacio / Recinto
El contexto arquitectónico. Muros, piso, aberturas, puntos de circulación y vistas. **No escribe geometría de piezas.** Define direcciones de uso (un mueble puede tener dos frentes si es una isla). Es el contenedor de colocación (instancia + pose global).

### L3 — Módulo Compuesto (Escritorio / Alacena / Centro de TV)
Composición de técnicas (L2). Define el frente funcional y las fachadas, pero no los lados vistos (eso es C2). Ejemplo: un escritorio en L se modela como matriz de COCOs + paneles L1 posicionados relativamente.

### L2 — Módulo Esencia / COCO / Pacha
Técnica constructiva local: carcasa (COCO), pacha, entamborado, cajón externo, puerta parche. Conoce sus piezas, uniones, herrajes y su frente local. **No conoce muros ni orientación global.** Es el contenedor paramétrico (`Part::FeaturePython`, `Shape` nulo) que agrupa los paneles L1 mediante `App::PropertyLinkListChild`.

### L0 — Vano Libre
Cavidad útil libre dentro del COCO. Cotas netas útiles (X libre, Y libre, Z libre). Selector de habitante: vacío, subdividir (repisas/montantes), cajón o puerta. El vano no es una pieza física; es un volumen de referencia para el despiece de lo que lo habita.

### H — Habitante / Herraje
Elemento que ocupa un vano: cajón, puerta, repisa, división. Puede traer herrajes asociados (correderas, cazoletas, bisagras). Los herrajes tienen catálogo propio con cotas CAD automáticas.

### L1 — Pieza Física / Tablero
Unidad mínima de manufactura. Rectángulo de melamina ($L \times A \times E$) con 4 cantos cardinales (Norte, Sur, Este, Oeste). **No sabe si es "fachada", "lateral" ni si está vista.** Esa semántica vive en el diccionario semántico (datos puros), no en el motor geométrico.

### Flujo de contención

```
C0 (Espacio/Habitación)
  └── L3 (Módulo Compuesto: Escritorio, Alacena)
        └── L2 (Módulo Esencia/COCO/Pacha)  ← Part::FeaturePython, Shape nulo
              └── L0 (Vano Libre)            ← volumen de referencia, no pieza
                    ├── H (Habitante/Herraje) ← cajón, puerta, repisa
                    │     └── L1 (Pieza Física) ← tablero con 4 cantos
                    └── L1 (Pieza Física)      ← lateral, base, techo, fondo
```

**Invariante de jerarquía:** Un objeto de nivel $N$ nunca contiene directamente un objeto de nivel $N-2$. Siempre pasa por el nivel intermedio. Un cajón (H) contiene paneles L1, pero el COCO (L2) no contiene directamente los paneles del cajón; los contiene a través del cajón.

---

## 2. Principio de Equivalencia Física de la Melamina

**Axioma:** En una seccionadora industrial no existen "puertas", "zócalos", "repisas" ni "fachadas". Solo existen **rectángulos de melamina con 4 cantos**.

Toda entidad física del sistema se traduce en un tablero rectangular:

| Dimensión | Símbolo | Significado |
|-----------|---------|-------------|
| Largo | $L$ | Dimensión principal del tablero (eje de veta típico) |
| Ancho | $A$ | Dimensión secundaria del tablero |
| Espesor | $E$ | Grosor del tablero (15 / 18 / 36 mm típico) |

Cada tablero tiene exactamente 4 cantos cardinales:

| Canto | Símbolo | Ubicación en marco local del tablero |
|-------|---------|--------------------------------------|
| Norte | $N$ | Borde superior (local Y máxima) |
| Sur | $S$ | Borde inferior (local Y mínima) |
| Este | $E$ | Borde derecho (local X máxima) |
| Oeste | $O$ | Borde izquierdo (local X mínima) |

**Tipos de canto (política de taller):**

| Código | Nombre | Aplicación típica |
|--------|--------|-------------------|
| `RIG` | Canto rígido (grueso, ej. 2 mm ABS) | Bordes exteriores vistos, frentes de fachada |
| `FX` | Canto fino / delgado (ej. 0.45 mm) | Uniones internas, bordes en ranura, no vistos |
| `SMRG` | Canto semirrígido / medio | Casos intermedios según tabla de material × espesor |

**Invariante:** Cada cara del tablero tiene 4 bordes y cada borde tiene exactamente un tipo de canto asignado. Un borde no puede estar sin canto definido (default `FX` si no se especifica `RIG`).

---

## 3. Reglas de Taller

### 3.1 Política de Cantos

| Contexto | Canto por defecto | Justificación |
|----------|-------------------|---------------|
| Panel estándar | Selectivos (solo los bordes que lo requieran) | Flexibilidad de usuario |
| Fachada | `RIG` × 4 (todos los bordes) | Frente visible, necesita acabado grueso |
| COCO con exposición | `RIG` solo en bordes exteriores vistos; `FX` en uniones | `vdo_finish` cruza `VDO_Lados_Vistos` + rol de pieza |
| Reengrose independiente | Tira aparte con canto perimetral | Cada pieza se cantea individualmente |
| Reengrose pacha | Piezas individuales en `FX`; `cantos_bloque` en `RIG` | Bloque encolado se cantea como unidad |

**Regla de acabado por borde, no por cara:** Una cara vista no implica cantear todos sus bordes. El plan depende de la unión concreta (un borde en ranura no se cantea aunque la cara sea visible).

### 3.2 Fondo (Respaldo) — Ranurado vs. Atornillado

| Condición | Comportamiento | Umbral |
|-----------|----------------|--------|
| `fondo = False` | No existe en el modelo | — |
| `calibre ≤ 8 mm` | Fondo delgado ranurado en laterales, base y techo; posición `Y = fondo − calibre − profundidad_ranura` | **Umbral: 8 mm** |
| `calibre > 8 mm` | Fondo grueso sin ranura, retranqueado desde el fondo con `distancia_borde` | **Umbral: 8 mm** |

**Fórmula del fondo delgado:**
- $f_y = \text{fondo} - \text{calibre\_fondo} - \text{profundidad\_ranura}$
- El fondo nunca se coloca en $Y=0$ (frente funcional).
- Las divisiones terminan en la cara frontal del fondo ($f_y$), no lo atraviesan.

### 3.3 Estructura — Tapa y Base

| Tapa | Base | Resultado |
|------|------|-----------|
| `externo` | `interno` | Tapa cubre laterales; base cabe entre ellos |
| `externo` | `externo` | Ambos cubren laterales |
| `interno` | `interno` | Ambos caben entre laterales |
| `interno` | `externo` | Tapa cabe; base cubre laterales |

### 3.4 Sobremedida para Canteado Propio vs. Medida Terminada para Proveedor

| Origen de la pieza | Criterio de cotas |
|--------------------|-------------------|
| **Canteado propio (taller)** | Cotas netas de corte; el canto se aplica después y consume espesor en el borde. |
| **Proveedor (melamina precanteada)** | Cotas terminadas (ya incluyen el espesor del canto en la medida final). |

**Invariante:** Nunca se mezclan cotas netas con cotas terminadas en el mismo despiece. El manifiesto del taller declara qué política rige cada hoja/material.

---

## 4. Diccionario Semántico Oficial

El diccionario semántico mapea **semántica de mobiliario → propiedades físicas inmutables**. Es datos puros; el motor geométrico (`vdo_panel_core.py`) es agnóstico y no acopla reglas por tipo de pieza.

| Pieza (semántica) | Canto inmutable | Material inamovible | Orientación | Estado |
|-------------------|-----------------|---------------------|-------------|--------|
| Panel Estándar | libre | libre | libre | existente |
| Panel Fachada | `RIG` × 4 | `fachadas` | libre | existente |
| Panel División | libre | libre | vertical (por naturaleza) | existente |
| Lateral (COCO) | libre | libre | vertical | existente |
| Base (COCO) | libre | libre | horizontal | existente |
| Techo (COCO) | libre | libre | horizontal | existente |
| Fondo / Respaldo (COCO) | libre | libre | horizontal | existente |
| División interna (COCO) | libre | libre | vertical / horizontal | existente |
| Cajón — Lateral Izq/Der | libre | libre | vertical | existente |
| Cajón — Contrafrente | libre | libre | vertical | existente |
| Cajón — Frente interior | libre | libre | vertical | existente |
| Cajón — Piso | libre | libre | horizontal | existente |
| Cajón — Fachada | `RIG` × 4 | `fachadas` | vertical | existente |
| Zócalo | libre | libre | horizontal | existente |
| Tambor | libre | libre | vertical | existente |

**Regla de llenado (del diccionario fuente):**
1. Una fila por pieza semántica (no por objeto FreeCAD).
2. En "Propiedades físicas inmutables" anotar solo lo que **no puede variar** para que la pieza siga siendo "esa pieza" (ej. `fachada` → canto `RIG` × 4 + material `fachadas`).
3. Lo que quede libre (orientación, cantos, material) se deja en "libre".
4. No acoplar nada al motor hasta que una fila esté cerrada y validada.

**Promoción:** Cuando el diccionario madure, se promoverá a datos puros en `vdo_manifest.json` → sección `semantica`, para que el motor lo lea como datos sin acoplar reglas en código.

---

## 5. Marco Local Único (Contrato Geométrico)

Contrato obligatorio para todas las capas (de `Arquitectura de capas espacios a modulos.txt` y `CONTEXTO_TECNICO_VDO.md`):

| Eje | Dirección | Significado |
|-----|-----------|-------------|
| $+X$ | Derecha | Ancho del mueble / tablero |
| $+Y$ | Fondo | Profundidad del mueble / tablero |
| $+Z$ | Arriba | Altura del mueble / tablero |
| Frente funcional | $Y−$ | Lado por el que se abre/usa el mueble |

**Invariantes:**
- Origen del COCO: $(0,0,0)$ = esquina frontal-inferior-izquierda exterior del mueble.
- No hay coordenadas negativas en el marco COCO_Frame.
- El preview 2D siempre dibuja el frente local con etiqueta `FRENTE (Y−)` y ejes $X \rightarrow$, $Y \uparrow$.
- Si el mueble se rota 180° en el espacio, el preview sigue siendo local; la orientación global pertenece a C1/3D, no se mezcla con la edición.

**Seis lados de módulo:** `frente`, `fondo`, `izquierda`, `derecha`, `superior`, `inferior`.

---

## 6. Glosario de Términos (Vocabulario Controlado)

| Término | Definición canónica | Término prohibido (reemplazar por) |
|---------|---------------------|------------------------------------|
| Ancho total del vano | $w_{vano\_total} = X_{max} - X_{min}$ del rectángulo del vano en COCO_Frame | `ancho_total`, `w_total` (sin contexto) |
| Ancho neto disponible | $w_{disponible} = w_{vano\_total} - delta_{divisiones}$ | `w` (ambiguo), `clear_size` |
| Ancho libre (parámetro) | `ancho_libre := w_{vano\_total}` (siempre total, nunca neto) | `ancho_libre` interpretado como neto |
| Espacio de divisiones | $delta_{divisiones} = w_{vano\_total} - w_{disponible} \ge 0$ | — |
| Canto rígido | `RIG` (grueso, ej. 2 mm) | `canto grueso` (regionalismo) |
| Canto fino | `FX` (delgado, ej. 0.45 mm) | `canto delgado` |
| Luz perimetral | Borde libre alrededor de una pieza | `calle libre` (anglicismo) |
| Marco interior | Unión donde una tira topea contra otra | `confinado`, `empotrado` |
| De punta a punta | Tira que pasa por encima de otra (dominante) | `pasante` |
| Rebaje / cajeado en escuadra | Mocheo de esquina en 90° | `mocheo crudo` |
| Separación del canto | Distancia del borde al inicio del canteado | `retranqueo` |
| Frente funcional | Lado por el que se abre/usa el mueble ($Y−$) | — |
| Lados vistos | Caras exteriores visibles desde el espacio (contextual, C2) | — |
| Lados apoyados | Caras contra muro/piso (contextual, C2) | — |

---

## 8. Dos Ejes Ortogonales: Composición y Contexto (absorbido de `Arquitectura de capas espacios a modulos.txt`)

El mueble no se organiza en una sola escalera lineal, sino en dos ejes ortogonales que se cruzan en una política de acabados:

| COMPOSICIÓN | CONTEXTO |
|-------------|----------|
| **L1 — Pieza física:** Contrato físico puro: largo, ancho, espesor, material, veta, cantos por lado. No sabe si es "fachada", "lateral" ni si está vista. | **C0 — Espacio:** Muros, piso, aberturas, circulación y puntos de vista. No tiene un único "frente"; una isla o divisor pueden tener dos. Define direcciones de uso, no geometría de piezas. |
| **L2 — Técnica:** Ensamblaje local: coco, pacha, entamborado, cajón externo, puerta parche. Conoce sus piezas, uniones, herrajes y su frente local. No conoce muros ni orientación global. | **C1 — Instancia:** Módulo + pose. Transforma el frente local al frente global. Aquí se resuelve "este mueble mira hacia el pasillo". |
| **L3 — Módulo funcional:** Composición de técnicas: escritorios, archivador, alacena. Define el frente funcional y las fachadas, pero no los lados vistos (eso es C2). | **C2 — Exposición:** Calcula `lados_vistos` y `lados_apoyados`. No modifica geometría: emite un plan de acabados que dice qué cantos/fachadas corresponden. |

**Clave axiomática:** L1/L2/L3 no conocen "visto"; C0/C1/C2 no escriben geometría. Sólo se cruzan en una política de acabados. Así no se complejizan las capas inferiores.

### 8.1 Tres conceptos separados: Frente Funcional, Lados Vistos, Fachada

Hay que separar tres conceptos que hoy se mezclan:

1. **Frente funcional:** lado por el que se abre/usa el mueble. Es intrínseco al módulo (pertenece a L2/L3).
2. **Lados vistos:** caras exteriores visibles desde el espacio. Es contextual (pertenece a C2).
3. **Fachada:** puerta/panel funcional. No es lo mismo que "lado visto": un divisor puede tener el fondo visto y no llevar fachada al fondo.

**Seis lados de módulo:** `frente`, `fondo`, `izquierda`, `derecha`, `superior`, `inferior`.

**Casos de uso:**
- **Caso 98%:** vistos = [`frente`], apoyados = [`fondo`] o [`fondo`, `izquierda`].
- **Divisor de ambientes:** vistos = [`frente`, `fondo`], sin fachada al fondo pero con cantos vistos en ambos frentes.
- **Mueble contra muro con lateral derecho expuesto:** vistos = [`frente`, `derecha`].

Los cantos se resuelven a nivel de borde de pieza, no de "cara completa". La política debe saber qué bordes de cada pieza dan al exterior y cuáles quedan en unión con otra pieza.

---

## 9. Diccionario Semántico: Reglas de Llenado y Notas Pendientes (absorbido de `vdo_diccionario_semantico.md`)

### 9.1 Reglas de llenado

1. Una fila por **pieza semántica** (no por objeto FreeCAD).
2. En "Propiedades físicas inmutables" se anota SOLO lo que **no puede variar** para que la pieza siga siendo "esa pieza" (ej. `fachada` → canto `RIG` × 4 + material `fachadas`).
3. Lo que quede libre (orientación, cantos, material) se deja en "libre".
4. **No** acoplar nada al motor hasta que una fila esté cerrada y validada.

### 9.2 Notas y decisiones pendientes

- La única semilla semántica conocida hoy es **fachada** = canto rígido ×4 + material `fachadas`. Está anotada pero **aún NO acoplada en el motor** (correcto según Axioma 5 de separación semántica/física).
- La "división" y el "lateral" comparten física (panel vertical); su diferencia es únicamente semántica/posición, no de reglas del motor.
- Cuando exista una taxonomía de materiales ("fachadas", "cajas", "estructura"...), se referenciará aquí desde `vdo_manifest.json → materiales`.
- **Promoción:** Cuando el diccionario madure, se promoverá a datos puros en `vdo_manifest.json → sección semantica`, para que el motor lo lea como datos sin acoplar reglas en código.

---

## 7. Invariantes de Negocio (Resumen Ejecutivo) — ya presente, se mantiene.

--- 

*Fin del Pilar 1. Este documento es la fuente canónica de lógica de negocio y reglas de taller para VDO. Cualquier cambio debe reflejarse aquí antes de implementarse en código.*

*Fin del Pilar 1. Este documento es la fuente canónica de lógica de negocio y reglas de taller para VDO. Cualquier cambio debe reflejarse aquí antes de implementarse en código.*
