# 07 — Contraplan Fase 0 & Fase 1 (Núcleo VDO)

**Fecha:** 2026-10-30
**Sustituye a:** «Especificación técnica del núcleo VDO (Fase 0 & Fase 1)»
**Base:** `docs/06_AUDITORIA_PLAN_FASE0_FASE1.md` (22 hallazgos, verificados en FreeCAD 1.1.4)
**Canon aplicable:** Axiomas T1/T2/T5 (`docs/02`), C-01/C-02/C-06/C-07 (`docs/00`), INVS §1.4/§1.6/§3.1/§3.2/§3.5 (`docs/03`), ADR-001 (`docs/04`)

---

## 1. Qué se conserva del plan original

El plan acertó en lo estructural, y eso no se toca:

- **La secuencia de 5 pasos**: arranque → ESPACIO → plantilla → proyección → test mínimo. El orden es correcto y las dependencias son reales.
- **La idea del test mínimo (1 muro + 1 COCO)** como criterio de cierre de fase. Es la decisión más acertada del plan: un escenario pequeño que atraviesa todas las capas.
- **No duplicar funcionalidad C++** (§1.2). El principio es bueno; lo que estaba mal era cómo se verificaba.
- **El motor de dibujo desacoplado** (§3.1) y la exigencia de **escalas normalizadas** (§3.3). Ambos legítimos —y la segunda, necesaria: medido, `ScaleType="Automatic"` devuelve 1:4 y 1:8, que no existen en un escalímetro de taller.
- **Las tres familias de toolbar** y el `VDO_Tipo` como discriminante de filtrado rápido.

## 2. Qué cambia

| # | Del plan | Al contraplan | Por |
|---|----------|---------------|-----|
| 1 | Forzar el visor 3D / cerrar la pestaña de inicio | `newDocument()` crea el visor; detectar con `mdiViewsOfType`, crear con `createView` | F-1 |
| 2 | Verificar dependencias y abortar `Initialize()` | `package.xml` + import perezoso + `IsActive()` | F-4, F-5, F-6 |
| 3 | `App::DocumentObjectGroupPython` | `Part::FeaturePython` (+ extensión; ver **D-1**) | F-13, F-2 |
| 4 | 3 sub-carpetas `DocumentObjectGroup` «protegidas» | 1 lista de pertenencia + clasificación **por predicado** sobre `VDO_Tipo` | F-2, F-16 |
| 5 | `NivelPiso` como `PropertyLength` | `App::PropertyDistance` | F-14 |
| 6 | `doc.VDO_Proyecto` | objeto singleton `VDO_Proyecto` (ver **D-2**) | F-15 |
| 7 | Auto-escala desde el BBox 3D | `ScaleType="Automatic"` → leer `Scale` → normalizar hacia abajo | F-17 |
| 8 | Membrete con claves inventadas | contrato explícito de claves `freecad:editable` | F-8 |
| 9 | Checklist de 6 ítems en GUI | + **dossier generado en `FreeCADCmd`** como ítem bloqueante | F-21 |
| 10 | `vdo_space_core` | `VDO/cad/objects/vdo_cad_espacio.py` → `VDO_Espacio` | F-11 |

---

## 3. Decisiones previas

**Estado: D-1 y D-3 decididas el 2026-10-30. D-2 en firme por recomendación (sin objeción).**

| Decisión | Resultado |
|----------|-----------|
| **D-1** Contenedor del ESPACIO | **Opción A** — `Part::FeaturePython` con `Shape` nulo (T5/ADR-004); `PropertyLinkListChild` (`Hijos`) para pertenencia; nodo relacional puro sin `GeoFeatureGroupExtensionPython`; sin CS local propio |
| **D-2** Metadatos de proyecto | Singleton `VDO_Proyecto` (`App::FeaturePython`), espejo opcional a `doc.Meta` |
| **D-3** Escalas normalizadas | `1:1 1:2 1:5 1:10 1:20 1:25 1:50 1:100` — **1:15 fuera**, 1:25 dentro |

E-2 queda desbloqueado. La decisión D-1 (Opción A) cumple T2 y C-01 sin excepciones, por lo que no es necesario redactar un ADR matizador antes de tocar código.

