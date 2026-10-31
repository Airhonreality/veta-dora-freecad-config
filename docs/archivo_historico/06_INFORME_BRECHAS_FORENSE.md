# 06 — Informe de Brechas Forense (Fase de Descubrimiento)

**Sistema:** VDO (Veta de Oro) — FreeCAD 1.1+
**Origen:** carpeta `documentacion/` (SOLO LECTURA, intacta)
**Destino:** `documentacion_v2/`
**Estado:** Entregable preliminar — lista para integración (Fase 3)

---

## 1. Inventario Completo de Archivos Analizados

Se inspeccionó el 100% de los archivos de `documentacion/`. Ningún archivo fue descartado sin análisis previo.

### 1.1 Raíz de `documentacion/` (11 archivos de texto + 1 artefacto binario)

| # | Archivo | Tipo | Tema | Estado en v2 |
|---|---------|------|------|--------------|
| R1 | `AXIOMAS_VDO_Metodologia.md` | Texto | 5 axiomas geométricos, matriz BUG-001..BUG-008, código `vdo_axioms.py`, `vdo_types.py`, tests, plan de implementación | **PARCIAL** (solo axiomas en 04; código y matriz de bugs ausentes) |
| R2 | `ARQUITECTURA_ARBOL_NATIVO_DESVINCULACION.md` | Texto | Árbol nativo FreeCAD, jerarquía física, inspector reactivo, Friendly Unlink, tabla de propiedades, limitaciones | **PARCIAL** (referenciado en C-01/C-02/C-05 y ADR-002; contenido completo ausente) |
| R3 | `VDO_PROTOCOLO_CREACION_MODULOS.md` | Texto | Axiomas T1-T8, estructura de archivos, contrato núcleo/ViewProvider/factory, BOM, Task Panel, InitGui, Name/Label, nombres prohibidos | **COBERTO** (02 Pilar 2, 05) |
| R4 | `vdo_diccionario_semantico.md` | Texto | Diccionario semántico esqueleto, reglas de llenado, tabla de piezas, notas pendientes | **PARCIAL** (tabla en 01 §4; reglas/notas/estado ausentes) |
| R5 | `CONTEXTO_TECNICO_VDO.md` | Texto | Visión, 5 axiomas de arquitectura, marco local, reengrose Fase 1-3, Thin Wrapper, modelos de datos, reglas de negocio, propiedades VDO, dependencias, instalación, matriz de vanos v2, debugging | **PARCIAL** (fragmentos en 01/02; debugging, instalación, reengrose completo, tablas ausentes) |
| R6 | `PROGRESO_VDO.md` | Texto | Historial v1.0-1.8, sesiones 20/09, 22/10, 26/10, funcionalidades implementadas, tests pendientes, errores conocidos | **AUSENTE** |
| R7 | `DIAGNOSTICO_BUGS_GEOMETRICOS.md` | Texto | Fallo 1 (reengrose w/h invertidos), Fallo 2 (fachada asimétrica), tablas de validación, archivos corregidos, suites de prueba | **PARCIAL** (referenciado C-04; diagnóstico completo ausente) |
| R8 | `DISENO_UI_CAPAS_COGNITIVAS_VDO.md` | Texto | Modelo cognitivo 4 capas, flujo cognitivo, toolbar N1/N3, botones eliminados, 4 primitivas maestras, jerarquía árbol, inspector zoom semántico, Friendly Unlink, flujo despiece/corte, tabla de archivos implicados | **PARCIAL** (fragmentos en 01/02; modelo cognitivo, toolbar, primitivas, despiece ausentes) |
| R9 | `MANIFIESTO_DISENO_INTERFAZ_VDO.md` | Texto | Tesis central, 7 pilares UI, poka-yoke, paleta cromática, VDO_DoubleSpinBox, primitivas UI (BoxController, PanelHeader, VanoInspector, HardwareSelector), rebanada vertical C0-C4, regla de oro | **AUSENTE** (ningún pilar en v2) |
| R10 | `Arquitectura de capas espacios a modulos.txt` | Texto | Marco local único, dos ejes (COMPOSICIÓN/CONTEXTO), L1-L2-L3 / C0-C1-C2, 6 lados de módulo, vistos/frente/fachada, estado 2026-10-26, fases reengrose | **PARCIAL** (marco local en 01 §5; dos ejes y C0-C1-C2 ausentes) |
| R11 | `VDO_NESTING_README.md` | Texto | Optimizador de corte 2D, instalación, presets (5), algoritmo Minkowski/Physics, ejemplos, eficiencia, troubleshooting, integración DXF, API headless, versiones | **AUSENTE** (solo lista de archivos en 05 filas 65-68) |
| R12 | `.Arquitectura de capas espacios a modulos.txt.kate-swp` | BINARIO (swap de editor Kate) | Artefacto de editor, no contiene conocimiento del proyecto | **N/A** (archivo basura de sesión de editor, no migrar) |

