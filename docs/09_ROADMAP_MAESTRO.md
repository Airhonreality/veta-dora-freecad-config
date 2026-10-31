# 09 — Roadmap maestro (mapa final)

**Fecha de corte:** 2026-10-31
**Suite:** 468 passed, 1 skipped (FreeCADCmd, `tools/run_tests_freecad.py`)
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
| Láminas 1A, L02, tramo | **Pendiente** (catálogo `laminas_dossier.json` listo para añadirlas) |
| Estilo de huella en GUI (DOS-04) | **Pendiente** |
| Anotaciones de despiece con formato de taller | Básicas (una línea por pieza) |

### Bloque D — Fachadas · **Hecho**

| Ítem | Estado |
|---|---|
| Criterio único (`VDO_Rol == "fachada"` o módulo `puerta`) | Hecho |
| Botón «Mostrar / ocultar fachadas» en barra «VDO Vista» | Registrado |
| Mismo criterio en vistas del dossier | Hecho |
| Regla Δ_S del zócalo (`+H_zocalo − luz_suelo`) | **Pendiente**: falta el parámetro de fachada |

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
2. **Parámetro de fachada para Δ_S** del zócalo. Necesita decidir dónde vive el parámetro (propiedad del COCO o de cada puerta/cajón).
3. **Láminas restantes del catálogo:** 1A (obra civil), L02 (axonometría anti-muro) y tramo de montaje. Son entradas en `laminas_dossier.json` más, en su caso, un tipo de vista nuevo.
4. **Hueco de `NombreEspacio`:** `make_espacio()` fija `Label` pero no `NombreEspacio`. Corregir en el API para que el membrete no dependa de un paso manual.
5. **Conversión de mocheos sin rotación (latente):** `vdo_cad_coco.py` convierte mocheos al marco local sin aplicar la rotación de la pose. Hoy ninguna pieza rotada recibe mocheos; el test de contrato ya cubre el lado del panel. Corregir antes de asignar mocheos al fondo u otra pieza rotada.
6. **Deuda de `docs/05` §14 (D23–D35):** no revisada en esta tanda. Varias pueden haber quedado resueltas de forma indirecta (p. ej., D53 y D30). Hace falta una pasada de verificación pieza a pieza antes de darlas por cerradas.
7. **Deuda de `docs/05` §16 (D53–D60):** D53 pasa a parcial (queda el hueco de recortes resuelto como mecanizado). D54, D55 (hecho), D59 (hecho), D60 (recolocar, abierta).
8. **Nesting:** depende de un addon externo. Si se quiere independencia, habría que portar la lógica o documentar la instalación.

---

## 3. Decisiones tomadas (no reabrir sin motivo)

| Tema | Decisión | Fuente |
|---|---|---|
| Contenedor del Espacio | `Part::FeaturePython` con Shape nula | ADR-005 |
| Metadatos de proyecto | Singleton `VDO_Proyecto` | ADR-006 |
| Escalas de lámina | 1:1 a 1:100 sin 1:15, con 1:25 | ADR-006 |
| Zócalo | Dentro de `alto`; carcasa desplazada en Z | docs/05 §17 (D59) |
| Recorte base vs división | Ranura de mecanizado; B-Rep sin solape | docs/05 §17 |
| Altura de la división | B-Rep nominal; +6 mm en lista de corte | docs/05 §17 |
| Gestor de herrajes | Cerrado: selección en panel de propiedades | docs/05 §17 (D58) |

**Cambio de comportamiento a tener en cuenta:** la UI propone zócalo por defecto (altura 100). Los COCO nuevos creados desde la interfaz llevan zócalo; los creados por código sin configuración no cambian.

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
| 2 | Definir el parámetro de fachada y cerrar Δ_S | Láminas con zócalo cubierto |
| 3 | Corregir `NombreEspacio` en `make_espacio()` | Membrete correcto sin pasos manuales |
| 4 | Añadir láminas 1A, L02 y tramo al catálogo | Dossier completo |
| 5 | Corregir la conversión de mocheos con rotación | Asignar mocheos a piezas rotadas |
| 6 | Verificación pieza a pieza de D23–D35 | Cierre formal de la deuda |
| 7 | Decidir el destino del nesting (addon o port) | Autonomía del CAM |
