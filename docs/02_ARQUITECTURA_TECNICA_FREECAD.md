# 02 — Arquitectura Técnica FreeCAD (Pilar 2)

**Sistema:** VDO (Veta de Oro) — FreeCAD 1.1+
**Estado:** Definitivo — sin placeholders

---

## Modelo Canónico de 3 Dimensiones Ortogonales

Este documento desarrolla la **Dimensión 2 (Arquitectura de Software en 7 Capas)** y la **Dimensión 3 (Flujo Cognitivo del Usuario en Pantalla)**. La Dimensión 1 (Lógica de Negocio y Dominio de Carpintería) vive en `01_LOGICA_NEGOCIO_Y_CARPINTERIA.md`.

La **Axioma de Integración** establece: la Lógica de Negocio Pura (Dimensión 1) reside y se protege en las **Capas 0 y 1** de código, aislada de FreeCAD para que nunca se contamine.

---

## Dimensión 2 — Arquitectura de Software en 7 Capas

Cada capa responde a: *"¿Dónde y cómo se programa cada línea de código?"*

| Capa | Prefijo de archivo | Responsabilidad | Tecnologías permitidas |
|:-----|:-------------------|:----------------|:-----------------------|
| **Capa 0** | `vdo_math_*` | Matemáticas puras, algoritmos, DTOs, resolución de layout, marco de ejes. Cero FreeCAD, cero Qt. | Python stdlib, `json`, `math` |
| **Capa 1** | `vdo_hub_*` | Catálogos comerciales, manifiesto, datos de taller, especificaciones, rutas, detección de configuración. Fuente única de verdad. | Python, `json` |
| **Capa 2** | `vdo_cad_*` | Motor Geométrico CAD: `Part::FeaturePython`, entidades 3D, Shape nulo en contenedores, ViewProviders base, Placement. | `FreeCAD as App`, `Part`, `json` |
| **Capa 3** | `vdo_cad_*` | Interacción 3D y Enlace: ViewProviders especializados, Snapping, `claimChildren()`, colocación con snap (Draft) + fallback Coin3D. | `FreeCAD as App`, `Part`, `if App.GuiUp:` |
| **Capa 4** | `vdo_ui_*` | Interfaz de Usuario y Design System: TaskPanels por pestañas, widgets 2D, controles Qt, `VDOTransactionMixin`. | Qt, `PySide`, `FreeCADGui` (tras `if App.GuiUp:`) |
| **Capa 5** | `vdo_cam_*` | Producción, CAM y Documentación: TechDraw Dossier, Nesting MaxRects, exportación CSV/BOM, despiece. | TechDraw, `csv`, `DXF`, `SVG` |
| **Capa 6** | `vdo_devops_*` | Cloud, Sync & DevOps: sincronización, BBDD de precios, scripts de despliegue `user.cfg`. | Python, red, BBDD |

> **Regla de desacoplamiento:** La lógica de negocio pura (Capas 0 y 1) nunca importa `FreeCADGui`, `Qt`, `PySide` ni `Coin3D`. Todo acceso visual se protege con `if App.GuiUp:`.

---

## Dimensión 3 — Flujo Cognitivo del Usuario en Pantalla

Cada paso responde a: *"¿Qué pasos sigue el ser humano frente a la computadora?"*

| Paso | Capa de Flujo | Acción del usuario | Pantalla / Interacción |
|:-----|:--------------|:-------------------|:-----------------------|
| **Paso 1** | Capa 0 Flujo | Levantar muros en 2D/3D | Entorno Arquitectónico BIM (espacio, muros, aberturas) |
| **Paso 2** | Capa 1 Flujo | Insertar muebles (prohibido piezas sueltas) | Toolbar Spawner 3D en canvas |
| **Paso 3** | Capa 2 Flujo | Configurar módulo por pestañas | TaskPanel Contextual VDO (ventana unificada por pestañas) |
| **Paso 4** | Capa 3 Flujo | Salida a fabricación | Dossier TechDraw, Nesting 2D, BOM CSV |

---

## 1. Desacoplamiento Estricto App vs. Gui

FreeCAD implementa un patrón Modelo-Vista. La capa de datos (`App`) opera con independencia total de la plataforma gráfica; la capa de interfaz (`Gui`) administra los nodos del visor tridimensional basado en Coin3D/Open Inventor.

```
CAPA DE DATOS (App)                              CAPA DE INTERFAZ GRÁFICA (Gui / Coin3D / Qt)
┌─────────────────────────────┐                 ┌─────────────────────────────────────────────┐
│ App::DocumentObject         │                 │ Gui::ViewProviderDocumentObject             │
│   └─ App::GeoFeature        │                 │   └─ Gui::ViewProviderPart                  │
│       └─ Part::Feature      │                 │       └─ ViewProviderProxy (Python)         │
│           └─ Part::FeaturePython  │           │               claimChildren()               │
│           (VDO módulo / contenedor)│           │               controla Tree View            │
│           Propiedad: App::PropertyLinkListChild │       └─ claimChildren3D() (NO sobrescribir)│
└─────────────────────────────┘                 └─────────────────────────────────────────────┘
```

**Reglas de desacoplamiento:**

| Regla | Especificación |
|-------|----------------|
| R-01 | `vdo_*_core.py` nunca importa `Qt`, `PySide`, `FreeCADGui` ni `Coin3D`. Solo `FreeCAD as App`, `Part`, `json`, `os`. |
| R-02 | Todo acceso a `FreeCADGui` / `ViewObject` / iconos se guarda tras `if App.GuiUp:`. |
| R-03 | `execute()` reconstruye solo el `Shape` y **nunca** toca `Placement` — tampoco el de sus hijos. La pose de los insertos se propaga en `onChanged(fp, "Placement")`, fuera del ciclo de recompute: como el padre depende de sus hijos, su `execute()` corre *después* del de ellos, y escribirles el `Placement` allí los dejaba `still touched after recompute` en cada ciclo, sin converger nunca. |
| R-04 | `execute()` **nunca** invoca `doc.addObject()` ni `doc.removeObject()` (no muta topología dentro del ciclo de recompute). |
| R-05 | La jerarquía de datos reside en `App::PropertyLinkListChild` (capa de datos), no solo en `claimChildren()` (capa visual). |
| R-06 | `claimChildren()` es exclusivamente un reflejo visual de lo ya definido en la capa de datos. |

---

## 2. Protocolo de Creación de Módulos (Axiomas T1–T8)

Todo módulo VDO (COCO, cajón, panel, puerta, zócalo, tambor) debe cumplir los ocho axiomas definidos en `VDO_PROTOCOLO_CREACION_MODULOS.md`.

