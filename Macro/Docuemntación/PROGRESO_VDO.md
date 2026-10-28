# 📋 Documento de Progreso VDO - Motor Multiestado

## 🎯 Objetivo del Proyecto
Consolidar un motor unificado de paneles/fachadas y cofres para FreeCAD, eliminando configuración manual en la interfaz. Arquitectura **Code-as-UI** con patrón de envoltorio delgado (Thin Wrapper/Facade).

---

## 📁 Estructura Actual del Proyecto

```
Macro/
├── vdo_manifest.py              ← Contrato de datos (v1.4.0)
├── vdo_guardian.py              ← Guardián de dependencias
├── vdo_panel_core.py            ← Motor central de paneles
├── vdo_coco_core.py             ← Motor central de cofres
├── vdo_panel_estandar.FCMacro   ← Envoltorio: Panel Estándar
├── vdo_panel_fachada.FCMacro    ← Envoltorio: Panel Fachada
├── vdo_coco_4c.FCMacro          ← Envoltorio: COCO 4C
├── VDO_Crear_Hoja_Melamina.FCMacro ← Legacy (compatibilidad)
├── PROGRESO_VDO.md              ← Este documento
└── icons/
    ├── vdo_panel.svg
    ├── vdo_panel_v2.svg
    ├── vdo_coco.svg
    ├── vdo_coco_v2.svg
    ├── vdo_workbench.svg
    └── vdo_workbench_v2.svg
```

---

## ✅ Funcionalidades Implementadas

### 1. Arquitectura Base (v1.2.0)

| Componente | Estado | Descripción |
|------------|--------|-------------|
| `vdo_panel_core.py` | ✅ COMPLETADO | Motor central de paneles con parámetro `tipo` |
| `vdo_coco_core.py` | ✅ COMPLETADO | Motor central de cofres |
| Envoltorios (.FCMacro) | ✅ COMPLETADOS | 3 envoltorios ultraligeros |
| `vdo_manifest.py` | ✅ ACTUALIZADO | Contrato de datos unificado |

### 2. Motor de Paneles (`vdo_panel_core.py`)

```python
# Función principal
crear_pieza(configuracion)

# Parámetros soportados
configuracion = {
    "tipo": "estandar" | "fachada",
    "nombre": str,
    "cantos": {"norte": bool, "sur": bool, "este": bool, "oeste": bool},
    "etiqueta": str
}
```

**Propiedades FreeCAD inyectadas:**
- `VDO_Tipo`: Tipo de panel ("estandar" | "fachada")
- `VDO_Etiqueta`: Identificador descriptivo
- `VDO_Canto Norte/Sur/Este/Oeste`: Booleanos de cantos

### 3. Motor de Cofres (`vdo_coco_core.py`)

```python
# Función principal
crear_coco(configuracion)

# Parámetros soportados
configuracion = {
    "nombre": str,
    "etiqueta": str,
    "fondo": bool,
    "calibre_fondo": int,
    "profundidad_ranura": int,
    "distancia_borde": int,
    "tapa": "externo" | "interno",
    "base": "externo" | "interno"
}
```

---

## 📊 Parámetros Implementados

### Capa Global (`Params_Melamina`)

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `espesor` | 18mm | Espesor nominal del tablero |
| `canto_grueso` | 2mm | Espesor de cinta de canto |
| `ranura_fondo` | 3mm | Profundidad de ranura para trasera |

### Capa Local (`Params`)

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `alto` | 720mm | Alto total del módulo |
| `ancho` | 600mm | Ancho total del módulo |
| `fondo_modulo` | 580mm | Profundidad total del módulo |
| `espesor` | 18mm | Espesor estándar del tablero |

### Configuración del Fondo (v1.3.0)

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `habilitado` | True | Interruptor de existencia |
| `calibre` | 6mm | Espesor del fondo |
| `profundidad_ranura` | 3mm | Para fondos delgados |
| `distancia_borde` | 18mm | Retranqueo del borde trasero |

### Configuración Estructural (v1.4.0)

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `tapa` | "externo" | Tapa por encima de laterales |
| `base` | "interno" | Base entre laterales |

---

## 🔄 Flujo de Ejecución

