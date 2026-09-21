# 🚀 INSTALADOR VDO - Veta de Oro

## 📋 Opciones de Instalación

### Opción 1: Script de Inyección de Toolbar (Recomendado)

Desde FreeCAD, ejecutar:

```python
# Macro → Ejecutar → vdo_toolbar_inject.py
```

Esto inyecta la toolbar "CARPINTERIA - VDO" directamente en la configuración de FreeCAD (`user.cfg`) sin necesidad de workbench. La toolbar aparece en todos los workbenches con 4 botones funcionales.

### Opción 2: Dentro de FreeCAD (Manual)

1. Abrir FreeCAD
2. Ir a **Macro → Ejecutar Macro**
3. Navegar hasta `Codigo_VDO/vdo_install.py`
4. Hacer clic en **Ejecutar**

---

### Opción 3: Arranque Automático

Si copias `Init.py` e `InitGui.py` a la carpeta de macros de FreeCAD (`~/.local/share/FreeCAD/Macro/`), el sistema VDO se cargará automáticamente cada vez que FreeCAD inicie.

---

## 📁 Estructura del Repositorio

```
Codigo_VDO/
├── vdo_install.py        ← Instalador maestro (legacy)
├── instalar_vdo.sh       ← Script Linux/Mac (legacy)
├── instalar_vdo.bat      ← Script Windows (legacy)
├── Init.py               ← Inicializador (auto, legacy)
├── InitGui.py            ← Inicializador con GUI (legacy)
├── Macro/                ← Todos los archivos VDO
│   ├── vdo_manifest.py              ← Contrato de datos
│   ├── vdo_guardian.py              ← Guardián de dependencias
│   ├── vdo_panel_core.py            ← Motor central de paneles
│   ├── vdo_coco_core.py             ← Motor central de cofres
│   ├── VDO_Crear_Hoja_Melamina.FCMacro
│   ├── vdo_panel_estandar.FCMacro
│   ├── vdo_panel_fachada.FCMacro
│   ├── vdo_coco_4c.FCMacro
│   ├── vdo_toolbar_inject.py        ← Script de inyección de toolbar
│   └── icons/                       ← Iconos SVG
├── Documentacion/        ← Documentación del proyecto
│   ├── ARQUITECTURA_VDO.md          ← Visión de arquitectura
│   ├── CONTEXTO_TECNICO_VDO.md      ← Axiomas de arquitectura
│   ├── TOOLBAR_SOLUTION.md          ← Solución basada en XML
│   ├── PROGRESO_VDO.md              ← Progreso técnico (legacy)
│   ├── SESION_2026-09-20_TASK_PANEL_COCO.md  ← Notas de sesión
│   └── diagramas/                   ← Diagramas de arquitectura
└── PROGRESO_VDO.yaml    ← Registro estructurado de progreso
```

---

## 🔧 Qué Hace el Instalador

1. **Detecta** la ruta de macros de FreeCAD
2. **Copia** todos los archivos a esa carpeta
3. **Registra** los comandos VDO
4. **Crea** el workbench "VDO - Muebles Paramétricos"
5. **Crea** la toolbar con botones

---

## 🎯 Después de Instalar

1. Reiniciar FreeCAD (recomendado)
2. Seleccionar workbench: **VDO - Muebles Paramétricos**
3. Usar la toolbar:
   - 📋 Crear Hoja Parámetros (primera vez)
   - 📦 Panel Estándar
   - 📦 Panel Fachada
   - 🗄️ COCO 4C

---

## ❓ Solución de Problemas

### "FreeCAD no encontrado"
- Asegúrese de tener FreeCAD instalado
- El script busca en ubicaciones comunes automáticamente

### "Error al registrar workbench"
- Verifique que no haya otra instancia de FreeCAD abierta
- Intente reiniciar FreeCAD

### "Comandos no aparecen"
- Verifique que el workbench "VDO - Muebles Paramétricos" esté seleccionado
- La toolbar debería aparecer automáticamente

---

## 📞 Soporte

Si tiene problemas, verifique:
1. Que FreeCAD esté instalado correctamente
2. Que los archivos estén en la ubicación correcta
3. Los logs en la consola de FreeCAD
