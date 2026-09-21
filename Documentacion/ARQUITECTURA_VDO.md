Sí. Después de ampliar la investigación, **yo cambiaría la arquitectura que veníamos planteando**. El punto clave es que Veta de Oro no necesita ser una colección de trucos de `App::Link` + expresiones: necesita una **arquitectura de producto paramétrico**, donde FreeCAD sea el motor geométrico y de fabricación.

La conclusión que saco es esta:

# Stack recomendado para Veta de Oro

```text
┌──────────────────────────────────────────────────────────┐
│                  VETA DE ORO                              │
│          SISTEMA PARAMÉTRICO DE FABRICACIÓN               │
└─────────────────────────┬────────────────────────────────┘
                          │
              ┌───────────▼────────────┐
              │  1. MODELO DE DATOS    │
              │  Spreadsheet / Vars    │
              │  parámetros + reglas   │
              └───────────┬────────────┘
                          │
              ┌───────────▼────────────┐
              │  2. GENERADOR / REGLAS │
              │  Woodworking + Python  │
              │  componentes VDO       │
              └───────────┬────────────┘
                          │
              ┌───────────▼────────────┐
              │  3. GEOMETRÍA          │
              │  Part + Part Design    │
              │  Body / paneles        │
              └───────────┬────────────┘
                          │
              ┌───────────▼────────────┐
              │  4. INSTANCIACIÓN      │
              │  App::Link / Assembly  │
              │  submódulos Matrioshka │
              └───────────┬────────────┘
                          │
              ┌───────────▼────────────┐
              │  5. DOCUMENTACIÓN      │
              │  TechDraw              │
              │  planos / etiquetas    │
              └───────────┬────────────┘
                          │
              ┌───────────▼────────────┐
              │  6. PRODUCCIÓN         │
              │  BOM + CutList + CSV   │
              │  DXF / CNC             │
              └───────────┬────────────┘
                          │
              ┌───────────▼────────────┐
              │  7. CAM                │
              │  FreeCAD CAM            │
              │  G-code / CNC          │
              └────────────────────────┘
```

Y hay una decisión importante:

> **No usaría AIGenFurniture ni Cubinets como núcleo de Veta de Oro.**

Los estudiaría y reutilizaría ideas de ellos, pero construiría VDO sobre **FreeCAD nativo + Woodworking + una capa Python propia**.

---

# 1. La base: Spreadsheet / Variables

Esta es probablemente la modificación más importante respecto a lo que estábamos haciendo.

## No hagamos esto

```text
COCO_4C
   │
   ├── PANEL_LAT_IZQ
   │       │
   │       └── "busca el Alto del padre"
   │
   └── PANEL_BASE
```

Ese modelo nos estaba metiendo en problemas.

## Hagamos esto

```text
COCO_4C
│
├── PARAMETROS
│
│   Alto        720
│   Ancho       600
│   Fondo       580
│   Espesor      18
│   Trasera       6
│   ...
│
└── COMPONENTES
    ├── PANEL_LAT_IZQ
    ├── PANEL_LAT_DER
    ├── PANEL_BASE
    └── PANEL_TECHO
```

Pero los parámetros no tienen que vivir necesariamente como propiedades arbitrarias de `COCO_4C`.

Podemos tener:

```text
COCO_4C
└── Params
      Spreadsheet
```

con aliases:

```text
alto
ancho
fondo
espesor
```

FreeCAD recomienda precisamente utilizar **aliases de Spreadsheet** para las variables paramétricas porque son más legibles y robustos que referencias como `B17`. ([GitHub][1])

Por ejemplo:

```text
Params.alto
Params.ancho
Params.fondo
Params.espesor
```

Eso resuelve gran parte del problema que acabamos de tener.

---

# 2. Pero no quiero una Spreadsheet gigante

Esto es importante.

No haría:

```text
VDO_GLOBALS
────────────────────
1000 parámetros
```

porque terminaríamos construyendo otro Excel infernal.

Lo haría por **scope**.

### Nivel proyecto

```text
PROYECTO
└── ProjectParams
```

### Nivel módulo

```text
COCO_4C
└── Params
```

### Nivel componente

```text
PANEL_LAT_IZQ
└── Manufacturing
```

Así:

```text
Proyecto
    ↓
Mueble
    ↓
Módulo
    ↓
Componente
```

tiene parámetros propios.

---

# 3. El descubrimiento más importante: Cubinets

Cubinets confirma que este enfoque no es una teoría nuestra.

Su arquitectura es:

```text
Spreadsheet
     ↓
parámetros
     ↓
Parametric Template
     ↓
Assembly
     ↓
Cut List
```

