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
#
# Migrado a Part::FeaturePython para compartir el marco común VDO
# (clic derecho, doble clic, panel de configuración y colocación).
# =====================================================================

import sys

import FreeCAD as App
import Part

# Bootstrap
_vdo_macro_dir = App.getUserMacroDir(True)
if _vdo_macro_dir not in sys.path:
    sys.path.insert(0, _vdo_macro_dir)

import vdo_guardian
import vdo_defaults as VDO_D
import vdo_module_props as VDO_MOD
import vdo_reengrose as VDO_RE
from vdo_reengrose_solids import forma_ref
from vdo_view_base import VDOViewProviderBase

CANTOS_VALIDOS = ("RIG", "FX", "SMRG")


def add_reengrose_props(obj):
    """Anade las propiedades del motor de reengrose a un panel L1."""
    if not hasattr(obj, "VDO_Reengrose_Activo"):
        obj.addProperty(
            "App::PropertyBool", "VDO_Reengrose_Activo", "Reengrose",
            "Activa una tira o duplicado de refuerzo sobre el panel"
        ).VDO_Reengrose_Activo = False

    if not hasattr(obj, "VDO_Reengrose_Orientacion"):
        prop = obj.addProperty(
            "App::PropertyEnumeration", "VDO_Reengrose_Orientacion",
            "Reengrose",
            "Paralela al largo del panel o transversal cruzando el ancho")
        prop.VDO_Reengrose_Orientacion = list(VDO_RE.ORIENTACIONES)
        obj.VDO_Reengrose_Orientacion = "paralela"

    if not hasattr(obj, "VDO_Reengrose_Ancho"):
        obj.addProperty(
            "App::PropertyLength", "VDO_Reengrose_Ancho", "Reengrose",
            "Ancho de la tira de refuerzo en mm"
        ).VDO_Reengrose_Ancho = 70.0

    if not hasattr(obj, "VDO_Reengrose_Espesor"):
        obj.addProperty(
            "App::PropertyLength", "VDO_Reengrose_Espesor", "Reengrose",
            "Espesor de la tira; 0 usa el espesor del panel base"
        ).VDO_Reengrose_Espesor = 0.0

    if not hasattr(obj, "VDO_Reengrose_Cara"):
        prop = obj.addProperty(
            "App::PropertyEnumeration", "VDO_Reengrose_Cara", "Reengrose",
            "Cara del tablero donde se adhiere el refuerzo")
        prop.VDO_Reengrose_Cara = list(VDO_RE.CARAS)
        obj.VDO_Reengrose_Cara = "cara_a"

    if not hasattr(obj, "VDO_Reengrose_Alineacion"):
        prop = obj.addProperty(
            "App::PropertyEnumeration", "VDO_Reengrose_Alineacion",
            "Reengrose",
            "Posicion de la tira hacia el frente, centro o fondo")
        prop.VDO_Reengrose_Alineacion = list(VDO_RE.ALINEACIONES)
        obj.VDO_Reengrose_Alineacion = "frente"

    if not hasattr(obj, "VDO_Reengrose_Modo"):
        prop = obj.addProperty(
            "App::PropertyEnumeration", "VDO_Reengrose_Modo", "Reengrose",
            "Tira independiente o pacha encolada y canteada en bloque")
        prop.VDO_Reengrose_Modo = list(VDO_RE.MODOS)
        obj.VDO_Reengrose_Modo = "pacha"

    if not hasattr(obj, "VDO_Reengrose_Alcance"):
        prop = obj.addProperty(
            "App::PropertyEnumeration", "VDO_Reengrose_Alcance",
            "Reengrose",
            "Pacha parcial en tira o pacha total de toda la cara")
        prop.VDO_Reengrose_Alcance = list(VDO_RE.ALCANCES)
        obj.VDO_Reengrose_Alcance = "parcial"

    if not hasattr(obj, "VDO_Reengrose_PoliticaRepisa"):
        prop = obj.addProperty(
            "App::PropertyEnumeration", "VDO_Reengrose_PoliticaRepisa",
            "Reengrose",
            "Ante colision con repisa: retroceder o mochear en escuadra")
        prop.VDO_Reengrose_PoliticaRepisa = list(VDO_RE.POLITICAS_REPISA)
        obj.VDO_Reengrose_PoliticaRepisa = "retroceder"

    if not hasattr(obj, "VDO_Reengrose_PrioridadEncuentro"):
        prop = obj.addProperty(
            "App::PropertyEnumeration", "VDO_Reengrose_PrioridadEncuentro",
            "Reengrose",
            "Prioridad al cruzar tiras: vertical, horizontal o inglete 45")
        prop.VDO_Reengrose_PrioridadEncuentro = list(
            VDO_RE.PRIORIDADES_ENCUENTRO)
        obj.VDO_Reengrose_PrioridadEncuentro = "vertical_domina"

    if not hasattr(obj, "VDO_Reengrose_ChoqueNucleo"):
        prop = obj.addProperty(
            "App::PropertyEnumeration", "VDO_Reengrose_ChoqueNucleo",
            "Reengrose",
            "Choque contra panel nucleo: retroceso, mocheo o interrumpir tira")
        prop.VDO_Reengrose_ChoqueNucleo = list(
            VDO_RE.MODOS_CHOQUE_NUCLEO)
        obj.VDO_Reengrose_ChoqueNucleo = "retroceso"

    if not hasattr(obj, "VDO_Reengrose_JSON"):
        obj.addProperty(
            "App::PropertyString", "VDO_Reengrose_JSON", "Reengrose",
            "Instantanea JSON del modificador de reengrose"
        ).VDO_Reengrose_JSON = ""


