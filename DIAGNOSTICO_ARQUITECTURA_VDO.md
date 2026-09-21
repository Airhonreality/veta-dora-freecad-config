# 🏗️ DIAGNÓSTICO ARQUITECTÓNICO - Sistema VDO

**Fecha:** 2026-09-21  
**Estado:** Revisión completa  
**Scope:** Schemas, tipos, kernel, macros

---

## 📊 ARQUITECTURA ACTUAL

```
VDO Kernel (Puro)
├── vdo_manifest.py
│   └─ Diccionario Python con TODA la configuración
│   └─ Estructura de datos (capa_global, capa_local, materiales, etc)
│
├── vdo_guardian.py
│   └─ Crea/valida hojas de cálculo en FreeCAD
│   └─ Inyecta parámetros desde manifest
│
├── vdo_*_core.py (panel_core, coco_core, etc)
│   └─ Lógica geométrica pura
│   └─ Lee parámetros de hojas → genera geometría
│   └─ Inyecta propiedades personalizadas en objetos
│
├── vdo_*_spaces.py
│   └─ Cálculos de espacios/dimensiones
│
└── vdo_*_task.py
    └─ Task panels (UI en FreeCAD)

Macros de Usuario (.FCMacro)
├── vdo_panel_estandar.FCMacro → usa vdo_panel_core.py
├── vdo_panel_fachada.FCMacro → usa vdo_panel_core.py
├── vdo_coco_4c.FCMacro → usa vdo_coco_core.py
└── VDO_Crear_Hoja_Melamina.FCMacro → usa vdo_guardian.py

Sistema de Distribución
├── vdo_clone.py (instalación)
├── vdo_publish.py (publicación)
└── config/freecad/user.cfg (toolbar + settings)
```

---

## ✅ FORTALEZAS ACTUALES

### 1. **Separación de Concerns (Buena)**
```
✓ vdo_manifest.py = Datos puros (sin lógica)
✓ vdo_*_core.py = Lógica pura (sin UI)
✓ vdo_*_task.py = UI (Task panels)
```

### 2. **Guardian Pattern (Excelente)**
- Cualquier macro puede llamar `vdo_guard()`
- Auto-configura documento (crea hojas, inyecta parámetros)
- Garantiza estado consistente

### 3. **Parámetros Inyectados via Expresiones (Inteligente)**
```python
panel.setExpression("Length", "<<Params>>.ancho")
# Cambias Params.ancho → Panel se actualiza automáticamente
```

### 4. **Propiedades Personalizadas en Objetos (Flexible)**
```python
panel.VDO_Tipo = "estandar"
panel.VDO_Canto_Norte = True
# Metadata viaja con el objeto en FreeCAD
```

### 5. **Manifest como Fuente Única de Verdad (Correcto)**
- Un único lugar de configuración
- Extensible
- Exportable a JSON/ERP

---

## ⚠️ PUNTOS DÉBILES

### 1. **Todo vive en Python, no hay esquema formalizado**

**Problema:**
```python
# vdo_manifest.py mezcla:
# - Configuración de UI (modulos_ui)
# - Parámetros de taller (capa_global)
# - Material specs (materiales)
# - Dependencias del sistema (dependencias)

# Todo es un dict de Python, sin validación de tipos
materiales = {
    "melamina": {
        "espesores": [18, 25],  # ¿Es esto lista? ¿O rango?
        "presentaciones": "2440 x 1830"  # ¿Texto? ¿O JSON?
    }
}
```

**Impacto:**
- ❌ No hay validación en tiempo de carga
- ❌ Fácil añadir campos inconsistentes
- ❌ Difícil evolucionar sin quebrar código

### 2. **Propiedades de Material están Hardcodeadas**

**Problema:**
```python
# Cuando exportas lista de corte, ¿cómo sabe qué material es?
# No hay forma automática de extraer:
# - Referencia del material (Roble, Melamina, etc)
# - Tipo (RH, Standar)
# - Calibre (18mm, 25mm)

# El script export_cutting_list.py tendría que hardcodear:
if panel.thickness == 18:
    material = "18mm_Melamina_Standar"  # ❌ Hardcode
```

