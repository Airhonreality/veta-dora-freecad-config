# 06 — Auditoría técnica del Plan Fase 0 & Fase 1 (Núcleo VDO)

**Fecha:** 2026-10-30
**Objeto auditado:** «Especificación técnica del núcleo VDO (Fase 0 & Fase 1)», secciones 1 a 5 completas.
**Método:** verificación empírica contra **FreeCAD 1.1.4 (Libs 1.1.4R45040)** ejecutando `FreeCADCmd` en este equipo, más lectura del código fuente de BIM/Draft/TechDraw en `/usr/lib/freecad/Mod` y del canon propio (`docs/00`, `docs/02`, `docs/03 INVS`, `docs/04 ADR`).
**Contraplan:** `docs/07_CONTRAPLAN_FASE0_FASE1.md`.

> Ninguna afirmación de este documento es deducida. Cada hallazgo marcado **[medido]** se reprodujo ejecutando código en FreeCAD 1.1.4; los scripts están en `tools/` (ver §Reproducción).

---

## Veredicto

El **flujo** es correcto y se conserva: bootstrap → ESPACIO → plantilla → proyección → test mínimo. Los **fundamentos técnicos** no aguantan: de 22 hallazgos, **5 son críticos** y 4 de ellos son afirmaciones sobre FreeCAD que son falsas en FreeCAD 1.1.4 (no opinables: medidas).

Los tres que invalidan el diseño tal como está escrito:

1. **§1.1** diagnostica un bug de Coin3D que no existe, y atribuye a BIM un comportamiento que BIM no tiene.
2. **§2.1** elige un contenedor (`App::DocumentObjectGroupPython`) que **no tiene `Placement`**, y le pide «control de coordenadas locales». Es imposible, no difícil.
3. **§3.3** calcula la escala con el bounding box 3D. Para la isométrica de la Hoja B el error medido es de **2,6× en X y 3,0× en Y**, y produce un desbordamiento real de hoja en un caso de uso normal (armario de 2400 mm).

Además **§3.2** lee una propiedad de documento que FreeCAD no permite crear (`AttributeError` medido), y **§2.2** promete contenedores «protegidos» por tipo con un mecanismo que no se aplica por script (medido: el intruso entra).

---

## Tabla de hallazgos

| ID | Sev. | Sección | Afirmación del plan | Estado |
|----|------|---------|---------------------|--------|
| F-1 | **Crítica** | 1.1 | Falla el canvas porque FreeCAD «no inicializa el renderizador Coin3D»; BIM lo arregla forzando el visor | **Falso** |
| F-13 | **Crítica** | 2.1 | `App::DocumentObjectGroupPython` con «control de coordenadas locales» | **Imposible** [medido] |
| F-14 | **Crítica** | 2.3 | `NivelPiso` (NPT) como `App::PropertyLength` | **Corrompe datos en silencio** [medido] |
| F-15 | **Crítica** | 3.2 | Membrete lee `App.ActiveDocument.VDO_Proyecto` | **AttributeError** [medido] |
| F-17 | **Crítica** | 3.3 | Auto-escala desde el bounding box 3D | **Desborda la hoja** [medido] |
| F-2 | Alta | 2.2, 5 | Carpetas automáticas / sub-contenedores | **Viola T1, T2, C-01, ADR-001** |
| F-3 | Alta | 2.1, 2.3 | NPT como origen de obra | **Hueco**: sin CS local no hay origen [medido] |
| F-16 | Alta | 2.2 | Sub-contenedores «protegidos» por tipo | **No se aplica por script** [medido] |
| F-4 | Alta | 1.2, 1.3 | Verificar dependencias y «detener la carga» | Incorrecto: son módulos del core |
| F-5 | Alta | 1.2 | `Gui.Snapper` como API global | No existe hasta activar Draft/BIM |
| F-8 | Media | 3.2 | «Inyecta en el membrete» | **Falla en silencio** sin reasignación [medido] |
| F-9 | Media | 4.1 | Secuencia de vistas TechDraw | Infra-especificada; `addView` lanza sin template [medido] |
| F-18 | Media | 3.3 | Escalas `{…1:15…}` | 1:15 no es normalizada |
| F-19 | Media | 3.1 vs 3.2 | «No lee la pantalla» | Se contradice: lee `ActiveDocument` |
| F-20 | Media | 3.2 | Escala «calculada dinámicamente» al membrete | Debe leerse de `v.Scale` tras el recompute final |
| F-6 | Media | 1.3 | `Activated()` pone botones en gris | Antipatrón: es `IsActive()` |
| F-10 | Media | 4.2 | «Una sola acción deshacible» | En riesgo: TechDraw recomputa por su cuenta |
| F-21 | Baja | 4.2 | Checklist | Mide lo que no falla; falta el criterio headless |
| F-22 | Baja | 4.1 | «Bloque de texto paramétrico» | Nombrar la primitiva: `DrawViewAnnotation` [medido] |
| F-11 | Baja | 5 | Clase `vdo_space_core` | Colisión de nombres + viola convención |
| F-12 | Baja | 1.3 | Toolbars en 3 familias | Omite la trampa de `exec()` ya resuelta |
| F-23 | Baja | 2.3 | `VDO_Type` | Inconsistente con `VDO_Tipo` ya existente en COCO |
| F-24 | Baja | 2.3 | `NotasInstalacion` «multilínea» en `PropertyString` | **Válido** como almacenamiento [medido]; el editor de la GUI es de una línea |