| ID | Axioma | Especificación |
|----|--------|----------------|
| **T1** | Contenedor = `Part::FeaturePython` | Nunca usar `App::Part` ni `DocumentObjectGroup` como contenedor principal. `App::Part` no acepta Proxy en Python. |
| **T2** | Sin grupos intermedios | No crear carpetas `App::DocumentObjectGroup` automáticas (`Estructura_Carcasa`, `Cajones`, `Divisiones`). Los paneles cuelgan directamente del padre lógico. |
| **T3** | Jerarquía de datos en `PropertyLinkListChild` | La relación padre-hijo se expresa con `App::PropertyLinkListChild` (o `Hijos` reusada). Funciona en modo headless. **El retroenlace del hijo (`ParentCOCO`) tiene que ser `App::PropertyLinkHidden`**: `LinkListChild` sí entra en el grafo de dependencias (el padre depende de sus hijos), así que un `App::PropertyLink` normal en el hijo cierra un ciclo y FreeCAD aborta el orden de recompute con `The graph must be a DAG.`, dejando los objetos `still touched after recompute` (geometría sin reconstruir). |
| **T4** | `claimChildren()` retorna hijos directos | El `ViewProvider` retorna los objetos hijos directos del `PropertyLinkListChild`, nunca grupos intermedios. Si no hay hijos, retorna `[]`. |
| **T5** | `Shape` del contenedor nulo | `fp.Shape = Part.Shape()` (nulo) o, opcionalmente, wireframe de bounding box para selección. Evita Z-fighting y doble masa en CAM/Nesting. |
| **T6** | `onDelete()` para borrado en cascada | Implementar `onDelete()` en el proxy del módulo para eliminar objetos hijos dependientes al borrar el padre. Previene objetos huérfanos. |
| **T7** | `App.GuiUp` para todo lo de `Gui` | Todo acceso a `FreeCADGui`, `ViewObject`, iconos, se protege con `if App.GuiUp:`. Portabilidad headless (FreeCADCmd, scripts, CI). |
| **T8** | `dumps()`/`loads()` pueden retornar `None` | Si la forma se regenera en `recompute` y las propiedades persisten, la serialización puede simplificarse. |

### 2.1 Estructura de archivos obligatoria por módulo

```
/Macro/
  vdo_cad_X_core.py       # Lógica geométrica pura + FeaturePython + ViewProvider (no Qt/Gui)
  vdo_ui_X_task.py        # Task panel de configuración (hereda VDOTransactionMixin)
  tests/test_vdo_X_core.py  # Tests unitarios de calcular_geometria_X (puro, sin FreeCAD)
```

**Dependencias permitidas en `vdo_cad_X_core.py`:**
- `FreeCAD as App`, `Part`, `json`, `os`
- `vdo_cad_module_props as VDO_MOD` (propiedades comunes de colocación)
- `vdo_cad_view_base.VDOViewProviderBase` (ViewProvider base)
- `vdo_hub_defaults as VDO_D` (valores del manifiesto)
- `vdo_math_frames` (marco de ejes y vocabulario de lados)

**No importar Qt ni FreeCADGui en `_core.py`.**

### 2.2 Contrato del núcleo (`vdo_cad_X_core.py`)

```python
class XFeature:
    def __init__(self, obj):
        # Propiedades dimensionales propias
        obj.addProperty("App::PropertyString", "VDO_Tipo", "VDO", ...).VDO_Tipo = "x"
        obj.addProperty("App::PropertyString", "VDO_Subtipo", "VDO", ...)
        obj.addProperty("App::PropertyString", "VDO_Material_Ref", "VDO", ...)
        obj.addProperty("App::PropertyString", "VDO_Paneles_JSON", "VDO", ...)
        # Jerarquía de datos (Axioma T3)
        obj.addProperty("App::PropertyLinkListChild", "Hijos", "Estructura Lógica", "...")
        obj.addProperty("App::PropertyLink", "ParentCOCO", "VDO", "...")
        obj.addProperty("App::PropertyPlacement", "LocalPlacement", "VDO", "...")
        VDO_MOD.add_common_props(obj)  # VDO_RotacionZ, VDO_Anclaje, etc.
        obj.Proxy = self

    def execute(self, fp):
        # Axioma T5: Shape del padre nulo (sin duplicación geométrica).
        fp.Shape = Part.Shape()
        fp.VDO_Paneles_JSON = json.dumps(geo["piezas"], ensure_ascii=False)

    def onDelete(self, fp, subelements):
        # Axioma T6: borrado en cascada de hijos.
        doc = fp.Document
        for hijo in getattr(fp, "Hijos", []) or []:
            if hijo is not None and doc.getObject(hijo.Name):
                doc.removeObject(hijo.Name)
        return True

    def dumps(self):
        return None

    def loads(self, state):
        return None
```

### 2.3 ViewProvider

```python
class ViewProviderX(VDOViewProviderBase):
    MENU_LABEL = "Propiedades del X"
    ICON = "vdo_X.svg"

    def __init__(self, vobj):
        super().__init__(vobj)
        if App.GuiUp:
            vobj.Visibility = True

    def get_panel_class(self):
        from vdo_ui_X_task import XTaskPanel
        return XTaskPanel

    def claimChildren(self):
        # Axioma T4: reflejo visual de la capa de datos.
        if App.GuiUp is False:
            return []
        hijos = getattr(self.Object, "Hijos", None) or []
        return [h for h in hijos if h is not None]

    def getIcon(self):
        # Las rutas SIEMPRE salen de VDO._paths, nunca de
        # getUserMacroDir(): el workbench vive en Mod/, no en Macro/.
        if self.ICON:
            from VDO._paths import get_icon_path
            icon_path = get_icon_path(self.ICON)
            if os.path.exists(icon_path):
                return icon_path
        return "Part_Box"
```

> **`claimChildren()` va en la clase base.** `VDOViewProviderBase` lo
> implementa leyendo `fp.Hijos`, así que todo módulo lo hereda. Definirlo
> sólo en el ViewProvider concreto es una trampa: `make_coco()` instala
> preferentemente `DragableViewProvider`, y mientras ese no lo definió el
> COCO aparecía sin hijos y su carcasa suelta en la raíz del documento.

> **`onDelete()` lo invoca FreeCAD en el proxy del VIEWPROVIDER**, no en el
> del objeto de datos. El ejemplo de §2.2 lo coloca en la clase de datos
> porque ahí es donde vive la lógica de cascada del módulo;
> `VDOViewProviderBase.onDelete()` hace de puente y la delega. Sin ese
> puente los `onDelete()` de datos no se ejecutan nunca y borrar un COCO
> deja todos sus paneles huérfanos.

### 2.4 Factory

```python
def make_x(configuracion):
    doc = App.getActiveDocument()
    if doc is None:
        App.Console.PrintError("[VDO] No hay documento activo.\n")
        return None
    nombre = configuracion.get("nombre", "Modulo_X")
    obj = doc.addObject("Part::FeaturePython", nombre)
    XFeature(obj)
    if App.GuiUp:
        ViewProviderX(obj.ViewObject)
    doc.recompute()
    return obj
```

---

## 3. Arquitectura de Reactividad Híbrida (TaskPanel Clásico Unificado)

Este es el **patrón ganador canónico** (ver C-03 en la Matriz de Contradicciones). Reemplaza al inspector lateral flotante descartado (`vdo_universal_inspector.py`).

### 3.1 ¿Qué se descartó?

El **Inspector Lateral Flotante** (`vdo_universal_inspector.py` y `vdo_inspector_arbol.py`) está **deprecated y retirado**. Escuchaba `Gui.SelectionObserver` en segundo plano y provocaba condiciones de carrera (*race conditions*) con Coin3D, corrompiendo el árbol Qt al mutar el DAG como reacción inmediata a eventos de selección. Toda edición de módulos VDO pasa exclusivamente por el **TaskPanel Clásico Unificado (`CocoUnifiedTaskPanel`)**. No existe otro canal de edición activo.

### 3.2 Patrón Híbrido Reactivo — `CocoUnifiedTaskPanel`

El `CocoUnifiedTaskPanel` es el **único canal de edición activo** de VDO. Es una ventana modal/determinista que mantiene el foco, implementando el Patrón Híbrido Reactivo:

