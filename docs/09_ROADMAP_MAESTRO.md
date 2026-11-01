# 09 — Roadmap maestro (mapa final)

**Fecha de corte:** 2026-11-01
**Suite:** 482 passed, 1 skipped (FreeCADCmd, `tools/run_tests_freecad.py`)
**Auditoría de imports:** 71 módulos vivos, 20 no alcanzables (`.verif/auditoria.txt`)

Este documento es el mapa de referencia. Las decisiones detalladas siguen en
`docs/04` (ADR), `docs/05` §17 (ejecución y decisiones de arquitectura) y
`docs/08` §11 (estado de láminas).

---

## 1. Estado por bloque

### Bloque A — Núcleo COCO y carcasa · **Hecho**

| Ítem | Estado | Evidencia |
|---|---|---|
| Mocheos en panel base y división | Hecho, verificado en el mundo | `tests/test_coco_mocheo_rot.py` |
| Zócalo dentro de `alto` (D59) | Hecho, sin solapes, altura total invariante | `tests/test_coco_zocalo_encastre.py` |
| Ranura de encastre en la base (mecanizado) | Hecho, profundidad 6 mm, anchura 18.2 mm | ídem |
| División: +6 mm en lista de corte | Hecho (B-Rep nominal) | ídem |
| Recorte base vs división | Cerrado como ranura de mecanizado | `docs/05` §17 |

### Bloque B — Lista de corte, nesting y optimizador (CAM) · **Hecho, con dependencia externa**

| Ítem | Estado | Notas |
|---|---|---|
| Comandos `VDO_ListaCorte`, `VDO_Optimizador` | Registrados | Verificados en código; la GUI no se ha probado a mano |
| `VDO_Nesting` | Registrado, **opcional** | Requiere el addon `freecad.nestingworkbench`; si falta, el comando se desactiva |
| Fallo de `PySide2` en nesting (D56) | Corregido | Fallback a `PySide` |
| `sys.path` en `VDO/cam/` (D57) | Eliminado | |
| Bug `vdo_export_cutting_list` sin importar | Corregido | `vdo_cam_cutlist_preview.py` |
| Optimizador alcanzable (D55) | Movido a `VDO/cam/vdo_cam_optimizer_dialog.py` | |

### Bloque C — Dossier de láminas · **Núcleo hecho, catálogo incompleto**

| Ítem | Estado |
|---|---|
| Motor `generar_dossier(doc, espacio, destino)` | Hecho |
| Lámina 1B (planta del espacio) | Hecha |
| Ficha de módulo: casco, vanos libres, cerrado | Hecha |
| Escala normalizada D-3 con cabida verificada | Hecha |
| Membrete VDO (escala leída de la vista) | Hecho |
| Transacción única (un undo) | Hecho |
| Exportación SVG | Hecha, compuesta a mano (`FreeCADCmd` no expone exportación de página) |
| Lámina 1A (obra civil, sólo arquitectura) | Hecha en catálogo y motor (`familias`) |
| Lámina L02 (axonometría) | Hecha la vista base; **pendientes** corte anti-muro, globos y capturas |
| Láminas de tramo | **Pendiente**: requiere alcance nuevo (una lámina por pared o isla) |
| Líneas de escuadra de 1A (diagonales con cota) | **Pendiente**: el motor sólo admite texto en anotación |
| Estilo de huella en GUI (DOS-04) | **Pendiente** |
| Anotaciones de despiece con formato de taller | Básicas (una línea por pieza) |

### Bloque D — Fachadas · **Hecho**

| Ítem | Estado |
|---|---|
| Criterio único (`VDO_Rol == "fachada"` o módulo `puerta`) | Hecho |
| Botón «Mostrar / ocultar fachadas» en barra «VDO Vista» | Registrado |
| Mismo criterio en vistas del dossier | Hecho |
| Regla Δ_S del zócalo (`+H_zocalo − luz_suelo`) | **Hecho en puertas.** `COCO.LuzSueloDefault` (15 mm) y herencia en fachadas inferiores; un vector `VDO_Deltas_JSON` propio manda. **Cajones pendientes**: no tienen vínculo `ParentCOCO` |

### Bloque E — Herrajes · **Cerrado por decisión**

| Ítem | Estado |
|---|---|
| Gestor visual de herrajes (D58) | No migrado: el código original no existe en el repo ni en el historial. La selección vive en el panel de propiedades. Si se quiere un gestor, es funcionalidad nueva |

### Bloque F — TechDraw y plantilla · **Hecho en lo necesario**

| Ítem | Estado |
|---|---|
| Plantilla A3 VDO con área útil y cabecera | Hecha |
| Escalas normalizadas | Hechas |
| Verificación `tools/vdo_verify_fase1_techdraw.py` | Existente |

---

## 2. Pendientes abiertos

Ordenados por prioridad de cierre.

