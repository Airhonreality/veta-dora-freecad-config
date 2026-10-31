# 08 — Sistema de Láminas por Capas Informacionales (Dossier VDO)

**Sistema:** VDO (Veta de Oro) — FreeCAD 1.1+
**Subsistema:** Capa 5 — Producción, CAM y Documentación (TechDraw Dossier)
**Estado:** Implementación parcial — Entidad Espacio, TaskPaneles, comando VDO_CrearEspacio, plantilla SVG y tests listos. Motor de dossier (`vdo_cam_dossier.py`) pendiente.
**Fuente:** Consolidación de `docs/02 §4.1.4`, `docs/07 §E-2..E-5` y Directiva de Diseño Final (objeto Espacio, entorno de inicio, TechDraw engine y flujo de fabricación)

---

## 1. Objetivo y Alcance

El dossier se reorganiza eliminando la saturación de planos arquitectónicos convencionales. La información se distribuye en **4 Capas Informacionales Progresivas** más una **Capa Anexa de Herrajes/Capturas**, donde cada captura visual aparece vinculada inmediatamente a su entidad hermana (Espacio o Módulo).

El motor procesa **un Espacio a la vez**. La planta de replanteo, las axonometrías y las fichas de los muebles de ese espacio se compilan en un cuaderno cerrado, sin intercalar hojas de otros espacios.

**Regla de nomenclatura (Nombres Naturales):** Queda estrictamente prohibido usar códigos crípticos como `COC-01` o `DOR-02`. La nomenclatura es 100% en lenguaje natural: `Cocina`, `Habitacion_Juan`, `Vestidor_Ppal`, `Bano_Visitas`. Los objetos en el árbol de FreeCAD y las etiquetas visibles siguen esta regla: `ESPACIO_Cocina`, `ESPACIO_Habitacion_Juan`; módulos anidados: `Cocina_BajoMesada_01`, `Habitacion_Juan_Closet_01`; membretes: `"Cocina"`, `"Habitación Juan"`.

---

## 2. Estructura del Dossier por Espacio (Ej. Espacio Cocina)

| Capa | Lámina | Contenido | Destinatario |
|:-----|:-------|:----------|:-------------|
| **1** | L01A — Obra Civil y Verificación de Escuadras | Muros, vanos, líneas de escuadra, cero muebles | Instalador en obra |
| **1** | L01B — Huella de Implantación e Instalaciones en Piso | Huellas de módulos, puntos de servicio, cotas de referencia | Montador / Carpintero |
| **2** | L02 — Axonometría General Anti-Muro | Isométrica de habitación amueblada, globos de etiquetado, capturas de espacio | Instalador / Carpintero |
| **3** | L03A…L03N — Tramos de Montaje | Alzado frontal ortogonal por pared o isla, cotas Z desde NPT, cadena continua X | Montador |
| **4** | L04…LN — Fichas Unitarias por Módulo | 4 cuadrantes por mueble (isométrica casco, frontal vanos, frontal cerrado, info taller) | Carpintero de taller |
| **5** | Hojas hermanas — Herrajes y Capturas Vinculadas | Detalles de herraje, acabado, ficha proveedor, puntos de calibración | Carpintero / Montador |

---

## 3. Capa 1: Arquitectura y Replanteo

### 3.1 Lámina 1A — Obra Civil y Verificación de Escuadras

| Campo | Especificación |
|-------|----------------|
| Objetivo | Recibir el recinto en bruto y diagnosticar deformaciones en los muros |
| Proyección | Cenital Top pura (vector Z) |
| Escala | 1:20 |
| Muros existentes | Con cotas de largo total y espesores |
| Vanos | Cotas a puertas y ventanas (anchos libres y antepechos) |
| Líneas de Escuadra | Cian, triangulaciones diagonales esquina a esquina con medida en mm |
| Contenido | **Cero muebles dibujados** (plano despejado para cinta métrica) |

### 3.2 Lámina 1B — Huella de Implantación e Instalaciones en Piso