---

## Bloque 1 — Inicialización y entorno (§1)

### F-1 · El diagnóstico del canvas 3D es falso — **Crítica**

**Dice el plan:** la Página de Inicio «monopoliza el MDI»; FreeCAD «no destruye la vista de inicio ni inicializa el renderizador Coin3D»; BIM lo resuelve porque su `Activated()` «fuerza la verificación del visor 3D».

**Lo que BIM hace de verdad** (`/usr/lib/freecad/Mod/BIM/InitGui.py:509-528`):

```python
def Activated(self):
    if hasattr(FreeCADGui, "draftToolBar"):
        FreeCADGui.draftToolBar.Activated()
    if hasattr(FreeCADGui, "Snapper"):
        FreeCADGui.Snapper.show()
    WorkingPlane._view_observer_start()
    grid_observer._view_observer_setup()
```

`grid_observer._view_observer_setup()` (`Draft/draftutils/grid_observer.py:79-93`) sólo se conecta a la señal `subWindowActivated` del `QMdiArea`. Es un **observador**: reacciona *cuando* una vista 3D pasa a estar activa. **No crea ninguna vista.** Ningún workbench puede forzar un visor 3D: un `Gui::View3DInventor` no existe mientras no exista un documento. No hay bug de Coin3D.

**Mecanismos reales:**

| Necesidad | API | Precedente en el core |
|-----------|-----|------------------------|
| Que haya visor | `App.newDocument()` (en GUI crea el doc Gui **y** su vista 3D) | `Std_New` |
| Detectar si falta | `Gui.ActiveDocument.mdiViewsOfType("Gui::View3DInventor")` | `Show/SceneDetails/Camera.py:41` |
| Crearlo sobre un doc sin visor | `Gui.ActiveDocument.createView("Gui::View3DInventor")` | `CAM/Path/Main/Sanity/ImageBuilder.py:101` |
| Pestaña de inicio | parámetro `closeStart` en `User parameter:BaseApp/Preferences/Mod/Start` | preferencia nativa del Start WB |

**Reescritura de §1.1:**

```python
def Activated(self):
    if App.GuiUp and App.ActiveDocument is not None:
        gdoc = Gui.ActiveDocument
        if gdoc and not gdoc.mdiViewsOfType("Gui::View3DInventor"):
            gdoc.createView("Gui::View3DInventor")
```

Sin documento no se hace nada: el comando «Nuevo proyecto VDO» es el que abre documento y visor. El síntoma que el plan intenta curar desaparece con `App.newDocument()`.

### F-4 · La verificación de dependencias está mal planteada — **Alta**

Sketcher, Draft/BIM y TechDraw son módulos de la distribución base, presentes en este equipo (`/usr/lib/freecad/Mod/{Draft,Sketcher,TechDraw,BIM}`). No son addons opcionales: si faltan, la instalación está rota. La validación es código muerto.