### D-1 · Contenedor del ESPACIO y sistema de coordenadas local — **DECIDIDA: A**

El problema medido: `Part::FeaturePython` + enlaces **no propaga `Placement`** (hijo se queda en 0,0,0 al mover el padre a x=1000). El Espacio VDO **no necesita** un sistema de coordenadas local propio: `NivelPiso` y `AlturaCielorraso` son cotas de referencia lógicas (datos de obra), no desplazamientos geométricos que muevan a los hijos. Cada objeto hijo conserva sus coordenadas de mundo.

| Opción | Qué es | CS local | ADR-001 | T2 | Veredicto |
|--------|--------|----------|---------|-----|-----------|
| **A** | **`Part::FeaturePython` + `PropertyLinkListChild` (`Hijos`), `Shape` nulo** | No (no necesario: cotas lógicas) | ✔ cumple | ✔ cumple | **Recomendada** |
| B | `Part::FeaturePython` + `GeoFeatureGroupExtensionPython` | Sí, real | ✔ cumple | ⚠ añade `Group` | Descartada (roce con T2/C-01) |
| C | `App::DocumentObjectGroupPython` | **Imposible**: sin `Placement` ni `Shape` | ✘ viola T1 | ✘ | Descartada |

**Decidido: A para el ESPACIO.** Los módulos internos (COCO, cajón, panel) ya usan `Part::FeaturePython` + `PropertyLinkListChild` y funcionan así.

El Espacio se implementa como un nodo relacional puro: agrupa elementos mediante la lista de pertenencia canónica, sin aplicar matrices de transformación sobre ellos. Esto mantiene el árbol plano, sin carpetas visuales automáticas, y evita cualquier excepción al Axioma T2 o a C-01.

**Clasificación por predicado (no carpetas):** `Arquitectura`, `Mobiliario` y `Assets` son filtros semánticos sobre `VDO_Tipo` de cada hijo, no objetos `App::DocumentObjectGroup`.

### D-2 · Dónde viven los metadatos de proyecto — **en firme por recomendación**

`App.ActiveDocument.VDO_Proyecto` es inejecutable (medido: `AttributeError`; `App::Document` no acepta propiedades dinámicas).

| Opción | Pros | Contras |
|--------|------|---------|
| **Singleton `VDO_Proyecto` (`App::FeaturePython`)** — recomendada | propiedades tipadas; visible y editable en el árbol; **participa del DAG**, así que las hojas se recomputan al cambiar el nombre del proyecto | un objeto más en el documento |
| `doc.Meta` (dict, medido funcionando) | cero objetos; nativo | sólo strings; invisible al usuario; fuera del DAG (cambiarlo no recomputa nada) |

**Decidido** (recomendación sin objeción; reversible mientras no exista el objeto): singleton `VDO_Proyecto` como fuente de verdad, y espejo opcional a `doc.Meta` para los campos de archivo (cliente, autor) que interesan a herramientas externas. Igual que `EditableTexts`, `doc.Meta` exige reasignar el diccionario completo.

### D-3 · Conjunto de escalas normalizadas — **DECIDIDA**

**1:15 fuera** (no pertenece a la serie ISO 5455; no se mide con escalímetro). **1:25 dentro** (no ISO, pero presente en escalímetros de arquitectura; cubre el salto 1:20→1:50, grande para muebles altos). Conjunto definitivo:

```
1:1   1:2   1:5   1:10   1:20   1:25   1:50   1:100
1.0   0.5   0.2   0.1    0.05   0.04   0.02   0.01
```

Ya aplicado en `tools/vdo_verify_fase1_techdraw.py`.

---

## 4. Entregables

### E-0 · Saneamiento del arranque *(Fase 0)*

**Objetivo:** que activar el workbench nunca deje la interfaz en un estado muerto, y que el arranque no pueda romper FreeCAD.

**Contrato:**
- `Activated()`: si `App.GuiUp` y hay documento sin vista 3D → `createView("Gui::View3DInventor")`. Sin documento, no hacer nada.
- `Initialize()`: sólo registrar. **Nada de validar dependencias ni abortar.** Imports pesados fuera.
- Cada comando: `import` perezoso en `Activated()`; `IsActive()` devuelve `False` sin documento o sin prerrequisito.
- `Gui.Snapper`: `hasattr` y, si falta, `Gui.activateWorkbench("BIMWorkbench")`. Todo bajo `App.GuiUp`.
- Mantener el patrón de `InitGui.py` → `VDO/vdo_initgui.py` (trampa de `exec()` ya resuelta; no tocar).