| Campo | Especificación |
|-------|----------------|
| Objetivo | Marcar en el suelo dónde cae cada mueble y validar tomas de servicio |
| Proyección | Cenital Top idéntica a 1A |
| Huellas | Líneas discontinuas en piso: módulos bajos, columnas, islas |
| Puntos de servicio | Desagües fregadero/lavavajillas, acometidas agua, salidas gas, tomas corriente piso |
| Cotas de referencia | Distancia de cada acometida respecto a esquina inicio (X=0, Y=0) |

---

## 4. Capa 2: Vistas de Conjunto

### 4.1 Lámina L02 — Axonometría General de Implantación (Algoritmo Anti-Muro)

| Campo | Especificación |
|-------|----------------|
| Objetivo | Comprensión espacial 3D completa de la habitación amueblada |
| Proyección | Isométrica limpia (vector (1, -1, 1)) |
| Corte dinámico anti-muro | Paredes de cara a cámara se apagan o bajan a altura de zócalo (100 mm) |
| Muros de respaldo | Visibles en línea fina como referencia de fondo |
| Globos de etiquetado | Flechas directrices identificando cada mueble con nombre natural (Cocina_BajoMesada_01, Habitacion_Juan_Closet_01) |
| Capturas de Espacio hermanadas | Fotos del nicho con tuberías, desnivel de piso con advertencia de cuñas |

---

## 5. Capa 3: Por Tramos de Montaje

### 5.1 Lámina de Tramo (Ej. Pared Norte de la Cocina)

| Campo | Especificación |
|-------|----------------|
| Estructura | Una lámina por pared activa o isla; no se mezclan tramos |
| Vista | Alzado frontal ortogonal al tramo |
| Cotas Z | Desde Piso Terminado (Z=0): nivel zócalo, nivel mesón, altura libre mesón-alacenas, cota riel anclaje muro |
| Cadena continua X | Medidas acumuladas de cada mueble y vano |
| Puntos de muro | Tomas de corriente ocultas tras electrodomésticos, enchufes sobre mesón, refuerzos drywall |

---

## 6. Capa 4: Por Módulo (Fichas Unitarias de Fabricación)

Una hoja por mueble individual fabricable. Distribución fija en 4 cuadrantes.

| Cuadrante | Contenido | Enfoque |
|-----------|-----------|---------|
| **1** | Isométrica de casco crudo | Carcasa sin frentes, sistema de ensamble, dirección veta, fondos ranurados/clavados |
| **2** | Frontal de vanos libres | Casco sin puertas, cotas de luz útil, cotas a ejes perforación repisas |
| **3** | Frontal cerrado (fachadas) | Vista con frentes, holguras/fugas (2-3 mm), tipo fachada, uñeros/gola/tirador |
| **4** | Información de taller | Despiece esencial placas (cantos L1, L2, A1, A2), herrajes asignados, requerimientos cliente / notas de taller |

---

## 7. Capa 5: Herrajes y Capturas Vinculadas (Hojas Hermanadas)

| Árbol | Descripción |
|-------|-------------|
| `ESPACIO_Cocina_Ficha_Fabricacion` (o similar por módulo) | Lámina de 4 cuadrantes del mueble |
| `ESPACIO_Cocina_Anexo_Detalles` | Hoja hermana inmediata del mismo mueble |

**Contenido de la hoja hermana del módulo:**
1. Capturas vectoriales tipadas (VDO_Target = Modulo): detalle de herraje, detalle de acabado.
2. Ficha técnica del proveedor: código fabricante, plantilla perforación, brocas (copa 35 mm, broca 5 mm pernos Euro).
3. Puntos críticos de calibración: regulación tornillos excéntricos bisagras, ajustes caída cajón.

**Enrutamiento de capturas:**
- `VDO_Target = Espacio` → láminas hermanas al espacio (L02, L03).
- `VDO_Target = Modulo` → hojas hermanas de detalle técnico del herraje del mueble.

---

## 8. Entidad «Espacio» (Zona / Recinto)

### 8.1 Naturaleza Conceptual

El Espacio es la entidad territorial y organizativa de primer orden. No es una pieza geométrica ni un sólido de madera; es el marco de referencia físico, relacional y documental que define una habitación real (ej: Cocina, Habitación Juan, Vestidor Principal, Baño Visitas).

Actúa como padre semántico: todo lo que existe en el proyecto (muros, ventanas, muebles VDO, electrodomésticos, planos técnicos) pertenece a un Espacio determinado.

