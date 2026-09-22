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
    panel.setExpression("Height", "<<Params>>.espesor")
    
    # 5. Inyectar metadatos
    _inyectar_propiedades(panel, tipo, cantos, etiqueta)
    
    # 6. Recomputar
    doc.recompute()
    print(f"✅ Panel '{nombre}' configurado como '{tipo}'")
    
    return panel


def _inyectar_propiedades(panel, tipo, cantos, etiqueta):
    """Inyecta propiedades personalizadas al panel."""

    # Tipo de panel (siempre "panel" para identificar que es una pieza exportable)
    if not hasattr(panel, "VDO_Tipo"):
        panel.addProperty("App::PropertyString", "VDO_Tipo", "VDO")
    panel.VDO_Tipo = "panel"

    # Subtipo (estandar, fachada, etc.) - Enum
    if not hasattr(panel, "VDO_Subtipo"):
        panel.addProperty("App::PropertyEnumeration", "VDO_Subtipo", "VDO")
        panel.VDO_Subtipo = ["estandar", "fachada"]
    panel.VDO_Subtipo = tipo

    # Etiqueta
    if not hasattr(panel, "VDO_Etiqueta"):
        panel.addProperty("App::PropertyString", "VDO_Etiqueta", "VDO")
    panel.VDO_Etiqueta = etiqueta

    # === CANTOS (4 direcciones) - Enum: FX, RIG, SMRG ===
    for direccion in ["Norte", "Sur", "Este", "Oeste"]:
        prop_name = f"VDO_Canto_{direccion}"
        if not hasattr(panel, prop_name):
            panel.addProperty("App::PropertyEnumeration", prop_name, "Cantos")
            setattr(panel, prop_name, ["FX", "RIG", "SMRG"])
        canto_value = cantos.get(direccion.lower(), "FX")
        setattr(panel, prop_name, canto_value)

    # === PROPIEDADES ESPECÍFICAS PARA FACHADA ===
    if tipo == "fachada":
        # Tipo de fachada: parche, semi-parche, embebida
        if not hasattr(panel, "VDO_TipoFachada"):
            panel.addProperty("App::PropertyEnumeration", "VDO_TipoFachada", "Fachada")
            panel.VDO_TipoFachada = ["parche", "semi-parche", "embebida"]
        panel.VDO_TipoFachada = cantos.get("tipo_fachada", "parche")

        # Holgura superior (mm)
        if not hasattr(panel, "VDO_HolgoraSuperior"):
            panel.addProperty("App::PropertyFloat", "VDO_HolgoraSuperior", "Fachada")
        panel.VDO_HolgoraSuperior = cantos.get("holgura_superior", 0.0)

        # Holgura inferior (mm)
        if not hasattr(panel, "VDO_HolgoraInferior"):
            panel.addProperty("App::PropertyFloat", "VDO_HolgoraInferior", "Fachada")
        panel.VDO_HolgoraInferior = cantos.get("holgura_inferior", 0.0)

        # Tolerancia (mm)
        if not hasattr(panel, "VDO_Tolerancia"):
            panel.addProperty("App::PropertyFloat", "VDO_Tolerancia", "Fachada")
        panel.VDO_Tolerancia = cantos.get("tolerancia", 0.0)