### 1.2 Subcarpeta `Progreso/` (8 archivos)

| # | Archivo | Tema | Estado en v2 |
|---|---------|------|--------------|
| P1 | `Refactorización_Plan_Óptimo.md` | Plan óptimo de transacciones (focusIn/focusOut, timer 100ms, comparativa antes/después, beneficios, checklist, lecciones, FASE 6) | **AUSENTE** |
| P2 | `DEUDA_TECNICA_VDO.md` | Registro de deuda técnica DT-1..DT-35 (resueltas y abiertas: D23-D35) | **AUSENTE** |
| P3 | `Plan_de_Acciones_VDO.md` | Plan de acción 6 fases para incompatibilidad reactiva, matriz de dependencias, checklist, criterios de éxito, riesgos, comando de tests | **AUSENTE** |
| P4 | `PROGRESO_VDO.yaml` | Registro YAML de progreso con checkpoints detallados 2026-09-18 → 2026-10-26, arquitectura, siguientes pasos | **AUSENTE** |
| P5 | `Correcciones_Aplicadas.md` | 4 correcciones a `vdo_universal_inspector.py` (timer stop/start, micro-header, chasis, herrajes) | **AUSENTE** |
| P6 | `DIAGNOSTICO_CRITICO_AXIOMAS.md` | Diagnóstico crítico: verificación de 5 bugs reales, análisis de necesidad del plan de axiomas, alternativas (Opción 1-4), recomendación Opción 2 | **AUSENTE** |
| P7 | `Revision_Codigo_VDO.md` | Revisión de código `vdo_universal_inspector.py`: 6 hallazgos (timer bug, recompute sin transacción ×3, métodos largos, cobertura timer), plan de correcciones, tabla de impacto | **AUSENTE** |
| P8 | `SESION_20_SEPT_2026.md` | Informe de sesión: 5 funcionalidades, 5 errores corregidos, fuentes investigadas, estructura de archivos, tests pendientes, métricas, TNP, persistencia | **AUSENTE** |

### 1.3 Subcarpeta `investigaciones tecnicas de alto valor .invs/` (2 archivos)

| # | Archivo | Tema | Estado en v2 |
|---|---------|------|--------------|
| I1 | `Arquitectura Paramétrica de Objetos y Gestión de Jerarquías.invs.txt` | INVS-01: jerarquía objetos, App/Gui desacoplamiento, FeaturePython vs App::Part, DAG, claimChildren, claimChildren3D, riesgo headless, duplicación geométrica, expresiones vs execute(), Name/Label, código mínimo funcional, do's/don'ts | **COBERTO** (03 Deep Dive 1) |
| I2 | `Freecad UI aspectos tecnicos.invs.txt` | INVS-02: transaccionalidad, creación hijos en contenedores, sincronización DockWidget/vista 3D, matriz comparativa patrones UI, debounce, arquitectura híbrida VDO | **COBERTO** (03 Deep Dive 2-3) |