Y el patrón es peligroso: `Initialize()` sólo registra comandos, menús y toolbars; una excepción ahí deja el workbench **medio registrado**. Tampoco debe importar módulos pesados (penaliza el arranque de toda la aplicación).

**Correcto:** declarar en `package.xml` (ya tiene `<depend>BIM</depend>`); `import` perezoso en el `Activated()` de cada comando; `IsActive()` devuelve `False` si falta prerrequisito o documento; un único `PrintWarning`. **Nunca abortar `Initialize()`.**

### F-5 · `Gui.Snapper` no es una API global — **Alta**

Se instancia sólo al activarse Draft o BIM: `Draft/DraftTools.py:70` y `Draft/draftguitools/__init__.py:60`. BIM se protege con `hasattr` antes de usarlo (`InitGui.py:521`).

```python
if App.GuiUp:
    if not hasattr(Gui, "Snapper"):
        Gui.activateWorkbench("BIMWorkbench")   # nombre verificado: InitGui.py:34, :706
    if hasattr(Gui, "Snapper"):
        Gui.Snapper.show()
```

### F-6 · No se desactivan botones a mano — **Media**

El mecanismo es `IsActive()` **por comando**, que la GUI reevalúa continuamente. Tocar el estado de los `QAction` desde `Activated()` crea estado que se queda obsoleto en cuanto el usuario cierra un documento.

### F-12 · Toolbars: conservar el patrón ya resuelto — **Baja**

El plan omite la trampa que el repo **ya documentó y resolvió** en la cabecera de `InitGui.py`: FreeCAD ejecuta ese archivo con `exec(code, globals, locals)` usando dicts distintos, así que nada definido ahí es visible desde los métodos de una clase definida ahí (`NameError` diferido al construir la toolbar), y `__file__` no existe. La implementación sigue en `VDO/vdo_initgui.py`. No tocar.

---

## Bloque 2 — Objeto ESPACIO (§2)

### F-13 · `App::DocumentObjectGroupPython` no tiene `Placement` — **Crítica** [medido]

§2.1 pide un contenedor con «comportamiento paramétrico, TaskPanel propio **y control de coordenadas locales**». Lo primero y lo segundo sí; lo tercero es **imposible con ese tipo**.

Medido en FreeCAD 1.1.4:

```
TypeId = App::DocumentObjectGroupPython
props  = ['ExpressionEngine', 'Group', 'Label', 'Label2', 'Proxy', 'Visibility', '_GroupTouched']
tiene Placement      -> False
tiene Shape          -> False
isDerivedFrom GeoFeature -> False
```

Consecuencias directas sobre el plan:

- **Sin `Placement` no hay sistema de coordenadas local.** El `NivelPiso` (NPT) queda como un número decorativo del membrete, desacoplado de la geometría. Y `docs/02:323` exige «cotas verticales desde NPT (Z=0)»: con este contenedor, no hay NPT desde el que cotar.
- **Sin `Shape` no puede ser `Source` de una vista TechDraw.** El motor de §3 tendrá que recorrer descendientes para construir la lista de sólidos; el plan no lo dice.
- Viola **Axioma T1** y **ADR-001** (`docs/02:82`, `docs/04:207`): nunca `DocumentObjectGroup` como contenedor principal.

Nótese que el plan acierta a medias: `…GroupPython` **sí** acepta `Proxy` y por tanto `execute()` y TaskPanel (a diferencia de `App::Part`). Lo falso es sólo la parte de coordenadas — pero es la que sostiene todo el replanteo.

### F-3 · El CS local es un hueco real, no un detalle — **Alta** [medido]

Medido: un `Part::FeaturePython` con `App::PropertyLinkListChild` **no propaga `Placement`**. Moviendo el padre a x=1000, el hijo se queda en `Vector (0.0, 0.0, 0.0)`.

Medido también: la salida existe y es compatible con ADR-001 —

