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

## Desarrollo (opcional)

Para capturar cambios de toolbar:

```bash
# Snapshot ANTES
python3 Macro/vdo_detect_config.py

# (Crea toolbar en FreeCAD UI)

# Snapshot DESPUÉS
python3 Macro/vdo_detect_config.py

# Ver diff
diff config/freecad_snapshots/snapshot_*/user.cfg

# Exportar cambios
python3 Macro/vdo_sync_config.py export
git add config/freecad/user.cfg
git commit -m "Update toolbar configuration"
git push
```