| Pestaña | Comportamiento reactivo | Mecanismo |
|---------|------------------------|-----------|
| **Estructura** | Reactividad en vivo: cada clic en el corte transversal 2D (`VDOChassisControllerWidget`) actualiza las propiedades del objeto y ejecuta `doc.recompute()` en vivo dentro de la transacción abierta. | `recompute()` inmediato dentro de transacción abierta |
| **Divisiones** | Reactividad en vivo: el visor 2D (`CocoPreview2D`) responde en **0 ms** (memoria Qt). El 3D se actualiza en tiempo real mediante un **temporizador Debounce de 100–250 ms** que llama a `doc.recompute()` al detenerse la interacción del usuario. | Debounce timer (control de frecuencia, no diferimiento) |

El panel clásico **no tiene entropía interna**: no hay observador de selección en segundo plano, no hay mutación del DAG fuera de transacción, y no hay duplicidad de paneles. Toda la reactividad vive dentro del ciclo de transacción del TaskPanel.

### 3.3 Ciclo de vida de transacciones

```
focusIn  →  openTransaction("Edición VDO")   [transacción abierta]
            ↓
    Usuario modifica parámetros (UI responde 0 ms, reactividad en vivo)
            ↓
    Timer 100–250 ms (debounce) → recompute() dentro de transacción abierta
            ↓
focusOut / editingFinished → commitTransaction()
            ↓
    Usuario pulsa "Aceptar" → _vdo_commit() (consolida el historial de Undo como 1 bloque)
    Usuario pulsa "Cancelar" → _vdo_abort() (revierte el modelo 3D en vivo al estado previo)
```

**Transaccionalidad limpia:**
- El botón **"Aceptar"** no inicia el cálculo; **consolida la transacción** del historial mediante `_vdo_commit()`. El Undo registra **1 bloque por gesto de edición**, no micro-transacciones sueltas.
- El botón **"Cancelar"** ejecuta `_vdo_abort()` y **revierte el modelo 3D en vivo** a su estado previo, descartando todos los cambios de la sesión de edición.
- Todo `doc.recompute()` está envuelto en `openTransaction`/`commitTransaction`. Nunca se llama `recompute()` fuera de una transacción.

### 3.4 Implementación de referencia (`vdo_ui_task_base.py` — `VDOTransactionMixin`)

```python
class VDOTransactionMixin:
    def focusInEvent(self, event):
        super().focusInEvent(event)
        doc = App.ActiveDocument
        if doc:
            doc.openTransaction("Edición Paramétrica VDO")
        self._vdo_transaction_open = True

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self._vdo_commit()

    def _vdo_debounce_recompute(self):
        # Timer 100–250 ms: control de frecuencia, no diferimiento.
        self._timer.stop()
        self._timer.start(self._debounce_ms)

    def _vdo_on_debounce_expire(self):
        doc = App.ActiveDocument
        if not doc or not self._vdo_transaction_open:
            return
        try:
            doc.recompute()
            # commit se hace en focusOut / accept
        except Exception as e:
            doc.abortTransaction()
            self._vdo_transaction_open = False
            raise

    def _vdo_commit(self):
        if not self._vdo_transaction_open:
            return
        doc = App.ActiveDocument
        if doc:
            doc.commitTransaction()
        self._vdo_transaction_open = False

    def _vdo_abort(self):
        if not self._vdo_transaction_open:
            return
        doc = App.ActiveDocument
        if doc:
            doc.abortTransaction()
        self._vdo_transaction_open = False

    def accept(self):
        self._vdo_commit()
        super().accept()

    def reject(self):
        self._vdo_abort()
        super().reject()
```

---

## 4. Flujo de Creación de Módulos (Capa 1 Flujo — Toolbar Spawner 3D)

El flujo de creación sigue el patrón determinista:

1. Crear objeto **oculto** dentro de una sola transacción.
2. Abrir Task Panel del módulo (`auto_transaction=False`).
3. Colocar con el mouse (`Gui.Snapper.getPoint` con fallback Coin3D).
4. Commit al soltar; cancelar borra el objeto y aborta la transacción.

**Botones de nivel 1 (primitivas maestras):**
- Nuevo COCO (`vdo_coco_4c.FCMacro`)
- Panel Libre L1 (`vdo_panel_estandar.FCMacro`, `vdo_panel_fachada.FCMacro`)
- Tambor / División (`vdo_panel_division.FCMacro`)
- Zócalo (`vdo_zocalo.FCMacro`)

**Botón de nivel 3 (desplegable Módulos Compuestos L3):** escritorios, centros de TV, camas, armarios, cocinas, estanterías.

---

## 4.1 Capa 5 — TechDraw Dossier Carpintero (Salida a Fabricación)

La Capa 5 genera planos orientados a **taller y montaje** (no planos arquitectónicos tradicionales). Se compone de tres láminas canónicas:

### 4.1.1 Lámina de Implantación C0
- Planta del espacio acotada muro a muro.
- Axonometría general **sin muros frontales** (algoritmo anti-muro: se ocultan los muros que ocluyen el mueble para claridad de lectura).
- Orientada a la colocación del módulo en el recinto arquitectónico.

### 4.1.2 Lámina de Replanteo de Montaje
- Alzado contra pared con **cotas verticales desde NPT ($Z=0$)**.
- Alturas de amarre de cada componente.
- Notas de obra específicas para el montador.

### 4.1.3 Ficha Técnica por Mueble L2
1. **Isométrica de casco abierto:** sin frentes, mostrando el armado estructural (laterales, tapa, base, fondo, divisiones).
2. **Frontal de casco:** acotando luces libres netas ($w, h$) y alturas de repisas.
3. **Frontal cerrado:** verificando holguras de fachada (calles de $2\text{ mm}$, canal Gola).
4. **Tabla BOM física:** listado de tableros L1 con cantos $N, S, E, O$, rol, material y operación.

---

### 4.1.4 Exportación de Planos Automáticos — Sistema de Láminas por Capas Informacionales (TechDraw Nativo / Etch Draw)

El subsistema de exportación de visuales basado en TechDraw nativo (etch draw) genera el dossier de salida a fabricación organizado en 4 Capas Informacionales Progresivas más una Capa Anexa de Herrajes y Capturas Vinculadas. Cada captura visual aparece vinculada inmediatamente a su entidad hermana (Espacio o Módulo). El dossier se reestructura eliminando la saturación de planos arquitectónicos convencionales; la información se distribuye progresivamente según el rol del destinatario (instalador en obra, montador, carpintero de taller).

Estructura del dossier por espacio (Ej. COC-01):

1. Capa Arquitectura y Replanteo (subdividida): L01A (Obra Civil) + L01B (Huellas e Instalación).
2. Capa Vistas de Conjunto: L02 (Axonometría Anti-Muro + Capturas de Espacio).
3. Capa por Tramos de Montaje: L03A (Tramo Norte), L03B (Tramo Este / Isla).
4. Capa por Módulo (Fichas Unitarias): L04..LN (un COCO por hoja, 4 cuadrantes de taller).
5. Capa Herrajes y Capturas Vinculadas: hojas hermanas contiguas al módulo o al espacio.

#### Capa 1: Arquitectura y Replanteo (subdividida para máxima claridad)

Para que el plano sea legible en la obra, se separa la medición de las paredes del replanteo de los muebles e instalaciones en dos láminas independientes.

**Lámina 1A: Obra Civil y Verificación de Escuadras**

- Objetivo: recibir el recinto en bruto y diagnosticar deformaciones en los muros.
- Proyección: Cenital Top pura (vector Z). Escala: 1:20.
- Información Técnica:
  - Muros existentes con cotas de largo total y espesores.
  - Cotas a vanos de puertas y ventanas (anchos libres y antepechos).
  - Líneas de Escuadra (Cian): triangulaciones diagonales de esquina a esquina con su medida en milímetros para verificar si los ángulos de encuentro son de 90° o si hay desplomes.
  - Cero muebles dibujados (plano totalmente despejado para la cinta métrica del técnico).

