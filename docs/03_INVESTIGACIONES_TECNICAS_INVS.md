# 03 — Investigaciones Técnicas INVS (Pilar 3)

**Sistema:** VDO (Veta de Oro) — FreeCAD 1.1+
**Fuente primaria:** `documentacion/investigaciones tecnicas de alto valor .invs/`
**Estado:** Definitivo — compilación íntegra, sin placeholders

---

## Deep Dive 1: Topología y el Grafo DAG

### 1.1 Arquitectura de objetos y desacoplamiento App/Gui en FreeCAD 1.1.x

El núcleo de FreeCAD descarta la unificación de la geometría y su representación en un único objeto de software, optando por un patrón estrictamente desacoplado tipo Modelo-Vista:

- **Capa de datos (App):** Opera con independencia total de la plataforma gráfica. Gestiona el estado paramétrico, los atributos dimensionales y la topología subyacente.
- **Capa de interfaz (Gui):** Administra los nodos del visor tridimensional basados en Coin3D/Open Inventor.

Jerarquía de la capa de datos:

```
App::DocumentObject
  └─ App::GeoFeature          (introduce Placement: traslación + rotación)
       └─ Part::Feature       (introduce Shape: topología B-Rep de OpenCASCADE)
            └─ Part::FeaturePython  (clase programable; lógica de recálculo y gestión de propiedades en Python)
```

Jerarquía de la capa visual:

```
Gui::ViewProviderDocumentObject
  └─ Gui::ViewProviderPart
       └─ ViewProviderProxy (Python)
            └─ claimChildren()  ──► Controla la vista de árbol (Tree View)
```

### 1.2 Part::FeaturePython vs App::Part como contenedor padre

Al diseñar el nodo raíz de un módulo de carpintería paramétrica (gabinete, alacena), se presenta la disyuntiva entre `App::Part` (Std_Part) y un contenedor basado en `Part::FeaturePython`.

**App::Part** fue concebido para conjuntos mecánicos rígidos, agrupando sub-objetos con transformación espacial coordinada. Desde el desarrollo de addons en Python, exhibe una limitación crítica: su proveedor de vista (`Gui::ViewProviderPart`) está compilado en C++ y no acepta Proxy en Python. Esto imposibilita la lógica de recálculo paramétrico en Python y la personalización del árbol.

**Part::FeaturePython** permite:
- `execute()` para recálculo imperativo.
- `onDelete()` para borrado en cascada.
- Propiedades dinámicas (`App::PropertyLinkListChild`, etc.).
- `ViewProvider` personalizado en Python.

**Ganador canónico:** `Part::FeaturePython` (ver C-06, C-07 en la Matriz de Contradicciones).

### 1.3 El Grafo Dirigido Acíclico (DAG)

El DAG determina la secuencia cronológica en que el motor de FreeCAD recalcula los objetos del documento. Se establece formalmente cuando una propiedad de un objeto referencia a otro. El núcleo expone `getParentObject()`, que examina la red de propiedades de tipo enlace (`InList` y `OutList`) para retornar el contenedor primario.

La jerarquía visual del Tree View está regida por `claimChildren()` del ViewProvider del contenedor. Cuando la GUI construye o actualiza la vista de árbol, invoca `claimChildren()` en cada proveedor de vista registrado. Este método retorna una lista de objetos de datos que deben sangrarse visualmente debajo del contenedor:

```python
def claimChildren(self):
    """Retorna los objetos que deben anidarse visualmente bajo el padre."""
    if hasattr(self.Object, "Paneles"):
        return [p for p in self.Object.Paneles if p is not None]
    return []
```

Existe además `claimChildren3D()`, cuyo función es indicar qué objetos agruparse bajo el mismo nodo de transformación en el grafo de escena Coin3D. **Sobrescribir `claimChildren3D()` no es recomendable**, dado que distorsiona la gestión de selección tridimensional y la renderización de resaltado nativa de FreeCAD (ver C-12 en la Matriz).

### 1.4 El riesgo del modo headless y la persistencia de datos

El fallo metodológico más común es confiar la jerarquía del módulo exclusivamente al método `claimChildren()`. Cuando FreeCAD se ejecuta en `FreeCADCmd`, como módulo de Python externo, o en servidores de renderizado/CI, la interfaz gráfica (`FreeCADGui`) no se inicializa. Los proveedores de vista no existen y `claimChildren()` jamás se ejecuta.

Si las relaciones entre el mueble y sus paneles solo existieran dentro del ViewProvider, cualquier script headless destinado a generar listas de materiales (BOM), extraer planos de corte o exportar archivos CNC analizaría el documento como una colección de objetos planos inconexos, perdiendo la estructura del módulo.

**Solución:** La jerarquía debe residir de forma nativa en la capa de datos utilizando `App::PropertyLinkListChild` o `App::PropertyLinkChild`. `claimChildren()` es exclusivamente un reflejo visual.

