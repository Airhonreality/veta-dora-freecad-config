# 🧪 Flujo Manual de Prueba: Clonación de Toolbar VDO

**Objetivo:** Probar que la toolbar custom se clona correctamente desde GitHub → FreeCAD local

---

## FASE 1: Capturar Configuración Inicial

### Paso 1.1: Crear snapshot ANTES

```bash
cd ~/Proyectos/DEVs/veta-dora-freecad-config
python3 Macro/vdo_detect_config.py
```

**Resultado esperado:**
```
✅ Snapshot guardado: config/freecad_snapshots/snapshot_20260921_134956
   user.cfg (27425 bytes)
```

---

## FASE 2: Crear Toolbar Manualmente en FreeCAD

### Paso 2.1: Abrir FreeCAD

```bash
freecad &
```

### Paso 2.2: Crear Toolbar Custom

1. **Menu:** `View → Toolbars → Create New`
2. **Nombre:** `CARPINTERIA TEST`
3. **Click en botón:** `Add custom toolbar item`
4. **Seleccionar:** Una macro ficticia (ej: "VDO_PanelEstandar")
5. **Agregar a la toolbar**
6. **Click OK**

**Resultado esperado:**
- Aparece una nueva toolbar con un botón
- El botón tiene un ícono

### Paso 2.3: Guardar y Cerrar

- **FreeCAD:** `File → Exit` (o cerrar)
- FreeCAD guarda automáticamente la configuración en `~/.config/FreeCAD/v1-1/user.cfg`

---

## FASE 3: Detectar Cambios

### Paso 3.1: Crear snapshot DESPUÉS

```bash
python3 Macro/vdo_detect_config.py
```

**Resultado esperado:**
```
✅ Snapshot guardado: config/freecad_snapshots/snapshot_20260921_135101
   user.cfg (27450 bytes)
```

### Paso 3.2: Ver el diff

```bash
diff -u config/freecad_snapshots/snapshot_20260921_134956/user.cfg \
         config/freecad_snapshots/snapshot_20260921_135101/user.cfg
```

**Verás cambios en:**
- Sección `Toolbar` (dentro de `Workbench`)
- Posiblemente nuevas definiciones de macros

---

## FASE 4: Exportar Configuración al Repo

### Paso 4.1: Copiar user.cfg al repo

```bash
python3 Macro/vdo_sync_config.py export
```

**Resultado esperado:**
```
✅ Exportado:
   Desde: /home/javi/.config/FreeCAD/v1-1/user.cfg
   Hacia: /home/javi/Proyectos/DEVs/veta-dora-freecad-config/config/freecad/user.cfg
```

### Paso 4.2: Revisar cambios

```bash
git diff config/freecad/user.cfg
```

**Verás:**
- Nuevas líneas con `<FCParamGroup Name="Custom_1">` (toolbar)
- Botones dentro

---

## FASE 5: Commit y Push

```bash
git add config/freecad/user.cfg
git commit -m "Add custom toolbar CARPINTERIA TEST with buttons"
git push origin master
```

---

## FASE 6: Simular Instalación Limpia

### Paso 6.1: Eliminar toolbar local

```bash
# Opción A: Limpiar FreeCAD (opción fácil)
rm -rf ~/.config/FreeCAD/v1-1/user.cfg

# Opción B: Borrar solo la toolbar (manual en FreeCAD UI)
# - Abrir FreeCAD
# - View → Toolbars → Ver que "CARPINTERIA TEST" aparece
# - Right click en toolbar → Delete
# - Cerrar FreeCAD
```

### Paso 6.2: Verificar que desapareció

```bash
freecad &
```

**Verificar:** La toolbar "CARPINTERIA TEST" NO aparece

Cerrar FreeCAD.

---

## FASE 7: Simular Clonación Desde GitHub

### Paso 7.1: Hacer git pull (simular update)

Si ya tienes el repo local, simplemente:

```bash
git pull origin master
```

(Esto trae los cambios del user.cfg)

---

## FASE 8: Instalar con Restauración de Config

### Paso 8.1: Ejecutar instalador VDO

**Opción A: Dentro de FreeCAD**

```
FreeCAD → Macro → Ejecutar → Seleccionar vdo_install.py
```

**Opción B: Desde terminal**

```bash
python3 Macro/vdo_install.py
```

**Resultado esperado:**
```
🚀 INSTALADOR VDO
📁 Repositorio origen: /home/javi/Proyectos/DEVs/veta-dora-freecad-config
📁 FreeCAD Macro dir: /home/javi/.local/share/FreeCAD/Macro/

📦 Copiando archivos...
📂 Macro/ (fuente canónica):
   ✅ vdo_panel_estandar.FCMacro
   ... (más macros)

✅ Configuración restaurada (toolbar, botones)
   ⚠️ IMPORTANTE: Reinicia FreeCAD para ver los cambios
```

---

## FASE 9: Verificación Final

### Paso 9.1: Reiniciar FreeCAD

```bash
freecad &
```

### Paso 9.2: Comprobar que la toolbar aparece

**Verificar:**
1. ✅ La toolbar "CARPINTERIA TEST" aparece
2. ✅ El botón tiene el ícono correcto
3. ✅ Hacer click en el botón → debería abrir la macro (o mostrar error, pero la toolbar existe)

### Paso 9.3: Verificar que las macros funcionan

- **Menu:** `Macro → Macros disponibles`
- **Verificar:** VDO_PanelEstandar, VDO_PanelFachada, etc. aparecen

---

## ✅ FLUJO COMPLETADO

Si llegaste aquí sin errores:

```
SNAPSHOT BEFORE → CREAR TOOLBAR EN UI → SNAPSHOT AFTER
    ↓
DIFF → EXPORT → COMMIT → PUSH
    ↓
DELETE LOCAL → PULL → INSTALL
    ↓
✅ TOOLBAR APARECE EN NUEVO FREECAD
```

---

## 📋 Troubleshooting

### P: La toolbar no aparece después de `vdo_install.py`
**R:** 
- Asegúrate de reiniciar FreeCAD
- Verifica: `cat ~/.config/FreeCAD/v1-1/user.cfg | grep "CARPINTERIA TEST"`
- Si no aparece, el export/import falló

### P: `vdo_detect_config.py` dice "FreeCAD config no encontrada"
**R:**
- Verifica que FreeCAD se haya ejecutado al menos una vez
- Comprueba: `ls ~/.config/FreeCAD/`

### P: `git diff` no muestra cambios
**R:**
- Verifica que FreeCAD guardó la configuración (cerró normalmente)
- Comprueba: `diff ~/.config/FreeCAD/v1-1/user.cfg config/freecad/user.cfg`

---

## 🎯 Próximos Pasos (Fase 2)

Una vez validado este flujo:

1. **Automatizar capture/diff/restore** con vdo_capture.py
2. **Crear install.sh/install.bat** que haga todo automáticamente
3. **Documentar en README.md** para usuarios finales