```
┌─────────────────────────────────────────────────────────────┐
│  Usuario hace clic en: vdo_coco_4c.FCMacro                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  FreeCAD ejecuta el envoltorio (configuración)             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  from vdo_coco_core import crear_coco                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  1. vdo_guardian.vdo_guard() - Asegura entorno             │
│  2. _configurar_paneles_coco() - Laterales, base, techo    │
│  3. _configurar_fondo() - Respaldo condicional             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  FreeCAD actualizado con geometría + metadatos VDO         │
└─────────────────────────────────────────────────────────────┘
```

---

## 📐 Lógica del Fondo (Respaldo)

### Decisiones de Diseño

| Condición | Comportamiento |
|-----------|----------------|
| `fondo = False` | PANEL_FONDO eliminado del modelo |
| `fondo = True` + `calibre ≤ 8mm` | Fondo delgado ranurado |
| `fondo = True` + `calibre > 8mm` | Fondo grueso sin ranura |

### Fórmulas de Cálculo

**Fondo Delgado:**
- Ancho: `ancho_coco - (2×espesor) + (2×profundidad_ranura)`
- Alto: `alto_coco - (2×espesor) + (2×profundidad_ranura)`
- Posición: centrado en ranuras

**Fondo Grueso:**
- Ancho: `ancho_coco - (2×espesor)`
- Alto: `alto_coco - (2×espesor)`
- Posición: retranqueado (`distancia_borde`)

---

## 📐 Lógica Estructural (Tapa y Base)

### Tabla de Configuración

| Tapa | Base | Laterales | Techo | Base |
|------|------|-----------|-------|------|
| externo | interno | alto - espesor | ancho total | ancho - 2×espesor |
| externo | externo | alto - espesor | ancho total | ancho total |
| interno | interno | alto total | ancho - 2×espesor | ancho - 2×espesor |
| interno | externo | alto total | ancho - 2×espesor | ancho total |

---

## 🎨 Iconos Disponibles

| Icono | Uso |
|-------|-----|
| `vdo_panel.svg` | Panel estándar |
| `vdo_panel_v2.svg` | Variante panel |
| `vdo_coco.svg` | COCO 4C |
| `vdo_coco_v2.svg` | Variante COCO |
| `vdo_workbench.svg` | Workbench VDO |

---

## 📋 Tareas Pendientes

### Prioridad Alta
- [ ] Crear icono diferenciado para `vdo_panel_fachada.svg`
- [ ] Probar todas las macros en FreeCAD
- [ ] Asignar botones en la barra de herramientas

### Prioridad Media
- [ ] Agregar más variantes de cofres (COCO 2C, COCO 3C)
- [ ] Implementar generador de despiece (lista de cortes)
- [ ] Integración con reportes/ERP

### Prioridad Baja
- [ ] Crear InitGui.py para workbench automático
- [ ] Agregar validación de parámetros en tiempo real
- [ ] Documentación de usuario final

---

## 🐛 Errores Conocidos

Ninguno reportado actualmente.

---

## 📝 Notas de Desarrollo

### Convenciones de Nomenclatura

| Tipo | Prefijo | Ejemplo |
|------|---------|---------|
| Motor | `vdo_*_core.py` | `vdo_panel_core.py` |
| Envoltorio | `vdo_*.FCMacro` | `vdo_panel_estandar.FCMacro` |
| Icono | `vdo_*.svg` | `vdo_panel_estandar.svg` |
| Propiedades | `VDO_*` | `VDO_Tipo`, `VDO_Calibre` |

### Estructura de un Envoltorio

```python
# 1. Bootstrap (siempre igual)
import sys
import FreeCAD as App
_vdo_macro_dir = App.getUserMacroDir(True)
if _vdo_macro_dir not in sys.path:
    sys.path.insert(0, _vdo_macro_dir)

# 2. Importar motor
from vdo_X_core import crear_X

# 3. Definir configuración
configuracion = { ... }

# 4. Ejecutar
crear_X(configuracion)
```

---