**Criterio de aceptación:**
1. Activar VDO sin documento: cero trazas de error en el panel de informes; sólo el botón «Nuevo proyecto VDO» activo.
2. Con documento abierto y pestaña de inicio en primer plano: la vista 3D del documento queda enfocada.
3. `FreeCADCmd -c "import VDO"` no importa `FreeCADGui` (test de agnosticidad, ya existe el patrón en `tests/test_vdo_agnosticism.py`).

**Fuera de alcance:** cualquier cambio de toolbar que no sea el registro de las 3 familias.

### E-1 · ADR-002 y contrato de datos *(documentación, sin código)*

**Objetivo:** cerrar D-1, D-2 y D-3 por escrito antes de escribir el objeto.

**Entrega:** ADR-002 en `docs/04_DECISIONES_ADR_Y_AXIOMAS.md` con la decisión de contenedor, el matiz de T2 si se elige B, y la tabla de propiedades de E-2 como contrato.

**Criterio de aceptación:** `docs/00_MATRIZ_CONTRADICCIONES_Y_RESOLUCION.md` actualizada: si se elige B, la fila C-01 debe reflejar la distinción «carpeta visual» vs «contenedor con CS».

### E-2 · `VDO_Espacio`

**Fichero:** `VDO/cad/objects/vdo_cad_espacio.py`. (Y renombrar el actual `vdo_cad_space.py` → `vdo_cad_divisiones.py`, que es lo que hace.)

**Esquema de propiedades corregido:**

| Propiedad | Tipo | Grupo | Cambio vs plan |
|-----------|------|-------|----------------|
| `NombreEspacio` | `App::PropertyString` | Identificación | — |
| `CodigoZona` | `App::PropertyString` | Identificación | — |
| `NivelPiso` | **`App::PropertyDistance`** | Cotas de obra | **F-14**: `PropertyLength` clampa −150 → 0 en silencio |
| `AlturaCielorraso` | `App::PropertyLength` | Cotas de obra | correcto (siempre > 0) |
| `NotasInstalacion` | `App::PropertyString` | Documentación | válido: medido, conserva `\n`. El editor de propiedades es de una línea → editar desde el TaskPanel con un `QTextEdit` |
| `VDO_Tipo` | `App::PropertyString`, **sólo lectura** | Sistema | **F-23**: unificar con el `VDO_Tipo` del COCO (no `VDO_Type`); `setEditorMode(…, 1)` + espejo en `obj.Proxy.Type` |
| `VDO_Modulo` | `App::PropertyString` | Sistema | testigo de tipo, clave `"espacio"` |
| `Hijos` | `App::PropertyLinkListChild` | Estructura Lógica | pertenencia canónica (T2) |

**Estructura interna — las tres «subcarpetas» desaparecen como objetos.** Sustitución:

- **Pertenencia:** una sola lista, `Hijos` (`App::PropertyLinkListChild`, canon T2). Es la única fuente de verdad de pertenencia. Los módulos internos (COCO) siguen con el mismo patrón (`vdo_cad_coco.py:154`), sin cambios.
- **Clasificación:** *predicado*, no contenedor. `Arquitectura`, `Mobiliario` y `Assets` son **filtros** sobre la lista de pertenencia, derivados del `VDO_Tipo` de cada hijo.

```python
ARQUITECTURA = ("Muro", "Vano", "Columna", "Piso")
MOBILIARIO   = ("COCO", "Panel", "Zocalo")
ASSETS       = ("Asset", "Electrodomestico", "Sanitario")

def hijos_por_familia(espacio, familia):
    return [o for o in list(getattr(espacio, "Hijos", None) or [])
            if getattr(o, "VDO_Tipo", "") in familia]
```

Por qué esto es mejor que tres carpetas, aparte de cumplir T2:

