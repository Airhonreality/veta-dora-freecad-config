# -*- coding: utf-8 -*-
# =====================================================================
# vdo_nesting_presets.py
# Gestor de presets de tableros para nesting
# Guardar/cargar configuraciones predefinidas en preferencias de FreeCAD
# =====================================================================

import FreeCAD
import json

class NestingPresetManager:
    """Gestiona presets de tableros para nesting."""

    PREFS_PATH = "User parameter:BaseApp/Preferences/NestingWorkbench/VDO"

    # Presets estándar del taller (2440×1830 es estándar EN)
    DEFAULT_PRESETS = {
        "Estándar EN": {"width": 2440, "height": 1830, "spacing": 15, "thickness": 3},
        "Medio Horizontal": {"width": 1220, "height": 2440, "spacing": 15, "thickness": 3},
        "Pequeño": {"width": 1200, "height": 900, "spacing": 12, "thickness": 3},
        "Cuadrado": {"width": 1000, "height": 1000, "spacing": 15, "thickness": 3},
        "Larguero": {"width": 3000, "height": 600, "spacing": 15, "thickness": 3},
    }

    @staticmethod
    def get_prefs():
        """Obtiene el objeto de preferencias."""
        return FreeCAD.ParamGet(NestingPresetManager.PREFS_PATH)

    @staticmethod
    def initialize_defaults():
        """Inicializa presets por defecto si no existen."""
        prefs = NestingPresetManager.get_prefs()

        # Verificar si ya hay presets
        if prefs.GetString("Presets", "") == "":
            # Guardar presets por defecto
            presets_data = {
                "list": list(NestingPresetManager.DEFAULT_PRESETS.keys()),
                "presets": NestingPresetManager.DEFAULT_PRESETS
            }
            prefs.SetString("Presets", json.dumps(presets_data))
            print("[VDO Nesting] Presets inicializados con valores por defecto")

    @staticmethod
    def get_all_presets():
        """Obtiene todos los presets disponibles."""
        prefs = NestingPresetManager.get_prefs()
        presets_json = prefs.GetString("Presets", "{}")

        try:
            data = json.loads(presets_json)
            return data.get("presets", NestingPresetManager.DEFAULT_PRESETS)
        except:
            return NestingPresetManager.DEFAULT_PRESETS

    @staticmethod
    def get_preset(name):
        """Obtiene un preset específico."""
        presets = NestingPresetManager.get_all_presets()
        return presets.get(name, None)

    @staticmethod
    def save_preset(name, width, height, spacing=15, thickness=3):
        """Guarda un nuevo preset."""
        prefs = NestingPresetManager.get_prefs()
        presets_json = prefs.GetString("Presets", "{}")

        try:
            data = json.loads(presets_json)
        except:
            data = {"list": [], "presets": {}}

        if "list" not in data:
            data["list"] = []
        if "presets" not in data:
            data["presets"] = {}

        # Agregar preset
        data["presets"][name] = {
            "width": width,
            "height": height,
            "spacing": spacing,
            "thickness": thickness
        }

        # Actualizar lista si no existe
        if name not in data["list"]:
            data["list"].append(name)

        prefs.SetString("Presets", json.dumps(data))
        print(f"[VDO Nesting] Preset '{name}' guardado")

    @staticmethod
    def delete_preset(name):
        """Elimina un preset."""
        prefs = NestingPresetManager.get_prefs()
        presets_json = prefs.GetString("Presets", "{}")

        try:
            data = json.loads(presets_json)
        except:
            return False

        if name in data.get("presets", {}):
            del data["presets"][name]

        if name in data.get("list", []):
            data["list"].remove(name)

        prefs.SetString("Presets", json.dumps(data))
        print(f"[VDO Nesting] Preset '{name}' eliminado")
        return True

    @staticmethod
    def get_preset_names():
        """Obtiene lista de nombres de presets."""
        presets = NestingPresetManager.get_all_presets()
        return list(presets.keys())

    @staticmethod
    def export_presets_to_json(filepath):
        """Exporta todos los presets a un archivo JSON."""
        presets = NestingPresetManager.get_all_presets()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(presets, f, indent=2, ensure_ascii=False)
        print(f"[VDO Nesting] Presets exportados a: {filepath}")

    @staticmethod
    def import_presets_from_json(filepath):
        """Importa presets desde un archivo JSON."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                new_presets = json.load(f)

            prefs = NestingPresetManager.get_prefs()
            existing_data = json.loads(prefs.GetString("Presets", "{}"))

            if "presets" not in existing_data:
                existing_data["presets"] = {}
            if "list" not in existing_data:
                existing_data["list"] = []

            # Merged presets
            for name, config in new_presets.items():
                existing_data["presets"][name] = config
                if name not in existing_data["list"]:
                    existing_data["list"].append(name)

            prefs.SetString("Presets", json.dumps(existing_data))
            print(f"[VDO Nesting] Presets importados desde: {filepath}")
            return True
        except Exception as e:
            print(f"[VDO Nesting] Error importando presets: {e}")
            return False


# Inicializar presets al cargar el módulo
NestingPresetManager.initialize_defaults()