```
                               ┌────────────────────────┐
                               │     PROYECTO TOTAL     │
                               └───────────┬────────────┘
                     ┌─────────────────────┴─────────────────────┐
                     ▼                                           ▼
          ╔═════════════════════╗                     ╔═════════════════════╗
          ║   ESPACIO: Cocina   ║                     ║ ESPACIO: Habitacion_║
          ║   (Cocina Principal)║                     ║ _Juan              ║
          ╚══════════┬══════════╝                     ╚═════════════════════╝
     ┌───────────────┼───────────────┬────────────────────────┐
     ▼               ▼               ▼                        ▼
[Arquitectura] [Mobiliario]       [Assets]             [Dossier 2D]
(Muros/Vanos)  (Módulos COCO)  (Nevera/Fregadero)    (Plano de la Cocina)
```

### 8.2 Estructura Interna: Las 3 Subcarpetas Canónicas

La pertenencia de objetos al VDO_Espacio se gestiona mediante una lista de pertenencia única (`Hijos`, `App::PropertyLinkListChild`, canon T2). No se crean subcarpetas como objetos `App::DocumentObjectGroup` (eso violaría T2 y C-01).

La clasificación semántica en tres familias se deriva por **predicado sobre el discriminante autoritativo** (`VDO_Modulo` + `resolver_modulo(obj)` para módulos VDO; `IfcType` para objetos BIM ajenos), no por contenedores separados ni literales ficticios:

| Familia | Discriminante | Contenido típico |
|---------|--------------|------------------|
| `Arquitectura` | `IfcType ∈ {"Wall","Door","Window","Column","Slab"}` (objetos BIM de la toolbar Arch/BIM) o módulo VDO futuro | Muros, tabiques, columnas, puertas, ventanas, plano de piso |
| `Mobiliario` | `resolver_modulo(o).tipo ∈ {"coco","cajon","puerta","zocalo","panel","tambor"}` | Módulos VDO (cascos, cajoneros, alacenas, paneles ajuste, zócalos) |
| `Assets` | `VDO_Target ∈ {"Asset","Electrodomestico","Sanitario"}` o `IfcType` de mobiliario no manufactrable | Hornos, refrigeradores, lavavajillas, estufas, fregaderos |
| `Otros` | todo lo restante | Objetos sueltos, se omiten con aviso |

**Nota:** Un objeto sabe lo que es (`Arquitectura`, `Mobiliario`, `Assets`) independientemente de dónde se arrastre en la GUI. Un `Asset` nunca computa en listas de corte, esté donde esté. Un objeto sin `VDO_Modulo` y sin `IfcType` reconocible cae en `Otros` y no se proyecta ni entra en cutlist.

El clasificador vive en `VDO/shared/vdo_shared_familias.py` (`hijos_por_familia()`, `clasificar_hijo()`) y es consumido por el motor de dossier, el cutlist y el guardián.

### 8.3 Campos de Información del Espacio

| Grupo | Campo | Tipo | Descripción |
|-------|-------|------|-------------|
| **Identificación** | `NombreEspacio` | `App::PropertyString` | Nombre legible del recinto (ej. "Cocina") |
| **Identificación** | `VDO_Modulo` | `App::PropertyString` | Testigo de tipo: `"espacio"` |
| **Sistema** | `VDO_Tipo` | `App::PropertyString` (solo lectura) | Identificador de clase: `"EspacioFeature"` |
| **Estructura Lógica** | `Hijos` | `App::PropertyLinkListChild` | Lista de pertenencia (muros, COCOs, assets) |
| **Cotas de Obra** | `NivelPiso` | `App::PropertyDistance` | Cota NPT respecto al cero del proyecto (acepta negativos) |
| **Cotas de Obra** | `AlturaCielorraso` | `App::PropertyLength` | Altura libre al falso techo |
| **Obra** | `NotasInstalacion` | `App::PropertyString` | Instrucciones de montaje y advertencias de pared (multilínea) |
| **Diseño** | `RequisitosCliente` | `App::PropertyString` | Requerimientos estéticos y funcionales del cliente |

### 8.4 Comportamiento del Sub-árbol