def _validar_orientacion(configuracion):
    """Valida de forma estricta la clave 'orientacion'."""
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


def _limpiar_expresion(obj, prop):
    try:
        obj.clearExpression(prop)
    except Exception:
        pass


def aplicar_mapeo_orientacion(obj, orientacion):
    """Aplica las expresiones de Params según la orientación.

    `Largo`/`Ancho` son siempre las caras del tablero y `Espesor` su grosor
    (semántica de despiece), NO los ejes locales de la caja. Por eso el
    mapeo del manifiesto se traduce a esa semántica:
      - horizontal: Largo=ancho, Ancho=fondo, Espesor=espesor
      - vertical:   Largo=alto,  Ancho=fondo, Espesor=espesor
    """
    VDO_D.obtener_mapeo_orientacion(orientacion)  # valida el vocabulario
    if orientacion == "vertical":
        param_largo, param_ancho, param_espesor = "alto", "fondo", "espesor"
    else:
        param_largo, param_ancho, param_espesor = "ancho", "fondo", "espesor"

    _limpiar_expresion(obj, "Largo")
    _limpiar_expresion(obj, "Ancho")
    _limpiar_expresion(obj, "Espesor")
    obj.setExpression("Largo", f"<<Params>>.{param_largo}")
    obj.setExpression("Ancho", f"<<Params>>.{param_ancho}")
    obj.setExpression("Espesor", f"<<Params>>.{param_espesor}")


class PanelFeature:
    """FeaturePython que genera la geometría de un tablero VDO."""

    def __init__(self, obj):
        obj.addProperty(
            "App::PropertyLength", "Largo", "Dimensiones",
            "Largo del tablero (mm)").Largo = VDO_D.ANCHO_DEFAULT
        obj.addProperty(
            "App::PropertyLength", "Ancho", "Dimensiones",
            "Ancho del tablero (mm)").Ancho = VDO_D.FONDO_DEFAULT
        obj.addProperty(
            "App::PropertyLength", "Espesor", "Dimensiones",
            "Espesor del tablero (mm)").Espesor = VDO_D.ESPESOR_DEFAULT

        obj.addProperty(
            "App::PropertyString", "VDO_Tipo", "VDO",
            "Tipo de objeto").VDO_Tipo = "panel"

        prop_orient = obj.addProperty(
            "App::PropertyEnumeration", "VDO_Orientacion", "VDO",
            "Orientación del panel")
        prop_orient.VDO_Orientacion = VDO_D.ORIENTACIONES_VALIDAS
        if VDO_D.ORIENTACIONES_VALIDAS:
            obj.VDO_Orientacion = VDO_D.ORIENTACION_DEFAULT

        obj.addProperty(
            "App::PropertyString", "VDO_Etiqueta", "VDO",
            "Etiqueta libre de la pieza").VDO_Etiqueta = "Panel"

        obj.addProperty(
            "App::PropertyString", "VDO_Material_Ref", "VDO",
            "Material de la pieza"
        ).VDO_Material_Ref = "melamina_standar"

        for direccion in ["Norte", "Sur", "Este", "Oeste"]:
            prop_name = f"VDO_Canto_{direccion}"
            obj.addProperty(
                "App::PropertyEnumeration", prop_name, "Cantos",
                f"Canto {direccion}")
            setattr(obj, prop_name, list(CANTOS_VALIDOS))
            setattr(obj, prop_name, "FX")

        add_reengrose_props(obj)
        VDO_MOD.add_common_props(obj)

        obj.Proxy = self

    def execute(self, fp):
        try:
            largo = float(fp.Largo)
            ancho = float(fp.Ancho)
            espesor = float(fp.Espesor)
            if largo <= 0 or ancho <= 0 or espesor <= 0:
                fp.Shape = Part.Shape()
                return

            base = Part.makeBox(largo, ancho, espesor)
            try:
                mod = VDO_RE.desde_objeto(fp)
                if hasattr(fp, "VDO_Reengrose_JSON"):
                    fp.VDO_Reengrose_JSON = mod.to_json()
                if not mod.activo:
                    fp.Shape = base
                    return
                geo = VDO_RE.calcular_geometria_reengrose(
                    {"nombre": fp.Label or fp.Name,
                     "largo": largo, "ancho": ancho, "espesor": espesor},
                    mod)
                shapes = [base]
                for pieza in geo["refuerzos"]:
                    forma = forma_ref(pieza)
                    if forma is not None:
                        shapes.append(forma)
                fp.Shape = Part.makeCompound(shapes)
            except VDO_RE.ReengroseError as exc:
                App.Console.PrintWarning(
                    f"[VDO] Reengrose ignorado en '{fp.Label}': {exc}\n")
                fp.Shape = base
        except Exception as exc:
            App.Console.PrintError(
                f"[VDO] Error generando panel: {exc}\n")

    def dumps(self):
        return None

    def loads(self, state):
        return None