### 3. **Hojas de cálculo como "Base de Datos" Informal**

**Problema:**
```
Params_Melamina (hoja)          Params (hoja local)
├─ Parámetro | Valor            ├─ A1: alto (720)
├─ espesor   | 18               ├─ A2: ancho (600)
├─ canto_grueso | 2             ├─ A3: fondo_modulo (580)
└─ ranura_fondo | 3             └─ A4: espesor (18)
```

**Problemas:**
- ❌ No hay tipado (¿es 18 mm? ¿milímetros?)
- ❌ No hay validación (¿espesor negativo?)
- ❌ Difícil de programar (siempre leer celda A1?)
- ❌ Difícil de versionar (cambios no registrados)

### 4. **Propiedades de Panel sin Contrato Formal**

**Problema:**
```python
# Un panel tiene:
# - VDO_Tipo (string)
# - VDO_Etiqueta (string)
# - VDO_Canto_Norte, Sur, Este, Oeste (bool)
# - Referencia de Material (???) ← NO EXISTE

# ¿Cómo sabe export_cutting_list qué panel pide qué material?
```

### 5. **Sin Versionado de Schema**

```python
# vdo_manifest.py tiene version: "1.6.0"
# PERO:
# - ¿Qué cambió entre 1.5 y 1.6?
# - Si cambio el schema, ¿documentos viejos se rompen?
# - ¿Cómo migro documentos?
```

---

## 🎯 RECOMENDACIONES

### A. NIVEL INMEDIATO (Para export_cutting_list)

**Sin cambiar arquitectura:**

1. **Extender propiedades de Panel:**
```python
# En vdo_panel_core.py, añadir:
panel.addProperty("App::PropertyString", "VDO_Material_Ref", "VDO")
panel.addProperty("App::PropertyString", "VDO_Material_Type", "VDO")
panel.VDO_Material_Ref = "Roble"  # ← Del manifest
panel.VDO_Material_Type = "RH"
```

2. **Export Script Lee Propiedades:**
```python
# vdo_export_cutting_list.py
for panel in doc.Objects:
    if hasattr(panel, "VDO_Tipo"):
        material = f"{panel.Height}mm_{panel.VDO_Material_Ref}_{panel.VDO_Material_Type}"
        # ✅ Dinámico, sin hardcode
```

**Costo:** Bajo (1 línea por propiedad)  
**Beneficio:** Export funciona sin hardcode

---

### B. NIVEL ARQUITECTÓNICO (Mejora a largo plazo)

#### Opción B1: **Formalizar Manifest en YAML/JSON**

```yaml
# vdo_manifest.yml (en el repo)
version: "1.6.0"
taller: "Veta de Oro"

materials:
  melamina:
    label: "Melamina"
    color: "#E8D5C4"
    types:
      standard:
        name: "Estándar"
        cost_per_m2: 15
      rh:
        name: "Roble"
        cost_per_m2: 25
    thicknesses: [18, 25, 30]
    sizes:
      standard: "2440 x 1830"

parameters:
  global:
    espesor:
      value: 18
      unit: "mm"
      min: 10
      max: 50
    canto_grueso:
      value: 2
      unit: "mm"
```

**Beneficios:**
- ✅ Estructurado, validable (JSON Schema)
- ✅ Versionable en git
- ✅ Exportable a ERP
- ✅ Humano-legible

**Costo:** Reescribir guardian.py para leer YAML  
**Timidez:** 2-3 días

---

#### Opción B2: **Tipado con Dataclasses/Pydantic**

```python
# vdo_schema.py
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Material:
    name: str
    types: Dict[str, str]  # "rh" → "Roble"
    thicknesses: List[int]
    unit: str = "mm"

@dataclass
class Parameters:
    global_params: Dict[str, float]
    local_params: Dict[str, float]

@dataclass
class VDOManifest:
    version: str
    materials: Dict[str, Material]
    parameters: Parameters
    # Validación automática en tiempo de carga
```