**Lámina 1B: Huella de Implantación e Instalaciones en Piso**

- Objetivo: marcar en el suelo de la obra dónde cae cada mueble y validar tomas de servicio.
- Proyección: Cenital Top idéntica a la 1A.
- Información Técnica:
  - Líneas discontinuas en piso: huella exterior de todos los módulos bajos, columnas e islas.
  - Puntos de servicio en suelo: desagües de fregadero/lavavajillas, acometidas de agua, salidas de gas y tomas de corriente en piso.
  - Cotas de referencia: distancia de cada acometida respecto a la esquina de inicio (X=0, Y=0) para confirmar que ninguna tubería caiga justo donde coincide el lateral de un mueble.

#### Capa 2: Vistas de Conjunto (La Habitación Integrada)

**Lámina 2: Axonometría General de Implantación (Algoritmo Anti-Muro)**

- Objetivo: comprensión espacial 3D completa de la habitación amueblada.
- Proyección: Isométrica limpia (vector (1, -1, 1)).
- Información Técnica:
  - Corte dinámico anti-muro: las paredes que dan la cara a la cámara se apagan o se bajan a altura de zócalo (100 mm), dejando al descubierto alacenas, bajo mesadas y columnas.
  - Muros de respaldo visibles: las paredes de apoyo permanecen en línea fina como referencia de fondo.
  - Globos de etiquetado (Balloons): flechas directrices que identifican cada mueble con su código de zona (COC-01-M01, COC-01-M02, PANEL-AJUSTE).
- Capturas de Espacio Hermanadas: si el diseñador tomó capturas tipadas con identificador de espacio (VDO_Target = ESPACIO_Cocina), se insertan en un panel lateral de esta misma lámina o en su hoja inmediatamente contigua:
  - Foto del nicho existente con tuberías vistas.
  - Foto del desnivel de piso con advertencia de cuñas.

#### Capa 3: Por Tramos de Montaje (Los Alzados de Pared)

Se genera una lámina por cada pared activa o isla. No se mezclan tramos en un solo dibujo.

Lámina de tramo (Ej. Pared Norte):

┌──────────────────────────────────────────────────────────────────────────────────┐
│ ALZADO FRONTAL ORTOGONAL AL TRAMO                                                │
│                                                                                  │
│      [Alacena M03]            [Alacena M04]                                      │
│     ┌──────────────┐         ┌──────────────┐                                    │
│     │              │         │              │                                    │
│  ───┴──────────────┴─────────┴──────────────┴─────────────────────────── +2050mm │
│  ───┬─────────────────────────────────────────────────────────────────── +1500mm │
│     │ COTA LIBRE ENTRE MESÓN Y ALACENAS: 550 mm                                  │
│  ───┴─────────────────────────────────────────────────────────────────── +900 mm │
│     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────────┐         │
│     │ BajoMes M01  │ │ BajoMes M02  │ │ Hueco Lavav. │ │ Columna Horno │         │
│     │ (Cajonero)   │ │ (Fregadero)  │ │ (600 mm)     │ │ (Torre M05)   │         │
│  ───┴──────────────┴─┴──────────────┴─┴──────────────┴─┴───────────────┴ +100 mm │
│ ======================================================================== Z = 0   │
├──────────────────────────────────────────────────────────────────────────────────┤
│ COTAS Y REQUISITOS DEL TRAMO:                                                    │
│ • Cotas horizontales continuas desde la esquina izquierda (X=0).                 │
│ • Alturas de perforación para anclajes de colgado (+2050 mm).                    │
│ • Ubicación de enchufes de pared y salidas de agua traseras.                     │
└──────────────────────────────────────────────────────────────────────────────────┘

- Información Técnica:
  - Cotas Z desde Piso Terminado (0 mm): nivel de zócalo, nivel de mesón, altura libre entre mesón y alacenas, y cota exacta del riel de anclaje a muro.
  - Cadena continua X: medidas acumuladas de cada mueble y vano para que el montador marque con lápiz en la pared de una sola tirada de cinta métrica.
  - Puntos de muro: tomas de corriente ocultas tras electrodomésticos, enchufes sobre mesón y refuerzos de drywall requeridos.

#### Capa 4: Por Módulo (Fichas Unitarias de Fabricación)

Una hoja por cada mueble individual fabricable. Su distribución fija en 4 cuadrantes elimina el ruido abstracto y se centra en el carpintero de banco y el armador:

┌──────────────────────────────────────────┬──────────────────────────────────────────┐
│ CUADRANTE 1: ISOMÉTRICA DE CASCO CRUDO   │ CUADRANTE 2: FRONTAL DE VANOS LIBRES     │
│ • Carcasa armada sin frentes.            │ • Casco de frente sin puertas.           │
│ • Muestra el sistema de ensamble         │ • COTAS DE LUZ ÚTIL: ancho y alto libre  │
│   (lateral monta sobre base, o base      │   de cada hueco (para saber si entra el  │
│   abraza al lateral).                    │   accesorio o canasto extraíble).        │
│ • Dirección de la veta del material.     │ • COTAS A EJES: altura milimétrica de    │
│ • Posición de fondos ranurados / clavados│   perforación para repisas regulables.   │
├──────────────────────────────────────────┼──────────────────────────────────────────┤
│ CUADRANTE 3: FRONTAL CERRADO (FACHADAS)  │ CUADRANTE 4: INFORMACIÓN DE TALLER       │
│ • Vista con frentes montados.            │ 1. DESPIECE ESENCIAL DE PLACAS:          │
│ • Acotado de holguras / fugas (2 o 3 mm).│    - Nombre de pieza y cantidad.         │
│ • Tipo de fachada: parche total,         │    - Medidas de corte netas.             │
│   semi-parche o frente embebido.         │    - Mapeo de tapacantos (L1, L2, A1, A2)│
│ • Posición y distancia de uñeros, perfil │ 2. HERRAJES ASIGNADOS AL MÓDULO:         │
│   gola o perforaciones de tirador.       │    - Tipo de corredera, patas, bisagras. │
│                                          │ 3. 📝 REQUERIMIENTOS DEL CLIENTE:        │
│                                          │    "Frente con veta continua hacia M02"  │
│                                          │    "Dejar fondo retranqueado 50mm x tubo"│
│                                          │    "Sin tirador: sistema push to open"   │
└──────────────────────────────────────────┴──────────────────────────────────────────┘

Ajuste en el Cuadrante 4: se elimina el cómputo abstracto de metros cuadrados, pesos teóricos y metros lineales totales. En su lugar, el espacio se aprovecha para el Despiece Directo, la Lista de Herrajes del Módulo y el cuadro de Requerimientos del Cliente / Notas de Montaje, que es el texto real que el carpintero necesita leer mientras arma.

#### Capa 5: Herrajes y Capturas Vinculadas (Hojas Hermanadas)

Las capturas ya no se envían a un anexo genérico al final del libro. El motor de planos las ubica inmediatamente contiguas a la entidad que las originó:

[Árbol de Documentación]
 │
 ├── 📄 COC-01_M01_Ficha_Fabricacion  (la lámina de 4 cuadrantes del mueble)
 └── 📄 COC-01_M01_Anexo_Detalles     (hoja hermana inmediata del MISMO mueble)

Contenido de la Hoja Hermana del Módulo:

1. Capturas Vectoriales Tipadas (VDO_Target = Modulo):
   - Detalle de Herraje: zoom vectorial del mecanismo de corredera oculta o del pistón elevable con cotas de fijación interna.
   - Detalle de Acabado: zoom al encuentro entre el frente y el uñero gola.
