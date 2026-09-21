# 🏗️ Contexto Técnico VDO - Arquitectura del Sistema

## 📖 Visión General

El sistema VDO (Veta de Oro) es un motor paramétrico para FreeCAD que genera muebles modulares de melamina. La arquitectura sigue el patrón **Code-as-UI** donde la configuración se define en código Python en lugar de interfaces gráficas manuales.

---

## 🧱 Axiomas de la Arquitectura

### Axioma 1: Datos Puros (Sin lógica)
**Archivo**: `vdo_manifest.py`

- Contrato de dependencias globales del taller
- Contiene: hojas, alias, valores, dependencias
- **No contiene lógica**: solo datos (exportable a JSON/ERP)
- Es la "fuente única de la verdad"

### Axioma 2: Motor Geométrico (Sin UI)
**Archivos**: `vdo_panel_core.py`, `vdo_coco_core.py`

- Lógica geométrica pura
- Expresiones enlazadas al Guardián
- Gestión de propiedades dinámicas
- **No tiene dependencias de UI**

### Axioma 3: Comandos (Capa UI)
**Archivos**: `vdo_*.FCMacro`

- Envoltorios ultraligeros (~25 líneas)
- Contienen solo parámetros de configuración
- Llaman al motor central con sus respectivos parámetros
- **Uno por cada variante de mueble**

### Axioma 4: Inicialización (Orquestador)
**Archivo**: `InitGui.py` (futuro)

- Registra workbench en FreeCAD
- Inyecta comandos e iconos
- **Opcional**: se puede usar sin él

---

## 🔄 Patrón de Diseño: Thin Wrapper (Facade)

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPA UI (Envoltorios)                    │
│  vdo_panel_estandar.FCMacro  vdo_panel_fachada.FCMacro     │
│  vdo_coco_4c.FCMacro         (más variantes futuras)       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 CAPA MOTOR (Lógica Central)                 │
│  vdo_panel_core.py  →  crear_pieza(configuracion)          │
│  vdo_coco_core.py   →  crear_coco(configuracion)           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                CAPA DATOS (Manifiesto)                      │
│  vdo_manifest.py  →  VDO_MANIFEST (parámetros globales)    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│               CAPA VALIDACIÓN (Guardián)                    │
│  vdo_guardian.py  →  vdo_guard() (asegura entorno)         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  FreeCAD (Geometría 3D)                     │
│  Part::Box + Propiedades VDO + Expresiones Paramétricas    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📐 Modelos de Datos

### Panel (vdo_panel_core.py)

```python
# Entrada
configuracion = {
    "tipo": "estandar" | "fachada",
    "nombre": str,
    "cantos": {
        "norte": bool,
        "sur": bool,
        "este": bool,
        "oeste": bool
    },
    "etiqueta": str
}

# Salida (FreeCAD Object)
panel = {
    "Type": "Part::Box",
    "Length": "<<Params>>.ancho",
    "Width": "<<Params>>.fondo",
    "Height": "<<Params_Melamina>>.espesor",
    "VDO_Tipo": str,
    "VDO_Etiqueta": str,
    "VDO_Canto Norte": bool,
    "VDO_Canto Sur": bool,
    "VDO_Canto Este": bool,
    "VDO_Canto Oeste": bool
}
```

### Cofre (vdo_coco_core.py)

```python
# Entrada
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

# Salida (FreeCAD Group)
coco = {
    "Type": "App::DocumentObjectGroup",
    "Children": [
        "PANEL_LAT_IZQ",
        "PANEL_LAT_DER",
        "PANEL_BASE",
        "PANEL_TECHO",
        "PANEL_FONDO"  # condicional
    ]
}
```

---

## � Reglas de Negocio

### 1. CANTOS

| Tipo Panel | Cantos por Defecto |
|------------|-------------------|
| `estandar` | Selectivos (ej: solo este) |
| `fachada` | 4 cantos gruesos |

### 2. FONDO (RESPALDO)

| Condición | Comportamiento |
|-----------|----------------|
| `fondo = False` | No existe en el modelo |
| `calibre ≤ 8mm` | Ranurado (internas + 2×ranura) |
| `calibre > 8mm` | Sin ranura (retranqueado) |

### 3. ESTRUCTURA (TAPA/BASE)

