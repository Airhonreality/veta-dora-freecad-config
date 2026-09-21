#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vdo_loader.py
Cargador centralizado de configuración VDO desde JSON Schema

Lee vdo_manifest.json, valida contra schema, y proporciona acceso tipado.
"""

import json
import os
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("❌ Instala jsonschema: pip install jsonschema")
    sys.exit(1)


class VDOManifestLoader:
    """Cargador centralizado del manifest VDO"""

    def __init__(self, manifest_path=None, schema_path=None):
        if manifest_path is None:
            # Buscar en Macro/
            script_dir = Path(__file__).parent
            manifest_path = script_dir / "vdo_manifest.json"

        if schema_path is None:
            # Buscar en schemas/
            script_dir = Path(__file__).parent
            schema_path = script_dir.parent / "schemas" / "vdo_manifest_schema.json"

        self.manifest_path = Path(manifest_path)
        self.schema_path = Path(schema_path)
        self.manifest = None
        self.schema = None

    def cargar(self):
        """Carga y valida el manifest"""
        # Cargar JSON
        if not self.manifest_path.exists():
            print(f"❌ Archivo no encontrado: {self.manifest_path}")
            return False

        if not self.schema_path.exists():
            print(f"❌ Schema no encontrado: {self.schema_path}")
            return False

        try:
            with open(self.manifest_path) as f:
                self.manifest = json.load(f)

            with open(self.schema_path) as f:
                self.schema = json.load(f)

            print(f"✅ Manifest cargado: {self.manifest_path}")
            print(f"✅ Schema cargado: {self.schema_path}")

        except json.JSONDecodeError as e:
            print(f"❌ Error JSON: {e}")
            return False

        # Validar
        try:
            jsonschema.validate(self.manifest, self.schema)
            print("✅ Manifest válido según schema")
            return True
        except jsonschema.ValidationError as e:
            print(f"❌ Error de validación: {e.message}")
            print(f"   Ruta: {'.'.join(str(x) for x in e.path)}")
            return False

    def get_material(self, material_id):
        """Obtiene especificación de material"""
        if not self.manifest:
            return None
        return self.manifest.get("materiales", {}).get(material_id)

    def get_hardware(self, hardware_id):
        """Obtiene especificación de herraje"""
        if not self.manifest:
            return None
        return self.manifest.get("herrajes", {}).get(hardware_id)

    def get_process(self, process_id):
        """Obtiene especificación de proceso"""
        if not self.manifest:
            return None
        return self.manifest.get("procesos", {}).get(process_id)

    def validar_compatibilidad(self, material_id, hardware_id):
        """Valida si herraje es compatible con material"""
        material = self.get_material(material_id)
        hardware = self.get_hardware(hardware_id)

        if not material or not hardware:
            return False

        compatible_hw = material.get("herrajes_compatibles", [])
        return hardware_id in compatible_hw

    def calcular_costo_material(self, material_id, area_m2):
        """Calcula costo de material"""
        material = self.get_material(material_id)
        if not material:
            return 0
        return material.get("costo_m2", 0) * area_m2

    def listar_materiales(self):
        """Lista todos los materiales disponibles"""
        if not self.manifest:
            return []
        return list(self.manifest.get("materiales", {}).keys())

    def listar_herrajes(self):
        """Lista todos los herrajes disponibles"""
        if not self.manifest:
            return []
        return list(self.manifest.get("herrajes", {}).keys())


# Instancia global
_loader = None

def get_loader():
    """Obtiene la instancia global del loader"""
    global _loader
    if _loader is None:
        _loader = VDOManifestLoader()
        if not _loader.cargar():
            print("❌ No se pudo cargar el manifest VDO")
            _loader = None
    return _loader


if __name__ == "__main__":
    # Test
    loader = VDOManifestLoader()
    if loader.cargar():
        print("\n📊 Materiales disponibles:")
        for mat_id in loader.listar_materiales():
            mat = loader.get_material(mat_id)
            print(f"  - {mat_id}: {mat['nombre']} (${mat['costo_m2']}/m²)")

        print("\n📊 Herrajes disponibles:")
        for hw_id in loader.listar_herrajes():
            hw = loader.get_hardware(hw_id)
            print(f"  - {hw_id}: {hw['nombre']} (${hw['costo_unitario']} c/u)")

        print("\n✅ Sistema listo para usar")
    else:
        print("\n❌ Error cargando manifest")