- `Shape` nulo (`Part.Shape()`): evita duplicación geométrica, Z-fighting y doble masa CAM.
- `onDelete()` en cascada: borrar el Espacio elimina sus hijos (arquitectura, mobiliario, assets) sin dejar huérfanos.
- `claimChildren()`: reflejo visual de `Hijos` (`App::PropertyLinkListChild`, canon T2).
- Creación de hijos **fuera** de `execute()` (Axioma R-04): no mutar topología dentro del ciclo de recompute.

### 8.5 Reglas de Arquitectura (Axiomas No Negociables)

| Axioma | Especificación |
|--------|----------------|
| **Cero ciclos DAG** | La dependencia es estrictamente unidireccional: Espacio ⟶ contiene en su Group a ⟶ COCO. El `execute()` del COCO es geométricamente autónomo y **jamás** enlaza con el Espacio. Las colisiones con `AlturaCielorraso` o límites de obra se gestionan exclusivamente en la interfaz (TaskPanel / `vdo_creation_flow.py`) como restricciones de entrada del usuario, nunca como enlaces en el árbol de dependencias. |
| **Coexistencia T2 / T3** | `VDO_Espacio` es T2 (Contenedor Territorial): hereda de `Part::FeaturePython` con `Shape` nulo, nodo relacional puro sin `GeoFeatureGroupExtensionPython` ni CS local propio; agrupa mediante `Hijos` (`PropertyLinkListChild`). `COCO` es T3 (Componente Ensamblado Rígido): utiliza `PropertyLinkListChild` (`Hijos`) porque modela un conjunto físico de placas unidas mecánicamente. No hay inconsistencia; representan dos realidades físicas distintas (la habitación vs. el mueble). |
| **Nombres Naturales** | Prohibido `COC-01`, `DOR-02`, etc. Uso exclusivo de lenguaje natural. |

---

## 9. Matrices de Requerimientos por Objeto

### 9.1 Matriz de Requerimientos — Objeto Espacio (VDO_Espacio)

| ID | Requerimiento | Tipo | Prioridad | Origen | Verificación |
|:---|:--------------|:-----|:----------|:-------|:-------------|
| ESP-01 | `Part::FeaturePython` con `Shape` nulo (T5/ADR-004); `PropertyLinkListChild` (`Hijos`) para pertenencia; nodo relacional puro sin `GeoFeatureGroupExtensionPython` ni CS local propio | Técnico | Crítico | Directiva Diseño | `Hijos` es LinkListChild; hijos conservan coordenadas de mundo |
| ESP-02 | Propiedad `NombreEspacio` (`App::PropertyString`) | Datos | Crítico | Directiva Diseño §8.3 | Campo editable en TaskPanel / pestaña Datos |
| ESP-03 | Propiedad `VDO_Tipo = "EspacioFeature"` (solo lectura) | Sistema | Alta | Directiva Diseño §8.3 | `setEditorMode(…, 1)`, espejo en `obj.Proxy.Type` |
| ESP-04 | Propiedad `NivelPiso` (`App::PropertyDistance`, acepta negativos) | Datos | Crítico | `docs/06 F-14` | NPT = -150 conserva -150, no clampa a 0 |
| ESP-05 | Propiedad `AlturaCielorraso` (`App::PropertyLength`) | Datos | Alta | Directiva Diseño §8.3 | > 0, usado para alerta de colisión vertical en UI |
| ESP-06 | Propiedad `NotasInstalacion` (`App::PropertyString`, multilinea) | Datos | Media | `docs/06 F-24` | Conserva saltos de línea `\n` |
| ESP-07 | Propiedad `RequisitosCliente` (`App::PropertyString`) | Datos | Media | Directiva Diseño §8.3 | Texto libre de requerimientos del cliente |
| ESP-08 | `Shape` nulo (`Part.Shape()`) | Geometría | Crítico | `docs/02 T5` | Evita duplicación geométrica, Z-fighting |
| ESP-09 | `onDelete()` en cascada (borra hijos arquitectura/mobiliario/assets) | Ciclo de vida | Crítico | `docs/02 T6` | Borrar Espacio no deja huérfanos |
| ESP-10 | `claimChildren()` como reflejo visual de `Hijos` | Visual | Alta | `docs/02 T4` | Árbol muestra hijos bajo Espacio |
| ESP-11 | Creación de hijos fuera de `execute()` | Técnico | Crítico | `docs/02 R-04` | No mutar topología en ciclo de recompute |
| ESP-12 | Jerarquía de datos en `Hijos` (`PropertyLinkListChild`, canon T2) | Datos | Crítico | Directiva Diseño §8.2 | Pertenece y coordenadas sincronizadas |
| ESP-13 | Clasificadores por predicado: Arquitectura / Mobiliario / Assets sobre `VDO_Tipo` (NO son objetos `DocumentObjectGroup`) | Datos | Crítico | Directiva Diseño §8.2 | Filtros sobre `Hijos`; árbol permanece plano |
| ESP-14 | Validación de tipo en API de inserción (única puerta de entrada) | Datos | Alta | `docs/06 F-16` | Intruso no entra por script; chequeo pasivo en guardián |
| ESP-15 | Cero ciclos DAG: COCO no tiene `PropertyLink` hacia Espacio | Arquitectura | Crítico | Directiva Diseño §8.5 | COCO `execute()` autónomo, sin enlace al padre |
| ESP-16 | Coexistencia T2/T3: Espacio=T2 (`Part::FeaturePython` + `PropertyLinkListChild`), COCO=T3 (`PropertyLinkListChild`) | Arquitectura | Alta | Directiva Diseño §8.5 | Dos realidades físicas distintas, sin inconsistencia |