## 🔄 Historial de Versiones

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.1.0 | - | Estructura inicial (archivos separados) |
| 1.2.0 | - | Motor unificado de paneles + envoltorios |
| 1.3.0 | - | Lógica del fondo (respaldo) |
| 1.4.0 | - | Parámetros de tapa/base externo/interno |
| 1.5.0 | 20/09/2026 | Task Panel PySide + FeaturePython + ViewProvider |
| 1.6.0 | 26/10/2026 | Marco local, fondo en Y+, exposición y cantos |
| 1.7.0 | 26/10/2026 | Fase 1: motor de reengroses/pachas y panel L1 |
| 1.8.0 | 26/10/2026 | Fases 2 y 3: COCO, vanos, repisas y UI contextual |

---

## 📋 Última Sesión: 20 de Septiembre 2026

### Funcionalidades Implementadas (v1.5.0)

| Componente | Archivo | Estado |
|------------|---------|--------|
| FeaturePython | `vdo_coco_core.py` | ✅ COMPLETADO |
| ViewProvider | `vdo_coco_core.py` | ✅ COMPLETADO |
| Task Panel PySide | `vdo_coco_task.py` | ✅ COMPLETADO |
| Transacciones Undo/Redo | `vdo_coco_4c.FCMacro` | ✅ COMPLETADO |
| Icono dinámico | `vdo_coco_core.py` | ✅ COMPLETADO |

### Errores Corregidos

1. ✅ `'FeaturePython' object has no attribute 'Shape'` → Cambiado a `Part::FeaturePython`
2. ✅ `TypeError` en `getStandardButtons` → Eliminado cast a `int()`
3. ✅ Ruta del icono incorrecta → Buscar en carpeta de macros
4. ✅ Dos versiones de `vdo_coco_core.py` → Consolidado en `code_core/`
5. ✅ Falta `vdo_coco_task.py` en instalador → Copiado a `code_core/` y `macros/`

### Documentación Creada

- `SESION_20_SEPT_2026.md` - Resumen completo de la sesión
- `docs/PLAN_TASK_PANEL_COCO.md` - Plan detallado
- `docs/DECISIONES_TECNICAS.md` - Registro de decisiones

### Pruebas Pendientes

| Prueba | Descripción | Estado |
|--------|-------------|--------|
| 1 | Crear COCO desde macro | ⏳ |
| 2 | Task Panel abre al crear | ⏳ |
| 3 | Modificar propiedades + OK | ⏳ |
| 4 | Undo/Redo funciona | ⏳ |
| 5 | Reedición (doble clic) | ⏳ |
| 6 | Guardar/Cargar .FCStd | ⏳ |

---

## 📞 Contacto

- **Taller**: Veta de Oro (VDO)
- **Plataforma**: FreeCAD
- **Motor**: VDO Engine v1.5.0

---

*Documento generado automáticamente - Última actualización: v1.8.0 (26/10/2026)*

---

## 🧱 Sesión 22/10/2026 — Divisiones COCO v2

### Implementado
- `vdo_layout.py`: modelo puro de matriz de vanos, resolución fija/libre,
  overflow, anidación y serialización JSON v2.
- `vdo_coco_preview2d.py`: preview frontal con celdas seleccionables y overflow.
- `vdo_coco_divisions_task.py`: pestaña única “Divisiones” con preview, botones
  `+X/−X/+Y/−Y`, árbol agrupado por filas Y e inspector de vano.
- `vdo_coco_core.py`: propiedad `VDO_Divisiones`; divisiones construidas desde
  la cavidad interior real (`alto-2t`, `ancho-2t`) con piezas sin cruces.
- `vdo_coco_spaces.py`: `generar_divisiones_matriz()` para geometría/despiece.
- `vdo_coco_unified_task.py`: sustituidas las dos tablas de espacios por la
  pestaña “Divisiones”; resumen y validación de overflow al aplicar.

### Validación
- `py_compile` OK.
- Tests headless: 1×1, 3 columnas, 3×2, anidación X→Y→X, medidas fijas,
  overflow, preview/editor offscreen y `common().Volume == 0` entre piezas.
- COCO headless: bbox correcto, `VDO_Paneles_JSON` con laterales, base, techo,
  fondo y divisiones; `VDO_Divisiones` persistido.

### Pendiente
- Probar visualmente en FreeCAD GUI.
- Fase 1: transacción al abrir + debounce si se implementa edición en vivo.
- Revisar migración de subdivisiones legacy anidadas.

---

## 🧭 Sesión 26/10/2026 — Marco local, fondo en Y+ y exposición/cantos