Y hay una decisión de diseño especialmente interesante:

> Una plantilla paramétrica de Cubinets es simplemente un **documento FreeCAD normal**.

No inventa una clase de archivo monstruosa. Además, sus paneles son objetos `Part::Box`, y la plantilla contiene una Spreadsheet llamada `params`. ([GitHub][2])

Eso es exactamente la filosofía que yo adoptaría para VDO:

**documentos FreeCAD normales + convención VDO + automatización.**

---

# 4. Woodworking: sí lo usaría

Aquí cambia mi recomendación anterior.

El Workbench **Woodworking** está actualmente en versión **3.3.20260801**, actualizado el 1 de agosto de 2026, y está diseñado específicamente para gabinetes y carpintería. ([FreeCAD][3])

Además, su evolución incluye cosas que nos interesan muchísimo:

* parametrización automática;
* `VarSet`;
* herramientas para paneles;
* referencias;
* nesting;
* múltiples pockets;
* routers;
* dowels;
* mortise & tenon;
* paneles desde geometría;
* soporte de contenedores;
* herramientas para automatización paramétrica. ([GitHub][4])

### Por tanto:

**Woodworking = toolbox especializado de VDO.**

No lo usaría como "arquitectura de Veta de Oro".

---

# 5. AIGenFurniture: copiaría el paradigma UX

AIGenFurniture es muy interesante porque está atacando exactamente el problema de taller:

```text
CAJA
 ↓
DIMENSIONES
 ↓
CARACTERÍSTICAS
 ↓
GENERATE STRUCTURE
 ↓
PRODUCCIÓN
```

Actualmente figura en el Addon Manager como **0.1.6**, y su descripción oficial dice que genera gabinetes desde cajas simples, añade frentes, repisas y cajones y exporta archivos de fabricación. ([FreeCAD][5])

El propio desarrollador describe el flujo como:

> simple box layout → dimensions/positions → features → auto-generate cabinet structure → manufacturing files. ([Reddit][6])

### Para VDO esto es oro.

Porque la interfaz que tú recordabas:

```text
╔══════════════════╗
║    COCO_4C       ║
║                  ║
║  W: 600          ║
║  H: 720          ║
║  D: 580          ║
╚══════════════════╝
         ↓
   CREAR ESTRUCTURA
```

es probablemente una **mejor UX para el usuario de taller** que obligarlo a editar 25 expresiones.

---

# 6. Entonces VDO debería tener un "Cabinet Generator"

Aquí aparece nuestra propia capa.

No quiero que el usuario haga:

```text
crear Box
crear Box
crear Box
crear Box
crear Spreadsheet
crear expression
crear placement
crear link
...
```

Quiero:

```text
VDO → Nuevo módulo
```

y:

```text
Tipo:
[ COCO_4C ]

Ancho:
600

Alto:
720

Fondo:
580

Material:
[ Melamina 18 ]

Trasera:
[ 6 mm ]

Sistema:
[ Minifix ]
```

y:

```text
[ CREAR ESTRUCTURA ]
```

Eso genera automáticamente:

```text
COCO_4C
│
├── Params
│
├── PANEL_LAT_IZQ
├── PANEL_LAT_DER
├── PANEL_BASE
├── PANEL_TECHO
├── TRASERA
│
├── HARDWARE
│
└── Manufacturing
```

---

# 7. Aquí entra Python

Esta es la parte que **sí deberíamos desarrollar nosotros**.

No intentaría solucionar toda la lógica con Expression Engine.

El Expression Engine debe hacer:

```text
alto = Params.alto
ancho = Params.ancho
fondo = Params.fondo
```

pero Python debe hacer:

```text
crear_panel()
crear_modulo()
aplicar_canto()
aplicar_mecanizado()
generar_cutlist()
duplicar_componente()
actualizar_reglas()
```

Es decir:

```text
Expression Engine
       =
matemática paramétrica

Python VDO
       =
lógica de producto
```

Esta separación es muchísimo más escalable.

---

# 8. Y `pieza_tablero` no debería ser geometría

Este es otro cambio que haría.

`pieza_tablero` debería ser **metadato de fabricación**.

Por ejemplo:

```text
PANEL_LAT_IZQ
│
├── Geometry
│   └── Shape
│
└── Manufacturing
    ├── pieza_tablero = PT-001
    ├── material = MEL-18-BLANCO
    ├── espesor = 18 mm
    ├── largo = 720
    ├── ancho = 580
    ├── canto_1 = ABS_2
    ├── canto_2 = ABS_2
    ├── canto_3 = -
    ├── canto_4 = -
    ├── mecanizado = MZ-...
    └── cantidad = 1
```