**Total archivos analizados:** 22 (21 texto + 1 binario swap descartado como conocimiento).

---

## 2. Matriz de Brechas (Gaps) — Archivo por Archivo

A continuación, archivo fuente → qué conocimiento contiene → ¿existe en v2? → destino de incorporación.

| # | Archivo origen | Conocimiento técnico de bajo nivel presente | ¿En v2? | Destino de incorporación en `documentacion_v2/` |
|---|----------------|---------------------------------------------|---------|-------------------------------------------------|
| G-01 | `AXIOMAS_VDO_Metodologia.md` | 5 axiomas formales con invariantes, notación matemática | Sí (parcial) | 04 (axiomas ya están) |
| G-02 | `AXIOMAS_VDO_Metodologia.md` | Matriz BUG-001..BUG-008 con causa, axioma que lo previene, cómo | **NO** | Nuevo doc: `17_IMPLEMENTACION_AXIOMAS.md` |
| G-03 | `AXIOMAS_VDO_Metodologia.md` | Código completo `vdo_axioms.py` (decoradores @requires/@ensures, VDOCoordFrame, GeometricValidator, COCO_FRAME) | **NO** | Nuevo doc: `17_IMPLEMENTACION_AXIOMAS.md` |
| G-04 | `AXIOMAS_VDO_Metodologia.md` | Código completo `vdo_types.py` (AnchoVanoTotal, AnchoVanoNeto, EspacioDivisiones) | **NO** | Nuevo doc: `17_IMPLEMENTACION_AXIOMAS.md` |
| G-05 | `AXIOMAS_VDO_Metodologia.md` | Código completo `tests/test_axioms_vdo.py` (TestAxiom2, TestAxiom5) | **NO** | Nuevo doc: `17_IMPLEMENTACION_AXIOMAS.md` |
| G-06 | `AXIOMAS_VDO_Metodologia.md` | Plan de implementación 5 fases (infraestructura, documentación, validaciones, tipos, testing) + checklist final | **NO** | Nuevo doc: `17_IMPLEMENTACION_AXIOMAS.md` |
| G-07 | `AXIOMAS_VDO_Metodologia.md` | Contenido propuesto de `AXIOMAS_FORMALES.md` y `MAPEO_ANCHO_VDO.md` | **NO** | Nuevo doc: `17_IMPLEMENTACION_AXIOMAS.md` |
| G-08 | `ARQUITECTURA_ARBOL_NATIVO_DESVINCULACION.md` | Jerarquía física completa en árbol nativo (diagrama COCO_01 → Estructura_Carcasa/Cajones → paneles) | **NO** | Nuevo doc: `18_ARQUITECTURA_ARBOL_DESVINCULACION.md` |
| G-09 | `ARQUITECTURA_ARBOL_NATIVO_DESVINCULACION.md` | Tabla mapeo selección en árbol → vista panel lateral (COCO→PAGE_CHASIS, PANEL→PAGE_PIEZA, CAJON→PAGE_CIERRE) | **NO** | Nuevo doc: `18_ARQUITECTURA_ARBOL_DESVINCULACION.md` |
| G-10 | `ARQUITECTURA_ARBOL_NATIVO_DESVINCULACION.md` | Implementación VDOSelectionBridge (SelectionObserver, _on_selection_changed, QStackedWidget) | **NO** | Nuevo doc: `18_ARQUITECTURA_ARBOL_DESVINCULACION.md` |
| G-11 | `ARQUITECTURA_ARBOL_NATIVO_DESVINCULACION.md` | Protocolo Friendly Unlink 4 pasos atómicos + código headless `vdo_desvincular_pieza()` | Parcial (ADR-002) | Nuevo doc: `18_ARQUITECTURA_ARBOL_DESVINCULACION.md` (detalle completo) |
| G-12 | `ARQUITECTURA_ARBOL_NATIVO_DESVINCULACION.md` | Tabla de propiedades VDO (ParentCOCO PropertyLink, VDO_Rol, VDO_Canto_N/S/E/O, Largo/Ancho/Espesor, Piezas_Omitidas, Hijos) | **NO** | Nuevo doc: `18_ARQUITECTURA_ARBOL_DESVINCULACION.md` |
| G-13 | `ARQUITECTURA_ARBOL_NATIVO_DESVINCULACION.md` | 4 limitaciones conocidas + lógica de decisión 5.1-5.5 + flujo de implementación T1-T3 | **NO** | Nuevo doc: `18_ARQUITECTURA_ARBOL_DESVINCULACION.md` |
| G-14 | `CONTEXTO_TECNICO_VDO.md` | Sección Debugging (errores comunes, logs útiles) | **NO** | Nuevo doc: `22_CONTEXTO_TECNICO_VDO.md` |
| G-15 | `CONTEXTO_TECNICO_VDO.md` | Flujo de instalación (5 pasos) | **NO** | Nuevo doc: `22_CONTEXTO_TECNICO_VDO.md` |
| G-16 | `CONTEXTO_TECNICO_VDO.md` | Modelo de datos Panel (configuración de entrada, salida FreeCAD) y COCO (salida como Group) | **NO** | Nuevo doc: `22_CONTEXTO_TECNICO_VDO.md` |
| G-17 | `CONTEXTO_TECNICO_VDO.md` | Marco común de módulos D17-D21 (MODULE_SPECS, flujo crear→configurar→colocar, triple acceso, pose vs geometría, salida Cofre) | Parcial (02) | Nuevo doc: `22_CONTEXTO_TECNICO_VDO.md` (detalle completo) |
| G-18 | `CONTEXTO_TECNICO_VDO.md` | Reglas de negocio: cantos, fondo (umbral 8mm, f_y), estructura tapa/base, sobremedida vs medida terminada | Parcial (01) | 01 (ya cubre la mayoría) |
| G-19 | `CONTEXTO_TECNICO_VDO.md` | Matriz de vanos v2 de COCO (resolve_layout, reparto fijo/libre, overflow, cavidad interior, fondo y profundidad, exposición/cantos, UI, compatibilidad legacy, validación headless) | Parcial (01/02) | 01/02 (cubre parcialmente) |
| G-20 | `CONTEXTO_TECNICO_VDO.md` | Notas para desarrolladores (agregar módulo, agregar parámetro) | **NO** | Nuevo doc: `22_CONTEXTO_TECNICO_VDO.md` |
| G-21 | `DIAGNOSTICO_BUGS_GEOMETRICOS.md` | Fallo 1: tira reengrose disparada, causa matemática exacta (vdo_reengrose_solids.py:40-50), solución implementada con código | Parcial (C-04) | Nuevo doc: `19_DIAGNOSTICO_BUGS_GEOMETRICOS.md` |
| G-22 | `DIAGNOSTICO_BUGS_GEOMETRICOS.md` | Fallo 2: desplazamiento asimétrico fachadas, Parte A (ancho_ext vs li) y Parte B (offset delta/2), síntesis de doble impacto, cálculo de asimetría | Parcial (C-04) | Nuevo doc: `19_DIAGNOSTICO_BUGS_GEOMETRICOS.md` |
| G-23 | `DIAGNOSTICO_BUGS_GEOMETRICOS.md` | Tablas de validación Test 1 (BBox contención) y Test 2 (simetría bilateral) | **NO** | Nuevo doc: `19_DIAGNOSTICO_BUGS_GEOMETRICOS.md` |
| G-24 | `DIAGNOSTICO_BUGS_GEOMETRICOS.md` | Archivos corregidos (3) + suites de prueba nuevas (test_reengrose_l1_bbox.py, test_cajon_symmetry.py) | **NO** | Nuevo doc: `19_DIAGNOSTICO_BUGS_GEOMETRICOS.md` |
| G-25 | `DISENO_UI_CAPAS_COGNITIVAS_VDO.md` | Modelo cognitivo: 4 capas con tabla (Capa/Nombre/Qué hace/Quién/Entrada) y flujo cognitivo 6 pasos | **NO** | Nuevo doc: `20_UI_CAPAS_COGNITIVAS.md` |
| G-26 | `DISENO_UI_CAPAS_COGNITIVAS_VDO.md` | Toolbar: Nivel 1 botones directos (tabla), Nivel 3 desplegable L3 (categorías), botones eliminados/obsoletos | **NO** | Nuevo doc: `20_UI_CAPAS_COGNITIVAS.md` |
| G-27 | `DISENO_UI_CAPAS_COGNITIVAS_VDO.md` | 4 primitivas maestras (COCO, Vano, Panel L1, Ensamblaje L3) con specs de widget | Parcial (01/02) | Nuevo doc: `20_UI_CAPAS_COGNITIVAS.md` |
| G-28 | `DISENO_UI_CAPAS_COGNITIVAS_VDO.md` | Flujo lista de corte/despiece: 3 modos (selección/grupo/todo), flujo selección→preview→task panel→CSV, archivos implicados | **NO** | Nuevo doc: `20_UI_CAPAS_COGNITIVAS.md` |
| G-29 | `DISENO_UI_CAPAS_COGNITIVAS_VDO.md` | Tabla de archivos implicados UI (vdo_toolbar_inject.py, InitGui.py, vdo_coco_core.py, etc.) | **NO** | Nuevo doc: `20_UI_CAPAS_COGNITIVAS.md` |
| G-30 | `MANIFIESTO_DISENO_INTERFAZ_VDO.md` | Tesis central: fracaso UI CAD tradicional vs enfoque semiótico VDO | **NO** (ausente totalmente) | Nuevo doc: `06_UI_MANIFIESTO_DISENO.md` (o integrar en 20) |
| G-31 | `MANIFIESTO_DISENO_INTERFAZ_VDO.md` | 7 pilares UI con axiomas, reglas de oro, poka-yoke radical | **NO** (ausente totalmente) | Nuevo doc: `06_UI_MANIFIESTO_DISENO.md` |
| G-32 | `MANIFIESTO_DISENO_INTERFAZ_VDO.md` | Paleta cromática dark mode (base #141414/#1e1e1e, interactiva #252525/#2b2b2b, bordes #3a3a3a/#444444, acentos #007acc/#0098ff, texto #e0e0e0/#ffffff, secundario #888888) | **NO** (ausente totalmente) | Nuevo doc: `06_UI_MANIFIESTO_DISENO.md` |
| G-33 | `MANIFIESTO_DISENO_INTERFAZ_VDO.md` | Pilar 7: VDO_DoubleSpinBox (coma/punto, locale-agnostic) | **NO** (ausente totalmente) | Nuevo doc: `06_UI_MANIFIESTO_DISENO.md` |
| G-34 | `MANIFIESTO_DISENO_INTERFAZ_VDO.md` | Primitivas UI: VDOBoxControllerWidget, PanelHeaderWidget, VanoInspectorWidget, HardwareSelectorWidget | **NO** (ausente totalmente) | Nuevo doc: `06_UI_MANIFIESTO_DISENO.md` |
| G-35 | `MANIFIESTO_DISENO_INTERFAZ_VDO.md` | Rebanada vertical completa (mermaid C0→C4) y regla de oro para desarrolladores/agentes | **NO** (ausente totalmente) | Nuevo doc: `06_UI_MANIFIESTO_DISENO.md` |
| G-36 | `VDO_NESTING_README.md` | Documentación completa del optimizador de corte 2D: instalación, presets (5 tabla), algoritmos Minkowski/Physics con parámetros, 3 ejemplos de uso, interpretación eficiencia, piezas no colocadas, troubleshooting (4), integración DXF/PDF/CAM, API headless avanzada, versiones | **NO** (ausente totalmente) | Nuevo doc: `07_NESTING_OPTIMIZADOR_CORTE.md` |
| G-37 | `vdo_diccionario_semantico.md` | Estado ESQUELETO v0.1.0, reglas de llenado (4), notas/decisiones pendientes, promoción a vdo_manifest.json → semantica | Parcial (tabla en 01 §4) | Nuevo doc: `21_DICCIONARIO_SEMANTICO.md` |
| G-38 | `Arquitectura de capas espacios a modulos.txt` | Dos ejes ortogonales (COMPOSICIÓN L1-L2-L3 vs CONTEXTO C0-C1-C2), 6 lados de módulo, 3 conceptos (frente funcional/lados vistos/fachada), casos de uso, estado 2026-10-26, fases reengrose implementadas | Parcial (marco local en 01 §5) | Nuevo doc: `23_ARQUITECTURA_DOS_EJES.md` |
| G-39 | `PROGRESO_VDO.md` | Historial de versiones v1.0-1.8.0, sesiones 20/09/22/10/26/10, funcionalidades implementadas por versión, tests pendientes, errores conocidos | **NO** | Nuevo doc: `10_HISTORIAL_PROGRESO_VDO.md` |
| G-40 | `PROGRESO_VDO.yaml` | Registro YAML con checkpoints detallados (2026-09-18 → 2026-10-26), archivos creados/modificados por checkpoint, validaciones, pendientes, siguientes pasos | **NO** | Nuevo doc: `11_REGISTRO_PROGRESO_YAML.md` |
| G-41 | `Refactorización_Plan_Óptimo.md` | Plan óptimo de transacciones: antes (debounce 250ms diferimiento) vs después (focusIn/focusOut + timer 100ms), tabla comparativa, beneficios, cambios implementados (5), verificación, lecciones, checklist estado, FASE 6 | **NO** | Nuevo doc: `12_PLAN_TRANSACCIONES_OPTIMO.md` |
| G-42 | `DEUDA_TECNICA_VDO.md` | Registro deuda técnica: DT-1..DT-5 (resueltas), DT-6..DT-7 (resueltas), D17-D21 (resueltas), ajustes GUI, DT-5 (abierta), Divisiones COCO v2 (resuelto), D22 (resuelto), D23-D35 (abiertas: acabado caras, exposición cajón, tipo canto fijo, tests temporales, C0-C1-C2, reengrose Fase 1 solo L1, un reengrose por panel, mocheo sin integración, preview pacha, metadatos segmentados, reengrose horizontal, perímetro/selección directa) | **NO** | Nuevo doc: `08_REGISTRO_DEUDA_TECNICA.md` |
| G-43 | `Plan_de_Acciones_VDO.md` | Plan de acción 6 fases para incompatibilidad reactiva: diagnóstico ejecutivo, tabla problema/raíz, fases 1-6 con tareas, matriz de dependencias y ruta crítica, checklist de implementación, artefactos de salida, criterios de éxito, matriz de riesgos, siguiente acción, comando de tests headless | **NO** | Nuevo doc: `09_PLAN_ACCIONES_REACTIVIDAD.md` |
| G-44 | `Correcciones_Aplicadas.md` | 4 correcciones a `vdo_universal_inspector.py` (timer stop/start L1473, micro-header L1456, chasis L436, herrajes L886) con antes/después, verificación py_compile, patrón de parent lookup | **NO** | Nuevo doc: `13_CORRECCIONES_INSPECTOR.md` |
| G-45 | `DIAGNOSTICO_CRITICO_AXIOMAS.md` | Diagnóstico crítico: verificación de 5 bugs reales (BUG-001..005) con commits de reparación, BUG-006 revertido, tabla de criticidad, análisis de necesidad del plan de axiomas, alternativas Opción 1-4, recomendación Opción 2, roadmap Fase 1-4, veredicto final | **NO** | Nuevo doc: `14_DIAGNOSTICO_CRITICO_AXIOMAS.md` |
| G-46 | `Revision_Codigo_VDO.md` | Revisión de código `vdo_universal_inspector.py`: 6 hallazgos (timer no reinicia, recompute sin transacción ×3, métodos largos, cobertura timer), plan de correcciones (4 cambios), tabla de impacto, verificación final | **NO** | Nuevo doc: `15_REVISION_CODIGO_INSPECTOR.md` |
| G-47 | `SESION_20_SEPT_2026.md` | Informe de sesión 20/09/2026: motor unificado paneles, lógica fondo, parámetros estructurales, Task Panel PySide, FeaturePython+ViewProvider, 5 errores corregidos, fuentes investigadas, estructura archivos Codigo_VDO/, tests pendientes, métricas, notas TNP/persistencia/transacciones | **NO** | Nuevo doc: `16_SESION_20_SEPT_2026.md` |
| G-48 | `.Arquitectura de capas espacios a modulos.txt.kate-swp` | Artefacto binario de editor Kate (swap). No contiene conocimiento del proyecto. | N/A | No migrar (archivo basura de sesión de editor) |

**Resumen de brechas:** 48 gaps identificados. 31 corresponden a conocimiento ausente totalmente o parcialmente en `documentacion_v2/`. 17 están cubiertos (total o parcialmente). El archivo swap binario no es conocimiento migratorio.

---

## 3. Contrascendencia Detectada (Requiere Resolución)

Entre `ARQUITECTURA_ARBOL_NATIVO_DESVINCULACION.md` (estado "Aprobado e implementado oct 2026", describe inspector reactivo con `VDOSelectionBridge` y `QStackedWidget`) y `00_MATRIZ_CONTRADICCIONES_Y_RESOLUCION.md` (C-03, que declara **descartado** el inspector lateral flotante reactivo a favor del TaskPanel modal unificado).

**Recomendación:** Resolver a favor del ganador canónico de C-03 (TaskPanel modal + VDOTransactionMixin + debounce 100-250ms). El documento de árbol nativo debe anotarse como "arquitectura de datos y desvinculación" (válida) pero el inspector reactivo descrito en su §3 queda **supersedido** por el patrón híbrido reactivo de `02_ARQUITECTURA_TECNICA_FREECAD.md` §3 y `04_DECISIONES_ADR_Y_AXIOMAS.md` ADR-003. La parte de Friendly Unlink (§4) y la jerarquía física (§2) se mantienen vigentes.

---

## 4. Plan de Integración (Fase 3 — Zero-Loss)

Se crearán los siguientes documentos nuevos en `documentacion_v2/` para absorber cada gap con densidad técnica total (sin resúmenes ni placeholders):

| Nuevo doc | Origen principal | Contenido a inyectar |
|-----------|------------------|----------------------|
| `06_UI_MANIFIESTO_DISENO.md` | R9 (MANIFIESTO_DISENO_INTERFAZ_VDO.md) | 7 pilares, paleta cromática, poka-yoke, VDO_DoubleSpinBox, primitivas UI, rebanada vertical, regla de oro |
| `07_NESTING_OPTIMIZADOR_CORTE.md` | R11 (VDO_NESTING_README.md) | Optimizador 2D, presets, algoritmos, ejemplos, eficiencia, troubleshooting, API headless |
| `08_REGISTRO_DEUDA_TECNICA.md` | P2 (DEUDA_TECNICA_VDO.md) | DT-1..DT-35, resueltas y abiertas D23-D35 |
| `09_PLAN_ACCIONES_REACTIVIDAD.md` | P3 (Plan_de_Acciones_VDO.md) | Plan 6 fases, diagnóstico, matriz dependencias, checklist, criterios éxito, riesgos |
| `10_HISTORIAL_PROGRESO_VDO.md` | R6 (PROGRESO_VDO.md) | Historial v1.0-1.8, sesiones, funcionalidades, tests pendientes |
| `11_REGISTRO_PROGRESO_YAML.md` | P4 (PROGRESO_VDO.yaml) | Checkpoints detallados YAML |
| `12_PLAN_TRANSACCIONES_OPTIMO.md` | P1 (Refactorización_Plan_Óptimo.md) | Plan óptimo transacciones, focusIn/focusOut, timer 100ms |
| `13_CORRECCIONES_INSPECTOR.md` | P5 (Correcciones_Aplicadas.md) | 4 correcciones vdo_universal_inspector.py |
| `14_DIAGNOSTICO_CRITICO_AXIOMAS.md` | P6 (DIAGNOSTICO_CRITICO_AXIOMAS.md) | Verificación bugs, análisis necesidad axiomas, alternativas, recomendación |
| `15_REVISION_CODIGO_INSPECTOR.md` | P7 (Revision_Codigo_VDO.md) | 6 hallazgos código, plan correcciones, impacto |
| `16_SESION_20_SEPT_2026.md` | P8 (SESION_20_SEPT_2026.md) | Informe sesión 20/09/2026 |
| `17_IMPLEMENTACION_AXIOMAS.md` | R1 (AXIOMAS_VDO_Metodologia.md) | Matriz BUG-001..008, código vdo_axioms.py, vdo_types.py, tests, plan 5 fases, MAPEO_ANCHO |
| `18_ARQUITECTURA_ARBOL_DESVINCULACION.md` | R2 (ARQUITECTURA_ARBOL_NATIVO_DESVINCULACION.md) | Jerarquía árbol nativo, inspector mapping, Friendly Unlink detalle, tabla propiedades, limitaciones, lógica decisión, nota de supersedes C-03 |
| `19_DIAGNOSTICO_BUGS_GEOMETRICOS.md` | R7 (DIAGNOSTICO_BUGS_GEOMETRICOS.md) | Fallo 1, Fallo 2, tablas validación, archivos corregidos, suites prueba |
| `20_UI_CAPAS_COGNITIVAS.md` | R8 (DISENO_UI_CAPAS_COGNITIVAS_VDO.md) | Modelo cognitivo 4 capas, toolbar, 4 primitivas, flujo despiece, archivos implicados |
| `21_DICCIONARIO_SEMANTICO.md` | R4 (vdo_diccionario_semantico.md) | Estado esqueleto, reglas llenado, notas pendientes, promoción |
| `22_CONTEXTO_TECNICO_VDO.md` | R5 (CONTEXTO_TECNICO_VDO.md) | Debugging, instalación, modelos datos, marco común módulos, notas dev, matriz vanos v2 detalle |
| `23_ARQUITECTURA_DOS_EJES.md` | R10 (Arquitectura de capas espacios a modulos.txt) | Dos ejes COMPOSICIÓN/CONTEXTO, L1-L3/C0-C2, 6 lados, 3 conceptos, estado, fases reengrose |

**Total nuevos documentos:** 18. Con los 6 existentes, `documentacion_v2/` quedará con 24 documentos.

---

## 5. Recomendación Formal de Archivo Seguro

La carpeta `documentacion/` original se mantiene **intacta y en solo lectura** (cumple mandato). Una vez verificada la integración cero-pérdida en `documentacion_v2/`, se recomienda:

1. Marcar `documentacion/` como `legacy/auditoria-completa-YYYYMMDD` (solo lectura permanente).
2. Cualquier consulta futura de conocimiento técnico debe resolverse exclusivamente contra `documentacion_v2/`.
3. El archivo swap `.Arquitectura de capas espacios a modulos.txt.kate-swp` debe eliminarse como artefacto de editor no pertinente.

---

**Fin del informe forense de brechas.** Listo para proceder a la Fase 3 (integración cero-pérdida) previo conformidad.