### Implementado
- **Marco local único:** `vdo_frames.py` fija `X+ = derecha`, `Y+ = fondo`,
  `Z+ = arriba`, `frente funcional = Y−`. Incluye normales por lado,
  rotación de normales y serialización de exposición. Sin FreeCAD ni Qt.
- **Fondo delgado corregido:** el fondo de 6 mm ya no se coloca en el frente.
  Va en `Y = fondo − calibre − profundidad_ranura`, con ranuras reales en
  laterales, base y techo; las divisiones terminan en la cara frontal del
  fondo y no lo atraviesan.
- **Preview 2D:** etiqueta `FRENTE (Y−)` y ejes `X→  Y↑`; el preview sigue
  siendo local y no se espeja aunque el módulo esté rotado en el espacio.
- **Exposición contextual:** propiedades `VDO_Lados_Vistos` y
  `VDO_Lados_Apoyados` (JSON) en todos los módulos; UI de seis lados
  (`Frente, Fondo, Izquierda, Derecha, Superior, Inferior`) con estados
  `Oculto / Visto / Apoyado` en la pestaña Medidas → Colocación.
- **Política de cantos:** `vdo_finish.py` traduce lados vistos + rol de pieza
  + tapa/base en cantos por borde (`norte/sur/este/oeste`). Sólo los bordes
  exteriores vistos reciben `RIG`; uniones y bordes ocultos quedan en `FX`.
- **Despiece:** `VDO_Paneles_JSON` incorpora `rol`, `cantos`, `lados_vistos`
  y `lados_apoyados`; el CSV exporta columnas `Edge N/S/E/W`.
- **Documentación:** `vdo_layout` mantiene Divisiones v2; las piezas internas
  reciben `rol = division_x | division_y` para la política de acabados.

### Validación
- `py_compile` OK en todos los módulos tocados.
- `freecadcmd`: COCO 6 mm y 18 mm, fondos de 300/580 mm, profundidad de ranura
  3/6 mm; `Shape.isValid() == True` y `common().Volume == 0` entre todas las
  piezas (incluidas divisiones 3×2).
- Fondo delgado comprobado en `Y = 571..577` para fondo 580, calibre 6 y
  ranura 3; ya no aparece en `Y = 0`.
- Preview Qt offscreen: contiene `FRENTE (Y−)` y `X→  Y↑`.
- Panel Qt offscreen: seis combos, carga/guardado de exposición y `accept()` OK.
- CSV: cabecera y filas con `Edge N/S/E/W`; valores `RIG/FX/SMRG` conservados.
- Regresión: tests headless de Divisiones v2, anidación, overflow, editor,
  bbox y despiece siguen pasando.

### Decisiones
- **No espejar el preview:** el frente local es siempre la referencia de
  edición; la orientación global pertenece a C1/3D.
- **Cantos por borde, no por cara:** una cara vista no implica cantear todos
  sus bordes; el plan depende de la unión concreta.
- **Fondo visto:** de momento se modela la cara, no el canto; el panel de
  fondo queda sin cantos porque sus bordes van en ranura.
- **C0/C1/C2 quedan fuera de esta etapa:** la exposición se introduce a mano
  en el módulo; `VDO_Espacio` llegará después.

### Pendiente
- Probar visualmente en FreeCAD GUI (reiniciar para descartar caché de módulos).
- Definir acabado de **caras** (no sólo cantos), necesario para divisores con
  fondo visto sin fachada.
- Extender exposición/cantos a cajones y paneles sueltos.
- Implementar C0/C1/C2 y sustituir la exposición manual por cálculo contextual.

---

## 🧩 Fase 1 — Motor de Reengroses/Pachas + Panel L1 (26/10/2026)

### Implementado
- **`vdo_reengrose.py` puro:** DTO `ReengroseModifier`, validación, defaults,
  serialización JSON y helpers de geometría local.
- **Geometría L1:** tira paralela/transversal, caras A/B, alineación
  frente/centro/fondo, espesor automático o editable.
- **Pacha:** parcial (tira) y total (duplicado completo de la cara).
- **Cantos:** independiente cantea la tira aparte; pacha deja las piezas
  individuales en `FX` y emite `cantos_bloque` en `RIG`.