**Beneficios:**
- ✅ Type hints (IDE autocompletar)
- ✅ Validación en tiempo de carga
- ✅ Documentación automática

**Costo:** Bajo (dataclasses es Python puro)

---

### C. PARA EXPORT_CUTTING_LIST (Decisión de Diseño)

**Pregunta clave:**
> "¿Debe el manifest definir TODOS los materiales posibles?"
> O
> "¿Cada panel en FreeCAD decide su propio material?"

**Opción 1: Material en Manifest (Centralizado)**
```python
# vdo_manifest.py
materials: {
    "18_Roble_RH": {...},
    "25_Melamina_STD": {...},
}
# Ventaja: Control central
# Desventaja: No es flexible
```

**Opción 2: Material como Propiedad de Panel (Distribuido)**
```python
panel.VDO_Material = "18_Roble_RH"
# Referencia al manifest, pero panel decide
# Ventaja: Flexible
# Desventaja: Más proiedades en objetos
```

**Recomendación:** Opción 2 (Distribuido)
- El manifest define catálogo
- Cada panel elige de ese catálogo
- Export extrae propiedades

---

## 📋 TABLA RESUMEN

| Aspecto | Estado | Acción |
|--------|--------|--------|
| **Separación Concerns** | ✅ Bueno | Mantener |
| **Guardian Pattern** | ✅ Excelente | Mantener |
| **Expresiones Inyectadas** | ✅ Inteligente | Mantener |
| **Manifest como Datos** | ⚠️ Informal | Formalizar a YAML/JSON |
| **Tipado de Datos** | ❌ Ninguno | Añadir Dataclasses |
| **Schema Versionado** | ❌ No | Implementar |
| **Propiedades de Material** | ❌ No existen | Crear (VDO_Material_Ref, etc) |
| **Export sin Hardcode** | ❌ Imposible | Habilitado con propiedades |

---

## ✨ PROPUESTA CONCRETA

### Fase 1 (Immediate - 1 día)
```python
# En vdo_panel_core.py, función _inyectar_propiedades():

panel.addProperty("App::PropertyString", "VDO_Material_Ref", "VDO")
panel.addProperty("App::PropertyString", "VDO_Material_Type", "VDO")

panel.VDO_Material_Ref = configuracion.get("material_ref", "Melamina")
panel.VDO_Material_Type = configuracion.get("material_type", "Standar")

# Ahora export_cutting_list.py puede leer:
material_str = f"{thickness}mm_{panel.VDO_Material_Ref}_{panel.VDO_Material_Type}"
```

### Fase 2 (Architecture - 3 días)
```
✓ Convertir vdo_manifest.py → vdo_manifest.yml
✓ Crear vdo_schema.py con Dataclasses
✓ Guardian.py lee YAML + valida tipos
✓ Documentación de schema
```

### Fase 3 (Evolution - Opcional)
```
✓ Versionado de schema
✓ Migración de documentos
✓ ERP integration layer
```

---

## 🎓 CONCLUSIÓN

**¿Está bien la arquitectura?**
> **Sí, está BIEN. Pero puede estar EXCELENTE.**

```
Actual:                    Propuesto:
Python Dict              YAML/JSON + Dataclasses
(Flexible pero informal) (Formal pero flexible)
      ↓
Guardian.py             Guardian.py + Validator
(Inyecta parámetros)    (Inyecta + valida)
      ↓
Propiedades ad-hoc      Propiedades contractuales
(Lo que necesites)      (Lo que necesites + tipado)
```

**La clave:** "Contrato explícito"

Ahora es: "Espero que el panel tenga estos campos"  
Debería ser: "El panel DEBE tener estos campos"

---

## 🚀 ¿Qué hacemos?

Opciones:

1. **Fase 1 Solo** (1 día): Fix para export_cutting_list
2. **Fase 1 + 2** (4 días): Arquitectura robusta
3. **Fase 1 + 2 + 3** (1 semana): Sistema enterprise-ready

¿Tu preferencia?