2. Ficha Técnica del Proveedor: especificación del herraje utilizado (código de fabricante, plantilla de perforación y brocas requeridas: copa de 35 mm, broca de 5 mm para pernos Euro).
3. Puntos Críticos de Calibración: advertencias de regulación de tornillos excéntricos de bisagras o ajustes de caída de cajón.

Resumen de la Experiencia Visual Resultante:

- El Instalador en Obra: abre la Lámina 1A para medir y escuadrar, la 1B para verificar tuberías en suelo, y las Láminas de Tramo para perforar y colgar los muebles a sus alturas exactas sin hacer cálculos mentales.
- El Carpintero en Taller: abre la Ficha Unitaria de su mueble, lee el despiece del Cuadrante 4, valida las luces útiles del Cuadrante 2 y revisa los requerimientos particulares del cliente sin distraerse con información de la habitación.
- Cero Ambigüedad: si un mueble tiene un mecanismo complejo, su hoja hermana de capturas técnicas está justo detrás, con la imagen congelada en el ángulo exacto que el diseñador seleccionó en el 3D.

---

## 5. Convención de Nombres de Objeto: Name vs Label

| Campo | Tipo | Características | Uso | Formato recomendado |
|-------|------|-----------------|-----|---------------------|
| **Name** | Identificador interno | Alfanumérico inmutable, solo `[_0-9a-zA-Z]`, sin espacios ni símbolos. | Código, enlaces `PropertyLink`, DAG | `[TipoModulo]_[Rol]_[ID]` (ej. `Cajon_Oculta_001`, `Panel_Lateral_Izq_001`) |
| **Label** | Etiqueta visible | UTF-8, modificable por el usuario, se muestra en Tree View. Actualizada dinámicamente con dimensiones. | Operario de taller, Tree View | `[Nombre Descriptivo] [[Largo x Ancho x Espesor] mm]` |

**Invariante:** `Name` nunca cambia tras la creación. `Label` puede regenerarse en cada `execute()` o `accept()`.

---

## 6. Disciplina de Nomenclatura de Archivos (AJUSTE 3)

**Convención obligatoria:** `Dominio_Entidad_Función`

| Prefijo | Capa de Código | Alcance | Ejemplo |
|---------|----------------|---------|---------|
| `vdo_math_*` | Capa 0 | Matemáticas y algoritmos puros (Cero GUI, Cero FreeCAD). | `vdo_math_layout.py` |
| `vdo_hub_*` | Capa 1 | Catálogos comerciales, datos y especificaciones. | `vdo_hub_manifest.py` |
| `vdo_cad_*` | Capas 2 y 3 | Entidades 3D (`FeaturePython`), ViewProviders y Placement. | `vdo_cad_coco_core.py` |
| `vdo_ui_*` | Capa 4 | TaskPanels por pestañas, widgets 2D y controles Qt. | `vdo_ui_coco_unified_task.py` |
| `vdo_cam_*` | Capa 5 | TechDraw Dossier, Nesting MaxRects y exportación CSV. | `vdo_cam_cajon_despiece.py` |
| `vdo_devops_*` | Capa 6 | Sincronización, BBDD y scripts de despliegue. | `vdo_devops_sync.py` |

---

## 7. 🔴 AJUSTE 1 — Blindaje de Puntos de Entrada Nativos de FreeCAD

Los siguientes nombres están **TERMINANTEMENTE PROHIBIDOS de renombrarse**. Permanecen con su nombre exacto en la raíz de `Macro/`:

| Archivo | Motivo de protección |
|---------|---------------------|
| `Init.py` | Nombre reservado de FreeCAD C++. Si se cambia, el Addon no carga. Registro en App core. |
| `InitGui.py` | Nombre reservado de FreeCAD C++. Si se cambia, el Addon no carga. Registro de comandos y workbench. |
| `vdo_manifest.json` | Manifiesto en raíz de macros. Las rutas relativas de carga dependen de este nombre exacto. |
| `vdo_hardware_catalog.json` | Catálogo de herrajes en raíz. Las rutas relativas de carga dependen de este nombre exacto. |
| `vdo_coco_4c.FCMacro` | Macro registrada en `user.cfg`. Conserva el atajo de teclado inyectado (COCO). |
| `vdo_panel_estandar.FCMacro` | Macro registrada en `user.cfg`. Conserva el atajo de teclado inyectado (PANE). |
| `vdo_herrajes.FCMacro` | Macro registrada en `user.cfg`. Conserva el atajo de teclado inyectado (HERJ). |

---

## 9. Design System y Especificación de UI (absorbido de `MANIFIESTO_DISENO_INTERFAZ_VDO.md`)

### 9.1 Paleta cromática Dark Mode oficial

Toda la UI VDO sigue una jerarquía cromática estricta de luminancia:

| Rol | Valor |
|-----|-------|
| Superficie base | `#141414` / `#1e1e1e` |
| Superficie interactiva | `#252525` / `#2b2b2b` |
| Bordes estructurales | `#3a3a3a` / `#444444` |
| Acentos activos | Azul `#007acc` / `#0098ff` |
| Tipografía primaria | `#e0e0e0` / `#ffffff` |
| Tipografía secundaria y cotas | `#888888` |

**Regla:** Prohibido forzar `background: #ffffff` sin fijar `color: #000000`. Todo botón conmutable debe aplicar `:checked` con iluminación en azul acento (`#007acc`), borde nítido (`#0098ff`) y texto contrastado (`#ffffff`).

### 9.2 Entrada numérica agnóstica (`VDO_DoubleSpinBox`)

**Axioma:** Un diseñador no debe luchar contra el teclado numérico de su sistema operativo.
- Acepta indistintamente coma (`,`) o punto (`.`) decimal, independientemente del locale (`es_ES`, `en_US`, `de_DE`).
- Permite fijar cotas de precisión milimétrica sin truncamiento accidental ni excepciones de parseo numérico.

### 9.3 Primitivas de UI del sistema

| Primitiva | Metáfora | Comportamiento | Ámbito |
|-----------|----------|----------------|--------|
| `VDOBoxControllerWidget` | Cuadrado 3 × 3 del tablero (Figma Box Model) | Clic en bordes enciende/apaga tiras; clic en esquinas cicla uniones (tope/inglete/marco); candado central conmuta uniforme vs. individual. | Reengroses de carcasa, zócalos, canteado perimetral, fajas de dilatación. |
| `PanelHeaderWidget` | Etiqueta de código de barras de taller | Solo lectura interactiva. Muestra dimensiones nominales netas y estado de 4 cantos (`FX`, `RIG`, `SMRG`). | Cabecera de todos los inspectores de piezas físicas. |
| `VanoInspectorWidget` | Calibrador de luz libre | Muestra Cota Nominal vs Cota Útil Neta. Casilla de subdivisión fractal de vano. | Pestaña "Vanos" del COCO. |
| `HardwareSelectorWidget` | Mostrador de ferretería industrial | Dropdown de marcas (Ducasse, Blum, Hettich, genéricas). Computa cotas CAD ($D_1, D_2$, Newtons, taladros) y costo en tiempo real. | TaskPanels de puertas y cajones. |

### 9.4 7 pilares de la interfaz VDO (resumen ejecutivo)