class ViewProviderPanel(VDOViewProviderBase):
    """ViewProvider del panel VDO."""

    MENU_LABEL = "Propiedades del Panel"
    ICON = "vdo_panel.svg"

    def get_panel_class(self):
        from vdo_panel_task import PanelTaskPanel
        return PanelTaskPanel


def crear_pieza(configuracion):
    """Función principal del motor de paneles (agnóstica de semántica).

    Args:
        configuracion (dict): {
            "nombre": str,
            "etiqueta": str,      # tag libre, NO dirige geometría
            "orientacion": "horizontal" | "vertical",   # OBLIGATORIO
            "cantos": {"norte": str, "sur": str, "este": str, "oeste": str},
            "material_ref": str,  # opcional
            "largo"/"ancho"/"espesor": float,  # opcional
            "usar_params": bool,  # opcional (default True)
            "rotacion": float, "anclaje": str  # opcionales
        }

    Returns:
        App.DocumentObject: El panel FeaturePython creado.
    """
    orientacion = _validar_orientacion(configuracion)

    doc = vdo_guardian.vdo_guard()
    if not doc:
        print("❌ [VDO Error] No hay documento activo.")
        return None

    nombre = configuracion.get("nombre", "Panel")
    cantos = configuracion.get("cantos", {})
    etiqueta = configuracion.get("etiqueta", nombre)
    material_ref = configuracion.get(
        "material_ref", "melamina_standar")

    es_nuevo = False
    panel = doc.getObject(nombre)
    if panel is not None and not isinstance(
            getattr(panel, "Proxy", None), PanelFeature):
        if panel.TypeId != "Part::Box":
            raise ValueError(
                f"Ya existe un objeto '{nombre}' ({panel.TypeId}) que no es "
                "un panel VDO. Usa otro nombre.")
        # Migración: un Part::Box viejo no puede tener ViewProvider Python.
        doc.removeObject(panel.Name)
        panel = None

    if panel:
        print(f"⚠️ '{nombre}' ya existe. Actualizando...")
        add_reengrose_props(panel)
    else:
        panel = doc.addObject("Part::FeaturePython", nombre)
        PanelFeature(panel)
        es_nuevo = True

    if App.GuiUp:
        ViewProviderPanel(panel.ViewObject)

    panel.VDO_Orientacion = orientacion
    panel.VDO_Etiqueta = etiqueta
    panel.VDO_Material_Ref = material_ref

    for direccion in ["Norte", "Sur", "Este", "Oeste"]:
        prop_name = f"VDO_Canto_{direccion}"
        canto_value = cantos.get(direccion.lower(), "FX")
        if canto_value not in CANTOS_VALIDOS:
            raise ValueError(
                f"Canto inválido en '{direccion}': '{canto_value}'. "
                f"Debe ser uno de: {', '.join(CANTOS_VALIDOS)}.")
        setattr(panel, prop_name, canto_value)

    usar_params = configuracion.get(
        "usar_params",
        not any(k in configuracion for k in ("largo", "ancho", "espesor")))
    if usar_params:
        aplicar_mapeo_orientacion(panel, orientacion)
    else:
        for prop in ("Largo", "Ancho", "Espesor"):
            _limpiar_expresion(panel, prop)
        if "largo" in configuracion:
            panel.Largo = configuracion["largo"]
        if "ancho" in configuracion:
            panel.Ancho = configuracion["ancho"]
        if "espesor" in configuracion:
            panel.Espesor = configuracion["espesor"]

    if "reengrose" in configuracion:
        VDO_RE.aplicar_a_objeto(panel, configuracion.get("reengrose"))

    rotacion = float(configuracion.get("rotacion", 0.0))
    panel.VDO_RotacionZ = rotacion
    panel.VDO_Anclaje = configuracion.get(
        "anclaje", VDO_MOD.ANCLAJE_DEFAULT)

    if rotacion:
        panel.Placement = App.Placement(
            panel.Placement.Base, VDO_MOD.rotacion_z(rotacion))
    elif es_nuevo:
        panel.Placement = App.Placement()

    doc.recompute()
    print(f"✅ Panel '{nombre}' configurado: orientacion='{orientacion}'")
    return panel
