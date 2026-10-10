# -*- coding: utf-8 -*-
# =====================================================================
# vdo_panel_core.py
# Motor unificado de paneles VDO — AXIOMA 5: agnóstico de semántica
# Axioma 2: Lógica geométrica pura, sin dependencias de UI
#
# Modela SOLO una pieza física (tablero) con atributos físicos:
#   - orientacion (OBLIGATORIA, vocabulario del manifiesto)
#   - cantos por lado (RIG / FX / SMRG)
#   - material_ref (opcional)
#   - dimensiones/espesor (expresiones paramétricas)
# No acopla reglas de semántica de mobiliario (fachada/base/división/...).
# =====================================================================

import FreeCAD as App
import sys

# Bootstrap
_vdo_macro_dir = App.getUserMacroDir(True)
if _vdo_macro_dir not in sys.path:
    sys.path.insert(0, _vdo_macro_dir)

import vdo_guardian
import vdo_defaults as VDO_D

CANTOS_VALIDOS = ("RIG", "FX", "SMRG")


def _validar_orientacion(configuracion):
    """Valida de forma estricta la clave 'orientacion'.

    Raises:
        ValueError: si falta o no pertenece al vocabulario del manifiesto.
    """
    if "orientacion" not in configuracion:
        raise ValueError(
            "Configuración inválida: falta la clave obligatoria 'orientacion'. "
            "Ningún panel puede crearse sin definir su orientación "
            f"({', '.join(VDO_D.ORIENTACIONES_VALIDAS)}).")

    orientacion = configuracion["orientacion"]
    if orientacion not in VDO_D.ORIENTACIONES_VALIDAS:
        raise ValueError(
            f"Orientación inválida: '{orientacion}'. "
            f"Debe ser una de: {', '.join(VDO_D.ORIENTACIONES_VALIDAS)}.")
    return orientacion


def crear_pieza(configuracion):
    """
    Función principal del motor de paneles (agnóstico de semántica).

    Args:
        configuracion (dict): {
            "nombre": str,
            "etiqueta": str,      # tag libre, NO dirige geometría
            "orientacion": "horizontal" | "vertical",   # OBLIGATORIO
            "cantos": {"norte": str, "sur": str, "este": str, "oeste": str},
            "material_ref": str   # opcional
        }

    Returns:
        FreeCAD.Part.Box: El panel creado
    """
    # 1. Validación estricta de orientación
    orientacion = _validar_orientacion(configuracion)

    # 2. Asegurar entorno
    doc = vdo_guardian.vdo_guard()
    if not doc:
        print("❌ [VDO Error] No hay documento activo.")
        return None

    # 3. Extraer parámetros
    nombre = configuracion.get("nombre", "Panel")
    cantos = configuracion.get("cantos", {})
    etiqueta = configuracion.get("etiqueta", nombre)
    material_ref = configuracion.get("material_ref", "melamina_standar")

    # 4. Crear o recuperar geometría
    panel = doc.getObject(nombre)
    if panel:
        print(f"⚠️ '{nombre}' ya existe. Actualizando...")
    else:
        panel = doc.addObject("Part::Box", nombre)
        print(f"📦 Panel creado: {nombre}")

    # 5. Mapeo de ejes según orientación (expresiones paramétricas)
    ejes = VDO_D.obtener_mapeo_orientacion(orientacion)
    panel.setExpression("Length", f"<<Params>>.{ejes['X']}")
    panel.setExpression("Width", f"<<Params>>.{ejes['Y']}")
    panel.setExpression("Height", f"<<Params>>.{ejes['Z']}")

    # 6. Placement libre (identidad): la orientación NO se modela con rotación;
    #    la pose pertenece al mueble/espacio que posiciona la pieza.
    panel.Placement = App.Placement()

    # 7. Inyectar propiedades físicas (sin semántica de mobiliario)
    _inyectar_propiedades(panel, orientacion, cantos, etiqueta, material_ref)

    # 8. Recomputar
    doc.recompute()
    print(f"✅ Panel '{nombre}' configurado: orientacion='{orientacion}'")

    return panel


def _inyectar_propiedades(panel, orientacion, cantos, etiqueta, material_ref):
    """Inyecta propiedades físicas personalizadas al panel (sin semántica)."""

    # Identificador de pieza exportable
    if not hasattr(panel, "VDO_Tipo"):
        panel.addProperty("App::PropertyString", "VDO_Tipo", "VDO")
    panel.VDO_Tipo = "panel"

    # Orientación (atributo físico libre, visible en el panel de propiedades)
    if not hasattr(panel, "VDO_Orientacion"):
        panel.addProperty("App::PropertyEnumeration", "VDO_Orientacion", "VDO",
                          "Orientación del panel")
        panel.VDO_Orientacion = VDO_D.ORIENTACIONES_VALIDAS
    panel.VDO_Orientacion = orientacion

    # Etiqueta (tag libre, no dirige geometría)
    if not hasattr(panel, "VDO_Etiqueta"):
        panel.addProperty("App::PropertyString", "VDO_Etiqueta", "VDO")
    panel.VDO_Etiqueta = etiqueta

    # Material de referencia (manifiesto)
    if not hasattr(panel, "VDO_Material_Ref"):
        panel.addProperty("App::PropertyString", "VDO_Material_Ref", "VDO")
    panel.VDO_Material_Ref = material_ref

    # === CANTOS (4 direcciones) — Enum: RIG, FX, SMRG ===
    for direccion in ["Norte", "Sur", "Este", "Oeste"]:
        prop_name = f"VDO_Canto_{direccion}"
        if not hasattr(panel, prop_name):
            panel.addProperty("App::PropertyEnumeration", prop_name, "Cantos")
            setattr(panel, prop_name, list(CANTOS_VALIDOS))
        canto_value = cantos.get(direccion.lower(), "FX")
        if canto_value not in CANTOS_VALIDOS:
            raise ValueError(
                f"Canto inválido en '{direccion}': '{canto_value}'. "
                f"Debe ser uno de: {', '.join(CANTOS_VALIDOS)}.")
        setattr(panel, prop_name, canto_value)