### 9.2 Matriz de Requerimientos — Objeto Proyecto (VDO_Proyecto)

| ID | Requerimiento | Tipo | Prioridad | Origen | Verificación |
|:---|:--------------|:-----|:----------|:-------|:-------------|
| PRY-01 | Singleton `App::FeaturePython` (no `doc.VDO_Proyecto`, inejecutable) | Datos | Crítico | `docs/06 F-15` | Objeto visible en árbol, editable, participa DAG |
| PRY-02 | Propiedad `Nombre` | Datos | Alta | Directiva Diseño | Fuente de verdad para metadatos de proyecto |
| PRY-03 | Propiedad `Cliente` | Datos | Media | Directiva Diseño | Espejo opcional en `doc.Meta` para archivo |
| PRY-04 | Propiedad `Disenador` | Datos | Media | Directiva Diseño | Formulario de proyecto |
| PRY-05 | Propiedad `Fecha` | Datos | Media | Directiva Diseño | Formulario de proyecto |
| PRY-06 | Participa del DAG (hojas se recomputan al cambiar nombre) | Técnico | Alta | `docs/07 D-2` | Cambiar nombre propaga recompute a hojas |

### 9.3 Matriz de Requerimientos — Formulario de Proyecto (Punto de Entrada)

| ID | Requerimiento | Tipo | Prioridad | Origen | Verificación |
|:---|:--------------|:-----|:----------|:-------|:-------------|
| FPR-01 | Ventana modal única al iniciar proyecto (CmdNuevoProyecto o Start Page) | UI | Crítico | Directiva Diseño §2 | Se abre al crear proyecto |
| FPR-02 | Campos: Nombre del Proyecto, Cliente, Diseñador, Fecha | UI | Alta | Directiva Diseño §2 | Formulario completo |
| FPR-03 | Matriz de Espacios Iniciales: tabla editable con nombres naturales y alturas de techo | UI | Alta | Directiva Diseño §2 | Ej. Cocina / 2400 mm, Habitacion_Juan / 2600 mm |
| FPR-04 | Acción [Crear Proyecto]: crea .FCStd, inyecta metadatos en raíz, genera contenedores VDO_Espacio precargados con clasificación por predicado (Arquitectura / Mobiliario / Assets) | Funcional | Crítico | Directiva Diseño §2 | Objetos ESPACIO_* creados en árbol, sin subcarpetas como objetos |
| FPR-05 | Comando `VDO_CrearEspacio` en Toolbar (Familia Azul / Arquitectura) | UI | Alta | Directiva Diseño §2 GAP 4 | Permite añadir habitaciones en cualquier momento |
| FPR-06 | TaskPanel propio para VDO_Espacio vía `setEdit()` (doble clic en ESPACIO_Cocina) | UI | Alta | Directiva Diseño §2 GAP 2 | Edita NombreEspacio, AlturaCielorraso, NivelPiso, NotasInstalacion, RequisitosCliente |
| FPR-07 | Estilo visual oscuro de VDO en TaskPanel del Espacio | UI | Media | Directiva Diseño §2 | Paleta dark mode VDO |
| FPR-08 | Resumen en vivo de elementos contenidos (cantidad de muros, módulos y assets) | UI | Media | Directiva Diseño §2 | Conteos actualizados en TaskPanel |