```
esp.addExtension("App::GeoFeatureGroupExtensionPython")   -> OK
props tras extension: [... 'Group', 'Placement', 'Proxy', 'Shape' ...]
Padre movido a x=2000:
  HijoGeo.Placement.Base       = Vector (0.0, 0.0, 0.0)     <- coords locales
  HijoGeo.getGlobalPlacement() = Vector (2000.0, 0.0, 0.0)  <- CS local REAL
```

Es decir: se puede tener un recinto con origen de obra verdadero **conservando `Part::FeaturePython` con Proxy de Python**, que es exactamente la limitación que ADR-001 imputa a `App::Part` (`Gui::ViewProviderPart` compilado en C++). La ruta de extensión no es `App::Part` y no está prohibida por ADR-001, pero **sí roza T2** (añade una propiedad `Group`) y por tanto exige ADR nuevo, no decisión de implementación. Ver decisión **D-1** del contraplan.

### F-14 · `NivelPiso` como `App::PropertyLength` corrompe el NPT en silencio — **Crítica** [medido]

```
f.addProperty("App::PropertyLength",   "Largo"); f.Largo = -150.0  ->  0.0 mm      (!!)
f.addProperty("App::PropertyDistance", "Cota");  f.Cota  = -150.0  -> -150.0 mm
```

`App::PropertyLength` está acotada a ≥ 0 y **clampa a 0 sin lanzar ni avisar**. Un NPT de −150 mm (sótano, desnivel de obra, rebaje de ducha) se convierte en 0 y nadie se entera hasta que el montador replantea mal en obra.

- `NivelPiso` → **`App::PropertyDistance`** (longitud con signo).
- `AlturaCielorraso` → `App::PropertyLength` es correcto (siempre > 0).
- Regla general para el proyecto: **toda cota que pueda ser negativa va en `PropertyDistance`**. Conviene un test que recorra las propiedades de los objetos VDO y falle si una cota con signo está declarada como `PropertyLength`.

### F-16 · Los sub-contenedores «protegidos» no son protegibles — **Alta** [medido]

§2.2 dice que cada grupo «solo admite» ciertos tipos. Medido con un `Proxy` que implementa `allowObject()` devolviendo `False` para todo lo que no sea muro:

```
g2.addObject(Part::Box "Intruso")
contenido tras addObject: ['Intruso']        <- entró
addObject RESPETA allowObject -> False
```

`allowObject()` sólo lo consulta la GUI en drag & drop (`ViewProviderGroupExtension::canDropObject`). **Cualquier script —incluido el propio código de VDO— se lo salta.** La palabra «protegidos» del plan no es realizable con el tipo de contenedor.

**Correcto:** la validación de tipo vive en la **API de VDO** (la función/comando que inserta es la única puerta) más un chequeo en el guardián (`VDO/shared/vdo_guardian.py` ya existe) que reporte intrusos en el recompute. Y, si se quiere la defensa de la GUI además, implementar `allowObject()` *también* — pero como mejora de UX, no como garantía.

### F-2 · Las carpetas automáticas violan el canon propio — **Alta**

§2.2 y el paso 2 del roadmap crean tres `App::DocumentObjectGroup` automáticos. Choca de frente con:

- **Axioma T2** (`docs/02:83`): «No crear carpetas `App::DocumentObjectGroup` automáticas».
- **C-01** (`docs/00:40`): los grupos automáticos **perdieron**; gana `App::PropertyLinkListChild`.
- **INVS §1.4** (`docs/03:66-72`): la jerarquía debe estar en la capa de datos porque en `FreeCADCmd` no hay ViewProviders. El motor de dossier headless de §3.1 **es justo el caso que rompe**.

El plan confunde tres cosas distintas de FreeCAD. Esta es la corrección de fondo:

| Intención | Primitiva correcta | Verificado |
|-----------|--------------------|------------|
| **Pertenencia / jerarquía** | `App::PropertyLinkChild`, `App::PropertyLinkListChild` | registradas; `addProperty` OK [medido] |
| **Reutilización / instanciado** (mismo módulo N veces) | `App::Link`, `App::LinkGroup` — y sus variantes **`App::LinkPython` / `App::LinkGroupPython`, que sí aceptan Proxy** | registradas en `libFreeCADApp.so` |
| **Carpeta visual** | `App::DocumentObjectGroup` | prohibida por T2 |