### 1.5 Estrategia de mitigación de duplicación geométrica y objetos huérfanos

Cada componente (laterales, zócalos, divisores) debe existir como entidad topológica B-Rep independiente asignada a la propiedad `Shape` de un objeto `Part::FeaturePython`. Esta independencia es indispensable para CAM/Path, anidado (nesting) y despiece.

**El problema de la duplicación geométrica:** Si el contenedor padre asigna un `Part.makeCompound(solidos)` a su propio `Shape`, se duplica la geometría de los hijos. Esto provoca:
- Z-fighting en pantalla.
- Doble cálculo de masa/peso.
- Duplicación del corte en el exportador CAM/Nesting.

**Solución canónica:** `fp.Shape = Part.Shape()` (nulo) en el contenedor padre (ver C-02 en la Matriz).

**Gestión de objetos huérfanos:** Implementar `onDelete()` en el proxy de datos para borrado en cascada:

```python
def onDelete(self, obj, subelements):
    if hasattr(obj, "Paneles"):
        doc = obj.Document
        for panel in obj.Paneles:
            if panel and doc.getObject(panel.Name):
                doc.removeObject(panel.Name)
    return True
```

### 1.6 Propagación paramétrica: expresiones vs recálculo imperativo

**Declarativo por expresiones algebraicas:** Asigna expresiones explícitas (`<<Objeto>>.Propiedad`) a propiedades de hijos. Transparente para el usuario, pero introduce sobrecarga severa en el DAG: cada expresión registra un nodo y una arista adicional, incrementando tiempos de evaluación y riesgo de dependencias circulares en modificaciones masivas.

**Recálculo imperativo en `execute()`:** El contenedor padre calcula las nuevas coordenadas de cada panel y actualiza directamente sus propiedades. Mantiene el DAG limpio (solo un enlace global `App::PropertyLinkListChild` entre padre e hijos).

**Estrategia híbrida optimizada (recomendada):**
- **Nivel superior (Interfaz/Proyecto):** Hoja de cálculo nativa (Spreadsheet) o propiedades globales en el contenedor padre, con expresiones algebraicas para variables de diseño arquitectónico.
- **Nivel interno (Módulo/Componentes):** Recálculo imperativo en `execute()` del `Part::FeaturePython` para derivar geometría, posición y orientación de cada panel.

### 1.7 Estándares de nomenclatura: Name vs Label

- **Name:** Clave única no mutable asignada por el núcleo. Solo `[_0-9a-zA-Z]`. Formato: `[TipoModulo]_[RolPieza]_[Hash/ID]` (ej. `Mueble_Base_001`, `Panel_Lateral_Izq_001`). Usado para búsquedas y vinculaciones inequívocas.
- **Label:** Cadena UTF-8 modificable por el usuario, mostrada en Tree View y planos. Formato: `[Nombre Descriptivo] [[Largo x Ancho x Espesor]]` (ej. `Lateral Izquierdo [720 x 560 x 18 mm]`).

---

## Deep Dive 2: Coin3D y ViewProviders

### 2.1 Manejo de selección

La integración de un panel flotante permanente (`QDockWidget`) con el entorno 3D de FreeCAD se sustenta sobre el patrón Observador de Documento y Selección.

**Vista 3D → DockWidget:** El panel registra un observador mediante `FreeCADGui.Selection.addObserver(self)`. Al detectarse un cambio de selección, el panel recibe `setSelection()` y refresca sus controles sin solicitar reevaluaciones al documento CAD.

**DockWidget → Vista 3D:** Se usa filtrado asíncrono (debounce). La modificación de un control actualiza la vista 2D interna e inicia un temporizador que posterga el recompute 3D pesado hasta la estabilización de la entrada de datos.

**Aislamiento de código GUI:** Toda la lógica de sincronización debe protegerse con `FreeCAD.GuiUp` para compatibilidad en entornos desatendidos o línea de comandos.

### 2.2 Por qué no sobrescribir `claimChildren3D()`

`claimChildren3D()` indica qué objetos agruparse bajo el mismo nodo de transformación en el grafo de escena Coin3D. Sobrescribirlo distorsiona:
- La gestión de selección 3D.
- La renderización de resaltado nativa de FreeCAD.

**Ganador canónico:** No sobrescribir `claimChildren3D()`. Usar solo `claimChildren()` para el Tree View; dejar la gestión 3D a Coin3D nativa (ver C-12 en la Matriz).

### 2.3 Aislamiento de `GuiUp` para compatibilidad headless

Todo acceso a `FreeCADGui`, `ViewObject`, iconos y selección debe ir dentro de:

```python
if App.GuiUp:
    import FreeCADGui as Gui
    # ... código GUI ...
```

Esto garantiza que el código funcione en `FreeCADCmd`, scripts de CI y entornos sin display.

---

## Deep Dive 3: Transaccionalidad en FreeCAD

