# 🔲 VDO - Optimizador de Corte (Nesting)

## Descripción

Sistema completo de optimización de corte 2D integrado en FreeCAD. Permite:
- ✅ Seleccionar piezas (TODO documento, SELECCIÓN, GRUPO/MÓDULO)
- ✅ Configurar tableros predefinidos (presets guardados)
- ✅ Ejecutar nesting automático
- ✅ Visualizar resultado en 3D
- ✅ Exportar a DXF

## Instalación

### 1. Requisito: Nesting Workbench

```
FreeCAD → Tools → Addon Manager
Buscar: "Nesting Workbench"
Instalar
Reiniciar FreeCAD
```

### 2. Archivos VDO (automáticos)

Ya están en tu `/Macro`:
- `vdo_nesting_presets.py` - Gestor de presets
- `vdo_nesting_workflow.py` - Lógica automatizada
- `vdo_nesting.FCMacro` - Entry point

## Flujo de Uso

### Paso 1: Crear Paneles
```
Macro → vdo_panel_estandar / vdo_panel_fachada
  ↓
O crear COCO_4C desde toolbar
```

### Paso 2: Ejecutar Nesting
```
Macro → vdo_nesting.FCMacro
  ↓
Se abre diálogo:
  1️⃣ Elige modo: TODO / SELECCIÓN / GRUPO
  2️⃣ Configura tablero (o elige preset)
  3️⃣ Elige algoritmo: Minkowski (preciso) o Physics (rápido)
  4️⃣ Click "Ejecutar Nesting"
```

### Paso 3: Visualizar Resultado
```
Se crean automáticamente en el documento:
  NestingLayout
  ├── Sheet_1 (primer tablero)
  │   ├── Boundary (contorno tablero rojo)
  │   ├── Piezas colocadas
  │   └── Etiquetas con IDs
  └── Sheet_2, Sheet_3... (si necesita más tableros)

La consola muestra:
  - Cantidad de tableros necesarios
  - Eficiencia de aprovechamiento (%)
  - Piezas no colocadas (si las hay)
```

### Paso 4: Exportar (Opcional)
```
Click derecho en NestingLayout → "Export Sheets"
  ↓
Genera DXF / SVG listo para máquina de corte
```

## Configuración de Presets

### Presets Predefinidos (Estándar del Taller)

| Nombre | Dimensiones | Espaciado | Uso |
|--------|-------------|-----------|-----|
| **Estándar EN** | 2440×1830 mm | 15 mm | Tablero europeo estándar (MDF, melamina) |
| **Medio Horizontal** | 1220×2440 mm | 15 mm | Alternativa horizontal |
| **Pequeño** | 1200×900 mm | 12 mm | Piezas chicas |
| **Cuadrado** | 1000×1000 mm | 15 mm | Módulos cuadrados |
| **Larguero** | 3000×600 mm | 15 mm | Perfiles largos |

### Agregar Preset Personalizado (Python)

```python
import sys
sys.path.insert(0, "/home/javi/.local/share/FreeCAD/Macro")
import vdo_nesting_presets as pm

# Guardar nuevo preset
pm.NestingPresetManager.save_preset(
    name="Mi Tablero",
    width=2000,
    height=1500,
    spacing=20,
    thickness=3
)

# Ver todos los presets
print(pm.NestingPresetManager.get_preset_names())

# Obtener configuración específica
config = pm.NestingPresetManager.get_preset("Estándar EN")
print(config)
```

### Importar/Exportar Presets

```python
# Exportar a archivo
pm.NestingPresetManager.export_presets_to_json("/path/to/presets.json")

# Importar desde archivo
pm.NestingPresetManager.import_presets_from_json("/path/to/presets.json")
```

## Parámetros de Optimización

### Algoritmo: Minkowski (Recomendado)
- ✅ Mayor precision
- ✅ Mejor aprovechamiento (compactness)
- ❌ Más lento
- **Mejor para**: Piezas irregulares, máximo aprovechamiento

**Parámetros:**
- `Generaciones`: 1-100 (más = mejor optimización pero más lento)
  - 1: Single pass rápido
  - 5-10: Balance bueno
  - 20+: Optimización exhaustiva

### Algoritmo: Physics (Rápido)
- ✅ Muy rápido
- ✅ Bueno para formas complejas
- ❌ Menos compacto que Minkowski
- **Mejor para**: Muchas piezas, shapes complejas

**Parámetros:**
- Genera igual que Minkowski pero ignora `Generaciones`

## Ejemplos

### Ejemplo 1: Optimizar TODOS los paneles del documento

```
1. Crea varios paneles (Panel_Base, Fachada_Principal, etc.)
2. Ejecuta: Macro → vdo_nesting.FCMacro
3. En diálogo:
   - Elige: "📋 TODOS los paneles del documento"
   - Elige preset: "Estándar EN" (2440×1830)
   - Algoritmo: "Minkowski (Preciso)"
   - Generaciones: 5
   - Click "Ejecutar Nesting"
4. Ver resultado en 3D automáticamente
```

