# 📋 Documento de Progreso VDO - Motor Multiestado

> **NOTA**: El registro de progreso estructurado y canónico se encuentra en [`PROGRESO_VDO.yaml`](../PROGRESO_VDO.yaml). Este archivo se mantiene como referencia histórica.

## 🎯 Objetivo del Proyecto
Consolidar un motor unificado de paneles/fachadas y cofres para FreeCAD, eliminando configuración manual en la interfaz. Arquitectura **Code-as-UI** con patrón de envoltorio delgado (Thin Wrapper/Facade).

---

## 📁 Estructura Actual del Proyecto

```
Macro/
├── vdo_manifest.py              ← Contrato de datos (v1.6.0)
├── vdo_guardian.py              ← Guardián de dependencias
├── vdo_panel_core.py            ← Motor central de paneles
├── vdo_coco_core.py             ← Motor central de cofres
├── vdo_panel_estandar.FCMacro   ← Envoltorio: Panel Estándar
├── vdo_panel_fachada.FCMacro    ← Envoltorio: Panel Fachada
├── vdo_coco_4c.FCMacro          ← Envoltorio: COCO 4C
├── VDO_Crear_Hoja_Melamina.FCMacro ← Legacy (compatibilidad)
├── vdo_toolbar_inject.py        ← Script de inyección de toolbar XML
└── icons/
    ├── vdo_panel.svg
    ├── vdo_coco.svg
    ├── vdo_panel_estandar.svg
    ├── vdo_panel_fachada.svg
    └── vdo_workbench.svg
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
make_coco(configuracion)

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
│  from vdo_coco_core import make_coco                        │
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

*Documento generado automáticamente - Última actualización: v1.5.0 (20/09/2026)*