1. **Semiótica espacial directa:** el widget es el tablero; ninguna relación espacial se expresa con palabras si puede expresarse con topología.
2. **Dualidad ontológica:** prohibido mezclar vanos y piezas en la misma vista. Conmutador explícito Modo Vanos / Modo Estructura.
3. **Carné de identidad universal (`PanelHeaderWidget`):** mismo micropanel inmutable para cualquier entidad física.
4. **Poka-yoke radical:** la interfaz hace imposible formular errores geométricos ($V_{\text{colisión}} > 0$ no seleccionable).
5. **Lenguaje de taller:** erradicados regionalismos y anglicismos (ej. *retranqueo* → *separación del canto*, *pasante* → *de punta a punta*).
6. **Resiliencia gráfica:** iconos SVG puros en memoria (`QtSvg.QSvgRenderer`), dark mode estricto.
7. **Entrada numérica agnóstica:** `VDO_DoubleSpinBox` con coma/punto locale-independiente.

### 9.5 Rebanada vertical completa (Full Vertical Slice)

```
C0[Capa 0: Matemática y DTOs Puros] --> C1[Capa 1: Reglas de Taller y Poka-Yoke] --> C2[Capa 2: Motor de Sólidos 3D] --> C3[Capa 3: Planos de Fabricación y Despiece] --> C4[Capa 4: Semiótica Gráfica e Interfaz de Usuario]
```

Toda feature debe respetar las 5 capas. Regla de oro: si una función geométrica no tiene forma de seleccionarse, comprenderse e inspeccionarse visualmente con el lenguaje del carpintero y sin riesgo de colisión, **no está terminada**.

---

## 10. Toolbar Spawner 3D y Capas Cognitivas (absorbido de `DISENO_UI_CAPAS_COGNITIVAS_VDO.md`)

### 10.1 Modelo cognitivo: 4 capas de abstracción

| Capa | Nombre | Qué hace | Quién la provee | Entrada típica |
|------|--------|----------|-----------------|----------------|
| C0 | Espacio BIM | Planta 2D, muros, vanos, habitáculos | FreeCAD nativo (BIM/Arch) | Dibujo 2D → Levantamiento de muros |
| C1 | Primitivas maestras VDO | COCO, Panel Libre L1, Tambor, Zócalo | VDO Toolbar | Click en botón → colocación en canvas 3D |
| C2 | Habitante del vano | Vacío / Subdividir / Cajón / Puerta | Task Panel reactivo | Clic en COCO → elegir habitante |
| C3 | Módulos compuestos L3 | Escritorios, centros de TV, camas, armarios | Toolbar desplegable | Selección desde desplegable → ensamblaje |

### 10.2 Toolbar: Nivel 1 y Nivel 3

**Nivel 1 — Botones directos (primitivas maestras, Capa 1):**

| Botón | Script | Acción |
|-------|--------|--------|
| Nuevo COCO | `vdo_coco_4c.FCMacro` | Contenedor envolvente de 4 lados + fondo con Task Panel paramétrico |
| Panel Libre L1 | `vdo_panel_estandar.FCMacro` | Tablero atómico de melamina (dimensiones, espesor, cantos) |
| Tambor / División | `vdo_panel_division.FCMacro` | Elemento estructural vertical divisor |
| Zócalo | `vdo_zocalo.FCMacro` | Base de anclaje al piso |

**Nivel 3 — Desplegable "Módulos Compuestos L3" (Capa 3):** escritorios, centros de TV, camas, armarios, cocinas, estanterías. Cada entrada ejecuta la composición L3 correspondiente (matriz de COCOs + Paneles L1 posicionados relativamente).

**Botones eliminados / obsoletos:**
- "Crear Hoja" (`VDO_Crear_Hoja_Melumina.FCMacro`) → obsoleto como acción de usuario. La hoja global `Params_Melamina` se garantiza internamente por `vdo_guardian.vdo_guard()`.
- Herrajes (Gestor) en toolbar principal → se mueve a menú secundario.

### 10.3 Flujo de lista de corte / despiece (Capa manufactura)

- **Activación:** comando dedicado (no botón en toolbar). 3 modos: `seleccion` (`Gui.Selection.getSelectionEx()`), `grupo` (`doc.ActiveObject`), `todo` (todos los paneles y contenedores).
- **Flujo:** Selección → Preview (colorea piezas en rojo en 3D) → Task Panel de confirmación → Diálogo "Guardar CSV" → Genera CSV compatible con OpenCutList.
- **Archivos implicados:** `vdo_cutting_list.FCMacro`, `vdo_export_cutting_list.py`, `vdo_cutting_list_preview.py`.

---

## 11. Modelos de Datos de Panel y COCO (absorbido de `CONTEXTO_TECNICO_VDO.md`)

### 11.1 Panel (contrato agnóstico)

**Entrada (sin semántica de mobiliario):**
```python
configuracion = {
    "nombre": str,
    "etiqueta": str,                          # tag libre, NO dirige geometría
    "orientacion": "horizontal" | "vertical", # OBLIGATORIO
    "cantos": {
        "norte": "RIG" | "FX" | "SMRG",
        "sur":   "RIG" | "FX" | "SMRG",
        "este":  "RIG" | "FX" | "SMRG",
        "oeste": "RIG" | "FX" | "SMRG"
    },
    "material_ref": str                       # opcional (default "melamina_standar")
}
```

**Salida (FreeCAD Object):**
```python
panel = {
    "Type": "Part::FeaturePython",             # PanelFeature
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

> La orientación NO se modela con rotación de `Placement` (esa pose pertenece al mueble/espacio). Se modela por **mapeo de ejes** de las expresiones paramétricas.

### 11.2 COCO (salida como contenedor lógico)

```python
coco = {
    "Type": "Part::FeaturePython",
    "Children": [
        "PANEL_LAT_IZQ",
        "PANEL_LAT_DER",
        "PANEL_BASE",
        "PANEL_TECHO",
        "PANEL_FONDO"  # condicional
    ],
    "Shape": Part.Shape(),  # nulo (Axioma T5)
    "VDO_Paneles_JSON": json.dumps(piezas, ensure_ascii=False)
}
```

---

## 12. Debugging e Instalación (absorbido de `CONTEXTO_TECNICO_VDO.md`)

### 12.1 Errores comunes

| Error | Causa | Solución |
|-------|-------|----------|
| `No hay documento activo` | FreeCAD sin archivo abierto | Crear nuevo documento |
| `Hoja no encontrada` | Guardian no ejecutado | Ejecutar `vdo_guardian.vdo_guard()` |
| `Import failed` | Path incorrecto | Verificar Bootstrap en envoltorio |

### 12.2 Logs útiles del motor

```
📦 Panel creado: Nombre
✅ Panel 'Nombre' configurado como 'fachada'
📐 Estructura: Tapa=externo, Base=interno
📦 Fondo delgado (6mm) con ranuras de 3mm
```

### 12.3 Flujo de instalación

1. Copiar carpeta `Macro/` a FreeCAD Macro Path.
2. FreeCAD → Macro → Macros → Ejecutar `vdo_guardian.py`.
3. Verificar: hojas `Params_Melamina` y `Params` creadas.
4. Ejecutar `vdo_coco_4c.FCMacro`.
5. Verificar: `COCO_4C` con 5 paneles.

---

## 13. Jerarquía del Árbol Nativo y Friendly Unlink (absorbido de `ARQUITECTURA_ARBOL_NATIVO_DESVINCULACION.md`)

### 13.1 Jerarquía física en el árbol nativo

Al crear un COCO con 3 cajones, FreeCAD organiza sus grupos nativos:

```
▼ 📦 COCO_01 (Padre / Envolvente Macro, CocoFeature)
    │
    ├── 📁 Estructura_Carcasa (App::DocumentObjectGroup)
    │    ├── 🪵 Panel_Techo      (PanelFeature, ParentCOCO = COCO_01)
    │    ├── 🪵 Panel_Base
    │    ├── 🪵 Panel_Lateral_Izq
    │    ├── 🪵 Panel_Lateral_Der
    │    └── 🪵 Panel_Fondo
    │
    └── 📁 Cajones (App::DocumentObjectGroup)
         ├── ▼ 🗄️ Cajon_01 (Sub-ensamblaje, ParentCOCO = COCO_01)
         │    └── 📁 Paneles
         │         ├── 🪵 Panel_Fachada
         │         ├── 🪵 Panel_Costado_Izq
         │         ├── 🪵 Panel_Costado_Der
         │         ├── 🪵 Panel_Trasera
         │         └── 🪵 Panel_Piso
         ├── ▼ 🗄️ Cajon_02
         └── ▼ 🗄️ Cajon_03