1. **Una sola fuente de verdad de pertenencia.** Con tres listas o tres carpetas, un objeto puede estar en dos, o en ninguna, y nada lo detecta.
2. **Evita la doble reclamación en el árbol** (estar en `Group` y además en una `LinkListChild`).
3. **Y la de verdad importante:** con carpetas, un electrodoméstico arrastrado por error a `Mobiliario` **entra en la lista de corte de melamina** sin que nada chille. Con el predicado, el objeto sabe lo que es: un `Asset` nunca computa, esté donde esté. El plan quería resolver esto con contenedores «protegidos», y eso no existe (F-16: medido, `allowObject()` no se respeta por script).

**Validación de tipo** (lo que el plan llamaba «protegidos»): vive en la API de VDO —la función de inserción es la única puerta— más un chequeo pasivo en `VDO/shared/vdo_guardian.py` que reporte intrusos. Los consumidores (dossier, lista de corte) filtran por `VDO_Tipo`; objetos no soportados se omiten silenciosamente. `allowObject()` no es necesario.

**Obligatorio por canon:** `Shape` nulo (`Part.Shape()`, Axioma T5), `onDelete()` en cascada (INVS §1.5), `claimChildren()` como puro reflejo visual (INVS §1.3), creación de hijos **fuera** de `execute()` (INVS §3.2).

**Criterio de aceptación:**
1. Crear ESPACIO con 1 muro y 1 COCO: `hijos_por_familia(esp, ARQUITECTURA)` devuelve el muro y `…MOBILIARIO` el COCO, **ejecutado en `FreeCADCmd`**.
2. Un `Ctrl+Z` deshace la creación completa.
3. `NivelPiso = -150` conserva −150 (test de regresión de F-14).
4. Borrar el espacio no deja huérfanos.
5. Test de ciclo: el COCO lee `AlturaCielorraso` del espacio que lo contiene → **no** debe producir dependencia cíclica (éste es el ciclo real del diseño, no el que mide el plan).

### E-3 · Plantilla VDO y contrato de membrete

**Objetivo:** que el membrete no pueda quedarse vacío en silencio.

**Decisión de partida:** o se reutiliza una plantilla ISO de stock con sus claves, o se crea la plantilla VDO con claves propias. Medido sobre `ISO/A3_Landscape_ISO5457_advanced.svg`: 20 campos, entre ellos `title`, `scale`, `drawing_number`, `creator`, `date_of_issue`, `revision_index`, `sheet_number`, `part_material`. **Ninguna** de las claves del plan (`Titulo_Proyecto`, `Nombre_Cliente`, `Codigo_Lamina`, `Escala`) existe.

**Recomendación:** plantilla propia VDO heredando la caja ISO 5457, con claves documentadas:

| Clave `freecad:editable` | Origen |
|--------------------------|--------|
| `vdo_proyecto` | `VDO_Proyecto.Nombre` |
| `vdo_cliente` | `VDO_Proyecto.Cliente` |
| `vdo_espacio` | `Espacio.NombreEspacio` |
| `vdo_lamina` | `[CodigoZona]-[TipoLamina]-[NN]` |
| `vdo_npt` | `Espacio.NivelPiso` formateado |
| `vdo_escala` | **leído de `view.Scale` tras el recompute final** (F-20) |

**Contrato de escritura** (F-8, medido): leer el dict → mutar copia → **reasignar completo**. La mutación en sitio se ignora sin error.

**Criterio de aceptación:** un test que, dada la plantilla, compruebe que el conjunto de claves `freecad:editable` del SVG es exactamente el de la tabla. Si alguien edita el SVG y borra un campo, el test falla antes que el plano salga en blanco.

### E-4 · Motor de dossier (`vdo_cam_dossier.py`)

**Firma:** `generar_dossier(doc, espacio, destino=None)`. **No lee `App.ActiveDocument`** (F-19): recibe el documento. Así se puede generar en lote y testear.

**Orden obligatorio** (medido: `addView` antes de asignar la plantilla lanza `RuntimeError: Template not set for Page`):