### Ejemplo 2: Optimizar COCO_4C específico

```
1. Crea un COCO_4C (contiene 5 paneles internos)
2. Selecciona COCO_4C en Tree View (Active Object)
3. Ejecuta: Macro → vdo_nesting.FCMacro
4. En diálogo:
   - Elige: "📦 GRUPO/MÓDULO activo"
   - Elige preset: "Medio Horizontal" (1220×2440)
   - Algoritmo: "Physics (Rápido)"
   - Click "Ejecutar Nesting"
5. Se crea NestingLayout con los 5 paneles optimizados
```

### Ejemplo 3: Optimizar SELECCIÓN manual

```
1. Selecciona solo algunos paneles (Ctrl+Click en Tree)
2. Ejecuta: Macro → vdo_nesting.FCMacro
3. En diálogo:
   - Elige: "✋ SELECCIÓN (objetos marcados)"
   - Configura tamaño tablero manualmente (ej: 800×600)
   - Click "Ejecutar Nesting"
4. Optimiza solo las piezas seleccionadas
```

## Interpretación de Resultados

### Eficiencia de Utilización

```
Sheet 1: 87.5% utilización
  = (área piezas) / (área tablero) × 100
  = Mejor es menor desperdicio
```

**Interpretación:**
- **90%+**: Excelente aprovechamiento
- **80-90%**: Muy bueno
- **70-80%**: Bueno
- **<70%**: Revisar configuración

### Piezas No Colocadas

Si después de nesting aparece:
```
Piezas no colocadas (2): [Panel_A, Panel_B]
```

**Significados:**
- Tablero demasiado pequeño → Aumentar tamaño
- Espaciado muy grande → Reducir espaciado
- Geometría incompatible → Revisar forma pieza

## Troubleshooting

### "Nesting Workbench no instalado"

**Solución:**
```
FreeCAD → Tools → Addon Manager → Buscar "Nesting Workbench" → Instalar
```

### "No hay piezas seleccionadas"

**Solución:**
- Cambiar a modo "TODOS los paneles"
- O seleccionar paneles manualmente en Tree View

### Nesting muy lento

**Solución:**
- Reducir `Generaciones` (ej: 1 en lugar de 5)
- Usar algoritmo "Physics (Rápido)"
- Aumentar "Simplification" en ShapePreparer

### Resultado con muchos tableros

**Posibles causas:**
1. Tablero demasiado pequeño → Aumentar en preset
2. Espaciado demasiado grande → Reducir
3. Piezas muy grandes → Usar tablero más grande

## Integración con Exportación

El nesting genera automáticamente:

```
NestingLayout (grupo)
  ├── Sheet_1, Sheet_2...
  └── Contiene todas las piezas colocadas

Luego puedes exportar:
  1. A DXF (máquina corte)
  2. A PDF (documentación)
  3. Generar CAM job (opcional)
```

## Archivos del Sistema

| Archivo | Propósito |
|---------|-----------|
| `vdo_nesting.FCMacro` | Macro ejecutable (entry point) |
| `vdo_nesting_workflow.py` | Lógica automatizada + UI |
| `vdo_nesting_presets.py` | Gestor de presets |

## API Avanzada (Python)

### Usar directamente en macro

```python
import sys
sys.path.insert(0, "/home/javi/.local/share/FreeCAD/Macro")

from vdo_nesting_workflow import NestingDialog

# Crear diálogo y ejecutar
dialog = NestingDialog()
dialog.exec_()
```

### Ejecutar sin diálogo (headless)

```python
import FreeCAD
from vdo_nesting_presets import NestingPresetManager
from freecad.nestingworkbench.Tools.Nesting.nesting_logic import nest
from freecad.nestingworkbench.Tools.Nesting.shape_preparer import ShapePreparer

doc = FreeCAD.ActiveDocument

# Preparar piezas
preparer = ShapePreparer(doc, {})
shapes = [preparer.prepare_shape(obj, quantity=1) for obj in doc.Objects]

# Cargar preset
config = NestingPresetManager.get_preset("Estándar EN")

# Ejecutar nesting
sheets, unplaced, _, elapsed = nest(
    shapes,
    width=config['width'],
    height=config['height'],
    spacing=config['spacing'],
    algorithm='Minkowski',
    generations=2
)

print(f"✅ {len(sheets)} tablero(s) en {elapsed:.2f}s")
```

## Versión

- **VDO Nesting**: v1.0.0
- **Nesting Workbench**: v1.0.1 (requerido)
- **FreeCAD**: ≥ 1.0.0

## Soporte

Para problemas o preguntas:
1. Revisar Troubleshooting arriba
2. Verificar consola de FreeCAD (View → Panels → Python console)
3. Crear preset personalizado si es necesario

---

**Última actualización**: 2026-09-21
