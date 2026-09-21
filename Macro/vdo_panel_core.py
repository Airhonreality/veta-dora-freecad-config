# -*- coding: utf-8 -*-
# =====================================================================
# vdo_panel_core.py
# Motor unificado de paneles VDO
# Axioma 2: Lógica geométrica pura, sin dependencias de UI
# =====================================================================

import FreeCAD as App
import Part
import sys

# Bootstrap
_vdo_macro_dir = App.getUserMacroDir(True)
if _vdo_macro_dir not in sys.path:
    sys.path.insert(0, _vdo_macro_dir)

import vdo_guardian


def crear_pieza(configuracion):
    """
    Función principal del motor de paneles.
    
    Args:
        configuracion (dict): {
            "tipo": "estandar" | "fachada",
            "nombre": str,
            "cantos": {"norte": bool, "sur": bool, "este": bool, "oeste": bool},
            "etiqueta": str
        }
    
    Returns:
        FreeCAD.Part.Box: El panel creado
    """
    # 1. Asegurar entorno
    doc = vdo_guardian.vdo_guard()
    
    if not doc:
        print("❌ [VDO Error] No hay documento activo.")
        return None
    
    # 2. Extraer parámetros
    tipo = configuracion.get("tipo", "estandar")
    nombre = configuracion.get("nombre", f"Panel_{tipo}")
    cantos = configuracion.get("cantos", {})
    etiqueta = configuracion.get("etiqueta", tipo)
    
    # 3. Crear o recuperar geometría
    panel = doc.getObject(nombre)
    if panel:
        print(f"⚠️ '{nombre}' ya existe. Actualizando...")
    else:
        panel = doc.addObject("Part::Box", nombre)
        print(f"📦 Panel creado: {nombre}")
    
    # 4. Inyectar dimensiones paramétricas
    panel.setExpression("Length", "<<Params>>.ancho")
    panel.setExpression("Width", "<<Params>>.fondo")
    panel.setExpression("Height", "<<Params_Melamina>>.espesor")
    
    # 5. Inyectar metadatos
    _inyectar_propiedades(panel, tipo, cantos, etiqueta)
    
    # 6. Recomputar
    doc.recompute()
    print(f"✅ Panel '{nombre}' configurado como '{tipo}'")
    
    return panel


def _inyectar_propiedades(panel, tipo, cantos, etiqueta):
    """Inyecta propiedades personalizadas al panel."""
    
    # Tipo de panel
    if not hasattr(panel, "VDO_Tipo"):
        panel.addProperty("App::PropertyString", "VDO_Tipo", "VDO")
    panel.VDO_Tipo = tipo
    
    # Etiqueta
    if not hasattr(panel, "VDO_Etiqueta"):
        panel.addProperty("App::PropertyString", "VDO_Etiqueta", "VDO")
    panel.VDO_Etiqueta = etiqueta
    
    # Cantos (4 direcciones)
    for direccion in ["Norte", "Sur", "Este", "Oeste"]:
        prop_name = f"VDO_Canto {direccion}"
        if not hasattr(panel, prop_name):
            panel.addProperty("App::PropertyBool", prop_name, "VDO")
        setattr(panel, prop_name, cantos.get(direccion.lower(), False))