Eso nos permite separar:

**qué es la pieza físicamente**

de

**cómo se fabrica.**

---

# 9. Entonces nuestra biblioteca maestra cambia

En vez de:

```text
PANEL_MAESTRO.FCStd
```

como una especie de objeto mágico del cual todo depende...

yo construiría una **biblioteca de componentes VDO**:

```text
VDO_LIBRARY/
│
├── Components/
│   ├── PANEL_VERTICAL.FCStd
│   ├── PANEL_HORIZONTAL.FCStd
│   ├── TRASERA.FCStd
│   ├── FRENTE.FCStd
│   └── DIVISOR.FCStd
│
├── Hardware/
│   ├── MINIFIX.FCStd
│   ├── TARUGO.FCStd
│   └── BISAGRA.FCStd
│
├── Materials/
│   ├── MEL_18.FCStd
│   ├── MEL_25.FCStd
│   └── MDF_18.FCStd
│
└── Templates/
    ├── COCO_4C.FCStd
    ├── COCO_2P.FCStd
    └── COCO_CAJONES.FCStd
```

Y ahí sí:

```text
App::Link
```

tiene muchísimo sentido.

FreeCAD soporta Links tanto dentro del mismo documento como hacia documentos externos. ([GitHub][7])

---

# 10. Matrioshka sigue viva

No la abandonamos.

La hacemos correctamente:

```text
PANEL
   ↑
   │ Link
   │
COCO_4C
   ↑
   │ Link
   │
MUEBLE
   ↑
   │ Link
   │
PROYECTO
```

Pero el Link ahora cumple una función específica:

> **instanciación y reutilización**

y no:

> **sistema de transmisión de parámetros entre padres e hijos.**

Esa distinción es importantísima.

---

# 11. Para ensamblaje: FreeCAD Assembly, no Assembly4 como primera opción

Aquí también cambiaría mi recomendación.

FreeCAD ya tiene un **Assembly Workbench oficial incorporado desde 1.0**, con solver Ondsel, componentes, joints, subassemblies, exploded views y BOM. ([GitHub][8])

Además, las versiones actuales añaden:

* simulación;
* datums;
* subassemblies flexibles;
* BOM. ([GitHub][9])

Por eso:

### VDO

```text
FreeCAD Assembly
```

como capa de ensamblaje principal.

### Assembly4

Lo mantendría como **herramienta especializada**, no como fundamento de VDO.

Assembly4 es excelente para una arquitectura basada en:

```text
App::Link
+
LCS
+
Expression Engine
```

y permite componentes en documentos externos. ([GitHub][10])

Pero para nosotros introduce otra semántica de ensamblaje que no necesitamos para cada gabinete.

---

# 12. Para documentación: TechDraw

Aquí no inventaría absolutamente nada.

```text
Pieza
 ↓
TechDraw
 ↓
Plano
```

TechDraw permite insertar vistas de objetos y grupos en planos. ([GitHub][11])

Así podemos generar:

```text
PT-001
────────────────────
PANEL LATERAL

720 × 580 × 18

Cantos:
↑ ABS 2
→ ABS 2

Mecanizados:
MZ-001
MZ-003
```

---

# 13. Para producción: dos salidas distintas

Aquí debemos separar:

### CutList / BOM

```text
COCO_4C
 ↓
Manufacturing Data
 ↓
CSV / BOM / CutList
```

Cubinets ya demuestra este paradigma: ensamblaje → Cut List. ([GitHub][2])

FreeCAD Assembly también tiene generación de BOM incorporada. ([GitHub][8])

Pero VDO necesitará una **BOM propia**, porque nosotros necesitamos:

```text
pieza_tablero
material
espesor
largo
ancho
cantos
mecanizados
cantidad
mueble
módulo
posición
```

Eso va más allá de una BOM mecánica genérica.

---

# 14. Y después: CAM

FreeCAD ya tiene actualmente **CAM Workbench** integrado.

El flujo oficial es:

```text
3D MODEL
   ↓
CAM JOB
   ↓
TOOLS
   ↓
OPERATIONS
   ↓
SIMULATION
   ↓
POST PROCESSOR
   ↓
G-CODE
```

y está diseñado precisamente para generar instrucciones CNC desde modelos 3D. ([GitHub][12])

Por tanto:

```text
VDO
 ↓
pieza_tablero
 ↓
mecanizados
 ↓
CAM Job
 ↓
G-Code
```

es técnicamente viable.

---

# 15. La arquitectura final que recomiendo