Las «subcarpetas» son **propiedades de enlace**, no objetos:

```python
obj.addProperty("App::PropertyLinkListChild", "Arquitectura", "Espacio", "Muros, vanos, pisos")
obj.addProperty("App::PropertyLinkListChild", "Mobiliario",   "Espacio", "Modulos VDO")
obj.addProperty("App::PropertyLinkListChild", "Assets",       "Espacio", "Referencia, no computa")

def claimChildren(self):
    o = self.Object
    return list(o.Arquitectura) + list(o.Mobiliario) + list(o.Assets)
```

Y el motor **no «inspecciona subcarpetas»**: lee `espacio.Mobiliario`. Idéntico en GUI y en `FreeCADCmd`.

Esto además encaja con el contrato que el COCO **ya implementa** (`VDO/cad/objects/vdo_cad_coco.py:154`): `App::PropertyLinkListChild "Hijos"` + `claimChildren()` + `onDelete()`. El ESPACIO debe hablar el mismo idioma que el resto del repo.

### F-23 · `VDO_Type` es inconsistente con el código existente — **Baja**

El COCO ya usa `VDO_Tipo` y `VDO_Subtipo` (`vdo_cad_coco.py:140-142`), en español. El plan introduce `VDO_Type`. Unificar en `VDO_Tipo`, y marcarla **de sólo lectura** (`obj.setEditorMode("VDO_Tipo", 1)`) además de replicar el valor en `obj.Proxy.Type`: si el usuario la edita, el filtrado por código deja de funcionar en silencio.

### F-24 · `NotasInstalacion` multilínea: el plan acierta — **Baja** [medido]

Comprobado, porque era dudoso: `App::PropertyString` **sí conserva los saltos de línea** (`'linea 1\nlinea 2'` se almacena y se recupera íntegro). El tipo elegido por el plan es correcto.

La única limitación es de interfaz: el editor del panel de propiedades es de una línea, así que la edición real debe hacerse desde el TaskPanel con un `QTextEdit`. La alternativa `App::PropertyStringList` da editor de lista pero obliga a tratar las notas como líneas independientes, lo que complica el volcado al membrete. Se mantiene `PropertyString`.

---

## Bloque 3 — Motor TechDraw (§3)

> **Buena noticia medida:** TechDraw funciona **íntegramente en `FreeCADCmd`**. `DrawPage`, `DrawSVGTemplate`, `DrawViewPart`, `DrawViewAnnotation`, HLR y recompute se ejecutaron sin GUI. El criterio de aceptación headless que exige el contraplan es viable.

### F-17 · El algoritmo de auto-escala desborda la hoja — **Crítica** [medido]

§3.3 paso 1 dice: «Calcula la diagonal total del conjunto de sólidos a proyectar (Xmax − Xmin, Ymax − Ymin)». Eso es el bounding box **3D**, y sólo coincide con la extensión del dibujo si la dirección de vista está alineada con un eje. La Hoja B proyecta en isométrica `(1,-1,1)`.

Medido, área útil A3 = 220 × 277 mm (420×297 menos márgenes y membrete):

| Caso | BBox 3D (lo que usa el plan) | Proyección real (`TechDraw.project`) | Escala que elige el plan | Ocupación real | Resultado |
|------|------------------------------|--------------------------------------|--------------------------|----------------|-----------|
| COCO 600×580×720 | 600 × 580 | 933,4 × 1012,5 | 1:5 | 186,7 × 202,5 | cabe (por suerte) |
| **Armario 900×600×2400** | 900 × 600 | **2333,5 × 1837,1** | **1:5** | **466,7 × 367,4** | **DESBORDA** |

Error del BBox 3D en el caso del armario: **2,6× en X, 3,0× en Y**. El criterio de aceptación §4.2 «perfectamente contenido dentro de los márgenes / cero desbordamientos» falla con un módulo de altura normal de carpintería.

**Corrección de mi propia auditoría previa:** recomendé `view.getBoundingBox()`. Es incorrecto — el símbolo C++ existe (`TechDraw::DrawViewPart::getBoundingBox`) pero **no está expuesto a Python**:

```
AttributeError: 'TechDraw.DrawViewPart' object has no attribute 'getBoundingBox'
```

**Algoritmo correcto y medido** (delegar el ajuste en el C++ de TechDraw y normalizar después):

```python
v.Direction  = direccion
v.XDirection = xdir            # obligatoria: fija la rotacion en el plano
v.ScaleType  = "Automatic"     # TechDraw calcula el ajuste real
doc.recompute()
s = snap_abajo(float(v.Scale)) # primera escala normalizada <= la calculada
v.ScaleType = "Custom"
v.Scale = s
doc.recompute()
```

Resultados medidos con plantilla ISO A3:

| Vista | `Automatic` calcula | Normalizada | X / Y |
|-------|---------------------|-------------|-------|
| COCO cenital | 1:2,00 | 1:2 | 210 / 148,5 |
| COCO iso | 1:4,00 | 1:5 | 210 / 148,5 |
| Armario iso | 1:10,00 | 1:10 | 210 / 148,5 |
| Muro 3000×150×2400 cenital | 1:8,00 | 1:10 | 210 / 148,5 |

Esto **rectifica mi F-7 previa**: `ScaleType="Automatic"` por sí solo **no** basta, porque devuelve escalas no normalizadas (1:4, 1:8) que no existen en el escalímetro del taller. El requisito de escala normalizada del plan es legítimo; lo que estaba mal era medir el objeto en vez de la proyección. Si hace falta la extensión exacta en Python, la primitiva es `TechDraw.project(shape, direction)` (verificada; el módulo expone además `projectEx`, `findShapeOutline`, `makeExtentDim`).

**Sobre el centrado (§3.3 paso 4):** medido, TechDraw ya coloca la vista en el **centro de la página** por defecto (X=210, Y=148,5 en A3 = 420/2, 297/2). Lo que no hace es descontar el membrete. Así que el paso 4 es legítimo pero debe expresarse como **desplazamiento respecto al centro por defecto**, no como cálculo absoluto desde cero.

### F-15 · `App.ActiveDocument.VDO_Proyecto` no existe y no puede existir — **Crítica** [medido]

```
doc.VDO_Proyecto = "X"
-> AttributeError: 'App.Document' object has no attribute 'VDO_Proyecto'
```

`App::Document` **no acepta propiedades dinámicas**. El contrato de data binding de §3.2 es inejecutable tal como está escrito, en sus dos primeras líneas (`VDO_Proyecto`, `VDO_Cliente`).

Alternativas verificadas:

| Opción | Medición | Cuándo usarla |
|--------|----------|---------------|
| `doc.Meta` (dict persistente) | `doc.Meta["VDO_Proyecto"]` persiste tras reasignar el dict completo → **OK** | metadatos de archivo (cliente, autor) que no deben aparecer en el árbol |
| Objeto singleton `VDO_Proyecto` (`FeaturePython`) | patrón estándar | **recomendado**: propiedades tipadas, visible y editable en el árbol, y participa del DAG (las hojas pueden depender de él y recomputarse al cambiar el nombre del proyecto) |

`doc.Meta` tiene además la misma trampa que `EditableTexts`: hay que reasignar el diccionario completo.

### F-8 · El membrete falla en silencio si se muta el dict en sitio — **Media** [medido]

```
tpl.EditableTexts[clave] = "MUTADO_EN_SITIO"
tpl.EditableTexts.get(clave)  ->  'B. Hecate'      <- ignorado, sin error

d = tpl.EditableTexts; d[clave] = "REASIGNADO"; tpl.EditableTexts = d
tpl.EditableTexts.get(clave)  ->  'REASIGNADO'     <- OK
```

Es el patrón canónico del propio TechDraw (`TechDrawTools/TaskFillTemplateFields.py:128` y `:541`). Y los campos **sólo existen si el SVG los declara** con `freecad:editable`: medido sobre `ISO/A3_Landscape_ISO5457_advanced.svg`, hay 20 campos (`title`, `scale`, `drawing_number`, `creator`, `date_of_issue`, `revision_index`, `sheet_number`, `part_material`, …). Dos consecuencias para el plan:

