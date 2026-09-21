# 🚀 VDO - Instalación Minimalista

**Un solo script. Cero ruido.**

---

## Opción 1: Desde Terminal (Recomendado)

```bash
git clone https://github.com/Airhonreality/veta-dora-freecad-config.git
cd veta-dora-freecad-config
python3 Macro/vdo_clone.py
```

Luego abre FreeCAD y verifica que las macros aparecen.

---

## Opción 2: Desde FreeCAD

1. **FreeCAD → Macro → Ejecutar**
2. Selecciona `vdo_clone.py`
3. Listo

---

## ¿Qué hace?

```
vdo_clone.py
  ├─ Detecta dónde está tu FreeCAD
  ├─ Detecta dónde está el repo
  ├─ Copia macros
  ├─ Restaura toolbar + configuración
  └─ Fin
```

---

## Notas

- ✅ **Auto-detecta rutas** (pregunta a FreeCAD si está disponible)
- ✅ **Funciona en cualquier OS** (Linux, Windows, macOS)
- ✅ **Sin dependencias externas** (solo Python 3 + FreeCAD si quieres)
- ✅ **Mínimo código** (sin init.py, sin init.gui.py, sin bash/batch)
- ✅ **Backup automático** de configuración anterior

---

## Troubleshooting

**P: "Repo no encontrado"**  
R: Asegúrate de ejecutar desde dentro de la carpeta clonada

**P: "Macro dir no encontrado"**  
R: Abre FreeCAD una vez primero para que cree la estructura

**P: La toolbar no aparece**  
R: Reinicia FreeCAD después de ejecutar vdo_clone.py

---

## Desarrollo: Publicar Cambios del SDK

**El flujo normal:**

1. En FreeCAD: Crea macros, modifica toolbar, ajusta configuración
2. Ejecuta desde FreeCAD: `Macro → Ejecutar → vdo_publish.py`
3. ¡Listo! Todo se sincroniza a GitHub automáticamente

**Qué sincroniza vdo_publish.py:**
- ✅ Macros nuevas/modificadas (*.py, *.FCMacro)
- ✅ Iconos/assets (*.svg)
- ✅ Configuración (toolbar, settings)
- ✅ git add + commit + push automático

---

## Herramientas Avanzadas (opcional)

**Capturar cambios de configuración manualmente:**

```bash
# Snapshot ANTES
python3 Macro/vdo_detect_config.py

# (Crea toolbar en FreeCAD UI)

# Snapshot DESPUÉS
python3 Macro/vdo_detect_config.py

# Ver exactamente qué cambió
diff config/freecad_snapshots/snapshot_*/user.cfg
```

**Sincronizar manualmente (sin git):**

```bash
# Solo copiar config local → repo
python3 Macro/vdo_sync_config.py export

# Solo restaurar config repo → local
python3 Macro/vdo_sync_config.py import
```