Esta sería mi **V1 de arquitectura oficial de Veta de Oro**:

```text
                         VETA DE ORO
                              │
             ┌────────────────┴─────────────────┐
             │                                  │
             ▼                                  ▼
      VDO DATA MODEL                      VDO LIBRARY
             │                                  │
      Spreadsheet / Vars                  FCStd Components
             │                                  │
             └──────────────┬───────────────────┘
                            │
                            ▼
                    VDO GENERATOR
                       Python
                            │
              ┌─────────────┼──────────────┐
              │             │              │
              ▼             ▼              ▼
          CABINET        COMPONENT      HARDWARE
          RULES           RULES           RULES
              │             │              │
              └─────────────┼──────────────┘
                            ▼
                       FREECAD CORE
                  Part / PartDesign / Body
                            │
                            ▼
                      COCO_4C
                            │
                   ┌────────┴────────┐
                   │                 │
                App::Link         App::Link
                   │                 │
                   ▼                 ▼
                 PANEL             PANEL
                   │
                   ▼
             MANUFACTURING
                   │
       ┌───────────┼────────────┐
       │           │            │
       ▼           ▼            ▼
    CUTLIST       BOM        MACHINING
       │           │            │
       └───────────┼────────────┘
                   ▼
                TECHDRAW
                   │
                   ▼
                  CAM
                   │
                   ▼
                 CNC
```

---

# 16. El stack concreto

| Capa VDO              | Tecnología                                  |
| --------------------- | ------------------------------------------- |
| Motor CAD             | **FreeCAD 1.x**                             |
| Parámetros            | **Spreadsheet + aliases**                   |
| Variables avanzadas   | **VarSet / propiedades VDO**                |
| Geometría simple      | **Part**                                    |
| Piezas complejas      | **Part Design / Body**                      |
| Carpintería           | **Woodworking Workbench**                   |
| Generación automática | **Python VDO**                              |
| Biblioteca            | **FCStd + App::Link**                       |
| Instanciación         | **App::Link**                               |
| Ensamblaje            | **FreeCAD Assembly**                        |
| Documentación         | **TechDraw**                                |
| BOM                   | **VDO Manufacturing + Assembly BOM**        |
| CutList               | **VDO CutList**                             |
| Mecanizados           | **VDO Manufacturing Features**              |
| CNC                   | **FreeCAD CAM**                             |
| Datos intercambiables | **CSV / DXF / G-code / eventualmente JSON** |

---

# 17. Qué NO usaría como núcleo

### ❌ AIGenFurniture

No porque sea malo. Al contrario: su UX es muy cercana a lo que necesitamos.

Pero actualmente es **0.1.6** y está explícitamente en desarrollo. ([FreeCAD][5])

Lo usaría como:

> **referencia de UX y generación de estructura.**

---

### ❌ Cubinets

Es conceptualmente excelente y su arquitectura de templates es muy interesante. Pero actualmente aparece como **0.1.0-demo**, con roadmap todavía en evolución. ([FreeCAD][5])

Lo usaría como:

> **referencia de arquitectura paramétrica y CutList.**

---

### ❌ Assembly4 como núcleo

Muy potente, pero es una solución de ensamblaje basada en LCS + expresiones + App Links. ([GitHub][10])

No necesitamos convertir cada módulo de carpintería en un problema de ensamblaje mecánico.

---

### ❌ A2plus

No lo elegiría para una arquitectura nueva. FreeCAD actualmente tiene Assembly incorporado y la propia documentación señala que Assembly2 está sin mantenimiento; además los workbenches de ensamblaje no son intercambiables dentro del mismo documento. ([GitHub][13])

---

# 18. Y finalmente: dónde queda `COCO_4C`

Creo que ahora podemos redefinirlo correctamente.

`COCO_4C` **no es una pieza**.

Es un:

> **Product Template / Cabinet Generator Instance**

Por ejemplo:

```text
COCO_4C
│
├── Params
│    ├── width
│    ├── height
│    ├── depth
│    ├── thickness
│    └── ...
│
├── Rules
│    ├── side_panel
│    ├── top
│    ├── bottom
│    ├── back
│    └── ...
│
├── Components
│    ├── PANEL_LAT_IZQ
│    ├── PANEL_LAT_DER
│    ├── PANEL_BASE
│    ├── PANEL_TECHO
│    └── TRASERA
│
├── Manufacturing
│    ├── pieza_tablero
│    ├── edges
│    └── machining
│
└── Assembly
```

Y entonces:

```text
COCO_4C
```

recibe:

```text
600
720
580
18
```