### 3.1 Ciclo de vida de transacciones

El modelo transaccional clásico opera como un búfer temporal aislado. Durante la interacción del usuario con un TaskPanel, las modificaciones permanecen en memoria volátil de la vista. La mutación del documento (`App::Document`) se difiere hasta la activación explícita de "Aceptar":

```python
try:
    doc.openTransaction("Actualización Paramétrica VDO")

    # Mutación de propiedades y topología
    objeto_padre.Ancho = 600.0
    actualizar_estructura_hijos(objeto_padre)

    doc.recompute()
    doc.commitTransaction()
except Exception as error:
    doc.abortTransaction()
    FreeCAD.Console.PrintError(f"Falla en actualización: {str(error)}\n")
```

Esto garantiza que ante un error de cálculo o inconsistencia, la transacción se aborte automáticamente, previniendo corrupción del árbol de objetos.

### 3.2 Creación de objetos hijos fuera de execute()

Los objetos contenedores complejos no generan ni destruyen sus elementos subordinados dentro de `execute()`. Adoptan el patrón de gestión desacoplada mediante propiedades de enlace:

1. **Declaración de enlaces:** El contenedor define `App::PropertyLinkList` (habitualmente `Group` o `Hijos`).
2. **Instanciación externa:** La creación física de los hijos (`doc.addObject()`) la ejecuta un comando de UI o función controladora desacoplada.
3. **Registro de pertenencia:** El controlador actualiza la propiedad `Group` del padre.
4. **Cálculo espacial en `execute()`:** `execute()` lee las referencias de la propiedad `Group`/`Hijos` y actualiza exclusivamente `Placement` de cada hijo. **Nunca** invoca creadores o destructores de objetos.

### 3.3 Mitigación de saturación del Undo stack mediante debounce

Para controles Qt continuos (spinners, sliders), se aplica debounce para evitar saturar el historial de deshacer:

```python
def al_modificar_control(self):
    # Refresco inmediato de la vista 2D
    self.visor_2d.set_layout(self.leer_parametros_ui())

    # Reinicio del temporizador debounce (250 ms)
    self.timer_debounce.stop()
    self.timer_debounce.start(250)

def al_expirar_debounce(self):
    doc = FreeCAD.ActiveDocument
    doc.openTransaction("Modificación Paramétrica VDO")
    try:
        sincronizar_insertos_vdo(self.objeto_padre, self.leer_parametros_ui())
        doc.recompute()
        doc.commitTransaction()
    except Exception as error:
        doc.abortTransaction()
        FreeCAD.Console.PrintError(f"Error en recomputo: {str(error)}\n")
```

### 3.4 Plan óptimo de transacciones (Refactorización_Plan_Óptimo)

**Antes (obsoleto):** Debounce 250 ms que difería el recompute, creando gap temporal entre UI y documento.

**Después (plan óptimo, implementado):**
- `focusIn` → `openTransaction()` (transacción abierta antes de cualquier cambio).
- Cambio en parámetro → UI actualiza (0 ms).
- Timer 100 ms (control de frecuencia, no diferimiento) → `recompute()` dentro de transacción abierta.
- `focusOut` / `editingFinished` → `commitTransaction()`.

**Beneficios:**
- 0 ms de latencia perceptible (100 ms es imperceptible).
- Consistencia total: todo dentro de transacción.
- Conforme a la especificación de FreeCAD.
- Mejor manejo de errores: `abortTransaction()` revierte todo.

### 3.5 Recompute sin transacción: violación crítica

Llamar `doc.recompute()` fuera de una transacción (micro-header, chasis, herrajes) ensucia el historial de Undo y provoca múltiples micro-transacciones por sesión de edición. Todo `recompute()` debe estar envuelto en `openTransaction`/`commitTransaction` o gestionado por el debounce del panel padre.

---

## Matriz comparativa de patrones de interfaz

| Criterio | Patrón A: Transaccional Modal (TaskPanel) | Patrón B: Inspector Reactivo Continuo |
|----------|-------------------------------------------|---------------------------------------|
| Mutación del documento | En `commitTransaction()` explícito | Inmediata en cada evento de control |
| Historial de Undo | 1 bloque por gesto de edición | N micro-transacciones (ensuciado) |
| Estabilidad del DAG | Alta (mutaciones atómicas) | Baja (condiciones de carrera con Coin3D) |
| Compatibilidad headless | Total | Nula (depende de `Gui.SelectionObserver`) |
| Latencia perceptible | ~100 ms (imperceptible) | 0 ms visual, pero riesgo de congelamiento |
| Veredicto | **GANADOR** (Axioma del Sistema VDO) | Obsoleto — prohibido |

---

*Fin del Pilar 3. Este documento preserva íntegramente las investigaciones de ingeniería de VDO, incluyendo los tres Deep Dives y la matriz comparativa de patrones de interfaz.*