### 9.4 Matriz de Requerimientos — Plantilla VDO (SVG Membrete)

| ID | Requerimiento | Tipo | Prioridad | Origen | Verificación |
|:---|:--------------|:-----|:----------|:-------|:-------------|
| TPL-01 | Plantilla oficial `vdo_template_a3.svg` en `VDO/resources/templates/` | Recurso | Crítico | Directiva Diseño §5 | Archivo existe en ruta |
| TPL-02 | Marco horizontal A3 con cajetín técnico de carpintería | Diseño | Alta | Directiva Diseño §5 | Dimensiones A3 (420×297 mm) |
| TPL-03 | Clave `freecad:editable="vdo_proyecto"` | Técnico | Crítico | Directiva Diseño §5 | Campo existe en SVG |
| TPL-04 | Clave `freecad:editable="vdo_cliente"` | Técnico | Crítico | Directiva Diseño §5 | Campo existe en SVG |
| TPL-05 | Clave `freecad:editable="vdo_espacio"` | Técnico | Crítico | Directiva Diseño §5 | Campo existe en SVG |
| TPL-06 | Clave `freecad:editable="vdo_lamina"` | Técnico | Media | Directiva Diseño §5 | Campo existe en SVG |
| TPL-07 | Clave `freecad:editable="vdo_npt"` | Técnico | Alta | Directiva Diseño §5 | Campo existe en SVG |
| TPL-08 | Clave `freecad:editable="vdo_escala"` | Técnico | Crítico | Directiva Diseño §5 | Campo existe en SVG |
| TPL-09 | Escritura por reasignación completa del dict `EditableTexts` | Técnico | Crítico | `docs/06 F-8` | Mutación en sitio se ignora sin error |
| TPL-10 | `vdo_escala` leído de `view.Scale` tras recompute final | Datos | Crítico | `docs/06 F-20` | No inyectar string calculado |
| TPL-11 | Test de integridad: comparar claves `freecad:editable` del SVG con la tabla contractual (TPL-03…TPL-08); si el SVG se edita y falta una clave, el membrete sale en blanco sin error | Calidad | Crítico | `docs/06 F-8` | Falla antes de generar hoja en blanco |

### 9.5 Matriz de Requerimientos — Motor de Dossier (`vdo_cam_dossier.py`)