- **Colisiones puras:** `detectar_colision`, `calcular_vano_neto_con_reengrose`
  y `generar_mocheo_repisa` con retroceso por defecto y mocheo opcional.
- **Panel L1:** propiedades nativas `VDO_Reengrose_*`, compound base+tira,
  compatibilidad con paneles viejos y snapshot `VDO_Reengrose_JSON`.
- **UI L1:** grupo “Reengrose / Pacha”, habilitación contextual y resumen.
- **Despiece:** subpiezas, `grupo_pacha`, `operacion` y columnas `Group` /
  `Operation` en el CSV.
- **Tooltips:** controles nuevos y controles clave de Panel, COCO, Divisiones
  y Cajón con lenguaje de taller.
- **Tests permanentes:** `tests/test_vdo_reengrose.py` (puro) y
  `tests/test_reengrose_l1.py` (FreeCAD).

### Validación
- `python3 -m unittest tests/test_vdo_reengrose.py`: 9 tests OK.
- `freecadcmd tests/test_reengrose_l1.py`: 6 tests OK.
- `freecadcmd` con caras A/B, paralela/transversal, independiente/pacha
  parcial/pacha total: shapes válidos, 2 sólidos, `common().Volume == 0`.
- UI Qt offscreen: activar/desactivar, carga/guardado y tooltips OK.
- CSV: subpiezas de pacha agrupadas y operación de bloque unificado OK.
- Regresión: creación de panel viejo y panel estándar sigue funcionando.

### Limitaciones / siguiente fase
- Un solo reengrose por panel.
- Cuatro tiras perimetrales requieren selector de borde (Fase 2).
- `vdo_layout`, COCO y `vdo_finish` todavía no consumen los helpers de vano
  ni el mocheo automático.

---

## 🧩 Fases 2 y 3 — Reengroses en COCO, layout y UI contextual (26/10/2026)

### Implementado
- **`vdo_layout.py`:** `resolve_layout(..., reengroses=...)` con luz clara y
  geometría nominal; extras por cara A/B/ambos; laterales, base y techo.
- **`vdo_reengrose.py`:** geometría genérica de caja por ejes
  (`calcular_geometria_caja`), `despiece_caja`, caras `ambos` y despiece con
  `cantos_bloque`.
- **`vdo_coco_spaces.py`:** divisiones con reengrose, obstáculos verticales y
  ajuste automático de repisas por colisión (retroceso o mocheo).
- **`vdo_coco_core.py`:** propiedad `VDO_Reengrose_JSON`, reengroses de
  carcasa, recorte de refuerzos contra núcleos, expansión de subpiezas y
  despiece final.
- **UI contextual:** grupo “Elementos / refuerzos” en el árbol e inspector
  “Reengrose / Refuerzo” con elemento, activo, orientación, ancho, espesor,
  cara A/B/ambos, alineación, fabricación, alcance y política de repisa.
- **Tooltips:** controles nuevos de COCO y Divisiones con lenguaje de taller.
- **Persistencia:** al aplicar se guarda `VDO_Reengrose_JSON` y se recomputa.
- **CSV:** subpiezas de COCO con `Group` y `Operation`.

### Validación
- Tests puros:
  - `tests/test_vdo_reengrose.py`: 9 OK.
  - `tests/test_layout_reengrose.py`: 6 OK.
- Tests FreeCAD:
  - `tests/test_reengrose_l1.py`: 6 OK.
  - `tests/test_coco_reengrose.py`: 8 OK.
- COCO 2×2 con división central, tira de 50 mm:
  - vano izquierdo neto 255 mm; derecho 273 mm;
  - repisa izquierda retrocedida a 521 mm de profundidad;
  - mocheo con `mocheos` de 18 × 50 mm;
  - `common().Volume == 0` en todos los casos.
- Pacha: dos subpiezas, grupo, operación y `cantos_bloque`.
- CSV con `Group`/`Operation` verificado.
- COCO estándar sin reengrose: bbox y ausencia de solapes conservados.
- Carcasa con reengrose lateral y base: sin solapes.

### Limitaciones
- El preview 2D todavía no dibuja las tiras.
- Las tiras de carcasa cortadas por divisiones conservan metadatos de medida
  nominal; falta despiece segmentado.
- El perímetro de cuatro tiras sigue pendiente de un selector de borde.