- Los nombres del plan (`Titulo_Proyecto`, `Nombre_Cliente`, `Codigo_Lamina`, `Escala`) **no existen** en las plantillas de stock. Hay que elegir: partir de una plantilla ISO y reutilizar sus claves (`title`, `scale`, …), o crear la plantilla VDO declarando las claves propias. Debe quedar escrito como contrato.
- Medido: `tpl.Width`/`Height` valen **0.0 mm** hasta que se asigna el fichero SVG; después, 420/297 mm. El «área útil de página» de §3.3 paso 2 **no se puede calcular antes** de asignar la plantilla. El paso 3 del roadmap es prerrequisito duro del paso 4.

### F-19 · §3.1 se contradice con §3.2 — **Media**

§3.1 presume de desacoplamiento («no lee la pantalla ni la posición del ratón»), pero §3.2 lo hace leer `App.ActiveDocument`, que es estado global mutable: el equivalente a «leer la pantalla» en la capa de datos. El motor debe recibir `(doc, espacio)` como parámetros. Si no, no se puede generar el dossier de dos espacios en lote ni testear sin documento activo.

### F-20 · La escala del membrete debe leerse de vuelta — **Media**

Si el motor inyecta un string «1:10» calculado y luego algo cambia `view.Scale`, el membrete miente —y un plano con escala falsa es un error de obra, no un bug cosmético. Rellenar el campo `scale` **leyendo `v.Scale` después del recompute final**. Es lo que hace TechDraw (`TaskFillTemplateFields.py:120-127` toma la escala del primer DVP/DPG de la página). Medido funcionando: `membrete scale = '1:10'` leído de `v.Scale=0.1`.

### F-18 · 1:15 no es una escala normalizada — **Media**

El conjunto del plan `{1:1, 1:2, 1:5, 1:10, 1:15, 1:20, 1:50}` mete **1:15**, que no pertenece a la serie normalizada (ISO 5455: 1:2, 1:5, 1:10, 1:20, 1:50, 1:100 y sus decádicas). Un plano a 1:15 no se puede medir con escalímetro en taller ni en obra. Quitarlo. Si se quiere un escalón intermedio, el de uso arquitectónico habitual es **1:25** (no ISO, pero sí presente en escalímetros); decidirlo y documentarlo.

---

## Bloque 4 — Test de integración y roadmap (§4, §5)

### F-9 · Secuencia TechDraw infra-especificada — **Media** [medido]

Orden obligatorio, medido:

```
page.addView(v) antes de asignar template
-> RuntimeError: Template not set for Page
```

Secuencia mínima correcta (verificada en `FreeCADCmd`, con precedentes en `TechDraw/TDTest/`):

```python
page = doc.addObject("TechDraw::DrawPage", "Hoja_A")
tpl  = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
tpl.Template  = "/ruta/membrete_vdo.svg"   # ANTES que addView
page.Template = tpl
doc.recompute()                            # ahora tpl.Width/Height son validos

v = doc.addObject("TechDraw::DrawViewPart", "Planta")
page.addView(v)                            # TDTest/DrawHatchTest.py:34
v.Source     = [muro]                      # LISTA  — TDTest/DrawHatchTest.py:33
v.Direction  = (0, 0, 1)                   # cenital: correcto en el plan
v.XDirection = (1, 0, 0)                   # FALTA EN EL PLAN
v.HardHidden = False
```

Dos correcciones de fondo:

1. **`XDirection` es obligatoria en la práctica.** Con sólo `Direction`, la rotación dentro del plano la elige TechDraw y las láminas salen giradas de forma no determinista. Además la escala depende de la rotación: medir la extensión en una base y dibujar en otra da la escala equivocada. El criterio «contenido dentro de los márgenes» no es reproducible sin fijarla.
2. **Para la Hoja B usar `TechDraw::DrawProjGroup`**, no dos `DrawViewPart` sueltos (`TDTest/DrawProjectionGroupTest.py:42-54`): mantiene alineación entre proyecciones y una sola escala.

Vectores del plan: cenital `(0,0,1)` ✔ · frontal `(0,-1,0)` ✔ · isométrica `(1,-1,1)` ✔ (válida; necesita `XDirection` coherente).