| ID | Requerimiento | Tipo | Prioridad | Origen | Verificación |
|:---|:--------------|:-----|:----------|:-------|:-------------|
| DOS-01 | Firma `generar_dossier(doc, espacio, destino=None)` | API | Crítico | `docs/07 E-4` | No lee `App.ActiveDocument` |
| DOS-02 | Hoja A: planta del espacio (`DrawViewPart`, Direction=(0,0,1), XDirection=(1,0,0)) | Funcional | Alta | `docs/07 E-5` | Generada en FreeCADCmd |
| DOS-03 | Hoja A lee `espacio.Hijos` filtrado por `clasificar_hijo() == "arquitectura"` (discriminante: `IfcType ∈ {"Wall","Door","Window","Column","Slab"}` para objetos BIM de la toolbar Arch/BIM; `VDO_Modulo` para módulos VDO futuros); pasa solo esos sólidos como Source. Nunca por literales `"Muro"`/`"Vano"`/`"Columna"`/`"Piso"` | Funcional | Alta | Directiva Diseño §6 GAP 6 | Separación determinista de sólidos |
| DOS-04 | Hoja A: huella de Mobiliario en línea discontinua — degradado a headless-safe: geometría cosmética/Draft antes de proyectar; en FreeCADCmd (`v.ViewObject is None`) se usa línea continua y el formato de línea solo en GUI | Funcional | Media | Directiva Diseño §6 GAP 6 | Huella visible en planta (GUI); línea continua (headless) |
| DOS-05 | Hoja B: recibe referencia directa del COCO dentro de `espacio.Hijos` filtrado por `resolver_modulo().tipo` en `MOBILIARIO` (`{"coco","cajon","panel","zocalo","tambor"}`, o `vdo_tipo=="contenedor"` excluyendo espacio); nunca por literales `"COCO"`/`"Panel"`/`"Zocalo"` | Funcional | Alta | Directiva Diseño §6 GAP 6 | COCO identificado sin ambigüedad |
| DOS-06 | Hoja B: 4 `DrawViewPart` independientes con X/Y explícitos y Scale Custom común por hoja (casco crudo / vanos libres / cerrado / info taller); `DrawProjGroup` solo para juego ortográfico del mismo sólido (único Source, escala única) — no sirve para 4 cuadrantes con Source distintos | Funcional | Alta | `docs/07 E-4` | 4 cuadrantes con Source distintos, alineados |
| DOS-07 | 4 cuadrantes de taller en Hoja B (casco crudo, vanos libres, fachadas cerrado, info taller) en `DrawViewPart` independientes; distribución fija por hoja | Funcional | Alta | Directiva Diseño §6 GAP 6 | Distribución fija |
| DOS-08 | Bloque de despiece con `TechDraw::DrawViewAnnotation`, Text lista de strings | Funcional | Media | `docs/06 F-22` | Una línea por string |
| DOS-09 | Escala: `ScaleType="Automatic"` → `recompute()` → leer `v.Scale` → snap hacia abajo (conjunto 1:1…1:100, con 1:25, sin 1:15). Área útil derivada de la plantilla VDO (`tpl.Width/Height` menos márgenes publicados junto al SVG), **no** hardcodeada (220×277) | Técnico | Crítico | `docs/07 D-3` | Prohibido calcular desde BBox 3D |
| DOS-10 | `XDirection` obligatoria en cada vista | Técnico | Alta | `docs/06 F-9` | Rotación en plano determinista |
| DOS-11 | Orden construcción: page → template → recompute → vistas (F-9, RuntimeError si se invierte) | Técnico | Crítico | `docs/06 F-9` | `addView` antes de template lanza RuntimeError |
| DOS-12 | `page.KeepUpdated = False` durante montaje/posicionamiento X/Y de vistas; se activa (`True`) justo antes de leer `v.Scale` (DOS-09/DOS-10) y se deja `True` al final del dossier. No es requisito de Undo, es optimización de rendimiento | Técnico | Media | `docs/06 F-10` | Evita N recomputos y ensuciar Undo |
| DOS-13 | Todo el dossier en una transacción (`openTransaction` / `commitTransaction` / `abortTransaction`), no mezclar APIs | Técnico | Crítico | `docs/07 E-4` | Un solo Ctrl+Z deshace dossier completo |
| DOS-14 | No mezclar `openTransaction/commitTransaction` con `setActiveTransaction/closeActiveTransaction` | Técnico | Alta | `docs/06 F-10` | Consistencia transaccional |
| DOS-15 | Verificación en marco de vista: rotar la copia del shape con `Rotation(x, z.cross(x), z).inverted()` y `project(..., Vector(0,0,1))`; medir BoundBox 2D resultante. Aserción: `ex*Scale <= util_W and ey*Scale <= util_H` por vista. **Prohibido** `project()` crudo ni BoundBox 3D (invariante a XDirection; da falso "DESBORDA") | Calidad | Crítico | `docs/07 E-5` | Cada vista cabe en área útil |
| DOS-16 | Generación ejecutable en `FreeCADCmd` (headless) como criterio bloqueante (medido: TechDraw funciona sin GUI) | Calidad | Crítico | `docs/07 E-5` | Jerarquía en capa de datos, no de vista |
| DOS-17 | Enrutamiento de capturas: `VDO_Target = Espacio` → hojas hermanas al espacio; `VDO_Target = Modulo` → hojas hermanas de detalle técnico | Funcional | Media | Directiva Diseño §6 GAP 6 | Capturas vinculadas a entidad origen |
| DOS-18 | Red de seguridad por hoja: `len(solidos) > 0` antes de asignar Source; si `v.Source` apunta a un espacio con Shape nula → hoja vacía silenciosa (sin error) | Calidad | Alta | Directiva Diseño §6 GAP 6 | Ninguna hoja queda sin validar |