```python
page = doc.addObject("TechDraw::DrawPage", nombre)
tpl  = doc.addObject("TechDraw::DrawSVGTemplate", nombre + "_Tpl")
tpl.Template  = RUTA_SVG          # 1º el fichero
page.Template = tpl               # 2º la asignación
doc.recompute()                   # 3º ahora tpl.Width/Height son válidos (antes: 0.0 mm)
v = doc.addObject("TechDraw::DrawViewPart", "Planta")
page.addView(v)
v.Source     = [solidos]          # lista
v.Direction  = direccion
v.XDirection = xdir               # OBLIGATORIA: fija la rotación en el plano
v.HardHidden = False
v.ScaleType = "Automatic"         # 4º TechDraw calcula el ajuste real
doc.recompute()
page.KeepUpdated = False          # 5º evita N recomputos durante el montaje
                                  #    (despues de leer v.Scale, no antes)
v.ScaleType = "Custom"
v.Scale = snap_abajo(float(v.Scale))
doc.recompute()
page.KeepUpdated = True           # 6º al final del montaje
```

**Algoritmo de escala** (reemplaza §3.3 completo; validado en `tools/vdo_verify_fase1_techdraw.py`):

```python
v.ScaleType = "Automatic"         # el C++ de TechDraw calcula el ajuste real
doc.recompute()
v.ScaleType = "Custom"
v.Scale = snap_abajo(float(v.Scale))   # 1ª escala normalizada <= la calculada
doc.recompute()
```

**Nota sobre Undo (F-10 / DOS-12):** con TODO el montaje del dossier dentro de una sola
`openTransaction`/`commitTransaction` y `KeepUpdated=True` al final, `doc.UndoCount == 1`
y un `undo()` deshace el dossier completo. DOS-12 (`KeepUpdated=False` durante el
posicionamiento) es **optimización de rendimiento**, no requisito de Undo. La granularidad
de Undo la fija la transacción, no el número de recomputos.

Resultados medidos (plantilla ISO A3):

| Vista | `Automatic` | Normalizada |
|-------|-------------|-------------|
| COCO cenital | 1:2,00 | 1:2 |
| COCO iso | 1:4,00 | 1:5 |
| Armario 900×600×2400 iso | 1:10,00 | 1:10 |
| Muro 3000×150×2400 cenital | 1:8,00 | 1:10 |

**Prohibido:** calcular la escala desde `shape.BoundBox`. Medido en el armario: el BBox 3D da 900×600 cuando la proyección real mide 2333,5×1837,1 — error de 2,6× en X y 3,0× en Y, y la escala resultante (1:5) **desborda la hoja** (466,7×367,4 mm en un área útil de 220×277).

**Receta de verificación (DOS-15):** en el marco de vista, rotar la copia del shape con `Rotation(x, z.cross(x), z).inverted()` y `project(..., Vector(0,0,1))`; medir el BoundBox 2D resultante. **No usar `project()` crudo ni BoundBox 3D** (invariante a XDirection; da falso "DESBORDA"). El área útil se deriva de la plantilla VDO (`tpl.Width/Height` menos márgenes publicados junto al SVG), no de valores hardcodeados.

Si en algún momento hace falta la extensión exacta en Python, la primitiva es `TechDraw.project(shape, direction)` dentro del marco de vista; `DrawViewPart.getBoundingBox()` **no está expuesto a Python**.

**Centrado:** TechDraw ya centra en la página (medido: X=210, Y=148,5 en A3). Expresar el ajuste del membrete como **desplazamiento respecto a ese centro**, no como cálculo absoluto.

**Transaccionalidad** (INVS §3.1/§3.5): todo el dossier en **una** transacción, `abortTransaction()` en el `except`, `KeepUpdated=True` al final. No mezclar `openTransaction/commitTransaction` con `setActiveTransaction/closeActiveTransaction`.

**Hojas del test mínimo:**
- **Hoja A — planta del espacio:** `DrawViewPart`, `Direction=(0,0,1)`, `XDirection=(1,0,0)`.
- **Hoja B — ficha del módulo:** 4 `DrawViewPart` independientes con X/Y explícitos y Scale Custom común por hoja (casco crudo / vanos libres / cerrado / info taller); `DrawProjGroup` solo para juego ortográfico del mismo sólido (único Source, escala única — no sirve para 4 cuadrantes con Source distintos). Bloque de despiece con `TechDraw::DrawViewAnnotation`, `Text` como lista de strings (medido).