```

**Nota de arquitectura:** El inspector reactivo descrito en el documento original de árbol nativo (§3, `VDOSelectionBridge` → `QStackedWidget`) queda **supersedido** por el `CocoUnifiedTaskPanel` (ver C-03 y ADR-003). La jerarquía de datos y el protocolo Friendly Unlink siguen vigentes.

### 13.2 Protocolo Friendly Unlink (4 pasos atómicos)

1. **Congelación de cotas:** las cotas calculadas por el vano se copian como valores numéricos fijos en las propiedades locales del panel; se eliminan las expresiones paramétricas.
2. **Ruptura limpia del enlace:** `panel.ParentCOCO = None`; el panel se mueve fuera del grupo del padre a la raíz del documento.
3. **Registro de supresión en el padre:** el padre añade el rol de la pieza a su lista `Piezas_Omitidas` para que `execute()` la saltee sin crashear.
4. **Transacción atómica:** los 4 pasos se ejecutan dentro de una sola transacción de FreeCAD.

**Propiedades implicadas:**
- `PanelFeature.ParentCOCO` (`App::PropertyLink`): vínculo jerárquico al COCO/cajón padre.
- `PanelFeature.VDO_Rol` (`App::PropertyString`): rol dentro del padre (`lateral_izquierdo`, `techo`, `fachada`, etc.).
- `CocoFeature.Piezas_Omitidas` (`App::PropertyStringList`): lista de roles omitidos en `execute()`.
- `CocoFeature.Hijos` (`App::PropertyLinkList`): insertos contenidos.

---

## 8. Invariantes de Arquitectura (Resumen) — actualizado

1. **Desacoplamiento App/Gui:** `_core.py` sin Qt/Gui; `App.GuiUp` protege todo acceso visual.
2. **Contenedor = `Part::FeaturePython`:** Nunca `App::Part`, nunca `App::DocumentObjectGroup` como padre principal.
3. **Sin grupos intermedios:** `PropertyLinkListChild` + `claimChildren()` directo.
4. **`Shape` nulo en contenedor:** Previene Z-fighting y duplicación CAM.
5. **`onDelete()` implementado:** Borrado en cascada, sin huérfanos.
6. **No mutar topología en `execute()`:** Creación/destrucción de hijos fuera del ciclo de recompute.
7. **No sobrescribir `claimChildren3D()`:** Preserva selección y resaltado Coin3D nativo.
8. **UI transaccional híbrida:** TaskPanel modal + `VDOTransactionMixin` + focusIn/focusOut + timer 100–250 ms debounce + `_vdo_commit()` / `_vdo_abort()`.
9. **Inspector retirado:** `vdo_universal_inspector.py` y `vdo_inspector_arbol.py` deprecados; edición exclusivamente por `CocoUnifiedTaskPanel`.
10. **Name inmutable / Label dinámico:** Convención de nombrado separada.
11. **Nomenclatura de archivos:** `Dominio_Entidad_Función` (`vdo_math_`, `vdo_hub_`, `vdo_cad_`, `vdo_ui_`, `vdo_cam_`, `vdo_devops_`).
12. **Puntos de entrada protegidos:** `Init.py`, `InitGui.py`, `vdo_manifest.json`, `vdo_hardware_catalog.json` no se renombran.

---

## 14. Empaquetado y Despliegue del Workbench (absorbido de `arquitectura del plugin.md.txt`)

### 14.1 Estándar Oficial de Empaquetado (FreeCAD Addon Manager)

El workbench VDO se empaqueta según la especificación REP 149 de FreeCAD (formato 1.0). El archivo `package.xml` debe residir en la raíz del repositorio y constituye la fuente primaria de información para el Addon Manager:

```xml
<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<package format="1" xmlns="https://wiki.freecad.org/Package_Metadata">
  <name>CarpinteriaParametrica</name>
  <description>Workbench profesional para el diseño, modulación y fabricación de carpintería paramétrica y mobiliario.</description>
  <version>1.0.0</version>
  <date>2026-10-30</date>
  <maintainer email="soporte@empresa.com">Equipo de Desarrollo</maintainer>
  <license>LGPL-2.1-or-later</license>
  <url type="repository">https://github.com/organizacion/CarpinteriaParametrica</url>
  <url type="readme">https://github.com/organizacion/CarpinteriaParametrica/blob/main/README.md</url>
  <icon>Resources/icons/CarpinteriaWorkbench.svg</icon>

  <content>
    <workbench>
      <classname>CarpinteriaWorkbench</classname>
      <subdirectory>./</subdirectory>
      <icon>Resources/icons/CarpinteriaWorkbench.svg</icon>
    </workbench>
  </content>

  <depend>
    <package>BIM</package>
  </depend>
</package>
```

**Gestión de dependencias multinivel:**
1. **Nivel 1 — `package.xml`:** Jerarquía de módulos internos de FreeCAD o complementos requeridos (ej. `BIM`).
2. **Nivel 2 — `metadata.txt`:** Dependencias de bibliotecas de Python del sistema (`pylibs=`, `optionalpylibs=`).
3. **Nivel 3 — `requirements.txt` / `pyproject.toml`:** Paquetes del ecosistema PyPI (numpy, scipy, etc.) vía pip en entorno aislado.

### 14.2 Estructura Canónica de Directorios

| Ruta | Rol Arquitectónico | Ámbito de Carga |
|------|-------------------|-----------------|
| `package.xml` | Manifiesto de metadatos para el Addon Manager | Global / Instalación |
| `metadata.txt` / `requirements.txt` | Declaración de dependencias de Python y complementos | Entorno de Ejecución |
| `Init.py` | Punto de entrada sin GUI (headless / consola) | Consola / CLI / GUI |
| `InitGui.py` | Registro de Workbench, barras de herramientas y menús | Exclusivo GUI |
| `freecad/vdo/objects/` | Clases Proxy de `Part::FeaturePython` (geometría B-Rep, propiedades paramétricas, `execute()`) | Modelo de Datos |
| `freecad/vdo/views/` | Clases `ViewProvider` para representación en escena 3D (Coin3D) | Exclusivo GUI |
| `freecad/vdo/gui/` | Implementación de interfaz de usuario (task panels, comandos) | Exclusivo GUI |
| `Resources/icons/` | Iconos SVG vectoriales | Recursos |

### 14.3 Reglas de Dependencias entre Capas

- **Capa 0 (`math/`)**: No importa de ninguna otra capa del paquete.
- **Capa 1 (`hub/`)**: Importa solo de Capa 0.
- **Capa 2/3 (`cad/objects/`)**: Importa de Capa 0 y Capa 1.
- **Capa views (`cad/views/`)**: Importa de `cad/objects/` y de `FreeCADGui`/`pivy`. Nunca se importa desde `math/` ni desde `cad/objects/`.
- **Capa 4 (`ui/`)**: Importa de todas las capas inferiores y de PySide/FreeCADGui.
- **Capa 5 (`cam/`)**: Importa de Capa 0 y Capa 1.

### 14.4 Patrón de Comandos GUI

Cada acción de toolbar o menú debe ser una clase Python con:
- `GetResources()` → `Pixmap`, `MenuText`, `ToolTip`.
- `IsActive()` → condición de habilitación (ej. `FreeCAD.ActiveDocument is not None`).
- `Activated()` → lógica de ejecución.

Registro: `FreeCADGui.addCommand('NombreComando', ClaseComando())`.

Inyección en `InitGui.py` mediante `appendToolbar` y `appendMenu`.

### 14.5 Definición de Workbench

```python
import FreeCAD
import FreeCADGui