### F-22 · Nombrar la primitiva del bloque de despiece — **Baja** [medido]

«Bloque de texto paramétrico» = `TechDraw::DrawViewAnnotation`, con `Text` como **lista de strings** (una por línea). Verificado creándolo y recomputándolo en headless.

### F-10 · «Una sola acción deshacible» está en riesgo — **Media**

La creación de páginas y vistas dispara recomputos propios de TechDraw (`page.KeepUpdated` llega **a `True`** por defecto, medido). Sin control, el dossier deja N entradas en el historial y el checklist falla.

- Toda la generación en **una** transacción (INVS §3.1), con `abortTransaction()` en el `except` (INVS §3.5: `recompute()` fuera de transacción es violación crítica).
- `page.KeepUpdated = False` durante el montaje, `True` al final.
- TechDraw usa el par moderno `App.setActiveTransaction()` / `closeActiveTransaction()` (`TaskFillTemplateFields.py:535-545`) y el canon VDO usa `openTransaction`/`commitTransaction`. Ambos valen; **no mezclarlos** en la misma operación.

### F-21 · El checklist mide lo que no falla — **Baja**

- «No se produce ningún error de dependencias cíclicas» al crear 3 grupos: **crear grupos no puede producir ciclos**. El riesgo real de ciclo en este diseño es `Espacio → Mobiliario → COCO → Espacio` si el COCO alguna vez lee `AlturaCielorraso` del espacio que lo contiene. *Ése* es el que hay que testear.
- Falta el único criterio que valida de verdad la arquitectura: **generar el dossier en `FreeCADCmd`**. Si funciona en GUI y falla en headless, la jerarquía está en la capa de vista y el diseño está mal (INVS §1.4). Medido: TechDraw lo permite, así que no hay excusa.
- El repo ya tiene la infraestructura: `tests/_entorno.py` expone `HAY_FREECAD` y la suite se salta lo que necesita documentos (65 passed, 18 skipped sin FreeCAD).

### F-11 · Colisión de nombres — **Baja**

`vdo_space_core` choca con `VDO/cad/objects/vdo_cad_space.py` (554 líneas), que **no es el recinto**: es el motor de geometría de divisiones y tiras dentro de una cavidad (`generar_divisiones_matriz`, `resolver_tiras`). Y viola la convención de `docs/02 §6` (entidades `FeaturePython` → prefijo `vdo_cad_*`).

Propuesta: `VDO/cad/objects/vdo_cad_espacio.py` → objeto `VDO_Espacio`; y renombrar el existente a `vdo_cad_divisiones.py`, que es lo que hace.

---

## Reproducción

Los scripts de verificación se ejecutan con el FreeCAD del sistema:

```fish
FreeCADCmd tools/vdo_verify_fase1_nucleo.py   # F-13, F-14, F-15, F-16, F-3
FreeCADCmd tools/vdo_verify_fase1_techdraw.py # F-17, F-8, F-9, F-10, F-22
```

Dos notas de método, por si alguien repite las mediciones:

- En `FreeCADCmd`, `print()` **no llega a stdout** y `App.Console.PrintMessage` se vacía sólo al salir limpiamente. Si el proceso se cuelga o se mata, se pierde todo. Los scripts escriben a fichero con `flush()` en cada línea.
- El intérprete de este equipo es `fish`: **no soporta heredocs**. Los scripts van en ficheros, no en línea de comandos.

---

## Decisiones derivadas (cerradas el 2026-10-30)

Las tres decisiones que la auditoría dejó abiertas están resueltas en `docs/07_CONTRAPLAN_FASE0_FASE1.md §3`:

- **D-1** Contenedor del ESPACIO → `Part::FeaturePython` + `App::GeoFeatureGroupExtensionPython` (CS local real conservando el Proxy de Python). **Requiere ADR-002** matizando el Axioma T2.
- **D-2** Metadatos de proyecto → objeto singleton `VDO_Proyecto`, no `doc.VDO_Proyecto` (inejecutable) ni sólo `doc.Meta` (fuera del DAG).
- **D-3** Escalas → `1:1 1:2 1:5 1:10 1:20 1:25 1:50 1:100`. Sin 1:15.