---

## 10. Referencias Cruzadas

| Documento | Sección | Contenido relacionado |
|-----------|---------|----------------------|
| `docs/02_ARQUITECTURA_TECNICA_FREECAD.md` | §4.1.4 | Exportación de Planos Automáticos — Sistema de Láminas por Capas Informacionales |
| `docs/02_ARQUITECTURA_TECNICA_FREECAD.md` | §4.1.1–4.1.3 | Láminas C0, Replanteo de Montaje, Ficha Técnica por Mueble L2 |
| `docs/04_DECISIONES_ADR_Y_AXIOMAS.md` | ADR-005 | Contenedor Espacio + T2/C-01 (nodo relacional puro, sin GeoFeatureGroupExtension) |
| `docs/06_AUDITORIA_PLAN_FASE0_FASE1.md` | F-8, F-9, F-10, F-14, F-15, F-16, F-17, F-20, F-22 | Hallazgos TechDraw respaldados empíricamente |
| `docs/07_CONTRAPLAN_FASE0_FASE1.md` | E-2, E-3, E-4, E-5 | Entregables VDO_Espacio, plantilla, motor dossier, test |
| `docs/00_MATRIZ_CONTRADICCIONES_Y_RESOLUCION.md` | C-01 | Jerarquía de datos sin grupos intermedios |

---

## 11. Estado de Implementación

| Entregable | Estado | Código | Próximo paso |
|------------|--------|--------|--------------|
| Objeto `VDO_Espacio` | Implementado | `VDO/cad/objects/vdo_cad_espacio.py` | — |
| TaskPanel / Formulario Espacio | Implementado | `VDO/ui/vdo_ui_espacio_task.py` | — |
| `VDO_Proyecto` singleton | Implementado | `VDO/cad/objects/vdo_cad_proyecto.py` | — |
| Formulario de Proyecto (Start Page / CmdNuevoProyecto) | Parcial (TaskPanel listo) | `VDO/ui/vdo_ui_proyecto_task.py` | Integración en Start Page |
| Comando `VDO_CrearEspacio` (Toolbar Azul/Arquitectura) | Implementado | `VDO/vdo_initgui.py` (`CmdCrearEspacio`) | — |
| Plantilla VDO SVG `vdo_template_a3.svg` | Creada | `VDO/resources/templates/vdo_template_a3.svg` | JSON de área útil ya publicado |
| Motor `generar_dossier` | Implementado: lámina 1B (planta) y ficha de módulo con 3 vistas (casco, vanos libres, cerrado) según la acción de fachadas; exporta SVG con `destino` | `VDO/cam/vdo_cam_dossier.py` | Estilo de huella en GUI (DOS-04); láminas 1A, L02 y tramo |
| Catálogo de láminas | Creado | `VDO/resources/templates/laminas_dossier.json` | Añadir láminas 1A, L02 y tramo al catálogo |
| Acción mostrar/ocultar fachadas | Implementada (3D y dossier) | `VDO/shared/vdo_shared_fachadas.py`, `CmdFachadas` en barra «VDO Vista» | — |
| Comando GUI `VDO_Dossier` (barra CAM) | Creado | `VDO/vdo_initgui.py` (`CmdDossier`) | Probar en sesión GUI con un espacio real |
| Test `test_espacio_dossier` | Creado | `tests/test_espacio_dossier.py` | — |
| Test plantilla TPL-11 | Creado | `tests/test_template_vdo.py` | — |
| Test F-14 cotas con signo | Creado | `tests/test_cotas_con_signo.py` | — |
| Test motor de dossier y flujo completo | Creado | `tests/test_dossier_motor.py` | — |

---

**Nota:** Este documento consolida el subsistema de láminas por capas informacionales y la entidad Espacio con las decisiones de diseño definitivas. Es fuente de verdad para la implementación. Cualquier cambio debe reflejarse aquí antes de implementarse en código.