y **genera su estructura**.

No necesitamos que `PANEL_LAT_IZQ` descubra quién es su padre mediante una expresión.

---

# La idea central

La arquitectura que yo congelaría ahora para Veta de Oro es:

> **Spreadsheet define → Python decide → FreeCAD modela → App::Link instancia → Assembly ensambla → Manufacturing describe → TechDraw documenta → CAM fabrica.**

Y **Woodworking aporta las herramientas específicas de carpintería**, mientras AIGenFurniture y Cubinets nos sirven como referencias de diseño del generador, no como dependencias estructurales. ([FreeCAD][3])

Eso además resuelve la contradicción que teníamos: **sí podemos conservar la idea Matrioshka**, pero la dependencia paramétrica ya no depende de que un hijo "busque" propiedades de su contenedor. La parametrización fluye desde un **modelo de datos explícito**, y los Links se encargan de reutilizar componentes.

### El siguiente paso que haría

Antes de programar una sola línea de VDO, haría un **prototipo vertical mínimo**:

```text
Params
  ↓
COCO_4C
  ↓
Generate Structure
  ↓
4 paneles
  ↓
pieza_tablero + cantos
  ↓
CutList
```

Si ese prototipo funciona, después añadimos:

```text
COCO_4C
   ↓
App::Link
   ↓
MUEBLE
   ↓
PROYECTO
```

y finalmente:

```text
mecanizados → TechDraw → CAM → CNC
```

Así no volvemos a caer en el problema actual de intentar resolver **la arquitectura completa mediante expresiones antes de haber definido correctamente el modelo de datos**. ([GitHub][14])

[1]: https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Spreadsheet_Workbench.md?utm_source=chatgpt.com "FreeCAD-documentation/wiki/Spreadsheet_Workbench.md at main · FreeCAD/FreeCAD-documentation · GitHub"
[2]: https://github.com/foreachidea/Cubinets?utm_source=chatgpt.com "GitHub - foreachidea/Cubinets: Cubinets is a FreeCAD Workbench for furniture makers, developed to simplify and accelerate design process. Visualise Cabinet Assemblies in minutes using Parametric Templates and Generate Cut Lists instantly. · GitHub"
[3]: https://www.freecad.org/addons.php?lang=es&utm_source=chatgpt.com "FreeCAD: Su modelador paramétrico en 3D"
[4]: https://github.com/dprojects/Woodworking/releases?utm_source=chatgpt.com "Releases · dprojects/Woodworking · GitHub"
[5]: https://www.freecad.org/addons.php?lang=es_ES&utm_source=chatgpt.com "FreeCAD: Su modelador paramétrico en 3D"
[6]: https://www.reddit.com/r/FreeCAD/comments/1rcdygf/i_built_a_freecad_cabinet_generator_im_looking/?utm_source=chatgpt.com "I built a FreeCAD cabinet generator, I'm looking for feedback from cabinetmakers"
[7]: https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Release_notes_0.19.md?utm_source=chatgpt.com "FreeCAD-documentation/wiki/Release_notes_0.19.md at main · FreeCAD/FreeCAD-documentation · GitHub"
[8]: https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Assembly_Workbench.md?utm_source=chatgpt.com "FreeCAD-documentation/wiki/Assembly_Workbench.md at main · FreeCAD/FreeCAD-documentation · GitHub"
[9]: https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Release_notes_1.1.md?utm_source=chatgpt.com "FreeCAD-documentation/wiki/Release_notes_1.1.md at main · FreeCAD/FreeCAD-documentation · GitHub"
[10]: https://github.com/FarmingSoul/ASM4_MOD_FS/blob/main/TECHMANUAL.md?utm_source=chatgpt.com "ASM4_MOD_FS/TECHMANUAL.md at main · FarmingSoul/ASM4_MOD_FS · GitHub"
[11]: https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/TechDraw_View.md?utm_source=chatgpt.com "FreeCAD-documentation/wiki/TechDraw_View.md at main · FreeCAD/FreeCAD-documentation · GitHub"
[12]: https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/CAM_Workbench.md?utm_source=chatgpt.com "FreeCAD-documentation/wiki/CAM_Workbench.md at main · FreeCAD/FreeCAD-documentation · GitHub"
[13]: https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Assembly.md?utm_source=chatgpt.com "FreeCAD-documentation/wiki/Assembly.md at main · FreeCAD/FreeCAD-documentation · GitHub"
[14]: https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Expressions.md?utm_source=chatgpt.com "FreeCAD-documentation/wiki/Expressions.md at main · FreeCAD/FreeCAD-documentation · GitHub"