class VDOWorkbench(FreeCADGui.Workbench):
    MenuText = "VDO Carpintería Paramétrica"
    ToolTip = "Modulación y diseño paramétrico de mobiliario y paneles."

    def __init__(self):
        icon_path = os.path.join(
            FreeCAD.getHomePath(), "Mod", "VDO",
            "Resources", "icons", "VDOWorkbench.svg"
        )
        self.__class__.Icon = icon_path

    def Initialize(self):
        import freecad.vdo.gui.commands as VDOCommands
        self.appendToolbar("VDO - Módulos Base", ["VDO_CrearGabinete", "VDO_AgregarRepisa"])
        self.appendMenu("VDO", ["VDO_CrearGabinete", "VDO_AgregarRepisa", "VDO_ExportarDespiece"])

    def Activated(self):
        pass

    def Deactivated(self):
        pass

    def Contextmenu(self, selected_object):
        self.appendContextMenu("VDO", ["VDO_EditarModulo"])

    def GetClassName(self):
        return "Gui::PythonWorkbench"

FreeCADGui.addWorkbench(VDOWorkbench())
```

### 14.6 Task Panels (vista lateral combinada)

El uso de ventanas emergentes flotantes genera interrupciones en el flujo de trabajo 3D. La técnica recomendada es integrar los controles dentro de la pestaña "Tarea" de la Vista Combinada usando `FreeCADGui.Control.showDialog()`:

```python
from PySide2 import QtWidgets, QtCore
import FreeCAD
import FreeCADGui

class GabineteTaskPanel:
    def __init__(self):
        self.form = QtWidgets.QWidget()
        self.form.setWindowTitle("Parámetros del Gabinete")
        layout = QtWidgets.QVBoxLayout(self.form)
        self.spin_ancho = QtWidgets.QDoubleSpinBox()
        self.spin_ancho.setRange(100.0, 3000.0)
        self.spin_ancho.setValue(600.0)
        self.spin_ancho.setSuffix(" mm")
        layout.addWidget(QtWidgets.QLabel("Ancho del Módulo:"))
        layout.addWidget(self.spin_ancho)

    def accept(self):
        doc = FreeCAD.ActiveDocument
        doc.openTransaction("Crear Gabinete Paramétrico")
        obj = doc.addObject("Part::FeaturePython", "GabineteParametrico")
        from freecad.vdo.objects.gabinete import GabineteProxy
        from freecad.vdo.views.view_gabinete import ViewProviderGabinete
        GabineteProxy(obj, self.spin_ancho.value())
        ViewProviderGabinete(obj.ViewObject)
        doc.commitTransaction()
        doc.recompute()
        FreeCADGui.Control.closeDialog()
        return True

    def reject(self):
        FreeCADGui.Control.closeDialog()
        return True
```

### 14.7 Objetos Paramétricos y Proveedores de Vista

**FeaturePython Proxy (agnóstico a GUI):**
```python
class GabineteProxy:
    def __init__(self, obj, ancho=600.0):
        obj.Proxy = self
        obj.addProperty("App::PropertyLength", "Ancho", "Dimensiones", "Ancho total").Ancho = ancho
        obj.addProperty("App::PropertyLength", "Alto", "Dimensiones", "Alto total").Alto = 720.0
        obj.addProperty("App::PropertyLength", "Profundidad", "Dimensiones", "Profundidad total").Profundidad = 560.0

    def execute(self, obj):
        import Part
        mueble = Part.makeBox(obj.Ancho.Value, obj.Profundidad.Value, obj.Alto.Value)
        obj.Shape = mueble

    def __getstate__(self):
        return None
    def __setstate__(self, state):
        return None
```

**ViewProvider (exclusivo GUI, Coin3D):**
```python
class ViewProviderGabinete:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        from pivy import coin
        self.shaded = coin.SoGroup()
        vobj.addDisplayMode(self.shaded, "Shaded")

    def getIcon(self):
        import os, FreeCAD
        return os.path.join(
            FreeCAD.getHomePath(), "Mod", "VDO",
            "Resources", "icons", "GabineteTree.svg"
        )

    def __getstate__(self):
        return None
    def __setstate__(self, state):
        return None
```

### 14.8 Estrategia de Integración: Workbench Independiente vs. Módulo BIM

| Criterio | Workbench Independiente | Módulo Adicional de BIM | Arquitectura Híbrida Autónoma |
|----------|------------------------|-------------------------|-------------------------------|
| Autonomía | Máxima | Acoplado a BIM | Workbench independiente + inyección pasiva en BIM |
| Fricción de usuario | Conmutar de workbench | Sin conmutación | Mejor de ambos |
| Riesgo de reestructuración BIM | Nulo | Alto (depende de API BIM) | Bajo (detección pasiva) |

**Recomendación:** Arquitectura Híbrida Autónoma. El complemento se instala como workbench totalmente independiente. Durante `InitGui.py`, ejecuta detección pasiva: si el workbench BIM está instalado y cargado, inyecta dinámicamente sus barras de herramientas y menús dentro de BIM sin alterar el árbol de dependencias central:

```python
try:
    bim_wb = FreeCADGui.getWorkbench("BIMWorkbench")
    if bim_wb:
        bim_wb.appendToolbar(
            "Carpintería Paramétrica",
            ["Carpinteria_CrearGabinete", "Carpinteria_ExportarDespiece"]
        )
except Exception:
    pass  # Fallo silencioso si BIM no está cargado
```

### 14.9 Despliegue y Distribución

**Publicación en el FreeCAD Addon Manager oficial:**
1. Verificación de metadatos: validar integridad de `package.xml` mediante Herramientas de Desarrollador del Addon Manager.
2. Alojamiento en repositorio público (GitHub, GitLab, Framagit o Salsa Debian) con etiquetado de versiones semánticas.
3. Pull Request al repositorio de índice oficial `FreeCAD/FreeCAD-addons` como submódulo de Git en `.gitmodules`.
4. Inspección automatizada del pipeline de CI de FreeCAD (sintaxis de `package.xml`, validez de licencia, ausencia de conflictos de rutas).

**Despliegue en entornos corporativos privados:**
- A partir de FreeCAD 0.21, se admiten repositorios Git personalizados en las preferencias del Addon Manager (Edit → Preferences → Addon Manager → Custom Repositories).
- Permite apuntar a un servidor GitLab o GitHub Enterprise interno, gestionando actualizaciones automáticas dentro del perímetro de seguridad de la empresa.

---

*Fin del Pilar 2. Este documento es la fuente canónica de arquitectura técnica FreeCAD para VDO, incluyendo las Dimensiones 2 y 3 del modelo ortogonal, el Design System, los modelos de datos, la jerarquía del árbol nativo y el empaquetado/despliegue del workbench.*

*Fin del Pilar 2. Este documento es la fuente canónica de arquitectura técnica FreeCAD para VDO, incluyendo las Dimensiones 2 y 3 del modelo ortogonal.*