1. **Verificar en GUI real** los comandos nuevos: `VDO_Fachadas`, `VDO_ListaCorte`, `VDO_Optimizador`, `VDO_Nesting`, `VDO_Dossier`. El harness `tools/vdo_verify.py --gui` sólo cuenta `COMANDOS` (12), así que no los cubre.
2. ~~**Parámetro de fachada para Δ_S**~~ **Puertas cerradas.** Decisión: `luz_suelo` vive en el COCO (`LuzSueloDefault`), cada fachada inferior hereda `Δ_S = H_zocalo − luz` y un vector local manda. Tests en `tests/test_luz_suelo_fachada.py`. **Pendiente:** cajones (requieren vínculo `ParentCOCO`).
3. **Láminas restantes:** L02 completa (corte anti-muro, globos, capturas), escuadras de 1A y láminas de tramo. 1A y la vista base de L02 ya están en `laminas_dossier.json`.
4. ~~**Hueco de `NombreEspacio`**~~ **Cerrado.** `make_espacio()` toma `nombre_espacio` o, por defecto, `nombre`. Tests: `tests/test_espacio_dossier.py`.
5. ~~**Conversión de mocheos sin rotación**~~ **Cerrado.** `_mocheo_a_marco_pieza()` aplica `local = Rz(−rot_z)·(global − pos)` a cajas (re-ordenando w/h/d) y prismas (normalizando eje negativo). La pose de piezas sin `pos` se deriva con `pose_panel_desde_dict`, igual que la colocación final. Tests de contrato con rot 90 y 270 en `tests/test_coco_mocheo_rot.py`. Pendiente menor: no hay escenario de COCO completo con pieza rotada *y* mocheo en la suite.
6. **Deuda de `docs/05` §14 (D23–D35): pospuesta por directriz** a lectura pasiva; no bloquea el sprint de visualización ni de planos. Verificación por búsqueda, no por prueba. Estado observado:
   - **Resueltas (evidencia en código y tests):** D26 (suite permanente, 34 módulos), D33 (mocheos para tiras segmentadas, `_mocheos_locales`), D29 (perímetro por pieza en `vdo_ui_box_widget`).
   - **Abiertas (ausencia de implementación):** D23 (no existe `plan_caras`), D27 (C0/C1/C2 no implementados), D32 (sin overlay de refuerzos en preview), D35 (sin hotspots en preview), D31 (el modo «grupo» de preview es de selección, no agrupa columnas).
   - **Requieren leer el código antes de decidir:** D24, D25, D28, D30, D34.
7. **Deuda de `docs/05` §16 (D53–D60):** D53 pasa a parcial (queda el hueco de recortes resuelto como mecanizado). D54, D55 (hecho), D59 (hecho), D60 (recolocar, abierta).
8. **Nesting:** directriz: **fuera del core**. El núcleo no depende de ningún addon; sólo entrega la lista limpia de corte (rectángulos planos orientados). Si se integra, será un adapter desacoplado (Python puro o CLI externo).

---

## 3. Decisiones tomadas (no reabrir sin motivo)

| Tema | Decisión | Fuente |
|---|---|---|
| luz_suelo / Δ_S | Propiedad constructiva del COCO (`LuzSueloDefault`), heredada por fachadas inferiores; un vector local de la fachada manda | Directriz de arquitectura; `docs/09` §2, pendiente 2 |
| Nesting | Fuera del core; sin dependencia de addons | Directriz de arquitectura |
| Contenedor del Espacio | `Part::FeaturePython` con Shape nula | ADR-005 |
| Metadatos de proyecto | Singleton `VDO_Proyecto` | ADR-006 |
| Escalas de lámina | 1:1 a 1:100 sin 1:15, con 1:25 | ADR-006 |
| Zócalo | Dentro de `alto`; carcasa desplazada en Z | docs/05 §17 (D59) |
| Recorte base vs división | Ranura de mecanizado; B-Rep sin solape | docs/05 §17 |
| Altura de la división | B-Rep nominal; +6 mm en lista de corte | docs/05 §17 |
| Gestor de herrajes | Cerrado: selección en panel de propiedades | docs/05 §17 (D58) |

**Cambios de comportamiento a tener en cuenta:**
- La UI propone zócalo por defecto (altura 100). Los COCO nuevos creados desde la interfaz llevan zócalo; los creados por código sin configuración no cambian.
- Las puertas batiente **inferiores** de un COCO heredan Δ_S: quedan 15 mm sobre el piso (`LuzSueloDefault`), en lugar de bajar 16 mm bajo el vano. Con montaje embebida o semiparche, la rama de deltas también cambia el ancho (preset del montaje). Las puertas sin COCO padre no cambian.

---

## 4. Riesgos y deuda operativa

- **Undo en FreeCADCmd:** `UndoMode` viene apagado; los tests que cuentan transacciones lo activan explícitamente. No es un bug del motor, pero conviene recordarlo al escribir tests nuevos.
- **Instantánea de contrato** (`tests/datos/props_snapshot.json`): cambia cada vez que se añade una propiedad. Regenerar con `tools/vdo_snapshot_props.py` y revisar el diff ignorando direcciones de memoria.
- **Exportación SVG:** depende de la geometría de `TechDraw.project`, no de `viewPartAsSvg`, que resultó poco fiable en la suite completa.
- **Archivos generados:** `.verif/` está ignorado por git; los informes de verificación se regeneran y no son fuente de verdad.

---

## 5. Ruta recomendada (próximos pasos)

| Orden | Acción | Bloquea a |
|---|---|---|
| 1 | Probar a mano en FreeCAD GUI los cinco comandos nuevos | Confianza en la entrega |
| 2 | Vincular cajones al COCO para heredar Δ_S | Cajones inferiores con zócalo |
| 3 | Corregir `NombreEspacio` en `make_espacio()` | Membrete correcto sin pasos manuales |
| 4 | Completar L02 (anti-muro, globos), escuadras de 1A y tramos | Dossier completo |
| 5 | Corregir la conversión de mocheos con rotación | Asignar mocheos a piezas rotadas |
| 6 | Verificación pieza a pieza de D23–D35 | Cierre formal de la deuda |
| 7 | Nesting fuera del core: exportar matriz 2D agnóstica (`id, largo, ancho, espesor, material, veta_rotacion_permitida`) y un adapter opcional | Autonomía del CAM |
