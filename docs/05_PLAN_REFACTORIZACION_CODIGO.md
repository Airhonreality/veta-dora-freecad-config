# 05 — Mapa de Código y Deuda Técnica

**Sistema:** VDO (Veta de Oro) — FreeCAD 1.1+
**Convención de nombrado:** `Dominio_Entidad_Función` (ver C-13 en `00`)

> **Este documento describía una reubicación que ya se ejecutó.** La tabla
> original mapeaba 77 archivos planos de `Macro/` a nombres nuevos *en la
> misma carpeta* `Macro/`. El resultado real fue otro: el código se
> encapsuló en un paquete Python único, `VDO/`, instalado en
> `Mod/VDO_CarpinteriaParametrica/` (ver README, "Tres trampas de
> FreeCAD"). Mantener aquí el mapa viejo resultaba engañoso: declaraba
> "Mantener" para archivos que no existen y apuntaba a rutas inexistentes.
> Lo que sigue es el árbol real.

---

## 1. Capas y carpetas

| Carpeta | Capa | Alcance |
|:--|:--|:--|
| `VDO/core/` | `c0` | Matemática y algoritmos puros (cero FreeCAD, cero Qt) |
| `VDO/hub/` | `c1` | Catálogos, manifiesto, defaults, propiedades de módulo |
| `VDO/shared/` | `c1` | Guardián, manifiesto, acabados, espacios, loaders |
| `VDO/cad/objects/` | `c2` | Entidades Part::FeaturePython y sus fábricas |
| `VDO/cad/views/` | `c3` | ViewProviders base: árbol, menú contextual, borrado |
| `VDO/ui/` | `c4` | TaskPanels, widgets 2D, flujo de creación |
| `VDO/cam/` | `c5` | Lista de corte, nesting, optimizador |

| Capa | Módulo | Líneas |
|:--|:--|--:|
| `c0` | `VDO/core/vdo_math_cajon.py` | 626 |
| `c0` | `VDO/core/vdo_math_facade.py` | 202 |
| `c0` | `VDO/core/vdo_math_frames.py` | 187 |
| `c0` | `VDO/core/vdo_math_layout.py` | 882 |
| `c0` | `VDO/core/vdo_math_puerta.py` | 370 |
| `c0` | `VDO/core/vdo_math_reengrose.py` | 1864 |
| `c1` | `VDO/hub/vdo_hub_defaults.py` | 127 |
| `c1` | `VDO/hub/vdo_hub_hardware.py` | 370 |
| `c1` | `VDO/hub/vdo_hub_module_props.py` | 199 |
| `c1` | `VDO/shared/vdo_finish.py` | 90 |
| `c1` | `VDO/shared/vdo_guardian.py` | 93 |
| `c1` | `VDO/shared/vdo_loader.py` | 174 |
| `c1` | `VDO/shared/vdo_manifest.py` | 32 |
| `c1` | `VDO/shared/vdo_optimizer_preview.py` | 131 |
| `c1` | `VDO/shared/vdo_spaces.py` | 366 |
| `c2` | `VDO/cad/objects/vdo_cad_cajon.py` | 738 |
| `c2` | `VDO/cad/objects/vdo_cad_coco.py` | 975 |
| `c2` | `VDO/cad/objects/vdo_cad_panel.py` | 478 |
| `c2` | `VDO/cad/objects/vdo_cad_placement.py` | 264 |
| `c2` | `VDO/cad/objects/vdo_cad_puerta.py` | 351 |
| `c2` | `VDO/cad/objects/vdo_cad_reengrose_solids.py` | 76 |
| `c2` | `VDO/cad/objects/vdo_cad_space.py` | 554 |
| `c2` | `VDO/cad/objects/vdo_cad_unlink.py` | 153 |
| `c2` | `VDO/cad/objects/vdo_cad_zocalo.py` | 426 |
| `c2` | `VDO/cad/objects/vdo_tambor_core.py` | 280 |
| `c3` | `VDO/cad/views/vdo_cad_view_base.py` | 277 |
| `c4` | `VDO/ui/vdo_ui_box_widget.py` | 1251 |
| `c4` | `VDO/ui/vdo_ui_cajon_task.py` | 579 |
| `c4` | `VDO/ui/vdo_ui_chassis_widget.py` | 1171 |
| `c4` | `VDO/ui/vdo_ui_coco_task.py` | 1456 |
| `c4` | `VDO/ui/vdo_ui_creation_flow.py` | 397 |
| `c4` | `VDO/ui/vdo_ui_divisions_task.py` | 1741 |
| `c4` | `VDO/ui/vdo_ui_drag_handles.py` | 236 |
| `c4` | `VDO/ui/vdo_ui_panel_task.py` | 369 |
| `c4` | `VDO/ui/vdo_ui_preview2d_widget.py` | 386 |
| `c4` | `VDO/ui/vdo_ui_puerta_task.py` | 522 |
| `c4` | `VDO/ui/vdo_ui_qt_compat.py` | 118 |
| `c4` | `VDO/ui/vdo_ui_reengrose.py` | 697 |
| `c4` | `VDO/ui/vdo_ui_tambor_task.py` | 251 |
| `c4` | `VDO/ui/vdo_ui_task_base.py` | 153 |
| `c4` | `VDO/ui/vdo_ui_zocalo_task.py` | 321 |
| `c5` | `VDO/cam/vdo_cam_cutlist.py` | 275 |
| `c5` | `VDO/cam/vdo_cam_cutlist_preview.py` | 284 |
| `c5` | `VDO/cam/vdo_cam_nesting_presets.py` | 159 |
| `c5` | `VDO/cam/vdo_cam_nesting_workflow.py` | 296 |
| `c5` | `VDO/cam/vdo_cam_optimizer_engine.py` | 530 |
| `c5` | `VDO/cam/vdo_cam_optimizer_view.py` | 161 |


---

## 2. Puntos de entrada

| Archivo | Papel |
|---------|-------|
| `Init.py` | Cascarón de arranque (consola y GUI). Nombre reservado por FreeCAD. **Prohibido `__file__`.** |
| `InitGui.py` | Cascarón de registro del workbench. Nombre reservado. Solo localiza la raíz, siembra `sys.path`, importa y registra. **Sin clases.** |
| `VDO/vdo_initgui.py` | Implementación real: comandos, toolbars, menús y la clase `VDO_Workbench`. |
| `VDO/ui/vdo_ui_creation_flow.py` | Flujo `crear → configurar → colocar → commit`. Registro `ESPECIFICACIONES` de los 8 módulos creables. |
| `VDO/vdo_manifest.json` | Manifiesto de taller. Nombre reservado (rutas relativas). |
| `VDO/hub/vdo_hardware_catalog.json` | Catálogo de herrajes. Nombre reservado. |
| `macros/*.FCMacro` | Envoltorios equivalentes a los comandos de la toolbar. Delegan en `VDO.ui.vdo_ui_creation_flow`. |

### Al añadir un módulo creable

1. Fábrica en `VDO/cad/objects/vdo_cad_<x>.py` (`make_<x>()`).
2. TaskPanel en `VDO/ui/vdo_ui_<x>_task.py`, heredando `VDOTransactionMixin`.
3. Entrada en `ESPECIFICACIONES` de `vdo_ui_creation_flow.py`.
4. Comando en `VDO/vdo_initgui.py` llamando a `_crear("<x>")`, y el nombre
   en `COMANDOS` + la toolbar. **Nunca** abrir el TaskPanel sin objeto.
5. Tests en `tests/test_<x>_*.py`.

`tools/vdo_verify.py` deriva `COMANDOS_ESPERADOS` leyendo `COMANDOS` con
`ast`, así que un comando nuevo entra solo en la verificación.

---

## 3. Herramientas

| Script | Para qué |
|--------|----------|
| `tools/install.py` | Instala en `Mod/`. Por defecto enlace simbólico (el repo es la fuente de verdad); `--copy` para otro equipo. |
| `tools/vdo_verify.py` | N1 estático, N2 consola, N3 GUI (`--gui`), N4 end-to-end y N5 insertos (`--e2e`; `--insertos` para sólo el N5). El N4 crea el COCO **por el comando de la toolbar**, no llamando a la fábrica. Del N3 en adelante trabaja con *sondas* (§5). |
| `tools/vdo_audit.py` | Grafo de imports: imports irresolubles y módulos huérfanos. Sigue `from paquete import modulo` y las rutas de módulo escritas como cadena. |

---

## 4. Tests

| Carpeta | Qué contiene |
|---------|--------------|
| `tests/` | Suite real. Sin FreeCAD se omiten los tests que crean documentos (`tests/_entorno.HAY_FREECAD`); con `FreeCADCmd` se ejecutan todos. |
| `tests/obsoletos/` | Tests de la arquitectura retirada por C-03 / ADR-003. Fuera de la colección. |
| `tests/scripts/` | Guiones de diagnóstico procedimentales. Fuera de la colección: hacían `sys.exit()` al importarse y abortaban la suite. |

```bash
python3 -m pytest -q          # parte pura
FreeCADCmd tools/run_tests_freecad.py   # suite completa, con FreeCAD real
```

---

## 5. Sondas de GUI — verificar lo que los tests no ven

**El problema.** La suite daba 176 tests en verde mientras los cajones salían
sin piezas, apilados en el origen y duplicados en la lista de corte (D63, D64).
No es un fallo de la suite: los tests mockean Qt y FreeCAD, así que validan la
**matemática**, no el **proceso**. Todo lo que vive en el ViewProvider, en el
árbol, en el MDI o en el ciclo panel→Aceptar sólo se manifiesta con FreeCAD y
Qt reales. Para eso existen las sondas, del N3 en adelante.

### 5.1 Qué es una sonda

Un **experimento desechable**, no un test: una macro autogenerada que corre en
el FreeCAD real, escribe un JSON en `.verif/` y cierra la ventana. La lanza
`tools/vdo_verify.py::_lanzar()`, que la escribe en `/tmp`, ejecuta
`freecad <macro>` con `timeout` y devuelve el JSON parseado.

```python
import json, traceback
R = "/ruta/reporte.json"
r = {"ok": False, "pasos": {}, "errores": []}

def paso(nombre, fn):              # un fallo no aborta el resto de la sonda
    try:
        v = fn(); r["pasos"][nombre] = True; return v
    except Exception:
        r["pasos"][nombre] = False
        r["errores"].append(nombre + ": " + traceback.format_exc())
        return None

try:
    import FreeCAD as App, FreeCADGui as Gui
    ...medir ANTES...  ;  ...actuar...  ;  ...medir DESPUÉS...
    r["ok"] = all(r["pasos"].values())
except Exception:
    r["errores"].append(traceback.format_exc())

open(R, "w").write(json.dumps(r, indent=2, ensure_ascii=False))   # pase lo que pase

for nombre in list(App.listDocuments()):                          # sin modal al salir
    App.closeDocument(nombre)
from PySide import QtCore
QtCore.QTimer.singleShot(400, Gui.getMainWindow().close)          # se cierra sola
```

Cuatro reglas, cada una pagada con una sesión perdida:

| Regla | Por qué |
|-------|---------|
| **Artefacto en disco, nunca stdout** | Un proceso GUI mezcla buffers y a veces muere: `freecadcmd` segfalla en el *teardown* de Qt y se come el resumen de pytest (por eso la suite completa se lee con `--junit-xml`). Un fichero sobrevive al crash, y por eso `_lanzar()` lee el informe **también** cuando la ventana se cuelga al salir. |
| **Se cierra sola + `timeout`** | Una sonda que deja la ventana abierta bloquea al siguiente agente y a CI. Hay que **cerrar los documentos antes que la ventana**: con uno sin guardar, `close()` abre el modal «¿guardar cambios?» y la sonda se cuelga hasta que salta el timeout. |
| **Nunca aborta entera** | Cada medición envuelta en `paso()`; si muere a la primera no sabes nada de lo que venía detrás. |
| **Medir antes y después del acto** | Sin el "antes" no distingues lo que ya estaba roto de lo que rompiste tú. |

### 5.2 Elegir qué medir: hipótesis diferenciales

Es el 80% del diseño. Se enumeran las causas posibles y se eligen los valores
que las separan **de un solo tiro**. Para "el cajón no tiene desplegable":

| Hipótesis | Valor que la delata |
|-----------|---------------------|
| ViewProvider sin `claimChildren()` | nombre de la clase del proxy |
| ViewProvider equivocado (drag handles) | el mismo campo |
| Hijos reclamados por otro padre | `coco.claim` vs `cajon.claim` |
| No hay hijos que reclamar | `Hijos` **y** `len(VDO_Paneles_JSON)` |

> **Imprime identidades, nombres y conteos; nunca booleanos.** `ok: false` no
> dice nada. `hijos: [], paneles_json_n: 6` localiza el defecto en una línea:
> el despiece se calcula y nadie lo materializa.

Corolario: saca siempre `Placement` **y** `LocalPlacement` por separado. Ver
`local=(42.5, 0, 246.8)` junto a `placement=(0,0,0)` destapó D63, que nadie
había reportado.

### 5.3 Heurísticas de diseño

1. **Reproducir antes de arreglar**, en los términos literales del usuario. Si
   no reprodujiste, no sabes si arreglaste.
2. **Cerrar con el síntoma literal, no con su proxy.** Que `claimChildren()`
   devuelva 6 es un *proxy* de "el árbol tiene flechita"; la verificación final
   recorre el `QTreeWidget` de verdad.
3. **Probar la operación inversa.** Crear hijos ≠ funcionalidad correcta: 3
   cajones → 2 → vano vacío, contando objetos y buscando huérfanos. Todo
   arreglo que *crea* algo necesita su prueba de *destrucción* (T6).
4. **Buscar el daño colateral del propio arreglo.** Al materializar las piezas:
   ¿quién más lee ese despiece? → `grep VDO_Paneles_JSON` → la lista de corte,
   que pasó a contar doble (D64).
5. **Línea base construida a mano.** Para afirmar "ya fallaba antes": copiar el
   repo, revertir **exactamente** tus ediciones y comparar los dos
   `--junit-xml`. Obligatorio aquí, donde el índice de git ya traía cambios y
   no hay `HEAD` contra el que diferenciar.
6. **Mutar el arreglo para validar la sonda.** Una comprobación que no falla
   cuando reintroduces el bug no comprueba nada: romper el arreglo, ver el N5
   en rojo, restaurar.

### 5.4 Cuando no hay API: arqueología

Orden de ataque: documentación → símbolos del binario → árbol Qt en ejecución.
Así se resolvió D62: `strings StartGui.so | grep -i newfile` muestra las seis
tarjetas y **ningún** parámetro de preferencias ⇒ están hardcodeadas en C++;
entonces se baja a `findChildren` / `objectName` / `metaObject().className()`
para encontrar el punto de inyección. El **oráculo de diseño lo da lo nativo**:
no se inventa el tamaño de la tarjeta, se copia el de sus vecinas.

Trampas de Qt, todas vividas:

- **Medir antes del layout miente**: las tarjetas nativas valen 106 px antes de
  dimensionarse y 264 después. Se mide en el momento en que Qt pregunta
  (reimplementar `minimumSizeHint()`) o se difiere con `QTimer`.
- **Los enums de PySide6 no son `int`**: `int(policy)` lanza `TypeError`.
- **El widget puede no existir todavía**: `CreateNewRow` existe vacío antes de
  tener tarjetas. Exigir contenido, no presencia, y reintentar.

### 5.5 Qué cubre el N5 (`--insertos`)

Los invariantes del contenido de vano, que el N4 no toca. Entra por donde entra
el usuario: escribe `VDO_Contenido_JSON` y pulsa Aceptar en el panel del COCO.

| Paso | Invariante | Defecto que vigila |
|------|-----------|--------------------|
| `cajon_materializa_piezas` | cada cajón tiene 6 `PanelFeature` y `claimChildren()` los refleja | D63 |
| `insertos_colocados_en_su_vano` | `Placement` ≠ origen, torre escalonada en z, bbox dentro del mueble en X/Z | D63 |
| `lista_corte_sin_duplicados` | ningún nombre repetido en modo "todo"; ≥ 5 + 6·N piezas | D64 |
| `retirar_inserto_sin_huerfanos` | vaciar el vano deja exactamente COCO + 5 tableros | D63 |

**Sin cobertura todavía:** D61 (canvas al activar el banco) y D62 (tarjeta de
la página de Inicio); ambos se comprueban a mano hoy y su sitio natural es
ampliar el N3.

### 5.6 Añadir una sonda nueva

1. Plantilla de §5.1 como constante `%(...)s` del módulo (ojo: `%%` para
   cualquier `%` literal del código de la sonda).
2. Una función `nivelN()` que la lance con `_lanzar()` y traduzca el JSON a
   `ok()` / `fail()`; `_lanzar()` ya marca los `Traceback` de la consola.
3. Flag propio en `main()` y enganche en `--e2e`.
4. Ejercitar el **camino del usuario** (comando, panel, Aceptar), no la
   fábrica: así se detectó que el COCO no creaba nada por la toolbar (D50).
5. Validar la sonda mutando el arreglo (heurística 6) antes de darla por buena.

---

## 14. Registro de Deuda Técnica DT-1 a DT-35 (absorbido de `Progreso/DEUDA_TECNICA_VDO.md`)

### ✅ Resueltas

| ID | Título | Archivo | Estado |
|----|--------|---------|--------|
| DT-1 | Posición de divisores verticales | `vdo_coco_spaces.py` | RESUELTO 2026-10-20 |
| DT-2 | Recursión de sub-espacios anidados | `vdo_coco_spaces.py` | RESUELTO 2026-10-20 |
| DT-3 | Wrapper de división registrado en UI | `InitGui.py`, `vdo_install.py`, `vdo_toolbar_inject.py` | RESUELTO 2026-10-20 |
| DT-4 | Panel migrado a `Part::FeaturePython` | `vdo_panel_core.py`, `vdo_panel_task.py` | RESUELTO 2026-10-21 |
| DT-5 | Diccionario semántico vacío | `vdo_diccionario_semantico.md`, `vdo_manifest.json` | ABIERTA — pendiente llenado |
| DT-6 | Task Panels separados (básico + espacios) | `vdo_coco_unified_task.py` | RESUELTO 2026-10-20 |
| DT-7 | Panel propiedades COCO via click derecho | `vdo_coco_core.py`, `vdo_coco_unified_task.py` | RESUELTO 2026-10-20 |
| D17-D21 | Marco común de módulos y flujo de creación | 7 archivos nuevos | RESUELTO 2026-10-21 |
| D22 | Fondo delgado en el frente + preview ambiguo | `vdo_coco_core.py`, `vdo_frames.py`, `vdo_finish.py` | RESUELTO 2026-10-26 |
| Divisiones COCO v2 | Matriz de vanos, preview 2D, árbol | 4 archivos nuevos + 4 modificados | RESUELTO 2026-10-22 |

### 🧾 Abiertas (D23-D35)

| ID | Síntoma | Propuesta | Impacto |
|----|---------|-----------|---------|
| D23 | Acabado de caras (no sólo cantos) | Añadir `plan_caras` en C2 separado de `plan_cantos` | Despiece no describe revestimiento de cara vista |
| D24 | Exposición/cantos sólo en COCO | Extender `vdo_finish.aplicar_cantos()` a `vdo_cajon_core` y paneles sueltos | Cajones y paneles no cruzan exposición |
| D25 | Tipo de canto fijo (`RIG`) | Mover selección RIG/SMRG/FX a tabla de datos pura (material × espesor × borde) | Bordes vistos siempre RIG, sin variación |
| D26 | Tests A+B temporales | Crear suite `tests/` permanente (fondo Y+, sin solapes, preview local, exposición, CSV) | Validación solo en `/tmp` |
| D27 | C0/C1/C2 pendientes | Implementar C0 (muros/piso/vistas), C1 (instancia+pose), C2 (exposición calculada) | Exposición es manual por ahora |
| D28 | Reengrose Fase 1 sólo en L1 | Fase 2: modifiers por pieza/división en `VDO_Reengrose_JSON` | Reengrose no aplica dentro de COCO |
| D29 | Un reengrose por panel | Añadir `borde` y lista de modificadores, o modo `perimetral` | No se puede modelar tapa con 4 tiras perimetrales |
| D30 | Mocheo automático sin integración | Integrar en `vdo_layout._resolver_track()` y `vdo_coco_spaces` | Repisas no se recortan/mochean automáticamente |
| D31 | Previsualización de pacha | Añadir columnas/indicadores de grupo y operación en `vdo_cutting_list_preview` | CSV agrupa pero preview no muestra grupo |
| D32 | Preview 2D sin tiras de reengrose | Añadir overlay de refuerzos y marcar repisas retrocedidas/mocheadas | Usuario debe mirar inspector o 3D |
| D33 | Metadatos de tiras de carcasa segmentadas | Generar subpiezas segmentadas o `mocheos` equivalentes | JSON conserva medida nominal, no real |
| D34 | Reengrose horizontal por fila/columna | Modelar extras por segmento de repisa y resolver altura neta | Repisas horizontales no ajustan altura neta |
| D35 | Perímetro y selección directa en preview | Añadir `borde`/lista de modificadores y hotspots de piezas en preview 2D | Selección solo por árbol o combo |

---

## 15. Archivos movidos a `archivo/` (legacy, no código activo)

| Archivo | Origen | Motivo |
|---------|--------|--------|
| `vdo_ui_inspector_arbol.py` | `vdo_inspector_arbol.py` | Deprecated: inspector reactivo retirado (C-03, ADR-003) |
| `vdo_ui_toolbar_test.py` | `vdo_toolbar_test.py` | Test de toolbar, legacy |
| `vdo_hub_loader.py` | `vdo_loader.py` | Loader legacy, reemplazado por guardian |
| `vdo_ui_publish.py` | `vdo_publish.py` | Publicación legacy, verificar uso |
| `VDO_GIT.txt` | `VDO_GIT.txt` | Documento de git, no código |

---

---

## 16. Sesión 2026-10-30 — Reparación del flujo de creación

### Resueltas

| ID | Síntoma | Causa | Arreglo |
|----|---------|-------|---------|
| D36 | Los iconos de la toolbar salían con signo de interrogación | Barra personalizada `CARPINTERIA - VDO` en `Workbench/Global/Toolbar/Custom_1` de `user.cfg`, con `Pixmap` apuntando a la raíz de `Macro/`; los SVG se movieron a `Macro/svg/`. Al estar en el grupo *Global* aparecía en todos los workbenches | Se borra desde Herramientas → Personalizar → Barras, workbench **Global**. No es código del repo |
| D37 | El COCO abría el panel, "Crear" cerraba el diálogo y no aparecía nada | Los comandos abrían el TaskPanel **sin objeto** y los seis `accept()` empezaban con `if not self.obj: return True`. El orquestador `vdo_creation_flow` se perdió en la migración a `VDO/` | `VDO/ui/vdo_ui_creation_flow.py` reescrito; los 8 comandos pasan por `_crear()`; `accept()` crea el objeto si falta (`_vdo_asegurar_objeto`) |
| D38 | Aceptar el panel del COCO borraba toda la carcasa | `_construir_insertos()` barría como "huérfano" cualquier hijo que no fuese puerta o cajón recién construido, es decir los 5 paneles. Con Shape nula (T5) el módulo quedaba invisible | El barrido sólo toca insertos (`_es_inserto()`); la carcasa la gestiona `CocoFeature.sincronizar_paneles_hijos()` |
| D39 | `The graph must be a DAG.` y objetos `still touched after recompute` | Ciclo padre↔hijo: `Hijos` es `LinkListChild` (padre depende de hijos) y `ParentCOCO` era `App::PropertyLink` (hijo depende del padre) | `ParentCOCO` pasa a `App::PropertyLinkHidden`, fuera del grafo. `migrar_parent_link()` convierte los documentos antiguos en `onDocumentRestored()` |
| D40 | Los hijos seguían tocados en cada recompute | `CocoFeature.execute()` escribía el `Placement` de sus hijos; como el padre corre después que ellos, los volvía a tocar sin converger | La propagación se mueve a `onChanged(fp, "Placement")`, fuera del ciclo de recompute |
| D41 | Mover o rotar el COCO dejaba su carcasa atrás | `PanelFeature` no tenía `LocalPlacement`, y el bucle de propagación filtra por esa propiedad | `PanelFeature` declara `LocalPlacement`; `_crear_actualizar_panel()` la escribe |
| D42 | El COCO aparecía sin hijos en el árbol y sus paneles sueltos en la raíz | `make_coco()` instala `DragableViewProvider`, que no implementaba `claimChildren()` | `claimChildren()` sube a `VDOViewProviderBase` leyendo `fp.Hijos` (T4) |
| D43 | Borrar un COCO dejaba sus paneles huérfanos | `onDelete()` estaba en el proxy de datos, y FreeCAD lo invoca en el del **ViewProvider** | `VDOViewProviderBase.onDelete()` hace de puente y delega (T6). `PanelFeature.onDelete()` se desregistra del padre |
| D44 | Editar medidas no cambiaba las piezas del árbol | `_crear_paneles_hijos()` sólo se llamaba desde `make_coco()` | Renombrada a `sincronizar_paneles_hijos()`, se llama también desde `accept()`, y retira las piezas que el despiece ya no contempla |
| D45 | El cajón no producía ninguna geometría | `execute()` calculaba los 6 sólidos (laterales con notch y pin, contrafrente, piso, fachada) y los **descartaba** poniendo Shape nula por T5, sin materializar hijos | `sincronizar_paneles_hijos()` del cajón se llama desde `make_cajon()` y desde `accept()`; el compuesto del padre queda como red de seguridad sólo mientras no haya hijos con volumen |
| D46 | El bisel a 45° de la fachada nunca se aplicaba | `Part.makePolygon(..., closed=True)`: `makePolygon` no acepta argumentos por nombre, así que lanzaba `TypeError` siempre. El mock de los tests sí aceptaba el kwarg y lo tapaba | Cierre por repetición del primer punto, como en `vdo_cad_space.py` |
| D47 | **BUG-001**: la tira de reengrose atravesaba el panel vertical | `vdo_math_reengrose` resuelve en un marco canónico (largo→X, espesor→Z) que es el del panel *horizontal*; nadie aplicaba la orientación | `_al_marco_panel()` en `PanelFeature.execute()`. Solape medido: 22 680 mm³ → 0 |
| D48 | Divisiones, repisas y tiras nacían apiladas en el origen | `posiciones` sólo cubre los 5 roles de carcasa; `despiece_caja()` descartaba la caja geométrica de cada subpieza | `despiece_caja()` arrastra `caja_geometrica`; el COCO deriva la pose con `vdo_math_frames.pose_panel_desde_dict()`, **después** de expandir el reengrose. Solape medido: 5 961 240 mm³ → 0 |
| D49 | `vdo_ui_cajon_task.py` no se podía importar | Usa `QtWidgets` en el cuerpo de una clase sin importarlo: `NameError` al importar el módulo, el panel del cajón no abría nunca | Import con fallback a `QtGui` |
| D50 | El arnés daba verde con la creación rota | El E2E llamaba a `make_coco()` directamente y `COMANDOS_ESPERADOS` listaba 7 de 10 comandos | El E2E dispara `Gui.runCommand("VDO_Coco4C")` y comprueba carcasa, árbol, pose y cascada; la lista de comandos se lee de `vdo_initgui.COMANDOS` con `ast` |
| D51 | La suite de tests no coleccionaba (15 de 27 módulos en error) | `test_cajon_core.py` inyectaba un mock de FreeCAD en `sys.modules` a nivel de módulo y contaminaba los 26 archivos siguientes; 6 tests sembraban el `Macro/` viejo en `sys.path` y validaban el código pre-refactor; 5 tests apuntaban a módulos retirados por ADR-003 | Mock condicionado a que no haya FreeCAD real; `tests/_entorno.HAY_FREECAD`; `tests/obsoletos/` y `tests/scripts/` fuera de la colección; `tools/run_tests_freecad.py` |
| D52 | `vdo_audit.py` reportaba huérfanos falsos | No seguía `from paquete import modulo` ni las rutas de módulo escritas como cadena | Ambas aristas añadidas al grafo |
| D61 | Activar VDO sin documento deja `ActiveDocument=None` y el MDI sólo con "Inicio" | FreeCAD cambia de workbench pero no crea documento ni vista 3D | `_asegurar_canvas()` en `Activated()`: crea documento + vista axonométrica **sólo** si no hay ninguno abierto (`VDO/vdo_initgui.py`) |
| D62 | Banco VDO ausente en la pantalla de inicio | Las seis tarjetas de "Crear nuevo" están hardcodeadas en `StartGui::StartView::configureNewFileButtons`; no hay API ni parámetro para añadir una | `VDO/ui/vdo_ui_start_page.py` inyecta la tarjeta "Mueble VDO" en `CreateNewRow`/`newFileButton`, medida por sus vecinas (264×72), idempotente y silenciosa si FreeCAD renombra los widgets |
| D63 | Los cajones creados desde el COCO salían **sin piezas** (sin desplegable en el árbol) y los tres de una torre **apilados en el origen** | `_construir_cajones()` calculaba el despiece pero nadie llamaba a `sincronizar_paneles_hijos()`, que por R-04 vive fuera de `execute()` (`make_cajon()` sí la llama, el panel del COCO no). Y `CocoFeature` sólo propaga `Placement` desde `onChanged`, aviso que un inserto recién vinculado nunca recibe | `_materializar_insertos()`: recompute → propagar pose → materializar piezas, en ese orden obligado (la puerta reescribe su `LocalPlacement` dentro de `execute()`). `CajonFeature.onChanged()` propaga a su vez a sus 6 piezas, que es el eslabón que faltaba. El barrido de huérfanos invoca el `onDelete` del proxy, que `doc.removeObject()` no dispara (T6). Cubierto por el N5 |
| D64 | La lista de corte contaba cada pieza dos veces (un COCO de 5 tableros daba 10 líneas) | El modo "todo" sumaba los `PanelFeature` reales **y** el `VDO_Paneles_JSON` del contenedor, que publica el mismo despiece | `_piezas_ya_materializadas()`: si el contenedor ya tiene sus piezas como hijos se queda el objeto real (lleva cantos, material y reengroses al día) y se ignora el JSON, que sólo sirve para contenedores sin materializar. Cubierto por el N5 |

### Abiertas

| ID | Síntoma | Impacto | Propuesta |
|----|---------|---------|-----------|
| **D53** | **Los `PanelFeature` hijos no reproducen el mecanizado.** El padre calcula sólidos con ranuras, notches, mocheos e ingletes, pero cada hijo se reconstruye como caja simple desde `Largo/Ancho/Espesor`, así que las piezas se interpenetran donde debería haber ranura | Doble masa, Z-fighting y doble corte en CAM: exactamente lo que el axioma T5 quiere evitar. Solapes medidos: fondo↔carcasa 12 366 mm³ ×2 y ~10 000 mm³ ×2; esquinas de tiras 16 200 y 88 200 mm³. **20 de los 21 tests que fallan son este único defecto** | Dar a `PanelFeature` una propiedad de recortes (`VDO_Recortes_JSON`: lista de prismas en coordenadas locales del panel) y que `execute()` los reste. Las capas 2 ya calculan esos prismas con coordenadas conocidas ("booleanos generados por prismas en coordenadas calculadas"), sólo hay que emitirlos en vez de tirarlos |
| D54 | El ensamblaje L3 falla 3 comprobaciones de cadena | `tests/test_smoke_l3_desk_assembly.py` → `FAIL=3, GAP=0` | Diagnosticar las 3 cadenas una a una; la cobertura de API ya está al día |
| D55 | `VDO/cam/` (6 módulos, ~1 500 líneas) no es alcanzable desde el workbench | Lista de corte, nesting y optimizador sin comando: sólo accesibles por macro | Añadir comandos `VDO_ListaCorte`, `VDO_Nesting`, `VDO_Optimizador` y una toolbar CAM |
| D56 | `vdo_cam_nesting_workflow.py` importa `PySide2` sin alternativa | `ImportError` en FreeCAD 1.x (PySide6) | `try/except` como el resto de los módulos CAM |
| D57 | `vdo_cam_cutlist.py` siembra `VDO/cam` en el `sys.path` global | Es la trampa nº 3 del README (colisión entre addons) | Quitar el `sys.path.insert`; el paquete ya resuelve |
| D58 | El gestor visual de herrajes no se migró | `vdo_herrajes.FCMacro` es un aviso; sólo existe la capa de datos | Migrar `vdo_hardware_manager.py` a `VDO/ui/vdo_ui_hardware_task.py` |
| D59 | La estrategia de base del chasis no genera geometría | Altura de zócalo y separación de frente persisten en `VDO_Chassis_JSON` pero el COCO no construye zócalo con ellas | Generar el zócalo del COCO desde `cfg["base"]` (enlaza con D27) |
| D60 | `vdo_cad_placement.py` sólo lo usa el flujo de creación | La colocación con snap no está disponible al reposicionar un módulo ya creado | Acción "Recolocar" en el menú contextual |