| Tapa | Base | Resultado |
|------|------|-----------|
| `externo` | `interno` | Tapa cubre laterales, base cabe entre ellos |
| `externo` | `externo` | Ambos cubren laterales |
| `interno` | `interno` | Ambos caben entre laterales |
| `interno` | `externo` | Tapa cabe, base cubre |

---

## 🔧 Sistema de Propiedades VDO

Todas las propiedades personalizadas se agrupan bajo la categoría **"VDO"** en FreeCAD:

| Propiedad | Tipo | Descripción |
|-----------|------|-------------|
| `VDO_Tipo` | String | Identifica el tipo de pieza |
| `VDO_Etiqueta` | String | Nombre descriptivo |
| `VDO_Canto Norte/Sur/Este/Oeste` | Bool | Presencia de cantos |
| `VDO_Calibre` | Float | Espesor del fondo |

**Uso en reportes/despiece:**
```python
# Filtrar piezas por tipo
for obj in doc.Objects:
    if hasattr(obj, "VDO_Tipo"):
        if obj.VDO_Tipo == "Fachada":
            print(f"Pieza de fachada: {obj.Name}")
```

---

## 📊 Dependencias del Sistema

### Hojas Obligatorias (FreeCAD Spreadsheet)

| Hoja | Propósito |
|------|-----------|
| `Params_Melamina` | Parámetros globales del taller |
| `Params` | Parámetros locales del módulo |

### Archivos Core

| Archivo | Propósito |
|---------|-----------|
| `vdo_manifest.py` | Contrato de datos |
| `vdo_guardian.py` | Validación de entorno |
| `vdo_panel_core.py` | Motor de paneles |
| `vdo_coco_core.py` | Motor de cofres |

### Archivos UI

| Archivo | Propósito |
|---------|-----------|
| `vdo_panel_estandar.FCMacro` | Panel estándar |
| `vdo_panel_fachada.FCMacro` | Panel fachada |
| `vdo_coco_4c.FCMacro` | COCO 4 paneles |

---

## 🚀 Flujo de Instalación

```
1. Copiar carpeta Macro/ a FreeCAD Macro Path
2. FreeCAD → Macro → Macros → Ejecutar vdo_guardian.py
3. Verificar: hojas Params_Melamina y Params creadas
4. Ejecutar vdo_coco_4c.FCMacro
5. Verificar: COCO_4C con 5 paneles
```

---

## 🎯 Próximos Pasos

### Fase 1: Validación
- [ ] Probar todas las macros en FreeCAD
- [ ] Verificar propiedades VDO en panel de propiedades
- [ ] Confirmar expresiones paramétricas funcionan

### Fase 2: UI
- [ ] Crear iconos diferenciados
- [ ] Asignar botones en barra de herramientas
- [ ] (Opcional) Crear InitGui.py

### Fase 3: Funcionalidad
- [ ] Generador de despiece (lista de cortes)
- [ ] Integración con ERP/reportes
- [ ] Más variantes de cofres

---

## 📝 Notas para Desarrolladores

### Para agregar una nueva variante:

1. Crear envoltorio `vdo_nueva_variante.FCMacro`
2. Definir configuración con parámetros soportados
3. Llamar al motor central correspondiente
4. Agregar icono en `icons/`
5. Actualizar `vdo_manifest.py` → `modulos_ui`

### Para agregar un nuevo parámetro:

1. Agregar en `vdo_manifest.py` → sección correspondiente
2. Actualizar función del motor para usar el parámetro
3. Actualizar envoltorios con valor por defecto
4. Documentar en `PROGRESO_VDO.md`

---

## 🔍 Debugging

### Errores Comunes

| Error | Causa | Solución |
|-------|-------|----------|
| `No hay documento activo` | FreeCAD sin archivo abierto | Crear nuevo documento |
| `Hoja no encontrada` | Guardian no ejecutado | Ejecutar `vdo_guardian.vdo_guard()` |
| `Import failed` | Path incorrecto | Verificar Bootstrap en envoltorio |

### Logs Útiles

```python
# El motor imprime:
"📦 Panel creado: Nombre"
"✅ Panel 'Nombre' configurado como 'fachada'"
"📐 Estructura: Tapa=externo, Base=interno"
"📦 Fondo delgado (6mm) con ranuras de 3mm"
```

---

*Contexto técnico generado automáticamente - Motor VDO v1.4.0*