**Criterio de aceptación:**
1. Ambas hojas se generan en `FreeCADCmd` sin GUI.
2. Para cada vista: `ex*Scale <= util_W and ey*Scale <= util_H` (aserción explícita, no inspección visual).
3. `Scale` ∈ conjunto normalizado de D-3.
4. El campo `vdo_escala` del membrete coincide con `view.Scale` tras el recompute final.
5. Un solo `Ctrl+Z` deshace el dossier completo.

### E-5 · Test mínimo *(cierre de fase)*

`tests/test_espacio_dossier.py`, guardado con `HAY_FREECAD` (`tests/_entorno.py`), ejecutable con `FreeCADCmd`. Escenario del plan, sin cambios: doc `VDO_Test_01`, `ESPACIO_Cocina` (`COC-01`, NPT 0.0), 1 muro 3000×150×2400 en Arquitectura, 1 COCO 600×580×720 en Mobiliario.

**Checklist corregido** (reemplaza §4.2):

- [ ] Activar VDO sin documento: sin trazas de error, sólo «Nuevo proyecto VDO» activo. *(E-0)*
- [ ] Con documento y pestaña de inicio delante: la vista 3D queda enfocada. *(E-0)*
- [ ] La creación del ESPACIO es **una** acción deshacible. *(E-2)*
- [ ] `NivelPiso = -150` conserva −150. *(F-14)*
- [ ] `hijos_por_familia()` clasifica muro y COCO correctamente **en `FreeCADCmd`**. *(E-2)*
- [ ] El COCO leyendo `AlturaCielorraso` del espacio **no** crea dependencia cíclica. *(E-2)*
- [ ] **El dossier completo se genera en `FreeCADCmd`.** Ítem bloqueante: si funciona en GUI y falla headless, la jerarquía está en la capa de vista y el diseño está mal (INVS §1.4). *(E-4)*
- [ ] Toda vista cabe en el área útil, por aserción numérica. *(E-4)*
- [ ] Toda escala pertenece al conjunto normalizado. *(E-4, D-3)*
- [ ] Hoja B sin líneas ocultas (`HardHidden = False`). *(plan original, correcto)*
- [ ] Los membretes se rellenan solos y la escala impresa coincide con `view.Scale`. *(E-3, E-4)*
- [ ] Un solo `Ctrl+Z` deshace el dossier. *(E-4)*

---

## 5. Orden y dependencias duras

```
E-0  saneamiento de arranque ────────────────┐  (independiente, empezable ya)
                                             │
D-1 D-2 D-3 ✔ decididas ──► E-1  ADR-002 ──► E-2  VDO_Espacio ──┐
                                                                │
                              E-3  plantilla + contrato ────────┼──► E-4  motor ──► E-5  test
                                                                │
   (E-3 es prerrequisito DURO de E-4: sin SVG asignado,  ───────┘
    tpl.Width/Height valen 0.0 mm y no hay área útil)
```

**E-0 no espera a nadie.** E-2 sólo espera a que ADR-002 quede escrito (E-1), que es registrar D-1, no decidirla. E-3 puede ir en paralelo a E-2.

---

## 6. Riesgos abiertos

| Riesgo | Mitigación |
|--------|------------|
| D-1=A no requiere matizar T2 ni C-01; Espacio es nodo relacional puro sin `GeoFeatureGroupExtensionPython` | Ninguna acción adicional necesaria; T2 y C-01 se cumplen tal cual |
| `page.KeepUpdated=True` por defecto (medido) ensucia el Undo durante el montaje | Desactivar durante la construcción, activar al final |
| Las plantillas ISO de stock no tienen las claves del plan | E-3 fija el contrato y lo testea |
| Renombrar `vdo_cad_space.py` toca imports existentes | Hacerlo en E-2 con la suite verde antes y después (hoy: 65 passed, 18 skipped) |

---

## 7. Reproducir las mediciones

```fish
FreeCADCmd tools/vdo_verify_fase1_nucleo.py     # D-1, F-3, F-13, F-14, F-15, F-16
FreeCADCmd tools/vdo_verify_fase1_techdraw.py   # E-4, F-8, F-9, F-10, F-17, F-20, F-22
```
